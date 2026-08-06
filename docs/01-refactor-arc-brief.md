# pyH2A Refactor Arc — Brief for UI Design

Scope: merged/closed PRs #37–#179 and closed issues that shaped design, cross-checked against the local clone at `master` (`a15e7bb`). Cast: **@jschneidewind** (Jacob — maintainer, architect, final say), **@axfache** (primary refactorer and design interlocutor; writes long problem statements with enumerated options), **@Hanan-Nawaz** (per-plugin ports, repo hygiene), **@gulzerr** (CI), **@HomaHamedi207** (LCA/Monte-Carlo, mostly a parallel track that has not landed).

---

## 1. Chronological narrative

### Act I — Build the I/O substrate (Apr 14–27, #41 #44 #45 #49)

**#41** (`feat/new-input-resolver` → master) landed two things at once: `input_resolver` and a hand-rolled `Quantity` unit handler. The stated reason for not using Pint is blunt — *"Pint-based unit handling was too slow, implementation of a light-weight custom unit handler"* (#41). It deleted the old `Unit_conversion.py` / `Unit_dimension.py`. The resolver's contract: *"Input resolver handles the resolving of input information based on input_dict (defined on plugin level) and information in dcf.inp"* (#41).

**#44** added the mirror half — `Utilities/IO/output_inserter.py` and `check_functions.py` for type/dimension validation — completing the pair. **#45** integration-tested the full loop with two synthetic plugins (`Test_Plugin_A`, `Test_Plugin_B`) and an end-to-end fixture, and fixed a `Quantity`-handling bug in `process_input()`. **#49** fixed the resolver choking when an input is a *dict of Quantity objects* — the capability that later lets the time dict (§4) pass validation at all.

The pattern established here is the whole architecture: **a plugin declares what it needs (`input_dict`) and what it produces (`output_dict`); the framework does the fetching, unit conversion, type checking, bounds checking, and writing back.**

### Act II — Port every plugin, discover the structural problems (Apr 27 – Jun 14, #51–#82)

