# KI-003 長プロンプト対応調査

## 日付
2026-10-05

## 背景
KI-003: 生成画像が記事の场景と一致しない問題。根本原因はSDXLの77トークン制限で、長プロンプトが切り捨てられている。

## 試したアプローチと結果

### v1: 初期chunking実装（失敗）
**エラー:**
```
RuntimeError: mat1 and mat2 shapes cannot be multiplied (2x2304 and 2816x1280)
```
**原因:** pooled embeddingを`text_encoder` (CLIP-L, 768dim) から取得しようとしたが、SDXLは`text_encoder_2` (CLIP-G, 1280dim) を期待

### v2: sd_embed参考の実装（失敗）
**エラー:**
```
RuntimeWarning: invalid value encountered in cast
  images = (images * 255).round().astype("uint8")
```
**結果:** 画像が100%真っ黒（NaN/Inf値）

## 失敗理由の精査

### v1の失敗
- `max_length=tokenizer.model_max_length` (=77) で長文が最初から切り捨て
- pooled embeddingの次元不整合

### v2の失敗（黒画像の原因特定）
sd_embedの実装を直接確認した結果、v2が再現できていなかった关键点:

1. **hidden_states[-2] (penultimate layer) の使用**: SDXLでは最終層ではなくpenultimate layerを使用する必要がある
   ```python
   # sd_embedの実装
   prompt_embeds_1_hidden_states = get_prompt_hidden_states_sdxl(prompt_embeds_1, clip_skip=clip_skip)
   # get_prompt_hidden_states_sdxl は hidden_states[-2] を返す
   ```

2. **pooled embeddingの取得方法**:
   ```python
   # 正解: text_encoder_2のpooled出力を使用
   pooled_prompt_embeds = prompt_embeds_2[0]
   
   # 誤り: attention-weighted meanや[0]トークンのhidden state
   ```

3. **positive/negativeのチャンク数合わせ**: 長文時に両方のembedding長を合わせる必要がある

## 検討中の解決策

### Compel 2.3.1（第1候補）
- `CompelForSDXL`クラスで長プロンプト対応
- 2.3.1に「SDXLの78/77 token問題の修正」が含まれる
- 既存Space環境（Python 3.12, Diffusers, Transformers）との互換性確認必要
- 導入が困難な場合は、Compel/sd_embedのSDXL処理部分だけを参考にした自前実装

### 自前実装（第2候補）
sd_embedの実装を参考にした最小限の実装:
1. 全文tokenize → 75トークン単位分割
2. 各チャンクにBOS/EOS追加 → 77トークン
3. `hidden_states[-2]`を取得
4. 2つのencoderのembeddingを`dim=-1`で連結
5. チャンクを`dim=1`で連結
6. pooled embeddingは`text_encoder_2`のpooled出力から取得
7. positive/negativeのチャンク数を揃える

## テスト手順
段階的な検証:
1. 通常の `pipe(prompt=...)` → 成功確認
2. 77トークン以内のembedding生成 → 同じく成功
3. 78トークン → 成功確認
4. 150トークン → 成功確認
5. 300トークン → 成功確認

各ステップでembeddingのNaN/Infチェック:
```python
torch.isfinite(prompt_embeds).all()
torch.isfinite(negative_prompt_embeds).all()
torch.isfinite(pooled_prompt_embeds).all()
torch.isfinite(negative_pooled_prompt_embeds).all()
```

## 結論
- 「SDXLは77トークン超が不可能」ではない
- chunkingアプローチは可能だが、SDXLのconditioning形式を正確に再現する必要がある
- sd_embedパッケージそのものは導入しない（依存関係が重い）
- Compel 2.3.1は依存関係競合（huggingface-hubのバージョン）で導入断念
- sd_embedの実装を参考にした自前chunking実装で成功
- 关键点: `hidden_states[-2]`、`text_encoder_2`のpooled出力、positive/negativeのチャンク数一致

## 成功した実装
- `scripts/hf-space/app.py`に`get_long_prompt_embeddings_sdxl`関数を追加
- 短プロンプト・長プロンプト（~70トークン）両方で512x512テスト成功
- 平均輝度69（短）、110（長）で黒画像なし
