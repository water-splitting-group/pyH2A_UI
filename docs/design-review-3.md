# pyH2A "Paper Plant" — Cold Design Review, Round 3

**Reviewer:** ColdEye3 · **Date:** 2026-08-05 · **Build:** localhost:8721
**Viewport:** 1600×1000 @2× unless noted · **Session:** Home → open `pv_e` by clicking the row → sidebar only
**Audience assumed:** research scientists doing levelized-cost analysis
**Method:** every number below was either re-derived by hand from the figure it appears in, or read out of the DOM. Every screenshot cited was opened and looked at.

---

## Verdict up front

Something changed between round 2 and now that is bigger than a visual pass: this app stopped decorating data and started *arguing* with it. The Answer page will now show you, for any cost row, the second-level split across actual equipment, then a five- or six-step derivation ending in `5,122,875 USD ÷ 3,966,584 kg = 1.29151 USD/kg ✓ the ledger row above`, with the naive undiscounted answer sitting next to it labelled `✗ −48.4% against the ledger` so you can see exactly what discounting bought. The Bench re-runs 88 full DCFs and then tells you, in plain English, that four of its eight parameters turn inside the swept band and that a two-point tornado would have lied about every one of them. The Home page's log axis is geometrically exact to a tenth of a pixel across five pathways and 56.7×. The dispatch plate reconciles 8,760 hours back to the engine's own `physical.hydrogen_kg_yr` to within half a kilogram and says so. This is the rarest thing in scientific UI: a tool that shows its work and volunteers its own defects — including a red banner admitting that 19% of the headline number comes from an upstream authoring typo it has deliberately preserved. Round 2's central charge, *"it hides the money,"* is **answered** — not by fixing the flowsheet but by demoting it and building a real centerpiece with an ENERGY lens and a COST lens on the same left-to-right spine, where every cost station is an attribution that sums to `4.1943` exactly. What holds it back now is not ambition, it is finish: five buttons on the best page in the app are completely dead, the cash-flow figure has 59 px of its left column hard-clipped off the screen, roughly a quarter of the text in both flagship figures sits at 6.6–7.3 px and **2.4:1** contrast, a caption on the Plant page divides the wrong number by 365, and the front door presents the flagship answer with a green ✓ and no mention of the defect the next page leads with. The thinking is a grade A. The execution is a B−, and the gap is almost all in the last 5%.

---

# Part 1 — Three user stories

## Story A — First contact: land cold, open a pathway, understand the plant

**Screenshots:** `/tmp/r3-A01-home-top.png` → `/tmp/r3-A09-row01.png` → `/tmp/r3-A02-anatomy.png` → `/tmp/r3-A10-hover-row1.png` → `/tmp/r3-A13-after-open-20s.png`

### The clock

**At 10 seconds** I know: there are five plants, they cost `4.1943 / 3.2706 / 139.42 / 185.44` USD/kg and `0.0286` USD/kWh, the spread is 56.7×, and one of them is priced in a different unit and has been flagged `≠` and moved to its own axis. I have not clicked anything. That is an unusually good ten seconds — most tools of this class spend it on a logo.

**At 60 seconds** I additionally know: pathway 01 is a utility PV array feeding a PEM stack through a battery buffer with seawater RO, 8,250 kW of PV, a 5,500 kW stack, 378,915 kg/yr at the gate, 17 plugins, 37,500 m² of land shown as a bar against a 331,010 m² full-scale reference; that 31.1% of its cost is capital; that a log axis places it just left of 5 USD/kg with nothing between 3.27 and 139; and — from the black anatomy panel — that all five pathways share nine of twenty-two plugins, the finance spine, and differ only in the physics head.

**Home is the strongest first screen I have seen on a modelling tool.** It fits in one viewport (`scrollHeight 1010` against `clientHeight 1000`), it is left-aligned and editorial, it has no card grid, and the hover state is restrained: the row lifts, the index and the process glyph go olive, `OPEN ›` darkens (`/tmp/r3-A10-hover-row1.png`).

### Verified, not eyeballed

I checked the two claims the page makes about itself.

- **The log axis.** Ticks at 2, 3, 5, 10, 20, 30, 50, 100, 200, 300 land at x = 842.0, 870.3, 905.9, 954.2, 1002.5, 1030.7, 1066.4, 1114.6, 1162.9, 1191.2. One decade = 160.4 px. Predicted dot positions: 4.1943 → 893.7 (actual **893.6**); 3.2706 → 876.3 (**876.3**); 139.42 → 1137.7 (**1137.8**); 185.44 → 1157.6 (**1157.7**); and on the separate USD/kWh axis 0.0286 → 916.5 (**916.4**). **Exact to 0.1 px.** `NO PATHWAY LANDS HERE` is correctly parked in the 10–20 gap.
- **The anatomy matrix** (`/tmp/r3-A02-anatomy.png`). The copy says `9 of 22 are identical in all five`. The nine dimmed columns are Time, Inflation, Production, Capital_Cost, Replacement, Labor_Operating_Cost, Other_Fixed_Operating_Cost, Variable_Operating_Cost, Discounted_Cash_Flow — and every one of those does appear in all five rows, while `Hourly_Irradiation` (4 of 5) and `Multiple_Modules` (4 of 5) are correctly left bright. The dimming is *computed*, not decorative.

### Friction

**A1. The front door does not carry the app's own warning.** Home presents `4.1943 USD/kg` under the banner `PYH2A REFERENCE INPUT SET` and closes with `✓ checked  all 5 reconcile — Σ of 11 components = the levelized cost … max residual 2.8e-14`. The Answer page opens with a red banner: *"Grid electricity is priced at 10,000.12 USD/kWh … about 10,000× outside the plausible range … currently 0.8105 of the 4.2624 total (19%)"* (`/tmp/r3-D01-answer-top.png`), and the Bench devotes a footer paragraph headed **Known defect** to it. I confirmed the input is real: `app/examples/PV_E_Base.md:167` reads `Cost | 10000.12 | USD/kWh`. Reproducing it is correct. Being silent about it on the one screen a first-time visitor sees is not. A green reconciliation stamp next to a number that is 19% authoring typo is the most consequential mismatch in the product.

**A2. `56.7× BETWEEN THE CHEAPEST AND THE DEAREST` sits immediately after `5 PLANTS`.** The 56.7× is 185.44 ÷ 3.2706 and covers four of them. The middle clause (`4 PRICED IN USD/KG, 1 IN USD/KWH`) disambiguates it, but only just, and the bracket at bottom right has to re-say it (`56.7× across all four`).

**A3. Home's five primary actions are mouse-only.** `div.grid.row.first` carries `data-key="pv_e"` and `style="cursor: pointer"` and **no `role`, no `tabindex`, no `aria-label`.** The entire gallery iframe has exactly **one** focusable element, and it is `BROWSE ▸`. You cannot open a pathway from the keyboard.

**A4. `The other 13 are the physics` is off by one.** Thirteen columns are bright, but one of them is `Multiple_Modules`, which the diagram itself brackets under `COST & CASH FLOW`. It is twelve physics plugins and one cost-scaling plugin.

**Arrival on Plant** (`/tmp/r3-A13-after-open-20s.png`) is 3 s to navigate, ~15 s to settle, and the landing is confident: a black bar reading `4.1943 USD(2016)/kg [LCOH]` — the dollar-year basis round 2 asked for, delivered — then a 68 px `13.5%` and the sentence *"of the sunlight landing on 37,500 m² leaves as hydrogen. The other 86.5% is drawn below, in full."* That is a lede, and it checks: 12,629 MWh of LHV hydrogen ÷ 93,487 MWh of incident sunlight = 13.51%.

