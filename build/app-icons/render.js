// アプリのアイコン（1024px）と起動画面（2732px）を作る。形は「時間制限駐車区間」の標識（パーキング・メーターの区間）にならう：
// 青い地に白い縁、上に時間「8-20」、まん中に大きな「P」、下に「60分」。起動画面は青の地に白いマークだけ。
// 使い方：PLAYWRIGHT=<playwright のパス> node build/app-icons/render.js。できた PNG は ios/App/App/Assets.xcassets に入る
const { chromium } = require(process.env.PLAYWRIGHT || 'playwright');
const path = require('path');
const out = path.join(__dirname, '..', '..', 'ios', 'App', 'App', 'Assets.xcassets');
const BLUE = '#1E4E8C';
const FONT = "'DejaVu Sans','IPAGothic','Hiragino Sans',sans-serif";

// 1024 の枠の標識（白い部分だけ）。数字は標識らしく少し細長く
const mark = () => `
  <rect x="64" y="64" width="896" height="896" rx="168" fill="none" stroke="#fff" stroke-width="24"/>
  <text transform="translate(512 268) scale(0.86 1)" text-anchor="middle" font-family="${FONT}" font-weight="700" font-size="132" letter-spacing="6" fill="#fff">8-20</text>
  <path d="M424 736V352h112a108 108 0 0 1 0 216H424" fill="none" stroke="#fff" stroke-width="84" stroke-linejoin="round"/>
  <text transform="translate(512 878) scale(0.9 1)" text-anchor="middle" font-family="${FONT}" font-weight="700" font-size="124" fill="#fff">60分</text>`;

const pages = {
  // アイコン：青の地いっぱいに標識。角丸なし・透明なし（iPhone が角を丸める）
  'AppIcon.appiconset/AppIcon-512@2x.png': [1024, `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1024 1024" width="1024" height="1024">
    <rect width="1024" height="1024" fill="${BLUE}"/>${mark()}</svg>`],
  // 起動画面：地いっぱいを標識の青（上から下へごく弱いグラデーション）にして、まん中に白い標識のマークだけ。
  // 縦長の画面で左右が切れても、まん中は残る
  'Splash.imageset/splash-2732x2732.png': [2732, `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 2732 2732" width="2732" height="2732">
    <defs><linearGradient id="g" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#22579B"/><stop offset="1" stop-color="#1A4478"/></linearGradient></defs>
    <rect width="2732" height="2732" fill="url(#g)"/>
    <g transform="translate(1156 1156) scale(0.4063)">${mark()}</g></svg>`],
};
(async () => {
  const b = await chromium.launch();
  for (const [file, [size, svg]] of Object.entries(pages)) {
    const p = await b.newPage({ viewport: { width: size, height: size }, deviceScaleFactor: 1 });
    await p.setContent(`<html><body style="margin:0">${svg}</body></html>`);
    await p.screenshot({ path: path.join(out, file) });
    await p.close();
  }
  await b.close();
})();
