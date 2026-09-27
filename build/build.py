"""警視庁の時間制限駐車区間オープンデータから data/zones.geojson を作る。

    python3 build/build.py            # build/source/ にある元データから作る
    python3 build/build.py --fetch    # 先に parking-meter.jp から最新版を取り直す

線の形は KML（parkingmeter.kml.zip）、属性は CSV（parkingmeter_attr.csv）から取る。
CSV のほうが更新が新しいので、同じ識別idでは CSV の値を優先する。
（GeoJSON 版の zip はダウンロードページにあるが、2026年9月時点でリンク切れ）
"""
import csv, io, json, sys, urllib.request, zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / 'build' / 'source'
OUT = ROOT / 'data' / 'zones.geojson'
BASE = 'https://parking-meter.jp/'
FILES = ['parkingmeter.kml.zip', 'parkingmeter_attr.csv']
NS = {'k': 'http://www.opengis.net/kml/2.2'}
INTS = {'識別id', '制限時間', '手数料', '普通車', '貨物用有り', '二輪車', '標章車専用有り'}


def fetch():
    for f in FILES:
        with urllib.request.urlopen(BASE + f) as r:
            (SRC / f).write_bytes(r.read())
        print('fetched', f)


def value(k, v):
    v = (v or '').strip()
    if k in INTS and v.lstrip('-').isdigit():
        return int(v)
    return v


def main():
    if '--fetch' in sys.argv:
        fetch()
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
        feats.append({'type': 'Feature', 'id': props['識別id'], 'properties': props, 'geometry': geom})

    feats.sort(key=lambda f: f['id'])
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps({'type': 'FeatureCollection', 'features': feats},
                              ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
    missing = set(attrs) - {str(f['id']) for f in feats}
    print(f'{len(feats)} zones -> {OUT.relative_to(ROOT)}' + (f' ({len(missing)} ids in CSV without geometry)' if missing else ''))


if __name__ == '__main__':
    main()
