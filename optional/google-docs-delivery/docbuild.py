#!/usr/bin/env python3
"""
docbuild.py - deterministic text processing + fixed format spec for the Google Doc delivery.

WHY THIS EXISTS: the delivered Doc looked different every run and kept breaking — markdown
link brackets survived ("[Source: IRDAI]"), the meta title's "| Acme" pipe split table cells,
fonts/spacing drifted. Root cause: score-and-deliver improvised the formatting per run. This
module makes the error-prone parts DETERMINISTIC and LOCALLY TESTABLE:

  - parse_links(text)  -> clean text with brackets/backslashes removed + link ranges to apply
  - build_table(rows)  -> a clean cell matrix that NEVER splits on pipes inside a value
  - FORMAT             -> the one fixed style spec (fonts, sizes, spacing, widths, callout)

score-and-deliver imports these so every Doc is built the same way. The thin Google Docs API
renderer (apply_doc) consumes this module's output; the logic that used to break is here and
is unit-tested (run `python3 docbuild.py --selftest`).
"""
import re, sys

# ---- THE single fixed format spec. Change here = changes every output identically. ----
FORMAT = {
    "body_font": "Arial", "body_size": 11,
    "h1_size": 22, "h2_size": 18, "h3_size": 14, "h4_size": 12,
    "heading_bold": True, "heading_color": "000000",   # black, bold headings (not Word's blue)
    "space_above_pt": 6, "space_below_pt": 6, "space_above_heading_pt": 12,
    "table_header_bold": True,
    # column widths (points) for the two QA tables that were breaking
    "keyword_table_widths": [170, 45, 60, 60, 55, 75, 60, 60],  # wide Keyword col, narrow flags
    "meta_table_widths": [110, 320, 70],
    "callout": {"bg": "#FFF4CE", "border": "#E0A800", "bold_lead": True, "pad_pt": 8},
    "qa_explainer_italic": True, "qa_explainer_grey": "#666666",
}


def parse_links(text):
    """Return (clean_text, links) where links = [(start, end, url)] into clean_text.
    - Markdown [anchor](url)  -> 'anchor' with a link over its range. Brackets removed.
    - Bare [label] with no url -> 'label' with brackets removed (NO link). Fixes '[Source: IRDAI]'.
    - Stray backslashes removed. This guarantees zero literal '[' ']' '\\' survive.
    """
    out, links, i = [], [], 0
    pat = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")   # markdown link
    bare = re.compile(r"\[([^\]]+)\]")              # bare bracket
    while i < len(text):
        m = pat.match(text, i)
        if m:
            anchor = m.group(1)
            start = len("".join(out))
            out.append(anchor)
            links.append((start, start + len(anchor), m.group(2)))
            i = m.end()
            continue
        m = bare.match(text, i)
        if m:
            out.append(m.group(1))      # keep label, drop brackets, no link
            i = m.end()
            continue
        out.append(text[i]); i += 1
    clean = "".join(out).replace("\\", "")
    # collapse any double spaces introduced
    clean = re.sub(r"[ \t]{2,}", " ", clean)
    return clean, links


def build_table(rows):
    """rows = list[list[str]] already split into cells by the CALLER (structured data, never a
    markdown pipe string). Each cell is bracket/link-cleaned. Returns a clean matrix. Because we
    never split on '|', a value like 'What is X? | Acme' stays in ONE cell."""
    clean = []
    width = max((len(r) for r in rows), default=0)
    for r in rows:
        cells = [parse_links(str(c))[0].strip() for c in r]
        cells += [""] * (width - len(cells))      # pad ragged rows so columns never shift
        clean.append(cells)
    return clean


def assert_no_brackets(text):
    """Post-build guard: raise if any literal bracket/backslash survived (the run-2 bug)."""
    bad = [c for c in "[]\\" if c in text]
    if bad:
        raise ValueError("doc still contains literal %s — bracket-strip failed" % bad)
    return True


def _selftest():
    # 1. markdown link -> anchor only, link range correct, no brackets
    c, l = parse_links("see [survival period](https://x.com/sp) now")
    assert "[" not in c and "]" not in c, c
    assert c == "see survival period now", repr(c)
    assert l and c[l[0][0]:l[0][1]] == "survival period", l
    # 2. bare bracket citation -> brackets stripped, no link (the [Source: IRDAI] bug)
    c, l = parse_links("...2024. Source: [IRDAI] After five years")
    assert "[" not in c and "]" not in c, c
    assert l == [], l
    # 3. stray backslash removed (the meta-title bug)
    c, _ = parse_links("Does Car Insurance Cover Repairs? \\ | Acme")
    assert "\\" not in c, c
    # 4. pipe inside a cell value stays in ONE cell (the SEO table bug)
    t = build_table([["Asset", "Value", "Char"],
                     ["Meta title", "What is waiting period? | Acme", "50"]])
    assert t[1][1] == "What is waiting period? | Acme", t[1]
    assert len(t[1]) == 3, t[1]
    # 5. ragged row padded so columns don't shift
    t = build_table([["a", "b", "c"], ["x"]])
    assert t[1] == ["x", "", ""], t[1]
    # 6. no-bracket guard
    assert_no_brackets("clean text")
    try:
        assert_no_brackets("bad [x]"); raise AssertionError("guard missed bracket")
    except ValueError:
        pass
    print("docbuild selftest: ALL PASS")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        _selftest()
    else:
        print(__doc__)
