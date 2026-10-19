# タスク終了スクリプト：バックログ・イシューとの対応関係確認

**Status**: 完了
**Date**: 2026-10-19
**Next Action**: 設計案をユーザーに提示し、承認後に実装へ移行

## 意図 / 背景

ユーザー依頼: タスク終了スクリプトで、エンドするタスクがバックログ・イシューに該当するものがあるかを AI に確認させる方法を検討し、現状を確認する。ユーザー指示により過去の履歴調査ではなく、現在の `maintenance/task_manager.py` のみを根拠とする。

## 調査結果 / 変更内容

### 現状の end（cmd_end, lines 410-474）

1. `resolve_task_file` でタスクファイル解決（パス / 完全一致 / slug 境界）
2. `**Status**` 行 → 完了、`current-task.tsv` 参照行削除
3. 変更ファイルの `git add`（staging のみ）
4. レポート: git status --porcelain、diff --stat（unstaged/staged）、完了時チェックリスト未チェック項目

**`docs/ai/known-issues/`・`archive/`・`backlog.md` との照合はない。** スケルトンチェックリストは「解決した known-issues を archive へ mv」「backlog の完了項目を削除（該当する場合）」とエージェントに指示するが、スクリプトはどのファイル・どの行を指すこともなく、漏れリスクがエージェント判断に委ねられている。（`EXPECTED_REPORT_PATHS` は git status レポートで「想定内変更パス」としてのみ扱われ、照合機能ではない。）

### 現状スクリプトに既存で再利用できる構造

- `_backlog_entry(root, ref)` + `BACKLOG_REF_RE`（`^P(\d+)\s*#(\d+)$`）: backlog.md の `P<N> #<M>` 行検索（現在は add の開始前コンテキストのみ使用）
- `cmd_end` の report list / `git_report`: 新セクションの挿入箇所
- テスト基盤: `maintenance/tests/test_task_manager.py`（tmp_path + `end_ns` + `_git` モック）

### 検討案（推奨: end レポートに読み取り専用の「対応項目チェック」セクション）

**設計原則**: スクリプトは「解決済み/未解決」を判断しない（意味判断）。候補一致と位置のみを報告し、判断・実行（mv / 行削除）は AI エージェントに委ねる。既存の add 開始前コンテキスト（読み取りのみ・非ブロッキング）の pattern に一致。end の書き込みスコープは現状（タスクファイル + tsv）を維持。

1. タスクファイルからの参照抽出
   - KI ID: `re.findall(r'KI-\d{8}-\d{1,3}', task_text)`（タスクタイトルに `# ... (KI-YYYYMMDD-NN)` 形式が既に見る例多数）
   - タスクファイルの posix パス / stem
2. known-issues 照合（top + archive）
   - `docs/ai/known-issues/` と `archive/` のファイル名を走査: ファイル名がタスク由来の KI ID を含む → 候補
   - 2次: 未解決（top）イシュー本文がタスクパスを参照 → 候補
   - 各候補の報告: パス + 位置（top=未解決 / archive=解決済）+ 推奨動作
     - top → 「解決済みなら `known-issues/archive/` へ mv」
     - archive → 「既に移動済み」
3. backlog 照合
   - タスクファイルの `**Backlog**: P<N> #<M>` 行 → 既存在の `_backlog_entry` で行検索 → 行が存在 → 「完了時はこの行を削除」
   - 行なし → 2次: backlog 表全体をタスクパス / slug 参照で走査
4. レポート形式（読み取りのみ・非ブロッキング）:
```
--- 対応項目チェック ---
  known-issues:
    - docs/ai/known-issues/...md (未解決) → 解決済みなら archive/ へ mv
    - docs/ai/known-issues/archive/...md (解決済)
  backlog:
    - P<N> #<M> → タスク完了時は行削除
```
   該当なし → `なし`
5. スケルトンチェックリストに項目追加:
   - [ ] 対応項目チェック: 解決した known-issues → archive/ mv、完了した backlog 行 → 削除（該当する場合）

### 却下した代替案

- **スクリプトによる自動 mv / 行削除**: 却下 —「解決済み」の意味判断（タスクが解決したのか、意図的にオープン維持か）はエージェントの判断。スクリプトの既存的最小書き込みスコープ慣例を維持
- **end のブロック化**（対応未解決イシューがあれば拒否）: 却下 — 意図的にオープンの既知制約が存在し得るため、レポート提示で十分
- **新規 `check` サブコマンド**: 却下 — end が自然なタイミング。既存コマンドへのレポート追加が単純
- **タスクファイルへの結果記録**: 却下 — end の書き込みスコープを拡大しない

### テスト計画

`maintenance/tests/test_task_manager.py` に追加:
- 候補なし →「なし」出力
- top イシューファイルがタスクの KI ID に一致 → 未解決 + mv ヒントで提示
- archive 側ファイル → 解決済として提示
- タスクファイルに `**Backlog**` 行あり・backlog 行存在 → 行提示
- 未解決イシュー本文がタスクパスを参照 → 提示
- end dry-run → 書き込みなし
- end 通常 → チェックセクション出力あり、ファイル操作は現状の通り（Status / tsv 以外無変更）

### 検証方針

- `pytest maintenance/tests/ -v`
- 実タスクに対する end dry-run で対応項目チェックの表示確認

### 次のステップ

- 設計判断は `docs/ai/decisions/2026-10-19-task-end-related-check.md` に記録済み
- ユーザー承認後、上記 1〜5 + テストを実装（Python 変更 → pytest 実行）

## Verification

- 2026-10-19: 現状確認（調査のみ・コード変更なし）
  - `maintenance/task_manager.py` 全文読み込み: end が Status 更新 + tsv 行削除 + git レポートのみで、known-issues/backlog 照合なしことを確認
  - 既存在構造確認: `_backlog_entry` / `BACKLOG_REF_RE` / test harness（`maintenance/tests/test_task_manager.py`）
  - 参照シグナル確認: タスクファイルの KI ID 記述、issue 命名規則（`KI-YYYYMMDD-NN-*`、archive 一部は `resolved-` 接頭）、backlog の表行構造

## 完了時 Memory Bank 操作

- [ ] `current-task.tsv` の参照行を削除
- [ ] 解決した `known-issues/` ファイルを `known-issues/archive/` へ `mv`（該当する場合）
- [ ] `backlog.md` の完了項目を削除（該当する場合）
