# archive --apply が tmp/ 削除後に git add 失敗（gitignore 対象）して exit 1

**Date**: 2026-10-18

**症状**: `python maintenance/archive_memory_bank.py --apply` を実行し `tmp/` のエントリ削除が計画に含まれる場合、削除自体は成功するのに末尾の `git add -- docs/ai/tmp/<entry>` が失敗し、スクリプト全体が exit 1 になる。`verification/` の run 削除のみ（tmp/ 削除なし）では問題なし。

**原因**: `docs/ai/tmp/` は gitignore 対象（`.gitignore` の `tmp/` が全レベル一致、`git check-ignore -v` で確認済み）。`git add` は gitignore 対象パスへの pathspec が「何も追跡対象にマッチしない」ため失敗（pathspec did not match）する。tmp/ エントリはそもそも未追跡・git 管理外なので、`git add` すべき対象ではない。

**影響**: tmp/ バッチクリーンアップは実際に適用されている（ゴミ箱へ移動済み）のに、スクリプトがエラー + exit 1 を返す。失敗に見えるがクリーンアップ自体は完了している。`--no-git-add` を付けると回避できる。

**修正方針**: `archive_memory_bank.py` の git-add 手順で、gitignore 対象パス（`git check-ignore` で事前判定）を staging 対象から除外する（または tmp/ 削除のみを対象外にする）。本タスク（ゴミ箱化）では必須でないため、この場で修正せず記録のみ（AGENTS.md「タスク実行中に発見した非必須問題」ルール）。
