import glob
import json
import os
import re

from article.config import BASE_URL, SLUG_REDIRECTS_FILE


def _load_slug_redirects():
    if not os.path.exists(SLUG_REDIRECTS_FILE):
        return {}
    try:
        with open(SLUG_REDIRECTS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _save_slug_redirects(redirects):
    os.makedirs(os.path.dirname(SLUG_REDIRECTS_FILE), exist_ok=True)
    with open(SLUG_REDIRECTS_FILE, "w", encoding="utf-8") as f:
        json.dump(redirects, f, ensure_ascii=False, indent=2)


def _get_existing_slugs(posts_dir="src/content/posts"):
    slugs = set()
    if not os.path.exists(posts_dir):
        return slugs
    for filepath in glob.glob(os.path.join(posts_dir, "*.md")):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                c = f.read()
        except Exception:
            continue
        slug_m = re.search(r'^slug:\s*["\']?(.*?)["\']?$', c, re.MULTILINE)
        if slug_m and slug_m.group(1).strip():
            slugs.add(slug_m.group(1).strip())
    return slugs


def _resolve_slug_collision(slug, existing_slugs):
    redirects = _load_slug_redirects()
    if slug not in existing_slugs:
        return slug, False
    counter = 2
    unique_slug = f"{slug}-{counter}"
    while unique_slug in existing_slugs:
        counter += 1
        unique_slug = f"{slug}-{counter}"
    redirects[slug] = unique_slug
    _save_slug_redirects(redirects)
    print(f"🔗 slug競合を検出: {slug} → {unique_slug} (リダイレクト記録)")
    return unique_slug, True


def _load_posts_for_links(posts_dir="src/content/posts"):
    result = []
    if not os.path.exists(posts_dir):
        return result
    for filepath in glob.glob(os.path.join(posts_dir, "*.md")):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                c = f.read()
        except Exception:
            continue
        title_m = re.search(r'^title:\s*["\']?(.*?)["\']?$', c, re.MULTILINE)
        if not title_m:
            continue
        title = title_m.group(1).strip()
        slug_m = re.search(r'^slug:\s*["\']?(.*?)["\']?$', c, re.MULTILINE)
        slug = slug_m.group(1).strip() if slug_m else ""
        if not slug:
            base = os.path.basename(filepath)
            slug = base.replace("-auto-post.md", "").replace(".md", "").lower()
        tags_m = re.search(r'^tags:\s*\[([^\]]*)\]', c, re.MULTILINE)
        tags = []
        if tags_m:
            tags = [t.strip().strip('"\'') for t in tags_m.group(1).split(",") if t.strip()]
        result.append({"title": title, "slug": slug, "tags": tags})
    return result


def _existing_link_spans(content):
    spans = []
    for m in re.finditer(r'!\[[^\]]*\]\([^)]*\)|\[[^\]]*\]\([^)]*\)', content):
        spans.append((m.start(), m.end()))
    return spans


def inject_internal_links(content, posts_dir="src/content/posts", max_links=5):
    posts = _load_posts_for_links(posts_dir)
    if not posts:
        return content
    fm_end = content.find("---\n", 4)
    if fm_end == -1:
        body_start = 0
    else:
        body_start = fm_end + 4
    body = content[body_start:]
    link_spans = _existing_link_spans(body)
    replacements = []
    for post in posts:
        title = post["title"]
        slug = post["slug"]
        if len(title) < 3:
            continue
        pattern = re.escape(title)
        for m in re.finditer(pattern, body):
            pos = m.start()
            length = len(title)
            overlap = False
            for s, e in link_spans:
                if pos < e and pos + length > s:
                    overlap = True
                    break
            if overlap:
                continue
            url = f"{BASE_URL}/posts/{slug}"
            link_md = f"[{title}]({url})"
            replacements.append((pos, pos + length, link_md))
            if len(replacements) >= max_links:
                break
        if len(replacements) >= max_links:
            break
    if not replacements:
        return content
    replacements.sort(key=lambda x: x[0], reverse=True)
    for start, end, replacement in replacements:
        body = body[:start] + replacement + body[end:]
    return content[:body_start] + body
