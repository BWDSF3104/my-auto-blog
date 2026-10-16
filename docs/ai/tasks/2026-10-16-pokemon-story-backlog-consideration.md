# 2026-10-16: 新バックログ3項目の検討（直前ジャンル重複防止 / ポケモンジャンル追加 / ポケモンプロンプトタイプ追加）

**Status**: 完了（2026-10-16、検討＋項目2実装・バックログ登録完了）
**Next Action**: なし（項目1・項目3はバックログに保留。P3 #15 / P2 #17）

## 意図 / 背景

ユーザー提示の3項目を `docs/ai/backlog.md` に登録（P2 #11〜#13）し、それぞれを調査・検討する。本タスクは「検討（調査＋設計提案＋判断ポイント整理）」のみ。実装はユーザーの判断後、別タスクとして行う。

1. **直前ジャンルとの被りを防ぐ措置**（ストーリージャンルのみ、それ以外は特に防止しない）
2. **新たにストーリージャンルに「ポケモン」を追加**
3. **新たなプロンプトタイプ「ポケモン」を追加**（＋プロンプトタイプのランダム選定機能、RSSはケモノ系に加えてポケモン系も取得、e621はpokemonタグ絞り込み取得）

## 調査結果（現状）

### 項目1: 直前ジャンル重複防止
- ストーリーの「ジャンル」＝ `world_setting`（12種、`WORLD_SETTING_WEIGHTS` で重み付きランダム）→ `WORLD_SETTING_GENRE_MAP` 経由で正統7ジャンル（sf/fantasy/cyberpunk/action/slice_of_life/mystery/historical）にマッピング。
- 新ストーリーの world_setting が直前ストーリーと同一になる防止機構は**現状なし**。
- frontmatter には world_setting / ジャンルの明示フィールドが**ない**。世界設定は `tags` に日本語タグ（例: 「歴史」「スペースオペラ」）として入るのみ。
- `article/meta.py` の `get_recent_meta_by_type` / `get_existing_posts` は title・pub_date・prompt_type のみ抽出（tags 非抽出）。
- 連続同一 world_setting 確率 ≈ 10.5%（fantasy=21/100 が支配的）。

### 項目2: 「ポケモン」ジャンル追加
- 追加箇所: `WORLD_SETTING_WEIGHTS["pokemon"]` / `_KEMONO_WORLD_TAGS["pokemon"]` / `WORLD_SETTING_GENRE_MAP["pokemon"]`（`article/config.py`）。
- 正統7ジャンルに「pokemon」が無いため、`WORLD_SETTING_GENRE_MAP` のマッピング先が未定（判断ポイント）。

### 項目3: 「ポケモン」プロンプトタイプ追加
- **重要**: ポケモンデータソースは `fetch_topics.py` に**既に実装済み**:
  - RSS: 4フィード（PokéCommunity Art Studio / PokeBeach News / PokemonBlog / PocketMonsters）、category=pokemon（109〜128行）
  - e621: `{"tags": "pokemon rating:safe order:date", "category": "pokemon"}`（73行）
  - ただし `PROMPT_CATEGORIES`（849行）に "pokemon" キーが無く、deploy.yml が `PROMPT_TYPE=kemono_story` をハードコードするため、**日次パイプラインではポケモンデータは未収集**。
- プロンプトタイプ追加の変更箇所（約8箇所）:
  - 新テンプレート `scripts/prompts/pokemon.txt`
  - `article/gemini.py` `refine_content`（story系判定に追加）
  - `article/affiliate.py` `_improve_keyword` / `_rakuten_is_relevant`
  - `article/meta.py` `story_types` / `LIMITS_BY_TYPE`
  - `generate_article.py` `resolve_kemono` / `build_ng_instruction`
  - `article/trends.py` `_categories_for_prompt_type`
  - `fetch_topics.py` `PROMPT_CATEGORIES`
  - `.github/workflows/deploy.yml`（ランダム選定のため）
