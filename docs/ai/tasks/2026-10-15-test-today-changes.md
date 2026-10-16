# 本日（2026-10-15）変更分の E2E テスト（実ワークフロー実行）

**Status**: 完了
**Date**: 2026-10-15

## 意図・背景

本日コミット済みの 15 件（`no human` ポジティブ固定部追加の `a67a3c0` を含む）を、`docs/ai/workflow-test-procedure.md` 準拠で**実ワークフロー E2E**（`gh workflow run "Auto Generate Content and Deploy to GitHub Pages"`）により検証する。fetch → score → generate → build → deploy の全工程を実際に実行し、本番 GitHub Pages へライブ記事を生成・デプロイする（E2E の本来の目的・本テストの意図）。

## 本日の変更一覧

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
| `a67a3c0` | `BASE_QUALITY_PROMPT` に `no human` 追加（config.py:65）+ ドキュメント同期 | Python + docs |
| `2f14d70` | 本テスト計画の a67a3c0 正式反映 | docs |

## 前提条件（workflow-test-procedure.md 準拠）

- [x] `gh` CLI インストール済み・ログイン済み
- [x] ローカルが最新（local = origin/main、ahead/behind 0 0）
- [x] 変更がローカルで pytest/build 検証済み
  - `pytest scripts/tests/ -v`: 404 passed（`a67a3c0` の `no human` 変更を含む作業ツリーで実行）
  - `pytest maintenance/tests/ -v`: passed
  - `npm run build`: success
  - `2f14d70` は docs のみで再検証不要（AGENTS.md 例外）

## Step 2: 基準値（直近成功 run）

- **Run ID**: `38665222956`
- **完了日時**: 2026-10-15T01:25:17Z（event: schedule）
- **全体所要時間**: 3 分 35 秒（01:21:42 → 01:25:17）
- **generate job**: 2 分 59 秒（01:21:45 → 01:24:44）
- **build-and-deploy job**: 31 秒（01:24:46 → 01:25:17）

## Step 3〜7: 実行手順

| Step | 内容 | 方法 |
|---|---|---|
| 3 | ワークフロー手動トリガー | **スキップ** — 定刻 run `38833424145`（event=schedule, headSha `2a44c92`）を使用。5 テスト対象コミット全て headSha の祖先（確認済み） |
| 4 | 実行中監視 | `schedule_wakeup`/`cron_create` で約 3 分ごとに `gh run view <RUN_ID> --json status,conclusion,jobs`（完了目安 5〜10 分） |
| 5 | 完了/失敗確認 | 成功: `git stash; git pull --rebase; git stash pop` / 失敗: `gh run view <RUN_ID> --log --job <JOB_ID>` |
| 6 | 検証項目実施 | 下表（pull 後ローカルで実施） |
| 7 | 結果記録 | `test-results/2026-10-15-github-workflow-test.md` |

## 検証項目（Step 6）

| # | 検証項目 | 対象変更 | 確認方法 | 成功基準 |
|---|---|---|---|---|
| V1 | ワークフロー全体成功 | 全体 | `gh run view <RUN_ID> --json status,conclusion` | conclusion=success |
| V2 | ポジティブ `no human` 反映 | `a67a3c0` | `scripts/article/config.py:65` の `BASE_QUALITY_PROMPT` に `no human` 存在＋run headSha の祖先確認（prompt_log には固定部が出力されない） | 存在 |
| V3 | ネガティブ `human` 反映 | `22ba34a` | `scripts/article/image.py:155` の NEGATIVE_PROMPT に `human` 存在＋run headSha の祖先確認 | 存在 |
| V4 | クローン系ルール条件注入 | `1b292e4` | prompt_logs で extra_key=clone/dark_persona の時のみルール注入、none/rival は注入なし | 条件分岐どおり |
| V5 | 元投稿リンク表示 | `7efa100` | `npm run build` 後、生成記事の dist HTML で `.gen-info-link` / 元投稿 URL 確認 | 存在 |
| V6 | CTA スリム化 | `0f00705` | dist HTML で product-card / 新 CTA 存在・旧 CTA box 不在 | 新 CTA のみ |
| V7 | レイアウトスクリーンショット | `7efa100` | 生成記事ページ（本番 URL かローカルビルド）をスクリーンショットしユーザーへ送信（AGENTS.md 必須） | 送信済み |
| V8 | ビルド・デプロイ成功 | 全体 | build-and-deploy job success + Pages deploy 完了 | 成功 |
| V9 | 生成画像 `no human` 視覚検証 | `a67a3c0` | `analyze_image_with_groq`（画像はクラウド送信 → ユーザー確認必須） | 人物が被写体でない |
| V10 | 人気版権/artist「プロンプトに使用」実在性 | `7efa100` | 生成記事の生成情報値と prompt log が完全一致（単一 `e621_info` 構造 `generate_article.py:191` で乖離不可能）。版権: 製品推薦が実使用証拠 / artist: art_style に "by X" 未使用（任意） | 一致＋実使用確認 |

