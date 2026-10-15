# 画像生成プロンプト精査結果

生成モデルごとに固定値プロンプトを分離し、全体量を削減する目的で精査。

## 使用モデル

| # | モデル | 種類 | プロンプト形式 | ネガティブ対応 |
|---|---|---|---|---|
| 1 | Nova-Furry-XL (IL v18.0A) | SDXL / Illustrious | Danbooruタグ | ✅ あり |
| 2 | Flux.1 (Pollinations) | DiT / Transformer | 自然言語 | ❌ 非サポート |

---

## Nova-Furry-XL (Illustrious系) / HuggingFace

### ポジティブ - 最終案（7タグ・2026-10-15時点）

| タグ | 変更 | 理由 |
|---|---|---|
| `masterpiece` | 維持 | Illustrious必須 |
| `best quality` | 維持 | Illustrious必須 |
| `amazing quality` | **削除** | `best quality` と重複 |
| `very aesthetic` | **追加** | Illustrious公式推奨 |
| `ultra-detailed` | 維持 | Illustrious必須 |
| `absurdres` | **削除**（2026-10-06） | 947009c「順序変更+品質タグ削減」で削除 |
| `newest` | **削除**（2026-10-06） | 947009c「順序変更+品質タグ削減」で削除（年代制御不要と判断） |
| `furry` | 維持 | 必須 |
| `no human` | **追加**（2026-10-15） | human被写体防止のダブルガード（ネガティブ `human` と併用）。Illustrious公式ガイドの Subject Details タグ。Fluxフォールバック（ネガティブ非サポート）でも有効。Danbooru標準タグではないため IL v18.0A での実効は次回生成で検証（詳細: `tasks/2026-10-15-positive-prompt-no-human.md`） |
| `anthro` | **削除** | キャラプロンプトで重複 |
| `safe for work` | 維持 | SFW必須 |
| `wholesome` | **削除** | 非標準Danbooruタグ |
| `family-friendly` | **削除** | Danbooruタグではない（無効） |

```
masterpiece, best quality, very aesthetic, ultra-detailed, furry, no human, safe for work
```

### ネガティブ - 最終案（16タグ）

| 順 | タグ | カテゴリ | 変更 | 理由 |
|---|---|---|---|---|
| 1 | `nsfw` | SFW | **追加** | Danbooru標準カテゴリタグ、1タグで全SFW制御 |
| 2 | `human` | 被写体 | **再追加**（2026-10-14） | 実写風human被写体防止ガード。初回精査で不要と判断したが再検討で追加（anthroガード。過剰抑制はポジティブの `furry`/`anthro` タグで緩和） |
| 3 | `worst quality` | 品質 | 維持 | 品質必須 |
| 4 | `bad anatomy` | 品質 | 維持 | 必須 |
| 5 | `deformed` | 品質 | 維持 | 変形系必須 |
| 6 | `bad hands` | 品質 | 維持 | 必須 |
| 7 | `missing fingers` | 品質 | 維持 | 必須 |
| 8 | `extra digits` | 品質 | 維持 | 必須 |
| 9 | `fewer digits` | 品質 | **追加** | 公式推奨 |
| 10 | `cropped` | 品質 | 維持 | 必須 |
| 11 | `very displeasing` | 品質 | **追加** | Illustrious必須 |
| 12 | `ugly` | 品質 | **追加** | 公式推奨 |
| 13 | `jpeg artifacts` | アーティファクト | **追加** | 公式推奨 |
| 14 | `signature` | 水印 | **追加** | 公式推奨 |
| 15 | `watermark` | 水印 | **追加** | 公式推奨 |
| 16 | `username` | 水印 | **追加** | 公式推奨 |

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
nsfw, human, worst quality, bad anatomy, deformed, bad hands, missing fingers, extra digits, fewer digits, cropped, very displeasing, ugly, jpeg artifacts, signature, watermark, username
```

### 順序の理由

SDXLのCLIPエンコーダーでは先頭トークンほど重みが大きい:
1. **SFW (`nsfw`)** - 最優先で先頭
2. **被写体 (`human`)** - 実写風human被写体防止（anthroガード）
3. **品質核心 (`worst quality`〜`deformed`)** - 画像品質の根本
4. **手指・四肢 (`bad hands`〜`fewer digits`)** - 具体的な失敗パターン
5. **美観 (`very displeasing`, `ugly`)** - 美的品質
6. **アーティファクト・水印 (`jpeg artifacts`〜`username`)** - 末尾（低優先度）

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

## 削減まとめ（2026-10-15時点の実値）

| 項目 | 精査対象（2026-10-05） | 現在 | 変更 |
|---|---|---|---|
| Nova-Furry-XL ポジティブ | 9タグ | **7タグ**（2026-10-06: 8→6 品質タグ削減、2026-10-15: `no human` 追加で 7） | -2 |
| Nova-Furry-XL ネガティブ | 20タグ | **16タグ**（2026-10-14: `human` 追加で 16） | -4 |
| Flux.1 | 未対応 | 未対応 | 超低優先度 |
| **全体** | **29タグ** | **23タグ** | **-6（-21%）** |
