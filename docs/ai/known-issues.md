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

## Description Validation Bugs (2026-09-30)

**Status**: Partially Resolved (2026-09-30)

**Problem**: `_validate_description()` in `generate_article.py` had multiple bugs:

1. **Meaningless padding**: Description under 80 chars is padded with alternating `。` and space characters to reach the minimum, producing nonsensical output.
2. **Existing articles not fixed**: Validator only runs on new generation. 3/10 recent posts have descriptions under 80 chars (68-78 chars).
3. **No retry to LLM**: Validation failure does not trigger LLM regeneration. It silently applies client-side correction.
4. **Regex substitution vulnerability**: `re.sub` at L1428 uses the description value directly in the replacement string. If description contains `"` or `\`, the regex can break.

**Impact**: Short descriptions produce garbage text. Long descriptions may cause regex failures. Existing articles with short descriptions are unaffected but non-compliant.

**Fix**:
- Problem 1: RESOLVED - Added `_extract_first_sentence_from_body()` helper. When description is under 80 chars, it extracts the first sentence from the article body (skipping headings and image lines) and appends it to extend the description naturally.
- Problem 4: RESOLVED - Added `safe_corrected = corrected.replace("\\", "\\\\")` before the `re.sub` call to escape backslashes in the replacement string.
- Problem 2: DEFERRED - Will add optional `--fix-all-descriptions` CLI flag for batch correction in a future update.
- Problem 3: OUT OF SCOPE - Cost/benefit ratio does not justify LLM retry logic.
