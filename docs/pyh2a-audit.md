# pyH2A audit — master @ `a15e7bb`, 2026-08-05

**What this is.** A full audit of pyH2A as it stands on master, produced for two readers: the
maintainers (bugs, with file:line receipts) and the agent that will build the Streamlit/stlite UI
(the engine's actual runtime contract, which differs from its documented one in load-bearing ways).

**Method.** Five parallel static reviews covered the whole source tree (detailed reports:
`audit-core-utils.md`, `audit-unit-system.md`, `audit-finance-plugins.md`,
`audit-tech-plugins.md`, `audit-meta-layer.md` — ~170 findings with IDs CORE-n,
UNIT-n, FIN-n, TECH-n, META-n). In parallel I ran the engine itself: the full test suite, every
shipped input file, an 18-case error-path battery simulating user mistakes, and targeted probes
for every extraordinary claim. Every finding below is tagged:

- **✔run** — reproduced by execution today (command/probe in this session).
- **⊙read** — confirmed by reading source at the cited line; not executed.

All GitHub discussion is mirrored locally in `corpus/prs/` and `corpus/issues/` (136 PRs, 43
issues); "known upstream" claims were deduplicated against it.

---

## 0. The five findings that change decisions

1. **Every user-facing example is broken.** All 11 input files under `data/` and all 3 under
   `src/pyH2A/Example/` fail immediately with `KeyError: 'Functional Unit'` — they were never
   migrated past the PR #176 refactor (old `Type` workflow column, no `# Functional Unit`, no
   `# Input files to merge`, legacy brace-less paths). Only the 7 files in
   `src/tests/end_to_end/` run. A new user following the README cannot run anything. **✔run**
2. **The entire Analysis layer is dead — at three stacked layers.** All 7 modules in
   `src/pyH2A/Analysis/` fail: (a) they read `dcf.h2_cost`/`dcf.contributions`, removed by #176;
   (b) their parameter tables use bare `Top > Mid > Bottom` paths, which the post-#120 parser
   rejects — and brace-wrapped paths are rejected by the modules' own `get_by_path`, so **no
   syntax works** for Monte Carlo; (c) plugin outputs are now `Quantity` objects, which have no
   `__lt__`/`__float__`/arithmetic, so even the surviving code paths die in `sorted()`/`barh()`.
   The team knows at some level: every shipped example has its analysis tables suffixed
   `- Deactivate`. No test covers any analysis module, which is how this regressed silently. **✔run**
3. **Wrong numbers are quieter than crashes.** The engine's failure philosophy is inconsistent:
   inside the input resolver, errors are excellent (`[Plugin: X] Row 'Y' in table 'Z' is required
   but not found`); outside it, four distinct classes of user mistake produce *silently wrong
   LCOH* instead of any error — dangling path → value replaced by 1 with only a stdout print;
   path-unit annotation acts as a hidden multiplier (`kW`→`MW` in a path moved LCOH from 4.19 to
   1510.68 USD/kg); European decimal commas (`1,5` → 15); basis years after 2016 silently clamp
   to 2016 index data. **✔run**
4. **The engine is single-use per dict, and leaks per run.** `Discounted_Cash_Flow(dict)` mutates
   the caller's dict destructively; a second run on it fails (or double-counts sums). And
   `Hourly_Irradiation_Plugin`'s `@lru_cache` is keyed on identity-hashed `Quantity` objects:
   12 identical runs → 12 cache entries, 0 hits — an unbounded leak of 8760-hour arrays that
   never once serves its purpose. Any loop (sensitivity, Monte Carlo, an interactive UI) pays
   both costs. **✔run**
5. **The good news, verified:** the TEA core is solid. All 66 tests pass; the 5 reference
   pathways reproduce LCOH to 1e-13; a warm run takes ~9 ms; the DCF engine writes nothing to
   disk, prints nothing on success, and uses no multiprocessing; and **all 24 plugins are
   introspectable** — `Plugin(fake_dcf, print_info=False, run=False)` with a fake dcf carrying
   only `functional_unit` yields every plugin's full `input_dict`/`output_dict` (types, bounds,
   dimensions, optionality, descriptions) without executing anything. The UI's form schema,
   validation, and dataflow graph are all served by the engine itself. **✔run**

