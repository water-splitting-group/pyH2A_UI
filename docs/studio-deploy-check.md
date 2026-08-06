# Paper Plant Studio — the static deploy, checked against the native app

**Scope.** (1) Is the static build at `http://127.0.0.1:8740` (Pyodide) computing the same
numbers as the native server at `http://127.0.0.1:8730`? (2) Does `deploy/build.py`'s
self-verification actually hold when you try to break it? (3) Has anything on
`studio-verify-2.md`'s PASSED list regressed, and is `cells._digest_array` really
equivalent to a naive reduction on real engine arrays?

Read-only on `studio/src/`, `studio/tests/`, `studio/deploy/`. Everything below was run;
nothing is quoted from a previous round without re-running it.

``
studio/scratch/deploy_sweep.js      198 API calls per mode, driven from inside each page
studio/scratch/deploy_sweep2.js     the mutation ops, the year picker, the diagnostics
studio/scratch/build_probe.py       imports deploy/build.py and feeds it broken bundles
studio/scratch/verify3_regress.py   the PASSED list headless + the _digest_array audit
studio/scratch/verify3_regress.log  104 checks, 103 pass
studio/scratch/dc{,2}-{native,wasm}*.json   the raw comparison data
``

Method for part 1: a harness injected into each page calls `fetch('/api')` — the real HTTP
endpoint natively, `boot.js`'s interception under Pyodide — captures every response body,
strips only the three wall-clock keys (`took_ms`, `duration_ms`, `trace_ms`), canonicalises
with sorted keys, and hashes. Floats are compared as shortest-round-trip text, which is a
bijection with the double, so "same" below means bit-identical, not "same to 4 decimals".

---

## Headline

**The deploy is real and it is honest about the number that matters. It is not
bit-identical.**

Every levelized cost on every shipped pathway, the starter included, is identical to the
last digit in both modes. So is every rail row, every graph, all 673 rendered field values,
and both residuals on four of five pathways. What differs is arithmetic downstream of
numpy's elementary functions: **8 756 of 175 200 hourly values differ, by ≤ 4.3e-15
relative on 19 of the 20 candidates** (the twentieth reaches 6.4e-13), and once a user *edits* a cell the headline itself can
diverge — `Nominal power 5,500 → 6000` gives `4.2623654120352565` natively and
`4.262365412035259` under WASM, deterministically, through both `cell.edit` and
`source.replace`. Both render `4.2624`. The shipped baselines agreeing bit-for-bit is
luck, not invariance: the divergence already exists in step 201's arrays *before* any edit,
and the headline happens to round through it at 5,500 kW and not at 6,000 kW.

One user-visible text difference, and it is the *native* app that is wrong: the static
build shows a one-sentence description for `Reverse Osmosis`, `Hourly Irradiation` and
`Power Management`; the native app shows "no description in the plugin". Same files, same
bytes — CPython 3.13 dedents docstrings and 3.12 does not.

**The build's self-verification is not theatre.** Nine different removals from the
bundle — single data files, a plugin, a studio module, and a 14-file wipe of
`Lookup_Tables/` — were all refused; so was a corrupted
`MACRS.csv`; so was every wrong value of the scipy constant, down to one ULP. Two real
holes: the ±5e-4 *absolute* tolerance lets a **1.78 % wrong LCOE ship silently**, and a
shim with no constants in it passes vacuously. And when the check does fire on a missing
data file, it prints `KeyError: 'project'` instead of the message that says what is
missing.

Nothing on verify-2's PASSED list regressed. 103 of 104 checks pass; the one that does not
is a count that grew from 40 to 47 and the new number is the truthful one — but chasing it
turned up a fresh defect: **the scope search prints a match count it does not show.**

---

## Part 1 — native vs WASM, op by op

244 operations per mode (198 + 42 + 4 across three harness passes), 6 pathways (`pv_e`, `thermal`, `pec`, `photocatalytic`,
`pv_e_lcoe`, `tea_mass`), every step of each.

