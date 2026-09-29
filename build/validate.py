#!/usr/bin/env python3
"""Gate the generated data before it can be published.

This runs in CI on every refresh. A listing for other people's children is
worth being fussy about: it is better to publish yesterday's data than to
publish today's with a toddler class filed under teenagers.
"""
import collections, json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(HERE, "data")

MIN_EVENTS = 200            # NWA alone sits around 700; a collapse is a bug
AUDIENCE_MIN, AUDIENCE_MAX = 6, 18

ADULT = re.compile(r"\b(adults?|seniors?|grown[- ]?ups?|18 ?\+|21 ?\+)\b", re.I)
CLOSURE = re.compile(r"\b(closed|closing early|holiday hours|staff meeting|"
                     r"board meeting|friends of the library)\b", re.I)
INFANT = re.compile(r"\b(baby|babies|toddler|lapsit|newborn|infant)\b", re.I)
# A feed supplies this and it becomes an href. Anything but http(s) - a
# javascript: or data: URL, or a scheme-relative //host - is an injection.
URL_OK = re.compile(r"^https?://", re.I)


def sources_for(region):
    """Source ids the region registry declares, or [] when it has none."""
    p = os.path.join(ROOT, "registry", "regions", "%s.json" % region)
    if not os.path.exists(p):
        return []
    with open(p, encoding="utf-8") as fh:
        return [s["id"] for s in json.load(fh)["sources"]]


def check(path):
    with open(path, encoding="utf-8") as fh:
        d = json.load(fh)
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
        if e.get("url") and not URL_OK.match(e["url"]):
            errs.append("%s: url is not http(s): %r" % (where, e["url"][:60]))

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

    # A source whose feed quietly breaks returns nothing, and the global event
    # floor never notices: losing the largest source here still clears it. Each
    # configured source has to show up on its own.
    counts = collections.Counter(e.get("src") for e in ev)
    configured = sources_for(d.get("region", ""))
    for sid in configured:
        if not counts.get(sid):
            errs.append("%s: source %r produced no events - its feed is broken"
                        % (name, sid))
    for sid in sorted(k for k in counts if k and k not in configured):
        warns.append("%s: source %r is not in the region registry" % (name, sid))

    towns = {t["name"] for t in d.get("towns", [])}
    for e in ev:
        if e.get("town") and e["town"] not in towns:
            warns.append("%s: town %r is not in the region's town list"
                         % (name, e["town"]))
            break
    return errs, warns, counts


def main():
    files = sorted(f for f in os.listdir(DATA) if f.endswith(".json")) \
        if os.path.isdir(DATA) else []
    if not files:
        print("no data files in %s - run fetch_events.py first" % DATA)
        return 1
    all_err, all_warn, tally = [], [], collections.Counter()
    for f in files:
        e, w, c = check(os.path.join(DATA, f))
        all_err += e
        all_warn += w
        tally += c
    for w in all_warn[:20]:
        print("warn: " + w)
    if all_err:
        print("\n%d problem(s):" % len(all_err))
        for e in all_err[:40]:
            print("  " + e)
        return 1
    total = 0
    for f in files:
        with open(os.path.join(DATA, f), encoding="utf-8") as fh:
            total += len(json.load(fh)["events"])
    # Printed on success too: a source collapsing from 200 events to 3 is not an
    # error, but it is the thing a human should see in the log.
    for sid, n in sorted(tally.items(), key=lambda kv: -kv[1]):
        print("  %-26s %5d" % (sid, n))
    print("OK - %d region file(s), %d events, %d warning(s)"
          % (len(files), total, len(all_warn)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
