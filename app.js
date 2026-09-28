/* パーキング・メーター・マップ */
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
const SRC_ATTR = '区間データ：<a href="https://parking-meter.jp/" target="_blank" rel="noopener">警視庁</a>（<a href="https://creativecommons.org/licenses/by/4.0/deed.ja" target="_blank" rel="noopener">CC BY 4.0</a>）・<a href="https://www.police.pref.osaka.lg.jp/kotsu/tyusya/1/1/index.html" target="_blank" rel="noopener">大阪府警察</a>・神奈川県警察・北海道警察・京都府警察（線は OpenStreetMap から作成）';
const PREFS = ['北海道', '東京都', '神奈川県', '京都府', '大阪府']; // エリアの選択肢と「◯◯を表示」の並び

// 国土地理院の地名検索・住所の逆引き（鍵不要）
const GSI_SEARCH = 'https://msearch.gsi.go.jp/address-search/AddressSearch?q=';
const GSI_REVERSE = 'https://mreversegeocoder.gsi.go.jp/reverse-geocoder/LonLatToAddress';
// 逆引きは市区町村コードで返るので、都内の区市の名前を引けるようにしておく
const MUNI = {
  13101: '千代田区', 13102: '中央区', 13103: '港区', 13104: '新宿区', 13105: '文京区', 13106: '台東区',
  13107: '墨田区', 13108: '江東区', 13109: '品川区', 13110: '目黒区', 13111: '大田区', 13112: '世田谷区',
  13113: '渋谷区', 13114: '中野区', 13115: '杉並区', 13116: '豊島区', 13117: '北区', 13118: '荒川区',
  13119: '板橋区', 13120: '練馬区', 13121: '足立区', 13122: '葛飾区', 13123: '江戸川区',
  13201: '八王子市', 13202: '立川市', 13203: '武蔵野市', 13204: '三鷹市', 13205: '青梅市', 13206: '府中市',
  13207: '昭島市', 13208: '調布市', 13209: '町田市', 13210: '小金井市', 13211: '小平市', 13212: '日野市',
  13213: '東村山市', 13214: '国分寺市', 13215: '国立市', 13218: '福生市', 13219: '狛江市', 13220: '東大和市',
  13221: '清瀬市', 13222: '東久留米市', 13223: '武蔵村山市', 13224: '多摩市', 13225: '稲城市', 13227: '羽村市',
  13228: 'あきる野市', 13229: '西東京市',
};

const $ = s => document.querySelector(s);
const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

const state = { pref: '', ward: '', town: '', days: '', at: '', limit: '', vehicle: '', sort: 'near', here: null, sel: null,
  // 運転モード：follow＝地図が現在地を追う、place＝検索した場所、pick＝カードで選んだ区間
  follow: true, place: null, pick: null };
const drive = () => document.body.classList.contains('drive');
const IOS = /iPhone|iPad|iPod/.test(navigator.userAgent) || (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1);
// 条件入力の項目（画面の並び順）。数えるのとクリアに使う
const FILTERS = ['pref', 'ward', 'town', 'days', 'at', 'limit', 'vehicle'];
let zones = [];
let holidays = { years: [], dates: {} }; // data/holidays.json
let shown = [];
let map, tiles, layer, hereMark, placeMark;
const drawn = new Map(); // id → polyline 群
const addrCache = new Map();

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
  map = L.map('map', { center: TOKYO, zoom: 13, zoomControl: false, minZoom: 6, maxZoom: 21, preferCanvas: true });
  map.zoomCtl = L.control.zoom({ position: 'bottomright' }).addTo(map);
  map.attributionControl.addAttribution(SRC_ATTR);
  setTiles();
  darkQ.addEventListener?.('change', () => { setTiles(); draw(); });
  layer = L.layerGroup().addTo(map);
  // 現在地・検索した場所の印は、区間の線を描き直しても隠れないよう別の層に置く
  map.createPane('marks').style.zIndex = 450;
  map.on('moveend', () => { if (!state.here && listOpen()) renderList(); if (drive()) renderDrive(); });
  // 指で地図を動かしたら、現在地を追うのをやめる（現在地ボタンで戻す）
  map.on('dragstart', () => { state.follow = false; $('#locate').classList.add('off'); });
  map.on('zoomend', highlight);
}

