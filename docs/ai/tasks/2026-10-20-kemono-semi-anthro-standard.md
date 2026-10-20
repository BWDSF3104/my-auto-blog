# ケモノ体型タグ統一（anthro寄り廃止・semi-anthro, [feral] 固定）

**Status**: 完了
**Date**: 2026-10-20
**Next Action**: 完了（メモリバンク締結済み）

## 意図 / 背景

- 記事本文（`character_1` の体型表現）と画像タグ（`character_1/2` の Danbooru タグ）で「半」の意味がずれていた。本文は「動物と獣人のハーフ」を「半獣人」に解釈され、タグ側は別意味だった。
- ユーザーの意図: Gemini（本文）プロンプトには日本語の「二足歩行の動物」を使い、画像タグには「semi-anthro, [feral]」（feral に文字通り [] を付ける、ユーザー確認済み）を使う。英語タグは frontmatter 限定、本文は日本語（英語混入防止）。
- 初回実装では `semi-anthro` を「feral 寄りなら `semi-anthro, feral`、anthro 寄りなら `semi-anthro, anthro`」と二択にしていたが、ユーザー指示「意図と違う anthro寄りは要らない」により **anthro 寄り廃止**。`二足歩行の動物` は一律に `semi-anthro, feral` に固定した。その後のユーザー質問「feralの周りの[]は？」への回答で **feral に文字通り [] を含める**（`semi-anthro, [feral]`）に修正済み。

## 調査結果 / 変更内容

- `scripts/article/config.py` `CHAR_TYPE_WEIGHTS`（行135・137・139）: 「動物と獣人のハーフ」→「二足歩行の動物」。
- `scripts/prompts/kemono_story.txt` 行99:
  - 変更前: `二足歩行の動物: semi-anthro（feral寄りなら「semi-anthro, feral」、anthro寄りなら「semi-anthro, anthro」）`
  - 中間版: `二足歩行の動物: semi-anthro, feral`（anthro寄り廃止）
  - 最終版: `二足歩行の動物: semi-anthro, [feral]`（feral の文字通り [] 付与・ユーザー確認済み）
- `scripts/prompts/kemono_story.txt` 行96〜102（character_1 / character_2 の指定ルール）:
  - 体型タグマッピング: `動物: feral` / `二足歩行の動物: semi-anthro, [feral]` / `獣人: anthro` / `chibi: chibi`
  - 英語タグ（anthro/feral/semi-anthro）は `character_1/character_2` の frontmatter 限定。本文の体型表現は日本語（例: 二足歩行の動物）。
- `scripts/prompts/refine_story.txt` 行81: 本文英語置換 `semi-anthro→二足歩行の動物`。
- `scripts/tests/test_generate_article.py`（`test_char_types_split_into_individual_tags`）: アサーションを「二足歩行の動物」に更新。
- `data/equivalence_golden/build_golden.py` `verify()`: pokemon count を再ベースライン化（40→38、実 `latest.json` の TTL 自然変動で本変更と無関心）。
- ゴールデン fixture 再構築（`python data/equivalence_golden/build_golden.py`）: 変更後のプロンプトが `inputs/prompts/kemono_story.txt` に反映。

## Verification

- `python -m pytest scripts/tests/ -q` → **447 passed**（最終: 7.9s）
- `python scripts/tests/equivalence_check.py --selftest --variants kemono_story` → **RESULT: PASS**（自己整合 2 回実行バイト一致、括弧版プロンプトで再実行済み）
- 変更後 grep: 本変更対象ファイル群（`*.py`, 生 `kemono_story.txt`）に「動物と獣人のハーフ」残らない。`anthro寄り` は live prompt と golden input で皆無（歴史的 `data/prompt_logs/`, `docs/ai/verification/` のみ残存・不変）。

## 完了時 Memory Bank 操作

- [x] `current-task.tsv` の参照行を削除
- [x] 解決した `known-issues/` ファイルを `known-issues/archive/` へ `mv`（該当なし）
- [x] `backlog.md` の完了項目を削除（該当なし）
