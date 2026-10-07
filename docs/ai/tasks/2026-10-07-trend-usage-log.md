# #8 trend_usage ログの欠落調査 (2026-10-07)

## 概要
`_save_trend_usage_log()` が kemono_story モードで正しく実行されているか調査。

## 調査結果

### 1. ディレクトリ存在確認
- `data/trend_usage/`: **存在しない**
- `data/topics/latest.json`: 存在する ✓

### 2. 実装内容
- `generate_article.py:1464-1475`: `_save_trend_usage_log()` 実装済み
- `os.makedirs(TREND_USAGE_DIR, exist_ok=True)` でディレクトリ自動作成
- 出力先: `data/trend_usage/{timestamp}.json`

### 3. 呼び出しパス
- `generate_post()` (L2354) → `_append_trending_topics()` (L2408) → `_save_trend_usage_log()` (L1657)
- 全 `prompt_type` で共通パス（kemono_story も含む）

### 4. 問題の特定

**根本原因: 早期リターンでログがスキップされる**

`_append_trending_topics()` 内に2つの早期リターンがあり、どちらも `_save_trend_usage_log()` を呼ばずに関数を終了する:

1. **L1548-1550**: `TOPICS_JSON_PATH` が存在しない場合
   ```python
   if not os.path.exists(TOPICS_JSON_PATH):
       return ng_instruction, [], []  # ← ログ保存なし
   ```

2. **L1552-1557**: JSON読み込み失敗時
   ```python
   except Exception as e:
       return ng_instruction, [], []  # ← ログ保存なし
   ```

**追加問題: CIでのログコミット漏れ**

`.github/workflows/deploy.yml:L77`:
```yaml
[ -d "data/trend_usage" ] && git add data/trend_usage/
```
ディレクトリが存在する場合のみコミット。ディレクトリが作成されていても空の場合はコミットされない。

### 5. 修正案（両方実施予定）

**A. 早期リターンにもログを保存**

L1548-1550 と L1552-1557 の直前に `_save_trend_usage_log()` を呼び出して「データ未取得」状態を記録。

**修正箇所: generate_article.py:1548-1557**

**変更前:**
```python
    if not os.path.exists(TOPICS_JSON_PATH):
        print(f"[topics] {TOPICS_JSON_PATH} が見つかりません。トレンド注入をスキップします。")
        return ng_instruction, [], []

    try:
        with open(TOPICS_JSON_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"[topics] JSON 読み込み失敗: {e}")
        return ng_instruction, [], []
```

**変更後:**
```python
    if not os.path.exists(TOPICS_JSON_PATH):
        print(f"[topics] {TOPICS_JSON_PATH} が見つかりません。トレンド注入をスキップします。")
        _save_trend_usage_log({
            "timestamp": datetime.now(timezone(timedelta(hours=9))).isoformat(),
            "prompt_type": prompt_type,
            "status": "skipped",
            "reason": "topics_json_not_found",
            "data_file": TOPICS_JSON_PATH,
        })
        return ng_instruction, [], []

    try:
        with open(TOPICS_JSON_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"[topics] JSON 読み込み失敗: {e}")
        _save_trend_usage_log({
            "timestamp": datetime.now(timezone(timedelta(hours=9))).isoformat(),
            "prompt_type": prompt_type,
            "status": "skipped",
            "reason": "json_load_failed",
            "error": str(e),
            "data_file": TOPICS_JSON_PATH,
        })
        return ng_instruction, [], []
```

**B. CIコミットを確実化**

`data/trend_usage/` に `.gitkeep` を配置し、ディレクトリが空でもコミットされるようにする。

**実装:**
- `data/trend_usage/.gitkeep` ファイルを作成
- CIワークフローの git add を `git add data/trend_usage/` に変更（存在チェック不要になる）
