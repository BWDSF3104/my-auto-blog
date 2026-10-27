# メンテナンスバッチ

`maintenance/` には本番パイプライン外の開発用・運用用バッチを置きます。本ファイルは各バッチの**一覧と詳細**です。`docs/ai/architecture.md` の Development Tools 節からこちらへ参照します。

## 一覧

| バッチ | 実行口 | 呼び出し | 目的 |
|--------|--------|----------|------|
| Memory Bank クリーンアップ | `maintenance/archive_memory_bank.py` | タスク開始時 | `tasks/`・`verification/`・`tmp/` の保持管理 |
| タスク開始/終了 | `maintenance/task_manager.py` | タスク開始時・終了時 | `tasks/` と `current-task.tsv` の更新・報告 |
| VS Code 再起動 | `maintenance/restart-vscode.bat` | 手動 (Agent / ユーザー) | VS Code 正規クローズ＋再起動（強制終了なし） |

## `archive_memory_bank.py`

**目的**: Memory Bank のバッチクリーンアップ。`docs/ai/` の `tasks/`・`verification/`・`tmp/` の保持管理。

**実行方法**:
```
python maintenance/archive_memory_bank.py
python maintenance/archive_memory_bank.py --apply
python maintenance/archive_memory_bank.py --tmp-retention-days 14
```

**保持基準**:
- `tasks/`: mtime（最終更新）が **14 日** 経過 → `archive/` へ mv
- `verification/`: mtime 順で**直近 2 ラン**保持
- `tmp/`: 最更新 mtime が **7 日**以上経過したエントリを削除（`--tmp-retention-days` で変更）

**呼び出しタイミング**: 新規タスク開始時（バッチクリーンアップ）。

**副作用・注意**:
- dry-run が既定。`--apply` 時に初めて反映。
- 削除は `kilo-safe-remove.cmd` / `kilo-safe-rmdir.cmd`（Windows ゴミ箱へ・復元可能）へ委譲。
- `--apply` 時にスクリプトが touch したパスは `git add` される（staging のみ）。
- 判定は mtime 基準（ファイル名日付方式は不採用）。

**関連**:
- テスト: `maintenance/tests/test_archive_memory_bank.py`
- 設計: `docs/ai/decisions/2026-10-14-memory-bank-cleanup-script.md`、`2026-10-15-tmp-retention.md`

## `task_manager.py`

**目的**: タスクの開始/終了を補助。`docs/ai/tasks/` のタスクファイル作成と `current-task.tsv` の参照行管理。

**実行方法**:
```
# 開始（タスクファイル作成 + current-task.tsv 参照行追加）
python maintenance/task_manager.py add --slug <slug> --title "<タスク名>" [--backlog "P<N> #<N>"] [--next-action "<next action>"]
# 終了（Status→完了 + current-task.tsv 参照行削除 + レポート）
python maintenance/task_manager.py end --task <パス / date-slug / slug>
```
- 既定は反映。`--dry-run` でプレビュー、`--no-git-add` で staging スキップ。

**呼び出しタイミング**: タスク開始時（`add`）／タスク終了時（`end`）。

**副作用・注意**:
- 書き込みスコープは「タスクファイルの Status 更新」＋「`current-task.tsv` の行削除」のみ（判断・実行は AI）。
- `end` は読み取り専用の「対応項目チェック」（`known-issues/` / `backlog.md` 照合）を報告追加。書き込みスコープ不変。
- 完了タスクの `known-issues/` 行は `known-issues/archive/` へ mv、`backlog.md` 完了行は削除（対応項目チェックの推奨）。

**関連**:
- テスト: `maintenance/tests/test_task_manager.py`
- 設計: `docs/ai/decisions/2026-10-19-task-end-related-check.md`

## `restart-vscode.bat`

**目的**: VS Code の**正規クローズ（WM_CLOSE）＋再起動**を VS Code の PowerShell（Agent）から実行。`taskkill` 等の強制終了は不使用。

**実行口**（3 ファイル）:
- `restart-vscode.bat` — 実行口（ASCII のみ・CRLF）
- `vscode_graceful_restart.py` — 特定・WM_CLOSE・タスク委譲・自己テスト
- `vscode_relaunch_worker.py` — タスクスケジューラ worker（再起動実行）

**実行方法**:
```
maintenance\restart-vscode.bat                  # 無引数: Y/N 確認
maintenance\restart-vscode.bat --yes            # 非対話 (Agent 用)
maintenance\restart-vscode.bat --dry-run <cwd>  # 特定のみ
maintenance\restart-vscode.bat --self-test <cwd>  # 新規ウィンドウ 起動/クローズ 自己テスト
python maintenance/vscode_graceful_restart.py <cwd> --notify-session <sessionID>  # Agent 経路（推奨）＋完了通知
```

**完了通知（--notify-session, 2026-10-28）**:
- 呼出し元セッション ID を渡すと、worker が完了時（成功・失敗双方）に `kilo run --session <id> "<message>"` で follow-up を送る（追加ターン1回）。local DB にあるセッションのみ。`kilo` 不在・失敗は skip/失敗行をレポートへ
- `subprocess.run(..., capture_output=True, creationflags=CREATE_NO_WINDOW)` で呼ぶ。`kilo` は npm shim（`kilo.cmd`）解決で cmd.exe を経由し、redirected handles だけでは console window を防げない（実測 2026-10-28: `管理者: cmd.exe` ウィンドウ生成）。`CREATE_NO_WINDOW` で生成しない（KI-20261028-01）
- 呼出し元がクローズで消えたセッションでも `kilo run --session` は resumed して delivery できる（transcript に追加）。バッチ→セッションの通信路はこれが唯一
- `kilo run --session` は target の応答ターンを待つ（blocking、worker 側 timeout 60s・best-effort）。target が busy だと message は届くが応答生成されず、タイムアウト失敗行になる。通知は target が idle の時に届く前提
- caller session ID は `/TR`（255 文字上限）に埋めずスクラッチファイル `docs/ai/tmp/vscode_relaunch_notify.txt` で受け渡す（KI-20261028-02。worker が読んだ後削除）

