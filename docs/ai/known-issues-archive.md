# Known Issues Archive

Resolved issues moved from `known-issues.md`.

---

## 既存記事のアフィリエイトリンク一括置換 (解決済 2026-10-02)

`scripts/fix_affiliate_links.py` で既存記事 15ファイル（48行）のアフィリエイトリンクを `[text](url)` から `<a href="url" target="_blank" rel="noopener noreferrer nofollow sponsored">text</a>` に一括置換。1ファイルで試験実行・差分確認後、全体適用。ビルド成功 (94ページ) を確認。

## 静的監査バグ修正 (解決済 2026-09-30)

ソースコードの静的解析で発見した Medium/Low バグを 5 件修正。テスト85件全件通過を確認。

- **M-1** `generate_article.py:L710` `_extract_article_body` regex: 閉じ `---` の後に改行がない場合にマッチしなかった。`re.DOTALL` のみ使用し、末尾の `\n` を `\n?` に変更。
- **M-2** `generate_article.py:L1410` `_validate_description` loop: 短い description 拡張時に同じ文を無限ループで繰り返した。`len(extended) + len(sentence) <= MAX_DESC_LEN` 条件を `next_ext` 事前チェックに置換。
- **L-1** `generate_article.py:L1370` `_extract_first_sentence_from_body`: `fm_end + 3` の offset 計算が frontmatter 形式に依存していた。`_extract_article_body()` を再利用するようにリファクタ。
- **L-2** `generate_article.py` `urllib.parse` の関数内インポート (4箇所): モジュールレベルのインポートに移動。
- **L-3** `generate_article.py:L407` `compose_image_prompt` の括弧正規表現: `re.search` で最初の括弧グループのみを取得していた。`re.findall` に変更して複数括弧グループに対応。`clean_situation` の除去も `re.sub` に変更。

## frontmatter欠落によるCIビルド失敗 (解決済 2026-09-30)

Gemini APIの出力に`---`がない場合、`generate_article.py`の`content.replace("---", ...)`が何もしないままmdファイルが保存され、frontmatterのない記事が生成される。`PostLayout.astro`の`.split()`と`rss.xml.ts`の`escapeXml`がundefinedでクラッシュ。

- `PostLayout.astro`: `.split()`のnullチェックと関連記事フィルタのnull除外を追加
- `rss.xml.ts`: `title`, `pubDate`, `description`のデフォルト値を追加
- `generate_article.py`: `---`が出力にない場合、デフォルトfrontmatterを付与するガードを追加

## 記事ページダークモードの文字色コントラスト不足 (解決済 2026-10-01)

`PostLayout.astro` の `<article>` に `dark:prose-invert` + 各要素の `dark:` 変種クラスを追加して本文の文字色を改善。ビルド成功 (92ページ) 確認済み。

## ダークモードトグル不動作と記事ページダークモード未適用 (解決済 2026-10-01)

`Header.astro` の `<script>` に `is:inline` 属性を追加してダークモード切り替えを復元。`PostLayout.astro` に `Header` コンポーネントのインポート、`dark:` 変種クラス、ダークモードCSSを追加して記事ページのダークモード対応を完了。`tags/index.astro` の `<script>` にも `is:inline` を追加。ビルド成功 (90ページ) 確認済み。

## 既存記事の Description 修正 (解決済 2026-10-01)

80文字未満のdescriptionを持つ4件の記事を独立スクリプト(`scripts/fix_descriptions.py`)で120文字に拡張。全テスト通過、ビルド成功、HTML出力確認済み。

## 直近記事のキャラクター・テーマ被りの追跡不能 (解決済 2026-09-30)

`get_recent_meta_by_type()`: 直近5件の frontmatter から character_1, character_2, tags, art_style を抽出して NG 指示ブロックに注入。

## 同日の重複デプロイによる生成スキップ (解決済 2026-10-01)

`check_deploy_success()` 関数と `data/.last-deploy-success.json` の記録・チェック処理を削除。同日の成功記録がある場合に記事生成をスキップするロジックは不要と判断。`deploy.yml` からのタイムスタンプ記録ステップも削除。

## fetch_topics.py の CRITICAL バグ (解決済 2026-09-30)

静的監査で発見した 5 件の CRITICAL バグを修正。テスト85件全件通過、ビルド成功を確認。

