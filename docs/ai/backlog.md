# Backlog

未実装項目と改善案。優先度でソート。完了した項目は削除する（変更履歴は git commit に委ねる）。

## P2

| # | 項目 | 難易度 | 効果 | 備考 |
|---|------|--------|------|------|
| 2 | Featured/Pinned 記事 | ⭐⭐ | 中 | 保留（重要記事未準備） |
| 3 | アフィリエイトCTAカードのスリム化 + テキストリンクの統一・被り排除 | ⭐ | 中 | 現状CTAカード（`generate_article.py:1530-1533`「🔥 …の今すぐチェックできるおすすめアイテム / Amazonで確認する →」）とテキストリンク（`links_html`「Amazonで「kw」を探す」）で同一キーワードが重複表示される。カードの見た目をもっとスリムにし、テーマ関連商品のテキストリンクを全てこのカード形式に統一、キーワードの被りを排除 |
| 4 | コメント機能（Giscus）実装 | ⭐⭐ | 中 | 設計確定済み（2026-10-11、選定理由: `decisions.md`）。タスクファイル: `tasks/2026-10-11-giscus-comments-github-setup.md`（手動: Discussions 有効化 + giscus app 導入）、`tasks/2026-10-11-giscus-comments-env-config.md`（手動: 環境変数登録）、`tasks/2026-10-11-giscus-comments-component.md`（AI: コンポーネント + Layout 組み込み）、`tasks/2026-10-11-giscus-comments-workflow-env.md`（AI: deploy.yml / deploy-only.yml への env 配線）、`tasks/2026-10-11-giscus-comments-verification.md`（AI: E2E 検証 + 本番デプロイ）。完了時に本エントリを削除 |

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
| 9 | e621 参考キャラクター名のストーリー本文への「寄せる」指示検討 | ⭐ | 低 | 2026-10-13 調査: e621 キャラ名は本文に未使用（38 件中 0 件。参考データ・生成情報・アフィリエイトのみ）。名前での寄せは版権 IP リスク（Zootopia/Pokemon 等）のため現状はデザイン面のみで寄せる設計。直近改修（anthro/physical フィルタ）で改善の可能性 → 様子見・低優先度 |
| 10 | ストーリーのランダム種族を Danbooru/e621 主要種族タグに絞る（主要種族タグリスト化） | ⭐⭐ | 低 | 2026-10-13 調査: 種族は Gemini 自由選択（直近21記事で21種、alligator/raven 等の exotic 混在）。画像モデル（Nova-Furry-XL）は主要種族ほど安定。タスク: Danbooru/e621 主要種族タグをリスト化し、プロンプト推奨リスト or Python 側ランダム注入を検討。**採用見送り（不採用見込み）・低優先度** |

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
