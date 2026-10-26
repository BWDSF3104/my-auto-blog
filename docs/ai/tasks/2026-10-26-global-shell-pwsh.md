# Kiloグローバル設定: shell を pwsh に指定

**Status**: 完了
**Date**: 2026-10-26
**Next Action**: 新 Kilo セッション（プロセス再スタート）で `($PSVersionTable.PSVersion.ToString(); (Get-Process -Id $PID).Path)` が 7.6.9 / `pwsh.exe` を返すことを確認（ワークアラウンド B + 安定フルパス固定実施済み、ログオフ不要）

## 意図 / 背景

Kilo Code のシェル（bash ツール）を、既定の Windows PowerShell 5.1（`powershell.EXE`、5.1.19041.7725）から pwsh（PowerShell 7）へ切り替える。日本語の UTF-8 ファイルを Kilo が処理する際に Get-Content が ANSI(932) として読まないよう pwsh の utf8NoBOM 既定値を頼り、プラグインの `$PSDefaultParameterValues['Get-Content:Encoding']='UTF8'` 注入を不要にする。ユーザーの「グローバル設定で上書き可能ならそれでよい」の指示を受け、グローバル設定に適用した。

## 調査結果 / 変更内容

- Kilo の設定スキーマ（`https://app.kilo.ai/config.json`）に `shell` キー（"Default shell to use for terminal and shell tool execution"、type string）が存在し、グローバル上書きが正式にサポートされることを確認。
- 変更前のグローバル設定 `C:\Users\fujim\.config\kilo\kilo.jsonc` に `shell` キーが無く、Kilo は既定の PowerShell 5.1 を使用（現在のセッションは 5.1.19041.7725 / `powershell.EXE`）。
- pwsh 7.6.9 は winget（msix、ユーザー単位）でインストール済み。PATH 上は `C:\Users\fujim\AppData\Local\Microsoft\WindowsApps\pwsh.exe`（shim）で解決（`Get-Command pwsh` で確認）。
- 変更前にバックアップ作成: `C:\Users\fujim\.config\kilo\kilo.jsonc` → `kilo.jsonc.bak-20261026`（319 行）。
- 変更: `kilo.jsonc` の `$schema` 行（1 行目）の直後、2 行目へ `"shell": "pwsh",` を追加。
- 決定: グローバル設定で `shell: "pwsh"`。`shell` 値は PATH 解決できる `pwsh` を指定（フルパスは更新時に脆弱）。

### バロック原因（2026-10-26 追記: 再起動後も shell=5.1 確認）

- 再起動後も shell が 5.1 になることを実証。**原因は設定ではなく Kilo/opencode の既知アップストリームバグ**（GitHub **#55255**、関連 #41426/#30615/#17372。修正 PR #48968 はクローズ済み・未反映）。
- 機理: Kilo のシェル選択（`packages/core/src/shell/select.ts`）は bare name を Node の `which()`/`isexe` で解決し、PATH 候補に対し `fs.statSync().isFile()` を呼ぶ。winget 入力の pwsh は **Microsoft Store(msix) アプリ**であり、PATH 上の `pwsh.exe`（`%LOCALAPPDATA%\Microsoft\WindowsApps\pwsh.exe`）は **0バイトのリパースポイント（APPEXECLINK エイリアス）**。`fs.statSync()` は EACCES を thrown → `which("pwsh")` null → `select()` が `C:\Windows\System32\WindowsPowerShell\v1.0\powershell.EXE`（5.1）に**警告なしフォールバック**。「`shell: pwsh`」も同一経路のため無効。
- 本機確認: 非ストア位置 `C:\Program Files\PowerShell\7\pwsh.exe` 不存在（非ストア版未導入）。`WindowsApps\pwsh.exe` は `ReparsePoint=true`。一方、バージョン付き実バイナリ `C:\Program Files\WindowsApps\Microsoft.PowerShell_7.6.9.0_x64__8wekyb3d8bbwe\pwsh.exe` は実ファイル（ReparsePoint=false、stat 成功）。
- 実行中の Kilo は VS Code 拡張バンドル `kilo.exe`（v7.8.17）`serve --port 0`。プロセス再スタート（19:27:52）で設定は再読み込み済み。

### 決定: B（非ストア/MSI pwsh 導入）— 2026-10-26 実施（ユーザー確認）

