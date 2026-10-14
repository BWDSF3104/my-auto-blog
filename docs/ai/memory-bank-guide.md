# AI Memory Bank ガイド

docs/ai/ は git 追跡対象。変更履歴は git commit に委ね、docs/ai/ は「なぜ変えたか」の文脈を記録する。

更新タイミングは git commit 前。Memory Bank の変更はコード変更と同じ commit に含める。プロジェクト知識・状態・判断が変化した場合のみ更新する（コード変更 ≒ Memory Bank 更新ではない）。

## ファイル一覧

| ファイル・ディレクトリ | 役割 | 更新タイミング | 必須 |
|----------|------|---------------|------|
| `current-task.tsv` | アクティブタスクへの参照（TSV 3 列: task_file / status / next_action） | タスク開始時に参照行を追加。各チェックポイントでステータス・Next Action を更新。タスク完了時または中断時に参照行を削除 | ✅ |
| `tasks/*.md` | タスクの個別ファイル（1タスク1ファイル方式、アクティブ・完了問わず） | タスク開始時に `docs/ai/tasks/YYYY-MM-DD-short-name.md` として作成。完了時は Status を更新 | ✅ |
| `plans/` | 計画書（1エントリ1ファイル方式） | タスク開始前に `plans/YYYY-MM-DD-short-name.md` を作成。完了時はファイル内に `**Status**: 完了` を追加 | ✅ |
| `plans/archive/` | 古い完了計画のアーカイブ | クリーンアップ時に `plans/` から `mv` | — |
| `decisions/` | 設計判断ログ（1エントリ1ファイル方式） | 構造・データフロー・新しい統合の設計判断時に `decisions/YYYY-MM-DD-short-name.md` を作成 | ✅ |
| `decisions/archive/` | 古い設計判断のアーカイブ | クリーンアップ時に `decisions/` から `mv` | — |
| `known-issues/` | 既知問題（1エントリ1ファイル方式） | 新規問題発見時に `known-issues/KI-YYYYMMDD-NN-short-name.md` を作成。解決時はファイル内に `**Status**: 解決済` を追加 | ✅ |
| `known-issues/archive/` | 解決済み問題のアーカイブ | クリーンアップ時に `known-issues/` から `mv` | — |
| `backlog.md` | バックログ | 未実装項目の追加・完了時の削除（変更履歴は git commit に委ねる） | ✅ |
| `architecture.md` | アーキテクチャ図 | decisions に記録した変更がシステム構成に反映されたときのみ更新 | ✅ |

- `development-notes.md` は削除済み。詳細な実装履歴は git log で確認可能
- `issue-inventory-archive.md` は廃止済み（2026-10-04）。残存イシューは `backlog.md` に統合済み

## 1エントリ1ファイル方式

`plans/`、`decisions/`、`known-issues/` は各エントリを個別ファイルとして保持する。

### ファイル名規則

| ディレクトリ | 命名規則 | 例 |
|-------------|---------|-----|
| `plans/` | `YYYY-MM-DD-short-name.md` | `2026-10-13-safe-rmdir-allowlist.md` |
| `decisions/` | `YYYY-MM-DD-short-name.md` | `2026-10-13-safe-rmdir-allowlist.md` |
| `known-issues/` | `KI-YYYYMMDD-NN-short-name.md` | `KI-20261010-01-merge-drift.md` |

### ファイル内容形式

各ファイルは簡潔な Markdown で記述する。必須フィールドは `## ` タイトル行のみ。

