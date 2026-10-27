# 2026-10-13: キャラクター・テーマ被り防止セクションのトグル化（デフォルトOFF）

**Status**: 完了（2026-10-13）
**Next Action**: なし

## 概要

ユーザー要望: プロンプトの【キャラクター・テーマ被り防止】セクションをオン・オフ可能にし、デフォルトはオフとする。
理由: キャラクター・テーマのランダム化がPythonスクリプト側（`_randomize_kemono_params`）で実装済みのため、プロンプト側の被り防止指示は不要になった。

## 変更内容

- `scripts/article/config.py`:
  - 新定数 `ENABLE_CHAR_DEDUP = os.environ.get("ENABLE_CHAR_DEDUP", "0") == "1"`（デフォルトOFF、`ENABLE_CHAR_DEDUP=1` でON）
  - `__all__` に追加
- `scripts/generate_article.py`:
  - `build_ng_instruction`: キャラ・被り防止ブロックを `ENABLE_CHAR_DEDUP and recent_metas and ...` でゲート（generate_article.py:153）
  - `generate_post`: トグルOFF時は `get_recent_meta_by_type()` のファイルI/O自体をスキップ（`recent_metas = []`）
- `scripts/tests/test_generate_article.py`:
  - `TestBuildNgInstruction` 新增（5テスト）: OFF時セクション除外 / ON時セクション付与 / 非物語系はONでも除外 / メタ空は除外 / 入力空は空文字列
  - 定数パッチ先は `generate_article.ENABLE_CHAR_DEDUP`（定数を読むコードが所在するモジュール、AGENTS.md 規則）

## 影響

- 【直近の執筆作品（テーマ・展開被り防止）】セクション（タイトルベース）は不変（常時ON）
- 変更されたのは【キャラクター・テーマ被り防止】セクション（character_1/2・art_style・tags を列挙するブロック）のみ
- 次回以降の生成プロンプトログ（`data/prompt_logs/`）にキャラ詳細ブロックが出力されなくなる

## Verification

- `python -m pytest scripts/tests/ -v` → 370 passed（約7秒、新規5テスト含む）
- `TestBuildNgInstruction` 単独実行 → 5 passed
- Python変更のため pytest 実施必須（AGENTS.md 規則）。Astro変更なし → build 不要

## 備考

- `.env` への `ENABLE_CHAR_DEDUP` 追記は不要（既定OFFで動作）。有効化したい場合は `.env` に `ENABLE_CHAR_DEDUP=1` を追加
