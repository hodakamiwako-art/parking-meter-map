# パーキング・メーター・マップ / Tokyo Parking Meter Map

東京・大阪・札幌・京都のパーキング・メーター／パーキング・チケットの設置区間 **808区間**（東京752・大阪41・札幌10・京都5）を、地図と「近い順」の一覧で探せるウェブアプリです。

👉 **https://hodakamiwako-art.github.io/parking-meter-map/**

## できること

画面は**地図が主役**です。上に検索と「条件入力」ボタンがあり、右上のメニューから一覧を開けます。

- 設置区間を**線で地図に表示**。色は曜日で分け、**緑＝土日・祝日も使える／青＝日曜・祝日は除く**（うち9区間は土曜も除く）。メーターは実線、チケットは破線
- **地名・駅名で移動**（例：銀座、新宿駅）。国土地理院の地名検索を使っています
- **条件入力**：ふだんはボタンだけ。タップすると開き、次の順に選べます
  1. 都府県（札幌／東京／京都／大阪）→ 2. 区・市（選んだ都府県のものだけ）→ 3. 町名 → 4. 曜日（土日・祝日も使える／日曜・祝日は除く）→ 5. 時間帯（いま使える／◯:00 に使える）→ 6. 制限時間 → 7. 車種
  - 使っている条件の数をボタンに表示。「条件をクリア」で全部はずせます
  - 「いま使える」は曜日・祝日・正月まで判定します。祝日は `data/holidays.json`（2026〜2027年）で見ています
- **メニュー**：一覧で見る／札幌・東京・京都・大阪を表示／全体を表示／警視庁の地図
- **一覧**：「近い順」（現在地または地図の中心から）と「エリアごと」（見出しつき）を切り替え。選ぶと地図がその区間へ移ります
- 区間を選ぶと、住所・制限時間・料金・利用時間・除く日・いま使えるか・車種を表示し、**Googleマップで経路**を開ける
- スマホでは詳細が下からのシートで出て、選んだ区間はシートの上に見える位置へ寄せます。ダークテーマ対応

## データ

### 東京（752区間）

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

### 大阪（41区間）

大阪府警察「[パーキング・チケット発給設備設置状況](https://www.police.pref.osaka.lg.jp/kotsu/tyusya/1/1/index.html)」（12警察署）の表を使っています。
大阪はすべてパーキング・チケットで、手数料300円・同じ場所に続けて1時間までです（府警の案内による）。

府警は座標を公開しておらず、区間は「深里橋交差点から京町堀1丁目交差点まで」のように言葉で書かれています。
そこで `build/osaka.py` で、両端を OpenStreetMap の交差点名・橋・国土地理院の住所検索から求め、
その間を OSM の道路網でたどって線にしました。自動で決まらない・ずれる17区間の端点は、各署の設置地図（画像）と
OSM の道路を見比べて `MANUAL` に書いています。

⚠️ 大阪の線は府警の地図から起こしたもので、**枠の正確な位置（道路のどちら側か、交差点付近の切れ目など）までは表していません**。
現地の標識と枠線で確かめてください。大阪の線は OpenStreetMap から作っているため、© OpenStreetMap contributors（ODbL）です。

```bash
python3 build/osaka.py fetch                   # 府警のページから表を取り直す
python3 build/osaka.py geometry osaka.osm.pbf  # 線を作り直す（osaka.osm.pbf の作り方は osaka.py の冒頭）
python3 build/build.py --geocode               # 東京と合わせて data/zones.geojson を作る（新しい区間の住所も逆引き）
```

### 札幌（10か所）・京都（5か所）

北海道警察「[パーキング・チケット](https://www.police.pref.hokkaido.lg.jp/info/koutuu/p-ticket/p-ticket.html)」と
京都府警察「[パーキング・メーター、パーキング・チケット](https://www.pref.kyoto.jp/fukei/site/chutai_c/tiket_meter/)」の一覧を使っています。
どちらも「南1条西13丁目（札幌南一条病院西側）」「紫明通（烏丸通西入る南側）」のように目印で書かれているので、
`build/landmarks.py` で、OSM の建物の輪郭の指定の辺に面した道路（または交差点から指定の向き）に、枠数×6m の線を引いています。
一覧は `landmarks.py` の `REGIONS` に写してあり、県警のページが変わったら手で直します。

- 札幌の一般用8か所は **4月1日〜11月30日のみ**（冬期休止）。「いま使える」は冬期には外れます。丸井今井・三越の2か所は通年の**貨物車（積載量5トン未満）専用**です
- 札幌の「場所」は道警の住所をそのまま出しています
- ⚠️ 県警の地図がないため、線の中ほどは合っていても**端の位置は数十mずれうる**目安です

```bash
python3 build/landmarks.py sapporo sapporo.osm.pbf
python3 build/landmarks.py kyoto kyoto.osm.pbf
python3 build/build.py --geocode
```

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

- 区間データ（東京） — 警視庁 時間制限駐車区間案内地図 オープンデータ（CC BY 4.0）
- 区間データ（大阪） — 大阪府警察 パーキング・チケット発給設備設置状況。線は OpenStreetMap（ODbL）から作成
- 区間データ（札幌・京都） — 北海道警察・京都府警察の設置場所一覧。線は OpenStreetMap（ODbL）から作成
- 地名検索・住所の逆引き — [国土地理院](https://www.gsi.go.jp/)
- 祝日 — [内閣府「国民の祝日」](https://www8.cao.go.jp/chosei/shukujitsu/gaiyou.html)
- 地図タイル — OpenStreetMap contributors / CARTO

## ライセンス

コードは MIT。東京の区間データは CC BY 4.0（警視庁）、大阪・札幌・京都の区間の線と地図データは ODbL（OpenStreetMap）に従います。
