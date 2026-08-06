# Paper Plant — cold design review

**Reviewer:** ColdEye · **Date:** 2026-08-05 · **Build:** http://localhost:8721
**Method:** shared Chrome via CDP, own tab, 1440×900 and 1024×900 emulated, DPR 2. Walked Home → load *PV + Electrolysis* → Inputs (Project, Time, Photovoltaic, Capital Cost, Discounted Cash Flow) → Flowsheet → Run → Source → Report. All colours, sizes and geometry below are measured off the live DOM, not eyeballed.

---

## 0. Verdict in one paragraph

There is a real point of view here, and it is a good one: warm paper ground, monospace for anything the machine computed, a dark instrument slab for the answer, family colour-codes for plugin types, and copy that keeps promising reproducibility. On the Run screen that point of view lands hard — the readout card and the Σ-reconciled cost table are the best UI I've seen in a Streamlit app. Then you walk two screens left and the same design language falls apart: **the Inputs screen has literally zero visual difference between an editable field and a printed value** (`border: 1px solid #FFF` on `background: #FFF`, and no hover state), a blanket `margin-bottom: -16px` puts a **7–8 px overlap under every kicker and heading in the app**, the primary button fails contrast at **2.88:1**, and the default Streamlit **Deploy** button and **⋮** menu are still sitting in the top-right of every screen. So: credible and sleek in flashes, unintentional in the aggregate. It currently reads as *a designer's mockup rendered by a framework that keeps leaking through*. The gap between the Run screen and the Inputs screen is the whole review.

---

## 1. First impression / aesthetic verdict

**What earns praise**

- The ground is right. `#FAF7F0` paper, `#26251F` warm near-black ink, `#55524A` muted. Nothing is pure white or pure black in the type system — a discipline most people claim and few keep.
- The **readout card** (`.pp-readout`) is the single best object in the product: `#191A17` slab, `4.1943` at **49.6 px monospace 600 with `font-variant-numeric: tabular-nums`**, and — the detail that shows real taste — the numeral is coloured `rgb(250,247,240)`, i.e. **the paper colour used as ink on the dark card**, not `#FFF`. That's a deliberate, correct choice.
- The **Σ row** on the cost table: `Σ | 4.1943 | ✓ matches readout`. A total that audits itself against the headline. For scientists this is worth more than any chart. Keep it, and make more of it.
- Copy is genuinely well written and confident: *"Every screen is a view of that file, and the file you download reproduces what you see, exactly."* / *"The single source of truth — running it in pyH2A directly reproduces these numbers exactly."* Very few technical tools write this well.
- Proper typographic minus (U+2212) in `−0.0693` on the Run table. Somebody cared.

**What undercuts it immediately**

- **The Deploy button and the ⋮ main menu are still there** (`stAppDeployButton`, `stMainMenu` present on every page). They are the *only* things in the top-right, so they are effectively the app's masthead. Nothing else destroys the "this is a considered instrument" illusion faster. `stSidebarCollapseButton` (the floating `«` / `»`) and Streamlit's heading anchor-link element (`stHeaderActionElements`, 1 instance on `/Inputs`) are also unhidden.
- **The display face is Streamlit's default.** `h1` computes to `"Source Sans", sans-serif, "Source Sans", sans-serif` (note the duplicated stack — sloppy). The editorial feel is coming entirely from layout and colour; the type is doing none of the work. Meanwhile `--mono` resolves to `ui-monospace, "IBM Plex Mono", …`, so **on macOS you get SF Mono and IBM Plex Mono never renders** — the intended mono voice is not the one shipping. And inline `code` uses a *third* family, `Source Code Pro` at 10.32 px.
- Three near-whites with no ladder: page `#FAF7F0`, buttons `#FEFDFB`, tables and inputs **`#FFFFFF`**. The tables are unpainted Streamlit defaults sitting cold on a warm page — a 5/8/14 delta that reads as "unstyled", not "elevated".
- Two default Streamlit colour leaks survive: `st.info` at `#E7EBF2` (a cool blue-lavender bar, the most jarring colour in the product) and `st.code` at `#F8F9FB` with `#158237` green text — both cool-toned, both on a warm page.

