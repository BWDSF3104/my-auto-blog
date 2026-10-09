# Clef-flash ジャンルスコアリング（backlog #4）

- **Status**: 未着手（計画完了 2026-10-09）
- **関連 Plan**: `plans.md` Active Plans [2026-10-09]
- **関連 Backlog**: `backlog.md` P2 #4

## 目的

トレンド文字列を Cloudflare Workers AI の判断特化モデル `@cf/cloudflare/clef-flash` へ渡し、複数ジャンルへの関連度を 0-100 の整数スコアで取得する。ジャンル選択における「高速な判断（分類・スコアリング・真偽判定）」の高速判断層として後続タスクで活用する。

## スコープ

- 対象: 独立 CLI、モック単体テスト、手動ワークフロー、レート制限記録
- **スコープ外**: `generate_article.py` のジャンル選択（`PROMPT_TYPE` 判定）への組み込み（別タスク）

## 調査結果

### Cloudflare API（公式ドキュメント 2026-10-09 確認）

- エンドポイント: `POST https://api.cloudflare.com/client/v4/accounts/{ACCOUNT_ID}/ai/run/@cf/cloudflare/clef-flash`
- 認証: `Authorization: Bearer {API_TOKEN}`
- リクエスト: `{model: "clef-flash", state: <文字列>, questions: {<id>: {type: "score", instructions, criteria}}}`
  - 質問 1〜64 個。id は英数字・`_`・`.`・`-`（最大100文字）
  - score 型: `criteria` は低評価→高評価順の配列
- レスポンス（REST envelope）:
  ```json
  {
    "result": {
      "model": "clef-flash",
      "answers": {
        "sf": {"type": "score", "score": 2.7, "legend": {"0": "...", "4": "..."}, "probabilities": {"0": 0.1, "4": 0.6}, "confidence": 0.8}
      },
      "usage": {"input_tokens": 120, "output_tokens": 10}
    },
    "success": true, "errors": [], "messages": []
  }
  ```
  - **`score` は浮動小数**（probability-weighted level、段階間に割り込む値になりうる）。5段階なら範囲 0〜4
  - `probabilities`: 段階インデックス（文字列）→ 確率、和=1
  - 各質問は独立採点（正規化しない）
- 料金: clef-flash = **8182 neurons / M input tokens**。無料枠 **10,000 neurons/日**（00:00 UTC リセット）。超過時はエラーで操作失敗 → **恒久エラーとして再試行しない**
- 見積: 1リクエスト（4ジャンル・短テキスト）≈ 数百 input tokens ≈ 約2〜3 neurons → 無料枠内で1日数千回可能（概算）

### リポジトリ

- Python 3.11、`scripts/requirements.txt` に `requests` が既存 → 再利用
- 既存スクリプト共通パターン: 呼び出し時に env 取得、argparse、win32 で `sys.stdout.reconfigure(encoding="utf-8")`（`fetch_topics.py` 等）
- テストスタイル: unittest 風クラス + `patch("requests.post")` / `patch.dict(os.environ, ...)` / `pytest.raises`（`test_generate_article.py` 参照）。実 API 呼び出し禁止（RSS 除く）、`test_real_apis.py` は `conftest.py` で集計除外
- ワークフロー: `deploy.yml`（cron+手動）/ `deploy-only.yml` のみ。新ワークフローは自動トリガーなし・コミットしないため既存に影響なし
- 現在のジャンル選択: `PROMPT_TYPE` env（deploy.yml で `kemono_story` 固定）。プロンプト種別: `default` / `ai_deep` / `kemono_story`

## タスク切り分け

### T1. モジュール `scripts/genre_score.py`

- [ ] ジャンル定義: `GENRE_INSTRUCTIONS`（sf/fantasy/cyberpunk/action、日本語 instructions）+ `DEFAULT_GENRES` + `SCORE_CRITERIA`（5段階: ほぼ該当しない / 弱い関連要素がある / 関連要素があるが主要ではない / 主要ジャンルの一つ / 中心的・代表的なジャンル）+ `MAX_QUESTIONS = 64`
- [ ] `build_questions(genres)`: score 型質問 dict を生成。64 超はエラー。未知 id は汎用 instruction テンプレートにフォールバック
- [ ] `validate_raw_score(raw, max_level=4)`: 数値かつ 0≤raw≤4 を検証 → `int(round(raw / 4 * 100))`。**欠落・非数値・範囲外は例外を送出（0点でごまかさない）**
- [ ] `parse_response(payload, genres)`: `success` を検証し `result.answers.<id>.score` を取得。`probabilities`・`usage` は内部で保持（デバッグ用）
- [ ] `call_api(text, genres, account_id, api_token, timeout=60, max_attempts=3)`: `requests.post`。**5xx・タイムアウト → 指数退避で最大3回まで再試行。4xx（401/403/429=無料枠超過含む）→ 再試行せず明確なエラー**。トークンはログ・出力に含めない
- [ ] `score_text(...)`: 結果 dict `{input, model: "@cf/cloudflare/clef-flash", scores}` を組み立て（`--debug` 時に probabilities/usage 追加）
- [ ] CLI: `python scripts/genre_score.py --text "攻殻機動隊" [--genres sf,fantasy] [--output PATH] [--debug]`
- [ ] env: `CLOUDFLARE_ACCOUNT_ID` / `CLOUDFLARE_API_TOKEN`（呼び出し時に取得。未設定 → 明確なエラーで exit 1）
- [ ] JSON 出力は `ensure_ascii=False`、win32 stdout reconfigure 付き（日本語文字化け防止）
- 受け入れ条件: テストから import 可能、`--help` 動作確認