const COLORS = () => {
  const cs = getComputedStyle(document.documentElement);
  return { daily: cs.getPropertyValue('--daily').trim(), closed: cs.getPropertyValue('--closed').trim(), unknown: cs.getPropertyValue('--unknown').trim() };
};
// 線の色は曜日で分ける：土日・祝日も使える／日曜・祝日は除く（一部は土曜も除く）
const dayClass = z => (z.days === 'daily' ? 'daily' : z.days === 'unknown' ? 'unknown' : 'closed');
// メーターは実線、チケットは破線。破線の間隔は線の太さに合わせる
const dash = (z, w) => (z.kind === 'ticket' ? `${w} ${Math.round(w * 1.8)}` : null);
// 運転モードでは線を太くして、遠目にも分かるようにする
const weight = () => Math.max(3, Math.min(9, map.getZoom() - 9)) + (drive() ? 3 : 0);

function draw() {
  layer.clearLayers();
  drawn.clear();
  const col = COLORS();
  for (const z of shown) {
    // 運転モードは「いま使える＝緑／時間不明＝灰」の2色だけ。破線（チケット）も使わない
    const c = drive() ? (z.days === 'unknown' ? col.unknown : col.daily) : col[dayClass(z)];
    const pls = z.lines.map(l => l.length === 1
      ? L.circleMarker(l[0], { radius: 6, color: c, weight: 2, fillOpacity: .8 })
      : L.polyline(l, { color: c, weight: weight(), opacity: .9, lineCap: 'round', dashArray: drive() ? null : dash(z, weight()) }));
    pls.forEach(p => { p.zone = z; });
    pls.forEach(p => {
      p.on('click', () => (drive() ? pickDrive(z) : openDetail(z, false)));
      if (!drive()) p.bindTooltip(esc(title(z)), { sticky: true, direction: 'top' });
      layer.addLayer(p);
    });
    drawn.set(z.id, pls);
  }
  highlight();
}

function highlight() {
  drawn.forEach((pls, id) => pls.forEach(p => {
    if (p instanceof L.CircleMarker) return;
    const on = id === (drive() ? state.pick : state.sel);
    const w = on ? weight() + 5 : weight();
    p.setStyle({ weight: w, opacity: on ? 1 : .85, dashArray: drive() ? null : dash(p.zone, w) });
    if (on) p.bringToFront();
  }));
}

/* ---------- 表示の言い回し ---------- */
const KIND = { meter: 'パーキング・メーター', ticket: 'パーキング・チケット' };
const fmtLimit = z => (z.limitMin == null ? '' : z.limitMin >= 60 && z.limitMin % 60 === 0 ? `${z.limitMin / 60}時間` : `${z.limitMin}分`);
const fmtFee = z => (z.feeYen == null ? '' : `${z.feeYen.toLocaleString()}円`);
const terms = z => [fmtLimit(z), fmtFee(z)].filter(Boolean).join('・') || KIND[z.kind];
// 住所がわかっていれば住所を、なければ条件を見出しにする
const title = z => z.addr || terms(z);
// 一覧では「日曜・休日を除く」を「日・休日は除く」と短くし、全区間共通の正月の除外は省く
const shortRule = r => (/^1月1日/.test(r) ? '' : /^12月1日/.test(r) ? '冬期休止' : r.replace(/曜/g, '').replace(/、/g, '・').replace(/を除く$/, 'は除く'));
const vehicles = z => (z.truckOnly ? '貨物車専用（積載量5トン未満）'
  : [z.car && '普通車', z.truck && '貨物用あり', z.bike && '二輪車'].filter(Boolean).join('・'));

