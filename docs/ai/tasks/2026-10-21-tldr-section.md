# TL;DR ボックス表示実装（記事ページ header 直下・description 源）

**Status**: 完了
**Date**: 2026-10-21
**Backlog**: P5 #1
**Next Action**: PostLayout.astro の header 直下に tldr-box 追加 + CSS → npm run build → HTML 構造検証・スクリーンショット

## 意図 / 背景

バックログ P5 #1（TL;DR セクション）。記事一覧用の概要（frontmatter `description`、全タイプで記事一覧カード / OGP / 検索インデックスに表示済み）があるが、**記事ページ内の要旨表示は未実装**（`PostLayout.astro` の header 直後に本文 `## 第1章…` が直接続く）。本タスクは記事ページ上部に TL;DR ボックスを追加し、記事一覧の「要旨あり」体験と記事ページの「要旨あり」体験を一致させる。

## 調査結果 / 変更内容

### 現状確認（2026-10-21）
- 全記事（auto + manual）に frontmatter `description`（80〜120文字）あり
- 記事一覧（`index.astro:156`）/ OGP / Twitter Card / 検索インデックスに表示済み
- 記事ページ: `header`（タイトル・日付・著者・タグ・アイキャッチ画像）→ 本文直結。**要旨ボックスなし**
- 本文内の概要 H2: テック系（9月末まで生成、既存のみ）に `## 概要と背景`、物語系（kemono_story）はなし。既存技術記事 7 件程度
- 現在の auto 生成は kemono_story 中心（47 篇）

### 設計（決定 2026-10-21・ユーザー承認: 推奨案 A）
- **ボックス源**: `frontmatter.description`（全タイプ共通）
  - 物語系: Python 変更ゼロ（description はあらすじとして既存生成済み）
  - テック系既存記事の `## 概要と背景`（本文 H2）は抽出しない → **二重要旨を回避**（ボックス=description、本文 H2 は保持）
- **配置**: `PostLayout.astro` の `</header>`（現在 281 行）直後、`<article id="article-content">` の前
- **表示**: 「要旨」ラベル付きボックス（視覚的に区別）。既存 `.gen-info` 系ボックスのデザイン言語（`--color-bg-alt` 背景・`--color-border` 枠・角丸）に合わせる
- **Python 変更**: なし
- **変更対象**: `src/layouts/PostLayout.astro` のみ（HTML + `<style is:global>` 内の `.tldr-box` 系 CSS）
- **影響範囲**: 全記事ページ（既存 48 篇 + 将来記事）。OGP / TOC / アフィリエイトブロック等の既存構造に干渉しない

## Verification

- **`npm run build`** (2026-10-21 20:59): 成功 — 157 page(s) built in 8.85s、search index 63 posts 生成
- **`python docs\ai\tmp\verify_tldr.py`**: 4/4 OK
  - テスト対象: `posts/kageboushi-no-orugoru/`（物語系）、`posts/futahiki-no-ginrei-kyouzou-no-yoake/`（物語系）、`posts/2026-09-27-065052-auto-post/`（テック系・`## 概要と背景` H2 あり）、`posts/pokemon-super-mystery-dungeon-mew-relationship/`（manual）
  - 各記事: tldr-box 存在 / 順序 `</header>` < tldr-box < `article-content` / ラベル「要旨」存在 / tldr テキスト == description（89・85・103・80 文字）
- **レイアウト確認スクリーンショット** (astro preview + Playwright、ライト/ダーク両モード、ボックス近接 + 全ページ): `I:\マイドライブ\kilo\2026-10-21-tldr-section\`（tldr_box_light/dark.png, tldr_full_light/dark.png）
- 未変更: frontmatter（description 源）・Python パイプライン・OGP/TOC 等の既存構造

## 完了時 Memory Bank 操作

- [ ] `current-task.tsv` の参照行を削除
- [ ] 解決した `known-issues/` ファイルを `known-issues/archive/` へ `mv`（該当する場合）
- [ ] `backlog.md` の完了項目を削除（該当する場合）