### Story A grade: **A−**
Fast, dense, honest, and it answers "what is this, what does it make, what does it cost" before the first click. Two points off for the missing defect warning at the front door and for keyboard-inaccessible primary actions.

---

## Story B — Iterate: Electrolyzer nominal power 5,500 → 6,000, apply, read the answer

**Screenshots:** `/tmp/r3-C01-inputs.png` → `/tmp/r3-C02-inputs-electrolyzer.png` → `/tmp/r3-C05-dirty-crop.png` → `/tmp/r3-C06-dirty-sidebar.png` → `/tmp/r3-C08-after-apply-settled.png` → `/tmp/r3-H05-plant-header.png` → `/tmp/r3-H02-invalid.png`

### What works, and it is a lot

- The Inputs worksheet is generous and correctly labelled: `INPUTS — SUPPLIED BY YOU`, `NAME / VALUE / UNIT`, real editable fields with a 2 px olive focus outline, and unit placeholders that name the *quantity kind* (`power`, `mass / energy`, `time`, `dimensionless`). At this width `kg/kWh` fits.
- `AVAILABLE UPSTREAM — Everything computed before this plugin runs. Copy a reference to bind any of it into a Value or Path field.` Scoping the reference list to what is actually upstream of *this* plugin is the right idea and a genuine improvement on round 2's undifferentiated pile.
- **Error handling is transformed.** I typed `abc` and pressed Apply. Round 2 got a raw Python `TypeError`, the wrong plugin blamed, and the last good result destroyed. Round 3 gets: `Electrolyzer > Nominal power: "abc" is not a number, percentage, or {reference}` / `Nothing was applied — fix the fields above first.` — and the sidebar keeps `last run 4.2624 USD/kg` intact (`/tmp/r3-H02-invalid.png`). The engine is never invoked. This is exactly right.
- **The delta on the Plant page is now fully specified** (`/tmp/r3-H05-plant-header.png`): `4.1943 USD(2016)/kg [LCOH]  ▼ -0.0681 vs 4.2624 · Electrolyzer > Nominal power: 6000 → 5500`, with a run-history sparkline, coloured semantically — `.pp-delta-down { rgb(155,196,126) }`, `.pp-delta-up { rgb(224,149,107) }`. Cheaper is green, dearer is warm. Round 2's B6 and B7 are both closed, and closed well.
- Press `Run` with nothing changed and the bar says `= unchanged` (`/tmp/r3-J03-run-header.png`). Honest.

### Friction

**B1. The feedback is on a different page from the action.** After `Apply & run ▸` on Inputs (`/tmp/r3-C08-after-apply-settled.png`), the *only* thing that changes on screen is the sidebar's `last run 4.1943 → 4.2624`. No delta, no "was", no toast, no confirmation, no timing. The signed, annotated, colour-coded delta exists — 1,400 px away and one navigation over, on Plant. You iterate on Inputs and read the result on Plant. That is the loop broken across a page boundary.

**B2. There is still no dirty state, anywhere.** With `6000` typed and unapplied (`/tmp/r3-C05-dirty-crop.png`), the field is identical to its untouched neighbours: no accent, no `was 5,500`, no per-field revert, no pending-edit count. `Apply & run` is unchanged. The sidebar `last run 4.1943` carries no stale marker (`/tmp/r3-C06-dirty-sidebar.png`). Round 2's B2, verbatim, unaddressed.

**B3. There is no way back.** I enumerated every `button` and `a` on the Inputs page: seven nav links, a hidden `Deploy`, and `Apply & run ▸`. **No reset, no revert-to-reference, no undo, no run list.** The only route back to 5,500 is to remember 5,500 and retype it. And the Plant bar's record of what you changed survives exactly one further run — press `Run` again and it becomes `= unchanged`, taking the provenance with it.

**B4. Number formatting is still normalised on load and not on edit.** The table loads `5,500` and `80,000`; after editing you have `6000` sitting directly above `80,000`. Two conventions, five rows apart. Round 2's B3.

**B5. The invalid field itself gives no signal.** The banner names it correctly, but the field has no `aria-invalid`, no red border, no inline message, and `Apply & run` stays enabled. On a worksheet with twenty fields you read a name and then go hunting.

**B6. `kg/kWh` still elides in the Plant side panel.** The unit input went from 31 px to 59 px — most units now fit — but `kg/kWh` renders `kg/k…` (`/tmp/r3-B14-node-click.png`). Six characters of mono at 13.6 px need about 70 px with padding.

### Story B grade: **B**
Every individual mechanism is now good — validation, error copy, delta semantics, delta provenance. They are wired to the wrong surfaces. Knowing *what you changed* and *whether it was good* is solved on the page where you cannot change anything, and unsolved on the page where you can.

---

## Story C — Interrogate: chase the largest cost component to its source

**Screenshots:** `/tmp/r3-D01-answer-top.png` → `/tmp/r3-D04-fixedop-expanded.png` → `/tmp/r3-D-answer-950.png` → `/tmp/r3-E01-bench.png` → `/tmp/r3-E02-bench-630.png`

The largest single component is `01 Initial equity depreciable capital · 1.29 USD/kg · 30.3% share`. The plate says `click a row for its second level and its arithmetic`. It means it.

**Can I find out which equipment it belongs to?** Yes, immediately:

| | USD | share | USD/kg |
|---|---|---|---|
| PV | 7,362,000 | 60.8% | 0.786 |
| Electrolyzer | 4,704,000 | 38.9% | 0.502 |
| Reverse Osmosis | 38,065 | 0.314% | 0.00406 |
| **Direct capital cost** | **12,104,065** | | **1.292** |

7,362,000 + 4,704,000 + 38,065 = 12,104,065 exactly. The sub-USD/kg values sum to 1.292 against the row's 1.29. And the note explains why the shares survive the transform: *"allocated pro rata — every step from source USD to USD/kg is linear, so the shares carry through unchanged."*

**Can I verify the arithmetic?** Yes, all six steps, by hand:

1. `INFLATE  12,104,065 × 1.07819 = 13,050,525` ✓
2. `EQUITY   13,050,525 × 0.40 × 0.981354 = 5,122,875` ✓
3. `SOURCE   5,122,875 nominal, undiscounted — one payment, analysis year −1`
4. `NAIVE    5,122,875 ÷ 7,682,587 kg = 0.666816 USD/kg   ✗ −48.4% against the ledger` ✓ (0.666816 / 1.29151 − 1 = −48.4%)
5. `DISCOUNT NPV at 10.052% nominal = 5,122,875 — 100% of nominal survives`
6. `LEVELIZE 5,122,875 ÷ 3,966,584 kg = 1.29151 USD/kg   ✓ the ledger row above` ✓

And then the paragraph that closes round 2's C9 outright: *"Costs discount at the nominal after-tax IRR, 10.052% = (1 + 8.0%)(1 + 1.90%) − 1. Output discounts at the real IRR and is inflation-corrected, which turns 7,682,587 kg shipped into an effective 3,966,584 kg — 51.6% of it. That one denominator serves all 11 rows, which is why the ledger stays additive."* (1.08 × 1.019 − 1 = 0.10052 ✓; 3,966,584 / 7,682,587 = 51.63% ✓.)

I repeated the exercise on `05 Fixed operating costs` (`/tmp/r3-D04-fixedop-expanded.png`): second level 241,320 + 93,600 = 334,920 ✓; 334,920 × 1.07819 = 361,109 ✓; 8,687,150 ÷ 7,682,587 = 1.13076 ✓ (`+28.9%`); 3,479,310 ÷ 8,687,150 = 40.1% survives ✓; 3,479,310 ÷ 3,966,584 = 0.877155 ✓.