| what was compared | count checked | count differing | worst difference |
|---|---|---|---|
| levelized cost, shipped state, full precision | 6 | **0** | — |
| levelized cost after a mutation (edit / add / remove / move / source.replace) | 15 | **1** | `4.2623654120352565` vs `4.262365412035259` |
| cost `unit`, `steps`, `problems`, `failed` | 24 | 0 | — |
| rail rows (`position` / `status` / `problems` / `wrote`) | 74 | 0 | — |
| step frames, field count per frame | 74 | 0 | — |
| fields: `text`, `unit.text`, `bounds_shown`, `problems` | 673 | **0** | — |
| decomposition `total` / `headline` / `headline_residual` | 18 | 0 | — |
| decomposition `residual` | 6 | **1** (`pv_e_lcoe`) | `3.47e-18` vs `1.04e-17` |
| decomposition component `value` / `share` | 132 | 20 | rel. 8.4e-16 |
| annual-cost `peak` / `peak_year` / `lifetime` / `unit` | 24 | 0 | — |
| annual-cost `per_year` (nominal spend per year) | 126 | 0 | — |
| annual-cost stacked line values | 630 | 9 | rel. 4.0e-16 |
| graph: nodes, edge count, `unmet`, insertion points | 24 | 0 | — |
| hourly candidates offered (table/row/column/years/unit/max) | 20 | 0 | — |
| series `length` / `min` / `max` / `year` / `years` / `step` / `unit` | 224 | 0 | — |
| series `sum` (Python-side) | 32 | 15 | last 1–2 digits |
| series values, default year | 175 200 | **8 756** | rel. 6.4e-13 |
| series values, year picker (years 0/7/19/25 × 3 candidates) | 105 120 | **6 158** | rel. 2.0e-12 |
| front-door catalogue (`examples`) | 1 | 0 | — |
| `project.open` from supplied markdown (the drag-and-drop path) | 1 | 0 | — |
| error payloads: `error` string and HTTP status | 6 | 0 | — |
| error payloads: `traceback` | 1 | 1 | absolute paths (expected) |
| step-frame `docstring` | 74 | **74** | see D2 |
| step-head `summary` | 74 | **6** | see D2 |
| plugin-chooser `summary` | 102 | **18** | see D2 |

Both modes served every one of the 244 calls with the same HTTP status; the only non-200s
were the four I provoked deliberately, identical in both.

### D1. The engine's arrays diverge, and after an edit so does the headline

Reproduce, in a page on each origin:

``js
const post = async (op, payload) => (await (await fetch('/api', {method:'POST',
  headers:{'Content-Type':'application/json'}, body:JSON.stringify({op,payload})})).json());
await post('project.open', {example:'pv_e', session:'x'});
const e = await post('cell.edit', {table:'Electrolyzer', row:'Nominal power',
                                   column:'Value', text:'6000', session:'x'});
JSON.stringify(e.project.cost.value);
``

``
native  8730   "4.2623654120352565"
wasm    8740   "4.262365412035259"      3 ULP apart, rel. 6.25e-16
``

Deterministic — three repeats per mode, identical within each. The same two values come
out of `source.replace` with the same edit applied to the markdown, so it is the value and
not the op. Restoring `5,500` returns exactly `4.194302976489664` in both.

Where it enters: **not** the data. The bundle the browser fetches is byte-identical to the
working tree (115 members, all compared — see part 2), and at step `201 Hourly Irradiation`
every scalar read from the file matches exactly while every *computed* array does not:

| step 201 output | form | differing leaves |
|---|---|---|
| `Hourly Irradiation > Horizontal single axis tracking` | quantity_array, 8 760 | 27 |
| `Hourly Irradiation > No tracking` | quantity_array, 8 760 | 1 |
| `Hourly Irradiation > Two axis tracking` | quantity_array, 8 760 | 0 |
| `Hourly Irradiation > Mean solar input single axis tracking` | quantity | 2 |
| `Irradiance Area Parameters > Array azimuth`, `Dirt derating`, `Mismatch derating`, `Nominal operating temperature`, `Temperature coefficient` | quantity | 0 |

