"""大阪府警「パーキング・チケット発給設備設置状況」を読み込み、区間の線を付ける。

    python3 build/osaka.py fetch                # 府警の12警察署のページから表を取り直す → build/source/osaka/rows.json
    python3 build/osaka.py geometry OSM.pbf     # OSM の道路から区間の線を作る       → build/source/osaka/geometry.json

大阪府警は座標を公開しておらず、区間は「深里橋交差点から京町堀1丁目交差点まで」のように
言葉で書かれている。そこで両端の位置を
  - 「○○交差点」… OSM の名前つきノード（信号・交差点。name は「交差点」を付けない形が多い）
  - 「○○番○○号先」… 国土地理院の住所検索
で求め、その間を OSM の道路網で最短経路をとって線にする（区間の路線名と同じ名前の道路を優先）。
自動で決まらない区間は MANUAL に両端の座標を直接書く。結果は各署の設置地図（画像）と照らし合わせて確かめる。

OSM.pbf は OpenStreetMap のデータから大阪市周辺を切り出したもの（大きいのでリポジトリには入れない）。例：
    curl -sS https://download.bbbike.org/osm/planet/sub-planet-daily/asia.osm.pbf \\
      | osmium extract -s simple -b 135.44,34.58,135.60,34.78 -F pbf - -o osaka.osm.pbf
build/build.py はこのファイルが作った rows.json と geometry.json を読み、東京の区間と合わせて data/zones.geojson を作る。
"""
import heapq, html, json, math, re, sys, time, unicodedata, urllib.parse, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / 'build' / 'source' / 'osaka'
BASE = 'https://www.police.pref.osaka.lg.jp/kotsu/tyusya/1/1/'
GSI_SEARCH = 'https://msearch.gsi.go.jp/address-search/AddressSearch?q='

# 警察署 → 管轄の市区（住所で書かれた端点を住所検索にかけるときの頭につける）
STATION_CITY = {
    '曽根崎警察署': '大阪市北区', '天満警察署': '大阪市北区', '東警察署': '大阪市中央区', '西警察署': '大阪市西区',
    '天王寺警察署': '大阪市天王寺区', '南警察署': '大阪市中央区', '浪速警察署': '大阪市浪速区', '淀川警察署': '大阪市淀川区',
    '阿倍野警察署': '大阪市阿倍野区', '住之江警察署': '大阪市住之江区', '吹田警察署': '吹田市', '布施警察署': '東大阪市',
}


def text(x):
    return re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', ' ', x))).strip()


def get(url, tries=4):
    for i in range(tries):
        try:
            with urllib.request.urlopen(url, timeout=30) as r:
                return r.read().decode('utf-8')
        except Exception:
            if i == tries - 1:
                raise
            time.sleep(2 * (i + 1))


def fetch():
    index = get(BASE + 'index.html')
    pages = sorted(set(re.findall(r'href="(?:https://www\.police\.pref\.osaka\.lg\.jp)?/kotsu/tyusya/1/1/(\d+)\.html"', index)))
    rows = []
    for pid in pages:
        s = get(f'{BASE}{pid}.html')
        station = text(re.search(r'<h1[^>]*>(.*?)</h1>', s, re.S).group(1)).replace('のパーキング・チケット発給設備設置状況', '')
        asof = re.search(r'令和\d+年\d+月\d+日現在', s)
        table = re.search(r'<table.*?</table>', s, re.S).group(0)
        head = [text(c) for c in re.findall(r'<t[dh][^>]*>(.*?)</t[dh]>', re.findall(r'<tr.*?</tr>', table, re.S)[0], re.S)]
        has_truck = any('貨物' in h for h in head)
        for n, tr in enumerate(re.findall(r'<tr.*?</tr>', table, re.S)[1:], 1):
            c = [text(x) for x in re.findall(r'<t[dh][^>]*>(.*?)</t[dh]>', tr, re.S)]
            route, section, spaces = c[0], c[1], c[2]
            truck = c[3] if has_truck else ''
            hours = c[-1]
            rows.append({
                'id': f'osaka-{pid}-{n}', 'station': station, 'asof': asof.group(0) if asof else '',
                'page': f'{BASE}{pid}.html',
                'route': re.sub(r'\s*【.*?】', '', route).strip(),
                'truck_mark': (re.search(r'【(.*?)】', route) or [None, ''])[1],
                'section': section, 'spaces': int(spaces) if spaces.isdigit() else None,
                'truck_spaces': int(truck) if truck.isdigit() else 0,
                'weekday_only': '注釈' in hours,   # （注釈）= 日曜・休日を除く（土曜は使える）
                'hours': re.sub(r'（注釈）', '', hours).strip(),
            })
        print(station, asof.group(0) if asof else '', flush=True)
        time.sleep(1)
    SRC.mkdir(parents=True, exist_ok=True)
    (SRC / 'rows.json').write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding='utf-8')
    print(f'{len(rows)} rows -> {(SRC / "rows.json").relative_to(ROOT)}')