- ランダム選定: 現状 `prompt_type = os.environ.get("PROMPT_TYPE", "default")`（`generate_article.py:479`）。deploy.yml が kemono_story をハードコード（47行/90行）。
- **設計上の課題**: fetch（generate より前に実行）が「どのカテゴリを取るか」を prompt_type で決めるが、ランダム選定は generate 時に行うため鶏と卵。→ fetch は全カテゴリ取得（`--prompt-type` 非指定）、generate 側がランダム選定＋カテゴリフィルタで解決（下記）。

## 検討（設計提案）

### 項目1: 直前ジャンル重複防止
- **直前ジャンルの取得方法**（2案）:
  - [A] tags 逆引き: `get_existing_posts` に tags 抽出を追加し、直前ストーリーの tags から world タグを逆引き（`_KEMONO_WORLD_TAGS` 逆マッピング）で world_setting を特定。→ frontmatter 形式を変えず低リスク。ただし「fantasy+sf」は2タグでやや曖昧（実害小）。
  - [B] 新 frontmatter フィールド `world_setting`: `apply_frontmatter_fields` でキーを記録し、次回読み取り。→ 明示的・堅牢。ただし既存記事に無いためフォールバック（tags 逆引き or 除外スキップ）が必要。
- **防止手法**: **硬排除（一致したら再抽選）を推奨**。既存の最大100回リトライループ（`_randomize_kemono_params`）に `exclude` 引数を足すだけ。ソフトな重み減衰は重複排除を保証しないため非推奨。
- **対象**: ストーリー系のみ（kemono_story）。world_setting を持つのはストーリー系のみのため、自然に「それ以外は防止しない」を満たす。
- **推奨**: 低リスク重視なら [A]、長期的な堅牢性重視なら [B]。判断待ち。

### 項目2: 「ポケモン」ジャンル追加
- 追加: `WORLD_SETTING_WEIGHTS["pokemon"]`（重みは 8 程度を提案・要調整）、`_KEMONO_WORLD_TAGS["pokemon"]=["ポケモン"]`、`WORLD_SETTING_GENRE_MAP["pokemon"]=[?]`。
- **判断ポイント**: `WORLD_SETTING_GENRE_MAP["pokemon"]` の先。正統7ジャンルに該当が無いため、
  - (i) 既存にマッピング（例: `["action"]` / `["slice_of_life"]`）
  - (ii) 新ジャンル "pokemon" を7に追加
  - (iii) `["fantasy","action"]`（冒険系）
  - 影響は主に e621 版権のジャンルスコアリングとトレンドフィルタ。判断待ち。

### 項目3: 「ポケモン」プロンプトタイプ追加
- (a) 新テンプレート `pokemon.txt` + 上記約7箇所のプロンプトタイプ登録。
- (b) **ランダム選定**: `config.py` に `PROMPT_TYPE_WEIGHTS` 追加。`generate_post` で env が空なら重み付きランダム選定、env 指定時はそれを優先（デバッグ用オーバーライド保持）。deploy.yml の `PROMPT_TYPE` ハードコードを撤去（=ランダム有効化）。
  - **fetch/generate の整合**: fetch は全カテゴリ取得（`--prompt-type` 非指定 → latest.json が全カテゴリ）。generate がランダム選定後に `_categories_for_prompt_type` でフィルタ。→ 実現可能。代償: 日次 fetch の API 呼び出し増（全フィード・全 e621 クエリ）だが 12h キャッシュ内・許容範囲。
- (c) **RSS/e621 ポケモン取得**: データソースは既存のため、`PROMPT_CATEGORIES` に `"pokemon": ["kemono","pokemon"]`（ケモノ系＋ポケモン系）と `_categories_for_prompt_type` の分岐追加のみで済む。**新規データソース開発は不要**。
- **推奨**: (c) は低コストで即反映可。(b) のランダム選定は deploy.yml 変更を伴う。(a) はテンプレート設計が中心。

