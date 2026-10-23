# NSFWフォーク移行準備: ハードコード部分的抽出調査

**Status**: 完了
**Date**: 2026-10-23
**Next Action**: 提示完了。P0 の修正実装はユーザー指示待ち

## 意図 / 背景

本プロジェクトは将来、NSFW対応版のフォークを作成される。
移行前に、SFW/NSFW の分岐点・サイト特定・データ収集にハードコードされている要素を
特定し、「現行動作（既定値）を維持しつつ、環境変数・設定値で切り替えられる」ようにする
修正箇所を調査する。

## 調査結果 / 変更内容

### P0: NSFWフォークに直接関わるハードコード（変更必須）

| # | 位置 | 内容 | 課題 | 推奨修正 |
|---|------|------|------|----------|
| 1 | `scripts/article/config.py:71` | `BASE_QUALITY_PROMPT = "..., safe for work"` | SFW強制タグが画像プロンプトにハードコード。NSFW版では除去/変更が必要 | `"safe for work"` を環境変数（例: `IMAGE_SFW_TAG`、既定 `safe for work`）から生成、フォークでは `""` に |
| 2 | `scripts/article/image.py:225` | HF Space 呼び出しの negative prompt `"nsfw, human, worst quality, ..."` | クライアント側の negative prompt がハードコード。NSFW版では "nsfw, human" を除去 | `config.py` に `NEGATIVE_PROMPT`（既定＝現行値）を置き、`image.py` から参照 |
| 3 | `scripts/article/config.py:56` | `HF_SPACE_ID = "blume/kemono-image-api"` | 環境変数オーバーライドなし。フォークは独立の Space が必要 | `os.environ.get("HF_SPACE_ID") or "blume/kemono-image-api"` |
| 4 | `hf-space/app.py:24` | `_cached_neg_prompt = "nsfw, human, ..."` | Space 側の negative prompt ハードコード。フォークの Space は別値が必要 | 環境変数 `NEGATIVE_PROMPT`（既定＝現行値）から生成 |
| 5 | `hf-space/app.py:9-10` | `REPO_ID = "IbarakiDouji/Nova-Furry-XL"` / `FILENAME = "novaFurryXL_ilV180A.safetensors"` | モデルがハードコード。フォークで別モデル（NSFW向け）に切り替え可能にしたいため | 環境変数 `MODEL_REPO_ID` / `MODEL_FILENAME`（既定＝現行値）から生成 |
| 6 | `scripts/prompts/kemono_story.txt` L21 / L44 / L107、`default.txt` L69、`ai_deep.txt` L46 | 「SFWの範囲内」「画像は必ずSFW」「外見はSFW」等の指示文 | NSFW版では削除/書き換えが必要だが、テンプレート内に固定 | テンプレートに `{safety_instruction}` プレースホルダーを置き、`config.py` の `SAFETY_INSTRUCTION`（既定＝現行SFW文）から注入。代替案: ファイル単体で差し替え（現アーキテクチャでもフォーク可行だが、CIで明示的に設定管理したい場合はパラメータ化） |
| 7 | `scripts/fetch_topics.py` L65-73 / L323-327 / L418-420 | e621 検索が全 `rating:safe` / `rating:questionable` 固定、`_is_nsfw_post` が `e`/`q` を除外、NSFWタグ除外リスト | NSFW版では `rating:explicit` を収集・保持すべき | 許可 rating セット（例: `E621_ALLOWED_RATINGS` 既定 `"s,q"`、NSFW版は `"s,q,e"`）と除外タグリストを環境変数/設定化。e621 をトレンドソースとして再有効化する場合は `NON_TREND_SOURCES` 制御も |

### P1: サイト特定（GitHub Pages 領域名/パス）

| # | 位置 | 内容 | 課題 | 推奨修正 |
|---|------|------|------|----------|
| 8 | `scripts/gsc_index.py:22` | `SITE_URL = "https://bwdsf3104.github.io/my-auto-blog/"` | 完全ハードコード（env 未使用）。フォークのサイトURLとは異なる | `os.environ.get("SITE_ORIGIN") or "https://BWDSF3104.github.io"` + `BASE_URL` で構成 |
| 9 | `scripts/article/config.py:37-38, 57-58` | `RAKUTEN_ORIGIN`/`RAKUTEN_REFERER`/`SITE_ORIGIN` のフォールバックが `bwdsf3104.github.io` 系 | env 上書きは既にあり、フォークはリポジトリ変数設定で対応可能 | 現状でもフォーク可行（CI リポジトリ変数で設定）。フォースフルにする必要は低（記録のみ） |
| 10 | `scripts/fetch_topics.py:48` | `USER_AGENT = "my-auto-blog/1.0 (https://github.com)"` | 项目名のみ、実害なし | 任意: 環境変数で指定可能にする |

### P1: フォークで別サービスにする可能性のあるもの

| # | 位置 | 内容 | 課題 | 推奨修正 |
|---|------|------|------|----------|
| 11 | `scripts/article/image.py:121` | Pollinations フォールバック `https://image.pollinations.ai/prompt/...?model=flux&width=896&height=512` | NSFW版は別画像サービス（例: 自前スペース + OpenAI DALL-E 等）を使用する可能性。Pollinations も NSFW は別エンドポイント/鍵が必要 | `IMAGE_FALLBACK_URL_TEMPLATE`（既定＝現行値）に抽出 |

