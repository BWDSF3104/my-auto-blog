# my-auto-blog

Automated blog generation system powered by Astro, Gemini AI, and trend data collection.

## Immutable Rules

### Terminal Safety
- NEVER execute destructive terminal commands without explicit user confirmation
- Forbidden commands: `rm -rf`, `git push --force`, `sudo`, modifying files outside workspace root
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
- **Before implementation**: Record the plan and direction in `docs/ai/plans.md` under "進行中の計画"
- Update `docs/ai/architecture.md` when project structure or data flow changes
- Update `docs/ai/decisions.md` when making design decisions or architectural changes
- Update `docs/ai/known-issues.md` when discovering new issues or resolving existing ones
- Update `docs/ai/development-notes.md` after completing implementation work
- Move completed plans from `docs/ai/plans.md` to `docs/ai/development-notes.md` on completion

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
