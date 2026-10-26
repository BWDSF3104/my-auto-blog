# 2026-10-11: コメント機能（Giscus）— デプロイワークフローへの環境変数配線

**Status**: 未着手
**担当**: AI
**依存**: なし（`vars.*` 参照は値が確定していなくても記述可能。反映は `env-config` 完了後）
**関連**: `tasks/2026-10-11-giscus-comments-verification.md`（本番反映確認）

## 概要

`deploy.yml` / `deploy-only.yml` の build ステップに `PUBLIC_GISCUS_*` 4 値を渡す。渡さないと本番ビルドで env が欠落し、コンポーネントが early return してコメント欄が静かに消える。

## 手順

`deploy.yml` と `deploy-only.yml` の **Build step** に `env:` ブロックを追加（`env-config` タスクで GitHub Variables として登録した 4 件を参照）:

```yaml
      - name: Build
        run: npm run build
        env:
          PUBLIC_GISCUS_REPO: ${{ vars.PUBLIC_GISCUS_REPO }}
          PUBLIC_GISCUS_REPO_ID: ${{ vars.PUBLIC_GISCUS_REPO_ID }}
          PUBLIC_GISCUS_CATEGORY: ${{ vars.PUBLIC_GISCUS_CATEGORY }}
          PUBLIC_GISCUS_CATEGORY_ID: ${{ vars.PUBLIC_GISCUS_CATEGORY_ID }}
```

- `deploy.yml`（generate step 付き）と `deploy-only.yml`（build のみ）の両方に同様の追加が必要
- 既存の `PUBLIC_BUYMEACOFFEE_USERNAME` 等はコード内フォールバックに依存しているため配線しない（変更範囲を Giscus に限定）

## Verification

- YAML 構文チェック（`yaml.safe_load` で両ファイルをパース）
- 本番反映確認は `verification` タスク（deploy-only ワークフロー実行後、本番 HTML に giscus script タグが存在すること）

## Next Action

- `component` / `env-config` との整合後、`verification` タスクへ
