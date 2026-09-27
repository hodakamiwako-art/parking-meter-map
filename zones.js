/* data/zones.geojson（build/build.py が作る）を、アプリで扱う形にそろえる。
   属性は警視庁オープンデータの項目名そのまま：
   識別id・利用時間・制限時間・手数料・制限事項1・制限事項2・種別・普通車・貨物用有り・二輪車・標章車専用有り
   に、build.py が逆引きで足した 区市町村・町名・町丁目 が加わる。 */
(function () {
  const z2h = s => String(s ?? '').replace(/[０-９]/g, c => String.fromCharCode(c.charCodeAt(0) - 0xFEE0));
  const num = v => (v === '' || v == null || !Number.isFinite(+v) ? null : +v);

  // 「09:00-19:00」→ [540, 1140]（0時からの分）
  function span(s) {
    const m = z2h(s).match(/(\d{1,2}):(\d{2})\s*[-~〜－]\s*(\d{1,2}):(\d{2})/);
    return m ? [+m[1] * 60 + +m[2], +m[3] * 60 + +m[4]] : null;
  }
  const hhmm = t => `${Math.floor(t / 60)}:${String(t % 60).padStart(2, '0')}`;

  // GeoJSON の [lng, lat] を Leaflet の [lat, lng] の線の配列にする
  function lines(geom) {
    if (!geom) return [];
    const flip = c => [c[1], c[0]];
    if (geom.type === 'LineString') return [geom.coordinates.map(flip)];
    if (geom.type === 'MultiLineString') return geom.coordinates.map(l => l.map(flip));
    if (geom.type === 'Point') return [[flip(geom.coordinates)]];
    return [];
  }

  // 線のまん中あたりの点（端点だと隣の区間と重なりやすい）
  function midpoint(ls) {
    const longest = ls.reduce((a, b) => (b.length > a.length ? b : a), ls[0]);
    return longest[Math.floor(longest.length / 2)];
  }

  function normalize(geojson) {
    return geojson.features.map(f => {
      const p = f.properties || {};
      const geo = lines(f.geometry).filter(l => l.length);
      if (!geo.length) return null;
      const sp = span(p['利用時間']);
      return {
        id: String(p['識別id'] ?? f.id),
        kind: /チケット/.test(p['種別']) ? 'ticket' : 'meter',
        span: sp,
        hours: sp ? `${hhmm(sp[0])}–${hhmm(sp[1])}` : z2h(p['利用時間']),
        limitMin: num(p['制限時間']),
        feeYen: num(p['手数料']),
        rules: [p['制限事項1'], p['制限事項2']].filter(Boolean).map(z2h),
        car: !!p['普通車'],
        truck: !!p['貨物用有り'],
        bike: !!p['二輪車'],
        permitOnly: !!p['標章車専用有り'],
        ward: p['区市町村'] || '',
        town: p['町名'] || '',
        addr: (p['区市町村'] || '') + (p['町丁目'] || ''),
        lines: geo,
        center: midpoint(geo),
        raw: p,
      };
    }).filter(Boolean);
  }

  /* いま利用時間内か。「日曜・休日を除く」「土・日曜、休日を除く」「1月1日〜3日を除く」を見る。
     祝日の暦は持っていないので、祝日は判定しない（画面にもそう書く）。 */
  function openNow(z, now = new Date()) {
    if (!z.span) return false;
    const rules = z.rules.join(' ');
    const dow = now.getDay();
    if (dow === 0 && /日曜/.test(rules)) return false;
    if (dow === 6 && /土/.test(rules)) return false;
    if (now.getMonth() === 0 && now.getDate() <= 3 && /1月1日/.test(rules)) return false;
    const t = now.getHours() * 60 + now.getMinutes();
    return t >= z.span[0] && t < z.span[1];
  }

  window.Zones = { normalize, openNow };
})();
