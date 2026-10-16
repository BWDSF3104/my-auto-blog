# ダークモード修正: トグルボタン動作復元と記事ページのダークモード適用

**Status:** 完了
**Date:** 2026-10-02
**Commit:** d90ebe5

## Objective

`is:inline` 属性なしによりクライアントサイドスクリプトが動作しない問題を全ページで修正。記事ページに `dark:` クラスと `Header` コンポーネントを追加。

## Verification

- npm run build: 90 pages
