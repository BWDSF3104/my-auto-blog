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
- **Astroファイル編集後または記事生成後**: `npm run build` でビルド成功を確認
- **レイアウトに関わる変更後**: `npm run build` でビルド後、出力HTMLを解析して構造を検証（クラス名、要素階層、コンテンツ順序）。修正がすべて完了した際に最終確認としてユーザーにスクリーンショットを送信
- **git commit 前**: 変更内容に応じて再実行して最終確認（Pythonファイルの変更時は pytest、Astroファイルの変更時は build、両方変更時は両方）
- 成功時は `docs/ai/current-task.md` の Verification セクションにコマンド、結果、経過時間を記録
- **例外**: `docs/ai/` のみの変更、`AGENTS.md` のみの変更、`.kilo/` のみの変更は pytest と build の実行不要

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
| `current-task.md` | アクティブタスクへの参照（ファイルパス、ステータス、Next Action のみ） | タスク開始時に参照行を追加。各チェックポイントでステータス・Next Action を更新。タスク完了時または中断時に参照行を削除 | ✅ |
| `tasks/*.md` | タスクの個別ファイル（1タスク1ファイル方式、アクティブ・完了問わず） | タスク開始時に `docs/ai/tasks/YYYY-MM-DD-short-name.md` として作成。完了時は Status を更新 | ✅ |
| `plans.md` | 計画書 | タスク開始前に Active Plans に記録（実装・調査問わず）。完了時は Completed Plans に意図・背景を1行記録 | ✅ |
| `backlog.md` | バックログ | 未実装項目の追加・完了時の削除（変更履歴は git commit に委ねる） | ✅ |
| `known-issues.md` | 既知問題リスト | 新規問題発見時、問題解決時のステータス更新（解決済はアーカイブへ移動） | ✅ |
| `decisions.md` | 設計判断ログ | 構造・データフロー・新しい統合の設計判断。Decision / Reason / Rejected Alternatives を記録 | ✅ |
| `architecture.md` | アーキテクチャ図 | decisions.md に記録した変更がシステム構成に反映されたときのみ更新 | ✅ |

- 完了したバグは `known-issues.md` のアーカイブへ移動
- `development-notes.md` は削除済み。詳細な実装履歴は git log で確認可能

### Memory Bank アーカイブ

ファイルが膨張しないよう、完了したエントリは対応する `-archive.md` ファイルへ移動する。

| 本体ファイル | アーカイブファイル | 閾値 | 移動内容 |
|-------------|-------------------|------|---------|
| `plans.md` | `plans-archive.md` | Completed Plans が6件以上 | 古い Completed Plans エントリを移動 |
| `known-issues.md` | `known-issues-archive.md` | 解決済が1件以上 | 解決済エントリを即時移動 |
| `decisions.md` | `decisions-archive.md` | 15件以上 | 古い決定エントリを移動 |

- `current-task.md` はアクティブなタスクのみ保持。完了したタスクは `tasks/` へ個別ファイルとして移動
- `tasks/` のファイル名: `YYYY-MM-DD-short-name.md` 形式
- `Completed Plans` は直近5件まで `plans.md` に保持
- アーカイブのタイミング: 新規タスク開始時、または閾値超過時に実行
- アーカイブファイルは git 追跡対象

### Long-running Agent Tasks

- Before starting any task, read `docs/ai/current-task.md` if it exists.
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
- [ ] Pythonファイルを変更した場合はテストが全件通過したか (`pytest scripts/tests/ -v`)
- [ ] Astroファイルを変更した場合はビルドが成功したか (`npm run build`)
- [ ] 完了した計画が `plans.md` の「完了した計画」に記録されたか
- [ ] 新規問題が `known-issues.md` に記録されたか
- [ ] 解決した問題が `known-issues.md` の Archive へ移動されたか
- [ ] 完了したバックログ項目が `backlog.md` から削除されたか

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

### Deploy Verification

git push 後、DeployOnly ワークフローが push トリガーで自動実行されたことを確認:
1. `gh run list --workflow=deploy-only.yml --limit 5` — 直近の実行履歴を確認
2. 最新の push トリガー実行が `success` であることを確認
3. 失敗時は原因を調査して修正を継続

手動実行 (`gh workflow run`) はしない。push 自動トリガーに依存する。

例外（ワークフローが自動実行されないパターンで確認不要）:
- `docs/`, `scripts/`, `AGENTS.md`, `.github/` など、デプロイ対象外のファイルのみ変更した場合
- コミットメッセージに `[skip ci]` または `[skip deploy]` を含む場合

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
