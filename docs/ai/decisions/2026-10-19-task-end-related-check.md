# タスク終了スクリプト: backlog・known-issues 対応項目チェック（end レポート追加）

**Date**: 2026-10-19

**Decision**: `maintenance/task_manager.py` の `end` 出力に読み取り専用の「対応項目チェック」セクションを追加する。終了対象タスクについて、`docs/ai/known-issues/`（top 及/archive/）をタスクファイル内の KI ID（`KI-\d{8}-\d{1,3}`）/ タスクパス参照で照合し、`docs/ai/backlog.md` をタスクファイルの `**Backlog**: P<N> #<M>` フィールド（既存 `_backlog_entry` を再利用）/ 行内タスク参照で照合する。一致した候補のファイルパス・現在の位置（未解決/解決済）・推奨動作（archive へ mv / 完了時に backlog 行削除）を報告する。スクリプトの書き込みスコープは現状（タスクファイルの Status 更新 + current-task.tsv 行削除のみ）を維持し、判断・実行は AI エージェントが実施する。

**Reason**: 現行 `end`（cmd_end）は Status 更新と tsv 行削除、git status/diff レポート、チェックリスト未項目の列挙にとどまり、終了タスクが `known-issues/`・`backlog.md` にどのファイル・行に対応するか提示しない。タスクスケルトンの「完了時 Memory Bank 操作」チェックリストが「解決した known-issues を archive へ mv」「backlog の完了項目を削除（該当する場合）」と指示するものの、対応先がスクリプト側で特定されないため、漏れ・誤操作リスクがエージェント判断に委ねられている。一方、リポジトリには安定した参照シグナル（タスクファイルの KI ID 記述、issue ファイル命名規則、backlog の表行構造、既存 `_backlog_entry` ヒelpers）があり、決定的な照合が実現可能。なお「解決済みか否か」は意味判断（意図的にオープンの既知制約も存在し得る）のため、スクリプトは自動実行せず非ブロッキングの報告にとどめる。これは既存 `add` の開始前コンテキスト出力（読み取りのみ・非ブロッキング）の pattern と一貫する。

**Rejected Alternatives**:
- スクリプトによる自動 mv / backlog 行削除: 却下 — 解決判断は意味判断であり、スクリプトの既存最小書き込みスコープ慣例（end: Status+tsv / add: task+tsv）を維持
- end のブロック化（対応する未解決イシューが存在すれば終了拒否）: 却下 — 意図的にオープンの既知制約が存在し得るため、レポート提示で十分
- 新規 `check` サブコマンド: 却下 — end が自然なタイミングであり、既存コマンドへのレポート追加が単純で利用しやすい
- 照合結果をタスクファイルに記録: 却下 — end の書き込みスコープを拡大しない

**Impact**:
- `task_manager.py`: 照合関数新規（KI ID 抽出・issue 照合・backlog 照合）、end レポート追加、スケルトンチェックリスト項目追加、docstring 更新
- テスト: `maintenance/tests/test_task_manager.py` に追加（候補なし/有、top/archive、Backlog フィールド、本文参照、dry-run 無変更、通常時の書き込みスコープ不変）
- 今後の `end` 呼び出しの出力に影響（書き込み動作は変更なし）
- 実装: 2026-10-19 時点では検討・記録のみ（ユーザー承認待ち）
