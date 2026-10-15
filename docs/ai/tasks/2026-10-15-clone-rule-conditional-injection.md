# クローン系画像プロンプトルールの条件注入化

**Status**: 完了
**Date**: 2026-10-15

## 意図・背景

`2026-10-15-clone-image-prompt-tag.md` で `kemono_story.txt` に追加したクローン系ルールの問題: ルールブロックがテンプレートの静的テキストのため、クローン系以外（none / rival）の記事でも常に Gemini に送信されていた。「クローン系の時のみ注入」「クローン系以外では Gemini に指示を出すこともしない」要件を満たしていない。

## 要件（ユーザー指定）

- クローン系記事（extra_key: clone / dark_persona）の**み**でクローン系ルールの指示文をプロンプトに含める
- クローン系以外（none / rival）ではクローン系に関する指示を Gemini に一切送信しない
- 【追記】ダークペルソナについての特約も、`dark_persona` が選ばれた時だけ Gemini に渡す（クローン特約と独立した別の特約として分離）

## 変更内容

- `scripts/article/config.py`: `_KEMONO_CLONE_RULES` dict を廃止し、独立した 2 定数 `_KEMONO_CLONE_RULE_TEXT`（【クローン画像プロンプトルール】）と `_KEMONO_DARK_PERSONA_RULE_TEXT`（【dark persona画像プロンプトルール】）を追加し `__all__` に登録
- `scripts/generate_article.py`: `build_prompt()` で `extra_key` ごとに特約を選択（clone → クローン特約 / dark_persona → ダークペルソナ特約 / それ以外 → 空文字列）し `extra_rule_text` として `template.format()` に渡す
- `scripts/prompts/kemono_story.txt`: 静的なクローン系ルールブロックを `{extra_rule_text}` プレースホルダに置換

## Verification

- `pytest scripts/tests/ -v`: 404 passed（7.11s）
- スクラッチスクリプト（`docs/ai/tmp/check_clone_injection.py`）で `build_prompt()` を実呼びし、`extra_key` 4 値（clone / dark_persona / none / rival）の展開後プロンプトを確認:
  - clone: 【クローン画像プロンプトルール】あり・`clone` 指示あり・`dark persona` 文字列なし
  - dark_persona: 【dark persona画像プロンプトルール】あり・「`dark persona` と `clone` の両方」指示あり・【クローン画像プロンプトルール】なし
  - none / rival: 特約見出し・`clone`・`dark persona`・`selfcest` 一切なし
  - 全ケース: 未展開プレースホルダなし / 他テンプレート（default / refine_tech / refine_story / ai_deep）はプレースホルダを持たず影響なし
- `git diff` で変更範囲・ファイル破損を確認
  - 変更ファイル: `scripts/article/config.py` / `scripts/generate_article.py` / `scripts/prompts/kemono_story.txt` / タスクファイル
  - ユーザー指摘により `selfcest`/SFW 指示行は両特約から削除（Gemini は検閲済モデルのため不要）

## 完了時 Memory Bank 操作

- [x] `current-task.tsv` の参照行を削除
