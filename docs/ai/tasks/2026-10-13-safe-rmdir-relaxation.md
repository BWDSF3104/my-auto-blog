# 2026-10-13: kilo-safe-rmdir.cmd アローリスト緩和（プロジェクト内全フォルダ許可）

**Status**: 完了（2026-10-13 コミット）
**Next Action**: なし

## 概要

ユーザー要望: `kilo-safe-rmdir.cmd` が名前ベースアローリスト（`$allowedFolders`: node_modules, dist, .astro, .pytest_cache, tmp）に限定されていたため、リスト外の一時フォルダ（例: `test-results/`）を削除できなかった。制約を緩和する。

## 判断プロセス（ユーザー最終指示）

- 名前アローリスト拡張: 却下（リスト外の一時フォルダが常に漏れる）
- git 追跡ファイルチェック: 却下（一度 commit すると削除できなくなるため「解決にならない」）
- 採用: **プロジェクトフォルダ内なら全フォルダ許可 + 拒否リスト（deny list）継続**（「保護すべきものは保護」の方向性）
- 根拠: git 管理下なら削除しても復元可能。未追跡の一時コンテンツは設計上捨ててよい

## 変更内容

- `.kilo/scripts/safe-rmdir.ps1`:
  - `$allowedFolders` 配列とループ内の名前アローリストチェックを削除
  - ヘッダコメント追加（Any folder inside the project is deletable...）
  - ガード維持: ディレクトリのみ / シンボリックリンク拒否 / プロジェクト外拒否 / プロジェクトルート拒否 / `.git`・`.kilo` 拒否（safe-rmdir.ps1:86-94）
- `kilo-safe-rmdir.cmd`（ラッパー）・`kilo.jsonc` の permission.bash は不変（`./kilo-safe-rmdir.cmd *` の allow パターンは既存）

## Verification

- 陽性: `tmp-rmdir-selftest`（probe.txt 入り）を `./kilo-safe-rmdir.cmd tmp-rmdir-selftest` で削除 → `Deleted: tmp-rmdir-selftest`、exit 0、`Test-Path` → False で消失確認
- 陰性: `./kilo-safe-rmdir.cmd S:\Documents` → `Deleting outside project is not allowed`、exit 1
- 陰性: `./kilo-safe-rmdir.cmd AGENTS.md` → `This script is for directories only`、exit 1
- `.git`/`.kilo` 拒否試験: 未実施（ユーザー指示: 実フォルダで拒否試験しない）。ガードは既存変更なしコード
- サイトコード変更なし（`.kilo/` + `docs/ai/` のみ）→ AGENTS.md 規則により pytest / `npm run build` 不要
- `git status` で作業ツリーは `safe-rmdir.ps1` と Memory Bank のみ、テスト用フォルダの残骸なしを確認

## 備考

- `test-results/`（本来の動機: git 無視の一時ワークフローテストレポート）の削除: 未実施（ユーザー指示で試験一時停止）。`./kilo-safe-rmdir.cmd test-results` で随時削除可能
