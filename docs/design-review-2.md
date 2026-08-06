# pyH2A "Paper Plant" — Cold Design Review, Round 2

**Reviewer:** ColdEye2 · **Date:** 2026-08-05 · **Build:** localhost:8721
**Viewport:** 1600×1000 @2× unless noted · **Session:** Home → Open "PV + Electrolysis" → navigated by sidebar only
**Audience assumed:** research scientists doing levelized-cost analysis, not developers

---

## Verdict up front

The restructure is a real improvement. The voice is consistent and confident (`not run yet — press Run to light the plant`, `where it goes`, `✓ matches readout`), the palette is warm and disciplined, the Run page cost ledger with a Σ integrity check and a reference-delta is genuinely excellent scientific UI, and the iterate loop (click node → edit field → Apply & run → signed delta) closes in under 400 ms.

**But the centerpiece does not carry its weight.** Asked directly — *is the custom flowsheet the best way to understand and operate this model?* — the honest answer today is **no, not yet**, for three reasons that are all fixable:

1. **It hides the money.** Clicking `fit` leaves **7 of 17 nodes entirely off-canvas** — and they are exactly the seven cost plugins (400 Capital Cost through 900 Discounted Cash Flow). On a levelized-cost tool, the default view of the plant excludes the entire economics half. Measured: after `fit`, `svg.clientHeight = 660`, content bottom = 1083 → **61% of the diagram visible**. `fit` fits the *width* only.
2. **Its unique information is the wiring, and the wiring is the least legible thing on screen.** Stream labels render at **7.11 effective CSS px**, truncated at ~30 characters (`Power Generation > Available ener…` appears three times identically for three different streams), unattached to their curves, and colliding with each other.
3. **A better plugin navigator already exists elsewhere in the app.** The `/Inputs` sidebar workflow list (screenshot `/tmp/r2-30-inputs.png`) shows all 17 plugins with execution order, indentation and keyboard access in ~450 px of column. Everything the flowsheet does *except* show wiring, that list does better. So the flowsheet must win on wiring or it is decoration with a large footprint.

Everything below is specific. Numbers are measured from the DOM or sampled from the PNGs, not eyeballed.

---

# Part 1 — Three user stories

## Story A — First contact: Home → Open → Plant → Run → find the money

**Screenshots:** `/tmp/r2-03-home-full.png` → `/tmp/r2-05-after-open.png` → `/tmp/r2-09-run-600.png` → `/tmp/r2-12-resultbar.png` → `/tmp/r2-13-run-page.png`

### What works
- Home is the strongest page in the app. Left-aligned editorial hierarchy, five reference pathways with real numbers, no card-grid slop. `Open` puts you on `/Plant` in 3.2 s with the session loaded. Zero friction.
- The Plant arrival state is confident: `not run yet — press Run to light the plant` tells you exactly what to do, and the right rail explains the metaphor in three sentences before you have to guess.
- The run pulse (`/tmp/r2-09-pulse-strip.png`) sweeps top-to-bottom over ~1.5 s. It teaches "execution order" viscerally and is the best delight moment in the product.
- Post-run, the black bar `4.1943 USD/kg [LCOH]` plus `where it goes — full breakdown ↗` is the correct next action, correctly worded, and the Run page section header repeats the phrase (`WHERE IT GOES — COST COMPOSITION`). Copy continuity is doing real navigational work.

### Friction, in the order the eye hits it

**A1. The eye lands on the diagram, and the diagram is a wall of hairlines.**
At default zoom the canvas is 784 × 660 for a diagram that is 1048 × ~1400 units. Measured effective type sizes:

| element | authored | effective on screen |
|---|---|---|
| node title (`Electrolyzer`) | 13 px | **9.73 px** |
| node index (`203`) / timing (`<1 ms`) | 10 px | **7.48 px** |
| I/O badge (`3⇥ 5⤇`) | 9.5 px | **7.11 px** |
| stream label | 9.5 px | **7.11 px** |
| bus-rail label (`Electrolyzer`) | 9 px | **6.73 px** |

Colour contrast is fine (`#55524A` on `#FAF7F0` = 7.29:1). This is purely a size failure. Nothing below ~10 px is readable; five of the six label classes are below 8 px.

**A2. Forty percent of the canvas is empty and the other sixty is congested.**
Node cards occupy x 100–279 of 1048 units. Streams bundle into x 620–850. The band x 850–1048 (≈40% of the canvas, ~300 px on screen) holds two floating labels and nothing else, while labels that *could* live there are truncated at 30 characters. See `/tmp/r2-08b-canvas.png` — `Technical Operating Parameters an…` floats twice in dead space, attached to no visible curve.

**A3. `fit` is a no-op that lies.**
Clicking `fit` returns `viewBox="-20 -20 1048 882.24"` — the same as the arrival state. Off-canvas after `fit`: `Capital_Cost_Plugin`, `Multiple_Modules_Plugin`, `Replacement_Plugin`, `Labor_Operating_Cost_Plugin`, `Other_Fixed_Operating_Cost_Plugin`, `Variable_Operating_Cost_Plugin`, `Discounted_Cash_Flow_Plugin`. There is no scrollbar, no fade, no "7 more below" cue. Node 302 is sliced by the legend bar with its bottom border missing (`/tmp/r2-37-bottomedge.png`) — the only hint that content continues, and it reads as a rendering bug rather than an affordance.