/* ---------- 絞り込みと一覧 ---------- */
function applyFilters() {
  const now = new Date();
  if (drive()) {
    // 運転モード：条件入力は使わず、いま使える区間（と時間の分からない区間）だけ
    shown = zones.filter(z => z.days === 'unknown' || Zones.openNow(z, now, holidays.dates));
    draw();
    renderDrive();
    return;
  }
  shown = zones.filter(z => {
    if (state.pref && z.pref !== state.pref) return false;
    if (state.ward && z.ward !== state.ward) return false;
    if (state.town && z.town !== state.town) return false;
    if (state.limit) {
      const lim = +state.limit;
      if (z.limitMin == null || z.limitMin > lim) return false;
    }
    if (state.vehicle === 'truck' && !z.truck) return false;
    if (state.vehicle === 'bike' && !z.bike) return false;
    if (state.days === 'daily' && z.days !== 'daily') return false;
    if (state.days === 'closed' && (z.days === 'daily' || z.days === 'unknown')) return false;
    if (state.at === 'now' ? !Zones.openNow(z, now, holidays.dates) : state.at && !Zones.usableAt(z, +state.at)) return false;
    return true;
  });
  const n = shown.length.toLocaleString();
  ['#n', '#n2', '#n3'].forEach(id => { $(id).textContent = n; });
  const active = FILTERS.filter(k => state[k]).length;
  $('#fcount').textContent = active;
  $('#fcount').hidden = !active;
  draw();
  if (listOpen()) renderList();
}

function meters(a, b) {
  const R = 6371000, r = Math.PI / 180;
  const dLat = (b[0] - a[0]) * r, dLng = (b[1] - a[1]) * r;
  const h = Math.sin(dLat / 2) ** 2 + Math.cos(a[0] * r) * Math.cos(b[0] * r) * Math.sin(dLng / 2) ** 2;
  return 2 * R * Math.asin(Math.sqrt(h));
}
const fmtDist = m => (m < 1000 ? `${Math.round(m / 10) * 10}m` : `${(m / 1000).toFixed(1)}km`);

function listItem(z, d) {
  const rule = z.rules.map(shortRule).filter(Boolean)[0];
  const tags = [z.truckOnly ? '貨物車専用' : z.truck && '貨物枠', z.bike && '二輪', z.permitOnly && '標章車専用'].filter(Boolean);
  const head = z.addr ? `${z.ward === state.ward ? '' : z.ward}${z.addr.slice(z.ward.length)}` : terms(z);
  const meta = [z.addr && terms(z), z.hours, rule].filter(Boolean);
  return `
    <li data-id="${esc(z.id)}" class="${z.id === state.sel ? 'on' : ''}">
      <span class="k ${dayClass(z)} ${z.kind}"></span>
      <div class="body">
        <div class="nm">${esc(head)}${tags.map(t => `<span class="tag">${esc(t)}</span>`).join('')}</div>
        <div class="meta">${meta.map(m => `<span>${esc(m)}</span>`).join('')}</div>
      </div>
      <span class="dist">${fmtDist(d)}</span>
    </li>`;
}

function renderList() {
  const origin = state.here || [map.getCenter().lat, map.getCenter().lng];
  const byArea = state.sort === 'area';
  $('#sortnote').textContent = byArea ? '' : state.here ? '現在地から' : '地図の中心から';
  let rows = shown.map(z => ({ z, d: meters(origin, z.center) }));
  if (!byArea) {
    rows = rows.sort((a, b) => a.d - b.d).slice(0, LIST_MAX);
    $('#list').innerHTML = rows.map(({ z, d }) => listItem(z, d)).join('') || '<li class="none">条件に合う区間はありません</li>';
    return;
  }
  // エリアごと：区市町村（区を選んでいれば町名）を区間の多い順に並べ、その中は近い順
  const key = z => (state.ward ? z.town : z.ward) || '住所未取得';
  const n = {};
  rows.forEach(r => { n[key(r.z)] = (n[key(r.z)] || 0) + 1; });
  rows.sort((a, b) => n[key(b.z)] - n[key(a.z)] || key(a.z).localeCompare(key(b.z), 'ja') || a.d - b.d);
  const groups = new Map();
  rows.forEach(r => { const k = key(r.z); if (!groups.has(k)) groups.set(k, []); groups.get(k).push(r); });
  $('#list').innerHTML = [...groups].map(([k, rs]) => `
    <li class="group" data-group="${esc(k)}"><span>${esc(state.ward ? `${state.ward} ${k}` : k)}</span><b>${rs.length}</b></li>
    ${rs.map(({ z, d }) => listItem(z, d)).join('')}`).join('') || '<li class="none">条件に合う区間はありません</li>';
}

