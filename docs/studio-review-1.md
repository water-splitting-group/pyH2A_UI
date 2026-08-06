# Paper Plant Studio — cold design review

Reviewer: ColdDesign. First contact, no prior exposure, no source read.
Target: `http://127.0.0.1:8730`, viewport 1600×1000 @2×, PV + Electrolysis default.
Evidence: 82 captures in `notes/shots-cold/`. A shared-session bug (D28) was fixed by another
agent partway through this review. Captures numbered `07*` and later were taken after that fix;
captures `01*`–`05*` predate it and record static rendering of the PV + Electrolysis step frames,
which the bug did not touch. Two artefacts I *did* see before the fix — a horizontal overflow on
field focus, and a raw `KeyError: 'Electrolyzer'` toast — could not be reproduced afterwards and
are **not** reported as defects here; only the raw-exception-text problem survives, as part of D23.

---

## Verdict

**What it is.** A worksheet for a levelized-cost engine. Three columns: a workflow rail on the
left, one open step in the middle, everything the engine knows at that moment on the right.
I understood that in under ten seconds without being told, which is the highest compliment
I can pay a dense technical UI. The framing — *what this step needs / what this step made /
what is available here* — is the right frame. It is not a dashboard pretending to be a tool;
it is a tool.

**Does it work.** Yes, mechanically. All 17 steps open. Edits re-run the engine in ~10 ms and
propagate visibly. Breaking a field produces a genuinely well-designed failure cascade. Adding
a plugin that cannot run produces the single best panel in the app. Five pathways open, and the
electricity pathway swaps its functional unit from kg to kWh with **zero** leakage — I scanned
all 12 steps, both columns, every `title` attribute and every SVG tooltip, and found not one
occurrence of `hydrogen`, `H2`, `kg`, or `/kg`. That is real discipline.

**What it feels like.** Like reading someone's very good lab notebook through a dirty window.
The thinking is unusually sharp and the surface is unusually careless, and the gap between
them is the whole story of this review. The typography is confident and the layout has real
rhythm. But the app repeatedly shows me *the same number twice, differently*, in one viewport:
a field saying `-0.4%` above a panel saying `-0.004`; a headline cost at `4.1943`, `4.194` and
`4.1943` in three places on one screen; a chooser saying `0.0286` while the masthead says
`0.02858` for the same pathway. Each is small. Together they teach me not to trust the numbers,
which is fatal for a tool whose only product is numbers.

Two things I want to be blunt about. First, the entire secondary text layer — every field
description, every physical dimension, every declared range, every unit in the right column,
every section count, every rail step number, and the global run-health footer — is rendered at
**2.24–2.51:1 contrast at 9.5–12 px**. That is roughly half the WCAG AA minimum, applied
systematically to precisely the text a newcomer needs. Second, there is an entire second
interaction model in this app — "binding" a field to an upstream value, with 95 hidden `USE`
buttons — that is **completely undiscoverable**, armed by pressing Enter, and I found it only
by accident. A feature nobody can find is not a feature.

**Thinking: A−. Execution: C.** Graded separately below.

---

## Defects

Ordered by how much damage each does. Repro assumes a fresh load of `http://127.0.0.1:8730`
at 1600×1000. Screenshot paths are relative to `notes/shots-cold/`.

### D1 — The same number is shown twice, 100× apart, in one viewport

Percent-formatted fields are rendered as percent, but their declared range and the dark
"what this step made" panel below them are rendered as fractions. Both are on screen together.

- Step **201**, field 06 `Temperature coefficient`: field reads `-0.4%`; the meta line directly
  under it reads `range -0.5 … 0.5`; the panel 700 px below reads `-0.004 1/delta_degC`.
- Step **203**, field 03 `Minimum capacity`: `10%` / `range 0 … 1` / panel `0.1`.
- Step **203**, field 02 `Power requirement increase per year`: `0.3%` / panel `0.003`.
- Step **100**, field `Capital spent in 1st year of construction`: `100%` / `range 0 … 1`.
- Step **202**, `Efficiency`: `22%` / `range 0 … 1`. `Power loss per year`: `0.5%` / `range 0 … 1`.

**Repro:** click `201 Hourly Irradiation`; read field 06 and its meta line; scroll to the dark
panel. **Shots:** `15-201-calendar.png` (field and `-0.004` in one frame), `02e-201-tempco.png`,
`04-203-top.png`, `04-203-mid.png`.

The range annotation is the app's promise that it will tell you the legal bounds of a field.
As shipped, six fields display a value *outside* their own stated range. A user who trusts the
annotation and types `0.5` into `Temperature coefficient` will get 0.005. Fix by rendering the
range in the field's display unit (`-50% … 50%`), or by dropping percent display entirely.

### D2 — Equation rows label the multiplier with the product's unit

The app's flagship row type is `<price> × {upstream path} = <product>`. The unit chip beside
the editable number states the unit of the **result**, not of the number in the box.

- Step **202**, `Nominal power`: field `1.5`, chip `kW`, product `= 8 250 kW`. 1.5 is a
  dimensionless multiplier of the electrolyzer's 5 500 kW. `1.5 kW` is simply wrong.
- Step **400**, all four CAPEX rows: `Electrolyzer CAPEX 784 [USD]` × `5 500 kW`
  `= 4 312 000 USD`. 784 is USD **per kW**. Same for `PV CAPEX 818 [USD]`,
  `Reverse osmosis CAPEX 6000 [USD]` (USD per m³/h), `Battery CAPEX 0. [USD]`.
- Also non-equation: step **800** scope shows `Electrolyzer OPEX (fraction of CAPEX) 0.02 USD`
  and `PV OPEX (fraction of CAPEX) 0.02 USD` — a declared *fraction* labelled USD.

**Repro:** open `400 Capital Cost`, scroll to `DIRECT CAPITAL COSTS - ELECTROLYZER`.
**Shots:** `19b-eqrow-pve.png`, `05-400-900.png`.

An engineer checks units first. Every unit-bearing number in the most load-bearing table in
the app is mislabelled by the plant's own scale factor.

