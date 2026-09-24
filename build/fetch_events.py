#!/usr/bin/env python3
"""Collect youth activities for every region in the registry.

Reads registry/regions/*.json and writes build/data/<region>.json. Adding a
town means adding a source to a registry file; nothing here needs to change.

Four source types are supported, chosen because they are what public
institutions actually run:

  communico  The events platform many US public libraries use. Its own front
             end calls /eeventcaldata, which accepts a `days` window and
             returns an agesArray, so age comes from a field rather than from
             guessing at the title. It also sends Access-Control-Allow-Origin,
             which the other three do not.
  ics        Any iCalendar feed: Springshare LibCal, Google Calendar, most
             council and museum calendars. Recurrence rules are expanded here.
  tessitura  The ticketing system behind many museums and theatres, reached
             through the venue's own proxy.
  json       An escape hatch for a hand-maintained list, so a town with no
             machine-readable calendar can still be represented.

Standard library only, so it runs in CI with no install step.
"""
import json, os, re, ssl, sys, urllib.request, urllib.parse
from datetime import datetime, timedelta, date

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
REGIONS = os.path.join(ROOT, "registry", "regions")
OUT = os.path.join(HERE, "data")

UA = "youth-almanac/1.0 (+https://peira.dev/tools/youth-almanac/)"
TIMEOUT = 60
HORIZON_DAYS = 270          # far enough to be useful, short enough to stay small
CTX = ssl.create_default_context()
AMP = chr(38)

# The audience this tool is for. Anything whose stated range cannot overlap
# this at all is dropped at ingest; finer filtering is the reader's to do.
AUDIENCE_MIN, AUDIENCE_MAX = 6, 18
GRADE_TO_AGE = 5            # US grade N is about age N+5

try:
    from zoneinfo import ZoneInfo
    UTC = ZoneInfo("UTC")
except Exception:                                            # pragma: no cover
    ZoneInfo = None
    UTC = None


# --------------------------------------------------------------------- utils
def fetch(url, data=None, headers=None):
    req = urllib.request.Request(url, data=data, method="POST" if data else "GET")
    req.add_header("User-Agent", UA)
    for k, v in (headers or {}).items():
        req.add_header(k, v)
    with urllib.request.urlopen(req, timeout=TIMEOUT, context=CTX) as r:
        return r.read().decode("utf-8", "replace")


def strip_html(s):
    s = re.sub(r"<[^>]+>", " ", s or "")
    for a, b in (("nbsp", " "), ("amp", AMP), ("#39", "'"), ("quot", '"'),
                 ("rsquo", "'"), ("lsquo", "'"), ("ldquo", '"'), ("rdquo", '"'),
                 ("mdash", "-"), ("ndash", "-"), ("hellip", "...")):
        s = s.replace(AMP + a + ";", b)
    return re.sub(r"\s+", " ", s).strip()


# ----------------------------------------------------------------- age logic
def age_bounds(text):
    """Best-effort (min, max) age. None means the source did not say.

    None is never treated as "no limit, therefore fine" downstream - an
    unstated bound stays unstated, and the reader is shown what the source
    actually published.
    """
    lo = hi = None
    m = re.search(r"grades?\s*(\d{1,2})\s*(?:-|–|—|to)\s*(\d{1,2})", text, re.I)
    if m:
        lo, hi = int(m.group(1)) + GRADE_TO_AGE, int(m.group(2)) + GRADE_TO_AGE
    if lo is None:
        # The unit is load-bearing. "Best for ages 0-18 months" read as years
        # turned a baby storytime into an event for the whole 0-18 audience,
        # which is how 78 of them reached a listing for 6-to-18-year-olds.
        m = re.search(r"ages?\s*(\d{1,2})\s*(?:-|–|—|to)\s*(\d{1,2})"
                      r"\s*(months?|mos?\b|weeks?|years?|yrs?\b)?", text, re.I)
        if m:
            lo, hi = int(m.group(1)), int(m.group(2))
            unit = (m.group(3) or "").lower()
            if unit.startswith(("month", "mo", "week")):
                lo, hi = lo // 12, max(0, hi // 12)
    if lo is None:
        m = re.search(r"\b(?:ages?\s*)?(\d{1,2})\s*\+", text)
        if m:
            lo = int(m.group(1))
    if lo is None:
        m = re.search(r"\bgrades?\s*(\d{1,2})\b", text, re.I)
        if m:
            lo = hi = int(m.group(1)) + GRADE_TO_AGE
    if lo is None and re.search(r"\btween\b", text, re.I):
        lo, hi = 10, 12
    if lo is None and re.search(r"\bteen|young adult\b", text, re.I):
        lo, hi = 13, 18
    if lo is None and re.search(r"\b(preschool|pre-k)\b", text, re.I):
        lo, hi = 3, 5
    if lo is not None and hi is not None and hi < lo:
        lo, hi = hi, lo
    return lo, hi


