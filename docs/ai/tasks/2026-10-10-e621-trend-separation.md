# 2026-10-10: e621 データのトレンド配管からの分離（キャラクター特徴集計のみ継続）

## 概要

e621 のデータは「キャラクター特徴の集計（`data/character_features.json`）」専用であり、トレンドトピック（`data/topics/latest.json`）として記事生成に注入すべきではない。KI-20261010-01（`by_category`/`all` の merge 構造ドリフト）でも e621 項目の残存が問題化していたため、ユーザー承認済みの 1・2・4 を実施:
1. **コード修正** — `fetch_topics.py` が e621 をトレンド出力から排除（収集・集計は継続）
2. **データ一次性除去** — `data/topics/*.json` 12 ファイルから既存の e621 項目を除去
4. **テスト更新** — e621 を前提とするテスト例の改修 + 分離の回帰テスト追加

3（`genre_score.py` 側の変更）は不要: e621 が `latest.json` に入らなくなるため自動的にスコアリング対象外になる。

## 実装

### `scripts/fetch_topics.py`
- 冒頭 docstring :6 — e621 の行に「キャラクター特徴集計のみ（トレンドトピックには結合しない）」追記
- `E621_TAGS` コメント :63 — 「トレンド作品追跡用」→「キャラクター特徴のカバレッジ確保用」
- `NON_TREND_SOURCES = {"e621"}` 定数を新設（:85、`CHARACTER_FEATURE_CATEGORIES` 直後）
- `collect_e621()`（:522）を書き換え:
  - 戻り値 `list[dict]`（トレンドトピック）→ `int`（収集した投稿数）
  - トレンド項目（title/url/source/score 等）の組立を削除、`collected` カウンタのみ返却
  - 副作用（raw_tags 収集 → キャラクター特徴集計用）は変更なし
- `main()` step 3（:885）— `all_topics.extend(collect_e621(...))` を削除し、副作用のみの呼び出しに変更
- `main()` の出力構築前（:977-980）— `sources` / `merged_by_category` / `all_topics_merged` の 3 件すべてから `NON_TREND_SOURCES` をフィルタ
  - **重要**: 直前の `latest.json`（`prev`）から継承される merge 経路にも e621 が混入し得るため（KI-20261010-01 の機構）、出力直前のガードが必須。`collect_e621()` 側の削除だけでは不十分

### `scripts/tests/test_fetch_topics.py`（ユーザーリファクタリング後の 561 行版をベースに修正）
- `_run_main` docstring とモック patch: e621 の `collect_returns` 参照を削除、`return_value=0`
- 以下 3 テストの例を e621 → reddit に改名（e621 はもう「収集 source」ではないため）:
  - `test_uncollected_source_inherited_from_previous`
  - `test_uncollected_source_fetched_at_preserved`
  - `test_by_category_uncollected_inherited`
- **新規** `test_e621_from_previous_never_inherited`（:299）: 直前データに e621 が混入していても出力の `sources` / `all` / `by_category` に現れないこと + 通常の source（reddit）は継承されることを確認（KI-20261010-01 への回帰ガード）

### `scripts/tests/test_generate_article.py`
- `test_source_not_matching_category_not_checked`（:981-987）— 例を e621 → reddit に改名（TTL 判定ロジック自体は不変）

### 不変（意図的）
- `scripts/generate_article.py` — :2321（e621 除外）/ :2427（アフィリエイトKW除外）の e621 参照は**防御的残存**として維持（下流の二重ガード）
- `scripts/genre_score.py` — `PROTECTED_SOURCES = {"e621"}`（版権エントリの保護）は維持
- `scripts/tests/conftest.py` — e621 fixture（`sample_topics_json` :86 / `sample_e621_posts` :254）は未使用・不変
- `data/character_features.json` — 集計対象データのため不変

## データクリーンアップ

`data/topics/` の全 12 JSON ファイル（`latest.json` + タイムスタンプ付き 11 件）から e621 項目を除去（一時スクリプトで `sources` / `all` / `by_category` を同時更新し `total` を再計算）:
- 旧 10 ファイル: total 99 → 94（e621 5 件除去）
- 最新 2 ファイル（`2026-10-10_202328.json` + `latest.json`）: total 98 → 73（e621 25 件除去）
- git diff 検証: 追加 12 行（`total` のみ）/ 削除 7728 行（e621 エントリ）

`data/genre_scores/topics.json`（e621 24 件を含む）は派生キャッシュのため放置（次回 `score_topics()` 実行で再生成）。

## Verification

- `pytest scripts/tests/ -v` → **349 passed**（ベースライン 348 + 新規回帰 1）
- e621 関連テスト: `test_e621_from_previous_never_inherited` 含む全通過
- Astro 変更なし → `npm run build` 不要（AGENTS.md「Python のみ変更 → pytest」）
- `fetch_topics.py` 更新後の `test_real_apis.py --save` は未実行（e621 の収集挙動は不変・集計のみ。必要なら次回実行時）

## Next Action

- **コミット**: ユーザー判断待ち（コード 2 + テスト 2 + data 12 + Memory Bank 群）
- merge 構造ドリフトの一般問題（e621 以外）は backlog P3 #7 で継続