---

## 1. Broken shipped surface (what a new user hits first)

| What | Symptom | Evidence |
|---|---|---|
| `data/**/*.md` (11 files: PV_E, PEC, Photocatalytic bases/limits, LCA) | `KeyError: 'Functional Unit'` before any plugin runs | **✔run** sweep of all 23 shipped .md files |
| `src/pyH2A/Example/*.md` (3 files, shipped inside the wheel) | same, plus old `Type` column and no DCF plugin row | ⊙read META-41 |
| `pyH2A` console script | not installed — entry point lives only in `setup.cfg`, ignored under the `[project]` table (META-47) | **✔run** `uv run pyH2A` fails; no script in `.venv/bin` |
| `python -m pyH2A` | silent no-op, exit 0 — `__main__.py` is 0 bytes | **✔run** |
| `pyH2A generate` (step 2 of the documented tutorial) | three independent hard failures: reads removed `Workflow > Type` (META-22), `getattr`s deleted `pre_workflow`/`post_workflow` (META-21), calls `convert_input_to_dictionary(merge_default=...)` — kwarg removed (META-20/CORE-26) | ⊙read |
| `Defaults_LCA.md` / `Defaults_TEA_LCA.md` | schedule `Life_Cycle_Assessment_Plugin`, which does not exist in `Plugins/` → `ModuleNotFoundError`. 2 of 3 shipped default workflows unusable. LCA package is fully orphaned (zero imports anywhere; its test-data folder contains only a README) | ⊙read META-24/26/27 |
| `doc/` (Sphinx) | teaches the pre-#176 engine: removed `Type` column, removed DCF methods, non-existent `Fixed_Operating_Cost_Plugin`, no `# Functional Unit` anywhere, `pyH2A generate` as the getting-started flow | ⊙read META-36..41 |

The docs/examples drift matters beyond hygiene: the *only* working input format documentation
today is the 7 test files in `src/tests/end_to_end/`.

## 2. The Analysis layer, precisely

Verdicts from execution (**✔run**, each activated against the working PV_E test input):

| Module | First failure | Layer |
|---|---|---|
| Sensitivity_Analysis | `AttributeError: 'Discounted_Cash_Flow' object has no attribute 'h2_cost'` (line 93) | removed attribute |
| Waterfall_Analysis | same, at `__init__` (line 52) — dies at construction | removed attribute |
| Monte_Carlo_Analysis | bare paths: `ValueError: Expected a string wrapped in braces`; braced paths: `KeyError '{Direct Capital Costs - PV'` from its own `get_by_path` | **no valid parameter syntax exists** |
| Cost_Contributions_Analysis | default path: `base_case.contributions` AttributeError; the `plugin=Discounted_Cash_Flow_Plugin` escape hatch then dies at `sorted(key=...)`: `TypeError: '<' not supported between instances of 'Quantity' and 'Quantity'` (line 86) | Quantity vs float |
| Optimization_Analysis | wraps `discounted_cash_flow_function_1D`, whose default is the removed `attribute='h2_cost'` | removed attribute |
| Comparative_MC / Development_Distance_Time | construct Monte_Carlo_Analysis → transitively dead (except the `Input File` pre-computed-CSV path, which never runs a DCF) | transitive |

Also broken in the same seam (**✔run**): the public wrappers `discounted_cash_flow_function` /
`_1D` (`Discounted_Cash_Flow.py:13,83`) — the natural programmatic API — default to `h2_cost`;
their `dependent_variable` parameter is declared, never read, and its default path has the wrong
key casing *and* a hardcoded `USD/kg` that breaks non-mass functional units (UNIT-23).

Independent bugs inside the modules, found while reading (⊙read, all NEW upstream): the waterfall
chart labels step bars with the running total instead of the step delta (META-7); MC's
`metric is 'cityblock'` identity comparison silently changes the distance normalization for
file-sourced arguments (META-9); `target_price_2D_region` overwrites itself with a dict — second
plot call raises `TypeError: 'dict' object is not callable` — fatal for any interactive re-render
(META-10); the `File Index` remap loop resets its success flag every iteration and mutates the
dict it iterates (META-11); `Axes3D(fig, auto_add_to_figure=False)` was removed in matplotlib 3.7
while pyproject pins ≥3.9.4 (META-12); "perform_monte_carlo_multiprocessing" contains no
multiprocessing — the pool is commented out (META-13, good news for the browser port).

