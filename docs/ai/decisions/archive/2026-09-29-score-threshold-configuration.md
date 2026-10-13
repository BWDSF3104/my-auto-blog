# Score Threshold Configuration

**Date**: 2026-09-29

**Decision**: Add configurable minimum score threshold for trend injection.

**Reason**: Low-score topics can dilute article quality. A configurable threshold allows operators to filter without modifying code.

**Rejected Alternatives**:
- コードにハードコード: 運用中の調整が不可能
- 固定数のみ選択: スコア分布の変化に対応できない
