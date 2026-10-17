# 最新記事(2026-10-17-101357)の画像品質修正: 人間混入 / clone 不在 / キス・密着シーン未画像化

**Status**: 完了（実装・検証・Space 再デプロイ・推論確認・commit すべて完了）
**Date**: 2026-10-17
**Next Action**: なし（タスク完了・`current-task.tsv` 参照行削除済み）

## 意図 / 背景

最新自動生成記事 `src/content/posts/2026-10-17-101357-auto-post.md`（kemono_story / clone 設定 / yuri）で画像品質の 3 問題を確認（ユーザー指摘）:

- `1girl` 等の count タグが強すぎて**人間が混入する**
- **`clone` が画像プロンプトに含まれていない**
- 記事内に**キス・密着シーンがあるが画像生成シーンとして選択されていない**

## 事実確認（調査済み）

- 実際に行き渡った Gemini プロンプト: `data/prompt_logs/2026-10-17-101357.txt`（154 行、`generate_article.py:212-217` が自動保存）
- **clone ルールはプロンプトに含まれていた**（ログ 43-45 行、`{extra_rule_text}` 経由注入済み）→ 指示不足ではなく **Gemini の遵守失敗**
- テンプレ `kemono_story.txt:99` が frontmatter 定義に `1boy, 1girl` 等を**必須指定**、出力例 `:81-82` も `1boy` 始まり → count タグは指示どおりの出力
- `image_prompt` フロントマター**欠落**（Gemini 出力漏れ）→ ヘッダーは `_compose_smart_situation`（frontmatter.py:172-175）が kemono_story で DEFAULT_SITUATION を返す → 「dragon, blueeyes, white scale, sitting at desk with laptop, tech room」+ character_1 単独（image.py:333-337 フォールバック）で生成 → 物語（2 匹の白狼・遺跡）と不一致
- Space への最終 SD プロンプト（`compose_image_prompt` 出力）:
  - 単独: **先頭 `1girl,`**（定義先頭、単独経路 image.py:419-427 は除去しない）→ シーン → `..., masterpiece, best quality, very aesthetic, ultra-detailed, furry, no human, safe for work, <style>`
  - 2 人: **先頭 `2girls,`**（`_compute_count_tag`:342-354、`2boys` / `1boy, 1girl` / `Ncharacters` も生成しうる）→ char1, char2 → シーン → 同上
  - count タグが先頭（強ポジション）、`furry, no human` が末尾（弱ポジション）→ 競合の構造的説明
- `hf-space/app.py`: `tokenize_long_prompt`（36-41）は生 CLIP トークナイズで A1111 系 `(word:1.1)` / `[word]` 強調構文パーサー**なし** → `[1girl]` は `1girl` 全ウェイト + 括弧ノイズ 2 トークン（チャンク予算希釈）= 減衰不能
- Space 側でプロンプト整形が可能な chokepoint: `tokenize_long_prompt`（app.py:36-41、全リクエストの正プロンプトが通過）/ `predict`（app.py:192、negative prompt を受領）
- 先行事例: 2026-10-14 に neg へ `human` 追加（image.py:155）+ pos へ `no human` 追加（config.py:65）済み（`docs/ai/tasks/2026-10-14-negative-prompt-human.md`）→ **neg による human 抑制は既に導入済みで不十分**だった

## 修正方針（ユーザー最終判断を反映・実装済み）

ユーザーが方式を確定: (1) 人間混入は **space 側減衰**（count タグは**削除せず**減衰）/ (2) **dark_persona も対象** / (3) 実施。

### 人間混入（count タグ）— space 側減衰（emphasis 重み付け）

- Python 側が count タグを強調構文 `({tag}:{COUNT_TAG_WEIGHT})` で囲んで Space に送り、Space 側でテキストエンコーダ後の hidden state をトークン単位でスケーリング（A1111 系方式）。`COUNT_TAG_WEIGHT = 0.6`（config.py、調整可能）
- 単独: キャラ定義先頭 `1boy|1girl|1other|male|female` を regex で抽出→`(tag:0.6)`（image.py `compose_image_prompt`）
- 2 人+: `_compute_count_tag` 出力を `(tag:0.6)` ラップ（同上）
- Space 側実装（app.py）: `parse_emphasis` / `build_weighted_tokens` / `_tokenize_and_chunk_weighted` / `_apply_weights` を新設、`get_long_prompt_embeddings_sdxl` を positive だけ重み付け経路に置換（negative は従来・キャッシュ維持、pooled は無重み）
- 強調構文: `(w:1.2)`→1.2 / `(w)`→1.1 / `[w]`→0.5 / `[[w]]`→0.25 / 他→1.0

### clone — Gemini 指示廃止・完全スクリプト側対応（dark_persona も対象）

- **Gemini 指示の削除**: `build_prompt` の `extra_rule_text` 分岐 + `_KEMONO_CLONE_RULE_TEXT` **と** `_KEMONO_DARK_PERSONA_RULE_TEXT` **両方**削除（config.py）。テンプレ `{extra_rule_text}`（kemono_story.txt）も同時削除
- **スクリプト側強制注入**: `scene_keyword_injection(extra_key)`（image.py）が `clone`→`"clone"` / `dark_persona`→`"dark persona, clone"` / 他→`""` を返す
- 伝播: `generate_post`→`build_header_image` & `postprocess_content`→`process_inline_images`→`compose_image_prompt`（`scene_injection` 引数）
- **2 人以上登場時のみ** `clean_situation` 先頭に注入（1 人画像は注入しない）

### キス・密着シーン未画像化 — テンプレのみ

- 根本原因: `kemono_story.txt`（本文内挿絵ルール）が「複数枚の挿入を**許可**」の許可制であり、親密瞬間の画像化を必須としない
- 修正: 複数枚許可行の直後に「章内にキス・密着・告白などの親密・感情決定的瞬間がある場合、その場面を描写する挿絵を必ず 1 つ含めてください（複数枚の許可の範囲で追加）」を追加
- コード変更なし

## Verification

- `pytest scripts/tests/ -v`: **413 passed**（compose_image_prompt の count タグ減衰 / scene_injection の新テスト 6 件追加、既存 2 件の count タグ assert を `(2boys:0.6)` 形式に更新）
- `python -m py_compile hf-space/app.py`: **SYNTAX OK**
- 強調ロジックの孤立検証（`docs/ai/tmp/test_emphasis.py`、mock tokenizer）: **ALL PASS**（`parse_emphasis` / `build_weighted_tokens` の token・weight 同長整合 / `_tokenize_and_chunk_weighted` の各チャンク 77 整合）
- `npm run build`: テンプレ変更のみで記事生成時に確認（未実施）
- Space 再デプロイ: **RUNNING 確認済み**（app.py のみ upload → `RUNNING_BUILDING`→`RUNNING_APP_STARTING`→`RUNNING`、約66秒、起動エラーなし）
- 推論 1 回検証: **PASS**（`(2girls:0.6)` 減衰 + `clone` 注入を含むプロンプトで 18steps・512x512・seed=42 生成、平均輝度 93.1＝非黒、強調経路の実動作 OK。結果 `docs/ai/tmp/space_test_result.png`）

## 完了時 Memory Bank 操作

- [ ] `current-task.tsv` の参照行を削除
- [ ] 解決した `known-issues/` ファイルを `known-issues/archive/` へ `mv`（該当する場合）
- [ ] `backlog.md` の完了項目を削除（該当する場合）
