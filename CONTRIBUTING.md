# Contributing

The most useful thing you can do is **add your town**. That is a data change,
not a code change, and it needs no dependencies.

Read [docs/finding-feeds.md](docs/finding-feeds.md) — it covers the four source
types and how to find the one URL you need.

---

## Ground rules

**Only public feeds.** Nothing behind a login, nothing behind a paywall,
nothing a site's `robots.txt` asks you to leave alone. Use the endpoint the
organisation's own front end uses, at a polite interval. The weekly schedule is
deliberate; please do not shorten it.

**Do not invent data.** If a source does not state an age range, leave it
unstated — the tool shows *All ages* and the reader can judge. A wrong age rule
is worse than a missing one, because a parent acts on it.

**Free and open to the public.** This lists things a family can turn up to.
Commercial classes, private clubs and anything requiring membership are out of
scope, and so is anything that needs a background check to attend.

**No tracking, ever.** No analytics, no third-party scripts, no fonts or assets
loaded from someone else's server. The tool is one file and makes no network
calls once it has loaded. A pull request that adds a request to a third party
will be declined regardless of how useful it is.

---

## Adding a region or a source

```bash
git clone https://github.com/peiralabs/youth-almanac.git
cd youth-almanac
# edit registry/regions/<yours>.json
python3 build/fetch_events.py
python3 build/validate.py
python3 build/make_tool.py
```

Open `dist/youth-almanac.html` and actually read it, at an age you know a child
of. The validator catches the four mistakes that have bitten us before — adult
programmes, infant storytimes above age six, closures listed as activities, and
times shifted by a timezone bug — but it cannot tell you whether a listing is
*useful*.

In the pull request, say:

- which sources you added, and how many events each returned
- anything you had to work around
- that you opened the built file and read it

---

## Changing the code

Keep it boring. Python 3.9+ standard library, no packages. The tool is one HTML
file with no framework, no build step beyond data injection, and no
dependencies. This is what makes it possible for the whole thing to keep working
unattended, and to still work when downloaded.

If you are changing age parsing or filtering, add a case to the checks in
`build/validate.py` covering what you fixed. Age handling is the part with the
most real-world variation and the part where a mistake matters most.

---

## Reporting a wrong listing

Open an issue with the event title, the town, and what is wrong. If you know
what the organisation actually published, say so — a link to their page is
ideal.

Wrong listings are treated as bugs, not cosmetic issues. Getting a family to
the wrong place at the wrong time is the failure this project exists to avoid.

---

## Code of conduct

Be decent. This is a small project about helping families find things for their
kids to do; there is nothing here worth being unpleasant over.