- **C-1** `fetch_topics.py:L276`: `isinstance(post.get("score"), int)` → `(int, float)` に変更。e621 API が float スコアを返す場合、int チェックのみではスコアが `None` にフォールバックし、高スコア投稿が失われていた。
- **C-2** `fetch_topics.py:L499-503`: TTL merge ロジックが逆。収集したソースに `now.isoformat()` を割り当て、未収集ソースが前の `fetched_at` を継承するよう修正。前実装は収集したソースのタイムスタンプを消去し、未収集ソースに `now()` を設定していた（TTLが常にリセットされるバグ）。
- **C1** `generate_article.py:L915`: カテゴリ不一致のソースを `expired[src_name] = False`（有効）としてマーク。`True`（期限切れ）に修正。カテゴリ不足のソースが再取得されなかった。
- **C2** `generate_article.py:L862-863`: `except Exception: break` の bare except が API 一時障害時にループを早期終了。`APIError` ハンドラーと同じリトライロジックに置換。
- **C3** `generate_article.py:L1015`: `_check_topics_ttl()` の戻り値（期限切れ辞書）を破棄。変数にキャプチャしてログ出力に接続。

## e621 NSFW コンテンツ (解決済 2026-09-29)

`fetch_topics.py` に `_is_nsfw_post()` ヘルパーを追加。explicit レーティングと既知の NSFW タグをフィルタ。ストーリーモードは Safe のみに制限。収集投稿にレーティングフィールドを追加。

## プロンプトタイプとカテゴリルーティングの不整合 (解決済 2026-09-29)

`_append_trending_topics()` でカテゴリルーティングを統一。ストーリーモードは kemono/pokemon のみ、デフォルトモードは tech のみ。ストーリーモードは e621 の Safe レーティング投稿にフィルタ。

## 低スコアトピックの混入 (解決済 2026-09-29)

`generate_article.py` に `MIN_SCORE_THRESHOLD` 環境変数（デフォルト 0）を追加。しきい値未満の項目は注入時にスキップされる。

## Description 検証のバグ (解決済 2026-09-30)

- 無意味なパディング: 本文から最初の文を抽出する `_extract_first_sentence_from_body()` に置換
- 正規表現の脆弱性: `re.sub` 呼び出し前に `safe_corrected = corrected.replace("\\", "\\\\")` を追加
- 既存記事の修正: 独立スクリプトに保留
- LLM リトライ: スコープ外

## アフィリエイトリンクのPC表示溢出 (解決済 2026-09-30)

`article` 要素に `overflow-wrap: break-word` + `word-break: break-word` を追加。`PostLayout.astro:281-284`。

## アフィリエイトリストリンクのプレーンテキスト表示 (解決済 2026-09-30)

記事内のAmazon・楽天リスト形式リンクが下線のみのプレーンテキストで表示されていた。CSS `:has()` セレクタでカードスタイルに変更。Amazonは琥珀色、楽天はピンク色のテーマ。`global.css`。

## アフィリエイトリンクのモバイルクリック不能 (解決済 2026-09-29)

モバイルでアフィリエイトリンクがクリックできない問題を修正。`PostLayout.astro`。

## latest.json シンボリックリンクのクロスプラットフォーム互換性問題 (解決済 2026-10-02)

`data/topics/latest.json` が GitHub Actions ラナーの絶対パスへのシンボリックリンクだったため、ローカルWindowsとGitHub Pagesで壊れていた。`os.symlink()` を `shutil.copy2()` に置換して通常ファイルコピーに変更。テスト134件全件通過確認済み。`b569ece`。

## 静的監査バグ修正 - 残り3件 (解決済 2026-10-02)

ソースコードの静的解析で発見した残りの Low バグ 3 件を修正。テスト134件全件通過、ビルド成功を確認。

- **L-4** `fetch_topics.py` の相対パス: `TOPICS_DIR = os.path.join("data", "topics")` が CWD 変更時に失敗した。`PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))` を追加して絶対パスに変更。
- **L-5** `generate_article.py` の相対パス: `TOPICS_DIR` と `TOPICS_JSON_PATH` が CWD 変更時に失敗した。`PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))` を追加して絶対パスに変更。`_auto_fetch_topics` の subprocess 呼び出しも修正。
- **L-6** `collect_bluesky` の URI 解析: 空の URI で `uri.split(':')[-1]` が空文字列を返し、無効な URL が生成された。空 URI チェックと rkey の空チェックを追加。
- **L-7** `_is_nsfw_post` の `non_consecutive`: NSFW タグセットに `non_consecutive` が含まれており、e621 のメタタグを誤って NSFW としてフィルタしていた。セットから削除。

