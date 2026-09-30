# Development Notes

## 2026-09-29

### Completed
- Score-based sorting implemented for all topic categories
- TTL validation added with 24-hour default
- Documentation structure created (docs/ai/)
- NSFW filter: e621 explicit content filtered via `_is_nsfw_post()` + rating field
- Category strictification: story mode gets Safe-only e621; default gets tech-only
- Affiliate × Trend integration: `_append_trending_topics()` returns keywords, `inject_affiliate_links()` prioritizes them
- Affiliate all-categories: affiliate keyword extraction extended to kemono/pokemon (was tech-only)
- Bluesky collection: `collect_bluesky()` via Bsky search API with 3 category queries
- Frontmatter reference tracking: `trend_sources` YAML list in frontmatter
- Score threshold: configurable `MIN_SCORE_THRESHOLD` env var (default 0)
- **Prompt enhancement**: All 3 prompt templates enhanced with quality guidance (SEO, accuracy, character depth, narrative structure, show-don't-tell, dialogue quality)
- **2-pass generation**: `refine_content()` added to `generate_article.py`. Draft → Refine workflow with separate prompts for tech articles and stories. Pro model not used (flash-only).

### Observations
- Reddit API blocking is a critical gap in trend collection
- Bluesky API integration planned as future improvement
- e621 content filtering needed for non-kemono prompts

### Observations
- Reddit API blocking is a critical gap in trend collection
- Bluesky API integration planned as future improvement
- e621 content filtering needed for non-kemono prompts

### Dependencies Installed
- Pillow, pillow-avif-plugin
- google-genai
- gradio-client
- feedparser, beautifulsoup4, python-dotenv, requests

## SEO 改善（2026-09-29 実装完了）

### 完了項目

| 項目 | 内容 | ファイル | 検証 |
|------|------|----------|------|
| **slug SEO化** | Frontmatterに`slug`フィールド追加。AIがSEOフレンドリなスラッグを生成。日本語はローマ字変換。スラッグ無効時は`generate_article.py`が自動生成（全角→半角変換ロジック含む） | `scripts/generate_article.py:1034-1086`, `scripts/prompts/default.txt:34,44-47`, `scripts/prompts/kemono_story.txt:39,51-54` | `npm run build`成功 |
| **slugルーティング** | `[...slug].astro`がFrontmatterのslugを優先してルーティング。filenameはフォールバック | `src/pages/posts/[...slug].astro:13-14` | `npm run build`成功 |
| **RSS/Sitemap slug対応** | RSSフィードとsitemap.xmlがslugベースのURLを出力 | `src/pages/rss.xml.ts:20,30`, `src/pages/sitemap.xml.ts:21,30` | `npm run build`成功 |
| **TOC目次** | 記事内のh2/h3/h4を自動抽出して目次ナビゲーション生成。スムーズスクロール、IntersectionObserverで現在位置ハイライト | `src/layouts/PostLayout.astro:185-215,319-442` | `npm run build`成功 |
| **BreadcrumbList** | schema.org BreadcrumbList JSON-LDを各記事ページに注入。パンくずリストUIも追加 | `src/layouts/PostLayout.astro:87-96,131-138` | `npm run build`成功 |
| **WebSite SearchAction** | Google検索がサイト内検索を認識可能に。`SearchAction` JSON-LDをindexと記事ページに注入 | `src/pages/index.astro:58-67`, `src/layouts/PostLayout.astro:131-141` | `npm run build`成功 |
| **タグページ** | `/tags/` タグ一覧ページ、`/tags/[tag]` タグ別記事一覧ページ。CollectionPage JSON-LD、BreadcrumbList、SearchAction付き | `src/pages/tags/index.astro`, `src/pages/tags/[tag].astro` | `npm run build`成功 |
| **タグリンク** | 記事ページとindexページのタグをリンクに変更（タグページへナビゲーション） | `src/layouts/PostLayout.astro:167-169`, `src/pages/index.astro:207` | `npm run build`成功 |
| **関連記事** | 記事末尾にタグ一致スコアでソートされた関連記事を最大3件表示。サムネイル付き | `src/layouts/PostLayout.astro:24-50,218-240` | `npm run build`成功 |

### 未実装項目（次回候補）

| 優先度 | 項目 | 内容 |
|--------|------|------|
| **完了** | meta description最適化 | 検証・修正完了 (2026-09-30) |
| **高** | OG image自動生成 | 各記事に固有のOG imageを生成。現在は`image`フィールドがある記事のみ対応 |
| **中** | canonical URL一貫性 | slug変更時の301リダイレクト、sitemapとの整合性確認 |
| **中** | LCP/CLSパフォーマンス | 画像のloading="lazy"は実装済み。LCP画像の最適化、フォントのpreconnect |
| **中** | 自動内部リンク | 関連記事ページだけでなく、本文内でも関連記事へのアンカーテキストリンクを自動挿入 |
| **低** | FAQPage schema | Q&A形式の記事にFAQPage JSON-LDを自動追加 |
| **低** | Speakable schema | 記事の冒頭部分をGoogle Assistantが読み上げ可能に |

## 改善案（優先度付き）

### A. トレンド収集層（fetch_topics.py）

| 優先度 | 改善項目 | 内容 | 工数 |
|--------|----------|------|------|
| **高** | NSFW フィルタ | e621 収集時に `rating:explicit` または既知の NSFW タグを含む投稿をフィルタ。または分離して `nsfw` カテゴリに分類 | 小 |
| **中** | Bluesky 収集関数追加 | `collect_bluesky()` を新規追加。Bluesky AT Protocol の `app.bsky.feed.getPopularPost` または `app.bsky.graph.getSuggestedFeeds` を利用。カテゴリは `tech` / `kemono` に分類 | 中 |
| **低** | 部分キャッシュ | 各ソースごとに部分キャッシュを保存。一部ソースが失敗しても前回のデータで補完 | 大 |

### B. 記事生成層（generate_article.py）

| 優先度 | 改善項目 | 内容 | 工数 |
|--------|----------|------|------|
| **高** | カテゴリ厳格化 | `kemono_story` 系プロンプトには e621 の Safe 系タグのみを注入。技術記事には tech カテゴリのみを注入 | 小 |
| **高** | プロンプト強化 | 全テンプレートに質向上指示追加（SEO、正確性、キャラクター深み、物語構造、描写質、対話質） | 小 |
| **高** | 2-pass 生成 | 下書き→精製の2段階生成。技術記事と物語で異なる精製プロンプト | 中 |
| **中** | トレンド参照の Frontmatter 記録 | 注入したトレンドのソース/URL を Frontmatter の `references: [...]` に記録。記事生成後に「どのトレンドが参考されたか」を追跡可能に | 小 |
| **中** | スコアしきい値 | 低スコアトピックを自動的に除外するオプションを追加 | 小 |

### C. Bluesky API 追加時の設計

```python
# fetch_topics.py に追加する関数のスケルトン

BLUESKY_FEEDS = [
    {"handle": "some-tech-feed.bsky.social", "category": "tech"},
    {"handle": "some-kemono-feed.bsky.social", "category": "kemono"},
]

def collect_bluesky(limit_per_feed: int = 5) -> list[dict]:
    """Bluesky AT Protocol で人気投稿を取得"""
    # app.bsky.feed.getPopularPost や app.bsky.feed.getAuthorFeed を利用
    # Bluesky は認証不要で公開 API を提供（rate limit あり）
    ...
```

Bluesky は AT Protocol (JSON-RPC over HTTPS) なので、既存の `fetch_json()` パターンで実装可能。認証トークンなしでも `getPopularPost` エンドポイントは利用可能。

### D. 推奨実装優先度（全体）

| 優先度 | 改善 | 工数 | ステータス |
|--------|------|------|------------|
| **完了** | スコア順ソート + TTL 検証 | 小 | ✅ 完了 |
| **高** | NSFW フィルタ | 小 | ✅ 完了 (2026-09-29) |
| **高** | カテゴリ厳格化 | 小 | ✅ 完了 (2026-09-29) |
| **高** | アフィリエイト×トレンド連携 | 小〜中 | ✅ 完了 (2026-09-29) |
| **高** | プロンプト強化 | 小 | ✅ 完了 (2026-09-29) |
| **高** | 2-pass 生成 | 中 | ✅ 完了 (2026-09-29) |
| **中** | Bluesky 収集関数追加 | 中 | ✅ 完了 (2026-09-29) |
| **中** | トレンド参照の Frontmatter 記録 | 小 | ✅ 完了 (2026-09-29) |
| **中** | スコアしきい値 | 小 | ✅ 完了 (2026-09-29) |
| **中** | アフィリエイトリンクのPC表示修正 | 小 | 保留 |
| **低** | 部分キャッシュ機構 | 大 | 保留 |
| **低** | Reddit 公式 OAuth 対応 | 大 | 保留 |

### E. アフィリエイト × トレンド連携（2026-09-29 検討）

#### 現状の問題

`inject_affiliate_links()` は記事の `tags`（例: `"Tech"`, `"AI"`, `"Kemono"`）からキーワードを抽出してAmazon/楽天の検索リンクを生成する。タグは汎用的なため、検索結果も広範でCTR（クリック率）が低い。

一方、`_append_trending_topics()` は具体的なトレンド（例: "Claude Codeのハーネスを育てる"、"ローカルLLMを測り比べた"）を注入しているが、アフィリエイトには一切反映されない。

#### 目標

収集したトレンドトピックからアフィリエイトキーワードを抽出し、記事のテーマに即した具体的な商品検索リンクを生成する。

#### 検討したアプローチ

| 方式 | 内容 | メリット | デメリット |
|------|------|----------|------------|
| **A. トレンドキーワード抽出**（推奨） | `_append_trending_topics()` が注入したトレンドタイトルから日本語キーワードを自動抽出。`inject_affiliate_links()` に渡して検索リンクを生成 | 実装が単純、既存コードとの整合性が高い | トレンドタイトルが商品関連でない場合は改善しない |
| **B. AI による商品カテゴリ推論** | プロンプトに「この記事に関連する商品カテゴリをFrontmatterに出力する」指示を追加 | 記事内容に最適化されたキーワード | ハルシネーションのリスク、プロンプト変更が必要 |
| **C. トレンド→商品カテゴリのマッピング** | 各トレンドソースに対して商品カテゴリのルールを事前定義（例: Zenn AI → "AI 書籍"、HackerNews tech → "開発ツール"） | 安定性が高い | 維持コストが高い、新しいトレンドに対応できない |
| **D. 複合キーワード** | A + B の組み合わせ。トレンドから抽出したキーワードと、AI が推論したカテゴリを併用 | 最も正確 | 実装コストが高い |

#### 採用方針: A → D の段階的実装

##### Phase 1（即実装可能）: トレンドキーワード抽出

```
データフローの変更:

Before:
  latest_topics.json → _append_trending_topics() → プロンプト注入のみ
  記事生成 → inject_affiliate_links() → tags からの汎用キーワード

After:
  latest_topics.json → _append_trending_topics() → プロンプト注入 + キーワードリスト返却
  記事生成 → inject_affiliate_links(trend_keywords=...) → トレンドベースのキーワード
```

**実装ポイント:**

1. `_append_trending_topics()` の返り値を `str` → `tuple[str, list[str]]` に変更
   - 第1要素: 注入済みプロンプト（現状と同じ）
   - 第2要素: 抽出したアフィリエイトキーワードのリスト

2. キーワード抽出ロジック:
   - 注入したトレンドタイトルから日本語の単語を抽出
   - 英語タイトルはそのまま、日本語タイトルは主要語を抽出
   - 例: "Claude Codeのハーネスを育てる" → ["Claude Code", "AI開発"]
   - 例: "ローカルLLMを測り比べた" → ["LLM", "GPU", "ローカルAI"]
   - 技術系カテゴリ（tech）のみを対象（kemono/pokemonは商品化されにくい）

3. `inject_affiliate_links(content, trend_keywords=None)`:
   - `trend_keywords` が指定された場合はそれを優先
   - 指定されていない場合は既存の tags 抽出ロジックにフォールバック
   - 複数キーワードがある場合は、上位2つまでを別々のリンクとして出力

##### Phase 2（検討後実装）: AI 推論の追加

Phase 1 の効果を確認した後、プロンプトに以下を追加:

```
【Frontmatter 追加フィールド】
affiliate_keywords: "この記事に関連する商品・書籍の検索キーワード（カンマ区切り、最大3つ）"
```

AI が記事内容に合わせてキーワードを出力。`inject_affiliate_links()` は Frontmatter の `affiliate_keywords` を最優先して利用。

#### 対象カテゴリの絞り込み

| カテゴリ | アフィリエイト対象 | 理由 |
|----------|-------------------|------|
| tech | ✅ 対象 | AI書籍、開発ツール、GPU、クラウドサービスなど商品化しやすい |
| kemono | ✅ 対象 | 絵本、フィギュア、コスプレ関連。2026-09-29 に全カテゴリ対象化 |
| pokemon | ✅ 対象 | ポケモングッズ、図鑑アプリ、ゲーム関連。2026-09-29 に全カテゴリ対象化 |

#### 期待される効果

- 検索キーワードの具体化 → 検索結果の関連性向上 → CTR向上
- トレンドに即した記事 × トレンドに即した商品リンク = 一貫性のあるUX
- Amazon/楽天の検索ページで「この記事のテーマに関連する商品」が表示される

## アフィリエイト商品カードの導入（2026-09-29 実装完了）

### 背景
- 既存のアフィリエイトリンクは `amazon.co.jp/s?k=keyword` 形式で検索結果ページへ誘導するのみ
- 商品画像・価格・評価・商品名が表示されず、購買意欲を十分に引き出せていない

### 実装内容

| 項目 | 内容 | ファイル |
|------|------|----------|
| **product_recommendations フィールド** | Frontmatter に YAML リスト形式で具体商品名・カテゴリ・価格帯を記録 | `prompts/default.txt`, `prompts/kemono_story.txt`, `prompts/ai_deep.txt` |
| **具体商品名指向の指示** | プロンプトに「実在する具体商品名を出力」指示を追加。架空商品名を禁止 | 同上 |
| **商品カードパーサー** | `extract_product_recommendations()` で Frontmatter から YAML ブロックをパース | `scripts/generate_article.py:947-989` |
| **商品カードHTML生成** | `generate_product_cards()` で商品名・カテゴリ・価格帯・Amazon/楽天リンクを含むHTMLカードを生成 | `scripts/generate_article.py:992-1057` |
| **商品カード処理パイプライン** | `process_product_cards()` をメイン処理のステップ5.48に統合。アフィリエイトセクションの手前にカードを挿入 | `scripts/generate_article.py:1060-1096` |
| **商品カードCSS** | レスポンシブ対応のカードスタイル。カテゴリアイコン、価格表示、Amazon/楽天ボタン | `src/styles/global.css` |

### データフロー
```
記事生成 → Geminiが product_recommendations を Frontmatter に出力
→ extract_product_recommendations() でパース
→ generate_product_cards() でHTMLカード生成
→ process_product_cards() で記事に挿入（Frontmatterからは削除）
→ 最終出力: 商品カード + アフィリエイトセクション
```

## メタ記述検証の修正（2026-09-30 実装完了）

### 背景
- `_validate_description()` が80文字未満のdescriptionを無意味な文字（`。`と空白の交互）で埋めていた
- 10件中3件（30%）の最近の記事が80文字未満のdescriptionを持っていた
- `re.sub` の置換文字列にdescription値を直接埋め込んでおり、`\`や`"`を含むと正規表現が破損する可能性があった

### 実装内容

| 項目 | 内容 | ファイル |
|------|------|----------|
| **本文抽出ヘルパー** | `_extract_first_sentence_from_body()` を新規追加。Frontmatter終了後の本文から最初の文を抽出（見出し・画像行をスキップ） | `scripts/generate_article.py:1110-1126` |
| **記述拡張ロジック** | 80文字未満のdescriptionに本文の最初の文を連結して自然に拡張。120文字を超えないように制御 | `scripts/generate_article.py:1129-1146` |
| **正規表現安全化** | `re.sub` の置換文字列に`\`が含まれる場合をエスケープ処理 | `scripts/generate_article.py:1447` |
| **既存記事未修正** | 現在のバリデーターは新規生成時のみ実行。既存記事の修正は将来、独立スクリプト（例: `scripts/fix_descriptions.py`）として単体実行前提で実装予定。通常の生成パイプラインには組み込まない | 保留 |

### データフロー
```
記事生成 → LLMがdescriptionを出力（80-120文字を指示）
→ _extract_fm_field() で抽出
→ _validate_description(desc, content) で検証
  - 80-120文字: そのまま返す
  - 120文字超: 120文字に切り捨て + "..."
  - 80文字未満: _extract_first_sentence_from_body() で本文の最初の文を抽出して連結
→ re.sub でFrontmatterのdescriptionを更新（\をエスケープ）
→ 最終出力: 80-120文字のdescription
```