/* ---------- 運転モードのカード ---------- */
const DIRS = ['北', '北東', '東', '南東', '南', '南西', '西', '北西'];
function bearingDeg(a, b) {
  const k = Math.cos(a[0] * Math.PI / 180);
  return (Math.atan2((b[1] - a[1]) * k, b[0] - a[0]) * 180 / Math.PI + 360) % 360;
}
// 線のうち、起点に最も近い点（区間の中ほどではなく、いちばん近いところまでの距離を出す）
function nearestPoint(z, o) {
  let best = z.center, bd = Infinity;
  z.lines.flat().forEach(p => { const d = meters(o, p); if (d < bd) { bd = d; best = p; } });
  return [best, bd];
}
const until = z => (z.days === 'unknown' ? '時間は現地で確認' : z.span ? `${Math.floor(z.span[1] / 60)}:${String(z.span[1] % 60).padStart(2, '0')}まで` : '');
const routeUrl = p => (IOS ? `https://maps.apple.com/?daddr=${p[0]},${p[1]}&dirflg=d`
  : `https://www.google.com/maps/dir/?api=1&destination=${p[0]},${p[1]}&travelmode=driving`);

// 運転モードでは下のカードが地図を隠すので、カードより上の見えている範囲の中央に置く
function centerOn(ll, zoom, animate = true) {
  const card = drive() ? $('#drivecard').offsetHeight + 22 : 0;
  const pt = map.project(ll, zoom).add([0, card / 2]);
  map.setView(map.unproject(pt, zoom), zoom, { animate });
}

function driveOrigin() {
  if (state.place) return { p: state.place, label: '検索した場所から' };
  if (state.here) return { p: state.here, label: '' };
  const c = map.getCenter();
  return { p: [c.lat, c.lng], label: '地図の中心から' };
}

function renderDrive() {
  if (!drive() || !zones.length) return;
  const o = driveOrigin();
  // 時間の分からない区間は、使える区間が近くにないときだけ候補にする
  const rows = shown.map(z => { const [pt, d] = nearestPoint(z, o.p); return { z, pt, d }; })
    .sort((a, b) => (a.z.days === 'unknown') - (b.z.days === 'unknown') || a.d - b.d);
  const known = rows.filter(r => r.z.days !== 'unknown');
  const top = (known.length && known[0].d < 3000 ? known : rows.sort((a, b) => a.d - b.d)).slice(0, 3);
  if (!top.some(r => r.z.id === state.pick)) state.pick = top[0]?.z.id || null;
  $('#drivenote').textContent = !top.length ? 'いま使える区間はありません'
    : top[0].d > 3000 ? `近くにいま使える区間はありません（最寄り ${fmtDist(top[0].d)}）` : o.label;
  $('#drivelist').innerHTML = top.map(({ z, d, pt }) => {
    const deg = bearingDeg(o.p, pt);
    return `
    <li data-id="${esc(z.id)}" class="${z.id === state.pick ? 'on' : ''} ${z.days === 'unknown' ? 'unk' : ''}">
      <svg class="arrow" viewBox="0 0 24 24" style="transform:rotate(${Math.round(deg)}deg)" aria-hidden="true"><path d="M12 3l6 16-6-4-6 4z"/></svg>
      <div class="info"><b>${DIRS[Math.round(deg / 45) % 8]}へ ${fmtDist(d)}</b><span>${esc([terms(z), until(z)].filter(Boolean).join('・'))}</span></div>
    </li>`;
  }).join('');
  const sel = top.find(r => r.z.id === state.pick);
  $('#drivego').hidden = !sel;
  if (sel) {
    $('#drivego').href = routeUrl(sel.pt);
    $('#drivego').textContent = `${IOS ? 'Apple' : 'Google'}マップで経路`;
  }
  highlight();
}

function pickDrive(z) {
  state.pick = z.id;
  renderDrive();
}

/* 運転モード ⇄ 詳しく探す */
function setMode(isDrive) {
  document.body.classList.toggle('drive', isDrive);
  $('#menuModeText').textContent = isDrive ? '詳しく探す' : '運転モードに戻る';
  toggleMenu(false);
  closeSearch();
  if (isDrive) { closeDetail(); closeList(); toggleFilters(false); map.removeControl(map.zoomCtl); }
  else map.zoomCtl.addTo(map);
  try { localStorage.setItem('pmm-mode', isDrive ? 'drive' : 'detail'); } catch (e) {}
  setTimeout(() => map.invalidateSize(), 50);
  applyFilters();
}

function openSearch() {
  document.body.classList.add('searching');
  $('#q').focus();
}
function closeSearch() {
  document.body.classList.remove('searching');
}

