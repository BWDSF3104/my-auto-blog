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

### v3: 自前chunking実装（成功）
sd_embedのソースコード (`embedding_funcs.py`) を直接参照した正確な実装。

**关键点:**
1. `hidden_states[-2]` (penultimate layer) を両方のtext encoderで使用する
2. pooled embeddingを`text_encoder_2`のpooled出力 (`prompt_embeds_2[0]`) から取得
3. 75トークン単位でチャンク分割、BOS/EOSで77トークンにパディング
4. 2つのencoderのembeddingを`dim=-1`で連結、チャンクを`dim=1`で連結
5. positive/negativeのチャンク数を一致させる
6. 最初のチャンクのみpooled embeddingを取得（その後はNoneのまま）

**実装ファイル:** `scripts/hf-space/app.py`
- `get_prompt_hidden_states_sdxl()`: penultimate layer取得
- `tokenize_long_prompt()`: トルンケーションなしトークン化
- `group_into_chunks()`: 75トークン単位分割 + BOS/EOS
- `get_long_prompt_embeddings_sdxl()`: メインのembedding生成関数

### Compel 2.3.1（断念）
- `CompelForSDXL`クラスで長プロンプト対応のライブラリ
- 依存関係競合で断念: `gradio` が `huggingface-hub>=1.16.0` を要求、`transformers` が `<1.0` を要求
- HF SpaceのPython環境（`requirements.txt`経由のpip install）では解決不可能

## テスト結果

### 短プロンプト（~15トークン）
- 平均輝度: 69
- 画像品質: 正常（キャラクターが描画されている）
- 黒画像: なし

### 長プロンプト（~65トークン）
- 平均輝度: 110
- 画像品質: 正常（シーン説明が反映されている）
- 黒画像: なし

### 100+トークンプロンプト
- 平均輝度: 119
- 画像品質: 正常
- 黒画像: なし
- HF Spaceのログにエラーなし

## 失敗理由の精査

### v1の失敗
- `max_length=tokenizer.model_max_length` (=77) で長文が最初から切り捨て
- pooled embeddingの次元不整合

### v2の失敗（黒画像の原因特定）
sd_embedの実装を直接確認した結果、v2が再現できていなかった关键点:
1. `hidden_states[-2]` (penultimate layer) の使用漏れ
2. pooled embeddingの取得元が`text_encoder`ではなく`text_encoder_2`であること
3. positive/negativeのチャンク数不一致

## 教訓

1. **sd_embedパッケージは導入しない**: 依存関係が重い（notebookなど）。自前実装で十分
2. **Compelも導入しない**: 依存関係競合のリスクがある
3. **HF Spaceのpip installは制約が厳しい**: 既存の依存関係と競合しやすい
4. **ZeroGPUのインスタンスは一時的**: 各起動でチェックポイントを再ダウンロード
5. **embeddingのNaN/Infチェックは必須**: `torch.isfinite()` で検証
6. **画像の平均輝度で黒画像を検出可能**: 0に近い値はNaN/Infの兆候

## 結論
- 「SDXLは77トークン超が不可能」ではない
- chunkingアプローチは可能だが、SDXLのconditioning形式を正確に再現する必要がある
- 自前chunking実装で成功
- 关键点: `hidden_states[-2]`、`text_encoder_2`のpooled出力、positive/negativeのチャンク数一致
- 成功した実装は `scripts/hf-space/app.py` に保存済み

## 次のステップ
1. フル解像度（1152x768）でのテスト
2. `generate_article.py`とのエンドツーエンドテスト
3. HF Spaceへのデプロイ確認