### D3 — The equation rows do not read as equations

Rendered layout of step 202's `Nominal power`:

``
01  Nominal power ···········  [    1.5 ]  [kW]
    Nominal power of PV array.
    power   range ≥ 0
    ×   [{Electrolyzer > Nominal power > Value, kW}]              = 8 250 kW
``

Three failures at once. (a) The left operand `1.5` sits on line 1; the `×` sits on line 4, with
two lines of prose between them — the multiplication sign has no visible left operand. (b) The
`×` is the smallest, palest glyph on the row. (c) On step 202 the **resolved multiplicand is
absent**: the row is `× {path} = 8 250 kW`, with nothing between `×` and `=`. On step 400 the
same row type *does* show it: `× {path} 5.815 m3/h = 34 893 USD`. Same widget, two structures.

**Repro:** `202 Photovoltaic`, first field of `PHOTOVOLTAIC` — note `× … = 8 250kW`. Then
`400 Capital Cost`, `DIRECT CAPITAL COSTS - REVERSE OSMOSIS` — note `× … 5.815m3/h = 34 893USD`.
**Shots:** `19b-eqrow-pve.png`, `05-400-900.png`.

The idea is excellent and I want it kept. Put all three quantities on one line with the operator
between them, at readable weight.

### D4 — An entire feature is invisible: Enter arms an undocumented "binding" mode

Pressing **Enter** (or **Tab**) in any numeric field opens a green bar reading
`BINDING INTO Electrolyzer › Nominal power › Value  [cancel]` at the top of the *right* column,
~900 px from the field, where it displaces the `AUTHORED IN THE FILE` header. Simultaneously
**95 `USE` buttons** in the scope column go live.

Measured facts:
- On focus alone: bar is `0×0`. On `Enter`: `655×26`. On `Tab`: `655×26`, now targeting
  `Electrolyzer › Nominal power › **Unit**` — so ordinary keyboard traversal arms a binding on
  every field you land on.
- The `USE` buttons are `opacity: 0` with `pointer-events: auto` — invisible **and clickable**.
  A stray click in that 26 px band fires one.
- The bar's only action is `cancel`. There is no `bind` or `done`; the mode has no completion.
- The bar **persists across step navigation**, still pointing at a field on a step you left.
- Clicking `USE` produces the toast `copied {Hourly Irradiation > Horizontal single axis
  tracking > Value, Wh/m2}`. A button labelled **USE** performs **copy**.

**Repro:** click `203 Electrolyzer`, click into `Nominal power`, press Enter. Look right.
Then hover any row in the right column to reveal `USE`; click it; read the toast.
**Shots:** `22-bindmode-full.png`, `22b-bindmode-zoom.png`, `10-use-hover.png`, `10b-use-clicked.png`.

Nothing on the field, in the bar, or in the panel says what binding is or what to do next.
Enter in a numeric field means *commit* everywhere else in software; here it silently opens a
mode. This is the most valuable idea in the app and it is unreachable.

### D5 — Scope search misses units (which the placeholder promises) and the current step's own outputs

The search box reads `find a value by table, row or unit…`.

Unit search returns nothing, every time:

| query | matches | rows visibly showing it |
|---|---|---|
| `kW` | **0** | 6 (`Nominal power 5 500kW`, `Cost 10 000USD/kWh`, `… 0.0185kg/kWh`, …) |
| `USD` | **0** | 11 |
| `Wh/m2` | **0** | 6 |
| `deg` | **0** | 2 |
| `m2` | **0** | 4 |
| `Nominal power` | 2 | 2 ✓ |
| `capital` | 35 | 36 ✓ |

Separately, the panel renders 159 rows but the index omits the values produced by **the step you
are currently on**:

- Open `201 Hourly Irradiation`, search `tracking` → **0 match / "Nothing matches 'tracking'."**
  Six rows reading `Hourly Irradiation › … tracking` are visible in the same panel.
  Open `202 Photovoltaic`, search `tracking` → **6 matches**. Same rows.
- Open `900 Discounted Cash Flow`, search `Levelized` → **0 match**, while
  `Dependent Variables › Levelized cost 900` is on screen. From step 800, → 2 matches.

**Repro:** as above. **Shot:** `20-search-kW.png`.

### D6 — Step 202's middle hourly series button is dead

`202 Photovoltaic` → `HOUR BY HOUR` offers `Data`, `Available energy (hourly)`,
`PV hourly power generation`. The middle one never activates: it never receives the `on` class
and the figure never changes. Verified deterministically from both neighbouring states:

- From `PV hourly power generation`, click `Available energy (hourly)`, wait 4.5 s →
  heading stays `POWER GENERATION › PV HOURLY POWER GENERATION`, `on` stays on button 3.
- From `Data`, click it, wait 4.5 s → heading stays `IRRADIATION USED › DATA`, `on` stays on button 1.

The other two work. All three buttons on step 201 work. One of three figures on Photovoltaic
is unreachable. **Shots:** `14-202-Availableenerg.png` (identical to `14-202-Data.png`),
`14-202-PVhourlypowerg.png`.

### D7 — The hourly calendar contradicts its own caption

Caption: *"The lens that opens through summer and closes through winter is day length."*
There is no lens. The figure renders as a flat-topped, flat-bottomed solid teal block from Jan
to Dec. **Shots:** `14-202-Data.png`, `14-202-PVhourlypowerg.png`, `15-201-calendar.png`.

The lens is genuinely present in the geometry — I measured it — and the figure is sized to hide it:

- `svg.cal-grid` viewBox `0 0 1095 120`, rendered 446×128 CSS px. 4 315 rects, 3×5 user units
  each, stride 3 — so cells tile exactly at **1.22 CSS px per day**.
- Lit-hour envelope by day: Jan 5 → 9 rows (y 40–80); Jun 21 → **14 rows** (y 25–90);
  Dec 21 → 9 rows. The seasonal swing is ±10 user units = **±4 CSS px** in a 128 px panel.