/* 現在地を追いかける */
function startWatch() {
  if (!navigator.geolocation || startWatch.id != null) return;
  startWatch.id = navigator.geolocation.watchPosition(p => {
    const first = !state.here;
    state.here = [p.coords.latitude, p.coords.longitude];
    if (hereMark) hereMark.setLatLng(state.here);
    else hereMark = L.circleMarker(state.here, { pane: 'marks', radius: 9, color: '#fff', weight: 3, fillColor: '#F28C28', fillOpacity: 1 }).addTo(map);
    // 地図が追いかけるのは運転モードのとき（詳しく探すでは最初の1回だけ寄せる）
    if (first) map.stop(); // 東京全体への移動の途中でも止めて現在地へ
    if (drive()) renderDrive(); // 先にカードを作って高さを決める
    if (state.follow && !state.place && (drive() || first)) centerOn(state.here, first ? 17 : Math.max(map.getZoom(), 16), !first);
    if (listOpen()) renderList();
  }, () => { startWatch.id = null; if (drive()) renderDrive(); }, { enableHighAccuracy: true, maximumAge: 5000, timeout: 20000 });
}

/* ---------- 住所の逆引き（詳細を開いたときだけ） ---------- */
async function address(z) {
  if (z.addr) return z.addr;
  if (addrCache.has(z.id)) return addrCache.get(z.id);
  const [lat, lng] = z.center;
  const res = await fetch(`${GSI_REVERSE}?lat=${lat}&lon=${lng}`);
  const r = (await res.json()).results;
  const text = r ? `${MUNI[+r.muniCd] || ''}${r.lv01Nm && r.lv01Nm !== '－' ? r.lv01Nm : ''}` : '';
  addrCache.set(z.id, text);
  return text;
}

/* ---------- 詳細 ---------- */
function openDetail(z, fly = true) {
  state.sel = z.id;
  highlight();
  document.querySelectorAll('#list li').forEach(li => li.classList.toggle('on', li.dataset.id === z.id));
  if (narrow()) closeList();
  toggleFilters(false);
  const row = (k, v, id) => (v ? `<dt>${k}</dt><dd${id ? ` id="${id}"` : ''}>${esc(v)}</dd>` : '');
  const [lat, lng] = z.center;
  const today = new Date();
  const open = Zones.openNow(z, today, holidays.dates);
  const holiday = holidays.dates[Zones.ymd(today)];
  $('#detail').innerHTML = `
    <button class="close" aria-label="閉じる">×</button>
    <div class="badges"><span class="badge ${dayClass(z)}">${z.days === 'daily' ? '土日・祝日も使える' : z.days === 'weekday' ? '土・日・祝日は除く' : z.days === 'unknown' ? '時間・曜日は現地で確認' : '日曜・祝日は除く'}</span><span class="badge kind">${KIND[z.kind]}</span></div>
    <h2>${esc(terms(z))}</h2>
    <dl>
      ${row('場所', z.addr || '住所を調べています…', 'addr')}
      ${row('路線', z.route)}
      ${row('区間', z.section)}
      ${row('枠数', z.spaces != null ? `${z.spaces}台` + (z.truckSpaces ? `（うち貨物車 ${z.truckSpaces}台）` : '') : '')}
      ${row('制限時間', fmtLimit(z))}
      ${row('料金', fmtFee(z) && `${fmtFee(z)}（${fmtLimit(z) || '1回'}）`)}
      ${row('利用時間', z.hours || (z.days === 'unknown' ? '県警の公開情報になし（現地の標識で確認）' : ''))}
      ${row('除く日', z.rules.join('、'))}
      ${z.days === 'unknown' ? '' : row('いま', (open ? '利用時間内' : '利用時間外') + (holiday ? `（今日は${holiday}）` : holidayKnown() ? '' : '（祝日は判定していません）'))}
      ${row('車種', vehicles(z))}
      ${z.permitOnly ? row('注意', '標章車（障害者等用）専用の枠があります') : ''}
      ${z.pref === '東京都' ? row('区間番号', z.id) : ''}
      ${row('出典', z.source)}
    </dl>
    <div class="acts">
      <a class="btn primary" href="https://www.google.com/maps/dir/?api=1&destination=${lat},${lng}&travelmode=driving" target="_blank" rel="noopener">Googleマップで経路</a>
      <a class="btn primary" href="https://maps.apple.com/?daddr=${lat},${lng}&dirflg=d" target="_blank" rel="noopener">Appleマップで経路</a>
      <a class="maplink" href="https://www.google.com/maps/search/?api=1&query=${lat},${lng}" target="_blank" rel="noopener">Googleマップで場所だけ開く</a>
    </div>
    <p class="warn">現地の標識・メーターの表示が優先されます。利用時間外は駐車できないことがあります。工事や行事で使えない場合もあります。</p>`;
  $('#detail').classList.add('open');
  $('#detail .close').onclick = closeDetail;
  if (fly) {
    // 詳細が重なる分をよけて、選んだ区間が見える位置に寄せる（スマホは下のシート、広い画面は右のカード）
    const b = L.latLngBounds(z.lines.flat());
    const sheet = $('#detail').offsetHeight;
    map.flyToBounds(b, narrow()
      ? { maxZoom: 18, paddingTopLeft: [40, 150], paddingBottomRight: [40, sheet + 30], duration: .6 }
      : { maxZoom: 18, paddingTopLeft: [listOpen() ? 440 : 60, 60], paddingBottomRight: [420, 60], duration: .6 });
  }
  address(z)
    .then(a => { if (state.sel === z.id && $('#addr')) $('#addr').textContent = a || '（住所を特定できませんでした）'; })
    .catch(() => { if (state.sel === z.id && $('#addr')) $('#addr').textContent = '（住所を取得できませんでした）'; });
}

