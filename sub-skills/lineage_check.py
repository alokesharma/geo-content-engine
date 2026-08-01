#!/usr/bin/env python3
"""lineage_check.py v3 -- DISTINCTIVE-FINGERPRINT source-usage verification.

v3 (v20.6) change: only counts fingerprints that are DISTINCTIVE -- content that wouldn't
appear in any generic article on this topic. Generic topic-keyword matches don't count.

Distinctive content = (a) specific numbers (>=2 digits), (b) capitalized brand/entity names
not in the topic, (c) multi-word phrases (>=3 words) with >=2 nouns not in the topic itself.

If a source's distinctive fingerprints are 0, the source is EXEMPT (not gated). If a source
has distinctive fingerprints but 0 appear in body, that's a captured-but-not-used FAIL.

Usage: python3 lineage_check.py <run-folder>
Exit 0 = every gated source has >=1 distinctive match. Exit 1 = silent skip detected.
"""
import json, os, re, sys, glob

STOPWORDS = set("""a an the and or but if then else of to in on at by for with from into over under
again further once is are was were be been being have has had do does did this that these those it
its their there here you your we our they them as so than too very can will just not no nor only s t
now about above below up down out off about which who whom whose what when where why how all any
both each few more most other some such per via does pre yes""".split())


def _topic_nouns(folder):
    """Pull the article topic from research-execution.json or research-brief.md."""
    rexec = os.path.join(folder, "research-execution.json")
    if os.path.exists(rexec):
        try:
            d = json.load(open(rexec, encoding="utf-8"))
            t = d.get("topic", "")
            return {w.lower() for w in re.findall(r"[A-Za-z]+", t) if len(w) >= 4 and w.lower() not in STOPWORDS}
        except Exception:
            pass
    return set()


def _distinctive(phrase, topic_nouns):
    """v20.6: phrase is DISTINCTIVE if it contains specific numbers OR named entities OR
    multi-word phrases with >=2 non-topic nouns."""
    if not phrase or len(phrase) < 4:
        return False
    # numbers >=2 digits (e.g., 36, 1500, 2024, 50%, ₹1,000)
    if re.search(r"\d{2,}", phrase):
        return True
    # multi-word phrase with at least 2 nouns not in topic
    words = re.findall(r"[A-Za-z]+", phrase)
    if len(words) < 3:
        return False
    nouns = {w.lower() for w in words if len(w) >= 4 and w.lower() not in STOPWORDS}
    distinctive_nouns = nouns - topic_nouns
    if len(distinctive_nouns) >= 2:
        return True
    # capitalized phrase with proper-noun-ish words (>=2 Title-Cased multi-letter words)
    title_cased = [w for w in words if len(w) >= 3 and w[0].isupper() and not w.isupper()]
    if len(title_cased) >= 2:
        return True
    return False


def _phrase_in_body(phrase, body_lower):
    if not phrase or len(phrase) < 4:
        return False
    return re.sub(r"\s+", " ", phrase.lower().strip()) in body_lower


def _noun_overlap_in_body(phrase, body_words, topic_nouns, min_overlap=2):
    """Match on >=min_overlap distinctive (non-topic) nouns appearing in body."""
    pn = {w for w in re.findall(r"[a-z]+", phrase.lower()) if w not in STOPWORDS and len(w) >= 4}
    distinctive = pn - topic_nouns
    if len(distinctive) < min_overlap:
        return False
    return len(distinctive & body_words) >= min_overlap


