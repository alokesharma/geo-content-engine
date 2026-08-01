---
name: draft
description: Write the body of a blog article from an outline and research brief, applying voice rules at write time rather than as post-hoc cleanup. Reads content_rules.md (voice charter + the consolidated rule set). v19 — target_specimen.md is retired; the few-shot specimens at the bottom of this file are the voice reference (calibrated to a non-expert reader, grade-7 plain English). Produces draft.md ready for FAQ building, internal linking, and voice pass. Use after outline.md. Triggers on "draft this article" or as part of content-gen-pipeline.
---

# draft

Writes the actual article from the outline. Applies the canon's voice rules at write time so the post-hoc voice-pass has less cleanup to do. **The voice reference is the few-shot specimens at the end of this file** (v19 — replaces the retired target_specimen.md). Read them before drafting and match their register.

---

## When to use

Third stage of the pipeline, after `outline` produces `outline.md`. Output feeds `faq-builder` (which appends the FAQ block), then `internal-linking`, then `voice-pass`.

---

## Inputs

- `outline.md` (from outline skill)
- `research-brief.md` (for numbers, primary-source citations, anchor facts)
- `content_rules.md` (voice charter + the consolidated rule set)
- The **v19 few-shot specimens** at the end of this file (the only voice reference; `target_specimen.md` is retired)

---

## Process

1. **Read the outline.** Section by section, identify the H2, the planned section tool, and the bullets/sub-points. (No bridge cue — bridges are retired per canon B4.)

**v9 (May 2026):** the canon was consolidated to ~26 rules in 8 groups. Key behaviour changes baked in here: educate, never sell (no "the brand is the right choice", no CTA pitch — canon A3/E1); surface your brand's facts only if real and relevant, woven in or as bullets, no "(Source: internal data)" tag (E1); the brand KB is a FACTUAL source (extract product/spec facts as bullets, strip the sales-script register — E2); never name a research source (Reddit/Quora) in prose (C6); never associate the brand with a negative (E3); headings in Title Case (B2); progressive disclosure, don't dump the manual (D4).

