#!/usr/bin/env python3
"""Generate index.json from the markdown articles in articles/.

Each article is a .md file with a YAML-ish frontmatter block:

    ---
    title: ...
    excerpt: ...
    category: policy
    type: daily
    symbol: lock.shield.fill
    publishedAt: 2026-06-23T09:00:00Z
    readMinutes: 4          # optional; auto-computed from word count if absent
    image: images/x.jpg     # optional
    ---
    <markdown body>

- `id` is derived from the filename (ps_001.md -> ps_001).
- `path` is articles/<filename>.
- `readMinutes` defaults to ceil(words / 200) if not given.
- Output is sorted by publishedAt, newest first.

Intentionally dependency-free (simple frontmatter parser) so the Action needs no
pip install.
"""

import json
import math
import os
import re
from datetime import datetime, timezone

ARTICLES_DIR = "articles"
OUTPUT = "index.json"
WORDS_PER_MINUTE = 200

# Fields we carry into the manifest (body is intentionally excluded).
META_FIELDS = ("title", "excerpt", "category", "type", "symbol", "publishedAt",
               "readMinutes", "image")


def split_frontmatter(text):
    """Return (frontmatter_dict, body_str). Raises if frontmatter is missing."""
    if not text.startswith("---"):
        raise ValueError("missing frontmatter block")
    # Split on the closing --- delimiter.
    parts = re.split(r"\n---\s*\n", text[3:], maxsplit=1)
    if len(parts) != 2:
        raise ValueError("malformed frontmatter (no closing ---)")
    raw_fm, body = parts
    fm = {}
    for line in raw_fm.strip().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        value = value.strip()
        # Strip surrounding quotes if present.
        if len(value) >= 2 and value[0] in "\"'" and value[-1] == value[0]:
            value = value[1:-1]
        fm[key.strip()] = value
    return fm, body


def word_count(body):
    return len(re.findall(r"\b\w+\b", body))


def build():
    articles = []
    if not os.path.isdir(ARTICLES_DIR):
        raise SystemExit(f"no {ARTICLES_DIR}/ directory found")

    for filename in sorted(os.listdir(ARTICLES_DIR)):
        if not filename.endswith(".md"):
            continue
        article_id = filename[:-3]  # strip .md
        path = os.path.join(ARTICLES_DIR, filename)
        with open(path, "r", encoding="utf-8") as f:
            text = f.read()

        try:
            fm, body = split_frontmatter(text)
        except ValueError as e:
            raise SystemExit(f"{path}: {e}")

        for required in ("title", "excerpt", "category", "type", "publishedAt"):
            if required not in fm:
                raise SystemExit(f"{path}: missing required field '{required}'")

        entry = {"id": article_id, "path": f"{ARTICLES_DIR}/{filename}"}
        for key in META_FIELDS:
            if key in fm and fm[key] != "":
                entry[key] = fm[key]

        # Auto read time if not provided.
        if "readMinutes" not in entry:
            minutes = max(1, math.ceil(word_count(body) / WORDS_PER_MINUTE))
            entry["readMinutes"] = minutes
        else:
            entry["readMinutes"] = int(entry["readMinutes"])

        articles.append(entry)

    # Newest first.
    articles.sort(key=lambda a: a.get("publishedAt", ""), reverse=True)

    manifest = {
        "generatedAt": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "count": len(articles),
        "articles": articles,
    }

    with open(OUTPUT, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
        f.write("\n")

    print(f"Wrote {OUTPUT} with {len(articles)} articles.")


if __name__ == "__main__":
    build()
