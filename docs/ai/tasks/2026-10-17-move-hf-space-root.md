# HF Space ソースをプロジェクトトップへ移動 (hf-space/)

**Status**: 完了
**Date**: 2026-10-17
**Next Action**: git mv scripts/hf-space -> hf-space + docs 参照更新

## 意図 / 背景

`blume/kemono-image-api`（自社管理 HF Space）のデプロイ元ソース `scripts/hf-space/` が「GitHub Actions パイプライン用スクリプト置き場 `scripts/`」内にあり、位置づけがわかりづらい（ユーザー指摘）。本タスクでは:

1. `scripts/hf-space/` をプロジェクトトップの `hf-space/` へ `git mv` する
2. `architecture.md` / `README.md` / `AGENTS.md` などの生存ドキュメントの参照を更新する
3. `hf-space/app.py` の調査結果（パイプライン詳細）をタスクファイルに記録する

過去のタスク・決定記録（`tasks/`・`decisions/` の日付付きファイル）は歴史記録のため書き換えない。

## 調査結果 / 変更内容

### `hf-space/app.py` の調査（blume/kemono-image-api = 自社管理 Space）

- **モデル**: `IbarakiDouji/Nova-Furry-XL` / `novaFurryXL_ilV180A.safetensors`（SDXL / Illustrious 系）。`StableDiffusionXLPipeline.from_single_file` + `EulerAncestralDiscreteScheduler`（Euler a）
- **長プロンプト対応**（`app.py:93-187`）: 75 トークン単位チャンク分割（BOS/EOS 付き）+ デュアルテキストエンコーダ（OpenCLIP ViT-H / CLIP ViT-L）で SDXL の conditioning 形式を再現。pooled embedding は最初のチャンクのみ取得
- **negative prompt キャッシュ**（`app.py:22-24, 158-185`）: チャンク構成が同一なら 1 回のみ計算（全リクエスト同一の negative prompt を前提）。`app.py:23` の `_cached_neg_prompt` 定数は未使用の dead code（実効の negative prompt は API 経由でクライアント駆動: `scripts/article/image.py`）
- **ZeroGPU**: `@spaces.GPU(duration=20)`、初回 `pipe.to("cuda")` のみ。クォータ 3.5 分/日
- **API**: Gradio `predict`（7 入力: `prompt, negative_prompt, steps(1-50, 25), guidance_scale(1-15, 5.0), width(512-1536, 1152), height(512-1536, 768), seed(-1 ランダム / >=0 再現)`）
- **重要発見 — 強調構文非対応**: プロンプトは `tokenize_long_prompt()`（`app.py:36-41`）で CLIP トークナイザにそのまま通るため、A1111 系 `(word:1.1)` / `[word]`（0.83x）の強調構文は**解析されない**（リテラルトークンとして扱われる）。→ 前タスク（画像品質診断）の「`1girl` 等の count タグを `[]` で減衰する」案は本 Space では使えない。人間混入対策は `no human`（ポジティブ）/ `human`（ネガティブ）タグの調整に限られる
- **不整合発見**: `scripts/_test_hf_space.py`（ワンオフ・保留タスク `2026-10-14-move-oneoff-scripts.md` 対象）は 6 フィールド（seed なし）で POST しており、現行の 7 入力 API と不一致 → 実行すると失敗する見込み

### 変更内容

1. `git mv scripts/hf-space hf-space`（`app.py` / `requirements.txt` / `TEST_RULES.md`）
2. `hf-space/TEST_RULES.md`: アップロードパス `scripts/hf-space/app.py` → `hf-space/app.py`。`@spaces.GPU(duration=90)` 記載 2 箇所 → `duration=20`（app.py 実装・`api-rate-limits.md` と整合）。テスト結果記録先を現行タスクファイル方式へ更新
3. `README.md`: 構造ツリーから `scripts/hf-space/` を削除し、トップレベル `hf-space/` を追加
4. `docs/ai/architecture.md`: 「Image Generation Space (`hf-space/` → `blume/kemono-image-api`)」コンポーネントセクション新設（モデル・API・強調構文非対応・クライアント駆動の明記）。デプロイ手順のパスを `hf-space/app.py` へ更新
5. `AGENTS.md`: プロジェクト構成に `hf-space/` を追加
6. `docs/ai/decisions/2026-10-17-hf-space-root.md`: 決定記録新設
7. `docs/ai/tasks/2026-10-14-move-oneoff-scripts.md`（保留）: 対象外リストの `scripts/hf-space/` 行に失効注記を追加
8. 過去のタスク・決定記録（`tasks/2026-10-05〜15-*`、`decisions/2026-10-14-*`）の `scripts/hf-space/` 参照は歴史記録のため不変

### 追記: pytest が実キャッシュ `data/genre_scores/cache.json` を汚染する問題（検証中に発見・修正）

- **原因**: `test_genre_score.py` の `TestMain` 3 テスト（`test_cli_outputs_json` / `test_cli_writes_output_file` / `test_token_not_in_output`）が `main()` を `--no-cache` なし・`DEFAULT_CACHE_PATH` 未パッチで呼び出し → `_load_cache()` が実キャッシュの TTL 超過エントリ 94 件を破棄・書き戻し + モックスコアのテストエントリ 3 件（`攻殻機動隊` / `テスト` / `t`、source=`unknown`）が実ファイルに混入
- **修正**: `test_genre_score.py` にモジュールレベルの autouse fixture `_isolated_default_cache` を追加 — 全テストで `genre_score.DEFAULT_CACHE_PATH` をテスト毎の一時ファイルへ差し替え、pytest 実行中に実キャッシュを読み書きしない
- **復元**: 汚染された `data/genre_scores/cache.json` は `git checkout` で HEAD へ復元（TTL パージ 94 件は本来の破棄対象だが、テスト起因・かつ本タスクのコミットスコープ外のため次回本番実行時に自然に再発生する）

## Verification

- `pytest scripts/tests/ -v`: **407 passed**（7.92s、修正後再実行）— 実行直後 `git status data/` がクリーン（実キャッシュ汚染なし・fixture 有効性の確認済み）
- 初回実行時は `data/genre_scores/cache.json` が変更（+3 テストエントリ / -94 TTL 超過エントリ）→ 上記 fixture 追加 + 復元で解消
- `grep "scripts[/\\]hf-space"`: 残存参照はすべて過去記録（tasks/decisions の日付付きファイル）+ 本タスク関連の本文のみ。生存ドキュメント・コード・CI に旧パス参照なし
- CI（`.github/workflows/`）: `hf-space` / `kemono-image-api` 参照なし（grep 確認）— デプロイ影響なし（workflows.md の paths 不一致による例外該当）
- `npm run build` 不要（Astro 変更なし・AGENTS.md 例外）

## 完了時 Memory Bank 操作

- [ ] `current-task.tsv` の参照行を削除
- [ ] 解決した `known-issues/` ファイルを `known-issues/archive/` へ `mv`（該当する場合）
- [ ] `backlog.md` の完了項目を削除（該当する場合）