**Repair shape** (from META §8): one `levelized_cost(dcf)` accessor + unit unwrap at ~8 read
sites resurrects 6 of 7 modules; Cost_Contributions additionally needs its group-name check
retargeted (`'Total cost of hydrogen'` → `'Total Cost of Product'`, META-2). Plus one smoke test
per module so this cannot regress silently again. This is not the 5-line fix it first looks like,
but it is a contained, mechanical migration.

## 3. Silent-wrong-number bugs (highest severity class)

These produce plausible LCOH values with no exception. All verified by execution today unless noted.

| # | Bug | Magnitude | Where |
|---|---|---|---|
| S1 **✔run** | Dangling path (`Path` or `Value` referencing a nonexistent cell) → `Warning: Invalid path... setting to 1` on stdout, run continues | arbitrary — a typo'd CAPEX multiplier silently becomes ×1 | `input_modification.py:702-705` (CORE-9); same fallback for empty cells and typos (CORE-7), for paths to already-processed plain numbers (CORE-8), and for legitimate unit-less targets |
| S2 **✔run** | Unit inside `{path, unit}` is an unchecked multiplier — never reconciled with the row's own `Unit` column | `kW`→`MW` in the PV path: LCOH 4.19 → 1510.68 USD/kg | `input_modification.py:678,695` (CORE-11) |
| S3 **✔run** | `num()` strips all commas: European decimal `1,5` → 15; `5.500,5` → 5.5005 | 10×/1000× on any European-formatted number; team is largely EU-based | `input_modification.py:200-212` (CORE-6/UNIT-18) |
| S4 **✔run** | All 4 inflation index tables end at 2016/2017; later `Basis year`/`Reference year` silently clamps — basis 2024 ≡ basis 2016 | every cost quoted in the wrong dollar year; in-range control (2010) shifts LCOH +0.076 | `Inflation_Plugin.py:196-207` + `find_nearest` clamping (FIN-12, CORE-32) |
| S5 **✔run** | Fractional start-up time: `int(round(0.5)) == 0` disables all three start-up fractions. 0.5 y is the canonical H2A value; the shipped default (1 y) is the one value that works | rev-fraction 75%→10% at 0.5 y: ΔLCOH exactly 0 (control at 1 y: 0.298) | `Discounted_Cash_Flow_Plugin.py:545,672`, `Other_Fixed...:264`, `Variable...:367` (FIN-3) |
| S6 **✔run** | Replacement frequency ≥ plant life → one phantom replacement charged in the final year (`find_nearest` clamps). A stack that never wears out still costs money | +0.108 USD/kg on PV_E with a 200,000 h stack | `Replacement_Plugin.py:290,297` (FIN-2/TECH-6). *Correction to the scout claim: not active in shipped PV_E (its computed frequency is 10 y, legitimately charged at year 10).* |
| S7 **✔run** | Whitespace in a unit string concatenates numeric multipliers: `'m 2'` → factor 1.02, dimension `length 2` | 2% error + garbage dimension, no exception at construction | `quantity.py:41-75` (UNIT-7) |
| S8 **✔run** | `EUR: 0.8` hardcoded FX — wrong side of parity, no override, no date basis | EUR inputs understate cost ~30% | `config.py:123` (UNIT-5) |
| S9 ⊙read | `#170` refined: Replacement `contributions` disagrees with the authoritative `yearly_inflated` for **two** reasons — construction-year unplanned overcount (+C/(C+L)) and missing inflation escalation (≈−29% with defaults) | breakdown numbers lie relative to the LCOH they claim to explain | `Replacement_Plugin.py:239-263` (FIN-1; upstream #170 names only one cause) |
| S10 ⊙read | Property-tax-style rows pointing at already-inflated capital get the combined inflator **twice**; "Other Variable Operating Cost" is the only stream that never gets `Inflation correction`. Both invisible today only because the shipped defaults make every inflator exactly 1.0 | ~30% / ~8% respectively once basis ≠ reference year | `Other_Fixed_Operating_Cost_Plugin.py:236` (FIN-6), `Variable_Operating_Cost_Plugin.py:340-343` (FIN-7) |
| S11 ⊙read | Construction table: row count *is* construction duration; row order is zipped against inflation factors; fractions never checked to sum to 1; an empty table gives C=0 and a far-too-low LCOH with no diagnostic | arbitrary | `Time_Plugin.py:129`, `Capital_Cost_Plugin.py:566` (FIN-19) |
| S12 ⊙read | Table-group membership is a substring test: any table whose name *contains* `Direct Capital Cost` joins the group — including the plugin's own output table `Direct Capital Costs` (plural) on a re-run | double counting | `input_resolver.py:611`, `input_modification.py:1010` (CORE-22, FIN-8) |
| S13 ⊙read | Table sums add `base_value` with no dimension check — a `USD/m2` row in a `USD` cost table sums silently | mislabeled garbage | `input_modification.py:936-941` (UNIT-16) |

## 4. Crash bugs and contract violations

**Parser (the markdown → dict state machine, `input_modification.py:257-285`).** It is not a
markdown parser; it is a 35-line line-classifier with these verified behaviors: canonical GFM
tables *with leading/trailing pipes* parse to a silently **empty table** (**✔run**: `{'My Table': {}}`)
— this is what prettier and most LLMs emit (CORE-1); a missing blank line before the next `#`
header injects the header as a junk *row* of the new table and reuses the previous table's column
names (**✔run**, CORE-2); content before the first header → `UnboundLocalError` (CORE-3);
duplicate table names silently replace (**✔run**, the second `# Electrolyzer` wholesale replaced
the first, then failed downstream on missing rows); ragged rows silently truncate via `zip`
(CORE-4); any line starting with `-` (e.g. a bullet-list comment) flips the parser into table
mode (CORE-5).

**Resolver/inserter contract holes (⊙read).** Optional-table lies: `Replacement_Plugin` declares
`Planned Replacement` optional but crashes with a bare `KeyError` when it's absent (**✔run**);
same for `Utilities` in Variable_Operating_Cost — an *omitted* optional table crashes while an
*empty* one (header only) works; the shipped LCOE test file has to carry empty stub tables to
survive (FIN-10). Outputs are less validated than inputs: leaves inside dict-valued outputs skip
type checks entirely, strings skip everything, bounds are never checked on outputs (CORE-19) —
the escape route issue #116 documented. A plugin attribute that is `None` is silently not
inserted even when declared non-optional (CORE-18). `input_dict` specs and reality disagree:
`type: {int}` is unsatisfiable after any first read because the resolver rewrites cells as
Quantities with float `base_value` (FIN-9/UNIT-24 — this is exactly what makes re-runs fail,
**✔run**: `'2020.0': Expected int, got float`). Production_Plugin lost its both-or-neither guard
from PR #56: both supplied → capacity silently ignored; neither → bare `KeyError: 'Plant design
capacity'` outside the `[Plugin: ...]` wrapper (**✔run**, FIN-5).

**Unit system (`quantity.py`, `config.py`).** The root cause behind a family of bugs: dimension
equality is **string comparison** of unnormalized parse trees, not physical equivalence (UNIT-1).
Verified: `kWh/m2/day` — the standard solar-resource unit — cannot convert to `W/m2`
(**✔run**: `Dimension mismatch: 'energy / area / time' vs 'power / area'`). Consequences:
Photocatalytic's molar-attenuation branch is dead in both spellings (`L/(cm*mol)` vs `L/cm/mol`,
UNIT-2); the energy functional unit (LCOE mode) is broken in Production_Plugin — spec says
`energy/time`, conversion wants `kWh_per_year` which is registered under `power` — and open
PR #179 is necessary but not sufficient (`MWh/year` remains rejected after it lands; UNIT-3/FIN-4,
**✔run** for the resolver error). Temperature can't appear in any composite unit (`W/K`, `J/kg/K`
unexpressible — a hard blocker for the physical-properties push, #143/UNIT-8). Circular path
references recurse to `RecursionError` with a ~1000-frame traceback (**✔run**, CORE-10). Note for
whoever fixes UNIT-1: `quantity_test.py:19-23` pins the broken string format as the contract, and
the old UI project's handoff (`old/`) contains a working dimensional-equivalence patch (its "P13")
that was never upstreamed.

