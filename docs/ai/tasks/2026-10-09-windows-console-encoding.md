# Windowsコンソールエンコーディング対策の統一 (2026-10-09)

**状態: 完了 (2026-10-09)**

## 概要
Pythonスクリプト実行時のコンソールエンコーディング問題（`UnicodeEncodeError: 'cp932' codec can't encode character`・日本語文字化け）の原因を特定し、既存の4パターンあるワークアラウンドを `TextIOWrapper.reconfigure()` 方式に統一した。

## 原因
- Python の stdio は**コンソール直結**なら `WindowsConsoleIO`（UTF-8対応）、**パイプ/リダイレクト**（Kilo CLI が出力をキャプチャするケース）なら**ロケール cp932** にフォールバックする
- コンソールのコードページ（`chcp 65001`）は対話端末のみ有効で、パイプされた Python 出力には無効（2026-10-09 実測: コンソール 65001 なのに `sys.stdout.encoding` = cp932）
- cp932 は絵文字（📷=`U+1F4F7`）等非収録文字で `UnicodeEncodeError`、cp932 バイト列が UTF-8 解读されると文字化け

## 既存ワークアラウンド4パターン
1. `fetch_topics.py:34-36`: `os.environ["PYTHONIOENCODING"] = "utf-8"`（**無効**=起動時のみ参照される env を実行時設定。子プロセスへの影響のみ）
2. `fetch_topics.py:543-548` / `test_real_apis.py:42-47`: `_safe_print()`（UnicodeEncodeError 時の cp932 変換フォールバック。動作はするが逐次的）
3. `fix_affiliate_links.py:24-25`: `io.TextIOWrapper` 差し替え方式（有効だが旧 stream 参照の分裂・二重ラッパーの恐れ）
4. `test_real_apis.py:33-36`: `reconfigure()` 方式（**正しい**=コードベースの既存の先例）

## 修正内容
`reconfigure()` 方式（パターン4）へ統一:
- `fetch_topics.py`: 無効な env 設定を reconfigure に置換（`_safe_print` は防御として維持）
- `generate_article.py`: reconfigure ブロック新設（絵文字多用の主要エントリでワークアラウンドなしだった）
- `fix_affiliate_links.py`: TextIOWrapper 差し替え → reconfigure に統一（`import io` 削除）
- `fix_descriptions.py`: reconfigure ブロック新設
- すべて `if sys.platform == "win32":` ガード付き、import 直後・最初の print 前に配置
- 対象外: `_` 接頭辞のアドホック診断スクリプト、`hf-space/app.py`（HF Space=Linux 実行・AGENTS.mdで不変）
- `docs/ai/workflow-test-procedure.md`: 「ローカル実行注意」セクション追加（`$env:PYTHONUTF8="1"` 現セッション設定・`python -X utf8` 1回限り代替）

## Verification
- [x] `python -m py_compile` 4ファイル OK
- [x] `pytest scripts/tests/ -v` → **200 passed** (3.41s)
- [x] スモークテスト: パイプ環境で `fetch_topics` import 後 `sys.stdout.encoding` = utf-8、絵文字出力 OK
