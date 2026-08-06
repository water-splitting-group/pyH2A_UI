# Paper Plant Studio — cold design review, second pass

Reviewer: ConfirmDesign. Confirmation round against `studio-review-1.md` (D1–D29).
Target: `http://127.0.0.1:8730`, own tab (`window.name = COLD2-REVIEW-DONOTTOUCH`), 1600×1000 @2×,
own server session (`tmsgjocu9lc2koz`). Evidence: 9 captures in `notes/shots-cold2/`, plus
`studio/scratch/cold2_bounds.py` (headless bounds sweep across all five shipped pathways).
Every measurement below was retaken with the same method as the original — computed WCAG ratios,
CSS-pixel envelopes, element counts, tab stops — not read off the commit message.

Captures: `01-overview-100` (first contact), `02-400-eqrows` (the CAPEX table in full, the single
most informative frame in this set), `03-202-calendar-flat`, `04-201-calendar-ramp`,
`05-900-annual`, `06-201-ranges`, `07-203-readonly-trap`, `08-400-eq-wrap-1440`,
`09-400-eq-wrap-1600`.

---

## Headline

**Thirteen of twenty-nine defects are genuinely closed.** The remove-step control, the source
drawer, reload persistence, the annual chart, unit search, the equation units, the required/optional
contradiction, the arrow/extent contradiction, the sparkline collision, the five pathway names, the
chooser's published-vs-live provenance, and the dead series button are all fixed, and I verified
each one by the same measurement that condemned it. That is real work.

**Three of the most confident fixes were reasoned to and never looked at**, and all three fail the
same way — the author decided what the fix should be and shipped it without measuring the output:

1. **The contrast fix is inert.** `--ash-ink: #726C5D` exists, and `studio.css:13-18` assigns it to
   the whole secondary layer. Then **23 of that rule's 27 selectors are re-declared
   `color: var(--ash)` later in the same file**, and the cascade takes the later one. I measured the
   original eight pairs again and got **2.24, 2.24, 2.38, 2.38, 2.38, 2.51, 2.51** — identical to
   the first pass, to the decimal. 248 text nodes fail AA on step 100 alone. The single item the
   last review called "the most consequential change in this list" has had **zero effect on screen**.
2. **The hourly calendar now encodes no magnitude at all.** The geometry fix is excellent — the
   seasonal lens went from a ±4 px signal to a 62.5 px swing and is finally visible. But on step 202
   all 4 315 cells render at `opacity="0.220"`: **one distinct value**, min = median = p90 = max.
   The panel still says "Ink is magnitude" under a gradient key. It was hard to read; it is now
   impossible.
3. **A field declared in `degC` shows `range -68 038 … -136 075`.** The bound converter multiplies
   by `engine.convert(1.0, base, unit)`, which for an offset unit returns `-272.15`. `45 degC` now
   sits above an inverted, negative range on four of five shipped pathways. D1's exact complaint —
   a field displaying a value outside its own stated range — reproduced by D1's fix.

And one new trap: **after a bad keystroke you cannot fix the field you broke.** Every step marked
`never reached` renders with zero editable inputs, including the field holding the bad value.

**Thinking: B+. Execution: C+.** Graded at the end, separately, and not carried forward.

---

## Per-defect verdict

| # | Defect | Verdict | Measured now |
|---|---|---|---|
| D1 | Percent field vs fraction range | **PARTIAL** | 508/512 fields correct; 4 inverted (`degC`) |
| D2 | Multiplier labelled with product's unit | **FIXED** | `784 per kW × 5 500 kW = 4 312 000 USD` |
| D3 | Equation does not read as an equation | **PARTIAL** | operator fixed; 3/4 rows wrap at 1600, 4/4 at 1440 |
| D4 | Enter arms an invisible binding mode | **FIXED** | bar 0×0 after Enter and Tab; hidden buttons `pointer-events:none` |
| D5 | Search misses units and own outputs | **FIXED** | `kW`→4, `Wh/m2`→4, `deg`→3, `m2`→9; `tracking` on 201→6; `Levelized` on 900→2 |
| D6 | Dead middle series button on 202 | **FIXED** | activates from both neighbours, no 400, no toast |
| D7 | Calendar contradicts its caption | **PARTIAL** | 300 px panel, 62.5 px envelope, 365 tooltips — but ramp has **1 distinct value** on 202 |
| D8 | Four series, four normalizations | **PARTIAL** | 201 siblings share 952.5 Wh/m²; 202 shares across incompatible units |
| D9 | 20 of 43 bars at zero height | **FIXED** | **0** zero-height rects; 21/21 years have a full-height hit target |
| D10 | Two figures, no stated basis | **FIXED** | `DISCOUNTED, PER KG` / `NOMINAL, NOT DISCOUNTED · 34.2 M USD OVER 21 YEARS` |
| D11 | Upstream values masquerade as user input | **PARTIAL** | `Years` no longer a blank box; counters still reclassify computed → to enter |
| D12 | Misattribution notice on steps it contradicts | **STILL BROKEN** | both cases verbatim unchanged |
| D13 | No remove, no undo, no save, reload discards | **MOSTLY FIXED** | remove/source/download/reload all work; **no dirty marking**, no undo |
| D14 | Masthead names the pathway five ways | **FIXED** | all five match the chooser exactly |
| D15 | Chooser shows a constant styled as a result | **FIXED** | `PUBLISHED` label; `139.4189` / `185.4433`; masthead agrees on all five |
| D16 | Four notations, headline at three precisions | **PARTIAL** | `-0.0%` and year separators gone; `4.194` vs `4.1943` and `1.11e+7` ×6 remain |
| D17 | Secondary text fails contrast by half | **STILL BROKEN** | 2.24 / 2.38 / 2.51 — unchanged to the decimal |
| D18 | No labels, no semantics, no figure alternatives | **PARTIAL** | aria-labels + rail 1 stop + designed ring; sparklines still bare; arrows drop focus |
| D19 | `a → b` ordering contradicts the sparkline | **FIXED** | `→` chronological, `…` extent; row 4 no longer disagrees |
| D20 | Sparkline touches the numeral | **FIXED** | min gap 8 px (was 0); 46 px right pad in the scope column |
| D21 | Section counts label the wrong axis | **FIXED** | `TIME 1 computed`, `INFLATION 4 computed`, `2 tables · 3 rows` |
| D22 | `required` and `optional` 40 px apart | **FIXED** | `Module tilt` placeholder empty, `-` unit placeholder, no `.waiting` |
| D23 | Engine vocabulary throughout | **PARTIAL** | `UNDECLARED` gone, keys glossed; `sum_all_tables`, `dcf.inp`, `on_demand`, `Cost_Path` remain |
| D24 | Truncations with no recovery | **PARTIAL** | 5 of 9 clipped elements gained a `title`; 4 path inputs still bare |
| D25 | Picker truncates exactly what differs | **PARTIAL** | tail preserved, `+N more`, gap closed; no titles, `(e.g.` still unclosed, no search |
| D26 | `6 INPUTS NOTHING SUPPLIES` contradicted | **STILL BROKEN** | verbatim unchanged, self-listed writer included |
| D27 | Toasts cover persistent content | **STILL BROKEN** | opaque, bottom-anchored, covers three elements; still names no field |
| D28 | Tabs shared one project | **FIXED** | per-tab session; three studio tabs open, no cross-talk |
| D29 | Twenty smaller things | **PARTIAL** | itemised below: 1 fixed, 5 improved, 2 worse, 12 unchanged |

