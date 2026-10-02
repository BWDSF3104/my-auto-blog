# Current Task

Agentの現在進行中タスクの状態を記録する。Context Overflow後もこのファイルを読み込んで作業を復帰させる。

---

## Task (調査中 - 中断)

Reddit 代替ソースの追加 (P0)

## Priority

P0

## Status

調査中 - 中断

## Objective

Reddit API がブロックされているため、代替のトレンドデータソースを追加してトレンドデータの多様性を確保する。

## Investigation Results

### 現在のデータ収集状況 (2026-10-01_202015.json)

- 総トピック数: 14件
- 動作中のソース: e621, GitHub のみ
- 停止中のソース: Reddit, HackerNews, RSS, Bluesky
- カテゴリ別: kemono 7件, pokemon 7件, tech 0件

### Reddit ブロッキングの詳細

- `www.reddit.com/r/{sub}/hot.json` → HTTP 403
- `old.reddit.com/r/{sub}/hot.json` → HTTP 404
- User-Agent ヘッダの変更では回避不可
- 影響カテゴリ: kemono (r/kemono, r/furry, r/furry_irl), pokemon (r/pokemon), tech (r/localllama, r/MachineLearning)

### 代替ソースの候補

1. **HackerNews RSS**: 既に Firebase API で実装済みだが現在は動作停止中。RSS フィード (`https://hnrss.org/frontpage`) に切り替え可能
2. **TechCrunch RSS**: `https://techcrunch.com/feed/` - tech カテゴリに適合
3. **Lobsters RSS**: `https://lobste.rs/rss` - tech カテゴリに適合
4. **kemono/pokemon RSS**: 専用 RSS フィードの探索が必要

### 計画

1. `fetch_topics.py` に新しい RSS フィードを追加
2. HackerNews Firebase API が停止している場合、RSS にフォールバック
3. kemono/pokemon カテゴリの代替ソースを探索

## Next Action

代替 RSS フィードの可用性を確認し、`fetch_topics.py` に追加する

なし (調査段階)

---

## Task (完了)

Memory Bank archive files の作成

## Priority

P1

## Status

完了

## Objective

`docs/ai/` の Memory Bank ファイルが膨張したため、完了したエントリを `-archive.md` ファイルへ分離してファイルサイズを削減。

## Steps

1. [x] AGENTS.md のドキュメントルールを更新（全タスク対象、アーカイブファイルの構造と閾値を定義）
2. [x] `known-issues-archive.md` 作成（解決済問題を移動）
3. [x] `known-issues.md` クリーンアップ（3件のアクティブ問題のみ保持）
4. [x] `plans-archive.md` 作成（古い完了計画を移動）
5. [x] `plans.md` クリーンアップ（直近5件の完了計画のみ保持）
6. [x] `decisions-archive.md` 作成（古い決定を移動）
7. [x] `decisions.md` クリーンアップ（直近15件の決定のみ保持）
8. [x] `current-task-archive.md` 作成（古い完了タスクを移動）
9. [x] `current-task.md` クリーンアップ（アクティブタスク + 直近1件の完了タスクのみ保持）
10. [x] pytest 全件通過確認 (134件)
11. [x] npm run build 成功確認 (92ページ)
12. [x] git commit & push

## Verification

- pytest scripts/tests/ -v: 134 passed in 2.09s
- npm run build: 92 page(s) built in 3.83s, Complete!

## Commit

37538c4 — chore: create archive files for Memory Bank documentation

## Next Action

なし
