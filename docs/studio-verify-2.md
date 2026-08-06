# Paper Plant Studio — correctness confirmation sweep (round 2)

**Scope.** Re-run every check in `studio-verify-1.md`'s PASSED list (§1–§25) and re-test
defects 1–13 individually. Read-only: nothing under `studio/src/` or `studio/tests/` was
modified. Harness: `studio/scratch/v2_engine.py` (162 assertions) plus a browser pass over all
65 step views on `http://127.0.0.1:8730` via CDP in a dedicated tab.

``
cd studio && UV_PYTHON=3.12 uv run --with-editable . python scratch/v2_engine.py
# log: studio/scratch/v2_engine.log   data: studio/scratch/v2_engine.json
``

---

## Headline

**Twelve of the thirteen defects are fixed at the root, and nothing in the PASSED list
regressed.** All five pathways still reproduce their published cost bit-for-bit, the
decomposition still reconciles to ≤6e-14, `project.source` is still byte-identical to disk, all
599 rendered field values still match the API verbatim, and 65 step views produced zero
JavaScript errors and zero `undefined`/`NaN`/`[object Object]`. Defects 1, 2, 3, 5, 6, 7, 8, 9,
10, 12 and the reachable half of 13 are genuinely closed — and closed at the cause, not
papered over: `_commit` builds the response before adopting the project, `figures.series`
re-runs to the named step, `Project.visible_to` admits a step's own writes, `start()` asks the
server what it holds.

What is wrong now is **six new defects, four of them introduced by the fixes themselves.** Two
matter:

- **Every calendar on step 202 of both PV pathways is a flat block of uniform minimum ink.**
  The "siblings share one scale" fix takes `Math.max` across candidates without checking their
  units, and the per-year candidate `max` it maxes over is an *annual total*, not an hourly
  value. 4 315 of 4 680 cells at exactly opacity 0.22. The panel shows `Data … 0 … 0.909
  kWh/m2` twelve inches above a scale key reading `0 TO 8.08E+13 KWH/M2`. NEW-1/NEW-2.
- **The `did you mean` fix button breaks the model.** On any path row it writes the corrected
  reference with unit `-`, because `unitGuess()` looks for a `[data-unit]` input that the
  equation renderer never emits. One click turns a −33 % cost drift into
  `ValueError: Dimension mismatch`. This is the app's single best-designed error message
  offering a remedy that is worse than the fault. NEW-4.

And one silently-wrong item that is not new but is now user-facing: **defect 11's raw
`KeyError` text is gone from the toast, but the condition behind it is not.** The seven empty
optional fields on the shipped files are editable boxes that reject every keystroke.

---

## Per-defect verdicts

### 1. Reloading discards every edit — **FIXED**

`studio.js:1338` `start()` now calls `project.state` and only falls back to `openProject('pv_e')`
when the session holds nothing.

Click sequence: `OPEN A PATHWAY` → **Photoelectrochemical** → step `302 Solar Concentrator` →
set `Concentration factor` = `20` → ⌘R.

| | before | after |
|---|---|---|
| `sessionStorage['paperplant.session']` | `tmsgjkcypv178ii` | `tmsgjkcypv178ii` |
| project | Photoelectrochemical | **Photoelectrochemical** |
| masthead cost | `344.0475 USD/kg` | **`344.0475 USD/kg`** |
| `project.state` cost | 344.0475078756836 | **344.0475078756836** |
| `dirty` | true | **true** |
| toast | — | `restored Photoelectrochemical with your edits` |

*Minor:* the reload restores the project but reopens `100 Time`, not the step you were on.
`start()` picks `error || problems || rail[0]`; the open step is not part of session state.

### 2. `reference.check` reports 10 false dangling references per PEC / Photocatalytic — **FIXED**

`Project.visible_to()` now unions `available_at(step)` with `step.wrote`, and
`api.op_reference_check` calls it.

``
cd studio && UV_PYTHON=3.12 uv run --with-editable . python -c "
from pyh2a_studio import api
api.dispatch('project.open',{'example':'pec','session':'s'})
print(api.SESSIONS['s'].check_references('Capital_Cost_Plugin'))"
``

Per-step verdicts across all five files: **zero `dangling`, zero `unreached`.** The six named
Capital-Cost self-references (`… Gas Processing > Summed total`, `… Control System > Summed
total`, `Direct Capital Cost > Summed group total` ×4) are clean on both `pec` and
`photocatalytic`. The only residue at `Capital_Cost_Plugin` on `pec` is one honest `early`
(`Other Fixed Operating Costs > G&A` → `Fixed Operating Costs > Labor cost`, written at step
600) — correct.

`reference.check` driven as a UI would, on all 116 path cells of all five files scoped to their
owning step: `{'ok': 61, 'malformed': 55}`, **no `dangling`.** The 55 `malformed` are cells
whose Path text is the literal string `None`, which the frame correctly treats as "no
reference" — see *Minor observations*.

### 3. After a run failure the masthead invents reference problems — **FIXED**

`Project.reachable()` now takes the deepest snapshot plus every step's writes, and
`Project._verdict()` softens a `dangling` verdict to `unreached` while the run is failed.

