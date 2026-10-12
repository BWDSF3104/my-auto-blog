# リファクタリング機能等価性検証 証跡

- 日付: 2026-10-12
- 対象: `generate_article.py`（3561→484 行ファサダ化）+ `fetch_topics.py` リファクタリング
- ベースライン: `69bb5e8` / 現行: `9ac496e82b66f5b3033096e965d7e786763793b8`
- 計画書: `docs/ai/tasks/2026-10-12-refactor-equivalence-verification.md`
- ハーネス: `scripts/tests/equivalence_check.py`（決定論的・再実行可能）

## 結論

**全レイヤー PASS。** L1（決定論的リプレイ A/B）で全 3 プロンプトバリアントの全成果物が機能等価、
L3（実 Gemini 1 回）で実 API 経路の構造健全性を確認。リファクタリングは機能等価。

## 検証レイヤーと結果

| レイヤー | 内容 | 結果 |
|---|---|---|
| L0 | `pytest scripts/tests/ -v`（365 テスト） | **PASS**（`pytest_full.log`） |
| L1 | 決定論的リプレイ A/B: baseline `69bb5e8` vs 現行、全バリアント（default / kemono_story / ai_deep）× 自己整合 2 回 + A/B 1 回 | **PASS**（`l1_report.txt`、`runs/`） |
| L2 | 本番生成 CI（`deploy.yml` 毎日 cron `0 23 * * *` UTC、実測で約 3 時間遅延して ~02:00 UTC 開始）のリファクタ後初回実行 | 2026-10-13 実行予定（`gh run list --workflow=deploy.yml --limit 2` で確認。リファクタ push 10-12 08:51 UTC 後の初回 = 10-13 の run） |
| L3 | 実 Gemini API 1 回（`gemini-3.8-flash`、pass1 実呼び出し / pass2・画像はモック）の構造健全性チェック | **PASS**（`l3_report.txt`、`runs/realrun_default/`） |

## 方法（L1）

- `git archive --format=tar <commit>` で各コミットを pristine 展開し、ゴールデン fixtures
  （`data/equivalence_golden/`、inputs 53 posts / 5 prompts / latest.json 76 topics / rakuten cache 23 件）を
  同一のサンドボックスにデプロイして `generate_article.py` を実行（1 バリアントあたり selftest ×2 + A/B ×2 = 全 12 実行）。
- **時刻固定**: `datetime.now` → `2026-10-12T10:00:00 JST`（FIXED_EPOCH=1791766800）、`time.time` → 単調増加ダミー、`time.sleep` → no-op。
- **AI 呼び出しモック**: ステートフル fake client が呼び出し順で分岐（1 回目=pass1 固定草案 / 2 回目=pass2 固定推敲文）。画像生成もモック（dummy AVIF + プロンプト捕捉）。
- **ネットワーク遮断**: `requests.get/post` → 例外。`subprocess` は capture + 委譲（`fetch_topics` 呼び出しを検出したら硬失敗）。
- **hermetic 環境変数**: dummy API キー、楽天・Amazon アフィリエイトテスト ID、`MAX_INLINE_IMAGES=7`、`MIN_SCORE_THRESHOLD=0`（両ツリー同一）。
- パス正規化: JSON は parse→文字列 deep-normalize→再シリアライズ、テキストは sandbox パス→`<ROOT>` 置換。バイナリはハッシュ比較。
- 判定: **selftest** = 同一ツリー 2 回実行のバイト一致（順序差も失敗扱い）。**A/B** = baseline vs 現行の全成果物一致（`order_only` = 行集合同一・順序のみ異なる装飾差は非失敗）。

## L1 で確認した唯一の差異（装飾・許容）

`stdout.log` の `🎲 記事のbase seed: N` 出力位置のみ baseline（キャラクタ検出後）と現行（検出前）で異なる。
seed 値自体は同一、RNG 消費順序も同一で、成果物（記事・ログ・メタデータ）に一切影響しない表示順序差。

## L3 補足

- 初回実行は Gemini API が `503 UNAVAILABLE`（モデル高需要の一時的サーバー側障害）で失敗。
  リトライロジック（3 試行）が設計通り動作し RuntimeError を伝播。数分後の再実行で成功（API クォータは 1 回分のみ消費）。
- 成功した実行の成果物（`runs/realrun_default/`）に対し構造健全性チェックを再検証（`--l3-recheck`、API 呼び出しなし）。
  記事: フロントマター（title/description/tags/image/prompt_type 等）/ セクション群 / `🤖 生成情報` HTML セクション / ヘッダー画像を全て確認。
- `stdout.log` に `Gemini API (gemini-3.8-flash) リクエスト中... (試行 1/3)` が 1 行のみ（初試行成功・リトライなし）。
- 記事内容は実 Gemini 出力（固定草案とは別テキスト）。アフィリエイトリンクにテスト tracking ID が正しく付与。

## 再実行方法

```powershell
$env:PYTHONIOENCODING='utf-8'
python scripts/tests/equivalence_check.py                  # L1 全バリアント（決定論的・API 不要）
python scripts/tests/equivalence_check.py --selftest       # 自己整合のみ
python scripts/tests/equivalence_check.py --l3 --variants default  # L3 実 Gemini 1 回（クォータ消費）
python scripts/tests/equivalence_check.py --l3-recheck     # L3 成果物の構造チェックのみ（API 不要）
pytest scripts/tests/ -v                                   # L0
```

## ファイル構成

| ファイル | 内容 |
|---|---|
| `l1_report.txt` | L1 マトリックス判定レポート（RESULT: PASS） |
| `l3_report.txt` | L3 再検証レポート（RESULT: PASS） |
| `pytest_full.log` | L0: 365 passed |
| `scope_diff.txt` | `git diff --stat 69bb5e8..9ac496e -- scripts/`（14 files, +3956/−3438） |
| `runs/selftest_{1,2}_<variant>/` | 自己整合 2 回実行の全成果物（article / prompts / logs / metadata / images） |
| `runs/{baseline,current}_<variant>/` | A/B 両ツリーの全成果物 |
| `runs/realrun_default/` | L3 実 Gemini 実行の全成果物 |

各 run ディレクトリ: `article.md` / `prompt_pass1.txt` / `prompt_pass2.txt` / `trend_usage_log.json` /
`draft_metadata.json` / `affiliate_link_log.json` / `slug_redirects.json` / `stdout.log` / `stderr.log` /
`exit_code.txt` / `capture.json` / `images/`
