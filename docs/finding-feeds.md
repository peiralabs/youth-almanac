# Finding your library's calendar feed

You need one URL. Finding it takes about five minutes, and once someone has done
it for a town it never needs doing again.

Start at your library's events page and look at the address bar.

---

## Communico

**You have it if** the events URL contains `libnet.info`, or looks like
`attend.<something>.org`.

Communico's own front end fetches `/eeventcaldata`. You need only the hostname:

```json
{
  "id": "yourtown-library",
  "org": "Yourtown Public Library",
  "town": "Yourtown",
  "phone": "555-123-4567",
  "site": "https://www.yourtownlibrary.org/",
  "type": "communico",
  "host": "attend.yourtownlibrary.org"
}
```

Check it works:

```bash
curl -s "https://attend.yourtownlibrary.org/eeventcaldata?event_type=0&req=%7B%22private%22%3Afalse%2C%22date%22%3A%222026-01-01%22%2C%22days%22%3A60%2C%22locations%22%3A%5B%5D%2C%22ages%22%3A%5B%5D%2C%22types%22%3A%5B%5D%7D" | head -c 300
```

JSON starting with `[{` means you have the right host.

Communico is the best case: it returns an `agesArray`, so ages come from a
field rather than from reading the title, and it accepts a `days` window so one
request covers a year.

---

## Springshare LibCal

**You have it if** the events URL contains `libcal.com`, or the page embeds a
calendar from a `*.libcal.com` host.

You need the hostname **and** a calendar id.

1. Open the library's calendar page and view source.
2. Search for `cid=`. The number after it is the calendar id.

```json
{
  "id": "yourtown-library",
  "org": "Yourtown Public Library",
  "town": "Yourtown",
  "phone": "555-123-4567",
  "site": "https://www.yourtownlibrary.org/",
  "type": "ics",
  "url": "https://yourtown.libcal.com/ical_subscribe.php?cid=12345"
}
```

**Use `ical_subscribe.php`, not `api_events.php`.** The API endpoint caps at
roughly 200 records — about two months — while the ICS feed returns everything
the library has published, often a full year. This is the single most common
mistake.

**LibCal writes times in UTC.** The fetcher converts them using the region's
`timezone`, so make sure that field is right. Get it wrong and a 4:30 PM club
lists at 9:30 PM, then drifts another hour when the clocks change.

---

## Google Calendar

**You have it if** the page embeds `calendar.google.com`.

Find the calendar's public address — often the library's own email address —
and use the `basic.ics` form:

```json
{
  "type": "ics",
  "url": "https://calendar.google.com/calendar/ical/library%40example.com/public/basic.ics",
  "all_ages_calendar": true
}
```

Set `all_ages_calendar` when the calendar mixes every audience together and its
children's programmes are not titled by age. It relaxes the requirement for an
age keyword and relies on explicit ranges instead. Only use it where you have
actually read the calendar — it lets more through, including things you may not
want.

---

## Nothing machine-readable at all

Some towns publish a PDF, or nothing. Use the `json` source type and list the
events by hand:

```json
{
  "id": "yourtown-rec",
  "org": "Yourtown Parks and Recreation",
  "town": "Yourtown",
  "type": "json",
  "events": [
    { "date": "2026-06-14", "title": "Summer Art Camp",
      "age_min": 8, "age_max": 12, "venue": "Community Center",
      "desc": "Two weeks of drawing and clay.", "reg": true }
  ]
}
```

Hand-maintained entries are welcome but go stale, so prefer a feed where one
exists, and add a note saying when you last checked.

---

## Before you open a pull request

```bash
python3 build/fetch_events.py    # your source should report "ok" with a count
python3 build/validate.py        # must pass
python3 build/make_tool.py
```

Then open `dist/youth-almanac.html`, set the age to one you know a child of, and
read the listings. **Look for these specifically**, because they are what has
gone wrong before:

- Adult programmes appearing — an "18 +" range technically includes an
  18-year-old.
- Infant storytimes showing for older children.
- Library closures listed as activities.
- Times off by several hours, which means the timezone or the UTC handling is
  wrong.

The validator catches all four, but read the output anyway. It is a listing for
other people's children.
