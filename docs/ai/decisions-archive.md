# Design Decisions Archive

Older decisions moved from `decisions.md`. Kept 15 most recent in `decisions.md`.

---

## 2026-10-01: Mandatory Impressive Scenes and 3-Image Role Distribution for Kemono Story

**Decision**: Add condition 8 "印象的なシーンの必須配置" to `kemono_story.txt`, requiring at least one impressive scene from four categories: physical intimacy (kiss, hug, head pat, hand-holding), tense close contact (fall collision, narrow space closeness, protective embrace), intense action (duel, chase, magic battle, life-and-death fight), emotional decisive moments (tears, confession, parting, reunion, trust declaration). Redesign image prompt selection rules so the 3 images (1 header `image_prompt` + 2 inline `IMAGE_PROMPT`) each target a distinct moment with no overlap.

**Rationale**: Stories lacked memorable, emotionally impactful scenes. Image prompts for header and inline images targeted "the most impressive scene" identically, causing visual duplication when only 3 images are generated total. Role-based distribution ensures the 3 images cover different emotional beats: header = poster/climax, inline 1 = early-mid intimate/emotional, inline 2 = mid-late action/introspective.

**Rejected Alternatives**:
- 全画像に「最も印象的なシーン」を指定: 3枚で同じ瞬間が描かれ、視覚的に被る
- 画像枚数の増加: 生成コストと読み込み時間が伸びる

**Impact**:
- `scripts/prompts/kemono_story.txt`: 条件8追加、画像選出ルールを3枚の役割分担に書き換え、テンプレート例を更新
- `scripts/prompts/refine_story.txt`: クライマックス精製段階に印象的なシーンの弱化防止チェックを追加

## 2026-10-01: Pollinations.ai Fallback for Image Generation

**Decision**: Add Pollinations.ai as a fallback image generation service when HuggingFace API fails, plus an `IMAGE_PROVIDER` environment variable for direct Pollinations usage during local testing.

**Rationale**: HuggingFace free tier has usage limits. When the quota is exhausted, article generation fails entirely. Pollinations.ai provides a free, no-API-key alternative using the Flux model. The `IMAGE_PROVIDER=pollinations` environment variable allows bypassing HF entirely for quick local testing without consuming HF quota.

**Rejected Alternatives**:
- HuggingFaceの完全な置き換え: HFの画質がPollinationsより安定しているため、プライマリは維持
- APIキーが必要なサービス (SiliconFlow, Cloudflare Workers AI): 設定コストが高く、ローカルテストの利便性が下がる

**Impact**:
- `scripts/generate_article.py`: `import requests`追加、`_save_as_avif()` ヘルパー関数分離、`_generate_image_pollinations()` フォールバック関数追加、`generate_and_save_image()` にフォールバックロジック追加、`IMAGE_PROVIDER` 環境変数対応

## 2026-09-29: Score-Based Topic Sorting

**Decision**: Sort topics by score descending within each category before output.

**Rationale**: Higher-scoring topics are more relevant and should be prioritized when injecting trends into article prompts.

**Rejected Alternatives**:
- 収集順のまま使用: 高スコアトピックが後方に埋もれる
- 固定数のみカットオフ: しきい値の調整が難しい

## 2026-09-29: TTL Validation for Trend Data

**Decision**: Add 24-hour TTL to trend data with validation on read.

**Rationale**: Stale trend data produces irrelevant article content. TTL validation warns users when data is outdated.

**Impact**:
- `fetch_topics.py`: Added `ttl_hours` field to JSON output
- `generate_article.py`: Added `_check_topics_ttl()` function that warns on TTL expiration

## 2026-09-29: Affiliate × Trend Integration Strategy

**Decision**: Adopt Phase 1 approach — extract affiliate keywords from injected trend topics, pass to `inject_affiliate_links()`.

**Rationale**: Current affiliate links use generic tags ("Tech", "AI") producing broad search results with low CTR. Trend topics are specific and product-relevant (e.g., "ローカルLLM", "Claude Code"), enabling targeted affiliate search links.

**Rejected Alternatives**:
- Phase 2 (AI推論) の即時実装: 過剰設計でPhase 1の結果が不明
- 手動でのキーワード指定: 自動化の目的に反する

## 2026-09-29: NSFW Filter for e621

**Decision**: Filter explicit content at collection time in `fetch_topics.py`.

**Rationale**: e621 contains explicit-rated posts that should not appear in article prompts for non-kemono content. Filtering at collection prevents inappropriate content from entering the pipeline.

