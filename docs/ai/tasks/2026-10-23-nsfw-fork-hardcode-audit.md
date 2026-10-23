# NSFWフォーク移行準備: ハードコード部分的抽出調査

**Status**: 完了
**Date**: 2026-10-23
**Next Action**: env 追加（1,2,3,4,5,7,8,11）**完了・検証済み**（454 passed）。CI/移行の適用先（GitGud.io 等）決定はユーザー判定待ち（移行作業は別タスク）。詳細: 判定サマリー / decisions/2026-10-23-env-secrets-public-management.md / 本ファイルの GitGud.io 調査

## 意図 / 背景

本プロジェクトは将来、NSFW対応版を**GitGud.io**（GitLab Self-Managed 基盤の
無料ホスティング）にコピーする方針（**GitHub 間でのフォークではなく**、
ユーザーの「nsfw 規約」上の判断による）。移行前に、SFW/NSFW の分岐点・サイト特定・
データ収集にハードコードされている要素を特定し、「現行動作（既定値）を維持しつつ、
環境変数・設定値で切り替えられる」ようにする修正箇所を調査・検討する。

## 検討事項 / 判断

- **プロンプト (P0-6)**: フォーク側で新しいプロンプトテンプレートを用意する見込み。
  スクリプトレベル（`{safety_instruction}` プレースホルダー化など）での対応は不要。
  根拠: `scripts/article/gemini.py` の `load_prompt_template()` が
  `scripts/prompts/<prompt_type>.txt` をファイル名指定で読み込むため、
  フォーク側で `kemono_story.txt` 等を差し替えるだけで動作する。
- **env 追加の置き所（管理方針）**:
  - **ローカル開発**: `.env`（**シークレットのみ**、gitignore、**変更しない**）+
    `.env.public`（**公開のみ**、**git 管理**）。エントリ点 5 つ
    （`fetch_topics` / `generate_article` / `genre_score` / `test_real_apis` /
    `gsc_index`）が両方を読み込む。
  - **GitLab CI (GitGud.io)**: `.github/workflows/*.yml` はそのまま不可
    （`.gitlab-ci.yml` へ移行必要）。Vars/Secrets 相当は **CI/CD Variables**
    （通常変数 / Masked・Protected、リポジトリ単位設定可、既定 8000 件
    上限）。新 env 変数の CI 反映は CI/CD Variables で。
  - **HuggingFace Space** (`hf-space/app.py`): `load_dotenv()` は呼んでいないため
    `.env` 依存しない — **Space の設定（Environment variables）に直接 env 設定**
    （ローカルデバッグ時は OS 環境変数 / `.env` を shell に export するか dotenv 読み込み）。

## 判定サマリー (2026-10-23)

**方針（ユーザー指定）**: 現行挙動をなるべく変えない / 変更最小限 / フォーク先での変更容易。

