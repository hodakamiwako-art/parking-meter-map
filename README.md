# パーキング・メーター・マップ / Tokyo Parking Meter Map

東京都内のパーキング・メーター（青）とパーキング・チケット（緑）の設置区間 **752区間** を、地図と「近い順」の一覧で探せるウェブアプリです。

👉 **https://hodakamiwako-art.github.io/parking-meter-map/**

## できること

画面は**地図が主役**です。上に検索と「条件入力」ボタンがあり、右上のメニューから一覧を開けます。

- 設置区間を**線で地図に表示**。色は曜日で分け、**緑＝土日・祝日も使える／青＝日曜・祝日は除く**（うち9区間は土曜も除く）。メーターは実線、チケットは破線
- **地名・駅名で移動**（例：銀座、新宿駅）。国土地理院の地名検索を使っています
- **条件入力**：ふだんはボタンだけ。タップすると開き、次の順に選べます
  1. 区 → 2. 町名 → 3. 曜日（土日・祝日も使える／日曜・祝日は除く）→ 4. 時間帯（いま使える／◯:00 に使える）→ 5. 制限時間 → 6. 車種
  - 使っている条件の数をボタンに表示。「条件をクリア」で全部はずせます
  - 「いま使える」は曜日・祝日・正月まで判定します。祝日は `data/holidays.json`（2026〜2027年）で見ています
- **メニュー**：一覧で見る／全体を表示／警視庁の地図
- **一覧**：「近い順」（現在地または地図の中心から）と「エリアごと」（見出しつき）を切り替え。選ぶと地図がその区間へ移ります
- 区間を選ぶと、住所・制限時間・料金・利用時間・除く日・いま使えるか・車種を表示し、**Googleマップで経路**を開ける
- スマホでは詳細が下からのシートで出て、選んだ区間はシートの上に見える位置へ寄せます。ダークテーマ対応

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
python3 build/build.py --holidays   # 内閣府の祝日一覧から data/holidays.json を作り直す（年に一度）
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
data/holidays.json  祝日一覧（「いま使える」の判定に使う）
build/            データを作るスクリプトと元データ
vendor/           Leaflet 1.9.4
```

画面のファイル（`*.css` / `*.js`）を変えたら、コミット前に `python3 build/stamp.py` を実行してください。
`index.html` の読み込み先に中身から作った版番号（`?v=…`）が付き、公開後に古いファイルが混ざらなくなります。
（GitHub Pages はファイルを10分間キャッシュさせるので、更新直後は再読み込みが必要なことがあります）

ビルド不要の静的サイトです。`python3 -m http.server 4173` を実行し、http://localhost:4173/ を開きます。

## 地図の下地について

`config.js` の `cartoApiKey` が空のときは OpenStreetMap のタイルを使います（明るい配色のみ）。
[carto.com/basemaps/apikey](https://carto.com/basemaps/apikey/) で公開ドメイン用の無料の鍵を取って入れると、
ダークテーマに追従する CARTO のタイルに切り替わります。

## 出典

- 区間データ — 警視庁 時間制限駐車区間案内地図 オープンデータ（CC BY 4.0）
- 地名検索・住所の逆引き — [国土地理院](https://www.gsi.go.jp/)
- 祝日 — [内閣府「国民の祝日」](https://www8.cao.go.jp/chosei/shukujitsu/gaiyou.html)
- 地図タイル — OpenStreetMap contributors / CARTO

## ライセンス

コードは MIT。区間データは CC BY 4.0（警視庁）、地図データは ODbL（OpenStreetMap）に従います。