- Opacity distribution across all 4 315 cells: min 0.08, **median 0.693**, p90 0.905, max 1.
  Half the cells are already ≥ 69 % ink, so the ramp has no dynamic range left; the faint
  dawn/dusk cells that *form* the lens sit at 0.08–0.2 against a near-black panel.

So: the interesting signal occupies 8 of 128 vertical pixels and is drawn in the palest ink
available. Make the panel 3–4× taller, and gamma-correct or percentile-clamp the ink ramp.

Also on this figure:
- **No colour legend and no scale.** "Ink is magnitude" is asserted in prose; there is no ramp
  and no swatch. You cannot read any cell.
- **Zero tooltips.** `svg.cal-grid title` count = **0**. 8 760 cells, no readout. The annual
  chart on step 900 *does* have per-mark `<title>`; this one does not.
- Header claims `8 760 CELLS`; 4 315 marks are drawn.
- The y-axis reads `00 06 12 18` but the caption says the axis was **rotated −8 h**. The axis
  labels are corrected by a four-line footnote instead of relabelled. It also says "local solar
  time for this site" — nothing in the app says where the site is.
- For a 20-year dictionary (`20y` shape), one unspecified year is drawn. The empty state says
  "Pick a series to draw **its year**" — singular, undefined, and there is no year selector.
- `HOUR BY HOUR` wraps to two lines. So does the panel heading. So does the right-hand stat,
  breaking mid-expression: `8 760 CELLS · 0.00` / `→ 2.70 ×10¹⁰ J`.
- Series buttons are 16 px tall (below any reasonable target size), thin gray outline on
  near-black, no `aria-pressed` — selection is class-only.

### D8 — Four comparable series, four independent normalizations

Step 201 produces four tracking modes whose entire purpose is comparison. Each calendar is
scaled to its own max (`909`, `953`, `931 Wh/m²`), only one can be shown at a time, and there is
no shared colour scale and no side-by-side. Comparison is the only reason these four exist, and
it is the one thing the figure cannot do.

Worse, the app surfaces a result it then makes impossible to investigate: peak
`Two axis tracking 931 Wh/m2` < `No tracking 953 Wh/m2`, and mean
`two axis 283.4 W/m2` < `single axis 284.6 W/m2`. Two-axis tracking collecting less than a
fixed horizontal plane is not physically possible [INFERENCE: this is an engine or lookup-table
problem, not a rendering one — but the UI is where a user meets it, and it gives them no way to
check]. **Shot:** `15-201-calendar.png`.

### D9 — The annual-cost chart draws 20 of its 43 marks at zero height

`900 Discounted Cash Flow` → `WHEN THE MONEY IS SPENT`. Of 43 `<rect>` elements, **20 have
`height="0.0"`** — invisible, and with no hit area their `<title>` tooltips are unreachable.
The tooltips that would rescue the chart are unreachable for exactly the bars that need them.

The chart as drawn: 21 stacked bars in 472×128 px; one bar (year 20) is ~100 px, everything else
is 0–2.2 px. Two y labels only (`20.3 M USD`, `0`), no gridlines, no axis title, so no bar but
the tallest can be read. The 20 `Fixed operating` bars at 1.5–2.2 px form a thin **orange
horizontal line** along the baseline that reads as an axis rule drawn in a data colour.

The legend lists lifetime totals (`Variable operating 19.9 M`) beside a per-year axis, unlabelled
as such — and `19.9 M` happens to equal the year-20 bar, so the coincidence actively misleads.
Tooltip data: `year 1 · Variable operating · 1.84 k`, `year 10 · 2.71 k`, `year 19 · 2.99 k`,
`year 20 · 19.9 M`. A four-order-of-magnitude jump in the final year is the chart's dominant
feature, and the caption — *"Year 20 is the largest single spend at 20.3 M USD — 98% of it is
Variable operating."* — states it without explaining it.

**Repro:** `900`, scroll to bottom, hover the tall bar (works) then any short bar (nothing).
**Shots:** `12-900-3900.png`, `12b-chart-hover.png`.

### D10 — The two figures on step 900 cannot be reconciled, and neither states its basis

`WHERE THE KG PRICE COMES FROM` gives `Variable operating costs 0.8105 USD/kg`, 19.32 % of a
4.1943 USD/kg levelized cost. `WHEN THE MONEY IS SPENT` gives `Variable operating 19.9 M USD`
over a `34.2 M USD` lifetime. Against ~7.04 M kg/yr for 20 years those two statements are
orders of magnitude apart. Neither figure says whether it is nominal or discounted, inflated or
not, per-year or summed. Two figures, one step, one screen, no stated basis.
**Shots:** `12-900-3000.png`, `12-900-3900.png`.

### D11 — In the failure state, unavailable upstream values masquerade as required user input

Break `Nominal power` on 203 (see D12). Then:

- Step 203's header goes from `3 tables · 5 inputs` / `5 to enter · 2 computed` to
  `3 tables · 7 inputs` / **`7 to enter · 0 computed`**. The two computed inputs are silently
  reclassified as things you must type.
- The `TIME` section's `Years` row — a dictionary of 8 arrays, previously a dark
  `8 entries` chip — becomes an **empty editable text box with an empty unit box**, and the
  section header now says `TIME  1 to enter`. The app is instructing the user to hand-type a
  20-year time dictionary.
- Step 205 does the same: `4 tables · 10 inputs`, `10 to enter · 0 computed`, `Years` blank.
- Meanwhile step 202 (the step that actually *failed*) renders its `Years` correctly as
  `8 entries`. So the degradation is specific to `never reached`.
- The `NEVER REACHED` banner promises *"Its fields are shown as written"* — the blank `Years`
  box is not as written.

**Repro:** `203`, set `Nominal power` to `lots`, Enter. Read the `TIME` section.
**Shots:** `08b-badinput-after.png`, `08d-205-attention.png`, `08c-202-failed.png`.

### D12 — The boilerplate misattribution notice is pasted onto steps it contradicts

Every failed step carries: *"The engine blames the step that was running, which is not always
the step that owns the bad value — paths resolve lazily. Check the flagged fields in the rail
before this one."*

