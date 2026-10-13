# SEO Slug Implementation

**Date**: 2026-09-29

**Decision**: Add `slug` field to article frontmatter for SEO-friendly URLs.

**Reason**: File-based URLs (timestamps like `2026-09-29T123456`) are not SEO-friendly. A readable slug improves URL structure, search engine indexing, and user experience.

**Rejected Alternatives**:
- ファイル名のみを使用: タイムスタンプ形式でSEO不向き
- 日付ベースのURL: 記事の更新時にURLが変わり、リンク切れリスク