Per-candidate census of the 20 hourly series (default year):

| pathway · candidate | n | values differing | max rel. err | `sum` differs |
|---|---|---|---|---|
| pv_e 201 · Horizontal single axis | 8 760 | 727 | 8.4e-16 | yes |
| pv_e 201 · No tracking | 8 760 | 411 | 4.3e-15 | no |
| pv_e 201 · Two axis | 8 760 | 72 | 2.3e-16 | no |
| pv_e 202 · Irradiation Used › Data | 8 760 | 663 | 8.2e-16 | no |
| pv_e 202 · Available energy (hourly) | 8 760 | 663 | 8.3e-16 | no |
| pv_e 202 · PV hourly power generation | 8 760 | 663 | 8.3e-16 | no |
| pv_e 203 · Available energy (hourly) | 8 760 | 328 | **6.4e-13** | no |
| pv_e_lcoe 201–202 · same six | 8 760 ea. | 72–727 | 8.4e-16 | 1 of 6 |
| pec / photocatalytic 201 · three tracking modes | 8 760 ea. | 0–759 | 8.5e-16 | 2 of 3 |
| photocatalytic 301 · Solar Input › Hourly | 8 760 | 164 | 8.3e-16 | yes |
| thermal, tea_mass | — | no hourly candidates | — | — |

18 of 20 candidates carry at least one differing value. `min`, `max`, `length`, `years` and
the drawn year are identical everywhere, which is why the calendars, the scale keys and the
extents printed on screen are the same in both modes.

**[INFERENCE]** on mechanism: identical inputs and identical code producing ≤ 1 ULP
differences in trig-heavy array outputs is what a different libm does. Pyodide 0.28.3 runs
CPython 3.13 under Emscripten (confirmed — its own traceback names `/lib/python313.zip`)
with its own `sin`/`cos`/`arcsin`; macOS `libm` rounds a handful of arguments differently.
I could not execute arbitrary Python in the page to isolate the exact ufunc, because
`boot.js` exposes only `handle(op, payload)`.

