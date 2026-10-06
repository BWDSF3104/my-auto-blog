# タスク: kemono_story プロンプトのPython側ランダム化

 開始日: 2026-10-05
 Status: 完了

## 内容

 `kemono_story.txt:2-4` のハードコード済みテーマ指定をPython側で重み付きランダム選択して注入する形式に置き換える。

## 変更対象

- `scripts/prompts/kemono_story.txt`: 2-4行目をプレースホルダに置換
- `scripts/generate_article.py`: ランダム選択関数 + 重み定数 + format() 変数追加

## ランダム化項目

| # | 項目 | 選択肢 | 重み |
|---|------|--------|------|
| 1 | char_type | anthro, semi-anthro, feral, 複合5種 | 定義済み |
| 2 | world_setting | fantasy, sf, slice_of_life, fantasy+sf | 定義済み |
| 3 | transform | none, tf, tsf, tf+tsf | 定義済み |
| 4 | relationship | partnership, yaoi, yuri, hetero | 定義済み |
| 5 | extra | none, clone, rival | 定義済み |
| 6 | char_count | 1 (clone時のみ), 2 | 定義済み |

## 実装詳細

### 追加関数

- `_is_valid_kemono_combination(transform, relationship, extra)`: 無効な組み合わせのフィルタ（clone+hetero+tsfなしを禁止）
- `_randomize_kemono_params()`: 6項目の重み付きランダム選択 + バリデーション再試行（最大100回）

### 追加定数

- `CHAR_TYPE_WEIGHTS`, `WORLD_SETTING_WEIGHTS`, `TRANSFORM_WEIGHTS`
- `RELATIONSHIP_WEIGHTS`, `EXTRA_SETTING_WEIGHTS`, `CHAR_COUNT_WEIGHTS`
- `_KEMONO_WORLD_TEXT`, `_KEMONO_TRANSFORM_TEXT`, `_KEMONO_RELATIONSHIP_TEXT`
- `_KEMONO_EXTRA_TEXT`, `_KEMONO_CHAR_COUNT_DESC_1`, `_KEMONO_CHAR_COUNT_DESC_2`

### char_count の制約

- `extra == "clone"` の場合のみ `char_count` が 1 になる可能性がある（40%確率）
- それ以外の場合は常に `char_count == 2`
- `char_count_desc` は 1人の場合は "クローン", 2人の場合は "バディ"/"ライバル"/"カップル" からランダム選択

## Next Action

- [x] plans.md に Active Plans を追加
- [x] kemono_story.txt のテンプレート修正 (プレースホルダ置換完了)
- [x] generate_article.py に重み定数を追加 (6項目の定数定義完了)
- [x] generate_article.py にランダム選択関数を追加
- [x] template.format() に新変数を追加
- [x] pytest 確認 (155 passed)
- [x] npm run build 確認 (110ページ成功)

## Verification

- `pytest scripts/tests/ -v`: 155 passed (1.61s)
- `npm run build`: 成功 (110ページ、9.80s)
- commit: `2804bfd`
