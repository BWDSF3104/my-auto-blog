# my-auto-blog

Astro、Gemini AI、トレンドデータ収集で動作する自動ブログ生成システム。
静的サイトジェネレーターによるブログ。認証なし、データベースなし、SSR なし。GitHub Pages（`BWDSF3104.github.io/my-auto-blog`）へデプロイ。

## 言語

- ユーザーへの回答、進捗報告、説明、質問、作業結果、最終結果は日本語で行う。
- コード、コマンド、ファイルパス、API名、ライブラリ名などの正確な技術表記は原文を維持する。
- ユーザー向け回答を日本語にすることを理由として、プロジェクト内のファイル・データ・スクリプトの入力・出力を翻訳・変更してはならない。
- `docs/ai/` Memory Bank の新規エントリは日本語で記述。
- Git commit message: prefix は英語 (`feat:`, `fix:` など)、説明部分は日本語。

## ターミナル安全

- 明示的なユーザー確認なしに、破壊的なターミナルコマンドを実行してはならない。
- 禁止: `rm -rf`、`git push --force`、`sudo`、ワークスペースルート外のファイル変更。
- **ファイル削除**: `./kilo-safe-remove.cmd <file>` を使う（`Remove-Item` / `del` は不可）。
- **フォルダ削除**: `./kilo-safe-rmdir.cmd <folder>` を使う（`Remove-Item -Recurse` / `rmdir /s` は不可）。
- **決して** PowerShell の `Get-Content` / `Set-Content` パイプラインでファイル内容を操作しないこと。UTF-8 エンコーディングを破損させる（BOM 付与、日本語文字化け）。
- **editツール以外でファイルを改写する場合**: 必ず事前に `git diff` でリモートとの差異がないことを確認し、改写後はファイルが破損していないことを確認すること。

## コマンド実行ルール

