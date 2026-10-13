# 検索画面で検索インデックスの読み込みに失敗

**Date**: 2026-10-04
**Status**: 解決済

dev モードで検索画面にアクセスすると「検索インデックスの読み込みに失敗しました」が表示。`generate-search-index.js` が `dist/search-index.json` に出力していたが、dev モードでは `dist/` が空のためフェッチ失敗。
- `scripts/generate-search-index.js` の出力先を `dist/` から `public/` に変更
- `package.json` の build スクリプトを `node scripts/generate-search-index.js && astro build` に順序変更（`public/` → `dist/` のコピー前にインデックスを生成）
- ビルド成功 (108ページ) を確認

---
*以下は 2026-10-06 に known-issues.md からアーカイブ*
