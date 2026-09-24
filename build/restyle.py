#!/usr/bin/env python3
"""Replace the tool's style block and masthead with the Art Deco treatment.

Kept as a separate, re-runnable step so the design can be revised without
touching the template's markup or behaviour. Every id and class the script
depends on is preserved.

No webfonts: the tool must make no third-party request, so the period feel
comes from geometric system faces (Futura on macOS, Century Gothic on Windows)
plus wide-tracked uppercase and inline SVG ornament.
"""
import os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
TPL = os.path.join(ROOT, "src", "tool.template.html")

# Inline ornament. '#' MUST be percent-encoded inside a data URI - an unescaped
# one terminates the URI and silently truncates the image.
SUNBURST = (
    "data:image/svg+xml;utf8,"
    "%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 240 60'%3E"
    "%3Cg fill='none' stroke='%23C9A227' stroke-width='1.6'%3E"
    "%3Cpath d='M120 58 V14'/%3E"
    "%3Cpath d='M120 58 L96 20 M120 58 L144 20'/%3E"
    "%3Cpath d='M120 58 L74 30 M120 58 L166 30'/%3E"
    "%3Cpath d='M120 58 L54 42 M120 58 L186 42'/%3E"
    "%3Cpath d='M120 58 L36 52 M120 58 L204 52'/%3E"
    "%3C/g%3E"
    "%3Ccircle cx='120' cy='10' r='4.5' fill='%23C9A227'/%3E"
    "%3C/svg%3E")

CHEVRON = (
    "data:image/svg+xml;utf8,"
    "%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 300 12'%3E"
    "%3Cg fill='none' stroke='%23C9A227' stroke-width='1.3'%3E"
    "%3Cpath d='M0 6 H118'/%3E%3Cpath d='M182 6 H300'/%3E"
    "%3Cpath d='M128 10 L136 2 L144 10'/%3E"
    "%3Cpath d='M144 10 L152 2 L160 10'/%3E"
    "%3Cpath d='M160 10 L168 2 L176 10'/%3E"
    "%3C/g%3E%3C/svg%3E")

