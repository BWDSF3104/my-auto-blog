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

| Source | API | Category | Status | Notes |
|--------|-----|----------|--------|-------|
| HackerNews | Firebase API | tech | ✅ Active | |
| Reddit | .json endpoint | kemono/pokemon/tech | ⏸️ Disabled | 403 Blocked (2026-10-06 コメントアウト) |
| e621 | REST API | —（トレンド出力に含めない） | ✅ Active | キャラクター特徴集計のみ。2026-10-10 以降トレンド配管から分離（`latest.json` に入れない、`NON_TREND_SOURCES` ガード） |
| RSS (Zenn/Qiita) | xml.etree.ElementTree | tech | ✅ Active | |
| RSS (PokéCommunity/PokeBeach/PokemonBlog/PocketMonsters) | xml.etree.ElementTree | pokemon | ✅ Active | |
| GitHub | Search API | kemono/pokemon | ✅ Active | 未認証 60req/h |
| Bluesky | AT Protocol search API | tech/kemono/pokemon | ⏸️ Disabled | 501 Not Implemented (2026-10-06 コメントアウト) |
| GameSpot RSS | HTMLパース | kemono | ✅ Active | ゲームニュース → ストーリーインスピレーション |
| IGN RSS | HTMLパース | kemono | ✅ Active | ゲーム・エンタメニュース |
| Anime News Network | HTMLパース | kemono | ✅ Active | アニメニュース |
| Crunchyroll News | HTMLパース | kemono | ✅ Active | アニメ・エンタメニュース |

**カテゴリ別ソース構成:**
- **tech**: HackerNews, RSS (Zenn/Qiita)
- **kemono**: GitHub, GameSpot, IGN, Anime News Network, Crunchyroll
- **pokemon**: GitHub, RSS (PokéCommunity/PokeBeach/PokemonBlog/PocketMonsters)

Output: `data/topics/{YYYY-MM-DD}_{HHMMSS}.json` with structure:
- `fetched_at`: Run start ISO timestamp
- `ttl_hours`: Data validity period (24h, configurable via env var)
- `sources`: Per-source objects, each with `fetched_at` and `topics` array
- Symlink: `data/topics/latest.json` → newest file (backward compatibility)

Category-based source filtering: each source can be configured to collect for specific categories. e621 is filtered by NSFW rating at collection time. Per-source TTL allows `generate_article.py` to auto-trigger `fetch_topics.py --prompt-type X` when needed categories are stale.

Since 2026-10-10, e621 is separated from the trend pipeline: `collect_e621()` collects posts for character feature aggregation only (no trend topics), and `main()` filters `latest.json` output via the `NON_TREND_SOURCES` constant (covers the merge-inheritance path from previous data as well). e621 data is used only for character feature aggregation (`_aggregate_and_save_character_features` → `data/character_features.json`).

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
| HuggingFace | `HF_TOKEN` | read/write ロール必要（细粒度トークンは ZeroGPU quota API 不可） |
| Amazon | `AMAZON_TRACKING_ID` | - |
| Rakuten | `RAKUTEN_AFFILIATE_ID` | - |

**HF 運用**:
- CLI 認証: `hf auth login`（トークンをローカル保存）
- ZeroGPU 残り確認: `hf spaces zero-gpu quota`（`huggingface_hub` v2.1.0+ 必要）
- Space 停止時は再開に数分要する。起動待ち中にリクエストすると失敗する
- `gradio-client` は 2.7.2+ を使用（`huggingface_hub` 2.x 互換）

**HF Space デプロイ** (`scripts/hf-space/app.py` 変更後):
- アップロード: `hf upload --repo-type space blume/kemono-image-api scripts\hf-space\app.py`
- 起動確認: `python -c "from huggingface_hub import HfApi; api = HfApi(); info = api.get_space_runtime('blume/kemono-image-api'); print(info.stage)"` → `RUNNING` になるまで待機
- 生成テスト: `python scripts/_test_hf_space.py` （Space が `RUNNING` 後に実行）
- Space URL: `https://huggingface.co/spaces/blume/kemono-image-api`
- Scheduler: `EulerAncestralDiscreteScheduler` (Euler a)
- GPU予約: `@spaces.GPU(duration=20)` (実推論約5秒、マージン含め20秒)

## Configuration

- Node.js >= 22.12.0 required
- Python 3.10+ for scripts
- Output format: Markdown with AVIF images
- AI Memory Bank: `docs/ai/` (tracked in git, contains plans, backlog, known-issues, decisions, architecture)