function closeDetail() {
  state.sel = null;
  highlight();
  $('#detail').classList.remove('open');
  document.querySelectorAll('#list li.on').forEach(li => li.classList.remove('on'));
}

/* ---------- 地名で移動 ---------- */
async function goPlace(q) {
  q = q.trim();
  if (!q) return;
  const note = $('#qnote');
  note.textContent = '探しています…';
  note.hidden = false;
  try {
    const res = await fetch(GSI_SEARCH + encodeURIComponent(q));
    const hits = await res.json();
    // 都内を優先（同名の地名が全国にあるため）
    const hit = hits.find(h => /東京都|大阪府/.test(h.properties.title)) || hits[0];
    if (!hit) { note.textContent = `「${q}」は見つかりませんでした`; return; }
    const [lng, lat] = hit.geometry.coordinates;
    state.place = [lat, lng];
    state.follow = false;
    $('#locate').classList.add('off');
    closeSearch();
    if (placeMark) map.removeLayer(placeMark);
    placeMark = L.circleMarker([lat, lng], { pane: 'marks', radius: 7, color: '#fff', weight: 3, fillColor: '#D1452E', fillOpacity: 1 })
      .bindTooltip(esc(hit.properties.title)).addTo(map);
    if (drive()) renderDrive();
    centerOn([lat, lng], 16, false);
    if (listOpen()) renderList();
    note.textContent = `${hit.properties.title} の近く`;
  } catch (e) {
    note.textContent = '地名検索につながりませんでした';
  }
}

/* ---------- 祝日 ---------- */
const holidayKnown = (d = new Date()) => holidays.years.includes(d.getFullYear());
function holidayNote() {
  const h = holidays.dates[Zones.ymd(new Date())];
  $('#fnote').textContent = h ? `今日は${h}です。「いま使える」は祝日を除く区間を外しています。`
    : holidayKnown() ? '「いま使える」は曜日・祝日・正月まで見ます。'
    : '「いま使える」は曜日と正月まで見ます。祝日は判定しません。';
}

/* ---------- 時間帯の選択肢 ---------- */
function fillHours() {
  // データにある利用時間の範囲（最も早い開始〜最も遅い終了）で1時間ごとに出す
  const spans = zones.map(z => z.span).filter(Boolean);
  if (!spans.length) return;
  const from = Math.floor(Math.min(...spans.map(s => s[0])) / 60);
  const to = Math.ceil(Math.max(...spans.map(s => s[1])) / 60);
  let opts = '<option value="">すべて</option><option value="now">いま使える</option>';
  for (let h = from; h < to; h++) opts += `<option value="${h * 60}">${h}:00 に使える</option>`;
  $('#at').innerHTML = opts;
}

