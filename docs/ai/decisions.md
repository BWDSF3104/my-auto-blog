# Design Decisions

## 2026-09-30: Deploy Success Timestamp for Duplicate Prevention

**Decision**: Record a deploy-success timestamp in `data/.last-deploy-success.json` after successful deployment. Before generating a new article, check if a same-day successful deploy already exists — if so, skip generation with `sys.exit(0)`.

**Rationale**: The existing `data/.last-generated.json` timestamp was recorded on generation success, not deploy success. When deploy failed after generation, the timestamp was still set, so the next run skipped generation. Recording only on deploy success ensures the timestamp reflects actual published content. Additionally, character/theme duplication in story articles was not detected because overlap checks only compared titles — extending to full frontmatter (character_1, character_2, tags, art_style) gives the LLM negative instructions to avoid reused character combinations.

**Rejected Alternatives**:
- デプロイ失敗時の rollback job: 追加の CI/CD 複雑さで効果に見合わない
- 生成完了時のみタイムスタンプ記録（既存の方式）: デプロイ失敗時に誤ってスキップされる

**Impact**:
- `.github/workflows/deploy.yml`: `build-and-deploy` job に deploy 成功後の記録ステップ追加
- `scripts/generate_article.py`: `check_deploy_success()` 関数追加、`get_recent_meta_by_type()` 関数追加、NG 指示ブロックを強化

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

## 2026-09-29: SFW Enforcement + Art Style Unification

**Decision**: Enforce SFW image generation and unify art style per article.

**Rationale**: Image prompts were inconsistent, leading to varying art styles within a single article. SFW enforcement ensures content safety for all generated images.

**Rejected Alternatives**:
- 画像ごとに手動でスタイル指定: 生成パイプラインの自動化が壊れる
- 固定のデフォルトスタイル: 記事のテーマに合わない

## 2026-09-29: Affiliate Link Improvements

**Decision**: Add contextual inline placement, UTM tracking, click analytics, and comparison table for affiliate links.

**Rationale**: Generic affiliate links at the bottom of articles had low visibility and no tracking. Inline contextual placement improves CTR. UTM parameters and analytics enable performance measurement.

**Rejected Alternatives**:
- 記事末尾へのリンク配置のみ: 視認性が低くCTRが低い
- 外部解析サービスの利用: コストとプライバシーの問題

## 2026-09-29: Category-Based Source Filtering

**Decision**: Each trend source can be configured to collect for specific categories.

**Rationale**: Not all sources are relevant to all categories. Filtering at the source level prevents irrelevant data from entering the pipeline.

**Rejected Alternatives**:
- 全ソースから全カテゴリを収集: 無関係なデータが混入し、API呼び出しが無駄になる
- ソースごとに別スクリプト: 維持コストが膨大になる

## 2026-09-29: Product Card Generation

**Decision**: Generate visual product cards from `product_recommendations` frontmatter field.

**Rationale**: Text-only affiliate links do not convey product details (name, price, category). Visual cards improve user experience and conversion rates.

**Rejected Alternatives**:
- アフィリエイトリンクのみ: 商品情報が伝わらずCTRが低い
- 外部サービスの商品画像を使用: 著作権と可用性の問題

## 2026-09-30: Meta Description Validation

**Decision**: Extract first sentence from article body to extend short descriptions. Add regex safety.

**Rationale**: `_validate_description()` padded short descriptions with meaningless characters (`。` and spaces). 30% of recent articles had descriptions under 80 chars. Regex substitution was vulnerable to backslash characters in description text.

**Rejected Alternatives**:
- LLMでdescriptionを再生成: APIコストが高く、生成時間が伸びる
- 既存記事の無視: SEOが継続的に劣化する

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

## 2026-09-30: Per-Source TTL Cache with Time-Stamped Files

**Decision**: Replace single-file cache with per-run timestamped files, each containing per-source TTL tracking. Eliminate partial cache layer.