**A4. The header band has three different vertical centres.**
Measured at 1600: h1 `Plant` 112→201; black bar 119→165 (centre 142); Run button 145→185 (centre 165). Horizontally the black bar spans 800→1307, straddling the boundary between the canvas column (380–1164) and the panel column (1196–1520) — it is anchored to neither. `/tmp/r2-12-resultbar.png`.

**A5. The black result bar is 70% empty ink.**
507 px wide holding ~150 px of content. A black slab that large with that little in it reads as an error, not emphasis. It should either hug its content or earn the width (top-3 cost drivers inline, run timestamp, dollar-year basis).

**A6. The primary CTA is a text link styled exactly like body text.**
`where it goes — full breakdown ↗` computes to `color: rgb(38,37,31)`, `text-decoration: none`, 14 px — identical to the surrounding prose. The only affordance is the `↗` glyph, which conventionally means "opens in a new tab" and here means "goes to /Run". For the single action that answers the user's question, that is too quiet and slightly mislabelled.

**A7. No dollar-year basis anywhere near the number.**
`4.1943 USD/kg` on Plant, Run and Report. The basis (`Reference year 2016`, `Basis year 2016`) exists — buried inside `Capital Cost → Financial Input Values` on the Plant panel, four screens away. For this audience an LCOH without a $-year is not a citable number. The hero should read `4.19 USD(2016)/kg H₂`.

**A8. Precision is dishonest.** Home shows `4.19`; Plant and Run show `4.1943`; the ledger shows `+1.2915`. Five significant figures on a model whose inputs are given to two implies a resolution that does not exist, and the app contradicts itself between Home and Plant on the same quantity.

### Story A grade: **C+**
You get to the money in three clicks and the destination is excellent. But the flowsheet — the thing that fills the screen on arrival — is unreadable at default zoom and hides the cost model, so the first 20 seconds are spent squinting rather than orienting.

---

## Story B — Iterate: Electrolyzer → Nominal power 5,500 → 6000 → Apply & run → read the delta

**Screenshots:** `/tmp/r2-18-node-selected.png` → `/tmp/r2-18b-panel.png` → `/tmp/r2-21-focus2.png` → `/tmp/r2-22b-dirty.png` → `/tmp/r2-23-apply-4200.png` → `/tmp/r2-24-delta.png` → `/tmp/r2-27-restored.png`

### What works
- Click → panel swap is instant and correct: category chip (`CELL`) + `position 203`, plugin name at 28 px, the plugin docstring, then `INPUTS — EDIT AND RE-RUN` and a real editable table. This is the right information architecture.
- Field affordance is a clear round-1 win: bordered boxes, near-white fill, mono values, and a 2 px olive focus border with a soft halo (`/tmp/r2-21-focus2.png`). Unambiguous.
- `Apply & run ▸` is local to the panel, distinct from the global Run. Correct scoping.
- The delta readout `▲ +0.0681 vs previous` with a run-history sparkline is the right idea, and the history chart correctly excludes the failed run (three successful runs → up, then down).

### Friction

**B1. The UNIT column is 31 px wide and truncates every unit that matters.**
Measured: value input `width: 96px`, unit input `width: 31px`, both `13.6px` IBM Plex Mono, both editable. Actual values vs. rendered:

| field | unit value | renders as |
|---|---|---|
| Nominal power | `kW` | `k…` |
| Hydrogen yield per unit energy | `kg/kWh` | `k…` |
| Start-up time (Capital Cost) | `year` | `y…` |
| Plant life (Capital Cost) | `year` | `y…` |

In a techno-economic model the unit *is* the disambiguator. Truncating it to one character inside an editable field is the single worst-executed detail in the panel. The fix is free: the panel is 324 px wide, NAME is taking 130 px for text that already wraps, and VALUE is taking 96 px to hold `1`.

**B2. No dirty state, anywhere.**
With `Nominal power = 6000` typed and unapplied (`/tmp/r2-22b-dirty.png`): the field looks identical to untouched fields, `Apply & run` is unchanged, the black bar still reads `4.1943` with no stale marker, the sidebar `last run 4.1943 USD/kg` is unmarked. There is no "was 5,500", no per-field revert, no count of pending edits. After three edits across two nodes you have no way to know what you changed.

**B3. Number formatting is normalised on load but not on edit.**
The table loads `5,500` and `80,000`; after editing you have `6000` sitting next to `80,000`. Two conventions in a five-row table.

**B4. The flowsheet shows no evidence that anything changed.**
Apply & run recomputes the whole plant, and the diagram — the one surface whose job is to show how the model is wired — is completely inert. No highlight of the affected downstream path, no changed values, no dimming of unaffected branches. The only thing that changes on the canvas is the per-node millisecond timing, which jitters randomly (`Electrolyzer 6 ms → 4 ms`, `Hourly Irradiation 1 ms → 2 ms → 3 ms → 5 ms`) and means nothing.

