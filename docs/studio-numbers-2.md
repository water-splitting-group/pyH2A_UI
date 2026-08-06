# Numbers audit, round two

**Question asked:** does Paper Plant Studio ever show a number the engine did not
produce, or describe the model wrongly?

**Short answer:** the numbers are honest. Across 233 cell perturbations, 6 full
download/reopen round trips, 45 plugin-into-pathway combinations, 49 drawn equations,
571 bounded fields, 20 full hourly series and 6 cost breakdowns, I could not find a
single figure on screen that is not the number pyH2A reaches from the file the app
would hand you. The static/WASM build reproduces the native build bit for bit.

**But the app writes files real pyH2A refuses, and stays silent about it.** Two
defects, both in the "create a row / type a number" path, both reproducible in the
flagship pathway, both invisible at the field where the mistake lives. One of them
re-creates the exact `'NoneType' object has no attribute 'strip'` that the last round
of fixes was written to eliminate.

Everything below is reproducible. Harnesses are in `studio/scratch/nt*.py`; each is
runnable with
`cd studio && UV_PYTHON=3.12 uv run --with-editable . python scratch/<name>.py`.

---

## Defects

### D1 — BLOCKER. A row the app creates in a cost table breaks the model, silently

`scratch/nt2c_repro_newrow.py` · screenshot `scratch/nt-defect1-compressor.png`

Open **PV + Electrolysis**. Add one line to `Direct Capital Costs - Electrolyzer` —
a compressor, 250 000 USD. The single most ordinary edit anyone makes to a TEA.

``
cell.edit  table='Direct Capital Costs - Electrolyzer' row='Compressor'
           column='Value' text='250000' create=True
``

The app writes `Compressor | 250000 |  | - |` and the levelized cost goes from
4.1943 USD/kg to nothing:

``
[Plugin: Capital_Cost_Plugin] 'Direct Capital Costs - Electrolyzer > Compressor > Value'
(entry: 'Quantity(250000, '-')'): Expected dimension 'currency', but got 'dimensionless'
``

Upstream's own `pyH2A(input_file, out)` refuses the downloaded file with the identical
error, so this is the app authoring a bad file, not the app mis-reporting a good one.
The field on screen shows `currency · range ≥ 0 USD · optional`, a unit box reading
`-`, and **no problem at all**. The app knows the dimension well enough to label the
range in USD and writes the wrong unit anyway.

Six for six, all in `pv_e` except the last:

| created row | file gets | engine says |
|---|---|---|
| `Direct Capital Costs - Electrolyzer > Compressor` | `250000 \|  \| - \|` | `Expected dimension 'currency', but got 'dimensionless'` |
| `Other Fixed Operating Costs > Insurance` | `20000 \|  \| - \|` | same |
| `Utilities > Cooling water` | `5 \|  \|  \|  \|  \|  \|  \|  \|` | `Unknown unit encountered during parsing: 'n'` |
| `Planned Replacement > Membrane` | `50000 \|  \|  \|  \|  \|` | `Frequency_Value (entry: 'n/a'): Expected (int, float), but got str` |
| `Direct Capital Costs - Compression > Compressor` (new table) | `250000` | **`'NoneType' object has no attribute 'strip'`** |
| `tea_mass: Direct Capital Costs - Plant > Compressor` | `250000 \| - \|` | `Expected dimension 'currency', but got 'dimensionless'` |

Every one shows `problems=NONE` at the field. Every one is refused by upstream pyH2A
with the same message.

**Root cause, two halves that cover for each other.**

*The writer.* `grammar.ensure_cell` (grammar.py:239-249) fills a created row's unit
from `engine.declared_unit`, falling back to `-`:

``python
unit = engine.declared_unit(table_name, row_name)
...
row.setdefault(column, (unit or '-') if column == 'Unit' else '')
``

`engine.declared_unit` (engine.py:315) does a **literal** lookup:

``python
spec = inputs.get(table_name, {}).get(row_name)
``

