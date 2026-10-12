# Pythonスクリプトのリファクタリング（パッケージ分割 + 大関数分解）

**Status**: 進行中
**日付**: 2026-10-11
**ユーザー指示**: 長すぎるスクリプト・複雑すぎる関数の調査 → 分解案検討（管理のしやすさ考慮）→ 「パッケージ分割（推奨）」で実施

## 背景・調査結果

`ast` 解析による規模・複雑度監査（McCabe循環複雑度）:

| ファイル | 行数 | 備考 |
|---|---|---|
| `scripts/generate_article.py` | 3561 | 8以上の責務群が単一ファイルに混在 |
| `scripts/fetch_topics.py` | 1032 | 問題は `main()` に集中 |
| `scripts/genre_score.py` | 583 | やや超過（今回は対象外） |

第一優先関数（CC20超・長め）:

| 関数 | CC | 行数 | 位置 |
|---|---|---|---|
| `generate_post()` | 81 | 325 | `generate_article.py:3233` |
| `compose_image_prompt()` | 57 | 122 | `generate_article.py:877` |
| `main()`（fetch_topics） | 52 | 185 | `fetch_topics.py:844` |
| `inject_affiliate_links()` | 42 | 167 | `generate_article.py:1730` |
| `_append_trending_topics()` | 39 | 192 | `generate_article.py:2261` |
| `_build_generation_info_section()` | 30 | 119 | `generate_article.py:2455` |
| `_randomize_kemono_params()` | 29 | 65 | `generate_article.py:219` |
| `_select_character_features()` | 27 | 70 | `generate_article.py:614` |

## 制約（管理のしやすさの核心）

1. **プロダクション入口はファイル名固定**: `deploy.yml:50` `python scripts/fetch_topics.py` / `deploy.yml:89` `python scripts/generate_article.py` → 両ファイルは入口として残す
2. **サブプロセス起動**: `generate_article.py::_auto_fetch_topics` が `fetch_topics.py` をパス指定 subprocess で実行（`generate_article.py:2077`）
3. **テストが内部関数に強く結合**: `patch("generate_article.X")` 形式のモック多用（`_rakuten_search` 7 / `BASE_URL` 8 / `LOG_CLEANUP_DIRS` 8 / `SLUG_REDIRECTS_FILE` 7 / `_rakuten_load_cache` 6 / `requests` 6 / `DRAFTS_DIR` 6 / `Client` 4 等）。**関数を別モジュールへ移設すると patch 経路が壊れる**（mock が実コードに効かなくなる）ため、移設とテストの patch 経路更新はセットで実施
4. `conftest.py` の `collect_ignore = ["test_real_apis.py"]` により通常 pytest はオフラインスイートのみ

## 設計（`decisions.md` 2026-10-11 参照）

### generate_article.py → `scripts/article/` パッケージ

`generate_article.py` は薄い入口 + `generate_post()` パイプラインに縮約:

```
scripts/
├── generate_article.py     # 入口 + generate_post() パイプライン（__main__）
└── article/
    ├── __init__.py
    ├── config.py           # 定数群（MODELS_TO_TRY, 重み, GENRE_MAP, パス）
    ├── gemini.py           # client / generate_content_with_retry / refine_content / load_prompt_template
    ├── image.py            # kemonoパラメータ / 画像生成 / キャラ抽出 / compose_image_prompt / 本文画像
    ├── affiliate.py        # 楽天 / アフィリエイトリンク / 商品カード / キーワード抽出
    ├── trends.py           # TTL / auto_fetch / _append_trending_topics / trendログ
    ├── frontmatter.py      # frontmatter検証 / SEO / FAQ / speakable / description / slug生成
    ├── slug_links.py       # slugリダイレクト / 内部リンク
    └── meta.py             # 記事メタ / 直近タイトル / draft・affiliateログ / クリーンアップ
```

