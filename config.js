/* 地図タイル（CARTO）の鍵。https://carto.com/basemaps/apikey/ で無料で取れます（アカウント不要、月500万タイルまで）。
   鍵は公開するドメインで縛られるので、このアプリの公開先に合わせて取り直してください。
   空のままだと OpenStreetMap のタイルを使います（ダークテーマでは反転して暗く見せます）。 */
window.PAWMAP_CONFIG = {
  cartoApiKey: '',
};
