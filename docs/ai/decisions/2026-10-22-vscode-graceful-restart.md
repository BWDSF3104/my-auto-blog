# VS Code 正規クローズ＋再起動バッチ: タスクスケジューラによる再起動委譲（強制終了なし）

**Date**: 2026-10-22

**Decision**: エージェントから実行可能な VS Code 再起動を「正規クローズ（WM_CLOSE 送信）＋再起動」として実装。強制終了（taskkill 等）は一切不使用。再起動処理は、VS Code プロセスツリーの外にある**一発タスク（タスクスケジューラ）** に委譲する。

**背景**:
- ユーザー要求: エージェント（VS Code 内の PowerShell）から実行できる VS Code 再起動バッチ。追加条件: 「タスクキル等の強制終了系は避けてください」。
- プロセスツリー調査（Win32_Process、2026-10-22 時点）:
  - Code.exe メイン (pid 14688) ← explorer.exe (12028)
  - Code.exe 子プロセス (30704) ← kilo.exe (12012、エージェント本体)
  - kilo.exe の子 ← cmd.exe / powershell.exe（bash ツールのシェル、バッチ実行位置）
  - → バッチ・Python スクリプトは Code.exe プロセスツリーの descendants である。
- 正規クローズ時に VS Code がターミナル子プロセスツリーを殺害する可能性が高い（インテ그レートターミナルのプロセスが VS Code 終了で落ちるのは周知の挙動）。ツリー内の再起動ロジックは完遂できずに kill される恐れがある。

**設計**（すべて `maintenance/` 下、Python は標準ライブラリのみ）:
- `restart-vscode.bat`: 引数なし=Y/N 確認、`--yes`=非対話（エージェント用）、`--dry-run`=特定のみ、`--self-test <cwd>`=新規ウィンドウの起動/クローズ自己テスト。cmd コードページ対応のため **ASCII のみ**。
- `vscode_graceful_restart.py`:
  - 特定: tasklist（/FI IMAGENAME eq Code.exe, /FO CSV）で code.exe の PID 集合を取得。EnumWindows でトップレベルウィンドウを走査し、その PID が集合に含まれ、かつウィンドウクラスが `Chrome_WidgetWin_0/1`（Electron メインウィンドウ）の場合のみ対象とする。IME（`IME`/`MSCTFIME UI`）・crashpad・Electron host 等の補助ウィンドウは除外。
  - クローズ: 対象 hwnd へ WM_CLOSE 送信（ユーザーが X 押すのと同じ）。
  - 再起動: 一発タスク `my-auto-blog\vscode-restart` を /Create（約5分後バックストップ）＋ /Run（即時）で登録。
  - 起動: `subprocess.Popen([code_path, cwd], creationflags=DETACHED_PROCESS)` でバックグラウンド起動（cmd `start` の作業ディレクトリ解釈の曖昧さと非ブロッキング両立のため採用）。
  - code_path: `code` が PATH にあれば優先。なければ `code.cmd`（Windows ネイティブ ランチャー）のパスを候補ディレクトリ（C:/D:/E: の Program Files、LOCALAPPDATA、ProgramData）から特定。
- `vscode_relaunch_worker.py`: タスクのアクション。引数で cwd と code_path を受け取る。tasklist で Code.exe 消滅をポーリング（最大 180 秒）→ DETACHED_PROCESS 起動 → 起動確認（最大 60 秒）→ タスク定義を自己削除（ベストエフォート）。
- 補助: `--self-test` は scratch フォルダ（`docs/ai/tmp/vscode_selftest`、gitignore 対象）で新規ウィンドウを起動し WM_CLOSE で正規クローズして検証。既に開かれているフォルダへ起動すると既存ウィンドウのフォーカスになるため、新規ウィンドウの生成には scratch フォルダが必要。

**代替案と不採用理由**:
- `taskkill /F /IM Code.exe`: ユーザーが明言して禁止（かつ /T 併用ならバッチ自身が kill される、/T なしでもツリー kill に頼る必要が残る）。
- "Developer: Reload Window" のキー入力のシミュレーション: ウィンドウフォーカス・コマンドパレットのタイプイン・UI 言語に依存し脆弱。AutoHotkey は未導入。

**トレードオフ（許容）**:
- 実行毎にタスク定義が HKCU に残存し得る（次実行時に前回の定義を削除）。/Run は一発トリガーを消費する。万一残存してもワーカーは幂等（Code.exe が起動中なら 180 秒待機して無操作終了）。
- ワーカー実行中の自己削除でタスク定義が残存し得るが、完了した一発タスクは再発動しないため無害。
- ユーザーが手動で VS Code を閉じた直後にタスクが待機している場合、再起動され得る（稀。許容）。
- 未保存バッファのプロンプトが現れるとクローズが止まり、ワーカーが 180 秒待機後に失敗終了（手動対応必要）。
- エージェントセッションはクローズ時に中断され得る（設計上）。Kilo セッションは再開可能。
