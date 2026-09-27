"""目印（建物・交差点）と「どちら側か」で場所が書かれた県警の一覧から、区間の線を作る。

    python3 build/landmarks.py sapporo SAPPORO.osm.pbf   # 北海道警（札幌）→ build/source/sapporo/geometry.json
    python3 build/landmarks.py kyoto KYOTO.osm.pbf       # 京都府警         → build/source/kyoto/geometry.json

北海道警・京都府警は区間の座標も交差点名も出しておらず、「南1条西13丁目（札幌南一条病院西側）」
「紫明通（烏丸通西入る南側）」のように目印で書いている。そこで
  1. 目印の位置と大きさ（OSM の名前つき建物の輪郭、なければ国土地理院の住所検索、それでもだめなら手で書いた範囲）
  2. 目印の指定の辺（西側なら西の辺）に平行で、その外側にある道路（路線名が分かればその道路）
  3. 辺の中点に近い点を中心に（または交差点から指定の向きへ）道路に沿って「枠数×6m」、ただし辺の長さ＋20mまで
で線にする。府警・道警の地図がないので、長さと端の位置は目安（線の中ほどは合っているが端は数十mずれうる）。

各地域の一覧（REGIONS）は県警のページを写したもので、ページが変わったら手で直す。
OSM の PBF の作り方は build/osaka.py の冒頭と同じ（-b に地域の範囲を入れる）。
"""
import json, math, re, sys, time, urllib.parse, urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from osaka import Roads, dist, norm_road, GSI_SEARCH  # 道路網と距離は大阪と同じものを使う

ROOT = Path(__file__).resolve().parent.parent
SPACE_M = 6  # 縦列駐車1台ぶんの長さの目安

# side: 目印から見て道路がある向き（west/east/north/south）。along: 交差点などから道路に沿って伸ばす向き
REGIONS = {
    'sapporo': {
        'pref': '北海道',
        'source': '北海道警察 パーキング・チケット（令和7年12月）',
        'page': 'https://www.police.pref.hokkaido.lg.jp/info/koutuu/p-ticket/p-ticket.html',
        'common': {'種別': 'パーキング・チケット', '制限時間': 60, '手数料': 300, '利用時間': '08:30-19:00',
                   '制限事項1': '', '制限事項2': ''},
        'items': [
            # 一般用（4月1日〜11月30日。冬期休止）
            {'id': 'sapporo-1', 'addr': '札幌市中央区南1条西13丁目', 'mark': '札幌南一条病院', 'side': 'west', 'spaces': 5, 'season': '4-11'},
            {'id': 'sapporo-2', 'addr': '札幌市中央区北2条西2丁目', 'mark': 'STV北2条ビル', 'side': 'east', 'spaces': 6, 'season': '4-11'},
            {'id': 'sapporo-3', 'addr': '札幌市中央区北1条西2丁目', 'mark': 'オーク札幌ビル', 'side': 'east', 'spaces': 4, 'season': '4-11'},
            {'id': 'sapporo-4', 'addr': '札幌市中央区北3条西7丁目', 'mark': '北海道庁別館', 'side': 'north', 'spaces': 7, 'season': '4-11'},
            {'id': 'sapporo-5', 'addr': '札幌市中央区北3条西7丁目', 'mark': '北海道水産ビル', 'side': 'south', 'spaces': 6, 'season': '4-11'},
            {'id': 'sapporo-6', 'addr': '札幌市中央区南1条西9丁目', 'mark': '三田商店', 'side': 'west', 'spaces': 8, 'season': '4-11'},
            {'id': 'sapporo-7', 'addr': '札幌市中央区南2条西14丁目', 'mark': '中村記念病院', 'side': 'east', 'spaces': 5, 'season': '4-11'},
            {'id': 'sapporo-8', 'addr': '札幌市中央区北1条西2丁目', 'mark': '札幌市時計台', 'side': 'east', 'spaces': 8, 'season': '4-11'},
            # 貨物車（積載量5トン未満）専用。通年
            {'id': 'sapporo-9', 'addr': '札幌市中央区南1条西2丁目', 'mark': '丸井今井', 'side': 'north', 'spaces': 6, 'truck_only': True},
            {'id': 'sapporo-10', 'addr': '札幌市中央区南1条西3丁目', 'mark': '札幌三越', 'side': 'north', 'spaces': 8, 'truck_only': True},
        ],
    },
    'kyoto': {
        'pref': '京都府',
        'source': '京都府警察 パーキング・メーター、パーキング・チケット（2022年1月24日更新）',
        'page': 'https://www.pref.kyoto.jp/fukei/site/chutai_c/tiket_meter/',
        'common': {'制限時間': 60, '手数料': 300, '制限事項1': '', '制限事項2': ''},
        'items': [
            {'id': 'kyoto-1', 'label': '紫明通（烏丸通西入る南側）', 'road': '紫明通', 'from_cross': '烏丸通', 'along': 'west',
             'spaces': 7, 'hours': '08:00-20:00', '種別': 'パーキング・メーター'},
            {'id': 'kyoto-2', 'label': '踏水会前（熊野道西入一筋目）', 'mark': '踏水会', 'spaces': 13, 'hours': '08:00-20:00', '種別': 'パーキング・チケット'},
            {'id': 'kyoto-3', 'label': '釜座通（京都第二赤十字病院前）', 'road': '釜座通', 'mark': '京都第二赤十字病院', 'side': 'west',
             'spaces': 80, 'hours': '08:00-22:00', '種別': 'パーキング・チケット'},
            {'id': 'kyoto-4', 'label': '薬大前', 'mark': '京都薬科大学', 'side': 'north', 'spaces': 6, 'hours': '08:00-20:00', '種別': 'パーキング・チケット'},
            {'id': 'kyoto-5', 'label': '大手筋通（竹田街道東入る）', 'road': '大手筋通', 'from_cross': '竹田街道', 'along': 'east',
             'spaces': 11, 'hours': '08:00-20:00', '種別': 'パーキング・チケット'},
        ],
    },
}

