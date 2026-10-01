# my-auto-blog

Automated blog generation system powered by Astro, Gemini AI, and trend data collection.

## Immutable Rules

### Terminal Safety
- NEVER execute destructive terminal commands without explicit user confirmation
- Forbidden commands: `rm -rf`, `git push --force`, `sudo`, modifying files outside workspace root
- **File deletion**: Always use `./kilo-safe-remove.cmd <file>` instead of `Remove-Item` or `del`. It validates the target is inside the project, blocks directory/symlink deletion, and protects `.git/` and `.kilo/`.
- **Folder deletion**: Always use `./kilo-safe-rmdir.cmd <folder>` instead of `Remove-Item -Recurse` or `rmdir /s`. It validates the target is inside the project, blocks deletion of `.git/` and `.kilo/`, and requires explicit confirmation.
- Always verify tests pass after editing code, but do not touch production infrastructure

### Code Verification

- **Pythonコード編集後**: `pytest scripts/tests/ -v` で全テスト通過を確認
- **記事生成後またはAstroファイル編集後**: `npm run build` でビルド成功を確認
- **レイアウトに関わる変更後**: `npm run build` でビルド後、出力HTMLを解析して構造を検証（クラス名、要素階層、コンテンツ順序）。修正がすべて完了した際に最終確認としてユーザーにスクリーンショットを送信
- **git commit 前**: 上記両方を再実行して最終確認
- 成功時は `docs/ai/current-task.md` の Verification セクションにコマンド、結果、経過時間を記録

### Development
- Start dev server with background mode: `astro dev --background`
- Manage background server: `astro dev stop`, `astro dev status`, `astro dev logs`

### Documentation
- Full documentation: https://docs.astro.build
- Consult guides before working on: routing, components, framework integration, content collections, styling, i18n

### Code Standards
- Python scripts use UTF-8 encoding
- Trend data JSON output: `data/latest_topics.json`
- Generated articles: `src/content/posts/`
- Generated images: `public/images/`

### AI Memory Bank (docs/ai/)

docs/ai/ は git 追跡対象。変更履歴は git commit に委ね、docs/ai/ は「なぜ変えたか」の文脈を記録する。

更新タイミングは git commit 前。Memory Bank の変更はコード変更と同じ commit に含める。プロジェクト知識・状態・判断が変化した場合のみ更新する（コード変更 ≒ Memory Bank 更新ではない）。

| ファイル | 役割 | 更新タイミング | 必須 |
|----------|------|---------------|------|
| `current-task.md` | 現在進行中のタスク状態 | マルチステップタスクの各チェックポイントで更新。中断時は復帰可能な状態のまま残す | ✅ |
| `plans.md` | 計画書 | 実装開始前に Active Plans に記録。完了時は Completed Plans に意図・背景を1行記録 | ✅ |
| `backlog.md` | バックログ | 未実装項目の追加・完了時の削除（変更履歴は git commit に委ねる） | ✅ |
| `known-issues.md` | 既知問題リスト | 新規問題発見時、問題解決時のステータス更新（解決済はアーカイブへ移動） | ✅ |
| `decisions.md` | 設計判断ログ | 構造・データフロー・新しい統合の設計判断。Decision / Reason / Rejected Alternatives を記録 | ✅ |
| `architecture.md` | アーキテクチャ図 | decisions.md に記録した変更がシステム構成に反映されたときのみ更新 | ✅ |

- 完了したバグは `known-issues.md` のアーカイブへ移動
- `development-notes.md` は削除済み。詳細な実装履歴は git log で確認可能

### Long-running Agent Tasks

- Before starting a multi-step task, read `docs/ai/current-task.md` if it exists.
- Before starting a planned change, read the relevant `plans.md` and `backlog.md` entries.
- After completing a meaningful step, update `docs/ai/current-task.md`.
- After a successful build/test checkpoint, record the result in `current-task.md`.
- If the task is interrupted, leave `current-task.md` in a resumable state.
- Never assume previous conversation context is still available after compaction.
- Important decisions must be recorded in `decisions.md`.
- Important unresolved problems must be recorded in `known-issues.md`.
- Do not start the next planned item until the current item's build/test completion criteria are satisfied.
- **After git commit & push**: Update `docs/ai/current-task.md` — set `Status` to `完了`, clear `Next Action`, and record the commit hash in the completed checklist.

### Recovery After Interruption

When resuming an interrupted task:

1. Read `docs/ai/current-task.md`.
2. Check `git status`.
3. Check `git diff`.
4. Verify the last recorded build/test status.
5. Continue from the `Next Action` in `current-task.md`.
6. Do not discard existing changes unless explicitly instructed.

### Commit Checklist

git push 前に以下の確認を行う:
- [ ] Pythonテストが全件通過したか (`pytest scripts/tests/ -v`)
- [ ] Astroビルドが成功したか (`npm run build`)
- [ ] 完了した計画が `plans.md` の「完了した計画」に記録されたか
- [ ] 新規問題が `known-issues.md` に記録されたか
- [ ] 解決した問題が `known-issues.md` の Archive へ移動されたか
- [ ] 完了したバックログ項目が `backlog.md` から削除されたか

### Deploy Workflow

git push 後に DeployOnly ワークフローを実行し、成功を確認する:
1. `gh workflow run deploy-only.yml` — ワークフローを手動実行
2. 実行結果が success になるまで監視
3. 失敗時は原因を調査して修正を継続

例外: `AGENTS.md` および `docs/` 内のファイルのみを更新した場合はテスト実行と DeployOnly ワークフローの実行は不要

### Git Workflow
- After completing file changes, check if remote has new commits:
  1. `git fetch origin` — fetch remote refs without merging
  2. `git rev-list HEAD..origin/main --count` — count remote commits not yet pulled
- If remote has new commits (count > 0):
  1. `git stash` — save local changes temporarily
  2. `git pull` — fetch and merge remote changes
  3. `git stash pop` — restore saved changes (resolve conflicts if any)
  4. `git add`, `git commit`, `git push`
- If remote has no new commits (count == 0):
  1. `git add`, `git commit`, `git push`
- Commit message format: `feat: <description>` for features, `fix: <description>` for bug fixes
- Never use `git push --force` or modify remote history

### Scope
- This project is a static site generator blog
- No user authentication, no database, no server-side rendering
- Deployed to GitHub Pages (`BWDSF3104.github.io/my-auto-blog`)

## Project Structure

```
my-auto-blog/
├── scripts/               # Python automation scripts
│   ├── fetch_topics.py    # Trend data collection
│   ├── generate_article.py # Article generation
│   └── prompts/           # Prompt templates
├── src/                   # Astro source
│   └── content/posts/     # Generated markdown posts
├── public/                # Static assets
│   └── images/            # Generated images
├── data/                  # Collected data
│   └── latest_topics.json # Trend topics
└── docs/ai/               # AI Memory Bank (changing knowledge)
```
