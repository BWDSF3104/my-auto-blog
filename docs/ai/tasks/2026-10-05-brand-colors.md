# 2026-10-05 ブランドカラー統一（CSS変数化）

## 概要

`global.css` + `PostLayout.astro` に散在するハードコードされたHEXカラーをCSS変数に集約。
既存カラー値は一切変更せず、変数化のみ。

## 変更ファイル

- `src/styles/global.css`: CSS変数定義追加 + ハードコード→変数置換
- `src/layouts/PostLayout.astro`: ハードコード→変数置換

## 変数定義（26変数）

### UIベース（slateパレット）
- `--color-bg`, `--color-bg-alt`, `--color-border`, `--color-border-hover`
- `--color-text`, `--color-text-muted`, `--color-text-inverse`

### 機能色
- `--color-link` (blue-600), `--color-price` (orange-600)
- `--color-skip-link-bg`, `--color-skip-link-outline`

### アフィリエイト（Amazon 6変数）
- `--color-amazon-btn`, `--color-amazon-bg`, `--color-amazon-border`
- `--color-amazon-text`, `--color-amazon-label-bg`, `--color-amazon-label-text`

### アフィリエイト（Rakuten 6変数）
- `--color-rakuten-btn`, `--color-rakuten-bg`, `--color-rakuten-border`
- `--color-rakuten-text`, `--color-rakuten-label-bg`, `--color-rakuten-label-text`

## 検証

- 変更前ビルド: 45HEXカラー抽出
- 変更後ビルド: 45HEXカラー抽出
- 比較結果: 完全一致（視覚変化ゼロ）
- `npm run build`: 成功 (110ページ、2.72s)

## ダークモード

既存の `:root[class~="dark"]` セレクタは変数定義内に統合。
PostLayout.astro のダークモードセレクタは変数参照に置換済み。
