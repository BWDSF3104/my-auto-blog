# Known Issues

## Reddit API Blocking (2026-09-29)

**Status**: Active

**Problem**: Reddit blocks `.json` endpoints with HTTP 403. Fallback to `old.reddit.com` returns 404.

**Impact**: 0 Reddit posts collected. Trend data missing kemono/tech content from Reddit.

**Workaround**: None currently. Requires Reddit OAuth or alternative data source.

**Related**: Consider Bluesky API as alternative trend source.

## e621 NSFW Content

**Status**: Resolved (2026-09-29)

**Problem**: e621 tags may include explicit content that appears in article generation prompts.

**Impact**: Non-kemono prompts may receive inappropriate topic suggestions.

**Fix**: Added `_is_nsfw_post()` helper in `fetch_topics.py`. Filters explicit rating and known NSFW tags. Story mode further restricts to Safe-only. Rating field added to collected posts.

## Prompt Type vs. Category Routing

**Status**: Resolved (2026-09-29)

**Problem**: `_select_prompt_type()` and `_append_trending_topics()` have separate category selection logic.

**Impact**: Potential mismatch between selected prompt and injected topics.

**Fix**: Category routing unified in `_append_trending_topics()`. Story mode gets kemono/pokemon only. Default mode gets tech only. Story mode filters to Safe-rated e621 posts.

## Low Score Topic Inclusion

**Status**: Resolved (2026-09-29)

**Problem**: Topics with low scores are still included if they rank in top 5 per category.

**Impact**: Less relevant topics may dilute article inspiration.

**Fix**: Added `MIN_SCORE_THRESHOLD` env var (default 0) in `generate_article.py`. Items below threshold are skipped during injection.