Then the Σ SELF-AUDIT plate (`/tmp/r3-D-answer-950.png`): `Σ of 11 contributions 4.2624 · Σ of 4 family subtotals 4.2624 · headline 4.2624 · residual 0 [RECONCILES] · worst row vs contributions.data 1.11 × 10⁻¹⁶` — with the caveat that the eleven rows are *recomputed from cashflow*, not copied from the thing they are checked against. **This is the best object in the product and one of the best I have seen in this category.** Keep it. Do more of it.

**Does the Bench tell me whether it matters?** For this component, yes and precisely. Rows 03 and 04 of the influence ranking are exactly `Direct Capital Costs - PV › PV CAPEX` (span ×1.456, `MONOTONIC ↑`, ±8.4% for ±20%) and `Direct Capital Costs - Electrolyzer › Electrolyzer CAPEX` (span ×1.339, ±6.6%). The panels even show their derivation: `deck 818 USD/kW × Photovoltaic = 7,362,000 USD` and `deck 784 USD/kW × Electrolyzer = 4,704,000 USD` — the same two numbers I just chased through the ledger, on a different page, from a re-run of the engine. That is cross-page integrity you can bet on.

The Bench's editorial claim — *"4 of 8 parameters turn inside the swept band, and one is flat to the last bit. A two-point tornado misreports every one of them"* — checks against its own `BEHAVIOUR IN BAND` column: 4 × `TURNS`, 3 × `MONOTONIC ↑`, 1 × `FLAT · NO RESPONSE`. And the note on the flat one is the best sentence in the app: *"Eleven runs, one answer: the rating never binds anywhere in 480–1,200 MWh. Worth drawing — 'we checked and it does not matter here' is a finding, and a zero-length bar reads as a rendering fault."*

### Friction

**C1. The five pathway tabs on the ledger are dead.** `PV + Electrolysis · PV → Electricity · Solar thermal · Photoelectrochem. · Photocatalytic` render `cursor: pointer`, hover-highlight, and carry `data-case` and `aria-pressed`. Clicking any of them — by mouse at the correct coordinates, and by calling `element.click()` directly in the frame — changes **nothing**: `aria-pressed` stays `true` on `pv_e` and the ledger never switches (`/tmp/r3-L01-ledger-thermal.png`). Five buttons promising cross-pathway cost comparison, on the best page in the app, all inert. This is the single worst affordance failure in the build.

**C2. The Results Explorer got longer, not better.** 43 identical 40 px full-width accordions in a flat stack (round 2 counted ~35). No counts, no previews, no grouping, no input/output distinction, no execution order. And the singular/plural traps are all still adjacent: `Direct Capital Cost` / `Direct Capital Costs`, `Indirect Capital Cost` / `Indirect Capital Costs`, `Other Fixed Operating Cost` / `Other Fixed Operating Costs`, `Other Variable Operating Cost` / `Variable Operating Costs`, `Planned Replacement` / `Unplanned Replacement` / `Replacement` (`/tmp/r3-D-answer-2850.png`, `/tmp/r3-D-answer-3444.png`). Round 2's C2 and C3, unchanged.

**C3. The superscript on every ledger row reads as a footnote and is not one.** `Initial equity depreciable capital³`, `Replacement costs¹`, `Fixed operating costs²`. The element is `<span class="items">` — it is the count of second-level entries (3 for PV/Electrolyzer/RO, 2 for Other Fixed + Labor). There is no legend, no `title`, and no footnote anywhere on the page. In a financial table a superscript numeral means one thing. It is also `rgb(169,163,149)` at 10 px, which is **2.4:1**.

**C4. The Bench is a fixed report, not a bench.** Eight parameters, band 0.60–1.50, eleven factors, no controls except `Sweep again ▸`. You cannot add a parameter, change the band, or sweep the thing you just chased. `Fixed operating costs` is 20.6% of the headline and its second level (`Other Fixed Operating Costs`, 241,320 USD) is not sweepable. Nothing links a ledger row to its bench row or back.

**C5. `a local optimum sitting on the base`** (Bench panel 06). The base case is the *highest* cost point on that curve — both ±20% ends read 4.221 against a base of 4.2624. It is a local pessimum. In a cost model, calling it an optimum inverts the reader's conclusion.

### Story C grade: **A−**
The chase now completes. You can verify the arithmetic, name the equipment, and check whether it matters — three things that were all dead ends in round 2. The −  is entirely the dead tabs and the 43-row wall.

---

# Part 2 — The centerpiece: does the process diagram carry its weight?

Round 2's charge was: *"the flowsheet must win on wiring or it is decoration with a large footprint"* and *"it hides the money."*

**The answer this build gives is: don't defend the flowsheet — replace it.** The old 17-node flowsheet is now a supporting figure at the bottom of the Plant page under a small header (`THE MODEL — The same plant as the engine sees it`). The centerpiece is a new, scaled process figure with two lenses.

## The ENERGY lens — **carries its weight, decisively**

`/tmp/r3-B01-sankey.png`, `/tmp/r3-B08-diag-nohover.png`

Every width is a quantity. Sunlight 93,487 MWh/yr as an orange bar; the 72,920 MWh that never becomes electricity as grey; then an explicit, annotated scale break — `THE SURVIVING 20,567 MWh IS DRAWN BELOW, AT 4.5× THIS SCALE` (93,487 / 20,567 = 4.545 ✓) — and the surviving energy re-drawn at the larger scale with a real MWh/yr axis. The electrolyzer block splits green (12,629 MWh of LHV hydrogen) against hatched (7,853 MWh of loss) in a 62:38 ratio that I measured off the pixels at 100:60 against a true 61.7:38.3.

The arithmetic closes to the last digit:
- 93,487 − 72,920 = 20,567 ✓ and 72,920 / 93,487 = 78.0% ✓
- 378,915 kg × 33.33 kWh/kg = 12,629 MWh ✓ and 378,915 / 365 = 1,038 kg/day ✓
- 12,629 + 7,853 = 20,482 = the stream table's 18,861 + 1,621 into the stack ✓
- Dispatch regimes: 4,445 + 221 + 2,187 + 1,907 = 8,760 ✓; `hours the stack ran 4,094` = 2,187 + 1,907 ✓; `idle 4,666` = 4,445 + 221 ✓
- `10 OF 24 HOURS ARE DARK ON EVERY DAY · 3,650 h` + `THE OTHER 795 DARK HOURS FALL INSIDE THE BAND` = 4,445 ✓

This is the best process figure I have reviewed in a modelling tool. The 365×24 dispatch plate below it (`/tmp/r3-B-plant-scroll-900.png`) is nearly as good, and its hover is exemplary: crosshair, month-axis date chip, a per-hour card (`18 May · DAY 138 · 08:00–09:00 PST · UTC−8 · PV output 4,729 kW · to stack 4,729 kW · to storage 0 kW · DIRECT · STACK AT 86% OF NAMEPLATE` — 4,729/5,500 = 86.0% ✓), a day summary line, and simultaneous highlighting in the marginal mean-hour chart and the daily-total strip (`/tmp/r3-K02-dispatch-hover-crop.png`). The `Raw UTC` toggle actually re-renders the whole plate, shifts the band eight hours, relabels the axis, and updates `AXIS CHECK · UTC · solar noon 20.21 h` (`/tmp/r3-M01-dispatch-rawutc.png`). It teaches you that the source TMY data is UTC-stamped.

## The COST lens — **carries its weight, with a geometry caveat**

`/tmp/r3-B03-cost-lens.png`, `/tmp/r3-B04-cost-chart.png`