**Tech plugins (⊙read, from the compressed TECH report — details in `audit-tech-plugins.md`).**
Photocatalytic's homogeneous-catalyst branch is dead code via a `'Molar Weight'` vs
`'Molar weight'` key mismatch (also the real reason #116's bad unit never fired — which is fixed
on master at line 498 (`'1/h'`, **✔run** by grep) while the issue stays open). Power_Management:
`KeyError` when `Power Consumption` exists without `Grid Electricity`; a no-generation fallback
returns a bare ndarray into `.unit[...]` code; it zeroes the daily energy bus even when idle.
Hourly_Irradiation: hour-angle sign bug for non-cardinal azimuths; hardcoded PVGIS
`skip_header=17/skip_footer=9`; fixed-tilt cell temperature reused for tracking configs; `Wh/m2`
labels on a `W/m2` array.

## 5. Usability: the error-message map

From the 18-probe battery (**✔run**), the map a UI (and issue #141) needs. Two regimes:

**Good (resolver-mediated)** — located, actionable, prefixed `[Plugin: X]`:
missing row/table, wrong dimension, out-of-bounds (includes the offending Quantity and bound),
unknown unit, legacy brace-less path. Example verbatim:
`[Plugin: Electrolyzer_Plugin] 'Electrolyzer > Minimum capacity > Value' (entry: Quantity(1.5, '-')): Base value 1.5 is above the upper bound of 1.`

**Bad (everything else)** — raw Python, no location, or silent:
- `KeyError: 'Functional Unit'` / `KeyError: 'Workflow'` — bare, pre-workflow (CORE-27).
- Plugin name typo → `ModuleNotFoundError: No module named 'pyH2A.Plugins.Electrolyzer_Plugn'`.
- Bad value in table A → `TypeError: [Plugin: B] can't multiply sequence by non-int of type
  'float'` attributed to the *referencing* plugin B, not the table holding the bad value.
- Missing `Unit` column → `AttributeError: 'NoneType' object has no attribute 'strip'` (UNIT-10).
- Missing CSV → raw `FileNotFoundError` with absolute path, no mention of which table row asked.
- Dimension errors embed full 8760-element array reprs — multi-KB messages (UNIT-15, **✔run**).
- Output-inserter messages print paths **backwards** (`Value > Levelized cost > Dependent
  Variables`) and concatenate without spaces (CORE-24).
- The `raise type(error)(msg)` re-raise idiom breaks for multi-arg exception types and re-quotes
  KeyError messages (CORE-23).
- Empty `Arguments` cell in a Methods table → `ast.literal_eval('n/a')` → uncaught ValueError
  (META-29).
- Wrong `-o` output dir: validated never — failure arrives from `fig.savefig` *after* the entire
  computation (META-33).

**Also stdout-only, never raised or returned (CORE-28):** `check_processing`'s "table not
processed" warnings (the only signal for a misspelled table name), all "setting to 1"
substitutions, insert-overwrite notices, and the DCF's own NPV≈0 consistency check (which uses an
absolute 1e-6 USD threshold that false-positives on large plants, FIN-20).

