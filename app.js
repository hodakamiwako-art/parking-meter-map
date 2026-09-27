/* パーキングメーター地図 */
const TOKYO = [35.681, 139.767];
const LIST_MAX = 200;

const CARTO_KEY = (window.PAWMAP_CONFIG || {}).cartoApiKey || '';
const BASE = CARTO_KEY ? {
  light: `https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png?key=${CARTO_KEY}`,
  dark:  `https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png?key=${CARTO_KEY}`,
  attr: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
  subdomains: 'abcd', maxNativeZoom: 20,
} : {
  light: 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
  dark:  'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
  attr: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
  subdomains: 'abc', maxNativeZoom: 19,
};
const SRC_ATTR = '区間データ：<a href="https://parking-meter.jp/" target="_blank" rel="noopener">警視庁 時間制限駐車区間案内地図</a>';

const $ = s => document.querySelector(s);
const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

const state = { q: '', kind: '', ward: '', limit: '', here: null, sel: null };
let zones = [];
let shown = [];
let map, tiles, layer, hereMark;
const drawn = new Map(); // id → polyline 群

/* ---------- 端末への保存（読み込んだ GeoJSON） ---------- */
const DB = {
  open() {
    return new Promise((res, rej) => {
      const r = indexedDB.open('parkmap', 1);
      r.onupgradeneeded = () => r.result.createObjectStore('kv');
      r.onsuccess = () => res(r.result);
      r.onerror = () => rej(r.error);
    });
  },
  async get(k) {
    try {
      const db = await this.open();
      return await new Promise(res => {
        const q = db.transaction('kv').objectStore('kv').get(k);
        q.onsuccess = () => res(q.result);
        q.onerror = () => res(undefined);
      });
    } catch (e) { return undefined; }
  },
  async set(k, v) {
    try {
      const db = await this.open();
      db.transaction('kv', 'readwrite').objectStore('kv').put(v, k);
    } catch (e) { /* 保存できない環境でも表示はする */ }
  },
  async del(k) {
    try {
      const db = await this.open();
      db.transaction('kv', 'readwrite').objectStore('kv').delete(k);
    } catch (e) {}
  },
};

/* ---------- 地図 ---------- */
const darkQ = window.matchMedia('(prefers-color-scheme: dark)');
function setTiles() {
  if (tiles) map.removeLayer(tiles);
  tiles = L.tileLayer(darkQ.matches ? BASE.dark : BASE.light, {
    attribution: BASE.attr, subdomains: BASE.subdomains,
    maxNativeZoom: BASE.maxNativeZoom, maxZoom: 21, detectRetina: true,
  }).addTo(map);
}

function initMap() {
  map = L.map('map', { center: TOKYO, zoom: 13, zoomControl: false, minZoom: 9, maxZoom: 21, preferCanvas: true });
  L.control.zoom({ position: 'bottomright' }).addTo(map);
  map.attributionControl.addAttribution(SRC_ATTR);
  setTiles();
  darkQ.addEventListener?.('change', setTiles);
  layer = L.layerGroup().addTo(map);
  map.on('moveend', () => { if (!state.here) renderList(); });
  map.on('zoomend', highlight);
}

const COLORS = () => {
  const cs = getComputedStyle(document.documentElement);
  return { meter: cs.getPropertyValue('--meter').trim(), ticket: cs.getPropertyValue('--ticket').trim() };
};
const weight = () => Math.max(3, Math.min(9, map.getZoom() - 9));

function draw() {
  layer.clearLayers();
  drawn.clear();
  const col = COLORS();
  for (const z of shown) {
    const pls = z.lines.map(l => l.length === 1
      ? L.circleMarker(l[0], { radius: 6, color: col[z.kind], weight: 2, fillOpacity: .8 })
      : L.polyline(l, { color: col[z.kind], weight: weight(), opacity: .85, lineCap: 'round' }));
    pls.forEach(p => {
      p.on('click', () => openDetail(z, false));
      p.bindTooltip(esc(z.name || z.addr || '区間'), { sticky: true, direction: 'top' });
      layer.addLayer(p);
    });
    drawn.set(z.id, pls);
  }
  highlight();
}

function highlight() {
  drawn.forEach((pls, id) => pls.forEach(p => {
    if (p instanceof L.CircleMarker) return;
    p.setStyle({ weight: id === state.sel ? weight() + 5 : weight(), opacity: id === state.sel ? 1 : .85 });
    if (id === state.sel) p.bringToFront();
  }));
}

