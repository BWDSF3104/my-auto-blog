# 画像プロンプト精査（非固定部分）

Geminiが生成する art_style / character / situation の精査・改善記録。
対象: `kemono_story.txt` のみ（`default.txt` / `ai_deep.txt` は後日水平展開）

## プロンプト合成構造

```
compose_image_prompt() の出力:
  BASE_QUALITY_PROMPT(8) + art_style(3-5) + count_tag(1) + character(5-7) + situation(6-10)
  = 合計 23-31タグ（改善後）
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

## art_style 精査

### 現状
- テンプレート例（27行目）: `"watercolor, soft pastel, gentle lighting"` / `"pixel art, retro, 16-bit style"`
- デフォルト（generate_article.py）: `"anime style, illustration, cel shading, vibrant colors"` (5タグ)
- 最新記事実例: `"painterly, soft atmospheric light, rich textures, fantasy illustration, cinematic lighting"` (5タグ)

### 問題
| タグ | 問題 |
|---|---|
| `painterly` | Danbooruタグではない。`painting` が正しい |
| `soft atmospheric light` | 2語の自然言語。`soft lighting` または `atmospheric lighting` |
| `rich textures` | 認識率低。削除推奨 |
| `fantasy illustration` | `illustration` だけで十分 |
| `cinematic lighting` | 有効だが長め。維持可 |

### 修正候補A（kemono_story.txt 27行目）

**現状**:
```
・art_styleにはこの記事の画像に適用するアートスタイルを英語で指定してください（例: "watercolor, soft pastel, gentle lighting" や "pixel art, retro, 16-bit style"）。記事内の全画像はこのスタイルで統一されます。
```

**修正後案**:
```
・art_styleにはこの記事の画像に適用するアートスタイルを英語で指定してください。3-5タグ程度に簡潔にしてください。
  例: "anime style, illustration, cel shading, vibrant colors" や "digital painting, dramatic lighting, rich colors"
  記事内の全画像はこのスタイルで統一されます。
```

**変更点**:
- タグ数の推奨範囲（3-5）を明記
- 例の `soft pastel, gentle lighting` → `dramatic lighting, rich colors`（Danbooru互換に寄せる）

## character_1 / character_2 精査

### 現状
- テンプレート例（70-71行目）: `"1boy, blue wolf, golden eyes, white chest fur, wearing red scarf"` (6タグ)
- ルール（87-92行目）: 性別＋種族＋身体特徴＋象徴的な服装・アクセサリ
- 最新記事実例: `"1boy, wolf anthro, dark navy fur, amber eyes, wearing a white shirt, leather vest, monocle over left eye"` (8タグ)

### 問題
| 項目 | 問題 |
|---|---|
| `wolf anthro` | `anthro` は維持（feral/semi-anthroとの入れ替え形式） |
| `dark navy fur` | 2語の修飾。`navy fur` で十分 |
| `wearing a white shirt` | 自然言語。`white shirt` に簡略化 |
| 服装タグの多さ | 3タグ（shirt, vest, monocle）。1-2タグに集約 |

### 1boy / 1girl の扱い

Danbooruの `1boy` / `1girl` は「画像中に何人いるか」のカウンタータグ。
キャラクターごとに付与するのではなく、画像全体の人数として表現するのが正しい。

ただし、現在の設計では:
- 内部: 各characterに `1boy` / `1girl` を付与（性別の対応を保持）
- 出力: `compose_image_prompt()` が集約して全体カウントタグに変換

この設計は維持。テンプレートの指示を整理するだけでよい。

### 修正候補B（kemono_story.txt 87-92行目）

**現状**:
```
・性別（1boy, 1girl等）＋種族＋身体特徴（毛色、瞳など）＋象徴的な服装・アクセサリのみを英語で簡潔に記述してください。
・背景やシチュエーション、画質タグは含めないでください。
・外見はSFWにしてください。
・1人のみの物語の場合は character_2 を省略して構いません。
```

**修正後案**:
```
・性別（1boy, 1girl等）＋種族（例: wolf anthro, fox feral）＋身体特徴（毛色、瞳など）＋象徴的な服装・アクセサリ（1-2つ）のみを英語で簡潔に記述してください。
・服装・アクセサリは象徴的なもの1-2つに絞ってください（例: "red scarf" や "leather vest"）。
・5-8タグ程度にしてください。背景やシチュエーション、画質タグは含めないでください。
・外見はSFWにしてください。
・1人のみの物語の場合は character_2 を省略して構いません。
```

**変更点**:
- 種族の例に `wolf anthro, fox feral` を追加（anthro/feralの使い分けを示す）
- 服装・アクセサリを「1-2つ」に制限する明記
- タグ数の推奨範囲（5-8）を明記

## situation（image_prompt / IMAGE_PROMPT）精査

### 現状
- テンプレート指示（25行目）: 「ポーズや背景を英語で記述」
- テンプレート例（72行目）: `"[character_1, character_2] intense face-to-face confrontation, dramatic lighting, emotional"`
- テンプレート例（103行目）: `"[character_1, character_2] sharing an intimate moment, close contact, emotional expression"`
- テンプレート例（109行目）: `"[character_1, character_2] fierce battle scene, dynamic action, dramatic effects"`
- 最新記事実例: `"inside an antique shop, wolf anthro inspecting an ornate mirror on a wooden desk, otter anthro with brass goggles leaning in curiosity, warm lantern lighting, cozy atmospheric interior"` (14語)

### 問題
| 項目 | 問題 |
|---|---|
| 自然言語文 | `inside an antique shop` → `antique shop interior` |
| 所有格 | `otter anthro's body` → `otter body` |
| 長さの不安定 | 10-15語。制約がない |
| 前置詞の多さ | `inside`, `on`, `with`, `at` が無駄 |
| 現在分詞 | `inspecting`, `leaning`, `reaching` → 名詞形に簡略化可能 |

