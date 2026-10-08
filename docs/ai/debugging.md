# デバッグ（DebugMCP）

VS Code のデバッガを Kilo Code から MCP ツール（`debugmcp_*`）経由で制御する方法。
ブレークポイント・ステップ・変数確認・式評価を実際に動作検証済み（2026-10-08）。

## 用途

- Python スクリプト（`scripts/`）のランタイムバグ調査
- 変数値の確認、関数内部のトレース、条件分岐の追跡
- テストが通らない・出力が想定違いの場合の根本原因（WHY）の特定

## 前提条件（セットアップ済み）

| 項目 | 値 |
|------|-----|
| 拡張機能 | `ozzafar.debugmcpextension` v2.4.3 |
| MCP サーバー | `.kilo/kilo.jsonc` → `debugmcp`（remote, `http://127.0.0.1:3001/mcp`） |
| 権限 | `.kilo/kilo.jsonc` → `debugmcp_*: allow`（自動承認） |
| Launch 構成 | `.vscode/launch.json` → `"Debug Python (DebugMCP)"`（type `debugpy`, `program: ${file}`） |

- MCP サーバーは VS Code（Code プロセス）内で起動。ポート 3001。
- **重要**: `start_debugging` は必ず `configurationName: "Debug Python (DebugMCP)"` を指定する（「注意点 1」の根本原因）。

## ツール一覧（17件）

| ツール | 主な引数 | 用途 |
|--------|---------|------|
| `start_debugging` | `fileFullPath`, `workingDirectory`, `configurationName` | 起動 |
| `stop_debugging` | — | 終了 |
| `restart_debugging` | — | 再開始 |
| `continue_execution` | — | 実行再開（次の BP まで） |
| `pause_execution` | — | 実行中の割り込み |
| `step_over` | — | 1 行実行（関数には入らない） |
| `step_into` | — | 関数内部に入る |
| `step_out` | — | 関数から戻る |
| `add_breakpoint` | `fileFullPath`, `line`, 任意 `condition` | BP 設定 |
| `add_logpoint` | `fileFullPath`, `line`, `logMessage`, 任意 `condition` | 停止せず `{変数}` を埋めてログ出力 |
| `remove_breakpoint` | `fileFullPath`, `line` | BP 削除 |
| `clear_all_breakpoints` | — | BP 全削除 |
| `list_breakpoints` | — | BP 一覧 |
| `list_variable_names` | `scope`（`local`/`global`/`all`） | スコープ内変数名のみ |
| `get_variables_values` | `variableNames`（配列）, `scope` | 指定変数の値 |
| `evaluate_expression` | `expression` | 任意の式を実行時評価（最も強力・確実） |
| `get_debug_status` | 任意 `waitForPauseSeconds` | 状態確認（`paused`/`running`/`no-session`）、BP 到達をブロック待ち |

## 基本手順（ベストプラクティス）

**ブレークポイント方式でデバッグする**（実行系・割り込み方式は制約がある、後述）。

1. **ファイルをエディタで開く**: `code <file>`（launch 構成の `${file}` がアクティブエディタを指すため）。
2. **BP 設定**: `add_breakpoint`（停止したい行）。
3. **起動**: `start_debugging`（`configurationName: "Debug Python (DebugMCP)"`）。BP 到達で停止するまで数秒待機。
4. **状態確認**: `get_debug_status` で `paused` と停止行を確認。
5. **変数/式の確認**: `evaluate_expression`（確実）または `get_variables_values`。
6. **ステップ**: `step_over` / `step_into` / `step_out` で追跡。
7. **終了**: `continue_execution`（完走）または `stop_debugging`。`clear_all_breakpoints` で BP を片付ける。

### 例（`add`/`main` 関数、2026-10-08 実測）