**Rationale**: Current `latest_topics.json` is overwritten on each run, losing history. All sources are fetched regardless of prompt type, wasting API calls. Character/theme overlap between consecutive articles may be caused by stale cached data being reused across multiple generations within the 24h TTL window.

**New structure**:
- Files: `data/topics/{YYYY-MM-DD}_{HHMMSS}.json` (one per run)
- Compatibility: `data/topics/latest.json` symlink to newest file
- Each source has independent `fetched_at` for TTL tracking
- `generate_article.py` auto-triggers `fetch_topics.py --prompt-type X` when needed categories are stale
- Partial cache (`.cache/` directory) is not needed — per-source TTL within a single file provides sufficient granularity

**Impact**:
- `fetch_topics.py`: Output to timestamped file, per-source `fetched_at` in JSON, update symlink
- `generate_article.py`: Read from `latest.json`, check per-source TTL, auto-trigger fetch for stale sources with correct `--prompt-type`
- `data/latest_topics.json` → `data/topics/latest.json` (symlink)

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

## 2026-10-01: Mandatory Impressive Scenes and 3-Image Role Distribution for Kemono Story

**Decision**: Add condition 8 "印象的なシーンの必須配置" to `kemono_story.txt`, requiring at least one impressive scene from four categories: physical intimacy (kiss, hug, head pat, hand-holding), tense close contact (fall collision, narrow space closeness, protective embrace), intense action (duel, chase, magic battle, life-and-death fight), emotional decisive moments (tears, confession, parting, reunion, trust declaration). Redesign image prompt selection rules so the 3 images (1 header `image_prompt` + 2 inline `IMAGE_PROMPT`) each target a distinct moment with no overlap.

**Rationale**: Stories lacked memorable, emotionally impactful scenes. Image prompts for header and inline images targeted "the most impressive scene" identically, causing visual duplication when only 3 images are generated total. Role-based distribution ensures the 3 images cover different emotional beats: header = poster/climax, inline 1 = early-mid intimate/emotional, inline 2 = mid-late action/introspective.

**Rejected Alternatives**:
- 全画像に「最も印象的なシーン」を指定: 3枚で同じ瞬間が描かれ、視覚的に被る
- 画像枚数の増加: 生成コストと読み込み時間が伸びる

**Impact**:
- `scripts/prompts/kemono_story.txt`: 条件8追加、画像選出ルールを3枚の役割分担に書き換え、テンプレート例を更新
- `scripts/prompts/refine_story.txt`: クライマックス精製段階に印象的なシーンの弱化防止チェックを追加

## 2026-09-29: GH Actions dotenv Fix

**Decision**: Install `python-dotenv` in GitHub Actions workflow.

**Rationale**: Scripts failed in CI because `python-dotenv` was not installed in the Actions environment.

**Rejected Alternatives**:
- Actionsで.envファイルをコミット: 機密情報の漏洩リスク
- 環境変数の手動設定のみ: ローカル開発とCIの設定が分かれる

## 2026-10-01: Pollinations.ai Fallback for Image Generation

**Decision**: Add Pollinations.ai as a fallback image generation service when HuggingFace API fails, plus an `IMAGE_PROVIDER` environment variable for direct Pollinations usage during local testing.

**Rationale**: HuggingFace free tier has usage limits. When the quota is exhausted, article generation fails entirely. Pollinations.ai provides a free, no-API-key alternative using the Flux model. The `IMAGE_PROVIDER=pollinations` environment variable allows bypassing HF entirely for quick local testing without consuming HF quota.

**Rejected Alternatives**:
- HuggingFaceの完全な置き換え: HFの画質がPollinationsより安定しているため、プライマリは維持
- APIキーが必要なサービス (SiliconFlow, Cloudflare Workers AI): 設定コストが高く、ローカルテストの利便性が下がる

**Impact**:
- `scripts/generate_article.py`: `import requests`追加、`_save_as_avif()` ヘルパー関数分離、`_generate_image_pollinations()` フォールバック関数追加、`generate_and_save_image()` にフォールバックロジック追加、`IMAGE_PROVIDER` 環境変数対応