### 修正候補C（kemono_story.txt 25行目 + 41-42行目 + 103行目 + 109行目）

**現状（25行目）**:
```
・画像プロンプトでは、登場させたいキャラクターのID（例: [character_1] または [character_1, character_2]）を先頭に必ず指定し、続けてそのシーンのポーズや背景を英語で記述してください。
```

**修正後案（25行目）**:
```
・画像プロンプトでは、登場させたいキャラクターのID（例: [character_1] または [character_1, character_2]）を先頭に必ず指定し、続けてそのシーンのキーワードをカンマ区切りで記述してください。6-10語程度に簡潔にしてください。
```

**修正後案（41-42行目）**:
```
  挿入形式：<!-- IMAGE_PROMPT: "[character_1] keyword, keyword, keyword" -->
  または（2人登場時）：<!-- IMAGE_PROMPT: "[character_1, character_2] keyword, keyword, keyword" -->
```

**修正後案（103行目）**:
```
<!-- IMAGE_PROMPT: "[character_1, character_2] intimate moment, close contact, emotional expression, warm lighting" -->
```

**修正後案（109行目）**:
```
<!-- IMAGE_PROMPT: "[character_1, character_2] fierce battle, dynamic action, dramatic effects, energy burst" -->
```

## 共通: Danbooru互換タグの全体指示

### 修正候補D（kemono_story.txt 21行目付近への新規追加）

**追加案**（【キャラクターの一貫性と画像プロンプトのルール】の冒頭に追加）:
```
【画像プロンプトのキーワード形式】
・art_style, character_1/2, image_prompt, IMAGE_PROMPT のキーワードは、なるべく Danbooru 互換のタグ形式を使用してください。
・自然言語的な表現（例: "wearing a red scarf", "inside an antique shop"）は避けて、簡潔なキーワード（例: "red scarf", "antique shop interior"）にしてください。
```

## テンプレート修正対象まとめ

| 行番号 | 項目 | 修正候補 |
|---|---|---|
| 21付近 | 新規: Danbooru互換タグの全体指示 | D |
| 27 | art_style 生成指示 | A |
| 25 | IMAGE_PROMPT situation 指示 | C |
| 41-42 | IMAGE_PROMPT 挿入形式の例 | C |
| 87-92 | character 生成指示 | B |
| 103 | IMAGE_PROMPT 例（挿絵1） | C |
| 109 | IMAGE_PROMPT 例（挿絵2） | C |

---

## Python側ランダム化設計

プロンプト内の「ランダムに選択してください」指示を、Python側で事前決定してプロンプトに注入する設計。

### 方針

