#!/usr/bin/env python3
"""
validate.py - the geo-content-engine publish gate.

WHY THIS EXISTS: every fix used to live as prose the model graded itself on, so the same
issues (clock metaphors, stray brackets, jargon like "commencement"/"canonical") kept
recurring while the QA block claimed "pass". This script makes them PHYSICALLY UNABLE TO
SHIP: the recurring offenders are publish-blocking FAILs enforced as code, driven by a
team-editable rules file (sub-skills/style.json). When a reviewer flags something new,
they add ONE line to that JSON and it can never recur.

BUILT ON PROVEN TOOLS (not hand-rolled heuristics):
  - wordfreq  -> automatic rare/hard-word detection (zero maintenance; catches NEW hard words)
  - textstat  -> readability (Flesch, FK grade, sentence length)
  - style.json -> the house-style list the team owns (Vale-style, but zero-dependency)
  - (optional) Vale -> if the `vale` binary is on PATH it is also run as a bonus layer
Custom regex is kept ONLY for the domain-specific things no public tool does:
stray non-link brackets, merged-publisher citations, impossible metric labels, pillar link.

USAGE:
    python3 validate.py path/to/draft-voice-passed.md            # human report
    python3 validate.py path/to/draft-voice-passed.md --json     # JSON (skills read this)

EXIT CODE: 0 if zero FAILs, 1 if any FAIL. FLAGs never change the exit code.

DEPENDENCIES (install once):  pip install wordfreq textstat
If a library is missing the script does NOT silently pass: it marks that check SKIPPED and
prints an install hint, and any check it cannot run is reported, never assumed clean.
"""
import sys, os, re, json
# v20.6.1: textstat for H2 readability check; graceful if not installed
try:
    import textstat
except Exception:
    textstat = None

# v20.6 perf: pre-compile hot regexes at module load
_RX_COMPILED = True

HERE = os.path.dirname(os.path.abspath(__file__))
STYLE_PATH = os.path.join(HERE, "style.json")


def load_style():
    with open(STYLE_PATH, encoding="utf-8") as f:
        return json.load(f)


# Load the style dict once at import so the configurable site/brand values below are
# available to the module-level check regexes. Fall back to empty if the file is absent
# (e.g. tooling that imports this module without a style.json alongside it).
try:
    STYLE = load_style()
except Exception:
    STYLE = {}

# Configurable target site domain (used by the internal-link regexes) and brand name
# (used by the meta-title brand-suffix check). Override via env or style.json config.
SITE_DOMAIN = os.environ.get("SITE_DOMAIN") or STYLE.get("config", {}).get("site_domain", "example.com")
BRAND_NAME = os.environ.get("BRAND_NAME") or STYLE.get("config", {}).get("brand_name", "Acme")


def split_body_and_appendix(text):
    """The 'Team to supply' appendix legitimately contains brackets; exclude it from body checks."""
    m = re.search(r"(?im)^#{0,3}\s*team to supply", text)
    return (text[:m.start()], text[m.start():]) if m else (text, "")


def lines_matching(body, pattern, flags=re.I):
    hits = []
    for i, line in enumerate(body.splitlines(), 1):
        m = re.search(pattern, line, flags)
        if m:
            hits.append({"line": i, "match": m.group(0)[:60], "text": line.strip()[:150]})
    return hits


# ---------- domain-specific checks (no public tool does these) ----------
def check_brackets(body):
    hits = []
    for i, line in enumerate(body.splitlines(), 1):
        for m in re.finditer(r"\[[^\]\n]+\]", line):
            if line[m.end():m.end()+1] != "(":      # not a markdown link -> stray bracket
                hits.append({"line": i, "text": m.group(0)[:120]})
    return hits


def check_placeholder(body):
    return lines_matching(body, r"\[(brand internal data|tbd|needed|team to supply|placeholder)")


def check_merged_citation(body):
    """A citation must name ONE publisher. Flag two-source citations joined by / & 'and' 'via'
    INSIDE a 'Source:' run only. Restricted to Source: runs so descriptive internal-link anchors
    (e.g. 'switch from group health insurance to individual') are never false-flagged."""
    sep = re.compile(r"\s/\s|\s&\s|\s+and\s+|\s+via\s+|reported by|cited in|as reported", re.I)
    hits = []
    for i, line in enumerate(body.splitlines(), 1):
        for m in re.finditer(r"Source[:\)]?\s*\[?[^\]\n.]{0,140}", line, re.I):
            if sep.search(m.group(0)):
                hits.append({"line": i, "text": m.group(0).strip()[:140]})
    return hits


def first_sentence(body):
    for ln in body.splitlines():
        s = ln.strip()
        if not s or s.startswith("#") or s.startswith("|") or s.startswith(">"):
            continue
        if s.lower().startswith("last updated") or s.lower().startswith("topic:"):
            continue
        # skip a heading-style line (short, ends with '?') — that's the H1, not the lede
        if s.endswith("?") and len(s.split()) <= 13:
            continue
        return re.split(r"(?<=[.!?])\s", s)[0]
    return ""


def check_lede_opener(body, patterns):
    """BLUF: the article's first sentence must be the answer, not a scene-setter (canon B1)."""
    s = first_sentence(body)
    for pat in patterns:
        if re.search(pat, s.strip(), re.I):
            return [{"opener": s[:120], "issue": "scene-setter opener; sentence 1 must be the answer"}]
    return []


def check_long_paragraphs(body, limit=80):
    """FLAG prose paragraphs over `limit` words — break them into chunks (canon D6)."""
    hits = []
    for para in re.split(r"\n\s*\n", body):
        p = para.strip()
        if p.startswith(("#", "|", ">", "-", "*")) or p.lower().startswith("source"):
            continue
        wc = len(re.findall(r"[A-Za-z']+", p))
        if wc > limit:
            hits.append({"words": wc, "text": p[:90]})
    return hits


def check_source_gov(body, allow):
    """External-stat citations must come from a gov/IRDAI/authoritative source (canon C)."""
    hits = []
    for i, line in enumerate(body.splitlines(), 1):
        # only real citations: "Source:" with a colon, or "Source [" / "(Source:"
        for m in re.finditer(r"\(?Source[:\[]\s*\[?([^\]\n.]{2,90})", line, re.I):
            label = m.group(1).lower()
            if "brand internal" in label:
                continue
            if not any(a in label for a in allow):
                hits.append({"line": i, "source": m.group(1).strip()[:80],
                             "fix": "use a gov/IRDAI source, not a non-gov publisher"})
    return hits


def check_source_deeplink(body):
    """v22.1 FAIL. A Source citation link must point to a SPECIFIC page, never a domain homepage.
    The 2026-06-28 run shipped 'Source: [Ministry of Health](https://pmjay.gov.in/)' -- a bare
    root URL. Voice-pass check #12 has always required 'a specific page, not a generic homepage';
    this makes it machine-enforced. Only lines carrying a Source tag are checked, so internal
    site links (incl. the pillar) are unaffected."""
    hits = []
    for i, line in enumerate(body.splitlines(), 1):
        if not re.search(r"source\s*[:\[]", line, re.I):
            continue
        for m in re.finditer(r"\[[^\]]+\]\((https?://[^)\s]+)\)", line):
            url = m.group(1)
            path = re.sub(r"^https?://[^/]+", "", url)
            path = re.sub(r"[?#].*$", "", path).strip("/")
            if not path:
                hits.append({"line": i, "url": url[:100],
                             "fix": "cite the specific page (deep link), not the domain homepage"})
    return hits


def check_dangling_headings(body, words):
    """FLAG headings that lack standalone context (dangling 'this/these/the answer')."""
    hits = []
    for h in _headings(body)[1:]:
        hl = h.lower()
        for w in words:
            if w in hl:
                hits.append({"heading": h[:80], "dangling": w})
                break
    return hits


def check_regulator_named(body):
    """FLAG 'the regulator' used without naming IRDAI nearby (canon C7)."""
    hits = []
    for i, line in enumerate(body.splitlines(), 1):
        if re.search(r"\bthe regulator('s)?\b", line, re.I) and not re.search(r"irdai", line, re.I):
            hits.append({"line": i, "text": line.strip()[:120], "fix": "name IRDAI explicitly"})
    return hits


STOPWORDS = set("""a an the and or but if then else of to in on at by for with from into over under
again further once is are was were be been being have has had do does did this that these those it its
their there here you your yours we our ours they them he she his her as so than too very can will just
not no nor only own same s t don should now about above below up down out off no yes also which who whom
whose what when where why how all any both each few more most other some such per via
after before during while within without between because however also still even already
across whether time times since until though although against upgrade these""".split())

# v20.5: words that name the PRODUCT, not the SUBJECT. Subtracted from topic to get core nouns.
PRODUCT_NOUNS = {
    "group", "health", "insurance", "cover", "covers", "covering", "coverage",
    "car", "bike", "motor", "scooter", "wheeler", "vehicle",
    "life", "term", "pension", "retirement",
    "comprehensive", "party", "third",
    "plan", "plans", "policy", "policies", "scheme", "schemes",
    "india", "indian",
}

# v20.5: domains banned from internal links (forums/social). Any link to these = FAIL.
SOCIAL_FORUM_DOMAINS = {
    "reddit.com", "quora.com", "facebook.com", "fb.com", "youtube.com", "youtu.be",
    "x.com", "twitter.com", "instagram.com", "linkedin.com", "threads.net",
    "tiktok.com", "medium.com",
}



def _headings(body):
    """Section H1/H2 headings only. Excludes the FAQ block (its questions are not headings).
    Markdown headings first; fall back to short question-shaped lines for plain-text input."""
    # cut everything from the FAQ heading onward so FAQ questions aren't treated as headings
    m = re.search(r"(?im)^#{0,3}\s*frequently asked", body)
    scan = body[:m.start()] if m else body
    md = [re.sub(r"^#+\s*", "", ln).strip() for ln in scan.splitlines() if re.match(r"^#{1,3}\s", ln)]
    if md:
        return md
    out = []
    for ln in scan.splitlines():
        s = ln.strip()
        if s.endswith("?") and 0 < len(s.split()) <= 13:
            out.append(s)
    return out


def faq_block(body):
    """Return the FAQ section text (everything from 'Frequently asked' to the next H1/Key Takeaways)."""
    m = re.search(r"(?im)^#{0,3}\s*frequently asked.*$", body)
    if not m:
        return ""
    rest = body[m.end():]
    end = re.search(r"(?im)^#{0,3}\s*key takeaways", rest)
    return rest[:end.start()] if end else rest


def check_faq_answers(body):
    """FAQ answers must be 150-300 chars and BLUF (first sentence answers). FLAG out-of-band."""
    fb = faq_block(body)
    if not fb:
        return []
    hits = []
    # pair: a question line (ends ?) followed by answer text until the next question
    lines = [l.strip() for l in fb.splitlines() if l.strip()]
    i = 0
    while i < len(lines):
        q = lines[i]
        if q.endswith("?"):
            ans = []
            j = i + 1
            while j < len(lines) and not lines[j].endswith("?"):
                ans.append(lines[j]); j += 1
            atext = " ".join(ans).strip()
            atext = re.sub(r"^\d+[\.\)]\s*", "", atext)
            if atext:
                n = len(atext)
                if n < 150 or n > 300:
                    hits.append({"q": q[:60], "chars": n, "want": "150-300"})
            i = j
        else:
            i += 1
    return hits


def check_takeaways_leadin(body):
    """Key Takeaways bold lead-ins must be self-contained statements, not teaser fragments
    ('Yes, with limits', 'draws the line'). FLAG lead-ins that start Yes/No or are <4 words."""
    m = re.search(r"(?im)^#{0,3}\s*key takeaways", body)
    if not m:
        return []
    block = body[m.end():]
    end = re.search(r"(?im)^#{1,3}\s|^-{3,}\s*$|^next step|irdai registration", block)
    block = block[:end.start()] if end else block
    hits = []
    for ln in block.splitlines():
        s = re.sub(r"^[-*\d.)\s]+", "", ln).strip()
        if not s or not re.search(r"[A-Za-z]", s):       # skip blank / separator lines
            continue
        lead = re.split(r"[.:]", s, 1)[0].strip()        # the bold lead-in before the first . or :
        lead = lead.replace("*", "")
        words = lead.split()
        if not words:
            continue
        if re.match(r"(?i)^(yes|no)\b", lead) or len(words) < 4:
            hits.append({"leadin": lead[:50], "issue": "teaser fragment — make it a self-contained statement"})
    return hits


def check_bare_qualifier_headings(body):
    """A heading using a policy-type qualifier as a noun ('Comprehensive', 'Third-party',
    'Own-damage') must also name the product ('car insurance'/'policy'). 'What Won't
    Comprehensive Cover?' -> 'What Won't Comprehensive Car Insurance Cover?' (v15)."""
    hits = []
    for h in _headings(body)[1:]:
        if re.search(r"\b(comprehensive|third[\s-]?party|own[\s-]?damage)\b", h, re.I) and \
           not re.search(r"\b(insurance|policy|cover(age)?|plan)\b.*\b(insurance|policy|car)\b", h, re.I) and \
           not re.search(r"\bcar insurance\b|\binsurance\b", h, re.I):
            hits.append({"heading": h[:70], "fix": "name the product (e.g. 'Comprehensive Car Insurance')"})
    return hits


def check_third_person(body):
    """Body should be second person ('you/your'), not 'the reader' / 'readers' (v15 voice)."""
    return lines_matching(body, r"\bthe reader\b|\breaders\b")


def check_naked_url(body):
    """A bare http(s):// in body that is NOT inside a markdown link [..](url) = FAIL."""
    hits = []
    for i, line in enumerate(body.splitlines(), 1):
        for m in re.finditer(r"https?://\S+", line):
            # inside a markdown link if preceded by ']('
            pre = line[max(0, m.start() - 2):m.start()]
            if pre != "](":
                hits.append({"line": i, "url": m.group(0)[:60]})
    return hits


def check_bluf_yesno(body):
    """If the H1 is a yes/no question (Does/Is/Can/Will/Should...?), the lede's first sentence
    must open with Yes/No (B3, v13)."""
    heads = _headings(body)
    if not heads:
        return []
    h1 = heads[0].strip()
    if not re.match(r"(?i)^(does|is|are|can|will|should|do|did|has|have|was|were)\b", h1) or not h1.endswith("?"):
        return []
    s = first_sentence(body)
    if not re.match(r"(?i)^(yes|no)\b", s.strip()):
        return [{"h1": h1[:70], "lede": s[:90], "issue": "yes/no question; lede must open with Yes/No"}]
    return []


def check_meta_description(seo_text, h1):
    """Meta description = a direct answer: must NOT restate the H1 question, must NOT start Yes/No (v13)."""
    desc = None
    for cells in _md_table_rows(seo_text):
        if cells and cells[0].lower().startswith("meta desc") and len(cells) > 1:
            desc = cells[1]; break
    if not desc:
        return []
    hits = []
    h1core = re.sub(r"[?\s]+$", "", h1).strip().lower()
    if h1core and h1core[:40] in desc.lower():
        hits.append({"text": "meta description restates the H1 question: " + desc[:80]})
    if re.match(r"(?i)^(yes|no)\b", desc.strip()):
        hits.append({"text": "meta description must not start with Yes/No: " + desc[:80]})
    return hits



