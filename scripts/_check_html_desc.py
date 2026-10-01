import os, re
d = "dist/posts"
files = [
    ("2026-09-27-092931-auto-post", "092931"),
    ("2026-09-29-053425-auto-post", "053425"),
    ("2026-09-29-060942-auto-post", "060942"),
    ("kaze-wo-oru-gin-no-hari", "211041"),
]
for f, label in files:
    html = open(os.path.join(d, f, "index.html"), encoding="utf-8").read()
    m = re.search(r'<meta name="description" content="([^"]*)"', html)
    if m:
        desc = m.group(1)
        print(f"{label}: {len(desc)} chars")
    else:
        print(f"{label}: NOT FOUND")
