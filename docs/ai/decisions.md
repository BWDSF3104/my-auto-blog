# Design Decisions

古い決定は `decisions-archive.md` に移動する。直近15件のみ保持。

## 2026-10-01: Remove Deploy Success Skip Logic

**Decision**: Remove `check_deploy_success()` function and `data/.last-deploy-success.json` deploy timestamp recording. Generation no longer skips based on same-day deploy records.

**Reason**: The skip logic was intended to prevent duplicate generation on the same day, but it blocked legitimate regeneration when needed. Removing it simplifies the pipeline and allows the workflow to generate articles on each run.

**Rejected Alternatives**:
- スキップロジックを維持: 再生成が必要な場合にブロックされる問題が残る

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

## 2026-09-29: GH Actions dotenv Fix

**Decision**: Install `python-dotenv` in GitHub Actions workflow.

**Rationale**: Scripts failed in CI because `python-dotenv` was not installed in the Actions environment.

**Rejected Alternatives**:
- Actionsで.envファイルをコミット: 機密情報の漏洩リスク
- 環境変数の手動設定のみ: ローカル開発とCIの設定が分かれる
