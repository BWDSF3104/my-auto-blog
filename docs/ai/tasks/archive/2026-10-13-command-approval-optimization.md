# 2026-10-13: コマンド承認方式の最適化（permission.bash 再構築 + 2ルール追加）

**Status**: 完了（2026-10-13 コミット `c683247`・push 済み）

## 概要

ユーザー要望: kilo code のコマンド承認方式を最適化し、2つの行動ルール（一行コマンド / インライン Python 禁止→一時フォルダ書き出し実行）を適切な設定ファイルへ反映する。承認方式は kilo が読み込む設定ファイル（`permission.bash`）側、行動ルールは AGENTS.md 側へ分離して反映。

追加指示 (2026-10-13): 以下の 6 パターンを `ask`→`allow` に変更（「以下も許可で良い」）: `python -c *` / `python - *` / `node -e *` / `Set-Content *` / `Out-File *` / `New-Item *`。`powershell *` / `pwsh *` は対象外（`ask` 維持）。

## 変更内容

- `C:\Users\fujim\.config\kilo\kilo.jsonc` → `permission.bash` を再構築（旧 365 エントリの単発コマンドジャンク全削除 → 98 エントリ）:
  - 先頭 `"*": "ask"` フォールバック（`last match wins` により全マッチ対象の既定値）
  - 中段 allow 群: `python *` / `npm *` / `npx *` / `node *` / `astro *` / `pytest *` / `pip 系` / `curl *` / `Invoke-WebRequest *` / `Invoke-RestMethod *` / `git *` / `gh *` / `winget *` / `ffmpeg *` / `huggingface-cli *` / `chcp *` / 読取系 PowerShell cmdlet / `kilo-safe-*` 等
  - 後段 例外 ask: 破壊的操作（`Remove-Item *` / `rm *` / `del *` / `rd *` / `rmdir *` / `pip uninstall *` / `npm uninstall *` / `git push --force *` / `git push -f *` / `git push --mirror *` / `git reset --hard *` / `git clean *` / `gh repo delete *`）+ `powershell *` / `pwsh *`
  - 2026-10-13 緩和: `python -c *` / `python - *` / `node -e *` / `Set-Content *` / `Out-File *` / `New-Item *` を allow（最終 **allow=82 / ask=16**）
- `S:\Documents\AutoBlog\my-auto-blog\AGENTS.md` → `## Command Execution Rules` セクション追加:
  - Rule 1 一行コマンド（複数行禁止。複数文は `;` で一行に連結）
  - Rule 2 インライン Python 禁止 → `C:\Users\fujim\AppData\Local\Temp\kilo\` へスクリプトを書き出し `python <file>` で実行（一時ファイルはリポジトリ外に保持。例外: 一行・副作用なしの確認 `python -c "print(1+1)"` は allow）
  - Enforcement 注記（破壊的操作のみ ask、上記 6 パターンは allow）
- バックアップ: `C:\Users\fujim\.config\kilo\kilo.jsonc.bak-20261013`（SHA256 `E0E96981DE6CF84183CCB27F9B9A21324EEBC73008103B7B0E6146AB6CDB3932`、書込前・元ファイルと一致確認済み）

## 設計判断

- 公式ドキュメントで `last match wins`（後続ルールが優先）を確定した上で「フォールバック ask 先頭 → 特定 allow 中段 → 破壊的操作 ask 後段」の構造を採用。broad な allow が先頭にあると後続の特定 allow が上書きされないため、フォールバック ask を先頭に置く。
- 承認ゲート（`permission.bash`＝「どのコマンドを自動許可するか」）と行動指針（`AGENTS.md`＝「エージェントがコマンドをどう組むか」）を別レイヤとして分離。
- 詳細: `docs/ai/decisions.md` 2026-10-13

## Verification

- `validate_kilo_config.py`（`C:\Users\fujim\AppData\Local\Temp\kilo\`）実行: JSON 妥当性 OK、bash ルール 98 件（allow=82 / ask=16）、ask ルール一覧確認（`*` / `powershell *` / `pwsh *` / 破壊的操作 13 件）。システム `config_validation` も各 Edit 時通過。
- コード変更なし（`kilo.jsonc` + `AGENTS.md` + `docs/ai/` のみ）→ AGENTS.md 規則により pytest / `npm run build` 不要。
- エンコーディング: `AGENTS.md` は BOM なし UTF-8（Edit ツール使用、`git diff` で破損確認）

## Next Action

- なし（`c683247` で commit + push 済み）