```
add_breakpoint(line=7)
start_debugging(configurationName="Debug Python (DebugMCP)")   → paused @ main:7
evaluate_expression("__name__")                                 → '__main__'
evaluate_expression("add(20, 22)")                              → 42        # 実関数を呼び出し
step_over                                                       → main:8
get_variables_values(["x"], local)                              → x: 10 (int)
step_over                                                       → main:9   # total = add(x, y)
step_into                                                       → add:2    # a=10, b=32
step_out                                                        → main:9
continue_execution                                              → 完走 (no-session)
```

## 注意点・既知の制約

1. **`configurationName` は必須（根本原因）**
   - DebugMCP の自動構成は `.py` → type `python` にマップするが、登録済みアダプタは `debugpy` のみ。
   - 旧 `ms-python.python` 拡張が破損（`package.json` 欠落）のため type `python` は未登録。
   - 無指定で `start_debugging` すると type `python` で失敗する → 必ず `"Debug Python (DebugMCP)"` を指定。
2. **Kilo クライアントの 60 秒タイムアウト（`-32001`）**
   - BP なしの実行系プログラムでは `start_debugging` が「停止到達待ち」のため、クライアントが約 60 秒で `-32001` を返す（サーバーは 300 秒待ち）。
   - ただし**セッションはバックグラウンドで起動済み**。直後の `get_debug_status` → `pause_execution` で操作可能。
   - 回避: 常に BP を置いてから `start_debugging`（数秒で解決）。
3. **`pause_execution`（割り込み）後の制約**
   - 割り込み自体は成功（`paused: true`）するが、直後は「No active stack frame」で変数/式評価が不可。
   - C ブロッキング呼び出し（`time.sleep` 等）中に割り込むと特に顕著。純 Python ループでも同様。
   - ブレークポイント到達時は正常（スタック・変数・式すべて読取可）→ **BP 方式を推奨**。
4. **`step_out` 直後のローカル**
   - 関数呼び出し行（例: `total = add(x, y)`）で `step_out` 後、`total` はまだ代入未コミット（NameError）。戻り値は `__pydevd_ret_val_dict['add']` に一時保持。次の `step_over` で確定。
5. **変数ツリーの構造**
   - `list_variable_names` の global は `special variables` / `function variables` のグループ表示になる。
   - 個別値の読み取りは `get_variables_values`（変数名指定）または `evaluate_expression` が確実。
6. **タイムアウト**
   - DebugMCP 内部 300 秒（`debugmcp.timeoutInSeconds`）、toolBackstopMs 330 秒。
   - Kilo MCP の `timeout: 360000`（360 秒）は次回以降のセッションから適用。実操作は 10 秒未満のため既定値でも問題なし。
7. **ファイル変更後の再デバッグ**
   - `restart_debugging` は BP の再読み込みに注意。`clear_all_breakpoints` + 再設定が安全。

## よくある失敗と対処

| 症状 | 原因 | 対処 |
|------|------|------|
| `start_debugging` が type 未登録エラー | 自動構成が type `python` を使用 | `configurationName: "Debug Python (DebugMCP)"` を指定 |
| `-32001 Request timed out`（start） | BP なしの実行系待ち | `get_debug_status` で実行確認 → 操作。または BP を先に置く |
| `No active stack frame` | `pause_execution` 後の割り込み | BP 方式に変更（BP/step で停止する） |
| 式評価で NameError（step_out 直後） | ローカル未コミット | `step_over` を 1 回 → 再評価 |
| 変数が見つからない（global） | グループ表示 | `evaluate_expression` で直接評価 |

## DebugMCP の「ROOT CAUSE ANALYSIS CHECKPOINT」について

`stop_debugging` 時に「ROOT CAUSE ANALYSIS CHECKPOINT」が表示されることがある。これは**バグデバッグ**（症状→原因の特定）を促す案内で、`add_breakpoint` → `start_debugging` → 原因追跡 の再実行を勧めている。機能検証・動作確認のみで終わる場合は無視して問題ない。
