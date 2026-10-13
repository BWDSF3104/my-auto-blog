# Category Strictification

**Date**: 2026-09-29

**Decision**: Enforce strict category routing based on prompt type.

**Reason**: Story/kemono prompts should only receive Safe-rated kemono content. Default tech prompts should only receive tech trends. Prevents category mismatch and inappropriate content.

**Rejected Alternatives**:
- 全カテゴリを全モードに適用: 不適切なコンテンツが混入する
- カテゴリを完全に分離: 柔軟性が低くなり、新しいモードの追加が困難