**Rejected Alternatives**:
- 生成時にフィルタ: 不要なコンテンツがプロンプトに注入されるリスク
- e621の完全な排除: kemono/pokemonカテゴリで有用なSafeコンテンツが失われる

## 2026-09-29: Category Strictification

**Decision**: Enforce strict category routing based on prompt type.

**Rationale**: Story/kemono prompts should only receive Safe-rated kemono content. Default tech prompts should only receive tech trends. Prevents category mismatch and inappropriate content.

**Rejected Alternatives**:
- 全カテゴリを全モードに適用: 不適切なコンテンツが混入する
- カテゴリを完全に分離: 柔軟性が低くなり、新しいモードの追加が困難

## 2026-09-29: Bluesky Collection

**Decision**: Add Bluesky as a trend data source using the public search API.

**Rationale**: Reddit API blocks `.json` endpoints. Bluesky provides an open search API that can supplement tech and kemono trend data.

**Rejected Alternatives**:
- Reddit OAuth 導入: ユーザーインタラクションが必要でCI/CDと相性が悪い
- Twitter API: 有料プランが必要でコストが高い

## 2026-09-29: Frontmatter Reference Tracking

**Decision**: Record injected trend source URLs in article frontmatter.

**Rationale**: Enables traceability of which trends inspired each article. Useful for content auditing and understanding article provenance.

**Rejected Alternatives**:
- 本文末尾にソースURLを明記: 記事の見た目が悪くなり、SEOに悪影響
- ログファイルのみで追跡: 記事自体との関連が失われる

## 2026-09-29: Score Threshold Configuration

**Decision**: Add configurable minimum score threshold for trend injection.

**Rationale**: Low-score topics can dilute article quality. A configurable threshold allows operators to filter without modifying code.

**Rejected Alternatives**:
- コードにハードコード: 運用中の調整が不可能
- 固定数のみ選択: スコア分布の変化に対応できない

## 2026-09-29: Affiliate All-Categories Extension

**Decision**: Extend affiliate keyword extraction to all categories (tech, kemono, pokemon).

**Rationale**: Original design only extracted keywords from tech category. All recent articles use kemono_story prompt type, so affiliate links always fell back to generic tag-based keywords ("Kemono"). Kemono/pokemon topics have merchandise potential (figures, art books, games).

**Rejected Alternatives**:
- techカテゴリのみを維持: kemono記事で常にフォールバックキーワードになる
- カテゴリごとの個別設定: 複雑すぎて維持コストが高い

## 2026-09-29: Deferred Low-Priority Items

**Decision**: Defer partial cache and Reddit OAuth to future iterations.

**Rationale**: Both require significant implementation effort. Partial cache needs per-source cache files and merge logic. Reddit OAuth requires a full OAuth flow with user interaction. Neither blocks core functionality.

**Rejected Alternatives**:
- 即時実装: スコープが膨張し、コア機能の完了が遅れる
- 完全削除: 将来的に必要な可能性を排除しすぎる

## 2026-09-29: SEO Slug Implementation

**Decision**: Add `slug` field to article frontmatter for SEO-friendly URLs.

**Rationale**: File-based URLs (timestamps like `2026-09-29T123456`) are not SEO-friendly. A readable slug improves URL structure, search engine indexing, and user experience.

**Rejected Alternatives**:
- ファイル名のみを使用: タイムスタンプ形式でSEO不向き
- 日付ベースのURL: 記事の更新時にURLが変わり、リンク切れリスク

## 2026-09-29: TOC (Table of Contents) Implementation

**Decision**: Add dynamic TOC navigation to article pages using client-side JavaScript.

**Rationale**: Long articles benefit from in-page navigation. Server-side generation in Astro would require parsing markdown AST; client-side DOM extraction is simpler and maintains reactivity with scroll-based active state.

**Rejected Alternatives**:
- Astro側でMarkdown ASTをパース: 依存が増え、ビルド時間が伸びる
- 手動でTOCを記事に埋め込み: 生成物の保守性が高い

## 2026-09-29: BreadcrumbList JSON-LD

**Decision**: Add schema.org BreadcrumbList structured data to all article and tag pages.

**Rationale**: Breadcrumbs improve SERP display with rich snippets and help search engines understand site hierarchy.

**Rejected Alternatives**:
- 視覚的なパンくずリストのみ: 検索エンジンのリッチスニペットが生成されない
- 全ページに適用: インデックスページでは階層が不明確

## 2026-09-29: WebSite SearchAction

**Decision**: Add schema.org SearchAction to enable Google site search integration.

