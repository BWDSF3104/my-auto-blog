# VS Code 再起動バッチの WM_CLOSE 失敗（自動再起動未成功）

**Date**: 2026-10-26
**状態**: 未解決（未着手）

## 確認した事実

- `2026-10-26-plugin-utf8-minimal` プラグイン最小化の実装検証終了時に、ユーザー指示どおり `maintenance\restart-vscode.bat --yes` を実行。
- 出力:
  ```
  warning: WM_CLOSE failed for some window, continuing
  found Code.exe main windows: 3
    hwnd=... pid=... title=''
    hwnd=... pid=... title='... my-auto-blog - Visual Studio Code [管理者]'
    hwnd=... pid=... title=''
  close requested
  relaunch delegated to scheduled task my-auto-blog\vscode-restart; VS Code should reopen in about 5-10 seconds
  ```
- 結果: **WM_CLOSE が一部ウィンドウで失敗**。VS Code が自動再起動しなかった（ユーザー確認: 再起動失敗）。ユーザーが**手動再起動**を実施。

## 影響

- 自動再起動バッチの「実行モード」が本番未検証で、実際の実行で WM_CLOSE が失敗しうる。
- 再起動自体は手動で実現（新セッションは pwsh 7 + 新プラグイン）。

## 対応の方向性（未着手）

- `2026-10-22-vscode-graceful-restart.md`（設計）は「実行モード（実際のクローズ＋再起動）は未検証」と注記済み。
- 本次で実環境（3 ウィンドウ、1 本が管理者 `[管理者]` タイトル付き）で実行し、WM_CLOSE が一部失敗したことを実証。
- 改善候補:
  1. 管理者権限のウィンドウ（`[管理者]`）への WM_CLOSE 失敗原因を特定（UIAccess / 管理者権限の違い）。
  2. WM_CLOSE 失敗時は `WM_KILL` 等へのフォールバック、または `taskkill /IM code.exe /MINIMIZE` 等との併用検討。
  3. 再起動失敗を検知し、ユーザーに「手動再起動を必要」と通知する。

## 関連

- 設計: `docs/ai/decisions/2026-10-22-vscode-graceful-restart.md`
- バッチ: `docs/ai/tasks/2026-10-22-vscode-graceful-restart-batch.md`
- 実行口: `maintenance\restart-vscode.bat`、`maintenance\vscode_graceful_restart.py`、`maintenance\vscode_relaunch_worker.py`