**plans/**:
```markdown
# <計画名>

**Date**: YYYY-MM-DD
**Status**: 進行中 / 完了
**Backlog**: P<N> #<N>（該当する場合）

<意図・背景を1〜3行>

<関連タスクファイル: `tasks/YYYY-MM-DD-short-name.md`（該当する場合）>
```

**decisions/**:
```markdown
# <判断名>

**Date**: YYYY-MM-DD

**Decision**: <決定内容>

**Reason**: <理由>

**Rejected Alternatives**: <採用しなかった代替案（任意）>

**Impact**: <影響範囲（任意）>
```

**known-issues/**:
```markdown
# <問題名>

**Date**: YYYY-MM-DD
**Status**: 進行中 / 解決済

**症状**: <症状>

**原因**: <原因（特定後）>

**影響**: <影響範囲>

**修正方針**: <方針（特定後）>
```

## アーカイブルール

アーカイブは**新規タスク開始時のみ**実行する。コミット前・チェックリストに含めない。正常運用時のコンテキスト消費を最小化する。

### 形式ルール

- `current-task.tsv`: TSV（ヘッダ `task_file\tstatus\tnext_action` + データ行）。tab 区切り・コメント行なし・UTF-8（BOM なし）。status = `進行中`/`保留`/`完了`/`中断`。完了・中断タスクは参照行を削除
- `plans/`: 完了した計画はファイル内の `Status` を `完了` に更新（1行編集）。ファイル自体は `plans/` に残置
- `decisions/`: 作成後は不変。修正が必要な場合は新ファイルとして追加し旧ファイルの冒頭に `**Superseded by**: <新ファイル名>` を追加
- `known-issues/`: 解決した問題はファイル内の `Status` を `解決済` に更新（1行編集）。ファイル自体は `known-issues/` に残置

### 容量上限とクリーンアップ（新規タスク開始時に実行）

| ディレクトリ・ファイル | 上限 | 超過時の処理 |
|---------|------|-------------|
| `current-task.tsv` | 500 B | 完了・中断タスクの参照行を削除（詳細は `tasks/` に既記） |
| `plans/`（archive 除外） | 10 ファイル | 古い完了ファイルを `plans/archive/` へ `mv` |
| `decisions/`（archive 除外） | 10 ファイル | 古いファイルを `decisions/archive/` へ `mv` |
| `known-issues/`（archive 除外） | 5 ファイル | 解決済ファイルを `known-issues/archive/` へ `mv` |
| `tasks/` | — | `current-task.tsv` 未参照 AND ファイル名の日付が14日以上経過したファイルを `tasks/archive/` へ `mv` |
| `verification/` | — | 機能ディレクトリ毎に直近2ランのみ保持、それ以前を削除 |
| `tmp/` | — | 全ファイルを削除 |

**アーカイブ操作は `plans/`・`decisions/`・`known-issues/`・`tasks/` が `mv`（ファイル移動）、`verification/`・`tmp/` が削除。ファイル内容の編集・書き換えは行わない。**

### クリーンアップ手順（新規タスク開始時に実行）

1. `current-task.tsv`: 完了・中断済みの参照行を削除（1行削除）
2. `plans/`: 完了ファイルが10件を超える場合、最も古い完了ファイルを `plans/archive/` へ `mv`（10件まで維持）
3. `decisions/`: ファイルが10件を超える場合、最も古いファイルを `decisions/archive/` へ `mv`（10件まで維持）
4. `known-issues/`: 解決済ファイルが5件を超える場合、最も古い解決済ファイルを `known-issues/archive/` へ `mv`（5件まで維持）
5. `tasks/`: `current-task.tsv` 未参照 AND ファイル名の日付が14日以上経過したファイルを `tasks/archive/` へ `mv`
6. `verification/`: 機能ディレクトリ毎に直近2ランのみ保持、それ以前を削除
7. `tmp/`: 全ファイルを削除

- `plans/` の完了ファイルは常に日付が新しい順に並ぶ（ファイル名の日付でソート）
- アーカイブディレクトリは git 追跡対象

## 長時間の Agent タスク

- タスク開始前に `docs/ai/current-task.tsv` が存在する場合は読むこと。
- 計画済みの変更を開始前に、該当する `plans/` と `backlog.md` エントリを読むこと。
- 意味のあるステップの完了後に `docs/ai/current-task.tsv` を更新すること。
- ビルド/テストのチェックポイントが成功したら、結果はタスクファイルに記録し、`current-task.tsv` はステータス/Next Action の更新のみを行うこと。
- タスクが中断された場合は、`docs/ai/current-task.tsv` を再開可能な状態に残しておくこと。
- compaction 以降、以前の会話コンテキストがまだ使えると仮定しないこと。
- 重要な決定は `decisions/` に新ファイルとして記録すること。
- 重要な未解決の問題は `known-issues/` に新ファイルとして記録すること。
- 現行項目のビルド/テスト完了基準を満たすまで、次の計画項目を開始しないこと。
- **タスク完了時（git commit 前）**: `docs/ai/current-task.tsv` の該当参照行を削除し、`plans/` の該当ファイルの `Status` を `完了` に更新（1行編集）。Memory Bank の変更はコード変更と同じ commit に含めること。

## 中断からの復帰

中断したタスクを再開する際は:

1. `docs/ai/current-task.tsv` を読む。
2. `git status` を確認する。
3. `git diff` を確認する。
4. 最後に記録されたビルド/テストの状態を検証する。
5. `current-task.tsv` の `next_action` から作業を続ける。
6. 明確に指示されない限り、既存の変更を破棄しない。