Every cost table pyH2A ships is declared with a wildcard —
`'<...> Direct Capital Cost <...>': {'<...>': …}`, `'Utilities': {'<...>': …}`,
`'Planned Replacement': {'<...>': …}`, `'<...> Other Fixed Operating Cost <...>'`. The
literal lookup misses all of them, returns `None`, and `- ` is written into a field
declared `currency`. The `or '-'` fallback is doing exactly the thing its own
docstring warns against, one level up from where the docstring is looking.

Second, only the column named exactly `Unit` is ever filled. `Usage_Unit`,
`Cost_Unit`, `Frequency_Unit`, `Price_Conversion_Factor_Unit` are padded with `''`,
and pyH2A then reads its own `n/a` filler as a unit: `Unknown unit … 'n'`.

Third, when the table does not exist yet, `ensure_cell` creates it as `Name | Value`
and `declared_unit` returns `None`, so no `Unit` column is added at all — and the
plugin reading the group gets `None.strip()`. That is the failure mode the previous
round fixed for literal-declared tables and did not fix for pattern-declared ones.

*The validator.* `frame._check_dimension` (frame.py:762) returns early on `-`:

``python
if not declared or not unit_text or unit_text.strip() in ('', '-'):
    return
``

So the one token the writer falls back to is the one token the checker ignores.
`scratch/nt8_dashblind.py` scans every field of all six shipped files: **189 cells
hold `-` or blank on a field with a declared dimension, and all 189 are declared
`dimensionless`.** Zero legitimate uses of `-` on a dimensioned field exist. The early
return protects nothing and hides exactly the rows the app itself writes.

**Reach.** Today the shipped worksheet has no "add a row" button, so the only ways in
are the `cell.edit` API (`create: true`, exposed on both servers) and the source
editor. The worksheet's own create path fires only on a field rendered `absent`, and
across all six pathways there are exactly eight of those — `Irradiance Area
Parameters > Module tilt` (`declared_unit` → `rad`), `Technical Operating Parameters
and Specifications > Plant design capacity` (→ `kg / s`) and `> Design output by
year` (→ `kg`). All literal, all resolved, all safe. So is `workflow.add` + fill
(58 plugin/pathway combinations checked, below), because the guided fill only ever
names literal rows. But this is one UI button away from being the first thing Jacob
tries, and the validator half is a live hole regardless of who writes the `-`.

### D2 — MAJOR. `spell_for_field` asks the wrong plugin, and misses the pathway it was written for

`scratch/nt4_repro_spelling.py`

Open **Solar Thermal**. Type `1` into `Solar-to-Hydrogen Efficiency > STH`
(bounds are 0…1, so `1` is in range).

``
cost 3.2706 USD/kg  ->  no cost
[Plugin: Solar_Thermal_Plugin] 'Solar-to-Hydrogen Efficiency > STH > Value'
(entry: '1'): Expected (<class 'float'>,), but got <class 'int'>
problems shown at the field: NONE
``

Type `1.0` instead and it runs, to 3.2693 USD/kg. That is the precise message
`engine.spell_for_field` exists to prevent — its docstring is about
`Reverse_Osmosis_Plugin`'s `Power demand` and "a distinction between 4 and 4.0 that
does not exist in their problem."

It fails here because it consults the wrong plugin (engine.py:343-354):

``python
for plugin_name in installed_plugins():          # alphabetical
    spec = inputs.get(table_name, {}).get(row_name)
    if not spec: continue
    declared = (spec.get('Value') or {}).get('type') or set()
    if declared == {float}: return f'{stripped}.0'
    return text                                   # first declarer wins, by name
``

Three plugins declare `Solar-to-Hydrogen Efficiency > STH`. `PEC_Plugin` and
`Photocatalytic_Plugin` declare it `{float, int}`; `Solar_Thermal_Plugin` declares it
`{float}`. Only `Solar_Thermal_Plugin` is in this workflow. `PEC_Plugin` sorts first,
so the function answers from a plugin that is not running.

Ten rows have this shape (`scratch/nt34_units_types.py`, section 4a):

