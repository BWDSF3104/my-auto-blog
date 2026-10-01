# Current Task

Agentの現在進行中タスクの状態を記録する。Context Overflow後もこのファイルを読み込んで作業を復帰させる。

## Task

画像生成のフォールバック機制：HuggingFace → Pollinations.ai 連携とユニットテスト追加

## Priority

P1

## Status

完了

## Objective

HuggingFace 画像生成のフォールバックとして Pollinations.ai を統合し、`IMAGE_PROVIDER` 環境変数でプロバイダーを切り替えられるようにする。AVIF変換を `_save_as_avif` ヘルパーに分離し、テストスクリプトが外部APIを呼ばないことを確認してユニットテストを追加する。

## Modified Files

- `scripts/generate_article.py` — `_save_as_avif`, `_generate_image_pollinations`, `generate_and_save_image` を追加、フォールバックとプロバイダールーティングを実装
- `scripts/requirements.txt` — `requests>=2.31.0` を追加
- `scripts/tests/test_generate_article.py` — 11件のユニットテストを追加（AVIF変換3、Pollinations3、ルーティング5）
- `docs/ai/decisions.md` — Pollinations.ai フォールバックの判断理由を記録
- `docs/ai/architecture.md` — サービス表とデータフローを更新

## Completed

- [x] HF → Pollinations フォールバックと `IMAGE_PROVIDER` ルーティングを実装
- [x] AVIF変換を `_save_as_avif()` ヘルパーにリファクタリング
- [x] `_generate_image_pollinations()` を追加
- [x] テストスクリプトが外部APIを呼ばないことを確認
- [x] 11件のユニットテストを追加
- [x] `pytest scripts/tests/ -v` 成功確認（96/96, 1.39s）
- [x] `npm run build` 成功確認（83 pages, 1.77s）

## Pending

(なし)

## Verification

- `pytest scripts/tests/ -v`: 96/96 passed, 1.39s
- `npm run build`: 成功（83 pages, 1.77s）

## Next Action

(なし)

## Commit

ed2ebe0 (feat: add Pollinations.ai fallback image generation with unit tests)

## Notes

- `IMAGE_PROVIDER=hf`（デフォルト）: HuggingFace → Pollinations フォールバック
- `IMAGE_PROVIDER=pollinations`: HuggingFaceをスキップして直接 Pollinations
- テストは `os.chdir(tmp_path)` で作業ディレクトリを切り替える方式
- `monkeypatch.setattr` で `IMAGE_PROVIDER` モジュール変数を上書き
