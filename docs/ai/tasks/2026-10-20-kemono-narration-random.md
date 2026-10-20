# kemono_storyの叙述視点毎回ランダム（3種）

**Status**: 完了
**Date**: 2026-10-20
**Next Action**: config.py/image.py/gemini.py/generate_article.pyとpromptsに視点ランダム化を実装し、pytest実行

## 意図 / 背景

kemono_story 記事の叙述視点（一人称／第3人称有限（主人公視点）／第3人称全知）を、毎回の記事生成で均一にランダム選択したい。
現状はプロンプト（scripts/prompts/kemono_story.txt）に視点指定がなく、LLM のデフォルト（第3人称、主人公中心）に依存している。
ユーザー指示: 毎回ランダムでよい。候補は表の上3種（一人称・第3人称有限・第3人称全知）までがちょうどよい。

## 調査結果 / 変更内容

### 現状調査

- 生成プロンプト（`scripts/prompts/kemono_story.txt`）は視点指定なし。精製プロンプト（`scripts/prompts/refine_story.txt`:44）も「一人称・二人称が章を通じて一定か」のみで視点の強制なし
- 実出力は第3人称限定的（主人公中心）が基本、全知視点が混入する場合も
- `generate_article.py` の `generate_content()` は `kemono_params` 経由で 2-pass 精製に視点情報を渡していなかった（`kemono_params` は `generate_post()` 内で生成されるため、`generate_content` に追加引数が必要）
- テスト `test_return_keys` は `_randomize_kemono_params()` のキー集合の完全一致をアスертする（追加キーには同期更新が必要）

### 設計方針

- 3種（一人称 / 第3人称限定的・主人公視点 / 第3人称全知・俯瞰）から**均一ランダム**（`random.choice`、等重み）。ユーザー指示「上3つまでが丁度よい」に従い二人称・日記体は採用しない
- 選択キー（`narration_key`）は `kemono_params` に追加。テンプレート `{narration_instruction}` 注入 + 精製プロンプトに【視点】を前置 + 生成情報セクションに「視点」行表示
- `refine_story.txt` は「冒頭に【視点】が指定されている場合: …」の条件付きチェックに（非物語系・指定なし時は無効）

### 変更内容

1. `scripts/article/config.py`: 定数 `_KEMONO_NARRATION_OPTIONS`（key→指示文）、`_KEMONO_NARRATION_LABEL`（表示ラベル）を追加。`__all__` に追加
2. `scripts/article/image.py`: `_randomize_kemono_params()` に `narration_key = random.choice(...)` を追加し、返却値に `narration_key` / `narration_instruction` / `narration_label` を追加
3. `scripts/prompts/kemono_story.txt`: 必須条件の前に `【視点】{narration_instruction}` セクション追加
4. `scripts/prompts/refine_story.txt`: 【4. キャラクターの一貫性】に視点整合性チェック項目追加（条件付き）
5. `scripts/article/gemini.py`: `refine_content()` に `narration_instruction=""` 引数追加。指定時は【視点】を【下書き】前に注入
6. `scripts/generate_article.py`: `generate_content()` に `narration_instruction=""` 引数追加 + `refine_content` 呼び出し・`generate_post()` 呼び出し箇所の修正
7. `scripts/article/geninfo.py`: `_gen_info_setting_rows()` に「視点」行追加（`narration_label`）
8. `scripts/tests/test_generate_article.py`: `test_return_keys` の expected_keys 更新、`test_narration_in_options` 新增、import 追加

## Verification

- `pytest scripts/tests/ -v` → 448 passed / 8.44s（変更前 447 件 + 新規 1 件 `test_narration_in_options`、`test_return_keys` 更新）
- 変更ファイル: `scripts/article/config.py`, `scripts/article/image.py`, `scripts/article/gemini.py`, `scripts/article/geninfo.py`, `scripts/generate_article.py`, `scripts/prompts/kemono_story.txt`, `scripts/prompts/refine_story.txt`, `scripts/tests/test_generate_article.py`
- Python 変更のみ → build 不要。deploy 検証も不要（paths: `src/**`, `public/**`, `package.json`, `astro.config.mjs`, `tailwind.config.mjs` に該当ファイルなし）

## 完了時 Memory Bank 操作

- [ ] `current-task.tsv` の参照行を削除
- [ ] 解決した `known-issues/` ファイルを `known-issues/archive/` へ `mv`（該当する場合）
- [ ] `backlog.md` の完了項目を削除（該当する場合）
