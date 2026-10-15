# 画像生成ポジティブプロンプト固定部に no human を追加

**Status**: 完了
**Date**: 2026-10-15

## 意図・背景

2026-10-14 の「ネガティブプロンプトに human を追加」（実写風 human 被写体ドリフト防止・anthro ガード）の継続。ネガティブの `human` に加え、ポジティブ固定部（`BASE_QUALITY_PROMPT`）へ `no human` を追加するダブルガードをユーザーが検討依頼。サイトはケモノ/anthro 特化。

## 調査結果

- **Illustrious 公式ガイド**（tensor.art「IllustriousXL Generation Guide」）: ポジティブ 1 項目「Subject Details」に `no human` が明記（例: `1boy, 1girl, no human`）。本モデル Nova-Furry-XL IL v18.0A は Illustrious 系（Danbooru タグ形式）。
- **furry SD コミュニティ**（NoobXL 系メモ）: ポジティブの `no human` タグで human 混入回避と報告（「reduce anthro affect (more original style)」）。
- **Nova Furry v6 系**のコミュニティプロンプト（genur.art）でもポジティブに `no humans` 使用例あり。
- **注意**: `no human` は Danbooru 標準タグではない（Illustrious 学習データでの確立度は不確実）。CLIP のポジティブ側否定は不可靠 → IL v18.0A での実効は未検証。
- **Flux.1 フォールバックへの副次効果**: Flux はネガティブプロンプト非サポート（公式明言）。ポジティブ（自然言語解釈）は唯一の抑制手段のため、`no human` はフォールバック側で有効。
- **タグ形式**: 単数 `no human`（ユーザー依頼・Illustrious ガイド・NoobXL メモに一致。kemono.ai 表記の複数 `no humans` ではなく単数を採用）。
- **過剰抑制リスク**: anthro の人型特徴弱化の可能性は、ポジティブ `furry` で緩和（2026-10-14 決定と同一論理）。
- **配置**: `furry` の直後（被写体タグを隣接させ、`safe for work` は末尾維持）。
- `scripts/hf-space/app.py` は変更不要（ポジティブは完全クライアント駆動。app の UI デフォルトは例示のみ。ポジティブ embedding は毎回再計算 `app.py:139` のためキャッシュ影響なし）。

## 変更内容

- `scripts/article/config.py:65`: `BASE_QUALITY_PROMPT` 6 タグ → 7 タグ（`no human` 追加）
- `docs/ai/image-prompt-refinement.md`: ポジティブ最終案を実際の config と同期（2026-10-06 947009c「順序変更+品質タグ削減」で `absurdres` / `newest` が削除済みだがドキュメント未反映だった）＋ `no human` 追加の記録。削減まとめ表も現状値に更新
- HF Space デプロイ不要（Python 側変更のみ）

## Verification

- `pytest scripts/tests/ -v`: **404 passed**（6.98s）
- `compose_image_prompt` sanity check（`docs/ai/tmp/check_no_human_prompt.py`）: 合成プロンプトに `furry, no human, safe for work` が Illustrious 順序で含まれることを確認
  - 出力例: `1boy, 1girl, blue wolf, anthro, white markings, black panther, anthro, red eyes, sitting together, masterpiece, best quality, very aesthetic, ultra-detailed, furry, no human, safe for work, anime style, illustration, cel shading`

## 完了時 Memory Bank 操作

- [x] `current-task.tsv` の参照行を削除
- [x] 本ファイルの Status を「完了」に更新
- 注記: 効果検証（同一 seed の before/after 比較生成）は次回記事生成時に実施するとよい（画像の視覚解析は Groq 送信前にユーザー確認が必要）
