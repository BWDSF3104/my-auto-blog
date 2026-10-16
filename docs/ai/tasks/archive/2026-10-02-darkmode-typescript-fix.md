# ダークモードトグルボタン動作復元 (TypeScript型注釈削除)

**Status:** 完了
**Date:** 2026-10-02
**Commit:** 3232915

## Objective

`<script is:inline>` 内の TypeScript 型注釈 (`dark: boolean`) がブラウザで構文エラーを引き起こす問題を修正。

## Verification

- npm run build: 92 pages
- pytest: 134 passed
