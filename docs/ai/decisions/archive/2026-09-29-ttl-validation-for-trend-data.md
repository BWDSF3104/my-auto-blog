# TTL Validation for Trend Data

**Date**: 2026-09-29

**Decision**: Add 24-hour TTL to trend data with validation on read.

**Reason**: Stale trend data produces irrelevant article content. TTL validation warns users when data is outdated.

**Impact**:
- `fetch_topics.py`: Added `ttl_hours` field to JSON output
- `generate_article.py`: Added `_check_topics_ttl()` function that warns on TTL expiration
