# VS Code 再起動バッチ WM_CLOSE 失敗の再検証（KI-20261026-02）

**Status**: 完了
**Date**: 2026-10-28
**Next Action**: 昇格シェル（昇格 VS Code）からの端到端確認（`--yes` 実行の許可が必要）→ 成功後に KI を archive へ

## 意図 / 背景

- `docs/ai/known-issues/KI-20261026-02-vscode-restart-wmclose-failure.md`（未解決）の再検証。2026-10-26 の本番実行で WM_CLOSE が一部ウィンドウで失敗し、自動再起動に至らなかった（ユーザー手動再起動）。
- 現環境（タスクスケジューラで VS Code を最上位権限へ昇格起動）でクローズ経路が機能するかを確認し、失敗原因とコード上の判定欠陥を特定する。実装は行わない（承認待ち）。

## 調査結果 / 変更内容

### 機能する部分（実証）

- 現環境は VS Code 全体が昇格トークンで起動（`whoami /groups` → Mandatory Level High `S-1-16-12288`、`BUILTIN\Administrators` = `Enabled group, Group owner`。`net session` 成功＝昇格トークン。プロセスチェーン `services.exe`(780) → `Code.exe`(2304) → `Code.exe`(24212) → `pwsh`）。
- 同一インテグリティで WM_CLOSE が効くことを実証: `code -n docs/ai/tmp/vscode_selftest` で新規**可視**ウィンドウ（`Chrome_WidgetWin_1`）作成 → WM_CLOSE 送信 → 約1秒でクローズ。
- したがって 2026-10-26 の失敗は **UIPI（インテグリティ不一致）** が最有力（非昇格シェル → 高インテグリティ `[管理者]` ウィンドウの SendMessage はフィルタされる）。低インテグリティ側からの再現実验は当前不可なので推定どおり。

### 判定ロジックの欠陥（再現確認済み）

1. `maintenance/vscode_graceful_restart.py:165`（`send_close`）は `SendMessageW` の返り値を成功判定するが、返り値は窓プロックの返り値で、正常処理後も `DefWindowProc` は `0` を返す → 偽陰性。UIPI フィルタ時の `0` と区別不能（`last_error` も 0）。
2. `find_code_windows()` は `Chrome_WidgetWin_0/1` を区別しない。実測 4 ウィンドウ中可視は1のみ（`0x3a0a60`）、残り3は `visible=0` の `Chrome_WidgetWin_0` helper。helper は WM_CLOSE で閉じない → `all(send_close(...))` は常态で False。
3. `--self-test` は単一インスタンス環境で検証できない: `code <path>` は可視ウィンドウを作らず既存をフォーカスし、不可視 helper が増えてカウントだけ増える（実測: 失敗判定、helper `0x50d7a` 残存）。新規可視ウィンドウには `-n` が必要。

### 採用方針（改善案・未実装）

- 対象を**可視 `Chrome_WidgetWin_1` のみ**へ限定（`IsWindowVisible`）。
- 成功判定は返り値ではなく、送信後の**ウィンドウ／Code.exe プロセス消失をポーリング**（ワーカー側の 180 秒判定と統一）。残存時のみ失敗として通知。
- 実行シェルのインテグリティとターゲットウィンドウの一致を確認。不一致なら「UIPI で送信不可 → 昇格シェルで実行必須」と明示。
- `--self-test` は `code -n <scratch>` を使用し、可視ウィンドウ生成＋クローズを検証。

## 実装（ユーザー指示 2026-10-27「実装開始」）

- `maintenance/vscode_graceful_restart.py`
  - `is_main_window(class, visible)` → 可視 `Chrome_WidgetWin_1` のみ対象（helper 除外）
  - `close_and_verify()` → 返り値判定をやめ、送信後のウィンドウ消失（最大 15 秒）で判定
  - `own_integrity_level()` / `process_integrity_level(pid)` / `integrity_mismatch()` → `GetTokenInformation`（`TokenIntegrityLevel = 25`）。x64 ではバッファがクラス固有構造そのもの（PSID が offset 0）。不一致なら終了コード 3（UIPI）で実行前に通知
  - `self_test()` → `code -n <scratch>` で**可視**ウィンドウを作成し、そのウィンドウのみクローズ
  - 終了コード: 0 / 1 / 2 / 3（UIPI）
- `maintenance/vscode_relaunch_worker.py` → 結果を `docs/ai/tmp/vscode_relaunch_report.txt` へ追記（呼び出し元 shell は kill されるため通知口）
- 新規テスト: `maintenance/tests/test_vscode_graceful_restart.py`（判定ロジックのみ。ctypes 呼出しは検証しない）
- 設計改訂: `docs/ai/decisions/2026-10-22-vscode-graceful-restart.md`、`docs/ai/maintenance-batches.md`

## 実行モード端到端（2026-10-27 15:31、ユーザー許可）

- `maintenance\restart-vscode.bat --yes` を実行（出力は `docs/ai/tmp/exec_run_output.txt` へリダイレクト。shell は Code.exe 子ツリーなのでクローズ時に kill され、この turn の出力は消失しうる）
- 期待挙動:
  1. 可視 main window（`Chrome_WidgetWin_1`）のみ対象、インテグリティ一致（High/High）で UIPI 警告なし
  2. 一発タスク `my-auto-blog\vscode-restart` を `/Create`（約5分後バックストップ）＋ `/Run` → worker がツリー外で待機
  3. WM_CLOSE 送信後、この shell を抱えるウィンドウが閉じた瞬間に shell が kill される
  4. worker（スケジューラ）が Code.exe 消滅を確認 → DETACHED_PROCESS で `(cwd)` を開き再起動 → 結果を `docs/ai/tmp/vscode_relaunch_report.txt` へ追記
