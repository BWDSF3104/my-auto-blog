# Known Issues

## Reddit API Blocking (2026-09-29)

**Status**: Active

**Problem**: Reddit blocks `.json` endpoints with HTTP 403. Fallback to `old.reddit.com` returns 404.

**Impact**: 0 Reddit posts collected. Trend data missing kemono/tech content from Reddit.

**Workaround**: None currently. Requires Reddit OAuth or alternative data source.

**Related**: Consider Bluesky API as alternative trend source.

## e621 NSFW Content

**Status**: Unresolved

**Problem**: e621 tags may include explicit content that appears in article generation prompts.

**Impact**: Non-kemono prompts may receive inappropriate topic suggestions.

**Planned Fix**: Add NSFW filter to e621 collection. Separate Safe/Questionable/Explicit ratings.

## Prompt Type vs. Category Routing

**Status**: Partial

**Problem**: `_select_prompt_type()` and `_append_trending_topics()` have separate category selection logic.

**Impact**: Potential mismatch between selected prompt and injected topics.

**Planned Fix**: Unify category routing between prompt selection and topic injection.

## Low Score Topic Inclusion

**Status**: Unresolved

**Problem**: Topics with low scores are still included if they rank in top 5 per category.

**Impact**: Less relevant topics may dilute article inspiration.

**Planned Fix**: Add minimum score threshold for topic injection.