---

## Detail and evidence

### D1 — PARTIAL. The conversion is right for 508 fields and catastrophically wrong for 4.

The percent side is genuinely fixed. Measured on the four steps named in the brief:

| step | field | value | declared range shown |
|---|---|---|---|
| 100 | Capital spent in 1st year of construction | `100%` | `range 0% … 100%` ✓ |
| 201 | Mismatch derating / Dirt derating | `98%` | `range 0% … 100%` ✓ |
| 201 | Temperature coefficient | `-0.4%` | `range -50% … 50%` ✓ |
| 201 | Array azimuth | `180 deg` | `range 0 … 180` ✓ |
| 202 | Power loss per year / Efficiency | `0.5%` / `22%` | `range 0% … 100%` ✓ |
| 203 | Power requirement increase per year | `0.3%` | `range ≥ 0%` ✓ |
| 203 | Minimum capacity | `10%` | `range 0% … 100%` ✓ |

All six fields the first review named now read correctly. **Shot:** `06-201-ranges.png`.

**But** `frame._display_factor` derives the factor as `engine.convert(1.0, base, unit)`, which is a
pure ratio. For an offset unit it is not:

``
engine.convert(1.0, 'K', 'degC')  ->  -272.15
``

so declared bounds `[250, 500] K` print as `250 × -272.15 = -68 037.5` and `500 × -272.15 = -136 075`.
On screen, in `06-201-ranges.png`, directly under a field reading `45`:

``
03  Nominal operating temperature   [ 45 ]  [degC]
    absolute_temperature   range -68 038 … -136 075
``

Low is greater than high, both are negative, both are five orders of magnitude out, and the value is
outside the range in either reading. Sweep over all five shipped pathways
(`studio/scratch/cold2_bounds.py`): **512 fields carry a displayed range, 4 are suspect, and all four
are this same cell** on `pv_e`, `pec`, `photocatalytic`, `pv_e_lcoe`. Before the fix this field
showed `range 250 … 500` — confusing, but ordered and positive. This is worse than what it replaced.

Second, smaller residual: the conversion only fires when the cell has an authored unit. `Module tilt`
has none, so it shows `range 0 … 1.57` (radians) two rows above `Array azimuth`'s `range 0 … 180`
(degrees). Two angle fields, adjacent, in two unit systems.

### D2 — FIXED.

Step 400, all four CAPEX rows now read as dimensionally sound equations:

``
784  per kW  ×  {Electrolyzer > Nominal power ...}  5 500 kW  =  4 312 000 USD
818  per kW  ×  8 250 kW                                      =  6 748 500 USD
6000 per m3/h × 5.815 m3/h                                    =  34 893 USD
0.   per kWh  × 800 000 kWh                                   =  0 USD
``

The `per <unit>` chip is derived from the reference, and the result's unit moved onto the result.
Step 800's `Electrolyzer OPEX (fraction of CAPEX)` now renders `86 240 USD` — the computed product,
correctly labelled — rather than `0.02 USD`.

Residual, minor: the chip states only the denominator. `784 per kW` does not say USD; the currency is
recoverable from the product and from the `currency` dimension on the meta line, but a reader
checking units left-to-right meets an incomplete one first.

### D3 — PARTIAL. Right idea, and it does not fit.

Two of the three failures are fixed: the operands are now adjacent to their operator on a single flex
row, and `×` / `=` are 15 px in `--graphite` (`rgb(85,82,74)`), the largest glyphs on the row rather
than the smallest and palest.

The third is not. On a fresh 1600×1000 load, `#needs` is 584 px, `.field` is 520 px and `.eq` is
474 px, and `.eq` has `flex-wrap: wrap`. Measured heights on step 400:

| row | eq height | product position |
|---|---|---|
| Reverse osmosis CAPEX | **57 px** (two lines) | x 374, one line below the multiplier |
| Battery CAPEX | 27 px | inline |
| PV CAPEX | **57 px** | x 374, below |
| Electrolyzer CAPEX | **57 px** | x 374, below |

At 1440×900 and 1280×800, **all four** wrap. `02-400-eqrows.png` shows all three states in one frame
— `Battery CAPEX` inline, `PV CAPEX` and `Electrolyzer CAPEX` broken — and
`09-400-eq-wrap-1600.png` zooms one: the row
reads `784 per kW × {Electrolyzer > Nominal power > Val  5 500 kW =` with the `=` dangling at the
right margin, and `4 312 000 USD` alone on the next line back at the left, directly beneath `784`.
The path input is clipped mid-token to an unclosed `{Electrolyzer > Nominal power > Val`, with no
`title`. The most load-bearing table in the app — the one the original review cited — still does not
read as an equation at the reviewer's own viewport.

Step 202's single row does fit (27 px), but see N9: it now reads `1.5 × unresolved = 8 250 kW`.

### D4 — FIXED.

| probe | first pass | now |
|---|---|---|
| binding bar after focus | 0×0 | 0×0 |
| binding bar after **Enter** | 655×26 | **0×0** |
| binding bar after **Tab** | 655×26, retargeted | **0×0** |
| hidden buttons | `opacity:0`, `pointer-events:auto` | `opacity:0`, **`pointer-events:none`** |
| button label / action | `USE` → performs copy | **`copy`**, `title="copy this reference"` |

There is now an explicit `+ bind a path` control on reference-bearing steps, and pressing it toasts
`pick a value on the right to bind it here`. The feature is discoverable and the accidental arming is
gone.