def extract_fingerprints(src_path):
    base = os.path.basename(src_path)
    try:
        if src_path.endswith(".json"):
            data = json.load(open(src_path, encoding="utf-8"))
        else:
            data = open(src_path, encoding="utf-8").read()
    except Exception:
        return []
    fps = []
    if "ahrefs-keywords" in base or "ahrefs-questions" in base:
        if isinstance(data, dict):
            resp = data.get("response", {})
            items = resp.get("keywords") or resp.get("data") or resp.get("rows") or [] if isinstance(resp, dict) else (resp or [])
            if not items:
                items = data.get("keywords") or data.get("data") or []
            for it in items:
                if isinstance(it, dict):
                    if it.get("keyword"):  fps.append(it["keyword"])
                    if it.get("question"): fps.append(it["question"])
                elif isinstance(it, str):
                    fps.append(it)
    elif base == "ai-mode.json":
        for tb in (data.get("text_blocks") or []):
            if isinstance(tb, dict):
                if tb.get("title"):   fps.append(tb["title"])
                if tb.get("snippet"): fps.append(tb["snippet"][:200])
                for item in (tb.get("list") or tb.get("items") or []):
                    if isinstance(item, dict):
                        if item.get("title"):   fps.append(item["title"])
                        if item.get("snippet"): fps.append(item["snippet"][:120])
                    elif isinstance(item, str):
                        fps.append(item)
        for cs in (data.get("cited_sources") or []):
            if isinstance(cs, dict) and cs.get("title"):
                fps.append(cs["title"])
    elif base == "forums.json":
        results = data.get("results") or data.get("organic_results") or [] if isinstance(data, dict) else []
        for r in results:
            if isinstance(r, dict):
                if r.get("title"):   fps.append(r["title"])
                if r.get("snippet"): fps.append(r["snippet"][:150])
    elif base == "videos.json":
        items = data.get("videos") or data.get("video_results") or [] if isinstance(data, dict) else []
        for r in items:
            if isinstance(r, dict):
                if r.get("title"):       fps.append(r["title"])
                if r.get("description"): fps.append(r["description"][:120])
                if r.get("insight"):     fps.append(r["insight"][:120])
    elif base == "data-enrichment.json":
        for it in (data.get("must_include_stats") or data.get("stats") or []):
            if isinstance(it, dict):
                if it.get("number") is not None: fps.append(str(it["number"]))
                if it.get("value")  is not None: fps.append(str(it["value"]))
                if it.get("claim"):  fps.append(it["claim"][:120])
                if it.get("source"): fps.append(it["source"])
        for it in (data.get("nice_to_have_stats") or []):
            if isinstance(it, dict):
                if it.get("number") is not None: fps.append(str(it["number"]))
                if it.get("claim"):  fps.append(it["claim"][:120])
    elif base == "serpapi.json":
        for r in (data.get("organic_results") or [])[:10]:
            if r.get("title"):    fps.append(r["title"])
            if r.get("snippet"):  fps.append(r["snippet"][:120])
        for q in (data.get("related_questions") or []):
            if isinstance(q, dict) and q.get("question"): fps.append(q["question"])
    elif base == "paa.json":
        for q in (data.get("related_questions") or data.get("questions") or []):
            if isinstance(q, dict) and q.get("question"): fps.append(q["question"])
            elif isinstance(q, str):                       fps.append(q)
    elif base.startswith("reddit-") and base.endswith(".json"):
        if isinstance(data, list) and len(data) >= 2:
            try:
                thr = data[0]["data"]["children"][0]["data"]
                if thr.get("title"):    fps.append(thr["title"])
                if thr.get("selftext"): fps.append(thr["selftext"][:200])
                for c in (data[1]["data"]["children"] or [])[:5]:
                    bt = (c.get("data") or {}).get("body") or ""
                    sent = re.split(r"[.!?]", bt)[0]
                    if sent and len(sent) > 20:
                        fps.append(sent[:200])
            except Exception:
                pass
        elif isinstance(data, dict):
            for thr in (data.get("threads") or data.get("signals") or data.get("results") or []):
                if isinstance(thr, dict):
                    if thr.get("title"):   fps.append(thr["title"])
                    if thr.get("insight"): fps.append(thr["insight"][:150])
    elif "quora" in base:
        if isinstance(data, list):
            for it in data:
                if isinstance(it, str):                        fps.append(it)
                elif isinstance(it, dict) and it.get("title"): fps.append(it["title"])
        elif isinstance(data, dict):
            for t in (data.get("titles") or data.get("questions") or []):
                fps.append(t if isinstance(t, str) else (t.get("title") or ""))
    elif base.startswith("competitor-") and base.endswith(".md"):
        for ln in (data.splitlines() if isinstance(data, str) else []):
            ln = ln.strip()
            if not ln: continue
            if ln.startswith("- ") or ln.startswith("* "):
                fps.append(ln.lstrip("-* ").strip())
            elif re.match(r"^#{1,3}\s+", ln):
                fps.append(re.sub(r"^#+\s+", "", ln).strip())
    out, seen = [], set()
    for f in fps:
        f = (f or "").strip()
        if 4 <= len(f) <= 250:
            k = re.sub(r"\s+", " ", f.lower().strip())
            if k not in seen:
                seen.add(k)
                out.append(f)
    return out


