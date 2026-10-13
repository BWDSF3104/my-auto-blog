# 記事末尾の「生成情報」セクションは Python 側で本文に直接追記

**Date**: 2026-10-10

**Decision**: `generate_article.py` が `<details class="gen-info">` HTML を生成し本文末尾に追記。frontmatter 拡張+Layout 描画は不採用。`_append_trending_topics()` を 3→4 タプル化。表示要素なしならセクション非表示。

**Reason**: ユーザー指示「Pythonスクリプト側で行う」。本文直接追記で既存記事影響ゼロ・バックフィル不要。`<details>` + h2〜h4 不使用で TOC/JSON-LD に影響しない。
