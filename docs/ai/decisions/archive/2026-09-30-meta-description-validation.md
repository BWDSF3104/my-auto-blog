# Meta Description Validation

**Date**: 2026-09-30

**Decision**: Extract first sentence from article body to extend short descriptions. Add regex safety.

**Reason**: `_validate_description()` padded short descriptions with meaningless characters (`。` and spaces). 30% of recent articles had descriptions under 80 chars. Regex substitution was vulnerable to backslash characters in description text.

**Rejected Alternatives**:
- LLMでdescriptionを再生成: APIコストが高く、生成時間が伸びる
- 既存記事の無視: SEOが継続的に劣化する
