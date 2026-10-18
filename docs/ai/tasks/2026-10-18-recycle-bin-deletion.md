# アーカイブスクリプトの削除と安全削除コマンドでゴミ箱を使う

**Status**: 完了
**Date**: 2026-10-18

## 意図 / 背景

- `maintenance/archive_memory_bank.py` の自動削除と、`kilo-safe-remove.cmd` / `kilo-safe-rmdir.cmd` の削除を、恒久削除（`Remove-Item`）ではなく Windows ゴミ箱経由に行うように変更する。
- 誤削除時の復旧余地を残すため。ユーザー確認済みの方針（2026-10-18）。
- 制約: 破壊的コマンド禁止・テストはテスト専用ファイル/フォルダのみで実施（実際に使用している・削除してはならないファイル/フォルダを触らない）。

## 調査結果 / 変更内容

### 削除経路（調査結果）

- アーカイブスクリプト（`archive_memory_bank.py` L223-225）は `cmd.exe /c <root>\kilo-safe-{remove,rmdir}.cmd <相対パス>` で委譲。`.cmd` は `.kilo\scripts\safe-{remove,rmdir}.ps1` を実行する薄いラッパー。
- 恒久削除の本体は `.ps1` 内の `Remove-Item` のみ（safe-remove L93 `-Force`、safe-rmdir L97 `-Recurse -Force`）。**`.ps1` 2 ファイルの変更だけで両要件を満たす**（`.cmd`・アーカイブスクリプトのロジックは不変）。

### 実装方針（選定・確定）

- `.ps1` 内で **VB ラッパー**（`Add-Type -AssemblyName Microsoft.VisualBasic`）により `[Microsoft.VisualBasic.FileIO.FileSystem]::DeleteFile` / `DeleteDirectory` を `RecycleOption::SendToRecycleBin` で呼び出し、ゴミ箱削除を実装。リトライ 3 試行・バックオフ（1s/2s/3s）、対象消失時は成功扱い。
- **方針転向（SHFileOperation → VB ラッパー）**: 当初は `SHFileOperation`（`FO_DELETE`）P/Invoke + `FOF_NOAUTORECYCLE` を予定したが、検証で**メッセージループのないコンソール PowerShell**（`powershell.exe` / `cmd.exe` 委譲）で**ディレクトリ削除が非決定的に失敗**することが判明したため VB ラッパーへ転向した。
  - SHFileOperation の失敗: エラーコード 2=`FILE_NOT_FOUND` / 87=`INVALID_PARAMETER` / 124=`INVALID_LEVEL` / 170=`BUSY`。`-Sta` でファイルは安定化（5/5）するがディレクトリは STA 前後問わず失敗（4/4、ret=2）。末尾バックスラッシュも無効。ドライブ比較 `S:` 2/5 / `C:` 4/5（環境起因）。
  - VB ラッパー: **10/10 全成功**（ファイル 5 + ディレクトリ 5、STA 不要）。
