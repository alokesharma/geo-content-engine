#!/usr/bin/env python3
"""
build_doc.py - the EXECUTED delivery step. Renders the final Google Doc deterministically.

WHY THIS EXISTS: delivery was agent-improvised prose, so the format drifted every run
(fonts, spacing, table widths, surviving brackets). score-and-deliver now RUNS this script
instead of describing the steps, so every Doc is built identically from the locked FORMAT
spec in docbuild.py. The error-prone parsing (markdown -> ordered blocks, bracket-strip,
pipe-safe tables, Title Case) is here and is locally testable (`--dry-run`, `--selftest`);
the thin Google Docs API render sits behind it and needs one live-OAuth confirmation run.

USAGE:
    python3 build_doc.py article.md --dry-run        # parse + print block structure (no API)
    python3 build_doc.py article.md --title "<Brand> Blog -- <topic>"   # build the real Doc
    python3 build_doc.py --selftest

LOCKED FORMAT (from Format Reference.docx, frozen in docbuild.FORMAT):
    body Arial 11 | Heading 1/2/3/4 named styles | explainer text grey #666666
    "Section N." QA numbering | fixed meta + keyword table widths | pageless | callout #FFF4CE
"""
import sys, os, re, json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from docbuild import FORMAT, parse_links, build_table, assert_no_brackets

MINOR = {"a", "an", "the", "and", "but", "or", "nor", "for", "of", "in", "on", "at",
         "to", "by", "as", "is", "are", "vs", "with", "from", "into", "per", "via"}
# Acronyms to keep uppercase in Title-Cased headings. Add your own domain's acronyms here.
ACRONYMS = {"FAQ", "SEO", "GEO", "API", "SAAS", "USB", "LED", "PC", "AC", "DC"}


def title_case(text):
    """Title Case a heading: principal words capitalised, minor words lower (unless first/last),
    acronyms preserved, hyphen segments each capitalised ('Non-Accident')."""
    words = text.split()
    out = []
    for idx, w in enumerate(words):
        if w.upper() in ACRONYMS:
            out.append(w.upper()); continue
        segs = w.split("-")
        new_segs = []
        for seg in segs:
            if not seg:
                new_segs.append(seg); continue
            if seg.upper() in ACRONYMS:                 # acronym inside a hyphenated word (Non-PPN)
                new_segs.append(seg.upper()); continue
            low = seg.lower()
            first_last = (idx == 0 or idx == len(words) - 1)
            if low in MINOR and not first_last and "-" not in w:
                new_segs.append(low)
            else:
                new_segs.append(seg[0].upper() + seg[1:] if len(seg) > 1 else seg.upper())
        out.append("-".join(new_segs))
    return " ".join(out)


def _strip_internal_appendix(md):
    """v20.2 -- cut everything from '## Team to Supply' onwards before render. The Team-to-Supply
    appendix lists internal data requests ('brand internal data needed: …') that must never
    appear in the published Doc. v20.1 shipped them visible -- this strip closes that hole."""
    m = re.search(r"(?im)^#{1,3}\s*team to supply\b", md)
    return md[:m.start()].rstrip() + "\n" if m else md


