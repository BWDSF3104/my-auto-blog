# safe-*.cmd の削除を恒久削除から Windows ゴミ箱へ（VB ラッパー採用）

**Date**: 2026-10-18

**Decision**: `.kilo\scripts\safe-remove.ps1` / `safe-rmdir.ps1` の削除を `Remove-Item`（恒久削除）から **Windows ゴミ箱へ移動** に変更。実装は `[Microsoft.VisualBasic.FileIO.FileSystem]::DeleteFile` / `DeleteDirectory` を `RecycleOption::SendToRecycleBin` で呼び出す **VB ラッパー**（`Add-Type -AssemblyName Microsoft.VisualBasic`）。`kilo-safe-{remove,rmdir}.cmd` と `archive_memory_bank.py` の委譲ロジックは不変（変更は `.ps1` 2 ファイルのみ）。

**Reason**: 誤削除時の復旧余地を残すため。ユーザー確認済みの方針（2026-10-18）。

**VB ラッパー採用の根拠（SHFileOperation 不採用）**:
- 当初方針は `SHFileOperation`（`FO_DELETE`）P/Invoke + `FOF_NOAUTORECYCLE`（ゴミ箱容量超過時の静かな恒久削除フォールバックを明示排除）だった。
- しかし検証で `SHFileOperation` は**メッセージループのないコンソール PowerShell**（`powershell.exe` / `cmd.exe` 委譲）で**ディレクトリ削除が非決定的に失敗**することが判明:
  - エラーコード: 2=`FILE_NOT_FOUND` / 87=`INVALID_PARAMETER` / 124=`INVALID_LEVEL` / 170=`BUSY`。
  - `powershell.exe -Sta`（STA）でファイル削除は安定化（5/5）するが、ディレクトリは STA 前後変わらず失敗（4/4、ret=2）。末尾バックスラッシュも無効（0/3 vs 1/3）。
  - ドライブ比較: `S:`（Fixed/NTFS）2/5、`C:` 4/5。→ ドライブ依存ではなく呼び出し環境起因。
- 一方 VB ラッパーは **10/10 全成功**（ファイル 5 + ディレクトリ 5、STA 不要・末尾バックスラッシュ不要）。リトライ 3 試行・バックオフ（1s/2s/3s）を追加。対象が既に消失している場合は成功扱い。

**トレードオフ（許容）**:
- VB ラッパーは `FOF_NOAUTORECYCLE` を公開しないため、ゴミ箱容量超過時に**静かに恒久削除へフォールバックし得る**。これは既存の Windows 挙動であり、変更前の「常に恒久削除」からの**厳密な改善**（通常はゴミ箱へ、最悪で従来通り）。両 `.ps1` のコメントに明記済み。
- 超大きさ項目（ゴミ箱に収まらないもの）の静かな恒久削除リスクは、ゴミ箱の復元不能リスクと天秤にかけて許容（ユーザー方針: 復旧余地を残すのが主目的）。

**維持ガード**: `Test-InProject`、ReparsePoint 拒否、safe-remove=ファイルのみ / safe-rmdir=ディレクトリのみ・ルート拒否、`.git` / `.kilo` 保護 — 全て不変。メッセージ: safe-remove は「ゴミ箱に移動:」（日本語）、safe-rmdir は「Sent to Recycle Bin:」（英語）。
