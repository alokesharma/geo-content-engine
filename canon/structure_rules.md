> Example canon — replace with your own brand's rules.

# Structural & SEO Rules

> Page classification, section types, HTML schema, design system, clustering, and rollout policy for the content engineering pipeline. Read by the `outline` and `seo-meta-builder` skills. Sister file to `content_rules.md` (voice and editorial rules).
>
> *Previously named `skill.md` — renamed to avoid confusion with Claude Code SKILL.md files. Same content; new name.*

---

## 1. Content & SEO Guidelines

### 1.1 Core Principle

Every fact, figure, policy detail, and claim statistic in the output **must come from the original crawled content**. The AI rewrites for clarity and scannability but **never fabricates** information. This is a cleaning exercise, not a content generation exercise.

### 1.2 Page Classification

Every page is classified into one of three types before any content restructuring begins:

| Type | Examples | Focus | Goal |
|------|----------|-------|------|
| **Transactional** | `/product-a/`, `/product-b/` | 90% conversion, 10% content | Get users into the funnel. CTAs above the fold and repeated throughout. |
| **Informational** | `/product-a/what-is-x/`, `/product-a/how-to-y/` | Full-depth education | Answer the user's question completely, build trust, then guide to funnel. |
| **Longtail** | `/product-a/specific-variant/`, `/product-a/niche-topic/` | Concise, specific | Narrow topic, specific intent. Link back to parent pillar page. |

### 1.3 Title Tag

- **50-60 characters.** Primary keyword near the front.
- Format: `[Topic] - [Benefit/Action] | Brand`
- Example: `What is X in Product A? How It Works | Brand`

### 1.4 Meta Description

- **150-155 characters.** Must contain the primary keyword AND a call-to-action.
- Write a compelling reason to click, not a dry summary.
- Example: `X determines the outcome and affects your result. Learn how it's calculated and how to get the best value. Check options instantly on Brand.`

### 1.5 H1 Tag

- Conversational, benefit-oriented. Should feel like answering a question.
- **Good:** "What is X and how does it affect your final cost?"
- **Bad:** "Understanding Factor X In Product A"

### 1.6 H2 Headings (Critical for AEO / Featured Snippets)

