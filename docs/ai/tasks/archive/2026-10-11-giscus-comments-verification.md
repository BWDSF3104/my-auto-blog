# 2026-10-11: コメント機能（Giscus）— 最終検証と本番デプロイ

**Status**: 未着手
**担当**: AI（デプロイ・本番確認はユーザー承認を要する箇所あり）
**依存**: `github-setup`, `env-config`, `component`, `workflow-env`（全て完了）
**関連**: 本タスク完了で backlog の P2 エントリを削除

## 概要

4 タスク完了後、E2E で検証し本番デプロイする。

## 手順

1. `npm run build` が成功すること
2. `dist/posts/<slug>/index.html` を解析し、giscus script タグの `data-repo` / `data-repo-id` / `data-category` / `data-category-id` / `data-mapping` / `data-lang` / `data-loading` が正しいこと
3. `astro dev --background` でローカル確認:
   - コメント欄（iframe）が記事末尾に表示される
   - テーマ切替（light ↔ dark）でコメント欄のテーマが追従する（MutationObserver 同期）
   - `comments: false` の一時記事で非表示になること（確認後削除し再 build）
4. GitHub 側: 本番 URL の記事を開くと giscus bot が Discussion を自動作成すること（最初の投稿時）
5. **ユーザー確認**: 本番デプロイ前にデプロイを承認してもらう
6. コミット（`feat: 記事に Giscus コメント欄を追加`）+ push → `deploy.yml`（または `deploy-only.yml`）実行
7. 本番 `https://BWDSF3104.github.io/my-auto-blog/posts/<slug>` でコメント欄表示・投稿動作を確認
8. `src/pages/privacy.astro` に Giscus（GitHub Discussions 利用・GitHub アカウント必要・pathname 単位で Discussion が作られる）を記載（任意）
9. `docs/ai/current-task.md` の Verification にコマンド・結果・経過時間を記録
10. `plans.md` で Active Plans → Completed Plans に移動、`backlog.md` の P2 エントリを削除、本タスクファイルの Status を「完了」に更新

## 既知のリスク / トレードオフ

- 投稿には GitHub アカウント必須（匿名不可）— `decisions.md` 2026-10-11 参照
- slug リネームでコメントが引き継がれない（`slug-redirects.json` 使用時）
- giscus.app サービス / GitHub Discussions API の変更依存
- コメントデータは Discussions に紐づく（本リポジトリ外部のエクスポート API なし）

## Verification

- 上記手順 1〜7 が全て成功すること（手順 5 はユーザー承認）
- 本番 HTML に giscus script タグが出力されていること
- `docs/ai/current-task.md` に検証結果が記録されていること

## Next Action

- 完了後、backlog の P2 エントリ削除 + plans.md 更新 + 各タスクファイルの Status 更新
