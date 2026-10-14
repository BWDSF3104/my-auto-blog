# 2026-10-14: Memory Bank アーカイブ処理のスクリプト化（scripts/archive_memory_bank.py）

**Status**: 進行中
**Next Action**: Phase 5（スクリプト実装）をユーザー指示待ち

## 概要

新規タスク開始時の `docs/ai/` クリーンアップ（7 ステップ）を決定論的スクリプトへ移行する。

**設計原則（ユーザー指示）**:
1. スクリプトは正規（well-formed）データに対する安定ルールのみを実装する。過渡期（malformed）データの処理は AI エージェントが現時点で一手で行う。
2. **Status は補完情報**。tasks/ のアクティブ判定の正は `docs/ai/current-task.tsv` の参照行。Status 値（完了/進行中/なし/形式）は一切使用しない。
3. 全 6 dir が決定論的に評価可能で、バッチ処理に適すること。

## 変更内容

- `docs/ai/memory-bank-guide.md`: 曖昧点 3 件の定義追加 + `mv` のみ規定（`:108`）の恒久修正 + スクリプト相互参照（未着手）
- `scripts/archive_memory_bank.py`: 新規（dry-run 既定、`--apply` で実行、削除は `kilo-safe-*.cmd` 委譲、`shutil.move` は上書き禁止）（未着手）
- `scripts/tests/test_archive_memory_bank.py`: 新規（pytest + unittest.mock）（未着手）

## 調査結果（2026-10-14 確認済み）

### 曖昧点 3 件の再分類（ユーザーへ提示済み）

1. verification/「直近 2 ラン」→ 正規 = run ディレクトリ名昇順（文字列）ソートの末尾 2 件を保持（決定論・名順）
2. `mv` のみ（guide `:108`）vs 削除 → `mv` は plans/decisions/known-issues/tasks の 4 ディレクトリ限定、verification/tmp は削除操作（別カテゴリ）。恒久修正（文書バグ）
3. tasks/ 14 日 → **(today − ファイル名日付) ≥ 14 日 AND `current-task.tsv` に未参照** → `mv`。Status 値は使用しない（補完情報）。current-task.tsv 参照 = アクティブ = 残置

### dir 毎「古い」判定の根拠

| dir | ソートキー | 対象 | 超過時の処理 |
|-----|-----------|------|-------------|
| plans/ | YYYY-MM-DD | `**Status**` が `完了` を含む | 完了が 10 件超 → 最古から `mv` |
| decisions/ | YYYY-MM-DD | 全ファイル | 10 件超 → 最古から `mv` |
| known-issues/ | KI-YYYYMMDD-NN | `**Status**` が `解決済` を含む | 解決済 5 件超 → 最古から `mv` |
| tasks/ | YYYY-MM-DD（ファイル名） | **current-task.tsv 未参照** AND age ≥ 14 日 | 上限なし |
| verification/ | run ディレクトリ名（文字列） | 全ラン | 機能ディレクトリ毎に末尾 2 件保持、他削除 |
| tmp/ | — | 全ファイル | 削除 |

### 2026-10-14 時点の動作予測

- tasks/ は no-op（最古 10-01 = 13 日前 < 14 日、初発火は 10-15）。current-task.tsv 参照 1 件（2026-10-14-archive-script.md）は年齢不足＋アクティブのため残置
- plans/ (8) / decisions/ (10) / known-issues/ (2) は上限未満・no-op
- tmp/ は空
- 実作業は verification/ のみ（13 ラン中 11 削除）
- **10-15 初発火時**: 10-01 の 12 件が 14 日前に達し、current-task.tsv 未参照なら全件 mv（Status 値に依存しない）

### tasks/ Status 形式インベントリ（79 ファイル）

| パターン | 件数 | 備考 |
|---------|------|------|
| A `**Status:**` | 18 | 全 `完了`（10-01×12, 10-02×6） |
| B `**Status**:`（正規） | 28 | — |
| C `- **Status**:`（ダッシュ+ボールド、コロン外） | 3 | 全 `完了`（10-09×2, 10-10×1） |
| D `- Status:` | 2 | category-cards=進行中 / tag-split-refactor=完了・コミット済み |
| E `Status:` | 1 | known-issues-image-prompt=進行中 |
| F `## Status` | 4 | 4 件とも本文に `完了`（category-cards=完了(アコーディオン型に改造) / draft-metadata-tracking=完了 / increase-image-count=完了 / trend-rss-enhancement=**完了**） |
| Status なし | 24 | — |
| Status 有（別ファイル） | 55 | 重複 1 件（category-cards = D+F、D=進行中 と F=完了 で矛盾） |