**Rationale**: Allows Google to show site search results directly in SERPs. Uses `/tags/{search_term_string}` as the search target.

**Rejected Alternatives**:
- 外部検索エンジン (Google Custom Search): 設定が複雑でコストがかかる
- 独自の検索ページ実装: SSGでリアルタイム検索が難しい

## 2026-09-29: Tag Pages

**Decision**: Create tag-based navigation pages for content discovery.

**Rationale**: Tags provide an alternative navigation structure beyond chronological listing. Improves internal linking and SEO through additional indexable pages.

**Rejected Alternatives**:
- カテゴリベースのナビゲーションのみ: タグの方が粒度的に柔軟
- 静的なタグ一覧: 記事追加時に手動更新が必要

## 2026-09-29: Related Posts

**Decision**: Show related posts at the bottom of each article based on shared tags.

**Rationale**: Increases time-on-site, reduces bounce rate, and creates internal link structure for SEO.

**Rejected Alternatives**:
- 日付ベースの前後記事: テーマの関連性が低い
- LLMで関連性を判定: 毎ページの処理コストが高い

## 2026-09-28: Project Structure

**Decision**: Separate immutable rules (AGENTS.md) from changing knowledge (docs/ai/).

**Rationale**: Claude Memory Bank pattern allows agents to distinguish between permanent constraints and evolving project state.

**Rejected Alternatives**:
- 単一ファイルに全て記録: 変更履歴が混在し、ルールの変更が追跡困難
- git commit message のみに依存: Agentが過去の文脈を読み込めない

## 2026-09-29: python-dotenv Adoption

**Decision**: Use `python-dotenv` for environment variable management in scripts.

**Rationale**: Scripts need API keys and configuration from `.env` file. `python-dotenv` provides reliable `.env` loading with fallback to system environment variables.

**Rejected Alternatives**:
- `os.environ` のみ: `.env`ファイルの自動読み込みが不可能
- 設定ファイル (YAML/JSON): 機密情報をリポジトリにコミットするリスク

## 2026-09-29: Mobile Affiliate Link Clickability

**Decision**: Fix mobile clickability for affiliate links.

**Rationale**: Affiliate links were not clickable on mobile devices due to CSS issues.

**Rejected Alternatives**:
- モバイルでのアフィリエイトリンクを非表示: CTRが完全に失われる
- 別テンプレートの使用: 維持コストが2倍になる

## 2026-09-29: GH Actions dotenv Fix

**Decision**: Install `python-dotenv` in GitHub Actions workflow.

**Rationale**: Scripts failed in CI because `python-dotenv` was not installed in the Actions environment.

**Rejected Alternatives**:
- Actionsで.envファイルをコミット: 機密情報の漏洩リスク
- 環境変数の手動設定のみ: ローカル開発とCIの設定が分かれる

## 2026-09-29: Mobile Affiliate Link Clickability

**Decision**: Fix mobile clickability for affiliate links.

**Rationale**: Affiliate links were not clickable on mobile devices due to CSS issues.

**Rejected Alternatives**:
- モバイルでのアフィリエイトリンクを非表示: CTRが完全に失われる
- 別テンプレートの使用: 維持コストが2倍になる

## 2026-09-29: Product Card Generation

**Decision**: Generate visual product cards from `product_recommendations` frontmatter field.

**Rationale**: Text-only affiliate links do not convey product details (name, price, category). Visual cards improve user experience and conversion rates.

**Rejected Alternatives**:
- アフィリエイトリンクのみ: 商品情報が伝わらずCTRが低い
- 外部サービスの商品画像を使用: 著作権と可用性の問題

## 2026-10-02: Random Trend Selection and Character/Copyright Tag Expansion

**Decision**: Remove "pokemon" from `kemono_story` prompt type categories and change trend selection from "top 5 per category" to "random 2 items total across selected categories". Expand e621 character feature collection to include `character` and `copyright` tags.

**Reason**: Pokemon content was polluting kemono story articles with irrelevant keywords. Random selection reduces redundancy when multiple categories overlap. Character and copyright tags from e621 provide valuable context for affiliate product recommendations, enabling the AI to suggest official merchandise and related products.

**Rejected Alternatives**:
- pokemonカテゴリを維持: 将来の専用プロンプトタイプで対応するため、kemono_storyからは除外
- 固定数のトレンド選択: ランダム化によりカテゴリ間の重複を減らし、多様性を向上