**B5. The selection highlight is dropped on re-run.**
Before Apply: `class="node selected"` on `Electrolyzer_Plugin`. After Apply & run: no node carries `selected`; 16 nodes carry `node pulse`. The panel still shows Electrolyzer, so panel and canvas disagree about what is selected. You lose your place in the diagram every time you iterate.

**B6. The delta has no semantic colour.**
`▲ +0.0681 vs previous` and `▼ -0.0681 vs previous` both render `rgb(201,196,182)` at 12 px — identical. For a cost model, the sign of the change is the entire point of iterating; it should not depend on parsing a 12 px triangle. (`/tmp/r2-24-delta.png` vs `/tmp/r2-27-restored.png`.)

**B7. "vs previous" does not say what changed or what previous was.**
No `(was 4.1943)`, no `Electrolyzer > Nominal power 5,500 → 6,000`. On the third iteration this is guesswork.

**B8. No client-side validation; the error then blames the wrong node.**
I typed `abc` into `Electrolyzer > Nominal power` and pressed Apply & run (`/tmp/r2-26-invalid.png`). Result:
- The field accepted it. `aria-invalid` is absent; the input has no error styling.
- The banner reads: **"Photovoltaic failed: [Plugin: Photovoltaic_Plugin] can't multiply sequence by non-int of type 'float' — click the red node to fix its inputs."** The red node is **202 Photovoltaic**. The bad value is in **203 Electrolyzer**. Following the instruction takes you to a plugin where nothing is wrong.
- The raw Python `TypeError` string is shown verbatim to a scientist.
- The status line reverts to `not run yet — press Run to light the plant` — which is false; the plant has run twice successfully and just failed.
- The last good result (`4.2624`) is **destroyed**: the sidebar `last run` block disappears entirely. One typo wipes your working number.
- The "red" node is a pale pink fill on a node whose category colour is already orange — easy to miss among 17 cards, and it is not scrolled into view.

### Story B grade: **B−**
The loop mechanically works and is fast. It fails on the three things that make iteration *feel* controlled: knowing what you changed, knowing whether the change was good, and recovering from a mistake.

---

## Story C — Interrogate: chase "Replacement costs" from the ledger to its origin

**Screenshots:** `/tmp/r2-13-run-page.png` → `/tmp/r2-14-run-scroll1..3.png` → `/tmp/r2-15-filter-replacement.png` → `/tmp/r2-16-replacement-open.png`

### What works
- The ledger itself is the best-designed object in the app: eyebrow, huge mono number, `LCOH · run 12 ms · 17 plugins · 0 warnings`, `reference 4.1943 / Δ ±0.0000`, signed contributions sorted by magnitude, a Σ row with **`✓ matches readout`**. That integrity check is exactly the right instinct for this audience.
- `per-plugin timing` is correctly demoted to a collapsed disclosure here.
- The `filter tables and rows…` box searches row contents, not just table names — a genuine power feature.

### Friction

**C1. The trail dead-ends at step one.** The ledger row `Replacement costs` is a plain `<td>` with `cursor: auto`. No link, no hover, no drill-down. Nothing in the ledger connects a component to the plugin or table that produced it.

**C2. Thirty-five identical accordion rows with no hierarchy and no hints.**
The Results Explorer is a flat stack of ~35 full-width 40 px cards separated by 16 px gaps. No counts, no previews, no grouping, no input/output distinction, no relationship to the flowsheet's execution order. Everything looks equally important, which means nothing is findable by scanning.

**C3. Singular/plural table pairs are undifferentiated and unsurvivable.**
Present simultaneously in the same list, with no marker of which is an input and which is computed:
`Direct Capital Cost` / `Direct Capital Costs` · `Indirect Capital Cost` / `Indirect Capital Costs` · `Other Fixed Operating Cost` / `Other Fixed Operating Costs` · `Other Variable Operating Cost` / `Variable Operating Costs` · `Planned Replacement` / `Unplanned Replacement` / `Replacement`.
A scientist chasing "Replacement costs" is handed three plausible candidates and no way to choose.

**C4. Filtering works but does not explain itself.** Typing `replacement` surfaces `Workflow` and `Electrolyzer` alongside the three Replacement tables. Correct (they contain matching rows) but unlabelled — no `2 matching rows`, no highlight when expanded.

**C5. `FORMER FREQUENCY VALUE` / `FORMER COST VALUE`.** In the expanded `Planned Replacement` table these columns show `{Electrolyzer > Actual stack replacement time > Value, year}` and `0.4` next to a `COST VALUE` of `1 724 800 USD`. "Former" is pyH2A internals for "as written before the reference resolved". To a reader, `0.4` next to `1 724 800` looks like a contradiction. Either rename to `as written in file` or move behind a toggle.

**C6. The best provenance in the app is in column 7.** `COMMENT: Based on Chang 2020` is the citation a scientist actually wants. It is the seventh of nine columns in a 1085 px table.

