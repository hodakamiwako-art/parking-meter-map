"""神奈川県警「パーキング・メーター等の設置場所」の区間を線にする。

    python3 build/kanagawa.py KANAGAWA.osm.pbf    # → build/source/kanagawa/geometry.json

神奈川県警は区間を地区ごとの地図（画像）でしか示しておらず、通り名も交差点名も書いていない。
地図は複製禁止なので、線は地図から写さず、次のようにして OpenStreetMap の道路から作る。
  1. 地図に書かれた建物・駅（「高島屋」「横浜中央郵便局」など）と OSM の同じ建物を対応づけ、
     地図上の位置を経度・緯度に換算する式（拡大・回転・平行移動）を最小二乗で求める
  2. 地図で区間の両端がある場所を読み、その式で換算して、近くの OSM の交差点（なければ道路上の点）に合わせる
  3. その間を OSM の道路網でたどる
つまり線の形はすべて OSM の道路で、地図は「どの通りのどこからどこまでか」を知るためだけに使う。
県警の一覧に時間帯・曜日が書かれていないため、利用時間は「現地の標識で確認」とする。
"""
import json, math, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from osaka import Roads, dist

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'build' / 'source' / 'kanagawa'
PAGE = 'https://www.police.pref.kanagawa.jp/kotsu/ihochusha/mesf1080.html'

# 地区ごとの対応点と区間。対応点は (地図の x, y) ↔ OSM の名前（建物・駅。重心を使う）か [経度, 緯度]。
# 区間は (種別, 端1, 端2, メモ)。種別は 'meter' / 'ticket'、端は地図の (x, y) か [経度, 緯度]。
# 貨物車優先枠のある区間はメモに「貨」と書く。
AREAS = {
    'tsurumi': {
        'name': 'JR鶴見駅西口周辺・鶴見銀座', 'station': '鶴見警察署', 'map': 'f4002_m01',
        'segs': [
            ('ticket', [139.67603, 35.50946], [139.67671, 35.51171], 'JR鶴見駅北側、線路の西の道'),
            ('meter', [139.6782, 35.5071], [139.6770, 35.5048], '鶴見銀座（貨）'),
        ],
    },
    'yokohama': {
        'name': '横浜駅周辺', 'station': '神奈川警察署・戸部警察署', 'map': 'f4002_m02',
        'ctrl': [((172, 52), 'かながわ県民センター'), ((172, 108), [139.62069, 35.46742]),  # ヨドバシカメラ
                 ((225, 197), '髙島屋'), ((248, 282), '横浜中央郵便局'), ((402, 232), 'そごう'), ((105, 260), '横浜ビブレ')],
        'segs': [
            # 建物名の文字は建物の中心からずれるので、換算の結果を OSM の道路図と見比べて座標で書いた
            ('ticket', [139.6220, 35.4685], [139.6220, 35.4690], '鶴屋町2丁目、県民センターの東の道'),
            ('meter', [139.6224, 35.4677], [139.6214, 35.4674], '線路の南、ヨドバシカメラの北東の道'),
            ('meter', [139.6197, 35.4657], [139.6203, 35.4650], '南幸1丁目、帷子川の南から高島屋の西'),
            ('ticket', [139.6232, 35.4645], [139.6228, 35.4636], '高島2丁目、中央郵便局の東'),
            ('ticket', [139.6233, 35.4649], [139.6233, 35.4645], '高島2丁目、中央郵便局の東（短い区間）'),
        ],
    },
    'konandai': {
        'name': '港南台ひばり団地周辺', 'station': '港南警察署', 'map': 'f4002_m07',
        # 駅南の東西の道（港南台駅前交番の交差点 139.5768 〜 大通り 139.5823）に並ぶ。地図の x を経度に比例させて読んだ
        'segs': [
            ('ticket', [139.5771, 35.37395], [139.5784, 35.37405], '港南台駅前交番の東（北側）'),
            ('ticket', [139.5787, 35.37405], [139.5799, 35.3740], '（北側）'),
            ('ticket', [139.5802, 35.37401], [139.5805, 35.37398], '（北側、短い区間）'),
            ('meter', [139.5807, 35.37395], [139.5811, 35.37391], '（北側）'),
            ('meter', [139.5813, 35.37388], [139.5818, 35.37382], '大通りの手前（北側）'),
            ('meter', [139.5805, 35.37398], [139.5818, 35.37382], '（南側）'),
        ],
    },
    'tennocho': {
        'name': '天王町商店街通り', 'station': '保土ケ谷警察署', 'map': 'f4002_m08',
        # 天王町駅の北、水道道の1本北の通り。地図では途中で3か所切れているが、1本の区間として扱う
        'segs': [
            ('meter', [139.6021, 35.45692], [139.6052, 35.45545], '天王町1丁目'),
        ],
    },
    'hongodai': {
        'name': '本郷台駅周辺', 'station': '栄警察署', 'map': 'f4002_m09',
        # 駅の南の東西の2本の道（西の南北の道から東の大通りまで）
        'segs': [
            ('meter', [139.5488, 35.36665], [139.5519, 35.36700], '小菅ヶ谷1丁目、北の通り'),
            ('meter', [139.5489, 35.36575], [139.5521, 35.36635], '小菅ヶ谷1丁目、南の通り'),
        ],
    },
    'saginuma': {
        'name': '鷺沼駅周辺', 'station': '宮前警察署', 'map': 'f4002_m10',
        # 駅の南の東西の道。駅の位置と縮尺（約1.7m/px）から換算
        'segs': [
            ('ticket', [139.5713, 35.57808], [139.5729, 35.57822], '鷺沼1丁目・3丁目（道の両側）'),
            ('meter', [139.5735, 35.57828], [139.5745, 35.57838], '鷺沼1丁目'),
        ],
    },
    'hiratsuka': {
        'name': '平塚駅周辺', 'station': '平塚警察署', 'map': 'f4002_m11',
        # 浜大門通り（中央分離帯のある南北の道）・西の南北の道・八幡大門通りの交差の位置を合わせて換算（約2.45m/px）
        'segs': [
            ('meter', [139.35020, 35.33205], [139.35020, 35.32989], '浜大門通り（八幡大門通りの南北、道の両側）'),
            ('meter', [139.34750, 35.33062], [139.34750, 35.32896], '明石町・見附町、西の南北の道'),
            ('meter', [139.34600, 35.32888], [139.34715, 35.32905], '見附町・宮の前、駅北の東西の道（西）'),
            ('meter', [139.34723, 35.32929], [139.34939, 35.32967], '宮の前・明石町、駅北の東西の道'),
            ('meter', [139.35130, 35.32990], [139.35380, 35.33035], '老松町、浜大門通りの東（道の両側）'),
            ('meter', [139.35128, 35.32907], [139.35205, 35.32928], '宝町、南の東西の道'),
            ('meter', [139.35344, 35.32923], [139.35614, 35.32907], '宝町、南の東西の道（東）'),
        ],
    },
    'fujisawa': {
        'name': '藤沢駅南口周辺', 'station': '藤沢警察署', 'map': 'f4002_m12',
        # 南口の駅前広場から南へ延びる2本の道。駅とカトリック教会の位置から換算（約2.2m/px）
        'segs': [
            # 地図の2本の線は同じ道の両側と見て1区間にした
            ('ticket', [139.48718, 35.33785], [139.48692, 35.33722], '南藤沢、駅前広場の南西から南へ（道の両側）'),
        ],
    },
}

