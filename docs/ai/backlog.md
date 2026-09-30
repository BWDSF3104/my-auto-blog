# Backlog

未実装項目と改善案。優先度でソート。完了した項目は削除する（変更履歴は git commit に委ねる）。

## P0

| 項目 | 内容 | 工数 |
|------|------|------|
| Reddit 代替ソースの追加 | Reddit API がブロックされているため、HackerNews RSS、TechCrunch RSS、または Twitter/X trending を追加してトレンドデータの多様性を確保 | 中 |

## P1

| 項目 | 内容 | 工数 |
|------|------|------|
| canonical URL一貫性 | slug変更時の301リダイレクト、sitemapとの整合性確認 | - |
| LCP/CLSパフォーマンス | LCP画像の最適化、フォントのpreconnect | - |
| 自動内部リンク | 本文内でも関連記事へのアンカーテキストリンクを自動挿入 | - |
| 既存記事のdescription修正 | 80文字未満のdescriptionを持つ既存記事を修正。独立スクリプト（`scripts/fix_descriptions.py`）として単体実行前提。生成パイプラインには組み込まない | 小 |

## P2

| 項目 | 内容 |
|------|------|
| FAQPage schema | Q&A形式の記事にFAQPage JSON-LDを自動追加 |
| Speakable schema | 記事の冒頭部分をGoogle Assistantが読み上げ可能に |