`EACH COST ENTERS AT THE UNIT THAT INCURS IT AND RUNS TO THE GATE`. Eight stations along the same left-to-right spine: PV ARRAY +0.7855 · BATTERY +0.0000 · DESALINATION +0.0041 · ELECTROLYZER +0.7172 · RUNNING IT +1.6221 · FINANCING +1.0654 · DECOMMISSION +0.0693 · SALVAGE −0.0693. **Sum = 4.1943 exactly.** Every percentage checks. The Electrolyzer sits at roughly the same x as it does in the ENERGY lens, so the two views are spatially comparable. Round 2's "it hides the money" is answered: the money is one click away, on the same spine, in the same geometry.

Where it is soft:

- **The tick heights and the labels measure different things.** Each station's vertical tick is the *cumulative* total (Electrolyzer's reaches 1.5068 = 0.7855 + 0.0041 + 0.7172; Financing's reaches 4.1943; Decommission's overshoots to 4.2636 and Salvage's returns to 4.1943 — all correct). The label under each tick is the *increment* (`+0.7172`). Two quantities in one visual unit with no key.
- **The ogive is a lie about a step function.** Cost does not accrue gradually between the PV array and the electrolyzer; it jumps. The smooth S-curve between stations is interpolation for looks, in a figure whose whole authority rests on not doing that. Everywhere else this build annotates its compressions (`4.5× THIS SCALE`, `VALUE SCALE COMPRESSED 4.1:1 · NO RANGE OMITTED`, `AXIS BROKEN AT 5.7`). Here it smooths silently.
- **The three stacked bands are unlabelled.** Tan, green, purple, with no legend.
- **The KPI strip below does not tie to the chart above it.** `BUILD IT 1.2929 · RUN IT 1.8360 · FINANCE IT 1.0654` sums to 4.1943 ✓ — but the equipment tributaries above sum to 1.5068, not 1.2929. The 0.2139 difference is stack replacement, filed under the Electrolyzer in the chart and under RUN IT in the strip. Both are defensible; neither says so, and they sit 60 px apart.
- **`BATTERY +0.0000 · 0.0% of total`.** Combined with `BATTERY · 0 MWh curtailed` in the ENERGY lens and `204 Battery · 0 J` on the flowsheet, the battery is a first-class unit in three views with a zero in all of them. The Bench eventually explains it (`FLAT · NO RESPONSE`, *"the rating never binds anywhere in 480–1,200 MWh"*) — but that is three pages away, and until you find it the battery reads as broken.

## `THE MODEL` — the old flowsheet, now supporting cast

`/tmp/r3-B-plant-scroll-1800.png`, `/tmp/r3-B11-flowsheet-fit.png`, `/tmp/r3-B12-rail-labels.png`, `/tmp/r3-B13-flowsheet-zoomed.png`, `/tmp/r3-B14-node-click.png`

Demoting it was correct, and several round-2 fixes landed here:
- Legend now uses domain words: `framework · solar · conversion · storage & power · water · cost · scale-out`.
- `3⇥ 5⤇` is now `in 3 · out 5`.
- Cards carry a headline number instead of `<1 ms`: `11.1 M USD`, `62.4 k USD`, `284 k USD`, `4.19 USD/kg`, `7.04 M kg`.
- Wheel-zoom is gated: `⌘/Ctrl+wheel to zoom`. The scroll trap is gone.
- Accessibility is real: `svg[role=group]`, `.node[role=button]`, `aria-label="203 Electrolyzer, conversion, 3 input tables, 5 outputs"`, 21 focusable elements. Round 2 measured zero.
- The hover card headline is now `Electrolyzer`, with `CONVERSION · POSITION 203` beneath.
- A `↓ 6 more plugins below — scroll or click` cue exists at default zoom.

What did not land:

- **`fit` fits, and in fitting it destroys the diagram.** It now returns `viewBox="-24 -24 1844.75 1570"` with **0 of 17 nodes off-canvas** — genuinely fixed. But scale drops to 0.459, node titles render at **6.88 effective px**, and **every stream label disappears**. The fit box reserves 1,845 units of width for labels it then refuses to draw. The one thing only this diagram can show — the wiring — is absent from the only view that shows the whole plant.
- **At default zoom, 7 of 17 nodes are clipped and the cue says 6.** Node 400 `Capital Cost` is sliced rather than hidden, exactly as node 302 was in round 2.
- **Node titles now truncate.** Packing an index, a value, a title and `in N · out M` into a 179-unit card elides four of the seven cost nodes: `Labor Operating Co…`, `Other Fixed Operat…`, `Variable Operating…`, `Discounted Cash Fl…`. Round 2 measured titles fitting comfortably. **Regression.**
- **The payload is uneven.** `0 J` on two cards, `10 year` on two more, `0.6` with no unit on Multiple Modules, and nothing at all on Replacement and Variable Operating Cost.
- **The `Electrolyzer` bus rail still runs under the node cards** and clips to `Electro…` (`/tmp/r3-B12-rail-labels.png`). Round 2's exact finding.
- **Stream labels no longer truncate but now collide harder.** Five overprint around `Non-Depreciable Capital Costs > Land required` / `Photovoltaic > Nominal power` / `Technical Operating Parameters and Specifications > Design output by year`.
- **`+` zooms about the viewport centre, which after `fit` is empty label field.** Five presses from `fit` puts you at 170% looking at half-cropped label text with **zero nodes visible** — while the overlay still reads `↓ 5 more plugins below` (`/tmp/r3-B13-flowsheet-zoomed.png`).
- **The hover card still occludes the next two nodes** (hovering 203 hides 204 and 205).
- The run pulse — round 2's best delight moment — now happens 1,900 px below the button that fires it, so you never see it.

**Verdict on the centerpiece: it carries its weight, and then some.** The ENERGY lens is load-bearing information design; the COST lens puts the money on the same spine and makes it add up. Neither is decoration. The old flowsheet is now honestly labelled as what it is — a plumbing diagram for the engine — and it is still the weakest figure on the page.

---

# Part 3 — Scale and hierarchy: did the range land?

Measured as *effective* rendered px (SVG text scaled by its viewBox transform), across every leaf text element:

| surface | floor | ceiling | range | share ≤ 8 px |
|---|---|---|---|---|
| Process figure (ENERGY/COST) | **6.6** | **68** (`13.5%`) | **10.3×** | 22 of 94 (23%) |
| Dispatch plate | **7.0** | 21.1 | 3.0× | 34 of 108 (31%) |
| Plant page HTML chrome | 9.8 | 27.2 | 2.8× | 0 |
| Flowsheet @ 78% | 8.2 | 11.7 | 1.4× | 0 |
| Flowsheet @ `fit` (46%) | 4.8 | 6.9 | 1.4× | all |

**The range landed where it was aimed and nowhere else.** The process figure genuinely spans an order of magnitude of type size, and magnitude is genuinely encoded geometrically — Sankey widths, the Home log axis (exact to 0.1 px), the footprint bars normalised to a stated 331,010 m², the cost accretion, the ledger's waterfall, the cash-timing bars, the Bench envelopes, the dispatch's marginal mean-hour chart.

Where it did not land:

**H1. The floor is far too low, and it is load-bearing.** Every secondary caption in the flagship figure is `rgb(169,163,149)` on `rgb(250,249,245)` at 6.6–7.3 px. That is **2.4:1** — WCAG AA wants 4.5:1 — at roughly half a readable size. The list is not decorative:

- `8,250 kW · 22% efficient` (the PV array spec)
- `5,500 kW · 54.1 kWh per kg` (the electrolyzer spec)
- `THE SURVIVING 20,567 MWh IS DRAWN BELOW, AT 4.5× THIS SCALE` — the sentence that makes the whole figure honest
- `78.0% of incident · module efficiency 22%`
- `0 MWh curtailed · cell runs 4,389 h/yr on stored power`
- `8,491 m³ seawater in · 3,396 m³ fresh out · 40% recovery`
- `38% of the electricity · 54.1 kWh per kg`
- `AT THE GATE`, `MWh/yr`, and every axis tick