| row | float-only declarer | consulted instead |
|---|---|---|
| `Solar-to-Hydrogen Efficiency > STH` | Solar_Thermal | PEC |
| `Solar Input > Mean solar input` | Solar_Thermal | PEC |
| `Technical Operating Parameters and Specifications > Plant design capacity` | Solar_Thermal | PEC |
| `Electrolyzer > Nominal power` | Stored_Power_Electrolysis | Electrolyzer |
| `Electrolyzer > Minimum capacity` | " | " |
| `Electrolyzer > Replacement time` | " | " |
| `Electrolyzer > Hydrogen yield per unit energy` | " | " |
| `Electrolyzer > Power requirement increase per year` | " | " |
| `Inflation > Combined inflator` | Replacement | Capital_Cost |
| `Inflation > Inflation correction` | Replacement | Capital_Cost |

Two of them bite in a published pathway today (`STH`, `Mean solar input`, both in
Solar Thermal). The five `Electrolyzer` rows do not bite in PV+E — but only because
`Electrolyzer_Plugin` runs at 203 and converts the cell to a `Quantity` before
`Stored_Power_Electrolysis_Plugin` sees it at 205. That is an accident of ordering,
not a guard: `Plant design capacity` shows the same accident going the other way —
harmless in Solar Thermal (Production runs first) and fatal in a workflow that puts
`Solar_Thermal_Plugin` before `Production_Plugin`, as `workflow.add` at any position
below 250 will (`scratch/nt2_addall.py`, `Solar_Thermal_Plugin` row).

Nothing checks int-vs-float at the field either. `_check_type` only rejects non-numbers
in numeric fields and `_check_scalar` only rejects numbers in non-numeric fields;
neither compares an integer literal against a `{float}` declaration. So the whole
guard is one alphabetical coin-flip with no backstop.

**The value is never harmed.** Separately from the above, I proved the narrower
claim: across 271 authored `Value` cells and 5 771 hand-written spellings (negatives,
percentages, grouped thousands, exponents, `1.`, `.5`, `007`, `+5`, values with units,
whitespace, non-numbers) `spell_for_field` never changed a number — every rewrite it
made was exactly `f'{text.strip()}.0'` and parsed to the identical float.

---

## Judgement calls, not defects

### J1 — `step.effect` is unavailable for three quarters of all steps, silently

`scratch/nt1_effect.py`

`op_step_effect` returns `measurable: False, reason: 'the step is not written in the
file'` for any step that comes from the merged `Defaults_TEA.md` rather than the user's
own `Workflow` table, and `effectBand` renders nothing at all when `measurable` is
false — the reason is never shown.

| pathway | steps | measurable |
|---|---|---|
| PV + Electrolysis | 17 | 8 |
| Solar Thermal | 10 | 1 |
| Photoelectrochemical | 13 | 4 |
| Photocatalytic | 13 | 4 |
| PV Electricity | 12 | 3 |
| **A blank plant** | **9** | **0** |

Nothing false is said. But the headline feature never fires once on the starter — the
onboarding path — and on Solar Thermal it fires on one step out of ten. A reader
clicking Discounted Cash Flow and getting no band, then Electrolyzer and getting one,
has no way to know why. Measuring against the *effective* workflow rather than the
authored one would cover all 74.

### J2 — `would_matter_at` recommends the last position that bites, which is arbitrary

`scratch/nt1b_inert.py`

The claim itself is true. I moved every recommended step to its recommended position
and got the promised cost to the last digit, every time. The UI sentence — "Run it
before *X* and the same numbers give *Y*" — is exactly right.

But `_positions_that_bite` (api.py:742-747) keeps `found[-1]` on the theory that
"every earlier slot works, every later slot is dead". For PV+E with
`Reverse_Osmosis_Plugin` dragged to 900, five positions bite and they give **three
different answers**:

``
 203.5  before Battery                     4.2082  BITES
 204.5  before Stored Power Electrolysis   4.2082  BITES
 252.5  before Production                  4.1943  BITES   <- the pathway's own home
 301    before Power Management            4.1943  BITES
 351    before Capital Cost                3.3898  BITES   <- what the app recommends
 400.5+ everything later                   3.3838  .
``