KIND = {'meter': 'パーキング・メーター', 'ticket': 'パーキング・チケット'}


def fit(pairs):
    """地図 (x, y) → (経度, 緯度) の相似変換を最小二乗で求める（地図の y は下向き）"""
    lat0 = sum(g[1] for _, g in pairs) / len(pairs)
    k = math.cos(math.radians(lat0))
    P = [(x, -y) for (x, y), _ in pairs]
    G = [(g[0] * k, g[1]) for _, g in pairs]
    n = len(P)
    px, py = sum(p[0] for p in P) / n, sum(p[1] for p in P) / n
    gx, gy = sum(g[0] for g in G) / n, sum(g[1] for g in G) / n
    a = b = d = 0
    for (x, y), (u, v) in zip(P, G):
        x, y, u, v = x - px, y - py, u - gx, v - gy
        a += x * u + y * v
        b += x * v - y * u
        d += x * x + y * y
    a, b = a / d, b / d  # u = a x - b y, v = b x + a y
    def f(pt):
        x, y = pt[0] - px, -pt[1] - py
        return [(a * x - b * y + gx) / k, b * x + a * y + gy]
    scale = math.hypot(a, b) * 111320  # m / px
    return f, scale


def centroid_index(pbf, names):
    import osmium
    want = set(names)
    out = {}
    for o in osmium.FileProcessor(pbf).with_locations():
        nm = o.tags.get('name') if hasattr(o, 'tags') else None
        if nm not in want:
            continue
        if o.is_node() and o.location.valid():
            out.setdefault(nm, []).append((o.location.lon, o.location.lat))
        elif o.is_way():
            pts = [(n.lon, n.lat) for n in o.nodes if n.location.valid()]
            if pts:
                out.setdefault(nm, []).append((sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts)))
    return {k: (sum(p[0] for p in v) / len(v), sum(p[1] for p in v) / len(v)) for k, v in out.items()}


def elevated_nodes(pbf):
    """端を寄せないノード：首都高・高架・トンネルの道路と、構内道路（service）だけにあるノード"""
    import osmium
    out, service, street = set(), set(), set()
    for o in osmium.FileProcessor(pbf, osmium.osm.WAY):
        t = o.tags
        refs = [n.ref for n in o.nodes]
        if not t.get('highway'):
            continue
        if t.get('highway') in ('motorway', 'motorway_link') or t.get('bridge') or t.get('tunnel') or t.get('layer', '0') not in ('0', ''):
            out.update(refs)
        elif t.get('highway') == 'service':
            service.update(refs)
        else:
            street.update(refs)
    # 地上の一般道にも含まれる点（高架・構内道路との接続点）は残す
    return (out | service) - street


