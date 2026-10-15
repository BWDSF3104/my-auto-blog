# my-auto-blog

Automated blog generation system powered by Astro, Gemini AI, and trend data collection.
Static site generator blog. No authentication, no database, no SSR. Deployed to GitHub Pages (`BWDSF3104.github.io/my-auto-blog`).

## Language

- ユーザーへの回答、進捗報告、説明、質問、作業結果、最終結果は日本語で行う。
- コード、コマンド、ファイルパス、API名、ライブラリ名などの正確な技術表記は原文を維持する。
- ユーザー向け回答を日本語にすることを理由として、プロジェクト内のファイル・データ・スクリプトの入力・出力を翻訳・変更してはならない。
- `docs/ai/` Memory Bank の新規エントリは日本語で記述。既存の英語エントリはそのまま維持。
- Git commit message: prefix は英語 (`feat:`, `fix:` など)、説明部分は日本語。

## Terminal Safety

- NEVER execute destructive terminal commands without explicit user confirmation.
- Forbidden: `rm -rf`, `git push --force`, `sudo`, modifying files outside workspace root.
- **File deletion**: Use `./kilo-safe-remove.cmd <file>` (not `Remove-Item` / `del`).
- **Folder deletion**: Use `./kilo-safe-rmdir.cmd <folder>` (not `Remove-Item -Recurse` / `rmdir /s`).
- **NEVER** use PowerShell `Get-Content` / `Set-Content` pipeline for file content manipulation. It corrupts UTF-8 encoding (adds BOM, garbles Japanese text).
- **editツール以外でファイルを改写する場合**: 必ず事前に `git diff` でリモートとの差異がないことを確認し、改写後はファイルが破損していないことを確認すること。

## Command Execution Rules

- **One line per command**: Run shell commands on a single line. Do not split a command across multiple lines (kilo parses multi-line input line by line and records one approval pattern per line, polluting the allow list). If multiple statements are needed, join them on one line with `;`.
- **No inline Python**: Do not pass Python code directly on the command line (`python -c "..."`, `python -`, or piping code into `python`) — inline `python -c` mostly fails under PowerShell 5.1 due to quoting/encoding. Instead:
  1. Write the script to the scratch folder `docs\ai\tmp\` (e.g. `docs\ai\tmp\fetch_check.py`).
  2. Execute it with `python <file>`.
  3. Keep any output files in the same scratch folder.
  - Do not place throwaway scripts in production code directories (e.g. `scripts/`). `docs/ai/tmp/` is gitignored; entries not updated for 7+ days (mtime) are cleared by the batch at task start (`maintenance/archive_memory_bank.py`, retention configurable via `--tmp-retention-days`).
- **Enforcement**: Global config `~/.config/kilo/kilo.jsonc` → `permission.bash` gates destructive commands (`Remove-Item *` / `rm *` / `del *` / `rd *` / `rmdir *` / `pip uninstall *` / `npm uninstall *` / `git push --force *` / `git reset --hard *` / `git clean *` / `gh repo delete *`) to `ask`; `python -c *` / `python - *` / `node -e *` / `Set-Content *` / `Out-File *` / `New-Item *` are `allow`. Unknown commands default to `ask`.

## Code Verification

- **Python変更後**: `pytest scripts/tests/ -v` で全テスト通過を確認。`maintenance/`（開発ツール）を変更した場合は加えて `pytest maintenance/tests/ -v` も実行する。
- **Astro変更後・記事生成後**: `npm run build` でビルド成功を確認。
- **レイアウト変更後**: ビルド後、出力HTMLを解析して構造を検証（クラス名、要素階層、コンテンツ順序）。修正完了時にユーザーにスクリーンショットを送信。
- **git commit 前**: 変更内容に応じて再実行（Python→pytest, Astro→build、両方→両方）。
- 成功時は `docs/ai/tasks/` の該当タスクファイルの Verification セクションにコマンド・結果・経過時間を記録。
- **例外**: `docs/ai/`、`AGENTS.md`、`.kilo/` のみの変更は pytest / build 不要。
- **fetch_topics.py 更新後**: `python scripts/tests/test_real_apis.py --save` で各データソースの応答を確認（結果は `scripts/data/api_test_results/` に保存）。

### Test Script Rules

- テストスクリプトは外部APIを実際に呼び出してはならない。API キー・クォータ・レート制限がかかるサービス（Gemini AI, HuggingFace, Kemono API, e621 など）は `unittest.mock` でモックする。
- **例外**: RSS フィードは公開エンドポイントで認証・クォータ不要のため実呼出しを許可。
- レート制限の詳細: `docs/ai/api-rate-limits.md`

## Development

- Dev server: `astro dev --background`
- Background server: `astro dev stop`, `astro dev status`, `astro dev logs`

## Image Analysis

- 画像の視覚解析（スクリーンショットの文字/UI 読み取り、レイアウト検証、生成画像の確認）は MCP ツール `analyze_image_with_groq` を使用。
- 使い方・焦点化分析の例・メンテナンス手順は `docs/ai/image-analysis.md` を参照。
- 画像はクラウド（Groq API）へ送信されるため、送信前にユーザーの確認を取る。

## Code Standards

- Python scripts: UTF-8 encoding
- Trend data: `data/topics/latest.json`
- Generated articles: `src/content/posts/`
- Generated images: `public/images/`

## Documentation

- Astro docs: https://docs.astro.build
- Consult guides before: routing, components, framework integration, content collections, styling, i18n

## AI Memory Bank

`docs/ai/memory-bank-guide.md` を以下のタイミングで参照すること:

- **タスク開始時**
- **意味のあるステップ完了後**
- **タスク完了時（git commit 前）**
- **中断からの再開時**

## Workflows

`docs/ai/workflows.md` を以下のタイミングで参照すること:

- **ファイル変更の完了後、コミット前に**
- **git commit 実行前**
- **git commit 実行後（pushを実行するため）**
- **git push 完了後**
- **ユーザーが手動記事作成を依頼した際: `docs/ai/manual-article-workflow.md`**
- **デバッグが必要な際（Python スクリプトのバグ調査・変数確認・ステップ実行）: `docs/ai/debugging.md`**

## Project Structure

```
my-auto-blog/
├── scripts/               # Python automation scripts
│   ├── fetch_topics.py    # Trend data collection
│   ├── generate_article.py # Article generation (entry + pipeline)
│   ├── article/            # article/ package (config/gemini/image/affiliate/trends/frontmatter/slug_links/meta/characters/geninfo)
│   └── prompts/           # Prompt templates
├── maintenance/           # Development tools (outside the production pipeline)
│   └── archive_memory_bank.py # Memory Bank batch cleanup (dry-run is the default)
├── src/                   # Astro source
│   └── content/posts/     # Generated markdown posts
├── public/                # Static assets
│   └── images/            # Generated images
├── data/                  # Collected data
│   └── topics/            # Trend topics (timestamped + latest.json)
└── docs/ai/               # AI Memory Bank (changing knowledge)
```
