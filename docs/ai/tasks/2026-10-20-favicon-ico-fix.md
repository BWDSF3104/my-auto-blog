# サイトアイコン修正: favicon.ico をユーザー提供画像へ置換（SVGのみ更新ではブラウザ表示に反映しない）

**Status**: 完了
**Date**: 2026-10-20
**Next Action**: ビルド検証 → push → デプロイ確認

## 意図 / 背景
 
ユーザーが「サイトアイコンを変える（以前実施したが効果なし）」と依頼。2026-10-05 タスク（archive/2026-10-05-logo-favicon.md）で `public/favicon.svg` をユーザー提供ロゴに置換済みだが、ブラウザのタブ表示アイコンは従来通りで変化していない。Google Drive（`I:\マイドライブ\kilo`）にユーザー提供画像を再配置（同一 SHA256 `106E8A30…747DD`）。

## 調査結果 / 変更内容
 
- 部署先（`https://BWDSF3104.github.io/my-auto-blog/`）の HTML に `<link rel="icon" type="image/svg+xml" href=".../favicon.svg">`（先頭）＋ `<link rel="icon" href=".../favicon.ico">` の両方が存在。
- 部署先 `favicon.svg`（15190 bytes）は 2026-10-05 の新ロゴと一致（デプロイ済み）。
- 部署先 `public/favicon.ico`（655 bytes）は **Astro 初期値のまま**（git 履歴で 初期コミット以降変更なし）。
- **原因特定**: 実験ページ（SVG リンク先頭＋ICO リンク）を Chromium（Playwright）で開き、ネットワーク要求を確認。Chromium は SVG より `.ico` を選択（`blue.ico` のみ取得、`red.svg` 未取得）。つまり **`.ico` がタブアイコンとして表示され、SVG のみ更新ではタブ表示には反映されない**。
- 方針: ユーザー提供 JPEG（780x700、白背景・黒シルエット）を長辺 780x780 へ白背景を補い正方形化（ユーザー指定: クロップせず短辺に白背景追加）、16/24/32/48/64/128 の 6 サイズ `favicon.ico` を生成して `public/favicon.ico` を置換。SVG は維持（OG 画像フォールバック・SVG 優先ブラウザ対応）。
- 注意: ブラウザーは favicon を非常に強くキャッシュする（HTTP キャッシュヘッダーにもほぼ無視）。push 後はユーザーに「新規タブ・ハードリフレッシュ(Ctrl+Shift+R)・隐身ウィンドウ」で確認するよう伝える。

## Verification

- ICO 生成: 780x780（長辺に白背景補完、ユーザー指定）から 16/24/32/48/64/128 の 6 サイズ `public/favicon.ico` を生成（36637 bytes、旧 655 bytes からの更新確認）
- `npm run build`: 成功（154ページ、2.44s）
- `dist/favicon.ico` = 36637 bytes、SHA256 `04C5591F…6185`。`dist/index.html` に favicon.svg・favicon.ico リンク両方確認
- 表示検証（Playwright/Chromium）: 実験ページで `.ico` が SVG より選択されることを再現（blue.ico のみ取得）。生成 ICO は白/黒背景で 16/24/32/48/96px 表示し形状確認 OK
- push 後: `gh run list --workflow=deploy-only.yml` の success 確認 + 部署先 favicon.ico のハッシュ差分確認

- [ ] `current-task.tsv` の参照行を削除
- [ ] 解決した `known-issues/` ファイルを `known-issues/archive/` へ `mv`（該当する場合）
- [ ] `backlog.md` の完了項目を削除（該当する場合）