def snap_end(roads, c, limit=30, skip=frozenset()):
    """交差点（3本以上の道が集まるノード）が limit m 以内にあればそこへ、なければ最寄りの道路上のノードへ"""
    pool = [j for j in roads.adj if j not in skip]
    cross = [j for j in pool if len({v for v, _, _ in roads.adj[j]}) >= 3 and dist(c, roads.coord[j]) < limit]
    if cross:
        return min(cross, key=lambda j: dist(c, roads.coord[j]))
    return min(pool, key=lambda j: dist(c, roads.coord[j]))


def on_edge(roads, c, skip):
    """座標 c を最寄りの道路の辺に下ろした点 (q, a, b)"""
    best = None
    for a, es in roads.adj.items():
        if a in skip or dist(c, roads.coord[a]) > 400:
            continue
        for b, _, _ in es:
            if b in skip:
                continue
            A, B = roads.coord[a], roads.coord[b]
            kx = math.cos(math.radians(c[1]))
            ax, ay, bx, by, px, py = A[0] * kx, A[1], B[0] * kx, B[1], c[0] * kx, c[1]
            dx, dy = bx - ax, by - ay
            t = 0 if dx == dy == 0 else max(0, min(1, ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)))
            q = [A[0] + (B[0] - A[0]) * t, A[1] + (B[1] - A[1]) * t]
            d = dist(c, q)
            if not best or d < best[0]:
                best = (d, q, a, b)
    return best[1], best[2], best[3]


def route(roads, c1, c2, skip):
    """道路上の2点（辺の途中でもよい）を道路網でつなぐ"""
    q1, a1, b1 = on_edge(roads, c1, skip)
    q2, a2, b2 = on_edge(roads, c2, skip)
    if {a1, b1} == {a2, b2}:
        return [q1, q2]
    best = None
    for u in (a1, b1):
        for v in (a2, b2):
            p = roads.path(u, v, set())
            if p:
                L = dist(q1, roads.coord[u]) + sum(dist(x, y) for x, y in zip(p, p[1:])) + dist(roads.coord[v], q2)
                if not best or L < best[0]:
                    best = (L, p)
    return [q1] + best[1] + [q2] if best else None


def trim(line):
    """端の短いかぎ（全体の向きと60度以上ずれた30m未満の辺）を落とす"""
    if not line or len(line) < 3:
        return line
    import math as m
    def b(p, q):
        return m.degrees(m.atan2((q[0] - p[0]) * m.cos(m.radians(p[1])), q[1] - p[1])) % 360
    for _ in range(2):
        whole = b(line[0], line[-1])
        if len(line) > 2 and dist(line[0], line[1]) < 30 and min(abs((b(line[0], line[1]) - whole + 180) % 360 - 180), 180) > 60:
            line = line[1:]
        whole = b(line[0], line[-1])
        if len(line) > 2 and dist(line[-2], line[-1]) < 30 and abs((b(line[-2], line[-1]) - whole + 180) % 360 - 180) > 60:
            line = line[:-1]
    return line


def main(pbf):
    roads = Roads(pbf)
    skip = elevated_nodes(pbf)
    names = [c for a in AREAS.values() for _, c in a.get('ctrl', []) if isinstance(c, str)]
    cen = centroid_index(pbf, names) if names else {}
    out = {}
    for key, area in AREAS.items():
        f = None
        if area.get('ctrl'):
            pairs = []
            for px, g in area['ctrl']:
                g = cen.get(g) if isinstance(g, str) else g
                if g:
                    pairs.append((px, g))
            f, scale = fit(pairs)
            res = [round(dist(f(px), g)) for px, g in pairs]
            print(f'{key}: 対応点 {len(pairs)}、縮尺 {scale:.2f} m/px、ずれ {res} m', flush=True)
        for i, (kind, e1, e2, note) in enumerate(area['segs'], 1):
            c1 = e1 if isinstance(e1, list) else f(e1)
            c2 = e2 if isinstance(e2, list) else f(e2)
            # 地図から換算した端は近くの交差点へ、座標で直接書いた端は最寄りの道路の上（辺の途中でもよい）へ
            if isinstance(e1, list) and isinstance(e2, list):
                line = route(roads, c1, c2, skip)
            else:
                line = roads.path(snap_end(roads, c1, 30, skip), snap_end(roads, c2, 30, skip), set())
            line = trim(line)
            L = round(sum(dist(p, q) for p, q in zip(line, line[1:]))) if line else 0
            sid = f'kanagawa-{key}-{i}'
            out[sid] = {'area': area['name'], 'station': area['station'], 'kind': kind, 'note': note,
                        'truck': '貨' in note, 'line': line, 'length_m': L}
            print(f'  {sid:24} {KIND[kind]:12} {L:4}m {note}', flush=True)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / 'geometry.json').write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding='utf-8')
    print(f'{sum(1 for v in out.values() if v["line"])}/{len(out)} lines -> {(OUT / "geometry.json").relative_to(ROOT)}')


if __name__ == '__main__':
    if len(sys.argv) == 2:
        main(sys.argv[1])
    else:
        print(__doc__)