Residual: the `+ bind a path` control measures **78×13 px** and is drawn in `rgb(169,163,149)` at
2.38:1 — the app's newly-discoverable feature is rendered in its least legible ink. And 95 `opacity:0`
buttons are still in the tab order (see D18).

### D5 — FIXED, with a new cap.

Unit lookup works, and the current step's own outputs are indexed:

| query | step | first pass | now |
|---|---|---|---|
| `kW` | 203 | 0 | **4** |
| `Wh/m2` | 203 | 0 | **4** |
| `deg` | 203 | 0 | **3** |
| `m2` | 203 | 0 | **9** |
| `USD` | 900 | 0 | **47** |
| `tracking` | 201 | 0 | **6** |
| `Levelized` | 900 | 0 | **2** |

`USD` → 0 on step 203 is correct: no cell in scope at 203 carries USD. New defect N7 below: above 40
matches the list is silently truncated.

### D6 — FIXED.

Driven deterministically from both neighbouring states with 4.5 s settles, as the original was:
from `PV hourly power generation` → click `Available energy (hourly)` → the button takes `on`, the
heading becomes `POWER GENERATION › AVAILABLE ENERGY (HOURLY) · YEAR 0`, 4 315 marks redraw. From
`Data` → same. Zero console errors, zero toasts.

### D7 — PARTIAL, and the ink is a regression.

Geometry, remeasured the same way:

| measurement | first pass | now |
|---|---|---|
| `svg.cal-grid` viewBox | `0 0 1095 120` | `0 0 1095 240` |
| rendered panel | 446×128 CSS px | **517.7×300 CSS px** |
| row height | 5 uu / ~5.3 CSS px | 10 uu / **12.5 CSS px** |
| Jan 5 lit rows | 9 (y 40–80) | 9 (y 80–170, **112.5 CSS px**) |
| Jun 21 lit rows | 14 (y 25–90) | 14 (y 50–190, **175 CSS px**) |
| seasonal swing | ±4 CSS px | **62.5 CSS px** |
| `<title>` in grid | **0** | **365** (`1 Jan · 1.43e+11 J over the day`) |
| scale key | none | `HOUR OF DAY, LOCAL SOLAR TIME … 0 TO 952.5 WH/M2` |
| header claim | `8 760 CELLS` for 4 315 marks | `4 315 LIT HOURS OF 8 760` |
| `role` / `aria-label` | none | `role="img"`, full label |
| year selector for 20y cells | none | 0–19 buttons, `· year 0` in the title |

That is a large, real fix — `04-201-calendar-ramp.png` shows a lens with visible day-to-day weather
texture where the first pass got a flat teal block.

The ink ramp is the opposite. Opacity distribution across the lit cells:

| series | n | distinct | min | median | p90 | max |
|---|---|---|---|---|---|---|
| 201 · Horizontal single axis | 4 315 | 705 | 0.22 | 0.675 | 0.865 | 0.953 |
| 201 · No tracking | 4 315 | 748 | 0.22 | 0.549 | 0.852 | 1.0 |
| 201 · Two axis | 4 098 | 723 | 0.22 | 0.762 | 0.869 | 0.978 |
| **202 · Irradiation Used › Data** | 4 315 | **1** | 0.22 | 0.22 | 0.22 | **0.22** |
| **202 · Available energy (hourly)** | 4 315 | **1** | 0.22 | 0.22 | 0.22 | **0.22** |
| **202 · PV hourly power generation** | 4 315 | **1** | 0.22 | 0.22 | 0.22 | **0.22** |

Every rect on step 202 is `<rect ... fill="currentColor" opacity="0.220"/>`. See N2 for the cause.
On 201 the floor fixed the invisible dawn/dusk cells, but the top end is unchanged: median 0.675
against the original's 0.693. The stated goal — "leaving no range to read magnitude by inside the lit
band" — was not achieved there either.

Still open from D7: the series buttons carry **no `aria-pressed`** (selection is class-only); they are
22 px tall (up from 16, still under a 24 px target); the figure header, the axis caption and the scale
key all wrap, and the key breaks mid-expression again — `0 TO 7.40E+13` on one line, `J` orphaned on
the next (`03-202-calendar-flat.png`).

### D8 — PARTIAL.

Step 201's three tracking modes now share one scale — all three keys read `0 TO 952.5 WH/M2`, and the
header says `· SHARED SCALE`. Comparison is possible for the first time. Fixed.

Step 202's three candidates do not share a *comparable* scale. `renderHourly` computes
`Math.max(...candidates.map(c => c.max))` across series whose units are `kWh/m2` and `J`, so the
`Data` calendar is scaled by a joules figure and its key prints **`0 TO 7.40E+13 KWH/M2`** — a
magnitude and a unit that were never measured together. See N3.

The physical anomaly is unchanged and still unexplained: `No tracking 0 … 953 Wh/m2` against
`Two axis tracking 0 … 931 Wh/m2`, and mean `single axis 284.6 W/m2` against `two axis 283.4 W/m2`.

### D9 — FIXED.

`svg.annual`, 700×190 viewBox rendered 472×190:

- `<rect height="0">` count: **0** (was 20 of 43).
- 64 rects total, **64 carry a `<title>`**.
- 21 full-height transparent hit targets, one per year 0–20, each with a per-year summary
  (`year 1 — Variable operating 1.84 k · Fixed operating 306 k`).
- `role="img"`, `aria-label="annual spend over 21 years, peak 20.3 M USD in year 20"`.
- x-axis ticks `0 5 10 15 20` added; the legend is now headed `LIFETIME TOTALS`.
- The caption volunteers the problem instead of hiding it: *"The axis is linear and spans four orders
  of magnitude, so every other year is drawn at a floor rather than to scale; hover any year for its
  figures."*

That last sentence is the right answer to a chart that cannot be fixed by scaling alone.
**Shot:** `05-900-annual.png`.

### D10 — FIXED.

`WHERE THE KG PRICE COMES FROM — DISCOUNTED, PER KG · 11 COMPONENTS IN 4 FAMILIES`
`WHEN THE MONEY IS SPENT — NOMINAL, NOT DISCOUNTED · 34.2 M USD OVER 21 YEARS`

Both figures state their basis in the subhead. The two numbers no longer look like they should
reconcile, because the page now says why they don't.

### D11 — PARTIAL, and it uncovered something worse.

Fixed: breaking `203 › Nominal power` no longer turns the `Years` row into an empty editable text box
with an empty unit box. It renders `.field computed` reading `not computed — the run stopped earlier`
— honest, and the `NEVER REACHED` banner's promise is no longer contradicted by a blank input.

