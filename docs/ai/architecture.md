# Architecture

## Overview

Automated blog generation system with three main components: trend collection, article generation, and static site hosting.

## Data Flow

```
Trend Sources → fetch_topics.py → latest_topics.json → generate_article.py → src/content/posts/
```

## Components

### Trend Collection (`scripts/fetch_topics.py`)

Collects trending topics from multiple sources:

| Source | API | Category | Status |
|--------|-----|----------|--------|
| HackerNews | Firebase API | tech | ✅ Active |
| Reddit | .json endpoint | kemono/tech | ❌ Blocked (403) |
| e621 | REST API | kemono/pokemon | ✅ Active |
| RSS | Feedparser | tech | ✅ Active |
| GitHub | Search API | tech/kemono | ✅ Active |

Output: `data/latest_topics.json` with structure:
- `fetched_at`: ISO timestamp
- `ttl_hours`: Data validity period (24h)
- `total`: Topic count
- `by_category`: Grouped topics (tech, kemono, pokemon, other)
- `all`: All topics sorted by score descending

### Article Generation (`scripts/generate_article.py`)

Generates blog posts using AI:

| Service | Model | Purpose |
|---------|-------|---------|
| Gemini API | gemini-3.x | Text generation |
| HuggingFace | blume/kemono-image-api | Image generation |

Prompt templates:
- `default.txt`: Tech/AI articles
- `ai_deep.txt`: Deep AI technical articles
- `kemono_story.txt`: Kemono fiction stories

Output: Markdown files in `src/content/posts/` with AVIF images in `public/images/`

### Static Site (`astro.config.mjs`)

Astro SSG with:
- Tailwind CSS 4.3
- Content collections for posts
- GitHub Pages deployment
- Base path: `/my-auto-blog/`

## Configuration

- Node.js >= 22.12.0 required
- Python 3.10+ for scripts
- Environment: `GEMINI_API_KEY` required
- Output format: Markdown with AVIF images
