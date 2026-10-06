# Current Task

Agentの現在進行中タスクの参照を記録する。Context Overflow後もこのファイルを読み込んで作業を復帰させる。

完了したタスクは `docs/ai/tasks/` に個別ファイルとして記録される。

---

## Active Task

- `docs/ai/tasks/2026-10-05-known-issues-image-prompt.md` - KI-001, KI-002 修正完了。KI-003 調査完了（根本原因判明）
- `docs/ai/tasks/2026-10-05-hf-api-investigation.md` - HF ZeroGPU 調査、KI-003 根本原因特定

### Verification

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
