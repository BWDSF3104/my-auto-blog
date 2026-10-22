# 記事生成パイプライン調査 (2026-10-06)

## 概要

最新2記事（2026-10-06-224637, 2026-10-06-223208）の生成結果を分析し、
e621/trendデータの反映度と生成パイプラインの問題点を特定した。

## 調査対象

- 記事1: `2026-10-06-224637-auto-post.md`「琥珀の時計塔と星屑の庭師」
- 記事2: `2026-10-06-223208-auto-post.md`「翠玉の羅針盤と琥珀の砂時計」
- 注入データ: `data/character_features.json`, `data/topics/latest.json`
- 生成コード: `scripts/generate_article.py`
- プロンプト: `scripts/prompts/kemono_story.txt`, `scripts/prompts/refine_story.txt`

---

## e621/Trendデータの反映度分析

### データフロー

| データ源 | 注入関数 | 注入先 | 記事への影響 |
|----------|----------|--------|-------------|
| `character_features.json` | `_load_character_features()` | `{character_features_instruction}` | キャラクター外見定義 |
| `latest.json` (kemonoカテゴリ) | `_append_trending_topics()` | `ng_instruction` 末尾 | ストーリーインスピレーション |
| Python定数 | `_randomize_kemono_params()` | `{char_type}` | キャラクター種族 |

### 反映度

| データ源 | 反映度 | 詳細 |
|----------|--------|------|
| e621 character_features (species/colors/physical) | **高い** | キャラクターの種族・色・身体的特徴がe621高頻出タグと一致 |
| e621 character_features (artists) | **高い** | art_style がe621人気artist（cobalt_snow）から選択 |
| e621 character_features (copyrights) | **中** | アフィリエイト製品推薦にBEASTARS, どうぶつの森など |
| e621 trend topics (latest.json) | **なし** | story_modeで除外(1606行)、ストーリーテーマに影響なし |
| 非e621 trend topics (GitHub/RSS) | **ほぼなし** | score=0〜1のニュースが選択されてもストーリーに反映されない |

### 具体例

**art_style: cobalt_snow**
- character_features.json で4投稿（最高頻出artist）
- 2記事連続で選択されている

**種族: fox, deer, cat**
- e621集計: fox(8件), deer(4件), feline(3件) → 高頻出種族と一致

**色: amber eyes, green eyes, russet/tan fur**
- e621集計: yellow_eyes(5件), green_eyes(4件), brown_fur(6件) → 高頻出カラーと一致

---

## 問題点一覧

### 記事系

#### 1. 英語用語の漏れ（本文・description）

**症状:**
- 記事1: 「アントロポモルフであるシオン」「アントロポモルフであるルセット」
- 記事2: 「フェラルの赤ギツネであるルキウス」、description に「フェラルなキツネの探求者」

**根本原因:**
- `CHAR_TYPE_WEIGHTS` 定数（`generate_article.py:56-63`）が "anthro", "feral", "semi-anthro" を英語で保持
- `{char_type}` として英語のままプロンプトテンプレートに注入
- テンプレート内に日本語翻訳の指示がない
- `refine_story.txt` に言語整合性のルールがない

**修正箇所:** `CHAR_TYPE_WEIGHTS`, `kemono_story.txt`, `refine_story.txt`

---

#### 2. 表現の繰り返し

**症状:**
- 記事1: 「脳裏をよぎった」
- 記事2: 「脳裏を駆け巡る」「脳裏をよぎった」
- 「喉から〜声が漏れた」のパターンが共通

**根本原因:**
- AIの訓練データ由来の表現パターンが固定化
- 精製プロセスで表現の多様性を強制するルールがない

**修正箇所:** `refine_story.txt`

---

#### 3. trend topics の実質的な無効化

**症状:**
- kemono_story モードでは e621 投稿が除外（`generate_article.py:1606-1607`）
- 残る候補は score=0〜1 の GameSpot RSS, IGN RSS, Anime News Network
- ストーリーテーマ（時計塔、遺跡など）に trend データが反映されていない