**Impact**:
- `fetch_topics.py`: `PROMPT_CATEGORIES["kemono_story"]` から "pokemon" を削除、`CHARACTER_FEATURE_CATEGORIES` に "character", "copyright" を追加、`_aggregate_and_save_character_features()` に character/copyright カウンターを追加
- `generate_article.py`: `import random` 追加、`_append_trending_topics()` を「全カテゴリをプールしてランダム2件」に書き換え、`_load_character_features()` に character/copyright データの注入とアフィリエイト指示を追加
- `data/character_features.json`: "characters" と "copyrights" のフィールドが追加される

---
*以下は 2026-10-04 に decisions.md からアーカイブ*

## 2026-09-30: Per-Source TTL and Timestamped Cache Files

**Decision**: Change cache output from single `data/latest_topics.json` to timestamped `data/topics/{YYYY-MM-DD}_{HHMMSS}.json` with a `latest.json` symlink. Each source object gets its own `fetched_at` timestamp.

**Rationale**: Global TTL forced re-fetching all sources even when only one category was stale. Per-source TTL enables `generate_article.py` to auto-trigger `fetch_topics.py --prompt-type X` for only the expired categories, reducing API calls and generation time.

**Rejected Alternatives**:
- 単一ファイルの継続更新: 履歴が失われ、部分キャッシュとの整合性が取れない
- 完全な部分キャッシュ（`.cache/` 別ディレクトリ）: 複雑すぎて維持コストが大きい

**Impact**:
- `fetch_topics.py`: Outputs timestamped files, updates symlink, supports `--prompt-type` for partial fetches, inherits uncollected source data from previous run
- `generate_article.py`: Reads from symlink, checks per-source TTL via `_check_per_source_ttl()`, auto-triggers fetch via `_auto_fetch_topics()` when needed categories are stale
- Old `data/latest_topics.json` is deprecated

---
*以下は 2026-10-06 に decisions.md からアーカイブ*

## 2026-10-02: Kemono API Integration for Kemono Category

**Decision**: Add Kemono API (`/api/v1/posts`) as a data source for the kemono category, collecting recent posts from Patreon, Fanbox, SubscribeStar, and DLsite.

**Reason**: Reddit API is blocked (HTTP 403/404), so alternative sources are needed for kemono/furry content. Kemono API provides public access to creator posts without authentication.

**Rejected Alternatives**:
- Reddit OAuth 導入: 認証フローが複雑で、CI/CD 環境での維持が困難
- Twitter/X API: 有料プランが必要で、コストが高すぎる

**Impact**:
- `fetch_topics.py`: `collect_kemono_api()` 関数追加、`collect_topics()` に統合
- `test_fetch_topics.py`: `collect_kemono_api` のモックを追加

## 2026-10-02: RSS Feeds for Pokemon Category

**Decision**: Add 4 RSS feeds (PokéCommunity Art Studio, PokeBeach News, PokemonBlog, PocketMonsters) for the pokemon category.

**Reason**: Reddit API is blocked, so RSS feeds provide a stable alternative for pokemon-related content. RSS feeds are publicly accessible and don't require authentication.

**Rejected Alternatives**:
- 公式 Pokémon API: トレンドデータではなくゲームデータのみを提供
- Twitter/X API: 有料プランが必要

**Impact**:
- `fetch_topics.py`: `RSS_FEEDS` に 4 フィード追加、`collect_rss_feeds()` でカテゴリごとにフィルタリング

## 2026-10-02: cp932 Console Encoding Fix

**Decision**: Change `_safe_print()` to use `.encode("cp932", errors="replace")` instead of `.encode("utf-8", errors="replace")` for Windows console output.

**Reason**: Windows console uses cp932 encoding by default. Non-ASCII characters (e.g., "PokéCommunity") caused `UnicodeEncodeError` when printed to the console.

**Rejected Alternatives**:
- UTF-8 を維持: Windows コンソールで引き続きエラーが発生
- `chcp 65001` で UTF-8 に切り替え: 環境ごとに設定が必要で信頼性低い

**Impact**:
- `fetch_topics.py`: `_safe_print()` のエンコーディングを cp932 に変更

## 2026-09-30: Affiliate Link HTML `<a>` Tag Conversion

**Decision**: Change `inject_affiliate_links()` to generate HTML `<a>` tags instead of Markdown `[text](url)` links for affiliate search links.

**Rationale**: Markdown link syntax exposes the full URL with UTM tracking parameters in the rendered page source and potentially in the visual output. HTML `<a>` tags hide the raw URL, showing only the link text. Existing post files are left unchanged as a separate batch-fix issue.