| # | 項目 | 判定（最終） |
|---|------|--------------|
| 1 | `BASE_QUALITY_PROMPT` (config.py:71) | **全体 env 化**（既定＝現行値）。SFW 部分だけ抽出しない（ユーザー指示: プロンプト分割は複雑化のため不要） |
| 2 | negative prompt (image.py:225) | `NEGATIVE_PROMPT`（既定＝現行値）を config.py に追加し、image.py が参照 |
| 3 | `HF_SPACE_ID` (config.py:56) | env 化、既定＝現行値 |
| 4 | Space negative prompt (hf-space/app.py:24) | env `NEGATIVE_PROMPT`、既定＝現行値（Space 設定で指定） |
| 5 | `REPO_ID`/`FILENAME` (hf-space/app.py:9-10) | env `MODEL_REPO_ID` / `MODEL_FILENAME`、既定＝現行値（Space 設定で指定） |
| 6 | プロンプトテンプレートの SFW 指示 | スクリプト対応不要（フォーク側でファイル差し替えのみ） |
| 7a | e621 収集 rating | `E621_ALLOWED_RATINGS`（既定 `"s,q"` ＝ 現行クエリとバイト同一）。セットに `e` が含まれる場合のみ、各エントリのベース rating に `,explicit` を付加（カンマ区切り許容は 2026-10-23 実確認） |
| 7b | e621 除外 rating | `E621_NSFW_RATINGS`（既定 `"e,q"` ＝ 現行 `("e","q")`、既存テスト全件保持）。フォーク例: `""`（rating 除外を無効化し e を特徴集計に残す） |
| 7c | e621 `nsfw_tags` 20 タグ集合 | **現行維持**（変更最小限。フォーク側で緩和が必要ならフォーク側ファイル編集） |
| 7d | e621 `order:random` 付加 (L562) | **維持**（バイト同一。ベース `order:*` は既に上書き済み） |
| 8 | `SITE_URL` (gsc_index.py:22) | **直接 env 化**（既定＝現行値、ホスト小写もバイト同一）。`SITE_ORIGIN` 導出しない（既定のドメイン大小区違いで GSC の siteUrl 一致リスク） |
| 9 | RAKUTEN_*/SITE_* フォールバック | env 駆動済み、変更要因なし |
| 10 | `USER_AGENT` (fetch_topics.py:48) | **除外**（変更最小限。フォーク先は 1 行編集で対応可能。env 化が必要なら 1 行で実施可能） |
| 11 | Pollinations フォールバック URL (image.py:121) | `IMAGE_FALLBACK_URL_TEMPLATE`（既定＝現行値、`&seed={seed}` プレースホルダー保持） |
| P2 | ソース定義の JSON 化等 | 除外（将来タスク） |

### e621 最終設計

- **収集側**: `E621_TAGS` のエントリごとのベース rating（s/q）は現行のまま。
  クエリの rating メタタグは「ベース rating」のみ（既定でバイト同一）。
  `E621_ALLOWED_RATINGS` に `e` が含まれる場合のみ `,explicit` を付加
  （例: `kemono rating:safe,explicit order:date`）。e621 API がカンマ区切り
  rating を受け付けることは 2026-10-23 に実確認済み（`rating:safe,questionable`、
  `rating:safe,explicit`、`rating:s,q` 等すべて HTTP 200、
  検証スクリプト `docs/ai/tmp/e621_rating_comma_check.py`）。
- **除外側**: `_is_nsfw_post` の rating 判定 `rating in ("e", "q")` を
  `E621_NSFW_RATINGS`（既定 `"e,q"`）から生成するセット判定へ。
- **フォーク設定例**: `E621_ALLOWED_RATINGS=s,q,e`、`E621_NSFW_RATINGS=""`
  （e 投稿を特徴集計に残す）。

**env 管理方針（最終）**: `.env`（シークレットのみ、gitignore、**不変**）+
`.env.public`（公開のみ、**git 管理**）。`.env.example` は不要。
エントリ点 5 つが両方を読み込む。詳細:
`docs/ai/decisions/2026-10-23-env-secrets-public-management.md`
 
## GitGud.io 環境調査 (2026-10-23、調査のみ・実装未着手)

**方針変更**: NSFW 版の置き場は「GitHub 間でのフォーク」から
「**GitGud.io へのコピー**」へ変更。GitGud.io は GitLab Self-Managed
基盤の無料ホスティング（Sapphire 運営、無制限非公開リポジトリ、
無制限リポジトリサイズ）。ユーザーは「実行はせず調査検討」と指示。
本項目は web 検索（公式情報 + 実利用例）による確認。実環境の検証は未実施。

### 機能対応確認 (GitHub Actions → GitLab / GitGud.io)

