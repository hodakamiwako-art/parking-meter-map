"""警視庁の時間制限駐車区間オープンデータから data/zones.geojson を作る。

    python3 build/build.py            # build/source/ にある元データから作る
    python3 build/build.py --fetch    # 先に parking-meter.jp から最新版を取り直す
    python3 build/build.py --geocode  # 住所がまだない区間を国土地理院で逆引きしてから作る
    python3 build/build.py --holidays # 内閣府の祝日一覧から data/holidays.json を作り直す

線の形は KML（parkingmeter.kml.zip）、属性は CSV（parkingmeter_attr.csv）から取る。
CSV のほうが更新が新しいので、同じ識別idでは CSV の値を優先する。
（GeoJSON 版の zip はダウンロードページにあるが、2026年9月時点でリンク切れ）

元データには区間名も住所もないので、線のまん中の点を国土地理院の逆引きにかけ、
「区市町村」「町名」「町丁目」を属性に足す。結果は build/source/geocode.json に貯めておき、
新しく増えた区間だけ問い合わせる。
"""
import csv, io, json, re, sys, time, urllib.request, zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / 'build' / 'source'
OUT = ROOT / 'data' / 'zones.geojson'
BASE = 'https://parking-meter.jp/'
FILES = ['parkingmeter.kml.zip', 'parkingmeter_attr.csv']
NS = {'k': 'http://www.opengis.net/kml/2.2'}
HOLIDAYS = ROOT / 'data' / 'holidays.json'
HOLIDAYS_CSV = 'https://www8.cao.go.jp/chosei/shukujitsu/syukujitsu.csv'
GEOCODE = SRC / 'geocode.json'
REVERSE = 'https://mreversegeocoder.gsi.go.jp/reverse-geocoder/LonLatToAddress?lat={lat}&lon={lng}'
# 逆引きは市区町村コードで返るので、都内の区市の名前を引く
MUNI = {
    13101: '千代田区', 13102: '中央区', 13103: '港区', 13104: '新宿区', 13105: '文京区', 13106: '台東区',
    13107: '墨田区', 13108: '江東区', 13109: '品川区', 13110: '目黒区', 13111: '大田区', 13112: '世田谷区',
    13113: '渋谷区', 13114: '中野区', 13115: '杉並区', 13116: '豊島区', 13117: '北区', 13118: '荒川区',
    13119: '板橋区', 13120: '練馬区', 13121: '足立区', 13122: '葛飾区', 13123: '江戸川区',
    13201: '八王子市', 13202: '立川市', 13203: '武蔵野市', 13204: '三鷹市', 13205: '青梅市', 13206: '府中市',
    13207: '昭島市', 13208: '調布市', 13209: '町田市', 13210: '小金井市', 13211: '小平市', 13212: '日野市',
    13213: '東村山市', 13214: '国分寺市', 13215: '国立市', 13218: '福生市', 13219: '狛江市', 13220: '東大和市',
    13221: '清瀬市', 13222: '東久留米市', 13223: '武蔵村山市', 13224: '多摩市', 13225: '稲城市', 13227: '羽村市',
    13228: 'あきる野市', 13229: '西東京市',
    # 大阪（東京の中央区・北区と区別するため「大阪市」を付ける）
    27102: '大阪市都島区', 27103: '大阪市福島区', 27104: '大阪市此花区', 27106: '大阪市西区', 27107: '大阪市港区',
    27108: '大阪市大正区', 27109: '大阪市天王寺区', 27111: '大阪市浪速区', 27113: '大阪市西淀川区', 27114: '大阪市東淀川区',
    27115: '大阪市東成区', 27116: '大阪市生野区', 27117: '大阪市旭区', 27118: '大阪市城東区', 27119: '大阪市阿倍野区',
    27120: '大阪市住吉区', 27121: '大阪市東住吉区', 27122: '大阪市西成区', 27123: '大阪市淀川区', 27124: '大阪市鶴見区',
    27125: '大阪市住之江区', 27126: '大阪市平野区', 27127: '大阪市北区', 27128: '大阪市中央区',
    27205: '吹田市', 27227: '東大阪市',
    # 札幌・京都（区名がほかの市と重なるので市名を付ける）
    1101: '札幌市中央区', 1102: '札幌市北区', 1103: '札幌市東区', 1104: '札幌市白石区', 1105: '札幌市豊平区',
    1106: '札幌市南区', 1107: '札幌市西区', 1108: '札幌市厚別区', 1109: '札幌市手稲区', 1110: '札幌市清田区',
    26101: '京都市北区', 26102: '京都市上京区', 26103: '京都市左京区', 26104: '京都市中京区', 26105: '京都市東山区',
    26106: '京都市下京区', 26107: '京都市南区', 26108: '京都市右京区', 26109: '京都市伏見区', 26110: '京都市山科区',
    26111: '京都市西京区',
    14101: '横浜市鶴見区', 14102: '横浜市神奈川区', 14103: '横浜市西区', 14104: '横浜市中区', 14105: '横浜市南区',
    14106: '横浜市保土ケ谷区', 14107: '横浜市磯子区', 14111: '横浜市港南区', 14115: '横浜市栄区', 14133: '川崎市中原区',
    14136: '川崎市宮前区', 14203: '平塚市', 14205: '藤沢市',
}
OSAKA = SRC / 'osaka'
INTS = {'識別id', '制限時間', '手数料', '普通車', '貨物用有り', '二輪車', '標章車専用有り'}


