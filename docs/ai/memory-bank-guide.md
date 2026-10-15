# AI Memory Bank ガイド

docs/ai/ は git 追跡対象。変更履歴は git commit に委ね、docs/ai/ は「なぜ変えたか」の文脈を記録する。

更新タイミングは git commit 前。Memory Bank の変更はコード変更と同じ commit に含める。プロジェクト知識・状態・判断が変化した場合のみ更新する（コード変更 ≒ Memory Bank 更新ではない）。

## ファイル一覧

| ファイル・ディレクトリ | 役割 | 更新タイミング | 必須 |
|----------|------|---------------|------|
| `current-task.tsv` | アクティブタスクへの参照（TSV 3 列: task_file / status / next_action） | タスク開始時に参照行を追加（`tasks/` ファイル作成時は必ず同時に行追加）。各チェックポイントでステータス・Next Action を更新。タスク完了時または中断時に参照行を削除 | ✅ |
| `tasks/*.md` | タスクの個別ファイル（1タスク1ファイル方式、アクティブ・完了問わず） | タスク開始時に `docs/ai/tasks/YYYY-MM-DD-short-name.md` として作成。完了時は Status を更新 | ✅ |
| `plans/` | 計画書（1エントリ1ファイル方式）。トップ=進行中、`archive/`=完了 | タスク開始前に `plans/YYYY-MM-DD-short-name.md` を作成。完了時に `plans/archive/` へ `mv` | ✅ |
| `plans/archive/` | 完了計画のアーカイブ | 完了時に `plans/` から `mv` | — |
| `decisions/` | 設計判断ログ（1エントリ1ファイル方式） | 構造・データフロー・新しい統合の設計判断時に `decisions/YYYY-MM-DD-short-name.md` を作成 | ✅ |
| `decisions/archive/` | 過去の設計判断のアーカイブ | `decisions/` は不変・バッチクリーンアップ対象外（本 archive は履歴） | — |
| `known-issues/` | 既知問題（1エントリ1ファイル方式）。トップ=未解決、`archive/`=解決済 | 新規問題発見時に `known-issues/KI-YYYYMMDD-NN-short-name.md` を作成。解決時に `known-issues/archive/` へ `mv` | ✅ |
| `known-issues/archive/` | 解決済み問題のアーカイブ | 解決時に `known-issues/` から `mv` | — |
| `backlog.md` | バックログ | 未実装項目の追加・完了時の削除・不採用時は `backlog-archive.md` へ移動（変更履歴は git commit に委ねる） | ✅ |
| `backlog-archive.md` | 不採用バックログ項目のアーカイブ（履歴参照のみ） | 不採用判定時に `backlog.md` から移動。その後の更新は行わない | — |
| `architecture.md` | アーキテクチャ図 | decisions に記録した変更がシステム構成に反映されたときのみ更新 | ✅ |
| `tmp/` | スクラッチ置き場（使い捨てスクリプト・一時成果物。gitignore 対象） | 使用時に作成。タスク開始時のバッチクリーンアップ（`archive_memory_bank.py`）で全削除 | — |

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

## 背景

<背景>

## 調査結果 / 変更内容

<内容>

## Verification

<検証結果>

## 完了時 Memory Bank 操作

