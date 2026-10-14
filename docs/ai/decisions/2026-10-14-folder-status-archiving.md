# Memory Bank の folder = status 化・上限廃止（アーカイブ設計）

**Date**: 2026-10-14

**Decision**: `plans/`・`known-issues/` のステータスをフォルダの場所で判定する（トップ=active、`archive/`=done）。完了・解決時にファイルを `archive/` へ `mv`（1 回のみ・ワークフロー手順・バッチではない）。件数・容量の上限は全廃。`resolved-` リネームは廃止。`decisions/` は不変でアーカイブ操作なし（蓄積のみ）。バッチクリーンアップは `tasks/`（14 日 + `current-task.tsv` 未参照）・`verification/`（機能毎直近 2 ラン保持）・`tmp/`（全削除）に限定。

**Reason**: 上限管理（件数カウント・超過判定・バッチ mv）はコンテキスト消費と複雑さを増やし、AI の迅速・正確な操作を妨げていた。folder = status にするとステータスはフォルダ見ただけで判明し、完了時の `mv` が自然な状態遷移として定着する（バッチ不要）。tasks/ のアクティブ判定は既に `current-task.tsv` の参照行が正であるため、Status 値の解析は不要（補完情報）。

**Rejected Alternatives**:
- 従来方式（完了時にファイル内の `Status` を `完了`/`解決済` に 1 行編集 + 上限超過時のバッチ mv）: Status 値の表記揺れ（tasks/ 79 件で 5 種以上）に脆弱、上限管理が複雑。
- `resolved-` 等の接頭辞リネームによるステータス管理: ファイル名と内容の二重管理になり単純ではない。フォルダ移動の方が明確。

**Impact**:
- `docs/ai/memory-bank-guide.md`: ファイル一覧表・形式ルール・テンプレート（`plans/`・`known-issues/` の `Status` 字段削除）・アーカイブルール（folder = status + 上限廃止 + バッチクリーンアップ限定）・長時間タスク手順を改訂
- `docs/ai/workflows.md`: Commit Checklist の plans/・known-issues/ 項目を「Status 更新」から「`mv`」へ置換
- 既存ファイルの `Status` 行は編集しない（補完情報・権威ではない）
- Phase 5 のスクリプト対象は `tasks/`・`verification/`・`tmp/` に限定（`plans/`・`known-issues/`・`decisions/` は対象外）
