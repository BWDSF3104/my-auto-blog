# my-auto-blog

> **BWD's AI Auto Blog** — Gemini API × GitHub Actions による自動生成技術＆ストーリーブログ

トレンドデータを収集し、AI が毎日自動で記事・画像・商品推薦を生成して GitHub Pages にデプロイする静的ブログです。
データベースも認証も SSR も使わず、Astro による純粋な SSG（Static Site Generator）で構成されています。

## 特徴

- **毎日の自動生成** — トレンド収集 → AI 記事生成 → 画像生成 → ビルド → デプロイまでを GitHub Actions が毎日（日本時間 8:00）自動実行
- **トレンド連動** — Hacker News / RSS / GitHub Search / ゲーム・アニメニュースなど複数ソースから収集したトピックをプロンプトに注入
- **ジャンルスコアリング** — Cloudflare Workers AI（Clef-flash）でトレンドに事前採点し、記事の世界設定・ジャンルに合うトピックを優先選択
- **2-pass 生成** — Gemini が下書き（draft）を作成し、別プロンプトで精製（refine）する 2 段階の文章生成
- **AI 画像生成** — 自社ホストの HuggingFace Space（ZeroGPU）上で動く Stable Diffusion XL（SDXL）を第一候補、Pollinations.ai（Flux）をフォールバックに使用。ヘッダー画像とインライン画像を AVIF で出力
- **アフィリエイト統合** — Amazon / 楽天の検索リンク（UTM トラッキング付き）と、楽天 Web Service API による商品推薦カード
- **SEO 最適化** — slug ルーティング、目次（TOC）、パンくずリスト、タグページ、関連記事、JSON-LD（BreadcrumbList / SearchAction / Speakable）、サイト内検索

## 生成フロー

```text
 GitHub Actions (deploy.yml)
 毎朝 日本時間 8:00 / 手動トリガー
        │
        ▼
 ① トレンド収集        scripts/fetch_topics.py        (APIキー不要)
   Hacker News / RSS / GitHub Search / ゲーム・アニメニュース / e621
        │   → data/topics/{timestamp}.json + latest.json
        ▼
 ② ジャンルスコアリング  scripts/genre_score.py
   Cloudflare Workers AI (Clef-flash)
        │   → data/genre_scores/topics.json   (失敗時はランダム選択にフォールバック)
        ▼
 ③ 記事・画像生成       scripts/generate_article.py
   Gemini (2-pass) + SDXL/Pollinations + アフィリエイト
        │   → src/content/posts/*.md + public/images/*.avif
        ▼
 ④ コミット・プッシュ   github-actions[bot] による自動コミット（[skip ci] 付き）
        ▼
 ⑤ ビルド              generate-search-index.js + astro build
        ▼
 ⑥ デプロイ            GitHub Pages
```

### ① トレンド収集（`scripts/fetch_topics.py`）

API キーが不要な公開エンドポイントから多ソースでトレンドを収集します。
ソースごとにカテゴリ（`tech` / `kemono` / `pokemon`）が設定されており、カテゴリごとの TTL（デフォルト 24 時間）で鮮度を管理します。

- 出力: `data/topics/{YYYY-MM-DD_HHMMSS}.json` と `latest.json`（最新コピー）
- 記事生成時にカテゴリが古いと判定されると、必要に応じて `fetch_topics.py` が自動再実行されます

### ② ジャンルスコアリング（`scripts/genre_score.py`）

トレンドトピックと関連する作品名・著作権名を Cloudflare Workers AI の判断特化モデル（Clef-flash）に渡し、ジャンルごとの適合度（0〜100 点）を採点します。

- 出力: `data/genre_scores/topics.json`（API 呼び出しはキャッシュして再利用）
- スコアファイルが無い・生成失敗時は `generate_article.py` がランダム選択にフォールバックするため、フローの失敗にはしません

### ③ 記事・画像生成（`scripts/generate_article.py`）

本プロジェクトの中核スクリプトです。処理は以下の順に行われます。

