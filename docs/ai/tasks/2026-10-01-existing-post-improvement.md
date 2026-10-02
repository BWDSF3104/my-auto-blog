# 既存記事の見栄え改善（モバイル対応含む）

**Status:** 完了
**Date:** 2026-10-01
**Commit:** dd356fe

## Objective

index.astro, tags/index.astro, tags/[tag].astro のインラインCSSをTailwindへ統一。共通 Header/Footer コンポーネント作成。

## Summary

ページネーション、タグ検索、ダークモード、404ページ、Aboutページ、読了時間表示を追加。

## Verification

- npm run build: 85 pages
