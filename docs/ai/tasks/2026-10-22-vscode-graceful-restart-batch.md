# VS Code正規クローズ＋再起動バッチ作成（強制終了なし）

**Status**: 完了
**Date**: 2026-10-22
**Next Action**: （完了。実運用で `restart-vscode.bat --yes` を実行して再起動を確認）

## 意図 / 背景

- エージェント（VS Code 内の PowerShell）から実行可能な VS Code 再起動バッチの作成。
- 追加条件: 強制終了（taskkill 等）は避ける。正規クローズ（WM_CLOSE、ユーザーが X 押すの同等）でクローズし、タスクスケジューラの一発タスクで再起動委譲（バッチは VS Code プロセスツリーの shell 内を走るため、クローズ時にツリー kill に強くなる）。

## 調査結果 / 変更内容

- プロセスツリー: Code.exe メイン ← explorer.exe、kilo.exe は Code.exe 子、bash シェルは kilo の子 → バッチ/Python はツリー内。
- `code` は PATH に登録されておらず、`code`（POSIX sh スクリプト）と `code.cmd`（Windows ランチャー）が存在 → 起動は `code.cmd` のフルパスで。
- Toolhelp Snapshot（CreateToolhelp32Snapshot + Process32FirstW）は、この環境では `Process32FirstW` が ERROR_INVALID_PARAMETER(24) を返して失敗 → 代替として **tasklist (/FO CSV) で PID 集合を取得**した。
- EnumWindows で特定したトップレベルウィンドウに、code.exe 以外に加え **IME（`IME`/`MSCTFIME UI`）・crashpad_SessionEndWatcher・Electron_SystemPreferencesHostWindow・Base_PowerMessageWindow** 等が含まれる → **ウィンドウクラス `Chrome_WidgetWin_0/1`（Electron メインウィンドウ）の过滤**で対象を狭める。
- 起動: `start "" "code" <cwd>` は `start` の作業ディレクトリ解釈と非ブロッキング両立に不都合（cmd の child がタイムアウト）→ `subprocess.Popen([code_path, cwd], creationflags=DETACHED_PROCESS(0x10))` に変更。実測で scratch フォルダを正しいタイトルで新規ウィンドウとして起動できた。
- 変更ファイル: `maintenance/vscode_graceful_restart.py`（特定・WM_CLOSE・schedule_relaunch・self_test）、`maintenance/vscode_relaunch_worker.py`（worker 論理 + code_path 引数）、`docs/ai/decisions/2026-10-22-vscode-graceful-restart.md`。

## Verification

- 構文: `python -m py_compile maintenance/vscode_graceful_restart.py maintenance/vscode_relaunch_worker.py` → 両方 OK。
- dry-run（`python maintenance/vscode_graceful_restart.py --dry-run <cwd>`）: code.exe の Electron メインウィンドウ（Chrome_WidgetWin_0/1）のみを特定（IME 等の補助ウィンドウは除外）。実行時 4 個を特定。
- 自己テスト（`python maintenance/vscode_graceful_restart.py --self-test <cwd>`）: scratch フォルダで新規ウィンドウを起動 → WM_CLOSE で正規クローズ →「self-test complete: scratch window closed normally」で成功。
- 起動機構: scratch フォルダで `code.cmd` を DETACHED_PROCESS で起動し、正しいフォルダのタイトルで新規ウィンドウが生成されることを確認（終了済み）。
- スケジューラ: `schtasks /Create /Run /Delete` の往復テスト成功（/Create=0, /Run=0, /Delete=0）。
- 未検証（実運用で確認要）: 実行モード（実際の VS Code クローズ＋再起動）。本セッションでは自己コードを閉じるため実行不能（設計上、エージェントセッションは中断され得る）。

## 完了時 Memory Bank 操作

- [x] `current-task.tsv` の参照行を削除
- [x] 解決した `known-issues/` ファイルを `known-issues/archive/` へ `mv`（該当なし）
- [x] `backlog.md` の完了項目を削除（該当なし）