The app names 351 and 3.3898. The step's authored home is 301, which reproduces the
published 4.1943. So the "move it" button steers a reader 19 % away from the
published number with no indication that the choice mattered. The tiebreak has no
engineering meaning; the *first* biting slot, or the modal cost, would at least be
defensible.

Related nuance: when no position bites, the UI says "No other position in this
workflow changes the answer either" — but positions where the file does not run at
all are skipped, not reported. In the case I checked (`Reverse_Osmosis_Plugin` added
to Solar Thermal) three of twelve positions make the file unrunnable and the sentence
still appears. Defensible — an unrunnable file has no answer to change — but it is
not the whole truth.

### J3 — two rough edges in `cell.edit`

* `op_cell_edit` reads `payload.get('text', '')` (api.py:381), so a call that omits
  `text` writes an empty cell and reports success. My first harness run created six
  rows with every cell blank and got no error back.
* `cell.edit` on the `Workflow` table surfaces a raw
  `ModuleNotFoundError: No module named 'pyH2A.Plugins.Audit row'`
  (`scratch/nt2b_rows.py`, part A). It refuses, which is right; the message names the
  import machinery.

---

## What I attacked, and what held

### 1. `step.effect` must never lie — HELD

`scratch/nt1_effect.py`, `nt1b_inert.py`, `nt1c_starter_inert.py`

For every step of all five pathways and the starter (74 steps), I asked the app, then
independently deleted that step's `Workflow` row **from the markdown text** — a path
that shares no code with `step.effect`'s `deepcopy` + `serialize_document` — and ran
the result through `Project.open`.

* 20 measurable steps: every `inert` / `live` / `required` verdict matched the control.
* Every reported `without` cost matched the control to 1e-9.
* 54 steps report "not written in the file"; the control confirms none of them is.
* Every `would_matter_at` promise was checked by actually moving the step there
  (textually) and re-running: the promised cost came back exactly, in all cases.
* The `inert`-everywhere branch was constructed on purpose and verified against a full
  twelve-position sweep.

**0 disagreements.**

### 2. A created row must produce a file real pyH2A accepts — BROKEN (D1), otherwise held

`scratch/nt2_addall.py`, `nt2b_rows.py`

For every one of the 22 installed plugins, added to the starter at a sensible
position via `workflow.add`, with every gap the app reports filled through
`cell.edit(create=True)` using values derived from the plugin's own declared bounds,
types and dimension. Then `project.source` handed to **upstream's own entry point**,
`pyH2A.run_pyH2A.pyH2A(input_file, output_directory)`, on a temp file.

* 13 plugins are not already in the starter's workflow and were added; the other 9 come
  from the merged defaults and `workflow.add` correctly refuses them.
* 6 of the 13 produced a running file. All 6: the app's cost and upstream's
  `Dependent Variables > Levelized cost` agree to 1e-6 (e.g. `PEC_Plugin` at
  280 485 537.859772 on both sides).
* The other 7 fail for real model reasons — a `dict` an earlier step must write, a
  missing table, a bound my synthetic value violates, and D2's integer spelling for
  `Solar_Thermal_Plugin` — and the app's verdict matches upstream's error text
  exactly in every case.
* Repeated over all 5 pathways × every plugin they lack: **45 combinations, zero
  disagreements** between app, `Project.open`, and upstream.
* Remove a step then add it back at the same position, for all 20 authored steps of
  all 5 pathways: the cost returns to the original float, bit for bit.
* The exception is the row-creation path in pattern-declared tables — D1.

### 3. Units — HELD

`scratch/nt34_units_types.py`, `nt8_dashblind.py`

Every `(table, row)` any installed plugin declares — 127 locations, 166 declared unit
fields, 26 distinct dimensions.

* Every dimension maps to a base unit the engine parses back at **exactly** the
  declared dimension. Including the compound ones the last round added:
  `currency / area → USD / m2`, `volume / (length * substance) → m3 / (m * mol)`,
  `1/temperature_diff → 1/delta_K`, `mass / energy → kg / J`.