| 項目 | GitLab (GitGud.io) 相当 | 状況（調査結果） |
|---|---|---|
| Secrets | CI/CD Variables（Masked / Protected） | **可能**（GitLab 標準機能、リポジトリ単位設定可） |
| Vars | CI/CD Variables（通常変数） | **可能**（GitLab 標準機能、リポジトリ単位設定可） |
| 定期実行 | Pipeline Schedules | **可能**（GitLab 標準機能。GitGud.io で既に利用実例あり） |
| Push時の実行 | `.gitlab-ci.yml` | **対応可能**（`.github/workflows/*.yml` はそのまま不可） |
| 手動実行 | Run pipeline | **対応** |
| cron タイムゾーン | Pipeline Schedules `cron_timezone` | 指定可能（例: `Asia/Tokyo`、ActiveSupport TZ） |
| 手動トリガー | Run pipeline / API | **対応** |

### 重要点 3 点の確認

1. **Pipeline Schedules を利用できるか**: **可能**。GitLab の標準機能であり、
   GitGud.io では実際にユーザーが `/-/pipeline_schedules` を使用している
   実例を web 検索で確認（例: `odilitime/netrunner`, `Ed86/rjw`）。
   制約: Pipeline schedule worker が10分間隔で実行されるため、10分未満
   間隔の cron は効かない。1 日あたり各スケジュールの触发回数は最低
   24（60分間隔以上）まで制限可能。
2. **CI/CD Variables をリポジトリ単位で設定できるか**: **可能**。
   GitLab はプロジェクトレベル CI/CD Variables を標準サポート
   （既定でリポジトリあたり 8000 件上限、Masked/Protected 指定可）。
3. **共有 Runner で定期実行できるか / 自前 Runner 必要か**:
   **共有 Runner あり（利用には申請要）**。GitGud.io の公式情報では
   「Free shared CI. Just request access from us via a communication channel」
   と明記。つまり、**リポジトリ作成直後では CI が使えるわけではない。
   管理者（admin@gitgud.io）へのアクセス申請が必要**。SLA なし、優先度
   保証なし、共用。自前 Runner の登録も可能だが、今回用途には
   共有 Runner を前提。

### 制約・リスク

- **CI アクセス申請必須**: 共有 Runner は自動提供されない。アクセス申請を
  管理者に要する（処理待ちのリスク、所要期間不明）。
- **月間約20分の停止**: GitLab セキュリティ更新のための月間約 20 分
  の停止が公式で明記。Pipeline 実行が中断される可能性。
- **Compute 上限**: GitGud.io は「明示的な compute 上限なし」と公式に
  謳うが、実際の運用上限（instance quota 等）は管理者設定次第。
  確認できない（管理者への問い合わせ要）。
- **YAML 移行**: `.github/workflows/*.yml`（GitHub Actions）はそのまま
  使用不可。`.gitlab-ci.yml` へ書き換える必要（jobs 定義の GitLab 構文
  化、secrets/vars の CI/CD Variables 参照化、GSC 等の再構成）。
- **ビルド環境**: 本プロジェクト（Astro + Python + Node.js）のビルド・
  実行が共用 Runner の環境（Docker executor? Shell executor?）で動くか
  未確認（`.gitlab-ci.yml` 設計時に実環境検証要）。
- **GSC indexing**: Google Search Console indexing は GitHub 特有の
  CI 構成。GitLab 環境での再構成要。
- **ToS / NSFW 許容**: GitGud.io は tracking なし・Cloudflare なし
  で、GitHub/CF との運用環境が違う。NSFW 用途（非公開リポジトリ内）の
  許容度は管理者方針次第。GitHub/CF の nsfw 規約問題の再発防止観点で
  確認要。

### 未確定事項（要確認）

1. 共有 Runner へのアクセス申請の具体的手順・所要期間。
2. GitGud.io の compute quota / 上限の実際の運用（管理者問い合わせ）。
3. Pipeline Schedules の `cron_timezone=Asia/Tokyo` が想定どおり動くか
   （実環境で確認）。
4. 本プロジェクト（Astro + Python + Node.js）のビルド・実行が
   共用 Runner の環境で動くか（`.gitlab-ci.yml` 設計要）。
5. GitGud.io の ToS / 管理者方針が NSFW コンテンツ（非公開リポジトリ
   内）を許容するかどうか。

