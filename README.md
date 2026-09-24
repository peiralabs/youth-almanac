# Youth Almanac

**What is there for my kid to do this week?** — answered from the calendars your
public library and museums already publish, for ages 6 to 18.

**Use it now → [peira.dev/tools/youth-almanac](https://peira.dev/tools/youth-almanac/)** ·
no signup, no tracking, no account.

Pick an age and a town. You get the things a child that age is actually eligible
for, with the time, the place, the age rule the organisation published, and
whether you need to register first.

---

## Why this exists

Every town has more for children than any one parent can keep track of. The
information is public, but it is scattered across five or six calendars, each on
a different platform, most of which show you one month at a time and none of
which let you ask the only question a parent has: *what can my nine-year-old do
on Saturday?*

The libraries are already publishing this properly. It just needs collecting.

---

## What it does

- **Filters by your child's actual age**, using the range each organisation
  published — not a guess from the title. A programme for grades 7–8 does not
  show up for a ten-year-old.
- **One town or all of them**, with a count next to each.
- **Next 7 days, 30 days, 3 months, or everything** the sources have published.
- **Activity types** — science, art, books, music, games, outdoors,
  volunteering, life skills, clubs — with live counts that reflect your other
  filters, so a type never promises results it cannot deliver.
- **Search** across titles, organisations, venues and descriptions.
- **Save things and copy the list** as plain text, to paste into a message.
- **Works offline.** Save the page and it keeps working, because the data is in
  the file rather than fetched from anywhere.
- **Nothing is tracked.** No analytics, no cookies, no network calls once the
  page has loaded. Your age and town preference are remembered in your own
  browser and go no further.

---

## Where the data comes from

Everything is a public feed, fetched the same way the organisation's own website
fetches it, once a week, with caching and an identifying User-Agent.

| Platform | Used by | How |
|---|---|---|
| Communico | many US public libraries | the `/eeventcaldata` endpoint its own front end calls, which returns an age field |
| Springshare LibCal | many US public libraries | the iCalendar subscribe feed |
| Google Calendar | smaller libraries and community groups | the public `.ics` feed |
| Tessitura | museums and theatres | the venue's own public proxy |

Nothing is scraped from behind a login, and nothing is republished that the
organisation has not already made public.

**Ages are parsed, not guessed.** "Grades 7–8", "Ages 10–12", "13+", "Teen" and
"Best for ages 0–18 months" are all read for what they say — including the
units, which matter more than you would think. Where a source states no age at
all, the listing says *All ages* rather than pretending to know.

---

## Adding your town

**You do not need to write any code.** A region is a JSON file in
[`registry/regions/`](registry/regions/), and adding a library means adding an
entry to its `sources` list.

1. Find your library's calendar platform. If the URL contains `libcal.com` it is
   LibCal; if it contains `libnet.info` or the page calls `/eeventcaldata` it is
   Communico. [`docs/finding-feeds.md`](docs/finding-feeds.md) walks through
   both.
2. Copy `registry/regions/nwa.json` as a starting point, or add a source to an
   existing region.
3. Run it and see what you get:

```bash
python3 build/fetch_events.py
python3 build/validate.py
python3 build/make_tool.py
```

4. Open `dist/youth-almanac.html` and check the listings look right for a child
   you know.
5. Open a pull request. Include roughly how many events your source returned and
   anything odd you had to work around.

No dependencies — the build is Python 3.9+ standard library only.

---

## How this repo is built

```
registry/regions/*.json   what to fetch — the part contributors edit
build/fetch_events.py     fetch, parse ages, categorise, de-duplicate
build/validate.py         the gate: refuses to publish bad data
build/make_tool.py        inject data into the template
src/tool.template.html    the tool itself, one file, no framework
dist/youth-almanac.html   the published artefact
```

A weekly GitHub Action runs all three steps and commits the result only if the
validator passes. The validator refuses adult-only listings, closures, infant
formats visible above age six, inverted age ranges, and any run that loses most
of its events.

---

## Honest limitations

- **Coverage is only as wide as the registry.** Right now that is Northwest
  Arkansas. There is no automatic way to go from a zip code to a library's
  calendar endpoint — someone has to find it once, and then it works forever.
- **Free things only, mostly.** These sources are public institutions, so
  almost everything listed is free. Paid classes and private clubs are not
  represented, and the tool does not pretend to price anything.
- **Age rules are what the organisation wrote down.** Some write nothing. When
  in doubt, call — every listing carries the phone number.
- **A weekly refresh means a cancellation may lag.** Always check before you go.

---

## Licence

MIT. See [LICENSE](LICENSE).

The listings themselves belong to the organisations that published them; this
repo only collects and points at them.