/* ---------- エリアの選択肢 ---------- */
// 画面での呼び名：東京都→東京、大阪府→大阪、京都府→京都、北海道→札幌（区間は札幌だけのため）
const prefName = p => ({ 北海道: '札幌' }[p] || p.replace(/[都府県]$/, ''));
function count(list, k) {
  const n = {};
  list.forEach(z => { if (z[k]) n[z[k]] = (n[z[k]] || 0) + 1; });
  return n;
}

function fillPrefs() {
  const n = count(zones, 'pref');
  // メニューの「◯◯を表示」も、データのある都道府県だけ出す
  const pin = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 21s-7-6.2-7-11.5A7 7 0 0 1 19 9.5C19 14.8 12 21 12 21z"/><circle cx="12" cy="9.5" r="2.5"/></svg>';
  $('#menuPrefs').innerHTML = PREFS.filter(p => n[p]).map(p => `<button data-pref="${p}">${pin}${prefName(p)}を表示</button>`).join('');
  $('#pref').innerHTML = '<option value="">すべて</option>' +
    PREFS.filter(p => n[p]).map(p => `<option value="${p}">${prefName(p)}（${n[p]}）</option>`).join('');
  $('#ward').closest('label').hidden = $('#town').closest('label').hidden = !zones.some(z => z.ward);
  fillWards();
}

// 区・市は、選んだ都府県のものだけを区間の多い順に出す（東京と大阪は混ぜない）
function fillWards() {
  const n = count(zones.filter(z => z.pref === state.pref), 'ward');
  const wards = Object.keys(n).sort((a, b) => n[b] - n[a]);
  $('#ward').innerHTML = `<option value="">${state.pref ? 'すべて' : '先に都府県を選んでください'}</option>` +
    wards.map(w => `<option value="${esc(w)}">${esc(w)}（${n[w]}）</option>`).join('');
  $('#ward').disabled = !state.pref;
  fillTowns();
}

function fillTowns() {
  const n = count(zones.filter(z => z.ward === state.ward), 'town');
  const towns = Object.keys(n).sort((a, b) => n[b] - n[a] || a.localeCompare(b, 'ja'));
  $('#town').innerHTML = `<option value="">${state.ward ? 'すべて' : '先に区を選んでください'}</option>` +
    towns.map(t => `<option value="${esc(t)}">${esc(t)}（${n[t]}）</option>`).join('');
  $('#town').disabled = !state.ward;
}

/* ---------- 画面の組み立て ---------- */
function fitAll(pref, animate = true) {
  const pts = shown.filter(z => !pref || z.pref === pref).flatMap(z => z.lines.flat());
  // 左上の検索・条件入力の下に隠れないよう、上側を広めにあける
  if (pts.length) map.fitBounds(L.latLngBounds(pts), { paddingTopLeft: [30, 130], paddingBottomRight: [30, 60], animate });
}

const narrow = () => window.innerWidth <= 760;
const listOpen = () => !$('#listpanel').hidden;

function openList() {
  toggleMenu(false);
  toggleFilters(false);
  if (narrow()) closeDetail();
  $('#listpanel').hidden = false;
  document.body.classList.add('listing');
  renderList();
}
function closeList() {
  $('#listpanel').hidden = true;
  document.body.classList.remove('listing');
}

function toggleMenu(open = $('#menu').hidden) {
  $('#menu').hidden = !open;
  $('#menuBtn').setAttribute('aria-expanded', open);
}

function toggleFilters(open = $('#filters').hidden) {
  $('#filters').hidden = !open;
  $('#ftoggle').setAttribute('aria-expanded', open);
  if (open) { toggleMenu(false); if (narrow()) { closeDetail(); closeList(); } }
}

function resetFilters() {
  FILTERS.forEach(k => { state[k] = ''; $('#' + k).value = ''; });
  fillWards();
  applyFilters();
  fitAll();
}