# Age words Communico and LibCal actually use, mapped to spans. Used only when
# a listing states no numeric range of its own.
AGE_WORDS = [
    (r"early childhood|baby|babies|toddler|lapsit|preschool|pre-k|"
     r"story ?time|tales for|mother goose|wiggle|rhyme", (0, 5)),
    (r"school[- ]age|grade school|elementary|kids|children", (6, 11)),
    (r"tween", (10, 12)),
    (r"teen|young adult", (13, 18)),
    (r"family|all ages", (0, 18)),
]

NOT_FOR_KIDS = re.compile(
    r"\b(adults? only|21 ?\+|18 ?\+ only|senior|medicare|caregivers? only|"
    r"staff meeting|board meeting|book a librarian|bookmobile|"
    # closures and internal business are not activities
    r"closed|closing early|holiday hours|friends of the library|"
    r"board of trustees|volunteer orientation for adults)\b",
    re.I)

# Checked against the TITLE only. "Adult Book Club" and "Tiny Art Show -
# ADULTS 18 +" both survived the range test, because "18 +" technically
# overlaps an 18-year-old. A description that merely mentions adults (a parent
# must attend, say) should not disqualify a children's event, which is why
# this never sees the description.
ADULT_TITLE = re.compile(
    r"\b(adults?|grown[- ]?ups?|parents? only|seniors?|"
    r"18 ?\+|19 ?\+|21 ?\+)\b", re.I)


def words_to_bounds(text):
    for pat, span in AGE_WORDS:
        if re.search(pat, text, re.I):
            return span
    return (None, None)


EARLY_FORMAT = re.compile(
    r"\b(story ?time|tales|mother goose|lapsit|wiggle|rhyme time)\b", re.I)


def refine_bounds(title, lo, hi):
    """Clamp formats whose name tells you more than their age tag does.

    Libraries tag a storytime "Family", which is true - a family may attend -
    but taken literally it advertises a ballerina storytime to a
    seventeen-year-old. Where the format is unmistakably for small children,
    the upper bound is pulled down to match the name.
    """
    if EARLY_FORMAT.search(title or "") and (hi is None or hi > 6):
        hi = 6
        if lo is not None and lo > hi:
            lo = hi
    return lo, hi


def overlaps_audience(lo, hi):
    """True unless the stated range provably sits outside 6-18."""
    if lo is not None and lo > AUDIENCE_MAX:
        return False
    if hi is not None and hi < AUDIENCE_MIN:
        return False
    return True


# ------------------------------------------------------------------ category
CATS = [
    ("stem",    r"3d print|laser|robot|engineer|coding|code |computer|science|"
                r"steam|stem|lego|snapology|circuit|minecraft|math|chess"),
    ("art",     r"craft|art|paint|draw|clay|pottery|sew|knit|jewel|bracelet|"
                r"printmak|linocut|maker|origami|collage|photograph"),
    ("books",   r"book club|writer|writing|poetry|read|storytell|manga|comic|"
                r"library card|literac|author|banned books"),
    ("music",   r"music|band|choir|ukulele|guitar|drum|karaoke|open mic|dance|"
                r"theatre|theater|drama|acting|improv"),
    ("games",   r"game|gaming|dungeons|dragons|pokemon|tabletop|board game|"
                r"video game|puzzle|trivia|movie|anime"),
    ("outdoors", r"garden|nature|hike|trail|park|bike|fishing|camp|outdoor|"
                r"astronomy|birding"),
    ("service", r"volunteer|service|donate|charity|food bank|community|"
                r"mentor|homework help|tutor"),
    ("life",    r"cook|bake|babysit|driving|finance|money|job|resume|college|"
                r"first aid|safety|wellness|mindful|yoga|life skill|etiquette|"
                r"sign language|language|spanish|study|homework|tutor|"
                r"scholarship|career|interview"),
    ("club",    r"\bclub\b|meetup|hangout|hang out|social|drop[- ]in|"
                r"advisory board|council|leadership|scouts?|troop|4-h"),
    ("play",    r"play|toy|bounce|sensory|messy|slime|bubble|balloon|"
                r"scavenger|hunt|party|festival|carnival|fair\b|celebration|"
                r"holiday|halloween|christmas|easter|birthday"),
]
DEFAULT_CAT = "other"