def check_interlink_position(body):
    """The first internal site link must not sit in the lede / first 2 paragraphs (B4/v11)."""
    paras = [p for p in re.split(r"\n\s*\n", body) if p.strip()]
    # drop H1 + 'last updated' lead lines from the count
    body_paras = [p for p in paras if not p.strip().endswith("?") or len(p.split()) > 14]
    body_paras = [p for p in body_paras if not p.lower().startswith("last updated")]
    for idx, p in enumerate(body_paras[:2]):
        if re.search(r"\]\(https?://(www\.)?" + re.escape(SITE_DOMAIN), p, re.I):
            return [{"para": idx + 1, "text": p[:90], "fix": "move the first site link to para 3+"}]
    return []


def _toks(s):
    return set(w for w in re.findall(r"[a-z]+", s.lower()) if w not in STOPWORDS and len(w) > 2)


def check_h1_h2_dup(body):
    """No H2 may restate/near-duplicate the H1 (Jaccard > 0.6 of meaningful tokens)."""
    heads = _headings(body)
    if len(heads) < 2:
        return []
    h1 = _toks(heads[0])
    hits = []
    for h in heads[1:]:
        ht = _toks(h)
        if not h1 or not ht:
            continue
        j = len(h1 & ht) / len(h1 | ht)
        if j > 0.6:
            hits.append({"h1": heads[0][:70], "h2": h[:70], "similarity": round(j, 2)})
    return hits


def check_word_repetition(body, glossary, rep_allow=None, threshold=8):
    """FLAG meaningful content words used too often (e.g. 'pool' x11). Excludes stopwords,
    glossary/domain terms, the common insurance vocabulary in repetition_allow, and the H1
    topic tokens (unavoidable core nouns) so only genuine outliers surface."""
    import collections
    heads = _headings(body)
    topic = _toks(heads[0]) if heads else set()
    allow = set(g.lower() for g in glossary) | set((r.lower() for r in (rep_allow or []))) | topic
    text = re.sub(r"\[[^\]]+\]\([^)]+\)", " ", body)
    words = [w for w in re.findall(r"[A-Za-z]{4,}", text)]
    counts = collections.Counter(w.lower() for w in words)
    hits = []
    for w, n in counts.most_common():
        if n <= threshold:
            break
        if w in STOPWORDS or w in allow:
            continue
        hits.append({"word": w, "count": n})
    return hits


def check_metric_label(body):
    hits = []
    for m in re.finditer(r"(\d{2,3}(?:\.\d+)?)\s*%", body):
        if float(m.group(1)) > 100:
            window = body[max(0, m.start()-60): m.end()+60].lower()
            if "settlement ratio" in window:
                hits.append({"value": m.group(0), "context": window.strip()[:140]})
    return hits


def check_pillar(body, verticals):
    for v in verticals:
        if re.search(r"\]\(https?://(www\.)?" + re.escape(SITE_DOMAIN) + r"/%s/?\)" % re.escape(v), body, re.I):
            return True
    return False


# ---------- house-style checks (driven by style.json) ----------
def check_ban_swaps(body, swaps):
    hits = []
    low = body.lower()
    for word, swap in swaps.items():
        for m in re.finditer(r"\b" + re.escape(word.lower()) + r"\b", low):
            ln = body.count("\n", 0, m.start()) + 1
            hits.append({"line": ln, "word": word, "use_instead": swap})
            break  # one hit per word is enough to block
    return hits


def check_patterns(body, patterns):
    hits = []
    for pat in patterns:
        hits += lines_matching(body, pat)
    return hits


def check_ban_phrases(body, phrases):
    hits = []
    for ph in phrases:
        if ph.lower() in body.lower():
            hits.append({"phrase": ph})
    return hits


# ---------- anti-AI writing tells (Wikipedia WP:AISIGNS) — anti-ai fork ----------
def check_literal_chars(body, chars):
    """Literal AI-tell characters (em/en dash, curly quotes) — FAIL.
    WP:AIDASH (em/en dash) and WP:AICURLY (curly quotes/apostrophes). One hit per line."""
    hits = []
    for i, line in enumerate(body.splitlines(), 1):
        for ch in chars:
            if ch in line:
                hits.append({"line": i, "char": ch, "text": line.strip()[:120]})
                break
    return hits


def check_rule_of_three(body):
    """Conservative triplet detector: 'word, word, and word' adjective-ish runs (WP:RO3).
    FLAG only — fine occasionally, a tell when frequent. Expect some noise on real lists."""
    hits = []
    # lowercase-only triplets — adjective/descriptor runs. Skips proper-noun lists
    # like "ADIP, RBSK, and PM-JAY" (acronyms/Title-Case), which are legitimate.
    pat = r"\b([a-z]+(?:ly)?), ([a-z]+(?:ly)?),? and ([a-z]+(?:ly)?)\b"
    for m in re.finditer(pat, body):
        ln = body.count("\n", 0, m.start()) + 1
        hits.append({"line": ln, "text": m.group(0)})
    return hits


def check_vague_attribution(body, patterns):
    """v22.1: vague-attribution FAILs only when the line carries no real citation. A line with a
    Source tag AND a markdown link ('Research shows X. Source: [IRDAI](url)') is legitimately
    cited -- rule #34 explicitly allows sourced stats, so it must not block. Unsourced weasel
    ('experts say', bare 'studies show') still FAILs."""
    hits = []
    for i, line in enumerate(body.splitlines(), 1):
        if re.search(r"source\s*[:\[]", line, re.I) and re.search(r"\[[^\]]+\]\(https?://[^)]+\)", line):
            continue                                     # properly cited -- exempt
        for pat in patterns:
            m = re.search(pat, line, re.I)
            if m:
                hits.append({"line": i, "match": m.group(0)[:60], "text": line.strip()[:150]})
                break
    return hits


# Example aggregator names (insurance vertical) — third-party recaps, not primary sources.
# Replace with the aggregator/competitor names relevant to your own vertical.
AGGREGATORS = ["algates", "policybazaar", "coverfox", "policyx", "insurancedekho",
               "bankbazaar", "paisabazaar", "ditto"]


def check_sales(body, patterns):
    """Promotional/sell register — FAIL (educate, don't sell)."""
    return check_patterns(body, patterns)


def check_source_words(body, words):
    """Research-mechanism words must never appear in body prose (Reddit, Quora, Ahrefs...)."""
    hits = []
    for i, line in enumerate(body.splitlines(), 1):
        for w in words:
            if re.search(r"\b" + re.escape(w) + r"\b", line, re.I):
                hits.append({"line": i, "word": w, "text": line.strip()[:120]})
    return hits


def check_brand_data_tag(body):
    """Inline '(Source: brand internal data)' tag in prose reads bad — FAIL (weave it in instead)."""
    return lines_matching(body, r"\(?\s*source:\s*brand internal data\s*\)?")


def _title_case_ok(heading):
    """True if heading follows Title Case: principal words capitalised, short connectors lower
    (unless first/last). Allows ALLCAPS acronyms (IRDAI, PED, NCB, CNG, RC, AC, IDV, OPD)."""
    minor = {"a", "an", "the", "and", "but", "or", "nor", "for", "of", "in", "on", "at",
             "to", "by", "as", "is", "are", "vs", "with", "from", "into", "per", "via"}
    words = heading.split()
    for idx, w in enumerate(words):
        # each hyphen segment is title-cased ("Non-Accident", not "Non-accident")
        for seg in w.split("-"):
            core = re.sub(r"[^A-Za-z]", "", seg)
            if not core:
                continue
            if core.isupper() and len(core) > 1:      # acronym, fine
                continue
            low = core.lower()
            first_last = (idx == 0 or idx == len(words) - 1)
            if low in minor and not first_last:
                if core[0].isupper():
                    return False                       # minor word wrongly capitalised
            else:
                if not core[0].isupper():
                    return False                       # principal word not capitalised
    return True


def check_title_case(body):
    """Every H2 should be Title Case (canon B2)."""
    hits = []
    for h in _headings(body)[1:]:                     # skip H1
        if not _title_case_ok(h):
            hits.append({"heading": h[:80]})
    return hits


def check_authority_overcite(body, maximum):
    """Cap how often a single regulator name is cited (IRDAI over-citation) — FLAG."""
    n = len(re.findall(r"\birdai\b", body, re.I))
    return [{"name": "IRDAI", "count": n, "max": maximum}] if n > maximum else []


def check_source_quality(body):
    """FLAG citations that attribute a regulator figure to a third-party aggregator's SUMMARY
    instead of the primary source (e.g. 'Algates Insurance summary of IRDAI Annual Report')."""
    hits = []
    for i, line in enumerate(body.splitlines(), 1):
        for m in re.finditer(r"\[([^\]\n]+)\]", line):
            anchor = m.group(1).lower()
            if "summary of" in anchor or any(a in anchor for a in AGGREGATORS):
                if re.search(r"irdai|annual report|gi council|regulator|circular", anchor):
                    hits.append({"line": i, "text": m.group(1)[:120],
                                 "fix": "cite the primary source (e.g. IRDAI) directly, not an aggregator summary"})
    return hits


def _md_table_rows(text):
    rows = []
    for ln in text.splitlines():
        if ln.count("|") >= 2 and not re.match(r"^\s*\|?[\s:-]+\|", ln):
            cells = [c.strip() for c in ln.strip().strip("|").split("|")]
            rows.append(cells)
    return rows


def check_meta_title(seo_text, h1):
    """Meta title must be the H1 (minus '?') minimally trimmed, with no brand suffix — never
    reworded. FAIL if it contains a content word not in the H1, or a stray backslash."""
    hits = []
    brand = BRAND_NAME.lower()
    title = None
    for cells in _md_table_rows(seo_text):
        if cells and cells[0].lower().startswith("meta title") and len(cells) > 1:
            title = cells[1]
            break
    if not title:
        return [{"text": "meta title row not found in seo file"}]
    if "\\" in title:
        hits.append({"text": "stray backslash in meta title: " + title[:80]})
    if re.search(r"\b" + re.escape(brand) + r"\b", title, re.I):
        hits.append({"text": "meta title must NOT contain '%s' (no brand suffix): %s" % (BRAND_NAME, title[:80])})
    new = _toks(title) - _toks(h1) - {brand}
    if new:
        hits.append({"text": "meta title introduces words not in the H1 (reworded): %s" % sorted(new),
                     "title": title[:90], "h1": h1[:90]})
    # if the H1 is a question, the title must end with '?'
    if h1.strip().endswith("?") and not title.strip().endswith("?"):
        hits.append({"text": "topic is a question; meta title must end with '?': " + title[:80]})
    return hits


def check_grounding(body, brief_text):
    """v12 grounding gate (numeric layer): every specific number in the body (₹ amounts,
    percentages, 'N months/years/days') must trace to research-brief.md OR carry a Source: tag.
    A number with neither = 'model-recall — verify or source'. (General prose isn't checked;
    numbers are the most verifiable proxy for 'specific claim'.)"""
    brief = re.sub(r"[,\s]", "", brief_text.lower())   # normalise for loose number matching
    hits = []
    for i, line in enumerate(body.splitlines(), 1):
        if re.search(r"source\s*[:\[]|brand internal", line, re.I):
            continue                                    # the sentence cites a source already
        for m in re.finditer(r"(?:₹\s?[\d,]+|\b\d{1,3}(?:,\d{2,3})*(?:\.\d+)?\s?%?|\b\d+\s?(?:months|years|days|crore|lakh))", line, re.I):
            window = line[max(0, m.start()-22):m.start()].lower()
            if re.search(r"\b(registration|reg|no\.?|valid|updated|as of|©|circular)\b", window) or \
               re.match(r"^(19|20)\d\d$", re.sub(r"\D", "", m.group(0))):
                continue                                  # skip reg numbers, dates, years (v15)
            tok = re.sub(r"[,\s₹%]", "", m.group(0).lower())
            tok = re.sub(r"(months|years|days|crore|lakh)", "", tok)
            if len(tok) < 2:                            # skip trivial 1-digit (e.g., "day 1")
                continue
            if tok not in brief:
                hits.append({"line": i, "number": m.group(0).strip(),
                             "issue": "not found in research-brief and no Source tag"})
    # de-dup by number
    seen, out = set(), []
    for h in hits:
        if h["number"] not in seen:
            seen.add(h["number"]); out.append(h)
    return out[:15]


def grounding_ratio(body, brief_text):
    """Return (grounded, total) for specific numbers: how many trace to the brief or carry a source.
    Floor lives in style.json config (grounding_floor, default 0.70). Below floor -> data is NOT
    the majority influence -> the run should reject (Part C)."""
    brief = re.sub(r"[,\s]", "", brief_text.lower())
    total = grounded = 0
    for line in body.splitlines():
        has_src = bool(re.search(r"source\s*[:\[]|brand internal", line, re.I))
        for m in re.finditer(r"(?:₹\s?[\d,]+|\b\d{1,3}(?:,\d{2,3})*(?:\.\d+)?\s?%?|\b\d+\s?(?:months|years|days|crore|lakh))", line, re.I):
            window = line[max(0, m.start()-22):m.start()].lower()
            if re.search(r"\b(registration|reg|no\.?|valid|updated|as of|©|circular)\b", window) or \
               re.match(r"^(19|20)\d\d$", re.sub(r"\D", "", m.group(0))):
                continue                                  # skip reg numbers, dates, years (v15)
            tok = re.sub(r"[,\s₹%]", "", m.group(0).lower())
            tok = re.sub(r"(months|years|days|crore|lakh)", "", tok)
            if len(tok) < 2:
                continue
            total += 1
            if has_src or tok in brief:
                grounded += 1
    return grounded, total


def check_keyword_trace(seo_text, brief_text):
    """Every keyword in the placement-audit table must appear VERBATIM somewhere in the brief
    (real Ahrefs/PAA/related-search data). A keyword not found = fabricated = FAIL (#62)."""
    blow = brief_text.lower()
    hits = []
    in_audit = False
    for cells in _md_table_rows(seo_text):
        first = cells[0].lower()
        if "keyword" in first and len(cells) > 3:
            in_audit = True
            continue
        if in_audit and cells and cells[0]:
            kw = re.sub(r"\(.*?\)", "", cells[0]).strip().lower()
            if len(kw) < 4:
                continue
            if kw not in blow:
                hits.append({"keyword": cells[0][:80], "issue": "not found verbatim in research-brief (possibly synthesized)"})
    return hits


# ---------- proven-tool checks ----------
def check_hard_words_wordfreq(body, cfg, glossary):
    try:
        from wordfreq import zipf_frequency
    except Exception:
        return None, "wordfreq not installed (pip install wordfreq) - rare-word check SKIPPED"
    text = re.sub(r"\[[^\]]+\]\([^)]+\)", " ", body)
    # Exclude markdown table rows (lines starting with '|') from the prose hard-words check —
    # tables are quoted/structured comparison data, not authored prose, and are already excluded
    # from the word-count checks. Comparison tables stay concise without tripping this.
    text = re.sub(r"(?m)^\s*\|.*$", " ", text)
    text = re.sub(r"[#>*`|]", " ", text)
    allow = set(g.lower() for g in glossary)
    seen, flagged = set(), []
    for w in re.findall(r"[A-Za-z][A-Za-z'-]+", text):
        lw = w.lower()
        if lw in seen or lw in allow or len(lw) < cfg["wordfreq_min_len"]:
            continue
        seen.add(lw)
        if zipf_frequency(lw, "en") < cfg["wordfreq_min_zipf"]:   # lower zipf = rarer/harder
            flagged.append({"word": lw, "zipf": round(zipf_frequency(lw, "en"), 2)})
    flagged.sort(key=lambda x: x["zipf"])
    return flagged[:25], "wordfreq zipf<%s (rarer = harder)" % cfg["wordfreq_min_zipf"]


