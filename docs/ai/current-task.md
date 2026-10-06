# Current Task

Agentの現在進行中タスクの参照を記録する。Context Overflow後もこのファイルを読み込んで作業を復帰させる。

完了したタスクは `docs/ai/tasks/` に個別ファイルとして記録される。

---

## Active Task

- `docs/ai/tasks/2026-10-06-draft-metadata-tracking.md` - 2-pass生成のメタデータ追跡（`.kilo/drafts/` にJSON保存）
- `docs/ai/tasks/2026-10-05-known-issues-image-prompt.md` - KI-001, KI-002 修正完了。KI-003 調査完了（根本原因判明）
- `docs/ai/tasks/2026-10-05-hf-api-investigation.md` - HF ZeroGPU 調査、KI-003 根本原因特定
- `docs/ai/tasks/2026-10-06-increase-image-count.md` - 画像生成上限を3枚→8枚に増加（ヘッダー含め）、ストーリー系は各章ごとに画像配置

### Verification

- `pytest scripts/tests/ -v`: 161 passed (1.90s) — 2-passメタデータ追跡用テスト6件追加
- `npm run build`: 成功 (114ページ、2.90s)
- docs 更新: current-task.md
- 2-passメタデータ追跡完了: `data/drafts/<timestamp>.json` に下書き・精製後の内容・モデル・時間・差分統計を記録
- 今後の予定: ドラフトファイル・トレンドファイルのクリーンアップ処理

- `pytest scripts/tests/ -v`: 155 passed (1.61s)
- `npm run build`: 成功 (110ページ、3.43s)
- docs 更新: image-prompt-refinement.md (新規), backlog.md (P4超低優先度追加), current-task.md
- `npm run build`: 成功 (110ページ、2.43s)
- docs 更新: known-issues.md (KI-001, KI-002追加), backlog.md (P1追加), plans.md (Active Plans追加), tasks/ 新規作成
- `npm run build`: 成功 (110ページ、2.57s)
- docs 更新: known-issues.md (KI-003 根本原因追記), backlog.md (P1 完了/新P1追加), api-rate-limits.md (HF ZeroGPU + Pollinations 追加)

P2バックログ完了: ロゴ画像置換 (`docs/ai/tasks/2026-10-05-logo-favicon.md`)
P2バックログ完了: ブランドカラー統一 (`docs/ai/tasks/2026-10-05-brand-colors.md`)
P2バックログ完了: モバイルハンバーガーメニュー (`docs/ai/tasks/2026-10-05-hamburger-menu.md`)
P2バックログ完了: ヒーローセクション (`docs/ai/tasks/2026-10-05-hero-section.md`)
P2バックログ完了: カテゴリーカード (`docs/ai/tasks/2026-10-04-category-cards.md`)
P1バックログ完了: TOCレスポンシブ対応 + Plausible有効化
P1バックログ完了: HF API 使用可能状況確認 (`docs/ai/tasks/2026-10-05-hf-api-investigation.md`)
- `docs/ai/tasks/2026-10-05-long-prompt-v2.md` - KI-003 長プロンプト対応v2（自前chunking実装成功、BASE_QUALITY_PROMPT短縮11→8タグ、ネガティブ20→15タグ完了）
- `docs/ai/image-prompt-refinement.md` - 画像生成プロンプト精査（Nova-Furry-XL用ポジティブ8タグ、ネガティブ15タグに削減、29→23タグ/-21%）
- `docs/ai/image-prompt-nonfixed-refinement.md` - 非固定部分（art_style/character/situation）精査 + Python側ランダム化設計（6項目の重み付き選択）
- Kemono API 削除 + エンタメトレンドソース追加（GameSpot/IGN/Anime News Network/Crunchyroll）+ e621 ストーリー注入除外 + Reddit/Bluesky コメントアウト（2026-10-06）
- e621 キャラクター特徴: 累積型→最新分みの修正 + 両スクリプトにログ出力追加（2026-10-06）
- e621 プロンプト注入 redesign: 投稿別ランダム選出（版権重複再抽選）+ physicalフィルタ（ポーズ/背景/表情/メタ/性別/体型/小道具/映像音響除外）+ アフィリエイト版権フィルタ（神話/放送局/食品/ミーム/プラットフォーム/音楽/ライセンス/政府/イベント/成人向け除外）+ 取得期間14日に短縮（2026-10-06）
- 画像プロンプト指示をDanbooruキーワード形式に統一: Danbooru互換全体指示新規追加、art_style指示に3-5タグ明記、character指示に服装1-2つ+5-8タグ制限、IMAGE_PROMPT例を自然言語→キーワード形式、DEFAULT_ART_STYLEを5→3トークン短縮（2026-10-06）
- e621 artistタグ集計機能: CHARACTER_FEATURE_CATEGORIESにartist追加、unknown_artist除外、generate_article.pyに人気artist注入、art_style指示にartist名候補追加（2026-10-06）
- 画像プロンプト順序最適化: BASE_QUALITY_PROMPTを8→6タグ短縮、Illustrious系推奨順序に再配置（被写体数→キャラクター→シチュエーション→artist→品質→スタイル）（2026-10-06）
- 画像生成seed制御: 記事ごとにbase seedを乱数生成、ヘッダーはbase seed、本文挿絵は+1,+2...を付与して記事内の画像スタイルを一貫させる、HF Space app.pyにもseedパラメータ追加（2026-10-06）
