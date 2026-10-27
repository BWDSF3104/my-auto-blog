# VS Code 再起動バッチの WM_CLOSE 失敗（自動再起動未成功）

**Date**: 2026-10-26
**状態**: 解決（2026-10-27 16:21 端到端確認）— 判定ロジック修正＋昇格シェルでの実行で、クローズ→worker 再起動→昇格インスタンスで再起動成功を実証

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

## 改善の方向性（未着手）

- `2026-10-22-vscode-graceful-restart.md`（設計）は「実行モード（実際のクローズ＋再起動）は未検証」と注記済み。
- 本次で実環境（3 ウィンドウ、1 本が管理者 `[管理者]` タイトル付き）で実行し、WM_CLOSE が一部失敗したことを実証。
- 改善候補:
  1. 管理者権限のウィンドウ（`[管理者]`）への WM_CLOSE 失敗原因を特定（UIAccess / 管理者権限の違い）。
  2. WM_CLOSE 失敗時は `WM_KILL` 等へのフォールバック、または `taskkill /IM code.exe /MINIMIZE` 等との併用検討。
  3. 再起動失敗を検知し、ユーザーに「手動再起動を必要」と通知する。

## 再検証（2026-10-27）

### 確認した事実

- 現環境は VS Code 全体が昇格トークンで起動（タスクスケジューラ由来）。根拠:
  - `whoami /groups` → Mandatory Level High（`S-1-16-12288`）、`BUILTIN\Administrators` が `Enabled group, Group owner`
  - `net session` が Access Denied にならず成功（昇格トークンの証左）
  - プロセスチェーン `services.exe`(780) → `Code.exe`(2304) → `Code.exe`(24212) → `Code.exe`(24464) → `pwsh`（Kilo シェル）
- 同一インテグリティでは WM_CLOSE が機能することを実証:
  - `code -n docs/ai/tmp/vscode_selftest` で新規**可視**ウィンドウ（`Chrome_WidgetWin_1`）を作成 → WM_CLOSE 送信 → 約1秒でクローズ成功
- したがって 2026-10-26 の失敗原因は **UIPI（インテグリティ不一致）** の可能性が高い（非昇格シェルから高インテグリティウィンドウへの SendMessage はフィルタされる）。当時は `[管理者]` ウィンドウと非昇格シェルが混在。直接証明は未実施（低インテグリティ側から再現実验できない）。

### 判明した追加の欠陥（再現確認済み）

1. **成功判定が偽陽性/偽陰性**: `send_close()` は `SendMessageW` の返り値で判定するが、WM_CLOSE が正常処理された後も `DefWindowProc` は `0` を返す（`SendMessageW` の返り値＝窓プロックの返り値）。よって返り値では失敗を検知できない。UIPI フィルタ時の `0` と区別不能。
2. **対象ウィンドウに不可視 helper が含まれる**: `find_code_windows()` は `Chrome_WidgetWin_0/1` を区別しない。実測で 4 ウィンドウ中可視は 1 のみ（`0x3a0a60`）、残り 3 は `visible=0` の `Chrome_WidgetWin_0`。helper ウィンドウは WM_CLOSE で閉じない → `all(send_close(...))` は常态で False になりうる。
3. **`--self-test` は単一インスタンス環境で検証できない**: `code <path>` は新規ウィンドウを作らず既存ウィンドウをフォーカスし、不可視 helper が増えてカウントだけ増える。実測: self-test 失敗判定、helper `0x50d7a` が未クローズで残存。新規**可視**ウィンドウには `-n` が必要。

### 改善案 → 実装済み（2026-10-28）