Round 2's complaint was that the flowsheet was *too small at good contrast* (`#55524A` on `#FAF7F0` = 7.29:1). The flowsheet was fixed. The problem moved into the new figures and got worse: now it is small **and** faint.

**H2. Hierarchy inverts between the chrome and the figures.** The page h1 `Plant` is 27.2 px. Inside the figure directly below it, `PV + Electrolysis` is 29 px and `13.5%` is 68 px. The page title is outranked by its own illustration. Section eyebrows (`A YEAR OF OPERATION`, `THE MODEL`) are 10.9 px — smaller than body text at 14 px — so the page's structural skeleton is its quietest layer.

**H3. Three strips are pure digits where the rest of the app draws geometry.** The Plant ENERGY KPI row (`37,500 m² · 22% · 62% · 8,491 m³ · 4.1943 USD/kg`), the COST KPI row (`1.2929 · 1.8360 · 1.0654 · 7,042,372 kg · 352,119 kg/yr`), and the Report's cost table. All values set at the same size, magnitudes spanning four orders, no bars, no axis, no encoding. On a page whose thesis is that quantity should be shape, these are the exception and they are adjacent to the rule.

**H4. Two number-grouping conventions on one page.** The dark plates use thin spaces (`20 567`, `4 094`, `378 915`, `15 155 786`); the light HTML tables use commas (`18,861`, `378,915`, `7,042,372`). Both appear on Plant within 400 px of each other.

---

# Part 4 — What is still boring

**The Source page is the weakest screen in the app, by a distance.** `/tmp/r3-F01-source.png`

It announces itself as `SOURCE — THE SINGLE SOURCE OF TRUTH / The markdown file the engine runs. Edits here re-parse the file; the input forms rebuild from it. Nothing drifts.` Then it hands you a bare Streamlit `<textarea>`:

- **174 lines / 6,825 characters in a 518 px box** (`scrollHeight 3,388`) — **15% of the file visible at once** — with `resize: none`.
- No line numbers. No syntax highlighting. No find. No section jump. No fold. No diff against the reference. No indication of which lines you have edited this session.
- The markdown is entirely structural — `# Electrolyzer`, pipe tables, `{Reference > Path > Value, unit}` chips — and none of that structure is rendered. Every other page in this build treats structure as the point.
- Button hierarchy is inverted and ungrouped: primary `Apply` is 59 px at x=332; secondary `Download .md` is 111 px at x=532. The secondary is nearly twice the width of the primary, 141 px away. Round 2 flagged this exact pair; it is unchanged.

Why it matters more than "it's a bit plain": this is the page where the 10,000.12 USD/kWh defect actually lives (`Cost | 10000.12 | USD/kWh`, line 167). The Answer page tells you to `Check Grid Electricity › Cost`. You arrive here and get a 15%-tall scrolling box with no search. The app builds a beautiful chain of custody from the headline down to the cell — and then drops you at the door with no key.

**Runners-up:** the Results Explorer (43 undifferentiated accordions), and the Report page — three peer buttons with no primary, sitting at three different vertical positions (two at y 203, one at y 183), under a column heading (`The file`, y 124) that overlaps the h1's box (y 94–125) at the identical left edge and therefore reads as the page's subtitle (`/tmp/r3-G01-report.png`).

---

# Part 5 — Wrong, not ugly

Ordered by how badly a scientist would be misled.

**W1. The five ledger pathway tabs do nothing.** Verified by mouse and by direct `element.click()`; `aria-pressed` never changes, the ledger never switches. `/tmp/r3-L01-ledger-thermal.png`

**W2. The dispatch `EXAMPLE` chips report a state they do not have.** Clicking `thermal` sets `aria-pressed="true"` on `thermal` and `false` on `pv_e`, and the chip renders as selected — while the figure re-paints (`painted in 6.0 ms`) with **identical pv_e data**: title `PV + Electrolysis`, `20 567 MWh/yr`, `4 094 h`, `378 915 kg/yr`, same heat map. Waited 14 s to be sure. `/tmp/r3-M03-thermal-pressed-header.png`, `/tmp/r3-M05-thermal-14s.png`. Worse: Home says pathway 02 has *"no hourly model"* at all, so there is nothing for this chip to show even in principle. (The neighbouring `TIME BASE` toggle does work properly, which is what makes this read as a bug rather than a decision.)

**W3. The cash-flow figure has 59 px hard-clipped off its left edge.** `.sheet` is 1,354 px wide, positioned at **x = −59** inside a 1,236 px window with `overflow-x: hidden`. No scrollbar, no scaling, no indicator. Result: `When the plant pays for itself` → `hen the plant pays for itself`; `CUMULATIVE, YEAR 19` → `LATIVE, YEAR 19`; and every label in the left ledger column loses 3–5 characters — `enue`, `erating, fixed`, `erating, variable`, `erest`, `rking capital`, `es`, `lacement`, `MULATIVE TO DATE`, `VENUE ■ CAPITAL`. `/tmp/r3-D03-cashflow-clip.png`

**W4. `PER YEAR 352,119 kg/yr · 1,038 kg a day`.** 352,119 ÷ 365 = **964.7**. The 1,038 belongs to 378,915 kg/yr, the peak-year gate figure. One KPI, two bases, one of them wrong. `/tmp/r3-B03-cost-lens.png`

**W5. The battery is curtailing 0 MWh and 85.3 MWh on the same page.** The Sankey caption reads `BATTERY · 0 MWh curtailed`; ~700 px below, the energy-balance note reads *"95.0% of surplus returns … the other 85.3 MWh is curtailed"* (1,706.5 × 0.95 = 1,621.2; 1,706.5 − 1,621.2 = 85.3 ✓, so the second one is right). `/tmp/r3-B01-sankey.png` vs `/tmp/r3-B-plant-scroll-900.png`

**W6. `cell runs 4,389 h/yr on stored power` on a stack that ran 4,094 h.** The dispatch plate's headline is `HOURS THE STACK RAN 4 094 h` (= 2,187 direct + 1,907 saturated, and the regimes sum to 8,760). You cannot run 4,389 hours on stored power inside 4,094 hours of running.

**W7. The energy balance omits desalination and still claims to close.** The stream table lists `PV array → Desalination · 23.0 MWh/yr`, and the ribbon is drawn. The `ENERGY BALANCE` panel then splits PV generation exactly two ways: `20,567.2 = 18,860.7 straight into the stack + 1,706.5 surplus to storage`, leaving zero room for the 23.0 MWh. 0.11% is nothing; the claim `Σ RECONCILES` is not.

**W8. `one of 10 identical modules` invites a 10× error.** `app/examples/PV_E_Base.md:56` reads `Plant modules | 10 | - | Modelling of 10 modules for calculation of staff cost`. The ten modules affect **labour cost only** — output, capital, and every other line are single-module. A reader who takes the subtitle at face value will report a 3.8 kt/yr plant from a model that priced 379 t.

**W9. `Hover a row to light its ribbon` does effectively nothing.** I pixel-diffed the diagram with and without hover over stream row 1. Maximum channel-sum delta across 1.18 M pixels: **19 out of 765 (2.5%)**. Region means: the hovered ribbon itself changes by **0.0**; the adjacent electrolyzer block lightens by 6/255 (2.4%); everything else moves by ≤0.9/255. The mechanism exists; it is invisible. `/tmp/r3-B08-diag-nohover.png` vs `/tmp/r3-B09-diag-hoverrow2.png`