- 結果確認先: `docs/ai/tmp/vscode_relaunch_report.txt`（success/failure）と `docs/ai/tmp/exec_run_output.txt`（pre-close 出力）

### 実行結果（2026-10-27 15:31）

- クローズ＋worker 再起動は成功（report `2026-10-28T00:33:06 success`）。判定は可視 main window 1、インテグリティ High/High 一致で UIPI 警告なし
- **管理者権限では再起動されなかった**: 起動後のインスタンス integrity = Medium（`whoami /groups`）。`schtasks` 作成タスクの run level が既定（Limited、XML に `<RunLevel>` なし）→ worker が Medium トークンで `code.cmd` を起動
- `/Run` は ONCE トリガーを消費せず、バックストップ（0:37）で worker が再発動 → Code.exe 180 秒待機後 failure（Last Result 2、report 00:40:31）。タスク定義は残存（実行中の自己削除は失敗）

### 修正（ユーザー指示 2026-10-27「実施」）

1. `schedule_relaunch()` に `/RL HIGHEST` 追加（既定の Limited では worker が非昇格トークンで Code.exe を起動し、再起動後インスタンスが昇格しない）。`/RL HIGHEST` の登録には昇格トークンが必要 → `needs_elevation()` で非昇格シェルを exit 3 で拒否
2. worker の冪等化: attempt id をタスク TR に埋め、`already_ran(attempt)` で再発動（ONCE トリガー）を静かに exit 0（`/Run` はトリガーを消費しない）
3. `--self-test` の後始末: scratch フォルダを `kilo-safe-rmdir.cmd`（ゴミ箱）へ

### 検証

- `pytest maintenance/tests/ -v` → **57 passed**（`test_vscode_graceful_restart.py` 5 件: 可視ウィンドウ判定 / integrity 判定 / `needs_elevation` / attempt 冪等）
- `schtasks /Change /TN "my-auto-blog\vscode-restart" /RL HIGHEST`（非昇格シェル）→ `Access is denied`（要昇格を確認）
- `restart-vscode.bat --yes`（非昇格シェル）→ 何も変更せず exit **3**（非昇格シェル拒否メッセージ）
- `--self-test` → 可視ウィンドウ作成 → WM_CLOSE → 正常クローズ → `scratch cleanup: Sent to Recycle Bin: docs\ai\tmp\vscode_selftest`
- 残る `my-auto-blog\vscode-restart`（前回の定義）は非昇格シェルからは削除不可（`Access is denied`）。次回昇格シェル実行時の `/Delete` で消える

### 端到端 2回目（2026-10-27 16:21、昇格シェル）

- 実行時シェル = High（昇格实例）→ 非昇格ガードを通り、`/RL HIGHEST` でタスク登録、`/Run` 実行
- `docs/ai/tmp/vscode_relaunch_report.txt`: `2026-10-28T01:23:17 attempt=20261028-012313 success: VS Code relaunch complete`（attempt id が記録され、再発動ガードが有効）
- 再起動後のインスタンスは**昇格**: `whoami /groups` → High（`S-1-16-12288`）、ウィンドウタイトルに `[管理者]`、Code.exe main pid 24332（親 = cmd/worker 系、1:23:15 起動）
- `--self-test` の scratch フォルダはゴミ箱へ送出済み（`exists=False`）。16:25 時点の可視 VS Code ウィンドウは1（このセッション）のみ。残る不可視 helper（`Chrome_WidgetWin_0`）は WM_CLOSE で閉じないためクローズ対象外

## Verification

実行日: 2026-10-27

- `python -m py_compile maintenance/vscode_graceful_restart.py maintenance/vscode_relaunch_worker.py` → OK
- `pytest maintenance/tests/ -v` → **56 passed**（新規 3 件を含む）
- `pytest scripts/tests/ -v` → 収集エラー 1 件（`scripts/generate_article.py` が `GEMINI_API_KEY` 未設定で ValueError）。本タスクの変更（`maintenance/` のみ）とは無関係。既知の `KI-20261026-01`（ローカル Gemini key 未設定）に該当
- `--dry-run <cwd>` → 可視 main window 1 のみ特定（helper 3 は除外）。`shell integrity: High` / `pid=24212 integrity=High`（一致）
- `--self-test <cwd>` → 新規可視ウィンドウ作成 → WM_CLOSE → `self-test complete: scratch window closed normally`（**成功**。改訂前は helper 増加のみで失敗判定）
- 実行モード（`--yes`）は未実行: 自分の VS Code を閉じるためユーザー許可が必要。worker 端到端も未確認

## 残存

- self-test が作成した不可視 helper ウィンドウ（hwnd `0x50d7a`）が未クローズで残存。ユーザーのウィンドウへの影響なし。

## 完了時 Memory Bank 操作

- [ ] `current-task.tsv` の参照行を削除
- [ ] 解決した `known-issues/` ファイルを `known-issues/archive/` へ `mv`（該当する場合）
- [ ] `backlog.md` の完了項目を削除（該当する場合）
