# ページネーション修復と画像サイズ復元

**Status:** 完了
**Date:** 2026-10-01
**Commit:** b996bf2

## Objective

/page/2 以降のルーティングを復元し、記事一覧の画像サイズを元の 180×120px に戻す。

## Verification

- npm run build: 89 pages
- pytest: 96 passed
