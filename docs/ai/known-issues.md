# 既知問題リスト

進行中の問題のみを記録。解決済は `known-issues-archive.md` に移動する。

## 検索画面で「検索インデックスの読み込みに失敗しました」が表示される

**報告日**: 2026-10-04

**現象**:
- 検索画面 (`/my-auto-blog/search`) にアクセスすると「検索インデックスの読み込みに失敗しました。」が表示される
- コンソールに `Failed to load search index` エラーが出力される

**原因**:
- `search.astro` の JS は `{baseUrl}/search-index.json` をフェッチする
- `generate-search-index.js` は `dist/search-index.json` に出力する
- `npm run build` を実行すると `dist/` にインデックスが生成されるが、dev モードでは `dist/` が空
- dev サーバー起動時は検索インデックスが存在しないため読み込み失敗

**影響範囲**:
- dev モードでの検索機能のテストが不可能
- build 実行前にも検索機能が利用できない

**解決候補**:
1. `public/` ディレクトリに `search-index.json` を出力するように変更（dev・production 両対応）
2. `astro dev` 起動時に検索インデックスを生成する watcher を追加
3. `package.json` の dev スクリプトにインデックス生成を先行させる