"""--- 区間の線を作る ---"""

# 車が通る道路だけで経路を作る（歩道・自転車道・階段などは使わない）
DRIVE = {'motorway', 'trunk', 'primary', 'secondary', 'tertiary', 'unclassified', 'residential',
         'motorway_link', 'trunk_link', 'primary_link', 'secondary_link', 'tertiary_link', 'living_street', 'service'}
KANJI_NUM = str.maketrans('〇一二三四五六七八九', '0123456789')

# 自動で決まらない・ずれる端点。府警の設置地図（画像）と OSM の道路を見比べて決めた。
# 区間 id → {'from': 端点, 'to': 端点}。端点は [経度, 緯度] か {'cross': 交わる道路名, 'near': [経度, 緯度]}
MANUAL = {
    # 布施：駅前の交差点を近鉄高架の南側にそろえ、渋川放出線は三ノ瀬1丁目までまっすぐ南へ
    'osaka-6012-1': {'from': [135.5632, 34.6644], 'to': [135.5620, 34.6646]},
    'osaka-6012-2': {'from': [135.5631, 34.6611], 'to': [135.5632, 34.6644]},
    # 吹田：吹田駅前通りは OSM では「旭通商店街」。地図の下（高浜神社側）の長い区間と、駅側の短い区間
    'osaka-6014-1': {'from': [135.52612, 34.75829], 'to': [135.52500, 34.76095]},
    'osaka-6014-2': {'from': [135.52470, 34.76143], 'to': [135.52345, 34.76234]},
    # 淀川：新御堂筋の西側、西中島3丁目交差点から北へ短く
    'osaka-6016-1': {'from': [135.4988, 34.7262], 'to': [135.4988, 34.7251]},
    # 住之江：南港通りの南側、国道26号の少し西
    'osaka-6018-1': {'from': [135.4893, 34.6230], 'to': [135.4879, 34.6228]},
    # 阿倍野：あびこ筋の上だけを通るよう、北の端を筋の上に
    'osaka-6019-1': {'to': [135.5170, 34.6339]},
    # 天王寺：清風高校前は上本町7丁目から東へ約270m
    'osaka-6020-1': {'from': [135.5217, 34.6630]},
    # 浪速：OSM の「日本橋西1」の信号は筋の東にあるので、両端とも筋の上に置く
    'osaka-6021-1': {'from': [135.50275, 34.65935], 'to': [135.5029, 34.6614]},
    # 南：堺筋鰻谷は長堀通との交差点。高島屋西筋はなんば駅側へ延ばす
    'osaka-6022-1': {'from': [135.5010, 34.6633]},
    'osaka-6022-4': {'to': {'cross': '長堀通', 'near': [135.5064, 34.6753]}},
    # 西：南堀江通りは西道頓堀橋北から東へ四つ橋筋の手前まで。西横堀西岸線はその東の南北の短い道
    'osaka-6023-1': {'from': [135.4961, 34.6707]},
    'osaka-6023-2': {'from': [135.4971, 34.6706], 'to': [135.4971, 34.6695]},
    'osaka-6023-4': {'to': [135.4932, 34.6848]},
    'osaka-6023-8': {'to': [135.4928, 34.6727]},
    # 天満：どちらも曽根崎通のすぐ北の短い区間
    'osaka-6025-1': {'from': [135.5061, 34.6992], 'to': [135.5061, 34.6982]},
    'osaka-6025-2': {'from': [135.5084, 34.6983], 'to': [135.5074, 34.6983]},
}


def norm_place(s):
    """交差点名をそろえる。OSM は「京町堀1」「道修町３」のように略すので、
    全角→半角、漢数字→数字にし、「丁目」「交差点」を落として比べる"""
    s = unicodedata.normalize('NFKC', s or '').translate(KANJI_NUM)
    return re.sub(r'交差点$|丁目|丁|\s', '', s)


def norm_road(s):
    """路線名をそろえる：「中央大通り」「中央大通」→「中央大通」、番号・括弧・空白を落とす"""
    s = re.sub(r'（.*?）|\(.*?\)|\s', '', s or '')
    s = re.sub(r'\d+$', '', s)
    return re.sub(r'り$', '', s)


def road_names(route):
    """表の路線名から、OSM の道路名として探す候補を作る（「大阪環状線（都島通り）」→ 両方）"""
    names = {norm_road(route)}
    for inner in re.findall(r'（(.*?)）', route):
        names.add(norm_road(inner))
    return {n for n in names if n}


def dist(a, b):
    """[経度, 緯度] 2点間のおよその距離（m）"""
    kx = 111320 * math.cos(math.radians((a[1] + b[1]) / 2))
    return math.hypot((a[0] - b[0]) * kx, (a[1] - b[1]) * 110540)