``
cd studio && UV_PYTHON=3.12 uv run --with-editable . python -c "
from pyh2a_studio import api
api.dispatch('project.open',{'example':'pv_e','session':'s'})
print('healthy:', len(api.SESSIONS['s'].check_references()))
api.dispatch('cell.edit',{'table':'Photovoltaic','row':'Nominal power','column':'Value','text':'-1','session':'s'})
for x in api.SESSIONS['s'].check_references(): print(' ', x['table'],'>',x['row'],'|',x['status'],'|',x['message'])"
``

``
healthy: 0
after break, 3 problems, every one 'unreached':
  Technical Operating Parameters and Specifications > Design output by year | unreached
  Direct Capital Costs - Reverse Osmosis > Reverse osmosis CAPEX          | unreached
  Planned Replacement > Electrolyzer stack replacement                    | unreached
      "the run stopped at Photovoltaic_Plugin (position 202), so this could not be
       checked — fix that step first"
``

`Irradiation Used > Data` — the cell verify-1 caught being accused while
`Hourly_Irradiation_Plugin` demonstrably wrote it — is **no longer reported at all**
(`('Hourly Irradiation','Horizontal single axis tracking','Value') in wrote → True`). No
`dangling` verdict survives a failure, on the masthead or at any step. Control: a genuinely
misspelled reference still reports `dangling` with a `near` list.

### 4. Optional fields render with the placeholder "required" — **FIXED**

All 7 fields in `state: 'missing'` on the shipped files now render `placeholder=""`, no
`.waiting` class, and `optional` in the meta line. Measured across all 65 views:
`requiredPlaceholder: 0`.

| pathway | step | cell | placeholder | `.waiting` | meta |
|---|---|---|---|---|---|
| pv_e | 201 | `Irradiance Area Parameters > Module tilt` | `""` | no | `angle · range 0 … 1.57 · optional` |
| pv_e | 300 | `… > Plant design capacity` | `""` | no | `mass/time · range ≥ 0 · optional` |
| thermal / pec / photocatalytic | 300 | `… > Design output by year` | `""` | no | `mass · range ≥ 0 · optional` |
| pv_e_lcoe | 201 | `… > Module tilt` | `""` | no | `angle · range 0 … 1.57 · optional` |
| pv_e_lcoe | 300 | `… > Plant design capacity` | `""` | no | `energy/time · range ≥ 0 · optional` |

**But those seven boxes cannot accept input** — see NEW-3.

### 5. Broken hourly-calendar buttons on PV + Electrolysis — **FIXED**

`figures.series` now re-runs the workflow to the named step (`engine.state_after`) instead of
reading `result.inp`, and `hourly_candidates` offers from the same place.

**Every one of the 20 candidates offered on every step of every pathway fetches cleanly** —
8 760 finite points, `length == 8760`, candidate metadata (`years`, `max`) agreeing with the
served series. Zero errors, zero non-finite values.

Browser: step `202 Photovoltaic` offers `Data`, `Available energy (hourly) 20y`,
`PV hourly power generation 20y`; each of the three activates, takes the `on` class, and
redraws the figure. Step `203 Electrolyzer`'s single button `Available energy (hourly) 20y`
draws (2 493 marks, median opacity 0.534). No HTTP 400, no `holds no array` toast.

### 6. The calendar draws end-of-run state and never says which year — **FIXED**

**(a) Provenance.** `series` reads the named step's own state, and it is observable:

``
step 202 Photovoltaic   Power Generation > Available energy (hourly)  sum 74 041 993 473 033.34
step 203 Electrolyzer   same cell                                     sum  6 143 413 295 318.36
end of run (what the old code read)                                   int 0
``

Both match `engine.state_after(project.inp, step)` element-for-element (n, sum, max, years),
and the payload echoes `'step'`. The old code would have raised `holds no array` for both.

**(b) Year.** A year picker is rendered for any `years > 1` cell (20 buttons on `pv_e` 202), the
caption states it (`Power Generation › PV hourly power generation · year 0`), the `on` class
follows, and the data changes: `1 Jan · 1.43e+11 J` at year 0 vs `1.30e+11 J` at year 19.
Out-of-range echo fixed: `year=25` returns `{'year': 19, 'years': 20}` — the year actually drawn.

*The year picker works; the ink ramp it feeds does not — see NEW-1.*

### 7. No way to remove / move a step, or see / edit / save the file — **FIXED**

Masthead now carries a `source` button; the step head carries `remove step`
(`title="take this step out of the workflow; its tables stay in the file"`). `studio.js` calls
`project.source`, `source.replace`, `workflow.remove`, `workflow.move`.

Click sequence, all from the UI:

1. rail `+ 202.5` → chooser → `Solar Concentrator` → step lands at `202.5`, badge `5`, masthead
   `no cost — the run stopped`, flag `Solar Concentrator failed`.
2. `remove step` → masthead `4.2624 USD/kg`, 17 steps, no `Solar Concentrator` in the rail,
   `project.state.cost.value == 4.2623654120352565` — **bit-for-bit the pre-add value.**
3. `SOURCE` → drawer shows `173 lines · PV_E_Base.md`, 6 864 chars of markdown, buttons
   `download .md` / `apply` / `close`.