def categorise(text):
    t = text.lower()
    for cat, pat in CATS:
        if re.search(pat, t):
            return cat
    return DEFAULT_CAT


# ---------------------------------------------------------------------- ICS
def ics_unfold(text):
    lines = []
    for ln in text.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        if ln[:1] in (" ", "\t") and lines:
            lines[-1] += ln[1:]
        else:
            lines.append(ln)
    return lines


def ics_parse(text):
    events, cur = [], None
    for ln in ics_unfold(text):
        if ln == "BEGIN:VEVENT":
            cur = {}
        elif ln == "END:VEVENT":
            if cur is not None:
                events.append(cur)
            cur = None
        elif cur is not None and ":" in ln:
            key, val = ln.split(":", 1)
            cur.setdefault(key.split(";")[0].upper(), val)
    return events


def ics_dt(val, tz):
    """Parse an ICS stamp to naive local time.

    LibCal writes DTSTART in UTC with a trailing Z. Read as local it puts a
    4:30 PM club at 9:30 PM and drifts another hour across the DST boundary,
    so Z values are converted rather than assumed.
    """
    v = (val or "").strip()
    if v.endswith("Z"):
        try:
            dt = datetime.strptime(v, "%Y%m%dT%H%M%SZ")
        except ValueError:
            return None
        if ZoneInfo is None:
            return dt - timedelta(hours=5)
        return dt.replace(tzinfo=UTC).astimezone(ZoneInfo(tz)).replace(tzinfo=None)
    for fmt in ("%Y%m%dT%H%M%S", "%Y%m%d"):
        try:
            return datetime.strptime(v, fmt)
        except ValueError:
            continue
    return None


WD = {"MO": 0, "TU": 1, "WE": 2, "TH": 3, "FR": 4, "SA": 5, "SU": 6}


def nth_weekday(year, month, wd, n):
    if n > 0:
        d = date(year, month, 1)
        d += timedelta(days=(wd - d.weekday()) % 7) + timedelta(weeks=n - 1)
        return d if d.month == month else None
    d = date(year + (month == 12), month % 12 + 1, 1) - timedelta(days=1)
    return d - timedelta(days=(d.weekday() - wd) % 7)


def expand_rrule(start, rule, stop_date, tz):
    parts = dict(p.split("=", 1) for p in rule.split(";") if "=" in p)
    freq = parts.get("FREQ", "")
    interval = max(1, int(parts.get("INTERVAL", "1") or 1))
    count = int(parts["COUNT"]) if parts.get("COUNT") else None
    until = ics_dt(parts.get("UNTIL", ""), tz)
    stop = min(until.date(), stop_date) if until else stop_date
    byday = [d for d in parts.get("BYDAY", "").split(",") if d]
    out, guard = [], 0

    if freq == "WEEKLY":
        days = [WD[d[-2:]] for d in byday] or [start.weekday()]
        cur = start.date()
        while cur <= stop and guard < 600:
            guard += 1
            wk = cur - timedelta(days=cur.weekday())
            for wd in sorted(days):
                d = wk + timedelta(days=wd)
                if start.date() <= d <= stop:
                    out.append(d)
            cur = wk + timedelta(weeks=interval)
    elif freq == "MONTHLY":
        y, m = start.year, start.month
        while date(y, m, 1) <= stop and guard < 300:
            guard += 1
            if byday:
                for tok in byday:
                    mt = re.match(r"(-?\d)?([A-Z]{2})", tok)
                    if mt and mt.group(2) in WD:
                        d = nth_weekday(y, m, WD[mt.group(2)],
                                        int(mt.group(1)) if mt.group(1) else 1)
                        if d and start.date() <= d <= stop:
                            out.append(d)
            else:
                try:
                    d = date(y, m, start.day)
                    if start.date() <= d <= stop:
                        out.append(d)
                except ValueError:
                    pass
            m += interval
            while m > 12:
                m -= 12
                y += 1
    elif freq == "DAILY":
        d = start.date()
        while d <= stop and guard < 600:
            guard += 1
            out.append(d)
            d += timedelta(days=interval)
    else:
        out = [start.date()]

    out = sorted(set(out))
    return out[:count] if count else out