---

## 2. Visual hierarchy and typography

**What reads first, per screen:**

| Screen | First read | Should be |
|---|---|---|
| Home | `Levelized cost of product, from one markdown file` (44 px) | fine |
| Inputs / Time | `Time` (44 px) | fine |
| Run (pre) | `Run` (44 px H1) | the **Run ▸** button |
| Run (post) | `4.1943` | correct |
| Report | `PV + Electrolysis — levelized cost report` (the *preview's* H1) | `Report` |

**Specific failures**

- **The Home page inverts its own hierarchy.** Card title 16 px/600, description **12.48 px**, and the LCOH — the one number the whole card exists to communicate — is **13.44 px monospace 400 in `#55524A` muted grey**. The decision-relevant number is 0.9 px bigger than the throwaway description and *less contrasty than the title*. It should be the second-largest thing on the card.
- **Four decimal places everywhere.** `4.1943`, `139.4189`, `185.4433 USD/kg`. On the comparison row this is precision theatre — nobody chooses a pathway on the 4th decimal of $139/kg. Worse, `PV Electricity (LCOE) · 0.0286 USD/kWh` sits in the same row with a **different denominator** and no visual flag; a reader scanning the row will read 0.0286 as the cheapest hydrogen.
- **Run page says "Run" three times** in 160 px of vertical space: the button, the H1, and the caption "Runs the full workflow and reads the levelized cost." Then the H1 *disappears* after you run — the page loses its title on state change, which no other page does.
- **The Report preview competes with the page.** `PREVIEW — THE PRINTOUT` is followed by an H1 that renders at app-chrome scale in app-chrome type, with no sheet, frame or scale reduction. The export preview outranks the page it lives on.
- **Kickers are mushy.** `START FROM A REFERENCE PATHWAY`, `NEEDS INPUT HERE`, `AVAILABLE AT THIS POINT — REFERENCE ANY OF IT`, `WHERE IT GOES — COST COMPOSITION`, `RESULTS EXPLORER`. Same weight, same size, same colour, whether they label a section, an instruction, or a filter. And two of them are bad copy: `NEEDS INPUT HERE` reads like a `TODO` left in the template (and it appears above tables that are mostly *computed references*, e.g. Photovoltaic), and `AVAILABLE AT THIS POINT — REFERENCE ANY OF IT` is a sentence pretending to be a label.

---

## 3. Density and rhythm

**Systematically broken — one CSS rule causes it.** Every Streamlit markdown wrapper (`.st-emotion-cache-3uwfjr`) carries **`margin-bottom: -16px`**. Measured overlaps on the live page:

| Pair | Wrapper bottom | Next top | Overlap |
|---|---|---|---|
| `/Inputs` H1 `Project` → subtitle | 693 | 686 | **7 px** |
| `/Flowsheet` kicker → H1 | −158 | −165 | **7 px** |
| `/Flowsheet` H1 → legend chips | −77 | −84 | **7 px** |
| `SHARED BUSES` kicker → bus chips | 561 | 553 | **8 px** |
| Edge-inspector prose → code block | 693 | 686 | **7 px** |

With single-line content the overlap hides inside the line box and just looks "tight". The moment the upper element **wraps to two lines or the lower element has a background**, it becomes a visible collision. The Edge Inspector is the smoking gun: *"…resolved at Battery's position **(forward reference).**"* has its second line painted **under** the `#F8F9FB` code block. That is a shipped, visible spacing collision, and it is one rule away from being fixed everywhere.

**Other rhythm problems**

- **The wall of drawers.** Run's Results Explorer is ~30 accordion bars, each 40 px with a 6 px gap, ~2,600 px tall, all identical, no counts, no preview, no grouping, no "has results" marker. Inputs pages append the same treatment ("AVAILABLE AT THIS POINT", 22 expanders on `/Inputs` alone, alphabetised). After a 27 ms run, the researcher's reward is 143 px of readout, 430 px of table, and then 2,600 px of closed identical boxes. The signal-to-chrome ratio is inverted.
- **Card-in-card.** `/Inputs` Project: `stExpander` (1 px border, 8 px radius) containing an 18 px inset `<table>` with its own border and white fill. Two frames, one dataset. The Functional Unit section is *one row of data* inside two nested boxes.
- **Cramped: the submit button.** On `/Inputs → Time`, `Apply changes` sits **~2,000 px below** the first editable field, inside the card, with ~8 px of air between it and the last table row. It collides optically with "Working Capital (fraction of yearly change in operating costs)" above it.
- **Loose: the readout card.** 1,268 × 143 px, content occupies the left ~700 px. 45 % of the app's hero object is empty dark. Same on Home: the page ends at ~700 px of a 900 px viewport, and the upload zone is a 780 px-wide bordered box holding one 93 px button.
- **Loose: Run pre-state.** 700 px of nothing below a 56 × 40 px button.
- **No row rhythm in the input tables.** 53 px pitch, four columns, **no hairlines, no zebra, no row hover.** The eye has to carry "Federal taxes" across 900 px of empty space to reach its unit. On a 60-row form.

---

## 4. Affordances — the single worst problem

**You cannot tell what is editable. At all.**

Measured on `/Inputs → Time`, which has **60 `<input>` elements**:

``
input[value="20"]
  font: 13.76px ui-monospace     color: #26251F
  background: transparent
  parent .stTextInputRootElement
    background: rgb(255,255,255)
    border:     1px solid rgb(255,255,255)   ← white border on white fill
``

- **At rest:** indistinguishable from printed text.
- **On hover:** I verified it — `border` stays `1px solid rgb(255,255,255)`. **No hover state exists.** The only signal is the I-beam cursor, which requires you to already suspect.
- **On focus:** `1px solid #74A648`. Contrast of that border against its own white fill: **2.88:1** — below the 3:1 WCAG 1.4.11 floor for non-text UI. The one affordance that exists is sub-threshold.

Consequence: a scientist opens the Time plugin, sees a beautifully typeset read-only table, and never discovers that the entire product is editable. This is not a polish issue; it's a "the app appears not to work" issue.

**Secondary affordance failures**

- **The Results Explorer filter field is invisible *and* has no focus indicator.** `background: #FFF`, `border: 1px solid #FFF`, and when tabbed to: `outline: none`, `box-shadow: none`. Placeholder `filter tables and rows…` floats as grey text on white. A focused input with zero focus indication is a flat WCAG 2.4.7 failure.
- **The empty state's only action is invisible.** `Go to Load` is an `<a>` with no underline, no colour, no chevron, no button — it renders as body copy. (Its computed `color` is `rgb(0,0,238)`, the *UA default* — nobody styled the element; an inner span happens to override the paint.)
- **The primary action is not obvious on any input screen.** `Apply changes` is off-screen for 90 % of the editing session, with the only hint being Streamlit's default in-field microcopy "Press Enter to submit form" — which also **overlaps the `VALUE` column header** when the field grows on focus.
- **Label drift on the same operation:** `Apply changes` (Inputs) vs `Apply` (Source). And `Open` × 5 on Home, all identical ghost buttons at 243 px full-column width, which makes a set of *pathway cards* read as a *form*.
- **Focus ring is too weak everywhere else:** `box-shadow: rgba(116,166,72,0.5) 0 0 0 3.2px` on `#FAF7F0` ≈ **1.8:1**.
- The `<textarea>` on Source has the **browser's default resize grip** in the corner.

---

## 5. Colour — accent discipline is not working

**Measured palette**

| Token | Value | Where |
|---|---|---|
| Page / sidebar | `#FAF7F0` | everywhere |
| Ink / muted | `#26251F` / `#55524A` | everywhere |
| Accent | `#74A648` | primary button, focus border, focus ring, `USD/kg`, `LCOH`, active rail dot, *and* series colour #5 |
| CLOCK | `#3D5A8F` | Time, DCF |
| SUN | `#D98E2B` | Photovoltaic |
| LEDGER | `#8D74B8` | Capital Cost |
| Nav active | `rgba(219,183,128,0.25)` | sidebar pill |
| Readout | `#191A17` | Run |

**Problems**

1. **`#74A648` is doing five unrelated jobs**: "this is the primary action", "this element has focus", "this is a physical unit", "this is the metric name", and "this is the Principal-payment cost component". A reader can't learn what green means because it doesn't mean anything.
2. **The family colours communicate nothing.** They appear in exactly one place — an 11.52 px chip above the H1 — and nowhere else. They do not tint the workflow rail (all 18 dots are identical grey/green), do not group the rail, do not tint the plugin card. Meanwhile the *Flowsheet* uses them properly on node borders and edges, proving the system works when it's applied. This is the biggest unclaimed win in the product.
3. **The family taxonomy reads arbitrary.** `Capital Cost` = LEDGER (violet), but `Discounted Cash Flow` = **CLOCK** (navy). The money plugin is not in the money family.
4. **Two of three family chips fail contrast** at 11.52 px/600 white text:
   - `SUN #D98E2B` → **2.67:1** ✗
   - `LEDGER #8D74B8` → **3.95:1** ✗
   - `CLOCK #3D5A8F` → 6.87:1 ✓
   Which is why SUN reads washed-out and CLOCK reads solid — the "family code" has inconsistent visual weight, so it can't be scanned.
5. **The primary button fails: white on `#74A648` = 2.88:1** at 16 px/400. Fails AA (4.5:1) and fails even the 3:1 large-text floor. This is the Run button. This is the Apply button.
6. **The 11-series cost palette has a duplicate.** `Initial equity depreciable capital` and `Non depreciable capital` are **both `#8D74B8`**. The largest component and the smallest share a swatch, in a legend-by-colour-dot table. The palette wrapped around and nobody checked.
7. **Three near-indistinguishable blues** in that same 11-way scale: `#24365B`, `#3D5A8F`, `#3E7CC4` — at 8 px dots and in 20 px bar slivers they are one colour.
8. **The series palette re-uses the family colours** for unrelated meanings, so `#3D5A8F` means "CLOCK family" on Inputs and "Replacement costs" on Run.
9. `Display Parameters → Color → darkblue` is rendered as **plain monospace text with no swatch**, in an app that otherwise cares about colour semantics.

---

## 6. The readout card and cost table — instrument-grade or dashboard-generic?

**Instrument-grade, with three fixable flaws.** This is the part of the app that justifies the whole design direction.

Right:
- 49.6 px mono 600, `tabular-nums`, paper-ink on `#191A17`.
- Kicker `LEVELIZED COST OF PRODUCT · PV + ELECTROLYSIS` at 11.52 px / `0.92px` tracking — restrained, correct.
- Provenance line `run 27 ms · 17 plugins · 0 warnings` — three facts a scientist actually wants, no chrome.
- Cost table: mono uppercase headers, `+1.2915` / `−0.0693` sign-aligned with a real minus, 32 px pitch, hairline rules, a stacked composition strip whose segment order maps to the row dots, and the **Σ / ✓ matches readout** self-audit.

Wrong:
1. **`= LCOH`** is cryptic. The `=` reads as a broken equation. `metric: LCOH` or just `LCOH`.
2. **45 % of the card is empty.** There is an obvious right-hand slot for the thing this audience always wants next: the comparison. `vs. reference 4.1943 · Δ 0.0000`, or the previous run, or the DOE target. Right now the card is a wide box holding a left-aligned number.
3. **`+0.0%`** for a `+0.0013` component. Show `<0.1%`.
4. Radius `4px` on the readout vs `8px` on every other surface vs `3px` on family chips. Three radii, no reason.
5. The strip's right-hand tail is 4–5 unlabelled 6-px slivers.

**And then the Results Explorer tables are the opposite of instrument-grade.** Opening `Electrolyzer` gives a 9-column grid where **four columns — `YEAR_VALUE`, `PRODUCTION_VALUE`, `PATH`, `DURATION_VALUE` — are empty for every row** and eat ~40 % of the width, while `NAME` is squeezed to ~90 px so "Power requirement increase per year" wraps to four lines. The headers are raw `snake_case` (the only snake_case in the product). And each `REFERENCE` cell fragments into **three separate green chips** because the inline `code` background wraps mid-token:

``
{Electrolyzer >
Nominal power >
Value, kW}
``

Three pills for one reference. Plus this table is a fully bordered grid while every table on `/Inputs` is hairline-only — **two table styles in one app.**

---

## 7. Sidebar and workflow rail

**Nav (top block) — good.** Five to six items, 16 px, 34 px pitch, active state `rgba(219,183,128,0.25)` full-width warm pill with weight 600. Quiet, legible, correct. The `PV + Electrolysis` / `17 plugins · functional unit [kg]` identity block below the rule is excellent, and `last run / 4.1943 USD/kg` persisting into the sidebar after a run is exactly right.

**Problems**

- **The nav grows silently.** `Flowsheet` appears after loading a project; `Report` appears later still. No animation, no marker, no explanation — items just materialise between existing ones.
- **The nav lies after state loss.** When the session drops, the sidebar still advertises `Flowsheet` and `Report` while the body says *"Load a pathway first."* Every one of those links dead-ends.
- **The workflow rail is a radio group, and it looks like one.** 18 items, each with a 16 px empty ring. A column of unchecked circles reads as *"nothing is configured yet"*, not *"you are here"*. It is a navigation control wearing a settings control's clothes. Make it a list with a 2 px left status bar per row.
- **The rail throws away its own structure.** The positions encode a hierarchy — `200 · Inflation` owns `201–205`, `300 · Production` owns `301–302`, `400 · Capital Cost` owns `401` — and the rail renders all 18 flat at one indent, one colour, one weight. Add indent + family colour on the status bar and the reader sees the plant's anatomy at a glance.
- **`· Project`** — the first item renders with a dangling interpunct because it has no position number. Visible formatting bug.
- **Rail order ≠ table order.** The rail is sorted `100, 200, 201, 202…`; the Workflow table on `/Inputs` renders `100, 200, 300 … 900, 201, 202, 203 …`. The `POSITION` column *is* execution order and the table ignores it. (It's also left-aligned, which for a pure numeric column is a tell.)
- No status legibility at all: nothing tells you which plugins have unsaved edits, which are fully computed, which have warnings.

---

## 8. Broken / accidental — things that look like bugs, not choices

1. **`margin-bottom: -16px`** global → 7–8 px overlaps app-wide; visible collision in the Edge Inspector (§3).
2. **Ragged column bottoms, three places.** Home example buttons land at `y=323` (2-line description) vs `y=342` (3-line) — a 19 px zigzag across five cards. Report's three download buttons: `y=258` vs `y=278`. Streamlit columns with no height equalisation.
3. **`0.037000000000000005`** rendered raw as the value of *Interest rate on debt* — on Time, Capital Cost **and** DCF. Float noise in a financial input, in a tool selling reproducibility.
4. **Raw docstring dumped as page subtitle** on Capital Cost: `Parameters ---------- Time > Years > Value : dict Dictionary containing all time-related quantities.` — including the reST underline. (Time's subtitle carries an upstream typo, *"contianing"*, presented as the product's own copy.)
5. **Real data truncated mid-word with no ellipsis and no tooltip.** The `VALUE` input is a fixed 219 px, so on Photovoltaic you get `{Hourly Irradiation > Ho` and `{Electrolyzer > Nomin`. In an app whose premise is *"reference any of it"*, references are unreadable.
6. **The `PATH` column is 17+ rows of identical placeholder text** — `{Top > Middle > Bottom, unit}` — rendered at near-body contrast. It is the third-loudest texture on the page and it is not data. A reader will believe every parameter shares one path.
7. **Literal `None`** rendered in the PATH column on Photovoltaic, next to placeholder ghost text. Python leaking.
8. **The Source editor is a proportional-font textarea.** `font-family: "Source Sans"`, 14 px / 19.6 px, for a pipe-delimited markdown table. The `|` columns don't align, the `--- | ---` rules don't line up, and the format's entire hand-editability is destroyed. On the page called *Source*. Plus the default resize grip.
9. **Source page button layout.** `Apply` at `x=380`, `Download .md` at `x=1022` — the secondary is stranded at the horizontal midpoint of a 1,268 px column, 500 px of nothing between them. Equal-width columns applied to unequal content.
10. **Export ≠ app.** Report's cost table uses hyphen-minus `-0.0693` where Run uses the proper `−0.0693`, orders rows differently from Run with no explanation, and uses a third table style (bordered grid, no dots).
11. **The Flowsheet diagram is illegible.** Node labels ~5 px, edge labels ~4 px, edge labels overlapping each other (three stacked strings plus `+2 more` around `y≈705`). No zoom, no pan, no click-through. 600 × 1,000 px of the most interesting idea in the app, rendered as an unreadable thumbnail — while the nodes are crammed into an 80 px-wide column and the curved edges get the other 900 px.
12. **A radio with one option.** Home's `MODE` offers exactly `TEA — techno-economic analysis`. A control that cannot be operated. Under it, a note exposing repo internals to scientists: *"the LCA plugin is not on master yet (branch `feat/lca-on-master`)"*.
13. **Home headline orphan** — `file` alone on line 2 at 1440 px.
14. **Session instability.** I lost the loaded project **four times** during this walkthrough (twice on plugin switch, twice on page nav), each time landing on *"Load a pathway first"* while the nav still showed project-only pages. ⚠️ Caveat: another agent was hitting the same server from another tab, so this may be cross-session state clobbering rather than a per-tab bug — but if two tabs can evict each other's project, that is itself the finding, and it's worth ten minutes with `st.session_state`.

---

## 9. Top 10 fixes, prioritised

Ordered by (damage prevented) ÷ (lines of CSS).

### 1. Make editable fields look editable — `/Inputs`, every plugin
The whole product's core interaction is currently invisible.
``css
.stTextInputRootElement{
  background:#FFFDF8;                     /* warm, not #FFF */
  border:1px solid rgba(38,37,31,.14);    /* visible at rest */
  border-radius:6px;
  transition:border-color .12s ease-out, background-color .12s ease-out;
}
.stTextInputRootElement:hover{ border-color:rgba(38,37,31,.34); background:#FFF; }
.stTextInputRootElement:focus-within{
  border-color:#4F7132;                   /* darkened accent: 4.6:1 on white */
  box-shadow:0 0 0 3px rgba(79,113,50,.22);
}
/* computed / read-only cells opt OUT, not in */
.pp-locked{ border:0; background:transparent; }
``
Rule to hold: **read-only is the exception that removes chrome; editable is the default that has it.** Ship the same treatment to the Results-Explorer filter field, and give it a magnifier glyph.

### 2. Kill the `-16px` and replace it with a real vertical scale
``css
/* delete: .st-emotion-cache-3uwfjr{ margin-bottom:-16px } */
:root{ --sp-1:4px; --sp-2:8px; --sp-3:12px; --sp-4:20px; --sp-5:32px; --sp-6:56px; }
.pp-kicker{ margin:0 0 var(--sp-2); }          /* kicker → thing it labels */
h1{ margin:0 0 var(--sp-2); }
h1 + .stCaptionContainer{ margin-bottom:var(--sp-5); }
[data-testid="stElementContainer"] + [data-testid="stElementContainer"]{ margin-top:var(--sp-3); }
``
Fixes the Edge Inspector collision and every "glued kicker" in one pass, and gives the app the rhythm it currently lacks.

### 3. Fix the primary-action contrast and stop overloading green
``css
:root{
  --accent:#4F7132;          /* white on this = 6.4:1  ✓AA          */
  --accent-soft:#74A648;     /* fills, dots, strip segments only    */
}
.stButton>button[kind="primary"],
[data-testid="stFormSubmitButton"] button{ background:var(--accent); border-color:var(--accent); font-weight:600; }
*:focus-visible{ outline:2px solid var(--accent); outline-offset:2px; box-shadow:none; }
``
Then **retire green from `USD/kg` and `LCOH`** on the readout — use `#C9C4B6` (paper-muted) for the unit and drop the colour on `LCOH` entirely. Green should mean exactly one thing: *you can act here*.

### 4. Remove the Streamlit chrome
``css
[data-testid="stAppDeployButton"],
[data-testid="stMainMenu"],
[data-testid="stHeaderActionElements"],
[data-testid="stSidebarCollapseButton"]{ display:none; }
[data-testid="stHeader"]{ background:transparent; height:0; }
``
And theme the two remaining default surfaces:
``css
[data-testid="stAlertContainer"]{ background:#F3EEE2; border-left:3px solid #D9B780; color:#26251F; }
pre, code{ background:#F4F1E9; color:#4F7132; font-family:var(--mono); }
``
Also drop `"IBM Plex Mono"` to the **front** of the mono stack (ahead of `ui-monospace`) or you are never seeing the face you specified, and collapse `Source Code Pro` into it — one mono, not three.

### 5. Give the composition palette a real categorical scale
Eleven series currently contain a **duplicate** (`#8D74B8` twice) and three indistinguishable blues. Generate 11 hues at even LCh spacing with ≥15° separation, hold chroma constant so no swatch reads "more important", and — critically — **reserve the family colours** (`#3D5A8F`, `#D98E2B`, `#8D74B8`) so they never appear as a cost component. Then add a per-row inline bar so magnitude is readable without decoding a colour:
``css
td.share{ position:relative; }
td.share::before{ content:""; position:absolute; inset:auto 0 2px 10px;
  width:calc(var(--share) * 1%); height:2px; background:currentColor; opacity:.28; }
``

### 6. Put the family colours to work in the workflow rail
Replace the 18 radio rings with a status rail. This is a two-hour change that transforms the screen from "a list of 18 settings" into "the anatomy of your plant".
``css
[data-testid="stSidebar"] [data-testid="stRadioOption"]>div:first-child{ display:none; }  /* kill the ring */
[data-testid="stRadioOption"]{
  padding:5px 10px 5px 12px;
  border-left:2px solid var(--family, transparent);   /* CLOCK / SUN / LEDGER … */
}
[data-testid="stRadioOption"][data-child="1"]{ padding-left:28px; }   /* 201–205 under 200 */
[data-testid="stRadioOption"]:has(input:checked){ background:rgba(219,183,128,.22); font-weight:600; }
.rail-pos{ font:400 11px/1 var(--mono); color:#8A867A; margin-right:8px; }  /* de-emphasise 100/201 */
``
Add a 4 px dot on the right edge for *edited-not-applied*.

### 7. Anchor the primary action to the viewport on `/Inputs`
`Apply changes` currently sits ~2,000 px below the field you are editing.
``css
[data-testid="stFormSubmitButton"]{
  position:sticky; bottom:0; z-index:5;
  margin:0 -28px -18px; padding:12px 28px;
  background:linear-gradient(to top, #FAF7F0 72%, rgba(250,247,240,0));
  backdrop-filter:blur(2px);
}
``
Show a dirty count in the label — `Apply 3 changes` — and grey it to disabled at zero. Use the same verb on Source (`Apply`, not `Apply changes` in one place and `Apply` in the other). Suppress Streamlit's "Press Enter to submit form" hint, which currently overlaps the `VALUE` column header on focus.

### 8. Repair the input tables: format, align, prune
- Round on render: `0.037000000000000005` → `0.037`. Use `%.6g` and strip trailing zeros. Show full precision in `title=`.
- Right-align + `tabular-nums` on the `VALUE` and `POSITION` columns so magnitudes stack.
- **Drop the `PATH` column when every cell is empty** (which is most of the time). Replace with a `+ reference` affordance on row hover; if you keep it, drop the placeholder to `rgba(38,37,31,.22)` and only paint it on `:focus`.
- Fix truncation: `.stTextInput input{ text-overflow:ellipsis }`, add `title` with the full value, and let the VALUE column flex instead of sitting at a fixed 219 px.
- Add row separation: `tr + tr td{ border-top:1px solid rgba(38,37,31,.07) }` and `tr:hover{ background:#FBF8F1 }`.
- Sort the Workflow table by `POSITION` so it matches the rail.
- In the Results-Explorer tables, **drop all-empty columns** and title-case the headers (`YEAR_VALUE` → `Year value`). Set `.stMarkdown code{ box-decoration-break: clone; white-space: nowrap; }` so a wrapped reference stops fragmenting into three pills.

### 9. Fix Home: hierarchy, equal heights, and the unit trap
``css
.pp-card{ display:flex; flex-direction:column; min-height:100%; }
.pp-card .pp-desc{ flex:1 1 auto; }              /* kills the 19px button zigzag */
.pp-card .pp-value{ font-size:22px; font-weight:600; color:#26251F; margin:2px 0 6px; }
.pp-card .pp-desc{ font-size:13px; color:#55524A; }
``
Apply the same `flex:1` fix to the three Report download columns (20 px zigzag). Round the comparison values to 3 s.f. (`4.19`, `139`, `185`), and **badge the odd one out** — `PV Electricity (LCOE) · 0.0286 USD/kWh` needs a `different unit` marker or it will be misread as the cheapest option. Constrain the H1 to `max-width: 20ch` so `file` stops orphaning. Replace the one-option `MODE` radio with a static line plus a real "LCA — coming soon" disabled row, and rewrite the branch note in user language (drop `feat/lca-on-master`).

### 10. Make the Flowsheet and the Source editor usable
**Flowsheet:** the diagram is the best idea in the product and it is currently 5 px tall. Render it into a `height: 78vh` scroll/zoom container with `+ / − / fit` controls, set a minimum label size of 11 px, widen the node spine to ~180 px so node labels breathe, and hide edge labels below a zoom threshold (reveal on hover). Add click-to-select on an edge that drives the Edge Inspector, so the inspector stops being a detached dropdown.

**Source:** it is a code editor. Treat it as one.
``css
[data-testid="stMain"] textarea{
  font:13px/1.55 var(--mono);
  tab-size:2;
  white-space:pre;              /* stop wrapping pipe tables */
  overflow-x:auto;
  background:#FDFBF5;
  border:1px solid rgba(38,37,31,.14);
  resize:none;                  /* remove the default grip */
}
``
Right-align `Download .md` to the column edge instead of stranding it mid-page, and add a dirty marker (`● unsaved`) beside `Apply`.

---

## 10. Two things to hold on to

The **readout card** and the **Σ / ✓ matches readout** row are the product's thesis statement — *"the number is the point, and it audits itself."* Everything above is, in effect, one request: **make the other seven screens as intentional as those two elements already are.** The vocabulary is already invented; it just isn't being spoken consistently.

And the copy is genuinely good. Don't let anyone "professionalise" *"Load a pathway to begin. Every screen is a view of that file, and the file you download reproduces what you see, exactly."*