def parse_markdown_to_blocks(md):
    """Markdown -> ordered list of typed blocks. This is the part that used to break.
    Block types: h1, h2, h3, h4, para, bullet, numbered, table, callout, hr, blank."""
    md = _strip_internal_appendix(md)                       # v20.2: drop Team-to-Supply before parsing
    blocks = []
    lines = md.split("\n")
    i = 0
    while i < len(lines):
        raw = lines[i]
        ln = raw.strip()
        if not ln:
            i += 1; continue
        # table: consecutive pipe rows -> ONE table block (cells split by caller, pipe-safe)
        if ln.startswith("|") and ln.count("|") >= 2:
            rows = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                cells = [c.strip() for c in lines[i].strip().strip("|").split("|")]
                if not re.match(r"^[\s:|-]+$", lines[i].strip()):   # skip the |---|---| rule
                    rows.append(cells)
                i += 1
            blocks.append({"type": "table", "rows": build_table(rows)})
            continue
        if ln.startswith("---"):
            blocks.append({"type": "hr"}); i += 1; continue
        m = re.match(r"^(#{1,4})\s+(.*)", ln)
        if m:
            lvl = len(m.group(1))
            txt = m.group(2).strip()
            txt = title_case(txt) if lvl in (1, 2) else txt   # H1/H2 -> Title Case
            blocks.append({"type": "h%d" % lvl, "text": parse_links(txt)[0]})
            i += 1; continue
        if ln.startswith(("⚠️", "💡", "📌")) or re.match(r"^>\s*\*\*", ln):
            clean, links = parse_links(re.sub(r"^>\s*", "", ln))
            blocks.append({"type": "callout", "text": clean, "links": links})
            i += 1; continue
        if re.match(r"^[-*]\s+", ln):
            clean, links = parse_links(re.sub(r"^[-*]\s+", "", ln))
            blocks.append({"type": "bullet", "text": clean, "links": links})
            i += 1; continue
        if re.match(r"^\d+[\.\)]\s+", ln):
            clean, links = parse_links(re.sub(r"^\d+[\.\)]\s+", "", ln))
            blocks.append({"type": "numbered", "text": clean, "links": links})
            i += 1; continue
        clean, links = parse_links(ln)
        blocks.append({"type": "para", "text": clean, "links": links})
        i += 1
    # post-build guarantee: no literal brackets/backslashes survived anywhere
    assert_no_brackets(" ".join(b.get("text", "") for b in blocks))
    return blocks


# ---------- Local .docx render (NO OAuth -- for fast format verification) ----------
def _add_hyperlink(paragraph, text, url):
    """Add a REAL Word hyperlink run (blue, underlined). python-docx has no built-in helper,
    so build the w:hyperlink element + external relationship by hand. Fixes the v8-v15 bug where
    links rendered as plain text because the renderer ignored the parsed link ranges."""
    from docx.oxml.shared import OxmlElement, qn
    r_id = paragraph.part.relate_to(
        url, "http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink",
        is_external=True)
    hl = OxmlElement("w:hyperlink"); hl.set(qn("r:id"), r_id)
    run = OxmlElement("w:r"); rPr = OxmlElement("w:rPr")
    col = OxmlElement("w:color"); col.set(qn("w:val"), "0563C1"); rPr.append(col)
    u = OxmlElement("w:u"); u.set(qn("w:val"), "single"); rPr.append(u)
    run.append(rPr)
    t = OxmlElement("w:t"); t.text = text; run.append(t)
    hl.append(run); paragraph._p.append(hl)


def _add_runs(paragraph, text, links=None):
    """Add text to a paragraph: parse **bold** inline, and apply REAL hyperlinks for any
    link ranges (list of (start, end, url) into `text`, as parse_links returns)."""
    from docx.shared import Pt

    def plain(seg):
        for j, part in enumerate(re.split(r"\*\*(.+?)\*\*", seg)):
            if not part:
                continue
            run = paragraph.add_run(part)
            run.font.name = FORMAT["body_font"]; run.font.size = Pt(FORMAT["body_size"])
            if j % 2 == 1:
                run.bold = True

    if not links:
        plain(text); return
    cursor = 0
    for start, end, url in sorted(links):
        if start > cursor:
            plain(text[cursor:start])
        _add_hyperlink(paragraph, text[start:end], url)
        cursor = end
    if cursor < len(text):
        plain(text[cursor:])


