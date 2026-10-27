# schtasks /TR の 255 文字上限（caller session ID 追加で超過し得る）

**KI-20261028-02**
**Date**: 2026-10-28
**状態**: 発生・実装解決（2026-10-28 実測）。caller 追加で TR=261 文字 → `schtasks /Create` 失敗（`/TR` の値を 255 文字より多く指定できない）

## 事実

- worker へのタスク action（TR）は `pythonw worker <cwd> <code_path> <attempt> <caller>` の連結
- `schtasks /TR` の上限は 255 文字。現環境の TR は約 232 文字（caller 17 文字込み）で受理
- path が長い環境（例 `C:\Users\<長いuser名>\AppData\Local\Programs\Python\Python310\pythonw.exe`）では caller 追加で 255 を超え `schtasks /Create` が失敗し得る

## 発生（2026-10-28 実測）

- `--notify-session ses_e821e8ac4ffeSkxRvQ2d2Z7pwo`（30 文字）で TR=261 文字 → `schtasks /Create` 失敗（exit 2、close 前）

## 対応（実装済み・採用）

- caller を TR に埋めず、entry がスクラッチファイル `docs/ai/tmp/vscode_relaunch_notify.txt` へ書き、worker が読んで notify 後削除（`write_notify_target()` / `read_notify_target()`）
- `schedule_relaunch()` に長さガード: TR が 255 を超える場合は `log()` に失敗行を出して exit 2（検知可能）
- テスト: `test_task_command_line_excludes_caller`, `test_notify_target_handoff`

## 関連

- `maintenance/vscode_graceful_restart.py`（`task_command_line()` / `schedule_relaunch()`）
- 設計: `docs/ai/decisions/2026-10-22-vscode-graceful-restart.md`（`--notify-session`）
