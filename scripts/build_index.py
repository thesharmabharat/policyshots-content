#!/usr/bin/env python3
"""Generate index.json from the markdown articles in articles/<category>/.

Layout:

    articles/
      policy/ps_001.md
      business/ps_019.md
      economy/...
      startup/...
      capitalMarkets/...

Each article is a .md file with a YAML-ish frontmatter block:

    ---
    title: ...
    excerpt: ...
    type: daily              # daily | markets | infographic
    symbol: lock.shield.fill
    publishedAt: 2026-06-23T09:00:00Z
    readMinutes: 4            # optional; auto-computed from word count if absent
    image: images/x.jpg       # optional
    ---
    <markdown body>

- `id` is derived from the filename (ps_001.md -> ps_001). Must be unique
  across the whole repo, not just within a category.
- `category` is inferred from the parent folder name (policy/ -> "policy"). A
  `category:` line in frontmatter, if present, overrides the folder (escape
  hatch for exceptions) but normally should be omitted.
- `path` is articles/<category>/<filename>.
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

VALID_CATEGORIES = {"policy", "business", "economy", "startup", "capitalMarkets"}

# Fields we carry into the manifest (body is intentionally excluded).
META_FIELDS = ("title", "excerpt", "type", "symbol", "publishedAt",
               "readMinutes", "image")


def split_frontmatter(text):
    """Return (frontmatter_dict, body_str). Raises if frontmatter is missing."""
    if not text.startswith("---"):
        raise ValueError("missing frontmatter block")
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
        if len(value) >= 2 and value[0] in "\"'" and value[-1] == value[0]:
            value = value[1:-1]
        fm[key.strip()] = value
    return fm, body


def word_count(body):
    return len(re.findall(r"\b\w+\b", body))


def build():
    articles = []
    seen_ids = {}

    if not os.path.isdir(ARTICLES_DIR):
        raise SystemExit(f"no {ARTICLES_DIR}/ directory found")

    category_dirs = sorted(
        d for d in os.listdir(ARTICLES_DIR)
        if os.path.isdir(os.path.join(ARTICLES_DIR, d))
    )

    for category_dir in category_dirs:
        if category_dir not in VALID_CATEGORIES:
            print(f"warning: skipping unknown category folder '{category_dir}/' "
                  f"(expected one of {sorted(VALID_CATEGORIES)})")
            continue

        dir_path = os.path.join(ARTICLES_DIR, category_dir)
        for filename in sorted(os.listdir(dir_path)):
            if not filename.endswith(".md"):
                continue
            article_id = filename[:-3]  # strip .md
            path = os.path.join(dir_path, filename)
            with open(path, "r", encoding="utf-8") as f:
                text = f.read()

            try:
                fm, body = split_frontmatter(text)
            except ValueError as e:
                raise SystemExit(f"{path}: {e}")

            for required in ("title", "excerpt", "type", "publishedAt"):
                if required not in fm:
                    raise SystemExit(f"{path}: missing required field '{required}'")

            if article_id in seen_ids:
                raise SystemExit(
                    f"duplicate article id '{article_id}': "
                    f"{seen_ids[article_id]} and {path}"
                )
            seen_ids[article_id] = path

            entry = {"id": article_id, "category": fm.get("category", category_dir),
                      "path": f"{ARTICLES_DIR}/{category_dir}/{filename}"}
            for key in META_FIELDS:
                if key in fm and fm[key] != "":
                    entry[key] = fm[key]

            if "readMinutes" not in entry:
                minutes = max(1, math.ceil(word_count(body) / WORDS_PER_MINUTE))
                entry["readMinutes"] = minutes
            else:
                entry["readMinutes"] = int(entry["readMinutes"])

            articles.append(entry)

    articles.sort(key=lambda a: a.get("publishedAt", ""), reverse=True)

    manifest = {
        "generatedAt": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "count": len(articles),
        "categories": sorted(VALID_CATEGORIES),
        "articles": articles,
    }

    with open(OUTPUT, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
        f.write("\n")

    print(f"Wrote {OUTPUT} with {len(articles)} articles across "
          f"{len(category_dirs)} category folders.")


if __name__ == "__main__":
    build()
