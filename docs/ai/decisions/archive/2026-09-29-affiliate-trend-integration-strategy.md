# Affiliate × Trend Integration Strategy

**Date**: 2026-09-29

**Decision**: Adopt Phase 1 approach — extract affiliate keywords from injected trend topics, pass to `inject_affiliate_links()`.

**Reason**: Current affiliate links use generic tags ("Tech", "AI") producing broad search results with low CTR. Trend topics are specific and product-relevant (e.g., "ローカルLLM", "Claude Code"), enabling targeted affiliate search links.

**Rejected Alternatives**:
- Phase 2 (AI推論) の即時実装: 過剰設計でPhase 1の結果が不明
- 手動でのキーワード指定: 自動化の目的に反する