## 6. The UI agent's contract with this engine

Facts a UI must build around, all verified today unless marked:

**Lifecycle.**
- Parse once (`convert_input_to_dictionary(path)`), keep the pristine dict, and
  **`copy.deepcopy` before every run** — `Discounted_Cash_Flow(dict)` stores and destructively
  mutates the caller's dict; a second run on it fails on its own type checks (int→float) and
  would double-count sum groups (**✔run**; CORE-14, FIN-8).
- A warm run is ~9 ms (PV_E, incl. deepcopy). Sensitivity/waterfall/tornado by re-running the
  engine is the *only* working analysis route today, and it is cheap even at WASM's ~5-20×.
- Runs are silent on success (0 stdout lines), print warnings on stdout when things are
  substituted or unprocessed — **capture stdout and treat "Warning:" lines as validation
  errors**, especially `setting to 1` (S1) and `has not been processed`.
- The engine writes nothing to disk and uses no multiprocessing (CORE-31, META-13). Only the
  Analysis/plot/template layer writes files, calls blocking `plt.show()` (`output_utilities.py:149`),
  and mutates global matplotlib rcParams to Arial on every figure (META-34/35).

**Introspection (the form-schema contract).**
- Every plugin: `Plugin(dcf, print_info, run=False)` → `_set_up` only. A fake dcf with just
  `functional_unit = resolve_functional_unit('kg')` suffices for **all 24 plugins** (**✔run**).
  `input_dict` rows carry `type` (a set), `bounds` (inclusive tuple), `Unit.dimension`,
  `optional`, `description`; `output_dict` rows carry `inserted_value` (attribute name), `type`,
  `dimension`. Wildcard rows are `'<...>'`; `sum_tables` is a pseudo-row (and makes its table
  impossible to declare optional, CORE-21).
