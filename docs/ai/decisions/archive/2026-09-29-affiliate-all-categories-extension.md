# Affiliate All-Categories Extension

**Date**: 2026-09-29

**Decision**: Extend affiliate keyword extraction to all categories (tech, kemono, pokemon).

**Reason**: Original design only extracted keywords from tech category. All recent articles use kemono_story prompt type, so affiliate links always fell back to generic tag-based keywords ("Kemono"). Kemono/pokemon topics have merchandise potential (figures, art books, games).

**Rejected Alternatives**:
- techカテゴリのみを維持: kemono記事で常にフォールバックキーワードになる
- カテゴリごとの個別設定: 複雑すぎて維持コストが高い