## ソースコード監査で発見された潜在的なバグ (解決済 2026-09-30)

ソースコードの静的解析で発見した 9 件の潜在的バグを全修正。テスト134件全件通過確認済み。

## Reddit API ブロッキング (解決済 2026-10-02)

Reddit が `.json` エンドポイントを HTTP 403 でブロック。e621、Kemono API、RSS フィードを代替ソースとして追加し、kemono/pokemon カテゴリのトピック収集を安定化。

## 重複YAMLキーによる Astro ビルド失敗 (解決済 2026-10-04)

AI がプロンプト指示の `character_1`/`character_2` を無視し、キャラクタータイプ名（例: `少年:`）を YAML キーとして出力。2人以上のキャラクターでキーが重複し、Astro/Vite が `duplicated mapping key` エラーでビルド中断。

- `scripts/generate_article.py` に `_fix_duplicate_yaml_keys()` と `_is_character_like_key()` を実装
- `validate_and_fix_frontmatter()` 内で `safe_load` 前に重複チェックを无条件実行
- 破損記事 `2026-10-04-112752-auto-post.md` を手動修正（`少年:` → `character_1:`/`character_2:`）
- テスト110件全通、ビルド成功、デプロイ完了を確認

## 検索画面で検索インデックスの読み込みに失敗 (解決済 2026-10-04)

dev モードで検索画面にアクセスすると「検索インデックスの読み込みに失敗しました」が表示。`generate-search-index.js` が `dist/search-index.json` に出力していたが、dev モードでは `dist/` が空のためフェッチ失敗。
- `scripts/generate-search-index.js` の出力先を `dist/` から `public/` に変更
- `package.json` の build スクリプトを `node scripts/generate-search-index.js && astro build` に順序変更（`public/` → `dist/` のコピー前にインデックスを生成）
- ビルド成功 (108ページ) を確認

---
*以下は 2026-10-06 に known-issues.md からアーカイブ*

### KI-001: ハンバーガーメニューの記事一覧リンクが反応しない (解決済 2026-10-05)

- 発見日: 2026-10-05
- 症状: モバイルハンバーガーメニュー内の「記事一覧」リンクを押してもページ遷移・スクロールが発生しない
- 影響範囲: `Header.astro` のモバイルメニュー
- 原因: `href="#main-content"` はページ内の `id="main-content"` 要素へのアンカーリンク。`page/[page].astro` には `id` 属性がないため、ページネーションページでリンクが機能しない
- 修正: `href="#main-content"` → `href={baseUrl}` に変更（トップページの記事一覧へ遷移）
- 修正完了: 2026-10-05, `Header.astro:112` を修正

### KI-002: ヒーローセクションの最新記事ボタンが記事一覧以外では動作しない (解決済 2026-10-05)

- 発見日: 2026-10-05
- 症状: ヒーローセクションの「最新記事を読む」ボタンがトップページ以外で期待通りに動作しない
- 影響範囲: `Header.astro` のヒーローセクション
- 原因: `href="#main-content"` のアンカーリンク。`page/[page].astro` に `#main-content` が存在しない
- 修正: `href="#main-content"` → `href={baseUrl}` に変更 + `page/[page].astro` に `id="main-content"` を追加
- 修正完了: 2026-10-05, `Header.astro:167` + `page/[page].astro:126` を修正

### KI-003: 記事内画像が劇中シーンと関連していない (解決済 2026-10-05)

- 発見日: 2026-10-05
- 症状: 記事内に生成される挿絵画像が、周囲の本文のシーンと関連性が低い
- 影響範囲: 物語系記事（kemono_story）
- 根本原因: `compose_image_prompt()` が合成するプロンプトが SDXL の CLIP エンコーダー 77 トークン上限を超過（実測 78-155 トークン）、末尾の「シチュエーション」が破棄される
- 修正案: SDXL長プロンプトchunking実装 (2026-10-05 成功)。HF Space `app.py` に `get_long_prompt_embeddings_sdxl` 関数を追加。75トークン単位でチャンク分割 → 各チャンクをtext encoderに通す → embeddingを連結
- 詳細: `docs/ai/tasks/2026-10-05-long-prompt-v2.md`
