# Project Structure

**Date**: 2026-09-28

**Decision**: Separate immutable rules (AGENTS.md) from changing knowledge (docs/ai/).

**Reason**: Claude Memory Bank pattern allows agents to distinguish between permanent constraints and evolving project state.

**Rejected Alternatives**:
- 単一ファイルに全て記録: 変更履歴が混在し、ルールの変更が追跡困難
- git commit message のみに依存: Agentが過去の文脈を読み込めない
