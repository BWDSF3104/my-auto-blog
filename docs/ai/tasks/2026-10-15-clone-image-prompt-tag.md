# kemono_story.txt にクローン系タグルール追加（画像プロンプト）

**Status**: 完了
**Date**: 2026-10-15

## 意図・背景

クローン系記事（extra_key: clone / dark_persona）では画像プロンプトにクローン関連タグが確実に含まれない問題。SFWキーワード選定をユーザーと確認の上、プロンプトルール追加（A案・コード変更なし）で対応する。

## 要件（ユーザー指定）

- クローン系記事（追加設定: 「クローンによる自分同士」または「dark persona」）の**み**で注入
- クローンによる自分同士: `clone`
- dark persona: `dark persona` **と** `clone` の**両方**
- クローン系以外（none / rival）では `clone` / `dark persona` を含めない
- `selfcest` 等のNSFW関係性タグは使用しない（SFWのみ）

## 調査結果 / 変更内容

- Danbooruタグ調査（前回セッション済み）: `clone` = 外見タグ（同一キャラの2実体以上が同一シーン）、`dark persona` = 闇版キャラタグ（訓練済み）、`selfcest` = NSFW関係性タグ。SFW記事は `clone` / `dark persona` の外見タグのみで十分。
- `scripts/generate_article.py:192` は `template.format(**kemono_params)` を使うため、テンプレート追加テキストにリテラルの `{}` を含めてはならない（遵守）。
- `scripts/prompts/kemono_story.txt`: 【キャラクターの一貫性と画像プロンプトのルール】セクションのSFWルールの直後に「クローン系画像プロンプトルール」を追加（条件分岐: クローン系の時のみ / 2人同時登場の画像のみ / dark persona は2タグ / selfcest 禁止）。

## Verification

- `pytest scripts/tests/ -v`: **404 passed**（7.16s）
- `python docs/ai/tmp/check_clone_prompt.py`: `template.format(**params)` が例外なしで展開、新ルールの4文字列がレンダリング済みプロンプトに存在することを assert で確認（OK）。スクラッチスクリプトは使用後に削除済み。
- `git diff`: 変更は `scripts/prompts/kemono_story.txt`（+7行）と Memory Bank のみ。ファイル破損なし（assert の正確な文字列一致で UTF-8 正常を確認）。

## 完了時 Memory Bank 操作

- [x] `current-task.tsv` の参照行を削除