Not fixed: the counters. Step 203 goes from `5 to enter · 2 computed` to **`7 to enter · 0 computed`**,
and the section header reads `TIME 1 to enter` **directly above** the row that says
`not computed — the run stopped earlier`. The two computed inputs are still silently reclassified as
things you must type, and now the app contradicts itself inside 40 vertical pixels.

Also unchanged: `89 values the engine already holds … · 0 arrive later` on the failed run (89 ≠ 157).

New and worse — see N4.

### D12 — STILL BROKEN. Both cases, word for word.

Break `203 › Nominal power`; open `202 Photovoltaic`. The notice reads:

> The engine blames the step that was running, which is not always the step that owns the bad value —
> paths resolve lazily. Check the flagged fields in the rail **before** this one.

The flagged steps in the rail are `203 Electrolyzer` (badge `1`) and `205 Stored Power Electrolysis`
— both **after** 202. The advice still points the reader the wrong way.

Add `Solar Concentrator` at 201.5. The same sentence appears above `6 INPUTS NOTHING SUPPLIES`, on a
step that owns its own fault, with nothing else flagged, and with the cause named precisely in the
panel below it. Not touched.

### D13 — MOSTLY FIXED. This is the biggest win in the round.

- **`REMOVE STEP` exists and works.** Add `Solar Concentrator` at 201.5 → masthead
  `no cost — the run stopped`, `STEPS 18`, rail dot red. Click `remove step` → `STEPS 17`,
  `LEVELIZED 4.1943 USD/kg`, `17 ran clean`, toast
  `Solar_Concentrator_Plugin removed — its tables are still in the file`. Bit-for-bit back to the
  pre-add cost, from the UI, which the verification sweep could only achieve out of band.
- **`SOURCE` drawer exists**: full markdown, editable, `174 lines · PV_E_Base.md`, with
  `download .md` / `apply` / `close`. I used it to repair a broken cell and the run recovered to
  `4.1943` / `17 ran clean`.
- **Reload preserves everything.** Opened Photoelectrochemical, set `302 › Concentration factor`
  to 20 (`139.4189 → 344.0475`), reloaded: session `tmsgjocu9lc2koz` intact, pathway
  `Photoelectrochemical`, cost `344.0475 USD/kg`, 13 steps. The unconditional `openProject('pv_e')`
  is gone.

Not fixed: **no dirty marking**. After changing `Nominal power` 5 500 → 7 000 the rail entry is still
`class="step ran"`, the field is still `class="field"`, and the words *edited / changed / unsaved /
baseline* appear nowhere in the document. After five edits you still cannot tell what you changed.
No undo, no revert, no baseline diff. Reload also always reopens on step `100 Time` rather than the
step you were reading.

The remove control itself is 83×16 px at 9.5 px in `rgb(169,163,149)` — **2.38:1**. The only
destructive action in the app is drawn in the least legible ink in the app, with no confirmation.

### D14 — FIXED.

| chooser | masthead |
|---|---|
| PV + Electrolysis | `PV + Electrolysis` |
| Solar Thermal | `Solar Thermal` |
| Photoelectrochemical | `Photoelectrochemical` |
| Photocatalytic | `Photocatalytic` |
| PV Electricity | `PV Electricity` |

Five for five. The `PC` cipher and the raw `PV_E_Electricity_Production.md` filename are gone.

### D15 — FIXED.

Each chooser cost now carries a `PUBLISHED` chip under it, distinguishing the pinned constant from
the live masthead figure, and the constants are shown at full published precision:
`4.1943`, `3.2706`, **`139.4189`**, **`185.4433`**, `0.0286`. Opening each pathway gives a masthead
that matches its chooser row exactly, including `0.0286 USD/kWh` (was `0.0286` vs `0.02858`).

Residuals: there is still **no marker for the currently-open pathway** (`aria-current` is `null` on
all five `<li>`); still no warning that opening one discards your edits; and the numbers are
right-aligned at x 1027 with mantissas starting at x 941 / 925 / 934, so the decimal points still
land at three different positions in a five-row comparison table.

### D16 — PARTIAL.

Fixed: `-0.0%` is gone (now `~0%`). Years no longer carry thousands separators anywhere — zero
matches for `2 0\d\d` across step 900 and the scope column. The chooser and masthead agree at four
decimals.

Not fixed:

- **The headline is still at two precisions on one screen.** On step 900 the masthead, the ledger
  total and the Σ line all read `4.1943`; the dark "what this step made" row
  (`TR.made > TD.v > SPAN.q`) reads **`4.194`**. Both are in the viewport together.
- **`1.11e+7` still appears 6 times** on step 400, beside `4 312 000 USD` and `×10⁷`/`×10¹³`
  elsewhere. Three notations for the same magnitudes, unchanged.
- `Battery CAPEX` is still the bare `0.`; `Cost of land` is `500.0`.
- **Enter and blur still format differently**: after an Enter-commit `Nominal power` reads `7000`
  while `Replacement time` two rows below reads `80,000`.
- Unit exponents are still never typeset (`m2`, `m3`, `Wh/m2`, `kWh/m3`) while mantissa exponents are.
- `20y` and `×20` are both still in use for the same concept.

### D17 — STILL BROKEN. The fix is in the file and does nothing.

`tokens.css:14` adds `--ash-ink: #726C5D` with the comment *"4.96:1 on paper … clears AA on both"*.
`studio.css:13-18` assigns it to 27 selectors covering the whole secondary layer. Then the same
stylesheet re-declares `color: var(--ash)` for **23 of those 27 selectors**, later in source order at
equal specificity, so the later declaration wins every time:

``
L  25  .u                     L 380  .tbl-head .note
L 125  .rail-sub              L 394  .field .idx
L 164  .insert .at            L 408  .field .desc
L 187  .step .pos             L 416  .field .meta
L 241  .rail-foot             L 667  .scope-sub
L 267  .step-head .plugin     L 685  .find-hint
L 273  .step-head .counts     L 743  .grp-head .n
L 338  .unmet .d              L 748  .tblgrp-head
L 359  .section-rule .count   L 782  .cell-row .r .col
                              L 793  .cell-row .v .u
                              L 874  .plugin-row p
                              L 882  .plugin-row .fit
                              L 912  .chooser-panel li p
                              L1108  .source-state
``

The eight pairs from the first review, remeasured with the same computed-WCAG method:

