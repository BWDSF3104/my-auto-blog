# ダークモード初期化スクリプトの全ページ投入

**Status:** 完了
**Date:** 2026-10-02
**Commit:** 7d80e61

## Objective

`ThemeInit.astro` 新規作成し、`PostLayout.astro` と各スタンドアロンページに `<ThemeInit />` を追加。`prefers-color-scheme` の自動検出と `localStorage` からのテーマ復元を全ページで有効化。

## Verification

- npm run build: 92 pages
- pytest: 134 passed
