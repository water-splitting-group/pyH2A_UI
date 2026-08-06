# pyH2A finance/core plugin chain — static review (FIN)

Scope: `src/pyH2A/Plugins/{Time,Inflation,Production,Capital_Cost,Replacement,Labor_Operating_Cost,Other_Fixed_Operating_Cost,Variable_Operating_Cost,Discounted_Cash_Flow,Test_Plugin_A,Test_Plugin_B}_Plugin.py` at master a15e7bb. Read-only; nothing executed. Corroborating reads: `Utilities/IO/{input_resolver,output_inserter}.py`, `Utilities/{input_modification,check_functions,find_nearest,functional_unit,docstring_generation,plugin_input_output_processing}.py`, `Unit_Handler/{quantity,config}.py`, `Config/Defaults_TEA.md`, `Lookup_Tables/*.csv`, `tests/end_to_end/*.md`. Deduplicated against `./corpus`.

## Findings table

| id | severity | file:line | one-line summary |
|---|---|---|---|
| FIN-1 | BUG-confirmed-by-reading | Replacement_Plugin.py:239,247,257 | #170 refined: `contributions` disagrees with `yearly_inflated` for **two** independent reasons (construction-year unplanned + no inflation escalation); ~−29% and +C/(C+L) errors |
| FIN-2 | BUG-confirmed-by-reading | Replacement_Plugin.py:290,297 | Planned replacement with frequency ≥ plant life is silently scheduled in the **final** year (find_nearest clamps) instead of never |
| FIN-3 | BUG-confirmed-by-reading | Discounted_Cash_Flow_Plugin.py:545,672; Other_Fixed…:264; Variable…:367 | `int(round(start_up_time))` makes every fractional start-up time (0.5 → 0) a silent no-op for all three start-up fractions |
| FIN-4 | BUG-confirmed-by-reading | Production_Plugin.py:63,166 | `Plant design capacity` is unusable for an energy functional unit (LCOE): spec dimension `energy/time` vs conversion to `kWh_per_year` whose dimension is `power` |
| FIN-5 | BUG-confirmed-by-reading | Production_Plugin.py:58-88,161-168 | Design capacity vs design output are both `optional`: both missing → bare `KeyError` outside the error wrapper; both present → capacity silently ignored |
| FIN-6 | LIKELY-BUG | Other_Fixed_Operating_Cost_Plugin.py:236 | `combined_inflator` applied to *every* Other-Fixed row, including rows defined as a % of already-inflated capital (property tax) → inflator² |
| FIN-7 | LIKELY-BUG | Variable_Operating_Cost_Plugin.py:340-343 | "Other Variable Operating Cost" never receives `Inflation correction`, while utilities do → systematically low by (1+i)^(startup−reference) |
| FIN-8 | BUG-confirmed-by-reading | input_resolver.py:487-495,560-575 + Capital_Cost_Plugin.py:300 | `dcf.inp` is single-use: re-running on an already-processed dict double-counts every `sum_all_tables` group and then crashes on the inserted `Contributions` dict |
| FIN-9 | LIKELY-BUG | Time_Plugin.py:74,86 | `type: {int}` specs are unsatisfiable on any *second* read: the resolver rewrites the cell as a `Quantity` whose `base_value` is float |
| FIN-10 | USABILITY | Variable…:327; Replacement_Plugin.py:233 | An *absent* (not empty) optional table gives a bare `KeyError: 'Utilities'` / `'Planned Replacement'`; empty header-only table is required |
| FIN-11 | USABILITY | Replacement_Plugin.py:100-102,287-297 | Replacement `Frequency` bound is `(0, None)` inclusive → 0 gives `ZeroDivisionError` / `slice step cannot be zero` |
| FIN-12 | BUG-confirmed-by-reading | Inflation_Plugin.py:196-207 | All four inflation index tables stop at 2016 (GDP 2017); `find_nearest` clamps silently, so any modern basis/reference year is silently treated as 2016 |
| FIN-13 | USABILITY | Discounted_Cash_Flow_Plugin.py:56 | Depreciation schedule length silently snaps to the nearest MACRS column (3/5/7/10/15/20) |
| FIN-14 | SMELL | Discounted_Cash_Flow_Plugin.py:73-75 | All depreciation falling past the analysis window is dumped into the final year (late replacements get a full tax shield immediately) |
| FIN-15 | BUG-confirmed-by-reading (doc) | Inflation_Plugin.py:34,156; Other_Fixed…:14 | "Combined inflator" is documented as the **sum** of CEPCI and CI; the code computes the **product** |
| FIN-16 | BUG-confirmed-by-reading (contract) | Labor_Operating_Cost_Plugin.py:18-20 vs 73,81; Other_Fixed…:22 | Labor output keys are `Labor cost` / `Labor cost - inflated`; the docstrings say `Labor Cost` / `Labor Cost - Inflated` / `Labor Cost - inflated` — and docstrings are machine-parsed by the template generator |
| FIN-17 | SMELL | docstring_generation.py:156; all 9 finance plugins | `generate_docstring` (PR #176) is used by **zero** plugins and cannot be used as designed, because `input_dict` is built inside `_set_up` from `dcf.functional_unit` |
| FIN-18 | SMELL | Other_Fixed_Operating_Cost_Plugin.py:210-213 | `special_insertions > Contributions` declares `{int, float}` where a `dict` is inserted (unvalidated, so doc-only) — contradicts Capital/Variable/Replacement |
| FIN-19 | USABILITY | Time_Plugin.py:129; Capital_Cost_Plugin.py:566 | Construction table: fractions never checked to sum to 1, row order is load-bearing, and an empty table yields C=0 with silently zero equity capital |
| FIN-20 | SMELL | Discounted_Cash_Flow_Plugin.py:758-759 | The NPV≈0 self-check uses an **absolute** 1e-6 USD threshold and `print`s to stdout — false positives on large plants, invisible in a UI |
| FIN-21 | SMELL | Discounted_Cash_Flow_Plugin.py:769,517; Test_Plugin_B.py:97-100 | Dead code: computed-and-discarded `revenue`, discarded `calculate_cash_flow()` return, dead `Quantity(200,'g')` default for a declared-optional input |
| FIN-22 | USABILITY | Variable_Operating_Cost_Plugin.py:173-186 | The Utilities unit contract is deliberately fake (`Cost_Unit` must be bare `USD`, `Usage_Unit` `1/kg`); correctness rests on an unchecked `Price_Conversion_Factor` |
| FIN-23 | USABILITY | Production_Plugin.py:161; DCF…:99-100; Variable…:362 | Length of `Design output by year` is never validated against plant life → raw numpy broadcast error two plugins later |
| FIN-24 | SMELL | Production_Plugin.py:93; Other_Fixed…:110-113 | Type/bounds specs for sibling fractions disagree (`{float}` vs `{float,int}`; `(0,1)` vs `(0,None)`) → `1` is a TypeError for one cell and fine for its neighbour |
| FIN-25 | SMELL | Capital_Cost_Plugin.py:558-563,590 | Hidden method-ordering coupling: `calculate_non_depreciable_capital_dcf_inputs` reads attributes set by `calculate_depreciable_capital_dcf_inputs` |
| FIN-26 | UI-FACT | Discounted_Cash_Flow_Plugin.py:640-645 | Debt model: interest is charged in **every** analysis year (construction included) and the whole principal is repaid in the final year |
| FIN-27 | UI-FACT | Discounted_Cash_Flow_Plugin.py:769-787 | Cost contributions provably sum to the levelized cost; `Salvage` is stored negative; a `Taxes` bucket is included; result lives at `Dependent Variables > Levelized cost` |
| FIN-28 | UI-FACT | (whole chain) | Per-plugin map of must-come-from-user vs defaulted inputs, wildcard tables, and downstream consumers |
| FIN-29 | SMELL | Test_Plugin_A.py:222,226; Test_Plugin_B.py:92,94 | Test plugins pass `__name__` (module path) as the plugin name; every other plugin passes the class name → inconsistent error prefixes |
| FIN-30 | SMELL | Time_Plugin.py:132; Discounted_Cash_Flow_Plugin.py:545 | `int(round(...))` truncation of plant life / start-up time is silent and uses banker's rounding |
| FIN-31 | UI-FACT | Labor_Operating_Cost_Plugin.py:102 | 2080 h/yr is hard-coded inside the labor cost; `Staff` normally comes from `Multiple_Modules_Plugin`, not the user |

---

## Detailed findings

### FIN-1 — Replacement contributions vs `yearly_inflated` (refines #170)
**Severity:** BUG-confirmed-by-reading · **Known upstream:** YES — issue #170, but the issue text names only *one* of the two causes.
**Where:** `Replacement_Plugin.py:239` (planned contribution), `:245-249` (unplanned contribution), `:257` (`contributions['Total']`), `:258-263` (`yearly_inflated`).

`self.yearly` is accumulated in *reference-year* dollars: planned events get `cost × non_integer_correction × combined_inflator` at their replacement-year indices (`:238`), unplanned gets added to **every** year of the analysis array including construction (`:246`). `contributions` is snapshotted from that array: per-entry planned totals at `:239`, unplanned as `np.sum(np.ones_like(self.yearly) × unplanned)` at `:247` — i.e. `unplanned × (C + L)` — and `contributions['Total'] = np.sum(self.yearly)` at `:257`. Only afterwards (`:258-263`) is `yearly_inflated` built by multiplying by `Inflation correction × Inflation factor full` and zeroing `[:start_idx]`.

So the two numbers differ for **two independent reasons**, and the issue only mentions the first:
1. **Construction years.** `contributions` counts `C` extra years of unplanned replacement that `yearly_inflated` zeroes. With the standard 2-year construction / 20-year life that is `2/22 ≈ 9%` over-statement of the unplanned bucket.
2. **Inflation escalation.** `contributions` applies neither `Inflation correction` nor the per-year `Inflation factor full`. `yearly_inflated` applies both. With the defaults (1.9% inflation, reference 2016, start-up 2020) the mean escalation over the operating years is `(1/L)·Σ(1+i)^t ≈ 1.20` and the correction is `(1+i)^4 ≈ 1.078`, so `contributions` under-states the actual charge by roughly **29%**.

Which number is wrong: `yearly_inflated` is the authoritative one — it is what `Discounted_Cash_Flow_Plugin.calculate_replacement_costs` NPVs into the levelized cost. `contributions` is the display-only breakdown, and it is wrong on both counts. The clean fix is to derive `contributions` *from* `yearly_inflated` (build the per-entry masks first, apply `inflation_correction × inflation_factor_full`, then zero `[:start_idx]` before summing), which also makes the per-entry numbers comparable to the DCF's own `Replacement costs` contribution.

### FIN-2 — Replacement frequency ≥ plant life schedules a phantom replacement in the last year
**Severity:** BUG-confirmed-by-reading · **Known upstream:** NEW.
**Where:** `Replacement_Plugin.py:290` and `:297`.

``python
initial_replacement_year_idx = fn.find_nearest(plant_years_relative, replacement_frequency)[0]
self.years = plant_years_relative[initial_replacement_year_idx:][0::replacement_frequency]
``
`find_nearest` (`Utilities/find_nearest.py:32-36`) is a clamping nearest-neighbour search on `np.searchsorted`: for a value past the end of the array it returns the **last** index. `plant_years_relative` runs `-C … L-1`, so a component whose replacement frequency exceeds the plant life (e.g. a 25-year stack in a 20-year plant, or any `Frequency` fed by a path such as `{Electrolyzer > Actual stack replacement time > Value, year}` that happens to exceed `Plant life`) is charged one full replacement in the **final operating year**, at `cost × ceil(freq)/freq × combined_inflator`. The physically correct answer is zero replacements. The same clamp silently mis-schedules any frequency between `L-1` and `L`. Guard with `if replacement_frequency > plant_years_relative[-1]: return` (empty `years`/`years_idx`) rather than relying on `find_nearest`.

### FIN-3 — Fractional start-up time silently disables all three start-up fractions
**Severity:** BUG-confirmed-by-reading · **Known upstream:** NEW.
**Where:** `Discounted_Cash_Flow_Plugin.py:545` + `:672-674`; `Other_Fixed_Operating_Cost_Plugin.py:264-269`; `Variable_Operating_Cost_Plugin.py:367-371`.

All three sites compute `start_up_time_idx = start_idx + int(round(start_up_time.unit['year']))` and then multiply the slice `[:start_up_time_idx]` by the start-up fraction, immediately followed by zeroing `[:start_idx]`. Consequences:
* For any start-up time `< 0.5` year, and for exactly `0.5` (Python's `round` is round-half-to-**even**, so `round(0.5) == 0`), `start_up_time_idx == start_idx`. The fraction is then applied only to the construction-year slice, which is zeroed on the very next line. **`Fraction of revenues during start-up`, `Fraction of fixed operating costs during start-up` and `Fraction of variable operating costs during start-up` become complete no-ops.**
* The canonical H2A start-up time is 0.5 year. `Config/Defaults_TEA.md:29` currently ships `Start-up time | 1 | year`, which is why no end-to-end test catches this — the defaults sit exactly on the one value where the code happens to work. A UI that exposes a start-up-time control will hit the broken path the moment a user types 0.5.
* The rounding also means 1.4 years and 1.0 years behave identically, and 1.5 years rounds *down* to 1 while 2.5 rounds down to 2.

The fix is a partial-year weight (`full_years = int(start_up_time)`, remainder applied as a blended factor on the next year) or at minimum `math.ceil` plus an explicit error for non-integer start-up times.

### FIN-4 — `Plant design capacity` cannot work with an energy functional unit
**Severity:** BUG-confirmed-by-reading · **Known upstream:** NEW (adjacent to #144/#149, closed by PR #176, and to the closed dimension issue #70).
**Where:** `Production_Plugin.py:63` (spec) and `:166` (use); `Utilities/functional_unit.py:24-32`.

The input spec declares `"dimension": f"{self.functional_unit.dimension}/time"`, and the code converts with `.unit[self.functional_unit.unit_per_year]`. For `kg` that is `mass/time` and `kg/year` — consistent. For an **energy** functional unit (the LCOE mode added by PR #176, exercised by `PV_E_Electricity_Production_Test.md`) the spec dimension is `energy/time` but `unit_per_year` is `kWh_per_year`, which `Unit_Handler/config.py:65` files under the **power** dimension. `UnitDictionary.__missing__` compares the parsed target dimension (`power`) against the quantity's dimension (`energy / time`) and raises `ValueError: Dimension mismatch`. There is no unit string that satisfies both the spec check and the conversion, so the `Plant design capacity` branch is dead for LCOE — users must supply `Design output by year`. `FunctionalUnit` already carries `dimension_per_time` (= `power` for energy) precisely for this, and `Production_Plugin` simply doesn't use it. Fix: use `self.functional_unit.dimension_per_time` in the spec.

### FIN-5 — Production's capacity/output pair: both-optional with no both-or-neither check
**Severity:** BUG-confirmed-by-reading · **Known upstream:** NEW.
**Where:** `Production_Plugin.py:58-88` (both rows `optional: True`), `:161-168` (dispatch).

`calculate_output` branches on `if 'Design output by year' in operating_parameters`, else indexes `operating_parameters['Plant design capacity']`. Two bad paths:
* **Neither supplied** — a very common first-run mistake — raises a bare `KeyError: 'Plant design capacity'`. Note this happens *after* `input_resolver_function` returns, so it escapes the `[Plugin: …]` error wrapper (`input_resolver.py:686-689`) and the user gets a naked KeyError with no table, row or plugin context (#141 family).
* **Both supplied** — `Design output by year` silently wins and `Plant design capacity` is ignored with no warning, even though the design capacity row is still marked `Processed` so `check_processing` stays quiet.

Also note `Design output by year` is simultaneously an *input* and an *output* of this plugin (`:69` and `:107`): the plugin overwrites the user's row in place (and `insert` sets its `Path` to `'None'`). A UI must treat that row as read-write.

### FIN-6 — Other-Fixed rows that point at already-inflated capital get the inflator twice
**Severity:** LIKELY-BUG · **Known upstream:** NEW (adjacent to #133, which asks the analogous question for variable costs).
**Where:** `Other_Fixed_Operating_Cost_Plugin.py:236-238`; triggered by e.g. `tests/end_to_end/PEC_Base_test.md:161` `Property tax | 2% | {Total Capital Costs > Inflated > Value, USD}`.

`calculate_total_fixed_operating_cost` multiplies the whole `Other Fixed Operating Cost` group total by `Combined inflator`, unconditionally. But the group's rows are user-authored paths, and the shipped examples point one of them at `Total Capital Costs > Inflated`, which `Capital_Cost_Plugin` already multiplied by `Combined inflator`. Property tax therefore carries `combined_inflator²`. (The sibling rows are fine: `Repairs` points at `Direct Capital Cost > Summed group total`, which is the *uninflated* sum, and `G&A` points at `Fixed Operating Costs > Labor cost`, the uninflated labor cost — though that one then receives `combined_inflator` rather than `labor_inflator`, an inconsistency of its own.)

This is invisible today only because the shipped defaults set `Reference year = Basis year = Current year for capital costs = 2016`, making every inflator exactly 1.0. Change the basis year to 2005 and `combined_inflator ≈ 1.3`, so property tax is over-stated by ~30%. Either point the example at `Total Capital Costs > Total` (the uninflated output exists, `Capital_Cost_Plugin.py:375`) or stop re-inflating rows whose path targets an inflated quantity.

### FIN-7 — "Other Variable Operating Cost" misses the inflation correction that utilities get
**Severity:** LIKELY-BUG · **Known upstream:** partially — #133 questions the *semantics* of this bucket (not scaled by production); the inflation asymmetry described here is NEW.
**Where:** `Variable_Operating_Cost_Plugin.py:340-343` vs `:365`, and vs `Other_Fixed_Operating_Cost_Plugin.py:262`.

Utility costs pick up `Inflation correction` inside `Utility.calculate_cost_per_unit_of_product` (`:406`/`:414`). `other_variable_costs` applies only `Chemical inflator`. `calculate_annual_variable_operating_cost` then applies `Inflation factor full` to the sum — so the "other" bucket is the only cost stream in the entire chain that never receives `Inflation correction` (fixed operating costs get it explicitly at `:262` of the Other-Fixed plugin; capital gets it in `Capital_Cost_Plugin.py:557`; replacement at `Replacement_Plugin.py:259`). With the shipped defaults (reference 2016 → start-up 2020, 1.9%) that is a systematic **7.8% under-statement** of other variable operating costs. It goes unnoticed because, as #133 notes, no end-to-end file uses this bucket. Confirm intent, then either add the correction or document why this stream alone is quoted in start-up-year dollars.

### FIN-8 — `dcf.inp` is single-use: a second run on the same dict double-counts, then crashes
**Severity:** BUG-confirmed-by-reading (latent; reachable through the public `discounted_cash_flow_function(inp=<dict>)` API) · **Known upstream:** NEW.
**Where:** `input_resolver.py:487-495` (wildcard row resolver iterates *everything* in `dcf.inp[top_key]`), `:560-575` (group total + `Contributions` insertion), `input_modification.py:936-946` (`sum_table_quantity` inserts `Summed total` into the very table it just summed); `Capital_Cost_Plugin.py:300-310` (output table `Direct Capital Costs`, plural).

Every `sum_all_tables` group mutates `dcf.inp` during resolution: each member table gains a `Summed total` row and the group gains `Summed group total` + `Contributions`. The wildcard row resolver has no exclusion list — it resolves **every** middle key present in the table. Therefore, running `Discounted_Cash_Flow` a second time over an already-processed `inp`:
1. re-sums the injected `Summed total` rows → each capital-cost group is counted **twice**;
2. sweeps the plugin's own output table `Direct Capital Costs` (plural) into the `Direct Capital Cost` (singular) group, because group matching is a plain substring test (`input_resolver.py:558`), adding `Direct Capital Costs > Inflated > Value` as if it were a line item;
3. finally hits `Unplanned Replacement > Contributions > Value`, a dict containing the string `'Replacement Costs'`, and dies in `_create_quantity_and_validate` with `TypeError: Unsupported type <class 'str'>`.

`Discounted_Cash_Flow.__init__` accepts a dict, and `discounted_cash_flow_function` deep-copies whatever dict it is handed — so the hazard is one careless caller away. **For the UI: always re-parse the input file (or deep-copy the pristine, pre-run parsed dict) for every run; never reuse `dcf.inp` from a completed run.** A defensive fix is to skip resolver-inserted middle keys (`Summed total`, `Summed group total`, `Contributions`) in `wildcard_row_resolver_function`, and to stop naming an output table with a superstring of a group key (#101).

### FIN-9 — `type: {int}` specs are unsatisfiable after the first read of a cell
**Severity:** LIKELY-BUG (latent, ordering-dependent) · **Known upstream:** NEW.
**Where:** `Time_Plugin.py:74` and `:86` (`Assumed start-up year`, `Reference year` declared `{int}`); mechanism at `input_resolver.py:355-375` and `Unit_Handler/quantity.py:196`.

`value_with_unit_resolver_function` overwrites the raw cell in `dcf.inp` with the `Quantity` it built. `Quantity.__init__` computes `base_value = supplied_value * multiplier` where the dimensionless multiplier is the **float** `1.0` (`config.py:223`), so an integer year becomes `2020.0`. On any subsequent read, `value_resolver_function` type-checks `value_retrieved.base_value`, i.e. a `float`, against the spec. Today this is masked purely by ordering (Time_Plugin runs at position 100, before anything else touches those cells) and by the fact that `Inflation_Plugin` declares the same `Reference year` cell as `{int, float}` (`Inflation_Plugin.py:86`) — the two plugins disagree about the type of the *same* cell. Insert any plugin before position 100 that reads `Financial Input Values > Reference year` and `Time_Plugin` fails with `TypeError: … Expected (int,), but got <class 'float'>`, which reads like a user error but isn't. Either drop `{int}` in favour of `{int, float}` + an integrality check, or make the resolver preserve integer base values.

### FIN-10 — An omitted optional table is not the same as an empty one
**Severity:** USABILITY · **Known upstream:** NEW (in the #141 "incomprehensible errors" family).
**Where:** `Variable_Operating_Cost_Plugin.py:327`; `Replacement_Plugin.py:233`; mechanism at `input_resolver.py:521-529`.

`table_resolver_function` returns `None` — and `input_resolver_function` then omits the key entirely — when a table whose rows are all `optional` is missing from `dcf.inp`. But both consumers iterate the key unconditionally (`for key in self.input_dict_resolved['Utilities']`, `… ['Planned Replacement']`). So *omitting* `# Utilities` or `# Planned Replacement` raises `[Plugin: Variable_Operating_Cost_Plugin] 'Utilities'`, while including the header with **zero rows** works fine — which is exactly what `PV_E_Electricity_Production_Test.md:87-89` has to do. That is an undiscoverable contract. Use `.get(key, {})` at both call sites (and in any new plugin), or make the resolver return `{}` instead of dropping the key.

### FIN-11 — Replacement frequency of 0 is inside the declared bounds
**Severity:** USABILITY · **Known upstream:** NEW.
**Where:** `Replacement_Plugin.py:100-102` (`"bounds": (0, None)`), consumed at `:287-297`.

`check_bounds` treats bounds as inclusive, so `Frequency = 0` passes validation and then produces `non_integer_correction = 0 / 0.0` → `ZeroDivisionError`, or if the value is an integer 0, `plant_years_relative[idx:][0::0]` → `ValueError: slice step cannot be zero`. Neither message mentions the table, the row, or the plugin. The same inclusive-zero problem applies to any denominator-bearing input. Bounds need an exclusive-lower option, or the plugin needs an explicit `Frequency > 0` check with a located message.

### FIN-12 — Every inflation index table ends in 2016 and lookups clamp silently
**Severity:** BUG-confirmed-by-reading (silently wrong results, not a crash) · **Known upstream:** NEW.
**Where:** `Inflation_Plugin.py:196-207` (`fn.find_nearest` on four tables), data at `Lookup_Tables/{Plant_Cost_Index,Labor_Index,SRI_Chemical_Price_Index}.csv` (last row 2016) and `GDP_Implicit_Deflator_Price_Index.csv` (last row 2017).

`find_nearest` clamps out-of-range values to the last row. `Basis year`, `Reference year` and `Current year for capital costs` are all `bounds: (0, None)` and free-form. A user who enters 2024 gets the 2016 index with no warning, so `CEPCI inflator`, `CI inflator`, `Labor inflator` and `Chemical inflator` silently collapse to ratios among 2016-and-earlier values, and every downstream cost is quoted in the wrong dollar year. **UI implication:** the year inputs must be constrained to the covered range (≤2016, or ≤2017 for the GDP deflator) or the app must surface a loud warning; a naive `st.number_input("Basis year", 2024)` produces a plausible-looking but wrong LCOH. A hard error (or explicit extrapolation) in `Inflation_Plugin` would be the right fix.

### FIN-13 — MACRS schedule length snaps to the nearest available column
**Severity:** USABILITY · **Known upstream:** NEW.
**Where:** `Discounted_Cash_Flow_Plugin.py:56-57`; table header `Lookup_Tables/MACRS.csv:1` = `3 5 7 10 15 20`.

`idx_macrs = find_nearest(macrs[0][1:], depreciation_length)[0]` clamps and rounds: `Depreciation schedule length = 12` silently becomes 10, `25` silently becomes 20, `0` silently becomes 3. The declared bounds `(0, None)` (`:262`) advertise a continuum that does not exist. A UI should expose this as a select box over `{3,5,7,10,15,20}`; the engine should reject anything else.

### FIN-14 — Depreciation past the analysis window is dumped into the final year
**Severity:** SMELL (documented nowhere; materially affects the tax shield) · **Known upstream:** NEW.
**Where:** `Discounted_Cash_Flow_Plugin.py:73-75`.

``python
annual_charge = charge[:end_idx]
annual_charge[-1] += np.sum(charge[end_idx:])
``
`charge` has `len == n_analysis_years + len(macrs_values)`; everything past the horizon (i.e. the depreciation of replacements made near end of life, which under MACRS would run for another 20 years) is added to the last operating year. That is a deliberate no-stranded-basis choice, but it front-loads a potentially large deduction into a single year, and it interacts with FIN-2 (a phantom final-year replacement gets its entire depreciation schedule recognised immediately). Worth an explicit comment and a maintainer decision; a UI showing an annual depreciation chart will render a conspicuous final-year spike that is not a rendering bug.

### FIN-15 — "Combined inflator" is documented as a sum, computed as a product
**Severity:** BUG-confirmed-by-reading (documentation/contract) · **Known upstream:** NEW.
**Where:** `Inflation_Plugin.py:225-227` (code: `cepci × ci`), `:34` (class docstring: "Sum of CEPCI and CI inflation factors"), `:156` (the `output_dict` description, same wrong wording), and it has already propagated to `Other_Fixed_Operating_Cost_Plugin.py:14` ("sum of CEPCI and CI inflation factors").

Because the `output_dict` `description` is the string PR #176's generator would emit into docs (FIN-17) and is what a UI would show as help text, the lie is load-bearing, not cosmetic. It also matters numerically: with a 1996 basis year the sum would be ≈2.6 and the product ≈1.7.

### FIN-16 — Labor cost key names disagree across code, docstrings, and example inputs
**Severity:** BUG-confirmed-by-reading (contract) · **Known upstream:** partially — naming issues #83/#101 cover the general problem; these specific mismatches are NEW.
**Where:** `Labor_Operating_Cost_Plugin.py:73`/`:81` insert `Labor cost` and `Labor cost - inflated`; its own docstring `:18`/`:20` advertises `Labor Cost` and `Labor Cost - Inflated`; `Other_Fixed_Operating_Cost_Plugin.py:22` advertises `Labor Cost - inflated` while its `input_dict:124` correctly requests `Labor cost - inflated`.

Three spellings for two cells. This is not cosmetic: `Utilities/plugin_input_output_processing.py:38-72` **parses these docstrings** to build input templates (`Generate_Template_Input_File`, wired to the CLI in `cli_pyH2A.py:3`). `check_parameters` matches requirement strings against output strings **exactly**, so the generator concludes that `Fixed Operating Costs > Labor Cost - inflated > Value` is unfulfilled and emits it as a user-supplied field in the template — a field that, if filled in, does nothing. Legacy inputs under `src/pyH2A/Example/` (e.g. `210511_Future_PEC_Type_4.md:170`) still reference `Fixed Operating Costs > Labor Cost > Value` and are therefore broken against master; the maintained tests (`PEC_Base_test.md:157`) use the correct `Labor cost`.

### FIN-17 — The docstring generator from PR #176 is not wired into a single plugin
**Severity:** SMELL (the premise "post-#176 docstrings are generated from the dicts" is false) · **Known upstream:** NEW.
**Where:** `Utilities/docstring_generation.py:156`; zero call sites outside `src/tests/Utilities/Docstring_Generation/docstring_generation_test.py`.

`generate_docstring` exists, is tested in isolation, and documents the intended usage `__doc__ = generate_docstring(summary, input_dict, output_dict)` at class-definition time. But every finance plugin builds `input_dict`/`output_dict` **inside `_set_up(self, dcf)`**, deriving dimensions from `dcf.functional_unit` — they do not exist at class-definition time, so the documented pattern cannot be applied without restructuring (e.g. a module-level `build_input_dict(functional_unit)` helper called both by `_set_up` and by a `__init_subclass__`/module-import-time doc build for a default unit). Until then every docstring is hand-maintained and drift is guaranteed — FIN-15, FIN-16 and the notation drift below are the current instances. Notation is also inconsistent between the two conventions the generator emits (`<...>` / `>>`) and the old one (`[...]`): `Time_Plugin.py:15` and `Capital_Cost_Plugin.py:20` use `Construction > [...] > Value`, `Replacement_Plugin.py:20` uses `[...] Unplanned Replacement [...]`, while `Capital_Cost_Plugin.py:24` uses `<...> Direct Capital Cost <...> >>`. `Variable_Operating_Cost_Plugin.py:35` also mis-documents the `Cost_Path`/`Usage_Path` columns as mandatory-but-empty, whereas `Testing_Plugin_IO.md:127` omits them entirely and works (`process_input` swallows the missing-path `KeyError` at `input_modification.py:843`).

### FIN-18 — `special_insertions` type specs are wrong and unvalidated
**Severity:** SMELL · **Known upstream:** NEW.
**Where:** `Other_Fixed_Operating_Cost_Plugin.py:210-213` declares `Other Fixed Operating Cost > Contributions > Value` as `{int, float}`; the resolver actually inserts the contributions **dict** (`input_resolver.py:571-574`). Compare `Capital_Cost_Plugin.py:439`, `Variable_Operating_Cost_Plugin.py:297`, `Replacement_Plugin.py:199` which all correctly say `{dict}`.

`output_inserter_function` skips the whole `special_insertions` top key (`output_inserter.py:14,268`), so nothing ever checks these specs — they are pure documentation that the (intended) generator would print. One of them is simply false. Either validate them or stop pretending they're specs.

### FIN-19 — The Construction table is under-specified and order-sensitive
**Severity:** USABILITY · **Known upstream:** NEW.
**Where:** `Time_Plugin.py:129` (`construction_time_years = len(...)`), `Capital_Cost_Plugin.py:566-573` (`for counter, key in enumerate(...)` indexed against `inflation_factor_full[counter]`).

Three traps for anyone authoring input (and for a UI that lets users add rows):
* **The number of rows *is* the construction duration.** A stray row — a "Total" line, a note row — silently lengthens construction by a year, shifting every year index in the model.
* **Row order is load-bearing.** Fractions are zipped positionally against `inflation_factor_full`, so listing "3rd year, 2nd year, 1st year" silently mis-escalates capital with no error.
* **The fractions are never checked to sum to 1.** Each is bounds-checked to `(0,1)` individually; a table summing to 0.9 silently under-spends 10% of the depreciable capital, and the resulting LCOH is simply wrong.
* An **empty** Construction table (header only) is accepted: `C = 0`, `construction_years == []`, `initial_equity_depreciable_capital == 0`, and the levelized cost comes out far too low with no diagnostic — while `Depreciable Capital Costs > Inflation corrected` (and hence the debt-financed portion and the depreciation base) stay non-zero. A `sum ≈ 1` assertion plus a non-empty check in `Time_Plugin` would close all of these.

### FIN-20 — The DCF's own consistency check is mis-scaled and prints to stdout
**Severity:** SMELL · **Known upstream:** NEW.
**Where:** `Discounted_Cash_Flow_Plugin.py:756-759`.

The after-tax post-depreciation cash flow must NPV to zero by construction — this is the invariant that makes the cost contributions sum to the levelized cost (FIN-27). The check compares an **absolute** residual against `1e-6` USD. For a plant with ~1e8–1e9 USD flows, float64 accumulation error over ~22 discounted terms is of order 1e-7–1e-6 USD, so the warning is on the edge of firing on healthy models and cannot detect a genuine 1e-3-relative error on a small one. It should be relative (e.g. `abs(npv) > 1e-9 * max(abs(cash_flow))`). Separately, it `print`s: in a Streamlit/stlite wrapper this vanishes into the server log. It should raise or be surfaced as a returned diagnostic. (`calculate_cash_flow`'s return value is discarded as well — see FIN-21.)

### FIN-21 — Dead code that hides intent
**Severity:** SMELL · **Known upstream:** NEW.
* `Discounted_Cash_Flow_Plugin.py:769` — `revenue = self.expenses_per_functional_unit_of_product(self.npv_dict['revenue'])` is computed and never used. It is in fact the exact cross-check for FIN-27 (it must equal `product_cost`); either assert on it or delete it.
* `Discounted_Cash_Flow_Plugin.py:517` / `:763` — `calculate_cash_flow()` returns the NPV of the cumulative cash flow; the caller ignores it. The cumulative cash-flow series is exactly what a UI would plot, and it is thrown away.
* `Test_Plugin_B.py:97-100` — `mass = Quantity(200, 'g')` is immediately overwritten by `self.inp['Plugin B Input']['Mass']['Value']`. `Mass` is declared `optional: True` (`:43`), so the resolver omits the row when absent and the plugin dies with `KeyError: 'Mass'`. The dead line is clearly the intended default; as written the optional flag is a lie.
* `Discounted_Cash_Flow_Plugin.py:671` — `self.annual_sales = self.output_per_year_at_gate` aliases rather than copies and is then mutated in place; harmless today only because `expand_to_analysis_years` returns a fresh array, but the two attribute names now describe the same, start-up-scaled object.

### FIN-22 — The Utilities unit contract is intentionally fake, and nothing checks the fudge factor
**Severity:** USABILITY · **Known upstream:** related to #89 (10000.12 USD/kWh grid cost) — the mechanism described here is NEW.
**Where:** `Variable_Operating_Cost_Plugin.py:173-175` (`Cost_Unit` dimension `currency`, with a comment saying the basis is omitted on purpose), `:180` (`Usage_Unit` dimension `1/{functional_unit.dimension}`), `:398-420` (`Utility`).

A user's honest units are rejected: `Cost_Unit = USD/kWh` fails the `currency` dimension check, and `Usage_Unit = kWh/kg` fails the `1/mass` check. The working incantation, per `PEC_Base_test.md:175`, is `Usage 0.16 [1/kg]`, `Cost <file> [USD]`, `Price_Conversion_Factor 0.0036 [-]` — i.e. the physical basis (kWh) is erased from both factors and reintroduced as an unchecked scalar. Consequences: (a) the unit system, the project's main safety net, provides **zero** protection on the single largest operating cost line; (b) a wrong `Price_Conversion_Factor` is undetectable, which is exactly the failure mode #89 is complaining about; (c) a UI cannot offer users a normal unit picker for utilities. Recommend giving `Cost`/`Usage` real reciprocal dimensions (`currency/X` and `X/functional_unit`) and dropping the conversion factor, which the unit handler can then verify.

Secondary, same area: when `Cost_Value` is a file path, `find_nearest(prices, operation_years)` (`:404`) clamps past the end of the price series, so operating years beyond the file's last year silently reuse the final price.

### FIN-23 — `Design output by year` length is never validated
**Severity:** USABILITY · **Known upstream:** related to #87 (float-vs-array shape of the output series) — the missing length check is NEW.
**Where:** `Production_Plugin.py:161-176` (array passed through untouched), `Discounted_Cash_Flow_Plugin.py:99-100` (`full[start_idx:] = operation_array`), `Variable_Operating_Cost_Plugin.py:362-363` (same pattern).

Nothing anywhere checks `len(design_output_by_year) == plant_life_years`. A user (or an upstream plugin such as `Electrolyzer_Plugin`) supplying a 25-element series for a 20-year plant gets `ValueError: could not broadcast input array from shape (25,) into shape (20,)` raised from inside `expand_to_analysis_years`, several plugins away from the offending table, with no mention of the row. `Production_Plugin` is the natural place to assert this (it already has `Operation years ones` in hand).

### FIN-24 — Sibling fraction inputs disagree about type and bounds
**Severity:** SMELL · **Known upstream:** NEW.
* `Production_Plugin.py:93` — `Fraction of output that reaches gate` accepts `{float}` only, while its neighbour `Operating capacity factor` (`:78`) accepts `{float, int}`. A user writing `1` instead of `100%` or `1.0` gets `TypeError: … Expected (float,), but got <class 'int'>` for one cell and no complaint for the other.
* `Other_Fixed_Operating_Cost_Plugin.py:110-113` — `Fraction of fixed operating costs during start-up` is bounded `(0, None)`, while the corresponding variable-cost (`Variable_Operating_Cost_Plugin.py:135`) and revenue (`Discounted_Cash_Flow_Plugin.py:326`) fractions are bounded `(0, 1)`. Nothing about fixed costs justifies allowing 400%.
* `Discounted_Cash_Flow_Plugin.py:335` — `Decommissioning costs (fraction of depreciable capital investment)` is `(0, None)` while `Salvage value (fraction of total capital investment)` is `(0, 1)`.

These are the specs a UI will render as widgets; they should agree.

### FIN-25 — Capital_Cost's two DCF-input methods are coupled through instance attributes
**Severity:** SMELL · **Known upstream:** NEW.
**Where:** `Capital_Cost_Plugin.py:552-556` sets `self.analysis_years_ones`, `self.inflation_factor_full`, `self.inflation_correction`; `:585-595` (`calculate_non_depreciable_capital_dcf_inputs`) reads all three but never fetches them.

Calling the second method without the first (a plausible move for anyone driving the plugin from a notebook or reusing it in a UI) raises `AttributeError`. Both should read from `self.input_dict_resolved` directly, or the shared lookups should move to `_run`.

### FIN-26 — Debt model: interest during construction, bullet principal repayment
**Severity:** UI-FACT (with a maintainer question attached) · **Known upstream:** NEW.
**Where:** `Discounted_Cash_Flow_Plugin.py:636-645`.

`interest_per_year = analysis_years_ones × interest` charges interest in **every** year of the analysis, construction years included, and `principal_payment[-1] = debt_financed_capital` repays the entire principal in the final year (there is no amortisation). During construction there is no revenue, so the interest produces negative taxable income and therefore a tax credit in the cash flow (`:734-741`). This is the H2A "constant debt" convention, but nothing in the docstring says so; a UI showing an annual cash-flow table needs to explain the final-year principal spike and the pre-operation tax credits, and maintainers should confirm that construction-period interest is intended (H2A's own workbook capitalises it).

### FIN-27 — Cost contributions provably sum to the levelized cost (and what the buckets mean)
**Severity:** UI-FACT · **Known upstream:** N/A.
**Where:** `Discounted_Cash_Flow_Plugin.py:766-802`.

Algebraically, from the NPV-zero cash-flow identity (`:747-756`) and `revenue_npv = price_nominal × npv_sales × (1+i)^(−C)`, the eleven `contributions['Data']` entries sum **exactly** to `contributions['Total'] == product_cost`. A UI can therefore render them as a waterfall/stacked bar with no residual bucket, but must know:
* `Salvage` is stored **negative** (`sign='negative'`, `:775`); everything else is positive.
* There is a `Taxes` bucket — it is not folded into the other lines.
* `Working capital reserve` is a net-of-recovery NPV and is normally small and positive.
* The identity holds only while the NPV-zero invariant holds; the guard on that invariant is the mis-scaled `print` of FIN-20, so a UI should re-check `abs(sum(contributions) − product_cost)` itself.
* Result locations: `dcf.inp['Dependent Variables']['Levelized cost']['Value']` (a `Quantity` in `USD/<functional unit>`) and `['Levelized cost contributions']['Value']` (dict with `Data` / `Total` / `Table Group`). Instance attributes `plugs['Discounted_Cash_Flow_Plugin'].{product_cost, contributions, npv_dict}` carry the same data plus every intermediate NPV. Note `Discounted_Cash_Flow.py:13-14` still defaults `discounted_cash_flow_function` to the pre-#176 `attribute='h2_cost'` and `'{Dependent Variables > Levelized Cost > Value, USD/kg}'` (capital "Cost") — both now dead paths (meta-layer scope, flagged here because it is the API a UI would reach for).

### FIN-28 — Per-plugin UI map: what must come from the user, what is defaulted, what is a wildcard table
**Severity:** UI-FACT · **Known upstream:** N/A.

Everything in `Config/Defaults_TEA.md` is merged in via `# Input files to merge` and needs **no** user input: the whole `Financial Input Values` block (reference/basis/start-up/current-capital-cost years, plant life, depreciation length, equity fraction, debt interest, the three start-up fractions, decommissioning, salvage, inflation, IRR, federal/state taxes, working capital), plus the `Workflow` positions 100–900 and `Functional Unit = kg`.

| plugin (position) | user MUST supply | wildcard (add-rows) tables | key outputs consumed downstream |
|---|---|---|---|
| Time (100) | `# Construction` table — one row per construction year, values must sum to 1 (FIN-19) | `Construction > <...>` | `Time > Years > Value` dict (`Plant years relative`, `Operation years`, `Start index`, `*_ones`) — read by **every** later plugin |
| Inflation (200) | nothing (years defaulted; must stay ≤2016, FIN-12) | — | `Inflation > {Inflation factor full, Inflation correction, CEPCI/CI/Combined/Labor/Chemical inflator}` |
| Production (300) | exactly one of `Plant design capacity` **or** `Design output by year`, plus `Operating capacity factor` and `Fraction of output that reaches gate` | — | `Technical Operating Parameters and Specifications > {Design output by year, Output at gate by year, Total design output, Total output at gate}`; `Output at gate by year` → DCF, `Design output by year` → Variable OpEx, Reverse Osmosis, Electrolyzer chain |
| Capital_Cost (400) | `Non-Depreciable Capital Costs > {Cost of land, Land required}` (both **required**, even if zero); at least one `Direct Capital Cost` table | `<...> Direct Capital Cost <...>`, `<...> Indirect Capital Cost <...>`, `<...> Other Non-Depreciable Capital Cost <...>` — whole *tables* are the repeatable unit, each with arbitrary rows | `Depreciable Capital Costs > {Total, Inflated, Inflation corrected, Initial equity, Annual equity}`, `Non-Depreciable Capital Costs > {Total, Inflated, Inflation corrected, Annual}`, `Total Capital Costs > {Total, Inflated}`, `<group> > Summed group total` (referenced by user paths in operating-cost tables) |
| Replacement (500) | `# Planned Replacement` and `# Unplanned Replacement` may be empty **but must exist** (FIN-10) | `Planned Replacement > <...>` (columns `Cost_Value/Cost_Unit/Cost_Path`, `Frequency_Value/Frequency_Unit/Frequency_Path`), `<...> Unplanned Replacement <...>` | `Replacement > Total` (full-analysis ndarray) → DCF; `Replacement > Contributions` → display only (broken, FIN-1) |
| Labor (600) | `Fixed Operating Costs > Hourly labor cost`; `Staff` is normally produced by `Multiple_Modules_Plugin` (position 401) — without it the user must supply `Staff` | — | `Fixed Operating Costs > {Labor cost, Labor cost - inflated}` (note lowercase, FIN-16) |
| Other_Fixed (700) | `# Other Fixed Operating Costs` tables (may be empty) | `<...> Other Fixed Operating Cost <...>` | `Fixed Operating Costs > {Total, Annual}` → DCF |
| Variable (800) | `# Utilities` (may be empty but must exist) | `Utilities > <...>` (9 columns, FIN-22), `<...> Other Variable Operating Cost <...>` | `Variable Operating Costs > {Total, Utilities, Other, Annual}` → DCF |
| DCF (900) | nothing beyond the defaults | — | `Dependent Variables > {Levelized cost, Levelized cost contributions}` |

Other facts a UI must respect: **row order matters** inside `Construction` and inside a `sum_all_tables` group (`Discounted_Cash_Flow.py` docstring, "Order in the input file"); **table-group membership is a substring test**, so naming a table `# Direct Capital Costs - PV` joins the `Direct Capital Cost` group automatically (and `# … Costs` plural collides with the plugin's own output table, FIN-8); a cell may hold either a number or a `{Top > Middle > Bottom, unit}` path, and a `*_Path` column **multiplies** the value cell; `%` and thousands separators are accepted; and `check_processing` prints a warning for any table no plugin touched, which is the only feedback a user gets for a misspelled table name.

### FIN-29 — Test plugins identify themselves differently from every other plugin
**Severity:** SMELL · **Known upstream:** NEW.
**Where:** `Test_Plugin_A.py:222,226` and `Test_Plugin_B.py:92,94` pass `__name__` (i.e. `pyH2A.Plugins.Test_Plugin_A`) to `input_resolver_function`/`output_inserter_function`; all nine finance plugins pass the bare class name string. Error prefixes (`[Plugin: …]`) therefore differ in shape between test and production plugins, which undermines the tests as a template for plugin authors.

### FIN-30 — Silent `int(round(...))` truncation of durations
**Severity:** SMELL · **Known upstream:** NEW.
**Where:** `Time_Plugin.py:132` (`Plant life`), `Discounted_Cash_Flow_Plugin.py:545` (`Start-up time`), plus the four `int(round(Start index))` sites.

`Plant life = 20.6 year` silently becomes 20; `20.5` becomes 20 (round-half-to-even) while `21.5` becomes 22. The spec allows `{int, float}` with dimension `time`, so a user can legitimately write `240 month` — which converts to 20.0 and works — or `250 month` (20.83) and silently lose 10 months. Either round explicitly with a warning or require integral years.

### FIN-31 — Labor cost internals a UI must surface
**Severity:** UI-FACT · **Known upstream:** the ambiguity of `Hourly labor cost` was #63 (CLOSED).
**Where:** `Labor_Operating_Cost_Plugin.py:102-107`.

Annual labor cost = `Staff × Hourly labor cost × 2080 h`, with 2080 h/yr (40 h × 52 wk) hard-coded and not exposed as an input. `Staff` is a *full-time-equivalent* count, and in every shipped example it is computed by `Multiple_Modules_Plugin` from solar collection area, supervisors and the number of 8-hour shifts — so a UI that offers a "number of staff" field must either drop `Multiple_Modules_Plugin` from the workflow or accept that its own value will be overwritten (position 401 runs before Labor at 600).