**W10. Year 0 or year 1?** The Plant subtitle says `year 1 of 20`, the stream table column is `YEAR 1`, and the dispatch prose says `One cell per hour of operating year 0`.

**W11. Four decompositions of the same eleven numbers, none cross-referenced.** Home splits into seven bands (`CAPITAL / REPLACE / FIXED OP / VAR OP / FINANCE / TAX & EOL / SALV`, with CAPITAL at 31.1%); the Answer into four families (CAPITAL at 36.2%, replacement folded in); the Plant COST lens into eight tributaries and then three buckets that do not tie to those tributaries; the Report into no groups at all, in file order, without shares. Every one is internally correct. Nothing tells you they are the same eleven rows. Round 2's C10, now with a fourth entry.

**W12. Precision and basis are inconsistent in the wrong direction.** The Answer uses 3 significant figures throughout (`1.29`, `0.215`, `0.00135`) and says so in its footer. The Report — the artifact a scientist actually cites — uses 4 decimal places (`+1.2915`, `+0.0013`, which silently drops `0.00135` to two significant figures), in a different order, without shares, and **without the `(2016)` dollar-year basis that the ephemeral black bar on Plant carries.** The exportable artifact is less rigorous than the screen.

**W13. `Power Generation > Available energy (hourly) = 0 J`** still appears in the COMPUTES panel, unexplained, next to a figure showing 93,487 MWh of sunlight. Round 2's item 4.

**W14. The Report page promises `warnings, provenance` and shows neither.** `The printout — A typeset one-pager: readout, composition, warnings, provenance.` The preview (the full page; `scrollHeight` = `clientHeight` = 1000) contains a title, the LCOH, three bullets, and a cost table. The 10,000.12 USD/kWh warning that the Answer leads with does not appear.

**W15. Three `WHAT IT DOES` cells are still empty** on the Workflow table — 201 Hourly Irradiation, 301 Reverse Osmosis, 302 Power Management (round 2 measured 8 of 17, so this is progress). Two data typos ship through: `Simulating mutliple plant modules` on 401, and 205 Stored Power Electrolysis carrying 203 Electrolyzer's docstring verbatim.

---

# Part 6 — Regression check against design-review-2

### The central charge

> *"the flowsheet must win on wiring or it is decoration with a large footprint"* · *"It hides the money."*

**Answered — by replacing the centerpiece, not defending it.** The flowsheet is demoted to a supporting figure. The new process figure encodes every quantity geometrically, annotates its own scale breaks, and has a COST lens whose eight stations sum to the headline exactly, laid out on the same spatial spine as the energy view. The money is no longer hidden; it is a lens toggle away, in the same geometry. What remains of the original complaint applies only to the demoted flowsheet, where it is still largely true.

### Round 2's Top 10

| # | round-2 fix | status | evidence |
|---|---|---|---|
| 1 | `fit` must fit; raise canvas height | ⚠️ **Half** | `fit` → `viewBox="-24 -24 1844.75 1570"`, **0/17 off-canvas** ✅. But scale 0.459 → titles at **6.9 eff. px** and **all stream labels vanish**; canvas still 846×720; at default zoom 7 nodes clipped and the cue says 6. `/tmp/r3-B11-flowsheet-fit.png` |
| 2 | Primary-button contrast | ✅ **Fixed** | Inner `<p>` now `rgb(255,255,255)` on `#4F7132` = **5.58:1**, pixel-verified. `/tmp/r3-B06-runbtn.png` |
| 2b | Reference/unit chip green | ❌ **Not fixed** | Still `rgb(21,130,55)` on `rgb(248,249,251)` at **9.84 px** (4.66:1), and `#F8F9FB` is still Streamlit's cool grey on a warm `#FAF9F5` page |
| 3 | UNIT column width; COMPUTES overflow | ✅/⚠️ | Unit input 31 → **59 px** with quantity-kind placeholders ✅; `kg/kWh` still elides. COMPUTES table **fully fixed** (359 px in a 359 px parent, right edge 1568 < 1600) ✅ |
| 4 | Replace `<1 ms` with the headline number | ⚠️ **Form yes, payload no** | `11.1 M USD`, `284 k USD`, `4.19 USD/kg` ✅ — but `0 J` ×2, `10 year` ×2, bare `0.6`, three cards blank, and titles now truncate. **New regression.** |
| 5 | Stream labels: size, attachment, no truncation | ⚠️ **Partial** | Truncation gone, size up; still unattached, still overprinting, and absent entirely below ~60% zoom |
| 6 | Clickable ledger; close the levelisation gap | ✅ **Fixed, brilliantly** | Rows expand to second level + 5–6 step derivation; `NAIVE ✗ −48.4%` vs `LEVELIZE ✓`; *"7,682,587 kg shipped into an effective 3,966,584 kg — 51.6%"*. Two rows re-derived by hand; both check. `/tmp/r3-D04-fixedop-expanded.png` |
| 7 | Client-side validation; blame the right field | ✅ **Fixed** | `Electrolyzer > Nominal power: "abc" is not a number…` + `Nothing was applied` + last good run preserved. Gaps: no `aria-invalid`, no red field, Apply not disabled. `/tmp/r3-H02-invalid.png` |
| 8 | Dirty state + semantic delta colour | ⚠️ **Half** | Delta fully specified and colour-coded (`#9BC47E` down / `#E0956B` up) with the change named ✅. **No dirty state anywhere**, and the delta is on Plant while the edit is on Inputs ❌ |
| 9 | Colour key, hover headline, keep selection, keyboard | ✅ **Mostly** | Domain-word legend ✅; hover headline is `Electrolyzer` ✅; `role="button"` + `aria-label` on all 17 nodes, 21 focusables ✅; selection now tinted ✅. Hover card still occludes the next two nodes ❌; `Electrolyzer` rail label still clipped by the cards ❌ |
| 10 | Header band, precision, `$`-year, wheel-zoom | ⚠️ **Mostly** | `4.1943 USD(2016)/kg` ✅; bar hugs content ✅; h1 centre 86 vs Run centre 82 ✅; `⌘/Ctrl+wheel` gating ✅. `stHeader` still `flex`/60 px ❌; sidebar still `17 plugins · functional unit kg` ❌; **responsive got worse** ❌ |

### Round 2's "still confusing" list

| | item | status |
|---|---|---|
| 1 | `CLOCK / SUN / CELL / LEDGER / SCALE` metaphors | ✅ Fixed — `framework / solar / conversion / storage & power / water / cost / scale-out` |
| 3 | `17 plugins · functional unit  kg` | ❌ Not fixed, character for character |
| 4 | `Available energy (hourly) = 0 J` | ❌ Not fixed |
| 5 | `Yearly operation data` blank cell | ✅ Fixed — renders `—` |
| 6 | `array[20] J (71 368 551 439.876 …)` | ⚠️ Improved — sparkline + range, still `326 467.348 … 378 915.062` at 6 dp |
| 7 | Error blames the wrong plugin | ✅ Fixed |
| 8 | `not run yet` after successful runs | ✅ Fixed |
| 9 | `Δ ±0.0000 / reference 4.1943` unexplained | ✅ Superseded by the Σ SELF-AUDIT plate, which explains itself |
| 10 | `Workflow` DESCRIPTION empty for 8 of 17 | ⚠️ 3 of 17 remain (201, 301, 302) |
| 11 | Inputs sidebar implies a false hierarchy | ❌ Not fixed — 201–205 still nested under 200 Inflation, now with vertical rules that make it look *more* like a tree |
| 12 | Report: three identical buttons, no primary | ⚠️ Context copy added; still three `secondary` buttons, now at **two different y positions** (203, 203, 183) |
| 13 | Source: plain `<textarea>` | ❌ Not fixed — 174 lines in a 518 px box, `resize:none` |
| 14 | Responsive floor ~1400 px | ❌ **Regressed.** At **1280** the Run button overlaps the black bar mid-sentence; at **1100** the bar runs off the right edge with no scrollbar. Sidebar still never collapses. `/tmp/r3-I01-plant-1280.png`, `/tmp/r3-I02-plant-1100.png` |
| 15 | COMPUTES table overflow | ✅ Fixed |
| — | `Source Serif 4` declared but unloaded | ✅ Fixed — `Source Serif 4 400` loaded and in use for headings |
| — | `body { font-family }` doubled stack | ❌ Not fixed — still `"Source Sans", sans-serif, "Source Sans", sans-serif` |
| — | Results Explorer: ~35 flat accordions | ❌ **Regressed to 43**, structure unchanged |
| — | Singular/plural table pairs | ❌ Not fixed — all five pairs still adjacent and unmarked |

