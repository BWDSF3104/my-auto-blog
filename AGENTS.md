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

更新タイミングは git commit 直後、git push 前で必ず実行する。1コミット = 1開発ノートのエントリ（最小: 日付 + 1行の概要 + 変更ファイル）。

| ファイル | タイミング | 必須 |
|----------|-----------|------|
| `plans.md` | 実装開始前に計画を記録（"進行中の計画"の下） | ✅ |
| `development-notes.md` | 実装完了後に変更内容を記録（コミット単位） | ✅ |
| `known-issues.md` | 新規問題発見時、問題解決時のステータス更新 | ✅ |
| `decisions.md` | 構造・データフロー・新しい統合の設計判断 | ✅ |
| `architecture.md` | decisions.md に記録した変更が反映されたときのみ | ✅ |

- 完了した計画は `plans.md` から `development-notes.md` へ移動

### Commit Checklist

git push 前に以下の確認を行う:
- [ ] 変更が `development-notes.md` に記録されたか
- [ ] 新規問題が `known-issues.md` に記録されたか
- [ ] 解決した問題のステータスが更新されたか

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
