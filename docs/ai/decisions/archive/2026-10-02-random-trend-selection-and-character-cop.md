# Random Trend Selection and Character/Copyright Tag Expansion

**Date**: 2026-10-02

**Decision**: Remove "pokemon" from `kemono_story` prompt type categories and change trend selection from "top 5 per category" to "random 2 items total across selected categories". Expand e621 character feature collection to include `character` and `copyright` tags.

**Reason**: Pokemon content was polluting kemono story articles with irrelevant keywords. Random selection reduces redundancy when multiple categories overlap. Character and copyright tags from e621 provide valuable context for affiliate product recommendations, enabling the AI to suggest official merchandise and related products.

**Rejected Alternatives**:
- pokemonカテゴリを維持: 将来の専用プロンプトタイプで対応するため、kemono_storyからは除外
- 固定数のトレンド選択: ランダム化によりカテゴリ間の重複を減らし、多様性を向上

**Impact**:
- `fetch_topics.py`: `PROMPT_CATEGORIES["kemono_story"]` から "pokemon" を削除、`CHARACTER_FEATURE_CATEGORIES` に "character", "copyright" を追加、`_aggregate_and_save_character_features()` に character/copyright カウンターを追加
- `generate_article.py`: `import random` 追加、`_append_trending_topics()` を「全カテゴリをプールしてランダム2件」に書き換え、`_load_character_features()` に character/copyright データの注入とアフィリエイト指示を追加
- `data/character_features.json`: "characters" と "copyrights" のフィールドが追加される

---
*以下は 2026-10-04 に decisions.md からアーカイブ*