## 調査結果 / 変更内容

### P0: NSFWフォークに直接関わるハードコード（変更必須）

| # | 位置 | 内容 | 課題 | 推奨修正 |
|---|------|------|------|----------|
| 1 | `scripts/article/config.py:71` | `BASE_QUALITY_PROMPT = "..., safe for work"` | SFW強制タグが画像プロンプトにハードコード。NSFW版では除去/変更が必要 | `"safe for work"` を環境変数（例: `IMAGE_SFW_TAG`、既定 `safe for work`）から生成、フォークでは `""` に |
| 2 | `scripts/article/image.py:225` | HF Space 呼び出しの negative prompt `"nsfw, human, worst quality, ..."` | クライアント側の negative prompt がハードコード。NSFW版では "nsfw, human" を除去 | `config.py` に `NEGATIVE_PROMPT`（既定＝現行値）を置き、`image.py` から参照 |
| 3 | `scripts/article/config.py:56` | `HF_SPACE_ID = "blume/kemono-image-api"` | 環境変数オーバーライドなし。フォークは独立の Space が必要 | `os.environ.get("HF_SPACE_ID") or "blume/kemono-image-api"` |
| 4 | `hf-space/app.py:24` | `_cached_neg_prompt = "nsfw, human, ..."` | Space 側の negative prompt ハードコード。フォークの Space は別値が必要 | 環境変数 `NEGATIVE_PROMPT`（既定＝現行値）から生成 |
| 5 | `hf-space/app.py:9-10` | `REPO_ID = "IbarakiDouji/Nova-Furry-XL"` / `FILENAME = "novaFurryXL_ilV180A.safetensors"` | モデルがハードコード。フォークで別モデル（NSFW向け）に切り替え可能にしたいため | 環境変数 `MODEL_REPO_ID` / `MODEL_FILENAME`（既定＝現行値）から生成 |
| 6 | `scripts/prompts/kemono_story.txt` L21 / L44 / L107、`default.txt` L69、`ai_deep.txt` L46 | 「SFWの範囲内」「画像は必ずSFW」「外見はSFW」等の指示文 | NSFW版では削除/書き換えが必要だが、テンプレート内に固定 | **スクリプト対応不要**（検討事項参照: フォーク側で新テンプレートを準備し、`scripts/prompts/` 内のファイル差し替えのみ） |
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

## 推奨移行手順（GitGud.io 側）

1. **設定抽出（P0）**: `scripts/article/config.py` に `BASE_QUALITY_PROMPT`
   （全体 env 化）、`NEGATIVE_PROMPT`, `HF_SPACE_ID`, `IMAGE_FALLBACK_URL_TEMPLATE`
   （全項目: 既定値＝現行値で動作不変）を追加し `__all__` を更新。
   `image.py` は既に `from article.config import *` のため参照のみ（L225 の
   negative prompt 文字列は定数参照に）。
2. **プロンプト**: 本リポジトリ変更なし。フォーク側で `scripts/prompts/` 内テンプレートを
   新ファイル（NSFW版）として置き換える（`load_prompt_template()` はファイル名指定読み込みのため
   スクリプト変更なしで対応）。
3. **HF Space パラメータ化**: `hf-space/app.py` に `MODEL_REPO_ID`, `MODEL_FILENAME`,
   `NEGATIVE_PROMPT` の env 対応（既定＝現行値）。Space 設定（Environment variables）で指定。
   本リポジトリの Space は env 未設定 → 既定値（現行値）で動作不変。
4. **GSC**: `gsc_index.py` の `SITE_URL` を直接 env 変数 `SITE_URL` に（既定＝現行値、
   ホスト小写もバイト同一）。フォーク先はリポジトリ変数 `SITE_URL` を deploy step 1-D
   に追加。
5. **e621 rating**: `fetch_topics.py` に `E621_ALLOWED_RATINGS`（既定 `"s,q"`、
   `e` 含みで各エントリに `,explicit` 付加）と `E621_NSFW_RATINGS`（既定 `"e,q"`、
   `"", "q"` 等も可）を追加。`E621_TAGS` と `nsfw_tags` 集合は現行維持。