class Roads:
    def __init__(self, pbf):
        import osmium
        self.coord, self.named, self.adj, self.bridges = {}, {}, {}, {}
        ways = []
        for o in osmium.FileProcessor(pbf).with_locations():
            if o.is_node():
                if o.location.valid():
                    self.coord[o.id] = (o.location.lon, o.location.lat)
                    for k in ('name', 'name:ja', 'junction:name', 'junction:name:ja'):
                        nm = o.tags.get(k)
                        if nm:
                            self.named.setdefault(norm_place(nm), set()).add(o.id)
            elif o.is_way() and o.tags.get('highway') in DRIVE:
                names = {norm_road(o.tags.get(k)) for k in ('name', 'alt_name', 'official_name', 'old_name', 'name:ja')} - {''}
                ways.append(([n.ref for n in o.nodes], names))
                bn = o.tags.get('bridge:name') or (o.tags.get('name') if o.tags.get('bridge') else None)
                if bn:
                    self.bridges.setdefault(norm_place(bn), []).extend(n.ref for n in o.nodes)
            elif o.is_way() and o.tags.get('man_made') == 'bridge' and o.tags.get('name'):
                # 橋の輪郭（面）として描かれた橋
                self.bridges.setdefault(norm_place(o.tags['name']), []).extend(n.ref for n in o.nodes)
        for refs, names in ways:
            for a, b in zip(refs, refs[1:]):
                if a in self.coord and b in self.coord:
                    d = dist(self.coord[a], self.coord[b])
                    self.adj.setdefault(a, []).append((b, d, names))
                    self.adj.setdefault(b, []).append((a, d, names))

    def nodes_on(self, names):
        return {a for a, es in self.adj.items() for _, _, ns in es if ns & names}

    def intersection(self, label, names, near=None):
        """「深里橋交差点」→ 名前が合う OSM ノードのうち、区間の道路上（なければ最寄りの道路上）のもの"""
        cands = [i for i in self.named.get(norm_place(label), ()) if i in self.coord]
        if not cands:
            return None
        on = self.nodes_on(names)
        def score(i):
            c = self.coord[i]
            s = 0 if i in on else min((dist(c, self.coord[j]) for j in on), default=500) if on else 0
            return s + (dist(c, near) / 10 if near else 0)
        best = min(cands, key=score)
        return self.snap(self.coord[best], names)

    def snap(self, c, names, limit=150):
        """座標 c に最も近い、区間の道路上のノード（なければ車道のノード）"""
        on = self.nodes_on(names)
        pool = on if on and min(dist(c, self.coord[j]) for j in on) < limit else self.adj.keys()
        return min(pool, key=lambda j: dist(c, self.coord[j]))

    def bridge_end(self, label, names, near=None):
        """「平野橋西詰」「新回生橋東」「深里橋」→ OSM の橋の、その向きの端に近い区間の道路上のノード。
        橋は bridge:name つきの道路・man_made=bridge の輪郭・橋の名前の信号のどれかで探す。
        向きが書かれていなければ、区間のもう一方の端（near）に近い側の端をとる"""
        m = re.match(r'(.+?橋)(西詰|東詰|南詰|北詰|西|東|南|北)?交差点$', label)
        if not m:
            return None
        base = norm_place(m.group(1))
        pts = [self.coord[n] for n in self.bridges.get(base, []) + list(self.named.get(base, ())) if n in self.coord]
        if near:  # 同じ名前の橋が離れた場所にもあるので、区間のもう一方の端から3km以内に限る
            pts = [p for p in pts if dist(p, near) < 3000]
        if not pts:
            return None
        side = (m.group(2) or '')[:1]
        key = {'西': lambda c: c[0], '東': lambda c: -c[0], '南': lambda c: c[1], '北': lambda c: -c[1]}.get(side)
        if key:
            c = min(pts, key=key)
        elif near:
            c = min(pts, key=lambda p: dist(p, near))
        else:
            c = (sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts))
        return self.snap(c, names)

    def crossing(self, other, names, near):
        """区間の道路と、名前 other の道路が交わるノード（near に最も近いもの）"""
        mine = self.nodes_on(names)
        theirs = self.nodes_on({norm_road(other)})
        both = mine & theirs
        return min(both, key=lambda j: dist(near, self.coord[j])) if both else None

    def crossing_near(self, c, names):
        """座標 c に近い、区間の道路上の交差点（3本以上の道が集まるノード）"""
        on = [j for j in self.nodes_on(names) if len({v for v, _, _ in self.adj[j]}) >= 3]
        return min(on, key=lambda j: dist(c, self.coord[j])) if on else None

    def path(self, a, b, names):
        """a→b の最短経路。区間の路線名と違う道路は3倍の重みにして、路線に沿わせる"""
        best, prev, pq = {a: 0}, {}, [(0, a)]
        while pq:
            d, u = heapq.heappop(pq)
            if u == b:
                break
            if d > best.get(u, 1e18):
                continue
            for v, w, ns in self.adj.get(u, []):
                nd = d + w * (1 if ns & names else 3)
                if nd < best.get(v, 1e18):
                    best[v], prev[v] = nd, u
                    heapq.heappush(pq, (nd, v))
        if b not in prev and a != b:
            return None
        out, u = [b], b
        while u != a:
            u = prev[u]
            out.append(u)
        return [list(self.coord[n]) for n in reversed(out)]


