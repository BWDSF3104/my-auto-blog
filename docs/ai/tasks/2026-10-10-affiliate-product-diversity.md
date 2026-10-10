# 2026-10-10: アフィリエイト商品推薦の書籍偏り（プロンプト中性化）

**Status**: 完了
**Next Action**: なし

## 背景

ユーザー報告: Gemini が生成するアフィリエイト商品名（frontmatter の `product_recommendations` → 商品カード）が書籍に偏る。直近記事（`src/content/posts/`）で定量確認: `pc-name` 商品カード約34件中、約6割が書籍・漫画・アートブック（BEASTARS 漫画 ×6、ケモノキャラクター図鑑公式ガイド ×3、Skyrim 公式アートブック、BNA アートブック ×2 等）。

偏り要因の特定:
- `scripts/prompts/default.txt`: Frontmatter 例の1件目が書籍、category 列挙が書籍先頭、比較表の例行が書籍のみ等
- `scripts/prompts/ai_deep.txt`: 同様のパターン ＋ AFFILIATE プレースホルダーの唯一の例が書籍
- `scripts/prompts/kemono_story.txt`: Frontmatter 例が書籍1件のみ、「実在作品を1つ選定」
- `scripts/generate_article.py` `_load_character_features()` 内「書籍・ゲーム・グッズ」1行（`kemono_story.txt` の `{character_features_instruction}` 経由で注入）

## 方針（ユーザー指示）

- 「書籍」を例から**削除しない**: 書籍自体は正規の商品カテゴリ
- 「カテゴリ構成を多様化せよ」「書籍に限定しない」等の**禁止指示・否定表現は追加しない**
- 修正は「書籍が先頭・単独例にならない」順序・複数例化のみ ＋ 「実在作品」→「実在商品」の選定対象の中性化

## 変更内容

### scripts/prompts/default.txt（6箇所）
1. 「関連書籍・ツール・サービス」→「関連ツール・サービス・書籍」
2. AFFILIATE 例2行を入れ替え（VS Code 拡張機能を先頭、Python 入門書を2番目に維持）
3. 比較表例に「開発ツールA」行を入門書行の前に追加（入門書行は維持）
4. Frontmatter 例: 商品名1 → グッズ/3000円台、商品名2 → 書籍/1000円台（書籍を2番目に）
5. 「カテゴリ（例: 書籍, フィギュア, ゲーム, ソフトウェア, ガジェット）」→「（例: ソフトウェア, ツール, ガジェット, 書籍, フィギュア, ゲーム）」
6. product_recommendations ルールの category 例も同順（書籍を末尾へ）

### scripts/prompts/ai_deep.txt（3箇所）
1. 「関連書籍・ツール・サービス」→「関連ツール・サービス・書籍」。書籍例の前に「AI開発フレームワーク」例を1件追加（書籍例は維持）
2. Frontmatter 例を入れ替え（関連ツールの名前/ソフトウェア/無料を先頭、関連書籍のタイトル/書籍を2番目に）
3. 「実在する書籍・ツール・グッズ」→「実在するツール・グッズ・書籍」、category 例は default と同順

### scripts/prompts/kemono_story.txt（4箇所）
1. 「関連書籍・グッズ」→「関連グッズ・書籍」
2. Frontmatter 例に「関連グッズ名」（グッズ/3000円台）を書籍項目の前に追加（書籍項目は維持）
3. 「実在作品を1つ選定」→「実在商品を1つ選定」
4. category 例 →「フィギュア, グッズ, BD, ゲーム, 書籍等」（書籍を末尾へ）

### scripts/generate_article.py（1箇所）
- `_load_character_features()` 注入行: 「トレンドに関連する書籍・ゲーム・グッズ」→「トレンドに関連するゲーム・書籍・グッズ」（語順のみ）

## 範囲外

- `_KEYWORD_ENHANCEMENT` / `_improve_keyword`: フォールバックセクションの検索リンクキーワード。Gemini 商品名とは別メカニズム
- `cat_icons`: 未知カテゴリは 📦 フォールバックで処理
- 既存記事の書き直し

## 検証

- `pytest scripts/tests/ -v` → **315 passed** (3.90s)
- プロンプト内容をアサートするテストは存在しない（パースロジックのみ）ためプロンプト編集はテストに影響なし
- Gemini 商品名は `gemini_products` → `_rakuten_api_keywords()` カスケードで楽天API検索にも波及するため、API カードの関連性も同時に改善される見込み
- 生成物への効果（商品カードのカテゴリ分布）は次回 deploy 実行の観察で確認

## コミット

（commit 後に記入）
