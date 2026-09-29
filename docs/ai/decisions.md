# Design Decisions

## 2026-09-29: Score-Based Topic Sorting

**Decision**: Sort topics by score descending within each category before output.

**Rationale**: Higher-scoring topics are more relevant and should be prioritized when injecting trends into article prompts.

**Impact**:
- `fetch_topics.py`: Added score sorting for all categories and global list
- `generate_article.py`: Topics are now selected by score, not collection order

## 2026-09-29: TTL Validation for Trend Data

**Decision**: Add 24-hour TTL to trend data with validation on read.

**Rationale**: Stale trend data produces irrelevant article content. TTL validation warns users when data is outdated.

**Impact**:
- `fetch_topics.py`: Added `ttl_hours` field to JSON output
- `generate_article.py`: Added `_check_topics_ttl()` function that warns on TTL expiration

## 2026-09-29: Affiliate × Trend Integration Strategy

**Decision**: Adopt Phase 1 approach — extract affiliate keywords from injected trend topics, pass to `inject_affiliate_links()`.

**Rationale**: Current affiliate links use generic tags ("Tech", "AI") producing broad search results with low CTR. Trend topics are specific and product-relevant (e.g., "ローカルLLM", "Claude Code"), enabling targeted affiliate search links.

**Impact**:
- `_append_trending_topics()`: Return type changes to `tuple[str, list[str]]` (prompt + keywords)
- `inject_affiliate_links()`: Accepts optional `trend_keywords` parameter, prioritizes over tag-based extraction
- Only `tech` category trends are used for affiliate keywords (kemono/pokemon have low product relevance)
- Phase 2 (AI-inferred keywords via Frontmatter) is deferred pending Phase 1 results

**Implementation order**: Phase 1 (keyword extraction from trends) → measure CTR → Phase 2 (AI inference) if needed.

## 2026-09-29: NSFW Filter for e621

**Decision**: Filter explicit content at collection time in `fetch_topics.py`.

**Rationale**: e621 contains explicit-rated posts that should not appear in article prompts for non-kemono content. Filtering at collection prevents inappropriate content from entering the pipeline.

**Impact**:
- Added `_is_nsfw_post()` helper checking `rating=="e"` and known NSFW tags
- `collect_e621()` skips NSFW posts and prints filter count
- Rating field (`s`/`q`/`e`) added to collected post data for downstream filtering

## 2026-09-29: Category Strictification

**Decision**: Enforce strict category routing based on prompt type.

**Rationale**: Story/kemono prompts should only receive Safe-rated kemono content. Default tech prompts should only receive tech trends. Prevents category mismatch and inappropriate content.

**Impact**:
- Story mode (`kemono_story`, `novel`, `story`): filters to Safe-rated e621 posts only, categories `["kemono", "pokemon"]`
- Default mode: categories `["tech"]` only
- Other modes: categories `["tech", "kemono", "pokemon"]`

## 2026-09-29: Bluesky Collection

**Decision**: Add Bluesky as a trend data source using the public search API.

**Rationale**: Reddit API blocks `.json` endpoints. Bluesky provides an open search API that can supplement tech and kemono trend data.

**Impact**:
- Added `BLUESKY_SEARCHES` config with 3 queries (LLM AI/tech, kemono furry art, pokemon)
- Added `collect_bluesky()` function using `app.bsky.unspecced.searchPostsLazy` endpoint
- Results categorized into `tech`, `kemono`, or `pokemon` based on query

## 2026-09-29: Frontmatter Reference Tracking

**Decision**: Record injected trend source URLs in article frontmatter.

**Rationale**: Enables traceability of which trends inspired each article. Useful for content auditing and understanding article provenance.

**Impact**:
- `_append_trending_topics()` now returns 3-element tuple: `(prompt, affiliate_keywords, source_urls)`
- `trend_sources` YAML list added to frontmatter (up to 10 URLs)

## 2026-09-29: Score Threshold Configuration

**Decision**: Add configurable minimum score threshold for trend injection.

**Rationale**: Low-score topics can dilute article quality. A configurable threshold allows operators to filter without modifying code.

**Impact**:
- Added `MIN_SCORE_THRESHOLD` env var (default 0, meaning no filtering)
- Items below threshold are skipped in `_append_trending_topics()`

## 2026-09-29: Affiliate All-Categories Extension