**使い方変更（2026-10-28）**:
- `--yes`（execute）は `start /b pythonw` 分離起動のため**コンソールに出力が出ない**。bat の終了コードは 0（即時 exit）で、結果はレポートファイル `docs/ai/tmp/vscode_relaunch_report.txt`（`entry:` 行＋worker 行）で読む
- Agent 経路の推奨: `cmd /c bat` を経由しない（中断時ツールラッパーのコンソールが孤児化し得る）。`pythonw maintenance/vscode_graceful_restart.py <cwd>` をシェル/background_process から直接。console app を経路に入れない（KI-20261028-01）
- 終了コードは従来どおり 0 成功 / 1 usage・ウィンドウなし / 2 失敗 / 3 非昇格・UIPI（直接呼出時に有効）
- `--self-test` のスクラッチ後始末は同一実装のまま cmd 経由をやめ `powershell -File maintenance/safe-rmdir.ps1` 直接呼出（`kilo-safe-rmdir.cmd` の実体。ゴミ箱送り）

**動作**（設計・2026-10-28 改訂）:
- エージェントの shell は Code.exe 子ツリー内 → バッチ内の直接再起動はクローズ時にツリー kill されうる。
- 回避: **タスクスケジューラの一発タスク `my-auto-blog\vscode-restart`** へ再起動委譲（`/Create` `/RL HIGHEST` ＋ 約5分バックストップ ＋ `/Run` 即時）。`/RL` なし（既定 Limited）では worker が非昇格トークンで Code.exe を起動し、再起動インスタンスが昇格しない。`/RL HIGHEST` の登録には昇格トークンが必要 → 非昇格シェルは exit 3。
- task action は `cmd /c` を経由せず `pythonw.exe`（GUI subsystem）を直接実行 → console app 経由しないのでコンソールウィンドウが出ない（`KI-20261028-01`）。pythonw がなければ `python.exe` へフォールバック。worker の出力はレポートファイルのみ（stdout なしでも例外を出さない）。
- bat の execute モード（`--yes`）は `start "" /b pythonw` 起動（cmd 即 exit・コンソールウィンドウ非生成。`KI-20261028-01` 実装・実測済み）。スクリプト側出力は `log()` 統一で、stdout 不可時はレポートファイル `docs/ai/tmp/vscode_relaunch_report.txt` へ追記。
- `/Run` は ONCE トリガーを消費しないためバックストップで再発動し得る。worker は attempt id（タスク TR に埋める）で `already_ran` を判定し、再実行は静かに exit 0。
- 対象は code.exe の**可視** Electron メインウィンドウのみ（クラス `Chrome_WidgetWin_1`）。不可視 helper（`Chrome_WidgetWin_0`）は WM_CLOSE で閉じないため除外。IME・crashpad 等は除外。
- 判定は `SendMessageW` の返り値では行わない（返り値は窓プロックの返り値で正常処理後も 0）。送信後の**ウィンドウ消失**で判定（最大 15 秒。ベストエフォート — 自分のウィンドウが閉じた瞬間に shell も殺される）。実際の再起動確認は worker（180 秒）。
- インテグリティチェック: ターゲットが実行シェルより高インテグリティなら UIPI が WM_CLOSE をフィルタする → 終了コード 3 で「昇格シェルで実行必須」を通知。
- `code` は PATH にない → `code.cmd` 全パスで **DETACHED_PROCESS(0x10)** 起動。単一インスタンス環境で新規ウィンドウを作るには `-n` が必要。

**呼び出しタイミング**: 手動（Agent / ユーザー）。

**副作用・注意**:
- 実行モードの端到端（実際のクローズ＋worker による再起動）は未検証。実行すると Agent 自分の VS Code が閉じる。
- Worker の結果は `docs/ai/tmp/vscode_relaunch_report.txt` へ追記（呼び出し元 shell は kill されるため通知口はここ）。
- ASCII のみ（cmd コードページ対応）。
- Worker は ~5 分待機後に再起動を確定し、自削除する。

**終了コード**（`vscode_graceful_restart.py`）: 0 成功 / 1 ウィンドウなし・usage / 2 失敗（ウィンドウが閉じない）/ 3 インテグリティ不一致（UIPI）またはシェル非昇格

**関連**:
- 設計: `docs/ai/decisions/2026-10-22-vscode-graceful-restart.md`（2026-10-28 改訂追記）
- テスト: `maintenance/tests/test_vscode_graceful_restart.py`（判定ロジック）。実ウィンドウ検証は `--self-test`（scratch は `kilo-safe-rmdir.cmd` でゴミ箱へ）

## 新規バッチの追加手順（将来）

1. `maintenance/` にバッチを実装（Python は標準ライブラリのみ・削除は `kilo-safe-*.cmd` へ委譲）。
2. 本ファイル「一覧」表に 1 行追加し、該当バッチのセクション（目的・実行方法・呼び出しタイミング・副作用・関連）を追加。
3. `docs/ai/architecture.md` の Development Tools 表に 1 行追加。
4. 関連テスト（あれば）を `maintenance/tests/` に追加し `pytest maintenance/tests/ -v` で確認。
5. 設計判断があれば `docs/ai/decisions/` に新ファイルを記録。