def render_to_docx(blocks, path):
    """Render parsed blocks to a real .docx (python-docx): real tables, Heading 1-4 styles,
    Arial 11 body, grey italic explainers, shaded callouts, bullet/number lists. This is the
    LOCAL proxy that proves the formatting logic without Google OAuth."""
    from docx import Document
    from docx.shared import Pt, RGBColor, Inches
    from docx.enum.section import WD_ORIENT
    doc = Document()
    doc.styles["Normal"].font.name = FORMAT["body_font"]
    doc.styles["Normal"].font.size = Pt(FORMAT["body_size"])
    # widen the usable area so wide tables (8-col keyword audit) aren't crushed
    sec = doc.sections[0]
    sec.left_margin = sec.right_margin = Inches(0.5)
    usable_in = sec.page_width.inches - 1.0   # full width minus the two 0.5in margins

    def _set_widths(tbl, ncols):
        """Distribute table width across the full page; give the content column the biggest share."""
        tbl.autofit = False
        if ncols == 3:                       # meta table: Asset | Value | Char
            shares = [0.22, 0.62, 0.16]
        elif ncols >= 6:                     # keyword audit: many narrow yes/no cols
            shares = [0.30] + [(0.70 / (ncols - 1))] * (ncols - 1)
        else:
            shares = [1.0 / ncols] * ncols
        for row in tbl.rows:
            for ci, cell in enumerate(row.cells):
                cell.width = Inches(usable_in * shares[ci])

    num_counter = 0
    for b in blocks:
        t = b["type"]
        if t in ("h1", "h2", "h3", "h4"):
            h = doc.add_heading("", level=int(t[1]))
            run = h.add_run(b["text"])
            run.bold = FORMAT["heading_bold"]
            run.font.name = FORMAT["body_font"]
            run.font.size = Pt(FORMAT["h%s_size" % t[1]])
            run.font.color.rgb = RGBColor.from_string(FORMAT["heading_color"])  # black, not Word blue
            num_counter = 0                  # reset numbered-list count at every heading
        elif t == "hr":
            pass  # v20.6.2: skip HR rendering -- 40 dashes were visible artifacts in final Doc
        elif t == "table":
            rows = b["rows"]
            if not rows:
                continue
            tbl = doc.add_table(rows=len(rows), cols=len(rows[0]))
            tbl.style = "Table Grid"
            for ri, row in enumerate(rows):
                for ci, cell in enumerate(row):
                    para = tbl.rows[ri].cells[ci].paragraphs[0]
                    _add_runs(para, cell)
                    if ri == 0:
                        for r in para.runs:
                            r.bold = True
            _set_widths(tbl, len(rows[0]))
        elif t == "callout":
            tbl = doc.add_table(rows=1, cols=1); tbl.style = "Table Grid"
            tbl.rows[0].cells[0].width = Inches(usable_in)
            _add_runs(tbl.rows[0].cells[0].paragraphs[0], b["text"], b.get("links"))
        elif t == "bullet":
            _add_runs(doc.add_paragraph(style="List Bullet"), b["text"], b.get("links"))
        elif t == "numbered":
            num_counter += 1                 # manual numbering, resets per section (fixes "FAQ starts at 10")
            pre = "%d. " % num_counter
            links = [(s + len(pre), e + len(pre), u) for (s, e, u) in (b.get("links") or [])]
            _add_runs(doc.add_paragraph(), pre + b["text"], links)
        else:  # para -- grey italic for QA explainers ("What this is:")
            p = doc.add_paragraph()
            _add_runs(p, b["text"], b.get("links"))
            if b["text"].lower().startswith("what this is"):
                for r in p.runs:
                    r.italic = True
                    r.font.color.rgb = RGBColor(0x66, 0x66, 0x66)
    doc.save(path)
    return path


def verify_rendered_docx(path):
    """POST-DELIVERY check (v13): read the RENDERED doc back and confirm it's not broken.
    Returns a list of failures; empty list = clean. The Google Docs path runs the same checks
    on the doc text read back via the API. This is the gap that let the v12 broken render ship."""
    from docx import Document
    d = Document(path)
    fails = []
    body = "\n".join(p.text for p in d.paragraphs)
    if "|" in body:
        fails.append("raw '|' pipes in body text (tables not built)")
    if "**" in body:
        fails.append("literal '**' markdown bold left unrendered")
    if "[" in body or "]" in body:
        fails.append("literal [ ] brackets survived")
    # v20.6.1: require pipe before dashes -- pure-dash lines come from rendered HR blocks (40 dashes), not table separators
    if re.search(r"^\s*\|\s*-{3,}", body, re.M):
        fails.append("markdown table separator row '|---|' rendered as text")
    if len(d.tables) == 0 and re.search(r"\bscore\b|\bweight\b", body, re.I):
        fails.append("scorecard present but ZERO real tables rendered")
    return fails


