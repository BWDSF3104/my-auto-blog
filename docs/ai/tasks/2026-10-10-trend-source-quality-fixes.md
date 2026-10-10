# 2026-10-10: トレンドソース品質修正（ANNナビゴミ排除 + Crunchyroll一時無効化 + per-source TTL 誤検知修正）

## 概要

trend topics 実効化タスク（`2026-10-10-trend-rss-enhancement.md`）完了後のライブ検証で、既存のソース品質問題 3 件を特定。ユーザー確認（「既存正常部分に影響しないか」）を経て、問題1（ANN HTML パースのナビ・フッターの混入）と問題2（`_check_per_source_ttl` の他カテゴリ専属 source 誤検知）を修正、問題3（`by_category` / `all` の merge 構造ドリフト）は影響低・単独修正が複雑なため known-issues.md に記録のみで不変更。

## 問題特定

### 問題1: ANN HTML パースがナビ・フッターを記事として収集
- `_parse_entertainment_page()` が `ENTERTAINMENT_HTML_SOURCES`（ANN / Crunchyroll）のページから `<a>` タグを単純抽出しており、ナビゲーション・フッター・関連リンク等が「記事」として収集されていた
- 実測: `latest.json` の "Crunchyroll News"（15 件）はすべてナビ・フッター系 URL（`/news`・`/genre/anime` 等）で記事本文 0 件。ANN も同様に記事混入
- Crunchyroll は JS 描画のため静的 HTML に記事が 0 件（RSS フィードも 404 確認済み）

### 問題2: `_check_per_source_ttl` が他カテゴリ専属 source を「陳腐化」と誤検知
- `_check_per_source_ttl()`（`generate_article.py:1972`）は source の `fetched_at` を TTL と比較して陳腐化判定していた
- しかし source 名（`"ANN"` 等）はカテゴリ横断で共有され、`fetched_at` も全カテゴリで共有のため、kemono 記事生成時に e621（pokemon 専属）や GitHub（tech 専属）の `fetched_at` が古いだけだと「陳腐化」と判定され、自動 fetch トリガーが毎回発火していた
- 実際は各 source のデータが正常（他カテゴリでは新鮮）であり、トリガーは不要

### 問題3: `by_category` / `all` の merge 構造ドリフト（不変更・記録のみ）
- `by_category` はカテゴリ単位の merge 継承、`all` / `sources` は source 単位の部分継承で乖離
- 結果: `by_category.pokemon` に `all` に存在しない 7 件（e621 5 件 + GitHub 2 件、旧 e621 再収集で sources から脱落）が merge 継承で残存
- 影響は低（`generate_article.py:2313` の注入は score しきい値でフィルタするため）が、理論上 pokemon 記事に注入可能性あり
- known-issues.md に記録、単独修正は後日（P3）

## 実装

### `scripts/fetch_topics.py`
- `ENTERTAINMENT_HTML_SOURCES` から Crunchyroll を削除（静的 HTML に記事 0 件・JS 描画のため一時無効化）
- 新規 `ENTERTAINMENT_ARTICLE_PATTERNS` 追加:
  ```python
  {
      "ANN": re.compile(r"^/(?:news|review|guide|interview|profile|gallery)/\d{4}-\d{2}-\d{2}/"),
  }
  ```
- `_parse_entertainment_page()` 書き換え:
  - `urllib.parse.urljoin(base_url, href)` で相対 URL を絶対 URL に解決
  - `javascript:` / `mailto:` / `#` アンカーはスキップ
  - source 別 whitelist パターン（`ENTERTAINMENT_ARTICLE_PATTERNS`）で記事パスのみ採用
  - 既知 source（ANN）以外には whitelist なしで従来動作（空リスト返却）
  - URL 重複除去 + 上限 15 件
- `collect_entertainment_trends()` で `base_url=url` を `_parse_entertainment_page()` に渡与
- ヘッダ docstring に Crunchyroll 一時無効化の注記追加

### `scripts/generate_article.py`
- `_check_per_source_ttl()`（`generate_article.py:1972`）精緻化:
  - 各 source の `fetched_at` を TTL 比較
  - **他カテゴリ専属 source**（トピック 0 件・要求カテゴリ 0 件）は `expired[src_name] = False`（自動 fetch トリガーにしない）
  - トピック 0 件 source（完全失敗）は従来どおり `expired[src_name] = True` 維持（自愈保持）
  - 戻り値キーは全 source 保持（呼び出し側が source 名を参照するため）

### テスト
- `scripts/tests/test_fetch_topics.py`:
  - `TestParseEntertainmentPage` 新規 7 件:
    - `test_nav_and_footer_excluded`（ナビ・フッター除外）
    - `test_article_url_resolved`（相対 URL → 絶対 URL 解決）
    - `test_non_article_path_excluded`（非記事パス除外）
    - `test_duplicate_url_removed`（URL 重複除去）
    - `test_max_15`（上限 15 件）
    - `test_unknown_source_empty`（既知 source 以外は空リスト）
    - `test_html_sources_excludes_crunchyroll`
  - fixture を whitelist 適合 URL（`https://www.animenewsnetwork.com/news/2026-10-10/some-anime-news-headline`）に更新
- `scripts/tests/test_generate_article.py`:
  - `TestCheckPerSourceTTL`:
    - `test_other_category_source_mixed_with_fresh_in_scope` 新規（他カテゴリ専属 source は `False`）
    - `test_zero_topic_source_still_expired` 新規（完全失敗 source は `True`）
    - 既存 `test_source_not_matching_category_not_checked` を `assert result["e621"] is False` に更新

## データクリーンアップ

- `data/topics/latest.json` から "Kemono"（10 件）+ "Crunchyroll News"（15 件）を sources / all / by_category から除去、total 124 → 99
- 20:23 ライブ fetch で再書替（60 件・9 source: e621 25 / GitHub 1 / GameSpot 10 / IGN 10 / ANN 14）

## Verification

- `pytest scripts/tests/ -v` → **348 passed**（ベースライン 339 + 新規 9 + 既存 1 アサート更新）
- ライブ fetch: `python -X utf8 scripts/fetch_topics.py --categories kemono` → ANN **14 件・全件正規記事絶対 URL**（`https://www.animenewsnetwork.com/news/2026-10-10/...`）、Crunchyroll 収集なし、計 60 件
- TTL dry check（`ttl_check.py`）:
  - kemono 実行 → **expired 空**（自動 fetch 不トリガー・修正前毎回トリガー）
  - pokemon 実行 → 4 件 pokemon source が正しく expired（10-06 取得・真の陳腐化）
  - tech → 空
- `python scripts/tests/test_real_apis.py --save` → 9/11 pass（失敗 2 件は既知無効化 source: Reddit 403 / Bluesky 501、fetch_topics.py ヘッダに記録済み）
- Astro 変更なし → `npm run build` 不要（AGENTS.md「Python のみ変更 → pytest」）

## Next Action

- **コミット**: ユーザー明示指示待ち（変更 16 + 新規 2 + 削除 3）
- Crunchyroll 再収集（JS 描画対策・RSS 代替探索）は backlog P3
- merge 構造ドリフト（問題3）は known-issues.md 記録・後日 P3