def from_ics(src, tz, horizon):
    text = fetch(src["url"])
    relaxed = bool(src.get("all_ages_calendar"))
    out = []
    for e in ics_parse(text):
        summary = strip_html(e.get("SUMMARY", ""))
        desc = strip_html(e.get("DESCRIPTION", ""))
        blob = summary + " " + desc + " " + (e.get("CATEGORIES", "") or "")
        if not summary or NOT_FOR_KIDS.search(blob) or ADULT_TITLE.search(summary):
            continue
        lo, hi = age_bounds(blob)
        if lo is None and hi is None:
            lo, hi = words_to_bounds(blob)
        # A calendar that mixes all audiences needs some youth signal; a
        # dedicated youth feed does not.
        if lo is None and hi is None and not relaxed:
            continue
        if not overlaps_audience(lo, hi):
            continue
        dt = ics_dt(e.get("DTSTART", ""), tz)
        if not dt:
            continue
        timed = "T" in (e.get("DTSTART") or "")
        end = ics_dt(e.get("DTEND", ""), tz)
        exdates = {x.date() for x in
                   (ics_dt(t, tz) for t in (e.get("EXDATE", "") or "").split(",") if t)
                   if x}
        days = (expand_rrule(dt, e["RRULE"], horizon, tz) if e.get("RRULE")
                else [dt.date()])
        for d in days:
            if d in exdates or d < date.today() or d > horizon:
                continue
            out.append(mk(summary, d, dt if timed else None,
                          end if (end and timed) else None,
                          src, desc, lo, hi,
                          strip_html(e.get("LOCATION", "")),
                          bool(re.search(r"regist", blob, re.I))))
    return out


# ---------------------------------------------------------------- Communico
def from_communico(src, tz, horizon):
    req = json.dumps({"private": False, "date": date.today().isoformat(),
                      "days": HORIZON_DAYS, "locations": [], "ages": [],
                      "types": []})
    qs = urllib.parse.urlencode({"event_type": 0, "req": req})
    raw = json.loads(fetch("https://%s/eeventcaldata?%s" % (src["host"], qs)))
    out = []
    for e in raw:
        title = re.sub(r"\s*\*\s*$", "", strip_html(e.get("title")))
        if not title:
            continue
        desc = strip_html(e.get("description"))
        ages = ", ".join(str(a) for a in (e.get("agesArray") or []))
        blob = title + " " + desc + " " + ages
        if NOT_FOR_KIDS.search(blob) or ADULT_TITLE.search(title):
            continue
        lo, hi = age_bounds(title + " " + desc)
        if lo is None and hi is None:
            lo, hi = words_to_bounds(ages or blob)
        if lo is None and hi is None:
            continue
        if not overlaps_audience(lo, hi):
            continue
        start = (e.get("event_start") or "")[:16]
        if len(start) < 10:
            continue
        d = datetime.strptime(start[:10], "%Y-%m-%d").date()
        if d < date.today() or d > horizon:
            continue
        t0 = datetime.strptime(start, "%Y-%m-%d %H:%M") if len(start) == 16 else None
        e1 = (e.get("event_end") or "")[:16]
        t1 = datetime.strptime(e1, "%Y-%m-%d %H:%M") if len(e1) == 16 else None
        venue = e.get("venue")
        out.append(mk(title, d, t0, t1, src, desc, lo, hi,
                      "" if str(venue) in ("None", "") else venue,
                      str(e.get("allow_reg")) == "1"))
    return out


# ---------------------------------------------------------------- Tessitura
def from_tessitura(src, tz, horizon):
    body = json.dumps({"startDateTime": date.today().isoformat() + "T00:00:00",
                       "endDateTime": horizon.isoformat() + "T00:00:00"}).encode()
    raw = json.loads(fetch(src["url"], data=body,
                           headers={"Content-Type": "application/json"}))
    recs = raw if isinstance(raw, list) else raw.get("data", [])
    out, seen = [], set()
    for e in recs:
        title = strip_html((e.get("ProductionSeason") or {}).get("Description"))
        when = (e.get("PerformanceDate") or "")[:19]
        if not title or len(when) < 10 or NOT_FOR_KIDS.search(title) \
                or ADULT_TITLE.search(title):
            continue
        lo, hi = age_bounds(title)
        if lo is None and hi is None:
            lo, hi = words_to_bounds(title)
        if lo is None and hi is None:
            continue
        if not overlaps_audience(lo, hi):
            continue
        d = datetime.strptime(when[:10], "%Y-%m-%d").date()
        if d < date.today() or d > horizon:
            continue
        key = (title, when)
        if key in seen:
            continue
        seen.add(key)
        t0 = None
        try:
            t0 = datetime.strptime(when.replace("T", " ")[:16], "%Y-%m-%d %H:%M")
        except ValueError:
            pass
        out.append(mk(title, d, t0, None, src, "", lo, hi, "", True))
    return out


