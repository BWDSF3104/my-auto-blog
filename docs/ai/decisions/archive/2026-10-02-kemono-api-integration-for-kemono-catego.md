# Kemono API Integration for Kemono Category

**Date**: 2026-10-02

**Decision**: Add Kemono API (`/api/v1/posts`) as a data source for the kemono category, collecting recent posts from Patreon, Fanbox, SubscribeStar, and DLsite.

**Reason**: Reddit API is blocked (HTTP 403/404), so alternative sources are needed for kemono/furry content. Kemono API provides public access to creator posts without authentication.

**Rejected Alternatives**:
- Reddit OAuth 導入: 認証フローが複雑で、CI/CD 環境での維持が困難
- Twitter/X API: 有料プランが必要で、コストが高すぎる

**Impact**:
- `fetch_topics.py`: `collect_kemono_api()` 関数追加、`collect_topics()` に統合
- `test_fetch_topics.py`: `collect_kemono_api` のモックを追加
