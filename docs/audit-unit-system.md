# UNIT SYSTEM AUDIT — pyH2A @ a15e7bb

Scope: `Utilities/Unit_Handler/quantity.py`, `Utilities/Unit_Handler/config.py`, `Utilities/functional_unit.py`, and every `Quantity` / `base_value` / `.unit[...]` site in `src/pyH2A`. Read-only static review; nothing executed.

**Headline.** The unit system is a string-rewriting engine, not a dimensional-algebra engine. `parse_composite_unit` concatenates per-token multipliers and per-token dimension *names* preserving the user's exact operator layout, and `check_dimension` / `UnitDictionary.__missing__` then compare those strings with `!=` after stripping spaces only. Numbers therefore convert correctly while dimensions compare *textually*: `energy / time` ≠ `power`, `volume / (length * substance)` ≠ `volume / length / substance`, `1/mass` ≠ `1.0/mass`. Two confirmed dead code paths fall out of this (UNIT-2, UNIT-3), and it is the root cause of most of the rest.

## Findings table

| id | severity | file:line | one-line summary | known upstream? |
|---|---|---|---|---|
| UNIT-1 | BUG-confirmed-by-reading | check_functions.py:37; quantity.py:148-152 | Dimension equality is string comparison, so physically identical units are rejected | NEW (root cause behind #179, #116-class bugs) |
| UNIT-2 | BUG-confirmed-by-reading | Photocatalytic_Plugin.py:277 vs :505 | Molar Attenuation Coefficient is unusable: spec uses parenthesised dimension, code requests flat one | NEW |
| UNIT-3 | BUG-confirmed-by-reading | Production_Plugin.py:64,166 | Energy functional unit is broken: spec says `energy/time`, code asks for `kWh_per_year` (dimension `power`) | PR #179 (open) — extended below |
| UNIT-4 | LIKELY-BUG | config.py:52-68 | `X_per_day`/`X_per_year` pseudo-units create a second, incompatible spelling of every energy rate | NEW |
| UNIT-5 | BUG-confirmed-by-reading | config.py:123 | `EUR: 0.8` is a hardcoded, undated, and currently wrong FX rate with no override path | NEW |
| UNIT-6 | SMELL | config.py:36-37, 89-90, 209 | `acre` matches no standard acre definition; `eV` truncated while `e` is exact CODATA | Adjacent to PR #139 (rationale), NEW as defect |
| UNIT-7 | LIKELY-BUG | quantity.py:41-43, 53-57, 71-75 | Adjacent tokens silently concatenate into a bogus multiplier (`'m 2'` → 1.02); `**` accepted; `1/month` comment refers to a nonexistent unit | NEW |
| UNIT-8 | LIKELY-BUG | config.py:241-242; quantity.py:59-60 | Temperature cannot appear in any composite unit — `K`/`degC` are absent from `FLAT_MULTIPLIERS` | NEW |
| UNIT-9 | USABILITY | quantity.py:136-137 vs :149; quantity.py:186 | Three different exception types for three flavours of bad unit; none mentions the input location | #141 (extends) |
| UNIT-10 | LIKELY-BUG | input_resolver.py:349 → quantity.py:186 | Missing `Unit` column yields `AttributeError: 'NoneType' object has no attribute 'strip'` | #141 (extends) |
| UNIT-11 | SMELL | quantity.py:168-175 | No `__eq__`/`__hash__`: identity hashing feeds the `lru_cache` leak and makes value comparison silently false | #152, PR #164, PR #161 |
| UNIT-12 | SMELL | quantity.py:104-109, 155-157 | Every `Quantity` is a reference cycle and carries an unbounded per-instance ndarray conversion cache | Adjacent to #152, NEW |
| UNIT-13 | SMELL | quantity.py:164-223 | No arithmetic operators at all; `ndarray * Quantity` fails with an opaque numpy error | NEW |
| UNIT-14 | LIKELY-BUG | quantity.py:108 | `unit[supplied_unit]` hands back the caller's ndarray uncopied — in-place mutation corrupts the Quantity | NEW |
| UNIT-15 | SMELL | quantity.py:213-223; check_functions.py:38,55 | `__repr__` docstring contradicts its behaviour; error messages interpolate whole arrays | #141 (extends) |
| UNIT-16 | LIKELY-BUG | input_modification.py:936-941, 1008-1015 | Table sums add `base_value` with no dimension check — mixed-dimension tables sum silently | NEW |
| UNIT-17 | LIKELY-BUG | input_modification.py:1052-1063 | `retrieve_base_unit` returns `None` or raises `KeyError` for any composite dimension | NEW |
| UNIT-18 | LIKELY-BUG | input_modification.py:200-212 | `num()` strips every comma, so `'1,5'` becomes `15`; empty string raises `IndexError` | NEW |
| UNIT-19 | USABILITY | Variable_Operating_Cost_Plugin.py:174,182 | Utility cost/usage units are deliberately dimension-lossy; a 1000× unit error is undetectable | #133 (adjacent, extends) |
| UNIT-20 | UI-FACT | quantity.py:104-157 | Exact display recipe, plus: `in` and `.get()` on `.unit` do **not** trigger conversion | NEW |
| UNIT-21 | UI-FACT | config.py (whole) | Complete supported-unit list; notable absences: `%`, `min`, `t`, `BTU`, `gal`, `kPa`, `mW`, any currency but USD/EUR | NEW |
| UNIT-22 | SMELL | Photocatalytic_Plugin.py:498 | `'1/hour'` is already fixed to `'1/h'` in master; the issue is still open | #116 — close it |
| UNIT-23 | LIKELY-BUG | Discounted_Cash_Flow.py:12-13,83 | Public wrapper defaults hardcode `USD/kg` and the removed `h2_cost` attribute | Adjacent to known meta breakage; NEW for the unit half |
| UNIT-24 | SMELL | quantity.py:207 | `base_value = value * multiplier` always floats an int, so an `{int}`-only type spec can never be satisfied from markdown | NEW |
| UNIT-25 | SMELL | Stored_Power_Electrolysis_Plugin.py:248; Electrolyzer_Plugin.py:240; Reverse_Osmosis_Plugin.py:146-147 | Physical constants hardcoded as bare floats, bypassing the unit system | NEW |
| UNIT-26 | UI-FACT | Unit_Handler test dir | `quantity_test.py` exists but pins the *broken* behaviour as correct (parenthesised dimension string) | NEW |

---

## UNIT-1 — Dimension equality is string comparison, not physical equivalence
**Severity:** BUG-confirmed-by-reading · **Where:** `Utilities/check_functions.py:37`; `Utilities/Unit_Handler/quantity.py:148-152` · **Known upstream?** NEW as a root-cause report (PR #179 patches one symptom)

`parse_composite_unit` (quantity.py:41-81) tokenises the unit string on `* / ( )` and whitespace, replaces each unit token with its dimension *name*, and rejoins with `" ".join(...)` — preserving the user's operator layout verbatim. `check_dimension` then does `value.dimension.replace(' ','') != expected_dimension.replace(' ','')`, and `UnitDictionary.__missing__` does the identical comparison before allowing a conversion. There is no normalisation, no canonical ordering, no exponent folding, and no dimensional reduction. Consequences, all reachable from ordinary input files:

- `'kWh/m2/day'` → `energy / area / time`; a plugin declaring `power / area` (Hourly_Irradiation_Plugin.py:166,175,184; PEC_Plugin.py:171; Photocatalytic_Plugin.py:303; Solar_Thermal_Plugin.py:69) rejects it. Solar resource is conventionally published in kWh/m²/day, so the most natural spelling of "mean solar input" is refused while `W/m2` is required.
- `'L/(cm*mol)'` → `volume / ( length * substance )`; `'L/cm/mol'` → `volume / length / substance`. Same physics, different strings, mutually unconvertible (this is UNIT-2).
- `'1.0/kg'` → `1.0 / mass` ≠ `1/mass`, so a user who writes `1.0/kg` instead of `1/kg` for a Utilities usage unit is rejected with a dimension error.
- Product ordering matters: `'kg*m'` → `mass * length`, `'m*kg'` → `length * mass`.

The fix is to reduce every parsed unit to a canonical exponent vector over base dimensions (a small `dict[str,int]`) and compare *that*, keeping the pretty string only for display. That single change also closes UNIT-2, UNIT-3, UNIT-4 and removes the need for the `_per_year` pseudo-units. Note the existing test suite actively pins the broken behaviour: `src/tests/Utilities/Unit_Handler/quantity_test.py:19-23` asserts `dim == "( energy * length ) / area"`, so a canonicalisation fix must update that test.

## UNIT-2 — Photocatalytic "Molar Attenuation Coefficient" is unreachable in both spellings
**Severity:** BUG-confirmed-by-reading · **Where:** `Plugins/Photocatalytic_Plugin.py:277` (spec) vs `:505` (use) · **Known upstream?** NEW

The input spec declares `"dimension": "volume / (length * substance)"` (line 277). The consuming code at line 505 asks for `...['Value'].unit['liter/cm/mol']`, whose parsed dimension is `volume / length / substance`. Under UNIT-1's string comparison these never match, so the feature is dead in both directions: a user who writes `L/(cm*mol)` passes `check_dimension` at resolve time and then hits `ValueError: Dimension mismatch` inside `UnitDictionary.__missing__` at line 505; a user who writes `L/cm/mol` is rejected earlier by `check_dimension`. Because the row is `optional: True` (line 279) nobody has tripped it, but the entire homogeneous-catalyst absorbance branch (lines 502-508: `Absorbance`, `Absorbed light`) is unreachable. Minimal fix without touching the parser: change line 277 to `"volume / length / substance"`.

## UNIT-3 — Energy functional unit is broken in Production_Plugin, and PR #179 only half-fixes it
**Severity:** BUG-confirmed-by-reading · **Where:** `Plugins/Production_Plugin.py:64` and `:166`; `Utilities/functional_unit.py:25-32` · **Known upstream?** YES — PR #179 (open, BLOCKED)

`resolve_functional_unit` special-cases energy: `dimension_per_time = 'power'`, `unit_per_year = unit + '_per_year'` (functional_unit.py:25-28). Production_Plugin ignores `dimension_per_time` and builds its own string at line 64: `f"{self.functional_unit.dimension}/time"` → `energy/time`. Line 166 then calls `.unit[self.functional_unit.unit_per_year]` → `.unit['kWh_per_year']`, and `kWh_per_year` is registered under **power** (config.py:65). So with a `kWh` functional unit the plugin is unusable either way: supply `MW` and `check_dimension` rejects it against `energy/time`; supply `MWh/year` and it passes resolution, then `UnitDictionary.__missing__` raises `Dimension mismatch: original 'energy / time', requested 'power'` at line 166. PR #179's substitution of `self.functional_unit.dimension_per_time` is correct and should be merged.

Two extensions the maintainers should fold in:
1. **#179 is necessary but not sufficient.** After it lands, an energy plant *must* be specified in a power unit (`MW`); `MWh/year` — the standard way an energy plant's annual output is quoted, and what the row description at line 67 ("functional unit of product / time") promises — is still rejected. Only UNIT-1's canonicalisation fixes that.
2. **`f'{dimension}/time'` string-building audit.** I grepped the whole tree; Production_Plugin.py:64 is the only remaining site. But `functional_unit.unit_SI_per_s` (functional_unit.py:11,27,31) has **zero** consumers anywhere outside `tests/Utilities/Functional_Unit/functional_unit_test.py`, and `dimension_per_time` has zero consumers in `src/pyH2A` at all. Dead fields on a frozen dataclass that only tests exercise are a trap — either wire them in or delete them.
3. **Functional-unit genericity is incomplete beyond Production_Plugin.** `Reverse_Osmosis_Plugin.py:49` hardcodes `"dimension": "mass"` for `Design output by year`, and `:149` calls `.unit['kg']`; `PEC_Plugin.py:64`, `Photocatalytic_Plugin.py:97` and `Solar_Thermal_Plugin.py:43` hardcode `mass/time` for Plant design capacity. Any non-mass functional unit breaks these too.

## UNIT-4 — `_per_day` / `_per_year` pseudo-units split every energy rate into two incompatible islands
**Severity:** LIKELY-BUG · **Where:** `Utilities/Unit_Handler/config.py:52-68` · **Known upstream?** NEW

The power dimension registers 22 synthetic tokens (`J_per_day` … `TWh_per_year`) whose numeric factors are correct (`kWh_per_year` = 1e3/(24·365) W = 0.11416 W ✓; `Wh_per_day` = 1/24 W ✓, consistent with `year = 31536000 s` at config.py:116). But they are a parallel spelling of things the composite parser already expresses: `kWh_per_year` (dimension `power`) and `kWh/year` (dimension `energy / time`) denote the same physical quantity and are mutually unconvertible under UNIT-1. This is precisely the trap Production_Plugin fell into. They also break the naming convention of every other unit (underscore-English instead of symbols), are undiscoverable, and are asymmetric (`TWh_per_year` exists, `TWh_per_day` does not; `MWh_per_day` exists, `mW` does not exist at all). Once dimensions are canonicalised these 22 entries can be deleted outright.

## UNIT-5 — `EUR: 0.8` is a hardcoded, undated, and currently wrong exchange rate
**Severity:** BUG-confirmed-by-reading · **Where:** `Utilities/Unit_Handler/config.py:123` · **Known upstream?** NEW

`"EUR": 0.8  # Exchange rate should be adjusted via an API or manually when needed`. A cost entered as `100 | EUR` silently becomes `base_value = 80` USD. Beyond staleness the rate is on the wrong side of parity — EUR has traded above USD for essentially the entire life of this repo, so any EUR input is wrong by roughly 30% in the direction that *understates* cost. There is no way to override it from an input file (nothing in `src/pyH2A` reads or rewrites `DIMENSIONS['currency']`; verified by grep), no basis year, and no interaction with the inflation machinery — which is doubly wrong, since a currency conversion is a point-in-time operation and every other price in the model is inflation-adjusted through `Inflation_Plugin`. Recommended: either delete `EUR` so it fails loudly, or promote the rate to an input-file row (e.g. `Financial Input Values > Exchange rate`) with a mandatory reference date. Note `Discounted_Cash_Flow_Plugin.py:711,803` hardcodes `f'USD/{unit}'` for the levelized cost regardless, so a non-USD run is not actually supported end to end.

## UNIT-6 — `acre` matches no standard acre; `eV` is truncated while `e` is exact
**Severity:** SMELL · **Where:** `config.py:36-37`, `config.py:89-90`, `config.py:209` · **Known upstream?** PR #139 records that these constants were deliberately changed (test values were updated to follow); no issue tracks the resulting inaccuracy

- `"acre": 4046.86266972` (line 90), with `#"acre": 4046.8564224` commented out immediately above (line 89). The international acre is 4046.8564224 m² exactly; the US survey acre is 4046.87260987 m². The committed value is neither — it is 1.5 ppm above the international acre and 1.0 ppm below the survey acre. It looks like a legacy DOE H2A number retained for test-fixture compatibility.
- `"eV": 1.602176e-19` (line 37) with the exact SI value `1.602176634e-19` commented out (line 36) — a 4×10⁻⁷ relative truncation. Meanwhile `"e": 1.602176634e-19` (line 209, charge) uses the exact value. So elementary charge and electron-volt are inconsistent with each other inside the same config file. This directly affects PEC/Photocatalytic/Solar_Thermal, which all compute H₂ rates via `Quantity(2*1.229, 'eV/entity')` (PEC_Plugin.py:263, Photocatalytic_Plugin.py:422, Solar_Thermal_Plugin.py:116).

Both are small enough not to move a headline LCOH, but a units module whose stated purpose is correctness should not ship a physical constant that matches no published definition, with the correct one commented out one line above. If the truncated values are needed for reference-test parity, say so in a comment and pin the reference tests to a tolerance instead.

Spot-checks that **passed**: `hp` 745.699872 ✓ mechanical hp; `cv` 735.49875 ✓; `toe` 4.1868e10 ✓; `cal` 4.184 / `kcal` 4184 ✓ thermochemical; `psi` 6894.757293168 ✓; `atm` 101325 ✓; `bar` 1e5 ✓; `ft` 0.3048 / `in` 0.0254 ✓; `ha` 1e4 ✓; `deg` π/180 ✓; `entity` 1/N_A ✓; `Ah` 3600 / `mAh` 3.6 ✓; `F` 96485.332… ✓ (faraday as a charge unit); `Nm3` 44.6150 mol ✓ (PV/RT at 273.15 K, 101325 Pa); `Sm3` 42.2925 mol ✓ (288.15 K) — though note "standard" conditions are 15 °C here while US practice often uses 60 °F/15.56 °C, and both are filed under **substance**, not volume, so `Nm3/h` is a molar flow, not a volumetric one, and `Nm3` cannot be converted to `m3`.

## UNIT-7 — Adjacent tokens silently concatenate into a bogus multiplier
**Severity:** LIKELY-BUG · **Where:** `quantity.py:41-43` (tokenise), `:53-57` (numeric branch), `:71-75` (eval) · **Known upstream?** NEW

`TOKEN_PATTERN = re.compile(r'([*/()])|\s+')` treats whitespace as a *discarded separator*, not as an implicit product. The per-token multipliers are then joined with `"".join(multiplier_expr)` (line 71) and `eval`'d. When two tokens are adjacent with no explicit operator, their numeric strings are glued together:

- `'m 2'` (a plausible typo for `m2`) → `"1.0" + "2"` = `"1.02"` → multiplier **1.02**, dimension `length 2`. No error.
- `'10 kg'` → `"10" + "1.0"` = `"101.0"` → multiplier **101.0**, dimension `10 mass`.

In both cases the garbage dimension string means `check_dimension` will normally reject the value later, so the blast radius is limited to "confusing error" rather than "wrong number" for spec'd inputs — but a `Quantity` constructed directly inside a plugin (there are ~60 such sites) is not dimension-checked unless it is routed through `output_dict`, which #116 already observed is not always the case. Related defects in the same function:

- `'m**2'` / `'cm**2'` tokenise to `['cm','*','*','2']` → `eval("0.01**2")` = 1e-4, numerically *correct*, dimension `length * * 2`, which matches no spec. Exponent syntax half-works, which is worse than not working.
- `'m^2'`, `'kg+m'`, `'h**-1'` are single unknown tokens → clean `ValueError` ✓.
- The numeric-coefficient branch's comment (line 55) says *"Support explicit coefficients like `'1/month'`"* but **`month` is not a registered unit** (config.py:110-116 has `s, ms, minute, h, day, week, year`). `Quantity(1,'1/month')` raises `Unknown unit encountered during parsing: 'month'`. Fix the comment or add the unit.
- `eval` is confined to `{"__builtins__": {}}` and every token is pre-validated against `FLAT_MULTIPLIERS` or a numeric test, so this is not an injection vector — but a two-line lookup-and-multiply loop would remove `eval` entirely and make the failure modes obvious.

Recommended: make whitespace an implicit `*` (or reject it), and drop the free-form numeric branch in favour of a literal-`1` numerator special case.

## UNIT-8 — Temperature cannot appear in any composite unit
**Severity:** LIKELY-BUG · **Where:** `config.py:231-242`; `quantity.py:59-60` · **Known upstream?** NEW

The flattening loop at config.py:231-239 only walks `DIMENSIONS`. `ABSOLUTE_TEMPERATURE` is merged into `FLAT_DIMENSIONS` alone (lines 241-242) — **not** into `FLAT_MULTIPLIERS` or `FLAT_BASES`. Since `parse_composite_unit` looks tokens up in `FLAT_MULTIPLIERS` (line 60), every composite containing temperature dies with `Unknown unit encountered during parsing: 'K'`. So `W/K` (heat transfer), `J/kg/K` (specific heat), `USD/degC`, `K/year` are all unexpressible. Scalar `K`/`degC` work only through the offset short-circuit at quantity.py:194-203. This is a hard blocker for issue #143 ("Develop Physical properties function", which explicitly wants energy balances) and it will bite the first heat-exchanger plugin. Failing loudly is the right behaviour for *absolute* temperature (offsets don't compose), but `temperature_diff` (`delta_K`, `delta_degC`, config.py:135-141) *is* in `FLAT_MULTIPLIERS` and composes fine — so the fix is to document that thermal composites must use `delta_K`, and to raise a message that says so instead of "Unknown unit".

## UNIT-9 — Three different exception types for three flavours of bad unit
**Severity:** USABILITY · **Where:** `quantity.py:136-137` (KeyError), `:149-152` (ValueError), `:186` (AttributeError) · **Known upstream?** #141 (extends it with specifics)

A caller that wants to handle "the user gave a bad unit" must catch three unrelated exception types: `KeyError` for an unsupported absolute-temperature target (line 137), `ValueError` for both unknown tokens (line 60) and dimension mismatch (line 149), and an uncaught `AttributeError` when the unit is `None` (UNIT-10). None of the three carries the `Table > Row > Column` location — that context is only prepended much later by `input_resolver_function`'s blanket `except Exception` at input_resolver.py:697-699, which re-raises `type(error)(...)`; that re-raise itself breaks for any exception type whose constructor doesn't take a single string. For a UI this matters: a Streamlit wrapper wanting to show "unknown unit 'kwh' in row X — did you mean 'kWh'?" has to pattern-match on message text. Recommend a single `UnitError(ValueError)` carrying `(location, supplied_unit, reason)`.

## UNIT-10 — A missing `Unit` column produces `AttributeError: 'NoneType' object has no attribute 'strip'`
**Severity:** LIKELY-BUG · **Where:** `Utilities/IO/input_resolver.py:349` → `quantity.py:186` · **Known upstream?** #141 (extends)

`value_with_unit_resolver_function` fetches the unit with `.get(bottom_key_group[1], None)` (input_resolver.py:349) and passes the result straight into `Quantity(value_retrieved, unit_retrieved)` (input_resolver.py:192). `Quantity.__init__` immediately does `unit_str.strip()` (quantity.py:186), so omitting the `Unit` column — the single most likely authoring mistake in a markdown table — produces a bare `AttributeError` with no location and no mention of units. (An *empty* unit cell is slightly better: `convert_file_to_dictionary` maps blanks to `'n/a'` (input_modification.py:~277), giving `Unknown unit encountered during parsing: 'n/a'`.) Guard at the resolver: if the spec has a `*_Unit` key and `dcf.inp` has no matching column, raise `KeyError(f"'{top} > {mid}': required unit column '{unit_key}' is missing")`.

## UNIT-11 — No `__eq__` / `__hash__`
**Severity:** SMELL · **Where:** `quantity.py:164-223` (only `__init__` and `__repr__` are defined) · **Known upstream?** YES — #152, PR #164, PR #161

`Quantity` defines `__slots__` and exactly two dunders. It therefore inherits identity `__eq__`/`__hash__`. Two consequences:

1. **The #152 leak, root-caused.** `Hourly_Irradiation_Plugin.py:277` decorates `calculate_PV_power_ratio` with `@lru_cache(maxsize=None)` and the call site (lines 207-215) passes six `Quantity` objects (the function's own comment at line ~293 says so). With identity hashing every call is a guaranteed *miss*, so the cache never helps and, with `maxsize=None`, permanently retains every `Quantity` plus its populated `UnitDictionary` and the ndarrays inside. In a Monte Carlo loop this is unbounded growth for zero benefit. PR #164's unwrap-before-call is the right shape of fix; PR #161 (caching `parse_composite_unit`, which takes only `str`) is orthogonal and safe.
2. **Silent false comparisons.** `q1 == q2` is `False` for two Quantities holding the same physical value, and `q == 'Default'` is `False` for any Quantity. `Hourly_Irradiation_Plugin.py:300` relies on exactly that (`if module_tilt == 'Default'`) and happens to be *correct*, because the caller passes the literal string when the row is absent (lines 199-202) — but it is correct by luck, not by design. Any future `if some_quantity == other_quantity` will be silently always-false. If `__eq__` is added it must compare `(base_value, dimension)` and `__hash__` must be defined alongside it, or the objects become unhashable and break the caches further.

## UNIT-12 — Every `Quantity` is a reference cycle carrying an unbounded conversion cache
**Severity:** SMELL · **Where:** `quantity.py:104-109`, `:155-157` · **Known upstream?** Adjacent to #152; NEW as stated

`Quantity.unit` holds a `UnitDictionary`, which holds `self._quantity` back-pointing at the owner (line 104). Every single `Quantity` is therefore an unbreakable refcount cycle reclaimable only by the cyclic GC — with hundreds of thousands of Quantities per Monte Carlo run, that is real GC pressure for no benefit (`_quantity` could be replaced by storing `base_value`/`dimension` on the dict, or by making `unit` a lightweight view). Separately, `__missing__` memoises every requested conversion (line 156). For array-valued Quantities each distinct requested unit allocates and *retains* a full copy of the array; `Photovoltaic_Plugin.py:207` stores one 8760-element Quantity per year per run. Also note `__slots__` omits `__weakref__`, so `Quantity` cannot be weak-referenced — which forecloses the obvious fix for #152.

## UNIT-13 — No arithmetic operators; mixing with numpy fails obscurely
**Severity:** SMELL · **Where:** `quantity.py:164-223` · **Known upstream?** NEW

`Quantity` defines no `__mul__`, `__add__`, `__truediv__`, `__neg__`, `__array__` or `__array_priority__`. Every plugin must therefore unwrap to a raw float/ndarray with `.unit[...]`, compute, and re-wrap — which the codebase does consistently and verbosely (e.g. `Capital_Cost_Plugin.py:506-530`, eight `Quantity(...unit['USD'] * ...unit['-'], 'USD')` constructions in a row). That is a defensible design choice for a lightweight handler, but two things follow that a maintainer should know: (a) all dimensional safety is lost *inside* every computation — the unit system only checks the boundaries, so `Photocatalytic_Plugin.py:475` wrapping a `mol/(m2·s)`-derived number as `'mol/h/kg'` would never be caught; and (b) `ndarray * Quantity` does not raise a clean `TypeError` — numpy falls through to object-array broadcasting and emits an unhelpful error, which is exactly the class of message #141 complains about. A one-line `__array_ufunc__ = None` on the class would at least force a clear `TypeError`.

## UNIT-14 — `unit[supplied_unit]` returns the caller's array uncopied
**Severity:** LIKELY-BUG · **Where:** `quantity.py:108` · **Known upstream?** NEW

`UnitDictionary.__init__` pre-populates `self[quantity.supplied_unit] = quantity.supplied_value` — the *original object*, not a copy. When `supplied_unit != base_unit` (e.g. `Quantity(arr, 'kWh')`), `q.unit['kWh']` hands back the caller's ndarray; any in-place mutation of it silently corrupts the Quantity, and vice-versa. (When `supplied_unit == base_unit` line 109 overwrites the key with `supplied_value * multiplier`, which allocates a fresh array, so the alias only exists for non-base supplied units — an inconsistency that is itself a hazard.) `Power_Management_Plugin.py:236-237` defensively calls `.copy()` on `.unit['J']` results; nothing else does, and nothing documents that it is required. Related aliasing fact for a UI: `value_with_unit_resolver_function` writes the resolved `Quantity` **back into `dcf.inp`** (input_resolver.py:365-374), so the same object is shared between `dcf.inp` and every plugin's `input_dict_resolved`; `__slots__` fields are writable, so any plugin can mutate a Quantity another plugin is reading.

## UNIT-15 — `__repr__` docstring contradicts behaviour; errors interpolate whole arrays
**Severity:** SMELL · **Where:** `quantity.py:213-223`; `check_functions.py:38`, `:55`, `:61` · **Known upstream?** #141 (extends)

`__repr__`'s docstring says *"Provide a compact representation using base units"* and *"String form `Quantity(<base_value>, '<base_unit>')`"*, but the implementation (line 223) returns `f"Quantity({self.supplied_value}, '{self.supplied_unit}')"`. The behaviour is the useful one for a UI (see UNIT-20) — the docstring is simply wrong and will mislead the next reader. Compounding it, `check_dimension` and `check_bounds` interpolate the whole `Quantity` into the message (`(entry: '{value}')` at check_functions.py:38, `(entry: {value})` at :55 and :61) — for an 8760-element hourly irradiation array that produces a multi-kilobyte exception string, which is a direct contributor to #141. Truncate array reprs in error paths.

## UNIT-16 — Table sums add `base_value` with no dimension check
**Severity:** LIKELY-BUG · **Where:** `input_modification.py:936-941` (`sum_table_quantity`) and `:1008-1015` (`sum_all_tables_quantity`) · **Known upstream?** NEW (#102 covered the empty-table crash, not this)

Both summers do `value += quantity.base_value` over every row and then blindly re-wrap with a `base_unit` supplied by the caller. Nothing verifies that the rows share a dimension. A `Direct Capital Costs - X` table containing one row in `USD` and one accidentally in `USD/m2` sums to a meaningless number and is then labelled `USD` — and, because `Capital_Cost_Plugin`'s wildcard row spec declares `"dimension": "currency"` (line 185), the mislabelled row *would* have been caught at resolve time... unless it reaches the summer through a path that skips the spec. Two further latent failures in the same functions: any row whose value is not a `Quantity` (a resolved string, a nested dict) raises `AttributeError: 'str' object has no attribute 'base_value'` with no location; and `sum_table_quantity` inserts its result back into `dcf.inp[top_key]['Summed Total']` (line 943-945) while the wildcard resolver iterates *all* middle keys of `dcf.inp[top_key]` (input_resolver.py:~476) — so re-running a DCF over the same, un-deepcopied `inp` will sum the previously inserted total again. Add a dimension assertion in the loop and, for the UI, see UNIT-20.

## UNIT-17 — `retrieve_base_unit` returns `None` or raises for composite dimensions
**Severity:** LIKELY-BUG · **Where:** `input_modification.py:1052-1063`; callers at `input_resolver.py:566` and `:624` · **Known upstream?** NEW

``python
dimension = value.get("dimension")
return DIMENSIONS[dimension]["base"]
``
This only works for atomic dimension names. Any sum table whose rows carry a composite dimension (`currency / area`, `currency / mass`, `energy / volume` — all of which exist today in `Capital_Cost_Plugin.py:231`, `Photocatalytic_Plugin.py:233`, `Reverse_Osmosis_Plugin.py:73`) raises `KeyError: 'currency / area'`. Today's sum tables all happen to be plain `currency`, so it is latent — but it is a landmine under the next `sum_tables` group. Worse, the function has **no fallback return**: if the table spec's first `*Unit*` dict lacks a `"dimension"` key, or no row matches, it falls off the end and returns `None`, which flows into `Quantity(value, None)` → `AttributeError: 'NoneType' object has no attribute 'strip'` (same signature as UNIT-10). It also returns the base unit of whichever row it happens to visit first in dict order, with no check that the other rows agree. Derive the base unit by parsing the dimension expression instead, or require an explicit `base_unit` in the `sum_tables` arguments.

## UNIT-18 — `num()` strips every comma, so `'1,5'` silently becomes `15`
**Severity:** LIKELY-BUG · **Where:** `input_modification.py:200-212` · **Known upstream?** NEW

The percent and thousands-separator handling is:
``python
if s[-1] == '%': return num(s[:-1])/100.
try:    return int(s.replace(',', ''))
except ValueError:
    try: return float(s.replace(',', ''))
    except ValueError: return str(s)
``
Comma removal is unconditional and unvalidated, so a European-style decimal `'1,5'` (meaning 1.5) parses as `15` — a silent 10× error in a project with European contributors and inputs quoted in EUR. `'1,2,3'` becomes `123`. There is no check that commas actually occur in thousands positions. Also, `s[-1]` raises `IndexError` on an empty string; `convert_file_to_dictionary` maps blank cells to `'n/a'` before calling `num`, but `process_cell` calls `num(cell)` on arbitrary cell text (input_modification.py:~750), so the guard is incidental rather than structural. The percent path is otherwise sound and composes correctly with the unit system: `50%` → `0.5` at parse time, then `Quantity(0.5, '-')`, and `2%` with a `Path` multiplies cleanly (`PV_E_Base_test.md:154`). **UI-relevant:** `%` is *not* a unit — `Quantity(50,'%')` raises `Unknown unit encountered during parsing: '%'`. Percentages must be written in the Value cell with the Unit cell set to `-`.

## UNIT-19 — Utility cost/usage units are deliberately dimension-lossy
**Severity:** USABILITY · **Where:** `Variable_Operating_Cost_Plugin.py:173-183`, consumed at `:396-411` · **Known upstream?** #133 is adjacent (it questions "Other Variable Operating Cost"); the Utilities half below is NEW

`Cost_Unit` is declared as plain `"currency"` with an explicit comment that the basis is omitted on purpose (line 174), and `Usage_Unit` as `f"1/{functional_unit.dimension}"` (line 182). So the real-world quantities — 0.0006 **USD per litre** and 10 **litres per kg H₂** (`PV_E_Base_test.md:161`) — must be entered as `USD` and `1/kg`, with the litre erased from both. The product is dimensionally consistent only if the user keeps the two bases in their head. Enter cost as USD/m³ (0.6) and usage as L/kg (10) — both individually reasonable — and you get a 1000× error that no check can catch, because the system has thrown away exactly the information needed to catch it. The system also actively *forbids* the honest spelling: `USD/L` parses as `currency / volume` and fails the `currency` check; `L/kg` parses as `volume / mass` and fails the `1/mass` check. Since the parser already supports arbitrary composites, the fix is to declare `Cost_Unit` as `currency / <anything>` and `Usage_Unit` as `<same anything> / <functional dimension>` and verify the cancellation — which requires UNIT-1's canonicalisation. Until then, this deserves a prominent warning in the docs and in any UI form.

## UNIT-20 — UI-FACT: how to display a Quantity, and how not to probe it
**Severity:** UI-FACT · **Where:** `quantity.py:104-157`, `:177-223` · **Known upstream?** NEW

**Display recipe (use this verbatim):**
``python
value = q.supplied_value      # the number to show
unit  = q.supplied_unit       # the unit string to show, exactly as authored
# canonical/SI form, for tooltips or cross-checks:
si_value = q.base_value       # always SI
si_unit  = q.base_unit        # e.g. 'J / m2 / s' (spaced, operator layout preserved)
# any other unit:
other = q.unit['MWh']         # raises ValueError on dimension mismatch
``
For **user inputs** resolved from markdown, `supplied_unit` is what the user typed and `supplied_value` is their number *after* percent conversion and `Path` multiplication — i.e. it is the correct display pair, not the raw cell. For **plugin outputs** the plugin picks both, e.g. the levelized cost is `Quantity(x, f'USD/{functional_unit.unit}')` (`Discounted_Cash_Flow_Plugin.py:711`) so it displays as `USD/kg` with no conversion needed. `repr()` gives `Quantity(<supplied_value>, '<supplied_unit>')` (quantity.py:223) — despite the docstring claiming base units.

**Traps a UI must avoid:**
- `q.unit` is a `dict` subclass with a `__missing__` hook. `'MWh' in q.unit` is **False** until that key has been accessed, and `q.unit.get('MWh')` returns **None** silently, because neither `__contains__` nor `dict.get` invokes `__missing__`. Only `q.unit['MWh']` performs the conversion. Never feature-detect convertibility with `in`/`.get`; call it inside `try/except (ValueError, KeyError)`.
- Enumerating "which units can I offer for this quantity" requires `FLAT_DIMENSIONS`, not the Quantity: filter `config.FLAT_MULTIPLIERS` to tokens whose `FLAT_DIMENSIONS[tok] == q.dimension`. That only works for atomic dimensions; for composites the UI must build the offer list itself.
- Result location for a completed run: `dcf.inp['Dependent Variables']['Levelized cost']['Value']` (a `Quantity`, unit `USD/<functional unit>`) and `['Levelized cost contributions']['Value']` (a dict `{'Data': {name: Quantity}, 'Total': Quantity, 'Table Group': str}` — note the mixed value types; `Table Group` is a plain string, per `Discounted_Cash_Flow_Plugin.py:771-786`).
- `Discounted_Cash_Flow.__init__` does **not** deepcopy a dict passed as `input_file` (`Discounted_Cash_Flow.py:189-192`); it mutates it in place (resolved Quantities, `Processed` markers, inserted `Summed Total` rows). A UI must `copy.deepcopy(inp)` before every run or the second run will double-count sums (UNIT-16) and skip re-processing. `discounted_cash_flow_function` already does this at line 59; the class does not.
- The functional unit is read once at `Discounted_Cash_Flow.py:201` from `inp['Functional Unit']['Functional Unit']['Unit']`; it must be a **single atomic token** in `FLAT_DIMENSIONS` (`functional_unit.py:19-21`). `kg/day` or `MWh/year` as a functional unit raise `ValueError: Unknown unit specified for functional unit`.

## UNIT-21 — UI-FACT: complete supported-unit inventory and notable absences
**Severity:** UI-FACT · **Where:** `config.py` (whole file) · **Known upstream?** NEW; PR #54 added `entity`, PR #122 added the current batch and chose to fix test data rather than add a `liters` alias

See the appendix for the full table (107 tokens in `FLAT_MULTIPLIERS`, plus `K`/`degC` reachable only as standalone units). Units a user will plausibly type that the system **rejects**:

| typed | why it fails | present alternative |
|---|---|---|
| `%` | not a unit | put `%` on the value, unit `-` |
| `min`, `sec`, `hr`, `hrs`, `month`, `months` | absent (`m` is metre) | `minute`, `s`, `h`, — none for month |
| `t`, `tonne`, `tonnes`, `kt`, `Mt`, `lb` | absent | `ton` (= 1000 kg, metric) |
| `liters`, `litres`, `litre`, `l` | absent | `L`, `liter` |
| `gal`, `gallon`, `bbl`, `ft3`, `in3` | absent | `m3`, `L` |
| `BTU`, `MMBtu`, `mmBTU`, `therm`, `TJ`, `PJ` | absent | `MJ`, `GJ`, `toe` |
| `kPa`, `mbar`, `barg`, `torr` | absent (`hPa` and `MPa` exist, `kPa` does not) | `Pa`, `hPa`, `MPa`, `bar`, `atm`, `psi` |
| `mW`, `uW`, `TW` | absent (only `W`,`kW`,`MW`,`GW`) | — |
| `um`, `nm`, `mi`, `yd` | absent | `mm`, `cm`, `m`, `km`, `ft`, `in` |
| `ft2`, `in2`, `sqft` | absent | `m2`, `acre`, `ha` |
| `GBP`, `CNY`, `JPY`, `CHF` | absent | `USD`, `EUR` (and see UNIT-5) |
| `wt%`, `vol%`, `mol%` | absent | `-`, `ppm`, `ppb` |
| `kWh/yr`, `p.a.` | `yr` absent | `kWh/year`, `kWh_per_year` |
| `KWh`, `kwh`, `Kg`, `USD/KG` | **case-sensitive**, exact match only | `kWh`, `kg`, `USD/kg` |
| `W/K`, `J/kg/K` | temperature not composable (UNIT-8) | use `delta_K` |
| `Nm3` where a volume is wanted | registered under **substance** | `m3` |

All rejections raise `ValueError: Unknown unit encountered during parsing: '<token>'` with no suggestion and no location. A UI should validate unit strings client-side against the appendix list before submitting, and offer a per-dimension dropdown rather than free text.

## UNIT-22 — Issue #116 is already fixed in master; the issue is still open
**Severity:** SMELL · **Where:** `Photocatalytic_Plugin.py:498` · **Known upstream?** YES — #116, still OPEN

#116 reports `Quantity(peak_TOF_hourly, '1/hour')`. At a15e7bb the line reads `Quantity(peak_TOF_hourly, '1/h')` and parses correctly (`1/3600` s⁻¹, dimension `1 / time`). The neighbouring `'1/day'` (line 499), `'mol/liter'` (496), `'mol/m2'` (497) and `'-'` (500) all parse. The issue should be closed — but the *underlying* observation in #116 ("it wasn't flagged automatically because this variable is not subject to the output_dict checks") remains true and is the more valuable half: `catalyst_properties` is a free-form dict assembled at lines 477-508 and only the outer dict is type-checked, so unit typos in it are still undetectable. That is the same gap as UNIT-13(a).

## UNIT-23 — Public wrapper defaults hardcode `USD/kg` and the removed `h2_cost`
**Severity:** LIKELY-BUG · **Where:** `Discounted_Cash_Flow.py:12-13`, `:35`, `:83` · **Known upstream?** The `h2_cost` half is known meta breakage; the `USD/kg` half is NEW

``python
dependent_variable = '{Dependent Variables > Levelized Cost > Value, USD/kg}',
attribute = 'h2_cost',
``
Two defects in two lines. (a) The path unit is hardcoded to `USD/kg`, so the wrapper is silently wrong for any non-mass functional unit — it should be `f'USD/{dcf.functional_unit.unit}'`, resolved after the DCF runs. (b) The table/row casing is `Levelized Cost`, while the plugin actually inserts under `Levelized cost` (`Discounted_Cash_Flow_Plugin.py:474`), so the path would `KeyError` even for kg. (c) `attribute='h2_cost'` refers to an attribute `Discounted_Cash_Flow` no longer has. I flag this here rather than leaving it to the meta reviewer because the unit half is invisible from the analysis modules — it's a functional-unit-genericity leak in the core wrapper's signature.

## UNIT-24 — Integers always become floats, so an `{int}`-only type spec is unsatisfiable
**Severity:** SMELL · **Where:** `quantity.py:207`; `check_functions.py:9-17`; `input_resolver.py:266-277` · **Known upstream?** NEW

`self.base_value = self.supplied_value * supplied_multiplier` where every multiplier is a float, so `Quantity(2016, '-').base_value` is `2016.0`. `check_type` is then run against `base_value` (input_resolver.py:267, 276), so a spec of `"type": {int}` can never be satisfied by a value that came through the markdown path. Every current spec hedges with `{int, float}` or `{float}`, so it is latent — but it means the `int` in those sets is decorative, and it interacts badly with numpy: `np.float64` *is* a `float` subclass so it passes, while `np.int64` is **not** an `int` subclass and would fail an `{int}` check. Callers work around it by casting at use sites (`int(round(...unit['-']))` at `Discounted_Cash_Flow_Plugin.py:537`, `Time_Plugin.py:132-133`, `Variable_Operating_Cost_Plugin.py:355`). Either preserve integer-ness when the multiplier is exactly 1.0, or drop `int` from the type vocabulary.

## UNIT-25 — Physical constants hardcoded as bare floats, bypassing the unit system
**Severity:** SMELL · **Where:** `Stored_Power_Electrolysis_Plugin.py:248`; `Electrolyzer_Plugin.py:240`; `Reverse_Osmosis_Plugin.py:146-147`; `Labor_Operating_Cost_Plugin.py:102` · **Known upstream?** NEW

- `SECONDS_IN_A_YEAR = 8760*3600` (= 31 536 000) — numerically consistent with `config.py:116`'s `year`, but a duplicate source of truth that will silently diverge the day anyone changes the year convention. Should be `Quantity(1,'year').unit['s']`.
- `electrolyzer_energy_demand = 3600*electrolyzer_power_demand  # integrate the power over 1 hour` — a magic 3600 encoding the assumption that the irradiation series is hourly. If that granularity ever changes, this is silently wrong with no dimensional trace.
- `MOLAR_RATIO_WATER = 18.01528 / 2.016` and `DENSITY_WATER_KG_PER_M3 = 997` — unitless floats for a molar mass ratio and a density. The density in particular is temperature-dependent and undocumented as to conditions (997 kg/m³ ≈ 25 °C; 0 °C seawater is ~1025). Both would be natural `Quantity` constants.
- `work_hours_in_a_year = Quantity(2080, 'h')` is the good pattern — it *is* a Quantity, with the 40 h × 52 wk derivation in a comment. Use it as the template.

## UNIT-26 — UI-FACT: existing unit tests pin the broken behaviour
**Severity:** UI-FACT (for anyone attempting the UNIT-1 fix) · **Where:** `src/tests/Utilities/Unit_Handler/quantity_test.py:19-23` · **Known upstream?** NEW

`test_parse_composite_unit_parentheses` asserts `dim == "( energy * length ) / area"`, i.e. it codifies the non-canonical dimension string as the contract. Any canonicalisation fix must rewrite that test. The suite is otherwise decent for the happy path (13 tests covering absolute temperature, arrays, lazy evaluation, mismatch detection) but has **no** coverage of: composite-vs-atomic equivalence, the `_per_year` pseudo-units, whitespace concatenation, `None`/empty units, `EUR`, or any conversion factor's numeric value beyond `kWh` and `cm`. There is no test file for `config.py` at all.

---

# Appendix — complete supported-unit inventory (config.py @ a15e7bb)

107 tokens in `FLAT_MULTIPLIERS`; `K` and `degC` are additionally present in `FLAT_DIMENSIONS` only, so they work as standalone units but **cannot appear in any composite** (UNIT-8).

| dimension | base | units (factor to base) |
|---|---|---|
| `energy` | `J` | `J` 1 · `kJ` 1e3 · `MJ` 1e6 · `GJ` 1e9 · `Wh` 3600 · `kWh` 3.6e6 · `MWh` 3.6e9 · `GWh` 3.6e12 · `TWh` 3.6e15 · `eV` 1.602176e-19 ⚠️UNIT-6 · `cal` 4.184 · `kcal` 4184 · `toe` 4.1868e10 |
| `power` | `W` | `W` 1 · `kW` 1e3 · `MW` 1e6 · `GW` 1e9 · `hp` 745.699872 · `cv` 735.49875 · `J_per_day` 1/86400 · `kJ_per_day` · `MJ_per_day` · `GJ_per_day` · `Wh_per_day` 1/24 · `kWh_per_day` · `MWh_per_day` · `GWh_per_day` · `J_per_year` 1/(86400·365) · `kJ_per_year` · `MJ_per_year` · `GJ_per_year` · `Wh_per_year` 1/(24·365) · `kWh_per_year` · `MWh_per_year` · `GWh_per_year` · `TWh_per_year` ⚠️UNIT-4 |
| `length` | `m` | `m` 1 · `mm` 1e-3 · `cm` 1e-2 · `km` 1e3 · `ft` 0.3048 · `in` 0.0254 |
| `area` | `m2` | `m2` 1 · `mm2` 1e-6 · `cm2` 1e-4 · `km2` 1e6 · `acre` 4046.86266972 ⚠️UNIT-6 · `ha` 1e4 |
| `volume` | `m3` | `m3` 1 · `mm3` 1e-9 · `cm3` 1e-6 · `km3` 1e9 · `uL` 1e-9 · `mL` 1e-6 · `L` 1e-3 · `liter` 1e-3 |
| `time` | `s` | `s` 1 · `ms` 1e-3 · `minute` 60 · `h` 3600 · `day` 86400 · `week` 604800 · `year` 31536000 (365 d) |
| `currency` | `USD` | `USD` 1 · `EUR` 0.8 ⚠️UNIT-5 |
| `mass` | `kg` | `kg` 1 · `mg` 1e-6 · `g` 1e-3 · `ton` 1000 (metric) |
| `temperature_diff` | `delta_K` | `delta_K` 1 · `delta_degC` 1 |
| `substance` | `mol` | `mol` 1 · `umol` 1e-6 · `mmol` 1e-3 · `kmol` 1e3 · `entity` 1/N_A · `Nm3` 44.6150334063 (0 °C, 1 atm) · `Sm3` 42.2925433799 (15 °C, 1 atm) |
| `voltage` | `V` | `V` 1 |
| `current` | `A` | `A` 1 · `mA` 1e-3 |
| `angle` | `rad` | `rad` 1 · `deg` π/180 |
| `pressure` | `Pa` | `Pa` 1 · `hPa` 100 · `MPa` 1e6 · `atm` 101325 · `bar` 1e5 · `psi` 6894.757293168 (no `kPa`) |
| `force` | `N` | `N` 1 · `kN` 1000 |
| `frequency` | `Hz` | `Hz` 1 · `kHz` 1e3 · `MHz` 1e6 · `GHz` 1e9 |
| `charge` | `C` | `C` 1 · `mC` 1e-3 · `F` 96485.332… (faraday) · `Ah` 3600 · `mAh` 3.6 · `e` 1.602176634e-19 ⚠️UNIT-6 |
| `resistance` | `Ohm` | `Ohm` 1 · `mOhm` 1e-3 · `kOhm` 1e3 |
| `dimensionless` | `-` | `-` 1 · `ppm` 1e-6 · `ppb` 1e-9 |
| `absolute_temperature` | `K` | `K`, `degC` — **offset path only, not composable** (UNIT-8) |

**Composite syntax accepted:** `*`, `/`, `(`, `)`, spaces around operators, and a leading literal `1` numerator (`1/kg`, `1/h`). Left-to-right evaluation, so `a/b/c` = `a/(b·c)`. **Not** accepted: `^`, unary `-`, negative exponents, `%`, unit labels like `kg H2` (see PR #157 for a proposed `kg[H2]` syntax), any capitalisation variant. `**` is accepted but produces a dimension string that matches nothing (UNIT-7).

**Units actually appearing in the shipped new-format inputs** (`src/tests/end_to_end/*.md`, `src/pyH2A/Config/Defaults_TEA.md`), for UI dropdown seeding: `-`, `deg`, `degC`, `kg`, `year`, `USD`, `kW`, `MWh`, `kWh`, `kWh/m2`, `kWh/m3`, `USD/acre`, `USD/kWh`, `m2`, `m3/h`, `1/kg`. Note `pyH2A/data/**/*.md` (PV_E_Base.md, PEC_Base.md, Photocatalytic_Base.md …) are in the **legacy** format — units embedded in row names like `Nominal Power (kW)`, no `Unit` column, no `Functional Unit` table — and are not loadable by the current engine. A UI must ship the `src/tests/end_to_end/` or `src/pyH2A/Example/` files as its examples, not `data/`.