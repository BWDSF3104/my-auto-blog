# pwsh 非ストア（MSI）版を msix 版に選択

**Date**: 2026-10-26

**Decision**: Kilo のシェル選択バグ（`docs/ai/known-issues/KI-20261026-03-kilo-pwsh-store-alias.md`）に対するワークアラウンド **B** を採用し、インストール済み msix pwsh 7.6.9.0 を退設し、classic MSI pwsh 7.6.9.0 を導入した。Kilo 設定 `kilo.jsonc` の `"shell": "pwsh"`（bare name）は維持。

**Reason**:
- Kilo/opencode のシェル選択（`packages/core/src/shell/select.ts`）は `which()` 候補に対し `fs.statSync().isFile()` を呼ぶ。msix 版の `%LOCALAPPDATA%\Microsoft\WindowsApps\pwsh.exe` は 0バイトリパースポイント（APPEXECLINK）で `statSync` が `EACCES` をthrown → `which("pwsh")` null → PowerShell 5.1 に静黙フォールバック。
- classic MSI 版は `C:\Program Files\PowerShell\7\pwsh.exe` に**実バイナリ**を置き、ReparsePoint ではない（`statSync` 成功）→ `which("pwsh")` が解決 → pwsh 7 が実効。
- MSI 版のインストール先 `C:\Program Files\PowerShell\7\` はバージョン更新でも安定（原地更新）。msix 版の WindowsApps ディレクトリ名（`7.6.9.0` 等）がバージョン依存で変わるのと違い、パス固定が必要なら破綻しない。
- winget の `Microsoft.PowerShell` は**classic MSI ではなく GitHub リリースの msixbundle**（`winget show`: Installer type = msix, `PowerShell-7.6.9.msixbundle`）。したがって classic MSI はリリース資産から直接取得し `msiexec` で導入した。
- PowerShell 5.1（OS組み込み）は対象外で intact を確認。

**Implementation**:
1. `winget uninstall Microsoft.PowerShell` → msix pwsh 7.6.9.0 退設（Appx 件数 0、`WindowsApps\pwsh.exe` Test-Path False）。
   - 教訓: 最初の `winget uninstall` → `winget install` で msix を再導入していた（winget 入力が msix だったため）。msix 退設は一度やり直し。
2. リリース資産 `PowerShell-7.6.9-win-x64.msi`（注: `PowerShell-7.6.9-x64.msi` は 404）を `docs/ai/tmp/` に取得、SHA256 `50D33C7494AAF82B987CFD4DE3F232D04F91FDD4C0DEECA8A669CCED3E7CF8F9` をリリースページと照合済み。
3. `msiexec /i .../PowerShell-7.6.9-win-x64.msi /qn`（マシンスコープ）でインストール。
4. 検証: `C:\Program Files\PowerShell\7\pwsh.exe` 実バイナリ（301,360 B、ReparsePoint=false）、`--version` → `PowerShell 7.6.9`、メンション PATH に `C:\Program Files\PowerShell\7\` 追加。

**Residual / Follow-up**:
- 実行中プロセス（Explorer/VS Code/Kilo）の env PATH は更新されない。bare `shell: "pwsh"` が PATH 経由で実効するにはログオフ/ログオン（または PC 再起動）が必要。
- **採用（2026-10-26、ユーザー指示: ログオフは避ける）**: `kilo.jsonc` に `"shell": "C:\Program Files\PowerShell\7\pwsh.exe"`（安定フルパス）を固定。MSI 版はパスが安定なので破綻しない。新 Kilo セッション（プロセス再スタート）から即効。Kilo 設定バリデーション + node 解析で検証済み。
- アップストリーム修正（opencode #55255 等、PR #48968 相当）は別で待つ。

**Alternatives**:
1. msix 版のバージョン付きフルパス固定（`C:\Program Files\WindowsApps\Microsoft.PowerShell_7.6.9.0_x64__8wekyb3d8bbwe\pwsh.exe`）— 即効だがストア自動更新でパスが破綻（関連 #56381）。
2. classic MSI 版の安定フルパスを `kilo.jsonc` に固定（上記 Residual）— ログオフ不要だが bare name 決定から逸脱。
3. アップストリーム修正を待つ — 未反映・時期不明。5.1（ANSI）環境が継続。

**Related**:
- 決定: `docs/ai/decisions/2026-10-26-global-shell-pwsh.md`（`shell: "pwsh"` 設定自体）
- タスク: `docs/ai/tasks/2026-10-26-global-shell-pwsh.md`
- 既知問題: `docs/ai/known-issues/KI-20261026-03-kilo-pwsh-store-alias.md`
