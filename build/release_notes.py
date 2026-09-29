#!/usr/bin/env python3
"""Describe what is actually in the build, for the release page.

Kept out of the workflow so it can be run and read locally, and so the notes
say what the artefact contains rather than repeating the tag back at people.
"""
import glob
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")


def main():
    files = sorted(glob.glob(os.path.join(DATA, "*.json")))
    if not files:
        print("no data files in %s" % DATA, file=sys.stderr)
        return 1

    regions, total = [], 0
    for path in files:
        with open(path, encoding="utf-8") as fh:
            d = json.load(fh)
        n = len(d["events"])
        total += n
        regions.append((d.get("name", d.get("region", "?")), n,
                        d.get("generated", "?")))

    print("Listings collected on %s." % regions[0][2])
    print()
    for name, n, _gen in regions:
        print("- **%s** — %d events" % (name, n))
    print()
    print("%d events in total." % total)
    print()
    print("The download is a single self-contained file. Open it from disk and it "
          "keeps working with no network and no build step, which is the point of "
          "the project — and the reason it cannot update itself. Check back here "
          "for a fresher copy rather than assuming the one you have is current.")
    print()
    print("Verify what you downloaded:")
    print()
    print("```sh")
    print("sha256sum --ignore-missing -c SHA256SUMS")
    print("```")
    return 0


if __name__ == "__main__":
    sys.exit(main())