**根本原因:**
- e621 除外後にストーリーインスピレーションとして意味のある代替データ源がない
- RSSニュースはゲーム・アニメ業界ニュースであり、ファンタジーストーリーのインスピレーションにならない

**修正箇所:** `fetch_topics.py`（データ源追加）、`generate_article.py:1559-1607`（カテゴリ選択ロジック）

---

#### 4. e621 データの過度な依存（キャラクター定義）

**症状:**
- art_style が `cobalt_snow` 2記事連続（e621 人気artist から選択）
- 種族・色・身体的特徴が e621 の高頻出タグと一致

**根本原因:**
- `_load_character_features()` が e621 投稿データを raw English タグのまま注入
- 代替のキャラクター定義データ源がない

**修正箇所:** `generate_article.py:522-604`（`_load_character_features()`）

---

### アフィリエイト系（生成AI作成）

#### 5. 架空の商品名

**症状:**
- 記事1: 「琥珀の時計塔 限定エディション フィギュア」「星屑の庭師 公式アートブック」
- 記事2: 「古代文明 失われた遺跡 公式ガイドブック」

**根本原因:**
- プロンプトで「実在する商品」と指示しているが、AI が物語テーマから商品名を捏造
- 精製プロセスに商品検証のステップがない

**修正箇所:** `kemono_story.txt`（product_recommendations 指定ルール）、`refine_story.txt`

---

#### 6. アフィリエイト製品推薦の汎用化

**症状:**
- 2記事とも「ケモノ 図鑑」が重複
- 記事1: 「ライトノベル おすすめ」
- 記事2: 「Feral 関連作品」
- 記事の具体的なテーマ（時計塔、遺跡、羅針盤など）と関連性がない

**根本原因:**
- ストーリー本文から製品推薦への橋渡しが弱く、AI が安全策として汎用キーワードを選択
- e621 copyrights から BEASTARS, どうぶつの森 などは選択されるが、それ以外は具体性に欠ける

**修正箇所:** `kemono_story.txt`（product_recommendations 指定ルール）

---

### アフィリエイト系（Pythonスクリプト作成）

#### 7. アフィリエイトキーワードの英語混在

**症状:**
- 記事2: 「Feral 関連作品」(Amazon/楽天検索リンク)

**根本原因:**
- `_extract_affiliate_keyword()` がタグからキーワードを抽出する際、`char_type` 由来の英語タグ ("Feral") がそのままキーワードになる
- 日本語化の処理がない

**修正箇所:** `generate_article.py:1697-`（`_extract_affiliate_keyword()`）、`inject_affiliate_links` 関数

---

### 運用系

#### 8. 運用ログの欠落

**症状:**
- `data/trend_usage/` ディレクトリが存在せず、trend usage log が保存されていない
- どのトレンドデータが注入されたかの追跡が不可能

**根本原因:**
- `_save_trend_usage_log()` がディレクトリ作成に失敗している、または以前のクリーンアップで削除された

**修正箇所:** `generate_article.py:1462-1475`（`_save_trend_usage_log()`）

---

## 優先度別サマリー

| 優先度 | 分類 | 問題 | 修正箇所 |
|--------|------|------|----------|
| **高** | 記事系 | 英語用語の漏れ | `CHAR_TYPE_WEIGHTS`, テンプレート |
| **高** | アフィリエイト(AI) | 架空の商品名 | `kemono_story.txt` |
| **中** | 記事系 | trend topics 無効化 | `fetch_topics.py`, カテゴリ選択ロジック |
| **中** | アフィリエイト(AI) | 製品推薦の汎用化 | `kemono_story.txt` |
| **中** | アフィリエイト(Python) | キーワードの英語混在 | `_extract_affiliate_keyword()` |
| **低** | 記事系 | e621 過度依存 | `_load_character_features()` |
| **低** | 記事系 | 表現の繰り返し | `refine_story.txt` |
| **低** | 運用系 | ログの欠落 | `_save_trend_usage_log()` |
