# 2026-10-14: memory-bank-guide.md 改訂（:128 修正 + 日本語統一）

**Status**: 完了（2026-10-14）
**Next Action**: なし

## 概要

`current-task.md` 記載誤りの原因分析の結果、ガイド `:128` の文言（チェックポイント結果を `current-task.md` に記録）が `:91` の「1タスク1行」ルールと矛盾し誤りを誘発していた。チェックポイント結果はタスクファイルへ記録し、`current-task.md` はステータス/Next Action 更新のみに制限するよう修正。併せてガイドの英語2セクションを日本語統一した。

## 変更内容

- `docs/ai/memory-bank-guide.md:128`: チェックポイント成功時は結果をタスクファイルに記録し、`current-task.md` はステータス/Next Action 更新のみ
- `docs/ai/memory-bank-guide.md:123-145`: "Long-running Agent Tasks" → 「長時間の Agent タスク」/"Recovery After Interruption" → 「中断からの復帰」の2セクションを日本語化（テンプレートのフィールド名 `Status`/`Next Action` 等は英語維持）。クロス参照 grep で参照破損なしを確認
- 原因分析（5因子）: ①タスク開始時にタスクファイル未作成 ②開始時のガイド再読漏れ ③ガイド `:128`/`:91` の内部矛盾 ④手軽さバイアス ⑤commit 前の形式セルフチェック欠如
- 併せて進行中のガイド改訂自体が `current-task.md` 未記録だった不整合を修正（タスクファイル作成＋参照行追加→完了時に削除）

## Verification

- docs/ai のみ変更 → pytest/build 不要
