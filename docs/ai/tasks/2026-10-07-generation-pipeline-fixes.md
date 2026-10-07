# 生成パイプライン修正案 (2026-10-07)

**状態: 完了 (2026-10-07)**

## #1 英語用語漏れ (anthro/feral)

### 方向性
従来部分（CHAR_TYPE_WEIGHTS）を日本語化し、トレンドキャラクターデータ（character_features.json 由来）は英語のタグのまま維持。

### 日本語訳の決定

e621 body type タグは画像生成用の分類であり、そのまま直訳すると不自然。記事本文で自然な日本語に置き換える。

| e621タグ | 記事本文用 | 備考 |
|----------|-----------|------|
| anthro | 獣人 | 二足歩行の人型動物キャラクター |
| feral | 動物 | 四足歩行の動物そのものの形態 |
| semi-anthro | 動物と獣人のハーフ | 動物寄りだが獣人の要素も持つ |

### 修正箇所: generate_article.py:56-63

**変更前:**
```python
CHAR_TYPE_WEIGHTS = [
    ("anthro", 30),
    ("semi-anthro", 20),
    ("feral", 20),
    ("anthro+semi-anthro", 10),
    ("anthro+feral", 10),
    ("semi-anthro+feral", 10),
]
```

**変更後:**
```python
CHAR_TYPE_WEIGHTS = [
    ("獣人", 30),
    ("動物と獣人のハーフ", 20),
    ("動物", 20),
    ("獣人 / 動物と獣人のハーフ", 10),
    ("獣人 / 動物", 10),
    ("動物と獣人のハーフ / 動物", 10),
]
```

### 修正箇所: generate_article.py:184 (_randomize_kemono_params の返り値)

**変更前:**
```python
"char_type": char_type.replace("+", "・"),
```

**変更後:**
```python
"char_type": char_type,  # 既に日本語なので置換不要
```

### 修正箇所: kemono_story.txt:2

**変更前:**
```
ケモノ（{char_type}）キャラクターたちが活躍する
```

**変更後:**
```
{char_type}のキャラクターたちが活躍する
```

### 修正箇所: kemono_story.txt:90-95 (character_1/2 ルール)

**変更前:**
```
【character_1 / character_2 の指定ルール】
・性別（1boy, 1girl等）＋種族（例: wolf anthro, fox feral）＋身体特徴（毛色、瞳など）＋象徴的な服装・アクセサリ（1-2つ）のみを英語で簡潔に記述してください。
```

**変更後:**
```
【character_1 / character_2 の指定ルール】
・性別（1boy, 1girl等）＋種族（例: wolf, fox）＋anthro/feral/semi-anthroの種族タイプタグ＋身体特徴（毛色、瞳など）＋象徴的な服装・アクセサリ（1-2つ）のみを英語で簡潔に記述してください。
```

### 修正箇所: kemono_story.txt:73-74 (例の character_1/2)

**変更前:**
```
character_1: "1boy, blue wolf, golden eyes, white chest fur, red scarf"
character_2: "1boy, black panther, emerald eyes, leather vest"
```

**変更後:** そのまま維持（画像生成用であり英語が正しい）

### 修正箇所: kemono_story.txt:98-101 (product_recommendations)

**変更前:**
```
【product_recommendations の指定ルール】
・物語のテーマ・世界観に関連する「実在する」書籍・グッズ・関連商品を2〜3つ選定してください。
・各商品には `name`（具体名）, `category`（書籍, フィギュア, ゲーム, ソフトウェア, ガジェット等）, `price_range`（例: 1000円台, 3000円台, 無料）を指定してください。
・架空の商品名は使用しないでください。有名なタイトルや実際に販売されている商品を選んでください。
```

**変更後:** そのまま維持（#2は対応しない）

---

## #3 表現の繰り返し / 2passリファイン強化

### 方向性
原案がAI生成であるため、2passの役割を「最小限の校正」から「大筋を維持したままの質的向上」に変更。設定の補完、小さな繋ぎ场景の追加、論理的矛盾の解消を許可。

### 修正箇所: refine_story.txt（全体書き換え）