**Severity.** Nothing a user reads changes: all 673 field texts, all 6 headline costs on
shipped files, every extent and every rail row are identical. What breaks is any claim of
bit-equality — a test that pins a full-precision value after an edit will pass on one mode
and fail on the other, and the `residual` the decomposition figure prints ("residual
8.9e-16") is mode-dependent on `pv_e_lcoe`. It should be stated somewhere rather than
discovered: **the two modes agree on every published number and to ~1e-15 on everything
else.**

### D2. The static build shows three plugin descriptions the native app hides

Same source file, different Python. `engine.plugin_summary` takes
`docstring.split('\n\n')[0]` and returns `''` if that paragraph contains `---`. Three
pyH2A plugins separate their summary from the numpydoc block with a line of *four spaces*,
not a blank line:

``
class Reverse_Osmosis_Plugin:
    '''Simulation of purified water production using reverse osmosis.\n    \n    Parameters\n    ----------\n...
``

CPython 3.13 dedents docstrings at compile time, so that line becomes empty and the split
works. 3.12 does not.

``
3.12.10 | paragraphs: 1 | summary: ''                     (the '---' guard fires)
3.13.5  | paragraphs: 2 | summary: 'Simulation of purified water production…'
``

Measured in both UIs, `pv_e`, rail `+` → plugin chooser:

| card | native (8730) | static (8740) |
|---|---|---|
| Reverse Osmosis | *no description in the plugin* | Simulation of purified water production using reverse osmosis. |
| Hourly Irradiation | *no description in the plugin* | Calculation of hourly and mean daily irradiation data with different module configurations. |
| Power Management | *no description in the plugin* | Management of electricity production and consumption. |
| Battery (control) | Simulation of electricity storage using a battery. | identical |

`.nodesc` elements in the chooser: **4 native, 1 static.** And on step `201 Hourly
Irradiation` the static build renders a `<p class="summary">` subtitle under the step title
that the native app leaves out entirely — screenshots `/tmp/dc-subtitle-DeployCheck_NATIVE.png`
vs `/tmp/dc-subtitle-DeployCheck_WASM.png`.

API-level: `frame.step.docstring` differs on **74 of 74** frames (indentation only),
`frame.step.summary` on 6, `plugins[].summary` on 3 plugins × 6 pathways.

This is worth fixing in the app, not in the deploy: `plugin_summary` is the one that is
wrong. `''.join(first_paragraph.split())` already normalises whitespace — the paragraph
split should too (`re.split(r'\n\s*\n', …)`), and then both interpreters agree and the
native app stops discarding three descriptions it has.

### D3. Error tracebacks differ by path, which is expected

`source.replace` with a misspelt plugin name returns the identical `error` string and the
identical 400 in both modes. The `traceback` field differs: native names
`/Users/hrishioa/Dropbox/Projects/ChatGPT/pyh2a-ui/studio/src/…`, WASM names
`/studio/src/…` (and 3.13 omits the `^^^^` anchors on some frames). `api.dispatch`
documents shipping the stack deliberately and nothing renders it, so this is a difference,
not a defect.

### Also confirmed identical

- The frontend is the same code. All five served JS/CSS files are byte-identical to
  `src/pyh2a_studio/web/`; `index.html` differs only by the documented `studio.js` →
  `boot.js` swap plus the boot panel; `studio.css` is the source file with `BOOT_CSS`
  appended. Nothing has drifted between `dist/` and the checkout.
- `examples` (the front door) — identical payload.
- `project.open` with supplied markdown (the picker / drag-and-drop path) — identical
  payload, identical cost.
- `reference.check` on a good and a dangling path, `reference.search` result *ordering* —
  identical (only the embedded float values differ).
- `workflow.add` / `remove` / `move`, and the three deliberate API errors — identical.

---

## Part 2 — is the bundle's self-verification real?

**Verdict: real, and it earns its keep. Two holes, both worth closing, neither of which
makes it theatre.**

`build_probe.py` imports `deploy/build.py` and calls its own `_verify` and `_verify_shim`
against tampered inputs, so what is under test is the shipped code.

### The bundle check catches every missing file I could think of

``
== control ==
  verified: 6 pathways reproduce their costs from the bundle      PASSED (correctly)

== drop one file at a time ==
  CAUGHT   without examples/PV_E_Base.md
  CAUGHT   without templates/tea_mass.md
  CAUGHT   without engine/pyH2A/Plugins/Photovoltaic_Plugin.py
  CAUGHT   without engine/pyH2A/Lookup_Tables/MACRS.csv
  CAUGHT   without engine/pyH2A/Lookup_Tables/Hourly_Irradiation_Data/  (2 files)
  CAUGHT   without engine/pyH2A/Lookup_Tables/Plant_Cost_Index.csv
  CAUGHT   without engine/pyH2A/Config/Defaults_TEA.md
  CAUGHT   without src/pyh2a_studio/core/starters.py
  CAUGHT   without engine/pyH2A/Lookup_Tables/          (all 14 files)

== corrupt rather than drop ==
  CAUGHT   MACRS.csv with its 20-year column zeroed
           -> the packaged bundle computes pv_e = 4.1873327000150375, not 4.1943
``

The clean-interpreter claim holds too, which is the part that could easily have been
fiction: `sys.path.insert` could have been shadowed by the editable install in the same
venv. It is not — dropping `Photovoltaic_Plugin.py` and `core/starters.py` both fail, and
the `ImportError` names `/tmp/tmpXXXXXXXX/src/pyh2a_studio/core/__init__.py`, i.e. the
extracted bundle is genuinely what gets imported.

Independently: the bundle **as served over HTTP right now** is byte-identical to the
working tree. All 115 members compared against disk — 0 byte differences, 0 files on disk
missing from the bundle (`src/pyh2a_studio` minus `web`/`__pycache__`, `pyH2A`, `examples`,
`templates`, `shim`).

### Hole 1 — the tolerance is absolute, so a 1.78 % wrong LCOE ships

`_verify` compares against 4-decimal constants with `abs(got - want) > 5e-4`. On
`pv_e_lcoe`, whose value is `0.0286`, that is a **1.75 % window**. Demonstrated by patching
one number in the bundled LCOE example:

| tamper | pv_e_lcoe from the bundle | error | build verdict |
|---|---|---|---|
| `PV CAPEX 818 → 822.09` | 0.028711472928060335 | +0.44 % | **SHIPS SILENTLY** |
| `PV CAPEX 818 → 826.18` | 0.028838324523141393 | +0.89 % | **SHIPS SILENTLY** |
| `PV CAPEX 818 → 834.36` | 0.0290920277133035 | **+1.78 %** | **SHIPS SILENTLY** |
| `PV CAPEX 818 → 858.9` | 0.029853137283789848 | +4.44 % | refused |

The README says the build "refus[es] to ship if any cost has moved". It refuses if a cost
has moved by more than 5e-4 absolute. The fix is free: the app already knows the
full-precision values (they are in this file's part 3 table and in `studio/tests/`), so
compare exactly, or at worst relatively.

### Hole 2 — the shim check is one-directional, and passes vacuously

`_verify_shim` iterates the names *the shim declares* and compares each to real scipy. It
is strict about what it looks at:

``
  CAUGHT   Avogadro off by one digit           -> shim 6.02214086e+23, real 6.02214076e+23
  CAUGHT   Avogadro off in the last bit        -> shim 6.022140760000001e+23, real 6.02214076e+23
  CAUGHT   Avogadro as a string                -> caught
  CAUGHT   a constant real scipy does not have -> shim Bogus = 1.0, real scipy has None
  CAUGHT   the constant behind a leading _     -> caught (via the derived value)
  PASSED   the constant deleted entirely       -> "verified: the scipy stand-in matches real scipy on "
``

An empty `constants.py` passes with the message printing an empty list of names. Nothing in
the build asserts that what the *engine* needs is present. Two mitigations, both real:
`con.Avogadro` is genuinely the only scipy constant on the engine path (`grep -o 'con\.[A-Za-z_]*'`
in `Utilities/Unit_Handler/config.py` → exactly one hit; `Analysis/` and `LCA/` import
`scipy.optimize`, `scipy.signal`, `scipy.sparse` but nothing on the engine path imports
them), and `boot.js` catches the failure at runtime anyway (below). Still: print the names
checked *and* fail on an empty set — one line.

Minor: the mismatch message for a type difference reads
`the scipy shim has Avogadro = 6.02214076e+23, real scipy has 6.02214076e+23`, two
identical-looking values, because it formats the value and not the type.

### Hole 3 — when the check fires on a missing data file, it does not say what is missing

`api.dispatch` turns the real exception into `{'error': …}`, then the check script does
`r['project']['cost']['value']` and dies:

``
Traceback (most recent call last):
  File "/tmp/_probe_check.py", line 15, in <module>
    out[key] = r['project']['cost']['value']
KeyError: 'project'
``

That is what an operator sees for a dropped `PV_E_Base.md`. The build correctly refuses to
ship, and tells them nothing. `r.get('error')` is right there.

### The browser has its own guard, and it works

`boot.js` re-runs `pv_e` after unpacking and refuses to hand over if the answer moves by
more than 5e-5 — an order of magnitude tighter than the build's. I served two tampered
copies of `dist/` (bundle swapped, everything else untouched) and loaded them:

| tampered bundle | what the boot panel says |
|---|---|
| `MACRS.csv` 20-year column zeroed | red bar, `could not start`, *"Error: the engine returned 4.1873327000150375 for the reference pathway, not 4.1943"* |
| `shim/scipy/constants.py` emptied | red bar, `could not start`, `PythonError: Traceback … /studio/src/pyh2a_studio/api.py …` |

Screenshot: `/tmp/dc-tamper-macrs.png`. The first message is exactly right — it names the
wrong number. The second is a raw Pyodide traceback in a 11px monospace block; it is honest
and it is unreadable, but it is also a state only a broken build can reach.

So the layering is sound: the build refuses to write a bundle that does not reproduce six
costs, and the page refuses to run one that does not reproduce the reference cost. Between
them, the "silently drops a lookup table" failure this whole thing exists to prevent is
covered twice. It is the *tolerance*, not the mechanism, that is soft.

---

## Part 3 — regressions

`verify3_regress.py`, headless against `api.dispatch` on the native tree. Every payload
carries an explicit `session`; no two scenarios share one. **103 pass, 1 fail** (that one
is a changed count, discussed below). Full log: `studio/scratch/verify3_regress.log`.

### The PASSED list, restated

| verify-2 item | re-run verdict |
|---|---|
| 1. published cost, all five | **holds** — 4.194302976489664 / 3.2705814097046098 / 139.41887561917213 / 185.44329282256817 / 0.02858462133297927, each 4-dp equal to its published constant |
| 2. `project.source` round-trips | **holds** — byte-identical to all five files on disk |
| 3. independent `engine.run` cross-check | **holds** — same float for all five |
| 4. every frame JSON-safe and complete | **holds** — 74 frames (65 + the 9-step starter), all `json.dumps(allow_nan=False)`-clean, no NaN/Inf |
| 5. zero field-level problems on shipped files | **holds** — 673 fields, `problems: []` on every one; every rail row 0; masthead 0 |
| 6. decomposition reconciles | **holds** — residuals 8.88e-16 / -4.44e-16 / 0.0 / 5.68e-14 / 3.47e-18, `headline_residual` 0.0 on all five, `total == headline == cost` as floats, shares sum to 1±2e-16, 11 rows / 4 families each |
| 7. every reference resolves | **holds** — `check_references() == []` for all five; step-scoped over all 116 path cells: `{ok: 61, malformed: 55}`, **zero dangling** |
| 8. zero JS errors | **holds where I exercised it** — 244 API calls per mode from inside both pages, every status as expected, no unprovoked non-200 (a full DOM sweep of all 65 views was not repeated this round) |
| 9. chooser constants | **holds** — `EXAMPLES` constants equal the computed cost at 4 dp for all five |
| 10. no engine bookkeeping columns in scope | **holds** — zero `Former`/`Processed`/`Comment` columns across all 74 frames; `reference.search` for `former`/`processed`/`comment` → 0 each |
| 11. raw exception text (PARTIAL in verify-2) | **unchanged** — the API still emits `KeyError: 'Nominal powerr'`, `KeyError: 'Nope Table'`, `KeyError: 'Module tilt'`, and `TypeError: '<' not supported between instances of 'str' and 'int'` for a Workflow position. Same partial state, no worse |
| 12. display names | **holds** — PV + Electrolysis / Solar Thermal / Photoelectrochemical / Photocatalytic / PV Electricity; none ends `.md` |
| 13. product equations reconcile | **holds** — 7 product rows on `pv_e`, all equal `value × path.as_requested` to 1e-9 relative. (Note for future harnesses: `path.target.value` is the cell in its *authored* unit — `50943.46 m3/year` — while `path.as_requested` is the `5.815 m3/h` the engine multiplies. The payload carries both; using the wrong one makes the app look broken when it is right.) |
| 14. DCF figures match the API | **holds** — `pv_e` lifetime 34 221 356.20, peak 20 305 763.33 in year 20; peak equals `max(per_year)` on all five |
| 15. an edit that moves the cost | **holds** — 6000 → 4.2623654120352565, restoring 5,500 → exactly 4.194302976489664 |
| 16. an edit that breaks the model | **holds** — `banana` → no cost, `failed: Photovoltaic_Plugin`, 1 error + 13 skipped in the rail, field reports *"banana" is not a number, and this field is declared float or int*; recovery restores the cost bit-for-bit |
| 17. a dangling reference that does not stop the run | **holds** — cost 2.7985027812542183, exactly 1 problem, `path-dangling` with *"the engine would silently use 1 instead"* and a `near` list headed by `Electrolyzer > Nominal power > Value` |
| 18. adding a plugin | **holds** — insertion points == steps + 1 on all five |
| 19. removing it returns the cost exactly | **holds** — all five catalogue plugins (`Solar_Concentrator`, `Catalyst_Separation`, `PEC`, `Photocatalytic`, `Solar_Thermal`) add-then-remove back to 4.194302976489664; `workflow.move Battery_Plugin 204 → 204.5 → 204` also exact |
| 20. the graph is consistent | **holds** — nodes == rail, every edge endpoint resolves, `unmet == []`, insertion points == steps + 1, on all five (35/21/26/24/23 edges) |
| 21–24 (DOM: edge lighting, keybindings, overflow, calendars) | not re-run headless; the calendar *data* half of 24 is covered by the 20-candidate check below |
| 25. `series` refuses to lie | **holds** — a scalar cell returns `ValueError: Electrolyzer > Nominal power > Value holds no array`; every candidate offered serves |
| extra: `series` reads the named step | **holds** — step 202 sum 74 041 993 473 033.34 vs step 203 6 143 413 295 318.36 |
| extra: out-of-range year echoes what was drawn | **holds** — `year=25` → `(19, 20)` |
| extra: 20 hourly candidates all serve | **holds** — 8 760 finite points each, `series.step` echoes the step asked for |
| extra: scope search finds units | **`kW` 7, `Wh/m2` 4, `deg` 3, `m2` 10 hold; `USD` is now 47, was 40** — see D4 |
| extra: `tracking` at 201 → 6, `Levelized` at 900 → 2 | **holds** |
| extra: a failed op leaves the session usable | **holds** — `source.replace` with a misspelt plugin is refused, the session still renders 4.194302976489664, the markdown does not contain the typo, and a following `cell.edit` works |
| extra: `workflow.add` with an unknown plugin | **holds** — `ValueError: no plugin named Nope_Plugin is installed` |
| extra: `state: 'missing'` fields | 8 across the six projects (7 on the five examples, 1 on the starter), every one `declared.optional: true` — consistent with verify-2 |

`tea_mass` (the new starter, not in verify-2) behaves: 5.5043552237656455, 9 steps, 20
edges, `unmet == []`, 0 problems, residual 1.78e-15, and an edit to `Operating capacity
factor` moves it to 5.747008499364798.

### `cells._digest_array` vs a naive per-bucket reduction — on real arrays

Hooked the real function and ran all six projects through every step: **1 704 arrays
digested.**

``
  PASS  vectorised envelope == naive per-bucket reduction (same bucketing)   0 mismatches
  bucket counts seen: {20: 263, 21: 208, 91: 380, 95: 853}
  arrays whose tail the reshape discards: 1233
  ... where a full-coverage bucketing would draw differently: 1153
  ... where the discarded tail lies outside the drawn envelope: 0
``

`np.min(buckets, axis=1)` is exactly the loop it replaced — 1 704 real arrays, zero
mismatches. min/max are selections, so there is no reassociation to worry about, and the
optimisation is safe as claimed.

What the audit *did* find is in the bucketing, not the reduction. `buckets =
finite[:(size // step) * step].reshape(-1, step)` drops the remainder:

``
  n= 8760  step= 92  buckets=95  covered= 8740  dropped=20
  n=  365  step=  4  buckets=91  covered=  364  dropped=1
  n=   96  step=  1  buckets=96  covered=   96  dropped=0
``

So **1 233 of 1 704 real arrays have a tail that never reaches the envelope** — the last 20
hours of every 8 760-hour series, the last day of every 365-day series — and the envelope
is 95 or 91 points rather than the declared `ENVELOPE_POINTS = 96`. In 1 153 of those, a
full-coverage bucketing (`np.array_split`) would draw a visibly different envelope.

I am not calling this a defect, for two measured reasons: `min`, `max`, `mean` and `sum` in
the same record are computed over the **whole** array, so no printed number is affected;
and across all 1 704 real arrays the discarded tail **never** falls outside the drawn
envelope's range (0 cases), so no peak or trough is hidden. It is a 0.23 % coverage gap in
a sparkline. Worth one line of comment where the reshape happens, since the next person to
read `ENVELOPE_POINTS = 96` will believe all 96 points are drawn and that every element is
covered.

---

## New defects

### D4. The scope search prints a match count it does not show

`op_reference_search` defaults `limit` to 40 and returns `{'results': …, 'total': len(hits)}`.
`studio.js:1316` sends no `limit`, then renders `state.search.total` in both the find hint
(`:779`) and the group head (`:877`) above a list that stops at 40. Nothing says the list
is cut.

**Repro, native or static:** open `PV + Electrolysis`, stay on step `100 Time`, type `a`
into the scope find.

``
find hint       : "156 match"
group head      : matches   156
.cell-row count : 40
"showing … of …": absent
``

`Cost` at the same step: `66 match`, 40 rows. Screenshot `/tmp/dc-search-truncation.png`.
Across the five pathways, **276 step-scoped searches report a total larger than the list
they return** (worst: `a` or `e` on `photocatalytic` → 189 reported, 40 shown). For an app
whose whole argument is that the number on screen is the number the engine holds, a counter
that overstates the list under it by 4× is the wrong kind of wrong. Either send a limit and
label it (`showing 40 of 156`), or render `results.length`.

This is not a regression — verify-2 checked search *counts*, never count-versus-list.

### D5. `reference.search "USD"` returns 47, not verify-2's 40

The only failing assertion in the regression run. Independently counting reachable
non-hidden `pv_e` cells whose unit or name mentions USD gives **47**, so today's number is
the honest one and `total` is uncapped — verify-2's `40` is exactly the default page size,
which is suspicious enough that I would read it as the same truncation bug being recorded
as a fact. Not a regression; recorded so the number does not get "fixed" back to 40.

### D6/D7/D8 — the build-script findings

Restated from part 2 so they are in one list: the ±5e-4 **absolute** tolerance ships a
1.78 % wrong LCOE (D6); `_verify_shim` passes vacuously on a shim with no constants (D7);
a missing data file is reported as `KeyError: 'project'` instead of the underlying error
(D8).

### D9 — the plugin-summary difference (D2 above), as an app defect

Independent of the deploy, `engine.plugin_summary` discards three real descriptions on
CPython 3.12 because it splits paragraphs on `'\n\n'` and pyH2A separates them with a line
of spaces. The native app is the one showing "no description in the plugin" for plugins
that have one. Fixing the split makes the two modes agree *and* improves the native app.

---

## What I did not check

- The DOM half of verify-2's items 21–24 (edge lighting, keybindings, overflow, calendar
  ink) — another agent owns the visual pass this round; I re-ran only their API-visible
  parts.
- Whether verify-2's NEW-1/NEW-2 (flat calendars from a cross-unit shared scale) are fixed.
  I can say the *data* they rest on is identical in both modes: `figures.hourly[].max` is
  bit-identical native vs WASM, including the 7.404e13 J ceiling offered beside the
  0.9085 kWh/m² `Data` candidate on `pv_e` step 202. If that defect is still open, it is
  equally open in the deploy.
- A cold first visit to the static build (no Pyodide in cache) — `FirstRun` owns that; my
  measurements are on a warm cache.
- Any host other than `python -m http.server`. The build is 2.1 MB across 10 files with no
  server-side anything, and `dist/` is gitignored, so a stale deploy is possible in
  principle — it is not stale now: all seven web assets and all 115 bundle members match
  the working tree byte for byte.
