# Architecture

## Overview

Automated blog generation system with three main components: trend collection, article generation, and static site hosting.

## Data Flow

```
Trend Sources → fetch_topics.py → data/topics/{timestamp}.json → generate_article.py → src/content/posts/
                                              ↕ latest.json (symlink)
                                                     ↓
                                           Affiliate Keywords → inject_affiliate_links() → Amazon/Rakuten links
                                                     ↓
                                           Product Recommendations → generate_product_cards() → Product cards HTML
```

## Components

### Trend Collection (`scripts/fetch_topics.py`)

Collects trending topics from multiple sources:

| Source | API | Category | Status |
|--------|-----|----------|--------|
| HackerNews | Firebase API | tech | ✅ Active |
| Reddit | .json endpoint | kemono/pokemon/tech | ❌ Blocked (403) |
| e621 | REST API | kemono/pokemon | ✅ Active |
| RSS | xml.etree.ElementTree | tech/pokemon | ✅ Active |
| GitHub | Search API | kemono/pokemon | ✅ Active |
| Bluesky | AT Protocol search API | tech/kemono/pokemon | ✅ Active |

Output: `data/topics/{YYYY-MM-DD}_{HHMMSS}.json` with structure:
- `fetched_at`: Run start ISO timestamp
- `ttl_hours`: Data validity period (24h, configurable via env var)
- `sources`: Per-source objects, each with `fetched_at` and `topics` array
- Symlink: `data/topics/latest.json` → newest file (backward compatibility)

Category-based source filtering: each source can be configured to collect for specific categories. e621 is filtered by NSFW rating at collection time. Per-source TTL allows `generate_article.py` to auto-trigger `fetch_topics.py --prompt-type X` when needed categories are stale.

### Article Generation (`scripts/generate_article.py`)

Generates blog posts using AI:

| Service | Model | Purpose |
|---------|-------|---------|
| Gemini API | gemini-3.x | Text generation |
| HuggingFace | blume/kemono-image-api | Primary image generation |
| Pollinations.ai | Flux | Fallback image generation (no API key, free) |

Prompt templates:
- `default.txt`: Tech/AI articles
- `ai_deep.txt`: Deep AI technical articles
- `kemono_story.txt`: Kemono fiction stories

2-pass generation: draft → refine workflow with separate prompts for tech articles and stories.

Image generation:
- SFW enforced via `BASE_QUALITY_PROMPT` with "safe for work, wholesome, family-friendly" tags
- Per-article art style from frontmatter `art_style` field via `extract_art_style()`
- Header image (896×512px AVIF) + inline images from `<!-- IMAGE_PROMPT: "..." -->` markers
- All images saved to `public/images/`
- Fallback: HF failure (2 retries exhausted) → Pollinations.ai (`https://image.pollinations.ai/prompt/`)
- Local testing: `IMAGE_PROVIDER=pollinations` skips HF and uses Pollinations directly

Output: Markdown files in `src/content/posts/` with AVIF images in `public/images/`

### Affiliate Integration (Implemented)

Trend topics are used to generate targeted affiliate search links and product cards:

1. `_append_trending_topics()` returns the injected prompt plus a list of extracted keywords from the trend titles
2. Keywords are passed to `inject_affiliate_links(content, trend_keywords=...)`
3. All categories (tech, kemono, pokemon) produce affiliate keywords
4. Links are generated for Amazon and Rakuten with UTM tracking and click analytics
5. `product_recommendations` frontmatter field generates visual product cards with name, category, price range, and affiliate links

Phase 2 (AI-inferred keywords via Frontmatter) is deferred pending Phase 1 results.

### Static Site (`astro.config.mjs`)

Astro SSG with:
- Tailwind CSS 4.3
- Content collections for posts
- GitHub Pages deployment
- Base path: `/my-auto-blog/`
- SEO: slug routing, TOC, breadcrumbs, tag pages, related posts, BreadcrumbList/SearchAction JSON-LD

## API Keys

All API keys are managed via `.env` (git-ignored) and GitHub Repository Secrets.
Scripts use `python-dotenv` (`from dotenv import load_dotenv`) to load environment variables.

| Service | Env Var | Name |
|---------|---------|------|
| Gemini | `GEMINI_API_KEY` | - |
| HuggingFace | `HF_TOKEN` | - |
| Amazon | `AMAZON_TRACKING_ID` | - |
| Rakuten | `RAKUTEN_AFFILIATE_ID` | - |

## Configuration

- Node.js >= 22.12.0 required
- Python 3.10+ for scripts
- Output format: Markdown with AVIF images
- AI Memory Bank: `docs/ai/` (tracked in git, contains plans, backlog, known-issues, decisions, architecture)
