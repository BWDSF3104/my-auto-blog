"""
既存記事のmarkdown形式アフィリエイトリンクをHTML <a> タグに置換する。

対象パターン:
  - 📦 [Amazonで「...」を探す](url)
  - 🛍️ [楽天市場で「...」を探す](url)

置換後:
  - 📦 <a href="url" target="_blank" rel="noopener noreferrer nofollow sponsored">Amazonで「...」を探す</a>
  - 🛍️ <a href="url" target="_blank" rel="noopener noreferrer nofollow sponsored">楽天市場で「...」を探す</a>

使い方:
  python scripts/fix_affiliate_links.py          # 全ファイル適用
  python scripts/fix_affiliate_links.py --dry-run # 差分を表示のみ
  python scripts/fix_affiliate_links.py --file <path>  # 指定ファイルのみ
"""

import re
import sys
import io
from pathlib import Path

# Windows コンソールのUTF-8出力対応
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

POSTS_DIR = Path(__file__).resolve().parent.parent / "src" / "content" / "posts"

# markdownリンクパターン: [text](url) → <a> タグ
# 行頭の `- 📦 ` または `- 🛍️ ` に続くmarkdownリンクを対象
MD_LINK_PATTERN = re.compile(
    r'^(- [\s\S]*?)\[([^\]]+)\]\(([^)]+)\)$'
)


def convert_line(line: str) -> str:
    """一行内のmarkdownアフィリエイトリンクをHTML <a> タグに置換する。"""
    match = MD_LINK_PATTERN.match(line)
    if not match:
        return line

    prefix = match.group(1)  # e.g. "- 📦 "
    text = match.group(2)    # e.g. 'Amazonで「Kemono」関連作品・アイテムを探す'
    url = match.group(3)     # e.g. 'https://www.amazon.co.jp/s?k=...'

    return f'{prefix}<a href="{url}" target="_blank" rel="noopener noreferrer nofollow sponsored">{text}</a>\n'


def fix_file(filepath: Path, dry_run: bool = False) -> int:
    """ファイル内のmarkdownアフィリエイトリンクをHTMLに置換する。置換数を返す。"""
    content = filepath.read_text(encoding="utf-8")
    lines = content.split("\n")
    new_lines = []
    count = 0

    for line in lines:
        new_line = convert_line(line).rstrip("\n")
        if new_line != line:
            count += 1
        new_lines.append(new_line)

    new_content = "\n".join(new_lines)

    if count == 0:
        return 0

    if dry_run:
        print(f"\n--- {filepath.name} ({count} 行置換) ---")
        for i, (old, new) in enumerate(zip(lines, new_lines)):
            if old != new:
                print(f"  - {old.rstrip()}")
                print(f"  + {new.rstrip()}")
    else:
        filepath.write_text(new_content, encoding="utf-8")
        print(f"  修正: {filepath.name} ({count} 行)")

    return count


def main():
    dry_run = "--dry-run" in sys.argv
    single_file = None

    for arg in sys.argv[1:]:
        if arg == "--file" and len(sys.argv) > sys.argv.index(arg) + 1:
            single_file = Path(sys.argv[sys.argv.index(arg) + 1])

    if single_file:
        total = fix_file(single_file, dry_run=dry_run)
        print(f"\n合計: {total} 行置換{'（dry-run）' if dry_run else ''}")
        return

    files = sorted(POSTS_DIR.glob("*.md"))
    total = 0

    for fp in files:
        c = fix_file(fp, dry_run=dry_run)
        total += c

    mode = "（dry-run）" if dry_run else ""
    print(f"\n合計: {total} 行置換{mode} / {len(files)} ファイル確認")


if __name__ == "__main__":
    main()