- 28 正規 + 27 変形 + 24 なし = 79
- `完了` を含む変形ファイル: **26 件**（A18 + C3 + D1 + F4）
- 修正経緯: compaction 前の値（E=2, F=3, なし=23, Status 有=56, 完了変形≈22, C 形式誤記）を `rg` による再検証で修正（kemono-randomization は Status なし、category-cards は F にも該当、C はコロン外形式）

### 旧形式ファイル一覧（51 件）

- **A `**Status:**`**（18、全 `完了`）: 2026-10-01-{canonical-url, auto-internal-links, faqpage-speakable-schema, deploy-only-workflow, description-fix, existing-post-improvement, ci-cache-seo-tasks, lcp-cls-optimization, image-size-mobile, pagination-image-restore, reddit-alternatives, google-index-registration} + 2026-10-02-{darkmode-setdark-fix, darkmode-typescript-fix, darkmode-contrast, darkmode-toggle-postpage, darkmode-themeinit, memory-bank-archive}
- **C `- **Status**:`**（3、全 `完了`）: 2026-10-09-clef-flash-genre-score（完了 2026-10-09）/ 2026-10-09-story-multi-images（完了）/ 2026-10-10-log-cleanup（完了 2026-10-10、コミット `dc2181b`）
- **D `- Status:`**（2）: 2026-10-04-category-cards（進行中）/ 2026-10-09-tag-split-refactor（完了・コミット済み 2026-10-09 `e19a96f`）
- **E `Status:`**（1）: 2026-10-05-known-issues-image-prompt（進行中）
- **F `## Status`**（4、全 `完了`）: 2026-10-04-category-cards [D と重複]（完了(アコーディオン型に改造)）/ 2026-10-06-draft-metadata-tracking（完了）/ 2026-10-06-increase-image-count（完了）/ 2026-10-10-trend-rss-enhancement（**完了** 2026-10-10 開始・完了）
- **Status なし**（24）: 2026-10-10-{trend-source-quality-fixes, generation-info-section, e621-trend-separation} / 2026-10-09-{windows-console-encoding, refiner-image-prompt-check, image-prompt-expressions, github-workflow-test-plan, genre-integration} / 2026-10-08-{topics-path-bug, rakuten-affiliate-api, github-workflow-test-plan, affiliate-keyword-revision} / 2026-10-07-{trend-usage-log, generation-pipeline-fixes, affiliate-keyword-investigation} / 2026-10-06-{github-workflow-test-plan, generation-pipeline-investigation} / 2026-10-05-{long-prompt-v2, logo-favicon, kemono-randomization, hf-api-investigation, hero-section, hamburger-menu, brand-colors}

### 他ディレクトリ（全て正規形式・旧形式なし）

- plans/ (8): 7 `完了` + 1 `進行中`（2026-10-11-giscus-comments）、全ファイル `**Status**:`
- decisions/ (10): 上限ちょうど（設計上 Status なし・不変）
- known-issues/ (2): KI-20261010-01-merge-drift=進行中 / KI-20261013-01-tf-tags-missing=解決済、両方 `**Status**:`
- tmp/: 0 ファイル

### verification/ 構造（確定）

- 機能ディレクトリ 1 件: `2026-10-12-refactor-equivalence/`
- `runs/` 配下に run ディレクトリ **13 件**（各 `images/` 付き）: baseline_{ai_deep,default,kemono_story} / current_{ai_deep,default,kemono_story} / realrun_default / selftest_1_{ai_deep,default,kemono_story} / selftest_2_{ai_deep,default,kemono_story}
- 名順ルールでは保持 2 件 = `selftest_2_default` + `selftest_2_kemono_story`、削除候補 11 件

### 環境・検索ツール

- `rg` は PATH に無かった（`Get-Command` 確認）→ `winget install BurntSushi.ripgrep.MSVC` で **ripgrep 15.2.0** を導入（2026-10-14）
- ユーザー PATH（永続）に `WinGet\Links` 追加済み、`%LOCALAPPDATA%\Microsoft\WinGet\Links\rg.exe` 存在確認 → **新規シェル・新規 Kilo 起動でそのまま使用可能**。インストール時に起動中のプロセスは再起動まで反映されない（本セッションは `$env:Path` を手動追加で対応）
- 検索ツール: 内容検索 = grep ツール（または `rg`）、ディレクトリ列挙・件数 = bash

## 設計確定（2026-10-14 ユーザー確認済）

- **tasks/ アクティブ判定**: `current-task.tsv` の参照行が正。Status 値（完了/進行中/なし/形式）は使用しない（補完情報）。
- **tasks/ アーカイブ条件**: (today − ファイル名日付) ≥ 14 日 AND current-task.tsv 未参照 → `mv`。
- **verification/ 2 件保持**: run ディレクトリ名昇順（文字列）の末尾 2 件（決定論・名順）。
- **バッチ適性**: 全 6 dir が決定論的に評価可能。Status 形式問題（正規/変形/なし 51 件）は tasks/ では消滅（Status を読まないため）。
- **current-task.md → current-task.tsv**: Markdown を TSV（3 列）へ転換。バッチ処理適性 + 記載誤りリスク低減のため。

