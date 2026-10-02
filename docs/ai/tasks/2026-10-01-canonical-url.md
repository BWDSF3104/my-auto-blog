# canonical URL一貫性

**Status:** 完了
**Date:** 2026-10-01
**Commit:** 1b8a6d4

## Objective

slug変更時の301リダイレクト実装。

## Summary

`data/slug-redirects.json` で旧→新slugマッピングを記録。`[...slug].astro` の `getStaticPaths` にリダイレクトルートを追加。

## Verification

- pytest: 119 passed
- npm run build: 90 pages