4. Edit `Nominal power | 5,500` → `6000` in the drawer, `apply` → masthead `4.2624`, toast
   `file applied`, API `4.2623654120352565`.
5. `download .md` → Blob `text/markdown`, filename `PV_Electrolysis.md`, content
   byte-identical to the drawer text including the edit.

### 8. A failed op can leave the session mutated and permanently unusable — **FIXED**

`api._commit()` builds `_summary` + `frame.rail` + `graph.build` **before** `_store`, so a
project that cannot be rendered is never adopted.

``
cd studio && UV_PYTHON=3.12 uv run --with-editable . python -c "
from pyh2a_studio import api; import re
api.dispatch('project.open', {'example':'pv_e','session':'s'})
md = api.dispatch('project.source',{'session':'s'})['markdown']
bad = re.sub(r'^Photovoltaic_Plugin','Photovoltaik_Plugin', md, count=1, flags=re.M)
print(api.dispatch('source.replace',{'markdown':bad,'session':'s'}))
print(api.dispatch('project.state',{'session':'s'}))"
``

``
source.replace -> {'error': "ModuleNotFoundError: No module named '…Photovoltaik_Plugin'"}
project.state  -> ok, cost 4.194302976489664
graph          -> ok, 17 nodes
step           -> ok
project.source -> the typo is NOT in the session's markdown
cell.edit      -> still works (4.2623654120352565)
``

Also checked: a `source.replace` that will not *parse* is retained deliberately with a readable
message (`line 2: unexpected content outside any table …`) and `project.state` still renders —
a different, correct failure class. `workflow.add` with a bogus plugin returns
`ValueError: no plugin named Nope_Plugin is installed`, leaves the cost unchanged, and does not
write the row.

### 9. The chooser shows a hardcoded constant styled like the live cost — **FIXED**

`examples.py`'s pinned constants now carry full published precision and the chooser renders
them raw, labelled `published`:

| pathway | chooser | masthead | computed |
|---|---|---|---|
| PV + Electrolysis | 4.1943 | 4.1943 | 4.194302976489664 |
| Solar Thermal | 3.2706 | 3.2706 | 3.2705814097046098 |
| Photoelectrochemical | **139.4189** | **139.4189** | 139.41887561917213 |
| Photocatalytic | **185.4433** | **185.4433** | 185.44329282256817 |
| PV Electricity | **0.0286** | **0.0286** | 0.02858462133297927 |

The headline is 4 decimal places everywhere: one distinct value per pathway across all 65 step
views. Opening a pathway no longer changes the number you just clicked.

### 10. Engine bookkeeping columns leak into the bindable scope — **FIXED**

Every scope group of all 65 frames scanned for a column matching
`^(Former|Processed|Comment)`: **zero.** `reference.search` for `former`, `processed`,
`comment`: `total = 0` each. The `Former Cost_Value` / `Former Frequency_Value` rows under
`500 REPLACEMENT` on `pv_e` step 900 are gone.

### 11. Raw Python exception text reaches the toast — **PARTIAL**

`studio.js humanize()` rewrites the shapes a user can provoke. Verified live:

- typing into an empty optional field → `there is no “Module tilt” in this file — add the row
  before writing to it` (was `KeyError: 'Module tilt'`)
- `workflow.add` unknown plugin → `no plugin named Definitely_Not_A_Plugin is installed`
  (raised as `ValueError` by the API now, not `ModuleNotFoundError`)

The API still emits raw exception text, which is fine for a log but means anything `humanize()`
does not recognise still surfaces verbatim:

