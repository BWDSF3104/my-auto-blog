# スクラッチ置き場を docs/ai/tmp/ に転用する

**Date**: 2026-10-15

**Decision**: 使い捨てスクリプト・一時成果物の置き場（scratch）をシステム一時ディレクトリ `C:\Users\fujim\AppData\Local\Temp\kilo\` からリポジトリ内 `docs/ai/tmp/` へ転用する。

**Reason**:
- `Temp\kilo` が 2,801 ファイル / 105.7MB まで無制限に蓄積（AGENTS.md の scratch 指定と Kilo sandbox の `TEMP`/`TMP`/`TMPDIR` リダイレクト `kilocode` `policy.ts:273-275` が重畳。自動クリーンアップ機構なし）
- `docs/ai/tmp/` は `.gitignore:34`（`tmp/`）と `archive_memory_bank.py` のバッチクリーンアップ（タスク開始時全削除・`kilo-safe-*.cmd` 経由）が**既に定義済み**の「死んだルール」で、新規スクリプト不要
- リポジトリ内なら `git diff` での追跡・監査が可能（gitignored だが）。Memory Bank の「記録は `tasks/` に、scratch は使い捨て」の設計思想と整合
- `%TEMP%` は `kilo-safe-remove.cmd` / `kilo-safe-rmdir.cmd` のスコープ外（プロジェクト内限定）のため、安全削除機構が適用できない

**Rejected Alternatives**:
- `Temp\kilo` を維持しクリーンアップスクリプトを追加: リポジトリ外のため git diff 検証不能 + 新規スクリプトが要る（ユーザーが「新規スクリプト不要」を指示）
- 日付管理（日付サブフォルダ + N 日保持）: 状態と複雑さを増やすだけで、価値のある成果物は `tasks/*.md` に記録するのが既定の役割分担。`backlog.md` P3 #12 にオプションとして登録（実装時は `archive_memory_bank.py` と AGENTS.md ルール文言を同時に改修する条件付き）

**Impact**:
- ライブ参照 3 箇所（`AGENTS.md` / `docs/ai/manual-article-workflow.md` / `scripts/tests/equivalence_check.py`）を更新。`tasks/` 履歴 9 件は変更しない
- `equivalence_check.py` の `EQ_DIR` 既定値が `docs/ai/tmp/eq`（gitignored ため `git status` は clean。環境変数 `EQ_TMP_DIR` 上書き可）
- %TEMP%\kilo の初回クリーンアップは別途実施（インベントリ → ユーザー承認 → `Remove-Item`）