| element | example | size | first pass | **now** |
|---|---|---|---|---|
| rail footer (run health) | `17 ran clean` | 10 px | 2.24 | **2.24** |
| rail step numbers | `200`, `201` (×16) | 11 px | 2.24 | **2.24** |
| field dimension + range | `range 0 … 1.57` | 9.5 px | 2.38 | **2.38** |
| field descriptions | every one | 12 px | 2.38 | **2.38** |
| section counts | `1 to enter` | 10 px | 2.38 | **2.38** |
| scope units | `Wh/m2`, `kg` (×105) | 9.5 px | 2.51 | **2.51** |
| scope group heads / row cols | `Cost Path` (×15) | 10 px | 2.51 | **2.51** |
| masthead labels | `.kicker` | 10 px | 4.43 | **4.67 ✓** |

`.kicker` is one of the four selectors that survives (it is only declared in `tokens.css`, which loads
first), and it did move to `#726C5D`. Everything else is unchanged, still `rgb(169,163,149)`.

A full walk of every visible text node on step 100 finds **248 failing elements**, the largest buckets
being 105 scope units at 2.51 and 82 scope row labels (`Time › Years`, 12.5 px) at 2.51. Two things
that were **not** in the first report and are failing now: the `remove step` control (2.38) and the
`+ bind a path` control (2.38) — the round's two new features, both drawn in the illegible ink.

Colour is still `rgb(169,163,149)` on `rgb(250,249,245)` / `rgb(244,242,236)` / `rgb(255,255,255)`.
Deleting the 23 later `color: var(--ash)` declarations would close this today.

### D18 — PARTIAL.

Fixed:

- **Accessible names on inputs.** 10 of 11 inputs on step 203 carry `aria-label`
  (`"Electrolyzer Nominal power value"`, `"Nominal power unit"`). `<label>` count is still 0, which
  no longer matters. The one input without a name is the scope search box.
- **`inputmode="decimal"`** on all 5 numeric cells.
- **Rail is one tab stop.** `#rail-list` exposes exactly one focusable element,
  `<li class="step" tabindex="0" role="button" aria-label="step 100, Time, ok">`. Reaching the rail
  from the top of the document takes **3 Tab presses** (was 33 to reach step 900).
- **The focus ring is designed.** Real keyboard focus gives `outline: solid 2px rgb(36,54,91)`
  (prussian) on rail steps and `solid 2px rgb(231,183,60)` (sodium) on masthead buttons, plus
  `box-shadow: rgba(36,54,91,0.12) 0 0 0 2px` and a prussian border on focused inputs. No Chrome blue.
- The `svg.cal-grid` and `svg.annual` figures now carry `role="img"` and substantive `aria-label`s.

Not fixed:

- **Every sparkline is still bare.** `svg.spark` × 15 on step 203 and × 28 on step 900:
  `role=null`, `aria-label=null`, no `<desc>`, no `<title>`. Plus one unclassed SVG on 203 with 35
  `<title>`s and no `role`.
- **95 `opacity:0` buttons are still in the tab order.**
- **Arrow-key traversal drops DOM focus** — see N5.
- The 18 `+ add a step` buttons are now `tabindex="-1"`, so adding a step is mouse-only — see N11.
- Amber now means four things: `required`, `UNDECLARED`'s successor state, `changed from baseline`,
  and *keyboard focus on a masthead button*.

### D19 — FIXED.

The four adjacent `POWER GENERATION` rows on step 202:

| row | notation now | shape |
|---|---|---|
| Available energy (daily) | `7.40 → 6.73 ×10¹³` | per-year dict, chronological |
| Available energy (hourly) | `7.40 → 6.73 ×10¹³` | per-year dict, chronological |
| PV hourly power generation | `7.40 → 6.73 ×10¹³` | per-year dict, chronological |
| **PV yearly power generation** | **`6.73 … 7.40 ×10¹³`** | plain array, extent |

Row 4 no longer disagrees with its own descending sparkline; it is now stated as an extent and the
sparkline is not asked to corroborate an ordering. The tracking rows read `0 … 909 Wh/m2` etc.

Residual: nothing in the app says what the distinction is. A text search of the rendered page for
*chronological*, *first → last*, *min … max*, *extent*, *year by year* returns zero hits, and none of
the `.q` elements carry a `title`. The reader now sees two consistent notations and still has to
infer which is which. The related complaint also stands: three of the four rows still print
byte-identical summaries.

### D20 — FIXED.

Minimum horizontal gap between a sparkline and its numeral is **8 px** (was 0). In the scope column
the order is `value | spark` with a 20–52 px gap and **46 px** of right padding, so the numeric
right-alignment holds. `—6.14 → 1.33` no longer reads as a negative.

### D21 — FIXED.

Step 400 now reads `WHAT THIS STEP NEEDS  7 to enter · 6 computed`, with sections
`TIME 1 computed`, `INFLATION 4 computed`, `NON-DEPRECIABLE CAPITAL COSTS 1 to enter · 1 computed`.
No section with content announces itself as empty. The header counts rows rather than "inputs"
(`9 tables · 13 rows`), so it no longer undercounts what is on screen, and `600 Labor Operating Cost`
reads `2 tables · 3 rows` — the `1 inputs` plural bug is gone.

Residual: `DIRECT CAPITAL COSTS - PV  1 to enter` sits above a single field that is filled (`818`)
and labelled `optional`. "To enter" now appears to mean "you author this", not "this is missing",
which is a different mislabel in the same place.

### D22 — FIXED.

`201 › Module tilt`: the input's `placeholder` is now `""` (was `required`), the field has no
`.waiting` class so no sodium-yellow fill, the meta line reads `angle  range 0 … 1.57  optional`, and
the unit box carries the standard `-` placeholder like every other dimensionless field. All three
halves of the contradiction are gone. **Shot:** `06-201-ranges.png`, field 01.

### D23 — PARTIAL.

Fixed: **`UNDECLARED` is gone** from step 400 (0 occurrences). Column keys are glossed in the grouped
scope view — `Cost Path`, `Cost Unit`, `Frequency Unit`, `Price Conversion Factor Unit`, `Usage Path`,
`Type` — inside a `<span class="col">`, so there is a separator. Exceptions are framed rather than
dumped: `THIS STEP RAISED KEYERROR` / `Table 'Solar Concentrator' is required but not found in
dcf.inp`, with the stray Python repr quote and the duplicated `[Plugin: X]` prefix both removed.
Markdown backticks in descriptions now render (`Path to a .csv file containing hourly irradiance data`).

Still on the user surface: `sum_all_tables`, `declared in special_insertions, never written`,
`absent`, `dcf.inp`, `on_demand`, `None`, `absolute_temperature`, `1/temperature_diff`,
`1/delta_degC`, `Test consumer`, and leaked path expressions as values. Plus N8: the gloss is missing
on one of the two code paths.

