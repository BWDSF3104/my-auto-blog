# 2026-10-05 モバイルハンバーガーメニュー

## 概要

640px未満のモバイル画面でヘッダー右にハンバーガーボタンを表示し、タップでドロップダウンメニューを展開するナビゲーションを実装。

## 変更ファイル

- `src/components/Header.astro`

## 実装内容

### ハンバーガーボタン
- `sm:hidden` でモバイルのみ表示
- `aria-expanded`, `aria-controls` でアクセシビリティ対応
- 3本線 ↔ バツマークのSVGアイコン切り替え

### モバイルドロップダウンメニュー
- `#mobile-menu` に `hidden sm:hidden overflow-hidden transition-all duration-200`
- 白背景 + `rounded-xl` + `border` + `shadow-lg` のカードデザイン
- メニュー項目:
  - 検索 (`/search`)
  - ダークモード切り替え (ボタン)
  - 記事一覧 (`#main-content` アンカーリンク)
  - タグ一覧 (`/tags`)
  - About (`/about`)
  - RSS (`/rss.xml`)
  - Privacy (`/privacy`)
- 各項目にアイコンSVG + ラベル
- セクション間には `<hr>` 区切り線

### JavaScript
- ハンバーガーボタンのクリックでメニュー展開/閉じる
- `aria-expanded` の状態管理
- 外部クリックでメニューを閉じる
- アイコンの切り替え（3本線 ↔ バツ）

## 検証

- `npm run build`: 成功 (110ページ、2.85s)

## コミット

- `193cfef` feat: モバイルメニューに「記事一覧」リンクを追加
