# latest.json シンボリックリンクのクロスプラットフォーム互換性問題

**Date**: 2026-10-02
**Status**: 解決済

`data/topics/latest.json` が GitHub Actions ラナーの絶対パスへのシンボリックリンクだったため、ローカルWindowsとGitHub Pagesで壊れていた。`os.symlink()` を `shutil.copy2()` に置換して通常ファイルコピーに変更。テスト134件全件通過確認済み。`b569ece`。
