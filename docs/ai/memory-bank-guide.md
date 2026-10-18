# AI Memory Bank ガイド

docs/ai/ は git 追跡対象。変更履歴は git commit に委ね、docs/ai/ は「なぜ変えたか」の文脈を記録する。

更新タイミングは git commit 前。Memory Bank の変更はコード変更と同じ commit に含める。プロジェクト知識・状態・判断が変化した場合のみ更新する（コード変更 ≒ Memory Bank 更新ではない）。

## ファイル一覧

| ファイル・ディレクトリ | 役割 | 更新タイミング | 必須 |
|----------|------|---------------|------|
| `current-task.tsv` | アクティブタスクへの参照（TSV 3 列: task_file / status / next_action） | `/task-add` で参照行追加・`/task-end` で削除。各チェックポイントでステータス・Next Action を更新 | ✅ |
| `tasks/*.md` | タスクの個別ファイル（1タスク1ファイル方式、アクティブ・完了問わず）。意図・背景・Backlog 参照を含む | **タスク開始時に**（調査開始段階で）`/task-add` で `docs/ai/tasks/YYYY-MM-DD-short-name.md` 作成。**設計・方針を選定・確定したタイミングで**「調査結果 / 変更内容」セクションを更新。完了時は `/task-end` で Status 更新 | ✅ |
| `decisions/` | 設計判断ログ（1エントリ1ファイル方式） | 構造・データフロー・新しい統合の設計判断時に `decisions/YYYY-MM-DD-short-name.md` を作成 | ✅ |
| `decisions/archive/` | 過去の設計判断のアーカイブ | `decisions/` は不変・バッチクリーンアップ対象外（本 archive は履歴） | — |
| `known-issues/` | 既知問題（1エントリ1ファイル方式）。トップ=未解決、`archive/`=解決済 | 新規問題発見時に `known-issues/KI-YYYYMMDD-NN-short-name.md` を作成。解決時に `known-issues/archive/` へ `mv` | ✅ |
| `known-issues/archive/` | 解決済み問題のアーカイブ | 解決時に `known-issues/` から `mv` | — |
| `backlog.md` | バックログ | 未実装項目の追加・完了時の削除・不採用時は `backlog-archive.md` へ移動（変更履歴は git commit に委ねる） | ✅ |
| `backlog-archive.md` | 不採用バックログ項目のアーカイブ（履歴参照のみ） | 不採用判定時に `backlog.md` から移動。その後の更新は行わない | — |
| `architecture.md` | アーキテクチャ図 | decisions に記録した変更がシステム構成に反映されたときのみ更新 | ✅ |
| `tmp/` | スクラッチ置き場（使い捨てスクリプト・一時成果物。gitignore 対象） | 使用時に作成。タスク開始時のバッチクリーンアップ（`archive_memory_bank.py`）で 7 日以上更新のないエントリを削除（`--tmp-retention-days` で保持期間変更） | — |

## 1エントリ1ファイル方式

`decisions/`、`known-issues/` は各エントリを個別ファイルとして保持する。

### ファイル名規則

| ディレクトリ | 命名規則 | 例 |
|-------------|---------|-----|
| `decisions/` | `YYYY-MM-DD-short-name.md` | `2026-10-13-safe-rmdir-allowlist.md` |
| `known-issues/` | `KI-YYYYMMDD-NN-short-name.md` | `KI-20261010-01-merge-drift.md` |

### ファイル内容形式

各ファイルは簡潔な Markdown で記述する。必須フィールドは `## ` タイトル行のみ。

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

**症状**: <症状>

**原因**: <原因（特定後）>

**影響**: <影響範囲>

**修正方針**: <方針（特定後）>
```

**tasks/**:
```markdown
# <タスク名>

**Status**: 進行中 / 完了 / 中断
**Date**: YYYY-MM-DD
**Backlog**: P<N> #<N>（該当する場合）

## 意図・背景

<意図・背景を1〜3行>

## 調査結果 / 変更内容

<内容>

## Verification

<検証結果>

## 完了時 Memory Bank 操作