On step 202 after breaking 203, that sentence is excellent and true. But:

- The flagged fields are on 203 and 205, which are **after** 202 in the rail. The advice says
  "before this one". It points the reader the wrong way.
- On the added `201.5 Solar Concentrator` the sentence is simply false: that step **does** own
  its fault (its own table is missing), nothing else is flagged, and the very next panel —
  `6 INPUTS NOTHING SUPPLIES` — names the cause precisely. The app hedges directly above its
  own correct diagnosis.

**Repro:** for the second case, hover the rail, click `+` between 201 and 202, choose
`Solar Concentrator`. **Shots:** `08c-202-failed.png`, `09b-added.png`.

### D13 — Steps can be added and never removed; nothing can be undone or saved

- The rail has **18** `add a step at …` buttons and **zero** remove buttons. No remove control
  exists anywhere in the document (`removeText` false; no matching button title).
- No revert, reset, undo, restore, or baseline anywhere in the page text.
- No dirty-state marking. After changing `Nominal power` from 5 500 to 7 000, step 203's rail
  entry is still `class="step ran"` — identical to every untouched step. After five edits you
  cannot tell what you changed.
- **A browser reload silently discards everything.** Edited to `LEVELIZED 4.1069`, added a step
  (`STEPS 18`); reloaded; back to `4.1943` and `STEPS 17`. No warning, no `beforeunload`, no
  save, no export.

An exploration tool with an irreversible mutation and no persistence is a tool you cannot
explore in. **Shots:** `09b-added.png`, `09c-hover-added.png`.

### D14 — The masthead names the open pathway five different ways, none matching the chooser

| chooser says | masthead says |
|---|---|
| PV + Electrolysis | `PV + E` |
| Solar Thermal | `Thermal` |
| Photoelectrochemical | `PEC` |
| Photocatalytic | **`PC`** |
| PV Electricity | **`PV_E_Electricity_Production.md`** |

A truncation, a word-drop, an acronym, a two-letter cipher that reads as "personal computer",
and a raw source filename with underscores and an extension. This is the persistent identity
label for the open document.

**Repro:** `OPEN A PATHWAY` → each of the five; read the masthead each time.
**Shots:** `16-chooser.png`, `17-photocatalytic.png`, `18-pv-electricity.png`.

### D15 — The chooser shows hardcoded published costs styled identically to the live one

`PV Electricity` reads **`0.0286 USD/kWh`** in the chooser and **`0.02858 USD/kWh`** in the
masthead for the same pathway, in the same monospace treatment, ~600 px apart. One is a
reference constant, the other is computed; nothing distinguishes them.

Also in that panel: precision is "5 significant figures" applied to a column spanning 0.0286 to
185.44, so decimal points land at four different x positions in a five-row comparison table
(`4.1943`, `3.2706`, `139.42`, `185.44`, `0.0286`) — and the published Photoelectrochemical and
Photocatalytic figures (139.4189, 185.4433) are rounded to `139.42` / `185.44` and are therefore
never visible anywhere in the UI. The `USD/kWh` row sits in the same right-aligned number column
as four `USD/kg` rows, inviting the reading "6 000× cheaper"; the description does warn, the
number column does not. There is no marker for which pathway is currently open, and no warning
that opening one discards your edits. **Shot:** `16-chooser.png`.

### D16 — Number formatting: four notations, one of them nonsense, and the headline at three precisions

- **Three notations for large numbers, arbitrarily mixed.** Step 400's panel: `1.11e+7USD`,
  `4 312 000USD`, `1.20e+7USD`, `0 → 4 695 969USD`. Step 203's: `6.73 ×10¹³` (typeset
  superscript). Step 900's decomposition: `4.19e-5`, `-2.89e-5`, `-5.23e-7`. So a currency total
  is `1.11e+7` while a smaller currency total is `4 695 969`, and elsewhere the same magnitude
  is `×10¹³`. `1.11e+7 USD` is the wrong register for a capital cost report.
- `1.11e+7 USD` appears six times for four genuinely different quantities; 3-sig-fig rounding
  makes `Depreciable Total` and `Total capital costs` (differing by 4 633 USD) print identically.
- **`-0.0%`** — signed zero. Step 900, `End of life`, both PV+E and PV Electricity.
- **`0.`** — a bare trailing decimal point as a field value. Step 400, `Battery CAPEX`.
- **Years get thousands separators.** `Assumed start-up year 2 020`, `Basis year 2 016`,
  `Reference year 2 016`, `Current year for capital costs 2 016`, in the scope column and the
  dark panel. The input field correctly shows `2020`.
- **The headline number at three precisions on one screen.** Step 900: masthead `4.1943`,
  made-panel `Levelized cost 4.194`, Σ line `4.1943`, decomposition footer `4.1943`.
- **`Enter` and blur format differently.** Enter leaves the raw text (`7000`); blur re-formats
  (`95,500`). After an Enter-commit, `Nominal power` reads `7000` while `Replacement time` two
  rows below reads `80,000`.
- Unit exponents are never typeset even though mantissa exponents are: `m2`, `m3`, `Wh/m2`,
  `kWh/m3`, and `liter/(cm*mol)` with a literal `*`.

**Shots:** `05-400-2700.png`, `05-400-900.png`, `12-900-3900.png`, `18b-pve-dcf.png`,
`01-first-contact.png`, `07c-enter-1200ms.png`.

### D17 — The entire secondary text layer fails contrast, by about half

Measured foreground/background pairs, computed WCAG ratios:

| element | example | size | contrast | AA needs |
|---|---|---|---|---|
| rail footer (run health) | `17 ran clean` / `2 need attention` | 10 px | **2.24** | 4.5 |
| rail step numbers | `100`, `201` | 11 px | **2.24** | 4.5 |
| field dimension + range | `dimensionless  range 0 … 1` | 9.5 px | **2.38** | 4.5 |
| field descriptions | every one | 12 px | **2.38** | 4.5 |
| section counts | `1 to enter`, `2 to fix` | 10 px | **2.38** | 4.5 |
| scope units | `Wh/m2`, `USD`, `kg` | 9.5 px | **2.51** | 4.5 |
| scope group heads | `Hourly Irradiation` | 10 px | **2.51** | 4.5 |
| masthead labels | `paper plant`, `steps` | 10 px | 4.43 | 4.5 |
| series buttons | `Data` | 9.5 px | 4.43 | 4.5 |

