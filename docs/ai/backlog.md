# Backlog

未実装項目と改善案。優先度でソート。完了した項目は削除する（変更履歴は git commit に委ねる）。

(完了済み項目は削除済み)

## P1 (完了)

| # | 項目 | 完了日 | 備考 |
|---|------|--------|------|
| 2 | HF Space デプロイ確認 | 2026-10-10 | 実質完了と確認 |
| 1 | art_style 短縮 | 2026-10-06 | DEFAULT_ART_STYLEを5→3トークン、テンプレート指示に3-5タグ明記 |
| 2 | キャラ定義のトークン最適化 | 2026-10-06 | 服装1-2つ制限、5-8タグ推奨、自然言語除去指示 |
| 3 | フル解像度テスト | 2026-10-06 | 不要と判断 |
| 1 | HuggingFace API 使用可能状況の確認 | 2026-10-05 | ZeroGPU 無料枠 3.5 分/日、1 日約 2 リクエスト。詳細は api-rate-limits.md |

## P2

| # | 項目 | 難易度 | 効果 | 備考 |
|---|------|--------|------|------|
| 2 | Featured/Pinned 記事 | ⭐⭐ | 中 | 保留（重要記事未準備） |
| 3 | アフィリエイトCTAカードのスリム化 + テキストリンクの統一・被り排除 | ⭐ | 中 | 現状CTAカード（`generate_article.py:1530-1533`「🔥 …の今すぐチェックできるおすすめアイテム / Amazonで確認する →」）とテキストリンク（`links_html`「Amazonで「kw」を探す」）で同一キーワードが重複表示される。カードの見た目をもっとスリムにし、テーマ関連商品のテキストリンクを全てこのカード形式に統一、キーワードの被りを排除 |

## P2 (完了)

| # | 項目 | 完了日 | 備考 |
|---|------|--------|------|
| 4 | 旧記事の UTF-8 BOM 除去（30 件 + `affiliate-link-context.txt`） | 2026-10-11 | BOM 付き 31 ファイルをバイト列除去（CRLF 維持）。`safe-remove.ps1` の BOM は PS 5.1 必須で維持。`npm run build` 135 pages 成功。詳細: `tasks/2026-10-11-utf8-encoding-audit.md` |
| 1 | trend topics の実質的無効化（#5 と統合実施） | 2026-10-10 | GameSpot/IGN を正規 RSS パースへ（description 取得化）、全エンタメソース失敗時の `STORY_INSPIRATION_THEMES` NameError を内蔵テーマ8件で修正。詳細: `tasks/2026-10-10-trend-rss-enhancement.md` |
| 5 | RSS取得の強化（description 追加） | 2026-10-10 | `fetch_rss()` が RSS2.0（content:encoded→description）/Atom（content→summary）から HTML除去・300文字切り詰めで抽出し `latest.json` に保存。`score_topics()` は title+description[:200] でスコアリング、`_append_trending_topics()` は description[:100] スニペット注入。pytest 339件通過。詳細: `tasks/2026-10-10-trend-rss-enhancement.md` |
| 1 | ログ・メタファイルのクリーン処理（リネーム+期間削除） | 2026-10-10 | リネーム `affiliate_links`→`affiliate_logs`・`trend_usage`→`trend_usage_logs`（機能コード1行+`git mv`+`.gitkeep`）。`generate_article.py` に `_cleanup_old_logs()`（ファイル名タイムスタンプで30日前の `drafts/`・`trend_usage_logs/`・`affiliate_logs/`・`prompt_logs/` を削除、`generate_post()` 末尾で呼出）。`deploy.yml` 参照+コミットメッセージ更新。全モックテスト8件、pytest 305件通過。詳細: `tasks/2026-10-10-log-cleanup.md` |

## P3

