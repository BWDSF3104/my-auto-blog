# Design Decisions

古い決定は `decisions-archive.md` に移動する。直近15件のみ保持。

## 2026-10-04: 重複YAMLキーの自動修復ロジック

**Decision**: `generate_article.py` の `validate_and_fix_frontmatter()` 内で、PyYAML `safe_load` 検証より前に重複キーチェックを无条件で実行。キャラクターキーの命名規則を `character_N` に強制し、AI が出力したキャラクタータイプ名（例: `少年:`）を自動リネーム。

**Reason**: AI がプロンプト指示の `character_1`/`character_2` を無視し、キャラクタータイプ名をキーとして出力するため、2人以上で重複し Astro/Vite が `duplicated mapping key` でビルド中断。PyYAML の `safe_load` は重複キーでエラーを発生させないので、事前チェックが必須。

**Rejected Alternatives**:
- AI プロンプトの修正のみ: AI が指示を無視する根本問題は解決しない
- `safe_load` のみの検証: 重複キーを検出できない
- ビルド失敗後の手動修正のみ: CI/CD パイプラインが毎度ブロックされる

**Impact**:
- `scripts/generate_article.py`: `_fix_duplicate_yaml_keys()` と `_is_character_like_key()` ヘルパー関数を追加、`validate_and_fix_frontmatter()` に无条件の重複チェックを組み込み
- `scripts/tests/test_generate_article.py`: 重複キー修復のテストケースを追加

## 2026-10-03: npm サプライチェーン攻撃対策の適用

**Decision**: npm の依存パッケージをバージョン固定化し、npm グローバル設定でサプライチェーン攻撃対策を有効化。

**Reason**: 2025-2026年にnpmエコシステムで複数の大規模なサプライチェーン攻撃（Shai-Hulud, ChainDrop, Miasma, IronWorm, GHAPPIER など）が発生。自己複製型のマルウェアが500〜1300以上のパッケージを汚染し、install-time script を経て資格情報を窃取する攻撃が常態化。本项目の直のパッケージ（astro, tailwindcss 等）は汚染リストには含まれていないが、推移的依存の `http-cache-semantics` に high 脆弱性（GHSA-ch52-4w7c-c8xp）が存在。

**Applied Settings**:

- `package.json`: 全パッケージのバージョン指定を `^` から exact version に変更（例: `^7.3.5` → `7.3.5`）
- `npm config set save-exact=true`: 今後 `npm install` する際にexact versionを記録
- `npm config set min-release-age=7`: 公開後7日未満のバージョンはインストールしない（汚染された新バージョンの回避）
- `npm config set ignore-scripts=true`: install-time script（postinstall, preinstall など）を無効化（マルウェア拡散経路の遮断）

**Impact**:
- `package.json`: `astro`, `tailwindcss`, `@tailwindcss/vite`, `@tailwindcss/typography` のバージョンを固定
- `package-lock.json`: 既存のロックファイルと整合性あり
- `allowScripts.esbuild`: `ignore-scripts=true` により無効化されるが、esbuildのネイティブバイナリは別パッケージとしてインストールされるためビルドに影響なし
- ビルド動作は確認済み（`npm run build` 成功）
- 今後 install script が必要なパッケージを追加する場合は `npm install --ignore-scripts=false` で明示的に有効化する必要がある

**Rejected Alternatives**:
- `^` を維持: メジャーバージョン内の自動更新が許可され、汚染された新バージョンがインストールされるリスク
- `~` (minor以下のみ) の使用: patch版本の自動更新が許可され、完全な固定ではない
- npm v12のリリースを待機: npm v12ではinstall scriptがデフォルト無効化されるが、リリース時期が不明確

## 2026-10-02: レート制限テーブルを独立ドキュメントに分離

**Decision**: AGENTS.md のレート制限テーブルを `docs/ai/api-rate-limits.md` に分離。`fetch_topics.py` 更新後に `test_real_apis.py --save` を実行する検証ルールを追加。

**Reason**: AGENTS.md にインラインで配置していたレート制限テーブルがファイル肥大化の原因。分離して保守性を向上し、AGENTS.md を運用ルールに集中させる。検証ルールにより、トレンド収集スクリプト変更後のデータソース可用性をチェック。

**Impact**:
- `AGENTS.md`: インラインレート制限テーブルを `docs/ai/api-rate-limits.md` への参照に置換。`fetch_topics.py` 変更後の `test_real_apis.py --save` 検証ルールを追加。
- `docs/ai/api-rate-limits.md`: 確認済みのレート制限テーブルを含む新ファイル。

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