This is systematic, not incidental. It hits the physical dimension, the declared range, every
description, every unit, the "to fix" count that tells you where the errors are, and the global
run-health footer. It is exactly the layer a first-time reader depends on and a returning expert
can skip. The colour is `rgb(169,163,149)` on `rgb(250,249,245)`; darkening it to about
`rgb(122,116,102)` clears AA without touching the palette's character.

### D18 — Accessibility: no labels, no semantics on the controls, no text alternative on any figure

- **`document.querySelectorAll('label').length === 0`.** Not one `<label>` in the app. No input
  carries `aria-label`, `name`, `id`, or `title`. A screen reader on step 203 hears
  "edit text, 5,500" with no indication of what it is. There are 10 such inputs on that step
  alone.
- Every numeric field is `type="text"` with no `inputmode="decimal"`.
- Rail steps are focusable `<li tabindex="0">` with a click handler — no `role`, no accessible
  name. `aria-current` *is* managed correctly, which shows the author knew where to look and
  then stopped.
- Every figure — `svg.annual`, `svg.cal-grid`, and every `svg.spark` sparkline (15 on step 203
  alone) — has no `role`, no `aria-label`, no `<desc>`.
  The calendar has no `<title>` on any of its 4 315 marks either.
- The focus ring is the browser default `auto 1px rgb(0,95,204)` — a Chrome blue on a warm
  cream serif page. Functional, undesigned.
- **Keyboard traversal of the rail is 35 stops.** Focusable items interleave
  `+ / step / + / step …`; arrow keys do nothing (ArrowDown from step 100 leaves focus on step
  100). Reaching step 900 takes 33 Tab presses. Enter and Space on a focused step do open it —
  that part works.
- 95 `USE` buttons at `opacity: 0` are in the tab order (they do reveal on focus).

### D19 — `a → b` range notation is not consistently ordered, and the sparkline contradicts it

Step 202, `POWER GENERATION`, four adjacent rows. All four sparkline paths are byte-identical
and descend left→right (measured: first y = 1.5, last y = 13.5, viewBox `0 0 78 15`).

- `Available energy (daily)` — `7.40 → 6.73 ×10¹³` (decreasing) ✓ matches the sparkline
- `Available energy (hourly)` — `7.40 → 6.73 ×10¹³` ✓
- `PV hourly power generation` — `7.40 → 6.73 ×10¹³` ✓
- `PV yearly power generation` — **`6.73 → 7.40 ×10¹³`** (increasing) ✗ same descending sparkline

Under a first→last reading, row 4 is wrong. Under a min→max reading, rows 1–3 are wrong. Nothing
anywhere states which it is. **Shot:** `13-202-hourly.png`.

Related, same four rows: `daily`, `hourly` and `PV hourly` show **byte-identical** summaries and
byte-identical sparklines. The `min → max` reduction is too lossy to distinguish three different
physical quantities from each other.

### D20 — The sparkline touches the numeral and reads as a minus sign

In the dark "what this step made" panel, the trend sparkline's right terminus abuts the first
digit with zero gap whenever the value string is wide. On step 203, `Available energy (daily)`
renders as `—6.14 → 1.33 ×10¹² J 20y`: a positive energy that looks negative.

**Repro:** `203 Electrolyzer`, scroll the middle column to ~900 px, `POWER GENERATION` rows.
**Shots:** `04b-203-collision.png`, `04-203-mid.png`, `13-202-hourly.png` (3 of 4 rows collide).

In the right column the same sparklines run flush to the panel's right edge with no padding,
breaking the numeric right-alignment that every other row obeys (`02f-201-scope.png`).

### D21 — Section counts label the wrong axis, so full sections announce themselves as empty

Step 203's header says `5 to enter · 2 computed`. Its three sections say `TIME 0 to enter`,
`ELECTROLYZER 5 to enter`, `POWER GENERATION 0 to enter`. The two computed inputs live in the
two sections labelled "0 to enter" — a section with content announcing itself as having none.
Step 400's `INFLATION` section says `0 to enter` above four informative rows. `1 to fix` proves
the counter can carry other states; it just doesn't carry "computed".

Related counting problems:
- The header's `N inputs` excludes computed rows, so it undercounts the rows on screen
  (`3 tables · 5 inputs` for a step showing 7).
- `600 Labor Operating Cost` reads **`2 tables · 1 inputs`**. The rail singularizes correctly
  (`5 values out to 1 step`), so the code for this exists elsewhere.
- Step 400's four CAPEX fields are each labelled `optional` in the meta line while their section
  says `1 to enter` — the counter includes optional fields.

**Shots:** `04-203-top.png`, `02-step-400.png`, `02-step-600.png`.

### D22 — `required` and `optional` on the same field, 40 px apart

Step 201, field `Module tilt`: an amber-highlighted empty box with placeholder **`required`**,
and directly beneath it the meta line **`angle  range 0 … 1.57  optional`**. Its unit box is
empty white — the only field in the app with neither a unit nor the `-` placeholder, which reads
as a third thing you must fill in. The section counts it (`6 to enter`) and the step still runs
clean (`17 ran clean`).

**Repro:** `201 Hourly Irradiation`, `IRRADIANCE AREA PARAMETERS`, field 01.
**Shot:** `02c-201-tilt.png`. (Confirmed independently by a sibling agent at 7 sites across
pathways, including `Technical Operating Parameters and Specifications > Design output by year`
on thermal/pec/photocatalytic step 300.)

### D23 — Engine vocabulary throughout the user surface

Terms shown to the user with no gloss, in a panel that otherwise writes in plain English:

- **`UNDECLARED`** in warning amber on 11 rows of step 400 — including every `Summed total` and
  `Summed group total`, i.e. the subtotals that make up the capital cost. The most important
  rows in the table are flagged with a scary unexplained word in the app's warning colour.
