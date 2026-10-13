# Score-Based Topic Sorting

**Date**: 2026-09-29

**Decision**: Sort topics by score descending within each category before output.

**Reason**: Higher-scoring topics are more relevant and should be prioritized when injecting trends into article prompts.

**Rejected Alternatives**:
- 収集順のまま使用: 高スコアトピックが後方に埋もれる
- 固定数のみカットオフ: しきい値の調整が難しい
