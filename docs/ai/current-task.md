# Current Task

Agentの現在進行中タスクの参照を記録する。Context Overflow後もこのファイルを読み込んで作業を復帰させる。

完了したタスクは `docs/ai/tasks/` に個別ファイルとして記録される。

---

## Active Task

- issue-inventory ドキュメント整理 (A-1〜A-9): 完了 (commit 51ac76c)
- C-1 (Reddit API): ユーザー指示待ち
- Trend usage logging: 完了 (未commit)

## Verification

- `pytest scripts/tests/ -v`: 134 passed in 1.93s
- `npm run build`: 97 page(s) built in 2.47s, Completed

## Changes

- `scripts/generate_article.py`: `_save_trend_usage_log()` 関数を追加。`_append_trending_topics()` 内でフィルタ統計を収集して JSON ログを `data/trend_usage/` に保存。
- `.github/workflows/deploy.yml`: `git add` に `data/trend_usage/` を追加。
