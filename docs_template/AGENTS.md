# [プロジェクト名]

[プロジェクトの1文説明]

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

## Code Verification

- **[言語]変更後**: `[テストコマンド]` で全テスト通過を確認。
- **[フレームワーク]変更後**: `[ビルドコマンド]` でビルド成功を確認。
- **git commit 前**: 変更内容に応じて再実行（テスト→テストコマンド, ビルド→ビルドコマンド、両方→両方）。
- 成功時に `docs/ai/current-task.md` の Verification セクションにコマンド・結果・経過時間を記録。
- **例外**: `docs/ai/`、`AGENTS.md`、`.kilo/` のみの変更はテスト/ビルド不要。

### Test Script Rules

- テストスクリプトは外部APIを実際に呼び出してはならない。API キー・クォータ・レート制限がかかるサービスはモックする。
- 公開エンドポイントで認証・クータ不要のデータソースは実呼出しを許可。
- レート制限の詳細: `docs/ai/api-rate-limits.md`

## Development

- Dev server: `[devコマンド]`
- Build: `[buildコマンド]`

## Code Standards

- [言語] scripts: UTF-8 encoding
- [データ出力パス]
- [生成ファイル出力パス]

## Documentation

- [フレームワーク] docs: [ドキュメントURL]
- Consult guides before: routing, components, framework integration, content collections, styling, i18n

## AI Memory Bank

Memory Bank のファイル構成、更新タイミング、アーカイブルール、Long-running Agent Tasks、Recovery After Interruption は `docs/ai/memory-bank-guide.md` を参照。

## Workflows

Git Workflow、Commit Checklist、Deploy Verification は `docs/ai/workflows.md` を参照。

## Project Structure

```
[プロジェクト名]/
├── [ソースコードディレクトリ]
├── [テストディレクトリ]
├── [データ出力ディレクトリ]
├── [静的アセットディレクトリ]
└── docs/ai/               # AI Memory Bank (changing knowledge)
```