/* ---------- 絞り込みと一覧 ---------- */
function applyFilters() {
  const q = state.q.trim().toLowerCase();
  const terms = q ? q.split(/\s+/) : [];
  shown = zones.filter(z => {
    if (state.kind && z.kind !== state.kind) return false;
    if (state.ward && z.ward !== state.ward) return false;
    if (state.limit) {
      const lim = +state.limit;
      if (z.limitMin == null) return false;
      if (lim === 61 ? z.limitMin <= 60 : z.limitMin > lim) return false;
    }
    return terms.every(t => z.hay.includes(t));
  });
  $('#n').textContent = shown.length.toLocaleString();
  draw();
  renderList();
}

function meters(a, b) {
  const R = 6371000, r = Math.PI / 180;
  const dLat = (b[0] - a[0]) * r, dLng = (b[1] - a[1]) * r;
  const h = Math.sin(dLat / 2) ** 2 + Math.cos(a[0] * r) * Math.cos(b[0] * r) * Math.sin(dLng / 2) ** 2;
  return 2 * R * Math.asin(Math.sqrt(h));
}
const fmtDist = m => (m < 1000 ? `${Math.round(m / 10) * 10}m` : `${(m / 1000).toFixed(1)}km`);
const fmtLimit = z => (z.limitMin != null ? (z.limitMin % 60 === 0 && z.limitMin >= 60 ? `${z.limitMin / 60}時間` : `${z.limitMin}分`) : z.limit);
const fmtFee = z => (z.feeYen != null ? `${z.feeYen.toLocaleString()}円` : z.fee);

function renderList() {
  const origin = state.here || [map.getCenter().lat, map.getCenter().lng];
  $('#sortnote').textContent = state.here ? '現在地から近い順' : '地図の中心から近い順';
  const rows = shown
    .map(z => ({ z, d: meters(origin, z.center) }))
    .sort((a, b) => a.d - b.d)
    .slice(0, LIST_MAX);
  $('#list').innerHTML = rows.map(({ z, d }) => `
    <li data-id="${esc(z.id)}" class="${z.id === state.sel ? 'on' : ''}">
      <span class="k ${z.kind}"></span>
      <div class="body">
        <div class="nm">${esc(z.name || z.addr || '名称なし')}</div>
        <div class="meta">
          ${z.ward ? `<span>${esc(z.ward)}</span>` : ''}
          ${fmtLimit(z) ? `<span>${esc(fmtLimit(z))}</span>` : ''}
          ${fmtFee(z) ? `<span>${esc(fmtFee(z))}</span>` : ''}
        </div>
      </div>
      <span class="dist">${fmtDist(d)}</span>
    </li>`).join('') || '<li class="none">条件に合う区間はありません</li>';
}

/* ---------- 詳細 ---------- */
function openDetail(z, fly = true) {
  state.sel = z.id;
  highlight();
  document.querySelectorAll('#list li').forEach(li => li.classList.toggle('on', li.dataset.id === z.id));
  if (fly) {
    const b = L.latLngBounds(z.lines.flat());
    const wide = window.innerWidth > 760; // 広い画面では右に詳細が重なるので、その分よける
    map.flyToBounds(b, { maxZoom: 18, paddingTopLeft: [60, 60], paddingBottomRight: [wide ? 420 : 60, 60], duration: .6 });
    showTab('map');
  }
  const row = (k, v) => (v ? `<dt>${k}</dt><dd>${esc(v)}</dd>` : '');
  const [lat, lng] = z.center;
  const rawRows = Object.entries(z.raw)
    .filter(([, v]) => v !== null && v !== '' && typeof v !== 'object')
    .map(([k, v]) => `<tr><th>${esc(k)}</th><td>${esc(v)}</td></tr>`).join('');
  $('#detail').innerHTML = `
    <button class="close" aria-label="閉じる">×</button>
    <div class="badge ${z.kind}">${z.kind === 'ticket' ? 'パーキング・チケット' : 'パーキング・メーター'}</div>
    <h2>${esc(z.name || z.addr || '名称なし')}</h2>
    <dl>
      ${row('所在地', z.addr)}
      ${row('区市町村', z.ward)}
      ${row('制限時間', fmtLimit(z))}
      ${row('料金', fmtFee(z))}
      ${row('時間帯', z.hours)}
      ${row('曜日', z.days)}
      ${row('対象車両', z.vehicle)}
      ${row('台数', z.count)}
    </dl>
    <div class="acts">
      <a class="btn primary" href="https://www.google.com/maps/dir/?api=1&destination=${lat},${lng}&travelmode=driving" target="_blank" rel="noopener">Googleマップで経路</a>
      <a class="btn" href="https://www.google.com/maps/search/?api=1&query=${lat},${lng}" target="_blank" rel="noopener">場所を開く</a>
    </div>
    <p class="warn">現地の標識・メーターの表示が優先されます。規制時間外や、工事・行事で使えない場合があります。</p>
    ${rawRows ? `<details><summary>元データのすべての項目</summary><table>${rawRows}</table></details>` : ''}`;
  $('#detail').classList.add('open');
  $('#detail .close').onclick = closeDetail;
}

