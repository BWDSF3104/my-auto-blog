# Deferred Low-Priority Items

**Date**: 2026-09-29

**Decision**: Defer partial cache and Reddit OAuth to future iterations.

**Reason**: Both require significant implementation effort. Partial cache needs per-source cache files and merge logic. Reddit OAuth requires a full OAuth flow with user interaction. Neither blocks core functionality.

**Rejected Alternatives**:
- 即時実装: スコープが膨張し、コア機能の完了が遅れる
- 完全削除: 将来的に必要な可能性を排除しすぎる
