# 2026-10-05: HF ZeroGPU 調査 + KI-003 根本原因特定

## 背景

- P1 Backlog「HuggingFace API 使用可能状況の確認」を実行
- KI-003（記事内画像が劇中シーンと関連していない）の根本原因を特定

## 調査内容

### 1. HF Space 接続確認

- `blume/kemono-image-api` は ZeroGPU A10G で稼働中
- 最終起動: 2026-09-27。Space 停止時は起動に数分要する
- テスト予測: 画像生成に約 6.8 秒/枚

### 2. ZeroGPU クォータ確認

- 無料枠: 3.5 分/日 (210 秒/日)
- `@spaces.GPU(duration=90)` で 1 リクエストあたり 90 秒予約
- 実質: 1 日約 2 リクエストのみ可能
- 1 記事 = 3 画像 (1 ヘッダー + 2 インライン) = 270 秒 → 無料枠の 1 記事生成ですら超過

### 3. コンテナログ分析 (MHT ファイルから抽出)

- 全プロンプトが SDXL CLIP エンコーダーの 77 トークン上限を超過
- 実測トークン数: 78-155 トークン
- 77 トークン以降は破棄されるため、末尾の「シチュエーション（シーン説明）」が完全に無視される

### 4. 77 トークン上限の性質

- Stable Diffusion XL の CLIP ViT-L/14 エンコーダーのアーキテクチャ制約
- HF Space の設定では変更不可
- プロンプト短縮のみが解決策

### 5. コンポーネント別のトークン消費量 (実測)

| コンポーネント | トークン数 | 備考 |
|---|---|---|
| BASE_QUALITY_PROMPT | 25 | `masterpiece, best quality, amazing quality, ultra-detailed, furry, anthro, safe for work, wholesome, family-friendly` |
| art_style | 11-14 | `anime style, illustration, cel shading, vibrant colors` など |
| character_1 | 24-29 | 記事依存 |
| character_2 | 23-30 | 記事依存 |
| **固定分合計** | **88-96** | **77 超過済み (15-25%)** |
| シチュエーション | 0-15 | 77 トークンで切り捨てられるため常に破棄 |

## 結論

- KI-003 の根本原因は「プロンプトが 77 トークン超過でシーン説明が破棄される」こと
- HF ZeroGPU のクォータでは 1 日 2 リクエストしか利用不可
- 修正案:
  - A: `compose_image_prompt()` の BASE_QUALITY_PROMPT とキャラ定義を短縮 (77 トークン内に収める)
  - B: `IMAGE_PROVIDER=pollinations` をデフォルトに変更 (クォータ無制限)
  - C: `MAX_INLINE_IMAGES=1` に制限
- 推奨: A + B の併用

## 更新したドキュメント

- `docs/ai/known-issues.md`: KI-003 に根本原因、修正案を追記
- `docs/ai/backlog.md`: P1 完了としてマーク、新 P1 項目を追加
- `docs/ai/api-rate-limits.md`: HF ZeroGPU + Pollinations.ai を追加
- `docs/ai/current-task.md`: 調査完了を記録
