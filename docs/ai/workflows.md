# ワークフロー

## Git Workflow

After completing file changes, check if remote has new commits:

1. `git fetch origin` — fetch remote refs without merging
2. `git rev-list HEAD..origin/main --count` — count remote commits not yet pulled

If remote has new commits (count > 0):

1. `git stash` — save local changes temporarily
2. `git pull` — fetch and merge remote changes
3. `git stash pop` — restore saved changes (resolve conflicts if any)
4. `git add`, `git commit`, `git push`

If remote has no new commits (count == 0):

1. `git add`, `git commit`, `git push`

Commit message format: `feat: <日本語説明>` for features, `fix: <日本語説明>` for bug fixes.
Never use `git push --force` or modify remote history.

## Commit Checklist

git push 前に以下の確認を行う:

- [ ] Pythonファイルを変更した場合はテストが全件通過したか (`pytest scripts/tests/ -v`)
- [ ] Astroファイルを変更した場合はビルドが成功したか (`npm run build`)
- [ ] 完了した計画が `plans.md` の「完了した計画」に記録されたか
- [ ] 新規問題が `known-issues.md` に記録されたか
- [ ] 解決した問題が `known-issues.md` の Archive へ移動されたか
- [ ] 完了したバックログ項目が `backlog.md` から削除されたか

## Deploy Verification

git push 後、DeployOnly ワークフローが push トリガーで自動実行されたことを確認:

1. `gh run list --workflow=deploy-only.yml --limit 5` — 直近の実行履歴を確認
2. 最新の push トリガー実行が `success` であることを確認
3. 失敗時は原因を調査して修正を継続

手動実行 (`gh workflow run`) はしない。push 自動トリガーに依存する。

例外（ワークフローが自動実行されないため確認不要）:

- 変更されたファイルがワークフローの paths (`src/**`, `public/**`, `package.json`, `astro.config.mjs`, `tailwind.config.mjs`) に一致しない場合
- コミットメッセージに `[skip ci]` または `[skip deploy]` を含む場合

## 手動記事作成フロー

ユーザーが記事コンテンツを用意し、ローカルでフォーマット・画像配置・ビルド検証を行うワークフロー。

### 前提

- `generate_image` は使用しない（ユーザー指定がない限り）
- 画像取得ソースは記事内容に依存するため、参考例として記載

### ステップ

#### 1. 記事ファイルの作成

`src/content/posts/` にMDファイルを作成。

**Frontmatter設定:**
```yaml
title: "記事タイトル"
slug: "article-slug"
pubDate: "YYYY-MM-DD HH:MM:SS"
description: "記事概要"
author: "AI Storyteller"
prompt_type: "manual"
tags: ["Tag1", "Tag2"]
art_style: "画像生成用のスタイル指定"
少女: "キャラクタープロンプト"
少年: "キャラクタープロンプト"
image: "/my-auto-blog/images/YYYY-MM-DD-HHMMSS-header.avif"
```

#### 2. 記事本文の構成

- セクション構成で記述
- インライン画像プレースホルダー配置:
  `![alt](/my-auto-blog/images/YYYY-MM-DD-HHMMSS-inline-{n}.avif)`
- アフィリエイトリンクセクション追加 (Amazon + 楽天)

#### 3. 画像の取得

**画像ソースの調査:**
- 記事テーマに関連する公式・ファン画像ソースを検索
- 参考ソース例:
  - Serebii: `https://www.serebii.net/{game}/pokemon/{id}.png`
  - Bulbapedia, Pokepedia, 公式ゲームサイト
- 直接ダウンロード可能なURLを探す

**ダウンロード:**
```powershell
Invoke-WebRequest -Uri "<url>" -OutFile "C:\Users\fujim\AppData\Local\Temp\kilo\{name}.png"
```

#### 4. 画像のavif変換

Pillow(PIL)で変換:
```python
from PIL import Image
img = Image.open("source.png")
img.save("dest.avif", "AVIF", quality=85)
```

`public/images/` に `YYYY-MM-DD-HHMMSS-` プレフィックスで保存:
- `header.avif`
- `inline-1.avif` ~ `inline-4.avif`

#### 5. 記事ファイルの画像パス更新

MDファイル内のプレースホルダーを実際のパスに更新。

#### 6. ビルド検証

```bash
npm run build
```

ビルド成功を確認。

#### 7. コミット・プッシュ

```bash
git add <files>
git commit -m "feat: 記事タイトル"
git push
```

### 注意事項

- 画像ソースは記事ごとに調査が必要
- `generate_image` はデフォルトで使用しない
- 画像形式は必ずavif
- 命名規則: `YYYY-MM-DD-HHMMSS-{type}.avif`