**Newly broken since round 2:** the ledger pathway tabs (W1), the dispatch `EXAMPLE` chips (W2), the cash-flow left clip (W3), node-title truncation on the flowsheet, and the responsive breakpoint moving from ~1400 to ~1300.

---

# Top 10 fixes, prioritised

### 1 — Wire the five ledger pathway tabs, or remove them

`.case[data-case][aria-pressed]` on the Answer page's ledger is inert to both mouse and programmatic click; `aria-pressed` stays `true` on `pv_e` forever. Five controls promising cross-pathway cost comparison, on the page that is otherwise the best thing in the build. Fix the handler; if the comparison data is not available client-side, route the click through Streamlit like the dispatch `TIME BASE` toggle already does (that one works). **Same class of bug, same file family:** the dispatch `EXAMPLE` chips (`pv_e / pv_e_lcoe / thermal`) set their pressed state and re-render the *same* pathway, which is worse than doing nothing — the chip claims you are looking at `thermal` while the plate says `PV + Electrolysis`. And `thermal` has no hourly model at all, so it should not be offered here. Audit every `cursor:pointer` + `aria-pressed` element in the figure components in one pass.
*Evidence: `/tmp/r3-L01-ledger-thermal.png`, `/tmp/r3-M03-thermal-pressed-header.png`, `/tmp/r3-M05-thermal-14s.png`*

### 2 — Un-clip the cash-flow figure

`.sheet` is 1,354 px at `x = −59` inside a 1,236 px `overflow-x: hidden` window. Fifty-nine pixels — the left edge of every label in the summary column, the legend, and the caption — are unreachable at the app's own default width. Either scale the sheet to its container (as the ledger figure already does: 1,236 in a 1,236 window at x=0) or reflow the summary column. Add a build-time assertion that no figure's `.sheet` has a negative `x` or a width exceeding `window.innerWidth`.
*Evidence: `/tmp/r3-D03-cashflow-clip.png`*

### 3 — Raise the secondary caption layer out of the 2.4:1 / 7 px basement

Every unit, spec, efficiency and axis tick in the two flagship figures is `rgb(169,163,149)` at **6.6–7.3 effective px** on `rgb(250,249,245)` — **2.4:1**, against AA's 4.5:1 — and that includes `THE SURVIVING 20,567 MWh IS DRAWN BELOW, AT 4.5× THIS SCALE`, the sentence the figure's honesty rests on. Take the caption ink to something near `#6A6459` (≈ 5.6:1) and the floor to 10 px. Twenty-three percent of the process figure's text and thirty-one percent of the dispatch plate's is at or below 8 px; there is horizontal room in both. Also lift the `<code>` reference chips off Streamlit's cool `#F8F9FB` onto the warm ground, and raise them from 9.84 px to 12 px.

### 4 — Fix the four numbers that disagree with other numbers

All four are one-line corrections and each one undermines a page whose whole argument is arithmetic integrity:
- `PER YEAR 352,119 kg/yr · 1,038 kg a day` — 352,119 ÷ 365 = 964.7. Either show `965 kg a day` or label the pair `nameplate year 378,915 kg/yr · 1,038 kg a day`.
- `BATTERY · 0 MWh curtailed` vs `the other 85.3 MWh is curtailed` on the same page. The second is right.
- `cell runs 4,389 h/yr on stored power` against `HOURS THE STACK RAN 4 094 h`.
- The `ENERGY BALANCE` panel splits PV generation exactly two ways (18,860.7 + 1,706.5 = 20,567.2) while the stream table above sends a third stream (23.0 MWh to Desalination) out of the same node. Add the line or explain the exclusion — do not print `Σ RECONCILES` over a gap.

Then reconcile `year 1 of 20` / `YEAR 1` / `operating year 0`, and qualify `one of 10 identical modules` with what the source file itself says: *for staff cost only*. As written it invites a 10× error on plant output.

### 5 — Put the delta where the edit happens

The Plant page's `▼ -0.0681 vs 4.2624 · Electrolyzer > Nominal power: 6000 → 5500` is exactly right and is on the wrong page. Render the same component at the top of the Inputs worksheet. Then add the dirty state round 2 asked for: a 2 px left accent and `was 5,500` under any changed field, a per-field revert, `4.1943 — stale, 1 pending edit` on the bar, and a `Reset to reference` action — the Inputs page currently has exactly one button, and there is no route back to a value you have overwritten. Normalise `6000` → `6,000` on blur so it stops sitting next to `80,000`.
*Evidence: `/tmp/r3-C05-dirty-crop.png`, `/tmp/r3-C08-after-apply-settled.png`, `/tmp/r3-H05-plant-header.png`*

### 6 — Make the Source page worth its title

`THE SINGLE SOURCE OF TRUTH` is a 174-line file in a 518 px `resize:none` textarea — 15% visible, no line numbers, no highlighting, no find. It is also the destination the Answer page sends you to (`Check Grid Electricity › Cost`) and where the 10,000.12 defect lives, on line 167. Minimum: CodeMirror or equivalent with line numbers, markdown-table highlighting, `⌘F`, a section jump list built from the `#` headings, and deep links so `Check Grid Electricity › Cost` scrolls to and highlights the cell. Group `Apply` and `Download .md` and make `Apply` visually dominant — right now the secondary button is 111 px and the primary is 59 px, 141 px apart.
*Evidence: `/tmp/r3-F01-source.png`*

### 7 — Give the Home page the warning the rest of the app leads with

The Answer opens with a red banner and the Bench devotes a footer section headed **Known defect** to the fact that 19% of `4.1943` comes from `Cost | 10000.12 | USD/kWh`. Home shows the number under `PYH2A REFERENCE INPUT SET` with `✓ checked  all 5 reconcile`. Add a per-row flag — a small `⚠ 1 note` chip next to the affected pathways' cost, linking to the Answer banner — and soften the global `✓ checked` to `✓ arithmetic reconciles · 1 input flagged`. Reconciling and being right are different claims and this page currently merges them.

### 8 — Decide what `fit` is for, and stop making the flowsheet choose between legible and complete

Today `fit` shows all 17 nodes at 6.9 px with **zero stream labels**, and the default 78% shows readable nodes with 7 clipped. Neither view answers "how is this plant wired". Three concrete moves: (a) raise the component height from 720 to ~1,000 px; (b) drop the label gutter from the fit bounding box — it currently reserves 1,845 units of width for labels it then hides, which is why the fit scale is 0.459; (c) two-column the 17-row stack so the aspect ratio matches the frame. Then fix the carry-overs: `+` zooms to the viewport centre, which after `fit` is empty space (five presses lands you at 170% with no nodes on screen); node titles truncate to `Labor Operating Co…` because the card packs index + value + title + `in N · out M` into 179 units; the `Electrolyzer` bus-rail label still runs under the cards; and the hover card still covers nodes 204 and 205.
*Evidence: `/tmp/r3-B11-flowsheet-fit.png`, `/tmp/r3-B12-rail-labels.png`, `/tmp/r3-B13-flowsheet-zoomed.png`*

