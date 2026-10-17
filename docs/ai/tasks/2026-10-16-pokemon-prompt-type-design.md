# 2026-10-16: 項目3「ポケモンプロンプトタイプ追加」の詳細設計

**Status**: 完了（詳細設計完了・実装はバックログ P2 #17 に保留）
**Next Action**: 保留。J1〜J5 の判断が確定したら、実装タスクとして分割・着手

## 意図 / 背景

バックログ P2 #17（新プロンプトタイプ「ポケモン」追加）の詳細設計を検討する。2026-10-16 の検討タスク（`2026-10-16-pokemon-story-backlog-consideration.md`）で「詳細設計は要検討」とされた項目3を、正確なコード調査に基づき詳細設計する。本タスクは「設計検討（調査＋判断ポイント整理＋推奨方針）」のみ。実装はユーザーの判断後、別タスクとして行う。

## 調査結果（現状の正確な把握）

### プロンプトタイプの決定フロー
- `generate_article.py:479`: `prompt_type = os.environ.get("PROMPT_TYPE", "default")` — **ランダム選定ロジックは存在しない**。全て env 変数で固定。
- `.github/workflows/deploy.yml`: 47行（fetch）/ 90行（generate）で `PROMPT_TYPE: "kemono_story"` をハードコード。
- 既存のプロンプトタイプ（記事生成用）: `default` / `ai_deep` / `kemono_story`（テンプレート: `scripts/prompts/` の `default.txt` / `ai_deep.txt` / `kemono_story.txt`）。
- 精製テンプレート: `refine_tech.txt` / `refine_story.txt`（2-pass 用、`refine_content` が prompt_type で選択）。

### 重要: 既存タスクファイルの補正
- `PROMPT_CATEGORIES` は **`scripts/fetch_topics.py:849`** に存在（gemini.py ではない、2026-10-16 検討時の記載は誤り）。
- `PROMPT_CATEGORIES = {"default": ["tech"], "ai_deep": ["tech"], "kemono_story": ["kemono"]}` — "pokemon" キーなし。
- `by_category` のキー: `tech` / `kemono` / `pokemon` / `other`（`fetch_topics.py:951-956`）。

### ポケモンデータソース（既に実装済み）
- RSS 4フィード（`fetch_topics.py:109-128`）: PokéCommunity Art Studio / PokeBeach News / PokemonBlog / PocketMonsters — 全て `category: "pokemon"`。
- e621: `{"tags": "pokemon rating:safe order:date", "category": "pokemon"}`（`fetch_topics.py:73`）。ただし `NON_TREND_SOURCES = {"e621"}`（85行）で e621 はトレンド出力から除外（キャラクター特徴集計専用）。
- GitHub: `{"query": "pokemon+language:typescript", "category": "pokemon"}`（143行）。
- → ポケモンデータは `by_category["pokemon"]` に流入するが、`PROMPT_CATEGORIES` に "pokemon" が無い＋deploy.yml が kemono_story 固定のため、**日次パイプラインでは未収集・未利用**。

### prompt_type による分岐箇所（pokemon が「それ以外」に落ちる影響）
1. `trends.py:200 _categories_for_prompt_type`: 物語系→`["kemono"]`、`default`→`["tech"]`、それ以外→`["tech","kemono"]`。**pokemon は `["tech","kemono"]` に落ちる（不自然）**。
2. `gemini.py:46 refine_content`: 物語系→`refine_story`、それ以外→`refine_tech`。pokemon は `refine_tech`。
3. `generate_article.py:141 build_ng_instruction`: 物語系→物語系 ng、それ以外→通常 ng。pokemon は通常 ng。
4. `generate_article.py:182 resolve_kemono`: `kemono_params = _randomize_kemono_params() if prompt_type == "kemono_story" else {}`。**pokemon は `kemono_params = {}`**（target_genres も None）。
5. `generate_article.py:357 apply_frontmatter_fields`: `if prompt_type == "kemono_story" and kemono_params` → pokemon は tags 自動生成スキップ（Gemini 出力の tags を使用）。
6. `generate_article.py:396 postprocess_content`: `skw = _kemono_affiliate_keywords(kemono_params) if prompt_type == "kemono_story" and kemono_params else None` → pokemon は None（フォールバックで記事本文から抽出）。
7. `affiliate.py:165 _improve_keyword`: 物語系→そのまま、default→「書籍/関連グッズ」付与、それ以外→そのまま。pokemon はそのまま。
8. `affiliate.py:671 _resolve_affiliate_keywords`: 物語系→「ライトノベル おすすめ」フォールバック、それ以外→「プログラミング 入門書」。pokemon は「プログラミング 入門書」（不自然）。
9. `meta.py:86,117 story_types = {"kemono_story","novel","story"}`: 同系統被り防止の物語系判定。pokemon は物語系に含まれない。
10. `geninfo.py:164 show_e621 = bool(e621_info) and prompt_type == "kemono_story"`: e621 ブロックは kemono_story のみ表示。pokemon では非表示（既存挙動で問題なし）。
11. `characters.py:93 _select_character_features(target_genres)`: pokemon は `target_genres=None` で全ジャンル（kemono 系）の e621 データから2投稿選出 → `e621_info` を返す（プロンプト注入はされるが、e621 ブロック表示は kemono_story のみ）。

