# コマンド承認はグローバル permission.bash（フォールバック→allow→例外ask）＋ 行動ルールは AGENTS.md

**Date**: 2026-10-13

**Decision**: kilo のコマンド承認はグローバル `kilo.jsonc` の `permission.bash` に集約し、「先頭 `"*": "ask"` フォールバック → 中段 allow 群 → 後段 例外 ask」（`last match wins`）で運用（98 エントリ）。行動ルール（一行コマンド / インライン Python 禁止）は `AGENTS.md` の `## Command Execution Rules` に置く。

**Reason**: 承認ゲート（設定ファイル）と行動指針（プロンプト）は別レイヤ。`last match wins` によりフォールバック ask を先頭・例外 ask を後段に配置。旧 365 エントリの単発ジャンクを削除して保守性回復。
