# コメント機能は Giscus（GitHub Discussions バックエンド）を採用

**Date**: 2026-10-11

**Decision**: Giscus（クライアントサイド iframe）を採用。`PostLayout.astro` 記事末尾に組み込み、frontmatter `comments: false` で記事単位無効化。`data-mapping="pathname"` で開発・本番同一 Discussion。テーマ同期は MutationObserver。env 4 値欠落時は early return で非表示。

**Reason**: 静的サイト（GitHub Pages）+ バックエンド/DB なしの設計哲学と整合。無料・広告なし・スパム抑制（GitHub OAuth 必須）で AI 自動生成記事に有効。セルフホスト型は常時稼働サーバーを新規追加するため矛盾。
