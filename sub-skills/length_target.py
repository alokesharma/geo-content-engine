#!/usr/bin/env python3
"""
length_target.py (v21) -- compute an EVIDENCE-BASED length + coverage target from the SERP.

WHY: a fixed word cap made guide-style topics too thin (a "mediclaim policy" guide capped at
1200 words while competitors ran ~2000). This computes, from the competitors actually scraped
in Phase 1, the median clean-body word count and the median H2-section count, and turns them
into a length band + a coverage (section-count) target. validate.py reads the output instead of
a hard-coded cap. Length is meant to be a BYPRODUCT OF COVERAGE: hit the section target with
real, grounded sections -- never pad to a number.

INPUT  : a run folder containing competitor-N.md (H2 lists) and, when available,
         competitor-N-body.txt (clean article body saved by research-flow, boilerplate removed
         via trafilatura or the WebFetch markdown). Body text is what makes the word count honest
         -- raw page scrapes include nav/header/footer and inflate the count.
OUTPUT : writes length-target.json to the run folder and prints a summary.

USAGE  : python3 length_target.py runs/<run-id>
         (optional flags: --floor 800 --ceiling 2800 --band-low 0.85 --band-high 1.25)
"""
import json, os, re, sys, glob


def _median(nums):
    s = sorted(n for n in nums if n is not None)
    if not s:
        return None
    mid = len(s) // 2
    return s[mid] if len(s) % 2 else (s[mid - 1] + s[mid]) / 2.0


def _count_words(text):
    return len(re.findall(r"[A-Za-z']+", text or ""))


def _h2_count(md_text):
    """Count H2-level entries in a competitor-N.md. The scraper stores them either as '## ...'
    markdown headings OR as '- ...' bullets under a '## H2' block. Count both, drop obvious
    nav/boilerplate lines."""
    lines = md_text.splitlines()
    junk = re.compile(r"^(skip to|otp|enter otp|investor|contact|about us|quick links|careers|"
                      r"media|popular search|explore more|recent blog|follow us|email|disclaimer|"
                      r"faqs?|conclusion|key takeaways|related|learn about|get in touch|"
                      r"motor insurance|health insurance|other insurance|term insurance)\b", re.I)
    heads = []
    in_h2_block = False
    for ln in lines:
        s = ln.strip()
        if re.match(r"^##\s+H2\b", s, re.I) or s.lower() == "## h2":
            in_h2_block = True
            continue
        if re.match(r"^##\s+H[13]\b", s, re.I) or s.lower() in ("## h1", "## h3"):
            in_h2_block = False
            continue
        m = re.match(r"^##\s+(.*)", s)
        if m and not re.match(r"^H[123]\b", m.group(1), re.I):
            t = m.group(1).strip()
            if t and not junk.match(t):
                heads.append(t)
            continue
        if in_h2_block and s.startswith("- "):
            t = s[2:].strip()
            if t and not junk.match(t) and len(t.split()) <= 16:
                heads.append(t)
    # de-dupe
    seen, out = set(), []
    for h in heads:
        k = h.lower()
        if k not in seen:
            seen.add(k); out.append(h)
    return len(out)


def compute(folder, floor=800, ceiling=2800, band_low=0.85, band_high=1.25):
    comp_md = sorted(glob.glob(os.path.join(folder, "competitor-*.md")))
    word_counts, h2_counts, basis = [], [], []
    for md_path in comp_md:
        name = os.path.basename(md_path).replace(".md", "")
        body_path = os.path.join(folder, name + "-body.txt")
        wc = _count_words(open(body_path, encoding="utf-8").read()) if os.path.exists(body_path) else None
        hc = _h2_count(open(md_path, encoding="utf-8").read())
        word_counts.append(wc)
        h2_counts.append(hc)
        basis.append({"competitor": name, "body_words": wc, "h2_sections": hc,
                      "body_source": "competitor body txt" if wc is not None else "MISSING (no -body.txt)"})

    med_words = _median(word_counts)
    med_h2 = _median(h2_counts)

    if med_words is None:
        # no clean competitor body captured -> safe default band, flagged in the file
        target_low, target_high = 900, 1600
        note = "NO competitor body text captured -- using a safe default band (900-1600). Save competitor-N-body.txt in research-flow for an evidence-based target."
    else:
        target_low = max(floor, int(round(med_words * band_low)))
        target_high = min(ceiling, int(round(med_words * band_high)))
        note = "Evidence-based: band = [%.2f, %.2f] x median competitor body words (%d), clamped to [%d, %d]." % (
            band_low, band_high, int(med_words), floor, ceiling)

    section_target = int(round(med_h2)) if med_h2 else 5
    section_target = max(3, min(section_target, 9))   # never below 3, never above the hard H2 cap
    # per-section cap scales with the target so a long guide can have deeper sections,
    # but no single section can swallow the whole budget. Floor 120, ceiling 300.
    section_word_max = max(120, min(300, int(round(target_high / max(section_target, 3)))))

    out = {
        "word_target_low": target_low,
        "word_target_high": target_high,
        "word_floor": floor,
        "word_ceiling": ceiling,
        "section_target": section_target,
        "section_word_max": section_word_max,
        "median_competitor_words": med_words,
        "median_competitor_h2": med_h2,
        "note": note,
        "basis": basis,
    }
    json.dump(out, open(os.path.join(folder, "length-target.json"), "w", encoding="utf-8"), indent=2)
    return out


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        print(__doc__); sys.exit(2)
    folder = args[0].rstrip("/")
    if not os.path.isdir(folder):
        print("ERROR: not a folder: " + folder, file=sys.stderr); sys.exit(2)

    def opt(flag, default):
        return type(default)(sys.argv[sys.argv.index(flag) + 1]) if flag in sys.argv else default
    out = compute(folder, opt("--floor", 800), opt("--ceiling", 2800),
                  opt("--band-low", 0.85), opt("--band-high", 1.25))
    print("=== length-target.json -- %s ===" % folder)
    print("median competitor body words :", out["median_competitor_words"])
    print("median competitor H2 sections:", out["median_competitor_h2"])
    print("WORD TARGET BAND  : %d - %d  (hard floor %d / ceiling %d)" % (
        out["word_target_low"], out["word_target_high"], out["word_floor"], out["word_ceiling"]))
    print("SECTION TARGET    : %d H2 sections" % out["section_target"])
    print("PER-SECTION CAP   : %d words" % out["section_word_max"])
    print(out["note"])
    for b in out["basis"]:
        print("  -", b["competitor"], "| words:", b["body_words"], "| H2:", b["h2_sections"], "|", b["body_source"])


if __name__ == "__main__":
    main()
