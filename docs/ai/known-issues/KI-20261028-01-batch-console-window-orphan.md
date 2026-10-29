# 再起動バッチのコンソールウィンドウが残存（cmd.exe デフォルトタイトル）

**KI-20261028-01**
**Date**: 2026-10-28
**状態**: 実装・実測完了（2026-10-28）。方針確定: **スイープ（B）は不採用** — 実行経路に console app（cmd.exe）を入れないことでウィンドウを生成しない。孤児化は console app が途中で kill されたときだけ起こるため、console app がなければ残るウィンドウ自体が存在しない

## 確認した事実

- 残ったウィンドウは VS Code のウィンドウではなく**コンソールウィンドウ**（`ConsoleWindowClass`、タイトル `C:\WINDOWS\system32\cmd.exe` = デフォルトタイトル）
  - `hwnd=0x2c010a pid=10456 cls=ConsoleWindowClass visible=True title='C:\WINDOWS\system32\cmd.exe'`
- pid 10456 は `conhost.exe`（`\??\C:\WINDOWS\system32\conhost.exe 0x4`）、作成時刻 `2026-10-28 1:23:15`
- その親（19460）は既に消滅 → **オーファン化したコンソールウィンドウ**
- バッチのタスク行動は `cmd /c python.exe vscode_relaunch_worker.py <cwd> <code_path> <attempt>` → 交互セッションで実行されるためコンソールウィンドウが生成される
- worker は 1:23:17 に success を書き、終了。タスク定義も削除済み（`schtasks /Query /TN "my-auto-blog\vscode-restart"` → 存在しない）

## 原因（推定）

- プロセス側は正常終了しているが、conhost ウィンドウが残った。交互セッションで Task Scheduler が割り当てたコンソールは、プロセス終了後もウィンドウが閉じない場合がある（owner が切り離された状態で conhost が残る）

## 改善案 → 実装済み（2026-10-28）

- タスク action から **`cmd /c` を除去**し、`pythonw.exe`（GUI subsystem）を直接実行。交互セッションで console app（cmd.exe）を経由しないためコンソールウィンドウが生成されない
- `_interpreter_path()` が pythonw を優先、存在しなければ `python.exe` へフォールバック
- worker の出力は `out()` ガード（`sys.stdout` が None の場合は例外を出さない）。通知口はレポートファイル
- 追加テスト: `test_interpreter_prefers_gui_subsystem`, `test_task_action_does_not_go_through_console_app`, `test_out_survives_missing_stdout`（`maintenance/tests/test_vscode_graceful_restart.py` 8 件）

### 検証

- `pytest maintenance/tests/ -v` → **61 passed**
- `--dry-run` → `interpreter (task action): ...\Python310\pythonw.exe`
- schtasks 受理確認（probe 作成 → XML 確認 → 削除）:
  - `<RunLevel>HighestAvailable</RunLevel>`
  - `<Command>"C:\...\Python310\pythonw.exe"</Command>`（cmd.exe なし）
- 未確認: 実際の再実行時にウィンドウが出ないこと（実行時は Agent 自分のウィンドウを閉じる）

### 実測（2026-10-28 2nd run）

- worker 側は問題なし: `pythonw` 行動で success（`attempt=20261028-014443`）、コンソールウィンドウは生成されなかった
- この回に残ったウィンドウ（`ConsoleWindowClass`, `C:\WINDOWS\system32\cmd.exe`）は worker ではなく **`cmd /c restart-vscode.bat --yes` を分離プロセスとして起動した側**（conhost オーファン）
- WM_CLOSE でクローズ済み（`docs/ai/tmp/post_run_check.py --close-orphans`）
- 運用: Agent 実行時は `cmd` を経由せず `python maintenance/vscode_graceful_restart.py` をシェルから直接。ユーザーが終端ペインで `.bat` を実行する分にはウィンドウ問題なし（terminal pane は ConsoleWindowClass を作らない）

### entry 側の実装（2026-10-28）

- `restart-vscode.bat` の execute モード（`--yes`）を `start "" /b pythonw "%~dp0vscode_graceful_restart.py" "%cd%"` に変更。cmd は即 exit するため自前ウィンドウは閉じ、pythonw（GUI subsystem）はコンソールウィンドウを作らない
  - `ask` モード（対話 Y/N）は表示が必要なため console 実行を維持（通常終了でウィンドウは閉じる。オーファン化は分離起動時の tree kill で起こった)
  - `pythonw` が PATH にない場合のみ `python.exe` へフォールバック
- 出力は `log()` に統一: stdout が使える場合は表示し、常に `docs/ai/tmp/vscode_relaunch_report.txt` へ追記（pythonw 起動の通知口。`out()` ガードと同趣旨）
- 追加テスト（`maintenance/tests/test_vscode_graceful_restart.py`）: `test_log_writes_to_report_without_stdout`, `test_log_survives_unwritable_report`, `test_execute_mode_uses_detached_pythonw_in_bat`
- `_code_path()`（worker と script 両方）: `code.cmd`（batch → cmd.exe）優先をやめ、native（WindowsApps `code` stub / `bin\code.exe` / `Code.exe`）を優先、`code.cmd` はフォールバックのみ。worker の `relaunch()` は native を Popen するため、タスク実行経路に console app が入らない（テスト: `test_code_path_prefers_native_over_cmd`, `test_code_path_falls_back_to_install_root_code_exe`）
- `cleanup_scratch()`: `cmd.exe /c kilo-safe-rmdir.cmd` をやめ、`powershell.exe -File maintenance/safe-rmdir.ps1`（同一実装）の直接呼出へ（テスト: `test_cleanup_scratch_does_not_go_through_cmd`）