## TSV 形式仕様（2026-10-14 ユーザー確認済）

**ファイル**: `docs/ai/current-task.tsv`

| 列 | 内容 | 形式 | 制約 |
|---|---|---|---|
| `task_file` | タスクファイルのプロジェクト相対パス | `docs/ai/tasks/YYYY-MM-DD-slug.md` | 絶対パス禁止。実在ファイルに一致 |
| `status` | アクティブ状態 | `進行中` / `保留` / `完了` / `中断` | 4 値のみ。完了/中断 = 即行削除 |
| `next_action` | 次の一手（1 行） | 日本語・簡潔 | タブ・改行禁止。詳細は tasks/ 本体 |

**ファイルルール**:
- 1 行目 = ヘッダ（`task_file\tstatus\tnext_action`）固定
- 2 行目以降 = データ行（0 ∼ N 件、通常 0 ∼ 1 件）
- 区切り = tab。末尾空行なし。UTF-8（BOM なし）。1 タスク 1 行
- コメント行なし（enum 定義は `memory-bank-guide.md` が唯一の正）
- バッチ処理: 1 行目スキップ → tab 分割 → `task_file` 列を参照

## 変更計画（2026-10-14 記録）

### 変更対象ファイル

| # | ファイル | 種別 | 変更内容 |
|---|---------|------|---------|
| 1 | `docs/ai/current-task.md` | 削除 | TSV へ転換 |
| 2 | `docs/ai/current-task.tsv` | 新規作成 | ヘッダ + アクティブ 1 行 |
| 3 | `docs/ai/memory-bank-guide.md` | 編集 | 14 箇所 `.md`→`.tsv` + tasks/ ルール + `:108` 修正 + TSV 仕様 |
| 4 | `AGENTS.md` | 編集 | `:40` Verification 記録先 → タスクファイル |
| 5 | `docs/ai/tasks/2026-10-14-archive-script.md` | 編集 | 本ファイル（参照更新 + 設計記録） |

変更しない（過去記録）: `tasks/2026-10-0*.md` 等、`plans/archive/` — 当時正しい参照。

### Phase 1: ファイル転換

| Step | 操作 |
|------|------|
| 1.1 | 新規作成 `docs/ai/current-task.tsv`（ヘッダ + 現 Active Task 1 行） |
| 1.2 | 削除 `docs/ai/current-task.md`（`./kilo-safe-remove.cmd`） |

### Phase 2: `memory-bank-guide.md` 編集

| Step | 行 | 変更 |
|------|-----|------|
| 2.1 | `:11` | `current-task.md` → `current-task.tsv`。役割列に TSV（3 列）を明記 |
| 2.2 | `:91` | TSV 形式ルールに更新（ヘッダ固定・tab 区切り・enum 4 値・コメント行なし） |
| 2.3 | `:100` | `current-task.md` → `current-task.tsv`。上限 3 KB → 500 B |
| 2.4 | `:104` | tasks/: `Status 完了 + 14日` → `current-task.tsv 未参照 AND age ≥ 14 日` |
| 2.5 | `:108` | 「すべて mv」→ plans/decisions/known-issues/tasks = mv、verification/tmp = 削除 |
| 2.6 | `:112` | `current-task.md` → `current-task.tsv` |
| 2.7 | `:116` | tasks/ 手順を 2.4 と同様に更新 |
| 2.8 ∼ 2.14 | `:125`〜`:144` | `current-task.md` → `current-task.tsv`（7 箇所） |

### Phase 3: `AGENTS.md` 編集

| Step | 行 | 変更 |
|------|-----|------|
| 3.1 | `:40` | 「`current-task.md` の Verification セクションに」→「`docs/ai/tasks/` の該当タスクファイルに」 |

### Phase 4: タスクファイル更新

| Step | 操作 |
|------|------|
| 4.1 | `current-task.md` → `current-task.tsv`、`Active Task セクション` → `参照行` |
| 4.2 | 設計決定 + TSV 仕様 + 変更計画を記録（本セクション） |
| 4.3 | Next Action 更新 |

### Phase 5: スクリプト実装（別指示・未着手）

| Step | 操作 |
|------|------|
| 5.1 | `scripts/archive_memory_bank.py` 新規作成（`current-task.tsv` を読む） |
| 5.2 | `scripts/tests/test_archive_memory_bank.py` 新規作成（TSV fixture） |
| 5.3 | `pytest scripts/tests/ -v` |
| 5.4 | `--dry-run` → 結果提示 → ユーザー確認 → `--apply` |

## Verification

- TBD