### 検証対象外（理由）

- `423115b` `75aa879` `ba1aa19` `3518a1b` `780e723`: docs/ルール変更のみ（コード検証不要・AGENTS.md 例外）
- `22ba34a` の `scripts/hf-space/app.py` 部分: HF Space 側デプロイ対象（E2E の generate 工程で API 経路の動作確認はされる）
- `16d418b` `3acc2af`: CI 生成物・クリーアップ
- genre_score（Clef-flash）: 本日変更なし（workflow 1-B は continue-on-error）

## 注意事項

- **本番デプロイ副作用**: ワークフロー実行で本番 GitHub Pages へライブ記事が生成・デプロイされる（E2E の目的。同日 CI 生成済み記事に追加される）
- **レート制限**（`docs/ai/api-rate-limits.md`）: e621 2 req/s・GitHub Search 10/窓（未認証）・HF ZeroGPU 3.5 分/日・Rakuten 1 req/s・Cloudflare clef-flash 10,000 neurons/日
- **API クォータ**: generate 工程は Gemini / HF_TOKEN / Rakuten の実クォータを消費（CI secrets）
- **V9**: 画像はクラウド（Groq API）へ送られるため、送信前に必ずユーザー確認
- **Step 5 成功時の pull**: ワークフローは記事・画像・prompt_logs・topics 等をリモートへコミットするため、pull 後にローカル検証

## Verification

| # | 結果 | 根拠 |
|---|---|---|
| V1 | ✅ | 定刻 run `38833424145`（event=schedule）conclusion=success |
| V2 | ✅ | `config.py:65` `BASE_QUALITY_PROMPT` に `no human` 存在。run headSha `2a44c92` の祖先確認済み |
| V3 | ✅ | `image.py:155` NEGATIVE_PROMPT に `human` 存在。run headSha の祖先確認済み |
| V4 | ✅ | prompt log（`2026-10-16-100918.txt`）でクローン系ルール注入確認（extra_key=clone） |
| V5 | ✅ | `dist\posts\zankyou-no-duplica\index.html` で `gen-info-link` 6 件、`e621.net/posts/1624482` 1 件、`e621.net/posts/2925603` 1 件 |
| V6 | ✅ | 同上 dist HTML で `pc-btn-amazon` 11 / `pc-btn-rakuten` 11 / `pc-name` 11 / 🔥 1（先頭強調）。旧 CTA box（gradient）0 件 |
| V7 | ✅ | 本番 URL full-page スクリーンショット `docs\ai\tmp\v7-article-full.png` をユーザーへ添付送信 |
| V8 | ✅ | build-and-deploy job success、GitHub Pages デプロイ完了 |
| V9 | ✅ | ユーザーが本番ウェブで視覚確認済み（人物被写体なし） |
| V10 | ✅ | 生成情報値と prompt log 133–134 行完全一致（単一 `e621_info` 構造）。版権: 製品推薦実使用証拠あり / artist: art_style に "by X" 未使用（任意） |

詳細: `test-results/2026-10-15-github-workflow-test.md`

## 完了時 Memory Bank 操作

- [x] `current-task.tsv` の参照行を削除
- [x] 本ファイルの Status を「完了」に更新
