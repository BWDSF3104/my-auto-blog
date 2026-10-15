# 本日（2026-10-15）変更分のまとめてテスト（実ワークフロー・可能なもののみ）

**Status**: 進行中
**Date**: 2026-10-15

## 意図・背景

本日コミット済みの 14 件（`no human` ポジティブ固定部追加の `a67a3c0` を含む）を、実ワークフロー（CI `deploy.yml` のパイプライン: fetch → score → generate → build）に沿ってまとめて検証する。デプロイ（push → GitHub Pages）は依頼外のため除外。

### 本日の変更一覧

| commit | 内容 | 種別 |
|---|---|---|
| `1b292e4` | kemono_story クローン系画像プロンプトルールの条件注入 | Python |
| `423115b` | plans/ ディレクトリ廃止 | docs/ルール |
| `7efa100` | 生成情報セクションにインスピレーション元リンク追加（trends.py / geninfo.py / PostLayout CSS） | Python + Astro |
| `75aa879` | AGENTS.md 日本語統一 | docs |
| `15a0d8a` | tmp/ クリーンの N 日保持（maintenance） | Python（開発ツール） |
| `ba1aa19` | scratch 置き場を docs/ai/tmp/ へ転用 | docs/ルール |
| `0f00705` | アフィリエイトCTAカードスリム化 + テキストリンク統一 | Python + Astro |
| `3acc2af` / `16d418b` | CI 自動生成記事 + クリーンアップ | CI 生成物 |
| `f72442b` | merge 構造ドリフト修正（by_category を all から再構築） | Python |
| `3518a1b` | docs/ai stale 記述整理 | docs |
| `22ba34a` | ネガティブプロンプトに human 追加（HF Space 反映） | Python + HF Space |
| `780e723` | Python 3.15.0 導入調査記録（保留） | docs |
| `a67a3c0` | `BASE_QUALITY_PROMPT` に `no human` 追加（config.py:65）+ ドキュメント同期 + テスト計画（本ファイル） | Python + docs |

## E2E 手順との逸脱（理由）

`docs/ai/workflow-test-procedure.md` が規定する E2E は `gh workflow run`（GitHub Actions 上での実行）＋ cron 監視 ＋ `test-results/` 記録。本計画は以下の理由でローカル再現方式（T4/T6 実実行）を採用する。

- **ライブ記事デプロイ副作用**: `deploy.yml` の実ランは本番サイトへライブ記事を commit/push する。本テストは「検証のみ」でデプロイを伴わない（T10 除外）
- **テスト範囲**: 検証対象はパイプライン各段階（fetch → score → generate → build）の正しさであり、deploy 段階は依頼外。`gh workflow run` 方式はデプロイ時検証を目的としており本タスクと意図が異なる

## テスト計画（実ワークフロー順）

| # | ステップ | ワークフロー段階 | 対象変更 | 方法 | 実行可否 |
|---|---|---|---|---|---|
| T1 | 単体テスト（main） | ユニット（外部APIは mock） | `1b292e4` `7efa100` `f72442b` `0f00705` `a67a3c0` | `pytest scripts/tests/ -v` | ✅ |
| T2 | 単体テスト（maintenance） | ユニット（mock） | `15a0d8a` | `pytest maintenance/tests/ -v` | ✅ |
| T3 | Astro ビルド（前） | build-and-deploy | `0f00705` `7efa100`（PostLayout） | `npm run build` | ✅ |
| T4 | fetch_topics 実実行 | 1-A Fetch trending topics | `f72442b` | `python scripts/fetch_topics.py --prompt-type kemono_story`＋`docs/ai/tmp/` スクラッチスクリプトで出力構造検証（by_category が all から再構築。インライン Python 禁止） | ✅（APIキー不要） |
| T5 | データソース応答確認 | 1-A Fetch（ソース別） | `f72442b` | `python scripts/tests/test_real_apis.py --save`（結果は `scripts/data/api_test_results/`） | ✅（公開エンドポイント） |
| T6 | generate_article 実実行 | 1-C Run generation | `1b292e4` `7efa100` `0f00705` `22ba34a` `a67a3c0` | `PROMPT_TYPE=kemono_story python scripts/generate_article.py`（.env の Gemini / HF_TOKEN / Rakuten 使用。長時間のため `background_process`） | ✅ |
| T7 | Astro ビルド（後）＋ HTML 検証 | build-and-deploy | `7efa100` `0f00705` | `npm run build` 後に生成記事の dist HTML を解析（`.gen-info-link` / 元投稿リンク / product-card 行 / 旧 CTA box 不在）＋**レイアウト変更（`7efa100`）のためスクリーンショットをユーザーへ送信**（AGENTS.md 必須） | ✅ |
| T8 | プロンプトログ検証 | 1-C（トレース性） | `a67a3c0` / `22ba34a` / `1b292e4` | `data/prompt_logs/` でポジティブ `no human`・ネガティブ `human`・clone/dark_persona ルール注入を確認 | ✅ |
| T9 | 生成画像の視覚検証（`no human` 効果） | 次記事生成時の後続検証 | `a67a3c0` | `analyze_image_with_groq` | ⚠️ 画像のクラウド送信のためユーザー確認必須 |
| T10 | デプロイ（push → GitHub Pages） | deploy | 全体 | `git push` | ❌ 依頼外（実施せず） |

### テスト対象外（理由）

- `423115b` `75aa879` `ba1aa19` `3518a1b` `780e723`: docs/ルール変更のみ（コード検証不要。AGENTS.md 例外規定）
- `22ba34a` の `scripts/hf-space/app.py` 部分: HF Space 側デプロイ対象でローカル検証不可（T6 の実生成で API 経路の動作確認はされる）
- `16d418b` `3acc2af`: CI 生成物・クリーアップ
- genre_score（Clef-flash）: 本日変更なし

## 注意事項

- **レート制限**（`docs/ai/api-rate-limits.md`）: e621 2 req/s・GitHub Search 10/窓（未認証）・HF ZeroGPU 3.5 分/日・Rakuten 1 req/s・Cloudflare clef-flash 10,000 neurons/日
- **API クォータ**: T6 は Gemini / HF_TOKEN / Rakuten の実クォータを消費する（.env 読込）
- **T6 実実行の副作用**: 本日 CI 生成済み 102240 記事に加え同日 2 記事目を生成する（`generate_article.py` に同日重複ガードなし・slug 競合調整のみ）。コミット・push はしない
- **外部サービス依存**: T4/T5/T6 は外部 API に依存。失敗時は `api-rate-limits.md` を参照
- **T9**: 画像はクラウド（Groq API）へ送られるため、送信前に必ずユーザー確認

## Verification

（実行後に記録）

## 完了時 Memory Bank 操作

- [ ] `current-task.tsv` の参照行を削除
- [ ] 本ファイルの Status を「完了」に更新
