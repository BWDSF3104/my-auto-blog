# タグ生成ロジックの構造化リファクタ（体型タグ分割・カンマバグ修正）

- 日付: 2026-10-09
- Status: 完了（コミット未実施・ユーザー指示待ち）
- 関連: `2026-10-09-genre-integration.md`（V6 build-and-deploy FAIL の `/` 置換対応が本タスクの引き金）

## 背景

最新記事 `2026-10-09-223016-auto-post` の tags が不自然だった:

```
tags: ["ケモノ", "動物と獣人のハーフ・動物", "ファンタジー", "BL", "、ライバル関係"]
```

- `動物と獣人のハーフ・動物`: キャラ体型タグが結合タグのままで分割されていない（ジャンルは「と」分割されているのに体型だけ分割漏れ）
- `、ライバル関係`: `extra_text`（プロンプト文への自然な接続のための「、」接頭）がそのままタグに混入
- 文字列の結合→分割を往復する設計自体が非効率（スクリプト内で最初から構造化データで保持できる）

調査中に同一箇所の潜在バグを発見:
- `generate_post` で `WORLD_SETTING_GENRE_MAP.get(kemono_params.get("world_setting", ""))` が**表示文字列**（`ファンタジー` 等）をキーに参照していたが、マップのキーは **`world_setting_key`**（`fantasy` 等）。恒常的に `None` となり、ジャンルベースのトレンド優先選択（genre-integration 実装）がサイレント無効化されていた。

## 実装内容

### `scripts/generate_article.py`

- `CHAR_TYPE_WEIGHTS`: 値を文字列 → **体型タグリスト**に変更（例: `("獣人 / 動物と獣人のハーフ", 10)` → `(["獣人", "動物と獣人のハーフ"], 10)`）
- `_KEMONO_WORLD_TAGS` 新設: 世界設定キー → タグリスト（`fantasy+sf → ["ファンタジー", "SF"]`）。旧 `_KEMONO_WORLD_TEXT`（`と`結合）は `_KEMONO_WORLD_TEXT = {key: "と".join(tags)}` で派生
- `_KEMONO_EXTRA_TAGS` 新設: 追加設定キー → タグ（`none: ""`, `rival: "ライバル関係"`）。旧 `extra_text`（「、」接頭）は `_KEMONO_EXTRA_TEXT = {key: f"、{text}" if text else ""}` で派生
- `_randomize_kemono_params` の戻り値を2層構成に:
  - 構造化データ: `char_types`（リスト）/ `world_tags`（リスト）/ `extra_tag`（文字列・カンマなし）
  - プロンプト表示用: `char_type`（`" / " 結合`）/ `world_setting`（`と`結合）/ `extra_text`（「、」接頭）— テンプレート `kemono_story.txt` への渡り値は従来どおり
- `_build_kemono_tags(kemono_params)` 新設: `ケモノ` → `char_types` → `world_tags` → 関係性（`_KEMONO_RELATIONSHIP_AFFILIATE`）→ `extra_tag`（空なら省略）の順にタグ生成。文字列の分割・結合は行わない
- `generate_post` のタグブロック: 旧のインライン結合・`split("と")`・`replace(" / ","・")` を `_build_kemono_tags()` 呼び出しに置換。`/` 置換は Astro `[tag].astro` ルート衝突防止の安全策として `t.replace("/","・")` 1行に簡略化
- `_kemono_affiliate_keywords` / `_rakuten_api_keywords`（kemono分岐）: `world_setting.split("と")` → `world_tags` 直接使用
- **バグ修正**: `target_genres = WORLD_SETTING_GENRE_MAP.get(kemono_params.get("world_setting_key", ""), []) or None`（`world_setting` → `world_setting_key`）

### `scripts/tests/test_generate_article.py`

- `TestRandomizeKemonoParams`: `test_return_keys` に新キー3件追加、`test_char_type_in_options` → `test_char_types_in_options`（リスト+結合一致）、`test_world_tags_consistent_with_display` / `test_extra_tag_consistent_with_display` 新規
- `TestBuildKemonoTags` 新設（7件）: 生成順、体型タグ分割、世界設定分割、カンマ接頭なし、空 extra 省略、関係性省略、単体型
- `TestKemonoAffiliateKeywords` 新設（3件）: カスケード順、関係性なし、「と」分割されない
- `TestRakutenApiKeywords`: 合成 `kemono_params` を `world_setting` → `world_tags` 形式へ更新（2件）

### 既存記事のデータ修正

- `src/content/posts/2026-10-09-223016-auto-post.md` の tags を修正済み:
  `["ケモノ", "動物と獣人のハーフ", "動物", "ファンタジー", "BL", "ライバル関係"]`

## Verification (2026-10-09)

- `pytest scripts/tests/` → **297 passed** (3.90s)（285 → 297、新規12件）
- 新テスト13件（BuildKemonoTags 7 + KemonoAffiliateKeywords 3 + 整合性2 + char_types1）すべて通過
- タグ生成スモーク: 全96種の組み合わせ（char×world×rel×extra）で出力確認、カンマ接頭・結合タグなし
- プロンプトテンプレート `kemono_story.txt` の `str.format(**kemono_params)` 20回スモーク: 新キー（リスト値）が出力に漏れず、従来文（「獣人のキャラクターたちが活躍する…」「…からランダムにテーマを選択」）が維持
- `npm run build` → **131 page(s) built** (8.95s) 成功。新タグページ `/tags/動物と獣人のハーフ/`・`/tags/ライバル関係/` 生成確認
- ビルト出力 `dist/posts/kagerou-no-kairou-to-kiba-no-chikai/index.html` のタグ確認: `ケモノ | 動物と獣人のハーフ | 動物 | ファンタジー | BL | ライバル関係`

## 補足

- 旧形式タグ（`ファンタジーとSF` 等）を持つ既存記事はそのまま維持（遡及再生成は実施せず）
- `target_genres` 修正により、次回以降の記事生成でジャンルベースのトレンド・版権優先選択が初めて実効する
- Commits: 未コミット（ユーザー指示待ち）
