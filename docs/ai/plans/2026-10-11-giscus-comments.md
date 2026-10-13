# コメント機能（Giscus）実装

**Date**: 2026-10-11
**Status**: 進行中
**Backlog**: P2 #4

静的サイト（GitHub Pages）+ バックエンド/DB/SSR なしの前提から、コメントに Giscus（GitHub Discussions バックエンド・クライアントサイド iframe）を採用。`data-mapping="pathname"`（base `/my-auto-blog` で開発・本番の pathname が一致し同一 Discussion 共有）、テーマ同期は MutationObserver で `data-theme` 更新（`Header.astro` 無変更）、記事単位無効化は frontmatter `comments: false`、env 欠落時は early return でセクション非表示。`deploy.yml` / `deploy-only.yml` は `vars.PUBLIC_GISCUS_*`（4 値）で配線。

タスクファイル 5 件: `tasks/2026-10-11-giscus-comments-github-setup.md`（手動: Discussions 有効化 + giscus app 導入）、`tasks/2026-10-11-giscus-comments-env-config.md`（手動: 環境変数登録）、`tasks/2026-10-11-giscus-comments-component.md`（AI: `GiscusComments.astro` + Layout 組み込み + `content.config.ts`）、`tasks/2026-10-11-giscus-comments-workflow-env.md`（AI: ワークフロー env 配線）、`tasks/2026-10-11-giscus-comments-verification.md`（AI: E2E 検証 + 本番デプロイ）。

選定理由: `decisions/2026-10-11-giscus-comments.md`。