### P2: データソース定義（JSON 化推奨）

- `scripts/fetch_topics.py` 内コードに固定:
  - `REDDED_SUBS` (L53-60), `E621_TAGS` (L65-73), `RSS_FEEDS` (L88-129),
  - `HN_TOP_STORIES_URL`/`HN_ITEM_URL` (L132-133), `GITHUB_SEARCH_QUERIES` (L137-144),
  - `BLUESKY_SEARCHES` (L147-153), `USER_AGENT` (L48)
- 現状: 収集ソースを追加・変更するにはコード編集が必要。
- 推奨: `data/sources.json`（または `scripts/article/config.py` の JSON-serializable 定数）へ移管し、
  フォークでソース構成をファイル単位で差し替えられるようにする。

### P2: その他

- `scripts/article/config.py:50-53` `MODELS_TO_TRY`（Gemini モデルリスト）— 両プロジェクト共通の API なので現状で可。環境変数化は任意。
- `scripts/genre_score.py` — Cloudflare Workers AI モデル ID ハードコードだが、API 不变なので現行動作維持で可。
- `scripts/article/affiliate.py` — Amazon/Rakuten のドメイン URL は固定だが、トラッキング ID は既に env（`.env` + CI secret）管理。フォークも同じサービスなら現行で可。
- `hf-space/app.py:341-349` — Gradio UI のデフォルト値のみ。無影響。

### 現行でフォーク対応済み（変更不要）

- `BASE_URL` / `SITE_ORIGIN` / `RAKUTEN_ORIGIN` / `RAKUTEN_REFERER` — env + フォールバックあり。
- `astro.config.mjs` — `SITE_ORIGIN` / `SITE_BASE_PATH` env 駆動。
- `IMAGE_PROVIDER` — env（hf / pollinations）で画像プロバイダ切替可能。
- CI `deploy.yml` — `SITE_ORIGIN` / `SITE_BASE_PATH` / `RAKUTEN_*` をリポジトリ変数で渡す設計。
  フォーク側は `main` を追従し、自分のリポジトリ変数（`SITE_BASE_PATH`、`SITE_ORIGIN`、`RAKUTEN_ORIGIN` 等）を定義するだけで動作する。
- `.env`（ローカル開発）/ GitHub Secrets — フォークに複製/再登録すれば可。

## 推奨移行手順（フォーク側）

1. **設定抽出（P0）**: `scripts/article/config.py` に `IMAGE_SFW_TAG`, `NEGATIVE_PROMPT`,
   `HF_SPACE_ID`（env 化）, `SAFETY_INSTRUCTION` を追加（既定値＝現行値で動作不変）。
2. **プロンプトパラメータ化**: 5つのプロンプトファイルの SFW 指示行を `{safety_instruction}`
   プレースホルダーに置き、`kemono_params` と同様に `build_prompt` で注入。
3. **HF Space パラメータ化**: `hf-space/app.py` に `MODEL_REPO_ID`, `MODEL_FILENAME`,
   `NEGATIVE_PROMPT` の env 対応（既定＝現行値）。
4. **GSC**: `gsc_index.py` の `SITE_URL` を `SITE_ORIGIN` + `BASE_URL` から導出。
5. **e621 rating**: `fetch_topics.py` に `E621_ALLOWED_RATINGS`（既定 `"s,q"`）を追加。
   NSFW版は `"s,q,e"` に。`_is_nsfw_post` も該当 rating を条件化。
6. **フォーク側設定**:
   - `.env` に `HF_SPACE_ID`, `IMAGE_SFW_TAG=""`, `NEGATIVE_PROMPT`（nsfw, human を削除）、
     `SAFETY_INSTRUCTION`（SFW指示を削除/書き換え）、`E621_ALLOWED_RATINGS="s,q,e"` を追加。
   - CI リポジトリ変数: `SITE_BASE_PATH`, `SITE_ORIGIN`, `RAKUTEN_ORIGIN`, `RAKUTEN_REFERER` を設定。
   - `hf-space` を独立の HuggingFace Space にデプロイ（`MODEL_REPO_ID`/`MODEL_FILENAME`
     で NSFW対応モデルを指定）。
7. **検証**: デフォルト値のままで `pytest scripts/tests/` + `npm run build` で
   現行動作不変を確認。特に `scripts/tests/equivalence_golden/` のハッシュ値テストで
   生成結果の等価性を確認（`build_golden.py` 経由）。

## Verification

- 本タスクは調査・報告のみ（コード変更なし）。
- 検証: 読み込みベース調査。実行: 実装時（上記手順 6 以降）に `pytest` + `build` を実行。

## 完了時 Memory Bank 操作

- [x] `current-task.tsv` の参照行を削除
- [x] 解決した `known-issues/` ファイルを `known-issues/archive/` へ `mv`（該当なし）
- [x] `backlog.md` の完了項目を削除（該当なし）