function bind() {
  $('#qform').addEventListener('submit', e => { e.preventDefault(); $('#q').blur(); goPlace($('#q').value); });
  $('#menuBtn').addEventListener('click', e => { e.stopPropagation(); toggleMenu(); });
  document.addEventListener('click', e => { if (!$('#menu').hidden && !e.target.closest('#menu')) toggleMenu(false); });
  $('#menuList').addEventListener('click', () => { if (drive()) setMode(false); openList(); });
  $('#menuMode').addEventListener('click', () => setMode(!drive()));
  $('#searchBtn').addEventListener('click', () => (document.body.classList.contains('searching') ? closeSearch() : openSearch()));
  $('#qclose').addEventListener('click', closeSearch);
  $('#drivelist').addEventListener('click', e => {
    const li = e.target.closest('li[data-id]');
    if (li) pickDrive(zones.find(z => z.id === li.dataset.id));
  });
  $('#menuFit').addEventListener('click', () => { toggleMenu(false); state.here = null; fitAll(); });
  $('#menuPrefs').addEventListener('click', e => {
    const b = e.target.closest('[data-pref]');
    if (b) { toggleMenu(false); state.here = null; fitAll(b.dataset.pref); }
  });
  $('#listClose').addEventListener('click', closeList);
  $('#ftoggle').addEventListener('click', () => toggleFilters());
  $('#fdone').addEventListener('click', () => toggleFilters(false));
  $('#freset').addEventListener('click', resetFilters);
  $('#pref').addEventListener('change', e => {
    state.pref = e.target.value;
    state.ward = state.town = '';
    fillWards();
    applyFilters();
    fitAll(state.pref);
  });
  $('#ward').addEventListener('change', e => {
    state.ward = e.target.value;
    state.town = '';
    fillTowns();
    applyFilters();
    fitAll();
  });
  $('#town').addEventListener('change', e => { state.town = e.target.value; applyFilters(); fitAll(); });
  $('#sort').addEventListener('change', e => { state.sort = e.target.value; renderList(); });
  $('#limit').addEventListener('change', e => { state.limit = e.target.value; applyFilters(); });
  $('#vehicle').addEventListener('change', e => { state.vehicle = e.target.value; applyFilters(); });
  $('#days').addEventListener('change', e => { state.days = e.target.value; applyFilters(); });
  $('#at').addEventListener('change', e => { state.at = e.target.value; applyFilters(); });
  $('#list').addEventListener('click', e => {
    const li = e.target.closest('li[data-id]');
    if (li) openDetail(zones.find(z => z.id === li.dataset.id));
  });
  // 現在地ボタン：検索した場所をやめて、また現在地を追う（現在地の印はオレンジ。線より上の層に置く）
  $('#locate').addEventListener('click', () => {
    if (!navigator.geolocation) return alert('この端末では現在地を使えません');
    state.follow = true;
    state.place = null;
    if (placeMark) { map.removeLayer(placeMark); placeMark = null; }
    $('#locate').classList.remove('off');
    $('#qnote').hidden = true;
    if (state.here) centerOn(state.here, Math.max(map.getZoom(), 16));
    startWatch();
    if (drive()) renderDrive();
  });
  document.addEventListener('keydown', e => {
    if (e.key !== 'Escape') return;
    if (document.body.classList.contains('searching')) closeSearch();
    else if (!$('#menu').hidden) toggleMenu(false);
    else if (!$('#filters').hidden) toggleFilters(false);
    else if ($('#detail').classList.contains('open')) closeDetail();
    else closeList();
  });
  // 「いま使える」は時間が進むと変わるので、1分ごとに見直す
  setInterval(() => { holidayNote(); if (state.at === 'now' || drive()) applyFilters(); }, 60000);
}

async function boot() {
  initMap();
  bind();
  try {
    const res = await fetch('data/zones.geojson', { cache: 'no-cache' });
    zones = Zones.normalize(await res.json());
  } catch (e) {
    $('#empty').hidden = false;
    return;
  }
  try {
    holidays = await (await fetch('data/holidays.json', { cache: 'no-cache' })).json();
  } catch (e) { /* 祝日一覧がなくても動く（祝日を判定しないだけ） */ }
  holidayNote();
  fillPrefs();
  fillHours();
  // 前回「詳しく探す」で閉じた人はそのまま。初めての人は運転モードから
  let mode = 'drive';
  try { mode = localStorage.getItem('pmm-mode') || 'drive'; } catch (e) {}
  if (mode !== 'drive') setMode(false);
  else { map.removeControl(map.zoomCtl); applyFilters(); }
  // 現在地が取れればそこへ。取れないうちは東京を見せる
  startWatch();
  // 動きをつけると、あとから届いた現在地への移動をズームの終わりで上書きしてしまうので、一度に切り替える
  if (!state.here) fitAll('東京都', false);
}

boot();