# ---------- Delivery: render .docx, then upload to Drive with native-Google-Doc convert ----------
# The Docs-API batchUpdate path was removed: it was an unfinished stub AND the API rejected the
# `pageless` field. The reliable path (confirmed working in production) is: render the .docx with
# render_to_docx() above -- which applies all heading/table/bold/list styling deterministically --
# then upload it to Drive with mimeType conversion to a native Google Doc, which PRESERVES that
# formatting. See sub-skills/upload_to_gdoc.py (delivery) and sub-skills/auth_helper.py (OAuth).
def run_gate(draft_path, brief=None, seo=None, corpus=None, topic=None, no_links=False, no_footer=False, run_folder=None):
    """STRUCTURAL ENFORCEMENT (v15, v20.5 updated). Run validate.py as subprocess.
    v20.5: section-sources.json retired; replaced by --corpus + --topic for the new heading-
    discipline checks (noun_floor, topic_anchor). corpus = comma-separated list of paths to
    competitor-*.md + ai-mode.json. topic = the article topic phrase.
    no_links: forwards --no-links so the pillar_link + gsc_used gates are skipped (batch mode).
    v22.1: run_folder defaults to the draft's parent dir so the run-scoped gates (lineage,
    research_execution_completeness, gsc_used, data_enrichment_consistency, dynamic length
    band) actually run -- they were silently no-opping without --run-folder."""
    import subprocess, json as _json, os as _os
    here = _os.path.dirname(_os.path.abspath(__file__))
    if not run_folder:
        run_folder = _os.path.dirname(_os.path.abspath(draft_path))
    cmd = ["python3", _os.path.join(here, "validate.py"), draft_path, "--json"]
    if brief:  cmd += ["--brief", brief]
    if seo:    cmd += ["--seo", seo]
    if corpus: cmd += ["--corpus", corpus]
    if topic:  cmd += ["--topic", topic]
    if run_folder: cmd += ["--run-folder", run_folder]
    _ai_mode = _os.path.join(run_folder, "ai-mode.json")
    if _os.path.exists(_ai_mode): cmd += ["--ai-mode", _ai_mode]
    if no_links: cmd += ["--no-links"]
    if no_footer: cmd += ["--no-footer"]
    out = subprocess.run(cmd, capture_output=True, text=True)
    try:
        r = _json.loads(out.stdout)
    except Exception:
        return False, ["validator did not return JSON: " + (out.stderr or out.stdout)[:200]]
    fails = [c["id"] for c in r.get("checks", []) if c["status"] == "FAIL"]
    return (r.get("overall") == "PASS", fails)


def deliver(md_path, doc_title, draft_path=None, brief=None, seo=None, corpus=None, topic=None, no_links=False, no_footer=False, run_folder=None):
    """Full delivery: GATE (validate, halt on FAIL) -> parse -> .docx -> verify -> upload-convert.
    No Google Doc is produced unless the gate passes. Returns the URL.
    v20.5: sources arg removed; corpus + topic now drive heading-discipline checks."""
    import tempfile, os as _os
    from upload_to_gdoc import upload_docx_as_gdoc
    # 1) un-ignorable content gate -- no Doc unless validate passes
    gate_target = draft_path or md_path
    ok, fails = run_gate(gate_target, brief, seo, corpus, topic, no_links=no_links, no_footer=no_footer, run_folder=run_folder)
    if not ok:
        raise SystemExit("DELIVERY BLOCKED -- validate.py FAILED: %s. Fix and re-run; no Doc created.\nIf the run is missing --corpus or --topic, pass them: --corpus competitor-1.md,...,ai-mode.json --topic \"<topic>\"" % ", ".join(fails))
    # 2) render + post-delivery render check
    raw_md = open(md_path, encoding="utf-8").read()
    raw_md = _strip_internal_appendix(raw_md)  # v20.6.2: strip Team-to-Supply before render
    blocks = parse_markdown_to_blocks(raw_md)
    tmp = _os.path.join(tempfile.gettempdir(), "geo-content-final.docx")
    render_to_docx(blocks, tmp)
    rfails = verify_rendered_docx(tmp)
    if rfails:
        raise SystemExit("DELIVERY HALTED -- broken render: " + "; ".join(rfails))
    return upload_docx_as_gdoc(tmp, doc_title)