- **トレードオフ（許容）**: VB ラッパーは `FOF_NOAUTORECYCLE` を公開しないため、ゴミ箱容量超過時に静かに恒久削除へフォールバックし得る。既存 Windows 挙動であり、変更前の「常に恒久削除」からの厳密な改善。
- 不採用案: `SHFileOperation` P/Invoke（上記の非決定性）。`send2trash` 等（新依存）。
- 既存ガード（`Test-InProject`、ReparsePoint 拒否、safe-remove=ファイルのみ / safe-rmdir=ディレクトリのみ・ルート拒否、`.git`/`.kilo` 保護）は全て維持。メッセージは `削除:` → `ゴミ箱に移動:`（safe-remove・日本語）、`Deleted:` → `Sent to Recycle Bin:`（safe-rmdir・英語）。
- 環境確認: `S:` ドライブは Fixed/NTFS（ラベル `SUBHDD`）でゴミ箱動作に問題なし。ゴミ箱先 `S:\$Recycle.Bin\<SID>\`（`$I*` メタデータに元パスが UTF-16 で格納）。詳細は `docs/ai/decisions/2026-10-18-recycle-bin-deletion.md`。

### テスト方針（ユーザー制約: テスト専用ファイル/フォルダのみ）

- 実施場所: `test-results/recycle-bin-test/`（`.gitignore` L42 で gitignore 済み）。実際の `docs/ai/tmp/`・`verification/`・`tasks/`・`.git`・`.kilo` は一切触らない。
- 統合テストは偽ルート `test-results/recycle-bin-test/fake-root/`（`.cmd` + `.kilo/scripts/*.ps1` のコピー + ダミー `docs/ai/{tasks,verification,tmp,current-task.tsv}`）で `python maintenance/archive_memory_bank.py --root <fake-root> --apply --no-git-add`。
- 手順: (a) ダミーファイルを safe-remove → ゴミ箱 `S:\$Recycle.Bin\<SID>\` の `$I` メタデータで元パスを確認、(b) ダミーフォルダを safe-rmdir → 同確認、(c) ガード拒否（非存在パス / ファイル→rmdir / フォルダ→remove / プロジェクト外 / `.kilo` 保護パス → 全 exit 1 かつ対象無傷）、(d) 偽ルート統合テスト（tmp/ 旧エントリ + verification/ 旧 run がゴミ箱化）、(e) pytest 両方。最後にテスト木を `kilo-safe-rmdir.cmd` 自身で片付ける（dogfooding）。

### 発見した既存問題（本タスクでは修正せず known-issues/ に記録のみ）

- `--apply` + tmp/ 削除の場合、末尾の `git add -- docs/ai/tmp/<entry>` が gitignore 対象（`.gitignore` L34 `tmp/` が全レベル一致、`git check-ignore -v` で確認済み）のため失敗し、削除成功してもスクリプトが exit 1 になる。→ 記録済み: `docs/ai/known-issues/KI-20261018-01-archive-git-add-gitignore.md`

## Verification

- (a) ファイル削除: `kilo-safe-remove.cmd` でダミーファイル削除 → exit 0、ゴミ箱 `S:\$Recycle.Bin\<SID>\` の `$I` メタデータに元パス確認、元パス消失。PASS
- (b) ディレクトリ削除: `kilo-safe-rmdir.cmd` でダミーフォルダ削除 → exit 0、ゴミ箱 `$I` に元パス確認、元パス消失。PASS
- (c) ガード拒否 5 種（非存在パス / ファイル→rmdir / フォルダ→remove / プロジェクト外 / `.kilo` 保護）: 全 5 種 exit 1 かつ対象無傷（9 チェック全 PASS、`docs/ai/tmp/guard_test.ps1`）。PASS
- (d) 偽ルート統合: `python maintenance/archive_memory_bank.py --root test-results\recycle-bin-test\fake-root --apply --no-git-add` → 4 アクション（1 mv + 3 ゴミ箱削除）全成功・0 エラー。run-1 削除（run-2/3 保持）・tmp 2 エントリ削除・タスク `tasks/archive/` へ mv を検証。削除物 3 件がゴミ箱 `$I` に存在（恒久削除でない）ことを確認。PASS
- (e) pytest: `pytest scripts/tests/ -v` → **413 passed**、`pytest maintenance/tests/ -v` → **51 passed**。PASS
- SHFileOperation vs VB ラッパー 検証: `SHFileOperation` はディレクトリ削除が非決定（`-Sta` 付きでも ret=2、`S:` 2/5 / `C:` 4/5）、VB ラッパーは **10/10 全成功**（ファイル 5 + ディレクトリ 5、STA 不要）。実験スクリプトは `docs/ai/tmp/recycle_bin_exp*.ps1`（gitignore・7 日で自動削除）。

## 完了時 Memory Bank 操作

- [ ] `current-task.tsv` の参照行を削除
- [ ] 解決した `known-issues/` ファイルを `known-issues/archive/` へ `mv`（該当する場合）
- [ ] `backlog.md` の完了項目を削除（該当する場合）
