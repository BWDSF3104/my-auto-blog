# 画像生成プロンプト精査結果

生成モデルごとに固定値プロンプトを分離し、全体量を削減する目的で精査。

## 使用モデル

| # | モデル | 種類 | プロンプト形式 | ネガティブ対応 |
|---|---|---|---|---|
| 1 | Nova-Furry-XL (IL v18.0A) | SDXL / Illustrious | Danbooruタグ | ✅ あり |
| 2 | Flux.1 (Pollinations) | DiT / Transformer | 自然言語 | ❌ 非サポート |

---

## Nova-Furry-XL (Illustrious系) / HuggingFace

### ポジティブ - 最終案（8タグ）

| タグ | 変更 | 理由 |
|---|---|---|
| `masterpiece` | 維持 | Illustrious必須 |
| `best quality` | 維持 | Illustrious必須 |
| `amazing quality` | **削除** | `best quality` と重複 |
| `very aesthetic` | **追加** | Illustrious公式推奨 |
| `ultra-detailed` | 維持 | Illustrious必須 |
| `absurdres` | **追加** | Illustrious公式推奨 |
| `newest` | **追加** | Illustrious公式推奨（年代制御） |
| `furry` | 維持 | 必須 |
| `anthro` | **削除** | キャラプロンプトで重複 |
| `safe for work` | 維持 | SFW必須 |
| `wholesome` | **削除** | 非標準Danbooruタグ |
| `family-friendly` | **削除** | Danbooruタグではない（無効） |

```
masterpiece, best quality, very aesthetic, ultra-detailed, absurdres, newest, furry, safe for work
```

### ネガティブ - 最終案（15タグ）

| 順 | タグ | カテゴリ | 変更 | 理由 |
|---|---|---|---|---|
| 1 | `nsfw` | SFW | **追加** | Danbooru標準カテゴリタグ、1タグで全SFW制御 |
| 2 | `worst quality` | 品質 | 維持 | 品質必須 |
| 3 | `bad anatomy` | 品質 | 維持 | 必須 |
| 4 | `deformed` | 品質 | 維持 | 変形系必須 |
| 5 | `bad hands` | 品質 | 維持 | 必須 |
| 6 | `missing fingers` | 品質 | 維持 | 必須 |
| 7 | `extra digits` | 品質 | 維持 | 必須 |
| 8 | `fewer digits` | 品質 | **追加** | 公式推奨 |
| 9 | `cropped` | 品質 | 維持 | 必須 |
| 10 | `very displeasing` | 品質 | **追加** | Illustrious必須 |
| 11 | `ugly` | 品質 | **追加** | 公式推奨 |
| 12 | `jpeg artifacts` | アーティファクト | **追加** | 公式推奨 |
| 13 | `signature` | 水印 | **追加** | 公式推奨 |
| 14 | `watermark` | 水印 | **追加** | 公式推奨 |
| 15 | `username` | 水印 | **追加** | 公式推奨 |

削除したタグ:
| タグ | 理由 |
|---|---|
| `bad quality` | `worst quality` のサブセット |
| `low quality` | `worst quality` のサブセット |
| `mutated` | `deformed` のサブセット |
| `disfigured` | `deformed` のサブセット |
| `lowres` | `worst quality` のサブセット |
| `nude` | `nudity` と重複 |
| `explicit` | `nsfw` で網羅 |
| `nudity` | `nsfw` で網羅 |
| `sexual` | `nsfw` で網羅 |
| `erotic` | `nsfw` で網羅 |
| `pornographic` | `nsfw` で網羅 |
| `gore` | 暴力系不要 |
| `blood` | 暴力系不要 |
| `violent` | 暴力系不要 |
| `inappropriate` | 非標準タグ（無効） |
| `human` | furry特有だが不要 |
| `multiple tails` | furry特有だが不要 |
| `long body` | furry特有だが不要 |
| `text` | 不要 |
| `sketch` | スタイル制御不要 |
| `simple background` | 不要 |
| `conjoined` | 不要 |
| `bad ai-generated` | 不要 |
| `glitch` | 不要 |
| `modern`~`oldest` | 年代制御不要 |
| `graphic`~`abstract` | スタイル制御不要 |

```
nsfw, worst quality, bad anatomy, deformed, bad hands, missing fingers, extra digits, fewer digits, cropped, very displeasing, ugly, jpeg artifacts, signature, watermark, username
```

### 順序の理由

SDXLのCLIPエンコーダーでは先頭トークンほど重みが大きい:
1. **SFW (`nsfw`)** - 最優先で先頭
2. **品質核心 (`worst quality`〜`deformed`)** - 画像品質の根本
3. **手指・四肢 (`bad hands`〜`fewer digits`)** - 具体的な失敗パターン
4. **美観 (`very displeasing`, `ugly`)** - 美的品質
5. **アーティファクト・水印 (`jpeg artifacts`〜`username`)** - 末尾（低優先度）

---

## Flux.1 (Pollinations.ai) - 超低優先度

自然言語形式。ネガティブプロンプト非サポート（公式明言）。

| 項目 | 判定 |
|---|---|
| Danbooruタグ形式 | ❌ 無効。自然言語に変換必要 |
| ネガティブプロンプト | ❌ 非サポート |

**モデル別プロンプト切り替え実装: 超低優先度で見送る**。現在のPollinationsはHF失敗時のフォールバックであり、Nova-Furry-XL用プロンプトをそのまま使用し続ける。

---

## 実装対象（Nova-Furry-XLのみ）

## 削減まとめ

| 項目 | 現在 | 最終案 | 変更 |
|---|---|---|---|
| Nova-Furry-XL ポジティブ | 9タグ | **8タグ** | -1 |
| Nova-Furry-XL ネガティブ | 20タグ | **15タグ** | -5 |
| Flux.1 | 未対応 | 未対応 | 超低優先度 |
| **全体** | **29タグ** | **23タグ** | **-6（-21%）** |
