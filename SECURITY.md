# Security policy

## Reporting a vulnerability

Please report security issues privately through
[GitHub's private vulnerability reporting](https://github.com/peiralabs/youth-almanac/security/advisories/new)
rather than opening a public issue, so a fix can ship before the details are public.

If that is not available to you, open an issue saying only that you have a security
concern and asking for a private channel. Do not put the details in it.

## What to expect

This is maintained by one person as a side project, so reports are handled on a
best-effort basis rather than against a service-level agreement. Expect an
acknowledgement within about a week. A valid report and its fix are published together.

## The thing most worth looking at

Youth Almanac builds its listings from **third-party calendar feeds** — public library
and museum systems such as LibCal, Communico and plain iCalendar. Those feeds are
outside our control, and their contents are rendered into a page that parents and
children then use. **Treat every field that originates in a feed as untrusted input,
and assume a feed can be wrong, compromised or hostile.**

Concretely, the following are in scope and are the reports most likely to matter:

- Anything in a calendar feed that leads to script execution, navigation to an
  attacker-chosen destination, or content injection in the built tool. Event data is
  embedded into a `<script type="application/json">` block by `build/make_tool.py`,
  and rendered by the template in `src/tool.template.html`.
- Any way to bypass the escaping in the build or the template.
- Anything that lets a pull request, a fork, or feed content influence what the weekly
  refresh workflow commits and pushes. That workflow holds a write token.
- Anything that causes the build to write outside `build/data` and `dist`.

## The offline copy matters

The tool is deliberately a single self-contained HTML file so that a downloaded copy
keeps working with no network and no build step. That is the point of the project, and
it has a security consequence worth stating plainly: **a copy someone downloaded does
not get patched when we fix something.** If you report an issue that affects the built
artefact, say so, because the advisory needs to tell people to re-download rather than
assume a fix reaches them.

## Not security issues

These are all welcome as ordinary issues, they are just not vulnerabilities:

- A listing that is wrong, stale, cancelled, duplicated, or in the wrong category.
- A library or museum feed that is unreachable or has changed shape.
- Disagreement about whether an event belongs in the almanac.

## Personal information and young people

The almanac lists **events, not people**. It is built from calendars that organisations
publish for the public, and it is intended to carry nothing beyond what those
organisations already published: what the event is, when and where it happens, and how
to contact the *organisation* running it.

If a listing nonetheless contains personal information about an individual — a private
phone number, a home address, a named child — that is a privacy problem rather than a
vulnerability, and it should be dealt with quickly rather than quietly. Report it the
same private way, say plainly that it is a personal-information issue, and it will be
removed from the data and the published build without waiting for a release.

If you are the organisation that published the source calendar and you want a listing
removed, an ordinary issue is fine.

## Supported versions

The published tool is rebuilt from the upstream feeds every week. Only the current
build is supported; there are no maintained older versions. For anything you are
running yourself, the supported answer is to rebuild from `main`.