### 項目2 と 項目3 の関係（重要）
- 項目2 = ポケモンを kemono_story の**テーマ（world_setting）として**追加（ケモノ/獣人スタイルのポケモン設定ストーリー）。
- 項目3a = ポケモンを**別プロンプトタイプ（独自テンプレート）として**追加。
- 両者は「ポケモン系ストーリー」を重複して表現しうる。方針を明確化すべき:
  - 「既存ケモノスタイルのポケモン設定ストーリー」が目的 → **項目2のみ**で十分（項目3a不要・低コスト）。
  - 「ケモノとは別のフォーマットのポケモン記事」が目的 → **項目3a**。
  - 項目3b（ランダム選定）は「プロンプトタイプが複数存在する」ことが前提。項目2のみで止めるならランダム選定の対象が増えない（kemono_story のみ維持）。
- 判断待ち: 項目2と項目3aは**どちらか**、还是**両方**か。

## 判断待ち（ユーザー確認事項）

1. **項目1**: 直前ジャンルの取得は [A] tags逆引き か [B] 新フィールド `world_setting` か。防止手法は硬排除で問題ないか。
2. **項目2**: `WORLD_SETTING_GENRE_MAP["pokemon"]` のマッピング先（(i) 既存 / (ii) 新ジャンル追加 / (iii) 複数）。weight の目安。
3. **項目2 vs 3a**: ポケモンは「ケモノ系テーマ」として（項目2）、「別プロンプトタイプ」として（項目3a）、还是その両方か。
4. **項目3b**: ランダム選定は「env 未指定時のみランダム / 指定時は優先」で問題ないか。deploy.yml の PROMPT_TYPE 撤去に問題ないか。
5. **項目3c**: `PROMPT_CATEGORIES["pokemon"]` は `["kemono","pokemon"]`（ケモノ系も併用）で問題ないか。

## ユーザー判断・実施結果（2026-10-16）

ユーザーのトリアージ判断（2026-10-16）:
- **項目1**（直前ジャンル重複防止）: 低優先度 → バックログ P3 #15 に保留（実装しない）。
- **項目2**（ポケモンジャンル追加）: 低コストにストーリージャンル(world_setting)として**今すぐ実装**。
- **項目3**（ポケモンプロンプトタイプ追加）: 項目2と無関係・別プロンプトタイプ追加の話 → バックログ P2 #17 に保留（詳細設計は要検討）。

### 項目2 実装内容（低コスト: config の 3 定数＋テスト1件更新のみ）

`scripts/article/config.py`:
- `WORLD_SETTING_WEIGHTS`: `("pokemon", 8)` を追加。合計100維持のため `("fantasy", 21)→("fantasy", 13)` に調整（test_generate_article.py:2657 の `sum==100` 制約）。
- `WORLD_SETTING_GENRE_MAP`: `"pokemon": ["action"]` を追加（正統7ジャンルに pokemon が無いため、既存の `action` に低コストでマッピング。e621 版権スコアリングへ `target_genres=["action"]` を渡す）。
- `_KEMONO_WORLD_TAGS`: `"pokemon": ["ポケモン"]` を追加（`_KEMONO_WORLD_TEXT` は自動導出）。

`scripts/tests/test_generate_article.py`:
- `test_world_setting_in_options`（2092行）のハードコード12種に「ポケモン」を追加（13種目）。

効果: kemono_story の world_setting 抽選に「ポケモン」が 8% で混入。frontmatter tags に「ポケモン」が付与され、ケモノ/獣人スタイルのポケモン設定ストーリーが生成可能になる。

### 項目2 と 項目3 の関係（再確認）
- 項目2 = kemono_story の**テーマ（world_setting）として**ポケモン追加（ケモノスタイルのポケモン設定ストーリー）。→ **実施済み**。
- 項目3 = ポケモンを**別プロンプトタイプ（独自テンプレート）として**追加。→ 項目2と独立。バックログ P2 #17 に保留。

## Verification

- 項目2 実装（Python 変更）: `pytest scripts/tests/ -v` → **404 passed in 7.29s**（初回 1 failed / 403 passed → `test_world_setting_in_options` に「ポケモン」追加で修正 → 404 passed）
- バックログ・current-task.tsv の変更は `docs/ai/` のみ
- 未コミット（ユーザーのコミット指示待ち）
