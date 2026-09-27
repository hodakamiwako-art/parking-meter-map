/* 警視庁「時間制限駐車区間」の GeoJSON を、アプリで扱う形にそろえる。
   オープンデータの属性名は版によって変わりうるので、決め打ちせず名前の型で拾う。
   拾えなかった属性も raw に残し、詳細画面にそのまま並べる。 */
(function () {
  const PICK = {
    name:    /区間名|路線名|名称|通り名|^name$|title/i,
    addr:    /所在地|住所|設置場所|場所|address|location/i,
    ward:    /区市町村|市区町村|自治体|区名|市町村|city|ward|municipality/i,
    kind:    /種別|種類|区分|方式|type|kind|category/i,
    limit:   /制限時間|駐車時間|時間制限|駐車可能時間|limit|duration/i,
    fee:     /料金|手数料|金額|fee|price|charge/i,
    hours:   /時間帯|規制時間|適用時間|有効時間|運用時間|hours|time/i,
    days:    /曜日|適用日|除外日|days/i,
    vehicle: /車種|対象車両|vehicle/i,
    count:   /台数|基数|枡数|区画数|spaces|count/i,
  };

  function pick(props, re, taken) {
    for (const k of Object.keys(props)) {
      if (taken.has(k)) continue;
      const v = props[k];
      if (v == null || v === '') continue;
      if (re.test(k)) { taken.add(k); return String(v).trim(); }
    }
    return '';
  }

  // 「60分」「1時間」「1時間30分」「60」→ 分
  function minutes(s) {
    if (!s) return null;
    const t = s.replace(/[０-９]/g, c => String.fromCharCode(c.charCodeAt(0) - 0xFEE0));
    const h = t.match(/(\d+(?:\.\d+)?)\s*時間/);
    const m = t.match(/(\d+)\s*分/);
    if (h || m) return Math.round((h ? parseFloat(h[1]) * 60 : 0) + (m ? +m[1] : 0));
    const n = t.match(/^\s*(\d+)\s*$/);
    return n ? +n[1] : null;
  }

  function yen(s) {
    if (!s) return null;
    const t = s.replace(/[０-９]/g, c => String.fromCharCode(c.charCodeAt(0) - 0xFEE0)).replace(/,/g, '');
    const n = t.match(/(\d+)/);
    return n ? +n[1] : null;
  }

  function kindOf(kindText, props) {
    const hay = kindText + ' ' + Object.values(props).join(' ');
    if (/チケット|ticket/i.test(kindText) || (!kindText && /チケット|ticket/i.test(hay))) return 'ticket';
    return 'meter';
  }

  function wardFrom(addr) {
    const m = addr.replace(/^東京都/, '').match(/^(.+?[区市町村])/);
    return m ? m[1] : '';
  }

  // GeoJSON の [lng, lat] を Leaflet の [lat, lng] の線の配列にする
  function lines(geom) {
    if (!geom) return [];
    const flip = c => [c[1], c[0]];
    switch (geom.type) {
      case 'Point': return [[flip(geom.coordinates)]];
      case 'MultiPoint': return geom.coordinates.map(c => [flip(c)]);
      case 'LineString': return [geom.coordinates.map(flip)];
      case 'MultiLineString': return geom.coordinates.map(l => l.map(flip));
      case 'Polygon': return [geom.coordinates[0].map(flip)];
      case 'MultiPolygon': return geom.coordinates.map(p => p[0].map(flip));
      case 'GeometryCollection': return geom.geometries.flatMap(lines);
      default: return [];
    }
  }

  // 線の長さの中ほどの点を代表点にする（端点だと隣の区間と重なりやすい）
  function midpoint(ls) {
    const pts = ls.flat();
    if (pts.length === 1) return pts[0];
    const longest = ls.reduce((a, b) => (b.length > a.length ? b : a), ls[0]);
    return longest[Math.floor(longest.length / 2)] || pts[0];
  }

  function normalize(geojson) {
    const feats = geojson.type === 'FeatureCollection' ? geojson.features : [geojson];
    const out = [];
    feats.forEach((f, i) => {
      const geo = lines(f.geometry).filter(l => l.length);
      if (!geo.length) return;
      const props = f.properties || {};
      const taken = new Set();
      const z = {};
      for (const key of Object.keys(PICK)) z[key] = pick(props, PICK[key], taken);
      z.id = String(f.id ?? props.id ?? props.ID ?? i);
      z.kind = kindOf(z.kind, props);
      z.ward = z.ward || wardFrom(z.addr);
      z.limitMin = minutes(z.limit);
      z.feeYen = yen(z.fee);
      z.lines = geo;
      z.center = midpoint(geo);
      z.raw = props;
      z.hay = [z.name, z.addr, z.ward, ...Object.values(props)].join(' ').toLowerCase();
      out.push(z);
    });
    return out;
  }

  window.Zones = { normalize, minutes, yen };
})();