### T2. 単体テスト `scripts/tests/test_genre_score.py`（全モック、API 未消費）

- [ ] questions 生成（4ジャンルの score 型・criteria 順序・64超でエラー・未知idフォールバック）
- [ ] スコア変換（0→0, 1→25, 2→50, 3→75, 4→100、小数 2.7→68、範囲外/非数値/欠落→エラー）
- [ ] レスポンス解析（複数ジャンルの独立採点、answers 欠落→エラー、`success: false`→エラー）
- [ ] HTTP（429/403 → 1回で即エラー、500 → 再試行後に成功、タイムアウト → 再試行。呼び出し回数を assert）
- [ ] CLI（日本語文字列入出力、`ensure_ascii=False` 検証、出力にトークンが含まれない）
- 受け入れ条件: `pytest scripts/tests/test_genre_score.py -v` 全通過、実 API 呼び出しゼロ

### T3. ワークフロー `.github/workflows/genre-score.yml`

- [ ] `workflow_dispatch` のみ（自動トリガー禁止）
- [ ] inputs: `text`（必須、既定「攻殻機動隊」）/ `genres`（任意、既定 sf,fantasy,cyberpunk,action）
- [ ] 入力文字列は env（`GENRE_SCORE_TEXT` / `GENRE_SCORE_GENRES`）経由で渡し、シェルコードとして展開しない
- [ ] secrets: `CLOUDFLARE_ACCOUNT_ID` / `CLOUDFLARE_API_TOKEN`（ログ・成果物に出さない）
- [ ] `permissions: {}`（書き込み権限不要）
- [ ] Python 3.11 + `pip install -r scripts/requirements.txt`、CLI 実行、結果 JSON を artifact 保存（`if-no-files-found: ignore` + `if: always()`）
- 受け入れ条件: `yaml.safe_load` で検証通过

### T4. 記録更新（コミット前）

- [ ] `docs/ai/api-rate-limits.md` に Cloudflare Workers AI（無料枠 10,000 neurons/日、clef-flash=8182 neurons/M input tokens）を追加
- [ ] 本タスクファイルの Status・Verification 更新
- [ ] `plans.md` を Active → Completed Plans へ移動
- [ ] `backlog.md` P2 #4 を削除
- [ ] `current-task.md` の参照行を完了扱いへ更新
- 受け入れ条件: Memory Bank 一貫性確認

## 検証（コミット前）

1. `pytest scripts/tests/ -v`（既存 200 件 + 新規 全通過）
2. CLI スモーク: credentials 未設定時のエラーメッセージ確認（クラッシュしない）
3. `python -c "import yaml; yaml.safe_load(open('.github/workflows/genre-score.yml', encoding='utf-8'))"`

## 完了報告項目（日本語）

1. 変更・追加したファイル
2. 実装した機能
3. テスト結果
4. GitHub Secrets 登録状況の確認方法（GitHub → Settings → Secrets and variables → Actions）
5. GitHub Actions 手動実行手順（Actions タブ → "Genre Score (Clef-flash)" → Run workflow → 文字列入力）
6. 実 API 疎通確認が未実施である旨と残作業（Secrets 登録後のユーザー操作）

## ユーザー実施事項（代理人不可）

- [x] Cloudflare dash（Workers AI → Use REST API）で API トークン + Account ID を作成（2026-10-09 ユーザー提供）
- [x] ローカル `.env` に `CLOUDFLARE_ACCOUNT_ID` / `CLOUDFLARE_API_TOKEN` 追加（2026-10-09、`.gitignore` 対象・未追跡を確認済み）
- [x] GitHub リポジトリの Secrets に `CLOUDFLARE_ACCOUNT_ID` / `CLOUDFLARE_API_TOKEN` 登録（2026-10-09、`gh secret set` で実施、`gh secret list` で確認済み）
- [ ] ワークフロー手動実行による実 API 疎通確認（T3 実装後）

## 制約・注意事項

- Cloudflare の API 仕様を推測で実装しない（公式ドキュメント: clef-flash / rest-api / pricing）
- 出力例の数値は仮例であり、テストで固定スコアを期待しない
- Git commit・push は指示がない限り実行しない
- 権限・認証情報を推測して完了扱いにしない（疎通未確認は明示）
