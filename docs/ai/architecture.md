# Architecture

## Overview

Automated blog generation system with three main components: trend collection, article generation, and static site hosting.

## Data Flow

```
Trend Sources → fetch_topics.py → data/topics/{timestamp}.json → generate_article.py → src/content/posts/
                                               ↕ latest.json (コピー)
                                                      ↓
                                           Affiliate Keywords → inject_affiliate_links() → Amazon/Rakuten links
                                                     ↓
                                            Product Recommendations → generate_product_cards() → Product cards HTML
```

> ログ・メタログ・CI log の**全出力先**は [`docs/ai/log-locations.md`](log-locations.md) で網羅的に記録している。
> 上記は「データ」の流れであり、ログ（監査・検証・コンソール・サイト表示）は上記ドキュメント参照。

## Components

### Trend Collection (`scripts/fetch_topics.py`)

Collects trending topics from multiple sources:

| Source | API | Category | Status | Notes |
|--------|-----|----------|--------|-------|
| HackerNews | Firebase API | tech | ✅ Active | |
| Reddit | .json endpoint | kemono/pokemon/tech | ⏸️ Disabled | 403 Blocked (2026-10-06 コメントアウト) |
| e621 | REST API | —（トレンド出力に含めない） | ✅ Active | キャラクター特徴集計のみ。2026-10-10 以降トレンド配管から分離（`latest.json` に入れない、`NON_TREND_SOURCES` ガード） |
| RSS (Zenn/Qiita) | xml.etree.ElementTree | tech | ✅ Active | |
| RSS (PokéCommunity/PokeBeach/PokemonBlog/PocketMonsters) | xml.etree.ElementTree | pokemon | ✅ Active | |
| GitHub | Search API | kemono/pokemon | ✅ Active | 未認証 60req/h |
| Bluesky | AT Protocol search API | tech/kemono/pokemon | ⏸️ Disabled | 501 Not Implemented (2026-10-06 コメントアウト) |
| GameSpot RSS | RSS 2.0 解析 | kemono | ✅ Active | ゲームニュース → ストーリーインスピレーション |
| IGN RSS | RSS 2.0 解析 | kemono | ✅ Active | ゲーム・エンタメニュース |
| Anime News Network | HTMLパース | kemono | ✅ Active | アニメニュース |

**カテゴリ別ソース構成:**
- **tech**: HackerNews, RSS (Zenn/Qiita)
- **kemono**: GitHub, GameSpot, IGN, Anime News Network
- **pokemon**: GitHub, RSS (PokéCommunity/PokeBeach/PokemonBlog/PocketMonsters)

Output: `data/topics/{YYYY-MM-DD}_{HHMMSS}.json` with structure:
- `fetched_at`: Run start ISO timestamp
- `ttl_hours`: Data validity period (24h, configurable via env var)
- `sources`: Per-source objects, each with `fetched_at` and `topics` array
- Symlink: `data/topics/latest.json` → newest file (backward compatibility)

Category-based source filtering: each source can be configured to collect for specific categories. e621 is filtered by NSFW rating at collection time. Per-source TTL allows `generate_article.py` to auto-trigger `fetch_topics.py --prompt-type X` when needed categories are stale.

Since 2026-10-10, e621 is separated from the trend pipeline: `collect_e621()` collects posts for character feature aggregation only (no trend topics), and `main()` filters `latest.json` output via the `NON_TREND_SOURCES` constant (covers the merge-inheritance path from previous data as well). e621 data is used only for character feature aggregation (`_aggregate_and_save_character_features` → `data/character_features.json`).

### Article Generation (`scripts/generate_article.py`)

Generates blog posts using AI:

| Service | Model | Purpose |
|---------|-------|---------|
| Gemini API | gemini-3.x | Text generation |
| HuggingFace | blume/kemono-image-api | Primary image generation |
| Pollinations.ai | Flux | Fallback image generation (no API key, free) |