**C7. Reference chips are inert, off-palette, and fail contrast.**
`{Replacement > Total > Value, USD}` renders as `<code>` at **10.32 px**, `color rgb(21,130,55)` on `background rgb(248,249,251)` — **4.21:1, below the 4.5:1 AA threshold**. `cursor: auto`, no `title`, no click handler. Meanwhile the Plant page promises *"click a stream to read the variables flowing and copy their references."* Nothing copies. Also `#F8F9FB` is a cool blue-grey — Streamlit's default code background leaking through a warm `#FAF7F0` page — and `#158237` is a second green that is not the app's olive `#4F7132`.

**C8. Two treatments of the same syntax on one screen.** In `Planned Replacement` the `{...}` references are plain table text; in `Replacement` immediately below they are green code chips.

**C9. The chase ends without closing the loop.** You arrive at `Replacement > Total = [21] 0 … 2 244 798.273 USD` and the ledger says `+0.2153 USD/kg`. Nothing bridges 2.24 M USD to 0.2153 USD/kg — the levelisation (discounting ÷ lifetime H₂) is invisible. `Contributions {3 entries}` is not expandable. The scientist has found the number but cannot verify the derivation, which is the whole reason they came.

**C10. Three orderings of one table.** Run page ledger: descending by magnitude. Report preview: file order (`Initial equity depreciable capital, Non depreciable capital, Replacement costs, Salvage…`). Report table also drops the SHARE column and the colour dots. Same data, three presentations.

### Story C grade: **C**
The destination data is rich and honest. The path there is unmarked, and the last mile — how a component total becomes a USD/kg contribution — is missing.

---

# Part 2 — The flowsheet, in detail

### Legibility at default zoom — **fails**
Covered in A1/A3. Summary: 5 of 6 text classes render below 8 px; 7 of 17 nodes are off-canvas after `fit`; 40% of the canvas is empty. The diagram becomes genuinely good at ~1.8× (see `/tmp/r2-21-field-focus.png`, captured mid-zoom) — cards breathe, labels are readable. The default is simply the wrong scale, and the container is the wrong shape: a 17-row vertical stack in a 784 × 660 frame.