- **1 コマンド 1 行**: シェルコマンドは 1 行で実行する。コマンドを複数行に分割しないこと（kilo は複数行入力を行ごとに解析し、行ごとに 1 つの承認パターンを記録するため、allow リストを汚染する）。複数の文が必要な場合は `;` で 1 行に結合する。
- **インライン Python 禁止**: コマンドラインに Python コードを直接渡さないこと（`python -c "..."`、`python -`、コードを `python` にパイプする等）— インライン `python -c` は PowerShell 5.1 でクォーティング・エンコーディングの問題によりほとんど失敗する。代わりに:
  1. スクリプトをスクラッチフォルダ `docs\ai\tmp\` に書き出す（例: `docs\ai\tmp\fetch_check.py`）。
  2. `python <file>` で実行する。
  3. 出力ファイルも同じスクラッチフォルダに保持する。
  - 使い捨てスクリプトを本番コードディレクトリ（例: `scripts/`）に置かないこと。`docs/ai/tmp/` は gitignore 対象で、7 日以上更新のないエントリ（mtime）はタスク開始時のバッチ（`maintenance/archive_memory_bank.py`、`--tmp-retention-days` で保持期間を設定可能）で削除される。
- **強制**: グローバル設定 `~/.config/kilo/kilo.jsonc` → `permission.bash` が破壊的コマンド（`Remove-Item *` / `rm *` / `del *` / `rd *` / `rmdir *` / `pip uninstall *` / `npm uninstall *` / `git push --force *` / `git reset --hard *` / `git clean *` / `gh repo delete *`）を `ask` に制御する。`python -c *` / `python - *` / `node -e *` / `Set-Content *` / `Out-File *` / `New-Item *` は `allow`。不明なコマンドはデフォルトで `ask`。

## コード検証

- **Python変更後**: `pytest scripts/tests/ -v` で全テスト通過を確認。`maintenance/`（開発ツール）を変更した場合は加えて `pytest maintenance/tests/ -v` も実行する。
- **Astro変更後・記事生成後**: `npm run build` でビルド成功を確認。
- **レイアウト変更後**: ビルド後、出力HTMLを解析して構造を検証（クラス名、要素階層、コンテンツ順序）。修正完了時にユーザーにスクリーンショットを送信。
- **git commit 前**: 変更内容に応じて再実行（Python→pytest, Astro→build、両方→両方）。
- 成功時は `docs/ai/tasks/` の該当タスクファイルの Verification セクションにコマンド・結果・経過時間を記録。
- **例外**: `docs/ai/`、`AGENTS.md`、`.kilo/` のみの変更は pytest / build 不要。
- **fetch_topics.py 更新後**: `python scripts/tests/test_real_apis.py --save` で各データソースの応答を確認（結果は `scripts/data/api_test_results/` に保存）。

### テストスクリプトルール

- テストスクリプトは外部APIを実際に呼び出してはならない。API キー・クォータ・レート制限がかかるサービス（Gemini AI, HuggingFace, Kemono API, e621 など）は `unittest.mock` でモックする。
- **例外**: RSS フィードは公開エンドポイントで認証・クォータ不要のため実呼出しを許可。
- レート制限の詳細: `docs/ai/api-rate-limits.md`

## 開発

- Dev サーバー: `astro dev --background`
- バックグラウンドサーバー: `astro dev stop`、`astro dev status`、`astro dev logs`

## 画像解析

- 画像の視覚解析（スクリーンショットの文字/UI 読み取り、レイアウト検証、生成画像の確認）は MCP ツール `analyze_image_with_groq` を使用。
- 使い方・焦点化分析の例・メンテナンス手順は `docs/ai/image-analysis.md` を参照。
- 画像はクラウド（Groq API）へ送信されるため、送信前にユーザーの確認を取る。

## コード規約

- Python スクリプト: UTF-8 エンコーディング
- トレンドデータ: `data/topics/latest.json`
- 生成記事: `src/content/posts/`
- 生成画像: `public/images/`

## ドキュメント

- Astro ドキュメント: https://docs.astro.build
- 変更前にガイドを確認すること: routing、components、framework integration、content collections、styling、i18n

## AI Memory Bank

`docs/ai/memory-bank-guide.md` を以下のタイミングで参照すること:

- **タスク開始時**
- **意味のあるステップ完了後**
- **タスク完了時（git commit 前）**
- **中断からの再開時**

### タスク開始時（初回コード変更の前）

初回コード変更の前に以下の 2 ステップを実行すること:

1. `docs/ai/tasks/YYYY-MM-DD-short-name.md` にタスクファイルを作成する（意図・背景を含む）
2. `docs/ai/current-task.tsv` に参照行を追加する

2 ステップ完了前に実装着手しないこと。

## ワークフロー

- git commit / push / deploy: `docs/ai/workflows.md` を参照する。
- ユーザーが手動記事作成を依頼した際: `docs/ai/manual-article-workflow.md` を参照する。
- デバッグが必要な際（Python スクリプトのバグ調査・変数確認・ステップ実行）: `docs/ai/debugging.md` を参照する。

## プロジェクト構成

```
my-auto-blog/
├── scripts/                   # Python 自動化スクリプト
│   ├── fetch_topics.py        # トレンドデータ収集
│   ├── generate_article.py    # 記事生成（エントリ + パイプライン）
│   ├── article/               # article/ パッケージ（config/gemini/image/affiliate/trends/frontmatter/slug_links/meta/characters/geninfo）
│   └── prompts/               # プロンプトテンプレート
├── maintenance/               # 開発ツール（本番パイプライン外）
│   └── archive_memory_bank.py # Memory Bank バッチクリーンアップ（デフォルトは dry-run）
├── src/                       # Astro ソース
│   └── content/posts/         # 生成された Markdown 記事
├── public/                    # 静的アセット
│   └── images/                # 生成画像
├── data/                      # 収集データ
│   └── topics/                # トレンドトピック（タイムスタンプ付き + latest.json）
└── docs/ai/                   # AI Memory Bank（変化する知識）
```
