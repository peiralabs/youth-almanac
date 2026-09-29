#!/usr/bin/env python3
"""Tests for the publish gate.

Run with: python3 -m unittest discover -s tests

These cover the two things that fail silently: a calendar feed handing us a
URL that is not a link, and a feed that stops returning anything at all.
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "build"))
import validate  # noqa: E402

TEMPLATE = os.path.join(ROOT, "src", "tool.template.html")
NODE = shutil.which("node")
REGION = "nwa"
SOURCES = validate.sources_for(REGION)


def event(**over):
    """One event that passes every other rule, so a test fails for its own reason."""
    e = {"t": "Lego Club", "d": "2026-10-01", "s": "16:00", "org": "Library",
         "town": "Bentonville", "c": "stem", "lo": 8, "hi": 12,
         "src": SOURCES[0], "url": "https://example.org/"}
    e.update(over)
    return e


def run(events):
    """Validate a synthetic region file and return its errors."""
    doc = {"region": REGION, "name": "Test", "generated": "2026-10-01",
           "towns": [{"name": "Bentonville"}], "orgs": [], "events": events}
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "%s.json" % REGION)
        with open(p, "w", encoding="utf-8") as fh:
            json.dump(doc, fh)
        errs, _warns, _counts = validate.check(p)
    return errs


def errors_matching(events, needle):
    return [e for e in run(events) if needle in e]


class UrlScheme(unittest.TestCase):
    """esc() in the template stops an attribute breakout but not a bad scheme."""

    def test_dangerous_schemes_are_rejected(self):
        for bad in ("javascript:alert(1)",
                    "JaVaScRiPt:alert(1)",
                    "data:text/html;base64,PHNjcmlwdD4=",
                    "vbscript:msgbox(1)",
                    "//evil.example.com/",      # scheme-relative, inherits https
                    "file:///etc/passwd",
                    # Contains a valid scheme but does not start with one: an
                    # unanchored check would wave these through.
                    "javascript:fetch('https://evil.example.com')",
                    " https://example.org/",
                    "data:text/html,<a href='https://x'>"):
            with self.subTest(url=bad):
                self.assertTrue(errors_matching([event(url=bad)], "url is not http(s)"),
                                "accepted a dangerous url: %r" % bad)

    def test_ordinary_links_are_accepted(self):
        for good in ("https://example.org/events",
                     "http://example.org/events",
                     "HTTPS://EXAMPLE.ORG/"):
            with self.subTest(url=good):
                self.assertFalse(errors_matching([event(url=good)], "url is not http(s)"),
                                 "rejected a valid url: %r" % good)

    def test_absent_url_is_allowed(self):
        self.assertFalse(errors_matching([event(url="")], "url is not http(s)"))


class SourceCoverage(unittest.TestCase):
    """The global event floor cannot see one feed dying; this can."""

    def test_missing_source_is_an_error(self):
        # Every configured source except the last one reports in.
        events = [event(src=s) for s in SOURCES[:-1]]
        errs = errors_matching(events, "produced no events")
        self.assertTrue(errs, "a dead feed went unnoticed")
        self.assertIn(SOURCES[-1], errs[0])

    def test_all_sources_present_is_clean(self):
        events = [event(src=s) for s in SOURCES]
        self.assertFalse(errors_matching(events, "produced no events"))

    def test_registry_lists_sources(self):
        self.assertTrue(SOURCES, "registry declares no sources; other tests are vacuous")


class TemplateGuard(unittest.TestCase):
    """Execute the regex the template actually ships, not a copy of it."""

    @unittest.skipUnless(NODE, "node is not installed")
    def test_shipped_regex_rejects_dangerous_schemes(self):
        with open(TEMPLATE, encoding="utf-8") as fh:
            line = next((l for l in fh if "var url =" in l), "")
        m = re.search(r"/\^.*?/i", line)
        self.assertTrue(m, "no scheme guard found in the template render path")
        js = ("const re=%s;"
              "const bad=['javascript:alert(1)','data:text/html,x',"
              "'//evil.example.com/','javascript:/*https://evil*/alert(1)',"
              "' https://example.org/'];"
              "const good=['https://example.org/','http://example.org/'];"
              "for (const u of bad) if (re.test(u)) { console.error('accepted '+u); process.exit(1); }"
              "for (const u of good) if (!re.test(u)) { console.error('rejected '+u); process.exit(1); }"
              % m.group(0))
        r = subprocess.run([NODE, "-e", js], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr.strip())


if __name__ == "__main__":
    unittest.main()
