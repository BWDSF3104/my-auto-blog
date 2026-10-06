# 2-pass生成メタデータ追跡 (2026-10-06)

## 概要

記事生成の2-pass（下書き→精製）プロセスのメタデータをJSONとして保存し、
後から1回目と2回目の差異を追跡・分析できるようにした。

## 背景

- ストーリー系プロンプトでは2-pass生成（下書き + 精製）を実施
- 1回目の下書きと2回目の精製結果の差異を後から確認できない状態だった
- 精製プロセスの効果測定のため追跡機能が必要

## 変更

### generate_article.py

- `generate_content_with_retry()`: 返り値を `response` → `(response, model_name)` タプルに変更
- `refine_content()`: 返り値を `str` → `(refined_content, model_name)` タプルに変更
- 新規 `DRAFTS_DIR = "data/drafts"` 定数追加
- 新規 `_save_draft_metadata()` 関数追加
- `generate_post()`: 1回目・2回目の経過時間を計測し、メタデータ保存を呼び出し

### 保存フォーマット (`.kilo/drafts/<timestamp>.json`)

```json
{
  "timestamp": "2026-10-06-120000",
  "prompt_type": "kemono_story",
  "article_file": "2026-10-06-120000-auto-post.md",
  "pass1": {
    "model": "gemini-3.8-flash",
    "duration_seconds": 12.5,
    "content_char_count": 15000,
    "content_line_count": 300,
    "content": "..."
  },
  "pass2": {
    "model": "gemini-3.8-flash",
    "duration_seconds": 10.2,
    "content_char_count": 16000,
    "content_line_count": 310,
    "content": "..."
  },
  "diff_stats": {
    "char_count_change": 1000,
    "line_count_change": 10,
    "char_count_change_percent": 6.67
  }
}
```

### テスト

- `TestSaveDraftMetadata` クラス追加（6件）
  - JSONファイルの保存
  - pass1/pass2情報の記録
  - 差分統計の計算
  - ディレクトリの自動作成
  - 行数カウントの正確性

## 検証

- `pytest scripts/tests/ -v`: 161 passed (1.90s)
- `npm run build`: 成功 (114ページ、2.90s)

## 今後の予定

- ドラフトファイルとトレンドファイルを一定期間でクリーンする処理

## Status

完了
