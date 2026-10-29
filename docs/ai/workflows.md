# ワークフロー

## Git Workflow

`git commit`と`git push`は不可分な一連の作業。commit完了直後は**必ず**`git push`を実行すること。pushを中断してはならない。

- **commit/push は1コマンド**: `git add -A; git commit -m "<メッセージ>"; git push` を `;` で1コマンドに結合して実行する。
- **commit前**: `git status --short` を単独実行して対象ファイルを特定する。
- **commitメッセージ**: `feat: <日本語説明>` / `fix: <日本語説明>`。指定なしの場合は変更ファイルから推論・作成。
- **remote 競合**: push が失敗した場合のみ `git pull --rebase` → 再実行。`git push --force` とリモート履歴の変更は禁止。

## Commit Checklist

git push 前に以下の確認を行う:

- [ ] 編集したファイルの内容を `git diff` で確認（hex 解析・codepoint 検証は不要）
- [ ] Pythonファイルを変更した場合はテストが全件通過したか (`pytest scripts/tests/ -v`。正典ツール（Kilo_Commons `bin/`）変更時は加えて Kilo_Commons で `python -m pytest tests/ -v`)
- [ ] Astroファイルを変更した場合はビルドが成功したか (`npm run build`)
- [ ] タスクファイルの `Status` が『完了』へ更新され、`current-task.tsv` の参照行が削除されたか
- [ ] 新規問題が `known-issues/` に新ファイルとして記録されたか
- [ ] 解決した問題の `known-issues/` ファイルが `known-issues/archive/` へ `mv` されたか
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