2. **Write the BLUF lede** (Rule #13). Single sentence. Sentence 1 IS the answer to the H1 question. No throat-clearing. No "In this article", "Today's", "Understanding".

2b. **Match the lede's SHAPE to the H1's question type (v21 — validate.py bluf_answer_shape).** A "How to / How do" H1 needs an ACTION-shaped answer ("To find the best value policy, compare three things: …"), never a definition ("The best value policy is the one that…" answers WHAT IS, not HOW TO). What-is → definition. Yes/No → Yes/No first word (existing bluf_yesno). Which/Best → the deciding criterion, not a circular restatement of the question.

3. **Optional stage-setter only (canon B3).** Do NOT write a mandatory 80-150 word stage-setter (that rule is retired). If the lede alone orients the reader, go straight to the first H2. If a short framing helps, keep it to 2-3 sentences, never boilerplate. Whole intro ≤ 3-4 short sentences.

4. **For each H2 section:**
    - Apply the planned section tool (prose / bullets / table / callout / steps)
    - **Comparison table (v22) — if the outline planned one (comparison topic), write it here:**
      - Format: a markdown table, `| Factor | <Option A> | Option B> |` shape, 5-8 rows, each cell a concise fragment (not full sentences). Place it inside the contrasting H2 section, right after that section's opening answer.
      - **Every cell is your brand's own wording.** The facts come from research (competitor scrapes + AI Mode + specs), but you rephrase them. **NEVER paste a competitor's table or copy cell wording verbatim — that is plagiarism/copyright infringement and a duplicate-content risk. Reword the fact.** Example: a source's "Works automatically and adjusts height at the press of a button" becomes "Raises and lowers on its own when you tap the preset."
      - Caption directly below the table: `Compiled from published <domain> specifications, <Month Year>.` Do NOT name competitor brands and do NOT write a `Source:` line that joins multiple publishers with "and"/"&"/"/" (the validator's `merged_citation` gate flags that).
      - Keep clean markdown pipes and no stray `[` `]`; build_doc renders it into a real Doc table. The validator excludes table rows from the prose word-count and register checks, so terse cell vocab is fine — but the anti-AI literal checks (dashes, curly quotes) still apply, so keep cells ASCII with no em/en dashes.
    - Use anchor numbers from research-brief; never invent specifics
    - If a claim doesn't have a number, hedge per Rule #14 ("typically", "in most cases") or rephrase to remove the quantifier
    - Cite the relevant regulator or standards body by name with the specific clause where the body needs it (Rule #5)
    - Apply the voice charter (content_rules.md §2): second person, active verbs, short sentences, no em/en dashes, contractions OK
    - Open the section on the reader's question/decision, not a mechanism (canon B4)
    - Headings in Title Case (canon B2)
    - Do NOT write a bridge sentence to the next section (canon B4 — bridges are retired)

5. **Apply Rules #18-#24 at write time** (the team-review additions):
    - No rhetorical setups ("the catch is", "the trap to watch", "binary", "knowing X is one thing")
    - No verb-repetition for emphasis ("Read it once. Read it again.")
    - Soft claim-denial language ("would not be payable under [clause]" not "almost certainly denied")
    - No dramatic punchlines as closing sentences

6. **DO NOT add** a reflective philosophical close (Rule #20). The article ends at the body, then FAQ, then Key Takeaways. No "Switch types aren't a gimmick…" paragraph.

5b. **Source citations carry a real linked URL (Rule #34).** Every stat ends with `Source: [Publisher](https://exact-source-url)` — the publisher name as a markdown link, using the URL captured in `research-brief.md` §7. Never write a bare `[Source]` label with no URL (that was the run-1 bug; voice-pass will hard-fail it). The delivery step converts these markdown links into real Doc hyperlinks.

7. **Write Key Takeaways** (Rule #17). Exactly 4 bullets with bold lead-ins (validator kt_exact). Different framing from the body; not copy-paste. This is the terminal section.

8. **Add a compliance/registration footer (if your domain needs one)** at the very end (Rule #6).

9. **Write the "as of [month, year]" footnote** where the article cites pricing, comparisons, or regulatory dates (Rule #7).

10. **Length = coverage, set by the SERP (v21).** There is no fixed word target. Read `length-target.json` (from research-flow): it gives a word BAND and a `section_target` (the median competitor H2-section count) computed from the pages actually ranking for this topic. **Drive length by COVERAGE, not by a word number:** cover every real sub-topic the competitors + AI Mode cover that's relevant — aim for `section_target` sections. The word band is a sanity check, not a goal. Two rules keep a longer article honest: each section stays within the per-section cap in `length-target.json` (no single section bloats), and every specific claim must trace to research (the grounding floor) — so extra length must be extra *real coverage*, never padding. A hard ceiling (2,800) FAILs only as a runaway guard; being below the band or below `section_target` FLAGs the article as too thin for the topic (the fix for the "guide capped too short" problem). Never pad to hit a number; never cut substance to stay short.

### v5 write-time rules (May 2026 — the reference-voice findings + 9 global fixes)

**v19 (May 2026) — these write-time rules are now subordinate to the few-shot specimens at the end of this file.** The earlier diagnosis was: the gap is *structural*. The v19 diagnosis is: the gap is *register* (a reviewer read v18.1 as too writerly for a layman). When this section's rules and the few-shot register conflict, the few-shot register wins.

11. **Lede may open with one human framing sentence** (canon Rule #3a). Name the reader's situation before the answer: "When you type for eight hours a day, a keyboard that fights you isn't really an option." Then give the BLUF answer. This situational sentence is encouraged and is NOT throat-clearing. Still cap the intro at 3-4 short sentences (Rule #39) and still delay any statistic (Rule #50).

12. **Open every section on the reader's question or decision, not a mechanism** (canon Rule #40). First sentence answers what they came for or names the choice they face: "If your current setup already feels comfortable, there's little reason to switch" — NOT "The actuation happens when the stem crosses the reset point." This is the single highest-impact change for killing the textbook feel.

13. **Write cohesion into the openings; do NOT manufacture bridge sentences** (canon Rule #3b). Forbidden: "Knowing the specs is half the story. Knowing what to do is the other half." / "Types are easier than mechanics. Here's how the switch actually fires." A clean H2 plus a strong first sentence carries it. The best reference writing uses zero bridges.

14. **Write exactly one expert verdict** (canon Rule #41). One opinionated, experience-based position grounded in real first-party data, e.g. "we find 7–8 of 10 buyers are happier with a tactile switch." If the figure isn't available, keep the verdict slot and attach the `[internal data needed — team to supply]` flag in the APPENDIX (step 17), never in the body.

15. **Plain words first** (canon Rule #42). Default to everyday vocabulary: "start date" not "commencement date"; "attached list" not "annexed list"; "has exceptions" not "nuanced". Domain terms (actuation force, travel, hot-swap, keycap profile) are allowed but glossed on first use (Rule #37). voice-pass runs the Dale-Chall check; write so it has little to flag.

16. **Stats: max 1, single-source, delayed, currency-stated, exact-metric** (canon Rules #43, #44, #48, #49, #50; v21 — the validator enforces external_stats_max: 1). Research-brief §7 supplies up to 2 candidate stats; the draft uses at most the 1 strongest. Each: one publisher per `[Source: …]`, no merged citations; placed no earlier than the third substantive paragraph; data vintage stated inline ("in 2024…"); labelled with the source's exact metric name (never relabel one metric as another).

17. **No internal placeholders in the body** (canon Rule #47). `[internal data needed]`, `[TBD]`, `[needed]` and any team-instruction bracket go ONLY in a "Team to supply" appendix at the very end of `draft.md`, after the registration footer. The body must read clean to a reader.

18. **One pillar interlink anchor** (canon Rule #45). Ensure the bare category name ("standing desks", "mechanical keyboards", etc.) appears once in the body as a natural phrase so internal-linking can link it to `https://www.example.com/<category>/`. Don't force it; most articles say the category name early anyway.

19. **Numbered FAQ + explicit advice.** The FAQ is built by faq-builder as a numbered list (Rule #46). In the body, prefer explicit guidance over hedged ambiguity where it's safe and accurate ("test the switch on a sample board before you buy the full set" beats "you may wish to consider testing it").

### v8 write-time rules (May 2026 — three-blog review)

20. **No H2 may restate the H1** (canon Rule #52). Don't open with an H2 that repeats the title question; the definitional answer is in the lede. The validator FAILs a near-duplicate H2.

21. **Verbatim keywords only** (canon Rule #53). Use only keywords that appear word-for-word in research-brief.md's real pulled sources (Ahrefs / PAA / related-searches / competitor headings / topic). Never invent or stitch a variant, and never let the SEO audit annotate a term "Ahrefs" unless it truly came from Ahrefs. The validator FAILs a made-up keyword.

22. **Expert verdict — no fabricated first-party experience** (canon Rule #54, extends #41). Use "in our experience"/"we find"/specific first-party numbers ONLY when real brand data is supplied. Otherwise drop the proprietary framing and invented specifics: hold the verdict with the `[internal data needed]` flag in the appendix, or make a general point with a cited external source. Never invent a proprietary stat.

23. **Model the BLUF on Google's AI Mode (canon G3, v12 #76 -- AI Mode retired). Paraphrase only -- never copy** (canon Rule #57). If research-brief §2b has a captured AI Mode, make the lede cover the same core question and sub-points it answers (raises AI-citation odds). NEVER copy phrasing — no verbatim span over ~8 words may match the AI Mode text.

24. **Source quality** (canon Rule #55). Cite primary sources (the relevant regulator or standards body, official manufacturer specs) directly, never a third-party aggregator's summary of them.

### v12 write-time rules (May 2026 — grounding + new sources)

25. **Evidence-first, not recall** (canon C8). Build each section from the research-brief's fetched material (competitor reads, Forums, Reddit/Quora, AI Mode, stats), not from memory. Tag every SPECIFIC claim (number, named rule, price, duration, "X%") with its source so the auditor can trace it. A specific claim you can't trace to a brief source should be cut or flagged — don't assert specifics from recall. The validator FLAGs numbers absent from the brief.

26. **Model the BLUF on AI Mode** (canon G3). Use brief §2b (Google AI Mode answer) to decide what the opening must cover and which sub-questions to answer — PARAPHRASE ONLY, no verbatim span over ~8 words. It shapes coverage, never wording.

28. **Facts-first, grounded ≥70% (v15, the data-majority rule).** Before prose, list every specific claim the article will make (numbers, named rules, prices, durations, the feature/spec items) and tag each to its research-brief source (competitor-N / forums / reddit / ai-mode / stat / official-source). Write prose ONLY from that tagged list. The validator computes a **grounding ratio** — specifics that trace to the paid data ÷ total specifics — and **FAILs below 70%** (delivery then refuses). Don't assert specifics from memory. The LLM owns the synthesis and voice; the data owns the facts and coverage. Floor is tunable in `style.json` (`grounding_floor`).

27. **Use the wider community pool** (v12). FAQ candidates and real-user body angles draw from Forums (§4.5) + Reddit/Quora, and video-transcript insights (§4.6) where genuine — never named in prose ("Reddit"/"a video" stay out of the body, canon C6).

---

## Output

`draft.md` — the full article body in Markdown. Does NOT yet include the FAQ block (faq-builder appends that next) but DOES include the Key Takeaways block at the end.

Also `draft-status.json` with PASS / FAIL + reason.

---

## Hard checks

- BLUF lede present (sentence 1 is the answer)
- Stage-setter only if it earns its place (optional per revised Rule #9; max 2-3 sentences; never boilerplate)
- No em/en dashes
- No forbidden phrases (from content_rules.md FORBIDDEN_PHRASES list)
- No phrases from Rule #18 ("the catch is", "the trap", "binary" used dramatically, "almost certainly denied", "will be voided")
- Every numeric claim traces to research-brief or is hedged
- Regulator/standards-body citations match research-brief regulation snippets exactly (no fabrication)
- Key Takeaways present, terminal
- Compliance/registration footer present (if your domain needs one)
- Length follows `length-target.json`: hit `section_target` sections within the SERP word band; hard ceiling ≤2,800 (FAIL); below band/section_target FLAGs as too thin. Coverage-driven, never padded.
- At least one non-commodity element present (real stat, worked scenario, or expert verdict) per Rule #29
- **No more than 1 externally-sourced statistic** (Rule #43; config external_stats_max: 1)
- **No statistic in the lede, stage-setter, or first section** (Rule #50)
- **No merged-publisher citations** like "[X / Y]" (Rule #44)
- **Exactly one expert verdict present** (Rule #41)
- **No internal placeholder brackets in body prose** — they belong in the Team-to-supply appendix only (Rule #47)
- **Bare vertical name appears once for the pillar link** (Rule #45)
- **Every stat states its data vintage inline and uses the source's exact metric name** (Rules #48, #49)

---

## What it prevents

- Hallucinated numbers (the v1 "40% increase" failure)
- Dramatic / copywriting register (the v2 failure that prompted the team review)
- AI tells getting past voice-pass cleanup
- Missing stage-setter (a real v1 failure)
- Forgotten registration footer

---

## Example writing

For the topic "what is a mechanical keyboard switch":

> # What is a mechanical keyboard switch?
>
> A mechanical keyboard switch is the spring-loaded mechanism under each key that registers a press. The exact feel depends on the switch type and its actuation force. For most keyboards, linear switches feel smooth, tactile switches give a bump at the point of activation, and clicky switches add an audible click on top of that bump.
>
> [stage-setter follows...]

This matches the v3 output the team approved. Use it alongside the v19 few-shot specimens below.

---

## Notes for the builder

- This is the longest-running skill in the pipeline (a guide topic can run ~2,000 words). Plan for 30-90 seconds of LLM time per run.
- Voice charter rules at WRITE time, not post-hoc. The voice-pass skill is the safety net, not the primary enforcer.
- Read the v19 few-shot specimens once at the start and hold their register in mind across sections (don't re-read per section).

---

## v19 few-shot specimens — the voice reference (READ FIRST)

These specimens replace the retired `target_specimen.md`. They show the exact register every article should hit. Match the **plain words, short sentences, direct answer, no narrator voice, no abstract group nouns**. Do not copy the topics or sentences; copy the register.

**Reader persona for every specimen:** an older, non-technical shopper who has never bought this kind of product and is not a confident reader. If a sentence below would lose them, you have failed.

### Specimen 1 — Definitional opener ("What is X?")

> A mechanical switch is the small spring-loaded part under each key that registers your press. Common types are linear, tactile, and clicky. If a switch gives a small bump halfway down, it is a tactile switch, even if it makes no sound.

Why this works: the definition is in sentence 1. No "If you've been typing for years…" wind-up. Plain words ("the small spring-loaded part under each key") instead of "the electromechanical actuation assembly beneath each keycap." Examples come right after the definition, not in a separate paragraph.

### Specimen 2 — Yes/No question opener

> Yes, most mechanical keyboards let you swap the switches yourself. The board uses hot-swap sockets, so you pull the old switch out and press a new one in without soldering. A cheaper board may have soldered switches that you can't change, so check the product page, not the photo on the box.

Why this works: "Yes" is sentence 1. The next sentence explains *why* in one line. The third sentence names the exception in one line. No "The answer is the socket design. A soldered board self-limits…" lecture.

### Specimen 3 — Concrete failure-mode paragraph (replaces v18.1's "Three failure modes turn a spec line…")

> Your new switches can still feel wrong even when the listing says the board is hot-swap. There are three common reasons.
>
> First, the board may not actually be fully hot-swap. Some makers use a cheaper socket to save money. That board still lets you pop a switch out, but it only fits a few switch types before the pins bend. The product page may say "hot-swap, no soldering" — both true — but full compatibility is just not there. Always check the product page, not the photo on the box.

Why this works: no "failure modes", no "spec line", no "they're worth knowing before you buy." Cause and consequence are stated plainly ("Your new switches can still feel wrong … there are three common reasons"). The reader is told what to do at the end of the paragraph (check the product page).

### Specimen 4 — Comparison ("How does X compare to Y?")

> With a membrane keyboard you press a soft rubber dome that flattens to register the key. With a mechanical keyboard you press a spring-loaded switch, so each key has a firmer, more consistent feel and lasts far longer. That is the single biggest practical difference between the two.

Why this works: the contrast IS the answer. One sentence each on the two sides, then one sentence on what it means. No "The mechanism is the dome collapse. A membrane self-limits…" detour.

### Specimen 5 — "What to do next" close

> The simplest check takes five minutes. Open the product page, search for the words "hot-swap" or "switch type", and see what is next to them. If it says "hot-swap" or "3-pin and 5-pin", you can change the switches from day one. If it says "soldered" or lists nothing, you are stuck with the switches it ships with. If you can't find the detail, message the seller and ask — that way you have it in writing.

Why this works: instruction is concrete (open the product page, search the words, look at what's next to them). Each option states what it means. No "the question that decides your build" framing. No "5-minute check" abstract framing — the *action* is the framing.

---

### What every specimen avoids (the v18.1 register problems)

- Abstract group nouns: "failure modes," "edge cases," "the small print," "the headline feature," "the technical definition," "the asymmetry."
- Narrator voice: "It's worth knowing," "It's worth understanding," "They're worth knowing before you buy," "The mechanism is X."
- Clever cause-effect constructions: "X turns Y into Z," "X makes the math work the other way," "What flips the math."
- Meta references to the document: "the brochure," "the spec line," "the headline." (Use "product page" only, and only when actually referring to a page.)
- Multi-sentence wind-ups before the answer: "If you've been typing for years, the question that decides your build is whether the maker calls it…"
- Compound abstract phrases: "actuated by a physical spring mechanism for which tactile feedback is produced" → "gives a bump when you press it."

If a sentence the LLM is about to write would *fit naturally* in v18.1 but not in these specimens, rewrite it.