* No dimension yields `''`, so no field silently gets `-` because the table is short.
* No plugin pair disagrees about a location's dimension.
* Separately: `-` is used on 189 shipped cells and every one of them is declared
  `dimensionless`. Never wrong in a shipped file — which is why the validator's
  blanket skip on `-` (D1) costs nothing to remove.

The one thing that is *not* covered is what `declared_unit` cannot see at all: the
pattern-declared locations, which return `None` and are the subject of D1.

### 4. The float spelling — the value never changes; the decision is wrong (D2)

`scratch/nt34_units_types.py` section 4b

271 authored `Value` cells across all six files, plus 20 hand-written spellings
applied to every row of every table — 5 771 cases in total, covering `-4`, `0`, `007`,
`4.0`, `-0.4%`, `98%`, `5,500`, `1e-3`, `1E6`, `-2.5e-4`, `1.`, `.5`, `  7  `, `+5`,
`1/kg`, `placeholder`.

Every rewrite was exactly `f'{text.strip()}.0'`, and `engine.parse_number` returned
the identical float before and after. **The function never changes a number.** It
sometimes declines to change a spelling it should have changed — that is D2.

### 5. Round trip — HELD

`scratch/nt5_roundtrip.py`

For all five pathways and the starter: open, apply five edits of different kinds —
a scalar, a percentage, a unit, a reference path, and a created row — download
`project.source`, reopen it as an upload, and compare.

* Levelized cost identical in all six (`pv_e` 3.9661295771594953,
  `tea_mass` 7.10826203569858, `thermal` 15.285781825365827,
  `pec` 608.7958467831146, `photocatalytic` 308.13430471478455,
  `pv_e_lcoe` 29.887914577001858 USD/kWh).
* Every displayed field of every step identical: text, unit, path and resolved target,
  live value, post-step value, state, shown bounds, problems.
* Rail identical (excluding `duration_ms`, which is wall time, not a claim).
* Reference problems and the graph's unmet list identical.
* Download → reopen → download again is byte-identical. The file is a fixed point.

---

## Beyond the brief

### 6. Every number the worksheet draws — HELD

`scratch/nt6_displayed.py`

* **The drawn equation.** `renderEquation` puts `multiplier × reference = product` on
  one line. For all 49 path-bearing rows in all six files,
  `parse_number(text) × path.as_requested` equals the value the engine holds after the
  step, to 1e-9. Including the conversion-request cases the app makes a point of:
  `784 × 5 500 kW`, `6 000 × 5.8154637 m3/h` (stored as 50 943 m3/year),
  `0. × 800 000 kWh` (stored as 800 MWh).
* **The shown range.** 571 bounded fields. Converting the displayed bounds back
  through the field's own unit and percent convention returns the plugin's declared
  base-unit bounds every time — affine temperature included.

### 7. Charts and tallies — HELD

`scratch/nt7_figures.py`, `nt10_broken_rail.py`

* **Cost breakdown reconciles.** For all six: the parts sum to the engine's own total
  (largest residual 5.7e-14 on 185.44), the total *is* the headline
  (residual exactly 0), family subtotals sum to the row total, shares sum to 1, and the
  unit `figures` builds (`f'USD/{functional_unit}'`) equals the unit the engine put on
  the levelized cost — `USD/kWh` for PV Electricity included.
* **Sparkline envelopes.** 91 array cells: no drawn envelope escapes its stated extent.
* **Calendars.** 20 full undecimated series, re-derived independently with
  `engine.state_after`: identical arrays element for element, identical unit, identical
  min/max/sum.
* **Rail tally is a partition.** Verified in 13 configurations — the 6 healthy files
  and 7 deliberately broken ones (new row in a currency table, text in a numeric
  field, bare integer on a float-only field, negative power, wrong-dimension units).
  In every case the four buckets are disjoint, sum to the step count, and exactly one
  row claims to have stopped the run. I could not construct a `ran, needing attention`
  case in a shipped pathway — pyH2A itself refuses everything the frame would flag —
  so that bucket is verified by inspection of `renderLegend`'s mutually exclusive
  filters, not by execution.

### 8. The broad sweep — HELD

`scratch/nt9_tamper.py`

