---
description: コミット実行（fetch→remote同期→チェック→add→commit→push→デプロイ検証。commit と push は分割しない）
---

次のメッセージで commit → push を実行する（`docs/ai/workflows.md` に従う）:

$ARGUMENTS

## 引数
- コミットメッセージ（必須）。`type: 説明`（Conventional Commit）。
  type がない場合、変更ファイルから一意に特定できる場合のみ自動導出（例: 全て `docs/**` のみ → `docs:`）。
  特定できない場合はユーザーに 1 回だけ type を確認する（`feat`/`fix` 等）。
- 末尾に `[skip ci]` / `[skip deploy]` を含めるとデプロイ検証を除外。
- `--dry-run`: 実行せず、変更差分・実行予定のチェック・commit 内容を表示のみ。

## 手順
1. 変更を確認
   - `git status --short` / `git diff --name-only`
   - 変更が 0 の場合は commit せず、その旨を報告して終了。
2. コミット前チェック（変更ファイルに応じて実行）
   - Python 変更: `pytest scripts/tests/ -v`（`maintenance/` 変更時は +`pytest maintenance/tests/ -v`）
   - Astro/JS 変更（`src/**` `public/**` `package.json` `astro.config.mjs` `tailwind.config.mjs`）: `npm run build`
   - 失敗時は commit せず、失敗内容を報告してユーザーへ確認。
3. remote 同期
   - `git fetch origin`
   - `git rev-list HEAD..origin/main --count`
   - カウント > 0 の場合: `git stash` → `git pull` → `git stash pop` → 競合があればエージェントが解決し、解決後に再実行。
4. commit → push（分割禁止・連続実行）
   - 意図したファイルのみ `git add`（秘密情報は絶対コミットしない）
   - `git commit -m "<メッセージ>"`
   - 直ちに `git push`
5. デプロイ検証（push 後・除外条件以外のみ）
   - `gh run list --workflow=deploy-only.yml --limit 5`
   - 最新の push トリガー実行が `success` か確認。失敗時は原因を調査。
   - 除外: 変更ファイルが paths に一致しない / メッセージに `[skip ci]`・`[skip deploy]` がある。

## 禁止
- `git push --force`、remote 履歴の変更、force push
- チェック失敗・競合未解決時の commit
- 秘密情報・キーのコミット
- 手動で `gh workflow run`（push 自動トリガーに依存）