### Stream labels — **the weakest component**
`/tmp/r2-06b-streams.png`, `/tmp/r2-08b-canvas.png`
- Truncated at ~30 chars, cutting exactly where the information is. `Power Generation > Available ener…` appears three times for three different streams.
- Two label modes with no visual distinction: `Source > Variable` and bare `5 variables` / `2 variables`. The latter is uninformative.
- No leader lines. Labels float near a bundle of 6 near-parallel curves with no way to tell which belongs to which.
- Hard collisions. At the `500 Replacement` row, `Fixed Operating Costs > Custom…` and `2 variables Staff` overprint into unreadable glyph soup.
- Labels overprint arrowheads (`Reverse Osmosis > Capacity` sits directly on node 302's inbound arrow).
- At 1280 px they are hard-clipped with no ellipsis (`Non-Depreciable Capital C`) — the SVG **crops rather than scales** (`viewBox` width 1048 → 747 while scale stays 0.748), silently hiding the right half of the wiring with no indicator.

### Node cards — **good object, wrong payload**
`/tmp/r2-06a-nodes.png`
- Structure is right: 4 px category rail, small mono index, bold title, right-aligned metadata. No shadow, 1 px border, tight radius. Clean.
- Titles fit comfortably (widest, `Other Fixed Operating Cost`, is 127 px in a 179 px card).
- **The category colour is unexplained.** Five colours (navy / orange / green / teal / purple / brown) encoding `CLOCK / SUN / CELL / LEDGER / SCALE`, discoverable only by hovering 17 nodes one at a time. The legend explains line styles and says nothing about colour.
- **The categories are invented metaphors that mislead.** `Discounted Cash Flow` is filed under **CLOCK** with Time and Inflation. DCF is the economics core, not a time table. `SCALE` for Multiple Modules is opaque. `CELL` for Electrolyzer collides with the bus rail also named "Electrolyzer".
- **The badge `3⇥ 5⤇` is undecodable.** ⇥ (rightwards arrow to bar) is used to mean *inbound*, and it points right. 7.11 px. The hover card decodes it as `user input tables 3 / outputs 5` — so the badge and the hover card are redundant with each other, and neither tells you anything about the model.
- **After a run, the one number on each card is `<1 ms`** — repeated on 13 of 17 cards, jittering between runs. This is developer telemetry on a science instrument, occupying the most valuable real estate in the diagram. The Run page correctly hides timing behind a disclosure; the Plant page makes it the headline. Replace with the node's headline output (`5,500 kW`, `$1.72 M`, `+0.2153 USD/kg`) or its share of LCOH.

### Hover cards — **well-made, wrong content, wrong z-order**
`/tmp/r2-10b-hover.png`, `/tmp/r2-11b.png`
- Node hover reads `CELL · POSITION 203` — **the node's own name is absent**. You must already know what you are hovering. Then `user input tables 3 / outputs 5 / click to edit inputs & see outputs`, which restates the badge.
- The card is anchored below-right and covers the next node down (hovering 203 hides 204 Battery entirely) and the adjacent stream label. No pointer/tail to its source.
- Stream hover is better — `REVERSE OSMOSIS → POWER MANAGEMENT` is exactly right — but the column widths are inverted: the long label (`Power Consumption > Reverse osmosis consumption (yearly)`) is squeezed into ~140 px and wraps to six lines, while the value gets ~640 px on one line.
- **The value is a raw float dump:** `array[20] J (71 368 551 439.876 … 82 834 069 733.609)`. Twelve significant figures, in joules, for annual electricity consumption. It should read `71.4 – 82.8 GJ/yr` or `19.8 – 23.0 GWh/yr`.
- **The legend bar paints over the hover card**, hiding the footer (`click to inspect & copy references` renders as `…inspect & copy references`).

### Bus rails — **under-built**
Three rails: `Time`, `Inflation`, `Electrolyzer`, labelled at 9 px (6.73 px effective).
- The `Electrolyzer` label spans x 62–117 while node cards begin at x 100 — a **17 px overlap**, which is why it renders clipped as `ELECTROL`.
- Labels appear only at the rail's top. Pan down to the cost plugins and the rails become three unlabelled grey hairlines at ~1.1:1 contrast.
- A bus rail named `Electrolyzer` sits eight rows above a node named `Electrolyzer`. Same word, two different objects, no distinction.
- Rails are not interactive — no hover, no click, no highlight of consumers — despite being one third of the legend.

### Run pulse — **the best delight moment, slightly dishonest**
`/tmp/r2-09-pulse-strip.png`. A top-to-bottom wave over ~1.5 s. It teaches execution order better than any label could. Two notes: the highlight is a flat neutral grey that reads as "disabled" rather than "executing" (an olive tint matching the Run button would read as live); and every node's timing is revealed at t=250 ms while the wave is still sweeping, so the animation and the data tell different stories. The honest number is `run 12 ms`.

### Pan / zoom feel — **competent, one trap**
- `cursor: grab` on the canvas, drag-to-pan works smoothly, wheel-zoom is cursor-anchored (correct), `+`/`−` zoom about the viewport centre.
- **Scroll trap.** The wheel over the canvas zooms and consumes the event; the page does not scroll (verified: `.stMain.scrollTop` stays 0 with the cursor inside the frame, moves 300 outside it). The canvas is 784 × 664 in the middle-left of a 1670 px-tall page. Scrolling down to read COMPUTES with the cursor in the middle of the window silently zooms the diagram instead. Gate zoom behind ⌘/Ctrl+wheel, or click-to-activate.
- Zoom is slow: one notch = 11%, so ~7 notches to double.
- Pan/zoom state is not preserved across reruns.

### Selection affordance — **too quiet, and it doesn't survive**
- Selected node gets `class="node selected"`: a slightly heavier border and lighter fill. At 9.7 px type in a stack of 17 near-identical cards, that is hard to spot.
- The selection is **not** reflected after Apply & run (see B5).
- Selecting a node does not reveal it. I selected `Capital_Cost_Plugin` and the panel filled in correctly while the canvas showed nothing — node 400 is below the fold (`/tmp/r2-28-capcost.png`). The canvas should pan the selected node into view.

### Accessibility — **the flowsheet is entirely inaccessible**
`<svg>`: no `role`, no `aria-label`, no `tabindex`. `.node`: no `role`, no `tabindex`, no `aria-label`. `.stream`: same.
The Plant page has **10 focusable elements total** — sidebar collapse, 6 nav links, one stray `<section>`, the breakdown link, and Run. **None of the 17 nodes or 25 streams is reachable by keyboard or announced to a screen reader.** The page's primary interaction is mouse-only.

---

# Part 3 — Density & delight: does it inform or decorate?

| device | verdict | why |
|---|---|---|
| **Value + unit packages** (`4.1943 USD/kg`, `+0.2153`) | **Informs** | Mono numerals, unit in smaller muted type, aligned columns. Correct. Undermined by 5-sig-fig precision and the missing $-year. |
| **`LCOH` chip** | **Decorates, and lies** | Bordered, padded, rounded — looks like a filter/toggle. Inert. False affordance. |
| **Cost-composition sparklines** (`/tmp/r2-16-replacement-open.png`) | **Informs, genuinely** | The `Replacement > Total` spark — flat with one spike — tells you instantly that this is a single 10-year event. Best data-ink in the app. But: 64 × 15 px, no `role`, no `aria-label`, no `title`, and 21 points at 3 px each. |
| **Run-history sparkline in the black bar** | **Half** | Correctly excludes the failed run. But it is teal — a colour that means "Battery/Power Management" on the flowsheet — unlabelled, unaxised, and meaningless at 2 points. |
| **Share bars in the ledger** | **Redundant** | Share is encoded three times per row: colour dot, mini bar, percentage — plus a fourth time in the full-width stacked band above the table. Two of the four are enough. |
| **Ledger colour dots** | **Decorates** | 11 hues with no relationship to the flowsheet's node colours. On Plant, everything cost-related is purple; here `Replacement costs` is steel-blue and `Initial equity depreciable capital` is purple. Chasing a component across pages gets no colour continuity. |
| **Per-plugin timing table (Run page)** | **Informs, correctly demoted** | Collapsed disclosure labelled `per-plugin timing · slowest Electrolyzer 6 ms`. Exactly right. |
| **Per-node timing on the flowsheet** | **Decorates, expensively** | `<1 ms` on 13/17 nodes, jittering per run, occupying the only numeric slot on each card. Directly contradicts the Run page's own judgement about how important timing is. |
| **`Δ ±0.0000` vs reference** | **Informs** | Validating against the published pyH2A value is the most trust-building element in the product. Only gaps: "reference" is unexplained, and `±0.0000` should read `exact` or `0.0000`. |
| **`✓ matches readout` Σ row** | **Informs** | Keep. Do more of this. |

---

# Part 4 — Regression check on round-1 fixes

| area | status | evidence |
|---|---|---|
| **Field affordances** | ✅ **Fixed** | Bordered inputs, near-white fill, mono values, 2 px olive focus border + halo. Unambiguous. `/tmp/r2-21-focus2.png` |
| **Fonts loading** | ⚠️ **Mostly** | `Source Sans` and `IBM Plex Mono` load and render. But **12 `@font-face` declarations for `Source Serif 4` (600/700) are `unloaded` and the family is used by zero elements** — dead weight, or a display serif that was specced and never wired up. Also `body { font-family }` resolves to a doubled stack: `"Source Sans", sans-serif, "Source Sans", sans-serif`. |
| **Contrast** | ❌ **Regressed — critical** | See below. |
| **Chrome hiding** | ⚠️ **Partial** | `stAppDeployButton` and `stMainMenu` are `display:none` ✅. But `stHeader` / `stToolbar` still render at `display:flex, height:60px` — an empty 60 px band that pushes every page down and is never used. The sidebar-collapse `»` is hover-revealed at 60% ink — nicely done. |
| **Spacing rhythm** | ⚠️ **Mixed** | Home and the Run page hero have real rhythm. The Plant header band does not (three vertical centres, 16 px gutters between a 44 px headline, a black slab and a button — see A4). The Results Explorer's uniform 40 px rows + 16 px gaps produce monotony, not rhythm. Source page: primary `Apply` (58 px) is smaller than secondary `Download .md` (110 px), separated by a 123 px gap — hierarchy inverted and not grouped. |

### The contrast regression — every primary button in the app

Computed style on `button[data-testid="stBaseButton-primary"]` is `color: rgb(255,255,255)`. But the innermost `<p>` inside `[data-testid="stMarkdownContainer"]` resets to `rgb(38,37,31)`. Pixel-sampled from the PNGs: the fill is `#56703A` and the dominant text colour is `#262520` (14 452 px of fill vs 571 px of near-black glyph vs 236 px of white antialiasing).

**`#262520` on `#56703A` = 2.76:1.** WCAG AA requires 4.5:1 at 16 px.

This affects `Run ▸` (Plant), `Run again ▸` (Run), `Apply & run ▸` (panel), `Apply` (Source) — every primary action in the product. `/tmp/r2-19-applybtn.png`, `/tmp/r2-19b-runbtn.png`.

Fix: `button[data-testid="stBaseButton-primary"] [data-testid="stMarkdownContainer"] p { color: inherit; }`

Second contrast failure: reference/unit code chips, `#158237` on `#F8F9FB` at 10.32 px = **4.21:1**.

---

# Part 5 — Still confusing, mislabelled, or dead-ended for a scientist

1. **`CLOCK / SUN / CELL / LEDGER / SCALE`** — invented metaphors replacing domain vocabulary, and one is wrong (DCF is not a clock). Discoverable only by hovering each node.
2. **`FORMER COST VALUE = 0.4` next to `COST VALUE = 1 724 800 USD`** — reads as a contradiction.
3. **`17 plugins · functional unit  kg`** (sidebar) — a dangling label with a floating chip. Missing both a separator and the substance: `functional unit: 1 kg H₂`.
4. **`Power Generation > Available energy (hourly) = 0 J`** in the COMPUTES table — zero available energy from a solar plant looks like a model failure. Unexplained.
5. **`Electrolyzer > Yearly operation data`** — blank value cell. Reads as broken rather than "not a scalar".
6. **`array[20] J (71 368 551 439.876 … 82 834 069 733.609)`** — raw float dump where engineering notation belongs.
7. **Error blames the wrong plugin** and instructs you to fix inputs that are correct (B8).
8. **`not run yet — press Run to light the plant`** shown after two successful runs and one failure.
9. **`Δ ±0.0000` / `reference 4.1943`** — reference to what? The published pyH2A value? Say so.
10. **`Workflow` table DESCRIPTION column is empty for 8 of 17 plugins** on `/Inputs`, while the Plant panel has a docstring for the same plugins (`Simulation of hydrogen production using electrolysis.`). The data exists; the table doesn't use it.
11. **`/Inputs` sidebar indentation implies a hierarchy that doesn't exist** — 201 Hourly Irradiation is nested under 200 Inflation purely by numeric range. Hourly Irradiation is not a child of Inflation.
12. **Report page: three identical outline buttons, no primary.** Which artifact does a scientist normally want?
13. **Source page**: a plain `<textarea>` for "the single source of truth" — no line numbers, no syntax highlighting, no find, fixed height on a long file.
14. **Responsive floor is ~1400 px.** At 1100 the black bar and the Run button overlap (`/tmp/r2-34-plant-1100.png`). At 1280 the canvas crops rather than scales and stream labels are hard-cut. On window resize the component does not re-fit until the next Streamlit rerun, so it transiently paints over the side panel. The 300 px sidebar never collapses.
15. **COMPUTES table overflows the viewport with no scrollbar.** Measured: table `x=1196, right=1610, width=414`, parent `width=324`, `overflow-x: visible`, viewport 1600. **90 px hangs off the right edge and is unreachable** — the `LAST RUN` header and every unit chip are sliced. `/tmp/r2-20-computes.png`

---

# Top 10 fixes, prioritised

### 1 — Fix `fit` so it fits, and give the canvas the height it needs
`fit` currently returns `viewBox="-20 -20 1048 882"` for content spanning ~1400 units, hiding all seven cost plugins. Compute the bounding box of *all* nodes plus a 24-unit margin and set both dimensions. Simultaneously raise the Streamlit component height from 664 → ~900 px so the fitted diagram lands at a usable scale (target: node title ≥ 12 effective px). If 17 rows genuinely will not fit, add a persistent bottom fade plus a `7 more below ↓` affordance, and never let a node card be sliced by the legend.
*Files: flowsheet component `fitView()`, `st.components.v1.html(height=...)`.*

### 2 — Repair primary-button contrast (2.76:1 → 5.6:1)
``css
button[data-testid="stBaseButton-primary"] [data-testid="stMarkdownContainer"] p { color: inherit; }
``
Also lift the reference-chip green: `code { color: #0F5F28; background: #F4F1EA; }` (warm ground, ≥4.5:1 at 10.3 px) — and raise those chips from 10.32 px to 12 px.

### 3 — Give the UNIT column room; stop truncating units
In the node panel, reallocate the 324 px: `NAME 44% / VALUE 30% / UNIT 26%` (≈ 84 px for units, enough for `kg/kWh`). Better: widen the panel itself to ~420 px by shrinking the canvas column — the canvas has ~300 px of empty right-hand space it is not using. And fix the COMPUTES overflow with `table { table-layout: fixed; width: 100% } td { overflow-wrap: anywhere }` — 90 px of that table is currently unreachable.

### 4 — Replace `<1 ms` on node cards with the node's headline number
Per-node latency is developer telemetry that jitters between runs; the Run page already treats it as secondary. Put the plugin's principal output there instead — `5,500 kW`, `$1.72 M`, `+0.2153 USD/kg (5.1%)`. If a share-of-LCOH is available per plugin, use it: the flowsheet then answers "where does the money go" *spatially*, which is the one thing no other page does. Move timing behind the same disclosure pattern the Run page uses.

### 5 — Make stream labels legible: size, attachment, no truncation
- Raise from 9.5 → 13 SVG px (≈ 9.7 effective at current scale; ≈ 13 after fix #1).
- Drop the 30-char truncation and use the empty right-hand third of the canvas; wrap to two lines rather than eliding the variable name.
- Add a 1 px leader from label to curve, or place the label on the curve with a `paint-order: stroke` halo in the page background colour.
- Collision-resolve vertically (simple greedy nudge) so `Fixed Operating Costs > …` and `2 variables Staff` stop overprinting.
- Replace bare `N variables` with `N variables ›` and make it open the stream card.

### 6 — Make the ledger clickable and close the levelisation gap
Turn each `COMPONENT` cell into a link to its source table in the Results Explorer (auto-expand + scroll + highlight the matching row). In the expanded table, show the arithmetic that gets from `Replacement > Total = 2.24 M USD` to `+0.2153 USD/kg` — even one line (`÷ 10.4 M kg H₂ lifetime, discounted @ 8%`) closes the loop that Story C currently leaves open.

### 7 — Validate inputs client-side and blame the right node
On blur/Apply, reject non-numeric values in numeric fields: red border, `aria-invalid="true"`, inline `must be a number`, and disable `Apply & run`. When the engine does fail, resolve the failing *reference* back to the *field the user edited* and name that field in the banner — never send the user to a plugin they did not touch. Preserve `last run 4.2624` in the sidebar as `last good run` instead of deleting it, and replace `not run yet` with `last run failed — fix the input above`.

### 8 — Add a dirty state and semantic delta colour
- Mark edited fields (2 px left accent + `was 5,500` in 11 px muted below the input) and add a per-field revert.
- When any field is dirty, mark the black bar stale (`4.1943 — stale, 1 pending edit`) and give `Apply & run` a subtle pulse.
- Colour the delta: `▲ +0.0681` in a warm rust (`#9A4B2F`), `▼ −0.0681` in the olive (`#4F7132`). Currently both are `#C9C4B6`.
- Append the change that caused it: `▲ +0.0681 vs 4.1943 · Electrolyzer > Nominal power 5,500 → 6,000`.

### 9 — Explain the colour taxonomy, name the node in its hover card, and keep the selection
- Add a one-line colour key to the legend row (`■ framework ■ solar ■ conversion ■ storage ■ cost`) using domain words, not `CLOCK / SUN / CELL / LEDGER / SCALE` — and re-file `Discounted Cash Flow` out of `CLOCK`.
- Node hover card headline should be **`Electrolyzer`**, with `CELL · position 203` as the sub-line.
- Raise the hover card above the legend bar (`z-index`) and flip it above the cursor when it would cover the next node.
- Keep `class="node selected"` across reruns, strengthen it (2 px border + 8% category-tinted fill), and pan the selected node into view.
- Add `role="button"`, `tabindex="0"`, `aria-label="203 Electrolyzer, 3 input tables, 5 outputs"` to `.node`, and arrow-key traversal on the `<svg>`. Right now zero of 17 nodes is keyboard-reachable.

### 10 — Header band, precision, and the $-year
- Align the Plant header band on one baseline: h1, black bar and Run all centred on the same axis; shrink the black bar to hug its content (or fill it with the top-3 drivers); pull `where it goes — full breakdown` **inside** the bar as a right-aligned link, drop the `↗`, and give it an underline on hover so it stops reading as a caption.
- Standardise LCOH precision at 3 significant figures everywhere (`4.19`), keeping 4 dp only inside the ledger where the Σ has to reconcile.
- Put the basis on the headline: **`4.19 USD(2016)/kg H₂`**. Fix the sidebar to read `functional unit: 1 kg H₂`.
- Gate wheel-zoom behind ⌘/Ctrl (the canvas is currently a 784 × 664 scroll trap in the middle of a 1670 px page), and reclaim the empty 60 px `stHeader` band.

---

## Screenshot index

| path | what |
|---|---|
| `/tmp/r2-03-home-full.png` | Home |
| `/tmp/r2-05-after-open.png` | Plant, arrival state (pre-run) |
| `/tmp/r2-06a-nodes.png` | Node cards, 2× crop |
| `/tmp/r2-06b-streams.png` | Stream labels, 2× crop |
| `/tmp/r2-06c-legend.png` | Legend slicing node 302 |
| `/tmp/r2-08b-canvas.png` | Cost half of the plant (after panning) |
| `/tmp/r2-09-pulse-strip.png` | Run pulse, t = 250/600/1100/1800/2800 ms |
| `/tmp/r2-09-run-600.png` | Plant, post-run |
| `/tmp/r2-10b-hover.png` | Node hover card (`CELL · POSITION 203`) |
| `/tmp/r2-11b.png` | Stream hover card + legend painting over it |
| `/tmp/r2-12-resultbar.png` | Black result bar, header band |
| `/tmp/r2-12b-sidebarrun.png` | Sidebar run summary |
| `/tmp/r2-13-run-page.png` | Run page hero + cost ledger |
| `/tmp/r2-14-run-scroll1.png` … `3.png` | Results Explorer, 35 accordions |
| `/tmp/r2-15-filter-replacement.png` | Filter = "replacement" |
| `/tmp/r2-16-replacement-open.png` | Planned Replacement + Replacement tables |
| `/tmp/r2-18-node-selected.png` | Electrolyzer selected, side panel |
| `/tmp/r2-18b-panel.png` | Panel 2× crop — truncated units |
| `/tmp/r2-19-applybtn.png`, `/tmp/r2-19b-runbtn.png` | Button contrast, 2.76:1 |
| `/tmp/r2-20-computes.png` | COMPUTES table overflowing the viewport |
| `/tmp/r2-21-focus2.png` | Input focus ring |
| `/tmp/r2-22b-dirty.png` | Edited field, no dirty state |
| `/tmp/r2-23-apply-4200.png` | After Apply & run |
| `/tmp/r2-24-delta.png` | `▲ +0.0681 vs previous` |
| `/tmp/r2-26-invalid.png` | Error state, wrong node blamed |
| `/tmp/r2-27-restored.png` | `▼ −0.0681`, same grey |
| `/tmp/r2-28-capcost.png` | Capital Cost selected, node off-canvas |
| `/tmp/r2-30-inputs.png` | Inputs page — the better plugin navigator |
| `/tmp/r2-31-source.png` | Source page |
| `/tmp/r2-32-report.png` | Report page |
| `/tmp/r2-35-1280-settled.png` | Plant at 1280 — crops, doesn't scale |
| `/tmp/r2-34-plant-1100.png` | Plant at 1100 — bar/button overlap |
| `/tmp/r2-36-plant-canonical.png`, `/tmp/r2-37-bottomedge.png` | Node 302 sliced by the legend |