# 自動で決まらない目印の範囲（(西, 南, 東, 北)）。id → 範囲
MANUAL_MARK = {
    # 「北海道水産ビル」は OSM では「水産ビル」（北3条西7丁目の南寄りの建物）
    'sapporo-5': (141.34587, 43.06380, 141.34627, 43.06426),
}

BEARING = {'north': 0, 'east': 90, 'south': 180, 'west': 270}


def bearing(a, b):
    kx = math.cos(math.radians((a[1] + b[1]) / 2))
    return math.degrees(math.atan2((b[0] - a[0]) * kx, b[1] - a[1])) % 360


def angle_diff(x, y):
    return abs((x - y + 180) % 360 - 180)


def find_mark(names_index, mark, addr=None):
    """目印の位置と大きさ：OSM の名前つき地物（部分一致。面なら外接矩形）→ 住所検索。
    戻り値は (西, 南, 東, 北) の範囲。点なら4つとも同じ点"""
    if mark:
        # 名前が完全に一致するものを優先（「タイムズ 札幌南一条病院」のような駐車場を拾わない）
        hits = names_index.get(mark) or [b for nm, bs in names_index.items() if mark in nm for b in bs]
        if hits:
            # 同じ名前が複数あれば、いちばん大きいもの（建物の面）を目印にする
            return max(hits, key=lambda b: (b[2] - b[0]) * (b[3] - b[1]))
    if addr:
        with urllib.request.urlopen(GSI_SEARCH + urllib.parse.quote(addr), timeout=20) as r:
            h = json.load(r)
        time.sleep(0.3)
        if h:
            x, y = h[0]['geometry']['coordinates']
            return (x, y, x, y)
    return None


def project(p, a, b):
    """点 p を線分 ab に下ろした足と、その距離（m）"""
    kx = math.cos(math.radians(p[1]))
    ax, ay, bx, by, px, py = a[0] * kx, a[1], b[0] * kx, b[1], p[0] * kx, p[1]
    dx, dy = bx - ax, by - ay
    t = 0 if dx == dy == 0 else max(0, min(1, ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)))
    q = (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)
    return q, dist(p, q)


def straight(roads, node, heading, length, names):
    """node から heading の向きへ、道路に沿って length m（最後の辺は途中で切る）"""
    line, cur, prev, left = [list(roads.coord[node])], node, None, length
    while left > 0:
        c = roads.coord[cur]
        opts = [(v, w, ns) for v, w, ns in roads.adj.get(cur, []) if v != prev]
        opts = [o for o in opts if angle_diff(bearing(c, roads.coord[o[0]]), heading) < 45]
        if not opts:
            break
        v, w, ns = min(opts, key=lambda o: angle_diff(bearing(c, roads.coord[o[0]]), heading) + (0 if (not names or o[2] & names) else 30))
        heading = bearing(c, roads.coord[v])
        if w >= left:
            t = left / w
            n = roads.coord[v]
            line.append([c[0] + (n[0] - c[0]) * t, c[1] + (n[1] - c[1]) * t])
            break
        line.append(list(roads.coord[v]))
        prev, cur, left = cur, v, left - w
    return line


def around(roads, q, a, b, length, names):
    """道路上の点 q（辺 ab の上）を中心に、辺の両方向へ length/2 ずつ"""
    h = bearing(roads.coord[a], roads.coord[b])
    fwd = [list(q)] + straight(roads, b, h, max(0, length / 2 - dist(q, roads.coord[b])), names) if dist(q, roads.coord[b]) < length / 2 \
        else [list(q), [q[0] + (roads.coord[b][0] - q[0]) * (length / 2) / dist(q, roads.coord[b]), q[1] + (roads.coord[b][1] - q[1]) * (length / 2) / dist(q, roads.coord[b])]]
    back = [list(q)] + straight(roads, a, (h + 180) % 360, max(0, length / 2 - dist(q, roads.coord[a])), names) if dist(q, roads.coord[a]) < length / 2 \
        else [list(q), [q[0] + (roads.coord[a][0] - q[0]) * (length / 2) / dist(q, roads.coord[a]), q[1] + (roads.coord[a][1] - q[1]) * (length / 2) / dist(q, roads.coord[a])]]
    return list(reversed(back)) + fwd[1:]


