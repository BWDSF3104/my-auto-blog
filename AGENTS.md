# my-auto-blog

Astro、Gemini AI、トレンドデータ収集で動作する自動ブログ生成システム。
静的サイトジェネレーター。認証なし、データベースなし、SSR なし。
デプロイ先: GitHub Pages（`BWDSF3104.github.io/my-auto-blog`）。

## 共通規約

言語・実装開始ゲート・ターミナル安全・コマンド実行ルール・正典ツール（`bin/`）・Memory Bank 運用・commit message 規約は global 正典 `AGENTS.md`（`C:\Users\fujim\.config\kilo\AGENTS.md`）を参照。このファイルにはプロジェクト固有項目のみ記載する（共通項目をここに書かない）。

## コード検証（本プロジェクト）

- **Python変更後**: `pytest scripts/tests/ -v`。`maintenance/`（開発ツール）変更時は加えて `pytest maintenance/tests/ -v`。正典ツール（task_manager / archive_memory_bank）のテストは Kilo_Commons `tests/`。
- **Astro変更後・記事生成後**: `npm run build` でビルド成功を確認。
- **`scripts/prompts/` のみ変更**: 検証不要。
- **レイアウト変更後**: ビルド後、出力HTMLを解析して構造を検証（クラス名、要素階層、コンテンツ順序）。修正完了時に `I:\マイドライブ\kilo` 下のスクリーンショットを送付（サブフォルダで日付・タスク名を区切可）。
- **fetch_topics.py 更新後**: `python scripts/tests/test_real_apis.py --save`（結果は `scripts/data/api_test_results/` に保存）。

## 開発

- Dev サーバー: `astro dev --background`
- バックグラウンドサーバー: `astro dev stop`、`astro dev status`、`astro dev logs`

## ドキュメント

- Astro ドキュメント: https://docs.astro.build
- 変更前にガイドを確認すること: routing、components、framework integration、content collections、styling、i18n
- 参照: `docs/ai/memory-bank-guide.md`、`workflows.md`、`debugging.md`、`image-analysis.md`、`api-rate-limits.md`、`manual-article-workflow.md`、`maintenance-batches.md`、`log-locations.md`

## Git

- commit・push・deploy 手順: `docs/ai/workflows.md`（CI は GitHub Actions: `deploy.yml` / `deploy-only.yml` / `gsc-verify.yml`）

## プロジェクト構成

```
my-auto-blog/
├── scripts/                   # Python 自動化スクリプト
│   ├── fetch_topics.py        # トレンドデータ収集
│   ├── generate_article.py    # 記事生成（エントリ + パイプライン）
│   ├── article/               # article/ パッケージ（config/gemini/image/affiliate/trends/frontmatter/slug_links/meta/characters/geninfo）
│   └── prompts/               # プロンプトテンプレート
├── hf-space/                  # 自社 HuggingFace Space のデプロイ元ソース（blume/kemono-image-api / SDXL パイプライン）
├── maintenance/               # 開発ツール（正典ツールは Kilo_Commons bin/。本プロジェクトは vscode_graceful_restart.py 等のみ）
├── src/                       # Astro ソース
│   └── content/posts/         # 生成された Markdown 記事
├── public/                    # 静的アセット（public/images/ = 生成画像）
├── data/                      # 収集データ（data/topics/ = タイムスタンプ付き + latest.json）
└── docs/ai/                   # AI Memory Bank（1エントリ1ファイル）
```
