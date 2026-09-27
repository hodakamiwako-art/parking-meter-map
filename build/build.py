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
}
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
    cache = geocode(feats) if '--geocode' in sys.argv else (
        json.loads(GEOCODE.read_text(encoding='utf-8')) if GEOCODE.exists() else {})
    for f in feats:
        g = cache.get(str(f['id']))
        if g:
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
