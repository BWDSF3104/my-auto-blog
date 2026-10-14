# ネガティブプロンプトに human を追加

**Status**: 完了
**Date**: 2026-10-14

## 背景

`docs/ai/image-prompt-refinement.md` の初回精査で `human` は「furry特有だが不要」としてネガティブから削除されていた。再検討の結果、サイトはケモノ/anthro特化であり、実写風human被写体へのドリフト防止ガードとして `human` 追加が妥当と判断。過剰抑制（anthro人型体型の弱化）リスクはポジティブ側に `furry`/`anthro` タグがあるため低い。

## 調査結果 / 変更内容

- `human` を `nsfw` の直後に追加（被写体カテゴリ・CLIP先頭加重の原則）:
  - `scripts/article/image.py:155`（HF Space API へ送信する文字列・実効箇所）
  - `scripts/hf-space/app.py:23`（`_cached_neg_prompt`、未使用のdead codeだが同期）
  - `scripts/hf-space/app.py:231`（Gradio UI既定値）
- ネガティブプロンプト: 15タグ → 16タグ
- `docs/ai/image-prompt-refinement.md` を更新（ネガティブ最終案・削除タグ表・順序・削減まとめ）
- embeddingキャッシュ機構への影響なし（キーは実際のプロンプト文字列から計算: `app.py:159`）
- `person` 等の追加はユーザー判断で今回は行わず（`human` のみ）

## HF Space デプロイ

`app.py` は HF Space（`blume/kemono-image-api`）のデプロイ元のため、ローカル変更のみでは反映されない。

- アップロード: `hf upload --repo-type space blume/kemono-image-api scripts\hf-space\app.py` → commit `9acb5f32`
- 起動確認: `get_space_runtime` の stage が `RUNNING` になるまでポーリング → **RUNNING**（新コード起動済み）
- 生成テスト: **ユーザー指示で実行せず**（クォータ消費回避。クォータは実行時に remaining=300 満タンだった）

## Verification

- `pytest scripts/tests/ -v`: 397 passed（7.15s）
- HF Space `RUNNING` 確認（2026-10-14）

## 完了時 Memory Bank 操作

- [x] `current-task.tsv` の参照行を削除
- [x] 本ファイルの Status を「完了」に更新
- 注記: 効果検証（同一seedでの before/after 比較生成）は次回記事生成時に実施するとよい（画像の視覚解析は Groq 送信前にユーザー確認が必要）