**Decision**: Extend affiliate keyword extraction to all categories (tech, kemono, pokemon).

**Rationale**: Original design only extracted keywords from tech category. All recent articles use kemono_story prompt type, so affiliate links always fell back to generic tag-based keywords ("Kemono"). Kemono/pokemon topics have merchandise potential (figures, art books, games).

**Impact**:
- `generate_article.py`: Line 579 changed from `cat == "tech"` to `cat in ("tech", "kemono", "pokemon")`
- kemono_story articles now get 2 trend-based affiliate keywords instead of generic fallback

## 2026-09-29: Deferred Low-Priority Items

**Decision**: Defer partial cache and Reddit OAuth to future iterations.

**Rationale**: Both require significant implementation effort. Partial cache needs per-source cache files and merge logic. Reddit OAuth requires a full OAuth flow with user interaction. Neither blocks core functionality.

**Impact**: Items remain on the backlog for future consideration.

## 2026-09-29: SEO Slug Implementation

**Decision**: Add `slug` field to article frontmatter for SEO-friendly URLs.

**Rationale**: File-based URLs (timestamps like `2026-09-29T123456`) are not SEO-friendly. A readable slug improves URL structure, search engine indexing, and user experience.

**Impact**:
- `generate_article.py`: Added slug validation and auto-generation fallback (hiragana/katakana to romaji conversion)
- `scripts/prompts/`: Added slug generation rules to both prompt templates
- `src/pages/posts/[...slug].astro`: Routes by frontmatter slug, falls back to filename
- `src/pages/rss.xml.ts`, `src/pages/sitemap.xml.ts`: Use slug-based URLs
- `src/pages/index.astro`: Post links use slug

## 2026-09-29: TOC (Table of Contents) Implementation

**Decision**: Add dynamic TOC navigation to article pages using client-side JavaScript.

**Rationale**: Long articles benefit from in-page navigation. Server-side generation in Astro would require parsing markdown AST; client-side DOM extraction is simpler and maintains reactivity with scroll-based active state.

**Impact**:
- `src/layouts/PostLayout.astro`: Added TOC nav element, JavaScript to extract h2/h3/h4 headings, smooth scroll, and IntersectionObserver for active state tracking
- CSS: Added `.toc-link`, `.toc-link-active`, `scroll-behavior: smooth`

## 2026-09-29: BreadcrumbList JSON-LD

**Decision**: Add schema.org BreadcrumbList structured data to all article and tag pages.

**Rationale**: Breadcrumbs improve SERP display with rich snippets and help search engines understand site hierarchy.

**Impact**:
- `src/layouts/PostLayout.astro`: BreadcrumbList JSON-LD + visual breadcrumb nav
- `src/pages/tags/`: BreadcrumbList JSON-LD on both index and tag pages

## 2026-09-29: WebSite SearchAction

**Decision**: Add schema.org SearchAction to enable Google site search integration.

**Rationale**: Allows Google to show site search results directly in SERPs. Uses `/tags/{search_term_string}` as the search target.

**Impact**:
- `src/pages/index.astro`, `src/layouts/PostLayout.astro`: SearchAction JSON-LD injected

## 2026-09-29: Tag Pages

**Decision**: Create tag-based navigation pages for content discovery.

**Rationale**: Tags provide an alternative navigation structure beyond chronological listing. Improves internal linking and SEO through additional indexable pages.

**Impact**:
- `src/pages/tags/index.astro`: Tag cloud with counts, CollectionPage JSON-LD
- `src/pages/tags/[tag].astro`: Tag-specific post listing with thumbnails
- Tags in article/index pages changed from `<span>` to `<a>` links

## 2026-09-29: Related Posts

**Decision**: Show related posts at the bottom of each article based on shared tags.

**Rationale**: Increases time-on-site, reduces bounce rate, and creates internal link structure for SEO.

**Impact**:
- `src/layouts/PostLayout.astro`: Computes shared tag score across all posts, shows top 3 related posts with thumbnails sorted by tag overlap then recency

## 2026-09-28: Project Structure

**Decision**: Separate immutable rules (AGENTS.md) from changing knowledge (docs/ai/).

**Rationale**: Claude Memory Bank pattern allows agents to distinguish between permanent constraints and evolving project state.

**Impact**: New documentation structure created for better knowledge management.
