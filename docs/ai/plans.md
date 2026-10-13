# Plans

実装開始前の計画と方針を記録する。完了後は下部の Completed Plans に意図と背景を記録する。

# Active Plans

- [2026-10-11] コメント機能（Giscus）実装: 静的サイト（GitHub Pages）+ バックエンド/DB/SSR なしの前提から、コメントに Giscus（GitHub Discussions バックエンド・クライアントサイド iframe）を採用。`data-mapping="pathname"`（base `/my-auto-blog` で開発・本番の pathname が一致し同一 Discussion 共有）、テーマ同期は MutationObserver で `data-theme` 更新（`Header.astro` 無変更）、記事単位無効化は frontmatter `comments: false`、env 欠落時は early return でセクション非表示。`deploy.yml` / `deploy-only.yml` は `vars.PUBLIC_GISCUS_*`（4 値）で配線。タスクファイル 5 件: `tasks/2026-10-11-giscus-comments-github-setup.md`（手動: Discussions 有効化 + giscus app 導入）、`tasks/2026-10-11-giscus-comments-env-config.md`（手動: 環境変数登録）、`tasks/2026-10-11-giscus-comments-component.md`（AI: `GiscusComments.astro` + Layout 組み込み + `content.config.ts`）、`tasks/2026-10-11-giscus-comments-workflow-env.md`（AI: ワークフロー env 配線）、`tasks/2026-10-11-giscus-comments-verification.md`（AI: E2E 検証 + 本番デプロイ）。選定理由: `decisions.md` 2026-10-11。バックログ: P2 #4

# Completed Plans

- [2026-10-13] safe-rmdir アローリスト緩和: プロジェクト内全フォルダ削除許可、拒否リストガード（.git / .kilo / ルート / シンボリックリンク / プロジェクト外）維持。詳細: `tasks/2026-10-13-safe-rmdir-relaxation.md`
- [2026-10-13] コマンド承認方式の最適化: permission.bash 再構築（フォールバック ask 先頭 → allow 中段 → 破壊的操作 ask 後段、365→98 エントリ）、行動ルールは AGENTS.md へ分離、6パターン allow 化。詳細: `tasks/2026-10-13-command-approval-optimization.md`
- [2026-10-11] Pythonスクリプトリファクタリング: `generate_article.py` → `article/` パッケージ分割 + `generate_post()` 8ステージ分解。等価性検証（A/Bリプレイ）PASS。詳細: `tasks/2026-10-11-python-refactor-package-split.md`
- [2026-10-11] README 全面書き換え: Astro Starter 既定→プロジェクト説明（生成フロー・技術スタック・CI/CD）。機微情報排除確認済み。詳細: `tasks/2026-10-11-readme-rewrite.md`
- [2026-10-11] e621 生成情報: キャラ特徴（参考キャラ2投稿・版権・artist）を kemono_story 限定で表示。同一選出データ保証。詳細: `tasks/2026-10-11-e621-generation-info.md`
- [2026-10-11] UTF-8 BOM 除去: 旧記事30件+1件の BOM 除去（CRLF維持）+ 旧 worktree 削除。詳細: `tasks/2026-10-11-utf8-encoding-audit.md`


完了した計画は git の変更履歴と重複せず、「なぜ変えたか」の文脈のみを記録する。ハッシュは参照用。
新しいエントリは常に上部に追加（prepend）。並び順=追加順=コミット順。
古い計画は `plans-archive.md` に移動する。
