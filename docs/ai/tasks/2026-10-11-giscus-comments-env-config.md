# 2026-10-11: コメント機能（Giscus）— 環境変数登録

**Status**: 未着手
**担当**: ユーザー（手動）
**依存**: `github-setup`（4 つの設定値の確定）
**関連**: `tasks/2026-10-11-giscus-comments-workflow-env.md`（CI 側配線）

## 概要

`PUBLIC_GISCUS_*` 4 値をローカル `.env` と GitHub リポジトリの Variables に登録する。**本タスクを実装しないと本番デプロイでコメント欄が表示されない**（現状 `deploy.yml` / `deploy-only.yml` の build ステップは `PUBLIC_*` 環境変数を一切渡していない。既存の `PUBLIC_BUYMEACOFFEE_USERNAME` 等は全てコード内フォールバックに依存している）。

`PUBLIC_GISCUS_REPO_ID` / `PUBLIC_GISCUS_CATEGORY_ID` は公開識別子であり機密ではない（生成される全ページ HTML に埋め込まれる値）。

## 手順

1. `github-setup` タスクの引き継ぎ情報から 4 値を確認
2. ローカル `.env`（git 管理外）に追記:
   ```
   PUBLIC_GISCUS_REPO=BWDSF3104/my-auto-blog
   PUBLIC_GISCUS_REPO_ID=<R_kgDO...>
   PUBLIC_GISCUS_CATEGORY=Comments
   PUBLIC_GISCUS_CATEGORY_ID=<DIC_kwDO...>
   ```
3. GitHub リポジトリ Settings → **Variables**（非機密）に同名 4 件を追加（secrets ではなく variables）

## Verification

- ローカルで `npm run build` 後、`dist/posts/<slug>/index.html` に `src="https://giscus.app/client.js"` の script タグが出力され、`data-repo` / `data-repo-id` / `data-category` / `data-category-id` が正しい値であること（component タスク完了後の確認）
- GitHub Variables に 4 件登録済みであること

## Next Action

- `component` / `workflow-env` タスクを並行着手可能