- Every H2 **must be phrased as a natural question** users search for.
- Use "What", "How", "Why", "When", "Which" question format.
- These become the voice-search and AI Mode answers (AIO retired v12 #76).
- **Good:** "How is X calculated for my order?"
- **Bad:** "X Calculation Method"

### 1.7 Internal Linking (Critical for SEO Equity)

- **Preserve every internal link** from the crawled data without exception.
- Embed them naturally in content using `<a href="...">descriptive anchor text</a>`.
- Group remaining links into a `related_articles` section at the bottom.
- Use descriptive anchors: "Read our complete guide to the standard plan" not "Read more".
- The `internal_links_footer` section must contain ALL unique internal links from the crawled page.

### 1.8 Structured Data / Snippet Targeting

- FAQ sections: clear question-answer pairs ready for FAQ schema markup.
- Steps sections: numbered and descriptive enough for HowTo schema.
- Each FAQ answer: self-contained (makes sense without reading the question).

### 1.9 What to Remove

- Keyword-stuffed sentences (same keyword 3+ times in one paragraph)
- Filler phrases: "In this article we will discuss...", "Let's explore...", "Read on to know..."
- References to images, infographics, or tables that don't exist in the crawled text
- Repetitive content (same information phrased differently across sections)
- Dense reference tables users can't act on (simplify into 3-4 key takeaway bullets)
- Generic disclaimers or boilerplate that appear on every page

### 1.10 What to Keep and Enhance

- All factual content (legal requirements, regulatory references, product specifics)
- Numerical data (price ranges, turnaround times, usage limits)
- Process steps (how to apply, how to renew, how to calculate)
- Real user-relevant advice (when to choose which plan, cost-saving tips)

---

## 2. User Experience Principles

### 2.1 Two User Personas

The content serves two distinct audiences simultaneously:

1. **High-intent users** (40-70% of traffic depending on product) - Want to check prices and buy immediately. Give them a frictionless path to the CTA with zero scrolling friction.
2. **Research-stage users** - Looking for information before making a decision. Give them scannable, trustworthy content that answers their questions, then funnel them.

### 2.2 Scannability Rules

- **No walls of text.** If a paragraph exceeds 3 sentences, break it up.
- If the original has a 500-word paragraph, restructure as: 1 intro sentence + bullet list of key points + 1 summary sentence.
- **Bold the first 2-4 words** of every bullet point as a scannable lead-in.
- Each bullet = ONE clear fact or action the user can act on.
- Paragraphs in content blocks: **3 sentences max**, then break.

### 2.3 Tone & Voice

**Conversational expert** - like a knowledgeable friend explaining the topic.

| Do | Don't |
|----|-------|
| Use "you" and "your" | Use "one should" or "the customer" |
| Active voice, present tense | Passive voice, hedging language |
| Short sentences (under 20 words) | Complex compound sentences |
| Confident but not salesy - inform first, sell second | Aggressive sales language or fear-based urgency |
| State facts directly | "It is pertinent to note that as per the stipulations..." |

**Good examples:**
- "A basic license is legally required to operate the tool commercially. Using it without one can lead to fines or a suspended account."
- "Your resale value drops each year as the product ages. A 3-year-old unit is worth roughly 70-75% of its original price."

**Bad examples (remove these patterns):**
- "It is pertinent to note that as per the stipulations of the applicable regulations..."
- "In this comprehensive guide, we shall delve into the intricacies of..."
- "Product A product A is important for product A owners buying product A..."

### 2.4 Content Depth Standards

Non-negotiable minimums:

| Page Type | Minimum Sections | Content Expectation |
|-----------|-----------------|---------------------|
| Transactional | 4-6 | Hero + Q&A overview + expert tip + CTA + FAQ + related articles |
| Informational | 5-8 | Full-depth coverage of the topic with body sections, takeaways, expert tips |
| Longtail | 3-5 | Quick answer box + focused article + FAQ + CTA |

Every page must have substantial, useful content. **No thin pages.**

### 2.5 Trust Signals

- **Authorship** is critical for blog posts and thought leadership content but unnecessary on core transactional pages (per product team decision).
- Transactional pages: product authority via trust badges, claim stats, review scores.
- Informational pages: author name, reviewer name, date, credentials.
- Longtail pages: author badge, quick attribution.

### 2.6 CTA Strategy

CTAs are tiered by priority:

| Priority | Action | Placement |
|----------|--------|-----------|
| Primary | Enter funnel (Check Prices / Get Quote) | Hero, sticky bar, mid-content, bottom |
| Secondary | Navigate to pillar page | After content sections |
| Tertiary | Read related articles | Bottom of page |

For transactional pages, the "Check Prices" CTA should be visible without scrolling.

---

## 3. Information Architecture Specs

### 3.1 Page Hierarchy

```
example.com/
  product-a/                              <- Pillar page (transactional)
    premium-product-a/                    <- Informational
    basic-product-a/                      <- Informational
    what-is-x/                            <- Informational
    support/                              <- Informational
    variant-name/                         <- Longtail (brand + product)
    niche-add-on/                         <- Longtail (niche topic)
    10-basic-tips/                        <- Longtail (content)
```

### 3.2 Authority Flow

- Homepage authority flows to main SEO pillar pages via "Our Products" section links in the body.
- Pillar pages link down to informational and longtail children.
- Longtail pages link back UP to their parent pillar page.
- Informational pages cross-link to related informational siblings and to the pillar page.

### 3.3 Section Types & When to Use

| Section Type | When to Use | Content Shape |
|-------------|------------|---------------|
| `hero` | **Always first.** Every page. | 2-3 sentence hook with primary keyword. |
| `qa` | When 3+ H2s can be restructured as question-answer cards. | Cards with question title, 3-5 bullet answers with bold lead-ins, CTA link. |
| `content_block` | Rich explanatory paragraphs. | HTML: `<p>`, `<strong>`, `<a href>`, `<ul>`/`<li>`. 2-3 sentences per paragraph max. |
| `bullet_list` | Lists of features, requirements, documents, benefits. | Items with **bold lead-in phrase** followed by detail. |
| `steps` | Sequential processes (how to claim, renew, calculate). | Numbered steps with title + description. |
| `comparison` | Comparing two options (premium vs basic tier). | Two-column table with feature/checkmark format. |
| `table` | Structured data useful to users (price ranges, tiers). | Max 6-8 rows. Must be actionable, not academic. |
| `expert_tip` | When content contains expert-level advice. | Quote attributed to a named advisor. |
| `faq` | **Always.** Every page. | 5-8 questions with self-contained 2-4 sentence answers. |
| `cta` | **Always second-to-last.** | Clear conversion prompt relevant to the page topic. |
| `related_articles` | **Always last.** | 3-6 article cards built from the page's internal links. Title + 1-line description. |

### 3.4 Section Ordering

Follow this hierarchy on every page:

```
1. hero                  (always first)
2. qa                    (overview cards - transactional/informational only)
3. content_block         }
   bullet_list           } the educational content
   steps                 } ordered by user journey logic
   comparison            }
   table                 }
4. expert_tip            (after main content, before FAQ)
5. faq                   (near bottom - catches long-tail queries)
6. cta                   (always second-to-last)
7. related_articles      (always last)
```

### 3.5 Template Selection

The system auto-selects the correct HTML template based on page classification:

| Classification | Template | Layout |
|---------------|----------|--------|
| Transactional | `transactional.html` | Sticky nav + hero with CTA + trust badges + Q&A cards (horizontal scroll mobile) + plan cards + add-ons + premium calculator + social proof + how-to steps + comparison table + FAQ accordion + article grid + sticky mobile CTA |
| Informational | `informational.html` | Breadcrumb + article hero with author/reviewer + two-column layout (main + sticky TOC sidebar) + body sections with key takeaways + mid-article CTA + related articles + internal links + FAQ accordion + author bio |
| Longtail | `longtail.html` | Breadcrumb + compact hero + quick answer box (AEO optimized) + narrow article body + related topic pills + FAQ accordion + CTA + slim footer |

### 3.6 Keyword Intent Spectrum (from meeting notes)

- ~20% of searches include the brand name ("brand product a")
- ~80% are non-branded ("product a", "product a online", "buy product a")
- Both are largely **commercial intent** - primary action is checking the price
- Conversion rates by product (illustrative):
  - Product A: ~40-45%
  - Product B: ~60-70%
  - Product C: ~20-30%
  - Product D: ~30-40%

---

## 4. Visual Design Details

### 4.1 Design System (from Final.pdf)

| Token | Value |
|-------|-------|
| Font | Inter, weights 400-900 |
| Primary purple | `#522ED3` |
| Dark text | `#1A1A2E` |
| Body text gray | `#4B5563` |
| Subtle caption gray | `#6B7280` |
| Section background (alt) | `#F9FAFB` |
| Border gray | `#E5E7EB` |
| Success green | `#10B981` |
| Accent blue | `#3B82F6` |
| Card border-radius | 12-16px |
| Card shadow | `0 1px 3px rgba(0,0,0,0.08)` |
| Container max-width | 1200px |
| Container padding | 0 24px |
| Section vertical padding | 72px |
| Button padding | 12-14px 28-32px |
| Button border-radius | 8-12px |
| Breakpoint (mobile) | 768px |

### 4.2 Component Patterns

**Hero (Transactional)**
- Dark gradient background (`#1A1A2E` to `#2D2B55`)
- Large H1 (2.8rem, weight 900, white)
- Subtitle in muted white (rgba 255,255,255,0.85)
- Primary input field + "Check Prices" purple button
- Trust badges strip below (white bg, subtle shadow)

**Hero (Informational)**
- Light background, left-aligned
- Product label pill (purple bg, white text, uppercase, small)
- H1 in dark (2.4rem, weight 800)
- Meta description as intro paragraph
- Author + reviewer badges with avatar initials, name, title, date

**Q&A Cards**
- Horizontal scroll container on mobile
- Each card: white bg, 16px border-radius, subtle shadow
- Question as H3 (1.1rem, weight 700)
- Answers as `<ul>` with bold lead-in per bullet
- CTA link at bottom (purple, with arrow)
- Min-width 300px per card

**Plan Cards**
- Grid layout (4 columns desktop, 1 mobile)
- "Most Popular" badge: purple bg, white text, positioned top-right
- Plan name in H3
- Description paragraph
- Feature list with green checkmarks
- Purple CTA button full-width at bottom

**Expert Tip Callout**
- Purple left border (4px)
- Light purple background (`#F3F0FF`)
- Quote icon or "Expert tip" label
- Quote text in slightly larger font
- Attribution: name + title below

**Key Takeaway Box (Informational/Longtail)**
- Purple left border (4px solid `#522ED3`)
- Light purple bg (`#FAF5FF`)
- "Key Takeaway" label (purple, bold, small)
- Content text

**Quick Answer Box (Longtail - AEO Optimized)**
- Purple gradient left border
- "Quick Answer" label
- 2-3 sentence direct answer optimized for featured snippets
- Appears immediately after hero, before article body

**FAQ Accordion**
- Clean white cards with subtle border
- Question as button with +/- toggle
- Answer hidden by default, slides open on click
- Purple highlight on active question

**Sticky TOC Sidebar (Informational)**
- 280px width, sticky positioning
- "IN THIS ARTICLE" label (purple, uppercase, small)
- List of H2s as links
- Active section highlighted with purple left border
- Smooth scroll on click

**Step Cards**
- Numbered circles (purple bg, white number)
- Title in bold
- Description in body text
- Connected by vertical line or horizontal progression

**CTA Banners**
- Purple gradient background
- White text: headline + subtitle
- White button with purple text ("Check Prices")
- Sticky mobile CTA bar at bottom of viewport

**Article Cards**
- 3-column grid (1 column mobile)
- White card with subtle shadow on hover
- Title (weight 700) + description (2 lines, gray text)
- "Read full guide" link in purple

### 4.3 Typography Scale

| Element | Size | Weight | Color |
|---------|------|--------|-------|
| H1 (hero) | 2.4-2.8rem | 800-900 | `#1A1A2E` or white (dark bg) |
| H2 (section) | 2rem | 800 | `#1A1A2E` |
| H3 (card/sub) | 1.1-1.25rem | 700 | `#1A1A2E` |
| Body text | 1rem (16px) | 400 | `#4B5563` |
| Caption/label | 0.75-0.85rem | 600-700 | `#6B7280` |
| Button text | 0.95rem | 600 | white or `#522ED3` |
| Bullet lead-in | inherit | 700 (bold) | `#1A1A2E` |

### 4.4 Responsive Behavior

- **Desktop (>768px):** Full grid layouts, sidebar TOC, horizontal Q&A cards
- **Mobile (<=768px):** Single column, horizontal scroll for card arrays, hamburger nav, sticky bottom CTA bar, collapsed sidebar

### 4.5 Accessibility

- All interactive elements keyboard-navigable
- Sufficient color contrast (4.5:1 minimum)
- Semantic HTML (`<article>`, `<section>`, `<nav>`, `<main>`)
- FAQ accordions use `<button>` with aria-expanded
- Images would use descriptive alt text (when applicable)

---

## Appendix: JSON Output Schema

The AI returns a single JSON object with this structure:

```json
{
  "page_classification": "transactional | informational | longtail",
  "page_title": "50-60 char SEO title",
  "meta_description": "150-155 char meta with CTA",
  "canonical_url": "from crawled data",
  "breadcrumb": [{"text": "Home", "url": "/"}, {"text": "Product A", "url": "/product-a/"}],
  "product_label": "PRODUCT A",
  "h1": "Conversational, benefit-oriented H1",
  "subtitle": "1-2 sentence value proposition",
  "author": {"name": "Name", "title": "Role"},
  "reviewer": {"name": "Name", "title": "Role"},
  "sections": [
    {
      "type": "hero | qa | content_block | bullet_list | steps | comparison | table | expert_tip | faq | cta | related_articles",
      "heading": "Question-format H2 or null",
      "content": "{ varies by type - see section specs above }"
    }
  ],
  "internal_links_footer": [{"href": "url", "text": "descriptive anchor"}]
}
```

---

## 5. Content Clustering & Generation Workflow (Blog-Writing Agent)

### 5.1 Mental Model Shift

Legacy approach: rewrite each page 1:1.
New approach: use 3,500 legacy pages as **raw research material** to build a question-led content engine.

- Pages are **grouped by consumer intent**, not URL structure
- Each cluster produces **new articles** (not rewrites) answering real search questions
- Old pages are gradually sunset via 301 redirects once new content is indexed

### 5.2 Clustering Logic

Group pages by the underlying consumer question, not by product path.

**Primary clusters (product A):**

| Cluster | Intent | Example queries |
|---------|--------|----------------|
| `buy-new` | First-time purchase | "how to buy product a online", "cheapest product a" |
| `renew` | Expiry / lapse | "product a renewal before expiry", "grace period product a" |
| `claim` | File / track / appeal | "how to get support for product a", "self-serve vs assisted" |
| `coverage` | What's included/excluded | "what does the premium tier include", "advanced add-on" |
| `compare` | Brand vs competitors / plan tiers | "brand vs competitor product a", "premium vs basic tier" |
| `how-it-works` | Education / jargon | "what is x", "what is the loyalty discount" |
| `regional` | City/region-specific queries | "product a in london", "regional availability" |

Each cluster has:
- One **pillar page** (Opus, full transactional or deep informational)
- 3–8 **supporting pages** (Sonnet, informational depth)
- N **longtail pages** for specific sub-questions (Haiku, 600–900 words each)

Internal links: longtail → supporting informational → pillar → quote funnel.

### 5.3 Model Tiering

| Page value | Model | Rationale |
|-----------|-------|-----------|
| Transactional pillar pages | `claude-opus-4-20250514` | Highest conversion value; needs best reasoning |
| Top informational pages (cluster pillars) | `claude-sonnet-4-20250514` | High SEO value; good quality/cost balance |
| Longtail / question pages | `claude-haiku-4-5-20251001` | High volume, lower unit value; speed matters |

### 5.4 Evaluation Checklist (before publishing)

- [ ] Primary keyword in H1, title tag, and first 100 words
- [ ] All H2s on informational pages phrased as full questions
- [ ] FAQ section has ≥ 5 Q&A pairs with question-format H3s
- [ ] At least one comparison table or structured list present
- [ ] Author/reviewer bar populated with name + credential
- [ ] Internal links ≥ 3 (no placeholder or bare `/` URLs)
- [ ] No paragraph exceeds 4 lines on desktop
- [ ] Primary CTA appears above the fold AND at least once below
- [ ] Length matches the SERP-derived target in `length-target.json` (v21): hit `section_target` H2 sections within the word band; runaway ceiling 2,800. Length is topic-driven and coverage-led — never pad to a number; never cut substance to stay short.
- [ ] No legalese in main body (T&C only in accordions/footnotes)
- [ ] No fabricated statistics or policy details not present in source data

### 5.5 Rollout Batches

1. **Batch 1 (pilot):** 20 highest-traffic transactional pages → manual QA → A/B test vs legacy
2. **Batch 2:** Top 100 informational pages by organic impressions (GSC data)
3. **Batch 3:** Remaining informational + top 500 longtail
4. **Batch 4:** Full longtail sweep; begin sunset redirects for legacy pages

### 5.6 Sunset Policy

Legacy page → 301 redirect to new page after 90 days **only if:**
- New page has been indexed (GSC confirmation)
- New page CTR ≥ legacy page CTR over same query set
- No keyword cannibalisation signal in GSC (check for overlap in queries report)

---

## Appendix: JSON Output Schema

The `content` field shape varies by section type:
- `hero`: `{"text": "intro paragraph"}`
- `qa`: `{"cards": [{"question": "", "answers": [{"bold": "", "detail": ""}], "cta_text": "", "cta_url": ""}]}`
- `content_block`: `{"html": "<p>...</p>"}`
- `bullet_list`: `{"items": ["**Bold lead:** detail", ...]}`
- `steps`: `{"steps": [{"title": "", "description": ""}]}`
- `comparison` / `table`: `{"headers": [...], "rows": [[...], ...]}`
- `expert_tip`: `{"quote": "", "name": "", "title": ""}`
- `faq`: `{"items": [{"question": "", "answer": ""}]}`
- `cta`: `{"heading": "", "description": "", "button_text": "", "button_url": ""}`
- `related_articles`: `{"articles": [{"title": "", "description": "", "url": ""}]}`