function closeDetail() {
  state.sel = null;
  highlight();
  $('#detail').classList.remove('open');
  document.querySelectorAll('#list li.on').forEach(li => li.classList.remove('on'));
}

/* ---------- 画面の組み立て ---------- */
function fillWards() {
  const wards = [...new Set(zones.map(z => z.ward).filter(Boolean))].sort((a, b) => a.localeCompare(b, 'ja'));
  $('#ward').innerHTML = '<option value="">区市町村：すべて</option>' +
    wards.map(w => `<option>${esc(w)}</option>`).join('');
  $('#ward').hidden = !wards.length;
}

function fitAll() {
  const pts = shown.flatMap(z => z.lines.flat());
  if (pts.length) map.fitBounds(L.latLngBounds(pts), { padding: [30, 30] });
}

function load(geojson) {
  zones = Zones.normalize(geojson);
  $('#empty').hidden = zones.length > 0;
  fillWards();
  applyFilters();
  fitAll();
}

function showTab(which) {
  document.body.dataset.tab = which;
  $('#tabList').setAttribute('aria-pressed', which === 'list');
  $('#tabMap').setAttribute('aria-pressed', which === 'map');
  if (which === 'map') setTimeout(() => map.invalidateSize(), 50);
}

function bind() {
  $('#q').addEventListener('input', e => { state.q = e.target.value; applyFilters(); });
  document.querySelectorAll('.seg button').forEach(b => b.addEventListener('click', () => {
    state.kind = b.dataset.kind;
    document.querySelectorAll('.seg button').forEach(x => x.setAttribute('aria-pressed', x === b));
    applyFilters();
  }));
  $('#ward').addEventListener('change', e => { state.ward = e.target.value; applyFilters(); fitAll(); });
  $('#limit').addEventListener('change', e => { state.limit = e.target.value; applyFilters(); });
  $('#list').addEventListener('click', e => {
    const li = e.target.closest('li[data-id]');
    if (li) openDetail(zones.find(z => z.id === li.dataset.id));
  });
  $('#fitall').addEventListener('click', () => { state.here = null; fitAll(); });
  $('#locate').addEventListener('click', () => {
    if (!navigator.geolocation) return;
    navigator.geolocation.getCurrentPosition(p => {
      state.here = [p.coords.latitude, p.coords.longitude];
      if (hereMark) map.removeLayer(hereMark);
      hereMark = L.circleMarker(state.here, { radius: 8, color: '#fff', weight: 3, fillColor: '#2A7FFF', fillOpacity: 1 }).addTo(map);
      map.setView(state.here, 17);
      renderList();
    }, () => alert('現在地を取得できませんでした'), { enableHighAccuracy: true, timeout: 10000 });
  });
  $('#importFile').addEventListener('change', async e => {
    const f = e.target.files[0];
    if (!f) return;
    try {
      const gj = JSON.parse(await f.text());
      const n = Zones.normalize(gj).length;
      if (!n) throw new Error('区間が見つかりません');
      await DB.set('geojson', gj);
      load(gj);
      alert(`${n.toLocaleString()}区間を読み込みました`);
    } catch (err) {
      alert('読み込めませんでした（GeoJSON 形式のファイルを選んでください）\n' + err.message);
    }
    e.target.value = '';
  });
  $('#tabList').addEventListener('click', () => showTab('list'));
  $('#tabMap').addEventListener('click', () => showTab('map'));
  document.addEventListener('keydown', e => { if (e.key === 'Escape') closeDetail(); });
}

async function boot() {
  initMap();
  bind();
  showTab('list');
  // 端末で読み込んだデータがあればそれを、なければ公開用に置いたデータを使う
  const local = await DB.get('geojson');
  if (local) return load(local);
  try {
    const res = await fetch('data/zones.geojson', { cache: 'no-cache' });
    if (res.ok) return load(await res.json());
  } catch (e) {}
  load({ type: 'FeatureCollection', features: [] });
}

boot();