Prompt templates:
- `default.txt`: Tech/AI articles
- `ai_deep.txt`: Deep AI technical articles
- `kemono_story.txt`: Kemono fiction stories

2-pass generation: draft → refine workflow with separate prompts for tech articles and stories.

Image generation:
- SFW enforced via `BASE_QUALITY_PROMPT` with "safe for work, wholesome, family-friendly" tags
- Per-article art style from frontmatter `art_style` field via `extract_art_style()`
- Header image (896×512px AVIF) + inline images from `<!-- IMAGE_PROMPT: "..." -->` markers
- All images saved to `public/images/`
- Fallback: HF failure (2 retries exhausted) → Pollinations.ai (`https://image.pollinations.ai/prompt/`)
- Local testing: `IMAGE_PROVIDER=pollinations` skips HF and uses Pollinations directly

Output: Markdown files in `src/content/posts/` with AVIF images in `public/images/`

### Image Generation Space (`hf-space/` → `blume/kemono-image-api`)

自社ホスト HuggingFace Space（ZeroGPU）のデプロイ元ソース。`generate_article.py` の画像生成パイプラインはこれをプライマリとして呼び出す。

| Item | Detail |
|------|--------|
| モデル | `IbarakiDouji/Nova-Furry-XL`（SDXL / Illustrious 系、`novaFurryXL_ilV180A.safetensors`） |
| ランタイム | ZeroGPU、`@spaces.GPU(duration=20)`（実推論約 5 秒） |
| Scheduler | `EulerAncestralDiscreteScheduler` (Euler a) |
| API | Gradio `predict`: `prompt, negative_prompt, steps, guidance_scale, width, height, seed`（`seed >= 0` で再現可能） |

実装メモ（`hf-space/app.py`）:
- 長プロンプト対応: 75 トークン単位チャンク分割（BOS/EOS 付き）+ デュアルテキストエンコーダ（OpenCLIP ViT-H / CLIP ViT-L）。SDXL の conditioning 形式（pooled は最初のチャンクのみ）を再現
- negative prompt の embedding キャッシュ: チャンク構成が同一なら 1 回のみ計算
- **強調構文なし**: プロンプトは CLIP トークナイザでそのままトークン化されるため、A1111 系 `(word:1.1)` / `[word]`（0.83x）の強調構文は解析されない（リテラルトークンとして扱われる）
- `app.py` の Gradio UI 既定値は例示のみ。本番の positive / negative prompt は完全クライアント駆動（`scripts/article/image.py`）
- テストルール: `hf-space/TEST_RULES.md`（ZeroGPU クォータ 3.5 分/日・steps 18 以下・512x512）

### Affiliate Integration (Implemented)

Trend topics are used to generate targeted affiliate search links and product cards:

1. `_append_trending_topics()` returns the injected prompt plus a list of extracted keywords from the trend titles
2. Keywords are passed to `inject_affiliate_links(content, trend_keywords=...)`
3. All categories (tech, kemono, pokemon) produce affiliate keywords
4. Links are generated for Amazon and Rakuten with UTM tracking and click analytics
5. `product_recommendations` frontmatter field generates visual product cards with name, category, price range, and affiliate links

末尾セクション（「### 📚 テーマ関連のおすすめアイテム・書籍」）の構成:
- 楽天API商品カード（最大3枚、カスケード検索: Gemini商品名 → 先頭句 → タグ由来キーワード。画像・価格付き）— 常時ON
- タグ由来の検索リンク行（キーワードごとの「Amazon / 楽天市場で検索」行）— `ENABLE_TAG_AFFILIATE` でトグル（デフォルトOFF、`ENABLE_TAG_AFFILIATE=1` でON。OFFかつ楽天APIカードも無い場合はセクション全体をスキップ）
- アフィリエイト開示文言 — セクション出力時に常時ON

Phase 2 (AI-inferred keywords via Frontmatter) is deferred pending Phase 1 results.