主要な変更点:
1. 「必要に応じて」を全箇所から除去
2. 過度な制限を除去（設定追加禁止、出来事追加禁止、補完禁止）
3. 大筋・章構成・主要キャラクターは維持するが、補完・改善を許可
4. 出力前の自己検証チェックリストを追加
5. 言語整合性のチェックを追加（anthro→獣人等）
6. ```markdown コードブロックの禁止を追加
7. キャラクター一貫性のチェックを具体化

**変更後の全体:**
```
あなたは商業小説の編集者兼校正者です。
以下の下書き小説を、読者が自然に没入できる完成度の高い文章へ精製してください。

【内部レビュー工程】
1. 全文を読む
2. 改善が必要な箇所を内部的に特定
3. 優先度を判断
4. 修正・補完を適用
5. 修正後に設定・構成・形式を再確認
6. 完成原稿のみ出力

【基本方針】
- まず全文を読み、改善すべき箇所を内部的に確認する。
- 物語の大筋、章構成、主要キャラクター、主題は維持する。
- 設定の不足は既存の情報から合理的に補完して構わない。
- 章と章の間の繋ぎや、場面の遷移が不自然な場合は適切な描写を追加して構わない。
- 文章量を増やすこと自体を目的としないが、不足している描写は充実させる。
- 原文の文体・雰囲気・ジャンル性を尊重する。

【1. 情景描写】
以下の問題がある場合、改善する。
- 場所や状況が想像しにくい
- 重要な場面なのに描写が不足している
- 視覚だけでなく、音、匂い、温度、触感などが有効なのに欠けている
ただし、すべての場面に五感描写を追加しない。重要場面を中心に、自然に追加する。

【2. Show, Don't Tell】
以下のような直接的な感情説明があり、動作・表情・反応によって自然に表現できる場合は改善する。
例: 「彼はとても緊張していた。」 → 手の震え、呼吸、視線、動作などによる表現へ変更する。
ただし、すべての感情説明を禁止しない。簡潔さや文体上必要な説明は維持する。

【3. 会話】
以下を確認し、問題がある箇所を修正する。
- キャラクターごとの口調・語彙・語尾が維持されているか
- 誰が話しているか分かりにくい箇所がないか
- 説明のためだけの不自然な会話になっていないか
- 会話のテンポが不自然になっていないか

【4. キャラクターの一貫性】
以下の矛盾を確認し、明確な矛盾がある場合、修正する。
- セリフの口調がそのキャラクターの性格・年齢・立場と一致しているか
- セリフの内容がそのキャラクターが知っているはずの情報を超えていないか
- 地の文の描写がそのキャラクターの設定（性格、能力、外見、人間関係）と矛盾していないか
- 一人称・二人称が章を通じて一定か

【5. ストーリーの論理的整合性】
以下の矛盾を確認し、明確な矛盾がある場合、修正する。
- 因果関係が破綻していないか
- 時間の流れが矛盾していないか
- 前章で確立された設定や状況と後章が矛盾していないか
- 物理的に不可能な状況になっていないか
矛盾の解消のために小さな設定の補完や繋ぎの追加は許可される。ただし大筋を変更してはならない。

【6. テンポ】
場面ごとの重要度を考慮する。
- 重要な場面が不十分な場合、描写を充実させる
- 冗長な場面は簡潔にする
- 緊張場面の反応や間を適切に残す

【7. クライマックス・余韻】
クライマックスが弱い、または重要な場面的な感情的な着地が不足している場合、改善する。
- 緊張が十分に積み上がっているか
- 決定的な瞬間が弱くなっていないか
- 行動・反応によって感情が伝わるか
- 結末に不要な説明が残っていないか
- 印象的なシーンの描写が弱化されていないか確認する。原有的な感情の強さを維持または強化する。
クライマックス自体を作り直す必要はないが、描写の不足は補完して構わない。

【8. 世界観】
世界観の説明不足によって読者が場面や設定を理解できない場合、補足する。
既存設定から合理的に導ける範囲で補完する。

【9. 文章表現】
- 同じ表現の繰り返しを修正する
- 不自然な比喩や冗長表現を修正する
- 文と文のつながりを滑らかにする
- 読みにくい長文・短文の偏りを調整する
ただし、個性的な表現を「一般的な文章」に均質化しない。

【10. 言語整合性】
- 本文に混入した英語用語を自然な日本語に置き換える（anthro→獣人, feral→動物, semi-anthro→動物と獣人のハーフ）
- character_1, character_2, art_style, IMAGE_PROMPT などのfrontmatter・タグ内の英語は変更しない
- 固有名詞としての英語（例: 作品名、キャラクター名）は維持する