### generate_post() のステージ分解（CC81/325行 → 約70行/CC約12）

| ステージ関数 | 現行の担い手（行） |
|---|---|
| `build_ng_instruction(prompt_type, recent_titles, recent_metas)` | L3242-3284 重複防止指示生成 |
| `resolve_kemono(prompt_type) -> (params, target_genres)` | L3286-3288 |
| `generate_content(prompt, prompt_type)` | L3295-3350 pass1+pass2+draftメタ |
| `build_header_image(content, seed, ...)` | L3352-3377 キャラ抽出→画像合成→生成 |
| `apply_frontmatter_fields(content, ...)` | L3380-3472 image/slug/tags/trend_sources |
| `postprocess_content(content, ...)` | L3474-3499 本文画像・プレースホルダ・アフィリエイト・商品・内部リンク |
| `apply_seo_schemas(content)` | L3501-3516 FAQ/speakable |
| `finalize_and_save(content, ts)` | L3518-3557 検証→生成情報→保存→ログ掃除 |

### 他大関数の分解目標

- `compose_image_prompt`（CC57）→ `_compute_count_tag()` / `_build_char_block()` に分割 → CC約15
- `inject_affiliate_links`（CC42）→ `_resolve_keywords()`（3段フォールバック）/ `_build_links_html()` / `_build_rakuten_cards()` / `_build_main_cta_section()` → CC約10
- `_append_trending_topics`（CC39）→ `_load_topics_data()` / `_collect_candidates()` / `_select_candidates()` / `_build_trend_usage_log()` → CC約8
- `_build_generation_info_section`（CC30）→ ソース別ブロック生成器に分割 → CC約10
- `_randomize_kemono_params`（CC29）/ `_select_character_features`（CC27）→ 重み抽選とタグ合成を分離 → CC約10

### fetch_topics.py → ファイル内関数抽出（パッケージ化不要・低リスク）

| 新関数 | 現行 main 内の該当（行） |
|---|---|
| `collect_all_topics(categories) -> list[dict]` | L873-913 各 source の try/except 収集 |
| `build_output(all_topics, now) -> dict` | L915-989 カテゴリ整理+TTL継承+非トレンド排除（純粋関数） |
| `save_output(output, now) -> str` | L991-1022 tsファイル+latest.jsonコピー |
| `cleanup_old_topic_files(keep=10)` | L999-1009 |
| `main()` | 引数解析+上記呼出+表示（約40行・CC約5） |

`main()` が `fetch_topics.py` に残るため `test_fetch_topics.py` の `patch("fetch_topics.TOPICS_DIR")` 等はそのまま動作。

## 移行フェーズ（各フェーズ末に pytest 緑で止める）

> **コミット方針（2026-10-11 ユーザー承認）**: 各フェーズが pytest 緑の検証済み状態で確定したら、その境界で `git commit` + `git push` を実施（後段失敗時のロールバック点として）。メッセージは `refactor: <日本語>`。

| フェーズ | 内容 | リスク |
|---|---|---|
| 0 | ベースライン: `pytest scripts/tests/ -v` 実行・記録 | - |
| 1 | `fetch_topics.py` 関数抽出 + テスト更新 | 低 |
| 2 | `article/` 雛形 + `config.py` / `meta.py` 移設 + テスト更新 | 低 |
| 3 | `image.py` 移設 + テスト更新 | 中 |
| 4 | `affiliate.py` 移設 + テスト更新（patch 経路多） | 中 |
| 5 | `trends.py` / `frontmatter.py` / `slug_links.py` 移設 + テスト更新 | 中 |
| 6 | 大関数のステージ分解 + テスト更新 | 中 |
| 7 | `generate_article.py` を入口に縮約。pytest + `npm run build` 全緑。README / AGENTS.md 構造記載更新 | - |

## Verification

