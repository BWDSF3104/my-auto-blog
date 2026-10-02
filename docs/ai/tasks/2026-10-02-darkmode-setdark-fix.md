# ダークモードトグルボタン動作復元 (setDark関数の引数修正)

**Status:** 完了
**Date:** 2026-10-02
**Commit:** 07e9804

## Objective

`setDark()` 関数内で未定義の変数 `dark` を参照していたバグを修正。

## Verification

- npm run build: 92 pages
- pytest: 134 passed