def _selftest():
    md = ("# Does a Sit-stand Desk Reduce Back Pain?\n\n"
          "Yes, alternating between sitting and standing eases back strain for many people.\n\n"
          "## what's not covered, no matter the setup?\n\n"
          "See [standing desks](https://example.com/products/standing-desks/) for details. "
          "Source: [WHO] sets the guideline.\n")
    blocks = parse_markdown_to_blocks(md)
    # H1/H2 Title Cased (incl. hyphen segment + word after the comma)
    assert blocks[0]["type"] == "h1" and blocks[0]["text"] == "Does a Sit-Stand Desk Reduce Back Pain?", blocks[0]
    h2 = next(b for b in blocks if b["type"] == "h2")
    assert h2["text"] == "What's Not Covered, No Matter the Setup?", h2["text"]
    # link parsed, brackets stripped everywhere (grab the para that has the link)
    para = next(b for b in blocks if b["type"] == "para" and "standing desks" in b["text"])
    assert "[" not in para["text"] and "]" not in para["text"], para["text"]
    assert para["links"], "link range missing"
    assert para["text"].startswith("See standing desks for details. Source: WHO"), para["text"]
    # acronyms preserved, incl. inside a hyphenated word
    assert title_case("what is api in a saas product?") == "What is API in a SAAS Product?", title_case("what is api in a saas product?")
    assert title_case("how are usb and usb-c ports different?") == "How are USB and USB-C Ports Different?", title_case("how are usb and usb-c ports different?")
    # the meta/keyword tables are built from STRUCTURED cells (build_table), never a markdown
    # pipe-string -- so a literal '| Acme' inside a value stays in one cell:
    from docbuild import build_table
    t = build_table([["Asset", "Value", "Char"], ["Meta title", "What is X? | Acme", "50"]])
    assert t[1][1] == "What is X? | Acme", t[1]
    print("build_doc selftest: ALL PASS")


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if "--selftest" in sys.argv:
        _selftest(); return
    if "--verify" in sys.argv:           # post-delivery check on an existing .docx
        path = sys.argv[sys.argv.index("--verify") + 1]
        fails = verify_rendered_docx(path)
        print("post-delivery check:", "PASS -- clean render" if not fails else "FAIL -> " + "; ".join(fails))
        sys.exit(0 if not fails else 1)
    if not args:
        print(__doc__); return
    md = open(args[0], encoding="utf-8").read()
    blocks = parse_markdown_to_blocks(md)
    if "--docx" in sys.argv:
        out = sys.argv[sys.argv.index("--docx") + 1]
        render_to_docx(blocks, out)
        fails = verify_rendered_docx(out)
        print("wrote %s" % out)
        print("post-delivery check:", "PASS -- clean render" if not fails else "FAIL -> " + "; ".join(fails))
        return
    if "--dry-run" in sys.argv:
        for b in blocks:
            print(b["type"], "|", (b.get("text") or ("rows=%d" % len(b.get("rows", []))))[:90] if isinstance(b.get("text"), str) else b.get("rows"))
        print("\n[dry-run] %d blocks, no brackets survived, ready to render." % len(blocks))
        return
    def opt(flag):
        return sys.argv[sys.argv.index(flag) + 1] if flag in sys.argv else None
    title = opt("--title") or "Blog Article"
    # THE ONLY DELIVERY DOOR: this runs the validate gate (halts on FAIL) -> render -> verify -> upload.
    print(deliver(args[0], title, draft_path=opt("--draft"), brief=opt("--brief"),
                  seo=opt("--seo"), corpus=opt("--corpus"), topic=opt("--topic"),
                  no_links=("--no-links" in sys.argv), no_footer=("--no-footer" in sys.argv),
                  run_folder=opt("--run-folder")))


if __name__ == "__main__":
    main()