Every authored numeric `Value` cell in every file — 233 of them — perturbed by 10 %
through `cell.edit`, then the resulting `project.source` opened independently with
`Project.open`.

* The app's reported cost is **exactly** the cost the engine reaches from the
  downloadable text. Not close: the same float, 233 times.
* `cell.edit`'s `before`/`after` pair — what the UI shows at the moment of the
  change — matches the costs on either side, 233 times.
* The written cell holds exactly what was typed (modulo the documented `.0`), and its
  parsed value is unchanged.
* 215 of 233 moved the cost, so the sweep is not testing dead cells.

### 9. Refused files — HELD

`scratch/nt11_remedy.py`

All three files in pyH2A's own `Example/` folder are refused with a named cause and an
offered remedy. The remedy's label is "open it with pyH2A's defaults merged in" and it
does exactly that: all three parse into a real worksheet with a 12–13 step rail. They
then stop at `Hourly_Irradiation_Plugin` — those files predate `Array azimuth` too —
but the app names all five missing rows in the unmet panel rather than showing a
`KeyError`. The claim made is the claim delivered.

Stripping the merge table from each bundled example and running the offered remedy
restores the published cost to the last digit in all four cases where a remedy is due.
`pv_e_lcoe` declares its own `Functional Unit`, so it still parses and is correctly not
diagnosed.

### 10. Both builds agree — HELD

Native (`http://127.0.0.1:8730/api`) and static/WASM Pyodide
(`http://127.0.0.1:8740/`, driven through its patched `fetch('/api')` seam) return
**identical floats** for all five pathways and the starter:

``
pv_e            4.194302976489664  USD/kg    (advertised 4.1943)
thermal         3.2705814097046098 USD/kg    (advertised 3.2706)
pec           139.41887561917213   USD/kg    (advertised 139.4189)
photocatalytic 185.44329282256817  USD/kg    (advertised 185.4433)
pv_e_lcoe       0.02858462133297927 USD/kWh  (advertised 0.0286)
tea_mass        5.5043552237656455 USD/kg
``

Every front-door reference cost rounds to the engine's own answer, and every
advertised unit equals the unit the engine puts on the levelized cost. The scipy shim
(`Avogadro = 6.02214076e+23`, exact by the 2019 SI redefinition) matches real scipy.
D1 and D2 both reproduce identically in the WASM build.

---

## Files written

| path | what |
|---|---|
| `studio/scratch/nt_common.py` | shared helpers; textual Workflow surgery used as the control |
| `studio/scratch/nt1_effect.py` | invariant 1: every step, every pathway, vs a hand-rolled control |
| `studio/scratch/nt1b_inert.py` | invariant 1: the inert / `would_matter_at` branch, with full position sweeps |
| `studio/scratch/nt1c_starter_inert.py` | invariant 1: the scenario `op_step_effect`'s docstring describes |
| `studio/scratch/nt2_addall.py` | invariant 2: all 22 plugins into the starter, checked against upstream `pyH2A` |
| `studio/scratch/nt2b_rows.py` | invariant 2: rows in every table; 45 plugin×pathway adds; remove-and-re-add |
| `studio/scratch/nt2c_repro_newrow.py` | **D1 reproduction** |
| `studio/scratch/nt34_units_types.py` | invariants 3 and 4 |
| `studio/scratch/nt4_repro_spelling.py` | **D2 reproduction** |
| `studio/scratch/nt5_roundtrip.py` | invariant 5, plus the published-cost check |
| `studio/scratch/nt6_displayed.py` | drawn equations and shown ranges |
| `studio/scratch/nt7_figures.py` | breakdown, envelopes, series, rail partition |
| `studio/scratch/nt8_dashblind.py` | how much legitimate coverage the `-` skip protects (none) |
| `studio/scratch/nt9_tamper.py` | 233-cell perturbation sweep |
| `studio/scratch/nt10_broken_rail.py` | rail partition on runs that stopped |
| `studio/scratch/nt11_remedy.py` | refusal diagnostics and their offered remedy |
| `studio/scratch/nt-defect1-compressor.png` | D1 in the shipped UI |

No source file was modified.
