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
- （以降フェーズごとに追記）

## Next Action

Phase 2: `scripts/article/` パッケージ雛形作成 + `config.py`（定数群）/ `meta.py`（記事メタ・ログ管理）へ移設 + テスト更新 + pytest 緑確認