def check_source(src_path, body_lower, body_words, topic_nouns):
    fps = extract_fingerprints(src_path)
    distinctive_fps = [f for f in fps if _distinctive(f, topic_nouns)]
    if not distinctive_fps:
        return {"source": os.path.basename(src_path),
                "fingerprints_extracted": len(fps), "distinctive_fingerprints": 0,
                "matches_in_body": 0, "verdict": "EXEMPT_NO_DISTINCTIVE_CONTENT",
                "sample_matches": []}
    matches = []
    for fp in distinctive_fps:
        if _phrase_in_body(fp, body_lower):
            matches.append({"fp": fp[:120], "match_type": "substring"})
        elif _noun_overlap_in_body(fp, body_words, topic_nouns):
            matches.append({"fp": fp[:120], "match_type": "noun_overlap>=2_distinctive"})
    return {"source": os.path.basename(src_path),
            "fingerprints_extracted": len(fps),
            "distinctive_fingerprints": len(distinctive_fps),
            "matches_in_body": len(matches),
            "verdict": "USED" if matches else "CAPTURED_BUT_NOT_USED",
            "sample_matches": matches[:5]}


def main():
    if len(sys.argv) < 2:
        print(__doc__); sys.exit(2)
    folder = sys.argv[1].rstrip("/")
    if not os.path.isdir(folder):
        print(f"ERROR: not a folder: {folder}", file=sys.stderr); sys.exit(2)
    draft_path = os.path.join(folder, "draft-voice-passed.md")
    if not os.path.exists(draft_path):
        draft_path = os.path.join(folder, "draft-linked.md")
    if not os.path.exists(draft_path):
        draft_path = os.path.join(folder, "draft.md")
    if not os.path.exists(draft_path):
        print(f"ERROR: no draft in {folder}", file=sys.stderr); sys.exit(2)
    body = open(draft_path, encoding="utf-8").read()
    body_lower = re.sub(r"\s+", " ", body.lower().strip())
    body_words = set(re.findall(r"[a-z]+", body.lower()))
    topic_nouns = _topic_nouns(folder)
    patterns = ["ahrefs-keywords.json", "ahrefs-questions.json", "serpapi.json", "paa.json",
                "ai-mode.json", "forums.json", "videos.json", "quora-titles.json",
                "quora.json", "data-enrichment.json"]
    srcs = []
    for pat in patterns:
        p = os.path.join(folder, pat)
        if os.path.exists(p):
            srcs.append(p)
    srcs.extend(sorted(glob.glob(os.path.join(folder, "reddit-*.json"))))
    srcs.extend(sorted(glob.glob(os.path.join(folder, "competitor-*.md"))))
    report = {"folder": folder, "draft_used": os.path.basename(draft_path),
              "draft_words": len(body.split()), "topic_nouns": sorted(topic_nouns),
              "sources": []}
    for s in srcs:
        report["sources"].append(check_source(s, body_lower, body_words, topic_nouns))
    out_path = os.path.join(folder, "lineage-report.json")
    json.dump(report, open(out_path, "w", encoding="utf-8"), indent=2)
    print(f"\n=== lineage-check v3 (distinctive-fingerprint) -- {folder} ===")
    print(f"Draft: {os.path.basename(draft_path)} ({report['draft_words']} words)")
    print(f"Topic nouns excluded from distinctive check: {sorted(topic_nouns)}\n")
    print(f"{'Source':<40} {'Extracted':>10} {'Distinctive':>12} {'Found':>8} {'Verdict':<28}")
    print("-" * 100)
    silent_skips = []
    for s in report["sources"]:
        v = s["verdict"]
        if v == "USED":             mark = "OK "
        elif v.startswith("EXEMPT"): mark = "-- "
        else:                        mark = "!! "
        print(f"{mark}{s['source']:<37} {s['fingerprints_extracted']:>10} {s['distinctive_fingerprints']:>12} {s['matches_in_body']:>8} {v:<28}")
        if v == "CAPTURED_BUT_NOT_USED":
            silent_skips.append(s["source"])
    print()
    print(f"Wrote: {out_path}")
    if silent_skips:
        print(f"\nCAPTURED-BUT-NOT-USED ({len(silent_skips)}): " + ", ".join(silent_skips))
        sys.exit(1)


if __name__ == "__main__":
    main()