### 9 — One decomposition of the eleven components, referenced everywhere

Four groupings currently coexist: Home's seven bands (`CAPITAL 31.1%`), the Answer's four families (`CAPITAL 36.2%` — the difference is Replacement), the COST lens's eight tributaries plus three non-tying buckets (`BUILD IT 1.2929` against an equipment tributary sum of 1.5068), and the Report's ungrouped file order at a different precision. Pick the Answer's four families as canonical, express the other three as declared re-groupings of it, and print the bridge where they differ (`BUILD IT 1.2929 = equipment 1.5068 − stack replacement 0.2139, filed under RUN IT`). Bring the Report to 3 significant figures, add the SHARE column, add the family subtotals, and put `USD(2016)/kg` on the exported headline — the ephemeral black bar carries the dollar-year basis and the citable artifact does not.

### 10 — Finish the small honest details

- **Explain the superscript.** `Initial equity depreciable capital³` is `<span class="items">` — a count of second-level entries — rendered as a footnote reference with no footnote, at 10 px and 2.4:1. Make it `▸ 3 parts` or put it in the disclosure triangle.
- **Make `Hover a row to light its ribbon` visible.** Measured effect: 2.4% lightening on one adjacent block; the hovered ribbon itself changes by 0.0. Either dim non-selected ribbons to ~35% and stroke the selected one, or delete the promise.
- **Annotate the cost ogive.** The smooth curve between stations implies gradual accrual; the data is a step function. Every other compression in this build is labelled (`4.5× THIS SCALE`, `COMPRESSED 4.1:1 · NO RANGE OMITTED`, `AXIS BROKEN AT 5.7`). Either step the line or say `smoothed between stations`. While there, add a three-swatch key for the tan/green/purple bands.
- **Say why the battery is zero.** `+0.0000 USD/kg`, `0 MWh curtailed`, `0 J` — three zeros across three views, with the explanation three pages away in the Bench. One clause on the Sankey (`design capacity never binds — see Bench 08`) closes it.
- **Fix `a local optimum sitting on the base`** on Bench panel 06 — the base is a local cost *maximum*, and both ±20% ends are cheaper.
- **Reclaim the 60 px `stHeader`**, which is still `display:flex; height:60px` and transparent on every page, and fix the responsive break: at 1280 the Run button overlaps the result bar mid-sentence, at 1100 the bar runs off-screen with no scrollbar, and the 300 px sidebar never collapses.
- **Give Home's five pathway rows `role="button"`, `tabindex="0"` and an `aria-label`.** The gallery iframe has exactly one focusable element and it is `BROWSE ▸`. The flowsheet got proper keyboard access this round; the front door did not.
- **Report page:** the three download buttons sit at y 203, 203 and **183**; the `The file` heading (y 124, x 332) overlaps the h1 box (y 94–125, x 332) and reads as its subtitle; and the printout preview promises `warnings, provenance` and delivers neither.

---

## Screenshot index

| path | what |
|---|---|
| `/tmp/r3-A01-home-top.png` | Home, full viewport |
| `/tmp/r3-A02-anatomy.png` | Anatomy matrix, 22 columns × 5 pathways, 3× |
| `/tmp/r3-A09-row01.png` | Pathway row 01, 4× — big number, composition bar, footprint |
| `/tmp/r3-A10-hover-row1.png` | Home row hover state |
| `/tmp/r3-A13-after-open-20s.png` | Plant on arrival, ENERGY lens |
| `/tmp/r3-B-plant-scroll-900.png` | Dispatch plate, energy balance, `Σ RECONCILES` |
| `/tmp/r3-B-plant-scroll-1800.png` | `THE MODEL` flowsheet at default 78% |
| `/tmp/r3-B01-sankey.png` | Sankey detail, 3× — `0 MWh curtailed`, `4,389 h/yr` |
| `/tmp/r3-B03-cost-lens.png` | Plant, COST lens |
| `/tmp/r3-B04-cost-chart.png` | Cost accretion chart, 4× |
| `/tmp/r3-B06-runbtn.png` | Run button, 6× — contrast fixed |
| `/tmp/r3-B08-diag-nohover.png` / `/tmp/r3-B09-diag-hoverrow2.png` | Hover A/B, pixel-diffed |
| `/tmp/r3-B10-table-hoverrow2.png` | Stream table hover row, 4× |
| `/tmp/r3-B11-flowsheet-fit.png` | `fit` — all 17 nodes, no stream labels, 6.9 px |
| `/tmp/r3-B12-rail-labels.png` | Rail label clipped by cards; truncated node titles, 8× |
| `/tmp/r3-B13-flowsheet-zoomed.png` | 170% after `fit` — zero nodes visible |
| `/tmp/r3-B14-node-click.png` | Node selected, side panel, hover card occluding 204/205 |
| `/tmp/r3-C01-inputs.png` | Inputs — Project / Workflow table |
| `/tmp/r3-C02-inputs-electrolyzer.png` | Electrolyzer worksheet |
| `/tmp/r3-C05-dirty-crop.png` | `6000` typed, no dirty state, 3× |
| `/tmp/r3-C06-dirty-sidebar.png` | Sidebar, `functional unit kg`, 5× |
| `/tmp/r3-C08-after-apply-settled.png` | After Apply & run — no delta on Inputs |
| `/tmp/r3-D01-answer-top.png` | Answer — warning banner, ledger, row 01 derivation |
| `/tmp/r3-D-answer-950.png` | Σ SELF-AUDIT plate; cash-flow section head |
| `/tmp/r3-D-answer-1900.png` | Cash-flow notes; Results Explorer begins |
| `/tmp/r3-D-answer-2850.png` / `/tmp/r3-D-answer-3444.png` | 43 accordions; singular/plural pairs |
| `/tmp/r3-D03-cashflow-clip.png` | 59 px clipped off the cash-flow figure, 4× |
| `/tmp/r3-D04-fixedop-expanded.png` | Fixed operating costs — second level + derivation |
| `/tmp/r3-E01-bench.png` | Bench — influence ranking |
| `/tmp/r3-E02-bench-630.png` | Bench — response curves, method footer, known defect |
| `/tmp/r3-F01-source.png` | Source page — the weakest screen |
| `/tmp/r3-G01-report.png` | Report page |
| `/tmp/r3-H02-invalid.png` | Invalid input — correct field named, last run preserved |
| `/tmp/r3-H05-plant-header.png` | Black bar with signed, named, coloured delta, 4× |
| `/tmp/r3-I01-plant-1280.png` | 1280 — Run button over the result bar |
| `/tmp/r3-I02-plant-1100.png` | 1100 — bar clipped off-screen |
| `/tmp/r3-J01-run-pressed.png` | Run pressed — no visible pulse above the fold |
| `/tmp/r3-J03-run-header.png` | `= unchanged` state, 4× |
| `/tmp/r3-K02-dispatch-hover-crop.png` | Dispatch hover — hour card, day strip, crosshair |
| `/tmp/r3-L01-ledger-thermal.png` | Pathway tabs — clicked, nothing changed |
| `/tmp/r3-M01-dispatch-rawutc.png` | `Raw UTC` — a toggle that works |
| `/tmp/r3-M03-thermal-pressed-header.png` | `thermal` selected, PV + Electrolysis shown, 3× |
| `/tmp/r3-M05-thermal-14s.png` | Same, 14 s later, re-painted, still pv_e |
