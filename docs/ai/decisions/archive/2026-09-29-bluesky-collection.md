# Bluesky Collection

**Date**: 2026-09-29

**Decision**: Add Bluesky as a trend data source using the public search API.

**Reason**: Reddit API blocks `.json` endpoints. Bluesky provides an open search API that can supplement tech and kemono trend data.

**Rejected Alternatives**:
- Reddit OAuth 導入: ユーザーインタラクションが必要でCI/CDと相性が悪い
- Twitter API: 有料プランが必要でコストが高い