- [ ] `current-task.tsv` の参照行を削除
- [ ] 解決した `known-issues/` ファイルを `known-issues/archive/` へ `mv`（該当する場合）
- [ ] `backlog.md` の完了項目を削除（該当する場合）
```

## アーカイブルール

ステータスは**フォルダの場所**で判定する（folder = status）。アーカイブ操作は 2 種類:

- **ワークフロー駆動**: `known-issues/` は解決時に `archive/` へ `mv`（1回のみ）
- **バッチ**: `tasks/`・`verification/`・`tmp/` は新規タスク開始時にクリーンアップ。正常運用時のコンテキスト消費を最小化する

`decisions/` は不変でアーカイブ操作なし。

### 形式ルール

- `current-task.tsv`: TSV（ヘッダ `task_file\tstatus\tnext_action` + データ行）。tab 区切り・コメント行なし・UTF-8（BOM なし）。`task_file` = プロジェクトルート相対の posix パス（例 `docs/ai/tasks/2026-10-15-kilo-temp-cleanup.md`。`archive_memory_bank.py` は `f.relative_to(root).as_posix()` と照合するため、絶対パス・バックスラッシュパスは未参照扱いになる）。status = `進行中`/`保留`/`完了`/`中断`。完了・中断タスクは参照行を削除
- `decisions/`: 作成後は不変。修正が必要な場合は新ファイルとして追加し旧ファイルの冒頭に `**Superseded by**: <新ファイル名>` を追加
- `known-issues/`: 解決時にファイルを `known-issues/archive/` へ `mv`（1回のみ・ワークフロー手順）

### フォルダ = status

`known-issues/` はフォルダの場所でステータスを判定する:

| 場所 | ステータス |
|------|-----------|
| `known-issues/`（トップ） | 未解決 |
| `known-issues/archive/` | 解決済 |

- 完了・解決時に `archive/` へ `mv`（1回のみ・ワークフロー手順）。上限なし・バッチなし
- 専用「未完了フォルダ」は設けない（未完了はトップに留置）。他のステータスフォルダも不要（2 態のみ: トップ=active、`archive/`=done）
- 保留・blocked はファイル本文 or `current-task.tsv` に注記
- 既存ファイルは `**Status**` フィールドを有する場合がある（補完情報・権威ではない）。ステータスはフォルダの場所で判定

### バッチクリーンアップ（新規タスク開始時に実行）

`python maintenance/archive_memory_bank.py` で実行（dry-run が既定・`--apply` で反映）。`--apply` 時にスクリプト自身が touch したパスは `git add` される（staging のみ・`--no-git-add` でスキップ。commit/push はエージェントが担当）。

| ディレクトリ・ファイル | 処理 |
|---------|------|
| `current-task.tsv` | 完了・中断タスクの参照行を削除（詳細は `tasks/` に既記） |
| `tasks/` | `current-task.tsv` 未参照 AND mtime（最終更新）から14日以上経過したファイルを `tasks/archive/` へ `mv` |
| `verification/` | 機能ディレクトリ毎に `runs/` 配下の run ディレクトリを mtime 順に直近2保持（同値は名順）、それ以前を削除 |
| `tmp/` | 最更新 mtime が 7 日以上経過したエントリを削除（ファイル + サブディレクトリ。サブディレクトリは内部の最更新 mtime で判定。シンボリックリンクはスキップ。`--tmp-retention-days` で保持期間変更） |

**アーカイブ操作は `tasks/` が `mv`（ファイル移動）、`verification/`・`tmp/` が削除（`kilo-safe-remove.cmd` / `kilo-safe-rmdir.cmd` 経由・**Windows ゴミ箱へ**・復元可能）。`known-issues/` はワークフロー駆動の `mv`（解決時・バッチではない）。ファイル内容の編集・書き換えは行わない（`current-task.tsv` の行削除のみ例外）。アーカイブディレクトリは git 追跡対象。**

## 中断からの復帰

中断したタスクを再開する際は:

1. `docs/ai/current-task.tsv` を読む。
2. `git status` を確認する。
3. `git diff` を確認する。
4. 最後に記録されたビルド/テストの状態を検証する。
5. `current-task.tsv` の `next_action` から作業を続ける。
6. 明確に指示されない限り、既存の変更を破棄しない。
