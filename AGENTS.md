# my-auto-blog

Automated blog generation system powered by Astro, Gemini AI, and trend data collection.

## Immutable Rules

### Terminal Safety
- NEVER execute destructive terminal commands without explicit user confirmation
- Forbidden commands: `rm -rf`, `git push --force`, `sudo`, modifying files outside workspace root
- **File deletion**: Always use `./kilo-safe-remove.cmd <file>` instead of `Remove-Item` or `del`. It validates the target is inside the project, blocks directory/symlink deletion, and protects `.git/` and `.kilo/`.
- Always verify tests pass after editing code, but do not touch production infrastructure

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

更新タイミングは git commit 直後、git push 前で必ず実行する。1コミットにつき少なくとも1つのファイルを更新する（単なる依存更新・タイポ修正など文脈記録が不要な場合は除く）。

| ファイル | 役割 | 更新タイミング | 必須 |
|----------|------|---------------|------|
| `plans.md` | 計画書 | 実装開始前に計画を記録（"進行中の計画"の下）。完了時は「完了した計画」に意図・背景を1行記録 | ✅ |
| `backlog.md` | バックログ | 未実装項目の追加・完了時の削除（変更履歴は git commit に委ねる） | ✅ |
| `known-issues.md` | 既知問題リスト | 新規問題発見時、問題解決時のステータス更新（解決済はアーカイブへ移動） | ✅ |
| `decisions.md` | 設計判断ログ | 構造・データフロー・新しい統合の設計判断 | ✅ |
| `architecture.md` | アーキテクチャ図 | decisions.md に記録した変更がシステム構成に反映されたときのみ更新 | ✅ |

- 完了したバグは `known-issues.md` のアーカイブへ移動
- `development-notes.md` は削除済み。詳細な実装履歴は git log で確認可能

### Commit Checklist

git push 前に以下の確認を行う:
- [ ] 完了した計画が `plans.md` の「完了した計画」に記録されたか
- [ ] 新規問題が `known-issues.md` に記録されたか
- [ ] 解決した問題が `known-issues.md` の Archive へ移動されたか
- [ ] 完了したバックログ項目が `backlog.md` から削除されたか

### Git Workflow
- After completing file changes, always run `git pull` then `git add`, `git commit`, `git push`
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
