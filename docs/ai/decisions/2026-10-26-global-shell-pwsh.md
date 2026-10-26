# Kilo グローバル設定で shell を pwsh に変更

**Date**: 2026-10-26

**Decision**: Kilo のグローバル設定 `C:\Users\fujim\.config\kilo\kilo.jsonc` に `shell: "pwsh"` を追加した。Kilo の bash（terminal/shell）ツールのシェルを、既定の Windows PowerShell 5.1（`powershell.EXE`, 5.1.19041.7725）から pwsh 7.6.9 へ変更した。変更前は `kilo.jsonc.bak-20261026` にバックアップ。

**Reason**: pwsh 7.6.9 は winget（msix, ユーザー単位）でインストール済みで PATH に存在（`C:\Users\fujim\AppData\Local\Microsoft\WindowsApps\pwsh.exe` shim）。pwsh の `Get-Content` は既定が `utf8NoBOM` であり、日本語の UTF-8 ファイルを ANSI(932) として読まないため、プラグインの `$PSDefaultParameterValues['Get-Content:Encoding']='UTF8'` 注入を不要にできる。設定スキーマ（`https://app.kilo.ai/config.json`）に `shell` キー（"Default shell to use for terminal and shell tool execution"）があり、グローバル上書きは正式にサポートされる。

**Alternative**: (1) プロジェクト設定（`.kilo/kilo.jsonc`）でのみ `shell` を指定 — 他プロジェクトへの影響を避けたい場合。(2) 既定 5.1 を維持しプラグイン注入を続ける — UTF-8 保証が弱く不望。