- [ ] `current-task.tsv` の参照行を削除
- [ ] `plans/` の該当ファイルを `plans/archive/` へ `mv`（該当する場合）
- [ ] 解決した `known-issues/` ファイルを `known-issues/archive/` へ `mv`（該当する場合）
- [ ] `backlog.md` の完了項目を削除（該当する場合）
```

## アーカイブルール

ステータスは**フォルダの場所**で判定する（folder = status）。アーカイブ操作は 2 種類:

- **ワークフロー駆動**: `plans/`・`known-issues/` は完了・解決時に `archive/` へ `mv`（1回のみ）
- **バッチ**: `tasks/`・`verification/`・`tmp/` は新規タスク開始時にクリーンアップ。正常運用時のコンテキスト消費を最小化する

`decisions/` は不変でアーカイブ操作なし。

### 形式ルール

- `current-task.tsv`: TSV（ヘッダ `task_file\tstatus\tnext_action` + データ行）。tab 区切り・コメント行なし・UTF-8（BOM なし）。`task_file` = プロジェクトルート相対の posix パス（例 `docs/ai/tasks/2026-10-15-kilo-temp-cleanup.md`。`archive_memory_bank.py` は `f.relative_to(root).as_posix()` と照合するため、絶対パス・バックスラッシュパスは未参照扱いになる）。status = `進行中`/`保留`/`完了`/`中断`。完了・中断タスクは参照行を削除
- `plans/`: 完了時にファイルを `plans/archive/` へ `mv`（1回のみ・ワークフロー手順）。ファイル内容は編集しない
- `decisions/`: 作成後は不変。修正が必要な場合は新ファイルとして追加し旧ファイルの冒頭に `**Superseded by**: <新ファイル名>` を追加
- `known-issues/`: 解決時にファイルを `known-issues/archive/` へ `mv`（1回のみ・ワークフロー手順）

### フォルダ = status

`plans/`・`known-issues/` はフォルダの場所でステータスを判定する:

| 場所 | ステータス |
|------|-----------|
| `plans/`（トップ） | 進行中 |
| `plans/archive/` | 完了 |
| `known-issues/`（トップ） | 未解決 |
| `known-issues/archive/` | 解決済 |

- 完了・解決時に `archive/` へ `mv`（1回のみ・ワークフロー手順）。上限なし・バッチなし
- 専用「未完了フォルダ」は設けない（未完了はトップに留置）。他のステータスフォルダも不要（2 態のみ: トップ=active、`archive/`=done）
- 保留・blocked はファイル本文 or `current-task.tsv` に注記
- 既存ファイルは `**Status**` フィールドを有する場合がある（補完情報・権威ではない）。ステータスはフォルダの場所で判定

### バッチクリーンアップ（新規タスク開始時に実行）

`python maintenance/archive_memory_bank.py` で実行（dry-run が既定・`--apply` で反映）。

| ディレクトリ・ファイル | 処理 |
|---------|------|
| `current-task.tsv` | 完了・中断タスクの参照行を削除（詳細は `tasks/` に既記） |
| `tasks/` | `current-task.tsv` 未参照 AND mtime（最終更新）から14日以上経過したファイルを `tasks/archive/` へ `mv` |
| `verification/` | 機能ディレクトリ毎に `runs/` 配下の run ディレクトリを mtime 順に直近2保持（同値は名順）、それ以前を削除 |
| `tmp/` | 全ファイル・サブディレクトリを削除（シンボリックリンクはスキップ） |

**アーカイブ操作は `tasks/` が `mv`（ファイル移動）、`verification/`・`tmp/` が削除（`kilo-safe-remove.cmd` / `kilo-safe-rmdir.cmd` 経由）。`plans/`・`known-issues/` はワークフロー駆動の `mv`（完了・解決時・バッチではない）。ファイル内容の編集・書き換えは行わない（`current-task.tsv` の行削除のみ例外）。アーカイブディレクトリは git 追跡対象。**

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
- **タスク完了時（git commit 前）**: `docs/ai/current-task.tsv` の該当参照行を削除し、`plans/` の該当ファイルを `plans/archive/` へ `mv`（1回のみ）。Memory Bank の変更はコード変更と同じ commit に含めること。
- **問題解決時（git commit 前）**: `known-issues/` の該当ファイルを `known-issues/archive/` へ `mv`（1回のみ）。Memory Bank の変更はコード変更と同じ commit に含めること。

## 中断からの復帰

中断したタスクを再開する際は:

1. `docs/ai/current-task.tsv` を読む。
2. `git status` を確認する。
3. `git diff` を確認する。
4. 最後に記録されたビルド/テストの状態を検証する。
5. `current-task.tsv` の `next_action` から作業を続ける。
6. 明確に指示されない限り、既存の変更を破棄しない。