1. **被り防止** — 直近の同タイプ記事のタイトル・キャラクター設定・アートスタイルを読み込み、「これと被らないで」という指示をプロンプトに注入
2. **世界設定の決定** — ストーリー系記事では、世界観（ファンタジー / イセカイ / SF / 現代 ほか 12 種）・キャラクター構成・関係性などを重み付きランダムで決定し、ジャンルスコアリングで選んだトレンドと突合
3. **プロンプト構築** — `scripts/prompts/` のテンプレート（`default.txt` 技術系 / `ai_deep.txt` AI 深掘り / `kemono_story.txt` ストーリー系）に、被り防止指示・トレンドトピック・キャラクター参考データ（e621 タグ集計）を注入
4. **Pass 1（下書き）** — Gemini API で記事を生成
5. **Pass 2（精製）** — `refine_tech.txt` / `refine_story.txt` の別プロンプトで下書きを精製
6. **画像生成** — 記事 frontmatter からキャラクター設定（`character_1` 等）と `art_style` を抽出し、ヘッダー画像（896×512 AVIF）と本文の `<!-- IMAGE_PROMPT: "..." -->` マーカーによるインライン画像（最大 7 枚）を生成。記事ごとに base seed を共有してスタイルを一貫させ、SFW タグを固定付与して安全な画像生成を強制
   - 第一候補: 自社ホストの HuggingFace Space（ZeroGPU、SDXL パイプライン）を `gradio_client` で呼び出し
   - フォールバック: 2 回リトライしても失敗した場合は Pollinations.ai（Flux、API キー不要）に切り替え
   - `IMAGE_PROVIDER=pollinations` で HF をスキップしてローカルテストが可能
7. **アフィリエイト注入** — トレンドから抽出したキーワードで Amazon / 楽天の検索リンク（UTM 付き）を生成。楽天 Web Service API で実際に商品を検索し、frontmatter の `product_recommendations` と合わせて商品推薦カード（名称・カテゴリ・価格帯・アフィリエイトリンク）を挿入（検索結果は 30 日キャッシュ）
8. **内部リンク・slug 処理** — 既存記事への関連リンク（最大 5 本）を注入。slug 衝突時はリダイレクトを `data/slug-redirects.json` に登録
9. **frontmatter 検証・修正** — description の検証・補正、YAML の重複キー修正など
10. **生成情報セクション追記** — 記事末尾に使用したトレンド情報とキャラクターデータを「生成情報」として追記
11. **保存・ログ** — `src/content/posts/{timestamp}-auto-post.md` と `public/images/` に保存。使用プロンプト（`data/prompt_logs/`）、下書きメタデータ（`data/drafts/`）、トレンド使用ログ（`data/trend_usage_logs/`）を記録し、古いログは期間ベースで自動削除

### ④〜⑥ コミット・ビルド・デプロイ

生成物（記事・画像・キャッシュ JSON・ログ）を `github-actions[bot]` が `[skip ci]` 付きコミットでプッシュした後、`npm run build`（サイト内検索インデックス生成 + Astro ビルド）で `dist/` を作成し、GitHub Pages（ベースパス `/my-auto-blog/`）へデプロイします。

## 技術スタック

| レイヤー | 技術 |
|---------|------|
| サイト | Astro 7（SSG）、Tailwind CSS 4（`@tailwindcss/vite`） |
| Node.js | >= 22.12.0 |
| 自動化スクリプト | Python 3.10+（`requests` / `python-dotenv` / `PyYAML` / `google-genai` / `gradio_client` / `Pillow` + `pillow-avif-plugin`） |
| 文章生成 | Google Gemini API（Flash シリーズを複数モデルで自動フォールバック） |
| ジャンル採点 | Cloudflare Workers AI（`@cf/cloudflare/clef-flash`） |
| 画像生成 | Stable Diffusion XL（自社ホストの HuggingFace Space / ZeroGPU）→ フォールバック: Pollinations.ai（Flux） |
| 商品データ | 楽天 Web Service API（商品検索・カード生成）、Amazon アソシエイト（検索リンク） |
| CI/CD | GitHub Actions |
| ホスティング | GitHub Pages |
| テスト | pytest（外部 API はモック） |

