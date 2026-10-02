# 記事一覧の画像サイズ修正（モバイル対応）

**Status:** 完了
**Date:** 2026-10-01
**Commit:** 8c6b844, d52b445, 23fb19e

## Objective

記事一覧の画像が横幅一杯に広がる問題を修正。Tailwind CSS がページに注入されない問題を調査・修正。

## Verification

- npm run build: 89 pages
- pytest: 96 passed
