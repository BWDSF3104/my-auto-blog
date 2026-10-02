# 記事ページダークモードの文字色コントラスト改善

**Status:** 完了
**Date:** 2026-10-02
**Commit:** 1f611e5

## Objective

`PostLayout.astro` の `<article>` に `dark:prose-invert` + 各要素の `dark:` 変種クラスを追加。

## Verification

- npm run build: 92 pages
