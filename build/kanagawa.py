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
    'kannai': {
        'name': '関内地区', 'station': '加賀町警察署', 'map': 'f4002_m03',
        # 地図の色付きの線が OSM の道路に重なるよう自動で合わせた変換（平均のずれ 7m）。区間は地図の太線の両端を読んだ
        'tf': (2.0024, -0.354, 139.6316048, 35.4497827),
        'ctrl': [((25, 10), [139.63075, 35.45124]), ((447, 22), [139.64099, 35.44998]), ((470, 213), [139.64172, 35.44646]),
                 ((467, 290), [139.6422, 35.4447]), ((393, 325), [139.63989, 35.44358]), ((185, 333), [139.63604, 35.44408])],
        'segs': [
            ('ticket', (106, 38), (169, 75), '関内'),
            ('ticket', (139, 35), (181, 59), '関内'),
            ('ticket', (194, 36), (231, 60), '関内'),
            ('ticket', (178, 64), (216, 84), '関内'),
            ('ticket', (170, 83), (206, 108), '関内'),
            ('ticket', (223, 93), (260, 114), '関内'),
            ('ticket', (213, 113), (249, 135), '関内'),
            ('ticket', (119, 105), (140, 123), '関内'),
            ('ticket', (145, 131), (181, 159), '関内'),
            ('ticket', (186, 164), (223, 189), '関内'),
            ('ticket', (50, 135), (108, 210), '関内'),
            ('ticket', (105, 213), (131, 245), '関内'),
            ('ticket', (273, 123), (313, 148), '関内'),
            ('ticket', (258, 144), (299, 173), '関内'),
            ('ticket', (315, 150), (358, 176), '関内'),
            ('ticket', (303, 176), (345, 203), '関内'),
            ('ticket', (365, 183), (404, 206), '関内'),
            ('ticket', (229, 196), (265, 220), '関内'),
            ('ticket', (350, 205), (391, 234), '関内'),
            ('ticket', (273, 228), (313, 258), '関内'),
            ('ticket', (314, 260), (356, 286), '関内'),
            ('ticket', (390, 250), (430, 275), '関内'),
            ('ticket', (465, 231), (509, 259), '関内'),
            ('ticket', (420, 79), (465, 105), '関内'),
            ('ticket', (344, 100), (314, 148), '関内'),
            ('ticket', (176, 276), (210, 300), '関内、関内駅北口の東（貨）'),
            ('ticket', (213, 303), (249, 328), '関内、関内駅北口の東（貨）'),
            ('meter', (328, 18), (348, 33), '関内'),
            ('meter', (100, 59), (155, 98), '関内'),
            ('meter', (158, 103), (198, 129), '関内'),
            ('meter', (83, 97), (95, 109), '関内'),
            ('meter', (103, 120), (123, 140), '関内'),
            ('meter', (125, 143), (141, 169), '関内'),
            ('meter', (85, 173), (99, 163), '関内'),
            ('meter', (105, 159), (143, 131), '関内'),
            ('meter', (163, 95), (176, 64), '関内'),
            ('meter', (395, 119), (400, 108), '関内'),
            ('meter', (375, 165), (384, 143), '関内'),
            ('meter', (374, 159), (350, 203), '関内'),
            ('meter', (324, 240), (350, 205), '関内'),
            ('meter', (314, 149), (278, 206), '関内'),
            ('meter', (274, 210), (258, 240), '関内'),
            ('meter', (214, 225), (250, 250), '関内'),
            ('meter', (240, 262), (249, 252), '関内'),
            ('meter', (253, 253), (293, 280), '関内'),
            ('meter', (310, 260), (278, 305), '関内'),
        ],
    },
    'isezaki': {
        'name': '伊勢佐木・南地区', 'station': '伊勢佐木警察署・南警察署', 'map': 'f4002_m05',
        # 自動の位置合わせ（交番・警察署の位置から±120mの範囲。平均のずれ 6.7m）
        'tf': (2.0137, -0.505, 139.6214956, 35.4471664),
        'segs': [
            ('ticket', (460, 8), (522, 95), '伊勢佐木・南'),
            ('ticket', (330, 120), (365, 98), '伊勢佐木・南'),
            ('ticket', (440, 170), (489, 225), '伊勢佐木・南'),
            ('ticket', (360, 413), (386, 395), '伊勢佐木・南'),
            ('ticket', (410, 405), (437, 388), '伊勢佐木・南'),
            ('ticket', (250, 470), (322, 430), '伊勢佐木・南'),
            ('ticket', (332, 448), (392, 412), '伊勢佐木・南'),
            ('ticket', (262, 485), (300, 465), '伊勢佐木・南'),
            ('ticket', (176, 515), (214, 494), '伊勢佐木・南'),
            ('ticket', (209, 518), (246, 498), '伊勢佐木・南'),
            ('meter', (452, 16), (471, 41), '伊勢佐木・南'),
            ('meter', (289, 131), (357, 93), '伊勢佐木・南'),
            ('meter', (375, 93), (437, 166), '伊勢佐木・南'),
            ('meter', (401, 205), (435, 172), '伊勢佐木・南'),
            ('meter', (382, 220), (399, 205), '伊勢佐木・南'),
            ('meter', (402, 204), (422, 228), '伊勢佐木・南'),
            ('meter', (270, 235), (312, 272), '伊勢佐木・南'),
            ('meter', (330, 268), (365, 235), '伊勢佐木・南'),
            ('meter', (280, 312), (315, 282), '伊勢佐木・南'),
            ('meter', (380, 292), (392, 308), '伊勢佐木・南'),
            ('meter', (345, 328), (355, 340), '伊勢佐木・南'),
            ('meter', (180, 358), (228, 305), '伊勢佐木・南'),
            ('meter', (245, 345), (260, 322), '伊勢佐木・南'),
            ('meter', (260, 332), (290, 370), '伊勢佐木・南'),
            ('meter', (205, 378), (228, 360), '伊勢佐木・南'),
            ('meter', (100, 430), (172, 368), '伊勢佐木・南'),
            ('meter', (18, 480), (90, 442), '伊勢佐木・南'),
            ('meter', (105, 448), (189, 395), '伊勢佐木・南'),
            ('meter', (125, 478), (260, 372), '伊勢佐木・南'),
            ('meter', (35, 528), (118, 485), '伊勢佐木・南'),
            ('meter', (428, 468), (508, 420), '伊勢佐木・南'),
        ],
    },
    'yamashita': {
        'name': '山下町・元町周辺', 'station': '加賀町警察署', 'map': 'f4002_m04',
        # 橋（谷戸橋・前田橋・西之橋・山下橋）と建物（県民ホール・産業貿易センター・加賀町警察署・ホテルニューグランド）で換算
        'ctrl': [((505, 261), [139.65095, 35.44197]), ((398, 300), [139.64842, 35.44098]), ((260, 385), [139.64512, 35.43938]),
                 ((603, 219), [139.6535, 35.44298]), ((483, 129), [139.64957, 35.4448]), ((330, 56), [139.64694, 35.44619]),
                 ((265, 27), [139.64577, 35.44687]), ((198, 194), [139.64363, 35.44355])],
        'segs': [
            ('ticket', (298, 52), (455, 155), '山下公園通りの一本内側（県民ホールからホテルニューグランド）'),
            ('ticket', (225, 268), (250, 348), '山下町、中華街の西の南北の道'),
            ('ticket', (265, 380), (470, 275), '山下町、首都高の北側（西之橋から谷戸橋の手前）'),
            ('meter', (290, 405), [139.6505, 35.4413], '元町1〜5丁目、首都高の南側（中村川沿い）'),
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


def from_tf(tf):
    """自動の位置合わせ（地図の色付きの線を OSM の道路に重ねる最適化）で求めた変換。
    tf = (m/px, 回転[度], 地図の左上の経度, 緯度)"""
    s, r, lon0, lat0 = tf
    k = math.cos(math.radians(lat0))
    c, sn = math.cos(math.radians(r)), math.sin(math.radians(r))
    def f(pt):
        u, v = pt
        x = s * (c * u + sn * v)       # 東向き m
        y = s * (-sn * u + c * v)      # 南向き m
        return [lon0 + x / (111320 * k), lat0 - y / 111320]
    return f


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
        f = from_tf(area['tf']) if area.get('tf') else None
        if area.get('ctrl') and not f:
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
            # 座標で書いた端、または60mより短い区間は交差点に寄せない（両端が同じ交差点に寄って消えるため）
            if (isinstance(e1, list) and isinstance(e2, list)) or dist(c1, c2) < 60:
                line = route(roads, c1, c2, skip)
            else:
                a, b = snap_end(roads, c1, 30, skip), snap_end(roads, c2, 30, skip)
                line = roads.path(a, b, set()) if a != b else route(roads, c1, c2, skip)
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