| # | 項目 | 難易度 | 効果 | 備考 |
|---|------|--------|------|------|
| 8 | 改行コードの `.gitattributes` による正規化（別タスク化 2026-10-11） | ⭐ | 低 | CRLF/LF 混在（例: `deploy.yml` CRLF+LF, `test_fetch_topics.py` CRLF+LF, `PostLayout.astro` CRLF+LF）。エンコード監査（`tasks/2026-10-11-utf8-encoding-audit.md`）で発覚。`* text=auto eol=lf` 等の導入は全ファイルに改行変更diffを生むため単独タスクで実施 |
| 1 | ジャンル候補を LLM で自動生成 → Clef-flash でスコアリング（2段構成） | ⭐⭐ | 中 | 固定リストでは未知ジャンルを発見できない問題を解消。`@cf/meta/llama-3.1-8b-instruct`（JSON schema 出力）で候補生成→Clef-flash で採点。`genre_score.py` に `--auto-genre` フラグ追加。API 2回/作品 |
| 2 | PWA 対応 | ⭐⭐⭐ | 中 | Service Worker + manifest.json |
| 3 | Service Worker | ⭐⭐⭐ | 中 | オフライン対応、キャッシュ戦略 |
| 4 | ソーシャルメディア自動投稿 | ⭐⭐⭐ | 中 | X/Twitter API, Bluesky API 連携 |
| 5 | ページ間トランジション | ⭐⭐ | 低 | 実験的API。ブラウザサポート確認必要 |
| 6 | Crunchyroll ニュース再収集 | ⭐⭐ | 低 | 静的HTMLは記事0件（JS描画）・RSS 404のため2026-10-10に一時無効化。代替RSSフィードの探索 or JS描画手段の検討。詳細: `tasks/2026-10-10-trend-source-quality-fixes.md` |
| 7 | トレンドデータ `by_category`/`all` の merge 構造ドリフト修正 | ⭐⭐ | 低 | e621 5 件は 2026-10-10 のトレンド分離（`NON_TREND_SOURCES` ガード + データ一次性除去）で解消済み。GitHub 2 件と一般構造ドリフト（カテゴリ単位継承 vs source 単位継承の再設計）は残存。詳細: `known-issues.md` |

## P4 (超低優先度)

| # | 項目 | 難易度 | 効果 | 備考 |
|---|------|--------|------|------|
| 1 | Flux.1 向け自然言語プロンプト + モデル別切り替え | ⭐⭐ | 低 | PollinationsはHFフォールバック。詳細は image-prompt-refinement.md |

## P5 (実験的・追加検討)

| # | 項目 | 難易度 | 効果 | 備考 |
|---|------|--------|------|------|
| 1 | TL;DR セクション | ⭐ | 高 | 記事テンプレートに追加するのみ |
| 2 | Callout Boxes (Note/Tip/Warning) | ⭐⭐ | 中 | MDXカスタムコンポーネントで実装 |
| 3 | Reading Mode Toggle | ⭐⭐ | 中 | 没入型読書モード |
| 4 | Series 機能 | ⭐⭐ | 中 | ストーリー記事に有効 |
| 5 | Chapter Navigation | ⭐⭐ | 中 | 前後章のナビゲーション |
| 6 | Spoiler Warnings | ⭐ | 低 | ストーリー記事に有効 |
| 7 | AI生成の明示 | ⭐ | 高 | 透明性向上。SEOにも影響 |
| 8 | 情報源の明示 | ⭐ | 中 | 信頼性向上 |
| 9 | MDX Support | ⭐⭐ | 高 | インタラクティブコンポーネントを記事に埋め込み可能 |
| 10 | Multiple Collections | ⭐⭐ | 中 | posts, authors, series, faq を分離 |
| 11 | Image Optimization | ⭐ | 中 | 組み込みの image() ヘルパー |
| 12 | Zod Schema Validation | ⭐ | 中 | フロントマターの型安全 |
| 13 | コメントシステム (Giscus) | ⭐ | 中 | 技術的に可能。自動生成ブログの特性上不適合だが低優先度で実装検討 |
| 14 | Reddit API の収集機能 | ⭐⭐ | 低 | `collect_reddit()` 実装済みだが403規制中。優先度最低 |

## 不採用（見送り）

| # | 項目 | 理由 |
|---|------|------|
| 1 | 記事アーカイブページ | 既存のページネーション+タグフィルタで実用性十分 |
| 2 | Related Posts の改善 | タグベースは実装済み。改善コスト/効果比低い |
| 3 | 多言語対応 | 自動翻訳パイプライン必要。APIクォータ消費大 |
| 4 | 自動翻訳パイプライン | APIコスト、品質管理が課題 |
| 5 | A/B テスト | 静的サイトではリアルタイムテスト困難 |
| 6 | サウンドフィードバック | ブログとして不自然。アクセシビリティ悪影響 |
| 7 | カスタムカーソル | アクセシビリティ悪影響 |
| 8 | Scroll-jacking | UXを損なう可能性 |
| 9 | Particle エフェクト | パフォーマンス悪影響 |
| 10 | 読者貢献システム | バックエンド必要。静的サイトの前提と矛盾 |
| 11 | AI Chat Assistant | 維持コスト高。効果不明 |
| 12 | 音声コマンドナビ | 利用者が少ない |
| 13 | Background Music | 迷惑になる可能性 |
| 14 | カスタムフォント | Noto Sans JP 等の読み込みでLCP遅延。パフォーマンス影響中 |
| 15 | IMAGE_PROVIDER=pollinations デフォルト化 | 廃止。HF Space がメイン画像生成手段 |
