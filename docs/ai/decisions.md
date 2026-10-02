# Design Decisions

古い決定は `decisions-archive.md` に移動する。直近15件のみ保持。

## 2026-10-02: Separate Rate Limit Table to Dedicated Doc

**Decision**: Move the API rate limit table from `AGENTS.md` to `docs/ai/api-rate-limits.md` and add a verification rule to run `test_real_apis.py --save` after `fetch_topics.py` updates.

**Reason**: The rate limit table was inline in `AGENTS.md`, making the file bloated. Separating it improves maintainability and keeps `AGENTS.md` focused on operational rules. The verification rule ensures data source availability is checked after trend collection script changes.

**Impact**:
- `AGENTS.md`: Inline rate limit table replaced with reference to `docs/ai/api-rate-limits.md`. Added verification rule for `test_real_apis.py --save` after `fetch_topics.py` changes.
- `docs/ai/api-rate-limits.md`: New file containing the confirmed rate limit table.

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