6. **GitGud.io 側設定**（管理者は自分・自分のリポジトリとして扱う）:
    - **`.env.public`（git 管理）を編集してコミット**: `BASE_QUALITY_PROMPT`
      （"safe for work" 削除等）、`NEGATIVE_PROMPT`（"nsfw, human" 削除）、
      `HF_SPACE_ID`、`E621_ALLOWED_RATINGS="s,q,e"`、`E621_NSFW_RATINGS=""`、
      `SITE_URL`、`IMAGE_FALLBACK_URL_TEMPLATE`
    - `.env`（シークレット、gitignore）+ **GitLab CI/CD Variables**
      （Masked 設定で `GSC_SA_JSON` を新規作成、`HF_TOKEN` 等再登録）+
      HuggingFace Space の Environment variables（`MODEL_REPO_ID` /
      `MODEL_FILENAME` / `NEGATIVE_PROMPT`）
    - **`.gitlab-ci.yml`**（`.github/workflows/*.yml` の GitLab 同等化）:
      `SITE_BASE_PATH`, `SITE_ORIGIN`, `RAKUTEN_ORIGIN`, `RAKUTEN_REFERER`
      等を CI/CD Variables として定義。Pipeline Schedules（cron、
      timezone `Asia/Tokyo`）を定期実行として設定。
7. **検証**: デフォルト値のままで `pytest scripts/tests/` + `npm run build` で
   現行動作不変を確認。特に `scripts/tests/equivalence_golden/` のハッシュ値テストで
   生成結果の等価性を確認（`build_golden.py` 経由）。
8. **`.env.example` 不要**（公開値は `.env.public` に直接トラッキング）。

## Verification

- 調査・判断は記録済み（本ファイル）。
- 実装（env 追加: 1,2,3,4,5,7,8,11）は **完了**（2026-10-23、実行は本タスク）。
  - 対象ファイル: `scripts/article/config.py`（HF_SPACE_ID / BASE_QUALITY_PROMPT /
    NEGATIVE_PROMPT / IMAGE_FALLBACK_URL_TEMPLATE の env 化 + `__all__` 追加）、
    `scripts/article/image.py`（L121 URL / L225 negative prompt → 定数参照）、
    `hf-space/app.py`（`import os` + MODEL_REPO_ID / MODEL_FILENAME / _cached_neg_prompt env 化、
    参照 L12/L13 更新）、`scripts/fetch_topics.py`（E621_ALLOWED_RATINGS /
    E621_NSFW_RATINGS + _e621_rating_query ヘルパー + _is_nsfw_post rating 判定 +
    collect_e621 クエリ変換）、`scripts/gsc_index.py`（SITE_URL env 化）。
  - 検証:
    - 構文: `python -m py_compile`（5ファイル）→ OK
    - `python -m pytest scripts/tests/ -v` → **454 passed**（再実行 7.9s）。
      初回 9 fail（`__all__` 未更新 → `from article.config import *` で
      NEGATIVE_PROMPT / IMAGE_FALLBACK_URL_TEMPLATE が取得できず）→ `__all__`
      補正後全件パス。
  - 既定値＝現行値 → env 未設定時は現行動作不変（バイト同一）。
  - e621: 既定 `E621_ALLOWED_RATINGS="s,q"` でクエリは `rating:safe` / `rating:questionable`
    （バイト同一）。`e` 含みで `,explicit` 付加（2026-10-23 実確認済み）。
  - `npm run build`: 未実行（Astro 変更なし・記事生成未実行）。記事生成パイプライン
    実行時に必要に応じて実行。

## 完了時 Memory Bank 操作

- [x] `current-task.tsv` の参照行を削除
- [x] 解決した `known-issues/` ファイルを `known-issues/archive/` へ `mv`（該当なし）
- [x] `backlog.md` の完了項目を削除（該当なし）
