# パーキングメーター地図 / Tokyo Parking Meter Map

東京都内のパーキング・メーター（青）とパーキング・チケット（緑）の設置区間 **752区間** を、地図と「近い順」の一覧で探せるウェブアプリです。

👉 **https://hodakamiwako-art.github.io/parking-meter-map/**

## できること

- 設置区間を**線で地図に表示**（メーター＝青、チケット＝緑。警視庁の地図と同じ色分け）
- **現在地から近い順**に一覧表示（現在地を使わないときは地図の中心から近い順）
- **地名・駅名で移動**（例：銀座、新宿駅）。国土地理院の地名検索を使っています
- **エリア（区市町村 → 町名）で絞り込み**。一覧は「近い順」と「エリアごと」（見出しつき）で切り替え
- 種類（メーター／チケット）、制限時間（20分・40分まで）、車種（貨物用あり・二輪車）で絞り込み
- **いま利用時間内の区間だけ**に絞り込み（曜日と正月は判定。祝日は判定しません）
- 区間を選ぶと、住所（国土地理院の逆引き）・制限時間・料金・利用時間・除く日・車種を表示し、**Googleマップで経路**を開ける
- スマホでは「一覧」「地図」をタブで切り替え。ダークテーマ対応

## データ

警視庁「[時間制限駐車区間案内地図](https://parking-meter.jp/)」の[オープンデータ](https://parking-meter.jp/open-data)を使っています（[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/deed.ja)）。

| 項目 | 内容 |
|---|---|
| 区間数 | 752（メーター634・チケット118） |
| 属性 | 利用時間・制限時間・手数料・制限事項・種別・車種 |
| 属性の更新日 | 2026年4月1日（CSV） |
| 線の形 | 2025年10月1日版（KML） |

**区間の名前や住所は元データに入っていません。** そこで `build/build.py --geocode` で各区間の線のまん中の点を
国土地理院の逆引きにかけ、「区市町村」「町名」「町丁目」を足しています（結果は `build/source/geocode.json` に保存）。
住所のない区間は、詳細を開いたときにその場で逆引きします。

⚠️ 現地の標識・メーターの表示が優先されます。利用時間外は駐車できないことがあり、工事や行事で使えない場合もあります。

### データの更新

```bash
python3 build/build.py --fetch --geocode   # 取り直して、新しい区間の住所を逆引きしてから作る
python3 build/build.py --fetch   # parking-meter.jp から取り直して data/zones.geojson を作る
python3 build/build.py           # build/source/ の手元の元データから作り直す
```

線の形は KML、属性は CSV から取ります（同じ識別idでは更新が新しい CSV を優先）。
ダウンロードページには GeoJSON 版もありますが、2026年9月時点でリンク切れのため KML を使っています。

## 構成

```
index.html        画面
app.js            アプリ本体（Leaflet）
zones.js          GeoJSON をアプリの形にそろえる
styles.css        スタイル（ライト／ダーク対応）
config.js         地図タイル（CARTO）の鍵。空なら OpenStreetMap
data/zones.geojson  752区間（build/build.py が作る）
build/            データを作るスクリプトと元データ
vendor/           Leaflet 1.9.4
```

ビルド不要の静的サイトです。`python3 -m http.server 4173` を実行し、http://localhost:4173/ を開きます。

## 地図の下地について

`config.js` の `cartoApiKey` が空のときは OpenStreetMap のタイルを使います（明るい配色のみ）。
[carto.com/basemaps/apikey](https://carto.com/basemaps/apikey/) で公開ドメイン用の無料の鍵を取って入れると、
ダークテーマに追従する CARTO のタイルに切り替わります。

## 出典

- 区間データ — 警視庁 時間制限駐車区間案内地図 オープンデータ（CC BY 4.0）
- 地名検索・住所の逆引き — [国土地理院](https://www.gsi.go.jp/)
- 地図タイル — OpenStreetMap contributors / CARTO

## ライセンス

コードは MIT。区間データは CC BY 4.0（警視庁）、地図データは ODbL（OpenStreetMap）に従います。
