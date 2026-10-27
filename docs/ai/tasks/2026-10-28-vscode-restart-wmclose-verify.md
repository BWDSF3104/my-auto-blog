# VS Code 再起動バッチ WM_CLOSE 失敗の再検証（KI-20261026-02）

**Status**: 進行中
**Date**: 2026-10-28
**Next Action**: 実装案の承認待ち（対象を可視ウィンドウ限定・返り値ではなく消失ポーリング判定・self-test に -n）

## 意図 / 背景

- `docs/ai/known-issues/KI-20261026-02-vscode-restart-wmclose-failure.md`（未解決）の再検証。2026-10-26 の本番実行で WM_CLOSE が一部ウィンドウで失敗し、自動再起動に至らなかった（ユーザー手動再起動）。
- 現環境（タスクスケジューラで VS Code を最上位権限へ昇格起動）でクローズ経路が機能するかを確認し、失敗原因とコード上の判定欠陥を特定する。実装は行わない（承認待ち）。

## 調査結果 / 変更内容

### 機能する部分（実証）

- 現環境は VS Code 全体が昇格トークンで起動（`whoami /groups` → Mandatory Level High `S-1-16-12288`、`BUILTIN\Administrators` = `Enabled group, Group owner`。`net session` 成功＝昇格トークン。プロセスチェーン `services.exe`(780) → `Code.exe`(2304) → `Code.exe`(24212) → `pwsh`）。
- 同一インテグリティで WM_CLOSE が効くことを実証: `code -n docs/ai/tmp/vscode_selftest` で新規**可視**ウィンドウ（`Chrome_WidgetWin_1`）作成 → WM_CLOSE 送信 → 約1秒でクローズ。
- したがって 2026-10-26 の失敗は **UIPI（インテグリティ不一致）** が最有力（非昇格シェル → 高インテグリティ `[管理者]` ウィンドウの SendMessage はフィルタされる）。低インテグリティ側からの再現実验は当前不可なので推定どおり。

### 判定ロジックの欠陥（再現確認済み）

1. `maintenance/vscode_graceful_restart.py:165`（`send_close`）は `SendMessageW` の返り値を成功判定するが、返り値は窓プロックの返り値で、正常処理後も `DefWindowProc` は `0` を返す → 偽陰性。UIPI フィルタ時の `0` と区別不能（`last_error` も 0）。
2. `find_code_windows()` は `Chrome_WidgetWin_0/1` を区別しない。実測 4 ウィンドウ中可視は1のみ（`0x3a0a60`）、残り3は `visible=0` の `Chrome_WidgetWin_0` helper。helper は WM_CLOSE で閉じない → `all(send_close(...))` は常态で False。
3. `--self-test` は単一インスタンス環境で検証できない: `code <path>` は可視ウィンドウを作らず既存をフォーカスし、不可視 helper が増えてカウントだけ増える（実測: 失敗判定、helper `0x50d7a` 残存）。新規可視ウィンドウには `-n` が必要。

### 採用方針（改善案・未実装）

- 対象を**可視 `Chrome_WidgetWin_1` のみ**へ限定（`IsWindowVisible`）。
- 成功判定は返り値ではなく、送信後の**ウィンドウ／Code.exe プロセス消失をポーリング**（ワーカー側の 180 秒判定と統一）。残存時のみ失敗として通知。
- 実行シェルのインテグリティとターゲットウィンドウの一致を確認。不一致なら「UIPI で送信不可 → 昇格シェルで実行必須」と明示。
- `--self-test` は `code -n <scratch>` を使用し、可視ウィンドウ生成＋クローズを検証。

## Verification

- `python maintenance/vscode_graceful_restart.py --dry-run <cwd>` → 4 ウィンドウ列挙（可視1・helper3）。変更なし。
- `python maintenance/vscode_graceful_restart.py --self-test <cwd>` → 失敗判定（可視ウィンドウ未生成、helper 增加のみ）。欠陥3を実証。
- スクラッチ検証スクリプト（`docs/ai/tmp/`）:
  - `window_probe.py`（read-only）→ `visible=0` の helper を区別
  - `wmclose_probe.py` → `SendMessageW -> 0`（helper・閉じず）、`PostMessageW -> 1`（helper・閉じず）
  - `wmclose_visible_test.py` → 可視ウィンドウは WM_CLOSE で閉じた
- 本タスクは docs のみ変更（コード変更なし）→ pytest / build 不要（AGENTS.md 例外）。

## 残存

- self-test が作成した不可視 helper ウィンドウ（hwnd `0x50d7a`）が未クローズで残存。ユーザーのウィンドウへの影響なし。

## 完了時 Memory Bank 操作

- [ ] `current-task.tsv` の参照行を削除
- [ ] 解決した `known-issues/` ファイルを `known-issues/archive/` へ `mv`（該当する場合）
- [ ] `backlog.md` の完了項目を削除（該当する場合）
