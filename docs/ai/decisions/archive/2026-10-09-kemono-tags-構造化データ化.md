# kemono_tags の構造化データ化（結合・分割往復の廃止）

**Date**: 2026-10-09

**Decision**: kemono パラメータを「構造化データ + プロンプト表示文字列」の2層構成に変更し、タグ生成を `_build_kemono_tags()` に集約。`CHAR_TYPE_WEIGHTS` の値を体型タグのリスト化、`_KEMONO_WORLD_TAGS` / `_KEMONO_EXTRA_TAGS` を一次データとし結合文字列は派生生成。`target_genres` キー不一致バグ修正。

**Reason**: 最新記事の tags が不自然だった。原因は (1) 体型タグは `replace(" / ","・")` のみで分割漏れ、(2) `extra_text` の「、」接頭がタグに混入。根本原因は「結合文字列を一次データとして扱い、用途ごとに分割・結合を往復させる」設計。併発: `WORLD_SETTING_GENRE_MAP` のキー不一致でジャンルベーストレンド選択がサイレント無効化。

**Rejected Alternatives**:
- タグブロック側の `split(" / ")` 追加のみ: 各所で個別の分割ロジックが残り継続的に壊れる
- `extra_text` から「、」を除去: プロンプト側の文脈が不自然になる
- 旧形式タグの遡及修正: 再生成コストとリンク切れリスク

**Impact**:
- `scripts/generate_article.py`: 複数関数変更
- pytest 297通過、`npm run build` 131ページ成功
