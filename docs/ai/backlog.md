# Backlog

未実装項目と改善案。優先度（P2 高 → P5 実験的）で分類。
完了した項目は削除し、不採用項目は `backlog-archive.md` へ移す（変更履歴は git commit に委ねる）。
各項目は **難易度・効果・具体的な作業内容・備考** で記述する。

## 推奨実行順序（2026-10-21 見直しの結果）

| 順 | タスク群（内容） | 対象項目 | 難易度 |
|---:|---|---|---|
| 1（進行中） | 改行正規化 第2ステップ（全ファイル LF 化 + mixed 8 件修正） | P3 #8 | ⭐ |
| 2 | Giscus コメント機能（手動 2 件：Discussions 有効化 + env 登録） | P2 #4 | ⭐⭐ |
| 3 | ストーリー系シリーズ機能（Series + Chapter Navigation + Multiple Collections + Zod） | P5 #4, #5, #10, #12 | ⭐⭐ |
| 4 | ストーリー UI 追加（Spoiler 警告 + Callout Boxes） | P5 #6, #2 | ⭐ |

**非実装予定**（詳細は各項目）: P2 #17, P3 #4, #9, #10, #12, #15, P4 #1, P5 #9, #14

---

## P2

### #2 Featured/Pinned 記事
- **難易度 / 効果**: ⭐⭐ / 中
- **作業内容**: frontmatter に `pinned: true` を追加し、記事一覧（index.astro）に先頭へ固定表示
- **備考**: 保留（重要記事未準備）。重要記事が揃ったら再検討。

### #4 コメント機能（Giscus）実装
- **難易度 / 効果**: ⭐⭐ / 中
- **作業内容**: 設計確定済み（2026-10-11。選定理由は `decisions/2026-10-11-giscus-comments.md`）。
  | 内容 | 実施 | ファイル |
  |---|---|---|
  | GitHub 側設定（Discussions 有効化 + giscus app 導入） | **手動（ユーザー）** | `tasks/2026-10-11-giscus-comments-github-setup.md` |
  | 環境変数登録 | **手動（ユーザー）** | `tasks/2026-10-11-giscus-comments-env-config.md` |
  | コンポーネント + Layout 組み込み | AI | `tasks/2026-10-11-giscus-comments-component.md` |
  | deploy.yml / deploy-only.yml への env 配線 | AI | `tasks/2026-10-11-giscus-comments-workflow-env.md` |
  | E2E 検証 + 本番デプロイ | AI | `tasks/2026-10-11-giscus-comments-verification.md` |
- **備考**: 手動 2 件が先に必要。**完了時に本エントリを削除**。

### #17 新プロンプトタイプ「ポケモン」追加
- **難易度 / 効果**: ⭐⭐ / 中（新コンテンツタイプ・データソース多様化）
- **作業内容**: ポケモンプロンプトテンプレート + プロンプトタイプランダム選定 + RSS/e621 ポケモン取得
- **備考**:
  - 2026-10-16 ユーザー判断: #16（ポケモンテーマ）とは**独立**
  - 詳細設計**済み**（保留・**J1〜J5 判断待ち**）
  - ポケモン RSS（4 フィード）・e621 pokemon タグは **fetch_topics.py に既存**（配線のみで可）。ランダム選定は deploy.yml 変更を伴う
  - 初期検討: `tasks/2026-10-16-pokemon-story-backlog-consideration.md` ／ 詳細設計: `tasks/2026-10-16-pokemon-prompt-type-design.md`

---

## P3

### #8 改行コードの `.gitattributes` による正規化（第2ステップ）
- **難易度 / 効果**: ⭐ / 低
- **作業内容**: `* text=auto eol=lf` を導入し、全ファイルを LF 正規化 + mixed 8 件を修正（全ファイルに改行 diff を生むため単独タスク）
- **備考**: CRLF/LF 混在（例: `deploy.yml`、`test_fetch_topics.py`、`PostLayout.astro`）をエンコード監査で発見（`tasks/2026-10-11-utf8-encoding-audit.md`）。
  - 第1ステップ（画像/バイナリ定義のみ）**完了**（`tasks/2026-10-21-gitattributes-binary-only.md`・差分ゼロ・**commit 待ち（現在進行中）**）

