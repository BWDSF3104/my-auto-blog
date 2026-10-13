# TOC (Table of Contents) Implementation

**Date**: 2026-09-29

**Decision**: Add dynamic TOC navigation to article pages using client-side JavaScript.

**Reason**: Long articles benefit from in-page navigation. Server-side generation in Astro would require parsing markdown AST; client-side DOM extraction is simpler and maintains reactivity with scroll-based active state.

**Rejected Alternatives**:
- Astro側でMarkdown ASTをパース: 依存が増え、ビルド時間が伸びる
- 手動でTOCを記事に埋め込み: 生成物の保守性が高い