- **`sum_all_tables` / `declared in special_insertions, never written` / `absent`** — the final
  row of step 400.
- **`Table 'Solar Concentrator' is required but not found in `dcf.inp`"`** — with Python's repr
  double-quotes still wrapped around it, and an internal variable name.
- **`[Plugin: Photovoltaic_Plugin] can't multiply sequence by non-int of type 'float'`** — raw
  interpreter text, and the plugin prefix duplicates the step title above it.
- Raw column keys as row qualifiers: `Process WaterCost_Path`, `Cost_Unit`, `Cost_Value`,
  `Price_Conversion_Factor_Unit`, `Usage_Path`, `Yearly operation dataDuration_Value`,
  `Electrolyzer stack replacementFrequency_Value`, `Test consumerType`. Note the missing
  separator: the accessible/copyable text is `Process WaterCost_Path`, one word.
- Raw values: `None` (Python), `on_demand`, `flexible`.
- Raw dimensions: `1/temperature_diff`, `absolute_temperature`, `1/delta_degC`.
- Leaked path expressions as *values*: `{Electrolyzer > H2 production (yearly) …`,
  `{Hourly Irradiatio…`, `pyH2A.Config~Defaults_TEA.md`.
- `Test consumer` as a first-class table in the shipped PV+E pathway. [INFERENCE: probably
  pyH2A's own naming, but the UI launders it into a user-facing row.]

**Shots:** `05-400-2700.png`, `09b-added.png`, `08c-202-failed.png`, `01d-scope-later.png`.

Also: step 201's `File` description renders literal markdown — `Path to a `.csv` file
containing hourly irradiance data` — backticks unprocessed (`02d-201-file.png`).

### D24 — Truncations with no recovery path

No `title` attribute, no tooltip, no expansion anywhere:

- `File` value hard-clipped mid-word to `pyH2A.Lookup_Tabl` with no ellipsis (step 201). The same
  value in the scope column is clipped differently: `pyH2A.Lookup_Table…`. Two truncations of one
  string, neither showing it (`02d-201-file.png`).
- `Data` value clipped to `{Hourly Irradiation` — an unclosed brace (step 202).
- Unit chips clip mid-glyph: `1/delt` for `1/delta_degC`; `USD/ac` for `USD/acre` (the trailing
  partial glyph reads as a colon). The full `USD/acre` renders fine 900 px away in the dark
  panel (`02e-201-tempco.png`, `05-400-900.png`).
- **The scope column truncates the unit — the load-bearing part.** Step 203, `202 PHOTOVOLTAIC`:
  three of four rows read `7.40 → 6.73 ×10¹³…` with `J` eaten, while the fourth keeps it
  (`04c-203-scopetrunc.png`).
- Descriptions in the dark panel clamp mid-word with no expand: `(dictionary of y…`,
  `non-zero only in the firs…`, and once to a dangling `…` alone on a fresh line
  (`05-400-2700.png`).

### D25 — The add-a-step picker truncates exactly the part that differs

`ADD A STEP` ranks candidates by how much of their input the project already supplies — a
genuinely excellent idea. The execution throws it away:

- Requirements are clipped at ~29 characters, and they share long prefixes, so the three rows
  under `Solar Concentrator` read `Non-Depreciable Capital Costs › Land re…`,
  `Non-Depreciable Capital Costs › Solar c…`, `Direct Capital Costs - Solar Concentrat…`. The
  discriminating tail is exactly what is cut. Meanwhile ~500 px sits empty between the
  description column and the requirement column.
- `Catalyst Separation`'s description is cut to **"Calculation of cost for catalyst separation
  (e.g."** — no ellipsis, unclosed parenthesis.
- The readiness figure (`1 of 6 ready` / `17%`) is right-aligned on two lines ~140 px below its
  title with empty space above it, reading as a footer to the wrong row. It is also redundant:
  17 % *is* 1/6, and 1-of-6 is the more useful form.
- The ranking is degenerate here: five of six visible candidates tie at `0%`, with no secondary
  ordering and no explanation of what "ready" counts.
- No search or filter, in a scrolling list — while the scope column, which needs one less, has one.
- Already-present plugins are dimmed with no explanation and still occupy full rows.
- Category swatches appear with no legend, same as the rail dots.

**Repro:** hover the rail, click the `+` between 201 and 202. **Shots:** `09-add-picker.png`,
`21-picker-zoom.png`.

### D26 — `6 INPUTS NOTHING SUPPLIES` is contradicted by two of its own six rows

Add `Solar Concentrator` at 201.5. The panel is the best thing in the app, and its heading is
wrong:

- `PEC Cells › Number` — annotated **`written by PEC`**.
- `Non-Depreciable Capital Costs › Solar collection area` — annotated
  **`written by [PEC] [Photocatalytic] [Photovoltaic] [Solar_Concentrator]`**.

Something *does* supply those. `Photovoltaic` is in this very pathway, half a position later —
so the actual fix is "move this step after 202", and the panel never says so even though it has
computed everything needed to. The step lists **itself** as a writer of a value it needs, with
no explanation. The writer chips mix display names with a raw class name (`Solar_Concentrator`).
The chips are `<button>`s but carry no hover affordance.

Presentation: the italic annotation *"no plugin writes this — it is a value you supply"* wraps on
three of six rows, orphaning **"you supply"** on its own line directly above the description, so
annotation and description merge into one gray blob.

**Shot:** `09b-added.png`.

### D27 — Transient toasts cover persistent content

The toast is bottom-anchored in the middle column and opaque.

- After adding `Solar Concentrator`, the `copied {Hourly Irradiation > …}` toast covers the
  `MISSING — required, and neither this file nor its defaults supply it` error on
  `Concentration factor` (`10b-use-clicked.png`).
- After editing `Nominal power`, the `4.1943 → 4.2267 (+0.77%)` toast covers the
  `Available energy (hourly)` value chip (`07c-enter-1200ms.png`).

The edit toast also lands ~520 px below the field that caused it, and never says *which* field
changed — only the aggregate delta. Two edits in a row and you cannot attribute either.

### D28 — Every browser tab shared one server-side project

Observed live: my masthead flipped from `PV + E / 17 steps / 4.1943` to
`Thermal / 10 steps / 3.2706` while my rail and body still rendered PV+E, and a red toast read
literally `KeyError: 'Electrolyzer'`. Cause confirmed with the sibling agent driving the same
server: the client never sent a session id, so all tabs shared one document — last `project.open`
won, and other tabs kept rendering stale state because nothing pushes. **Already fixed during
this review** (per-tab session ids); I re-verified every finding above afterwards. Logged for the
record, and because the residue is still citable: **raw Python exception text reaches the toast
unmodified** (`KeyError: 'X'`), which is D23's problem in its most user-hostile form.

### D29 — Smaller things, verified

1. **The rail's edge gutter encodes no direction.** Hovering `400 Capital Cost` lights inbound
   edges from 100/200/202 and the outbound edge to 900 in identical weight, with no arrowheads
   and no distinction. The footer says `6 values in from 3 steps / 5 values out to 1 step`; the
   drawing cannot tell you which is which. Colour is spent on the source's category, not on
   direction — and direction is the reason you hovered (`03-hover-400.png`).
2. **The hover readout is 380–700 px from the cursor.** It is a fixed footer at the bottom of the
   rail, not a tooltip. Hovering step 203 puts the count 620 px below the pointer; moving your
   eyes there is fine, moving your mouse there kills the hover.
3. **The hover readout lies about broken steps.** Hovering `201.5 Solar Concentrator` — which the
   middle column says needs 6 unsupplied values — reports **`0 values in from 0 steps / 0 values
   out to 0 steps`** (`09c-hover-added.png`). And `0 values out to 0 steps` on step 900 is a
   robot's way of saying "this is the last step".
4. **At rest the gutter is texture, not information.** Twelve edges share ~8 tracks at ~10 px
   spacing and cross each other; no single edge is traceable. The claim "the rail is the workflow
   graph" is only true on hover (`01c-gutter.png`).
5. **The rail's dot does double duty.** Healthy steps get a category colour; broken steps get a
   status colour. So a failing step loses its category and a healthy step has no status.
   There is no legend for the category colours anywhere in the app.
6. **Four of 17 steps have no description** (201, 301, 302, 400). The title block silently
   collapses from three lines to two; no "no description" state, so the vertical rhythm breaks
   step to step (`02-step-201.png`).
7. **Computed chips and editable inputs have different right edges.** Dark computed chips
   right-align at ~847 px (with the unit column); editable values at ~778 px. In a worksheet
   built for vertical scanning, "the value" sits in two different columns
   (`04-203-top.png`, `05-400-900.png`).
8. **84 redundant step chips.** Every row in `NOT COMPUTED YET` carries a `200` / `201` chip
   restating the group header directly above it (`01d-scope-later.png`).
9. **Adjacent groups differing only in plurality.** Step 400's panel shows
   `DIRECT CAPITAL COST` then `DIRECT CAPITAL COSTS`, and `INDIRECT CAPITAL COST` then
   `INDIRECT CAPITAL COSTS`, as separate headers. It reads as a duplicate-render bug
   (`05-400-2700.png`).
10. **Undefined array-shape suffixes, in two notations.** `×10¹³ J 20y` on step 203 and
    `0 J ×20` on step 400 — `20y` and `×20` for the same concept, neither explained anywhere,
    and `J 20y` reads as a compound unit.
11. **Inconsistent zero handling within one step.** The annual chart writes
    `zero in this pathway: Variable operating, Replacement` — a lovely touch — while the
    decomposition table immediately above gives those same zeros full rows with empty bars
    (`18b-pve-dcf.png`).
12. **The decomposition's family gloss wraps and orphans.** `Financing & tax` + gloss becomes
    two lines with `state takes` alone under the bold name; `End of life` orphans `parts fetch`.
    Both read as separate list items (`12-900-3900.png`).
13. **`Salvage -1.65%` gets a green tick and `Decommissioning +1.65%` a gray one**, 3 px each,
    breaking the family-colour scheme that governs every other bar, with no explanation.
14. **Mixed unit systems presented unreconciled.** `Cost of land 500 USD/acre` beside
    `Land required 37 500 m2`, with no conversion shown. The engine handles it; the reader is
    left to.
15. **`157 held · 2 arrive later` on the final step**, where the masthead already shows the
    levelized cost the panel calls "not computed yet". The model is right; the phrasing stumbles.
16. On failure the invariant breaks: `89 held · 0 arrive later` (89 ≠ 159), so the sentence
    silently changes meaning from "will arrive" to "did arrive".
17. **Half the masthead is dead space** — a 796 px gap of 1600 between `PV + E` and
    `open a pathway` — while `LEVELIZED 4.1943`, the app's entire product, is set at the same
    size as `RUN 10.1 ms`, a debug stat (`01b-masthead.png`).
18. Amber means three things: "required" on `Module tilt`, "UNDECLARED" in step 400, and
    "changed from baseline" in the masthead after an edit.
19. **The `-` in a dimensionless field's unit box is an editable input containing a literal
    hyphen**, indistinguishable from a placeholder or a disabled control.
20. Exposed insert positions are engine-internal and oddly derived: `add a step at 1`, `at 150`,
    `at 252.5`, `at 351`, `at 450.5`.

---

## What is genuinely good and must not be lost

1. **The three-column frame, and its three questions.** *What this step needs / what this step
   made / what is available here.* I understood the app in ten seconds cold. Keep this exactly.
2. **Editable inputs vs. dark computed chips.** The single best decision in the app: "you can
   change this" and "this came from upstream" are distinguishable at a glance, with no legend
   and no learning. Do not unify these treatments.
3. **`READS` badges in the scope column.** They answer the question that makes a 159-value scope
   panel usable: *which of these does this step actually touch?* Nothing else in the app earns
   its pixels this hard.
4. **The failure cascade.** `NOT A NUMBER` + `"lots" is not a number, and this field is declared
   float or int` at the field; the section counter flipping `5 to enter` → `1 to fix`; the step's
   `never reached` banner; the rail's red dot on the failing step, amber badges on the flagged
   ones, and everything downstream going hollow; the footer's `3 ran clean / 2 need attention /
   13 never reached`; `no cost — the run stopped` in the masthead. Five coordinated registers,
   all correct, all legible. This is better than most commercial tools manage.
5. **The lazy-resolution disclaimer.** *"The engine blames the step that was running, which is not
   always the step that owns the bad value — paths resolve lazily."* Somebody understood their
   own engine's failure mode and told the user the truth about it. Fix where it's pasted (D12);
   never delete the sentence.
6. **`6 INPUTS NOTHING SUPPLIES`.** Every unmet requirement as `Table › Row`, each annotated
   either "no plugin writes this — it is a value you supply" or `written by [PEC]`. Naming the
   plugin that would fix it is the correct answer to "what do I do next". Fix the heading and add
   the reorder hint; keep the panel.
7. **Ranking candidate plugins by how much the project already supplies.** The right idea for
   choosing a plugin. It needs untruncated requirements and a tiebreaker, not a redesign.
8. **The Σ reconciliation.** *"the 11 components sum to 4.1943, and that is the headline —
   residual 8.9e-16."* An audit trail on the app's only claim, volunteered. Every model should
   do this and almost none do.
9. **Family + component structure in the cost decomposition**, with one shared bar scale across
   both levels and the value coloured to match its family bar. The parents genuinely reconcile
   with their children — I checked both pathways.
10. **The functional-unit swap.** `WHERE THE KG PRICE COMES FROM` → `WHERE THE KWH PRICE COMES
    FROM`, `USD/kWh` in the masthead, and zero `hydrogen`/`H2`/`kg` anywhere across 12 steps,
    both columns, `title` attributes and SVG tooltips. Meticulous.
11. **Prose captions that make a specific, checkable claim.** *"Year 20 is the largest single
    spend at 20.3 M USD — 98% of it is Variable operating."* *"zero in this pathway: Variable
    operating, Replacement."* This is what figure captions are for.
12. **Empty states that instruct.** *"Pick a series to draw its year."* Guidance, not
    "nothing here".
13. **The typography and the restraint.** Serif headings against monospace numerals, warm-tinted
    neutrals, no gradients, no glass, no card grid, no centred hero. It looks made rather than
    generated. It is also the reason the contrast failure is so annoying: the palette is good,
    the greys are just three steps too light.
14. **Sub-20 ms recalculation with visible propagation.** Change `Nominal power` 5 500 → 7 000
    and watch `Land required` go 37 500 → 47 727 m² in the right column. The engine loop is
    the foundation everything else rests on, and it is fast and correct.

---

## Grades

### Thinking — A−

The conceptual work is the best part of this and it is not close. Someone worked out that a
levelized-cost model is not a form but a *pipeline*, and that the honest way to show a pipeline
is one step at a time with its needs, its scope, and its products separated. They worked out that
users need to distinguish authored values from computed ones, and gave that distinction a
dedicated visual channel. They worked out that a failing step is usually not the guilty step, and
said so in plain English. They worked out that "which plugin should I add" is answered by "how
much of its input do you already have". They put a residual on the headline number. They handled
the kg→kWh functional-unit swap without a single leak across 12 steps.

Three points off. The **binding** mechanism is unfinished thinking, not just unfinished
execution: the bar says "binding into X" but the only available action copies a path to the
clipboard, so the model has no completion, and no thought was given to how anyone would discover
it. **Provenance of edits** is missing from the model entirely — no dirty marks, no revert, no
save, no inverse for "add a step" — which contradicts the app's own premise that you should
explore. And the **figures were specified without checking that the data would fit them**: the
hourly calendar is 128 px tall for a signal whose whole vertical structure is 27 px, and the
annual chart's linear y-scale renders 19 of its 21 years at 2.2 px or less.

### Execution — C

Every layer above the concept is unfinished, and the failures are the kind that cost trust
rather than usability.

The **numbers** are the worst of it, because numbers are the product. One value rendered at two
magnitudes in one viewport (D1). The multiplier's unit chip stating the product's unit on every
equation row in the capital-cost table (D2). Four notations for large numbers, `-0.0%`, `0.`,
years with thousands separators, and the headline cost at three precisions on one screen (D16).
A chooser price that disagrees with the masthead price for the same pathway (D15). An arrow
notation whose direction contradicts its own sparkline (D19). A sparkline that touches a numeral
and turns a positive energy negative (D20). Individually each is a twenty-minute fix. Together
they mean I would re-derive anything this tool told me.

The **accessibility** floor is not met. Zero `<label>` elements. No `aria-label` on any input.
No text alternative on any figure. And the secondary text layer — the layer carrying every
dimension, range, description, unit, and the run-health footer — sits at 2.24–2.51:1 at 9.5–12 px
(D17). That is one CSS variable away from fixed and it is the most consequential single change in
this list.

The **details** are not swept. Truncations with no recovery in six places, including the units
in the scope column and the requirement paths in the picker — clipped precisely where they
differ (D24, D25). `required` and `optional` on the same field (D22). `2 tables · 1 inputs`.
Sections full of content announcing `0 to enter` (D21). `UNDECLARED`, `sum_all_tables`,
`special_insertions`, `dcf.inp`, `Cost_Path`, `on_demand`, raw `KeyError`, unrendered markdown
backticks — engine vocabulary throughout the surface (D23). Toasts covering error messages (D27).
Two dead ends: an hourly series button that does nothing (D6), and a search box that advertises
unit lookup and returns zero for every unit while silently omitting the current step's own
outputs (D5).

Nothing here is architectural. The plumbing is fast, the model is right, the type is good. What's
missing is the last 20 % that a careful pass over units, number formatting, contrast, labels, and
truncation would deliver — plus finishing the binding interaction and giving the two figures the
vertical room and the tooltips their own captions promise. Do that and the execution grade moves
to a B+ without one structural change.