def check_readability(body, cfg):
    try:
        import textstat
    except Exception:
        return {"status": "SKIPPED", "reason": "textstat not installed (pip install textstat)"}
    plain = re.sub(r"\[[^\]]+\]\([^)]+\)", " ", body)
    plain = re.sub(r"(?m)^\s*[#>|].*$", " ", plain)
    flesch = textstat.flesch_reading_ease(plain)
    fk = textstat.flesch_kincaid_grade(plain)
    sents = [s for s in re.split(r"[.!?]+", plain) if s.strip()]
    asl = (len(re.findall(r"[A-Za-z']+", plain)) / len(sents)) if sents else 0
    dc = None
    try:
        dc = round(textstat.dale_chall_readability_score(plain), 1)
    except Exception:
        pass
    # v20 — readability is a FAIL gate (not FLAG): FK > readability_fk_pass OR Flesch < readability_flesch_pass
    # both block publish. The CMO's "too complex" complaint required this teeth.
    if flesch >= cfg["readability_flesch_pass"] and fk <= cfg["readability_fk_pass"]:
        status, verdict = "PASS", "ship-ready"
    else:
        status, verdict = "FAIL", "too difficult — Flesch %.1f (need >=%d), FK %.1f (need <=%d)" % (
            flesch, cfg["readability_flesch_pass"], fk, cfg["readability_fk_pass"])
    if asl > cfg["max_avg_sentence_len"]:
        status, verdict = "FAIL", "avg sentence length > %d words" % cfg["max_avg_sentence_len"]
    return {"status": status, "flesch": round(flesch, 1), "fk_grade": round(fk, 1),
            "dale_chall": dc, "avg_sentence_len": round(asl, 1), "verdict": verdict}


def run_vale(path):
    """Optional bonus layer: run the `vale` binary if it is installed. Never required."""
    import shutil, subprocess
    if not shutil.which("vale"):
        return {"status": "SKIPPED", "reason": "vale binary not on PATH (optional)"}
    try:
        out = subprocess.run(["vale", "--output=JSON", path], capture_output=True, text=True, timeout=60)
        data = json.loads(out.stdout or "{}")
        n = sum(len(v) for v in data.values())
        return {"status": "FLAG" if n else "PASS", "issues": n}
    except Exception as e:
        return {"status": "SKIPPED", "reason": "vale run failed: %s" % e}


# ---------- v18: instruction-rules turned into hard checks ----------
def check_product_name_trim(body, trims):
    """v18 FAIL. A heading must use the FULL product name, not a trimmed shorthand. The GMC
    blog shipped 'How Does Group Cover Handle PEDs?' / 'When Do Group Plans Cover...' — those
    must read 'Group Health Insurance'. Driven by style.json product_name_trims so the
    team adds the shorthand they keep seeing + the correct full name (no Python edit)."""
    hits = []
    for h in _headings(body):                       # H1+H2+H3, FAQ questions already excluded
        for t in trims:
            m = re.search(t["pattern"], h, re.I)
            if m:
                hits.append({"heading": h[:80], "trimmed": m.group(0),
                             "use_instead": t.get("fix", "the full product name")})
                break                               # one hit per heading is enough
    return hits


def _intro_text(body):
    """The intro = prose between the H1 and the first H2 (skips H1, 'Last updated', tables)."""
    lines = body.splitlines()
    h1 = next((i for i, ln in enumerate(lines) if re.match(r"^#{1,3}\s", ln)), None)
    if h1 is None:
        return ""
    out = []
    for ln in lines[h1 + 1:]:
        if re.match(r"^#{1,3}\s", ln):
            break
        s = ln.strip()
        if not s or s.startswith(("|", ">", "-", "*")):
            continue
        if s.lower().startswith(("last updated", "topic:")):
            continue
        out.append(s)
    return " ".join(out)


def _sentences(text):
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]


def check_intro_length(body, max_sentences):
    """v18 FLAG. The opening must be tight — <= `max_sentences` sentences (config)."""
    intro = _intro_text(body)
    if not intro:
        return []
    n = len(_sentences(intro))
    return [{"sentences": n, "limit": max_sentences, "text": intro[:120]}] if n > max_sentences else []


