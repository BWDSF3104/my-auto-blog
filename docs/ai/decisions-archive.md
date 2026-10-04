# Design Decisions Archive

Older decisions moved from `decisions.md`. Kept 15 most recent in `decisions.md`.

---

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
