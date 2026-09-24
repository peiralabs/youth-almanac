#!/usr/bin/env python3
"""Inject region data into the template to produce a standalone tool.

The data is embedded rather than fetched. A browser refuses to fetch a sibling
file from a file:// page, so a tool that loaded its own JSON would work on the
website and break the moment someone downloaded it - and being able to keep a
copy that still works is the point.
"""
import json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
TEMPLATE = os.path.join(ROOT, "src", "tool.template.html")
DATA = os.path.join(HERE, "data")
DIST = os.path.join(ROOT, "dist")


def build(region):
    src = os.path.join(DATA, "%s.json" % region)
    data = json.load(open(src, encoding="utf-8"))
    tpl = open(TEMPLATE, encoding="utf-8").read()

    # The payload sits in a <script type="application/json">, so the only
    # sequence that could break out of it is a literal </script>.
    blob = json.dumps(data, separators=(",", ":"), ensure_ascii=False)
    blob = blob.replace("</", "<\\/")

    if "__DATA__" not in tpl:
        raise SystemExit("template has no __DATA__ placeholder")
    out = tpl.replace("__DATA__", blob)

    os.makedirs(DIST, exist_ok=True)
    dst = os.path.join(DIST, "youth-almanac.html" if region == "nwa"
                       else "youth-almanac-%s.html" % region)
    open(dst, "w", encoding="utf-8").write(out)
    return dst, len(out), len(data["events"])


def main():
    regions = sys.argv[1:] or [f[:-5] for f in sorted(os.listdir(DATA))
                               if f.endswith(".json")]
    for r in regions:
        dst, size, n = build(r)
        print("%-10s %4d events -> %s (%.0f KB)"
              % (r, n, os.path.relpath(dst, ROOT), size / 1024))
    return 0


if __name__ == "__main__":
    sys.exit(main())