def geocode(addr):
    """国土地理院の住所検索。「南堀江1丁目4番9号先」→ 街区の代表点 [経度, 緯度]"""
    q = addr.translate(KANJI_NUM)
    q = re.sub(r'(\d+)番(?:地)?(\d+)?号?', lambda m: m.group(1) + ('-' + m.group(2) if m.group(2) else ''), q)
    q = re.sub(r'(先|街区.*|角.*)$', '', q)
    with urllib.request.urlopen(GSI_SEARCH + urllib.parse.quote(q), timeout=20) as r:
        hits = json.load(r)
    return hits[0]['geometry']['coordinates'] if hits else None


def endpoint_label(s, prev_town):
    """「同1丁目3番2号先」の「同」を直前の町名で補う"""
    if s.startswith('同') and prev_town:
        return prev_town + s[1:]
    return s


def geometry(pbf):
    rows = json.loads((SRC / 'rows.json').read_text(encoding='utf-8'))
    roads = Roads(pbf)
    print(f'roads: {len(roads.adj):,} nodes, {len(roads.named):,} named', flush=True)
    out = {}
    for r in rows:
        m = re.match(r'(.+?)から(.+?)まで(?:（(.)側）)?$', r['section'])
        a_txt, b_txt = m.group(1), m.group(2)
        town = re.match(r'(.+?\d+丁目)', a_txt)
        b_txt = endpoint_label(b_txt, re.sub(r'\d+丁目$', '', town.group(1)) if town else '')
        names = road_names(r['route'])
        ends, notes = [], []
        for label in (a_txt, b_txt):
            man = MANUAL.get(r['id'], {}).get('from' if label is a_txt else 'to')
            if isinstance(man, dict):   # {'cross': 交わる道路名, 'near': [経度, 緯度]}
                ends.append(roads.crossing(man['cross'], names, man['near'])); notes.append('手入力（交差する道路）')
            elif man:                   # [経度, 緯度]
                ends.append(roads.snap(man, names)); notes.append('手入力')
            elif label.endswith('交差点'):
                n = roads.intersection(label, names)
                b = None if n else roads.bridge_end(label, names)
                if n:
                    ends.append(n); notes.append('交差点')
                elif b:
                    ends.append(('bridge', label)); notes.append('橋の端')
                else:
                    # 名前のついた信号が OSM にない：交差点名（多くは町名＋丁目）の位置に近い、路線上の交差点
                    c = geocode(STATION_CITY[r['station']] + re.sub(r'交差点$', '', label))
                    n = roads.crossing_near(c, names) if c else None
                    ends.append(n); notes.append('町名から推定' if n else '見つからない')
                    time.sleep(0.3)
            else:
                c = geocode(STATION_CITY[r['station']] + label)
                ends.append(roads.snap(c, names) if c else None); notes.append('住所' if c else '住所が見つからない')
                time.sleep(0.3)
        # 橋の端は、もう一方の端が決まってから求める（向きがなければ近い側、同名の遠い橋は除く）
        for i, e in enumerate(ends):
            if isinstance(e, tuple):
                other = ends[1 - i]
                near = roads.coord[other] if other and not isinstance(other, tuple) else None
                ends[i] = roads.bridge_end(e[1], names, near)
        line = roads.path(ends[0], ends[1], names) if all(ends) else None
        length = sum(dist(p, q) for p, q in zip(line, line[1:])) if line else 0
        out[r['id']] = {'line': line, 'how': notes, 'length_m': round(length)}
        print(f"{r['id']:14} {r['route'][:14]:14} {r['section'][:34]:34} {notes} {round(length)}m", flush=True)
    (SRC / 'geometry.json').write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding='utf-8')
    print(f"{sum(1 for v in out.values() if v['line'])}/{len(out)} lines -> {(SRC / 'geometry.json').relative_to(ROOT)}")


if __name__ == '__main__':
    cmd = sys.argv[1] if len(sys.argv) > 1 else ''
    if cmd == 'fetch':
        fetch()
    elif cmd == 'geometry' and len(sys.argv) > 2:
        geometry(sys.argv[2])
    else:
        print(__doc__)
