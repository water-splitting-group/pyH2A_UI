# Paper Plant Studio — correctness sweep

**Scope.** Every number the UI shows must be one the engine computed. Two halves: headless
against `pyh2a_studio.api.dispatch`, and the real UI at `http://127.0.0.1:8730` driven over
CDP. Read-only: nothing under `studio/src/` or `studio/tests/` was modified. Throwaway
harnesses live in `studio/scratch/` (`sweep1.py`, `sweep2.py`, `repro_refcheck.py`,
`repro_series.py`, `repro_series2.py`, `repro_edit.py`, `repro_mutate.py`, `repro_addall.py`).

Mid-sweep the server was restarted with per-tab sessions. Every browser finding below was
re-confirmed after that restart on a clean single-tab session; the transient
`no project open in session "main"` / `Failed to fetch` toasts I saw during the restart
window are **not** defects and are not listed.

---

## Headline

The engine layer is clean. **All five pathways reproduce their published cost bit-for-bit,
the decomposition reconciles to ~1e-14, and 599 rendered field values are verbatim-identical
to what the API returned.** Zero JavaScript errors across 65 step views. I could not find a
single case of the UI displaying an arithmetic result the engine did not produce.

What is wrong is a different class: **the app throws work away and it diagnoses problems that
do not exist.** Defect 1 destroys user work silently on a page reload. Defects 2, 3 and 4 are
false accusations against unmodified reference input — the exact failure the brief calls out.
Defect 7 means a third of the API is unreachable, so an added step cannot be undone.

---

## Defects

### 1. Reloading the page silently discards every edit and resets to PV + Electrolysis

The last line of `studio/src/pyh2a_studio/web/studio.js` is an unconditional
`openProject('pv_e')`. The per-tab session id survives a reload, as its own comment intends —
and then the first thing the client does is overwrite the project that id points at.

Reproduction (browser):
1. Masthead → `OPEN A PATHWAY` → **Photoelectrochemical**. Masthead reads `139.42 USD/kg`.
2. Click step `302 Solar Concentrator`. Set `Concentration factor` = `20`.
   Masthead moves to `344.05 USD/kg`, toast `139.42 → 344.05 (+146.77%)`,
   `project.state` reports `dirty: true`, `name: "PEC"`.
3. Reload (⌘R).

| | expected | actual |
|---|---|---|
| `sessionStorage['paperplant.session']` | `tmsgh7ysnmj71py` | `tmsgh7ysnmj71py` (survives, correct) |
| project | PEC | **PV + E** |
| cost | 344.0475078756836 | **4.194302976489664** |
| dirty | true | **false** |

No warning, no `beforeunload` prompt, no toast. Both the edit *and* the chosen pathway are
gone. Compounded by defect 7: there is no source view, no download and no save, so there is
no way to preserve work before a reload either. `studio.js`'s own header says "State lives on
the server … so a reload never shows something the file cannot reproduce" — technically true,
and useless: a reload shows `pv_e`.

### 2. `reference.check` reports 10 false dangling references per shipped PEC / Photocatalytic file

`frame._compute_fields` validates a reference against `visible | step.wrote`, with an explicit
comment saying that excluding a step's own writes "reports those files as containing six
dangling references." `api.op_reference_check` does exactly that exclusion
(`available = set(opened.available_at(step_name))`, no `step.wrote`), and so does
`Project.check_references(step_name)`.

``
cd studio && UV_PYTHON=3.12 uv run --with-editable . python scratch/repro_refcheck.py
``

