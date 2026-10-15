# 画像プロンプト精査（非固定部分）

Geminiが生成する art_style / character / situation の精査・改善記録。
対象: `kemono_story.txt` のみ（`default.txt` / `ai_deep.txt` は後日水平展開）

## プロンプト合成構造

```
compose_image_prompt() の出力:
  BASE_QUALITY_PROMPT(6) + art_style(3-5) + count_tag(1) + character(5-8) + situation(6-10)
  = 合計 21-30タグ（改善後）
```

### 1boy / 1girl の2層構造

`compose_image_prompt()` は既に Danbooru 準拠の2層構造を実装済み。

**内部データ**（Frontmatterのcharacter定義）:
```
character_1: "1boy, wolf anthro, navy fur, amber eyes, red scarf"
character_2: "1girl, fox anthro, white fur, green eyes, leather vest"
```
各キャラクターに性別タグを付与（内部でA→boy, B→girlの対応を保持）

**最終出力**（合成プロンプト）:
```
BASE_QUALITY_PROMPT, art_style, 1boy, 1girl, wolf anthro, navy fur..., fox anthro, white fur..., situation
```
- 各キャラの先頭から `1boy` / `1girl` を除去
- 全体のカウントタグ（`2boys`, `1boy, 1girl`, `2girls` など）を計算して挿入
- Danbooruのカウンタータグとして正しい位置に配置

**結論**: 内部設計は既に最適。テンプレートの指示を整理すればよい。