About twenty PRs, all based on `feat/plugin_refactor`, each with the same body: *"Insert output_dict / Adapt the code to use IO resolver / update plugin test / update docstrings"* (#51, #61, #62, #67, #71, #73, #74, #76, #77). Mechanical on the surface; four of them cracked open real design questions.

- **#52 / #72** (Electrolyzer, Stored Power Electrolysis): "Yearly operation data" stopped being a 3-column array and became *three separate arrays each with its own `*_Value` / `*_Unit`*; the third column was kept as a **time** rather than dimensionless because *"otherwise we complicate our lives with extra conversions in both plugins"* (#52).
- **#57** (Hourly Irradiation): the resolver's strict resolve→compute→insert ordering killed a pattern where tilt angle pointed at latitude mid-plugin. Fix: *"I introduced a default value for the tilt: when it's absent from the input file, we make it equal to the latitude automatically"* (#57). **Absence of a row is now meaningful input.**
- **#56** (Production): `Production_Scaling_Plugin` was deleted outright and replaced by a simpler `Production_Plugin`. *"No more scaling is applied"*; the plugin raises if the input supplies *neither or both* of Plant design capacity and yearly design output (#56). Follow-up #126 propagated it to every other plugin.
- **#69** (Fixed Operating Cost): split into `Labor_Operating_Cost_Plugin` + `Other_Fixed_Operating_Cost_Plugin`, fixing #63 where the refactor had naively converted USD/h → USD/year without counting only work hours.
- **#82** made `Discounted_Cash_Flow.py` Quantity-aware and normalized capitalization (#79). It also flagged that constants got *more accurate* (eV: 1.602176e-19 → 1.602176634e-19; acre: 4046.86266972 → 4046.8564224 m²), so every end-to-end expected value shifted (#82).

### Act III — Four blockers, four design changes (May–Jun)

None of these were papered over.

**#97 — sum ordering.** The input resolver parses *all* paths before any plugin computation, but Capital Cost tables reference sums produced by `sum_all_tables` over *earlier* tables. axfache: *"This is intrinsic to the new logic: the input_resolver-based approach can't have variables processed after the calculation of the previous variables in the same plugin"* (#97), then laid out three options and asked Jacob to pick. Resolution (**#98**, replacing contributor PR #60): make `sum_table` / `sum_all_tables` Quantity-aware and *call them from inside the resolver*, so sums exist on the fly — *"enables referencing of sums in the way it worked before input_resolver was added"* (#98). **#128** later fixed the crash when a table in a group is simply absent (closes #102, #106).

**#108 — what unit does a reference return?** axfache's diagnosis: *"if it's a Quantity, the reference will return the base value, but if the value was not previously turned into a Quantity, it stays in the unit where it was specified... this is very dangerous in practice"* (#108). Fix (**#120**): paths are now **always** written with their unit — `{top key > middle key > bottom key, unit}` — and the resolver *overwrites the value in `dcf.inp` with the corresponding Quantity object*, so a second reader sees a Quantity, never a raw float (#120). Related: **#118**, where unprocessed-value warnings had become hard failures — *"Quantities now constructed on the fly when unprocessed values are accessed via a path"* (#118).

**#109 — `add_processed` vs coexisting `*_Value` and `*_Path`.** Marking a whole table row processed made a user-supplied `Cost_Path` silently ignored. axfache's chosen fix inverted the direction of data flow: *"we don't even insert the replacement frequency as such, but the lifetime... then the input file's replacement table points to the lifetime. This is actually more coherent with what we do everywhere"* (#109, implemented in #117). Jacob confirmed the principle: plugins *"no longer insert directly into replacement table, but instead create a variable in dcf.inp, which is referenced through a user provided path — the previous behaviour also works now... but is undesired"* (#109).

**#70 — flowrate or mass?** axfache first preferred renaming to `Design output flowrate` (mass/time), then argued against himself on generality grounds: *"soon we will have to make pyH2A handle functional units that are not 'kg of something'... thinking in terms of mass or energy on that day, rather than mass or energy per day... might be better"* (#70). Jacob ruled: *"Should be mass only (not mass / time) and always yearly. Larger refactor of production_scaling_plugin is needed"* (#70). That ruling is the seed of both #56 and the flexible functional unit.

Also settled here: **#84** — workflow position collisions. axfache proposed defaults at odd positions; Jacob escalated: *"I would go a step further and put the default workflow positions at 100, 200, 300, 400. That way there is enough space between the default workflow functions/plugins to place all plugins without overlap"* (#84).

### Act IV — Consolidation onto master (#151, Jul 6–7)

**#151** merged `staging/plugin-refactor` → `master`: 74 files, breaking change, self-merged with no review comments or approvals (verified via the GitHub reviews API — the array is empty).

The branch lineage matters and is not what the names suggest. Per-plugin PRs (#51–#82) targeted **`feat/plugin_refactor`**. `staging/plugin-refactor` was a *curated re-land*, not a fast-forward: Jacob hand-carried contributions into it rather than merging branches. See #117 — *"Good fix, manually implemented it in staging/plugin-refactor"* — and #136 — *"Thanks a lot! Manually implemented on staging/plugin-refactor"*; both source PRs were then **closed unmerged**. #140 (documentation catch-up) is one of the few PRs that actually targeted `staging/plugin-refactor` directly. So `feat/plugin_refactor` is best read as a *design scratchpad whose ideas were re-implemented*, and #151 as the single import event into master.

### Act V — Time, then post-workflow (#138 → #176, Jun 24 – Jul 30)

**#138** (axfache) answers the still-open **#114**, where Jacob had objected to plugins reaching into `dcf.inp` for time: *"We should provide a harmonised way of providing the construction time, plant life time etc. in the dcf object"* (#114). Two consequential findings:

1. Ambiguous names had produced *wrong tests*: *"some of the existing plugin tests... made a confusion between calendar year, and year 'relative to the startup year'. And the input parameters were chosen in an unrealistic manner, which compensated the fact that we counted ageing for over 2000 years of operation"* (#138). The fix was naming discipline — `_relative` years (zero = startup year) vs calendar years.
2. Array lengths were normalized. Previously production arrays were padded with construction-year zeros: *"It was creating unnecessary complication in the plugins... In this new version, arrays have the necessary length in the plugins, no more no less"*, with a new `expand_to_analysis_years` used only where the full span is needed (#138).

Jacob returned **CHANGES_REQUESTED** with a structural demand, not a nitpick: *"Updating time and inflation function in dcf (should only create class attributes, not insertion), deleting pre-workflow"* (#138). axfache complied: *"No more calculation is done in DCF, the pre-workflow is suppressed, everything happens in the Plugins"* (#138). Merged three weeks later. **#166 → #168** then documented the three time-dict entries the docstring had missed (`Start index`, `Analysis years ones`, `Construction years ones`); Jacob approved #168.

**#176** is the capstone — *"Turning discounted cash flow analysis into plugin, simplifying Discounted_Cash_Flow.py, making functional unit flexible"*. It closes #144, #149 and #142. Concretely:

- `Discounted_Cash_Flow.py` **−527 lines**; a new `Discounted_Cash_Flow_Plugin.py` **+803 lines** sits at Workflow position 900 like any other plugin.
- `Defaults.md` deleted; replaced by **`Defaults_TEA.md`**, **`Defaults_LCA.md`**, **`Defaults_TEA_LCA.md`**.
- `Utilities/functional_unit.py` + `docstring_generation.py` added.
- `lcoe_test.py` added — the receipt that the functional unit is genuinely flexible.
- #142 fixed here too: the Electrolyzer's hardcoded 100% operating capacity factor that *"favours arbitrarily the PV_E system"* (#142).

The flexible-functional-unit work took three attempts: **#148** → **#149** (both by axfache, both closed unmerged) → absorbed into **#176**.

---

## 2. End-state architecture (verified against `a15e7bb`)

``mermaid
graph TD
  A[input .md file] --> B[convert_input_to_dictionary]
  B --> C[merge Defaults_TEA.md]
  C --> D[dcf.inp]
  D --> E[resolve_functional_unit]
  E --> F[Workflow sorted by Position]
  F --> G[Time 100]
  G --> H[Inflation 200]
  H --> I[Production 300]
  I --> J[Capital 400 / Replacement 500]
  J --> K[Labor 600 / OtherFixed 700 / VarOp 800]
  K --> L[DCF Plugin 900]
  L --> M[Dependent Variables Levelized cost]
  M --> N[check_processing]
  N --> O[meta_workflow Analysis modules]
``

Every plugin is now the same shape (`Time_Plugin.py`, `Production_Plugin.py`, `Discounted_Cash_Flow_Plugin.py`):

``python
def __init__(self, dcf, print_info, run=True):
    self._set_up(dcf)          # build input_dict/output_dict, capture dcf.functional_unit
    if run: self._run(dcf)     # resolve → compute → insert
``

The `_set_up` / `_run` split is post-#176 and is a gift to a UI: **`_set_up` is side-effect-free**, so a UI can instantiate any plugin with `run=False` and read its full `input_dict` — types, dimensions, bounds, optionality, descriptions — to generate a form without executing anything.

Note a doc drift: `doc/plugins/Plugin_Guide.rst` still shows module-level `input_dict` and a two-arg `__init__`. The shipped plugins do neither. Trust the code.

---

## 3. Decisions and rationale

| # | Decision | Rationale | Who |
|---|---|---|---|
| #41 | Custom `Quantity` instead of Pint | Pint too slow | Jacob |
| #41/#44 | Declarative `input_dict`/`output_dict`; framework does I/O | Plugins stop hand-parsing `dcf.inp` | Jacob |
| #98 | `sum_all_tables` runs *inside* the resolver | Restores pre-refactor referencing without multiplying dicts (rejects #97's options 1–3) | Jacob, over axfache's 3 options |
| #120 | Paths always `{a > b > c, unit}`; resolver rewrites `dcf.inp` cells as Quantities | Kills the "depends when you read it" unit ambiguity of #108 | Jacob |
| #118 | Build Quantities on the fly for unprocessed values | Avoids forcing plugins to declare inputs they don't use | Jacob |
| #109/#117 | Plugins publish *their own* variable; input file points at it | Plugin should not reach into another plugin's table | axfache proposed, Jacob endorsed |
| #70 | Yearly output is a **mass** (or energy), always yearly — not a flowrate | Generalizes to non-mass functional units | Jacob decided |
| #56 | Delete `Production_Scaling_Plugin`; new `Production_Plugin` with no scaling | Scaling was implicit and untestable | axfache |
| #56 | Error if neither or both of design capacity / design output supplied | *"wasn't part of the original request but I felt it could be nice"* | axfache |
| #57 | Omitted tilt row ⇒ tilt = latitude | Path-to-latitude impossible under new ordering | axfache |
| #69 | Split Fixed Operating Cost into Labor + Other | Two unrelated cost models; also fixes #63 | axfache |
| #84 | Default workflow at 100/200/…/900 | *"enough space between the default workflow functions/plugins to place all plugins without overlap"* | Jacob, escalating axfache's odd-numbers idea |
| #79 | `Construction time` capitalized like every mid key | Consistency | axfache |
| #114/#138 | One `Time_Plugin` owns all time; no direct `dcf.inp` time reads | Ends calendar-vs-relative-year confusion that had corrupted tests | Jacob raised, axfache built |
| #138 | Arrays sized to their natural span; `expand_to_analysis_years` where needed | Padding leaked DCF concerns into plugins | axfache |
| #138 | DCF functions create attributes only, never insert; pre-workflow deleted | Single insertion mechanism | Jacob (CHANGES_REQUESTED) |
| #138 | `np.zeros_like(array)` over `0 * array` | *"the intent is more clear and the type is guaranteed (np.float64)"* | Jacob |
| #110 | Production plugin emits lifetime totals | *"This is what needs to be referenced by the LCA table"* | Jacob |
| #144/#176 | `Functional Unit` becomes an input table; `FunctionalUnit` computed per DCF instance | *"In the future we want to make the code product-agnostic"* (#149) | Jacob |
| #176 | DCF becomes a plugin at position 900 | Simplification; one execution model | Jacob |
| #176 | `Defaults.md` → TEA / LCA / TEA_LCA | Analysis type is a workflow choice | Jacob |
| #176 | Docstrings generated from the spec dicts | *"so the docstring can never drift from the spec it describes"* | Jacob |
| #142/#176 | Operating capacity factor is a real variable | PV+E was being flattered vs PEC/photocatalytic | axfache raised, Jacob fixed |
| #128 | Empty table group must not crash the sum | Optional cost categories | Jacob |

---

## 4. Glossary — the team's actual vocabulary

- **`dcf.inp`** — the single nested dict `{top key: {middle key: {bottom key: value}}}` parsed from the Markdown input file. The *only* medium of exchange between plugins. Mutated in place as the workflow runs.
- **top / middle / bottom key** — table name / row name / column name. A **path** is `top > middle > bottom`.
- **path (with unit)** — since #120, always `{top key > middle key > bottom key, unit}` in curly braces. Bare `a > b > c` is legacy.
- **`input_dict`** — plugin-declared spec of what it reads: per bottom key a `type` set, optional `bounds`, a `Unit.dimension`, plus `optional` and `description`.
- **`output_dict`** — spec of what it writes: `inserted_value` names the plugin attribute to publish, plus `type` and `dimension`.
- **input resolver / `input_resolver_function`** — walks `input_dict`, calls `process_input`, builds Quantities, checks type/options/dimension/bounds, returns `input_dict_resolved`.
- **output inserter / `output_inserter_function`** — walks `output_dict` and writes the named attributes back into `dcf.inp`.
- **`Quantity`** — value + unit. Read a magnitude with `q.unit['kg']`; `q.base_value` is SI. Wraps scalars *and* ndarrays.
- **dimension** — the physical class (`mass`, `energy`, `time`, `power`, `dimensionless`) that the resolver checks; distinct from unit.
- **functional unit** — the denominator of the levelized cost. Declared in a `# Functional Unit` table; `kg` gives LCOH, `kWh` gives LCOE.
- **`FunctionalUnit`** — frozen dataclass from `resolve_functional_unit(unit)` carrying `unit`, `dimension`, `unit_SI`, `dimension_per_time`, `unit_SI_per_s`, `unit_per_year`. Energy is special-cased: per-time is `power`/`W`.
- **time dict** — the 8-entry dict at `Time > Years > Value`: `Startup time offset`, `Plant years relative`, `Operation years`, `Operation years relative`, `Start index`, `Operation years ones`, `Analysis years ones`, `Construction years ones`. All dimensionless; years are indices, not durations.
- **relative year** — zero = startup year (negative during construction). **Calendar year** = actual AD year. Conflating them caused the bad tests in #138.
- **analysis years** vs **operation years** — construction + plant life vs plant life alone.
- **table group** — several tables sharing a name fragment, matched by `<...>` (`WILDCARD_MARKER`) in a top key, e.g. `<...> Direct Capital Cost <...>`. Documented with `>>`.
- **wildcard row** — `<...>` as a middle key: any number of rows, names unknown to the plugin.
- **`sum_tables`** — a pseudo-middle-key inside `input_dict` (`mode: 'all'`) telling the resolver to sum a table group during resolution (#98). Produces `Summed total` per table and `Summed group total` for the group.
- **post-workflow** — the team's name for #176's arc: everything that used to run *after* `workflow()` inside `Discounted_Cash_Flow.py` is now a plugin *inside* the workflow. (**pre-workflow**, deleted in #138, was the symmetric thing running before.)
- **`Processed`** — marker key added to a row once consumed; `check_processing()` warns about unprocessed tables at the end. Exempt: `Workflow`, `Display Parameters`, `Functional Unit`, `Input files to merge`, anything containing `Analysis`.
- **meta module / Analysis module** — post-DCF analyses (Sensitivity, Monte Carlo, Optimization), selected by a top key containing `Analysis`, run by `pyH2A.meta_workflow` *after* the DCF.
- **staging branch** — Jacob's curated integration branch (`staging/plugin-refactor`) into which contributions are *manually re-implemented*, not merged.

---

## 5. Subtleties a UI must respect

1. **Never display a raw number without asking the Quantity for a unit.** Post-#120 a `Value` cell may hold a float *or* a `Quantity`; the resolver rewrites cells in place as the run proceeds, so identity depends on *when* you look (#108, #120).
2. **A path must carry its unit.** Emitting `{A > B > Value}` without `, unit` is a syntax regression against #120.
3. **Absence is meaningful.** Omitting the tilt row means "use latitude" (#57); supplying both `Plant design capacity` and `Design output by year` is an error (#56). A form that emits every field with a blank default will break models.
4. **Workflow positions:** defaults occupy 100–900; user plugins go between (201, 202, 302, 401…). Colliding with a default is silently order-dependent (#84).
5. **Yearly output is a mass/energy, not a rate** (#70). `Plant design capacity` remains per-time — and PR **#179** (open) is *"Production_Plugin: correct the dimension of Plant design capacity"*, so treat that dimension as unsettled.
6. **Array lengths differ by concept.** Production arrays span operation years; DCF arrays span analysis years. `expand_to_analysis_years` bridges them (#138). Plotting a production array on an analysis-year axis will be off by the construction time.
7. **`Life_Cycle_Assessment_Plugin` does not exist.** It is listed in `Defaults_LCA.md` (position 300) and `Defaults_TEA_LCA.md` (position 1000), but there is no such file in `src/pyH2A/Plugins/`. Every shipped end-to-end input uses `Default TEA | pyH2A.Config~Defaults_TEA.md`. **Only the TEA path is runnable today.**
8. **Read the answer at** `dcf.inp['Dependent Variables']['Levelized cost']['Value']` as a Quantity, then `.unit['USD/kg']` or `.unit['USD/kWh']` (`lcoe_test.py`). Breakdown lives at `Levelized cost contributions`, whose dict carries `'Table Group': 'Total Cost of Product'` and a `'Total'`.
9. **`docstring_generation.py` is a free schema.** It already walks `input_dict`/`output_dict` to emit typed, described, optionality-annotated parameter lists — the UI should consume the dicts directly rather than re-describing parameters.

---

## 6. Review style and quality bar (Jacob)

- **Self-merges infrastructure fast, with no reviewers.** #122, #123, #124 each merged ~2 minutes after opening; #44 and #45 within 3 minutes. #151 and #176 — the two largest breaking changes in the arc — have **zero reviews and zero comments**.
- **Closes contributor PRs and re-lands a cleaned version himself.** #80→#122 (*"Cleaned up version of PR #80"*), #81→#123, #55→#124, #60→#98, #148/#149→#176. For branch work he re-implements by hand: #117 and #136 both got *"manually implemented on staging/plugin-refactor"* and were closed unmerged.
- **Blocks on architecture, not style.** The one CHANGES_REQUESTED in the arc (#138) demanded a structural change — *"should only create class attributes, not insertion... deleting pre-workflow"* — and cost three weeks.
- **Style notes are about intent and type guarantees.** *"I would argue it is better to use `np.zeros_like(array)` instead of `0 * array`, since the intent is more clear and the type is guaranteed (np.float64)"* (#138).
- **Answers design questions decisively, and usually enlarges them.** #84 (odd positions → 100/200/300/400), #70 (*"Should be mass only... Larger refactor of production_scaling_plugin is needed"*).
- **Housekeeping is disciplined.** Every closed issue gets a one-line pointer: *"Implemented on staging/plugin-refactor"* (#84, #126), *"Closed by #120"* (#108), *"Implemented in PR #176"* (#142). Merge conflicts must be cleared before he reviews (#96).
- **Praise is specific and public.** *"Very nice work on this change @axfache!"* (#138); *"Good fix"* (#117).
- **Testing bar:** end-to-end levelized-cost tests assert to `abs=1e-13` — *"Very strict tolerance to detect economic regression"* (`lcoe_test.py`). Numerical drift is treated as a defect, which is why #82's constant corrections were called out explicitly.

**Still in flight** (relevant to any UI): #179 (Plant design capacity dimension), #178 (plugins into `Core/Energy/Finance/Hydrogen/Process_Units/Testing` subdirectories — #177 was closed because it targeted master instead of the post-workflow branch), #171 (move `tests/` to repo root), #169/#96 (docs for non-Python users), #157 (reference labels on Quantity), #164 (Quantity memory leak via `lru_cache`), #161 (cache `parse_composite_unit`).