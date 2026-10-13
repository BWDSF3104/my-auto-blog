# NSFW Filter for e621

**Date**: 2026-09-29

**Decision**: Filter explicit content at collection time in `fetch_topics.py`.

**Reason**: e621 contains explicit-rated posts that should not appear in article prompts for non-kemono content. Filtering at collection prevents inappropriate content from entering the pipeline.

**Rejected Alternatives**:
- 生成時にフィルタ: 不要なコンテンツがプロンプトに注入されるリスク
- e621の完全な排除: kemono/pokemonカテゴリで有用なSafeコンテンツが失われる
