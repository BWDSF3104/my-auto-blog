# 2026-10-11: コメント機能（Giscus）— GitHub 側セットアップ（手動）

**Status**: 未着手
**担当**: ユーザー（手動）
**依存**: なし
**関連**: `tasks/2026-10-11-giscus-comments-env-config.md`（次工程）, `decisions.md`（2026-10-11 選定理由）

## 概要

Giscus は GitHub Discussions をバックエンドとするクライアントサイドコメントウィジェット。導入のためリポジトリ `BWDSF3104/my-auto-blog` で Discussions 機能を有効化し、giscus app をインストールする。本タスクの成果物（4 つの設定値）が `env-config` タスクの入力になる。

## 手順

1. リポジトリ `BWDSF3104/my-auto-blog` の Settings → General → Features で **Discussions を有効化**（リポジトリは公開であること）
2. Discussions タブでカテゴリ「**Comments**」を作成（種別: **Announcements** → 新規 Discussion の作成が管理者と giscus bot に制限されスパム抑制）
3. https://giscus.app/ の設定ウィザードを実行:
   - Repository: `BWDSF3104/my-auto-blog`
   - Page ↔ Discussions mapping: **pathname**
   - Discussion category: `Comments`
   - Reactions: **on** / Emit metadata: **off** / Input position: **bottom**
   - Language: **Japanese** / Loading: **lazy**
   - ウィザードが giscus app をリポジトリにインストールし、`<script>` タグを生成する
4. 生成された script タグから **`repo_id`（`R_kgDO...` 形式）と `category_id`（`DIC_kwDO...` 形式）を抽出**し、下方の引き継ぎ欄に記録

## 引き継ぎ情報（env-config タスクへ）

| 値 | 内容 |
|----|------|
| `PUBLIC_GISCUS_REPO` | `BWDSF3104/my-auto-blog` |
| `PUBLIC_GISCUS_REPO_ID` | （未確定 — ウィザード生成値をここに記録） |
| `PUBLIC_GISCUS_CATEGORY` | `Comments` |
| `PUBLIC_GISCUS_CATEGORY_ID` | （未確定 — ウィザード生成値をここに記録） |

## Verification

- リポジトリに Discussions タブが表示され「Comments」カテゴリが存在すること
- リポジトリの Installed integrations に giscus が表示されること
- 4 つの設定値が全て確定していること

## Next Action

- `tasks/2026-10-11-giscus-comments-env-config.md` を着手
