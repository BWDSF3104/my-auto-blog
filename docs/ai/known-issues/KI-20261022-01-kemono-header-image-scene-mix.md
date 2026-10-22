# 最新記事のヘッダー画像プロンプトに場面混在（scene mismatch）

**Date**: 2026-10-22
**状態**: 既知の問題（未解決）。Gemini 生成の画像プロンプト品質の問題。

## 確認した事実

対象: `src/content/posts/2026-10-22-102516-auto-post.md`（kemono_story・clone 設定）

- Gemini の image_prompt（`data/prompt_logs/2026-10-22-102516.txt` 対応の drafts pass1/pass2 で確認）:
  - `[character_1: blushing, parted lips, character_2: closed eyes, gentle smile] forehead to forehead, touching faces, holding each other, glowing crystals background, soft rim light`
- 本文中の「額を押し当て、抱きしめる」場面は第3章の洞窟（瓦礫・塵の背景）と最終章の工房（朝光）にあり、**結晶は登場しない**。
- 光る結晶は第1章の地下遺跡の培養pod（硝子円筒・クリスタル盤）の設定のみ（本文 26・31行）。
- 生成画像（`public/images/2026-10-22-102516-header.avif`, `analyze_image_with_groq` 確認）は「2匹の赤狐が顔寄せ・顔触れ pose で、背景に青白い発光結晶」= 物語に存在しない合成シーンで生成済み。

## 本来の意図（テンプレート）

- `scripts/prompts/kemono_story.txt`（画像シーンの選出ルール・アイキャッチ画像）:
  - image_prompt は「物語全体のポスター画像」相当で、**最も視覚的にインパクトのある1瞬間**（クライマックスの決着、2人の決定的な接触など）を指定。
  - 各画像は**異なる瞬間**で、同じシーンの複数アングル禁止（＝1枚1シーンの意図）。
- 生成されたヘッダープロンプトは「接触シーン（第3章/最終章）× 結晶背景（第1章）」と**2つの場面のキーワードが混合**しており、1枚1シーンの意図に反する。

## 同記事で確認された副次的な逸脱

1. **最終章のキス・告白の必須挿絵が未確保**
   - テンプレート「【必須】章内にキス・密着・告白などの親密・感情決定的瞬間がある場合、その場面を描写する挿絵を必ず1つ含めてください」
   - 最終章の画像は `cuddling in bed, morning sunlight, holding hands, intertwined tails, cozy bedroom`（告白後の寝台シーン）で、**実際のキス（本文196行）・告白（199行）の場面を描写する挿絵は存在しない**（生成画像の視覚確認でキスなし）。
2. **人気artist が art_style に未使用**（任意だが）
   - e621 参照に `人気artist: 327b_(artist)` 注入、テンプレートは「使用できます」（任意）。
   - 本記事 art_style: `anime style, illustration, cel shading, warm lighting`（by 未使用）。直近6記事では约半数が by 使用（例: 10/21 `by alasou`）。
   - `scripts/article/geninfo.py` のラベル「人気artist（プロンプトに使用）」は使用していない記事でも同じ表示のため、実態と乖離しうる（2026-10-15 検証タスクでも「by X 未使用（任意）」と記録）。

## 対応の方向性（未着手）

- 選択肢1: `kemono_story.txt` の画像シーンルールに「シーンキーワードは選択した瞬間の同一ロケーション限定。異なる章の背景設定を混在させないこと」を明記。
- 選択肢2: ヘッダーはクライマックス（告白・キス）場面に固定し、最終章の親密瞬間は本文内挿絵に必須化（テンプレート必須ルールを最終章限定に強化）。
- 選択肢3: 生成後チェック（`generate_article.py` 或 `data/prompt_logs` 比対）で、image_prompt の背景キーワードが本文に現れない場合に警告をログ出力。
- 選択肢4: geninfo の artist ラベルを「注入（art_style への反映は任意）」に変更。

## 確認方法

- Gemini 出力: `data/drafts/2026-10-22-102516.json`（pass1/pass2 content）
- 使用プロンプト: `data/prompt_logs/2026-10-22-102516.txt`
- 生成画像: `public/images/2026-10-22-102516-header.avif`（+ inline-1..4.avif）
- 検証スクリプト: `docs/ai/tmp/check_image_prompt.py`（合成プロンプト再構築）