def fetch():
    for f in FILES:
        with urllib.request.urlopen(BASE + f) as r:
            (SRC / f).write_bytes(r.read())
        print('fetched', f)


def midpoint(lines):
    """線のまん中あたりの点 [lng, lat]（zones.js の midpoint と同じ選び方）"""
    longest = max(lines, key=len)
    return longest[len(longest) // 2]


def town(chome):
    """「銀座四丁目」→「銀座」。丁目がなければそのまま"""
    return re.sub(r'[一二三四五六七八九十]+丁目$', '', chome)


def geocode(feats):
    cache = json.loads(GEOCODE.read_text(encoding='utf-8')) if GEOCODE.exists() else {}
    todo = [f for f in feats if str(f['id']) not in cache]
    for i, f in enumerate(todo, 1):
        lng, lat = midpoint(f['_lines'])
        with urllib.request.urlopen(REVERSE.format(lat=lat, lng=lng), timeout=20) as r:
            res = json.load(r).get('results') or {}
        cache[str(f['id'])] = {'muniCd': res.get('muniCd', ''), 'lv01Nm': res.get('lv01Nm', '')}
        if i % 50 == 0 or i == len(todo):
            print(f'geocoded {i}/{len(todo)}')
            GEOCODE.write_text(json.dumps(cache, ensure_ascii=False, indent=0, sort_keys=True), encoding='utf-8')
        time.sleep(0.2)  # 国土地理院に負担をかけない
    return cache


def holidays():
    """「日曜・休日を除く」区間の判定に使う祝日一覧。今年以降の分だけ残す"""
    with urllib.request.urlopen(HOLIDAYS_CSV, timeout=20) as r:
        text = r.read().decode('cp932')
    this_year = time.localtime().tm_year
    dates = {}
    for line in text.splitlines()[1:]:
        d, _, name = line.partition(',')
        y, m, dd = (int(x) for x in d.split('/'))
        if y >= this_year:
            dates[f'{y:04d}-{m:02d}-{dd:02d}'] = name.strip()
    years = sorted({int(d[:4]) for d in dates})
    HOLIDAYS.write_text(json.dumps({'source': '内閣府「国民の祝日」（build/build.py --holidays で取り直せます）',
                                    'years': years, 'dates': dates}, ensure_ascii=False, indent=1), encoding='utf-8')
    print(f'{len(dates)} holidays ({years[0]}-{years[-1]}) -> {HOLIDAYS.relative_to(ROOT)}')


def value(k, v):
    v = (v or '').strip()
    if k in INTS and v.lstrip('-').isdigit():
        return int(v)
    return v


def osaka_features():
    """build/osaka.py が作った表（rows.json）と線（geometry.json）を、東京と同じ属性名の区間にする"""
    rows_f, geo_f = OSAKA / 'rows.json', OSAKA / 'geometry.json'
    if not (rows_f.exists() and geo_f.exists()):
        return []
    geo = json.loads(geo_f.read_text(encoding='utf-8'))
    feats = []
    for r in json.loads(rows_f.read_text(encoding='utf-8')):
        line = (geo.get(r['id']) or {}).get('line')
        if not line:
            print('osaka: no line for', r['id'], r['route'], r['section'])
            continue
        h = re.match(r'(\d+)\s*-\s*(\d+)', r['hours'])
        props = {
            '識別id': r['id'], '都道府県': '大阪府',
            '利用時間': f'{int(h.group(1)):02d}:00-{int(h.group(2)):02d}:00' if h else r['hours'],
            # 大阪府警の案内：手数料300円、同じ場所に続けて1時間まで
            '制限時間': 60, '手数料': 300,
            '制限事項1': '日曜・休日を除く' if r['weekday_only'] else '', '制限事項2': '',
            '種別': 'パーキング・チケット', '普通車': 1,
            '貨物用有り': int(bool(r['truck_spaces'] or r['truck_mark'])), '二輪車': 0, '標章車専用有り': 0,
            '路線名': r['route'], '設置区間': r['section'], '駐車枠数': r['spaces'], '貨物車枠数': r['truck_spaces'],
            '出典': f"大阪府警察 {r['station']}（{r['asof']}）",
        }
        coords = [[round(x, 6), round(y, 6)] for x, y in line]
        feats.append({'type': 'Feature', 'id': r['id'], 'properties': props,
                      'geometry': {'type': 'LineString', 'coordinates': coords}, '_lines': [coords]})
    return feats


def landmark_features():
    """build/landmarks.py の地域（札幌・京都）を、東京と同じ属性名の区間にする"""
    sys.path.insert(0, str(ROOT / 'build'))
    from landmarks import REGIONS
    feats = []
    for region, cfg in REGIONS.items():
        geo_f = SRC / region / 'geometry.json'
        if not geo_f.exists():
            continue
        geo = json.loads(geo_f.read_text(encoding='utf-8'))
        for it in cfg['items']:
            line = (geo.get(it['id']) or {}).get('line')
            if not line or len(line) < 2:
                print(f'{region}: no line for', it['id'])
                continue
            props = {'識別id': it['id'], '都道府県': cfg['pref'], **cfg['common'],
                     '普通車': 0 if it.get('truck_only') else 1, '貨物用有り': int(bool(it.get('truck_only'))),
                     '二輪車': 0, '標章車専用有り': 0, '出典': cfg['source']}
            props.setdefault('種別', it.get('種別'))
            if it.get('種別'):
                props['種別'] = it['種別']
            if it.get('hours'):
                props['利用時間'] = it['hours']
            if it.get('label'):
                props['設置区間'] = it['label']
            elif it.get('mark'):
                props['設置区間'] = f"{it['addr'].replace('札幌市中央区', '')}（{it['mark']}の{ {'west': '西', 'east': '東', 'north': '北', 'south': '南'}[it['side']] }側）"
            props['駐車枠数'] = it['spaces']
            # 住所が書かれている地域（札幌）は、逆引きではなく県警の住所をそのまま使う
            # （線が街区の境の道路上にあるので、逆引きだと隣の街区になることがある）
            m = re.match(r'(.+?市.+?区)(.+)', it.get('addr', ''))
            if m:
                props.update({'区市町村': m.group(1), '町名': re.sub(r'\d+丁目$', '', m.group(2)), '町丁目': m.group(2)})
            if it.get('truck_only'):
                props['貨物車専用'] = 1
            if it.get('season') == '4-11':
                props['制限事項2'] = '12月1日〜3月31日は休止'
                props['運用月'] = '4-11'
            coords = [[round(x, 6), round(y, 6)] for x, y in line]
            feats.append({'type': 'Feature', 'id': it['id'], 'properties': props,
                          'geometry': {'type': 'LineString', 'coordinates': coords}, '_lines': [coords]})
    return feats


def kanagawa_features():
    """build/kanagawa.py が作った線を区間にする。県警が時間帯・曜日を公開していないので「不明」とする"""
    geo_f = SRC / 'kanagawa' / 'geometry.json'
    if not geo_f.exists():
        return []
    feats = []
    for sid, v in json.loads(geo_f.read_text(encoding='utf-8')).items():
        if not v.get('line') or len(v['line']) < 2:
            print('kanagawa: no line for', sid)
            continue
        props = {'識別id': sid, '都道府県': '神奈川県', '利用時間': '', '制限時間': 60, '手数料': 300,
                 '制限事項1': '', '制限事項2': '', '曜日不明': 1,
                 '種別': 'パーキング・メーター' if v['kind'] == 'meter' else 'パーキング・チケット',
                 '普通車': 1, '貨物用有り': int(v['truck']), '二輪車': 0, '標章車専用有り': 0,
                 '設置区間': f"{v['area']}：{v['note']}", '出典': f"神奈川県警察 {v['station']}（パーキング・メーター等の設置場所）"}
        coords = [[round(x, 6), round(y, 6)] for x, y in v['line']]
        feats.append({'type': 'Feature', 'id': sid, 'properties': props,
                      'geometry': {'type': 'LineString', 'coordinates': coords}, '_lines': [coords]})
    return feats


def main():
    if '--fetch' in sys.argv:
        fetch()
    if '--holidays' in sys.argv:
        holidays()
    with zipfile.ZipFile(SRC / 'parkingmeter.kml.zip') as z:
        name = next(n for n in z.namelist() if n.endswith('.kml'))
        root = ET.fromstring(z.read(name))
    attrs = {}
    with open(SRC / 'parkingmeter_attr.csv', encoding='utf-8-sig') as f:
        for row in csv.DictReader(f):
            attrs[row['識別id']] = {k: value(k, v) for k, v in row.items()}

    feats = []
    for pm in root.iter('{%s}Placemark' % NS['k']):
        props = {d.get('name'): value(d.get('name'), d.text) for d in pm.iter('{%s}SimpleData' % NS['k'])}
        props.update(attrs.get(str(props.get('識別id')), {}))
        lines = []
        for ls in pm.iter('{%s}LineString' % NS['k']):
            pts = [c.split(',') for c in ls.find('k:coordinates', NS).text.split()]
            lines.append([[round(float(x), 6), round(float(y), 6)] for x, y, *_ in pts])
        if not lines:
            continue
        geom = ({'type': 'LineString', 'coordinates': lines[0]} if len(lines) == 1
                else {'type': 'MultiLineString', 'coordinates': lines})
        feats.append({'type': 'Feature', 'id': props['識別id'], 'properties': props, 'geometry': geom, '_lines': lines})

    feats.sort(key=lambda f: f['id'])
    for f in feats:
        f['properties']['都道府県'] = '東京都'
    feats += osaka_features()
    feats += landmark_features()
    feats += kanagawa_features()
    cache = geocode(feats) if '--geocode' in sys.argv else (
        json.loads(GEOCODE.read_text(encoding='utf-8')) if GEOCODE.exists() else {})
    for f in feats:
        g = cache.get(str(f['id']))
        if g and not f['properties'].get('区市町村'):
            chome = '' if g['lv01Nm'] in ('', '－') else g['lv01Nm']
            f['properties'].update({'区市町村': MUNI.get(int(g['muniCd'] or 0), ''), '町名': town(chome), '町丁目': chome})
        del f['_lines']
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps({'type': 'FeatureCollection', 'features': feats},
                              ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
    missing = set(attrs) - {str(f['id']) for f in feats}
    print(f'{len(feats)} zones -> {OUT.relative_to(ROOT)}' + (f' ({len(missing)} ids in CSV without geometry)' if missing else ''))
    noaddr = sum(1 for f in feats if not f['properties'].get('区市町村'))
    if noaddr:
        print(f'{noaddr} zones without address (run with --geocode)')


if __name__ == '__main__':
    main()