- 案A（重み付き選択）を採用
- `none` が選ばれる確率が低すぎないよう重み調整
- 3つすべての組み合わせは現実的ではないため除外
- semi-anthro は e621 の定義に基づく（コード・プロンプトには意味の説明を記載しない）

### ランダム化項目

#### 1. キャラクタータイプ（char_type）

```python
CHAR_TYPE_WEIGHTS = [
    ("anthro", 30),           # 30%
    ("semi-anthro", 20),      # 20%
    ("feral", 20),            # 20%
    ("anthro+semi-anthro", 10), # 10%
    ("anthro+feral", 10),     # 10%
    ("semi-anthro+feral", 10), # 10%
]
```

注入: `ケモノ（{char_type}）キャラクターたちが活躍する...`
例: `anthro+feral` → `ケモノ（anthro・feral）キャラクターたちが活躍する...`

#### 2. 世界観（world_setting）

```python
WORLD_SETTING_WEIGHTS = [
    ("fantasy", 35),       # 35%
    ("sf", 20),            # 20%
    ("slice_of_life", 25), # 25%
    ("fantasy+sf", 20),    # 20%
]
```

注入: `...{world_setting}{transform}から単一または複数のテーマを選択し...`

#### 3. トランスフォーメーション（transform）

```python
TRANSFORM_WEIGHTS = [
    ("none", 40),   # 40%
    ("tf", 25),     # 25%
    ("tsf", 25),    # 25%
    ("tf+tsf", 10), # 10%
]
```

注入: `...{world_setting}{transform_text}から...`
例: `tf` → `、TF(変身・変形)` / `none` → `""`（空文字）

#### 4. 関係性（relationship）

```python
RELATIONSHIP_WEIGHTS = [
    ("partnership", 30),  # 30%
    ("yaoi", 25),         # 25%
    ("yuri", 25),         # 25%
    ("hetero", 20),       # 20%
]
```

注入: `{relationship_text}からランダムにテーマを選択してください。`
例: `yaoi` → `同性愛（男性同士の恋愛）`

#### 5. 追加設定（extra）

```python
EXTRA_SETTING_WEIGHTS = [
    ("none", 70),   # 70%
    ("clone", 20),  # 20%
    ("rival", 10),  # 10%
]
```

注入: `{relationship_text}{extra_text}からランダムにテーマを選択してください。`
例: `clone` → `、クローンによる自分同士` / `none` → `""`（空文字）

#### 6. キャラクター人数（char_count）

```python
CHAR_COUNT_WEIGHTS = [
    (1, 40),  # 40% (extra=clone時のみ使用)
    (2, 60),  # 60% (extra=clone時のみ使用)
]
_KEMONO_CHAR_COUNT_DESC_1 = ["クローン"]
_KEMONO_CHAR_COUNT_DESC_2 = ["バディ", "ライバル", "カップル"]
```

注入: `登場キャラクターは{char_count}人（{char_count_desc}）を中心に設定してください。`
- `extra != "clone"` の場合: 常に `char_count=2`
- `extra == "clone"` の場合: 重み付きランダムで 1または 2
- `char_count_desc`: 1人の場合は "クローン", 2人の場合は "バディ"/"ライバル"/"カップル" からランダム選択

### バリデーション

```python
def _is_valid_kemono_combination(transform, relationship, extra):
    """無効な組み合わせをフィルタ"""
    # clone + hetero は tsf がなければ不可（自分同士＝必然的に同性、TSFで一方転換すれば可）
    if extra == "clone" and relationship == "hetero" and "tsf" not in transform:
        return False
    return True
```

### 現在の2-4行目 → 注入後の置換

```diff
-ケモノ（獣人・アンthro・Feral）キャラクターたちが活躍するファンタジー、SF、TF(ジャンル）、TSF（性転換フィクション）、または日常などから単一または複数のテーマを選択し短編物語を作成してください。
-同性愛・異性愛・相棒関係・クローンによる自分同士などからランダムにテーマを選択してください。
-登場キャラクターは1人、または2人（バディ・カップル・ライバル等）を中心に設定してください。
+ケモノ（{char_type}）キャラクターたちが活躍する{world_setting}{transform_text}から単一または複数のテーマを選択し短編物語を作成してください。
+{relationship_text}{extra_text}からランダムにテーマを選択してください。
+登場キャラクターは{char_count}人（{char_count_desc}）を中心に設定してください。
```