### 採用運用（B 不採用、2026-10-28 確定）

- 残存ウィンドウの唯一の原因は「console app が途中で kill されたときの conhost 孤児化」。console app を経路に入れないことで解決（スイープ不要）
- **Agent 経路**: `cmd /c bat` を呼ばず `pythonw maintenance/vscode_graceful_restart.py <cwd>` を直接実行（GUI subsystem → コンソールウィンドウ生成されない。中断で kill されても閉じるウィンドウが存在しない）
- **worker 経路**: pythonw（実装済み）
- **.bat**: ユーザー対話用のみ。終端ペイン実行ではウィンドウ不出。ダブルクリックでは実行中 cmd のウィンドウが一瞬出るが正常 exit で閉じる（孤児化は force kill 時だけ）
- トレードオフ: Agent 実行の出力はコンソールではなくレポートファイル経由
- 実測（pythonw 経路, 2026-10-28 02:08）: `pythonw maintenance/vscode_graceful_restart.py <cwd>` 実行で batch 経路はウィンドウを生成しなかった（レポート success、再起動インスタンス [管理者]）。残ったウィンドウは batch ではなく **ツール呼び出し自身の console app ラッパー（pwsh）が中断で kill されたことによる conhost 孤児化**。呼出しが正常完了すればウィンドウは閉じる（呼出し内で長 sleep を同一呼出しに含めない/中断しない）

### 推奨回避方法（優先度順・外部からの WM_CLOSE 強制閉じは使わない）

1. **console app をそもそも実行しない**: Agent 実行は `background_process` で `pythonw maintenance/vscode_graceful_restart.py <cwd>` を起動（GUI subsystem → console が生成されず、残留プロセスが発生し得ない。完了判定はレポートファイル）。これが根本解決
2. **正常終了で閉じさせる**: console app を使う場合は呼出しを短く完結させ、正常 exit でウィンドウを自閉じる（bat の execute モードは `start /b pythonw` 後 cmd が即 exit）。中断・長 sleep で呼出しが生きて kill されないこと
3. （非推奨）孤児ウィンドウの WM_CLOSE は後始末としてのみ

#### 実測

- `pytest maintenance/tests/ -v` → **64 passed**
- 分離起動 probe: `start "" /b pythonw maintenance\vscode_graceful_restart.py --dry-run docs\ai\tmp` → 新コンソールウィンドウなし、レポートに `entry:` 行を確認（`ConsoleWindowClass` は Kilo CLI 自前のコンソールと不可視の Google Drive のみ）
- 注意: `start` のクォーティングは cmd 側で完結する必要がある（シェル経由で `""` が壊れると title 扱いされウィンドウが出る。bat 内リテラルは正常）

なお `/RL HIGHEST` の登録は昇格シェルが必要: 非昇格シェルでは `schtasks /Change ... /RL HIGHEST` が `Access is denied`（実測）、昇格シェルでは成功（実測）。

### worker notify 側の実測・修正（2026-10-28）

- notify の `kilo` は npm shim 経由で `kilo.cmd`（cmd.exe）解決。`capture_output=True`（redirected handles）だけでは console window を防げない: 実測で `管理者:  C:\WINDOWS\system32\cmd.exe` ウィンドウが生成された（owner pid 23560 = `kilo.exe`、cmd 終了後も conhost が残った）
- 修正: worker `notify()` の `subprocess.run(..., creationflags=CREATE_NO_WINDOW)`（生成しない）。テスト: `test_notify_sends_via_kilo_run` に creationflags 追加 → 73 passed
- 修正後実測（attempt=20261028-025604, 2026-10-28 02:56）: console window は生成されなかった（CREATE_NO_WINDOW 有効）。delivery は target の user turn として成功。応答は target の turn 完了時に生成され、`kilo run --session` はその応答を待つ（busy 中は block、60s 内に応答が完了すれば `notify sent`）
- 副次観察: `kilo run --session` は target の応答ターンを待つ（blocking、worker 側 timeout 60s）。target が busy のとど（今回の呼出し元=self）message は届くが応答ターンが生成されず、60s 後に `notify failed: ... timed out` 行をレポートへ。notify は target が idle の時に届く前提

## 関連

- バッチ: 正典 `Kilo_Commons\Common_Operations\bin\vscode_graceful_restart.py`（`schedule_relaunch()`）、`bin\vscode_relaunch_worker.py`、`bin\kilo-vscode-restart.cmd`（2026-10-29 正典化。プロジェクト内 `maintenance/` コピーはリタイア）
- 設計: `docs/ai/decisions/2026-10-22-vscode-graceful-restart.md`（2026-10-28 改訂）
- 解決済み KI: `docs/ai/known-issues/archive/KI-20261026-02-vscode-restart-wmclose-failure.md`

## 移動注記（2026-10-29）

- ラッパーの execute モード（`--yes`）は `start "" /b pythonw "%~dp0vscode_graceful_restart.py" %2..%9`（正典 bin 内の `.cmd`）。`%*` は mode 引数自身を含むため使わない（mode 以降をスライス）。cmd 内は ASCII・CRLF、label/loop なし
- テストは Kilo_Commons `tests/test_vscode_graceful_restart.py` へ集約（`test_wrapper_execute_mode_uses_detached_pythonw` が `.cmd` の分離起動を照合）