### テンプレートの placeholder 構造（重要）
- `build_prompt` は `template.format(ng_instruction=..., pub_date_str=..., character_features_instruction=..., extra_rule_text=..., **kemono_params)` を実行（`generate_article.py:200-206`）。
- **pokemon は `kemono_params={}` なので、pokemon.txt で使える placeholder は `ng_instruction` / `pub_date_str` / `character_features_instruction` / `extra_rule_text` の4つのみ**。`kemono_story.txt` の `{char_type}` / `{world_setting}` / `{relationship_text}` 等は使えない（KeyError）。
- `default.txt` は `ng_instruction` / `pub_date_str` のみ使用（参考）。

## 設計判断ポイント（ユーザー確認が必要）

### J1. ポケモン記事の「性格」（最重要・他を左右する）
- **(a) 物語系**（kemono_story と同種の短編物語 + character_1/2 + IMAGE_PROMPT）:
  - `refine_content` → `refine_story`
  - `build_ng_instruction` → 物語系 ng
  - `story_types` / `LIMITS_BY_TYPE` → 物語系扱い
  - `_improve_keyword` → そのまま（グッズ検索）
- **(b) 解説・ニュース記事系**（default と同種の解説記事 + 比較表 + FAQ）:
  - `refine_content` → `refine_tech`
  - `build_ng_instruction` → 通常 ng
  - 物語系判定に追加しない
- **推奨: (a) 物語系**。理由:
  - ポケモン記事は物語・ファンタジーとして自然（2026-10-16 検討で「ケモノとは別のフォーマットのポケモン記事」が目的）。
  - 既存のポケモンデータソース（RSS: ポケモンニュース・アート / GitHub: ポケモン関連）は物語・コンテンツ素材として活用しやすいため。
  - 解説記事系（default）は技術・AI 特化でポケモンと不整合。

### J2. ランダムプロンプトタイプ選定の有無
- **(a) 導入しない**: pokemon は固定で別途トリガー（`workflow_dispatch` の input で `PROMPT_TYPE` を指定）。deploy.yml 変更は fetch/generate の `PROMPT_TYPE` を input 参照にする程度。
- **(b) 導入する**（2026-10-16 検討の提案）:
  - `config.py` に `PROMPT_TYPE_WEIGHTS` 追加（例: `{"kemono_story": 60, "pokemon": 25, "default": 15}` 要調整）。
  - `generate_post` で env 未指定時に重み付きランダム選定、env 指定時はそれを優先（デバッグ用オーバーライド保持）。
  - deploy.yml の `PROMPT_TYPE: "kemono_story"` ハードコードを撤去（ランダム有効化）。
  - **fetch/generate の整合（鶏と卵問題）**: fetch は generate より前に実行されるため「どのカテゴリを取るか」を prompt_type で決められない → **fetch は全カテゴリ取得**（`--prompt-type` 非指定 → latest.json が全カテゴリ）。generate がランダム選定後に `_categories_for_prompt_type` でフィルタ。代償: 日次 fetch の API 呼び出し増（全フィード・全 e621 クエリ）だが 12h キャッシュ内・許容範囲。
- **推奨: (b) ランダム選定導入**（コンテンツ多様化の観点で効果大。ただし deploy.yml 変更を伴うため、ユーザーの判断待ち）。

### J3. `PROMPT_CATEGORIES["pokemon"]` の収集カテゴリ
- **(i) `["pokemon"]` のみ**（ポケモン専業。ポケモン記事に tech/kemono トレンドを混ぜない）
- **(ii) `["kemono","pokemon"]`**（ケモノ系＋ポケモン系併用、2026-10-16 検討の提案）
- **推奨: (i) `["pokemon"]` のみ**。理由: ポケモン記事に tech トレンドは不自然（J1=物語系なら kemono も不要）。ただし (ii) も「ケモノ系ポケモン」を想定するなら選択肢。

### J4. 被り防止の系統（`story_types`）
- ** pokemon を物語系（`story_types`）に含めるか**（J1 連動）。
  - 含める（J1=(a) 推奨）: pokemon と kemono_story の被り防止が効く（物語系として扱う）。`LIMITS_BY_TYPE["pokemon"]=5`。
  - 含めない: pokemon は独立系統として扱う（kemono_story との被り防止なし）。

### J5. e621 参考データの活用
- pokemon では `_select_character_features` が `target_genres=None` で全ジャンル（kemono 系）の e621 データから2投稿選出 → `character_features_instruction` がプロンプト注入される。
- **判断: pokemon では e621 参考データを注入しない**（kemono 系データと不整合・版権 IP リスク）。
  - 対処: `build_prompt` で pokemon 時は `character_features_instruction` を空文字にする、または `resolve_kemono` で pokemon 時に e621 参照をスキップ。
  - 影響: pokemon.txt の `{character_features_instruction}` placeholder は空になる（テンプレートに含めるが空注入）。