### Static Site (`astro.config.mjs`)

Astro SSG with:
- Tailwind CSS 4.3
- Content collections for posts
- GitHub Pages deployment
- Base path: `/my-auto-blog/`
- SEO: slug routing, TOC, breadcrumbs, tag pages, related posts, BreadcrumbList/SearchAction JSON-LD

## API Keys

All API keys are managed via `.env` (git-ignored) and GitHub Repository Secrets.
Scripts use `python-dotenv` (`from dotenv import load_dotenv`) to load environment variables.

| Service | Env Var | Name |
|---------|---------|------|
| Gemini | `GEMINI_API_KEY` | - |
| HuggingFace | `HF_TOKEN` | read/write ロール必要（細粒度トークンは ZeroGPU quota API 不可） |
| Amazon | `AMAZON_TRACKING_ID` | - |
| Rakuten | `RAKUTEN_AFFILIATE_ID` | - |

**HF 運用**:
- CLI 認証: `hf auth login`（トークンをローカル保存）
- ZeroGPU 残り確認: `hf spaces zero-gpu quota`（`huggingface_hub` v2.1.0+ 必要）
- Space 停止時は再開に数分要する。起動待ち中にリクエストすると失敗する
- `gradio-client` は 2.7.2+ を使用（`huggingface_hub` 2.x 互換）

**HF Space デプロイ** (`hf-space/app.py` 変更後):
- アップロード: `hf upload --repo-type space blume/kemono-image-api hf-space\app.py`
- 起動確認: `python -c "from huggingface_hub import HfApi; api = HfApi(); info = api.get_space_runtime('blume/kemono-image-api'); print(info.stage)"` → `RUNNING` になるまで待機
- 生成テスト: `python scripts/_test_hf_space.py` （Space が `RUNNING` 後に実行）
- Space URL: `https://huggingface.co/spaces/blume/kemono-image-api`
- Scheduler: `EulerAncestralDiscreteScheduler` (Euler a)
- GPU予約: `@spaces.GPU(duration=20)` (実推論約5秒、マージン含め20秒)

## Development Tools (`maintenance/`)

本番パイプライン外の開発用ツール置き場:

| Tool | Purpose |
|------|---------|
| `bin/archive_memory_bank.py`（Kilo_Commons 正典） | Memory Bank バッチクリーンアップ（cwd ルート判定）。dry-run 既定・`--apply` で反映。tasks/ は mtime 14 日基準でアーカイブ、verification/ は mtime 順直近 2 ラン保持、tmp/ は最更新 mtime が 7 日以上経過したエントリを削除（保持期間は `--tmp-retention-days` で変更）。削除は正典 `kilo-safe-remove` / `kilo-safe-rmdir`（Windows ゴミ箱へ・復元可能）へ委譲。git add は repo 存在時のみ（なければ skipped） |
| `bin/task_manager.py`（Kilo_Commons 正典） | タスク開始/終了。tasks/ と current-task.tsv の更新、完了時の「対応項目チェック」 |
| `bin/kilo-vscode-restart.cmd`（Kilo_Commons 正典） | VS Code 正規クローズ（WM_CLOSE）＋再起動。強制終了なし、タスクスケジューラへ委譲。正典化（2026-10-29）でプロジェクト内コピーをリタイア |

> 各バッチの実行方法・呼び出しタイミング・副作用・関連テスト/設計の詳細: [`docs/ai/maintenance-batches.md`](ai/maintenance-batches.md)

テスト: 正典ツールは Kilo_Commons `tests/`（`python -m pytest tests/ -v`）。プロジェクト固有テストのみ `maintenance/tests/`（標準コマンドは `pytest scripts/tests/ -v`）

## Configuration

- Node.js >= 22.12.0 required
- Python 3.10+ for scripts
- Output format: Markdown with AVIF images
- AI Memory Bank: `docs/ai/` (tracked in git, contains tasks, backlog, known-issues, decisions, architecture)
