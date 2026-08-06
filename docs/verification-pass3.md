# Verification pass 3 — every page, every pathway

Scope: correctness only, no design opinions. No file under `app/` was modified.
Added: `app/scratch/verify_pass3.py` (throwaway harness, as instructed).

App under test: `http://localhost:8721`, shared Chrome on CDP `127.0.0.1:9222`.
Date: 2026-08-05.

**Verdict: not clean.** 13 defects, four of them serious enough to show a reader a
wrong number. The engine and the payload layer are sound — every headless invariant
holds for all five pathways. Every defect below is in the *figure* layer: three
figures re-derive in JavaScript what the payload already computed correctly, and
each of those re-derivations is hardcoded to the `pv_e` pathway.

---

## Part 1 — headless matrix

### Test suite and lint

``
cd app && UV_PYTHON=3.12 uv run --with-editable . pytest -q
122 passed in 3.88s

cd app && UV_PYTHON=3.12 uv run ruff check src/
All checks passed!
``

Both green.

### Payload invariants — `app/scratch/verify_pass3.py`

``
cd app && UV_PYTHON=3.12 uv run --with-editable . python scratch/verify_pass3.py
82 assertions, 0 failed
``

Per pathway, all passing:

| assertion | pv_e | thermal | pec | photocatalytic | pv_e_lcoe |
|---|---|---|---|---|---|
| `levelized_cost` == bundled reference | 4.194303 | 3.270581 | 139.418876 | 185.443293 | 0.028585 |
| `cost_unit` == reference unit | USD/kg | USD/kg | USD/kg | USD/kg | **USD/kWh** |
| `sum(contributions.data) == levelized_cost` (1e-9) | Δ 8.9e-16 | Δ −4.4e-16 | Δ 0.0 | Δ 5.7e-14 | Δ 3.5e-18 |
| `contributions.total == sum(data)` | pass | pass | pass | pass | pass |
| `cost_layers.residual == 0.0` | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| `sum(layer totals) == levelized_cost` | pass | pass | pass | pass | pass |
| payload holds no NaN/Infinity (deep walk) | 0 found | 0 | 0 | 0 | 0 |
| `payload.to_json` succeeds, no `NaN`/`Infinity` tokens | 42,705 B | 23,186 B | 38,121 B | 41,688 B | 28,732 B |
| `to_json` round-trips | pass | pass | pass | pass | pass |
| hourly payload serializes | 2×8760 | n/a | n/a | n/a | 1×8760 |

Every figure template rendered through `figures.html(name, {key: payload})` for every
pathway — 35 combinations, all non-empty, all with the payload inlined and the
stylesheet substituted (verified by asserting the `<link rel="stylesheet">` is gone
and the exact `levelized_cost` literal is present):

``
templates exercised: ['bench','cashflow','dispatch','gallery','ledger','process','worksheet']
smallest markup 58,040 B (thermal/process) · largest 227,305 B (pv_e/dispatch)
``

Note: `figures.html` is only a *string* builder. It succeeding says nothing about
whether the figure runs — four of these seven throw once the browser executes them.
See Part 2.

### `process.available` / `has_hourly` vs what the pathway physically models

| pathway | unit | `process.available` | nodes/streams | `has_hourly` | correct? |
|---|---|---|---|---|---|
| pv_e | kg | True | 7 / 7 | `pv_generation_kwh`, `unused_energy_kwh` | yes |
| thermal | kg | False — *"models no power system"* | 0 / 0 | `[]` | yes — 10 plugins, no `Hourly_Irradiation_Plugin`, no electrical system |
| pec | kg | False — *"models no power system"* | 0 / 0 | `[]` | `available` yes; **`has_hourly` wrong** |
| photocatalytic | kg | False — *"models no power system"* | 0 / 0 | `[]` | `available` yes; **`has_hourly` wrong** |
| pv_e_lcoe | kWh | True | 3 / 1 | `pv_generation_kwh` | yes |

`process.available=False` is right for all three: no power system, so no energy
balance to draw. But `has_hourly=[]` is wrong for `pec` and `photocatalytic` — both
run `Hourly_Irradiation_Plugin` and carry three 8,760-point series
(`hourly_energy`, `hourly_energy_dat`, `hourly_energy_sat`). Verified directly:

``
pv_e            hourly_irr: [('hourly_energy',8760),('hourly_energy_dat',8760),('hourly_energy_sat',8760)]
thermal         hourly_irr: []
pec             hourly_irr: [('hourly_energy',8760),...]
photocatalytic  hourly_irr: [('hourly_energy',8760),...]
pv_e_lcoe       hourly_irr: [('hourly_energy',8760),...]
``

`payload.HOURLY_SOURCES` only inspects `Photovoltaic_Plugin` and
`Electrolyzer_Plugin`, and the comment above it — *"Only the PV pathways model an
hour at all"* — is factually wrong. Defect 9.

---

## Part 2 — browser matrix

Every one of the 35 cells was visited by clicking the sidebar nav (client-side, so
the session survives), waiting 12–38 s per page, then reading: page `stException`
count, `console`/`pageerror`/`requestfailed` events, the `innerText` length of every
`srcdoc` figure frame, and `section.stMain.scrollHeight`.

Legend — `h` = `section.stMain.scrollHeight` px; `fig` = characters of `innerText`
inside the figure frame(s); `1000` means the page fits the viewport (block container
measured separately and non-empty), not that it is blank.