- **Phase 0 (2026-10-11)**: `pytest scripts/tests/ -v` → **365 passed** (7.80s)。失敗 0。ベースライン確立
- **Phase 1 (2026-10-11)**: `fetch_topics.py::main()` 関数抽出。`main()`（CC52/185行）→ 約45行・CC<10（解析閾値未満に）。新関数: `collect_all_topics`（各 source try/except 収集）/ `load_previous_output`（latest.json 読取・破損耐性）/ `build_output`（CC26/68行・純粋関数化、merge/継承ロジック）/ `save_output`（ts書き出し+latestコピー）/ `cleanup_old_topic_files(keep=10)`。テストは `patch.object(fetch_topics, ...)` + `TOPICS_DIR`/`OUTPUT_PATH` monkeypatch 方式のため**無変更で全緑**。`pytest scripts/tests/ -q` → **365 passed** (6.81s)。`--help` で CLI エントリ動作確認。`build_output` CC26 は純粋データ変換のため許容（Phase 6 で必要なら再分解）
- **Phase 2a (2026-10-11)**: `scripts/article/` パッケージ雛形 + `config.py` へ静的定数 56 件を移設（`__all__` 定義 + `generate_article.py` で `from article.config import *`）。`PROJECT_DIR` は 3 階層 dirname で `<root>` に正解決（`scripts/fetch_topics.py` 存在確認）。関数移設なしのためテスト patch 経路無変更。`py_compile` OK + `pytest scripts/tests/ -q` → **365 passed** (6.69s)。コミット `08dc13c`（+ `a9446f9`=Phase 1）を push
- **Phase 2b (2026-10-11)**: `meta.py`（`get_existing_posts` / `get_recent_titles_by_type` / `get_recent_meta_by_type` / `_save_trend_usage_log` / `_save_draft_metadata` / `_save_affiliate_link_log` / `_cleanup_old_logs` / `_extract_fm_field`）+ `slug_links.py`（`_load_slug_redirects` / `_save_slug_redirects` / `_get_existing_slugs` / `_resolve_slug_collision` / `_load_posts_for_links` / `_existing_link_spans` / `inject_internal_links`）へ 15 関数移設。`generate_article.py` は再エクスポート import で留置（`generate_post` 等の呼出元はそのまま）。テスト patch 経路更新: `SLUG_REDIRECTS_FILE` 7 / `DRAFTS_DIR` 6 / `LOG_CLEANUP_DIRS` 8 を `article.meta.` / `article.slug_links.` へ（`patch.object(generate_article, "_save_trend_usage_log")` と `BASE_URL` は呼び出し元留置のため維持）。`_extract_fm_field` は meta.py へ（Phase 5 の frontmatter.py へ移行する可能性を残す）。AST ベース削除スクリプトで 437 行除去し孤立セクションコメントも除去。`py_compile` OK + `pytest scripts/tests/ -q` → **365 passed** (7.02s)
- **Phase 3 (2026-10-11)**: `image.py` へ 13 関数移設（kemono パラメータ `_is_valid_kemono_combination` / `_randomize_kemono_params` / `_build_kemono_tags`、画像生成 `_save_as_avif` / `_generate_image_pollinations` / `generate_and_save_image`、プロンプト合成 `extract_character_prompts` / `extract_art_style` / `_parse_image_prompt_targets` / `compose_image_prompt` / `extract_image_prompt`、本文画像 `process_inline_images` / `replace_character_placeholders`）。`_kemono_affiliate_keywords`（affiliate 依存）とキャラ特徴 4 関数（`_select_character_features` 等、`_is_affiliate_excluded` / `_load_genre_scores` 依存）は後続フェーズへ延期。`generate_article.py` は `from article.image import (...)` で再エクスポート留置（519 行除去・孤立セクションコメントも除去）。テスト patch 経路更新: `BASE_URL` 8 / `Client` 4 / `IMAGE_PROVIDER` 5 を `article.image.` へ（`requests` / `time.sleep` / `monkeypatch.setenv("HF_TOKEN")` はグローバル・os.environ 方式のため維持）。`py_compile` OK + `pytest scripts/tests/ -q` → **365 passed** (6.93s)
- **Phase 4 (2026-10-12)**: `affiliate.py` へ 22 関数 + 1 module var（`_rakuten_last_call_time`）移設。Region A（旧 L264-990）: `process_inline_affiliates` / `process_inline_products` / `_is_affiliate_bad_keyword` / `_improve_keyword` / `_extract_article_body`（`_validate_description`（留置）からも使用 → affiliate.py 移設 + re-export で循環 import 回避）/ `_is_github_repo_name` / 楽天API `_rakuten_load_cache` / `_rakuten_save_cache` / `_rakuten_search` / `_generate_rakuten_card` / `_find_table_end_line` / `_extract_article_keywords` / `_kemono_affiliate_keywords` / `_rakuten_is_relevant` / `_rakuten_first_phrase` / `_rakuten_api_keywords` / `_rakuten_collect` / `inject_affiliate_links`。Region B（旧 L1504-1693）: `_extract_affiliate_keyword` / `extract_product_recommendations` / `generate_product_cards` / `process_product_cards`。`generate_article.py` は 703 行除去（2354→1452 行）し `from article.affiliate import (...)` で 22 関数を再エクスポート留置。移設で不要になった import 5 行（`urllib.parse` / `requests` / `PIL.Image` / `pillow_avif` / `gradio_client.Client`）を削除。テスト patch 経路 24 件を `article.affiliate.*` へ（`_rakuten_search` 7 / `_rakuten_load_cache` 6 / `_rakuten_save_cache` 3 / `requests.get` 6 / `time.sleep` 2）、`TestRakutenSearch.setUp` のレート制限リセット先を `article.affiliate._rakuten_last_call_time` に変更（テスト実行時間は従来と同等に維持）。`TOPICS_JSON_PATH` patch 2 件は留置関数（`_auto_fetch_topics`）が読むため維持。`py_compile` OK + `pytest scripts/tests/ -q` → **365 passed** (7.52s)
- **Phase 5 (2026-10-12)**: `trends.py`（362 行・6 関数: `_load_genre_scores` / `_filter_by_genre`（`_append_trending_topics` が必要とするため同伴移設）/ `_check_topics_ttl` / `_check_per_source_ttl` / `_auto_fetch_topics` / `_append_trending_topics`）+ `frontmatter.py`（340 行・10 関数: `_extract_first_sentence_from_body` / `_validate_description` / `_extract_fm_tags` / `_get_body_after_fm` / `_extract_faq_pairs` / `_extract_speakable_text` / `_compose_smart_situation` / `_fix_duplicate_yaml_keys` / `_is_character_like_key` / `validate_and_fix_frontmatter`）へ移設。`generate_article.py` は 653 行除去（1452→799 行・10 defs 残）し `from article.trends import (...)` 6 名 + `from article.frontmatter import (...)` 10 名で再エクスポート留置。移設で不要 import 2 行（`subprocess` / `yaml`）を削除。`_build_generation_info_section`（CC30）は `_is_affiliate_excluded`（留置）を呼ぶため循環 import 回避で留置（Phase 6 の分解対象）。テスト patch 経路 36 件を `article.trends.*` へ（`patch.object(generate_article, ...)` 34 件 → `patch("article.trends....")` 文字列形式: `TOPICS_JSON_PATH` 6 / `GENRE_SCORES_PATH` 10 / `_save_trend_usage_log` 6 / `_check_topics_ttl` 6 / `_check_per_source_ttl` 6 + 旧 `patch("generate_article.TOPICS_JSON_PATH")` 2 件）。留置関数が内部で移設関数を呼ぶケース（`_load_character_features` → `_load_genre_scores`）も patch 対象が `article.trends` 側になるため同様に更新。`py_compile` OK + `pytest scripts/tests/ -q` → **365 passed** (6.96s)
- **Phase 6a (2026-10-12)**: `generate_post()`（CC81/325行）を 9 ステージ関数に分解 → **CC1/49行**。新関数（generate_article.py 内・`generate_post` の直上に配置）: `build_ng_instruction`（CC13/40: 重複防止指示生成）/ `resolve_kemono`（CC2/5: kemono パラメータ+target_genres）/ `build_prompt`（CC1/20: テンプレート+e621 選出+プロンプト保存）/ `generate_content`（CC5/39: pass1+コードブロック除去+frontmatter 保険+pass2+draft メタ）/ `build_header_image`（CC5/26: キャラ抽出+シチュエーション+ヘッダー画像）/ `apply_frontmatter_fields`（CC14/36: image/slug/prompt_type/tags/trend_sources）/ `postprocess_content`（CC3/28: 本文画像・プレースホルダー・アフィリエイト・商品カード・内部リンク）/ `apply_seo_schemas`（CC7/17: FAQ+Speakable）/ `finalize_and_save`（CC4/42: 検証・記述補正・生成情報・保存・ログ掃除）+ `_apply_slug_field`（CC8/20: slug 検証・生成・競合解決。`apply_frontmatter_fields` CC21→CC14 に寄与）。`generate_article.py` の inline `import unicodedata` を除去し、slug 生成ルジック全体を `article/frontmatter.py` の `_generate_ascii_slug(raw_title)`（CC 相当の単純ループ・re+unicodedata）へ移設 + re-export 追加（frontmatter 17 名）。`safe_faq` 未使用変数 1 行削除（`apply_seo_schemas` 内・`faq_json` が f-string で直接使われていた）。動作等価性はスラッグ分岐の 4 ケース（frontmatter 既存 / 欠落 / 空値 / 生成 0 件）で確認。`generate_post` 呼び出し元テストなし（個別関数の単体テストのみ）のためテスト変更ゼロ。`py_compile` OK + `pytest scripts/tests/ -q` → **365 passed** (6.98s)
- **Phase 6b (2026-10-12)**: `_append_trending_topics()`（CC39/192行、trends.py）を 9 ヘルパーに分解 → **CC4/58行**。新関数（trends.py 内・旧関数の位置へ置換）: `_load_topics_data`（CC4: latest.json 読取、(data, skip_reason) 返却）/ `_save_trend_skip_log`（CC1: スキップ時ログ）/ `_categories_for_prompt_type`（CC3: カテゴリ厳格化）/ `_refresh_topics_if_expired`（CC5: グローバル+per-source TTL 検証・自動再取得）/ `_collect_candidates`（CC7: スコアしきい値フィルタ+物語モード e621 除外、ログ計数返却）/ `_select_candidates`（CC4: ジャンル優先選択+件数上限）/ `_build_selection_lists`（CC8: 表示リスト+アフィリエイトキーワード組立）/ `_topics_elapsed_hours`（CC4: fetched_at 経過時間）/ `_build_trend_usage_log`（CC2: 利用ログ dict 組立）。`_build_generation_info_section()`（CC24/119行、generate_article.py）を 5 ブロック生成器に分解 → **CC10/45行**: `_gen_info_setting_rows`（CC4: 体型/世界設定/変身/関係性/追加設定）/ `_gen_info_trend_block`（CC1）/ `_gen_info_char_data_block`（CC6: 行無しの空リストで非表示分岐維持）/ `_gen_info_e621_updated_label`（CC3: UTC 整形）/ `_gen_info_e621_block`（CC8: 参考キャラクター+版権/artist/データ時点）。新ヘルパー全て CC≤8。テスト patch は `article.trends.*` モジュールグローバル経由のため、新ヘルパーも同一グローバルを参照する設計で**テスト変更ゼロ**。`py_compile` OK + `pytest scripts/tests/ -q` → **365 passed** (6.97s)
- **Phase 6c (2026-10-12)**: `inject_affiliate_links()`（CC42/167行、affiliate.py）を 6 ヘルパーに分解 → **CC8/59行**。新関数（affiliate.py 内・旧関数の直上に配置）: `_fallback_keyword_from_tags_title`（CC8: tags 先頭→title 先頭語のフォールバック抽出）/ `_append_trend_keywords`（CC8: trend_keywords 最大3件補充、GitHub リポジトリ名・重複・悪質 kw 除外）/ `_resolve_affiliate_keywords`（CC9: 3段フォールバック = script → 本文抽出+trend 補充 → tags/title → デフォルト、(keywords, sources) 返却）/ `_build_affiliate_links_html`（CC3: Amazon/楽天検索リンク+UTM、リンクログエントリ組立）/ `_build_rakuten_cards_section`（CC2: カスケード検索→最大3商品カード）/ `_build_main_cta_section`（CC2: 複数 kw 時のメイン CTA）。新ヘルパー全て CC≤9。`inject_affiliate_links` は直接テストなし（内部 `_rakuten_*` 系のみテスト・patch 経路不変）+ 新ヘルパーは同一モジュール内で module-level 関数を呼ぶため**テスト変更ゼロ**。`py_compile` OK + `pytest scripts/tests/ -q` → **365 passed** (7.02s)
- **Phase 6d (2026-10-12)**: 残り 3 大関数を分解 → **全対象 CC≤6**。`compose_image_prompt()`（CC57/122行、image.py）を 6 ヘルパーに分解 → **CC6/36行**: `_extract_artist_name`（CC2: "by artist_name" 抽出）/ `_collect_prompt_targets`（CC10: 括弧区間解析・マージ・フォールバック）/ `_compute_count_tag`（CC7: boys/girls 集計→2boys/1boy and 1girl/2characters）/ `_strip_single_count_tags`（CC2: 単独カウントタグ除去）/ `_build_char_block`（CC9: 表情タグのキャラ直後配置・全同一 dedupe・shared 末尾追加）/ `_finalize_prompt_parts`（CC4: situation/artist/品質/style の順付加）。`_randomize_kemono_params()`（CC29/65行、image.py）→ **CC3/36行** + `_weighted_pick`（CC3: 重み抽選 1 回）/ `_pick_char_count`（CC2: clone 時のみ抽選）。random 呼び出し順序を厳密に維持（テストの分布検証が順序依存）。`_select_character_features()`（CC27/70行、generate_article.py）を 5 ヘルパーに分解 → **CC4/49行**: `_cp_genre_score`（CC3: 旧クロージャ関数をモジュールレベル化）/ `_filter_valid_copyrights`（CC4: 版権降順+不適格除外+genre 優先・最大10件）/ `_extract_post_copyrights`（CC5: 選出投稿の版権抽出・重複排除）/ `_merge_copyrights`（CC4: 補完+上位8件結合）/ `_extract_top_artists`（CC2）。3 関数とも直接呼び出しテストのみ（内部 patch なし）+ 新ヘルパーは同一モジュール内 module-level 呼出のため**テスト変更ゼロ**。image.py 566→560行、generate_article.py 847→871行。EOL 発見: image.py 作業ツリーは混合（冒頭約20行 LF・残り CRLF、コミット済みブロブは純 LF、autocrlf で clean 維持）→ splice は既存バイト状態保持・新行 CRLF 挿入。`py_compile` OK + `pytest scripts/tests/ -q` → **365 passed** (7.10s)
- （以降フェーズごとに追記）

## Next Action

Phase 7: `generate_article.py` の入口縮約確認（既に入口+パイプライン化済み）+ `pytest` 全緑再確認 + `npm run build` 検証 + README / AGENTS.md のプロジェクト構造記載更新（`scripts/article/` パッケージ反映）
