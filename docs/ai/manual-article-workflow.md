# 手動記事作成フロー

ユーザーが記事コンテンツを用意し、ローカルでフォーマット・画像配置・ビルド検証を行うワークフロー。
（`docs/ai/workflows.md` からコンテキスト節約のため分離）

## 前提

- `generate_image` は使用しない（ユーザー指定がない限り）
- 画像取得ソースは記事内容に依存するため、参考例として記載

## ステップ

### 1. 記事ファイルの作成

`src/content/posts/` にMDファイルを作成。

**Frontmatter設定:**
```yaml
title: "記事タイトル"
slug: "article-slug"
pubDate: "YYYY-MM-DD HH:MM:SS"
description: "記事概要"
author: "AI Storyteller"
prompt_type: "manual"
tags: ["Tag1", "Tag2", "Manual"]
art_style: "画像生成用のスタイル指定"
少女: "キャラクタープロンプト"
少年: "キャラクタープロンプト"
image: "/my-auto-blog/images/YYYY-MM-DD-HHMMSS-header.avif"
```

### 2. 記事本文の構成

- セクション構成で記述
- インライン画像プレースホルダー配置:
  `![alt](/my-auto-blog/images/YYYY-MM-DD-HHMMSS-inline-{n}.avif)`
- アフィリエイトリンクセクション追加 (Amazon + 楽天)

### 3. 画像の取得

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

### 4. 画像のavif変換

Pillow(PIL)で変換:
```python
from PIL import Image
img = Image.open("source.png")
img.save("dest.avif", "AVIF", quality=85)
```

`public/images/` に `YYYY-MM-DD-HHMMSS-` プレフィックスで保存:
- `header.avif`
- `inline-1.avif` ~ `inline-4.avif`

### 5. 記事ファイルの画像パス更新

MDファイル内のプレースホルダーを実際のパスに更新。

### 6. ビルド検証

```bash
npm run build
```

ビルド成功を確認。

### 7. コミット・プッシュ

```bash
git add <files>
git commit -m "feat: 記事タイトル"
git push
```

## 注意事項

- 画像ソースは記事ごとに調査が必要
- `generate_image` はデフォルトで使用しない
- 画像形式は必ずavif
- 命名規則: `YYYY-MM-DD-HHMMSS-{type}.avif`