def service_nodes(pbf):
    import osmium
    out = set()
    for o in osmium.FileProcessor(pbf, osmium.osm.WAY):
        if o.tags.get('highway') == 'service':
            out.update(n.ref for n in o.nodes)
    return out


def build(region, pbf):
    import osmium
    cfg = REGIONS[region]
    roads = Roads(pbf)
    names_index = {}
    for o in osmium.FileProcessor(pbf).with_locations():
        nm = o.tags.get('name') if hasattr(o, 'tags') else None
        if not nm:
            continue
        if o.is_node() and o.location.valid():
            x, y = o.location.lon, o.location.lat
            names_index.setdefault(nm, []).append((x, y, x, y))
        elif o.is_way() and not o.tags.get('highway'):
            pts = [(n.lon, n.lat) for n in o.nodes if n.location.valid()]
            if pts:
                names_index.setdefault(nm, []).append((min(p[0] for p in pts), min(p[1] for p in pts),
                                                       max(p[0] for p in pts), max(p[1] for p in pts)))
    # 構内道路・駐車場の通路（highway=service）には枠がないので使わない
    service = service_nodes(pbf)
    edges = [(a, b, ns) for a, es in roads.adj.items() for b, _, ns in es if a < b and not (a in service and b in service)]
    out = {}
    for it in cfg['items']:
        names = {norm_road(it['road'])} if it.get('road') else set()
        want = it['spaces'] * SPACE_M
        line, how, box = None, '', None
        if it.get('from_cross'):
            both = roads.nodes_on(names) & roads.nodes_on({norm_road(it['from_cross'])})
            if both:
                start = min(both, key=lambda j: -roads.coord[j][1])  # 複数あれば北側（どれも同じ交差点のノード群）
                line = straight(roads, start, BEARING[it['along']], want, names)
            how = f"{it['from_cross']}との交差点から{it['along']}へ"
        else:
            box = MANUAL_MARK.get(it['id']) or find_mark(names_index, it.get('mark'), it.get('addr'))
            if box:
                W, S, E, N = box
                cx, cy = (W + E) / 2, (S + N) / 2
                side = it.get('side')
                # 目印の辺の中点。道路はその外側にあり、辺と平行（向きの差30度以内）
                p = {'west': (W, cy), 'east': (E, cy), 'north': (cx, N), 'south': (cx, S)}.get(side, (cx, cy))
                par = {'west': 0, 'east': 0, 'north': 90, 'south': 90}.get(side)
                best = None
                for a, b, ns in edges:
                    if names and not (ns & names):
                        continue
                    ca, cb = roads.coord[a], roads.coord[b]
                    # 道路の向き（上り下りは問わない）が辺と平行か
                    if par is not None and min(angle_diff(bearing(ca, cb), par), angle_diff(bearing(ca, cb), par + 180)) > 30:
                        continue
                    q, d = project(p, ca, cb)
                    if d > (60 if W != E else 90):  # 目印が点（建物の輪郭がない）なら街区の中ほどにあるので遠くまで見る
                        continue
                    if side and angle_diff(bearing((cx, cy), q), BEARING[side]) > 60:
                        continue
                    if not best or d < best[0]:
                        best = (d, q, a, b)
                if best:
                    # 長さは枠数ぶん。ただし目印の辺の長さ（＋前後10m）を超えない
                    extent = dist((W, S), (W, N)) if par == 0 else dist((W, S), (E, S)) if par == 90 else want
                    L = min(want, extent + 20) if extent > 5 else want
                    line = around(roads, best[1], best[2], best[3], L, names)
                how = f"{it.get('mark') or it.get('addr')}の{side or '前'}"
        L = sum(dist(p, q) for p, q in zip(line, line[1:])) if line else 0
        out[it['id']] = {'line': line if line and L > 5 else None, 'how': how, 'length_m': round(L)}
        print(f"{it['id']:12} {how:30} {round(L)}m (枠数ぶん {want}m)", 'mark', [round(v, 5) for v in box] if not it.get('from_cross') and box else '', flush=True)
    d = ROOT / 'build' / 'source' / region
    d.mkdir(parents=True, exist_ok=True)
    (d / 'geometry.json').write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding='utf-8')


if __name__ == '__main__':
    if len(sys.argv) == 3 and sys.argv[1] in REGIONS:
        build(sys.argv[1], sys.argv[2])
    else:
        print(__doc__)