## 推奨方針（J1=(a) 物語系 / J2=(b) ランダム選定 / J3=(i) pokemon のみ / J4=物語系含める / J5=e621 非注入）

### 変更箇所一覧

| # | ファイル | 変更内容 | 判断ポイント |
|---|---------|---------|-------------|
| 1 | `scripts/prompts/pokemon.txt`（新規） | ポケモン物語テンプレート。placeholder: `{ng_instruction}` / `{pub_date_str}` / `{character_features_instruction}`（J5 で空）/ `{extra_rule_text}`（空）。frontmatter: `prompt_type: "pokemon"` | J1 |
| 2 | `scripts/article/config.py` | `PROMPT_TYPE_WEIGHTS = {"kemono_story": 60, "pokemon": 25, "default": 15}` 追加（要調整） | J2(b) |
| 3 | `scripts/generate_article.py` | `generate_post`: env 未指定時に `PROMPT_TYPE_WEIGHTS` で重み付きランダム選定。`build_ng_instruction`: 物語系判定に `"pokemon"` 追加。`build_prompt`: pokemon 時は `character_features_instruction` を空にする（J5） | J1, J2(b), J5 |
| 4 | `scripts/article/gemini.py` | `refine_content`: 物語系判定 `("kemono_story","novel","story")` に `"pokemon"` 追加 | J1 |
| 5 | `scripts/article/trends.py` | `_categories_for_prompt_type`: `if prompt_type == "pokemon": return ["pokemon"]` 追加 | J3(i) |
| 6 | `scripts/article/affiliate.py` | `_improve_keyword`: 物語系判定に `"pokemon"` 追加。`_resolve_affiliate_keywords`: フォールバックに pokemon 用（「ポケモン おすすめ」等） | J1 |
| 7 | `scripts/article/meta.py` | `story_types` に `"pokemon"` 追加。`LIMITS_BY_TYPE` に `"pokemon": 5` 追加 | J4 |
| 8 | `scripts/fetch_topics.py` | `PROMPT_CATEGORIES` に `"pokemon": ["pokemon"]` 追加 | J3(i) |
| 9 | `.github/workflows/deploy.yml` | 47行/90行の `PROMPT_TYPE: "kemono_story"` を撤去（ランダム有効化）。fetch ステップは `--prompt-type` 非指定（全カテゴリ取得） | J2(b) |
| 10 | `scripts/article/geninfo.py` | 既存挙動で pokemon では e621 ブロック非表示（`show_e621 = ... and prompt_type == "kemono_story"`）→ **変更不要** | — |

### テスト追加
- `test_generate_article.py`:
  - `PROMPT_TYPE_WEIGHTS` の sum 検証（J2(b) なら `sum == 100` 制約の可能性。ただし既存の `WORLD_SETTING_WEIGHTS` とは独立なので任意）
  - `_categories_for_prompt_type("pokemon") == ["pokemon"]` テスト
  - `build_ng_instruction` の pokemon 物語系テスト
  - `refine_content` の pokemon → `refine_story` テスト
  - `generate_post` のランダム選定テスト（env 未指定時に `PROMPT_TYPE_WEIGHTS` から選定される）
  - `build_prompt` の pokemon → `character_features_instruction` 空テスト（J5）

### リスク・注意点
- **テンプレートの placeholder 制限**: pokemon.txt は `kemono_params={}` なので `{char_type}` 等は使えない（KeyError）。`{ng_instruction}` / `{pub_date_str}` / `{character_features_instruction}` / `{extra_rule_text}` のみ。
- **J2(b) ランダム選定**: deploy.yml 変更を伴う。fetch が全カテゴリ取得になる（API 呼び出し増）。ただし 12h キャッシュ内。
- **J5 e621 非注入**: `build_prompt` の pokemon 分岐追加が必要。既存の kemono_story 挙動には影響しない。
- **deploy.yml の fetch ステップ**: `--prompt-type` 非指定で全カテゴリ取得。ただし `PROMPT_CATEGORIES` に "pokemon" が無い限り `--prompt-type pokemon` は使えない（J3(i) で追加）。
- **既存記事への影響なし**: pokemon は新プロンプトタイプのため、既存の default / ai_deep / kemono_story 記事には影響しない。

## 判断待ち（ユーザー確認事項）

1. **J1**: ポケモン記事は「物語系（a）」か「解説記事系（b）」か。
2. **J2**: ランダムプロンプトタイプ選定は「導入する（b）」か「導入しない（a）」か。
3. **J3**: `PROMPT_CATEGORIES["pokemon"]` は `["pokemon"]` のみ（i）か `["kemono","pokemon"]`（ii）か。
4. **J4**: pokemon を物語系（`story_types`）に含めるか（J1 連動）。
5. **J5**: pokemon では e621 参考データを注入しない（推奨）で問題ないか。
6. **J2(b) のウェイト**: `PROMPT_TYPE_WEIGHTS` の初期値（例: kemono_story 60 / pokemon 25 / default 15）で問題ないか。

## Verification

（未実施 — 実装待ち。実装後 `pytest scripts/tests/ -v` で全テスト通過を確認）