### #4 ソーシャルメディア自動投稿
- **難易度 / 効果**: ⭐⭐⭐ / 中
- **作業内容**: X/Twitter API、Bluesky API 連携で自動投稿
- **備考**: 非実装予定。API キー管理 + レート制限の運用コストと効果のバランスが未検討。

### #9 e621 参考キャラクター名のストーリー本文への「寄せる」指示検討
- **難易度 / 効果**: ⭐ / 低
- **作業内容**: e621 キャラ名を本文に挿入する指示を追加
- **備考**: 2026-10-13 調査: e621 キャラ名は本文に未使用（38 件中 0 件、参考データ・生成情報・アフィリエイトのみ）。
  - 名前での寄せは版権 IP リスク（Zootopia/Pokemon 等）のため、現状はデザイン面のみで寄せる設計
  - 直近改修（anthro/physical フィルタ）で改善の可能性 → 様子見・低優先度

### #10 ストーリーのランダム種族を Danbooru/e621 主要種族タグに絞る
- **難易度 / 効果**: ⭐⭐ / 低
- **作業内容**: 主要種族タグをリスト化 → プロンプト推奨リスト or Python 側ランダム注入を検討
- **備考**: 2026-10-13 調査: 種族は Gemini 自由選択（直近 21 記事で 21 種、alligator/raven 等の exotic 混在）。画像モデル（Nova-Furry-XL）は主要種族ほど安定。

### #12 `docs/ai/tmp/` スクラッチの日付管理（タスク別日付サブフォルダ）
- **難易度 / 効果**: ⭐ / 低
- **作業内容**: タスク別日付サブフォルダ（任意）
- **備考**: 2026-10-15: N 日保持は**実装済み**（mtime 基準・既定 7 日・`--tmp-retention-days` 指定可。AGENTS.md / memory-bank-guide.md と挙動一致済み）。残り: 日付サブフォルダのみ。

### #15 直前ジャンルとの被りを防ぐ措置（ストーリー系のみ）
- **難易度 / 効果**: ⭐ / 中（多様性向上・連続同種別ストーリーの防止）
- **作業内容**: 直前ストーリーの `world_setting` を今回の抽選から除外（kemono_story のみ）
- **備考**: 2026-10-16 ユーザー判断: **低優先度（保留・未実装）**。
  - 未定: 取得方法（tags 逆引き vs 新 frontmatter フィールド `world_setting`）、防止手法（硬排除推奨・既存リトライループに `exclude` 追加）
  - 詳細: `tasks/2026-10-16-pokemon-story-backlog-consideration.md`

---

## P4 (超低優先度)

### #1 Flux.1 向け自然言語プロンプト + モデル別切り替え
- **難易度 / 効果**: ⭐⭐ / 低
- **作業内容**: ポリニシェン（Pollinations）は HF フォールバック。Flux.1 向けに自然言語プロンプトへ変換 + モデル別切り替え
- **備考**: 非実装予定。詳細: `docs/ai/image-prompt-refinement.md`

---

## P5 (実験的・追加検討)

### #2 Callout Boxes (Note/Tip/Warning)
- **難易度 / 効果**: ⭐⭐ / 中
- **推奨実行順序: 6**（#6 と 1 タスク「ストーリー UI 追加」）
- **作業内容**（案 A: 推奨）:
  - Markdown 慣用 `> **Note:**` / `> **Tip:**` / `> **Warning:**` + CSS で強調ボックス化（CSS 追加のみで完結）
  - 案 B: `@astrojs/mdx` 導入 + `<Note>` 等のコンポーネント（依存増加）
