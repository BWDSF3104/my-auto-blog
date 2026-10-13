# kemono_story 記事の TF/TSF タグ欠落

**Date**: 2026-10-13
**Status**: 解決済

**症状**: 2026-10-08 以降、kemono_story 記事の frontmatter tags に TF/TSF タグが一切付与されない。直近3記事（10-11〜10-13）は全て変身設定 TSF（生成情報「変身: TSF（性転換フィクション）」）だが、tags は `["ケモノ", "獣人", "動物", "日常", "恋愛"]` 等。10-08 以前の記事（Gemini 生成タグ）には "TF" が存在した（10-06・10-07）。

**原因**: コミット `c973af4`（2026-10-08 21:29）で kemono_story の frontmatter tags を Gemini 生成から `_build_kemono_tags()` によるスクリプト生成に切替えた際（`generate_article.py:320-327` が `tags:` 行を全面上書き）、体型 / 世界 / 関係性 / 追加設定は収録したが**変身次元（transform_key: tf/tsf/tf+tsf）のタグが未追加**になっていた。タグ設定の入れ忘れ（退行ではない）。

**影響**: 10-08 以降の全 kemono_story 記事（約25%が tf/tsf/tf+tsf 設定）で TF/TSF タグ欠落。TF/TSF タグページが未作成のまま。

**修正方針**: `config.py` に `_KEMONO_TRANSFORM_TAGS`（tf→"TF"、tsf→"TSF"、tf+tsf→["TF","TSF"]）を追加し、`image.py` の `_build_kemono_tags` で `transform_key` 分岐を組み込む。2026-10-13 タスク（`tasks/2026-10-13-kemono-backlog-triage.md`）で修正済み。既存記事の遡及タグ修正は未実施。