def from_json(src, tz, horizon):
    """Hand-maintained listings committed to the registry."""
    out = []
    for e in src.get("events", []):
        try:
            d = datetime.strptime(e["date"], "%Y-%m-%d").date()
        except (KeyError, ValueError):
            continue
        if d < date.today() or d > horizon:
            continue
        lo, hi = e.get("age_min"), e.get("age_max")
        out.append(mk(e.get("title", ""), d, None, None, src,
                      e.get("desc", ""), lo, hi, e.get("venue", ""),
                      bool(e.get("reg"))))
    return out


# ------------------------------------------------------------------- record
def mk(title, d, t0, t1, src, desc, lo, hi, venue, reg):
    lo, hi = refine_bounds(title, lo, hi)
    return {
        "t": title,
        "d": d.isoformat(),
        "s": t0.strftime("%H:%M") if t0 else "",
        "e": t1.strftime("%H:%M") if t1 else "",
        "org": src["org"],
        "town": src["town"],
        "ph": src.get("phone", ""),
        "url": src.get("site", ""),
        "v": venue or "",
        "x": (desc or "")[:280],
        "lo": lo, "hi": hi,
        "c": categorise(title + " " + (desc or "")),
        "reg": bool(reg),
        "src": src["id"],
    }


HANDLERS = {"communico": from_communico, "ics": from_ics,
            "tessitura": from_tessitura, "json": from_json}


def build_region(path):
    reg = json.load(open(path, encoding="utf-8"))
    tz = reg.get("timezone", "America/Chicago")
    horizon = date.today() + timedelta(days=HORIZON_DAYS)
    events, report = [], []
    for src in reg["sources"]:
        fn = HANDLERS.get(src.get("type"))
        if not fn:
            report.append((src["id"], 0, "unknown type %r" % src.get("type")))
            continue
        try:
            got = fn(src, tz, horizon)
            events.extend(got)
            report.append((src["id"], len(got), "ok"))
        except Exception as exc:
            report.append((src["id"], 0, "FAIL %s: %s" % (type(exc).__name__, exc)))

    seen, uniq = set(), []
    for e in sorted(events, key=lambda x: (x["d"], x["s"], x["t"])):
        k = (e["src"], e["t"].lower(), e["d"], e["s"])
        if k in seen:
            continue
        seen.add(k)
        uniq.append(e)

    out = {
        "region": reg["region"],
        "name": reg["name"],
        "towns": reg["towns"],
        "generated": datetime.now().strftime("%Y-%m-%d"),
        "horizon": horizon.isoformat(),
        "orgs": [{"id": s["id"], "org": s["org"], "town": s["town"],
                  "phone": s.get("phone", ""), "site": s.get("site", "")}
                 for s in reg["sources"]],
        "events": uniq,
    }
    return out, report


def main():
    os.makedirs(OUT, exist_ok=True)
    files = sorted(f for f in os.listdir(REGIONS) if f.endswith(".json"))
    if not files:
        print("no regions in %s" % REGIONS)
        return 1
    failed = False
    for f in files:
        data, report = build_region(os.path.join(REGIONS, f))
        print("\n%s  (%s)" % (data["name"], data["region"]))
        for sid, n, status in report:
            print("   %-24s %5d  %s" % (sid, n, status))
            if status != "ok":
                failed = True
        dst = os.path.join(OUT, "%s.json" % data["region"])
        json.dump(data, open(dst, "w", encoding="utf-8"),
                  separators=(",", ":"), ensure_ascii=False)
        size = os.path.getsize(dst)
        print("   %-24s %5d events -> %s (%.0f KB)"
              % ("TOTAL", len(data["events"]), os.path.basename(dst), size / 1024))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
