# KI-002: ヒーローセクションの最新記事ボタンが記事一覧以外では動作しない

**Date**: 2026-10-05
**Status**: 解決済

- 発見日: 2026-10-05
- 症状: ヒーローセクションの「最新記事を読む」ボタンがトップページ以外で期待通りに動作しない
- 影響範囲: `Header.astro` のヒーローセクション
- 原因: `href="#main-content"` のアンカーリンク。`page/[page].astro` に `#main-content` が存在しない
- 修正: `href="#main-content"` → `href={baseUrl}` に変更 + `page/[page].astro` に `id="main-content"` を追加
- 修正完了: 2026-10-05, `Header.astro:167` + `page/[page].astro:126` を修正