## データソース

| ソース | 取得方法 | カテゴリ |
|--------|---------|---------|
| Hacker News | Firebase API（認証不要） | tech |
| Zenn / Qiita | RSS フィード | tech |
| PokéCommunity / PokeBeach / ポケモン関連ブログ群 | RSS フィード | pokemon |
| GitHub | Search API（未認証 60req/h） | kemono / pokemon |
| GameSpot / IGN | RSS フィード（description 取得） | kemono |
| Anime News Network | HTML パース（URL whitelist 抽出） | kemono |
| e621 | REST API（認証不要） | キャラクター特徴集計専用（トレンドには結合しない） |
| Reddit | `.json` エンドポイント | 一時的に無効化（403 Blocked） |
| Bluesky | AT Protocol search API | 一時的に無効化（501 Not Implemented） |

## 環境変数

API キーは `.env`（git 管理対象外）または GitHub Repository Secrets で管理し、リポジトリにキーをコミットしないでください。

| 変数 | 用途 | 必須 |
|------|------|------|
| `GEMINI_API_KEY` | Gemini API（記事生成） | ○ |
| `HF_TOKEN` | HuggingFace Space（画像生成）への認証 | ○ |
| `AMAZON_TRACKING_ID` | Amazon アフィリエイトリンクのトラッキング ID | ○ |
| `RAKUTEN_AFFILIATE_ID` | 楽天アフィリエイトリンクの ID | ○ |
| `RAKUTEN_APPLICATION_ID` / `RAKUTEN_ACCESS_KEY` | 楽天 Web Service API（商品検索） | ○ |
| `CLOUDFLARE_ACCOUNT_ID` / `CLOUDFLARE_API_TOKEN` | Cloudflare Workers AI（ジャンル採点） | △（無い場合はランダム選択にフォールバック） |
| `PROMPT_TYPE` | 生成タイプ（`default` / `ai_deep` / `kemono_story`） | 省略可（デフォルト `default`） |
| `IMAGE_PROVIDER` | 画像プロバイダー（`hf` / `pollinations`） | 省略可（デフォルト `hf`） |
| `MAX_INLINE_IMAGES` | インライン画像の最大枚数 | 省略可（デフォルト 7） |
| `CACHE_TTL_HOURS` | トレンドデータの有効時間 | 省略可（デフォルト 24） |
| `MIN_SCORE_THRESHOLD` / `GENRE_FILTER_MIN_SCORE` | ジャンルスコアの下限 | 省略可 |

## プロジェクト構造

```text
my-auto-blog/
├── .github/workflows/        # GitHub Actions
│   ├── deploy.yml            # 毎日自動生成 + ビルド + デプロイ
│   ├── deploy-only.yml       # サイト変更時のビルド + デプロイのみ
│   └── genre-score.yml       # ジャンル採点の手動実行
├── data/
│   ├── topics/               # トレンドデータ（タイムスタンプ付き + latest.json）
│   ├── genre_scores/         # ジャンルスコア結果 + キャッシュ
│   ├── prompt_logs/          # 使用プロンプト（追跡性確保用）
│   ├── drafts/               # 2-pass 下書きメタデータ
│   ├── trend_usage_logs/     # トレンド使用ログ
│   ├── affiliate_logs/       # アフィリエイトリンクログ
│   ├── character_features.json   # e621 タグからのキャラクター特徴集計
│   ├── rakuten_cache.json        # 楽天 API 商品キャッシュ（30日TTL）
│   └── slug-redirects.json       # slug 衝突時のリダイレクト
├── docs/ai/                  # AI Memory Bank（アーキテクチャ・計画・既知の問題など）
├── hf-space/                 # 自社ホスト HuggingFace Space のソース（SDXL パイプライン / blume/kemono-image-api）
├── maintenance/
│   └── archive_memory_bank.py # Memory Bank バッチクリーンアップ（開発ツール・dry-run 既定）
├── public/
│   └── images/               # 生成画像（AVIF）
├── scripts/
│   ├── fetch_topics.py       # トレンドデータ収集（APIキー不要）
│   ├── genre_score.py        # ジャンルスコアリング（Cloudflare Workers AI）
│   ├── generate_article.py   # 記事・画像生成（入口 + パイプライン）
│   ├── article/              # article/ パッケージ（config/gemini/image/affiliate/trends/frontmatter/slug_links/meta/characters/geninfo）
│   ├── generate-search-index.js  # サイト内検索インデックス生成
│   ├── prompts/              # プロンプトテンプレート
│   ├── tests/                # pytest テストスイート
│   └── requirements.txt      # Python 依存関係
├── src/
│   ├── components/           # Astro コンポーネント（Header / Footer 等）
│   ├── content/posts/        # 生成記事（Markdown + frontmatter）
│   ├── layouts/              # レイアウト（Layout / PostLayout）
│   ├── pages/                # ルーティング（記事・タグ・検索・RSS・sitemap 等）
│   ├── lib/                  # 共有ロジック
│   └── styles/               # グローバルスタイル
├── astro.config.mjs          # Astro 設定（site / base / Tailwind）
├── tailwind.config.mjs       # Tailwind 設定
└── package.json
```

