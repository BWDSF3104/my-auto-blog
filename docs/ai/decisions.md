# Design Decisions

古い決定は `decisions-archive.md` に移動する。直近10件のみ保持。アクティブファイルは Decision + Reason のみ（Rejected Alternatives / Impact はアーカイブ時に付与）。

## 2026-10-13: コマンド承認はグローバル `permission.bash`（フォールバック→allow→例外ask）＋ 行動ルールは AGENTS.md

**Decision**: kilo のコマンド承認はグローバル `kilo.jsonc` の `permission.bash` に集約し、「先頭 `"*": "ask"` フォールバック → 中段 allow 群 → 後段 例外 ask」（`last match wins`）で運用（98 エントリ）。行動ルール（一行コマンド / インライン Python 禁止）は `AGENTS.md` の `## Command Execution Rules` に置く。

**Reason**: 承認ゲート（設定ファイル）と行動指針（プロンプト）は別レイヤ。`last match wins` によりフォールバック ask を先頭・例外 ask を後段に配置。旧 365 エントリの単発ジャンクを削除して保守性回復。

## 2026-10-11: Pythonスクリプトの構造は「入口ファイル固定 + `scripts/article/` パッケージ + フェーズ分割移行」

**Decision**: `generate_article.py`（3561行）を `scripts/article/` パッケージ（8 モジュール）へ責務分離し、入口+`generate_post()` パイプライン（8 ステージ関数）に縮約。`fetch_topics.py` は関数抽出のみ（入口不変）。8 フェーズで各フェーズ末に pytest 緑で進行。

**Reason**: `deploy.yml` がファイル名固定で起動するため入口は残置。テストが `patch("generate_article.X")` に強く結合するため関数移設と patch 経路更新を同一フェーズで実施。フェーズ分割で中間状態の回帰を最小単位で検出。

## 2026-10-11: コメント機能は Giscus（GitHub Discussions バックエンド）を採用

**Decision**: Giscus（クライアントサイド iframe）を採用。`PostLayout.astro` 記事末尾に組み込み、frontmatter `comments: false` で記事単位無効化。`data-mapping="pathname"` で開発・本番同一 Discussion。テーマ同期は MutationObserver。env 4 値欠落時は early return で非表示。

**Reason**: 静的サイト（GitHub Pages）+ バックエンド/DB なしの設計哲学と整合。無料・広告なし・スパム抑制（GitHub OAuth 必須）で AI 自動生成記事に有効。セルフホスト型は常時稼働サーバーを新規追加するため矛盾。

## 2026-10-11: 生成情報の e621 ブロックは「実際にプロンプトに使った選出データ」を Python 側で表示

**Decision**: `_load_character_features()` を `_select_character_features()`（dict 返却）/ `_format_character_features_instruction()` に分割。`generate_post()` で 1 回の選出をプロンプトと生成情報セクションの両方に渡す（同一データ保証）。kemono_story 限定表示。

**Reason**: `random.choice` を2回実行するとプロンプトと表示の参考キャラが一致しない。選出を dict に分離し1回だけ呼び出せば同一データ保証。非ケモノ記事では e621 がプロンプトに使われないため非表示が正しい。

## 2026-10-10: 記事末尾の「生成情報」セクションは Python 側で本文に直接追記

**Decision**: `generate_article.py` が `<details class="gen-info">` HTML を生成し本文末尾に追記。frontmatter 拡張+Layout 描画は不採用。`_append_trending_topics()` を 3→4 タプル化。表示要素なしならセクション非表示。

**Reason**: ユーザー指示「Pythonスクリプト側で行う」。本文直接追記で既存記事影響ゼロ・バックフィル不要。`<details>` + h2〜h4 不使用で TOC/JSON-LD に影響しない。

## 2026-10-10: e621 データのトレンド配管からの分離

**Decision**: e621 を `latest.json` から完全排除（収集は継続・キャラクター特徴集計用）。`NON_TREND_SOURCES = {"e621"}` 新設、出力構築前に `sources`/`merged_by_category`/`all_topics_merged` をフィルタ。

**Reason**: e621 は「キャラクター特徴集計」専用でありニュース的トレンドではない。トレンドとして注入されると意味が不自然。merge 継承で残存し続ける構造的問題の温床も解消。

## 2026-10-10: トレンドソース品質（ANN whitelist + Crunchyroll一時無効化 + TTL誤検知修正）

**Decision**: ANN に URL whitelist（記事パス5種+日付形式）を導入しナビゴミを排除。Crunchyroll を一時無効化（静的 HTML に記事0件）。`_check_per_source_ttl()` で他カテゴリ専属 source を `expired=False`（自動 fetch 不トリガー）。

**Reason**: ANN のナビ・フッター URL は開放集合で blocklist では追えないが記事パスは閉集合。Crunchyroll は JS 描画で静的 HTML に記事なし。TTL は source 横断共有のため他カテゴリ専属が毎회トリガーしていた。

## 2026-10-10: RSS description の取得・活用（backlog P2 #1, #5 統合）

**Decision**: `fetch_rss()` に description 抽出（RSS2.0: content:encoded→description / Atom: content→summary、300文字切り詰め）。`score_topics()` で title+description[:200] スコアリング、`_append_trending_topics()` で description[:100] スニペット注入。GameSpot/IGN を HTML→RSS パースへ。`STORY_INSPIRATION_THEMES` NameError 修正。

**Reason**: kemono_story で e621 除外後の残り候補が title のみで score=0-1 になり物語テーマに反映されない問題。description 取得で下流全フロー（スコアリング→スニペット注入）を改善。GameSpot/IGN は実測で正規 RSS 2.0。

## 2026-10-10: アフィリエイト商品推薦の書籍偏りの中性化（書籍例は維持）

**Decision**: プロンプト3種 + 注入行で「書籍」が先頭・単独例にならないよう例の順序入れ替えと複数例化。削除・禁止指示・否定表現は追加しない。kemono「実在作品」→「実在商品」、category 列挙で書籍を末尾へ。

**Reason**: 直近記事の商品カード約6割が書籍（LLM はプロンプト例を強く模倣）。書籍は正規カテゴリ（削除不可）だが順序でアンカーを分散。禁止指示はプロンプトノイズになる可能性。

## 2026-10-10: 世界設定の2段階拡大（12種・アンカワーク基準）

**Decision**: 世界設定7種→12種（+isekai/modern/space_opera/dungeon_crawl/historical）。`WORLD_SETTING_GENRE_MAP` +5件。`historical` genre 新設（6→7種）。追加基準を「ケモノに独立世界を定義するアンカワーク存在＋明確に異なる物語を生む」に変更。

**Reason**: 現代人獣社会（Zootopia 系）と時代設定が表現不能だった。異世界は読者目線で独立ラベル。アンカワーク基準で細分化しすぎを制御。未デプロイ変更と同バッチ化で再スコアリング1回に集約。
