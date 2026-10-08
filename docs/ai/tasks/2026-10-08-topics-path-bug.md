# トレンドデータ読み込みパス不一致バグ修正 (2026-10-08)

**状態: 完了 (2026-10-08)**

## 概要
`generate_article.py` がトレンドデータ `latest.json` を `scripts/data/topics/`（存在しない）から読むようになり、`fetch_topics.py` が書き込む `data/topics/`（リポジトリ直下）と不一致。2026-10-02 のコミット `2b4a815`（静的解析修正「相対パスを絶対パス化」）で `PROJECT_DIR` を `scripts/` 自身に設定した際の退行。以降の全記事生成でトレンド注入がサイレント無効化（`skipped: "file_not_found"`）されていた。

楽天API商品リンク連携タスク中の最新記事キーワード調査で発見。リンク生成の範囲と被らないため、別タスクとして切り出して先に修正した。

## 原因
- `generate_article.py:1342`: `PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))` → `scripts/` を指す
- `generate_article.py:1343`: `TOPICS_DIR = os.path.join(PROJECT_DIR, "data", "topics")` → `scripts/data/topics/`（存在しない）
- 一方 `fetch_topics.py:41`: `PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))` → リポジトリ直下、`TOPICS_DIR = <root>/data/topics/`
- 履歴: `dfdabff` まで CWD 相対パス `data/topics`（ワークフローはリポジトリ直下実行で動作）→ `2b4a815` が絶対パス化し `scripts/` 基準にずれ

## 影響範囲
- プロンプトへのトレンドタイトル注入（`_append_trending_topics`）
- アフィリエイト末尾セクションのトレンドキーワード補完（B系・`inject_affiliate_links` の2番目）
- 自動再取得（`_auto_fetch_topics`）は `scripts/fetch_topics.py` を正しく起動していた（PROJECT_DIR=scripts/ 基準で誤って正しく機能していた）

## 証拠
- `data/trend_usage/2026-10-08-113611.json`: `"skipped": "file_not_found"`、`data_file: .../scripts/data/topics/latest.json`
- リポジトリに `scripts/data/topics/` ディレクトリが存在しないこと
- `git log -L 1342,1343:scripts/generate_article.py` で `2b4a815` の差分確認済み

## 修正内容
1. `generate_article.py:1342`: `PROJECT_DIR` をリポジトリ直下に変更（`fetch_topics.py:41` と同じ `dirname(dirname(abspath(__file__)))` 方式）
2. `generate_article.py:1437`: 自動再取得の `fetch_topics.py` 起動パスを `os.path.join(PROJECT_DIR, "scripts", "fetch_topics.py")` に修正（PROJECT_DIR 変更による相殺）
3. テスト: `_append_trending_topics` が `data/topics/latest.json` を読むことを確認するテストを追加（モック）

## Verification
- [x] `pytest scripts/tests/ -v` 全テスト通過 (2026-10-08)
