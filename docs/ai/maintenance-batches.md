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
```

**動作**（設計）:
- エージェントの shell は Code.exe 子ツリー内 → バッチ内の直接再起動はクローズ時にツリー kill されうる。
- 回避: **タスクスケジューラの一発タスク `my-auto-blog\vscode-restart`** へ再起動委譲（`/Create` 約5分バックストップ ＋ `/Run` 即時）。
- 対象は code.exe の Electron メインウィンドウのみ（クラス `Chrome_WidgetWin_0/1`）。IME・crashpad・Electron 補助ウィンドウは除外。
- `code` は PATH にない → `code.cmd` 全パスで **DETACHED_PROCESS(0x10)** 起動。

**呼び出しタイミング**: 手動（Agent / ユーザー）。

**副作用・注意**:
- **実行モード（実際のクローズ＋再起動）は未検証**: 本セッションでは自分の VS Code を閉じるため実行不能。委譲 worker の端到端も未検証。
- ASCII のみ（cmd コードページ対応）。
- Worker は ~5 分待機後に再起動を確定し、自削除する。

**関連**:
- 設計: `docs/ai/decisions/2026-10-22-vscode-graceful-restart.md`
- テスト: 専用 pytest なし（`--self-test` モードが内蔵の検証）

## 新規バッチの追加手順（将来）

1. `maintenance/` にバッチを実装（Python は標準ライブラリのみ・削除は `kilo-safe-*.cmd` へ委譲）。
2. 本ファイル「一覧」表に 1 行追加し、該当バッチのセクション（目的・実行方法・呼び出しタイミング・副作用・関連）を追加。
3. `docs/ai/architecture.md` の Development Tools 表に 1 行追加。
4. 関連テスト（あれば）を `maintenance/tests/` に追加し `pytest maintenance/tests/ -v` で確認。
5. 設計判断があれば `docs/ai/decisions/` に新ファイルを記録。
