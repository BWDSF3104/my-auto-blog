# ダークモードトグル不動作と記事ページダークモード未適用

**Date**: 2026-10-01
**Status**: 解決済

`Header.astro` の `<script>` に `is:inline` 属性を追加してダークモード切り替えを復元。`PostLayout.astro` に `Header` コンポーネントのインポート、`dark:` 変種クラス、ダークモードCSSを追加して記事ページのダークモード対応を完了。`tags/index.astro` の `<script>` にも `is:inline` を追加。ビルド成功 (90ページ) 確認済み。