``
cell.edit unknown row   -> {'error': "KeyError: 'Module tiltt'"}
cell.edit unknown table -> {'error': "KeyError: 'Nope Table'"}
cell.edit Workflow>Position='zzz' -> {'error': "TypeError: '<' not supported between
                                      instances of 'str' and 'int'"}
``

The first two are caught by `humanize`'s `KeyError` pattern. The `TypeError` is not, and
`humanize` would render it as `'<' not supported between instances of 'str' and 'int'` — no
verb, no advice. Not reachable from the UI today (no editable Workflow field), and the session
survives it.

### 12. `PV Electricity`'s masthead title is a raw filename — **FIXED**

`PV_E_Electricity_Production.md` → `PV Electricity`. All five: `PV + Electrolysis`,
`Solar Thermal`, `Photoelectrochemical`, `Photocatalytic`, `PV Electricity`. None ends in `.md`.
The display names are also longer and more informative than verify-1's `PV + E` / `PEC` / `PC`.

### 13. Minor / latent — **FIXED (all four items)**

- **Global keydown handler on non-Element targets.** `studio.js:1302` now takes `event.target`
  into a local and guards it. `document.dispatchEvent(new KeyboardEvent('keydown',{key:'/'}))`
  → no throw. `/`, `j`, `k` and `Escape` all still work (§22 below).
- **Negative zero in the decomposition.** `pv_e` `End of life` renders `-2.89e-5  ~0%`, not
  `-0.0%`. Scanned all five decompositions for `|share| < 5e-5 && share != 0`: one component,
  rendered `~0%`.
- **Unsupported prose in the annual-costs figure.** The upstream-typo claim is gone. The
  caption now reads: *"Year 20 is the largest single spend at 20.3 M USD — 98% of it is
  Variable operating. The axis is linear and spans four orders of magnitude, so every other
  year is drawn at a floor rather than to scale; hover any year for its figures."* Every clause
  is checkable and true.
- **`workflow.add` with an unknown plugin** → `ValueError: no plugin named X is installed`.
- **Plugin chooser printing module names as descriptions** → the four docstring-less plugins now
  read `Reverse Osmosis — no description in the plugin`, etc.

---

## PASSED — restated, all re-exercised

Nothing below is assumed; each was run again this round.

| pathway | published | computed | `project.source` | direct `engine.run` | steps |
|---|---|---|---|---|---|
| pv_e | 4.1943 | 4.194302976489664 | byte-identical to `PV_E_Base.md` | identical | 17 |
| thermal | 3.2706 | 3.2705814097046098 | byte-identical to `Thermal_Base.md` | identical | 10 |
| pec | 139.4189 | 139.41887561917213 | byte-identical to `PEC_Base.md` | identical | 13 |
| photocatalytic | 185.4433 | 185.44329282256817 | byte-identical to `Photocatalytic_Base.md` | identical | 13 |
| pv_e_lcoe | 0.0286 | 0.02858462133297927 | byte-identical to `PV_E_Electricity_Production.md` | identical | 12 |

1. **Published cost matches** — all five to 4 decimals; units `USD/kg` ×4, `USD/kWh` ×1.
2. **`project.source` round-trips exactly** — the returned markdown is byte-identical to the
   file on disk (compared against every `.md` in `EXAMPLES_DIR`), and re-opening it returns the
   same float.
3. **Independent cross-check passes** — `engine.run(grammar.engine_dict(text))` outside the API
   returns the same float for all five.
4. **Every step frame is JSON-safe and complete** — 65 frames, all `json.dumps`-clean, no NaN,
   no Inf, no non-string dict key. Every step op returned. *One new wart:* a Python `tuple`
   ships in the payload (NEW-6).
5. **Zero field-level validation problems on shipped files** — 65 frames × 599 fields,
   `problems: []` on every field; every rail row `problems: 0`; masthead `problems: 0`;
   `warnings: []`. The false-positive gate holds.
6. **The cost decomposition reconciles:**

   | pathway | residual | headline_residual | Σfamilies − total | Σ shares | rows / families |
   |---|---|---|---|---|---|
   | pv_e | 8.88e-16 | 0.0 | 8.88e-16 | 1.0000000000000002 | 11 / 4 |
   | thermal | -4.44e-16 | 0.0 | -4.44e-16 | 0.9999999999999999 | 11 / 4 |
   | pec | 0.0 | 0.0 | 0.0 | 1.0 | 11 / 4 |
   | photocatalytic | 5.68e-14 | 0.0 | 5.68e-14 | 1.0000000000000002 | 11 / 4 |
   | pv_e_lcoe | 3.47e-18 | 0.0 | 3.47e-18 | 1.0000000000000002 | 11 / 4 |

   `total == headline == masthead cost` as a float on all five, and the figure's unit tracks
   the functional unit (`USD/kWh` for `pv_e_lcoe`).
7. **Every reference in every shipped file resolves** — `check_references()` returns `[]` for
   all five, and the step-scoped variant now agrees (defect 2).
8. **Zero JavaScript errors** — `pageerror`, `console.error`/`warning`, `requestfailed` and
   every HTTP ≥ 400 across all 65 step views in all five pathways: **empty.** (The only HTTP
   400 seen all round was the one I provoked by typing into an empty optional field — NEW-3.)
9. **No `undefined` / `NaN` / `[object Object]` / stray `null`** — full text-node walk plus every
   `<input>`/`<textarea>` value plus every `title` attribute on all 65 views: **zero hits.**
10. **No empty panels** — `#needs`, `#scope-body`, `#rail-list` non-empty on all 65 views.
11. **Every rendered number matches the API** — 599 fields; every `input.cell` / `input.unit` /
    `input[data-path]` value verbatim identical to `field.text` / `unit.text` / `path.text`.
    Field counts match the frame exactly on all 65 views (136 + 86 + 141 + 149 + 87 = 599, the
    same 599 the API reports). Scope subtitle counts match the frame's own scope size.
12. **The masthead cost matched the API on all 65 views** — exactly one distinct rendered value
    per pathway, always the API's value at 4 decimals.
13. **The product equations reconcile, and now read as equations.** One line, operator between
    operands, resolved multiplicand shown, multiplier unit stated as a rate:
    `[784] per kW × {Electrolyzer > Nominal power > Value, kW} 5 500 kW = 4 312 000 USD`;
    `[818] per kW × 8 250 kW = 6 748 500 USD`; `[6000] per m3/h × 5.815 m3/h = 34 893 USD`;
    `[0.] per kWh × 800 000 kWh = 0 USD`. All reconcile. (Step 202's `Nominal power` is the one
    exception — NEW-5.)
14. **The DCF figures match the API and now state their basis.** `where the kg price comes from
    — discounted, per kg · 11 components in 4 families`, footer `the 11 components sum to
    4.1943, and that is the headline — residual 8.9e-16`. `when the money is spent — nominal,
    not discounted · 34.2 M USD over 21 years`. API: total 4.194302976489664, residual 8.88e-16,
    lifetime 34 221 356.20, peak 20 305 763.33, peak year 20. Every on-screen figure matches.
15. **An edit that moves the cost works.** `pv_e` step 203 `Nominal power` `5,500` → `6000`:
    masthead `4.1943 → 4.2624`, toast `4.1943 → 4.2624  (+1.62%)`, API 4.2623654120352565.
    Restoring `5,500` returns **exactly** 4.194302976489664 and toast `4.2624 → 4.1943 (-1.60%)`.
16. **An edit that breaks the model behaves.** Same cell → `banana`: masthead `no cost — the run
    stopped`, toast `the model stopped at Photovoltaic`, flag `Photovoltaic failed`, rail marks
    `Photovoltaic:error` and all 13 downstream `skipped`, and the field reports
    `not a number — "banana" is not a number, and this field is declared float or int`. Step
    203's head reads `3 tables · 7 rows / never reached` — no "7 to enter" reclassification, no
    blank `Years` box (D11's symptoms are gone). *But the field is now read-only — NEW-3.*
17. **A dangling reference that does not stop the run is caught correctly.** Setting
    `Direct Capital Costs - Electrolyzer > Electrolyzer CAPEX > Path` to
    `{Electrolyzer > Nominal powerr > Value, kW}`: cost `4.1943 → 2.7985 (-33.28%)`, flag
    `1 to fix`, rail badge `400 Capital Cost 1`, field
    `path dangling — nothing writes Electrolyzer > Nominal powerr > Value; the engine would
    silently use 1 instead`, with `did you mean Nominal power …`. *The diagnosis is still the app
    at its best. The fix button is now broken — NEW-4.*
18. **Adding a plugin via `+` works.** 18 insertion points for 17 steps, each labelled with its
    position (`add a step at position 202.5`), catalogue ranked, added step lands at 202.5 with
    its unmet inputs named.
19. **Removing it returns the cost exactly.** `4.194302976489664`, bit-for-bit — and now from
    the UI. Also verified for **all five** catalogue plugins `pv_e` does not already run
    (`Solar_Concentrator`, `Catalyst_Separation`, `PEC`, `Photocatalytic`, `Solar_Thermal`):
    every add/remove pair restores the cost exactly and leaves the session usable.
    `workflow.move Battery_Plugin 204 → 204.5 → 204` also round-trips exactly.
20. **The graph is consistent.** All five: `nodes == rail`, every edge endpoint resolves,
    `unmet == []` on shipped files, `insertion_points == steps + 1`, JSON-clean.
21. **Edge lighting and the flow readout are right.** Hovering `400 Capital Cost` on `pv_e`
    lights 4 of 71 edge elements and reports `6 values in from 3 steps · 5 values out to 1 step`.
22. **Keybindings work.** `/` → `#find` focused; `j` `Hourly Irradiation → Photovoltaic`;
    `k` back; `Escape` closes the chooser. A `keydown` targeting `document` no longer throws.
23. **No clipping, overlap or horizontal overflow** —
    `documentElement.scrollWidth == clientWidth` on all 65 views at 1680×1050.
24. **The hourly calendars fetch cleanly and the working ones work.** All 20 candidates serve
    8 760 finite points; the extent printed on screen matches the array; the UTC→solar-noon
    rotation is derived from the data and printed (`the axis is rotated -8 h`). The calendar is
    now 300 px tall (was 128), carries **365 per-day `<title>` tooltips** (was 0), a scale key,
    a year picker, and a stated shared scale. Step 201's three tracking modes share one correct
    scale (`0 to 952.5 Wh/m2`) with a healthy ink distribution (median 0.588–0.774, 9 of 4 680
    cells at the floor) — D8's normalisation problem is genuinely solved for commensurable
    siblings. *For incommensurable ones it is catastrophically wrong — NEW-1/NEW-2.*
25. **`series` refuses to lie about arrays it cannot serve** — still returns `None` rather than
    fabricating, and `hourly_candidates` no longer offers what it cannot serve.

Additionally re-verified this round, not in the original list:

- **785 editable inputs across 65 views, every one with an `aria-label`.** Zero missing.
- **The annual chart has no zero-height bars.** 43 data bars, minimum height 1.2 px (was 20 of
  43 at exactly 0), plus **21 full-height `fill="transparent"` hover targets**, one per year,
  each with a per-year summary tooltip (`year 1 — Variable operating 1.84 k · Fixed operating
  306 k`). 64 rects, 64 `<title>`s.
- **Scope search finds units and the current step's own outputs.** `kW` → 7, `USD` → 40,
  `Wh/m2` → 4, `deg` → 3, `m2` → 10 (all were 0). `tracking` from step **201** → 6 matches (was
  0); `Levelized` from step **900** → 2 matches (was 0).
- **The invisible-but-clickable `USE` buttons are safe and honestly labelled.** 76 of them, now
  `copy` with `aria-label="copy this reference"`, `opacity: 0` **and `pointer-events: none`** —
  a stray click can no longer fire one.
- **The rail is one tab stop.** Exactly one `.step` carries `tabindex="0"` (the current one);
  every other step and all 18 `+` buttons carry `-1`.
- **A focus ring is designed and paints** on buttons (`2px solid sodium`) and rail steps
  (`2px solid prussian`) under `:focus-visible`. *Not on text inputs — NEW-6b.*

---

## NEW defects

### NEW-1. Every 20-year hourly calendar is drawn against its *annual total*, so it renders as a flat block

`figures.hourly_candidates` publishes `max` for a per-year cell from `record['max']`, which for
a `form: 'years'` record is the maximum of `per_year` — the maximum **annual total**, not the
maximum hourly value. `studio.js` hands that to `calendar()` as the ink ceiling
(`figures.js:225`, `ink = 0.22 + 0.78 * (value/peak)**1.3`), so every hour is
`0.22 + 0.78 × (tiny)^1.3 ≈ 0.22`.

``
cd studio && UV_PYTHON=3.12 uv run --with-editable . python -c "
from pyh2a_studio import api
api.dispatch('project.open',{'example':'pv_e','session':'s'})
c = [x for x in api.dispatch('figures',{'step':'Photovoltaic_Plugin','session':'s'})['figures']['hourly']
     if x['row']=='PV hourly power generation'][0]
s = api.dispatch('series',{'step':'Photovoltaic_Plugin','table':c['table'],'row':c['row'],
                           'column':c['column'],'session':'s'})['series']
print('candidate max (used as the ink ceiling):', c['max'])
print('true hourly max of the drawn year     :', s['max'])
print('ratio                                  :', c['max']/s['max'])"
``

``
candidate max (used as the ink ceiling): 74041993473033.34
true hourly max of the drawn year     : 26982457347.047504
ratio                                  : 2744.0
``

Measured on screen (`svg.cal-grid` rect opacities, step `202 Photovoltaic` →
`Available energy (hourly)`):

``
min 0.22   p25 0.22   median 0.22   p75 0.22   p90 0.22   max 1.0
4 315 of 4 680 marks at exactly 0.22
``

Compare step 201, whose candidates are one-year arrays: `median 0.588, 9 of 4 680 at the floor`.

The caption still asserts *"Ink is magnitude."* It is not: it is a constant. Screenshot:
`/tmp/cs2-202-flat.png` (flat) vs `/tmp/cs2-201-good.png` (correct).

### NEW-2. The shared scale is taken across candidates with **different units**, and mislabelled

`studio.js:634-635`:

``js
const extents = candidates.map((entry) => entry.max).filter((entry) => entry);
const shared = extents.length > 1 ? Math.max(...extents) : null;
``

No unit check. Step `202 Photovoltaic` offers `Irradiation Used › Data` in **kWh/m²**
(max 0.9085) beside two **J** series at 7.40e13, so the `Data` calendar is ceilinged at
7.40e13 — a factor of **8.15e13** — and the scale key prints the Joule magnitude with the
kWh/m² label:

**Repro:** open `202 Photovoltaic`, click `Data`. Read the scale key under the calendar, then
read `IRRADIATION USED › Data PROCESSED` in the same panel 400 px above it.

``
scale key      : "hour of day, local solar time   0 to 8.08e+13 kWh/m2"
same panel says: "Data PROCESSED   0 … 0.909 kWh/m2"
opacity        : 4 315 of 4 680 marks at exactly 0.22 — a solid flat block
``

Two numbers for the same quantity, 10¹⁴ apart, in one viewport. Full inventory — **6 of the 20
offered calendars are flat**, all of them on step 202 of the two PV pathways:

| pathway | step | series | unit | ink ceiling | true hourly max | ratio |
|---|---|---|---|---|---|---|
| pv_e | 202 | Data | kWh/m2 | 7.404e13 | 0.9085 | 8.15e13 |
| pv_e | 202 | Available energy (hourly) | J | 7.404e13 | 2.698e10 | 2 744 |
| pv_e | 202 | PV hourly power generation | J | 7.404e13 | 2.698e10 | 2 744 |
| pv_e_lcoe | 202 | Data | kWh/m2 | 7.629e13 | 0.9085 | 8.40e13 |
| pv_e_lcoe | 202 | Available energy (hourly) | J | 7.629e13 | 2.780e10 | 2 744 |
| pv_e_lcoe | 202 | PV hourly power generation | J | 7.629e13 | 2.780e10 | 2 744 |

`pv_e` step 203 escapes only because it offers a single candidate, so `shared` is `null` and
`peak` falls back to `series.max`.

### NEW-3. Seven empty optional fields on the shipped files are editable boxes that reject every keystroke

`studio.js commit()` never sends `create`, and `op_cell_edit` defaults it false, so
`grammar.set_cell` raises on a row the file does not carry. The plugin declares the input, the
frame emits a field for it, the client renders an editable box — and the box cannot be used.

**Repro:** open **PV + Electrolysis** → step `201 Hourly Irradiation` → click field 01
`Module tilt` → type `0.3` → Tab.

``
HTTP 400 on /api  +  console error
red toast: “there is no “Module tilt” in this file — add the row before writing to it”
the box still displays 0.3          <- looks accepted
project.source: no “Module tilt” row  <- was not written
``

The value clears on the next re-render, so a user who types and navigates away sees no trace of
the loss. The advice names no way to add a row: there is no "add value" control anywhere on the
field, and `op_cell_edit` already supports `create` ("The UI asks for it explicitly when adding
a value" — it does not).

Affects the same 7 cells listed under defect 4, i.e. `Plant design capacity` /
`Design output by year` on step 300 of **all five** pathways. These are the alternative-input
pairs: the file supplies one and the app offers you the other, then refuses it.

Headless:

``
cd studio && UV_PYTHON=3.12 uv run --with-editable . python -c "
from pyh2a_studio import api
api.dispatch('project.open',{'example':'pec','session':'s'})
print(api.dispatch('cell.edit',{'table':'Technical Operating Parameters and Specifications',
  'row':'Design output by year','column':'Value','text':'5','session':'s'}))"
# -> {'error': "KeyError: 'Design output by year'", 'op': 'cell.edit'}
``

*Related, same seven cells:* `Module tilt`'s meta reads `angle · range 0 … 1.57` — radians,
because the empty row has no `Unit` cell to convert from — directly beside its sibling
`Array azimuth` reading `angle · range 0 … 180`. Two angle fields in one table with ranges
80× apart and no unit stated on the empty one. Moot while the box cannot be typed into, but it
will surface the moment NEW-3 is fixed.

### NEW-4. The `did you mean` fix button breaks the model on every path row

`studio.js:911` builds the corrected reference as
`{${table} > ${row} > ${column}, ${unitGuess(field)}}`, and `unitGuess` (line 928) reads
`field.querySelector('[data-unit]')`, falling back to `'-'`. The equation renderer
(`renderField`'s `eq` branch, line 566) **emits no `[data-unit]` input at all** — only
`input.cell.mult` and `input[data-path]`. So for every path row, the fix writes unit `-`,
discarding the unit the user's own broken reference already carried.

**Repro:** open **PV + Electrolysis** → `400 Capital Cost` → set
`Direct Capital Costs - Electrolyzer > Electrolyzer CAPEX`'s path input to
`{Electrolyzer > Nominal powerr > Value, kW}` → the field reports the dangling reference
correctly (cost `4.1943 → 2.7985`, flag `1 to fix`) → click the `Nominal power` fix button.

| | before the fix | after the fix |
|---|---|---|
| path in the file | `{Electrolyzer > Nominal powerr > Value, kW}` | **`{Electrolyzer > Nominal power > Value, -}`** |
| cost | 2.7985 USD/kg | **`no cost — the run stopped`** |
| flag | `1 to fix` | **`Capital Cost failed`** |
| step banner | — | `this step raised ValueError Dimension mismatch: original dimension 'power', but requested dimension 'dimensionless' when mapping '-'` |
| `problems` | 1 | **0** — the app now reports nothing to fix while the run is dead |

The fix button *does* work on a value cell whose field has a `Unit` column: breaking
`Irradiation Used > Data` on step 202 and clicking its fix restores `4.1943` correctly. It is
specifically the equation/path rows — every one of them — that get `-`. The right unit is
sitting in the reference the user typed, and in the target cell's own scope record.

*Also on that panel:* the five fix buttons are labelled with `path[1]` only, so two suggestions
pointing at different columns of the same row render as two identical buttons
(`Horizontal single axis tracking` twice, on the `Data` field).

### NEW-5. Step 202's equation prints the literal word `unresolved` where the multiplicand belongs

D3(c) reported the resolved multiplicand missing on step 202. It is now present as the word
`unresolved`:

**Repro:** `202 Photovoltaic`, first field of `PHOTOVOLTAIC`.

``
01  Nominal power    [ 1.5 ]  ×  unresolved  =  8 250 kW
``

`Electrolyzer > Nominal power` is written at step 203, so it genuinely is not in step 202's
scope — but the engine plainly resolved it, and the product on the same line proves the value
(8 250 / 1.5 = 5 500 kW). The row asserts an equation the reader cannot check, and the
`per`/rate chip that the other equation rows carry is absent here too. On step 400 the same
widget renders `[784] per kW × {…} 5 500 kW = 4 312 000 USD` correctly. One widget, two
structures — still.

### NEW-6. Two smaller regressions

**(a) A `tuple` ships in the step-frame payload.** `frame._scope_group` puts a sort key into
every scope group (`'sort': (0, distance)` / `(2, 0)`, `frame.py:876,886`), used once by
`groups.sort()` at line 840 and then serialized to the client, which never reads it. Present in
every scope group of all 65 frames. It survives `json.dumps` as an array, so nothing breaks —
but verify-1's §4 checked for exactly this and found none, so it is new. Strip it after sorting.

**(b) The designed focus ring is suppressed on every text input in the app.**
`studio.css:451` `:focus-visible { outline: 2px solid var(--prussian); outline-offset: 2px }`
is out-specified by `studio.css:443` `input.cell:focus, input.unit:focus { outline: none }`
(0-2-1 beats 0-1-0), and by `#find:focus { outline: none }` at line 685.

``
measured after a real Tab, matches :focus-visible = true
#open-button          outline: solid 2px rgb(231,183,60)   <- ring paints
#rail-list .step      outline: solid 2px rgb(36,54,91)     <- ring paints
#needs input.cell     outline: NONE 3px                    <- suppressed
#find                 outline: NONE 3px                    <- suppressed
``

What remains on the 785 editable inputs is `border-color: #24365B` plus
`box-shadow: 0 0 0 2px rgba(36,54,91,0.12)` — a 12 %-alpha halo. The border change is a real
signal, but the ring the CSS was written to provide never paints where it is needed most.

**(c) Arrow-key traversal of the rail works exactly once, then focus is lost.**
`stepNode`'s `ArrowDown`/`ArrowUp` handler does `next.focus(); openStep(next.dataset.name)`, and
`openStep` → `renderRail()` → `list.innerHTML = ''`, which destroys the element that was just
focused.

**Repro:** focus the rail's current step, press ArrowDown three times.

``
start          active=Time_Plugin        current=Time_Plugin
after 1st ↓    active=BODY               current=Inflation_Plugin   tabindex0=Inflation_Plugin
after 2nd ↓    active=BODY               current=Inflation_Plugin
after 3rd ↓    active=BODY               current=Inflation_Plugin
``

The `tabindex="0"` bookkeeping is correct — it follows the current step — so the rail is
genuinely one tab stop. It is only the focus that is dropped, and re-Tabbing into the rail
restores it. (Measured with synthetic `KeyboardEvent` dispatch on the focused element; CDP
`Input.dispatchKeyEvent` does not reach an unfocused tab, as verify-1 also found.)

---

## Minor observations — checked, not defects

Recorded so nobody spends a day on them.

- **`reference.check` calls the literal string `None` `malformed`.** 55 of the 116 path cells on
  the shipped files carry `None` in their `Path` column. `refs.NO_PATH` correctly treats that as
  "no reference" and the frame raises no problem, so nothing is on screen — but the two
  validators disagree about the same text, which is the same shape as defect 2, one notch
  quieter. A live path editor would say `a reference must be wrapped in braces` about a cell
  the frame calls fine.
- **`cell.edit` stores before it renders.** `op_cell_edit` calls `_store(payload, updated)` at
  line 222 and `frame.rail(updated)` at line 226 — the ordering `_commit` was rewritten to
  avoid. I could not reach a poisoning through it: `opened.edit()` re-parses and re-runs first,
  so anything that would kill `frame.rail` raises before the store. `cell.edit` on
  `Workflow > Position = 'zzz'` returns a `TypeError` and leaves the session at
  4.194302976489664 with 17 steps. Worth aligning for symmetry, not urgent.
- **After an edit the serialized document gains one line** (173 → 174) because
  `grammar.serialize_document` normalises the trailing newline. The cost round-trips exactly and
  the *unedited* source is byte-identical to disk, so this is cosmetic.
- **The masthead flag button keeps stale `textContent` when hidden.** After a successful
  `remove step` the button reads `Solar Concentrator failed` but `hidden === true` and
  `offsetParent === null`. Not visible; `renderMasthead` sets `hidden` before it would set text.
- **`series` will serve a 21-element array** (`Time > Years`), which is right — it is a real
  array — and `hourly_candidates` correctly declines to offer it as a calendar (8 760 only).
- **The `pending`/`later` split explains the scope-search count difference.** `reference.search`
  for `USD` reports 47 hits against `reachable()`; the panel renders 40 `.cell-row`s because
  `later` cells are listed separately. Both are right.
- **The field-vs-panel percent split from D1 is only half closed.** The declared *range* is now
  in the field's terms (`22%` / `range 0% … 100%`; `180 deg` / `range 0 … 180`;
  `-0.4%` / `range -50% … 50%`) — that part is genuinely fixed and I could find no field
  displaying a value outside its own shown range except the temperature cell below. But the dark
  `what this step made` panel on the same screen still prints the fraction: step 202 shows
  `Efficiency 22%` in the field and `Efficiency PROCESSED 0.22` in the panel,
  `Power loss per year 0.5%` vs `0.005`. Design's call, not a correctness fault — the panel is
  faithful to the engine — but it is the same number twice, differently, in one viewport.
- **`Nominal operating temperature`'s shown range is nonsense, and inverted.** Declared bounds
  `[250, 500]` K, authored unit `degC`; `frame._display_factor` derives a *multiplicative*
  factor via `engine.convert(1.0, base, unit)`, which for an affine unit returns `-272.15`, so
  the range renders `range -68 038 … -136 075` beside a field reading `45`. On screen on all
  four PV/PEC/PC pathways. The correct conversion is affine (`250 K → -23.15 °C`,
  `500 K → 226.85 °C`); only `degC` is affected among the units the shipped files use
  (`deg`→57.296, `kW`→0.001, `1/delta_degC`→1.0 are all genuinely multiplicative). I am listing
  this here rather than as a NEW defect only because it is the same finding the design pass
  owns as D1; it is a real, visible, silently-wrong number and it should be fixed.

  ``
  cd studio && UV_PYTHON=3.12 uv run --with-editable . python -c "
  from pyh2a_studio.core import engine
  print(engine.convert(1.0, engine.base_unit('degC'), 'degC'))"   # -> -272.15
  ``
