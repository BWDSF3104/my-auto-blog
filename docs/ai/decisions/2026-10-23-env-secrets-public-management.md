# ローカルシークレットと公開変数の分離管理（env 管理方針） — 最終

**Status**: 最終 (2026-10-23)
**Date**: 2026-10-23
**関連タスク**: `docs/ai/tasks/2026-10-23-nsfw-fork-hardcode-audit.md`

## 要件（ユーザー、2026-10-23）

1. **シークレットと公開変数の分離は必須**
2. 現行 `.env` の中身は全て秘匿情報 → **`.env` はシークレットのみ維持し、公開変数を入れない**
3. 公開変数は **Git 管理（トラッキング）**
4. フォーク先管理者は自分自身 → フォークリポジトリも自分のリポジトリとして扱う

## 最終設計

| ファイル | 中身 | Git |
|---|------|-----|
| `.env` | **シークレットのみ**（現行 12 キー、変更なし） | gitignore（維持） |
| **`.env.public`**（新規） | **公開値のみ**（サイト、プロンプト、ratings、モデル名等） | **トラッキング（コミット）** |
| `.env.example` | **不要**（`.env.public` 自体が値の文書） | — |
| GitHub Secrets / リポジトリ変数 | 変更なし | — |
| HuggingFace Space 設定 | 変更なし（Space 設定 env、`.env` は読まない） | — |

### `.env.public` の対象変数（本リポジトリ値はすべて現行既定値）

- サイト: `SITE_ORIGIN`, `SITE_BASE_PATH`, `SITE_URL`
- 記事生成: `BASE_QUALITY_PROMPT`, `NEGATIVE_PROMPT`, `HF_SPACE_ID`,
  `IMAGE_PROVIDER`, `IMAGE_FALLBACK_URL_TEMPLATE`
- e621: `E621_ALLOWED_RATINGS=s,q`, `E621_NSFW_RATINGS=e,q`
- HF Space: `MODEL_REPO_ID`, `MODEL_FILENAME`（ローカルデバッグ / Space 設定）
- Rakuten: `RAKUTEN_ORIGIN`, `RAKUTEN_REFERER`
- 他: `CACHE_TTL_HOURS`, `MAX_INLINE_IMAGES`, `ZERO_GPU_*` 等も記載（必要に応じて）

## 読み込み方法

エントリ点 5 つ（`fetch_topics` / `generate_article` / `genre_score` /
`test_real_apis` / `gsc_index`）に:

```python
from dotenv import load_dotenv
from dotenv.find_dotenv import find_dotenv

load_dotenv()  # .env（シークレット、gitignore。CI では存在しない → no-op）
_public = find_dotenv(filename=".env.public", usecwd=True)
if _public:
    load_dotenv(_public)
```

- `generate_article.py` は「読取 → `from article.config import *`」の既存順序を維持
- CI: `.env.public` は checkout 済みで読取されるが、同名変数はリポジトリ変数優先
  （`load_dotenv` の `override=False`）→ 干渉なし
- 分離により同名キーは存在しない

## ルール

- **シークレット**: `.env.public` / git に一切入れない。
  `.env`（ローカル）/ GitHub Secrets（CI）/ Space 設定（HF）のみ。コード既定値なし。
- **公開値**: すべて `.env.public` に書く
- コミット前に `.env.public` にシークレットキーが混入していないか確認

## フォークフロー（管理者は自分）

1. fork
2. **`.env.public`（トラッキング）を編集してコミット**（フォーク側の環境変更は
   これがコミット）
3. `.env`（シークレット、ローカル）+ GitHub Secrets（`GSC_SA_JSON` は新規、
   `HF_TOKEN` 等）+ HuggingFace Space 設定
4. 以上（テンプレートコピー等の余計な手順なし）

## 検討済み代替案（不採用）

- **A**: `.env`（シークレット+公開の混在）+ `.env.example`（文書）—
  不採用。シークレットと公開が混在する
- **B**: `.env`（公開）+ `.env.secrets`（両方 gitignore）—
  不採用。公開値が Git 管理されない
- **C**: `.env`（公開）をトラッキング + `.env.secrets` を gitignore —
  不採用。ユーザー指示で「現行 `.env`（全シークレット）に公開変数を加えない」
- **D（採用）**: `.env`（シークレット、不変）+ `.env.public`（公開、トラッキング）