### D24 — PARTIAL.

Of 9 clipped elements on steps 201 and 400, **5 now carry a `title` with the full string** — the
scope column's values, including the units that used to be eaten (`7.40 → 6.73 ×10¹³ J 20y` with
`title="{Power Generation > PV hourly power generation > Value, J}"`). Real improvement.

Four are still bare: the four `{...}` path inputs on step 400, each clipped mid-token with an unclosed
brace and no `title` (`{Electrolyzer > Nominal power > Val`). They are `<input>`s so the text is
scroll-recoverable, but nothing indicates that. The `File` value on 201 is clipped from 617 px to
138 px with no title and no ellipsis.

### D25 — PARTIAL.

Fixed or improved:

- Requirements truncate from the **head**, preserving the discriminating tail:
  `…ble Capital Costs › Land required`, `…ntrator › Solar concentrator cost`.
- `+2 more` / `+5 more` overflow indicators.
- The dead space is gone: description column x 453 w 474, requirement column x 943 w 204, 16 px apart
  (was ~500 px of empty).
- A tiebreaker exists: after `1 of 6 ready`, ties order by requirement count (`0 of 3`, `0 of 10`,
  `0 of 20`).
- Already-present plugins carry a `plugin-row in-use` class.

Unchanged: no `title` on any truncated requirement, so the full path is still unrecoverable — and
`…tal Costs › Solar collection area` is now ambiguous between *Direct Capital Costs* and
*Non-Depreciable Capital Costs*. `Catalyst Separation`'s description is still cut to
**`Calculation of cost for catalyst separation (e.g.`** — no ellipsis, unclosed parenthesis, no title.
Still `1 of 6 ready` **and** `17%`. Still no search or filter in a 22-row scrolling list. Still no
legend for the category swatches.

### D26 — STILL BROKEN. Verbatim.

Add `Solar Concentrator` at 201.5:

``
6 INPUTS NOTHING SUPPLIES
  Solar Concentrator › Concentration factor      no plugin writes this — it is a value you supply
  Solar Concentrator › Cost                      no plugin writes this — it is a value you supply
  PEC Cells › Number                             written by PEC
  Land Area Requirement › South spacing          no plugin writes this — it is a value you supply
  Land Area Requirement › East/West spacing      no plugin writes this — it is a value you supply
  Non-Depreciable Capital Costs › Solar collection area
                     written by PEC  Photocatalytic  Photovoltaic  Solar_Concentrator
``

Two of six rows still contradict the heading. The step still lists **itself** as a writer of a value
it needs. The chips still mix display names with the raw class name `Solar_Concentrator`.
`Photovoltaic` is in this pathway half a position later and the panel still never says "move this
step after 202", though it has computed everything needed to.

### D27 — STILL BROKEN.

Toast measured live at `x 680, y 943, 241×33` in a 1000 px viewport, `background: rgb(22,23,26)`,
`opacity: 1`. `elementsFromPoint` through its three corners returns, behind it:

``
DIV.desc     :: Total solar collection area.
DIV.field computed :: 01 Solar collection area 637.2m2
DIV.cell-row :: Combined inflator 1
``

Opaque, bottom-anchored, covering persistent content in both the middle and right columns. The text
is still the aggregate delta only — `344.0475 → 230.3209 (-33.06%)` — with no indication of which
field caused it.

### D28 — FIXED.

Three studio tabs were open on the same server throughout this review (two belonging to other
agents). My session id `tmsgjocu9lc2koz` was stable across ~40 navigations, five pathway opens, a
workflow add/remove and three reloads, and my masthead never flipped. No `KeyError: 'X'` toast
appeared. The residue the first review flagged — raw Python exception text reaching the toast — is
improved but not gone (D23).

### D29 — itemised

| # | item | verdict |
|---|---|---|
| 1 | Rail gutter encodes no direction | **STILL BROKEN** — 4 of 35 edges light on hover, `marker-end` absent on all |
| 2 | Hover readout far from cursor | **IMPROVED** — 362 px below the hovered step (was 380–700), still a fixed footer |
| 3 | Hover readout lies about broken steps | **IMPROVED** — hovering `201.5 Solar Concentrator` still reports `0 values in from 0 steps · 0 values out to 0 steps`, now followed on the same line by `6 inputs unsupplied`; the contradiction is intact, the truth is just beside it |
| 4 | Gutter is texture at rest | **STILL BROKEN** — 35 paths, no single edge traceable |
| 5 | Rail dot does double duty, no legend | **STILL BROKEN** — `.step.error .dot` overrides `--fam`; no legend anywhere |
| 6 | Four steps with no description | **STILL BROKEN** — 201/301/302/400 have no description element; head-to-first-section gap is **32 px** on those against **66 px** on 203, so the rhythm still breaks by 34 px step to step |
| 7 | Computed chips vs editable right edges | **WORSE** — now **three** right edges: 470 (equation multipliers), 693 (value inputs), 864 (computed chips) |
| 8 | Redundant step chips | **IMPROVED** — 44 on step 400 (was 84 on the default view); still restate the group header |
| 9 | Adjacent groups differing only in plurality | **STILL BROKEN** — `DIRECT CAPITAL COST` / `DIRECT CAPITAL COSTS`, `INDIRECT CAPITAL COST` / `INDIRECT CAPITAL COSTS` |
| 10 | `20y` vs `×20` for one concept | **STILL BROKEN** — both present, neither explained |
| 11 | Inconsistent zero handling | **IMPROVED** — the decomposition now prints `~0%` rather than `-0.0%` |
| 12 | Family gloss wraps and orphans | **FIXED** — `Financing & tax debt service and what the state takes` renders inline |
| 13 | Salvage/Decommissioning tick colours | **STILL BROKEN** — `Salvage` fills 3.2 px in `rgb(116,166,72)` (`--hydrogen`), `Decommissioning` 3.2 px in `rgb(110,106,96)` (`--fam-scale`); both are `End of life` rows and neither uses the family colour, with no explanation |
| 14 | `USD/acre` beside `m2`, unreconciled | **STILL BROKEN** |
| 15 | `157 held · 2 arrive later` on the final step | **STILL BROKEN** — `155 values … · 2 arrive later` on 900 |
| 16 | Invariant breaks on failure | **STILL BROKEN** — `89 values … · 0 arrive later`, 89 ≠ 157 |
| 17 | Half the masthead is dead space | **IMPROVED** — spacer 598 px of 1600 (was 796); `LEVELIZED` is now 16 px against `RUN`'s 13 px |
| 18 | Amber means three things | **WORSE** — now four; the masthead focus ring is amber too |
| 19 | `-` unit box is an editable literal hyphen | **STILL BROKEN** — and now inconsistent: `Module tilt` has `value=""` with `placeholder="-"`, its siblings have a literal `value="-"` |
| 20 | Engine-internal insert positions exposed | **STILL BROKEN** — `add a step at 1`, `at 150`, `at 201.5`, `at 252.5`, `at 450.5` |