def _prose_paragraphs(body):
    """Body prose paragraphs only: skip headings, tables, blockquotes, lists, Source lines.
    Link anchors are unwrapped so word counts reflect readable text."""
    out = []
    for para in re.split(r"\n\s*\n", body):
        p = para.strip()
        if not p or p.startswith(("#", "|", ">")):
            continue
        if re.match(r"^\s*[-*]\s", p) or re.match(r"^\s*\d+[\.\)]\s", p) or p.lower().startswith("source"):
            continue
        out.append(re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", p))
    return out


def check_sentence_length(body, cap):
    """v18 FLAG. Hard cap: no single prose sentence may exceed `cap` words (config
    sentence_hard_cap). Complements the readability AVERAGE check with a per-sentence ceiling."""
    hits = []
    for p in _prose_paragraphs(body):
        for s in _sentences(p):
            wc = len(re.findall(r"[A-Za-z']+", s))
            if wc > cap:
                hits.append({"words": wc, "cap": cap, "text": s[:110]})
    return hits[:12]


def _faq_questions(body):
    fb = faq_block(body)
    return [l.strip() for l in fb.splitlines() if l.strip().endswith("?")] if fb else []


def check_presence(body, skip_footer=False):
    """v18 FAIL. Mandatory structural elements — each missing one blocks publish:
    a Key Takeaways section, an IRDAI registration footer, and a 'Last updated' line.
    skip_footer: batch mode where the IRDAI footer is intentionally removed; KT + Last
    updated stay required."""
    hits = []
    if not re.search(r"(?im)^#{0,3}\s*key takeaways", body):
        hits.append({"missing": "Key Takeaways section"})
    if not skip_footer and not re.search(r"irdai\s+registration|irdai\s+reg(istration)?\.?\s*no", body, re.I):
        hits.append({"missing": "IRDAI registration footer"})
    if not re.search(r"(?im)^\s*\**\s*last updated", body):
        hits.append({"missing": "'Last updated' line"})
    return hits


def check_takeaways_terminal(body):
    """v18 FLAG. Key Takeaways should be the FINAL block. FLAG if a substantive section
    heading (not a disclaimer/registration footer) appears after it."""
    m = re.search(r"(?im)^#{0,3}\s*key takeaways", body)
    if not m:
        return []
    for ln in body[m.end():].splitlines():
        if re.match(r"^#{1,2}\s", ln):
            txt = re.sub(r"^#+\s*", "", ln).strip().lower()
            if any(k in txt for k in ("irdai", "registration", "disclaimer", "team to supply")):
                continue
            return [{"heading": ln.strip()[:60],
                     "issue": "a section follows Key Takeaways — KT should be the final block"}]
    return []


def check_structure_variety(body, max_prose_run=3):
    """v22.4 FLAG (user request — advisory, never blocks). Readers scan better when sections
    vary their tool (bullets, numbered steps, tables, callouts) where the content supports it.
    Fires when (a) `max_prose_run`+ consecutive body H2 sections are prose-only, or (b) the
    whole body has no list, table, or callout at all. FAQ + Key Takeaways excluded (fixed
    formats). Prose can be the right call — the reviewer decides; that is why this is a FLAG."""
    m_faq = re.search(r"(?im)^#{0,3}\s*frequently asked", body)
    m_kt  = re.search(r"(?im)^#{0,3}\s*key takeaways", body)
    cut = min([x.start() for x in (m_faq, m_kt) if x is not None] or [len(body)])
    scope = body[:cut]
    parts = re.split(r"(?m)^(##\s+.*)$", scope)
    sections = []                                    # (heading, has_nonprose_element)
    for i in range(1, len(parts), 2):
        h = parts[i].strip().lstrip("#").strip()
        b = parts[i + 1] if i + 1 < len(parts) else ""
        nonprose = bool(re.search(r"(?m)^\s*([-*]\s|\d+[\.\)]\s|\||>)", b))
        sections.append((h, nonprose))
    if not sections:
        return []
    hits = []
    best, best_heads, cur, cur_heads = 0, [], 0, []
    for h, np_ in sections:
        if np_:
            cur, cur_heads = 0, []
        else:
            cur += 1
            cur_heads = cur_heads + [h]
            if cur > best:
                best, best_heads = cur, list(cur_heads)
    if best >= max_prose_run:
        hits.append({"consecutive_prose_only_sections": best,
                     "headings": [h[:60] for h in best_heads],
                     "fix": "%d prose-only sections in a row — where the content supports it, use a bullet list (parallel items), numbered steps (sequence), a small table (comparison) or a callout. Keep prose where it is genuinely the right tool." % best})
    if not any(np_ for _, np_ in sections):
        hits.append({"text": "no list, table, or callout anywhere in the article body",
                     "fix": "add at least one non-prose element where the content supports it (steps, parallel items, or a comparison)"})
    return hits


def check_callout_budget(body, maximum):
    """v18 FLAG. Count callout/note boxes (markdown blockquotes). Too many (> `maximum`) or two
    back-to-back boxes read as clutter — surface both."""
    lines = body.splitlines()
    groups, cur = [], None
    for i, ln in enumerate(lines):
        if ln.lstrip().startswith(">"):
            cur = [i, i] if cur is None else [cur[0], i]
        elif cur is not None:
            groups.append(tuple(cur)); cur = None
    if cur is not None:
        groups.append(tuple(cur))
    hits = []
    if len(groups) > maximum:
        hits.append({"boxes": len(groups), "max": maximum})
    for a, b in zip(groups, groups[1:]):
        if all(lines[x].strip() == "" for x in range(a[1] + 1, b[0])):
            hits.append({"lines": "%d & %d" % (a[0] + 1, b[0] + 1),
                         "issue": "two callout boxes are adjacent — separate them with prose"})
    return hits


def check_data_vintage(body):
    """v18 FLAG. Every external statistic (a line carrying a 'Source:' tag and a figure such as
    %, crore, lakh, ratio or ₹) must state its data vintage — a year (e.g. 2024) on the line."""
    hits = []
    for i, line in enumerate(body.splitlines(), 1):
        if not re.search(r"source\s*[:\[]", line, re.I):
            continue
        if not re.search(r"%|crore|lakh|ratio|₹|\bpercent\b", line, re.I):
            continue
        if re.search(r"\b(19|20)\d\d\b", line):
            continue
        hits.append({"line": i, "text": line.strip()[:120], "fix": "state the data year (e.g. 2024)"})
    return hits


# ---------- v20.4: heading discipline + content quality (7 checks) ----------
def check_h2_h2_duplicate(body, threshold=0.6, topic=""):
    """v20.4 FAIL. No two body H2s may share more than `threshold` noun overlap (Jaccard).
    Kills v20.3's twin 'When Does GHI Pay a Pre-Existing Claim?' + 'How GHI Pays Pre-Existing
    Claims?' the moment they appear. FAQ + Key Takeaways exempt."""
    topic_core = _topic_noun_set(topic) if topic else set()  # v20.5: subtract topic nouns
    heads = [h for h in _headings(body)[1:]
             if not re.search(r"frequently asked|key takeaways|team to supply", h, re.I)]
    hits = []
    for i in range(len(heads)):
        a = _heading_nouns(heads[i]) - topic_core
        for j in range(i + 1, len(heads)):
            b = _heading_nouns(heads[j]) - topic_core
            if not a or not b:
                continue
            jac = len(a & b) / len(a | b)
            if jac > threshold:
                hits.append({"h2_a": heads[i][:70], "h2_b": heads[j][:70],
                             "jaccard": round(jac, 2),
                             "fix": "two H2s on the same sub-topic — merge into one section, or repurpose the second"})
    return hits


def check_heading_content_mismatch(body):
    """v20.4 FAIL. A 'When/How/Why' question heading's first content block must NOT be a 3+ row
    table — tables belong in comparison-headed sections. Catches v20.3's '§2 When Does GHI
    Pay...' opening with a group-vs-retail comparison table."""
    parts = re.split(r"(?m)^(##\s+.*)$", body)
    hits = []
    for i in range(1, len(parts), 2):
        h = parts[i].strip().lstrip("#").strip()
        if not re.match(r"(?i)^(when|how|why)\b", h):
            continue
        if re.search(r"frequently asked|key takeaways|team to supply", h, re.I):
            continue
        b = parts[i + 1] if i + 1 < len(parts) else ""
        # find first non-blank, non-prose block
        rows = 0
        for ln in b.splitlines():
            if ln.strip().startswith("|") and ln.count("|") >= 2:
                rows += 1
            elif rows > 0:
                break
        if rows >= 3:
            hits.append({"heading": h[:80], "table_rows": rows,
                         "fix": "comparison table under a '%s' heading — move table to a comparison-headed section" % h.split()[0]})
    return hits


def check_concrete_example(body):
    """v20.4 FAIL. The article body must contain at least one CONCRETE example — either a rupee
    figure (₹) anywhere in body prose, OR a numbered/lettered scenario ('₹5 lakh', '30 days',
    'For example...'). Catches v20.3's all-abstract body that read fact-correct but never gave
    the reader a stake-anchor."""
    # body scope = exclude FAQ + KT + headings + tables
    m_faq = re.search(r"(?im)^#{0,3}\s*frequently asked", body)
    m_kt  = re.search(r"(?im)^#{0,3}\s*key takeaways", body)
    cut = min([x.start() for x in (m_faq, m_kt) if x is not None] or [len(body)])
    scope = body[:cut]
    scope = re.sub(r"(?m)^\s*[#>|].*$", " ", scope)        # strip headings/tables/blockquotes
    # accept any of: ₹ symbol, 'Rs.', a scenario marker, or "for example/instance"
    if re.search(r"₹|\brs\.?\s*\d|\bfor (example|instance)\b|\bsuppose\b|\bimagine\b", scope, re.I):
        return []
    return [{"text": "no concrete example found in body prose",
             "fix": "add at least one ₹ figure (e.g. '₹5 lakh sum insured') or a worked scenario — abstract claims need a stake-anchor"}]


def check_intro_substantive_v204(body, min_second_words):
    """v20.4 FAIL — replaces v20.2's check_intro_substantive. The 2nd sentence must:
       1. be at least `min_second_words` words long (the v20.2 rule),
       2. NOT start with a coordinating conjunction (so/but/and/or/yet/for/nor),
       3. contain at least 1 noun from the H1.
    Stops v20.3's trailing 'so what your colleague gets and what you get can look different.'"""
    intro = _intro_text(body)
    if not intro:
        return []
    sents = _sentences(intro)
    if len(sents) < 2:
        return [{"sentences": len(sents), "fix": "intro must be 2 sentences"}]
    second = sents[1]
    hits = []
    n = len(re.findall(r"[A-Za-z']+", second))
    if n < min_second_words:
        hits.append({"second_words": n, "min": min_second_words, "text": second[:110],
                     "fix": "2nd sentence too short — add a substantive follow-up"})
    if re.match(r"(?i)^(so|but|and|or|yet|for|nor)\s", second):
        hits.append({"text": second[:90],
                     "fix": "2nd sentence opens with a coordinating conjunction — start a fresh sentence, don't trail off"})
    heads = _headings(body)
    if heads:
        h1_nouns = _heading_nouns(heads[0])
        second_nouns = _heading_nouns(second)
        if h1_nouns and not (h1_nouns & second_nouns):
            hits.append({"text": second[:90], "h1_nouns": sorted(h1_nouns), "second_nouns": sorted(second_nouns),
                         "fix": "2nd sentence shares no noun with the H1 — restate the subject so it adds substance"})
    return hits


_PORTABILITY_CLAIM_PATTERNS = [
    r"\bcarr(y|ies|ied)\s+(forward|over)\b",
    r"\bmonths?\s+on\s+(the\s+)?group\s+(plan\s+)?count\b",
    r"\bwaiting\s+(period\s+)?credit\b",
    r"\bcontinuity\s+(of\s+)?cover\b",
]
_HEDGE_TOKENS = [
    "typically", "usually", "often", "in most cases", "in some cases", "may", "might", "can",
    "with the same insurer", "same-insurer", "under irdai portability", "subject to portability",
    "within the portability window", "depending on the insurer", "if you port",
]


def check_hedged_portability(body):
    """v20.4 FAIL. Universal claims about waiting-credit carrying forward must be hedged. IRDAI
    portability carries credit forward only under specific same-insurer / migration-window
    conditions; presenting it as universal is misleading. The validator scans each sentence for
    portability-claim patterns; if found and no hedge token appears in the same sentence, FAIL.
    Catches v20.3's KT #4 + FAQ #3 unhedged 'months on group plan count later.'"""
    hits = []
    for line in body.splitlines():
        l = line.strip()
        if not l or l.startswith(("#", "|", ">", "-", "*")):
            continue
        for sent in re.split(r"(?<=[.!?])\s+", l):
            slow = sent.lower()
            if not any(re.search(p, slow) for p in _PORTABILITY_CLAIM_PATTERNS):
                continue
            if any(h in slow for h in _HEDGE_TOKENS):
                continue
            hits.append({"sentence": sent[:120],
                         "fix": "portability/credit-carry claim presented as universal — hedge ('typically', 'with the same insurer', 'under IRDAI portability rules', 'if you port')"})
    return hits


# ---------- v20.3: India geo + GSC interlink + verbatim source backing + anchor relevance ----------
_US_CONTEXT_MARKERS = [
    r"\baffordable care act\b", r"\bACA\b", r"\bfederal (law|protection)",
    r"\bgrandfathered (plan|policy)", r"\bHIPAA\b", r"\bIRS\b", r"\bmedicare\b",
    r"\bmedicaid\b", r"\bobamacare\b", r"\bemployer-sponsored health plan\b",
    r"\bMarch 23,? 2010\b", r"\bsection 1557\b",
]


def check_ai_mode_country(ai_mode_path):
    """v20.3 FAIL. The ai-mode.json capture must NOT contain US-context regulatory markers
    (ACA, federal, Grandfathered, HIPAA, IRS, Medicare, etc.) for India-targeted articles.
    v20.2 shipped an article whose AI Mode capture was US-leaning because the SerpAPI call
    forgot gl=in&hl=en&location=India. This check blocks that class of silent failure.

    The validator reads ai-mode.json (path passed via --ai-mode flag); if any US marker appears
    in the concatenated `text_blocks` snippets, FAIL. If the file isn't present, SKIP (run
    might have used AI Overview path instead)."""
    if not ai_mode_path or not os.path.exists(ai_mode_path):
        return None                                      # SKIP — file not provided
    try:
        data = json.load(open(ai_mode_path, encoding="utf-8"))
    except Exception as e:
        return [{"text": "could not parse %s: %s" % (ai_mode_path, e)}]
    # collect all snippet text
    bodies = []
    for tb in data.get("text_blocks", []):
        if isinstance(tb.get("snippet"), str):
            bodies.append(tb["snippet"])
        for item in tb.get("list", []) or []:
            if isinstance(item.get("snippet"), str):
                bodies.append(item["snippet"])
    body = " ".join(bodies)
    hits = []
    for pat in _US_CONTEXT_MARKERS:
        m = re.search(pat, body, re.I)
        if m:
            hits.append({"marker": m.group(0),
                         "fix": "AI Mode capture is US-leaning. SerpAPI call must include gl=in&hl=en&location=India. Re-run research-flow."})
    return hits


def check_interlink_anchor_relevance(body):
    """v20.3 FAIL. Every contextual site link in the body must have an anchor that shares at
    least 1 meaningful noun with the article's H1 (stopwords stripped). Catches v20.2's
    'personal health insurance policy' anchor → group-vs-individual page on a *group health
    insurance* article (zero overlap with the H1 nouns). Pillar link (anchor == vertical name)
    is exempt."""
    heads = _headings(body)
    if not heads:
        return []
    h1_nouns = _heading_nouns(heads[0])
    # Example pillar anchors (insurance vertical). Replace with your own site's pillar topics.
    pillar_anchors = {"health insurance", "car insurance", "bike insurance", "two wheeler insurance",
                      "travel insurance", "term insurance", "life insurance", "group health insurance"}
    hits = []
    for m in re.finditer(r"\[([^\]]+)\]\(https?://(?:www\.)?" + re.escape(SITE_DOMAIN) + r"/[^)]+\)", body):
        anchor = m.group(1).strip()
        if anchor.lower() in pillar_anchors:
            continue                                      # pillar link, exempt
        anchor_nouns = _heading_nouns(anchor)
        if not (anchor_nouns & h1_nouns):
            ln = body.count("\n", 0, m.start()) + 1
            hits.append({"line": ln, "anchor": anchor[:60], "h1_nouns": sorted(h1_nouns),
                         "anchor_nouns": sorted(anchor_nouns),
                         "fix": "anchor text shares no noun with article H1 — drop this link or rewrite the anchor"})
    return hits



def _heading_nouns(heading):
    """The meaningful nouns in a heading (stopwords + tiny words stripped). Used to verify the
    section opener actually carries the heading's subject, not a thin restatement."""
    return {w for w in re.findall(r"[a-z]+", heading.lower())
            if w not in STOPWORDS and len(w) > 3}


def check_section_noun_overlap(body, minimum):
    """v20.2 FAIL. The first sentence of each body section MUST contain at least `minimum`
    meaningful nouns from its heading (default 2). Catches openers that drop the heading's
    subject — e.g. heading 'When Does GHI Apply a Waiting Period for PED?' with opener
    'A wait still applies in two common cases.' (drops 'group health insurance' + 'pre-existing
    diseases'). Stopwords stripped on both sides; FAQ + Key Takeaways exempt."""
    heads = _headings(body)[1:]                 # skip H1
    hits = []
    for h in heads:
        if re.search(r"frequently asked|key takeaways|team to supply", h, re.I):
            continue
        opener = _section_opener(body, h)
        if not opener:
            continue
        first = re.split(r"(?<=[.!?])\s+", opener)[0]
        heading_nouns = _heading_nouns(h)
        opener_nouns = _heading_nouns(first)
        shared = heading_nouns & opener_nouns
        if len(shared) < minimum:
            hits.append({"heading": h[:80], "shared_nouns": sorted(shared),
                         "need": minimum, "opener": first[:110],
                         "fix": "first sentence must include the heading's subject — name the topic explicitly"})
    return hits


def check_section_continuation(body, minimum):
    """v20.2 FAIL. Each body H2 section must contain at least `minimum` prose sentences (default
    3). Stops one-liner-then-list patterns where a section answers in one line and jumps straight
    to a list, leaving the answer dangling without elaboration. FAQ + Key Takeaways are exempt."""
    # cut FAQ + KT
    m_faq = re.search(r"(?im)^#{0,3}\s*frequently asked", body)
    m_kt  = re.search(r"(?im)^#{0,3}\s*key takeaways", body)
    cut = min([x.start() for x in (m_faq, m_kt) if x is not None] or [len(body)])
    scope = body[:cut]
    parts = re.split(r"(?m)^(##\s+.*)$", scope)
    hits = []
    for i in range(1, len(parts), 2):
        h = parts[i].strip()
        b = parts[i + 1] if i + 1 < len(parts) else ""
        # collect prose paragraphs only (skip headings, tables, blockquotes, lists)
        prose = []
        for para in re.split(r"\n\s*\n", b):
            p = para.strip()
            if not p or p.startswith(("#", "|", ">")):
                continue
            if re.match(r"^\s*[-*]\s", p) or re.match(r"^\s*\d+[\.\)]\s", p):
                continue
            prose.append(re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", p))
        sents = []
        for p in prose:
            sents += [s for s in re.split(r"(?<=[.!?])\s+", p) if s.strip()]
        if len(sents) < minimum:
            hits.append({"heading": h[:80], "prose_sentences": len(sents), "need": minimum,
                         "fix": "this section is too thin — add %d more sentences of elaboration after the opener" % (minimum - len(sents))})
    return hits


def check_brand_reg_no(body, expected):
    """Example domain rule (insurance). Replace or disable for your vertical.
    v20.2 FAIL. The footer MUST contain the brand's actual IRDAI Registration Number (default 157).
    v20.1 shipped with '152' — a hallucinated number. This hard-codes the truth."""
    if not re.search(r"irdai\s*registration\s*(no\.?|number)\.?\s*:?\s*" + str(expected), body, re.I):
        return [{"expected": expected,
                 "fix": "footer must contain 'IRDAI Registration No. %d' (the brand's real number); the model previously hallucinated other digits" % expected}]
    return []


def check_banned_facts(body, banned):
    """v20.2 FAIL. A list of factual claims that are no longer true under current regulation. The
    PED look-back and max wait are both 36 months as of the IRDAI Master Circular dated 29 May
    2024 (was 48). Any current-tense mention of '48 month'/'48-month' fails — unless it's a
    historical reference ('was', 'previously', 'used to be', 'earlier', 'formerly', 'changed
    from') within the prior ~10 words."""
    hits = []
    for entry in banned:
        pat = re.compile(entry["pattern"], re.I)
        for m in pat.finditer(body):
            # check left context for a historical qualifier
            left = body[max(0, m.start() - 80): m.start()].lower()
            if re.search(r"\b(was|were|used to be|previously|earlier|formerly|changed from|reduced from|down from)\b", left):
                continue                        # historical / change-mention — OK
            ln = body.count("\n", 0, m.start()) + 1
            hits.append({"line": ln, "match": m.group(0), "fix": entry.get("fix", "this fact is out of date")})
    return hits


# ---------- v19: tightened citations, length cap, per-section answer shape ----------
def check_irdai_in_heading(body):
    """v19 FAIL. No heading (H1/H2/H3) may contain 'IRDAI' — never a regulator-named section.
    IRDAI references stay inline, woven into a generic section, never as a standalone heading."""
    hits = []
    for h in _headings(body):
        if re.search(r"\birdai\b", h, re.I):
            hits.append({"heading": h[:80], "fix": "rephrase the heading; reference IRDAI inline inside the section, never as its own block"})
    return hits


def check_external_stats_max(body, maximum):
    """v19 FAIL. Total external statistics (lines carrying a Source: tag with a figure such as
    %, crore, lakh, ratio or ₹) must be <= `maximum` (config external_stats_max, default 1).
    Stats added without sources are caught by the grounding check; this limits the SOURCED ones."""
    hits = []
    cited = []
    for i, line in enumerate(body.splitlines(), 1):
        if not re.search(r"source\s*[:\[]", line, re.I):
            continue
        if not re.search(r"%|crore|lakh|ratio|₹|\bpercent\b", line, re.I):
            continue
        cited.append({"line": i, "text": line.strip()[:120]})
    if len(cited) > maximum:
        for c in cited:
            hits.append({**c, "found": len(cited), "max": maximum,
                         "fix": "cap the article at %d sourced external stat" % maximum})
    return hits


def _body_word_count(body):
    text = re.sub(r"\[[^\]]+\]\([^)]+\)", " ", body)        # drop link URLs, keep anchors
    text = re.sub(r"(?m)^\s*[#>|].*$", " ", text)            # drop heading / table / blockquote lines
    return len(re.findall(r"[A-Za-z']+", text))


def _load_length_target(run_folder):
    """v21: read the per-run evidence-based length target written by length_target.py."""
    if not run_folder:
        return None
    p = os.path.join(run_folder, "length-target.json")
    if os.path.exists(p):
        try:
            return json.load(open(p, encoding="utf-8"))
        except Exception:
            return None
    return None


def check_word_count(body, maximum):
    """v21 FAIL -- HARD guard only. Body word count must not exceed the absolute ceiling
    (config word_count_ceiling, fallback word_count_max). This is the runaway guard; the
    evidence-based SERP band is enforced separately as a FLAG (check_length_vs_serp), and
    thinness below the floor is also a FLAG, because length is topic-driven."""
    n = _body_word_count(body)
    return [{"words": n, "max": maximum, "fix": "over the hard ceiling -- cut %d words" % (n - maximum)}] if n > maximum else []


def check_length_vs_serp(body, run_folder, cfg):
    """v21 FLAG -- advisory length band derived from the SERP (length-target.json). Below the
    band = too thin for this topic (the mediclaim-guide failure); above = likely padded. FLAG,
    not FAIL, because the right length is topic-driven and the writer may justify an outlier.
    Also FLAGs below the absolute floor (word_count_floor)."""
    n = _body_word_count(body)
    tgt = _load_length_target(run_folder)
    floor = cfg.get("word_count_floor", 800)
    if not tgt:
        if n < floor:
            return [{"words": n, "floor": floor, "fix": "below the %d-word floor -- likely too thin; no length-target.json found, run length_target.py" % floor}]
        return []
    lo, hi = tgt.get("word_target_low", floor), tgt.get("word_target_high", cfg.get("word_count_ceiling", 2800))
    if n < lo:
        return [{"words": n, "serp_band": [lo, hi], "median_competitor_words": tgt.get("median_competitor_words"),
                 "fix": "thin for this topic: %d words vs SERP band %d-%d. Competitors cover more -- add the sub-topics they cover that you skipped (do NOT pad existing sections)." % (n, lo, hi)}]
    if n > hi:
        return [{"words": n, "serp_band": [lo, hi],
                 "fix": "longer than the SERP band %d-%d -- check for padding; every section must earn its place and trace to research." % (lo, hi)}]
    return []


def check_coverage_vs_serp(body, run_folder):
    """v21 FLAG -- coverage signal independent of word count. If competitors average N H2
    sections and we have materially fewer, the article is thin on COVERAGE (the real fix for
    thinness: cover more real sub-topics, not pad). FLAG only."""
    tgt = _load_length_target(run_folder)
    if not tgt:
        return []
    target_sections = tgt.get("section_target")
    if not target_sections:
        return []
    heads = [h for h in _headings(body)[1:]
             if not re.search(r"frequently asked|key takeaways|team to supply", h, re.I)]
    n = len(heads)
    if n < target_sections - 1:
        return [{"our_h2": n, "serp_median_h2": target_sections,
                 "fix": "thin coverage: %d H2 sections vs competitor median %d. Add the real sub-topics competitors cover that you skipped." % (n, target_sections)}]
    return []


def check_section_word_count(body, maximum):
    """v20 FAIL. Each body H2 section <= `maximum` prose words (config section_word_max). Stops
    one section eating the total-word budget while others stay tiny. Excludes the FAQ block and
    Key Takeaways (those have their own counts). Headings, tables, blockquotes excluded from the
    per-section count, same as the total-word check."""
    # cut FAQ and Key Takeaways from the body scope (they are bounded by other checks)
    m_faq = re.search(r"(?im)^#{0,3}\s*frequently asked", body)
    m_kt  = re.search(r"(?im)^#{0,3}\s*key takeaways", body)
    cut = min([x.start() for x in (m_faq, m_kt) if x is not None] or [len(body)])
    scope = body[:cut]
    # split on H2 lines
    parts = re.split(r"(?m)^(##\s+.*)$", scope)
    # parts: [pre-H1 stuff, "## heading1", body1, "## heading2", body2, ...]
    hits = []
    for i in range(1, len(parts), 2):
        h = parts[i].strip()
        b = parts[i + 1] if i + 1 < len(parts) else ""
        # strip headings/tables/blockquotes/links inside this section
        t = re.sub(r"\[[^\]]+\]\([^)]+\)", " ", b)
        t = re.sub(r"(?m)^\s*[#>|].*$", " ", t)
        n = len(re.findall(r"[A-Za-z']+", t))
        if n > maximum:
            hits.append({"heading": h[:90], "words": n, "max": maximum,
                         "fix": "cut %d words from this section" % (n - maximum)})
    return hits


def check_kt_exact(body, want):
    """v20 FAIL. Key Takeaways must contain EXACTLY `want` items (config kt_count_exact, default
    4). A 'takeaway' is a bullet/numbered item whose first 4-12 words form the bold lead-in."""
    m = re.search(r"(?im)^#{0,3}\s*key takeaways", body)
    if not m:
        return [{"count": 0, "want": want, "issue": "no Key Takeaways section found"}]
    block = body[m.end():]
    end = re.search(r"(?im)^#{1,3}\s|^-{3,}\s*$|irdai registration", block)
    block = block[:end.start()] if end else block
    items = 0
    for ln in block.splitlines():
        s = re.sub(r"^[-*\d.)\s]+", "", ln).strip()
        if not s:
            continue
        if not re.search(r"[A-Za-z]", s):                  # skip dividers
            continue
        items += 1
    return [{"count": items, "want": want}] if items != want else []


def check_glossary_gloss(body, glossary):
    """v20 FAIL. For each domain term in `glossary` (style.json glossary_required), the
    FIRST body occurrence must carry a parenthetical gloss within ~80 chars. A gloss is detected
    as text in parentheses immediately after the term (or starting within 80 chars of it). If the
    term never appears, no failure. If it appears unglossed on its first occurrence, FAIL."""
    # cut Team-to-supply appendix and FAQ block — first-occurrence check is body-prose only
    m_app = re.search(r"(?im)^#{0,3}\s*team to supply", body)
    scope = body[:m_app.start()] if m_app else body
    # strip markdown link anchors so "[rider](url)" doesn't count as a gloss
    scope_norm = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", scope)
    hits = []
    for term in glossary:
        pat = re.compile(r"\b" + re.escape(term) + r"\b", re.I)
        m = pat.search(scope_norm)
        if not m:
            continue
        window = scope_norm[m.end(): m.end() + 80]
        if not re.match(r"\s*\(.{4,}?\)", window):
            ln = scope_norm.count("\n", 0, m.start()) + 1
            hits.append({"line": ln, "term": term,
                         "fix": "gloss on first use, e.g. '%s (%s)'" % (term, glossary[term])})
    return hits


# ---------- v20.1: callout-vs-body and FAQ-vs-body uniqueness ----------
def _shingles(text, n=6):
    """6-gram shingles of meaningful tokens (lowercase, alpha-only). Catches near-duplication
    even when phrasing differs slightly. Stopwords kept (they shape the shingle), only punctuation
    and case stripped."""
    toks = re.findall(r"[A-Za-z']+", text.lower())
    return set(" ".join(toks[i:i + n]) for i in range(len(toks) - n + 1)) if len(toks) >= n else set()


def check_callout_unique(body):
    """v20.1 FAIL (G1 v20). A callout (blockquote) must NOT repeat content already in its
    section's body prose. Compares 6-gram shingles of the callout text against the surrounding
    section. If ≥40% of the callout's shingles also appear in the section body, FAIL."""
    lines = body.splitlines()
    # find blockquote groups
    groups, cur = [], None
    for i, ln in enumerate(lines):
        if ln.lstrip().startswith(">"):
            cur = [i, i] if cur is None else [cur[0], i]
        elif cur is not None:
            groups.append(tuple(cur)); cur = None
    if cur is not None:
        groups.append(tuple(cur))
    if not groups:
        return []
    hits = []
    for a, b in groups:
        # find the H2 above this callout, and the next H2 (section bounds)
        head = None
        for j in range(a - 1, -1, -1):
            if re.match(r"^##\s", lines[j]):
                head = j; break
        if head is None:
            continue
        nxt = None
        for j in range(b + 1, len(lines)):
            if re.match(r"^##\s", lines[j]):
                nxt = j; break
        sec_end = nxt if nxt is not None else len(lines)
        # callout text (strip leading '>')
        callout = " ".join(re.sub(r"^\s*>+\s*", "", lines[k]) for k in range(a, b + 1))
        # rest of the section, excluding the callout itself and any other blockquote lines
        rest = []
        for k in range(head + 1, sec_end):
            if k >= a and k <= b:
                continue
            if lines[k].lstrip().startswith(">"):
                continue
            rest.append(lines[k])
        section = " ".join(rest)
        cs, ss = _shingles(callout), _shingles(section)
        if not cs:
            continue
        overlap = len(cs & ss) / len(cs)
        if overlap >= 0.40:
            hits.append({"line": a + 1, "overlap_pct": round(overlap * 100),
                         "callout": callout.strip()[:90],
                         "fix": "callout duplicates section content — drop the callout or rewrite to add new info"})
    return hits


def check_faq_unique(body):
    """v20.1 FAIL (F1 v20). A FAQ entry must NOT restate a body section's content. For each FAQ
    Q+A pair, compare its 6-gram shingles against ALL body section prose (everything before the
    FAQ block). If ≥40% of the FAQ's shingles appear in the body, FAIL."""
    fb = faq_block(body)
    if not fb:
        return []
    # body prose = everything before the FAQ heading, with tables/blockquotes/headings stripped
    m_faq = re.search(r"(?im)^#{0,3}\s*frequently asked", body)
    pre = body[:m_faq.start()] if m_faq else ""
    pre = re.sub(r"(?m)^\s*[#>|].*$", " ", pre)
    pre = re.sub(r"\[[^\]]+\]\([^)]+\)", " ", pre)
    body_shingles = _shingles(pre)
    if not body_shingles:
        return []
    hits = []
    # walk the FAQ — each Q (ends ?) followed by its answer until the next Q
    lines = [l for l in fb.splitlines() if l.strip()]
    i = 0
    while i < len(lines):
        q = lines[i].strip()
        if q.endswith("?"):
            ans = []
            j = i + 1
            while j < len(lines) and not lines[j].strip().endswith("?"):
                ans.append(lines[j]); j += 1
            qa = q + " " + " ".join(ans)
            qs = _shingles(qa)
            if qs:
                overlap = len(qs & body_shingles) / len(qs)
                if overlap >= 0.40:
                    hits.append({"q": q[:60], "overlap_pct": round(overlap * 100),
                                 "fix": "FAQ duplicates body content — drop or replace with a different user question"})
            i = j
        else:
            i += 1
    return hits



# ---------- per-section answer shape (v19, Issue 4 fix) ----------
_QTYPE_PATTERNS = [
    ("yesno",      r"^\s*(does|do|is|are|can|will|should|did|has|have|was|were)\b"),
    # v20.1 — "what happens" is its OWN qtype, NOT definition. Answer is typically a verb phrase
    # ("Your cover ends on...") with no "is/are/means" — so it cannot be checked as a definition
    # without false positives. Tagged "process" — we only enforce the generic wind-up guard for it.
    ("event",      r"^\s*what happens\b"),
    ("definition", r"^\s*(what is|what's|what are|what counts as|what do(es)? .* mean)\b"),
    ("comparison", r"^\s*(how does .* compare|how does .* (treat|handle|cover) .*\b(differently|different) from\b|what'?s the difference|.*\bvs\.?\b|.*\bversus\b)"),
    ("conditional",r"^\s*(when|under what)\b"),
    ("causal",     r"^\s*(why|how come)\b"),
    ("howto",      r"^\s*(how (do|to|can)|steps)\b"),                          # process — no narrow rule, just no wind-up
    ("listing",    r"^\s*(which|what (kind|type|examples?))\b"),
]
_WINDUP_OPENERS = re.compile(
    r"^\s*(if you|when you|most (people|owners|buyers|policyholders|customers)|many (people|owners|buyers|policyholders)|"
    r"imagine|picture this|we'?ve all|think about|in india|in today)\b", re.I)


def _classify(heading):
    h = heading.strip().lower()
    for label, pat in _QTYPE_PATTERNS:
        if re.search(pat, h):
            return label
    return "other"


def _section_opener(body, h_text):
    """Return the first 1-2 sentences of prose under heading `h_text`."""
    pat = re.compile(r"^#{1,3}\s*" + re.escape(h_text.strip()) + r"\s*$", re.I | re.M)
    m = pat.search(body)
    if not m:
        return ""
    rest = body[m.end():]
    # cut at the next heading
    nxt = re.search(r"(?m)^#{1,3}\s", rest)
    block = rest[:nxt.start()] if nxt else rest
    # first prose paragraph
    for para in re.split(r"\n\s*\n", block):
        p = para.strip()
        if not p or p.startswith(("#", "|", ">", "-", "*")):
            continue
        # take first 2 sentences
        sents = re.split(r"(?<=[.!?])\s+", p)
        return " ".join(sents[:2]).strip()
    return ""


def check_section_answer_shape(body):
    """v19 FLAG. Each section's first 1-2 sentences must deliver the answer shape its heading asks
    for. Yes/No → opens with Yes/No. 'What is X?' → opens with the definition (no narrative
    wind-up). Conditional/Why → first sentence names the condition/cause. Generic catch: any
    section opener that starts with 'If you / When you / Most people / Imagine ...' is a wind-up."""
    heads = _headings(body)
    hits = []
    for h in heads[1:]:                          # skip H1 (handled by check_bluf_yesno + check_lede_opener)
        qtype = _classify(h)
        opener = _section_opener(body, h)
        if not opener:
            continue
        first = re.split(r"(?<=[.!?])\s+", opener)[0]
        # generic wind-up guard for every section, regardless of type
        if _WINDUP_OPENERS.search(opener):
            hits.append({"heading": h[:80], "qtype": qtype, "opener": opener[:110],
                         "fix": "drop the narrative wind-up; lead with the answer to the heading"})
            continue
        if qtype == "yesno" and not re.match(r"(?i)^(yes|no)\b", first):
            hits.append({"heading": h[:80], "qtype": qtype, "opener": opener[:110],
                         "fix": "yes/no question — first sentence must open Yes/No"})
        elif qtype == "definition":
            # crude: a definition usually says "X is/are/means ..."
            if not re.search(r"\b(is|are|means|refers to|=)\b", first):
                hits.append({"heading": h[:80], "qtype": qtype, "opener": opener[:110],
                             "fix": "definitional question — first sentence must be the definition (X is …)"})
    return hits


def _opt(flag):
    if flag in sys.argv:
        i = sys.argv.index(flag)
        if i + 1 < len(sys.argv):
            return sys.argv[i + 1]
    return None


# ---------- v20.5: heading + link discipline (ported from mini skill v1.3.2 + new) ----------
def _topic_noun_set(topic):
    """Core topic nouns = topic nouns minus product nouns."""
    if not topic:
        return set()
    raw = {w for w in re.findall(r"[a-z]+", topic.lower())
           if w not in STOPWORDS and len(w) > 3}
    core = raw - PRODUCT_NOUNS
    return core if core else raw


def check_noun_floor(body, corpus_text):
    """v20.5 FAIL. Every meaningful noun in each H2 must appear at least once in the raw scraped
    corpus. Kills fabricated topics in headings without per-H2 backing claims."""
    heads = [h for h in _headings(body)[1:]
             if not re.search(r"frequently asked|key takeaways|team to supply", h, re.I)]
    if not corpus_text:
        return [{"text": "no corpus text provided -- pass --corpus competitor-1.md,...,ai-mode.json"}]
    corpus_words = set(re.findall(r"[a-z]+", corpus_text.lower()))
    hits = []
    for h in heads:
        h_nouns = {w for w in re.findall(r"[a-z]+", h.lower())
                   if w not in STOPWORDS and len(w) > 3}
        missing = sorted(n for n in h_nouns if n not in corpus_words)
        if missing:
            hits.append({"h2": h[:90], "missing_nouns": missing,
                         "fix": "H2 has nouns the scraped corpus never mentions -- invented topic. Pick a topic the data covers."})
    return hits


def check_topic_anchor(body, topic):
    """v20.5 FAIL -- drift killer. Every H2 must be anchored to the article's subject: it contains
    EITHER >=1 core topic noun (topic nouns minus product nouns) OR the full product name.
    v21: a heading carrying the full product name is NOT drift -- requiring a core topic noun ON TOP
    of the product name was the rule that forced the 'Floater Premium' weld (this rule and
    h2_product_name_presence collided). Accepting the product name as a valid anchor dissolves that
    collision while still catching headings that drift to an unrelated subject (neither present)."""
    core = _topic_noun_set(topic)
    if not core:
        return []
    product = _detect_product_phrase((_headings(body) or [""])[0], topic)
    heads = [h for h in _headings(body)[1:]
             if not re.search(r"frequently asked|key takeaways|team to supply", h, re.I)]
    hits = []
    for h in heads:
        if product and re.search(r"\b" + re.escape(product) + r"\b", h, re.I):
            continue  # full product name present -> on-topic, not drift
        h_nouns = {w for w in re.findall(r"[a-z]+", h.lower())
                   if w not in STOPWORDS and len(w) > 3}
        if not (h_nouns & core):
            hits.append({"h2": h[:90], "core_topic_nouns": sorted(core),
                         "h2_nouns": sorted(h_nouns),
                         "fix": "H2 has neither a core topic noun nor the product name -- drifted to an adjacent topic. Restructure."})
    return hits


_QUESTION_STARTERS = {"what", "how", "when", "why", "who", "can", "does", "is", "are",
                      "will", "should", "which", "do", "could", "would", "shall", "may"}


def check_question_shape(body):
    """v20.5 FAIL -- every H2 must be a real question (question word + ?) or How-to instruction.
    Catches '?' tacked onto a noun phrase."""
    heads = [h for h in _headings(body)[1:]
             if not re.search(r"frequently asked|key takeaways|team to supply", h, re.I)]
    hits = []
    for h in heads:
        low = h.lower().strip().lstrip("#").strip()
        if low.startswith(("how to", "step", "steps to")):
            continue
        if not low.endswith("?"):
            hits.append({"h2": h[:90], "fix": "H2 must end with '?' or be a How-to instruction."})
            continue
        first = low.split()[0] if low.split() else ""
        if first not in _QUESTION_STARTERS:
            hits.append({"h2": h[:90], "starts_with": first,
                         "fix": "H2 ends with '?' but starts with a noun -- '?' tacked on a fragment. Rewrite as a real question."})
    return hits


def check_link_count_max(body, cfg):
    """v20.5 FAIL -- max N links total per article."""
    max_total = cfg.get("max_links_total", 4)
    links = re.findall(r"\[[^\]]+\]\((https?://[^)]+)\)", body)
    if len(links) > max_total:
        return [{"link_count": len(links), "max_allowed": max_total,
                 "fix": "too many links -- cap is %d (1 pillar + %d contextual)" % (max_total, max_total - 1)}]
    return []


def check_no_forum_links(body):
    """v20.5 FAIL -- no links to social/forum domains."""
    links = re.findall(r"\[[^\]]+\]\((https?://[^)]+)\)", body)
    hits = []
    for url in links:
        host = re.sub(r"^https?://(www\.)?", "", url).split("/")[0].lower()
        for banned in SOCIAL_FORUM_DOMAINS:
            if host == banned or host.endswith("." + banned):
                hits.append({"url": url[:100], "domain": host,
                             "fix": "remove link -- %s is on the social/forum block list" % host})
                break
    return hits


def check_link_para_spacing(body, cfg):
    """v20.6.1 FAIL -- any two links must be at least min_link_para_spacing+1 paragraphs apart.
    Auto-relaxes to 0 (no spacing requirement) for short articles where strict spacing would
    drop legitimate contextual links. Threshold: articles with <12 substantive paragraphs."""
    paras = body.split("\n\n")
    substantive_paras = [p for p in paras if len(p.split()) >= 10]
    min_gap = cfg.get("min_link_para_spacing", 1)
    # v20.6.1 -- short article relaxation
    if len(substantive_paras) < 12:
        min_gap = 0
    link_paras = []
    for i, para in enumerate(paras):
        if re.search(r"\[[^\]]+\]\(https?://", para):
            link_paras.append(i)
    hits = []
    for i in range(len(link_paras) - 1):
        gap = link_paras[i + 1] - link_paras[i]
        if gap <= min_gap:
            hits.append({"para_indexes": [link_paras[i], link_paras[i + 1]], "gap_paras": gap,
                         "min_required": min_gap + 1,
                         "fix": "two links too close -- at least %d para(s) between them" % (min_gap + 1)})
    return hits


def check_faq_count_range(body, cfg):
    """v20.5 FAIL -- FAQ count in [faq_count_min, faq_count_max]. Replaces v20.1's faq_count_exact."""
    fmin = cfg.get("faq_count_min", 4)
    fmax = cfg.get("faq_count_max", 6)
    m = re.search(r"(?im)^#{2,3}\s*frequently asked", body)
    if not m:
        return [{"text": "no FAQ block found"}]
    rest = body[m.end():]
    nxt = re.search(r"(?im)^#{2,3}\s+", rest)
    block = rest[:nxt.start()] if nxt else rest
    questions = re.findall(r"(?m)^#{3,4}\s+(.+?\?)\s*$", block)
    n = len(questions)
    if n < fmin or n > fmax:
        return [{"faq_count": n, "min": fmin, "max": fmax,
                 "fix": "FAQ count out of [%d, %d] range" % (fmin, fmax)}]
    return []



EXPECTED_FILES_BY_SUBSTEP = {
    "1_keyword_intelligence": ["ahrefs-keywords.json", "ahrefs-questions.json"],
    "2_paa_serpapi": ["serpapi.json", "paa.json"],
    "2b_ai_mode": ["ai-mode.json"],
    "2c_forums_news_videos": ["forums.json"],
    "5_site_url_graph": ["site-urls.json"],
    "6_data_enrichment": ["data-enrichment.json"],
    "7_bundle": ["research-brief.md"],
}


PHASE_ARTIFACTS = [
    ("outline.md",              "Phase 2 (outline)"),
    ("outline-status.json",     "Phase 2 (outline)"),
    ("draft.md",                "Phase 3 (draft)"),
    ("draft-status.json",       "Phase 3 (draft)"),
    ("faq-builder-status.json", "Phase 4 (FAQ)"),
    ("voice-pass-report.md",    "Phase 6 (voice pass)"),
    ("voice-pass-status.json",  "Phase 6 (voice pass)"),
    ("seo-meta-status.json",    "Phase 7 (SEO meta)"),
    ("audit-report.md",         "Phase 8 (lineage audit)"),
    ("audit-status.json",       "Phase 8 (lineage audit)"),
]


def check_phase_artifacts(run_folder):
    """v22.7 FAIL -- anti-shortcut guard. The 2026-07-15 batch session shipped Docs from a
    truncated ad-hoc flow: no outline.md, no draft.md, no voice-pass or status files -- the
    nine phases never ran, so no rule (old or new) was applied. build_doc.py is the only
    delivery door and re-runs validate with run_folder defaulted to the draft's parent dir,
    so this check makes that shortcut physically unable to ship: every mandatory phase must
    have left its artifact on disk. Mode-independent (--no-links / --no-footer exempt none
    of these; phase-5 artifacts are gated separately by gsc_used)."""
    hits = []
    for fname, phase in PHASE_ARTIFACTS:
        if not os.path.exists(os.path.join(run_folder, fname)):
            hits.append({"missing_file": fname, "phase": phase,
                         "fix": "%s never ran (or did not write its artifact). Run the full pipeline per SKILL.md -- shortcut flows cannot ship." % phase})
    return hits


def check_research_execution_completeness(run_folder):
    """v20.5.1 FAIL. Every PASS/PARTIAL sub_step in research-execution.json must have its
    expected files on disk. Catches silent-skip bugs."""
    import json as _json
    if not run_folder or not os.path.isdir(run_folder):
        return []
    rexec = os.path.join(run_folder, "research-execution.json")
    if not os.path.exists(rexec):
        return [{"text": "research-execution.json missing"}]
    try:
        d = _json.load(open(rexec, encoding="utf-8"))
    except Exception as e:
        return [{"text": "research-execution.json unparseable: %s" % e}]
    hits = []
    for sub, meta in (d.get("sub_steps") or {}).items():
        if (meta.get("status") or "").upper() not in ("PASS", "PARTIAL"):
            continue
        for fname in EXPECTED_FILES_BY_SUBSTEP.get(sub, []):
            if not os.path.exists(os.path.join(run_folder, fname)):
                hits.append({"sub_step": sub, "missing_file": fname,
                             "fix": "claimed PASS but file not on disk -- silent skip"})
    return hits


def check_lineage(run_folder):
    """v20.5.1 FAIL. Runs lineage_check.py subprocess against the run folder. Any source with
    fingerprints_extracted > 0 but matches_in_body == 0 is a silent-skip and FAILs the run."""
    import subprocess as _sp, json as _json
    if not run_folder or not os.path.isdir(run_folder):
        return []
    here = os.path.dirname(os.path.abspath(__file__))
    lc = os.path.join(here, "lineage_check.py")
    if not os.path.exists(lc):
        return [{"text": "lineage_check.py missing from sub-skills/"}]
    try:
        _sp.run(["python3", lc, run_folder], capture_output=True, text=True, timeout=60)
    except Exception as e:
        return [{"text": "lineage_check.py crashed: %s" % e}]
    report_path = os.path.join(run_folder, "lineage-report.json")
    if not os.path.exists(report_path):
        return [{"text": "lineage-report.json not written by lineage_check.py"}]
    try:
        report = _json.load(open(report_path, encoding="utf-8"))
    except Exception as e:
        return [{"text": "lineage-report.json unparseable: %s" % e}]
    hits = []
    for s in report.get("sources", []):
        if s.get("verdict") == "NOT_FOUND_IN_BODY" and s.get("fingerprints_extracted", 0) > 0:
            hits.append({"source": s["source"], "extracted": s["fingerprints_extracted"],
                         "found": s["matches_in_body"],
                         "fix": "source has data but NOT used in body -- silent skip"})
    return hits



# ---------- v20.6: heading discipline (FK, noun-stack, word cap, count, synonym drift) ----------


def check_h2_word_cap(body, cfg):
    """v20.6 FAIL. Each H2 must be <= cfg.h2_word_max (default 10) words."""
    cap = cfg.get("h2_word_max", 10)
    heads = [h for h in _headings(body)[1:]
             if not re.search(r"frequently asked|key takeaways|team to supply", h, re.I)]
    hits = []
    for h in heads:
        n = len(h.split())
        if n > cap:
            hits.append({"h2": h[:90], "words": n, "max": cap,
                         "fix": "H2 too long (%d words > %d max) -- trim." % (n, cap)})
    return hits


def check_h2_count_range(body, cfg):
    """v20.6 FAIL. H2 count must be in [cfg.h2_count_min, cfg.h2_count_max] (default 3-5)."""
    hmin = cfg.get("h2_count_min", 3)
    hmax = cfg.get("h2_count_max", 5)
    heads = [h for h in _headings(body)[1:]
             if not re.search(r"frequently asked|key takeaways|team to supply", h, re.I)]
    n = len(heads)
    if n < hmin or n > hmax:
        return [{"h2_count": n, "min": hmin, "max": hmax,
                 "fix": "H2 count %d out of [%d, %d] range -- merge or split sections." % (n, hmin, hmax)}]
    return []



def check_gsc_used(run_folder):
    """v21 (content-gen-pipeline) -- REPURPOSED from the v20.6 GSC gate. The new interlink flow
    is DRAFT-FIRST: anchors are noun phrases already present in the prose, matched to targets
    from link_map.json; GSC is no longer the anchor source. This check now verifies the audit
    trail instead: internal-linking-audit.json must exist and every link must declare
    anchor_source "draft" (proof the anchor pre-existed in prose, never force-inserted) and a
    slot of pillar / secondary / topical / service."""
    if not run_folder or not os.path.isdir(run_folder):
        return []
    audit_path = os.path.join(run_folder, "internal-linking-audit.json")
    if not os.path.exists(audit_path):
        return [{"text": "internal-linking-audit.json missing -- Phase 5 did not run cleanly"}]
    try:
        a = json.load(open(audit_path, encoding="utf-8"))
    except Exception as e:
        return [{"text": "internal-linking-audit.json unparseable: %s" % e}]
    hits = []
    links = a.get("links") or []
    valid_slots = {"pillar", "secondary", "topical", "service"}
    for ln in links:
        if not isinstance(ln, dict):
            continue
        if (ln.get("slot") or "").lower() not in valid_slots:
            hits.append({"anchor": ln.get("anchor", "?")[:60],
                         "fix": "link has no valid slot (pillar/secondary/topical/service)"})
        if (ln.get("anchor_source") or "").lower() != "draft":
            hits.append({"anchor": ln.get("anchor", "?")[:60],
                         "fix": "anchor_source must be 'draft' -- anchors come from phrases already in the prose, never inserted for the link"})
    return hits


def check_data_enrichment_consistency(run_folder):
    """v20.6 FAIL. If research-execution.json claims data-enrichment had N must_include_stats,
    the file's must_include_stats array must have >=N items. Catches the GMC bug where audit
    said '1 must-include stat' but file had must_include_stats: []."""
    if not run_folder or not os.path.isdir(run_folder):
        return []
    rexec = os.path.join(run_folder, "research-execution.json")
    de = os.path.join(run_folder, "data-enrichment.json")
    if not os.path.exists(rexec) or not os.path.exists(de):
        return []
    try:
        re_data = json.load(open(rexec, encoding="utf-8"))
        de_data = json.load(open(de, encoding="utf-8"))
    except Exception:
        return []
    sub = (re_data.get("sub_steps") or {}).get("6_data_enrichment") or {}
    notes = (sub.get("notes") or "").lower()
    must_in_file = len(de_data.get("must_include_stats") or [])
    # Heuristic: notes mentions "must-include" + a number
    m = re.search(r"(\d+)\s+must[- ]include", notes)
    if m:
        claimed = int(m.group(1))
        if claimed > must_in_file:
            return [{"claimed_must_include": claimed, "actual_in_file": must_in_file,
                     "fix": "research-execution.json claims %d must-include stats but data-enrichment.json has %d. Update one." % (claimed, must_in_file)}]
    return []



# ---------- v20.6.1: H2 must contain the full product name from H1 ----------
PRODUCT_PHRASES = [
    "Group Health Insurance", "Car Insurance", "Bike Insurance", "Health Insurance",
    "Term Life Insurance", "Term Insurance", "Travel Insurance",
    "Comprehensive Car Insurance", "Two-Wheeler Insurance",
]


def _scan_for_product_phrase(text):
    """Scan a string for the longest PRODUCT_PHRASES match. Returns the canonical phrase or None."""
    if not text:
        return None
    best = None
    for p in PRODUCT_PHRASES:
        if re.search(r"\b" + re.escape(p) + r"\b", text, re.I):
            if best is None or len(p) > len(best):
                best = p
    return best


def _detect_product_phrase(h1, topic_arg=None, run_folder=None):
    """v20.6.2: chain H1 -> --topic flag -> research-execution.json topic.
    Returns canonical product phrase (e.g. 'Car Insurance') or None if none of the 3 has it."""
    p = _scan_for_product_phrase(h1)
    if p:
        return p
    p = _scan_for_product_phrase(topic_arg)
    if p:
        return p
    if run_folder and os.path.isdir(run_folder):
        rexec = os.path.join(run_folder, "research-execution.json")
        if os.path.exists(rexec):
            try:
                import json as _json
                d = _json.load(open(rexec, encoding="utf-8"))
                p = _scan_for_product_phrase(d.get("topic", ""))
                if p:
                    return p
            except Exception:
                pass
    return None


def check_h2_product_name_presence(body, topic_arg=None, run_folder=None):
    """v20.6.2 FAIL. Every H2 must contain the full product name detected in H1 (or topic /
    research-execution.json fallback). Catches H2s that drop the product name."""
    heads = _headings(body)
    if not heads:
        return []
    h1 = heads[0]
    product = _detect_product_phrase(h1, topic_arg, run_folder)
    if not product:
        return []
    hits = []
    for h in heads[1:]:
        if re.search(r"frequently asked|key takeaways|team to supply", h, re.I):
            continue
        if not re.search(r"\b" + re.escape(product) + r"\b", h, re.I):
            hits.append({"h2": h[:90], "missing_product": product,
                         "fix": "H2 must contain the full product name '%s' from H1." % product})
    return hits



# ---------- v20.6.1: BLUF casing matches H1 product casing ----------

def check_anchor_quality(body, cfg):
    """v21 (content-gen-pipeline): every internal link's anchor must be a natural phrase that
    describes its TARGET page: 2-6 words AND >=2 meaningful-token overlap with the target URL
    slug. Kills 'add parent' -> /including-parents-in-employer-health-insurance/. Pillar links
    (exact pillar_map URLs) are exempt from the overlap rule (anchor = bare vertical name)."""
    hits = []
    pillar_urls = {u.rstrip("/") for u in (cfg.get("pillar_map") or {}).values()}
    stop = {"the", "a", "an", "of", "in", "for", "and", "to", "with", "your", "is", "on",
            "how", "what", "best", "india", "online"}
    wmin, wmax = cfg.get("anchor_word_min", 2), cfg.get("anchor_word_max", 6)
    need = cfg.get("anchor_slug_noun_overlap_min", 2)
    for m in re.finditer(r"\[([^\]]+)\]\((https?://(?:www\.)?" + re.escape(SITE_DOMAIN) + r"[^)]*)\)", body):
        anchor, url = m.group(1).strip(), m.group(2)
        words = anchor.split()
        if len(words) < wmin or len(words) > wmax:
            hits.append({"anchor": anchor, "url": url,
                         "reason": "anchor must be %d-%d words" % (wmin, wmax)})
            continue
        if url.rstrip("/") in pillar_urls:
            continue
        slug = re.sub(r"[?#].*$", "", url.rstrip("/")).split("/")[-1]
        slug_toks = {t for t in re.split(r"[-_]", slug.lower()) if len(t) >= 3 and t not in stop}
        anchor_toks = {t for t in re.findall(r"[a-z]+", anchor.lower()) if len(t) >= 3 and t not in stop}
        overlap = {a for a in anchor_toks
                   if any(a.rstrip("s") == s.rstrip("s") for s in slug_toks)}
        if len(overlap) < need:
            hits.append({"anchor": anchor, "url": url,
                         "reason": "anchor shares only %d (< %d) meaningful words with target slug '%s' — pick a noun phrase that names the target page, or drop the link" % (len(overlap), need, slug)})
    return hits


def check_anchor_self_scoping(body, style):
    """v22.5 FAIL (user request). A contextual site link anchor must SELF-SCOPE: read alone,
    outside its sentence, it must still be an insurance/service phrase. The ethanol run shipped
    anchor 'consequential damage' -> /insurance/consequential-damages/ -- standalone that is a
    generic legal term Google associates with contract law, while the prose right there said
    'consequential damage cover' (the scoping word was left outside the link). Rule: every
    non-pillar site anchor must contain >=1 scoping token (anchor_scoping_tokens) OR a
    self-scoping proper/service term (anchor_proper_terms). Both lists are team-editable in
    style.json."""
    scoping = set(t.lower() for t in style.get("anchor_scoping_tokens", []))
    proper = [t.lower() for t in style.get("anchor_proper_terms", [])]
    # Example pillar anchors (insurance vertical). Replace with your own site's pillar topics.
    pillar_anchors = {"health insurance", "car insurance", "bike insurance", "two wheeler insurance",
                      "travel insurance", "term insurance", "life insurance", "group health insurance"}
    hits = []
    for m in re.finditer(r"\[([^\]]+)\]\((https?://(?:www\.)?" + re.escape(SITE_DOMAIN) + r"/[^)]+)\)", body):
        anchor = m.group(1).strip()
        al = anchor.lower()
        if al in pillar_anchors:
            continue
        toks = set(re.findall(r"[a-z0-9-]+", al))
        if toks & scoping:
            continue
        if any(p in al for p in proper):
            continue
        ln = body.count("\n", 0, m.start()) + 1
        hits.append({"line": ln, "anchor": anchor[:60], "url": m.group(2)[:80],
                     "fix": "anchor is generic standalone -- extend it to the full prose noun phrase that carries a scoping word (e.g. 'consequential damage cover'), or add the term to anchor_proper_terms if it self-scopes"})
    return hits


def check_bluf_answer_shape(body):
    """v21: the lede's SHAPE must match the H1's question type. A 'How to / How do' H1 needs an
    action-shaped first sentence ('To find X, compare ...'), not a definition ('The best X is ...').
    Yes/No H1s are handled by check_bluf_yesno; What-is H1s by the BLUF checks."""
    hs = _headings(body)
    if not hs:
        return []
    h1 = hs[0].lower()
    if not re.match(r"how\s+(to|do|does|can|should)\b", h1):
        return []
    fs = first_sentence(body)
    if not fs:
        return []
    f = fs.strip().lower()
    action_shape = re.match(
        r"(to\s+\w+|start\b|begin\b|first\b|compare\b|check\b|look\b|use\b|set\b|pick\b|"
        r"choose\b|ask\b|open\b|search\b|calculate\b|list\b|focus\b|"
        r"you\s+(can\s+)?(find|get|check|compare|start|choose|pick|lower|do|need)\b)", f)
    definition_shape = re.match(r"(the|a|an)\s+\w[\w\s-]*?\s+(is|are|means|refers)\b", f)
    if definition_shape and not action_shape:
        return [{"text": fs.strip()[:160],
                 "reason": "H1 asks HOW TO, but the lede answers WHAT IS — open with the action ('To find ..., do X')"}]
    return []


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    # drop values that belong to --brief/--seo/--sources from positional args
    opt_vals = {_opt("--brief"), _opt("--seo"), _opt("--sources"), _opt("--ai-mode"), _opt("--audit"), _opt("--competitors")}
    args = [a for a in args if a not in opt_vals]
    json_only = "--json" in sys.argv
    # run-scoped batch mode: ship with no internal links (no pillar, no contextual, no GSC).
    # ONLY relaxes the two link-dependent FAIL gates (pillar_link, gsc_used). Everything else
    # stays enforced. Normal single-topic runs never pass this flag, so they keep full linking.
    no_links = "--no-links" in sys.argv
    # run-scoped batch mode: ship with NO IRDAI registration footer. Relaxes the presence
    # check's footer requirement (KT + Last updated stay required) and skips brand_reg_no.
    no_footer = "--no-footer" in sys.argv
    run_folder = _opt("--run-folder") or ""
    # v20.5: corpus paths for heading-discipline checks
    corpus_paths = [pp.strip() for pp in (_opt("--corpus") or "").split(",") if pp.strip()]
    # v20.6.4 R4 -- cache-from: skip checks that PASSed in a prior iteration (voice-pass speedup)
    cache_from = _opt("--cache-from")
    cached_passed = set()
    if cache_from and os.path.exists(cache_from):
        try:
            cdata = json.load(open(cache_from, encoding="utf-8"))
            cached_passed = {c["id"] for c in cdata.get("checks", []) if c.get("status") == "PASS"}
        except Exception:
            pass
    corpus_text = ""
    for cp in corpus_paths:
        try:
            corpus_text += "\n" + open(cp, encoding="utf-8").read()
        except Exception:
            pass
    topic = _opt("--topic") or ""
    brief_path, seo_path = _opt("--brief"), _opt("--seo")
    ai_mode_path = _opt("--ai-mode")        # v20.3 — ai-mode.json from research-flow (US-context check)
    audit_path = _opt("--audit")            # v20.3 — internal-linking-audit.json from interlink step
    competitors_arg = _opt("--competitors") # v20.3 — comma-separated paths to competitor-N.md files
    competitor_files = [p.strip() for p in (competitors_arg or "").split(",") if p.strip()]
    if not args:
        print("usage: validate.py <article.md> [--json] [--brief research-brief.md] [--seo seo-meta.md] [--sources section-sources.json]")
        sys.exit(2)
    text = open(args[0], encoding="utf-8").read()
    body, _ = split_body_and_appendix(text)
    # Prose-only view of the body: markdown table rows (lines starting with '|') removed. Used by
    # the word-choice register checks (banned words/phrases, metaphor, sales, casual) so a
    # research-sourced comparison table (paraphrased, never copied) is not policed as authored
    # prose. Structural and anti-AI literal-character checks still run on the full body.
    body_prose = re.sub(r"(?m)^\s*\|.*$", " ", body)
    S = load_style(); cfg = S["config"]
    checks = []

    def add(cid, name, severity, hits, extra=None):
        # v20.6.4 R4: skip checks that already PASSed in prior iteration
        if cid in cached_passed:
            checks.append({"id": cid, "name": name, "severity": severity, "status": "CACHED_PASS", "hits": []})
            return
        status = ("FAIL" if severity == "FAIL" else "FLAG") if hits else "PASS"
        row = {"id": cid, "name": name, "severity": severity, "status": status, "hits": hits}
        if extra: row.update(extra)
        checks.append(row)

    def add_run_scoped(cid, name, fn):
        """v22.1: a check that NEEDS --run-folder is visibly SKIPPED when it's missing --
        never a silent PASS ('any check it cannot run is reported, never assumed clean')."""
        if cid in cached_passed:
            checks.append({"id": cid, "name": name, "severity": "FAIL", "status": "CACHED_PASS", "hits": []})
            return
        if not run_folder or not os.path.isdir(run_folder):
            checks.append({"id": cid, "name": name, "severity": "FAIL", "status": "SKIPPED",
                           "note": "--run-folder not provided -- check cannot run", "hits": []})
        else:
            add(cid, name, "FAIL", fn())

    # ---- publish-blocking FAIL checks ----
    add("brackets", "Stray non-link [..] in body", "FAIL", check_brackets(body))
    add("placeholder", "Internal placeholder leak", "FAIL", check_placeholder(body))
    add("merged_citation", "Merged-publisher citation", "FAIL", check_merged_citation(body))
    add("metric_label", "Impossible metric label (>100% settlement ratio)", "FAIL", check_metric_label(body))
    add("naked_url", "No naked URLs in body — use a linked anchor (B4)", "FAIL", check_naked_url(body))
    add("bluf_opener", "Lede opens with the answer, not a scene-setter (B1)", "FAIL", check_lede_opener(body, S.get("scene_setter_openers", [])))
    add("bluf_yesno", "Yes/No question H1 -> lede opens Yes/No (B3)", "FAIL", check_bluf_yesno(body))
    add("source_gov", "External stats from gov/IRDAI sources only (C)", "FAIL", check_source_gov(body, S.get("allowed_source_substrings", [])))
    add("source_deeplink", "Source links cite a specific page, not a homepage (C/#12/v22.1)", "FAIL", check_source_deeplink(body))
    add("dangling_heading", "Headings stand alone — no dangling 'this/the answer' (B2)", "FAIL", check_dangling_headings(body, S.get("dangling_heading_words", [])))
    add("sales", "Promotional/sell register — educate, don't sell (A3/E1)", "FAIL", check_sales(body_prose, S.get("sales_patterns", [])))
    add("source_words", "Research-source word in prose — Reddit/Quora/etc (C6)", "FAIL", check_source_words(body, S.get("source_words", [])))
    add("brand_data_tag", "Inline '(Source: brand internal data)' tag in prose (E1)", "FAIL", check_brand_data_tag(body))
    add("title_case", "H2s in Title Case (B2)", "FAIL", check_title_case(body))
    add("banned_words", "Banned jargon (style.json ban_swaps)", "FAIL", check_ban_swaps(body_prose, S["ban_swaps"]))
    add("banned_phrases", "Banned phrases (style.json ban_phrases)", "FAIL", check_ban_phrases(body_prose, S["ban_phrases"]))
    add("metaphor", "Metaphor/personification (style.json metaphor_patterns)", "FAIL", check_patterns(body_prose, S["metaphor_patterns"]))
    # ---- anti-AI writing tells (Wikipedia WP:AISIGNS) — anti-ai fork, FAIL ----
    add("ai_dash", "Em/en dash — use comma/colon/period (A6/WP:AIDASH)", "FAIL",
        check_literal_chars(body, ["—", "–"]))
    add("ai_curly", "Curly quotes/apostrophes — straighten to ASCII (WP:AICURLY)", "FAIL",
        check_literal_chars(body, ["“", "”", "‘", "’"]))
    # v22.1: the ai_* PATTERN checks run on body_prose (tables excluded) -- SKILL.md has always
    # documented that tables are exempt from register checks; only the literal ai_dash/ai_curly
    # gates above stay on the full body. ai_vague_attr also exempts properly-cited lines.
    add("ai_copula", "Copula avoidance — say it with is/are/has (WP:AIWTW)", "FAIL",
        check_patterns(body_prose, S.get("copula_patterns", [])))
    add("ai_ing_tail", "Superficial '-ing' significance tail (WP:SUPERFICIAL)", "FAIL",
        check_patterns(body_prose, S.get("superficial_ing_patterns", [])))
    add("ai_vague_attr", "Vague attribution/weasel — name the source (WP:AIWEASEL)", "FAIL",
        check_vague_attribution(body_prose, S.get("vague_attribution_patterns", [])))
    add("ai_neg_parallel", "Negative parallelism 'not X, but Y' (WP:AIPARALLEL)", "FAIL",
        check_patterns(body_prose, S.get("negative_parallelism_patterns", [])))
    add("ai_puffery", "Significance/legacy puffery (WP:AILEGACY/AIPUFFERY)", "FAIL",
        check_patterns(body_prose, S.get("significance_puffery_patterns", [])))
    add("h1_h2_dup", "H2 duplicates the H1", "FAIL", check_h1_h2_dup(body))
    _service_kws = cfg.get("service_topic_keywords", [])
    _is_service_topic = bool(topic) and any(k in topic.lower() for k in _service_kws)
    if no_links or _is_service_topic:
        checks.append({"id": "pillar_link", "name": "Pillar interlink to <site_domain>/<vertical>/", "severity": "FAIL",
                       "status": "SKIPPED",
                       "note": "no-links batch mode" if no_links else "service-topic article — insurance pillar not forced (v21)",
                       "hits": []})
    else:
        ok = check_pillar(body, cfg["verticals"])
        checks.append({"id": "pillar_link", "name": "Pillar interlink to <site_domain>/<vertical>/", "severity": "FAIL",
                       "status": "PASS" if ok else "FAIL",
                       "hits": [] if ok else [{"text": "no <site_domain>/<vertical>/ pillar link found"}]})
    add("product_name_trim", "Headings use the full product name, not a trimmed shorthand (B2/v18)", "FAIL",
        check_product_name_trim(body, S.get("product_name_trims", [])))
    # v20 — FAQ EXACTLY N (was 5-7 range; ranges produce ceiling-hugging output)
    add("faq_count", "FAQ count in [%d, %d] (F1/v20.5)" % (cfg.get("faq_count_min", 4), cfg.get("faq_count_max", 6)), "FAIL",
        check_faq_count_range(body, cfg))
    # v20 — Key Takeaways EXACTLY N
    add("kt_exact", "Key Takeaways has exactly %d items (B6/v20)" % cfg.get("kt_count_exact", 4), "FAIL",
        check_kt_exact(body, cfg.get("kt_count_exact", 4)))
    add("presence", "Mandatory blocks present: Key Takeaways + IRDAI footer + Last updated (v18)", "FAIL",
        check_presence(body, skip_footer=no_footer))
    # v21 — per-section word cap (FAIL); dynamic from length-target.json (scales with the SERP
    # target so a long guide can have deeper sections) else config section_word_max fallback.
    _ltgt = _load_length_target(run_folder)
    _sec_cap = (_ltgt or {}).get("section_word_max") or cfg.get("section_word_max", 250)
    add("section_word_count", "Each body H2 section <= %d words (D7/v21 dynamic)" % _sec_cap, "FAIL",
        check_section_word_count(body, _sec_cap))
    # v20 — glossary gloss: domain terms must be glossed on first body use
    add("glossary_gloss", "Domain terms glossed on first use (D1/v20)", "FAIL",
        check_glossary_gloss(body, S.get("glossary_required", {})))
    # v19: tightened IRDAI handling — no heading, max 1 mention (FAIL, was FLAG @5)
    add("irdai_heading", "No heading may contain 'IRDAI' (C/v19) — keep references inline only", "FAIL",
        check_irdai_in_heading(body))
    # v19: cap total external sourced stats
    add("external_stats_max", "External sourced stats <= %d per article (C/v19)" % cfg.get("external_stats_max", 1), "FAIL",
        check_external_stats_max(body, cfg.get("external_stats_max", 1)))
    # v21: body word-count HARD CEILING (runaway guard). The evidence-based SERP band and the
    # coverage signal are FLAGs below.
    _ceiling = cfg.get("word_count_ceiling", cfg.get("word_count_max", 2800))
    add("word_count", "Body word count <= %d (v21 hard ceiling)" % _ceiling, "FAIL",
        check_word_count(body, _ceiling))

    # ---- FLAG checks (review, not blocking) ----
    # v21: evidence-based length band + coverage, both derived from the scraped SERP
    add("length_vs_serp", "Body length within the SERP-derived band (v21)", "FLAG",
        check_length_vs_serp(body, run_folder, cfg))
    add("coverage_vs_serp", "H2 coverage >= competitor median sections (v21)", "FLAG",
        check_coverage_vs_serp(body, run_folder))
    add("source_quality", "Source quality — primary over aggregator summary", "FLAG", check_source_quality(body))
    add("authority_overcite", "IRDAI mentioned at most %d time (C/v19)" % cfg.get("authority_mention_max", 1), "FAIL", check_authority_overcite(body, cfg.get("authority_mention_max", 1)))
    add("regulator_named", "Name IRDAI, don't say 'the regulator' (C7)", "FLAG", check_regulator_named(body))
    add("bare_qualifier_headings", "Policy-type qualifier in heading must name the product (B2)", "FLAG", check_bare_qualifier_headings(body))
    add("third_person", "Body in second person — no 'the reader' (A1)", "FLAG", check_third_person(body))
    add("faq_answers", "FAQ answers 150-300 chars (F1)", "FLAG", check_faq_answers(body))
    add("interlink_position", "First site link not in para 1-2 (B4)", "FLAG", check_interlink_position(body))
    add("long_paragraphs", "Break up paragraphs over 80 words (D6)", "FLAG", check_long_paragraphs(body))
    add("takeaways_leadin", "Key Takeaways lead-ins are self-contained, not teasers (B6)", "FLAG", check_takeaways_leadin(body))
    add("casual", "Casual/commercial register (style.json casual_patterns)", "FLAG", check_patterns(body_prose, S["casual_patterns"]))
    # ---- anti-AI writing tells (Wikipedia WP:AISIGNS) — anti-ai fork, FLAG ----
    add("ai_knowledge_cutoff", "Knowledge-cutoff/'not documented' disclaimer (WP:AICUTOFF)", "FLAG",
        check_patterns(body_prose, S.get("knowledge_cutoff_patterns", [])))
    add("ai_outline_close", "Outline 'Challenges/Future' close (WP:AICHALLENGES)", "FLAG",
        check_patterns(body_prose, S.get("outline_challenges_patterns", [])))
    add("ai_rule_of_three", "Rule-of-three triplet — fine occasionally (WP:RO3)", "FLAG",
        check_rule_of_three(body_prose))
    # v22.1 -- PROPOSED v23 tell families (WP:AISIGNS coverage gaps): observe-only pilot.
    # FLAG never blocks; the team reviews hits across real runs, then promotes proven-clean
    # families into their own FAIL keys. Patterns live in style.json proposed_tell_patterns.
    add("ai_proposed_tells", "PROPOSED v23 AI-tell families — observe-only pilot (WP:AISIGNS)", "FLAG",
        check_patterns(body_prose, S.get("proposed_tell_patterns", [])))
    add("word_repetition", "Word over-repetition (content word used too often)", "FLAG", check_word_repetition(body, S["glossary_allow"], S.get("repetition_allow", [])))
    # v20.1 — intro_length is now FAIL (was FLAG). v20 set the number to 2 but forgot to bump the severity.
    add("intro_length", "Intro <= %d sentences (B3/v20.1)" % cfg.get("intro_max_sentences", 2), "FAIL",
        check_intro_length(body, cfg.get("intro_max_sentences", 2)))
    add("sentence_length", "No prose sentence over %d words (D6/v18)" % cfg.get("sentence_hard_cap", 28), "FLAG",
        check_sentence_length(body, cfg.get("sentence_hard_cap", 28)))
    add("takeaways_terminal", "Key Takeaways is the final block (v18)", "FLAG", check_takeaways_terminal(body))
    add("callout_budget", "Callout boxes <= %d and never adjacent (G/v18)" % cfg.get("callout_max", 3), "FLAG",
        check_callout_budget(body, cfg.get("callout_max", 3)))
    # v22.4 (user request) — advisory section-tool variety; never blocks
    add("structure_variety", "Section-tool variety — not all prose (advisory, v22.4)", "FLAG",
        check_structure_variety(body, cfg.get("structure_prose_run_max", 3)))
    # v20.1: callout must NOT duplicate section body content (G1 v20)
    add("callout_unique", "Callouts must not repeat section content (G1/v20.1)", "FAIL", check_callout_unique(body))
    # v20.1: FAQ must NOT restate body content (F1 v20)
    add("faq_unique", "FAQ entries must not restate body content (F1/v20.1)", "FAIL", check_faq_unique(body))
    add("data_vintage", "Each cited stat states its data year (C/v18)", "FLAG", check_data_vintage(body))
    # v19/v20: each section's first 1-2 sentences must deliver the answer shape its heading asks for
    # bumped to FAIL in v20 — was FLAG, now blocks publish
    add("section_answer_shape", "Sections lead with the answer to their heading (no wind-up) (B4/v20)", "FAIL",
        check_section_answer_shape(body))
    # v20.4 — extended intro_substantive: word count + no leading conjunction + H1 noun overlap
    add("intro_substantive", "Intro's 2nd sentence carries weight + names H1 subject (B3/v20.4)", "FAIL",
        check_intro_substantive_v204(body, cfg.get("intro_min_second_sentence_words", 10)))
    # v20.4 — no two body H2s on the same sub-topic (Jaccard > 0.6)
    add("h2_h2_duplicate", "No two body H2s overlap >0.6 in nouns (B4/v20.4)", "FAIL",
        check_h2_h2_duplicate(body, 0.6, topic=topic))

    # v20.5: heading discipline (ported from mini skill)
    add("noun_floor", "Every H2 noun appears in scraped corpus (v20.5 fabrication-killer)", "FAIL",
        check_noun_floor(body, corpus_text))
    add("topic_anchor", "Every H2 contains >=1 CORE topic noun (v20.5 drift-killer)", "FAIL",
        check_topic_anchor(body, topic))
    add("question_shape", "H2 is a real question or How-to (v20.5)", "FAIL",
        check_question_shape(body))

    # v20.5: link discipline
    add("link_count_max", "Max %d links total (1 pillar + %d contextual) (v20.5)" % (cfg.get("max_links_total", 4), cfg.get("max_links_total", 4) - 1), "FAIL",
        check_link_count_max(body, cfg))
    add("no_forum_links", "No links to social/forum domains (v20.5)", "FAIL",
        check_no_forum_links(body))
    add("link_para_spacing", "Links >=%d para(s) apart (v20.5)" % (cfg.get("min_link_para_spacing", 1) + 1), "FAIL",
        check_link_para_spacing(body, cfg))

    # v21 (content-gen-pipeline): anchor quality + BLUF answer shape
    # Batch mode (--no-links): interlinks are team-curated from the source sheet, so the
    # model-anchor-quality heuristics must not gate them; they still run for normal pipeline runs.
    if not no_links:
        add("anchor_quality", "Every anchor is a natural 2-6 word phrase matching its target slug (v21)", "FAIL",
            check_anchor_quality(body, cfg))
        add("anchor_self_scoping", "Contextual anchors read as insurance/service phrases standalone (v22.5)", "FAIL",
            check_anchor_self_scoping(body, S))
    add("bluf_answer_shape", "Lede shape matches the H1 question type (How-to -> action) (v21)", "FAIL",
        check_bluf_answer_shape(body))

    # v20.4 — when/how/why heading must not open with a comparison table
    add("heading_content_mismatch", "When/How/Why H2 does not open with a 3+ row comparison table (B4/v20.4)", "FAIL",
        check_heading_content_mismatch(body))
    # v20.4 — every H2 uses the canonical noun phrase from the H1
    # v20.4 — body must carry at least one concrete example (rupee figure or worked scenario)
    add("concrete_example", "Body has at least one concrete example or rupee figure (D4/v20.4)", "FAIL",
        check_concrete_example(body))
    # v20.4 — portability/credit-carry claims must be hedged
    add("hedged_portability", "Portability/credit claims are hedged, not stated as universal (H/v20.4)", "FAIL",
        check_hedged_portability(body))
    # v20.2 — section opener must include >=2 nouns from its heading
    add("section_noun_overlap", "Section opener names the heading's subject (>= %d nouns) (B4/v20.2)" % cfg.get("section_noun_overlap_min", 2), "FAIL",
        check_section_noun_overlap(body, cfg.get("section_noun_overlap_min", 2)))
    # v20.2 — each section must have >= N prose sentences (no one-liner-then-list)
    add("section_continuation", "Each section has >= %d prose sentences (B4/v20.2)" % cfg.get("section_min_sentences", 3), "FAIL",
        check_section_continuation(body, cfg.get("section_min_sentences", 3)))
    # Example domain rule (insurance). Replace or disable for your vertical.
    # v20.2 — brand IRDAI Reg No. must be the real one (157), not the hallucinated 152
    if no_footer:
        checks.append({"id": "brand_reg_no", "name": "Footer contains the correct IRDAI Registration No. (G2/v20.2)",
                       "severity": "FAIL", "status": "SKIPPED", "note": "no-footer batch mode", "hits": []})
    else:
        add("brand_reg_no", "Footer contains the correct IRDAI Registration No. (G2/v20.2)", "FAIL",
            check_brand_reg_no(body, cfg.get("brand_irdai_reg_no", 157)))
    # v20.2 — banned outdated facts (e.g. "48 months" without a historical qualifier)
    add("banned_facts", "No outdated regulatory facts (e.g. '48 months' as current) (H/v20.2)", "FAIL",
        check_banned_facts(body, S.get("banned_facts", [])))


    # v22.1 -- wire the v20.3 US-context gate (was defined but never called even though SKILL.md
    # passes --ai-mode). None = file not provided -> visibly SKIPPED, never a silent pass.
    _amc = check_ai_mode_country(ai_mode_path)
    if _amc is None:
        checks.append({"id": "ai_mode_country", "name": "AI Mode capture is India-context, not US (v20.3)",
                       "severity": "FAIL", "status": "SKIPPED",
                       "note": "--ai-mode not provided / file missing", "hits": []})
    else:
        add("ai_mode_country", "AI Mode capture is India-context, not US (v20.3)", "FAIL", _amc)
    # v22.1 -- wire the v20.3 anchor-vs-H1 relevance check. FLAG, not FAIL: the v21 3-slot link
    # design allows secondary/topical anchors that legitimately share no noun with the H1.
    if not no_links:
        add("interlink_anchor_relevance", "Contextual anchor shares >=1 noun with the H1 (v20.3)", "FLAG",
            check_interlink_anchor_relevance(body))

    # ---- optional trace checks (need the run-folder files) ----
    if seo_path and os.path.exists(seo_path):
        seo_text = open(seo_path, encoding="utf-8").read()
        h1 = (_headings(body) or [""])[0]
        add("meta_title", "Meta title matches the topic/H1 (#58)", "FAIL", check_meta_title(seo_text, h1))
        add("meta_description", "Meta description = direct answer, not the title question (v13)", "FAIL", check_meta_description(seo_text, h1))
        if brief_path and os.path.exists(brief_path):
            add("keyword_trace", "Keywords verbatim in research-brief — no made-up KWs (#62)", "FAIL",
                check_keyword_trace(seo_text, open(brief_path, encoding="utf-8").read()))
    if brief_path and os.path.exists(brief_path):
        brief_text = open(brief_path, encoding="utf-8").read()
        add("grounding", "Specific numbers trace to research-brief (C8 grounding)", "FLAG",
            check_grounding(body, brief_text))
        floor = cfg.get("grounding_floor", 0.70)
        g, tot = grounding_ratio(body, brief_text)
        ratio = (g / tot) if tot else 1.0
        gr_fail = tot >= 3 and ratio < floor
        checks.append({"id": "grounding_ratio",
                       "name": "Grounding ratio: specifics traced to paid data >= floor (Part C)",
                       "severity": "FAIL", "status": "FAIL" if gr_fail else "PASS",
                       "detail": {"grounded": g, "total": tot, "ratio": round(ratio, 2), "floor": floor},
                       "hits": [{"text": "only %d/%d specifics (%.0f%%) trace to data; floor %.0f%%" %
                                 (g, tot, ratio*100, floor*100)}] if gr_fail else []})
    hard, method = check_hard_words_wordfreq(body, cfg, S["glossary_allow"])
    # v20.1 — wordfreq hard words is now FAIL (was FLAG). The CMO complaint was about register
    # complexity; FLAGging it allowed drafts with "undeclared", "insurer's", etc. to ship.
    if hard is None:
        checks.append({"id": "hard_words", "name": "Rare/hard words (wordfreq)", "severity": "FAIL",
                       "status": "SKIPPED", "note": method, "hits": []})
    else:
        checks.append({"id": "hard_words", "name": "Rare/hard words (wordfreq)", "severity": "FAIL",
                       "status": "FAIL" if hard else "PASS", "method": method, "hits": hard})

    read = check_readability(body, cfg)
    checks.append({"id": "readability", "name": "Readability (textstat)", "severity": "FAIL",
                   "status": read.get("status", "SKIPPED"), "detail": read})
    vale = run_vale(args[0])
    checks.append({"id": "vale", "name": "Vale house-style (optional)", "severity": "FLAG",
                   "status": vale.get("status", "SKIPPED"), "detail": vale})

    # v22.7: anti-shortcut guard -- every mandatory phase left its artifact on disk
    add_run_scoped("phase_artifacts", "All 9 phases ran and wrote their artifacts (anti-shortcut, v22.7)",
        lambda: check_phase_artifacts(run_folder))
    # v20.5.1: run-artifact completeness + lineage gate (v22.1: SKIPPED without --run-folder)
    add_run_scoped("research_execution_completeness", "Every PASS/PARTIAL sub_step's files exist on disk (v20.5.1)",
        lambda: check_research_execution_completeness(run_folder))
    add_run_scoped("lineage", "Every captured research source has trace in article body (v20.5.1)",
        lambda: check_lineage(run_folder))


    # v20.6: heading discipline
    add("h2_word_cap", "Each H2 <= %d words (v20.6)" % cfg.get("h2_word_max", 10), "FAIL",
        check_h2_word_cap(body, cfg))
    add("h2_count_range", "H2 count in [%d, %d] (v20.6)" % (cfg.get("h2_count_min", 3), cfg.get("h2_count_max", 5)), "FAIL",
        check_h2_count_range(body, cfg))

    # v20.6.1: H2 product name presence + lede casing + redundant abbreviation
    add("h2_product_name_presence", "Every H2 contains full product name from H1 (v20.6.1)", "FAIL",
        check_h2_product_name_presence(body, topic, run_folder))

    # v21: draft-first interlink audit (replaces the v20.6 GSC gate) + data-enrichment cross-check
    if no_links:
        checks.append({"id": "gsc_used", "name": "Interlink audit: draft-first anchors + valid slots (v21)",
                       "severity": "FAIL", "status": "SKIPPED", "note": "no-links batch mode", "hits": []})
    else:
        add_run_scoped("gsc_used", "Interlink audit: draft-first anchors + valid slots (v21)",
            lambda: check_gsc_used(run_folder))
    add_run_scoped("data_enrichment_consistency", "research-execution.json claims match data-enrichment.json contents (v20.6)",
        lambda: check_data_enrichment_consistency(run_folder))

    fails = [c for c in checks if c["status"] == "FAIL"]
    flags = [c for c in checks if c["status"] == "FLAG"]
    skipped = [c for c in checks if c["status"] == "SKIPPED"]
    overall = "FAIL" if fails else "PASS"
    result = {"overall": overall, "checks_total": len(checks),
              "passed": sum(1 for c in checks if c["status"] == "PASS"),
              "fails": len(fails), "flags": len(flags), "skipped": len(skipped),
              "checks": checks}

    if json_only:
        print(json.dumps(result, indent=2, ensure_ascii=False))
        sys.exit(0 if overall == "PASS" else 1)

    print(f"\n=== validate.py — {os.path.basename(args[0])} ===")
    print(f"OVERALL: {overall}   ({result['passed']} clean / {len(fails)} FAIL / "
          f"{len(flags)} FLAG / {len(skipped)} SKIPPED)\n")
    mark = {"PASS": "✓", "FAIL": "✗", "FLAG": "!", "SKIPPED": "-"}
    for c in checks:
        print(f"[{mark.get(c['status'],'?')}] {c['status']:7} {c['name']}")
        for h in (c.get("hits") or [])[:8]:
            print(f"        - {h}")
        if c["id"] in ("readability", "vale") and isinstance(c.get("detail"), dict):
            print(f"        {c['detail']}")
        if c.get("note"):
            print(f"        ({c['note']})")
    print()
    sys.exit(0 if overall == "PASS" else 1)


if __name__ == "__main__":
    main()
