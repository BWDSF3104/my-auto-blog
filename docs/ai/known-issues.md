# 既知問題リスト

進行中の問題のみを記録。解決済は下部のアーカイブに移動する。

## ソースコード監査で発見された潜在的なバグ (静的解析 2026-09-30)

**ステータス**: 保留

**発見方法**: テスト実行によるものではなく、ソースコードの静的解析（手動監査）で発見。テストスクリプト（85/85全件通過）は正常に動作している。

**候補リスト**:
- **[Medium]** `_extract_article_body` regex (`generate_article.py:L604`): 閉じ `---` の後に改行がない場合に本文抽出に失敗する可能性
- **[Medium]** `_validate_description` loop (`generate_article.py:L1299`): 短い description を拡張する際に同じ文を繰り返す可能性がある
- **[Low]** `_extract_first_sentence_from_body`: frontmatter 文字列内に `---` が含まれる場合、offset 計算がずれる可能性
- **[Low]** `urllib.parse` の関数内インポート: モジュールレベルでインポートすべき
- **[Low]** `_auto_fetch_topics` の相対パス: `scripts/fetch_topics.py` が CWD 変更時に失敗する可能性
- **[Low]** `compose_image_prompt` の括弧正規表現: 最初の括弧グループのみを取得
- **[Low]** `fetch_topics.py` の Windows シンボリックリンクフォールバック: 孤立したタイムスタンプファイルが蓄積する可能性
- **[Low]** `collect_bluesky` の URI 解析: 特定のコロン区切り形式を前提
- **[Low]** `_is_nsfw_post`: `non_consecutive` メタタグを誤って NSFW として扱う可能性

**Next action**: Medium 項目の修正を優先検討。Low 項目は実装影響が小さいため保留。

## Reddit API ブロッキング (2026-09-29)

**ステータス**: 進行中

**問題**: Reddit が `.json` エンドポイントを HTTP 403 でブロック。`old.reddit.com` へのフォールバックも 404 を返す。

**影響**: Reddit からの投稿収集が 0件。トレンドデータから kemono/tech 系の Reddit コンテンツが欠落。

**回避策**: 現在なし。Reddit OAuth 導入または代替データソースの検討が必要。

**Next action**: backlog P0 の「Reddit 代替ソースの追加」を実施し、HackerNews RSS または TechCrunch RSS を追加する。

**関連**: Bluesky API を代替トレンドソースとして検討中。

## 既存記事の Description 修正 (2026-09-30)

**ステータス**: 保留

**問題**: 最近10件中3件（30%）の記事が80文字未満の description を持つ（68-78文字）。現在のバリデーターは新規生成時のみ実行される。

**影響**: 記述が短い既存記事が規格に準拠していない。

**Next action**: backlog P1 の「既存記事のdescription修正」を実施する。独立スクリプトとして実装。

**計画**: 将来実装する場合、通常の生成パイプラインとは完全に分離し、単体実行前提の独立スクリプトとして実装する（例: `python scripts/fix_descriptions.py`）。`--fix-all-descriptions` フラグなど生成時のオプションには組み込まない。

---

## アーカイブ

### 直近記事のキャラクター・テーマ被りの追跡不能 (解決済 2026-09-30)

2つの改修で対応:
1. `check_deploy_success()`: デプロイ成功後にのみタイムスタンプを記録し、同日の成功記録があれば再生成をスキップ
2. `get_recent_meta_by_type()`: 直近5件の frontmatter から character_1, character_2, tags, art_style を抽出して NG 指示ブロックに注入

### fetch_topics.py の CRITICAL バグ (解決済 2026-09-30)

静的監査で発見した 5 件の CRITICAL バグを修正。テスト85件全件通過、ビルド成功を確認。

- **C-1** `fetch_topics.py:L276`: `isinstance(post.get("score"), int)` → `(int, float)` に変更。e621 API が float スコアを返す場合、int チェックのみではスコアが `None` にフォールバックし、高スコア投稿が失われていた。
- **C-2** `fetch_topics.py:L499-503`: TTL merge ロジックが逆。収集したソースに `now.isoformat()` を割り当て、未収集ソースが前の `fetched_at` を継承するよう修正。前実装は収集したソースのタイムスタンプを消去し、未収集ソースに `now()` を設定していた（TTLが常にリセットされるバグ）。
- **C1** `generate_article.py:L915`: カテゴリ不一致のソースを `expired[src_name] = False`（有効）としてマーク。`True`（期限切れ）に修正。カテゴリ不足のソースが再取得されなかった。
- **C2** `generate_article.py:L862-863`: `except Exception: break` の bare except が API 一時障害時にループを早期終了。`APIError` ハンドラーと同じリトライロジックに置換。
- **C3** `generate_article.py:L1015`: `_check_topics_ttl()` の戻り値（期限切れ辞書）を破棄。変数にキャプチャしてログ出力に接続。

### e621 NSFW コンテンツ (解決済 2026-09-29)

`fetch_topics.py` に `_is_nsfw_post()` ヘルパーを追加。explicit レーティングと既知の NSFW タグをフィルタ。ストーリーモードは Safe のみに制限。収集投稿にレーティングフィールドを追加。

### プロンプトタイプとカテゴリルーティングの不整合 (解決済 2026-09-29)

`_append_trending_topics()` でカテゴリルーティングを統一。ストーリーモードは kemono/pokemon のみ、デフォルトモードは tech のみ。ストーリーモードは e621 の Safe レーティング投稿にフィルタ。

### 低スコアトピックの混入 (解決済 2026-09-29)

`generate_article.py` に `MIN_SCORE_THRESHOLD` 環境変数（デフォルト 0）を追加。しきい値未満の項目は注入時にスキップされる。

### Description 検証のバグ (解決済 2026-09-30)

- 無意味なパディング: 本文から最初の文を抽出する `_extract_first_sentence_from_body()` に置換
- 正規表現の脆弱性: `re.sub` 呼び出し前に `safe_corrected = corrected.replace("\\", "\\\\")` を追加
- 既存記事の修正: 独立スクリプトに保留
- LLM リトライ: スコープ外

### アフィリエイトリンクのPC表示溢出 (解決済 2026-09-30)

`article` 要素に `overflow-wrap: break-word` + `word-break: break-word` を追加。`PostLayout.astro:281-284`。

### アフィリエイトリストリンクのプレーンテキスト表示 (解決済 2026-09-30)

記事内のAmazon・楽天リスト形式リンクが下線のみのプレーンテキストで表示されていた。CSS `:has()` セレクタでカードスタイルに変更。Amazonは琥珀色、楽天はピンク色のテーマ。`global.css`。

### アフィリエイトリンクのモバイルクリック不能 (解決済 2026-09-29)

モバイルでアフィリエイトリンクがクリックできない問題を修正。`PostLayout.astro`。
