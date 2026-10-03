# Current Task

Agentの現在進行中タスクの参照を記録する。Context Overflow後もこのファイルを読み込んで作業を復帰させる。

完了したタスクは `docs/ai/tasks/` に個別ファイルとして記録される。

---

## Active Task

- なし (pokemon_super_mystery_dungeon_mew_relationship 記事完了)

## Completed Task

- pokemon_super_mystery_dungeon_mew_relationship_verified_vs_theory.md: 記事のフォーマット・画像配置・ビルド検証 **完了**

### 完了内容
- Serebii SMDページからMew・Mewtwo・Larvitar・Lugia・Rayquazaのスプライトをダウンロード
- Pillow(PIL)でPNG→avif変換、`public/images/` に保存
- 記事の画像パス確認 (header.avif + inline-1~4.avif)
- `npm run build`: 104 page(s) built in 3.01s, Completed

## Verification

- `pytest scripts/tests/ -v`: 134 passed in 1.93s
- `npm run build`: 104 page(s) built in 3.01s, Completed

## Changes

- `scripts/generate_article.py`: `_save_trend_usage_log()` 関数を追加。`_append_trending_topics()` 内でフィルタ統計を収集して JSON ログを `data/trend_usage/` に保存。
- `.github/workflows/deploy.yml`: `git add` に `data/trend_usage/` を追加。

## Relevant Files

- `src/content/posts/pokemon_super_mystery_dungeon_mew_relationship_verified_vs_theory.md`: 対象記事
- `public/images/`: avif画像の保存先
- `docs/ai/current-task.md`: 進捗追跡ファイル