- **効果**: ストーリー系・アフィリエイト記事の信頼性向上
- **備考**: 案 A の Markdown 慣用は Gemini が自然に生成しやすい。既存パイプライン（Markdown 生成）と整合。

### #4 Series 機能
- **難易度 / 効果**: ⭐⭐ / 中
- **推奨実行順序: 5**（#5, #10, #12 と 1 タスク）
- **作業内容**:
  - frontmatter 新增 `series: string`
  - 新規ページ `src/pages/series/[series].astro`（シリーズ記事一覧）
  - `PostLayout.astro` の header に「シリーズ: [リンク]」表示
- **備考**: ストーリー系のみ対象。**前提: #10（Multiple Collections）で `series` collection を定義**

### #5 Chapter Navigation
- **難易度 / 効果**: ⭐⭐ / 中
- **推奨実行順序: 5**（#4, #10, #12 と 1 タスク）
- **作業内容**:
  - frontmatter 新增 `order: number`（または `prevUrl` / `nextUrl`)
  - `PostLayout.astro` の関連記事セクション前に「← 前章 / 次章 →」リンク
- **備考**: #4（Series）とセットが自然。単独でも frontmatter に `prevUrl`/`nextUrl` を指定できれば可能

### #6 Spoiler Warnings
- **難易度 / 効果**: ⭐ / 低
- **推奨実行順序: 6**（#2 と 1 タスク「ストーリー UI 追加」）
- **作業内容**:
  - frontmatter 新增 `spoiler: boolean`（または `spoilerText: string`)
  - true なら header 直後に `<details><summary>⚠️ スパイラー警告</summary>...</details>` 表示
- **備考**: e621 由来ストーリーのネタバレ防止に有用（ユーザーのネタバレ判断支援）

### #9 MDX Support
- **難易度 / 効果**: ⭐⭐ / 高（理論上）
- **非実装予定**
- **作業内容**: `@astrojs/mdx` 導入 → 記事内にインタラクティブコンポーネント（チャート、クイズ等）
- **備考**: 本プロジェクトの記事は Gemini が生成する Markdown のため、MDX のメリットが**ほぼ使えない**（手動記事のみ対象）。依存増加（`@astrojs/mdx`、`mdx`、`react`）+ ビルド速度低下。需要が明確になるまで保留。

### #10 Multiple Collections
- **難易度 / 効果**: ⭐⭐ / 中
- **推奨実行順序: 5**（#4, #5, #12 と 1 タスク「シリーズ機能」）
- **作業内容**:
  - 新規 `src/content/config.ts`（collections + schema: `posts` / `series` 等）
  - 各 layout の `import.meta.glob`（eager load）を `astro.content.load('posts')` 等に置き換え
- **効果**: 型安全化、Series 機能（#4）の前提
- **備考**: #12（Zod Validation）を**内包**する。現状の `import.meta.glob` 方式の interface は静的型のみ（runtime 検証なし）


### #12 Zod Schema Validation
- **難易度 / 効果**: ⭐ / 中
- **推奨実行順序: 5**（#4, #5, #10 と 1 タスク「シリーズ機能」）
- **作業内容**: `src/content/config.ts` に `schema: z.object({...})` を定義 → `astro build` 時に各 post の frontmatter を自動検証（不適合ならエラー表示）
- **備考**: #10（Multiple Collections）の**一部**（schema 定義のみ）。現状 `title` / `pubDate` / `description` の必須性や `tags` の array 型は runtime で検証されていない。

### #14 Reddit API の収集機能
- **難易度 / 効果**: ⭐⭐ / 低
- **非実装予定**
- **作業内容**: `collect_reddit()` を実装済みだが **403 規制中**
- **備考**:
  - 403 解除には Reddit API の OAuth 認証 + App credentials 登録が必要（コスト vs 利益で不成立）
  - 代替: Reddit の public RSS（`/r/<subreddit>/hot.rss`）を `fetch`（非公式）
  - 現状 e621 + RSS で十分 → **未実装のまま。Reddit トレンドが重要になった時のみ再検討**