- ユーザー確認: 「インストール済のストア版 pwsh は不要なら削除 / 必要な方をインストールしたい」→ msix 版を削除し classic MSI 版を導入。
- **教訓**: winget の `Microsoft.PowerShell` カタログ項目は **classic MSI ではなく GitHub リリースの `msixbundle`**（`winget show` で確認、msix bundle URL）。最初の `winget uninstall` → `winget install` は同じ msix 版を再インストールしていた → 改めて msix 版を退設。
- classic MSI はリリース資産 `PowerShell-7.6.9-win-x64.msi`（注意: `PowerShell-7.6.9-x64.msi` は 404）を `docs/ai/tmp/` へ取得、SHA256 をリリースページと照合: `50D33C7494AAF82B987CFD4DE3F232D04F91FDD4C0DEECA8A669CCED3E7CF8F9`。
- `msiexec /i .../PowerShell-7.6.9-win-x64.msi /qn`（マシンスコープ）でインストール。
- **5.1 は intact（ユーザー質問への回答）**: `C:\WINDOWS\System32\WindowsPowerShell\v1.0\powershell.exe`（10.0.19041.3996）がそのまま存在。退設したのは msix pwsh 7.6.9.0 のみ。
- 新検証:
  - msix 退設: `Get-AppxPackage`（PowerShell）件数 0、`Test-Path %LOCALAPPDATA%\Microsoft\WindowsApps\pwsh.exe` → `False`（shim 消滅）。
  - `C:\Program Files\PowerShell\7\pwsh.exe`: 301,360 B、`ReparsePoint=false`（実バイナリ、shim ではない）。
  - `& "C:\Program Files\PowerShell\7\pwsh.exe" --version` → `PowerShell 7.6.9`。
  - メンション PATH（`HKLM:\SYSTEM\CurrentControlSet\Control\Session Manager\Environment`）に `C:\Program Files\PowerShell\7\` が加算。
  - 上記「バロック原因」中の「非ストア位置 `C:\Program Files\PowerShell\7\pwsh.exe`: 不存在」は本実施で上書き。
- 未了: 実行中の Kilo プロセスの env PATH は再読み込みされない（プロセス起動時確定）。マシン PATH 変更は既存プロセス（Explorer/VS Code/Kilo）には反映されず、**ログオフ/ログオン（または PC 再起動）** が必要。
- **採用（ユーザー指示: ログオフは避ける）**: `kilo.jsonc` の `"shell"` を安定フルパス `"C:\Program Files\PowerShell\7\pwsh.exe"` に固定。MSI 版はバージョン更新でも `C:\Program Files\PowerShell\7\` が固定（msix の WindowsApps ディレクトリ名がバージョン依存で変わるのと違い、**破綻しない**）。次セッションで即効。
  - 変更: `kilo.jsonc` 3 行目 `"shell": "pwsh",` → `"shell": "C:\Program Files\PowerShell\7\pwsh.exe",`
  - 検証: Kilo 設定バリデーション OK + node 解析 OK（`parses OK; shell = C:\Program Files\PowerShell\7\pwsh.exe`）

## Verification

- node で JSON 解析: `parses OK; shell = "pwsh"`（エラーなし）。
- Kilo の設定バリデーション: 編集時に "Config file validated successfully."（エラーなし）。
- 再起動後確認: `($PSVersionTable.PSVersion.ToString(); (Get-Process -Id $PID).Path)` → **5.1.19041.7725 / `powershell.EXE`**（**期待外: pwsh 未反映**）。上記バロック原因により設定無効。
- pwsh 実効の確認は、ワークアラウンド適用後に新セッションで行う（同上コマンドで `7.6.9` / `pwsh.exe` を要）。
- 非ストア MSI 版検証（2026-10-26）: SHA256 一致。`C:\Program Files\PowerShell\7\pwsh.exe` 実バイナリ（301,360 B, ReparsePoint=false）、`--version` → `PowerShell 7.6.9`。msix 版退設（Appx 0, `WindowsApps\pwsh.exe` is Test-Path False）。メンション PATH に `C:\Program Files\PowerShell\7\` 追加。
- 5.1 intact: `C:\WINDOWS\System32\WindowsPowerShell\v1.0\powershell.exe`（10.0.19041.3996）確認。
- `kilo.jsonc` 安定フルパス固定（2026-10-26, ログオフ回避）: Kilo 設定バリデーション OK + node 解析 OK（`parses OK; shell = C:\Program Files\PowerShell\7\pwsh.exe`）。

## 完了時 Memory Bank 操作

- [ ] `current-task.tsv` の参照行を削除（保留中は保持）
- [ ] 解決した `known-issues/` ファイルを `known-issues/archive/` へ `mv`（該当する場合）
- [ ] `backlog.md` の完了項目を削除（該当する場合）

## 関連

- 既知問題（解決済み・アーカイブ）: `docs/ai/known-issues/archive/KI-20261026-03-kilo-pwsh-store-alias.md`
- 決定: `docs/ai/decisions/2026-10-26-global-shell-pwsh.md`
- 決定: `docs/ai/decisions/2026-10-26-pwsh-classic-mix.md`（非ストア MSI 採用）
- 設定: `C:\Users\fujim\.config\kilo\kilo.jsonc`（`"shell": "pwsh"`、バックアップ `.bak-20261026`）