【11. 構成と形式】
以下は必ず維持する。
- 章構成、見出し、Frontmatter、各種タグ、物語の順序、主要登場人物

【最重要ルール】
修正前より明確に良くなる確信がない場合は変更しない。
特に以下は禁止する。
- 物語の大筋・主題の変更
- 主要キャラクターの性格変更
- 章の削除・順序変更
- 不要な内容の水増し

【出力前の自己検証】
出力前に以下のチェックリストで確認する。
- 大筋・主題・章構成が維持されている
- キャラクターの設定・口調が一貫している
- 論理的矛盾が解消されている
- 本文に英語用語が混入していない（frontmatter・タグ内を除く）
- Frontmatter・タグが維持されている

【出力フォーマット】
修正済みの完成原稿のみを返す。
編集内容の説明、評価、採点、コメントは出力しない。
```markdown などのコードブロック囲みは含めない。
```

---

## #5 e621データ収集の開始時期ランダム化

### 方向性
投稿の偏りはトレンドとして受け入れる。収集の開始時期をランダム化することで、各実行で異なる投稿プールが収集されるようにする。

### e621 API 日付フィルタの調査結果

- `date_min` / `date_max` URLパラメータ: 無視される（e621の仕様ではない）
- `date:YYYY_MM_DD..YYYY_MM_DD` (アンダースコア): 0件返す
- `date:YYYY-MM-DD..YYYY-MM-DD` (ハイフン): **動作確認済み** ✓
- `order:random`: ランダム順に取得可能 ✓

### 修正箇所: fetch_topics.py:493-496

**変更前:**
```python
encoded = urllib.parse.quote(tag_query)
from datetime import datetime, timezone, timedelta
fourteen_days_ago = int((datetime.now(timezone.utc) - timedelta(days=14)).timestamp())
url = f"https://e621.net/posts.json?tags={encoded}&limit={limit_per_tag}&date_min={fourteen_days_ago}"
```

**変更後:**
```python
import random
from datetime import datetime, timezone, timedelta, date
# 2010-01-01 〜 現在-14日の範囲でランダムな開始日を選択し、そこから14日間のウィンドウ
now_date = datetime.now(timezone.utc).date()
start_bound = date(2010, 1, 1)
end_bound = now_date - timedelta(days=14)
rand_days = random.randint(0, (end_bound - start_bound).days)
window_start = start_bound + timedelta(days=rand_days)
window_end = window_start + timedelta(days=14)
date_metatag = f"date:{window_start.isoformat()}..{window_end.isoformat()}"
tag_query_with_date = f"{tag_query} {date_metatag} order:random"
encoded = urllib.parse.quote(tag_query_with_date)
url = f"https://e621.net/posts.json?tags={encoded}&limit={limit_per_tag}"
```

2010年1月1日から現在-14日の間にランダムな開始日を選び、そこから14日間のウィンドウを絶対日付で指定。`order:random`で期間内からランダム取得。各実行で異なる16年間のプールからサンプリングされ、キャラクター特徴の多様性が向上する。

### 検証コマンド
```
python -c "import urllib.request, json, urllib.parse; from datetime import datetime, timezone, timedelta; now=datetime.now(timezone.utc); d1=(now-timedelta(days=60)).date(); d2=(now-timedelta(days=30)).date(); date_tag='date:'+str(d1)+'..'+str(d2); tag_query='wolf '+date_tag+' order:random'; encoded=urllib.parse.quote(tag_query); url='https://e621.net/posts.json?tags='+encoded+'&limit=5'; req=urllib.request.Request(url, headers={'User-Agent': 'my-auto-blog/1.0'}); resp=urllib.request.urlopen(req, timeout=15); data=json.loads(resp.read()); posts=data.get('posts',[]); print('Count:', len(posts)); [print('  Post', p['id'], 'created', p.get('created_at','N/A')) for p in posts[:5]]"
```

---

## #6 アフィリエイト英語キーワード

### 方向性
スクリプトが機械的に処理しているため、tags の値を日本語化し、フィルタを追加して英語キーワードがアフィリエイトリンクに流入しないようにする。

### 修正箇所: kemono_story.txt:71 (tagsのデフォルト値)

**変更前:**
```
tags: ["Kemono", "Novel", "Fantasy"]
```