## ローカル開発

### 前提

- Node.js >= 22.12.0
- Python 3.10+

### サイト開発

```sh
npm install
npm run dev        # 開発サーバー起動 (localhost:4321)
npm run build      # 本番ビルド（./dist/）
npm run preview    # ビルド結果のプレビュー
```

### 記事生成（ローカル）

`.env` に必要な API キーを設定した後、以下の順で実行します。

```sh
# 1. トレンド収集（APIキー不要）
python scripts/fetch_topics.py

# 2. ジャンルスコアリング（任意・Cloudflare Workers AI が必要）
python scripts/genre_score.py --text "採点対象の文字列" --genres "sf,fantasy,action"

# 3. 記事・画像生成
set PROMPT_TYPE=kemono_story     # 省略時は default
python scripts/generate_article.py

# 4. ビルド検証
npm run build
```

> **注意**: 画像生成の第一候補である HuggingFace Space は停止状態から起動に数分かかるため、起動待ち中のリクエストは失敗します。ローカルでのみ Pollinations.ai を直接使用したい場合は `IMAGE_PROVIDER=pollinations` を設定してください。

## CI/CD ワークフロー

| ワークフロー | トリガー | 内容 |
|-------------|---------|------|
| `deploy.yml` | スケジュール（毎日 JST 8:00）/ 手動 | トレンド収集 → ジャンル採点 → 記事・画像生成 → 自動コミット → ビルド → GitHub Pages デプロイ |
| `deploy-only.yml` | push（`src/**`, `public/**` 等のサイト関連ファイル変更時）/ 手動 | ビルド → GitHub Pages デプロイのみ（記事生成はしない）。`[skip ci]` / `[skip deploy]` 付きコミットはスキップ |
| `genre-score.yml` | 手動（workflow_dispatch） | 任意の文字列に対するジャンル採点を単体実行し、結果を成果物として保存 |

## テスト

```sh
pytest scripts/tests/ -v
```

- テストスクリプトは API キー・クォータ・レート制限がかかる外部 API（Gemini / HuggingFace / e621 等）を `unittest.mock` でモックします
- 例外: RSS フィードは公開エンドポイントで認証・クォータ不要のため、実呼出しを許可
- `fetch_topics.py` の変更後は `python scripts/tests/test_real_apis.py --save` で各データソースの応答を実際に確認できます（結果は `scripts/data/api_test_results/` に保存）

## 注意事項

- 生成画像はプロンプトに SFW タグを固定付与することで安全な出力を強制しています
- e621 のデータはキャラクター特徴の集計（種族・身体的特徴などのタグ統計）にのみ使用し、トレンドトピックには結合していません
- GitHub Search API は未認証で 60req/h のレート制限があるため、収集頻度は 1 日 1 回に抑えています
- 記事末尾の「生成情報」セクションには、記事生成に使用したトレンドソースとキャラクターデータを掲載しています
