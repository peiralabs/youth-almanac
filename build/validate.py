#!/usr/bin/env python3
"""Gate the generated data before it can be published.

This runs in CI on every refresh. A listing for other people's children is
worth being fussy about: it is better to publish yesterday's data than to
publish today's with a toddler class filed under teenagers.
"""
import json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(HERE, "data")

MIN_EVENTS = 200            # NWA alone sits around 700; a collapse is a bug
AUDIENCE_MIN, AUDIENCE_MAX = 6, 18

ADULT = re.compile(r"\b(adults?|seniors?|grown[- ]?ups?|18 ?\+|21 ?\+)\b", re.I)
CLOSURE = re.compile(r"\b(closed|closing early|holiday hours|staff meeting|"
                     r"board meeting|friends of the library)\b", re.I)
INFANT = re.compile(r"\b(baby|babies|toddler|lapsit|newborn|infant)\b", re.I)


def check(path):
    d = json.load(open(path, encoding="utf-8"))
    ev = d.get("events", [])
    errs, warns = [], []
    name = os.path.basename(path)

    if len(ev) < MIN_EVENTS:
        errs.append("%s: only %d events (floor %d)" % (name, len(ev), MIN_EVENTS))

    for f in ("region", "name", "towns", "generated", "orgs", "events"):
        if f not in d:
            errs.append("%s: missing top-level %r" % (name, f))

    seen = set()
    for i, e in enumerate(ev):
        where = "%s[%d] %r" % (name, i, e.get("t", "")[:40])
        for f in ("t", "d", "org", "town", "c"):
            if not e.get(f):
                errs.append("%s: empty %s" % (where, f))
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", e.get("d", "")):
            errs.append("%s: bad date %r" % (where, e.get("d")))
        if e.get("s") and not re.match(r"^\d{2}:\d{2}$", e["s"]):
            errs.append("%s: bad time %r" % (where, e["s"]))

        lo, hi = e.get("lo"), e.get("hi")
        if lo is not None and hi is not None and lo > hi:
            errs.append("%s: inverted ages %s-%s" % (where, lo, hi))
        if hi is not None and hi < AUDIENCE_MIN:
            errs.append("%s: max age %s is below the audience" % (where, hi))
        if lo is not None and lo > AUDIENCE_MAX:
            errs.append("%s: min age %s is above the audience" % (where, lo))

        title = e.get("t", "")
        if ADULT.search(title):
            errs.append("%s: adult-only title reached a youth listing" % where)
        if CLOSURE.search(title):
            errs.append("%s: closure or internal meeting is not an activity" % where)
        if INFANT.search(title) and (hi is None or hi > 6):
            errs.append("%s: infant format is visible above age 6" % where)

        k = (e.get("src"), e.get("t"), e.get("d"), e.get("s"))
        if k in seen:
            warns.append("%s: duplicate" % where)
        seen.add(k)

    towns = {t["name"] for t in d.get("towns", [])}
    for e in ev:
        if e.get("town") and e["town"] not in towns:
            warns.append("%s: town %r is not in the region's town list"
                         % (name, e["town"]))
            break
    return errs, warns


def main():
    files = sorted(f for f in os.listdir(DATA) if f.endswith(".json")) \
        if os.path.isdir(DATA) else []
    if not files:
        print("no data files in %s - run fetch_events.py first" % DATA)
        return 1
    all_err, all_warn = [], []
    for f in files:
        e, w = check(os.path.join(DATA, f))
        all_err += e
        all_warn += w
    for w in all_warn[:20]:
        print("warn: " + w)
    if all_err:
        print("\n%d problem(s):" % len(all_err))
        for e in all_err[:40]:
            print("  " + e)
        return 1
    total = sum(len(json.load(open(os.path.join(DATA, f), encoding="utf-8"))["events"])
                for f in files)
    print("OK - %d region file(s), %d events, %d warning(s)"
          % (len(files), total, len(all_warn)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
