# 2026-10-13: kemono_story パラメータ調整（重み・char_count固定・character2ルール条件分岐）

**Status**: 完了（2026-10-13）
**Next Action**: なし

## 概要

ユーザー要望の3点:
1. RELATIONSHIP_WEIGHTS で yaoi を 55% に引き上げ（クローン系×恋愛の比率向上）
2. クローン時「1人」は同じ外見のキャラ2人を意味するが、説明文が solo と誤読される恐れがある → 複雑化を避けるため char_count=1 オプションを廃止し常に2人に統一（ユーザー承認済み）
3. 固定プロンプト内のクローン時説明を、クローン時のみ記載するようにする（条件分岐化）

## 変更内容

- `scripts/article/config.py`:
  - `RELATIONSHIP_WEIGHTS`: yaoi 55 / yuri 20 / partnership 15 / hetero 10
  - `CHAR_COUNT_WEIGHTS` / `_KEMONO_CHAR_COUNT_DESC_1` を削除（char_count 常に2）
  - 新定数 `_KEMONO_CHARACTER2_RULES`: 追加設定（none/clone/dark_persona/rival）ごとの character_2 定義ルール文字列。クローン指示は clone のみ、dark persona 体色指示は dark_persona のみ
  - `__all__` を更新
- `scripts/article/image.py`:
  - `_pick_char_count` 関数を削除
  - `_randomize_kemono_params`: `char_count: 2` / `char_count_desc`（バディ・ライバル・カップル抽選）を固定、`character2_rule: _KEMONO_CHARACTER2_RULES[extra]` を追加
- `scripts/prompts/kemono_story.txt`:
  - 「character_1/character_2 の定義ルール」行を固定記述から `・{character2_rule}` に置換（template.format で extra に応じてレンダリング）
- `scripts/tests/test_generate_article.py`:
  - `test_char_count_in_options` → `test_char_count_always_2`、`test_char_count_desc_matches_count` / `test_char_count_1_only_with_clone_or_dark_persona` / `test_distribution_char_count` を削除
  - `test_return_keys` に `character2_rule` を追加
  - 新規: `test_character2_rule_matches_extra`（ルールとextra_keyの一致）、`test_character2_rule_clone_only_mentions_clone`（クローン・体色指示が該当extra時のみ出現）

## 実効分布（拒否率 ≈ 5.7%: clone/dark_persona 65% × hetero 10% × tsfなし 87%）

| 関係性 | nominal | 実効 |
|--------|---------|------|
| yaoi | 55% | ≈58% |
| yuri | 20% | ≈21% |
| partnership | 15% | ≈16% |
| hetero | 10% | ≈4.6% |

## Verification

- `python -m pytest scripts/tests/ -q` → 375 passed（約7秒、新規2テスト含む）
- kemono 関連単独: `pytest scripts/tests/test_generate_article.py -k "kemono or Kemono"` → 49 passed
- テンプレートレンダリング確認: dummy GEMINI_API_KEY で `load_prompt_template('kemono_story').format(**params)` 成功（character2_rule 行が展開されることを確認）
- Python変更のため pytest 実施必須（AGENTS.md 規則）。Astro変更なし → build 不要

## 備考

- 非kemonoプロンプトテンプレートは `character2_rule` を参照しないため影響なし（format の余分な kwarg は無視される）
- `geninfo.py` / アフィリエイト関数は `character2_rule` を不使用
