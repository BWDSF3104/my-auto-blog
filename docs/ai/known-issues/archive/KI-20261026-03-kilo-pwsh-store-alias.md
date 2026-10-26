# Kilo/opencode のシェル選択がストア版 pwsh エイリアスを解決できず、PowerShell 5.1 に静黙フォールバック（アップストリームバグ）

**Date**: 2026-10-26
**状態**: 解決済み（2026-10-26、ワークアラウンド B + 安定フルパス固定） — msix 退設、非ストア MSI pwsh 7.6.9 導入、`kilo.jsonc` に `C:\Program Files\PowerShell\7\pwsh.exe` 固定（ログオフ不要）。VS Code 再起動後の新 Kilo セッションで実効確認: pwsh 7.6.9 / 実バイナリ。アップストリーム修正（opencode #55255 等）は別問題として未反映

## 確認した事実

- `C:\Users\fujim\.config\kilo\kilo.jsonc` に `"shell": "pwsh"` を設定。再起動（kilo プロセス再スタート 19:27:52、設定再読み込み）後も、Kilo の bash ツールのシェルは `C:\Windows\System32\WindowsPowerShell\v1.0\powershell.EXE`（5.1.19041.7725）のままである。
- 実行中の Kilo は VS Code 拡張のバンドル `kilo.exe`（v7.8.17）: `c:\Users\fujim\.vscode\extensions\kilocode.kilo-code-7.8.17-win32-x64\bin\kilo.exe serve --port 0`。
- 根本原因（Kilo は opencode の派生。関連 issue: **#55255**、#41426、#30615、#17372。修正 PR **#48968** はクローズ（stale 削除）済みで未反映）:
  - Kilo のシェル選択（`packages/core/src/shell/select.ts`）は bare name を Node の `which()`（which@2.0.2 → isexe）で解決する。
  - `which()` は PATH 候補に対し `fs.statSync(candidate).isFile()` を呼ぶ。
  - winget 入力の pwsh 7.6.9 は **Microsoft Store（msix）** アプリ。その `pwsh.exe` は `%LOCALAPPDATA%\Microsoft\WindowsApps\pwsh.exe` の **0バイトリパースポイント（APPEXECLINK エイリアス）** であり実ファイルでない。
  - `fs.statSync()` はそのリパースポイントに対して **`EACCES`** を thrown → `which("pwsh")` → null → `select()` が `win()[0]` = `C:\Windows\System32\WindowsPowerShell\v1.0\powershell.EXE`（5.1）に**警告なし**にフォールバック。
  - 設定 `"shell": "pwsh"` も同一 `select()` パスを通るため無効。
- 本機確認:
  - 非ストア位置 `C:\Program Files\PowerShell\7\pwsh.exe`: **不存在**（非ストア版未インストール）。
  - 導入済み pwsh はストア版のみ（winget `Microsoft.PowerShell 7.6.9.0`）。
  - `%LOCALAPPDATA%\Microsoft\WindowsApps\pwsh.exe`: `ReparsePoint = true`（実証）。
  - `C:\Program Files\WindowsApps\Microsoft.PowerShell_7.6.9.0_x64__8wekyb3d8bbwe\pwsh.exe`: 存在・**実ファイル**（ReparsePoint=false、stat 成功）。
- 副次観察: 別のコードパスでは EACCES が `SessionModelRequest.prepare` に伝播しセッションステップを crash させうる（#55255 コメント）。本機では「静黙 5.1 フォールバック」。

## 影響

- Kilo の bash（コマンド実行）が PowerShell 5.1（ANSI 932）で動作。7.x 要件コマンド（例: `&&`）が ParserError。
- プラグインの Get-Content 注入を不要にするという目的が未達成（5.1 が使われ続ける）。
- 設定変更では解消不能（upstream バグ）。

## 対応の方向性（未着手・ユーザー判定待ち）

- **ワークアラウンド A（即時、issue コメントで動作検証済み）**: `shell` をバージョン付き実バイナリに固定。
  `C:\Program Files\WindowsApps\Microsoft.PowerShell_7.6.9.0_x64__8wekyb3d8bbwe\pwsh.exe`
  - 即刻に動作（実ファイルなので stat 成功）。
  - **欠点**: ストア自動更新でディレクトリ名（`7.6.9.0` 等）が変化 → 固定パスが破滅し、再固定が必要（関連 #56381）。
- **ワークアラウンド B（推奨・持続）**: pwsh を**非ストア（MSI）版**でインストール → 実ファイル `C:\Program Files\PowerShell\7\pwsh.exe` を PATH 上に配置 → `shell: "pwsh"`（bare）が `which()` 経由で解決 → pwsh 7。更新でも `C:\Program Files\PowerShell\7\` は安定（原地更新）。
  - 最大限の清浄性のため、ストア版（リパースポイント）を退設し PATH から除外するのが望ましい。
- **アップストリーム**: `select()` が APPEXECLINK リパースポイントを受け入れ、または `where.exe`/SearchPath にフォールバックする修正（#48968 相当）が必要。上流リリースを待つ。

### 対応進捗（2026-10-26、ワークアラウンド B）

- `winget uninstall Microsoft.PowerShell` で msix pwsh 7.6.9.0 を退設（Appx 件数 0、`%LOCALAPPDATA%\Microsoft\WindowsApps\pwsh.exe` は Test-Path False）。
  - 教訓: winget の `Microsoft.PowerShell` は GitHub リリースの msixbundle（classic MSI ではない）。最初の `winget install` で msix が再導入されていたため、msix 退設を一度やり直し。
- classic MSI: リリース資産 `PowerShell-7.6.9-win-x64.msi` を `docs/ai/tmp/` に取得（SHA256 照合）、`msiexec /i ... /qn` で導入。
- 検証:
  - `C:\Program Files\PowerShell\7\pwsh.exe`: 実バイナリ（301,360 B、ReparsePoint=false）、`--version` → `PowerShell 7.6.9`。
  - メンション PATH に `C:\Program Files\PowerShell\7\` 追加。5.1（`powershell.exe`）は intact。
- 実効条件: 実行中プロセスの env PATH は更新されないため、bare `shell: "pwsh"` が PATH 経由で実効するには**ログオフ/ログオン（または PC 再起動）** が必要。
- **採用（2026-10-26、ユーザー指示: ログオフは避ける）**: `kilo.jsonc` に `"shell": "C:\Program Files\PowerShell\7\pwsh.exe"`（安定フルパス）を固定 — **ログオフ不要**。新 Kilo セッション（プロセス再スタート）から即効。Kilo 設定バリデーション + node 解析で検証済み。
- 上流修正（#55255 等）は別で待つ。

## 関連

- 上流: https://github.com/anomalyco/opencode/issues/55255（#41426 / #30615 / #17372、PR #48968）
- タスク: `docs/ai/tasks/2026-10-26-global-shell-pwsh.md`
- 決定: `docs/ai/decisions/2026-10-26-global-shell-pwsh.md`
- 設定: `C:\Users\fujim\.config\kilo\kilo.jsonc`（`"shell": "pwsh"`、バックアップ `.bak-20261026`）
- 関連: `KI-20261026-02`（VS Code 再起動、別問題）