**変更後:**
```
tags: ["ケモノ", "小説", "ファンタジー"]
```

### 修正箇所: generate_article.py:_extract_article_keywords() (1095行)

tags 抽出時に日本語文字を含まないタグを kemono_story モードではスキップするフィルタを追加。

**変更前:**
```python
    # 1. tags から抽出
    tags_match = re.search(r'^tags:\s*\[(.*?)\]', content, re.MULTILINE)
    if tags_match:
        for t in tags_match.group(1).split(','):
            tag = t.strip().strip('"\'')
            if tag and len(tag) >= 2 and tag not in seen:
                seen.add(tag)
                keywords.append(tag)
                if len(keywords) >= max_kw:
                    return keywords
```

**変更後:**
```python
    # 1. tags から抽出（物語系モードでは日本語タグのみ使用）
    tags_match = re.search(r'^tags:\s*\[(.*?)\]', content, re.MULTILINE)
    if tags_match:
        for t in tags_match.group(1).split(','):
            tag = t.strip().strip('"\'')
            if tag and len(tag) >= 2 and tag not in seen:
                # 物語系モードでは日本語文字を含まないタグをスキップ
                if prompt_type in ("kemono_story", "novel", "story"):
                    if not re.search(r'[\u3040-\u309f\u30a0-\u30ff\u4e00-\u9fff]', tag):
                        continue
                seen.add(tag)
                keywords.append(tag)
                if len(keywords) >= max_kw:
                    return keywords
```

ただし `_extract_article_keywords()` は `prompt_type` を引数に受け取っていない。`prompt_type` の取得を関数内で行うか、呼び出し元でフィルタを行う必要がある。

**実装方針:** `_extract_article_keywords()` のシグネチャに `prompt_type` 引数を追加し、呼び出し元（`inject_affiliate_links:1166`）で `prompt_type` を渡す。

### 修正箇所: generate_article.py:_extract_article_keywords() シグネチャ

**変更前:**
```python
def _extract_article_keywords(content: str, max_kw: int = 2) -> list[str]:
```

**変更後:**
```python
def _extract_article_keywords(content: str, max_kw: int = 2, prompt_type: str = "default") -> list[str]:
```

### 修正箇所: generate_article.py:1166 (呼び出し元)

**変更前:**
```python
    article_kw = _extract_article_keywords(content, max_kw=2)
```

**変更後:**
```python
    article_kw = _extract_article_keywords(content, max_kw=2, prompt_type=prompt_type)
```

---

## #7 アフィリエイト製品推薦の汎用化

詳細は別タスクファイルを参照: [`2026-10-07-affiliate-keyword-investigation.md`](2026-10-07-affiliate-keyword-investigation.md)

**概要:** AIが「ケモノ 図鑑」「ライトノベル おすすめ」などの汎用キーワードを選定する問題を改善。
**修正箇所:** `kemono_story.txt:98-101`（product_recommendationsルールに具体例追加 + 汎用キーワード禁止）
**関連:** アフィリエイト検索キーワードの作成箇所を整理（S1-S2スクリプト生成, A1-A2 AI生成, F1-F2フィルタ）
**追加検討:** F1フィルタ拡張, A2プレースホルダー調査, S2抽出ロジック見直し

---

## #8 trend_usage ログの欠落

詳細は別タスクファイルを参照: [`2026-10-07-trend-usage-log.md`](2026-10-07-trend-usage-log.md)

**概要:** 早期リターン時にログ保存がスキップされる問題を修正。`.gitkeep` でCIコミットを確実化。
**修正箇所:** `generate_article.py:1548-1557`（早期リターンにログ追加）, `data/trend_usage/.gitkeep` 新規作成

---

## 修正ファイル一覧

| ファイル | 修正項目 | 変更行数 |
|----------|---------|---------|
| `scripts/generate_article.py` | #1 CHAR_TYPE_WEIGHTS, #6 _extract_article_keywords, 呼び出し元, #8 trend_log | 約15行 |
| `scripts/prompts/kemono_story.txt` | #1 char_type説明, character_1/2ルール, tags, #7 product_recommendations | 約10行 |
| `scripts/prompts/refine_story.txt` | #3 全体書き換え | 約30行 |
| `scripts/fetch_topics.py` | #5 date_min ランダム化 | 約3行 |
