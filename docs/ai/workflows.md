# ワークフロー

## Git Workflow

After completing file changes, check if remote has new commits:

1. `git fetch origin` — fetch remote refs without merging
2. `git rev-list HEAD..origin/main --count` — count remote commits not yet pulled

If remote has new commits (count > 0):

1. `git stash` — save local changes temporarily
2. `git pull` — fetch and merge remote changes
3. `git stash pop` — restore saved changes (resolve conflicts if any)
4. `git add`, `git commit`, `git push`

If remote has no new commits (count == 0):

1. `git add`, `git commit`, `git push`

Commit message format: `feat: <日本語説明>` for features, `fix: <日本語説明>` for bug fixes.
Never use `git push --force` or modify remote history.

## Commit Checklist

git push 前に以下の確認を行う:

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

例外（ワークフローが自動実行されないため確認不要）:

- 変更されたファイルがワークフローの paths (`src/**`, `public/**`, `package.json`, `astro.config.mjs`, `tailwind.config.mjs`) に一致しない場合
- コミットメッセージに `[skip ci]` または `[skip deploy]` を含む場合