| | Home | Plant | Inputs | Answer | Bench | Source | Report |
|---|---|---|---|---|---|---|---|
| **pv_e** | PASS h1010 gallery 3733ch | PASS h2624 fig 1449+2558 | PASS h1000 19 steps, 13 fields | PASS h4444 fig 3753+2484 | PASS h1630 fig 9083, 17 svg | PASS h1000 md 3.2 KB | PASS h1000 preview 4.1943 USD/kg |
| **thermal** | PASS h1010 gallery 3733ch | PASS h1574 fig 501 *(composed empty state; see D8)* | PASS h1000 | PASS h3703 fig 3703+1784 | **FAIL h1000 fig 258, 0 svg, pageerror `deckBase`** | PASS h1000 | PASS h1000 preview 3.2706 USD/kg |
| **pec** | PASS h1010 gallery 3733ch | PASS h1574 fig 527 | PASS h1000 | PASS h4238 fig 4014+1846 | **FAIL h1000 fig 258, 0 svg, pageerror `deckBase`** | PASS h1000 | PASS h1000 preview 139.4189 USD/kg |
| **photocatalytic** | PASS h1010 gallery 3733ch | PASS h1574 fig 539 | PASS h1000 | PASS h4334 fig 3907+1857 | **FAIL h1000 fig 258, 0 svg, pageerror `deckBase`** | PASS h1000 | PASS h1000 preview 185.4433 USD/kg |
| **pv_e_lcoe** | PASS h1010 gallery 3733ch | **FAIL h2115 fig 418+234, 2 pageerrors** | PASS h1000 13 steps | PASS h3752 fig 3779+1796 | **FAIL h1000 fig 258, 0 svg, pageerror `deckBase`** | PASS h1000 md 3.1 KB | PASS h1000 preview 0.0286 USD/kWh |

- `stException` count was **0** in all 35 cells. Every failure is a JS exception
  inside a figure frame, which Streamlit cannot see.
- Console was **clean in all 35 cells except the six marked FAIL**.
- The Plant flowsheet component (`plant_component`) drew for every pathway:
  2045 / 934 / 1378 / 1319 / 1244 chars.
