# 静的監査バグ修正 - 残り3件

**Date**: 2026-10-02
**Status**: 解決済

ソースコードの静的解析で発見した残りの Low バグ 3 件を修正。テスト134件全件通過、ビルド成功を確認。

- **L-4** `fetch_topics.py` の相対パス: `TOPICS_DIR = os.path.join("data", "topics")` が CWD 変更時に失敗した。`PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))` を追加して絶対パスに変更。
- **L-5** `generate_article.py` の相対パス: `TOPICS_DIR` と `TOPICS_JSON_PATH` が CWD 変更時に失敗した。`PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))` を追加して絶対パスに変更。`_auto_fetch_topics` の subprocess 呼び出しも修正。
- **L-6** `collect_bluesky` の URI 解析: 空の URI で `uri.split(':')[-1]` が空文字列を返し、無効な URL が生成された。空 URI チェックと rkey の空チェックを追加。
- **L-7** `_is_nsfw_post` の `non_consecutive`: NSFW タグセットに `non_consecutive` が含まれており、e621 のメタタグを誤って NSFW としてフィルタしていた。セットから削除。