STYLE = """<style>
/* Art Deco: geometry, symmetry, brass on deep green. System faces only -
   the tool makes no third-party request, so no webfonts. */
:root{
  --night:#12211D; --deep:#0C1714; --cream:#F5F0E3; --paper:#FFFDF6;
  --ink:#17241F; --muted:#5C6B62; --gold:#A8801F; --gold-line:#D8C48A;
  --jade:#1B5247; --oxblood:#7E3B44; --line:#DED5BE; --soft:#EFE9D8;
  --accent:var(--jade); --accent-ink:#F7F2E4;
  --deco:url("%s"); --chev:url("%s");
}
@media (prefers-color-scheme:dark){
  :root:not([data-theme="light"]){
    --cream:#0E1A17; --paper:#152420; --ink:#EDE5D2; --muted:#9AACA1;
    --gold:#D9B65E; --gold-line:#6B5A2E; --line:#2A3B34; --soft:#1A2B26;
    --jade:#79C2AC; --accent:#79C2AC; --accent-ink:#0B1512; --oxblood:#D08A96;
  }
}
*{box-sizing:border-box}
html{-webkit-text-size-adjust:100%%}
body{
  margin:0;background:var(--cream);color:var(--ink);
  font:16px/1.6 "Avenir Next","Avenir","Segoe UI",system-ui,-apple-system,Roboto,Helvetica,Arial,sans-serif;
}
.wrap{max-width:920px;margin:0 auto;padding:0 18px 72px}
a{color:var(--jade)}
:focus-visible{outline:2px solid var(--gold);outline-offset:3px}
.skip{position:absolute;left:-9999px}
.skip:focus{left:10px;top:10px;background:var(--paper);padding:10px 14px;z-index:30}

/* ---- masthead ------------------------------------------------------- */
header.top{text-align:center;padding:40px 0 4px;position:relative}
.deco-top{height:52px;margin:0 auto 10px;max-width:260px;
  background:var(--deco) no-repeat center/contain}
h1{
  font-family:"Futura","Century Gothic","Avenir Next",system-ui,sans-serif;
  font-size:clamp(1.9rem,7vw,3rem);font-weight:600;margin:0;
  letter-spacing:.3em;text-transform:uppercase;line-height:1.05;
  text-indent:.3em;  /* balance the trailing letter-space */
}
.rule{height:12px;margin:14px auto 12px;max-width:320px;
  background:var(--chev) no-repeat center/contain}
.sub{color:var(--muted);margin:0 auto;max-width:44ch;font-size:1rem}
.meta{color:var(--muted);font-size:.74rem;margin:14px 0 0;
  text-transform:uppercase;letter-spacing:.18em}

/* ---- stepped frame, the recurring deco device ----------------------- */
.panel,.ev{
  background:var(--paper);border:1px solid var(--line);
  box-shadow:inset 0 0 0 1px var(--paper),inset 0 0 0 2px transparent;
  position:relative;
}
.panel::before,.ev::before,
.panel::after,.ev::after{
  content:"";position:absolute;width:14px;height:14px;pointer-events:none;
  border-color:var(--gold-line);border-style:solid;border-width:0;
}
.panel::before,.ev::before{top:5px;left:5px;border-top-width:2px;border-left-width:2px}
.panel::after,.ev::after{bottom:5px;right:5px;border-bottom-width:2px;border-right-width:2px}

.panel{padding:20px;margin:22px 0}
.row{display:flex;flex-wrap:wrap;gap:16px}
.f{flex:1 1 200px;min-width:0}
label.lbl,.lbl{
  display:block;font-size:.68rem;text-transform:uppercase;letter-spacing:.2em;
  color:var(--gold);margin:0 0 7px;font-weight:700;
  font-family:"Futura","Century Gothic","Avenir Next",system-ui,sans-serif;
}
select,input[type=search],input[type=number]{
  width:100%%;font:inherit;padding:11px 12px;border-radius:0;
  border:1px solid var(--line);border-bottom:2px solid var(--gold-line);
  background:var(--cream);color:var(--ink);-webkit-appearance:none;appearance:none}
input[type=range]{width:100%%;accent-color:var(--jade)}
.agewrap{display:flex;align-items:center;gap:14px}
.agebig{
  font-family:"Futura","Century Gothic",system-ui,sans-serif;
  font-size:1.7rem;font-weight:600;min-width:2.4ch;text-align:center;
  font-variant-numeric:tabular-nums;color:var(--jade);
  border-bottom:2px solid var(--gold);line-height:1.1}

.chips{display:flex;flex-wrap:wrap;gap:9px;margin-top:16px}
.chip{
  cursor:pointer;border:1px solid var(--gold-line);background:transparent;
  color:var(--ink);border-radius:0;padding:8px 14px;
  font:600 .78rem/1.2 "Futura","Century Gothic","Avenir Next",system-ui,sans-serif;
  text-transform:uppercase;letter-spacing:.11em}
.chip[aria-pressed="true"]{background:var(--jade);color:var(--accent-ink);border-color:var(--jade)}
.chip .n{opacity:.75;font-weight:400;margin-left:7px;letter-spacing:0}

.bar{display:flex;flex-wrap:wrap;gap:12px;align-items:center;
  justify-content:space-between;margin:22px 0 4px}
.count{font-family:"Futura","Century Gothic",system-ui,sans-serif;
  text-transform:uppercase;letter-spacing:.13em;font-size:.82rem}
.count strong{font-size:1.1rem;color:var(--jade)}
.count .q{color:var(--muted);letter-spacing:.09em}
.btn{
  cursor:pointer;border:1px solid var(--gold-line);background:var(--paper);
  color:var(--ink);border-radius:0;padding:9px 16px;
  font:600 .74rem/1.2 "Futura","Century Gothic","Avenir Next",system-ui,sans-serif;
  text-transform:uppercase;letter-spacing:.14em}
.btn[aria-pressed="true"]{background:var(--jade);color:var(--accent-ink);border-color:var(--jade)}

/* ---- day headings --------------------------------------------------- */
.day{
  margin:30px 0 10px;font-size:.78rem;font-weight:700;position:sticky;top:0;
  background:var(--cream);padding:12px 0 8px;z-index:2;
  font-family:"Futura","Century Gothic",system-ui,sans-serif;
  text-transform:uppercase;letter-spacing:.22em;color:var(--gold);
  border-bottom:2px solid var(--gold-line);
  display:flex;align-items:center;gap:12px}
.day::after{content:"";flex:1;height:1px;background:var(--gold-line);opacity:.6}

/* ---- events --------------------------------------------------------- */
.ev{padding:18px;margin:12px 0}
.ev h3{margin:0 0 5px;font-size:1.06rem;line-height:1.3;font-weight:600;
  font-family:"Futura","Century Gothic","Avenir Next",system-ui,sans-serif;
  letter-spacing:.01em}
.evtop{display:flex;gap:12px;align-items:baseline;flex-wrap:wrap}
.time{
  font-family:"Futura","Century Gothic",system-ui,sans-serif;
  font-variant-numeric:tabular-nums;font-weight:700;color:var(--jade);
  white-space:nowrap;text-transform:uppercase;letter-spacing:.09em;font-size:.92rem}
.where{color:var(--muted);font-size:.88rem;margin:3px 0 0;font-style:italic}
.desc{margin:10px 0 0;font-size:.93rem}
.tags{display:flex;flex-wrap:wrap;gap:7px;margin-top:12px}
.tag{
  font:600 .66rem/1.3 "Futura","Century Gothic",system-ui,sans-serif;
  border:1px solid var(--line);border-radius:0;padding:4px 10px;color:var(--muted);
  text-transform:uppercase;letter-spacing:.12em}
.tag.age{border-color:var(--jade);color:var(--jade)}
.tag.reg{border-color:var(--oxblood);color:var(--oxblood)}
.acts{display:flex;gap:9px;margin-top:13px;flex-wrap:wrap}
.acts a,.acts button{
  font:600 .7rem/1.2 "Futura","Century Gothic",system-ui,sans-serif;
  text-transform:uppercase;letter-spacing:.12em;text-decoration:none;
  border:1px solid var(--line);background:var(--cream);color:var(--ink);
  border-radius:0;padding:7px 13px;cursor:pointer}
.save[aria-pressed="true"]{background:var(--gold);color:#1B1403;border-color:var(--gold)}

.empty{text-align:center;padding:52px 18px;color:var(--muted)}
.empty h2{color:var(--ink);font-size:1.1rem;margin:0 0 10px;
  font-family:"Futura","Century Gothic",system-ui,sans-serif;
  text-transform:uppercase;letter-spacing:.18em}
footer{
  margin-top:52px;padding-top:22px;border-top:2px solid var(--gold-line);
  color:var(--muted);font-size:.85rem}
footer strong{color:var(--ink)}
.sr{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0);white-space:nowrap}

@media (max-width:520px){
  h1{letter-spacing:.18em;text-indent:.18em}
  .day{letter-spacing:.16em}
}
@media print{
  .panel,.bar,.acts,.deco-top,.rule,footer .noprint{display:none}
  body{background:#fff;color:#000}
  .ev{break-inside:avoid;border-color:#999}
  .ev::before,.ev::after{display:none}
  .day{position:static}
}
</style>""" % (SUNBURST, CHEVRON)

MAST = """<header class="top">
  <div class="deco-top" aria-hidden="true"></div>
  <h1>Youth Almanac</h1>
  <div class="rule" aria-hidden="true"></div>
  <p class="sub">Free clubs, classes and events for ages 6&ndash;18, taken straight from public library and museum calendars.</p>
  <p class="meta" id="meta"></p>
</header>"""


def main():
    s = open(TPL, encoding="utf-8").read()

    a = s.index("<style>")
    b = s.index("</style>") + len("</style>")
    s = s[:a] + STYLE + s[b:]

    s = re.sub(r'<header class="top">.*?</header>', MAST, s, count=1, flags=re.S)

    open(TPL, "w", encoding="utf-8").write(s)

    # The '#' rule is worth asserting rather than trusting.
    for name, uri in (("sunburst", SUNBURST), ("chevron", CHEVRON)):
        if "#" in uri:
            raise SystemExit("%s contains a raw '#': it would truncate the data URI" % name)
    for need in ('id="meta"', 'id="controls"', 'id="results"', 'class="chip'):
        if need not in s:
            raise SystemExit("restyle dropped %s" % need)
    print("restyled: style block + masthead replaced, ornaments clean")
    return 0


if __name__ == "__main__":
    sys.exit(main())