**Rejected Alternatives**:
- 内部リダイレクトページ: 実装コストが高く、既存のデプロイフローを変更する必要あり
- CSSのみで隠蔽: MarkdownリンクのURLはHTMLソースに残るため完全な隠蔽不可能
- 既存記事の一括修正: 修正スクリプトの作成・検証に時間がかかるため保留

**Impact**:
- `scripts/generate_article.py`: `inject_affiliate_links()` のリンク生成ロジックを `<a>` タグに変更
- `docs/ai/known-issues.md`: 既存記事のリンク形式を保留イシューとして追加

## 2026-09-30: Meta Description Validation

**Decision**: Extract first sentence from article body to extend short descriptions. Add regex safety.

**Rationale**: `_validate_description()` padded short descriptions with meaningless characters (`。` and spaces). 30% of recent articles had descriptions under 80 chars. Regex substitution was vulnerable to backslash characters in description text.

**Rejected Alternatives**:
- LLMでdescriptionを再生成: APIコストが高く、生成時間が伸びる
- 既存記事の無視: SEOが継続的に劣化する

## 2026-09-30: CSS-Only Bullet List Affiliate Card Styling

**Decision**: Style bullet list affiliate links as card-style elements using CSS `:has()` selector, without modifying Python templates.

**Rationale**: Bullet list links (`- 📦 [Amazonで〜を探す](url)`) were rendered as plain underlined text, inconsistent with the visual product cards. CSS-only approach avoids template changes and retroactively applies to all existing posts.

**Rejected Alternatives**:
- Pythonテンプレートの変更: 既存記事に遡及適用できない
- HTMLの完全な書き換え: 既存記事の再生成が必要でコストが高い

## 2026-09-30: Affiliate Keyword Contextualization

**Decision**: Change affiliate keyword priority to "article-extracted > filtered trend_keywords > tags fallback".

**Rationale**: `inject_affiliate_links()` used `trend_keywords` directly, which contained GitHub repo names (e.g., "o3-pro", "langgraph") that produced irrelevant affiliate search results. Article tags and body text reflect the actual article theme, producing more relevant product search links.

**Rejected Alternatives**:
- trend_keywordsをそのまま使用: GitHubリポジトリ名が混入し、無関係な検索結果になる
- tagsのみを使用: 記事のテーマを十分に反映できない

## 2026-10-02: e621 rating:safe for Kemono Trending Works

**Decision**: Add `rating:safe` or `rating:questionable` to e621 tag queries to avoid NSFW filtering. Expand tags to include furry/wolf/fox/rabbit species with `order:score` for trending works tracking.

**Reason**: Without rating restrictions, e621 queries returned mostly NSFW content that was filtered out (30/35 posts filtered). Adding `rating:safe` ensures usable SFW results. Expanding species tags captures more kemono/furry trending works.

**Rejected Alternatives**:
- NSFWフィルタの緩和: 生成された記事に不適切なコンテンツが含まれるリスク
- e621の完全な置き換え: 公開APIで認証不要な代替ソースが限られる

**Impact**:
- `fetch_topics.py`: `E621_TAGS` に `rating:safe` または `rating:questionable` を追加、furry/wolf/fox/rabbit の `order:score` クエリを追加
- kemono カテゴリの e621 収集件数が 3件 → 30件に増加

## 2026-10-02: Replace latest.json Symlink with File Copy

**Decision**: Replace `os.symlink()` with `shutil.copy2()` for `data/topics/latest.json`, converting it from a symlink to a regular file copy of the latest timestamped file.

**Reason**: The symlink stored an absolute path (e.g., `/home/runner/work/...` from GitHub Actions) in git, making it broken on local Windows and GitHub Pages. Symlinks require `core.symlinks` configuration and admin privileges on Windows, causing cross-platform incompatibility. Both consumers (`generate_article.py` reading topics and `fetch_topics.py` inheriting `fetched_at`) only need the file content, not symlink behavior.

**Rejected Alternatives**:
- シンボリックリンクを維持: 絶対パスがコミットされ、クロスプラットフォームで壊れる
- `.gitattributes` で `core.symlinks=true` 設定: 開発環境ごとに設定が必要で信頼性低い
- `data/latest_topics.json` の単一ファイルに戻す: タイムスタンプファイルの履歴追跡が失われる

**Impact**:
- `fetch_topics.py`: `os.symlink()` → `shutil.copy2()`, `import shutil` 追加
- `test_fetch_topics.py`: シンボリックリンク検証テストをファイルコピー検証に更新
- `data/topics/latest.json`: git 管理下の通常ファイルとしてコミット可能に