---

## New defects

### N1 — A `degC` field's declared range is inverted, negative, and 5 orders of magnitude out

`frame._display_factor` treats every unit conversion as multiplicative:
`one = engine.convert(1.0, base, unit_text)`. For an affine unit that returns the *converted value of
1*, not a ratio — `convert(1.0, 'K', 'degC') = -272.15`.

**Repro:** open `201 Hourly Irradiation`, read field 03. Value `45`, unit `degC`, meta line
`absolute_temperature   range -68 038 … -136 075`. Declared SI bounds are `[250, 500] K`.
Four occurrences on shipped files (`pv_e`, `pec`, `photocatalytic`, `pv_e_lcoe`), all this cell.
**Evidence:** `06-201-ranges.png`; `studio/scratch/cold2_bounds.py`.
**Fix:** convert both endpoints through the engine (`convert(low, base, unit)`), not by a factor;
or fall back to the SI bounds when `base != unit` and the conversion is not affine-free.

### N2 — The hourly calendar's ink ramp collapses to the floor on every per-year series

`figures.js:215` takes `peak = scaleMax || series.max`. `scaleMax` comes from
`candidates.map(c => c.max)`, and for a per-year dictionary the candidate's `max` is the maximum
**annual total**, not the maximum hour:

``
Available energy (hourly), year 0:  true hourly max 2.698e+10 J,  annual sum 7.404e+13 J
candidate.max reported to the client:               7.404e+13 J
``

`ink(2.698e10) = 0.22 + 0.78 × (2.698e10 / 7.404e13)^1.3 = 0.22003`, so the brightest hour of the
year and the dimmest both round to `0.220`.

**Repro:** `202 Photovoltaic` → any of the three series → every `<rect>` in `svg.cal-grid` is
`opacity="0.220"`; 4 315 cells, **1 distinct value**. The caption still reads "Ink is magnitude" and
the key still shows a dark→bright gradient swatch.
**Evidence:** `03-202-calendar-flat.png`.
**Fix:** scale by the maximum of the *drawn array*, and only share a scale across candidates whose
`unit` and per-year shape match.

### N3 — The calendar's scale key prints a joules magnitude with a `kWh/m2` unit

Same root cause. Step 202's candidates are `Irradiation Used › Data` (`kWh/m2`, max 0.9085) and two
`J` series (max 7.404e13). `Math.max` across them yields 7.404e13, which is then printed with the
*drawn series'* unit.

**Repro:** `202 Photovoltaic` → click `Data`. The key reads **`0 TO 7.40E+13 KWH/M2`**. The true
range of that array is 0 to 0.9085 kWh/m². A number that was never measured, in a unit it was never
measured in, on the figure's only quantitative label.

### N4 — After a bad keystroke, the field you broke becomes read-only

Every step whose status is `never reached` renders with its inputs suppressed.

**Repro:** `203 Electrolyzer` → set `Nominal power` to `lots` → Enter. 202 fails, 203 becomes
`never reached`. Now count inputs:

| step | status | fields | editable |
|---|---|---|---|
| 100 Time | ran | 4 | 4 |
| 201 Hourly Irradiation | ran | 7 | 7 |
| 202 Photovoltaic | failed | 5 | 4 |
| **203 Electrolyzer** | never reached | 7 | **0** |
| 400 Capital Cost | never reached | 13 | 4 |

`203 › Nominal power` renders `class="field bad computed"` with the value cell showing
`not computed — the run stopped earlier` and, 60 px below it,
`NOT A NUMBER — "lots" is not a number, and this field is declared float or int`. Two contradictory
statements about the same authored cell, and no input to correct it. The `NEVER REACHED` banner's
promise — *"Its fields are shown as written"* — is false: the written value is not shown.

**Evidence:** `07-203-readonly-trap.png`.
The only escape is the `SOURCE` drawer (which does work — I recovered `4.1943` that way), but nothing
in the field, the banner or the error points there. Before this round the field was editable and you
could just retype it.

### N5 — Arrow-key rail traversal advances one step, then dies, and loses focus doing it

`studio.js:217`: `if (next) { next.tabIndex = 0; next.focus(); openStep(next.dataset.name); }`.
`openStep` re-renders `#rail-list`, destroying the node that was just focused.

**Repro:** Tab three times from the top of the document to land on the rail (`outline: solid 2px
prussian` visible). Press ↓:

| after | `document.activeElement` | `li[tabindex="0"]` | `aria-current` |
|---|---|---|---|
| Tab ×3 | `LI.step ran` (100 Time) | 100 Time | 100 Time |
| ↓ #1 | **`BODY`** | 200 Inflation | 200 Inflation |
| ↓ #2 | `BODY` | 200 Inflation | 200 Inflation |
| ↓ #3 | `BODY` | 200 Inflation | 200 Inflation |
| ↓ #4 | `BODY` | 200 Inflation | 200 Inflation |

One press works, the focus ring vanishes, a screen reader is left on `<body>`, and every subsequent
arrow is dead because the handler lives on the `<li>` that no longer has focus. Walking the rail by
keyboard is now Tab-↓-Tab-↓, two keys per step, with no visible focus between them. The 33-tab
problem was replaced, not solved.
**Fix:** re-focus after the render, or move the handler to `#rail-list`.

### N6 — The equation row wraps at the reviewer's own viewport

Covered under D3. At a fresh 1600×1000 load `#needs` is 584 px and `.eq` is 474 px, so three of the
four CAPEX rows wrap; at 1440×900 and 1280×800 all four do. The break lands **after the `=`**, so the
result is orphaned on a second line at the left margin under the multiplier.
**Evidence:** `02-400-eqrows.png` (three rows, one frame), `09-400-eq-wrap-1600.png`,
`08-400-eq-wrap-1440.png`.

### N7 — Scope search silently caps at 40 results