- Caveats: specs lie in places — `{int}` is unsatisfiable (UNIT-24), sibling fractions disagree
  on types/bounds (FIN-24), `special_insertions` specs are unvalidated documentation (FIN-18),
  and optional flags are violated by two plugins (FIN-10). Treat specs as the source for widget
  generation but not as a guarantee of engine behavior.

**Results.**
- LCOH/LCOE: `dcf.inp['Dependent Variables']['Levelized cost']['Value']` — a `Quantity` in
  `USD/<functional unit>`. Breakdown: `['Levelized cost contributions']['Value']` =
  `{'Data': {11 named Quantity entries}, 'Total': Quantity, 'Table Group': str}`; entries
  provably sum to the total (FIN-27); `Salvage` is stored negative.
- `Quantity` display recipe: show `q.supplied_value` + `q.supplied_unit` (what the user wrote,
  post-%-conversion and post-path-multiply); SI pair at `q.base_value`/`q.base_unit`; convert
  with `q.unit['MWh']` in try/except. **Never** `'x' in q.unit` or `q.unit.get(...)` — the
  `__missing__` hook means both silently miss (UNIT-20, **✔run** adjacent). No arithmetic, no
  ordering, no float(), and `==` between equal quantities returns False (**✔run**).
- Time semantics: the time dict at `Time > Years > Value` uses relative years (0 = startup,
  negative = construction); production arrays span operation years, DCF arrays span analysis
  years — plotting one on the other's axis is off by construction time (#138 vocabulary).

