# Backlog

未実装項目と改善案。優先度でソート。完了した項目は削除し、不採用項目は `backlog-archive.md` へ移す（変更履歴は git commit に委ねる）。

## P2

| # | 項目 | 難易度 | 効果 | 備考 |
|---|------|--------|------|------|
| 2 | Featured/Pinned 記事 | ⭐⭐ | 中 | 保留（重要記事未準備） |
| 4 | コメント機能（Giscus）実装 | ⭐⭐ | 中 | 設計確定済み（2026-10-11、選定理由: `decisions/2026-10-11-giscus-comments.md`）。タスクファイル: `tasks/2026-10-11-giscus-comments-github-setup.md`（手動: Discussions 有効化 + giscus app 導入）、`tasks/2026-10-11-giscus-comments-env-config.md`（手動: 環境変数登録）、`tasks/2026-10-11-giscus-comments-component.md`（AI: コンポーネント + Layout 組み込み）、`tasks/2026-10-11-giscus-comments-workflow-env.md`（AI: deploy.yml / deploy-only.yml への env 配線）、`tasks/2026-10-11-giscus-comments-verification.md`（AI: E2E 検証 + 本番デプロイ）。完了時に本エントリを削除 |

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
| 9 | e621 参考キャラクター名のストーリー本文への「寄せる」指示検討 | ⭐ | 低 | 2026-10-13 調査: e621 キャラ名は本文に未使用（38 件中 0 件。参考データ・生成情報・アフィリエイトのみ）。名前での寄せは版権 IP リスク（Zootopia/Pokemon 等）のため現状はデザイン面のみで寄せる設計。直近改修（anthro/physical フィルタ）で改善の可能性 → 様子見・低優先度 |
| 10 | ストーリーのランダム種族を Danbooru/e621 主要種族タグに絞る（主要種族タグリスト化） | ⭐⭐ | 低 | 2026-10-13 調査: 種族は Gemini 自由選択（直近21記事で21種、alligator/raven 等の exotic 混在）。画像モデル（Nova-Furry-XL）は主要種族ほど安定。タスク: Danbooru/e621 主要種族タグをリスト化し、プロンプト推奨リスト or Python 側ランダム注入を検討 |
| 11 | Python 3.15.0 へ `python` の切替（PEP 686 UTF-8 既定有効化） | ⭐ | 中 | 2026-10-14 導入済み（per-user `Python315\`、`py -3.15` 利用可・待機）。`python` は 3.10.8 のまま。ブロック: `pillow-avif-plugin` の cp315 wheel が PyPI に不存在（全バージョン確認済み）。cp315 wheel 公開後: `python` を 3.15 に再切替 → `py -3.15 -m pip install pillow-avif-plugin` → `pytest scripts/tests -v` 全テスト確認 → PEP 686 有効化確認（`PYTHONUTF8=1` 回避策の簡素化）。詳細: `tasks/2026-10-14-python315-upgrade.md` |
| 12 | `docs/ai/tmp/` スクラッチの日付管理（タスク別日付サブフォルダ + N日保持） | ⭐ | 低 | 現在 `archive_memory_bank.py` は tmp/ を全削除（タスク開始時）。日付管理を実装する場合は `archive_memory_bank.py` を「N日経過した日付フォルダを削除」に改修し、**同時に AGENTS.md のルールの文言も「全削除」→ 該当動作に合わせる**（docs と挙動の一致必須）。実装時のみ本エントリを有効化 |

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