- 対象を **可視 `Chrome_WidgetWin_1` のみ** に限定（`IsWindowVisible`）。
- 判定は返り値ではなく、送信後の**ウィンドウ/プロセス消失ポーリング**で行い、残存時のみ失敗として通知（ワーカー側の 180 秒判定と統一）。
- 実行シェルとターゲットウィンドウのインテグリティ一致を確認。不一致なら「UIPI で送信不可 → 昇格シェルで実行必須」と明示（タスクスケジューラで VS Code を昇格起動する現運用で一致する）。
- `--self-test` は `code -n <scratch>` を使用し、可視ウィンドウの生成＋クローズを検証。
- `schtasks /Create` に **`/RL HIGHEST`** 追加（既定 Limited では再起動インスタンスが非昇格）。非昇格シェルでは登録不可のため `needs_elevation()` で exit 3（何も変更しない）。
- worker の attempt id 冪等化: `already_ran(attempt)` で ONCE トリガーの再発動を静かに exit 0。
- `--self-test` の scratch フォルダは `kilo-safe-rmdir.cmd`（ゴミ箱）へ。

### 実行モード端到端（2026-10-27 15:31、ユーザー許可）

- WM_CLOSE（可視 main window 1、インテグリティ一致 High/High）→ shell kill → worker 0:33:06 に Code.exe 消滅確認＋起動確認 → **success**（`docs/ai/tmp/vscode_relaunch_report.txt`）。クローズ＋再起動経路は機能。
- ただし**再起動後のインスタンスは非昇格（Medium）**:
  - `whoami /groups` → Medium（`S-1-16-8192`）。再起動後インスタンス pid 16744 の integrity も Medium、タイトルから `[管理者]` が消えた
  - 原因: `schtasks /Create` の run level 既定（Limited）。`schtasks /Query /TN "my-auto-blog\vscode-restart" /XML` に `<RunLevel>` がない（=Limited）。よって worker（Limited トークン）が起動した Code.exe は Medium。最上位権限で起動していた元のインスタンス（タスクスケジューラ設定）とは別
  - 修正案: `schtasks /Create` に **`/RL HIGHEST`** を追加
- **`/Run` は ONCE トリガーを消費しない**（設計の「完了した一発タスクは再発動しない」は誤り）: バックストップ（0:37）で worker が再発動し、Code.exe が 180 秒待機後に failure（Last Result 2、report 00:40:31）。タスク定義も残存（実行中の `schtasks /Delete` は失敗）。
- self-test の後始末: `--self-test` が作った scratch フォルダ（`docs/ai/tmp/vscode_selftest`）と、不可視 helper ウィンドウ（WM_CLOSE では閉じない）が残る。VS Code の `globalStorage/storage.json` の `profileAssociations` に scratch フォルダが記録され、起動時にウィンドウが復元されうる。

### 残存

- self-test が作成した不可視 helper ウィンドウ（hwnd `0x50d7a`）が未クローズで残存（WM_CLOSE では閉じないため）。ユーザーのウィンドウには影響なし。改訂後は helper はクローズ対象に含まれない。
- 失敗通知の受け口: worker が `docs/ai/tmp/vscode_relaunch_report.txt` へ結果を追記（実行シェルは自分のウィンドウクローズで kill されるため、 Agent 側の判定はベストエフォート）。
- 未確認: 実行モードの端到端（実クローズ＋worker による再起動）。`--yes` 実行は Agent 自分の VS Code を閉じるためユーザー許可が必要。
- 前回のタスク定義 `my-auto-blog\vscode-restart` が残存（非昇格シェルからは `schtasks /Delete` が Access denied）。次回、昇格シェルからの実行時 `/Delete` で消える。

## 関連

- 設計: `docs/ai/decisions/2026-10-22-vscode-graceful-restart.md`
- バッチ: `docs/ai/tasks/2026-10-22-vscode-graceful-restart-batch.md`
- 再検証タスク: `docs/ai/tasks/2026-10-28-vscode-restart-wmclose-verify.md`
- 実行口: `maintenance\restart-vscode.bat`、`maintenance\vscode_graceful_restart.py`、`maintenance\vscode_relaunch_worker.py`