| query | counter says | rows in the DOM |
|---|---|---|
| `Nominal` | 3 match | 3 |
| `inflation` | 10 match | 10 |
| `capital` | 35 match | 35 |
| `h` | **47 match** | **40** |
| `e` | **157 match** | **40** |

No "showing 40 of 157", no scroll-to-load, no visual cue — the list simply stops after
`Financial Input Values › Reference year`. The counter and the panel disagree, which is the same
class of problem the first review named as fatal: two numbers for one thing on one screen.

### N8 — Raw engine column keys leak in the search view only

The gloss that turns `Cost_Path` into `Cost Path` runs on the grouped scope render but not on the
filtered one.

**Repro:** `203 Electrolyzer`, type `replacement` in the scope search. Five rows read
`Planned Replacement › Electrolyzer stack replacement` **`Cost_Path`** / `Cost_Unit` / `Cost_Value` /
`Frequency_Unit` / `Frequency_Value`. Clear the search: the same five rows read `Cost Path`,
`Cost Unit`, `Cost Value`, `Frequency Unit`, `Frequency Value`. One fix, two code paths, one of them
missed.

### N9 — `1.5 × unresolved = 8 250 kW`

Step 202's `Nominal power` row now renders, on one line:

``
[ 1.5 ]  ×  [{Electrolyzer > Nominal power > Value, kW}]  unresolved  =  8 250 kW
``

The operand is labelled `unresolved` — honest about the forward reference, and better than the blank
the first review found. But the product beside it is resolved, so the row states an equation with an
unknown left-hand factor and a known result. A reader cannot check it, and it looks like a rendering
bug rather than a statement about run order. Either resolve the operand (the engine clearly can — the
product is 1.5 × 5 500) or say *why*: "read at 203, after this step".

### N10 — Three right edges for values, where there were two

The first review flagged computed chips right-aligning at 847 px and editable values at 778 px.
On step 400 there are now three: equation multipliers at **470**, ordinary value inputs at **693**,
computed chips at **864**. Vertical scanning across a worksheet is worse than before.

### N11 — `add a step` is now mouse-only

All 18 `+` buttons in the rail carry `tabindex="-1"`. Collapsing the rail to one tab stop was right,
but it took the insertion points out of the keyboard entirely rather than folding them into the arrow
model (e.g. ← / → on a focused step, or a dedicated key).

---

## What the round got right, and should not be undone

1. **`REMOVE STEP` + `SOURCE` + reload persistence.** Three separate promises kept, and together they
   turn the app from a one-way exploration into an actual tool. The remove is exact: add a failing
   step, remove it, and the cost returns to `4.1943` bit-for-bit.
2. **The annual chart.** Zero zero-height bars, 21 full-height per-year hit targets, a labelled
   `LIFETIME TOTALS` legend, and a caption that *admits the axis cannot show what the data does*
   rather than pretending. That last move is better design than a log scale would have been.
3. **The calendar's geometry.** 128 → 300 px, ±4 → 62.5 px seasonal swing, 365 dated tooltips, an
   honest `4 315 LIT HOURS OF 8 760`, a scale key, `role="img"`, and a solar-noon shift derived from
   the data rather than a timezone table with the amount printed on the figure. Everything about this
   is right except the one number the ink is divided by.
4. **`per kW` on the multiplier.** Derived from the reference instead of guessed. The most
   load-bearing table in the app is now dimensionally honest.
5. **`PUBLISHED` on the chooser costs, at full precision.** One word, and the provenance ambiguity
   that made two numbers look like the same number is gone.
6. **`→` for chronology, `…` for extent.** The right cut. It just needs one sentence somewhere.
7. **Head-truncation in the picker.** Keeping the discriminating tail is the correct trade.
8. **The failure cascade** is still the best thing in the app, and the new `THIS STEP RAISED
   TYPEERROR` framing improves it.

---

## Grades

### Thinking — B+ (was A−)

The underlying model is untouched and still excellent, so this grades the round's own thinking: the
diagnosis and design of 41 fixes. Much of it is very good. Somebody worked out that one hit target per
day carries the readout a reader actually wants at 1/24th the DOM; that a solar shift can be derived
from the data's own circular mean rather than a timezone table, and that the amount should be printed
so the axis stays auditable; that a chart spanning four orders of magnitude on a linear axis should
*say so in its caption* rather than fake a scale; that a per-year series and an array want different
notations; that the honest thing to print for a forward reference is `unresolved`.

Three points off for a specific and repeated failure: **several fixes were designed and never looked
at.** The contrast fix was written into a stylesheet that overrides it 23 times and shipped. The ink
ramp was tuned against a `peak` that is an annual total, so the "gamma 1.3" the comment reasons about
at length has no effect on any pixel. The bound converter assumed every unit is a ratio. The equation
was declared "one line now" at a width where it is two. Each of those would have been caught by
opening the page once with the same measurement that produced the original complaint. The round
answered the report rather than the app.

### Execution — C+ (was C)

Thirteen defects fully closed with evidence, one mostly closed, eleven partially, four untouched —
and eleven new. That
is net forward motion, and some of it is substantial: the app is now recoverable (remove, source,
reload), its search works, its flagship table's units are right, its chart's tooltips are reachable,
and its second-most-important figure finally shows the thing its caption promises.

It does not reach B because the two most-cited items in the first report are in worse shape than they
were. The contrast layer — called out as "one CSS variable away from fixed" and "the most
consequential single change in this list" — measures **identically to the decimal**, in the same
places, at the same sizes, and the round's own two new controls (`remove step`, `+ bind a path`) were
added into that same 2.38:1 ink. The hourly calendar went from a figure with a badly-ranged ramp to a
figure with **one distinct opacity value across 4 315 cells**, still captioned "Ink is magnitude"
under a gradient key. And a new trap means one mistyped character makes the offending field
read-only, which is exactly the kind of trust-destroying dead end D13 was about.

The numbers are better than they were and still not trustworthy: the headline shows `4.1943` in three
places and `4.194` in a fourth, on one screen; `1.11e+7` appears six times beside `4 312 000` and
`×10¹³`; `range -68 038 … -136 075` sits under a field reading `45`; a scale key reads
`0 TO 7.40E+13 KWH/M2`; a search counter says 157 above 40 rows. Every one of those is a case of the
app showing a reader two versions of one fact, which is the charge the first review brought and the
commit message quotes back. It has been reduced, not answered.

Delete the 23 stale `color: var(--ash)` declarations, take the calendar's peak from the drawn array,
convert bounds through the engine instead of by a factor, and stop suppressing inputs on skipped
steps, and this is a B — four changes, none of them structural, three of them one line.
