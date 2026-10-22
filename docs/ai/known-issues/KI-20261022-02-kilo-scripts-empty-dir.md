# `.kilo/scripts/` 空ディレクトリの削除不可（ガード拒否）

**Date**: 2026-10-22

**Symptom**: `safe-*.ps1` を `maintenance/` へ移動（2026-10-22）後、`.kilo/scripts/` が空ディレクトリとして残存し、削除できない。

**Cause**: safe 工具（`maintenance/safe-{remove,rmdir}.ps1`）は `.git` / `.kilo` を保護領域として拒否している（意図的: Kilo ランタイム状態・設定の保護）。`.kilo/scripts/` も `.kilo/` 直下であり、`kilo-safe-rmdir.cmd .kilo/scripts` は guard で exit 1。

**Impact**: `.kilo/scripts/`（空）がディスクに残存する。git 追跡対象なし（空ディレクトリは git 管理外）、動作影響なし。

**Direction**: 放置。ガードの意図（Kilo 状態保護）が優先される。`.kilo/` 全体が不要になるまでの間、無害として扱う。
