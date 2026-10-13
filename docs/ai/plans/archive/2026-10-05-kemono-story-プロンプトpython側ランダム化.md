# kemono_story プロンプトのPython側ランダム化

**Date**: 2026-10-05
**Status**: 完了

6項目の重み付きランダム選択 (`_randomize_kemono_params`) + バリデーション (`_is_valid_kemono_combination`) を実装。`char_count=1` は `extra=clone` 時のみに制限。`char_count_desc` は 2人の場合 "バディ"/"ライバル"/"カップル" からランダム選択。テスト21件追加、全155件通過、ビルド成功 (110ページ)。commit: `2804bfd`
