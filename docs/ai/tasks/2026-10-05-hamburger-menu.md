# モバイルハンバーガーメニュー実装

## 変更

- `src/components/Header.astro`: モバイル用ハンバーガーメニュー追加
  - `sm` (640px) 未満: 検索・ダークモードボタンを非表示、ハンバーガーボタンを表示
  - ドロップダウンメニュー: 検索、ダークモード、タグ一覧、About、RSS、Privacy
  - アイコン切替: ハンバーガー ⇄ クローズ (X)
  - 外部クリックでメニューを閉じる
  - `sm` 以上: 既存のボタンレイアウト維持
  - アクセシビリティ: `aria-expanded`, `aria-controls`, `role="navigation"`

## ビルド

- `npm run build`: 成功 (110ページ、2.96s)