# ワークフロー

## Git Workflow

`git commit`と`git push`は不可分な一連の作業。commit完了直後は**必ず**`git push`を実行すること。pushを中断してはならない。

**コミット実行前に必ず以下の手順を完了すること:**

1. `git fetch origin` — remote refsを取得
2. `git rev-list HEAD..origin/main --count` — remoteの新しいコミット数をカウント
3. カウント > 0 の場合: `git stash` → `git pull` → `git stash pop` → 競合解決
4. `git add` → `git commit` → `git push`を続けて実行

Commit message format: `feat: <日本語説明>` for features, `fix: <日本語説明>` for bug fixes.
Never use `git push --force` or modify remote history.

## Commit Checklist

git push 前に以下の確認を行う:

- [ ] 編集したファイルの内容を `git diff` で確認（hex 解析・codepoint 検証は不要）
- [ ] Pythonファイルを変更した場合はテストが全件通過したか (`pytest scripts/tests/ -v`)
- [ ] Astroファイルを変更した場合はビルドが成功したか (`npm run build`)
- [ ] 完了した計画が `plans.md` の「完了した計画」に記録されたか
- [ ] 新規問題が `known-issues.md` に記録されたか
- [ ] 解決した問題が `known-issues.md` の Archive へ移動されたか
- [ ] 完了したバックログ項目が `backlog.md` から削除されたか

## Deploy Verification

git push 後、DeployOnly ワークフローが push トリガーで自動実行されたことを確認:

1. `gh run list --workflow=deploy-only.yml --limit 5` — 直近の実行履歴を確認
2. 最新の push トリガー実行が `success` であることを確認
3. 失敗時は原因を調査して修正を継続

手動実行 (`gh workflow run`) はしない。push 自動トリガーに依存する。

例外（deploy verificationが不要）:

- 変更されたファイルがワークフローの paths (`src/**`, `public/**`, `package.json`, `astro.config.mjs`, `tailwind.config.mjs`) に一致しない場合
- コミットメッセージに `[skip ci]` または `[skip deploy]` を含む場合

## GitHub Actions ワークフロー実テスト

機能変更後のワークフローEnd-to-Endテスト手順。

詳細: `docs/ai/workflow-test-procedure.md`

## デバッグ（DebugMCP）

Python スクリプト（`scripts/`）のランタイムバグ調査・変数確認・ステップ実行。`debugmcp_*` MCP ツールで VS Code デバッガを制御。

- **基本**: ブレークポイント方式でデバッグ（BP なしの割り込み方式は変数読取の制約あり）
- **必須**: `start_debugging` は `configurationName: "Debug Python (DebugMCP)"` を指定
- 詳細: `docs/ai/debugging.md`

## 手動記事作成フロー

`docs/ai/manual-article-workflow.md` を参照。
