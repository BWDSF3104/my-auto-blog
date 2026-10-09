# ジャンル事前スコアリングを記事生成フローに統合

- 日付: 2026-10-09
- 関連: `2026-10-09-clef-flash-genre-score.md`（独立CLI実装）

## 背景

Clef-flash ジャンルスコアリングの独立CLI（`genre_score.py`）が完成したが、記事生成フローへの統合が未実装だった。
トレンド選択（`_append_trending_topics`）と版権選択（`_load_character_features`）がランダム選出のみで、
世界設定（world_setting）のジャンルとトレンド・版権の関連度を利用できていなかった。

## 実装内容

### `scripts/genre_score.py`
- `score_topics()` 関数追加: `data/topics/latest.json` の全トレンド + `data/character_features.json` の版権を
  Clef-flash で事前スコアリング → `data/genre_scores/topics.json` に保存
- 個別API失敗時は `scores: null` で保存し、残りアイテムのスコアリング継続

### `scripts/generate_article.py`
- `WORLD_SETTING_GENRE_MAP` 定数追加:
  - `fantasy → [fantasy]`
  - `sf → [sf]`
  - `slice_of_life → [action]`
  - `fantasy+sf → [fantasy, sf]`
- `_load_genre_scores()`: `data/genre_scores/topics.json` 読み込み（不存在・破損時は `{}`）
- `_filter_by_genre()`: ジャンル適合度（target_genres の max）でソート、未登録は末尾保持
- `_append_trending_topics(target_genres=...)`: 新パラメータ。事前スコアでジャンル適合度が高いトレンドを優先選択
  - スコアファイル不存在時は従来のランダム2件選択にフォールバック
- `_load_character_features(target_genres=...)`: 新パラメータ。版権リストをジャンル適合度で優先順にソート
  - スコアファイル不存在時は従来の頻度降順にフォールバック
- **生成フロー順序変更**（`generate_post`）:
  - 従来: `_append_trending_topics` → `_randomize_kemono_params`
  - 変更: `_randomize_kemono_params`（world_setting 決定）→ `_append_trending_topics`（ジャンル優先選択）

### 運用フロー
```
fetch_topics.py → genre_score.py score_topics → generate_article.py
```
`score_topics()` は `fetch_topics.py` 実行後に1回调用（日次、キャッシュTTL 7日で自動更新）。

### 失敗時動作（グレースフルデグラデーション）
| 失敗箇所 | 影響 |
|---|---|
| API 全滅 | `topics.json` 全件 `scores: null` → 生成時はランダム選択 |
| `topics.json` 未作成 | `_load_genre_scores()` → `{}` → ランダム選択 |
| 1件だけ失敗 | その件だけ末尾配置、他はジャンル優先 |

## Verification (2026-10-09)

- `pytest scripts/tests/` → **285 passed** (3.87s)
  - `test_genre_score.py`: TestScoreTopics 5テスト追加（全71）
  - `test_generate_article.py`: 統合テスト14テスト追加（全190）

## Commits

- `d8d3e7d` feat: Clef-flash ジャンル事前スコアリングを記事生成フローに統合
- `670051a` test: ジャンル事前スコアリング統合テスト追加（14テスト・全285通過）
