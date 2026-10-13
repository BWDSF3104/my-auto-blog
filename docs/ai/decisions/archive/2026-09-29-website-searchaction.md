# WebSite SearchAction

**Date**: 2026-09-29

**Decision**: Add schema.org SearchAction to enable Google site search integration.

**Reason**: Allows Google to show site search results directly in SERPs. Uses `/tags/{search_term_string}` as the search target.

**Rejected Alternatives**:
- 外部検索エンジン (Google Custom Search): 設定が複雑でコストがかかる
- 独自の検索ページ実装: SSGでリアルタイム検索が難しい
