# pwsh 7 導入・プラグインバックアップ・プラグイン修正設計提示

**Status**: 完了
**Date**: 2026-10-26
**Backlog**: なし
**Next Action**: pwsh 7 導入実行 → 完了（設計提示はチャットで提示済み。実装は未着手）

## 意図 / 背景

ユーザー指示 (2026-10-26):
1. pwsh (PowerShell 7) を導入する
2. プラグインバックアップを取得し、プラグイン修正の**設計提示のみ**（実装しない）

前段階: プロジェクト内影響調査（`2026-10-26-kilo-utf8-project-impact`, 完了）で
- プラグイン注入の Get-Content 部分はプロジェクト内で依存なし → 削除可
- pwsh 7 導入は 5.1 非破壊（.cmd ラッパーは 5.1 専用に固定）
と判断していた。本タスクはその導入実施 + 修正設計の提示。

## 調査結果 / 変更内容

### pwsh 7 導入（実施済み）

- `winget install --id Microsoft.PowerShell --silent` → **PowerShell 7.6.9.0** 導入（msix, 2026-10-25 リリース）
- 設置: MSIX パッケージ（per-user）。shim: `C:\Users\fujim\AppData\Local\Microsoft\WindowsApps\pwsh.exe`
  - 実体: `C:\Program Files\WindowsApps\Microsoft.PowerShell_7.6.9.0_x64__8wekyb3d8bbwe\pwsh.exe`
- 現行セッション（5.1）は不変。新 Kilo セッションは `which("pwsh")` により pwsh へ
- `powershell.exe` (5.1.19041.7725) は別設置場所 → 影響なし

### バックアップ（実施済み）

- `C:\Users\fujim\.config\kilo\plugin\powershell-utf8.js.2026-10-26.bak` に現行プラグイン（v2）をコピー
- 復元: このファイルを元名にコピー

### プラグイン修正設計（提示のみ・未実施）

**方針**: Kilo シェルが pwsh 7 になった以上、コマンド注入は不要。プラグインは `shell.env`（Python 用）のみへ最小化。

**削除**:
- `tool.execute.before` の注入（`[Console]::InputEncoding/[OutputEncoding]/$OutputEncoding` 設定、`$PSDefaultParameterValues['Get-Content:Encoding']='UTF8'`、PLUGIN_MARKER・再挿入ガード）
  - コンソール設定: Kilo 内蔵層（`@opencode-ai/core/kilocode/powershell`）+ pwsh 7 既定 (utf8NoBOM) でカバー
  - Get-Content 指定: pwsh 7 の Get-Content 既定が utf8NoBOM（本セッションで検証）

**保持**:
- `shell.env`: `PYTHONIOENCODING=utf-8`, `PYTHONUTF8=1`（Python 3.10.8 現行。PEP 686 未導入のため pytest/ad-hoc python の cp932 フォールバック対策として継続必要。Python 3.15 移行後に不要化 — `2026-10-14-python315-upgrade.md`）

**適用後のプラグイン（案）**:
```js
const PowerShellUtf8 = async () => {
  return {
    "shell.env": async (_input, output) => {
      if (process.platform !== "win32") return;
      output.env.PYTHONIOENCODING = "utf-8";
      output.env.PYTHONUTF8 = "1";
    },
  };
};
export default {
  id: "powershell-utf8",
  server: PowerShellUtf8,
};
```

**変更しない**: AGENTS.md ルール、.cmd/.ps1、`docs/ai/workflow-test-procedure.md`、Python 3.10.8 現状

### 検証計画（実装時）

1. 新 Kilo セッション: シェル = pwsh 7.x（`$PSVersionTable.PSVersion`）
2. スクラッチ ps1 で Get-Content（BOM なし UTF-8 日本語ファイル）→ 正常
3. `pytest scripts/tests/ -v` + `pytest maintenance/tests/ -v`
4. `npm run build`
5. `kilo-safe-remove.cmd` / `kilo-safe-rmdir.cmd` スモーク（5.1 経路不変）

**ロールバック**: `Copy-Item powershell-utf8.js.2026-10-26.bak` → 元名（または `.user-v2.bak`）

## Verification

- `winget list --id Microsoft.PowerShell` → PowerShell 7.6.9.0 導入済み
- `pwsh -NoLogo -NoProfile -File docs\ai\tmp\verify_pwsh.ps1` → PS 7.6.9、プロセス `...\WindowsApps\...\pwsh.exe`、`Get-Content` で `docs\ai\workflow-test-procedure.md` の日本語 1 行目を正常読取（BOM なし UTF-8 ファイル → 既定 utf8NoBOM を実証）
- `python --version` → 3.10.8（不変）
- Backup: `Test-Path powershell-utf8.js.2026-10-26.bak` = True
- 本タスクはプラグイン本体変更なし（設計提示のみ）

## 完了時 Memory Bank 操作

- [ ] `current-task.tsv` の参照行を削除
- [ ] `known-issues/` ファイルの archive 移動（該当なし）
- [ ] `backlog.md` の完了項目削除（該当なし）