**Input format the UI must emit** (the engine's real grammar, not GFM):
- Tables **without** leading/trailing pipes; blank line before every `#` header; `---`
  separator row present; no row names starting with `-`; no duplicate table/row names
  (CORE-1..5).
- Numbers: decimal point only; `%` suffix ok; never emit thousands commas (CORE-6).
- Paths always braced with unit: `{Top > Middle > Bottom, unit}` — and the UI should itself
  verify the unit matches the target's dimension *and* the row's own Unit column, because the
  engine will not (S2).
- Mandatory tables: `# Workflow` (Position column; row name = plugin module name),
  `# Functional Unit`, and in practice `# Input files to merge` → `pyH2A.Config~Defaults_TEA.md`.
  Functional unit must be a single atomic token (`kg/day` rejected).
- Empty-but-present stub tables are required for `Planned Replacement`, `Unplanned Replacement`,
  `Utilities`, `Power Consumption` when unused (FIN-10 — omission crashes).
- Units are case-sensitive exact tokens; full inventory + common-rejection table in
  `audit-unit-system.md` appendix (107 tokens; no `%`, `min`, `t`, `gal`, `BTU`, `kPa`,
  `month`, no currency but USD/EUR; `Nm3` is a *molar* unit). Offer per-dimension dropdowns, not
  free text.
- Workflow positions: defaults occupy 100–900; user plugins slot between (201-205, 301-302,
  401 in shipped examples). Position collisions are silently order-dependent.
- The analysis on/off idiom is the table-name suffix ` - Deactivate`.
- File references: `package.subpackage~filename` resolves inside the installed package;
  everything else is **CWD-relative** (not input-file-relative) — pin the working directory or
  absolutize (CORE-29, META-43). `lru_cache` on file readers means replacing an uploaded file's
  contents at the same path serves stale data for the session (CORE-30, META-45, **✔run** for the
  cache-never-hits half).

**stlite/WASM feasibility.** No multiprocessing anywhere (the MC pool is commented out); scipy
usage in the DCF path is `scipy.constants.Avogadro` (Pyodide ships scipy anyway); matplotlib is
Analysis-layer only. The engine core is browser-clean. The Arial rcParams mutation and blocking
`plt.show()` need interception if any upstream plot code is ever called.

## 7. Suggested repair order (upstream)

Ranked by (severity × cheapness). PR-sized receipts for each are in the per-area reports.

1. **Ship runnable examples**: migrate `data/` flagships to the current format or delete them and
   point README at `src/tests/end_to_end/`; fix or drop `Example/`; remove the
   `Life_Cycle_Assessment_Plugin` rows from the two LCA defaults until the plugin exists.
2. **Resurrect the Analysis layer**: one unit-unwrapping `levelized_cost(dcf)` accessor applied
   at ~8 sites + Cost_Contributions' accessor + one smoke test per module (META §8). Fix the
   MC parameter-path parsing to accept the braced syntax.
3. **Kill the silent-1 substitutions** (S1): make dangling paths and non-numeric values fatal
   (they are always authoring errors), or at minimum route warnings into a returned diagnostics
   list instead of stdout.
4. **Reconcile path units** (S2): error when the `{path, unit}` unit's dimension or scale
   disagrees with the target/row unit.
5. **Dimensional canonicalization** (UNIT-1): compare exponent vectors, not strings. Closes
   UNIT-2/3/4, unblocks LCOE inputs in natural units, and subsumes half of PR #179. The old
   `old/` project contains a tested implementation to crib from.
6. **Boundary/rounding fixes**: FIN-2 phantom replacement guard, FIN-3 fractional start-up
   handling, FIN-12 inflation-table range error instead of clamp, CORE-6/UNIT-18 comma
   validation, FIN-5 restore Production's both/neither guard.
7. **Parser hardening** (CORE-1..5): accept piped tables (or reject them loudly), duplicate-name
   errors, initialization guards. This is also what makes LLM/tool-generated inputs safe.
8. **Packaging**: move the console script into `[project.scripts]`, fill `__main__.py`, validate
   CLI paths up front, drop the doc-build deps from install requires (META-47/33).
9. **Docs**: regenerate `default_settings.rst` from `Defaults_TEA.md`; fix `guide.rst`'s workflow
   example and output format; document `_set_up`/`_run`/`run=False` in Plugin_Guide (it is the
   single most UI-relevant feature of the refactor and appears nowhere in the docs, META-40).

## 8. Corrections to scout claims (verification deltas)

For the record, where execution disagreed with static review: TECH-6's claim that the phantom
stack replacement is live in the shipped PV_E test is **wrong** — PV_E's computed frequency is
10.0 years (one genuine replacement, correctly charged); the bug itself is real and fires
whenever zero replacements are needed (**✔run**, +0.108 USD/kg). UNIT-26's suggestion to ship
`src/pyH2A/Example/` files as UI examples is wrong — those files predate #176 and cannot run
(META-41 has it right). MetaLayer's "Cost_Contributions is one attribute-unwrap away" understates
it slightly: the plugin-arg escape hatch also dies on Quantity ordering (**✔run**), so the
Quantity unwrap is load-bearing there too, as META-3 itself documents.

---

*Detailed findings: `audit-core-utils.md` (CORE-1..33), `audit-unit-system.md`
(UNIT-1..26 + full unit inventory), `audit-finance-plugins.md` (FIN-1..31 + per-plugin UI
map), `audit-tech-plugins.md` (TECH-1..31, compressed), `audit-meta-layer.md`
(META-1..50 + analysis-module input-table contracts). Probe scripts: `/tmp/pyh2a_probe_*.py`.
GitHub corpus mirror: `corpus/`.*