- The Answer page's ledger and cashflow figures drew correctly for **all five**
  pathways, including `pv_e_lcoe` (labelled `USD/kWh` throughout, "LEVELIZED COST OF
  PRODUCT", `404,269,742 kWh LIFETIME OUTPUT`).
- Inputs, Source and Report are native Streamlit; they render for every pathway and
  their `h=1000` is a short page, not an empty one (block container 871 px, Source
  textarea 3,057 chars, Report preview lists all 11 components and the correct total).

### Degenerate case 1 — `thermal` (no hourly, no power system)

Handled **correctly, with two blemishes**.

- The Plant page **omits** the "A year of operation" plate entirely
  (`plant.py:57` gates on `Photovoltaic_Plugin`), so there is no dispatch calendar
  and therefore no blank rectangle. That is a legitimate answer to the brief, but
  note it is *omission*, not *a composed empty state* — nothing on the page tells a
  reader that this pathway has no hour.
- The energy lens **is** a composed empty state, not a blank rectangle:
  *"This pathway reports no incident-energy balance. / This pathway does not model an
  energy balance. / No generation or power-flow tables — switch to the cost lens,
  which always applies."* No broken axis. Screenshot: `/tmp/pp_thermal_plant.png`.
- Blemishes: `COLLECTOR 0 m²` in the stat strip (the gallery says "NO PLANT GEOMETRY
  IN THIS MODEL"; the figure claims a zero-area collector), a `STREAM TABLE` heading
  with no rows beneath it, and ~330 px of dead band. Defect 8.
- The **cost** lens is not fine — see Defect 4.

### Degenerate case 2 — `pv_e_lcoe` (priced in electricity)

Hunted specifically. Scanned `section.stMain.innerText` **and** every frame's
`innerText` on all seven pages for `/hydrogen|LCOH|kg\/yr|USD\/kg|per kg|\bkg\b|H₂|H2/i`.

**One leak found**, on Inputs:

> `900 · Discounted Cash Flow` → *"Performs discounted cash flow analysis to
> determine the levelized cost of **hydrogen**"*

Sourced verbatim from the upstream plugin docstring via `engine.plugin_description`.
Defect 10.

Everything else is correctly unit-aware: readout `0.0286 USD(2016)/kWh` badged
`LCOE`, ledger and cashflow in `USD/kWh`, Report preview *"Levelized cost of product:
0.0286 USD/kWh · Functional unit: kWh"*, bench caption *"Costs are kWh-basis"*. The
Home gallery's `USD/kg` mentions are the comparison sheet describing the other four
pathways — correct, not a leak.

But `pv_e_lcoe`'s **Plant page is broken** for a different reason: both figures throw.
Defects 2 and 3. Screenshot: `/tmp/pp_lcoe_plant.png`.

---

## Part 3 — the interactive loop

Run in a **clean isolated browser context** (see Defect 6 for why that matters).

| step | result |
|---|---|
| Home → click `pv_e` | lands on `/Plant`, `4.1943 USD(2016)/kg` |
| Inputs → `203 · Electrolyzer` | Nominal power field reads `5,500` kW |
| set to `6000`, **Apply & run ▸** | sidebar `last run 4.2624 USD/kg` — **matches the expected 4.2624** |
| Plant | `4.2624 USD(2016)/kg` · `▲ +0.0681 vs 4.1943 · Electrolyzer > Nominal power: 5500 → 6000` · process figure redrew (`40,909 m²`, `101,986 MWh/yr`, was `37,500 m²` / `93,487`) |
| Answer | ledger `4.2624`, cashflow `levelized cost 4.2624 USD/kg`, plausibility note recomputed against the new total |
| Bench | `BASE CASE · LEVELIZED COST 4.2624`, 88 runs in 0.74 s, no stale `4.1943` anywhere in the sheet; `Electrolyzer › Nominal power` row re-based |

Cross-checked headlessly: patching the cell to `6000` and running
`engine.run_dcf` gives `4.2624`. Agreed to four decimals.

### Reload persistence

`page.reload()` while on `/Bench`, 40 s settle:

| check | result |
|---|---|
| project survived | **yes** — sidebar `PV + Electrolysis · 17 plugins · functional unit kg` |
| URL preserved | yes, `/Bench` |
| `stException` | 0 |
| **edit survived** | **yes** — Source textarea reads `Nominal power \| 6000 \| kW` |
| answer survived | yes — Answer shows `4.2624` |

**Persistence works.** It is genuinely proven, not assumed — but only for a single
tab. See Defect 6: my first attempt at this test *failed* (reload restored `5500`),
and the cause was four other live tabs of the app on the same origin overwriting the
shared localStorage key. That is a real bug, reproduced deterministically below.

---

## Defects

### 1. Bench page is dead for four of five pathways — CRITICAL

`app/src/pyh2a_app/ui/figures/bench.html:843`

``js
const gridDeck = rows.find(r => r.name === 'Grid Electricity > Cost');
``

Only `pv_e` has a `Grid Electricity > Cost` sweep row. For every other pathway
`gridDeck` is `undefined`, and line 850 dereferences it while building the `CAUSE`
object literal — before any drawing happens:

``js
<code>${deckExact(gridDeck.deckBase)} USD/kWh</code>
``

`TypeError: Cannot read properties of undefined (reading 'deckBase')`. Line 985 has
the same dereference.

The engine side is fine — `sweep.tornado` returns 2 / 3 / 2 / 4 responses for
thermal / pec / photocatalytic / pv_e_lcoe in 0.04–0.15 s. The data is computed and
handed to a figure that dies before using it.

**Repro:** load `thermal` from Home → Bench. You get a 231 px header strip:
`BASE CASE · LEVELIZED COST` shows an em-dash, `COST OF THIS ANALYSIS` is blank,
`§1 Influence ranking` and `§2 Response curves` are headings with nothing under
them, and the page footer reads *"the whole sheet took 0.00 s"*. Identical for
`pec`, `photocatalytic`, `pv_e_lcoe`. Screenshot: `/tmp/pp_thermal_bench.png`.

### 2. Dispatch calendar paints a black rectangle for `pv_e_lcoe` — CRITICAL

`app/src/pyh2a_app/ui/figures/dispatch.html:962`

``js
load(q.get('key') || 'pv_e');
``

Inside the app there is no query string, so the figure always boots asking for
`fixtures/pv_e.json` and `fixtures/pv_e-hourly.json`. `figures._shim` resolves an
unknown fixture key to `keys[0]` of the payload dict — the *main* payload. So for
`pv_e_lcoe`:

- `fetch('fixtures/pv_e.json')` → falls back to the `pv_e_lcoe` main payload (looks
  right by luck, which is why the title and blurb are correct)
- `meta.has_hourly` is `['pv_generation_kwh']` → truthy → proceeds past the empty-state branch
- `fetch('fixtures/pv_e-hourly.json')` → falls back to the **main payload again**
- `derive()` at line 323 does `pvA.length` on `hourly.pv_generation_kwh`, which is
  `undefined` → `TypeError: Cannot read properties of undefined (reading 'length')`

`pv_e` works only because its payload key happens to be the string `pv_e`.

**Repro:** load `pv_e_lcoe` from Home → Plant → scroll to "A year of operation".
The calendar is a solid black rectangle with no axes, no legend, no census, no
readout — exactly the failure mode the brief said must not happen.
Screenshot: `/tmp/pp_lcoe_plant.png`.

### 3. Process figure half-draws for `pv_e_lcoe` — HIGH

`app/src/pyh2a_app/ui/figures/process.html:485` draws the PV→electrolyzer stream
unconditionally. `m.direct` is `physical.direct_electrolysis_mwh_yr`, which is `null`
for a pathway with no electrolyzer. `N()` at line 153 is
`v => v.toLocaleString(...)` with no null guard →
`TypeError: Cannot read properties of null (reading 'toLocaleString')`, thrown from
`stream()` → `drawFlow()` → `draw()`, aborting the rest of the diagram.

**Repro:** load `pv_e_lcoe` → Plant. The energy lens stops after the PV bar: an
orange stub hangs into ~250 px of white space, the sunlight-to-product efficiency
reads `—`, and `STREAM TABLE` heads an empty table. Frame `innerText` is 418 chars
against 1,449 for the healthy `pv_e` equivalent.

### 4. Process cost lens invents a `pv_e` plant for every non-PV pathway — CRITICAL

`app/src/pyh2a_app/ui/figures/process.html:194-227`, `costModel()`. It re-derives
the cost spine in JavaScript against a hardcoded unit list —
`Direct Capital Costs - PV`, `- Battery`, `- Reverse Osmosis`, `- Electrolyzer` —
and ignores `payload.cost_layers`, which the backend already computes correctly per
pathway (and which `verify_pass3.py` proves reconciles to 0.0 residual for all five).

What the app shows vs what the payload holds:

| pathway | figure spine | payload `cost_layers` |
|---|---|---|
| thermal | PV ARRAY +0.0000 · BATTERY +0.0000 · DESALINATION +0.0000 · **ELECTROLYZER +0.2513 (7.7%)** | Equipment 0.2921 · Gas Processing 0.0725 |
| pec | PV ARRAY +0.0000 · BATTERY +0.0000 · DESALINATION +0.0000 · **ELECTROLYZER +114.8440 (82.4%)** | PEC Cells 117.028 · Solar Concentrator 0.520 · Installation 0.119 · Control System 0.013 |
| photocatalytic | PV ARRAY +0.0000 · BATTERY +0.0000 · DESALINATION +0.0000 · **ELECTROLYZER +150.3205 (81.1%)** | Photocatalyst 154.640 · Installation 0.121 · Control System 0.118 · Gas Processing 0.116 |

A solar-thermochemical plant, a PEC cell array and a photocatalyst slurry are each
told they have an electrolyzer carrying 82% of their cost, plus three phantom
zero-value units.

Worse, the equity capital vanishes. Because none of the four hardcoded table names
match, every equipment share is 0 and the spine is short by exactly the "BUILD IT"
figure printed directly beneath it:

| pathway | Σ tributaries | headline | missing | "BUILD IT" tile |
|---|---|---|---|---|
| thermal | 2.9060 | 3.2706 | 0.3646 | 0.3659 |
| pec | 136.5794 | 139.4189 | 2.8395 | 2.8427 |
| photocatalytic | 180.6572 | 185.4433 | 4.7861 | 4.8030 |

And the chart's own footer asserts **"Σ of 11 components ✓ reconciles"** while doing it.

`pv_e` (0.7855+0+0.0041+0.7172+1.6221+1.0654+0.0693−0.0693 = 4.1943) and
`pv_e_lcoe` reconcile only because their table names happen to match. Both still
show a phantom `BATTERY +0.0000` row — neither has a `Direct Capital Costs - Battery`
entry.

**Repro:** load `thermal` → Plant → click the `COST` lens toggle at top right.

### 5. Δ readout compares across pathways, and across units — HIGH

Loading a new pathway does not reset `last_good_cost`, so the mini readout diffs the
new plant against the previous plant.

- thermal after pv_e: `3.2706 USD(2016)/kg  ▼ -0.9237 vs 4.1943`
- pv_e after thermal: `4.1943 USD(2016)/kg  ▲ +0.9237 vs 3.2706`
- **pv_e_lcoe after photocatalytic: `0.0286 USD(2016)/kWh  ▼ -185.4147 vs 185.4433`**

The last one subtracts USD/kg from USD/kWh and prints the result. Reproduced
deterministically in a clean context.

The same mechanism is *correct* within a project — after the Part 3 edit it read
`▲ +0.0681 vs 4.1943 · Electrolyzer > Nominal power: 5500 → 6000`, which is exactly
right. It only needs clearing on project load.

**Repro:** Home → `thermal` → Home → `pv_e`. Read the black readout beside the title.

### 6. Two tabs of the app fight over one localStorage key — HIGH (silent data loss)

`persist_component/frontend/index.html:21` — `const KEY = 'paperplant.project.v1'` is
a single global slot, and `pages._sync_persistence()` writes it on every rerun of
every page in every tab. Last writer wins.

**Repro (deterministic, clean profile):**
1. Tab A: load `PV + Electrolysis`. Inputs → `203 · Electrolyzer` → Nominal power
   `6000` → Apply & run. Confirm `4.2624 USD/kg`. localStorage now holds
   `Nominal power | 6000 | kW`.
2. Tab B (same browser): open `http://localhost:8721/`, click `Solar Thermal`.
   localStorage is now `{name: "Solar Thermal", ...}`.
3. Tab A: `page.reload()`.
4. Tab A comes back as **Solar Thermal**. The PV project and the 6000 kW edit are gone.

This also silently corrupted my first persistence test — four unrelated live tabs of
the app were stamping their own `5,500` markdown over my edit mid-navigation, which
is what made the reload appear to lose the edit. Traced with a 200 ms localStorage
poll: after apply the store read `5500`, then flipped to `7000` 203 ms later.

Single-tab persistence is correct and proven (Part 3).

### 7. Standalone-page pathway switchers leaked into the app — MEDIUM

Two figures still carry the case-switcher UI they used when they were standalone
workshop pages. Inside the app there is only one payload, so these controls are dead
at best and throwing at worst.

- **dispatch**, Plant page: `EXAMPLE  pv_e | pv_e_lcoe | thermal`. On `pv_e`,
  clicking `thermal` throws `TypeError: Cannot read properties of undefined (reading
  'length')` (same shim-fallback path as Defect 2) and leaves the previous pathway's
  calendar on screen — a control that looks like it switched and did not.
- **ledger**, Answer page: `PV + Electrolysis | PV → Electricity | Solar thermal |
  Photoelectrochem. | Photocatalytic`. Clicking any of them is a silent no-op.

**Repro:** load `pv_e` → Plant → in the dispatch figure click `thermal`.

### 8. Empty-state blemishes on the process figure — MEDIUM

For `thermal`: `COLLECTOR 0 m²` in the stat strip. The Home gallery correctly says
"NO PLANT GEOMETRY IN THIS MODEL" for this pathway; the figure instead asserts the
collector has zero area.

For `thermal`, `pec`, `photocatalytic` and `pv_e_lcoe`: the `STREAM TABLE` heading
and its caption render with no rows beneath them. The energy-lens empty state also
leaves ~330 px of dead band between the message and the stat strip.

**Repro:** load `thermal` → Plant, energy lens.

### 9. `has_hourly` is empty for `pec` and `photocatalytic` although both model hours — LOW

`payload.HOURLY_SOURCES` only inspects `Photovoltaic_Plugin` and
`Electrolyzer_Plugin`. Both pathways run `Hourly_Irradiation_Plugin` and hold three
8,760-point series. The comment above `HOURLY_SOURCES` — *"Only the PV pathways model
an hour at all"* — is wrong; only `thermal` genuinely has no hourly series. Not a
crash, but two pathways silently lose a view they have the data for, and the code
states a false reason.

### 10. `pv_e_lcoe` Inputs says "hydrogen" — LOW

Step `900 · Discounted Cash Flow` shows *"Performs discounted cash flow analysis to
determine the levelized cost of hydrogen"* on a pathway priced in `USD/kWh`. Comes
verbatim from the upstream plugin docstring through `engine.plugin_description`.
This is the only hydrogen/kg leak on the entire `pv_e_lcoe` pathway.

**Repro:** load `pv_e_lcoe` → Inputs → `900 · Discounted Cash Flow`.

### 11. Number fields silently accept malformed input — LOW

Values are displayed with thousands separators (`5,500`) but parsed by stripping
commas, so an incomplete edit produces a valid-looking number three orders of
magnitude off, with no warning.

**Repro:** Inputs → `203 · Electrolyzer` → triple-click Nominal power (`5,500`) →
type `6000` without clearing → field reads `5,506000` → Apply & run ▸ is accepted and
reports `3.4567 USD/kg`.

### 12. Two copies of the gallery figure, drifted; two dead files — LOW (maintenance)

`figures.py`'s docstring promises *"One copy of each figure, runnable both ways"*.
That no longer holds:

- `ui/figures/gallery.html` and `ui/gallery_component/frontend/index.html` are two
  copies of the same figure that have diverged — 244 differing lines, distinct md5s
  (`c105c70a…` vs `c0297e82…`). Only the component copy is ever served; edits to the
  `figures/` copy do nothing.
- `ui/figures/worksheet.html` (67 KB) is never rendered — the Inputs page uses native
  Streamlit forms (`pages._render_plugin_worksheet`). `INITIAL_HEIGHTS['worksheet']`
  is dead config.

### 13. 404s on hard reload of a sub-page — COSMETIC

Reloading any non-root page emits two console errors:

``
404  http://localhost:8721/Bench/_stcore/health
404  http://localhost:8721/Bench/_stcore/host-config
``

Streamlit resolves these relative to the page path. The websocket still connects and
the app works. Noted only because the brief asked for every console error.

---

## What is solid

Worth saying plainly, because most of this passed:

- The engine, `payload`, `process_flow.cost_layers`, `cashflow` and `sweep` are
  correct for all five pathways. Every headline matches its published reference,
  every contribution sum and layer allocation reconciles to machine epsilon, no
  payload contains a non-finite number, and the sweeps run in well under a second.
- The Answer page — the one that carries the actual cost decomposition — is correct
  and complete for all five pathways, including the LCOE unit switch.
- Home, Inputs, Source and Report work for all five pathways with no exceptions and
  no console errors, and Report's printout preview carries the right unit each time.
- The interactive loop is exactly right: edit → 4.2624 → all three downstream pages
  pick it up, with a correct in-project delta naming the parameter that changed.
- Single-tab reload persistence works.

Every defect above lives in the figure layer, and Defects 1–4 share one root cause:
`bench.html`, `dispatch.html` and `process.html` each re-derive in JavaScript
something the payload already computed, and each re-derivation is written against
`pv_e`. Wiring those three to `payload.cost_layers`, `payload.has_hourly` and the
actual payload key would close four of the five serious defects.

---

## Confirmation sweep

Re-verification of the 13 defects after commit `36962c1` *"Fix every defect the
verification pass found, at the root"*. Same app (`http://localhost:8721`), same
shared Chrome, a freshly-claimed tab (`window.name = 'CS_TAB'`), 20–25 s settle per
navigation. No file under `app/` was modified.

**Verdict: 8 of the 9 checks pass. One does not, and it is a new crash, not the old
one.** Every original root cause is genuinely gone — `gridDeck.deckBase`, the
`fixtures/pv_e` key fallback, the hardcoded `costModel()` table names, the unreset
`last_good_cost`, the shared `localStorage` slot. But `bench.html` acquired a second
null dereference three lines away from the first, and it kills the same sheet on the
same four pathways, just later in the render.

### Part 1 — headless

``
cd app && UV_PYTHON=3.12 uv run --with-editable . pytest -q
129 passed in 3.81s

cd app && UV_PYTHON=3.12 uv run ruff check src/
All checks passed!
``

Both green, and 129 is the expected count (was 122 last pass).

### Part 2 — the nine checks

#### 1. Bench across all five pathways — **STILL BROKEN**

The old crash is fixed and most of the sheet now draws. What the check asked for:

| | base case | matches pathway | §1 tornado rows | §2 panels drawn | provenance block | pageerror |
|---|---|---|---|---|---|---|
| pv_e | `4.1943 USD/kg` | yes | 8 | **8 of 8** | present | none |
| thermal | `3.2706 USD/kg` | yes | 2 | **1 of 2** | empty | **yes** |
| pec | `139.42 USD/kg` | yes | 3 | **1 of 3** | empty | **yes** |
| photocatalytic | `185.44 USD/kg` | yes | 2 | **1 of 2** | empty | **yes** |
| pv_e_lcoe | `0.0286 USD/kWh` | yes | 4 | **2 of 4** | empty | **yes** |

`gridDeck` is now guarded (`bench.html:841`, `hasGridDefect`) and the grid-defect
narrative appears on `pv_e` only — correctly, and unavoidably: `PV_E_Base.md` is the
only example file that contains a `Grid Electricity` table at all.

But four of five throw:

``
TypeError: Cannot read properties of null (reading 'toFixed')
    at about:srcdoc:1179:72          →  app/src/pyh2a_app/ui/figures/bench.html:975
    at about:srcdoc:1162:8           →  bench.html:958, rows.forEach
``

`app/src/pyh2a_app/ui/figures/bench.html:975`, the final `else` of the §2 panel loop:

``js
note = `<b class="calc">Calc.</b> Turns at <code>f ${neg(r.turnF.toFixed(2))}</code>; total
``

`turnF` is initialised to `null` at line 361 and only assigned when the response
changes direction (line 366). The branch above it catches `r.flat` and `linear`, and
the branch above *that* catches rows with a `CAUSE` entry — so the `else` is reached
by any row that is **monotonic, not flat, and not exactly linear**. Every non-`pv_e`
pathway has one. The throw is inside `rows.forEach`, so it aborts the whole loop: no
further panels, and lines 983–1008 (`Source` / `Method` / `Reading the deck` /
`Timing`) never run. `document.getElementById('prov').innerHTML` is `''` on all four.

`pv_e` survives only because all 8 of its rows land in an earlier branch.

**Repro:** load `thermal` from Home → Bench. Screenshot `/tmp/cs-thermal-bench.png`:
headline, both tornado rows and panel 01 render; the right half of the §2 grid is
empty and the footer is gone.

Same class of bug as Defect 1, same file, three lines away. Guarding `turnF` the way
`gridDeck` was guarded would close it.

#### 2. Dispatch calendar for `pv_e_lcoe` — **CONFIRMED**

A real 365 × 24 plate. `canvas` 2400 × 660; sampling 16,330 pixels found **239
distinct colours**, dominant `rgb(244,242,236)` paper at 41.4% — not a black
rectangle. Month axis, hour axis, mean-hour histogram (peak 5,651), daily-total strip
(mean 58.1 MWh/d, best 87.6 MWh 16 Jul, worst 7.3 MWh 22 Nov), regime band
(DARK 4,445 h / GENERATING 4,315 h), "painted in 9.1 ms". Zero pageerrors on the page.
Screenshot `/tmp/cs-lcoe-cal2.png`.

#### 3. Process figure for `pv_e_lcoe` — **CONFIRMED on the figure, STILL BROKEN on "hydrogen"**

The figure itself is right, and there is no pageerror anywhere on the page:

- `22.0%` *"of the sunlight landing on 38,636 m² leaves as electricity"* ✓
- gate panel `AT THE GATE · 21,190,470 kWh/yr · 58,056 kWh a day` ✓
- stream table has exactly one row — `1 · PV array → Gate · kWh · 21,190,470 kWh/yr` ✓
- no electrolysis and no water rows; `SOLD AS kWh — no conversion step, the array is
  the product` ✓

The word **hydrogen still appears twice** on this pathway, not once. Scanned
`section.stMain.innerText` plus every frame's `innerText` on all seven pages:

| page | hit |
|---|---|
| Plant | dispatch figure, reconciliation footer: *"Σ RECONCILES — summed from the 8 760 h, this plate lands on the engine's own `physical.hydrogen_kg_yr` to within < 0.5 kWh."* |
| Inputs | `900 · Discounted Cash Flow` docstring — the known upstream leak |

The new one is `app/src/pyh2a_app/ui/figures/dispatch.html:614/617/620` (and the
provenance list at `:789`), which prints the payload's attribute name verbatim on a
plate whose every other number is `kWh`. Visible unaided in `/tmp/cs-lcoe-cal2.png`.
It is a caption naming an internal field, not a wrong number — but the check said
"anywhere on that pathway except Inputs step 900", and this is somewhere else.

#### 4. Cost lens for thermal / pec / photocatalytic — **CONFIRMED**

`costModel()` now reads `FIX.cost_layers.layers` (`process.html:218-232`). Each
pathway's stations are its own equipment, and the tributaries reach the headline:

| pathway | equipment stations | Σ all tributaries | headline |
|---|---|---|---|
| thermal | Equipment +0.2921 · Gas Processing +0.0725 | 0.2921+0.0725+2.5399+0.3661+0.0196−0.0196 = **3.2706** | 3.2706 |
| pec | PEC Cells +117.0280 · Solar Concentrator +0.5200 · Installation +0.1193 · Control System +0.0132 · Other Equipment +0.0029 | +2.5068+19.2287+0.1523−0.1524 = **139.4188** | 139.42 |
| photocatalytic | Photocatalyst +154.6403 · Installation +0.1213 · Control System +0.1180 · Gas Processing +0.1155 · Other Equipment +0.1115 | +4.3022+26.0349+0.2567−0.2571 = **185.4433** | 185.4433 |

No `PV ARRAY`, no `BATTERY`, no `DESALINATION`, no phantom `+0.0000` rows on any of
the three. The equity capital is inside `FINANCING` (0.3661 / 19.2287 / 26.0349) and
no longer vanishes. `Σ of 11 components ✓ reconciles` is now a true statement.

#### 5. Cross-pathway delta — **CONFIRMED**

`session.py:42` clears `last_good_cost` on project load. Driven in one tab, in order:

| sequence | Plant readout |
|---|---|
| photocatalytic → **pv_e_lcoe** | `0.0286 USD(2016)/kWh · LCOE` — no delta line |
| pv_e_lcoe → **thermal** | `3.2706 USD(2016)/kg · LCOH` — no delta line |
| thermal → **pv_e** | `4.1943 USD(2016)/kg · LCOH` — no delta line, no `vs 3.2706` |

No USD/kg is subtracted from USD/kWh because no cross-project delta is drawn at all.
The *in-project* delta is intact — after editing `Electrolyzer › Nominal power`
5500 → 6000 the readout is
`4.2624 USD(2016)/kg ▲ +0.0681 vs 4.1943 · Electrolyzer > Nominal power: 5500 → 6000`.

#### 6. Two-tab persistence — **CONFIRMED**

`persist_component/frontend/index.html:34` now reads `window.sessionStorage`.

1. Tab A: load PV + Electrolysis, Inputs → `203 · Electrolyzer` → Nominal power
   `6000` → Apply & run ▸ → sidebar `last run 4.2624 USD/kg`.
2. Tab B (`browser.newPage()`, same profile): Home → Solar Thermal → `3.2706 USD/kg`.
3. Snapshot of the two stores at that moment:
   `A.sessionStorage.name = "PV + Electrolysis"` with `Nominal power | 6000 | kW`;
   `B.sessionStorage.name = "Solar Thermal"`. Independent.
4. Tab A `page.reload()` → comes back **PV + Electrolysis, 17 plugins, 4.2624
   USD(2016)/kg on `/Plant`**, `stException` 0. Tab B unaffected.

Single-tab reload also restores the project *and* the unsaved edit, so the previous
pass's result is preserved.

One leftover, not a regression: `localStorage['paperplant.project.v1']` from the
pre-fix build is still sitting in the profile (it reads `Nominal power | 5,500 | kW`,
i.e. stale). Nothing reads, writes or clears it any more. Harmless, but every user who
ran the old build keeps an orphaned copy of a project in `localStorage` forever.

#### 7. Dead affordances — **CONFIRMED**

Both are `display: none`, bounding width `0`, and never paint:

- ledger, Answer page: the five `button.case` chips (`PV + Electrolysis`,
  `PV → Electricity`, `Solar thermal`, `Photoelectrochem.`, `Photocatalytic`).
- dispatch, Plant page: `div.switch[aria-label="example"]` with `pv_e | pv_e_lcoe |
  thermal`. The `time base` switch beside it is still live and still visible, which is
  correct — it is a real control.

They remain in the DOM (the figures still run standalone). Not visible in the app,
not clickable, not focusable by pointer. That satisfies the check.

#### 8. Bench timings are real — **CONFIRMED**

Run counts are exactly `parameters × 11` on every pathway, and the wall clock is
measured on this machine each time the sweep runs:

| pathway | parameters | runs shown | wall clock | per run |
|---|---|---|---|---|
| pv_e | 8 | 88 | 1356.4 / 1336.1 / 1349.6 ms *(three separate loads)* | 15.41 / 15.18 / 15.34 ms |
| thermal | 2 | 22 | 64.8 / 55.0 / 51.7 ms *(three separate loads)* | 2.95 / 2.50 / 2.35 ms |
| pec | 3 | 33 | 153.4 ms | 4.65 ms |
| photocatalytic | 2 | 22 | 117.5 ms | 5.34 ms |
| pv_e_lcoe | 4 | 44 | 160.4 ms | 3.65 ms |

The figure spells out the distinction itself — *"wall clock 1336.1 ms; per-run is the
mean of 88 warm calls on arm64, CPython 3.12. the fixture's own `run_ms` reads 14.2 ms
— that is the first, cold run of the process."* Within a single project load the
number is stable (three visits to thermal/Bench all read 55.0 ms) because the sweep is
cached in `session_state`; across loads it moves. Nothing reads 738.7 ms, and no
two-parameter pathway claims 88 runs.

Caveat: this band survives the crash in check 1 — it is drawn before the §2 loop.
The *lower* `Timing` line in the provenance block, which repeats the same numbers, is
one of the casualties.

#### 9. Caption legibility — measured

Method: for every element with its own text node, `getComputedStyle` for size and
colour, and `document.elementsFromPoint` at the element's centre for the *painted*
background, keeping only real SVG paint elements (`rect/circle/ellipse/path/polygon/
polyline/image`) with a resolved non-`none` fill. This matters: walking DOM ancestors
instead produces a rash of false `1.00:1` readings, because `<g>` and `<svg>` inherit
SVG's default black `fill` and the CSS `background-color` of a `<rect>` is transparent.
Measured on the `pv_e` Plant page (the densest instance of both figures).

| figure | text runs | **min font-size** | **worst contrast** | runs below WCAG AA |
|---|---|---|---|---|
| process | 107 | **8.5 px** — `AT THE GATE`, 4.43:1 | **4.43:1** — `#7C7E86` on `#16171A`, the gate panel's label / unit / sub-lines (`kg/yr`, `1,038 kg a day`, `12,629 MWh as LHV energy`) | 5 |
| dispatch | 122 | **8.8 px** — `physical.hydrogen_kg_yr` inline code, 11.37:1 | **3.23:1** — `Σ RECONCILES — summed from the 8 760 h…`, `#5E9A3C` on `#FAF9F5`, 10 px; then 3.95:1 for the teal `1 706.5` at 11.5 px | 15 |

**Overall: minimum font-size 8.5 px; worst contrast ratio 3.23:1.**

Nothing is illegible, but the two worst are both *green-on-paper* semantic accents in
the dispatch figure, and both fail AA (4.5:1) at body size. The 4.43:1 cluster in both
figures is the muted grey on the dark band — it misses AA by 0.07 and could be closed
by lifting `#7C7E86` two steps. The 8.5 px minimum is a deliberate small-caps label
size, consistent across both sheets.

Verified separately that the active lens toggle is *not* a contrast failure: the
pressed `ENERGY` button is `#FAF9F5` on its own `#26251F` background ≈ 14.5:1. An
earlier pass reported 1.00:1 for it; that was a measurement artefact of the
ancestor-walk, not a defect.

### Part 3 — regression check, seven pages × two pathways

Sidebar-click navigation (session preserved), 22 s settle per page, recording puppeteer
`pageerror`, `[data-testid="stException"]` count, and the `innerText` length of every
`srcdoc` figure frame and every declared component frame.

| | Home | Plant | Inputs | Answer | Bench | Source | Report |
|---|---|---|---|---|---|---|---|
| **pv_e** | gallery 3733 | fig 1501 + 2527, flowsheet 2045 | 1800 ch, 19 steps | fig 3671 + 2484 | fig 9066 | textarea 6864 ch | preview 4.1943 USD/kg |
| **thermal** | gallery 3733 | fig 501 *(composed empty state)*, flowsheet 935 | 1227 ch | fig 3621 + 1784 | **fig 3255, pageerror** | textarea 6864 ch | preview 3.2706 USD/kg |

- `stException`: **0 in all 14 cells.**
- `pageerror`: **0 everywhere except thermal/Bench**, which throws the `turnF` error
  above. `pv_e` is completely clean on all seven pages.
- No figure has trivial `innerText`. The one short frame — thermal/Plant at 501 chars —
  is the composed energy-lens empty state (*"This pathway reports no incident-energy
  balance… switch to the cost lens, which always applies"*), not a failure; the
  dispatch figure is deliberately omitted for a pathway with no PV plugin.
- Only console noise: two `404`s (`_stcore/health`, `_stcore/host-config`) on hard
  reload of a sub-page. Defect 13, unchanged, still cosmetic.

**Clean bill for `pv_e`. One defect for `thermal`, on Bench.**

### New defects

#### N1. `bench.html:975` dereferences `turnF` on any monotonic non-linear row — HIGH

Detailed under check 1. Kills §2 and the provenance block on thermal, pec,
photocatalytic and pv_e_lcoe.

**Repro:** Home → `Solar Thermal` → Bench. Console shows
`TypeError: Cannot read properties of null (reading 'toFixed')`; the §2 grid holds one
panel where there should be two; the sheet ends without `Source` / `Method` /
`Reading the deck` / `Timing`.

#### N2. `hydrogen` leaks into the dispatch reconciliation footer on `pv_e_lcoe` — LOW

Detailed under check 3. `dispatch.html:614/617/620` prints `physical.hydrogen_kg_yr`
in prose on a `USD/kWh` pathway.

**Repro:** Home → `Photovoltaic → electricity` → Plant → scroll to
`ENERGY BALANCE · SUMMED FROM THE 8 760 H` → read the green line.

#### N3. Bench announces an axis break that nothing crosses — COSMETIC

On `thermal` the §1 blurb reads: *"0 parameters reach -0.0 decades past where the
other 2 stop, so the axis is broken, once, in the open at 4.0 USD/kg — bars that cross
the break are cut, never bridged."* `bench.html:1178-1182` composes this
unconditionally, and `drawTornado` draws the `//` marks to match (visible in
`/tmp/cs-thermal-bench.png`). Both responses live inside 0.06 decades; there is
nothing to break the axis for. A negative decade count is the tell.

**Repro:** Home → `Solar Thermal` → Bench → read the §1 paragraph.

#### N4. `persist_component/__init__.py` still documents the old store — housekeeping

Line 8 of the module docstring: *"the browser's own `localStorage` is the store"*.
The frontend it describes uses `sessionStorage`, and the whole point of the fix was
that those are different. The frontend's own comment block (lines 20–26) is correct.

### The rest of the 13, spot-checked

Checks 1–9 cover Defects 1–7 and 10. The remainder:

- **Defect 8 — empty-state blemishes: UNCHANGED.** `thermal` → Plant, energy lens,
  still shows `COLLECTOR 0 m²` in the stat strip (the Home gallery still, correctly,
  says *"NO PLANT GEOMETRY IN THIS MODEL"* for the same pathway) and still heads an
  empty `STREAM TABLE`. The dead band between the bar and the stat strip is still
  there, and now shows on `pv_e_lcoe` too — see the white gap in `/tmp/cs-lcoe-plant.png`.
- **Defect 9 — `has_hourly`: UNCHANGED in substance.** The false comment is gone and
  `_hourly_series_names` has an honest docstring, but `HOURLY_SOURCES`
  (`payload.py:221-225`) still inspects only `Photovoltaic_Plugin` and
  `Electrolyzer_Plugin`. Re-measured directly:

  ``
  pv_e            has_hourly=['pv_generation_kwh','unused_energy_kwh']  hourly_irr=3 series
  thermal         has_hourly=[]                                        hourly_irr=[]
  pec             has_hourly=[]                                        hourly_irr=3 series
  photocatalytic  has_hourly=[]                                        hourly_irr=3 series
  pv_e_lcoe       has_hourly=['pv_generation_kwh']                     hourly_irr=3 series
  ``

  `pec` and `photocatalytic` still carry 3 × 8,760 points each and still report none.
- **Defect 11 — malformed numeric input: UNCHANGED.** Inputs → `203 · Electrolyzer`,
  set Nominal power to `5,506000`, Apply & run ▸. Accepted with no warning, no
  `stAlert`, button not disabled; sidebar reports `last run 3.4567 USD/kg`. Exactly the
  previous repro.
- **Defect 12 — duplicate gallery: FIXED.** `ui/figures/gallery.html` is gone; only
  `ui/gallery_component/frontend/index.html` remains.
  `ui/figures/worksheet.html` still ships, but `INITIAL_HEIGHTS` no longer lists it and
  `figures.py:40-43` now states why it is kept. Deliberate, documented, not dead config.
- **Defect 13 — sub-page reload 404s: UNCHANGED.** Two 404s on
  `_stcore/health` and `_stcore/host-config`. Cosmetic.

### Summary

| check | result |
|---|---|
| 1 · Bench, five pathways | **STILL BROKEN** — old crash fixed, new `turnF` crash truncates 4 of 5 |
| 2 · Dispatch calendar, pv_e_lcoe | CONFIRMED |
| 3 · Process figure, pv_e_lcoe | CONFIRMED (figure) / **STILL BROKEN** (second `hydrogen` leak) |
| 4 · Cost lens, thermal/pec/photocatalytic | CONFIRMED |
| 5 · Cross-pathway delta | CONFIRMED |
| 6 · Two-tab persistence | CONFIRMED |
| 7 · Dead affordances | CONFIRMED |
| 8 · Bench timings | CONFIRMED |
| 9 · Caption legibility | measured — min 8.5 px, worst 3.23:1 |
| Part 3 · pv_e, seven pages | clean |
| Part 3 · thermal, seven pages | one defect (Bench, N1) |

Two lines of JavaScript stand between this build and a clean sweep: a `turnF` guard in
`bench.html:975` and a unit-aware caption in `dispatch.html:617`.