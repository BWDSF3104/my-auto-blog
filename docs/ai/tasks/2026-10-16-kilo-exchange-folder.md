# ユーザーやり取りフォルダをルール(AGENTS.md)に記録

**Status**: 完了
**Date**: 2026-10-16
**Backlog**: —

## 意図・背景

ユーザー指示: 2026-10-16 に作成した Google Drive 同期フォルダ `I:\マイドライブ\kilo` を「ユーザーとのやり取り用フォルダ」としてプロジェクトルール(AGENTS.md)の適切な箇所に記録する。コード変更なしのドキュメント/ルール変更タスク。

## 調査結果 / 変更内容

- I: は物理ディスクではなく、Drive for Desktop が起動時に登録して記憶する仮想ドライブ(VDF)であることを確認済み（`Get-Volume` に I: 不在、`Win32_LogicalDisk` で DriveType=3 / VolumeName "Google Drive"、`root_preference_sqlite.db` の media テーブルに `last_mount_point=I:\`、レジストリ `HKCU\Software\Google\DriveFS\Share` の SyncTargets に `I:` を確認）。
- AGENTS.md の「## 開発」の直後に「## ユーザーやり取りフォルダ」セクションを新設し、パス `I:\マイドライブ\kilo` とドライブの性質を記録。

## Verification

- 変更は `AGENTS.md` と `docs/ai/` のみのため、AGENTS.md コード検証の例外規定により pytest / build 不要。

## 完了時 Memory Bank 操作

- [x] `current-task.tsv` の参照行を削除
