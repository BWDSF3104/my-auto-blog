# Current Task

Agentの現在進行中タスクの参照を記録する。Context Overflow後もこのファイルを読み込んで作業を復帰させる。

完了したタスクは `docs/ai/tasks/` に個別ファイルとして記録される。

---

## Active Task

## Completed Tasks

- レート制限テーブルを docs/ai/api-rate-limits.md に分離 + AGENTS.md に test_real_apis.py 検証ルール追加: `PENDING`
- データソースのレート制限調査: `27fba26`

- 'pokemon' 除外 + ランダムトレンド選択 + e621 character/copyright 拡張: `333aa8a`
- Reddit 代替ソースの追加 (Kemono API + RSS): `cc673c0`
- モバイルで商品名テキスト(.pc-name)の改行を有効化: `4c03fb0`
- モバイルで記事タグとアフィリエイトボタンの幅オーバーフローを修正: `5fbb1b9`
- 静的監査の残り3バグを修正 (relative paths, empty URI, non_consecutive): `2b4a815`
- latest.json のシンボリックリンクをファイルコピーに置換: `b569ece`
- Memory Bank 1タスク1ファイル方式への移行: `7c0c9a8`
- 既存記事のアフィリエイトリンクを一括置換: `a0299ef`
