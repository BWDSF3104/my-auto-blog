# トレンドデータRSS強化 + trend topics 実効化（backlog P2 #1, #5）

## Status
**完了** (2026-10-10 開始・完了)

## Background
- kemono_story モードでは e621 投稿がストーリーインスピレーションから除外されており（`generate_article.py` `_append_trending_topics()`）、残る候補は score=0-1 のエンタメニュース・GitHub レポのみで、物語テーマへの反映がない（調査: `tasks/2026-10-06-generation-pipeline-investigation.md` 問題点 #3）
- RSS パーサー（`fetch_topics.py` `fetch_rss()`）が title+URL のみ取得しており、description（summary）・本文一部が取得・保存されていない。ジャンル判断（`genre_score.py` `score_topics()`）や記事生成（トレンドブロック注入）に活用できない（backlog P2 #5）
- **発見バグ**: `fetch_topics.py:716` のエンタメ全ソース失敗フォールバックが `STORY_INSPIRATION_THEMES` を参照しているが未定義（NameError）。`main()` の try/except で吞まれて全ソース失敗時に0件になる

## 実測確認 (2026-10-10)
- GameSpot `https://www.gamespot.com/feeds/mashup/` → 200, 正規 RSS 2.0, 15 items, `description`（HTML `<p>` 入り）あり。**従来は HTML パース扱いで description を捨てていた**
- IGN `https://feeds.feedburner.com/ign/all` → 200, 正規 RSS 2.0, 20 items, `description` + `content:encoded` あり
- ANN `https://www.animenewsnetwork.com/feeds/news` → 404（RSS 不存在）。HTML パース維持

## 方針
1. `fetch_topics.py` `fetch_rss()`: description 抽出（RSS2.0: `content:encoded` → `description`、Atom: `content` → `summary`）。HTMLタグ除去・エンティティ復元・空白圧縮・300文字切り詰め（`_clean_rss_description()`）
2. `fetch_topics.py`: GameSpot/IGN を HTML パース → 正規 RSS パース（`fetch_rss()`）へ切り替え。ANN/Crunchyroll は HTML パース維持（description 空文字）
3. `fetch_topics.py`: `STORY_INSPIRATION_THEMES` を定数定義（内蔵テーマ8件、title+description 構造）で NameError 修正
4. `genre_score.py` `score_topics()`: スコアリング入力を title+description[:200] に変更（ジャンル判断精度向上）
5. `generate_article.py` `_append_trending_topics()`: トレンドブロックに description[:100] スニペットを「—」区切りで注入。`selected_items` ログに description[:200] 記録
6. `test_real_apis.py`: RSS テストに description 出力 + GameSpot/IGN フィード追加

## 実装内容
- `fetch_topics.py`:
  - `_clean_rss_description()` 新設（HTMLタグ除去 → `html.unescape` → 空白圧縮 → `RSS_DESCRIPTION_MAX=300` 文字切り詰め）
  - `_rss_item_description()`（RSS 2.0: `content:encoded` → `description`）/ `_atom_entry_description()`（Atom: `content` → `summary`）新設
  - `fetch_rss()` に description 抽出を追加（item/entry 各最大10件）
  - `ENTERTAINMENT_SOURCES` を `ENTERTAINMENT_RSS_SOURCES`（GameSpot/IGN）+ `ENTERTAINMENT_HTML_SOURCES`（ANN/Crunchyroll）に分離。`collect_entertainment_trends()` を RSS パース / HTML パースの分岐へ書き換え（HTML ソースは `description=""`）
  - `STORY_INSPIRATION_THEMES` 定数定義（内蔵テーマ8件: title+description）で NameError 修正
  - `collect_rss_feeds()` に description パススルー
- `genre_score.py`: `score_topics()` のスコアリング入力を `title + "\n" + description[:200]` に変更
- `generate_article.py`: `_append_trending_topics()` で description ありは `[source] title — desc[:100]` 形式で注入、`selected_items` ログに `description[:200]` 記録
- テスト: `test_fetch_topics.py` に `TestCleanRssDescription`(7) / `TestFetchRssDescription`(5) / `TestCollectRssFeedsDescription`(1) / `TestCollectEntertainmentTrends`(4) 新規。`test_genre_score.py` に `TestScoreTopics` へ description テスト3件。`test_generate_article.py` に `TestAppendTrendingTopicsDescription`(4) 新規
- `test_real_apis.py`: `_clean_rss_description` import + RSS フィードに GameSpot/IGN 追加 + description 抽出・出力

## Verification
- `pytest scripts/tests/` → **339 passed** (7.26s)（ベースライン 315 + 新規 24）
- `python scripts/tests/test_real_apis.py --save` (2026-10-10): `rss_gamespot` 200 / 3 items / description 出力確認、`rss_ign` 200 / 3 items / description 出力確認。結果: `scripts/data/api_test_results/api_test_20261010_074140Z.json`（既存の reddit 403 / bluesky 501 は本タスク無関係の既知事象）

## Next Action
- 次回 deploy で `score_topics` の全件再スコアリング発生（title+description 入力変更によるキャッシュキー変化、一次性コスト）
- 次回 deploy 実行でトレンドブロックの description スニペット注入を確認