``
=== pec  masthead problems = 0   step-scoped problems = 10
  Direct Capital Costs - Installation Costs > Gas processing installation
    path            : {Direct Capital Costs - Gas Processing > Summed total > Value, USD}
    frame problems  : []
    reference.check : {'status': 'dangling', 'message': 'nothing writes Direct Capital Costs -
                       Gas Processing > Summed total > Value; the engine would silently use 1
                       instead', ...}
``

Six distinct false verdicts on `pec` (`… Gas Processing > Summed total` ×1,
`… Control System > Summed total` ×1, `Direct Capital Cost > Summed group total` ×4), the same
six on `photocatalytic`, ten problems reported in total per file. `Capital_Cost_Plugin` writes
every one of those cells inside its own step; the frame is right and `reference.check` is
wrong. Full inventory: `studio/scratch/sweep1.json` → `<key>.reference_problems`.

Mitigating: `studio.js` never calls `reference.check`, so this is not on screen today. It is
still a validator that fails its own shipped fixtures, and it is the op a reference-editing
UI would call.

### 3. After any run failure the masthead invents reference problems, including for cells the engine computed

`Project.check_references(None)` checks against `set(self.run.steps[-1].visible)`. When a step
fails, every later step is `skipped` with `visible = {}`, so the check falls back to literals
only (183 cells) instead of the 224 that actually existed at the point of failure.

``
cd studio && UV_PYTHON=3.12 uv run --with-editable . python -c "
from pyh2a_studio import api
api.dispatch('project.open',{'example':'pv_e','session':'s'})
print('healthy problems:', len(api.SESSIONS['s'].check_references()))
api.dispatch('cell.edit',{'table':'Photovoltaic','row':'Nominal power','column':'Value','text':'-1','session':'s'})
for x in api.SESSIONS['s'].check_references(): print(' ', x['table'],'>',x['row'],'|',x['status'])"
``

``
healthy problems: 0
after break, masthead problems = 4
   Irradiation Used > Data > Value                  | dangling
   Technical Operating Parameters … > Design output by year | dangling
   Direct Capital Costs - Reverse Osmosis > … > Path | dangling
   Planned Replacement > Electrolyzer stack replacement > Frequency_Value | dangling
``

The first is flatly wrong. `Irradiation Used > Data > Value` references
`{Hourly Irradiation > Horizontal single axis tracking > Value, kWh/m2}`;
`Hourly_Irradiation_Plugin` ran **before** the failure and demonstrably wrote that cell
(`key in run.step('Hourly_Irradiation_Plugin').wrote → True`,
`key in run.step('Photovoltaic_Plugin').visible → True`). The verdict text is
"nothing writes … the engine would silently use 1 instead", which sends the reader to hunt a
cell that is fine. Right answer: 0, or at worst scoped to the point of failure — the honest
set (`run.step('Photovoltaic_Plugin').visible`, 224 cells) is right there and unused.

Silently wrong rather than visibly broken: the count is real, the diagnosis is fabricated. On
screen the flag button shows `Photovoltaic failed` instead of the count, so today the bogus 4
only reaches you through the API.

### 4. Unsupplied *optional* fields render with the placeholder "required", contradicting their own meta line

`studio.js renderField`: `placeholder="${waiting ? 'required' : ''}"` where
`waiting = field.state === 'missing'` — `declared.optional` is never consulted. The `.waiting`
class also paints the input sodium-yellow (`studio.css:436`).

Reproduction: open **PV + Electrolysis**, click step `201 Hourly Irradiation`. Field 01 renders:

``html
<div class="field waiting " data-table="Irradiance Area Parameters" data-row="Module tilt">
  <input class="cell" value="" placeholder="required">
  <div class="meta"><span><b>angle</b></span><span>range <b>0 … 1.57</b></span><span>optional</span></div>
``

The same field says **required** in the box and **optional** in the meta, with
`problems: []` and `declared.optional: true`. Seven occurrences on unmodified shipped files:

| pathway | step | cell |
|---|---|---|
| pv_e | 201 Hourly Irradiation | `Irradiance Area Parameters > Module tilt` |
| pv_e | 300 Production | `Technical Operating Parameters and Specifications > Plant design capacity` |
| thermal | 300 Production | `… > Design output by year` |
| pec | 300 Production | `… > Design output by year` |
| photocatalytic | 300 Production | `… > Design output by year` |
| pv_e_lcoe | 201 Hourly Irradiation | `Irradiance Area Parameters > Module tilt` |
| pv_e_lcoe | 300 Production | `… > Plant design capacity` |

`Plant design capacity` / `Design output by year` are alternatives — the file supplies one, so
the other is *correctly* empty. Marking it "required" in yellow is a false flag on reference
input, which the brief names as a bug.

### 5. Broken hourly-calendar buttons on PV + Electrolysis: one dead panel, one dead button

`figures.hourly_candidates` offers cells out of `step.wrote`; `figures.series` fetches them out
of `result.inp` (end of run). In `pv_e`, `Battery_Plugin` overwrites
`Power Generation > Available energy (hourly)` with a scalar `Quantity`, so the fetch fails for
a cell that two earlier steps offer.

Reproduction A — step `202 Photovoltaic`, click the small button `Available energy (hourly)`:
- console: `Failed to load resource: the server responded with a status of 400 (Bad Request)`
- red toast: `ValueError: Power Generation > Available energy (hourly) > Value holds no array`
- the calendar keeps drawing the **previously selected** series (`Irradiation Used › Data`)
  and the clicked button never lights (`call()` returns null → `state.series` untouched, no
  re-render). The click appears to do nothing but flash an error.

Reproduction B — step `203 Electrolyzer`. It offers exactly **one** button, the broken one.
The panel reads `hour by hour · Available energy (hourly) · "Pick a series to draw its year."`
forever. Same 400 and same toast. A whole figure section on a shipped pathway is dead.

Headless confirmation across all pathways:
``
cd studio && UV_PYTHON=3.12 uv run --with-editable . python scratch/repro_series2.py
``
``
=== pv_e
  BROKEN  Photovoltaic_Plugin   Power Generation > Available energy (hourly)
  BROKEN  Electrolyzer_Plugin   Power Generation > Available energy (hourly)
``
2 broken of 20 offered candidates; the other 18 fetch cleanly.

### 6. The calendar draws end-of-run state and never says which year it is drawing

Two coupled problems in the same code path as defect 5.

**(a) Wrong-provenance-by-construction.** `figures.series` reads `result.inp` — the state after
the *whole* run — while the panel is captioned with the *step* that wrote the cell. For any
cell a later step overwrites, an earlier step's calendar would draw the later step's numbers
under the earlier step's heading. On the five shipped files no such pair produces two differing
fetchable arrays (I checked every one — `repro_series2.py`, all `ok` or `BROKEN`, no
`MISMATCH`), so today the visible symptom is only defect 5's hard failure. The design is a
loaded gun: nothing prevents it, and the payload is a silently mislabelled chart.

**(b) Unlabelled year.** `studio.js:695` hard-codes `year: 0`, there is no year picker, and
`figures.js calendar()` captions the figure `"<label> — every hour of the year"`. For
`Power Generation > PV hourly power generation` in `pv_e` the cell is a 20-year mapping whose
years differ materially:

``
year 0  -> sum 74 041 993 473 033.34
year 19 -> sum 67 315 741 986 061.10     (-9.1%)
``

The payload already carries `per_year: true, years: 20`; the UI drops both. The reader is shown
one unnamed year of twenty and told it is "the year".

Related, latent: `figures.series` clamps out-of-range years (`min(year, len-1)`) but echoes back
the **requested** year, not the selected one — `year=25` returns year 19's data labelled
`'year': 25`.

### 7. No way to remove a step, move a step, or see/edit/save the file — adding a plugin is one-way

Of 16 API ops, `studio.js` calls 11. It never calls `workflow.remove`, `workflow.move`,
`project.source`, `source.replace` or `reference.check`:

``
$ grep -n "workflow\.\|project.source\|source.replace\|reference.check" studio.js
952:  const result = await call('workflow.add', { plugin: name, position });
``

I enumerated every `<button>` in `#masthead`, `#rail-list` and `#needs` on a step added via
`+`: 18 `+` insertion buttons, `open a pathway`, the flag, and one `data-add-plugin` fix
button. **There is no remove control, no move control, no source view and no download.**

Consequence, in the browser: rail `+` at 202.5 → `Solar Concentrator`. The step inserts
correctly and honestly (`202.5 Solar Concentrator`, badge `5`, five unmet inputs named, the
engine's own `KeyError … Table 'Solar Concentrator' is required but not found in dcf.inp`
quoted) — and the masthead is now `no cost — the run stopped`, flag `Solar Concentrator failed`.
There is no way back. The only escape is re-opening the pathway, which by defect 1 discards
everything else you did.

The removal *works* — I had to call it out-of-band:

``js
await __api('workflow.remove', {plugin:'Solar_Concentrator_Plugin'})
// → cost 4.194302976489664, steps 17, exact === true
``

Bit-for-bit identical to the pre-add cost. So the requested "remove it again and confirm the
cost returns exactly" **passes at the API and is unreachable from the UI.**

### 8. A failed op can leave the session mutated, and permanently unusable

`op_workflow_add` and `op_source_replace` call `_store()` before their last raising statement.
When `frame.rail` raises afterwards, `dispatch` returns `{'error': …}` — which the client
renders as a toast and otherwise treats as "nothing happened" — but the poisoned project is
already the session's project. `frame.rail` → `_step_problem_count` → `_fields_for` →
`project.spec` → `engine.plugin_io` is unguarded, so a Workflow row naming a non-existent
plugin kills every subsequent read.

Reachable from the UI *if* a source editor is ever wired up (defect 7); reachable now via the
API. Repro via `source.replace`, i.e. one typo in a plugin name:

``
cd studio && UV_PYTHON=3.12 uv run --with-editable . python -c "
from pyh2a_studio import api; import re
api.dispatch('project.open', {'example':'pv_e','session':'s'})
md = api.dispatch('project.source',{'session':'s'})['markdown']
bad = re.sub(r'^Photovoltaic_Plugin','Photovoltaik_Plugin', md, count=1, flags=re.M)
api.dispatch('source.replace',{'markdown':bad,'session':'s'})
print(api.dispatch('project.state',{'session':'s'}))
print(api.dispatch('graph',{'session':'s'}))"
``

``
source.replace -> {'error': "ModuleNotFoundError: No module named 'pyH2A.Plugins.Photovoltaik_Plugin'"}
project.state  -> {'error': "ModuleNotFoundError: No module named 'pyH2A.Plugins.Photovoltaik_Plugin'"}
graph          -> {'error': "ModuleNotFoundError: No module named 'pyH2A.Plugins.Photovoltaik_Plugin'"}
``

The session is dead for good; `project.source` still returns the text, so the data is
recoverable, but no screen can render again. `scratch/repro_mutate.py` shows the same via
`workflow.add`, including that the row (`Cell_Plugin | 999`) really was written to the
document the op claimed not to touch.

Not reachable through the plugin chooser: I added all five plugins the catalogue offers that
`pv_e` does not already run, at position 250, and every one loaded and failed cleanly with
`failed` naming the step and the session still usable (`scratch/repro_addall.py`).

### 9. The pathway chooser shows a hardcoded published constant styled exactly like the live cost

`showChooser` renders `num(example.reference_cost, 5)` — the pinned constant from
`core/examples.py`, never the computed value. The masthead renders
`num(project.cost.value, 5)`. Same visual treatment, different provenance, and for one pathway
a different number:

| pathway | chooser (pinned) | masthead (computed) | published reference |
|---|---|---|---|
| PV + Electrolysis | 4.1943 | 4.1943 | 4.1943 |
| Solar Thermal | 3.2706 | 3.2706 | 3.2706 |
| Photoelectrochemical | 139.42 | 139.42 | **139.4189** |
| Photocatalytic | 185.44 | 185.44 | **185.4433** |
| PV Electricity | **0.0286** | **0.02858** | 0.0286 |

Two problems. First, opening PV Electricity makes the number you just clicked change in front
of you with no explanation. Second, `num()` uses significant figures
(`decimals = significant - 1 - floor(log10(magnitude))`), so PEC and Photocatalytic are shown
to 2 decimals and their published precision — the whole point of pinning them — **is not
visible anywhere in the UI**. A user cannot confirm from the screen that the app reproduces
139.4189. If the engine regressed, the chooser would keep displaying the old pinned number
regardless; that is the silent-wrongness of showing a constant where a reader expects a result.

### 10. Engine bookkeeping columns leak into the bindable scope, including a pointer to a pointer

`ENGINE_COLUMNS = {'Processed', 'Former Value', 'Comment'}` matches the exact string
`Former Value` only. The engine writes prefixed variants for multi-quantity rows, and those
pass the filter.

Reproduction: open **PV + Electrolysis**, click `900 Discounted Cash Flow`, look in the right
column under `500 REPLACEMENT`:

``
Electrolyzer stack replacement  Former Cost_Value       0.4                              [use]
Electrolyzer stack replacement  Former Frequency_Value  {Electrolyzer > Ac…              [use]
``

Both are offered with a `use` (bind) button, and `reference.search` hands out ready-to-paste
strings for them:

``
reference.search "former" -> 2 hits
  Planned Replacement > Electrolyzer stack replacement > Former Cost_Value
    | {Planned Replacement > Electrolyzer stack replacement > Former Cost_Value, -}
  Planned Replacement > Electrolyzer stack replacement > Former Frequency_Value
    | {Planned Replacement > Electrolyzer stack replacement > Former Frequency_Value, -}
``

`Former Frequency_Value` *holds a reference string*, so binding it gives you a pointer to a
pointer — precisely what `frame.SCOPE_HIDDEN`'s docstring says it exists to prevent. Two cells
on `pv_e`, zero on the other four.

### 11. Raw Python exception text reaches the toast

`call()` surfaces `result.error` verbatim, and `dispatch` formats it as
`f'{error.__class__.__name__}: {error}'`. Observed on screen:
`ValueError: Power Generation > Available energy (hourly) > Value holds no array` (defect 5),
`KeyError: 'Module tilt'`, `KeyError: 'Electrolyzer'`. `op_cell_edit` → `grammar.set_cell`
raises a bare `KeyError` whose entire message is the missing name, so the user gets
`KeyError: 'Module tilt'` — no verb, no advice, a Python class name. The good error paths in
this app (the dangling-reference message with its "did you mean", the `.failure` block that
quotes the engine and warns "the engine blames the step that was running, which is not always
the step at fault") show what the standard should be.

### 12. `PV Electricity`'s masthead title is a raw filename

The other four pathways carry `Display Parameters > Name` and render `PV + E`, `Thermal`,
`PEC`, `PC`. `PV_E_Electricity_Production.md` has no such row, so `_display_name` falls back to
`origin` and the masthead `<h1>` reads **`PV_E_Electricity_Production.md`** — extension
included — where every other pathway shows a display name.

### 13. Minor / latent

- **The global keydown handler throws on non-Element targets.** `event.target.matches(…)` at
  `studio.js:1023` raises `TypeError: event.target.matches is not a function` when `target` is
  `document`. Captured live via `page.on('pageerror')`. For real keystrokes the target is
  `document.body`, so this is latent rather than user-facing — but it takes out `/`, `j`/`k`
  and `Escape` together whenever it fires.
- **Negative zero in the decomposition.** `pv_e` `End of life` renders
  `-2.89e-5   -0.0%`. `(share*100).toFixed(2)` on a tiny negative gives `-0.00`.
- **Unsupported prose in the annual-costs figure.** `figures.py:270-273` asserts the year-20
  spike is "the entire twenty-year grid draw … billed in the final year, at a tariff the
  reference file documents as an upstream typo." The file documents nothing of the kind —
  `Grid Electricity > Cost = 10000.12 USD/kWh` in `PV_E_Base.md:167` carries no comment — and
  the arithmetic does not match: the 20-year grid draw
  (`Variable Operating Costs > Other`) is 13.89 M USD while the year-20 spike is 19.87 M USD,
  43% larger. The number is the engine's; the explanation attached to it is the app's guess
  presented as fact.
- **`workflow.add` with an unknown plugin returns `ModuleNotFoundError`** rather than a named
  error listing valid plugins, unlike its sibling guards (`already in this workflow`,
  `needs a "position"`).
- **The plugin chooser prints module names as descriptions** for plugins without a docstring
  summary: `Reverse Osmosis — Reverse_Osmosis_Plugin`, `Hourly Irradiation —
  Hourly_Irradiation_Plugin`, `Power Management —`, `Capital Cost —`. Redundant with the title
  beside it.

---

## PASSED

Stated separately and plainly. Each was actually exercised; nothing here is assumed.

**Engine agreement — all five pathways**

| pathway | published | computed | `project.source` round-trip | direct `engine.run` | steps |
|---|---|---|---|---|---|
| pv_e | 4.1943 | 4.194302976489664 | identical | identical | 17 |
| thermal | 3.2706 | 3.2705814097046098 | identical | identical | 10 |
| pec | 139.4189 | 139.41887561917213 | identical | identical | 13 |
| photocatalytic | 185.4433 | 185.44329282256817 | identical | identical | 13 |
| pv_e_lcoe | 0.0286 | 0.02858462133297927 | identical | identical | 12 |

1. **Published cost matches** — every pathway agrees with its reference to 4 decimals, and the
   unit string matches (`USD/kg` ×4, `USD/kWh` ×1). The functional unit is genuinely not
   hard-coded: `pv_e_lcoe` reports `USD/kWh` and its figure is captioned
   *"where the kWh price comes from"*.
2. **`project.source` round-trips exactly.** The returned markdown is byte-identical to the
   file on disk, and re-opening it yields a cost identical **as a float**, not merely to
   4 decimals.
3. **Independent cross-check passes.** `engine.run(grammar.engine_dict(text))` run outside the
   API returns the same float and the same step count for all five.
4. **Every step frame is JSON-safe and complete.** 65 frames built, all `json.dumps`-clean, no
   NaN, no Inf, no non-string dict key, no non-JSON-native value. No step op errored. Every
   declared input row that exists in the file produced a field; the only spec keys with no
   field are absent optional wildcard tables (`<...> Indirect Capital Cost <...>` etc.), which
   is correct.
5. **Zero field-level validation problems on shipped files.** Every one of 65 frames returns
   `problems: []` on every field; every rail row reports `problems: 0`; the masthead reports
   `problems: 0`; `warnings: []`. (Defect 4 is a *rendering* false flag with no underlying
   problem record, and defects 2/3 live in ops the screen does not call.)
6. **The cost decomposition reconciles.** `figures` on `Discounted_Cash_Flow_Plugin`, all five:

   | pathway | residual | headline_residual | family subtotals − total | Σ shares |
   |---|---|---|---|---|
   | pv_e | 8.88e-16 | 0.0 | 8.88e-16 | 1.0000000000000002 |
   | thermal | -4.44e-16 | 0.0 | -4.44e-16 | 0.9999999999999999 |
   | pec | 0.0 | 0.0 | 0.0 | 1.0 |
   | photocatalytic | 5.68e-14 | 0.0 | 5.68e-14 | 1.0000000000000002 |
   | pv_e_lcoe | 3.47e-18 | 0.0 | 3.47e-18 | 1.0000000000000002 |

   11 components into 4 families every time, `total` equals the masthead headline to
   floating-point exactness, and the figure prints its own residual on screen
   (`the 11 components sum to 4.1943, and that is the headline — residual 8.9e-16`).
7. **Every reference in every shipped file resolves** when checked the way the frame checks it:
   `Project.check_references()` returns `[]` for all five. (Defect 2 is the step-scoped variant
   disagreeing with itself.)
8. **Zero JavaScript errors.** `page.on('pageerror')`, `page.on('console')` (error+warning) and
   `page.on('requestfailed')` across all 65 step views in all five pathways: empty, except the
   HTTP-400 pair in defect 5 and the synthetic-event `TypeError` I induced myself (defect 13).
9. **No `undefined` / `NaN` / `[object Object]` / stray `null` anywhere.** Full text-node walk
   plus every `<input>` value on all 65 views: zero hits.
10. **No empty panels.** `#needs`, `#scope-body` and `#rail-list` non-empty on all 65 views;
    every step rendered its head, its fields, its produced table and its scope groups.
11. **Every rendered number matches the API.** 599 editable fields across the 65 views: every
    `input.cell` value, every `input.unit` value and every `input[data-path]` value is
    **verbatim identical** to the frame's `field.text` / `unit.text` / `path.text`. Field
    counts match the frame exactly. The scope subtitle count
    (`157 values the engine already holds when Discounted Cash Flow runs · 2 arrive later`)
    matches the frame's own scope size on every view.
12. **The masthead cost matched the API cost on all 65 views** — never a stale or mismatched
    headline while stepping.
13. **The product equations reconcile.** 46 `path-row` equations across four pathways
    (`784 × 5,500 kW = 4,312,000 USD` and friends, percentages included): every one satisfies
    `typed × target-as-requested = engine's post-step value` to 1e-9 relative.
14. **The DCF figures on screen match the API** for all five: totals, residuals, per-line
    legend totals, lifetime, peak, peak year and driver share. `pv_e_lcoe` correctly labels
    `Variable operating, Replacement` as `zero in this pathway` rather than drawing flat lines.
15. **An edit that moves the cost works.** `pv_e` step 203, `Electrolyzer > Nominal power`
    `5,500` → `6000`: masthead `4.1943 → 4.2624 USD/kg`, toast `4.1943 → 4.2624 (+1.62%)`,
    API `4.2623654120352565`. Restoring `5,500` returns **exactly** `4.194302976489664`.
16. **An edit that breaks the model behaves.** Same cell → `banana`: masthead
    `no cost — the run stopped`, flag `Photovoltaic failed`, toast
    `the model stopped at Photovoltaic`, rail marks `Photovoltaic` error and all 13 downstream
    steps `skipped`, and the field itself reports
    `not a number — "banana" is not a number, and this field is declared float or int`. The
    error appears at the field *and* at the step, as claimed. The engine's blame
    (`Photovoltaic`, because PV's nominal power is a path to the electrolyzer's) is preserved
    rather than second-guessed, and the UI says so.
17. **A dangling reference that does *not* stop the run is caught correctly.** Setting
    `Direct Capital Costs - Electrolyzer > Electrolyzer CAPEX > Path` to
    `{Electrolyzer > Nominal powerr > Value, kW}`: cost moves `4.1943 → 2.7985 (-33.28%)`,
    masthead flag reads `1 to fix`, rail badges `Capital Cost 1`, and the field explains
    `path dangling — nothing writes Electrolyzer > Nominal powerr > Value; the engine would
    silently use 1 instead` with a `did you mean Nominal power` fix button. This is the app at
    its best.
18. **Adding a plugin via `+` works.** 18 insertion points for 17 steps, each labelled with the
    position it will use (`+ 202.5`), and the chooser is captioned
    `at position 202.5 — ranked by how much of each one this project already supplies`. The
    added step lands at 202.5 in execution order with its unmet inputs named individually.
    Clicking an already-in-use row is a silent no-op rather than an error.
19. **Removing it returns the cost exactly** — `4.194302976489664`, bit-for-bit — and the
    plugin's tables survive in the file, as designed. (API only; see defect 7.)
20. **The graph is consistent.** All five: `nodes` count equals the rail length, every edge
    endpoint resolves to a real node, `unmet` is empty on shipped files,
    `insertion_points == steps + 1`, and the payload is JSON-clean.
21. **Edge lighting and the flow readout are right.** Hovering `400 Capital Cost` on `pv_e`
    lights 4 of 35 edges and reports `6 values in from 3 steps · 5 values out to 1 step`.
22. **Keybindings work.** `/` focuses `#find`; `j` advanced `Capital Cost → Multiple Modules`;
    `Escape` closes the overlay; typing `electrolyzer capex` filters the scope to `2 match`
    (`Direct Capital Costs - Electrolyzer › Electrolyzer CAPEX 4 312 000 USD` and
    `Other Fixed Operating Costs › Electrolyzer OPEX (fraction of CAPEX) 0.02`), shrinking the
    panel from 13 473 to 284 characters.
23. **No clipping, overlap or horizontal overflow.** `documentElement.scrollWidth ==
    clientWidth` on all 65 views at 1680×1050 and again at 1280×800, 1100×760 and 960×700;
    no masthead element overlap at any of them; no element overflowing its box other than
    sub-pixel `line-height` differences on `.numeral` and two `<h2>`s, which are not visible
    in a screenshot.
24. **The hourly calendars that work, work.** 18 of 20 offered candidates fetch 8 760 finite
    points with no NaN, and the extent printed on screen matches the array
    (`0 → 0.909 kWh/m2`, `0.00 → 2.70 ×10¹⁰ J`). The UTC→solar-noon rotation is derived from
    the data and its amount is printed (`the axis is rotated -8 h`), which is the honest way
    to do it.
25. **`series` refuses to lie about arrays it cannot serve** — it returns `None` rather than
    fabricating or zero-filling. That is the right call; the bug in defect 5 is that
    `hourly_candidates` offers what `series` cannot serve, not that `series` declines.

---

## Explicitly checked and *not* defects

Recorded so nobody spends a day on them.

- **The 19.9 M USD year-20 spike in `pv_e`'s annual-costs chart is the engine's own number.**
  `Variable Operating Costs > Annual > Value` really is
  `[0, 1838, …, 2987, 1.987e7]` in `dcf.inp` after an independent `engine.run`. Root cause is
  `Grid Electricity > Cost = 10000.12 USD/kWh` in `PV_E_Base.md:167`, an upstream input. The
  chart is faithful; only the *prose* about it overreaches (defect 13).
- **The annual chart appearing to contradict the decomposition is discounting, not a bug.**
  Annual: variable 19.9 M vs fixed 7.36 M. Levelized: `0.8105` vs `0.8103`. The variable spend
  is concentrated in year 20 and discounted hard; the fixed spend is spread. Both figures read
  the engine.
- **`thermal` and `pec` showing identical `Variable operating 15 k` is real.** Two independent
  `engine.run` calls give `150495.8849628270` for both, element-for-element. Not a cache leak.
- **Legend colours match bar colours** in the annual chart — both index `drawn` with the same
  `index`.
- **`5,500` in `Electrolyzer > Nominal power` is the file's own text** (`PV_E_Base.md:68`), not
  a formatter inserting a separator into an input.
- **`None` in `Path` columns is the file's text**, and `refs.NO_PATH` correctly treats it as
  "no reference" — the frame raises no problem for it. My first harness pass flagged these; the
  harness was wrong, not the app.
- **`ColdDesign`'s two reports were my traffic**, on the pre-restart shared session.
  `KeyError: 'Electrolyzer'` on Enter is `cell.edit` against a project with no `Electrolyzer`
  table (same shape as `KeyError: 'Solar Thermal'` on thermal); on a clean run, focusing that
  field and pressing Enter with no change produces nothing. The reported column-widening /
  horizontal scrollbar on focus does not reproduce: measured
  `document.scrollWidth`/`body.scrollWidth`/`#needs scrollWidth`/`#stat-cost` right edge
  immediately before and after focusing a numeric cell — identical (1680/1680/629/1656.0).
- **`/` and `j` "not working" in my first browser attempt was a harness artifact.** An
  unfocused CDP tab receives no real key events at all (my own instrumented listener saw
  zero). Dispatching on `document.body` — an Element, exactly what a real keypress targets —
  proves every binding works. Reported as passing (§22), not as a defect.
