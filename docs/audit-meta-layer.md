# Meta / Orchestration Layer Audit — pyH2A @ master a15e7bb

**Reviewer:** MetaLayerReviewer · **Scope:** `run_pyH2A.py`, `cli_pyH2A.py`, `__main__.py`, all 7 `Analysis/` modules, `Utilities/plugin_input_output_processing.py`, `Utilities/output_utilities.py`, `LCA/`, `Example/`, `Other/`, `doc/` · **Method:** source-only, read-only. Nothing executed.

## Headline

The entire `Analysis/` layer is dead on master. **7 of 7 analysis modules fail**, either directly (they read `dcf.h2_cost` / `dcf.contributions`, both removed by PR #176) or transitively (they wrap `Monte_Carlo_Analysis`). `pyH2A generate` is dead too — it calls `convert_input_to_dictionary()` with a kwarg that no longer exists and `getattr`s two `Discounted_Cash_Flow` methods that were deleted. The `LCA/` package is fully orphaned: **nothing in `src/` imports it**, the plugin its own default config demands (`Life_Cycle_Assessment_Plugin`) does not exist, and its test-data folder contains a README and no matrices. The docs describe the pre-#176 engine almost throughout. None of this is tracked in `./corpus` — PR #176's body mentions only #144/#149 and never touches the analysis layer, so **every finding below is NEW** unless explicitly cited otherwise.

Critically for the UI agent: even after swapping `dcf.h2_cost` → `dcf.inp['Dependent Variables']['Levelized cost']['Value']`, **the analysis modules still will not work**, because that value is a `Quantity`, and `Quantity` (`Utilities/Unit_Handler/quantity.py`, `__slots__`, no `__float__`, no arithmetic dunders) cannot be subtracted, sorted, `float()`-ed, or handed to `ax.barh`. Every fix is two-part: relocate the read **and** unwrap the unit.

---

## Findings table

| id | severity | file:line | one-line summary |
|---|---|---|---|
| META-1 | BUG-confirmed-by-reading | `Analysis/Cost_Contributions_Analysis.py:79-80` | `self.base_case.contributions` — attribute removed by #176, AttributeError on first plot |
| META-2 | BUG-confirmed-by-reading | `Analysis/Cost_Contributions_Analysis.py:118` | Compares Table Group to `'Total cost of hydrogen'`; plugin now emits `'Total Cost of Product'` — H2 axis label never applies |
| META-3 | BUG-confirmed-by-reading | `Analysis/Cost_Contributions_Analysis.py:94,105,111` | Contribution values are `Quantity`, not float — `millify()`/`barh()`/division all fail even after META-1 is fixed |
| META-4 | BUG-confirmed-by-reading | `Analysis/Sensitivity_Analysis.py:93,172` | `dcf.h2_cost` / `self.base_case.h2_cost` — removed attribute |
| META-5 | BUG-confirmed-by-reading | `Analysis/Sensitivity_Analysis.py:83-86` | Misplaced paren: `cutoff=` lands on `str.format`, not `dynamic_value_formatting` — silently ignored |
| META-6 | BUG-confirmed-by-reading | `Analysis/Waterfall_Analysis.py:52,102` | `self.base_case.h2_cost` / `dcf.h2_cost` — removed attribute; fires in `__init__` |
| META-7 | BUG-confirmed-by-reading | `Analysis/Waterfall_Analysis.py:234` | Step bars are sized by `Relative Change` but labelled with absolute `Value` — chart lies |
| META-8 | BUG-confirmed-by-reading | `Analysis/Monte_Carlo_Analysis.py:317` | `dcf.h2_cost` inside the sampling loop — every MC run dies on sample #1 |
| META-9 | BUG-confirmed-by-reading | `Analysis/Monte_Carlo_Analysis.py:114` | `metric is 'cityblock'` — identity test on a string; wrong normalisation divisor for non-interned input |
| META-10 | BUG-confirmed-by-reading | `Analysis/Monte_Carlo_Analysis.py:664,718` | `target_price_2D_region` is a method that overwrites itself with a dict — second `plot_colored_scatter()` call raises `TypeError: 'dict' object is not callable` |
| META-11 | BUG-confirmed-by-reading | `Analysis/Monte_Carlo_Analysis.py:483-491` | `sucess = False` reset every iteration → spurious `KeyError` unless the match is the last parameter; also mutates the dict it is iterating |
| META-12 | BUG-confirmed-by-reading | `Analysis/Monte_Carlo_Analysis.py:~1006` | `Axes3D(fig, auto_add_to_figure=False)` — removed in matplotlib 3.7; `pyproject.toml` pins `matplotlib>=3.9.4` |
| META-13 | SMELL | `Analysis/Monte_Carlo_Analysis.py:1,321-350` | Method named `perform_monte_carlo_multiprocessing` is fully serial; pool code commented out, `import multiprocessing` unused |
| META-14 | BUG-confirmed-by-reading | `Analysis/Optimization_Analysis.py:85-87` | `differential_evolution` calls `discounted_cash_flow_function_1D`, which `getattr(dcf, 'h2_cost')` |
| META-15 | BUG-confirmed-by-reading | `Discounted_Cash_Flow.py:13,83` | Both public wrapper functions default `attribute='h2_cost'`; `dependent_variable` param is declared and never read |
| META-16 | USABILITY | `Analysis/Optimization_Analysis.py:29-34,53` | `# Optimization_Analysis` table (`Algorithm`/`Target`/`Direction`) is never read; docstring `Parameters` section is empty |
| META-17 | BUG-confirmed-by-reading | `Analysis/Development_Distance_Time_Analysis.py:59` vs `:94` | Docstring advertises `Extrapolation Limit > Year`; code reads `Extrapolation Limit Year > Value` — template generator emits the wrong table |
| META-18 | SMELL | `Analysis/Development_Distance_Time_Analysis.py:88` | `== 'False'` string compare — a real `False`/`0`/`false` all silently enable log normalisation |
| META-19 | BUG-confirmed-by-reading | `Analysis/Comparative_MC_Analysis.py:34`, `Development_Distance_Time_Analysis.py:78` | Both construct `Monte_Carlo_Analysis` → inherit META-8 unconditionally |
| META-20 | BUG-confirmed-by-reading | `Utilities/plugin_input_output_processing.py:147-148` | `convert_input_to_dictionary(file, merge_default=False)` — kwarg does not exist; `TypeError` |
| META-21 | BUG-confirmed-by-reading | `Utilities/plugin_input_output_processing.py:125-133,196` | Injects `pre_workflow`/`post_workflow` then `getattr(Discounted_Cash_Flow, ...)` — both methods deleted by #176 |
| META-22 | BUG-confirmed-by-reading | `Utilities/plugin_input_output_processing.py:182` | Reads `Workflow[key]['Type']`; the `Type` column was removed from the Workflow table (commit 1045570) |
| META-23 | SMELL | `Utilities/plugin_input_output_processing.py:35-80` | Scrapes docstrings by leading-space counting; superseded by `Utilities/docstring_generation.py` + plugin `input_dict` specs |
| META-24 | BUG-confirmed-by-reading | `Config/Defaults_LCA.md:6`, `Config/Defaults_TEA_LCA.md:14` | Both defaults schedule `Life_Cycle_Assessment_Plugin`, which does not exist in `Plugins/` → `ModuleNotFoundError` |
| META-25 | BUG-confirmed-by-reading | `LCA/LCA.py:17,67` | `from pyH2A import Discounted_Cash_Flow` binds the **module**, then uses it as a type annotation for a class instance |
| META-26 | UI-FACT | `data/LCA/LCA_Test_Data/` | Contains only `README.md` — no `A`/`B`/`C`/`f` matrices or index files; the shipped LCA example cannot load |
| META-27 | UI-FACT | `LCA/LCA.py` (whole file) | Zero references to `LCA` anywhere in `Plugins/`, `Utilities/`, `Discounted_Cash_Flow.py`, `run_pyH2A.py` or `tests/` — fully orphaned |
| META-28 | LIKELY-BUG | `LCA/LCA.py:167` | Hardcodes `'Output per Year at Gate'` and `np.sum(...)` on a value that is float-or-array — same float/array ambiguity as issue **#87** |
| META-29 | USABILITY | `run_pyH2A.py:103-118` | Empty `Arguments` cell parses to `'n/a'` → `KeyError` then `ast.literal_eval('n/a')` → uncaught `ValueError` |
| META-30 | UI-FACT | `run_pyH2A.py:119-129` | Any method whose name contains `plot`/`figure`/`chart` gets `directory` + `input_file_name` force-injected |
| META-31 | UI-FACT | `run_pyH2A.py:47,49` + each `Analysis/*.__init__` | Input file is parsed and the DCF re-run once per analysis module; a 4-module file runs the DCF ≥5× before any sampling |
| META-32 | SMELL | `run_pyH2A.py:131-139` | `run_pyH2A()` reads `sys.argv[1:2]` and is wired to no entry point — dead code, `IndexError` if ever called bare |
| META-33 | USABILITY | `cli_pyH2A.py:16-22`, `Utilities/output_utilities.py:163` | `-o` is never validated; a non-existent dir surfaces as a raw `FileNotFoundError` from `fig.savefig` after all compute is done |
| META-34 | UI-FACT | `Utilities/output_utilities.py:145-172` | `Figure_Lean.execute()` calls blocking `plt.show()`, else `plt.close()`; saving goes straight to the filesystem via `fig.savefig` |
| META-35 | UI-FACT | `Utilities/output_utilities.py:30-48` | `set_font` mutates global `rcParams` to `Arial` on every figure construction |
| META-36 | SMELL (docs) | `doc/pyH2A/default_settings.rst:6-30` | Documents six `function`-type Workflow rows that no longer exist, omits `Discounted_Cash_Flow_Plugin` and `# Functional Unit`, and uses the old `Financial Input Values` short-name schema |
| META-37 | SMELL (docs) | `doc/guide.rst:32-40,~150` | Teaches the removed `Type` column, and shows a plain-float LCOH print line that the code no longer produces |
| META-38 | SMELL (docs) | `doc/plugins/plugins.rst:15`, `doc/plugins/Fixed_Operating_Cost_Plugin.rst:4` | `automodule:: pyH2A.Plugins.Fixed_Operating_Cost_Plugin` — module does not exist; three real plugins have no page |
| META-39 | SMELL (docs) | `doc/utilities/utilities.rst:7` | Toctree references `Energy_Conversion`, which has no `.rst` file |
| META-40 | SMELL (docs) | `doc/analysis/analysis.rst`, `doc/plugins/Plugin_Guide.rst:57` | `Optimization_Analysis` undocumented; Plugin_Guide shows `__init__(self, dcf, print_info)` with inline work, not the real `run=True` / `_set_up` / `_run` shape |
| META-41 | SMELL | `src/pyH2A/Example/210613_PV_E.md`, `210511_…Type_4.md`, `211109_…Figure_Test.md` | All three shipped examples lack `# Functional Unit` and `# Input files to merge` → `KeyError('Functional Unit')` in `Discounted_Cash_Flow.__init__` |
| META-42 | USABILITY | `data/PV_E/Base/PV_E_Base_Figures.md` (Monte_Carlo / DDT tables) | Hardcoded `/Users/Jacob/Documents/...` absolute paths in shipped inputs |
| META-43 | USABILITY | `data/*/…md` `# Comparative_MC_Analysis` rows | Model paths like `./PEC/Base/PEC_Base.md` resolve against CWD, not against the referring input file |
| META-44 | UI-FACT | `Analysis/Monte_Carlo_Analysis.py:206-212,389` | Requires **either** `Input File` **or** `Output File`; the latter path is written with `np.savetxt` to an arbitrary location |
| META-45 | SMELL | `Analysis/Monte_Carlo_Analysis.py:461`, `Utilities/input_modification.py:152` | MC/DDT read results through `@lru_cache`'d `read_textfile` — stale reads within a session; same cache class as issue **#152** |
| META-46 | USABILITY | `Analysis/Monte_Carlo_Analysis.py:~927,~1000` | `plot_colored_scatter` silently requires ≥3 varied parameters, `plot_colored_scatter_3D` ≥4; fewer → bare `IndexError` (relates to **#141**) |
| META-47 | SMELL | `pyproject.toml` vs `setup.cfg` | Two competing metadata sources: `requires-python >=3.9` vs `>=3.7`, literal version vs `attr:`, and the console-script entry point lives only in `setup.cfg` |
| META-48 | UI-FACT | `Analysis/Comparative_MC_Analysis.py:~205`, `~300` | `plot_comparative_distance_cost_relationship` returns a `Figure_Lean`, not a `matplotlib.Figure` — inconsistent with every sibling plot method |
| META-49 | LIKELY-BUG | `Utilities/input_modification.py:383-395` used from Sensitivity/Waterfall/MC | `set_by_path` blind-writes the `Value` cell; if that cell holds a `{path, unit}` reference the reference is destroyed (or `*=` raises on a `str`) |
| META-50 | SMELL | `Analysis/Monte_Carlo_Analysis.py:~1255` | `plot_target_parameters_by_distance` indexes column `3` unconditionally and has an empty docstring |

---

# 1. Per-module breakage inventory (post-#176)

`Discounted_Cash_Flow` now sets exactly four attributes (`Discounted_Cash_Flow.py:186-193`): `inp`, `print_info`, `plugs`, `functional_unit`. There is no `h2_cost` and no `contributions`. Results live in `dcf.inp['Dependent Variables']['Levelized cost']['Value']` and `['Levelized cost contributions']['Value']`, both inserted by `Discounted_Cash_Flow_Plugin` (output_dict at `Plugins/Discounted_Cash_Flow_Plugin.py:472-493`), and **both are `Quantity` objects** (`product_cost` built at `:709-711`; each contribution built at `:807`).

## 1.1 Cost_Contributions_Analysis — **BROKEN**

**Dead references**
- `:79` `self.contributions = self.base_case.contributions` → `AttributeError`.
- `:80` `self.data = self.base_case.contributions['Data']` → same.
- `:118` `if self.contributions['Table Group'] == 'Total cost of hydrogen'` — the plugin writes `'Total Cost of Product'` (`Discounted_Cash_Flow_Plugin.py:787`), so the H2-specific x-axis label is now unreachable even on the plugin path.

**Still works**
- `:82-84`, the `plugin=` / `plugin_property=` branch: `self.base_case.plugs[plugin]` is live, and `Capital_Cost_Plugin.direct_contributions` (used by the shipped `cost_breakdown_plot_capital` method row) is a plugin attribute, not a DCF attribute. This is why the file is BROKEN rather than useless — the per-plugin breakdown is one attribute-unwrap away from running.
- `:24-25` `Discounted_Cash_Flow(input_file, print_info=False)` — constructor signature unchanged.

**Minimal conceptual fix.** Replace `:78-84` with a single accessor that reads `self.base_case.inp['Dependent Variables']['Levelized cost contributions']['Value']` when `plugin is None`, and — critically — unwrap units before plotting. `contributions['Data'][k]` and `contributions['Total']` are `Quantity`; `millify()` at `output_utilities.py:174` does `float(n)`, and `Quantity` declares `__slots__` with no `__float__`, so this raises `TypeError`. `ax.barh(name, Quantity)` and the `Total / label_offset` division at `:94` fail the same way. The fix must materialise floats via `q.unit[f'USD/{functional_unit.unit}']` (or `.base_value`) at the boundary. Also retarget the `:118` comparison at `'Total Cost of Product'`, or better, drive the axis label off `dcf.functional_unit.unit` so it survives the next functional-unit change.

*Known upstream?* **NEW.**

## 1.2 Sensitivity_Analysis — **BROKEN**

**Dead references:** `:93` `sensitivity_results[name]['Values'][shown_value] = dcf.h2_cost`; `:172` `base_case = self.base_case.h2_cost`.

**Still works:** the whole parameter-sweep machinery — `parse_parameter` (`:53`), `get_by_path`/`set_by_path` with `value_type` (`:60`, `:74`), deep-copying `self.inp` per variation (`:68`), and the plotting geometry.

**Independent bug (META-5).** At `:83-86`:

``python
sensitivity_results[name]['Base'] = '{0}%'.format(dynamic_value_formatting(
                                    get_by_path(self.inp, parameters) * 100),
                                    cutoff = format_cutoff)
``

The closing paren lands after the `dynamic_value_formatting(...)` argument, so `cutoff=format_cutoff` is passed to `str.format`, where it is a silently-ignored unused kwarg. Percentage-typed parameters therefore always format at the default cutoff of 6 while every other row honours the user's `format_cutoff`. Purely cosmetic, but silent and trivially fixable — move the paren.

**Latent trap.** `:60` calls `dynamic_value_formatting(get_by_path(self.inp, parameters))` on the **raw** parsed dict. If the targeted `Value` cell contains a reference string rather than a literal (entirely normal in current inputs — see `Photovoltaic > Nominal Power (kW) > Value` in `data/PV_E/Base/PV_E_Base.md`), `dynamic_value_formatting` hits its `raise ValueError('{0} is non-numeric...')` at `output_utilities.py:243`. A UI must either restrict the sensitivity parameter picker to literal-valued cells or catch this.

**Minimal conceptual fix:** `dcf.inp['Dependent Variables']['Levelized cost']['Value'].unit[f'USD/{unit}']` at both `:93` and `:172`. Note `:172` feeds `patches.Rectangle` arithmetic (`base_case - lower`) and `:101-107` does `min`/`max` over the dict — all of which need real floats, not `Quantity`.

*Known upstream?* **NEW.**

## 1.3 Waterfall_Analysis — **BROKEN**

**Dead references:** `:52` `results['Base Case'] = {'Value': self.base_case.h2_cost}` and `:102` `output[variable]['Value'] = dcf.h2_cost`. `:52` sits inside `perform_waterfall_analysis()`, which `__init__` calls at `:42` — so this module fails at **construction**, before any method row runs. Of the analysis modules it is the earliest to die.

**Still works:** the cumulative-modification algorithm (`:54-58`), `modify_inp_run_dcf` path/type handling (`:79-97`), the relative-change arithmetic (`:60-67`).

**Independent bug (META-7).** `:234`:

``python
ax.annotate(format_value_dollar_sign(df[i]['Value'], cutoff, currency, decimal_places),
            xy = (counter, y_label), va='center', ha='center', color=color)
``

The bar this labels is drawn from `df[i]['Relative Change']` (`:212-226`) and `y_label` is positioned relative to the *change*. The commented-out predecessor two lines up (`:231-233`) used `df[i]['Relative Change']` — the switch to `format_value_dollar_sign` swapped the field as well as the formatter. Every step bar in a waterfall chart is now annotated with the running total instead of its own delta, which is precisely the number a waterfall chart exists to show. The base-case bar (`:203`) and the final "Adjusted" bar are correct because they genuinely are totals.

**Minimal conceptual fix:** `:234` → `format_value_dollar_sign(df[i]['Relative Change'], ...)`; `:52`/`:102` → unwrapped `Dependent Variables > Levelized cost > Value`.

*Known upstream?* **NEW.**

## 1.4 Monte_Carlo_Analysis — **BROKEN** (and the blast radius for two more modules)

**Dead reference:** `:317` `h2_cost.append(dcf.h2_cost)` inside `perform_h2_cost_calculation`'s sample loop. Every sampling path funnels through here, so nothing downstream can run.

**Still works:** `read_results()` (`:391-500`) needs no DCF at all, so a model configured with `Monte_Carlo_Analysis > Input File` *reads* fine — which is exactly what the shipped `Example/210613_PV_E.md` does. Everything after (`target_price_components`, `determine_principal_components`, `development_distance`, `full_distance_cost_relationship`, and the histogram/scatter/cost-relationship plots) operates on the loaded array and is independent of `h2_cost`. **Practical consequence: with a pre-computed CSV, this module is one line from working.** Without one, it is unrecoverable. That is the single most important fact for the UI agent's MC feature.

### Independent bugs in this file

**META-9 — `:114` `if metric is 'cityblock':`.** Identity comparison against a string literal. It works today only because the default argument `metric='cityblock'` is the same interned constant. The moment a `metric` value arrives from a parsed input file (`Arguments` tables flow through `ast.literal_eval` in `run_pyH2A.get_arguments`, producing fresh string objects), the branch takes the `else` path and divides by `sqrt(n)` instead of `n`. Distances silently shrink by `sqrt(n)`, and since "development distance" is the module's headline output, the numbers would be wrong without any error. Python emits a `SyntaxWarning` for this on 3.8+. Fix: `==`.

**META-10 — `:664` `def target_price_2D_region(self, ...)` vs `:718` `self.target_price_2D_region = {...}`.** The method assigns a dict over its own name on the instance. `plot_colored_scatter` calls `self.target_price_2D_region()` at `:~914` and immediately subscripts `self.target_price_2D_region['Grid Values']` — so the first call works and every subsequent call raises `TypeError: 'dict' object is not callable`. In a Streamlit app, where a user re-renders the same plot on every widget change against a cached model object, this fails on the *second* interaction. Fix: name the result `self._target_price_2D_region_data` (or have the method return the dict and let the caller hold it).

**META-11 — `:481-491`, the `File Index` remap.** Two defects in ten lines:

``python
for self_key, self_parameter in self.parameters.items():
    sucess = False                                  # <- reset every iteration
    if self_parameter['Index'] == parameter['File Index']:
        self_parameter['Input Index'] = counter
        self.parameters[parameter['Name']] = self.parameters.pop(self_key)
        sucess = True
if sucess is False:
    raise KeyError('Input Parameter {0} could not be mapped.'.format(key))
``

(a) `sucess` is re-initialised at the top of each iteration, so the post-loop check reads only the **last** iteration's outcome. A successful match on any non-final parameter is reported as a mapping failure. (b) The body pops from and inserts into `self.parameters` while iterating it; the size happens to be restored so CPython does not raise, but the newly-inserted key may or may not be visited depending on hash placement — undefined behaviour by contract. Fix: hoist `sucess = False` above the loop, `break` on match, and collect remaps into a separate dict applied after iteration.

**META-12 — `:~1006` `ax = Axes3D(fig, auto_add_to_figure=False)`.** `auto_add_to_figure` was expired in matplotlib 3.7 (matplotlib PR #24251, milestone v3.7.0); passing it now raises. `pyproject.toml` requires `matplotlib>=3.9.4`, so `plot_colored_scatter_3D` cannot run on any supported install. Fix: `ax = fig.add_subplot(projection='3d')`.

**META-13 — `:1`, `:321-350`.** `perform_monte_carlo_multiprocessing` contains no multiprocessing: `num_cpus`, `Pool`, `divide_into_batches`, and `pool.map` are all commented out (`:342-348`), leaving a plain serial call at `:350`. `import multiprocessing` (`:1`) and the module-level `divide_into_batches` helper (`:24-38`) are now dead. **This is good news for stlite** — Pyodide has no `multiprocessing` — but the name is actively misleading and a maintainer restoring the pool would break the browser target. Either rename to `perform_monte_carlo` or gate the pool behind a capability check.

**META-45 — `:461` via `read_textfile`.** Results are loaded through `input_modification.read_textfile`, decorated `@lru_cache(maxsize=None)` at `input_modification.py:152`. Re-running MC after regenerating the CSV inside one process returns the stale array. Same cache mechanism as issue **#152** (which reports the unhashable-`Quantity` leak); this is a distinct symptom of the same decorator.

**META-46 — `:~927`, `:~1000`.** `plot_colored_scatter` indexes `pc[0..2]` and `plot_colored_scatter_3D` indexes `pc[0..3]` with no arity guard. A 2-parameter Monte Carlo (perfectly reasonable) produces a bare `IndexError: list index out of range` with no indication that the user needed a third parameter. Textbook instance of issue **#141** (incomprehensible errors); the finding itself is NEW.

**META-44 (UI-FACT) — `:206-212`, `:389`.** `__init__` branches on `'Input File' in self.inp['Monte_Carlo_Analysis']`; the `else` branch unconditionally reads `...['Output File']['Value']` and `np.savetxt`s there. Supplying neither key yields `KeyError: 'Output File'` *after* the full simulation has already run. A browser UI must inject one of the two, and must intercept the `savetxt` (`:389`) since there is no meaningful filesystem.

**META-50 — `:~1255`.** `plot_target_parameters_by_distance` has a `'''\n\n'''` docstring and plots `self.results_distances_sorted[:,3]` — column 3 hardcoded, meaningful only for a 4-parameter model. It is nevertheless wired up in the shipped `data/PV_E/Base/PV_E_Base_Figures.md` method table.

*Known upstream?* All **NEW**; META-45 adjacent to **#152**, META-46 an instance of **#141**.

## 1.5 Comparative_MC_Analysis — **BROKEN (transitively)**

No `h2_cost` / `contributions` references of its own. It fails only because `get_models()` at `:34` constructs a `Monte_Carlo_Analysis` per row of the `Comparative_MC_Analysis` table. If every referenced model supplies a Monte Carlo `Input File`, this module runs today (see 1.4). It becomes RUNNABLE the moment META-8 is fixed — no changes needed here.

**META-48 (UI-FACT).** Return types are inconsistent across the file: `plot_comparative_distance_histogram` returns `figure.fig`, `plot_combined_distance` returns a raw `fig` built by `plt.figure` + `gridspec` (bypassing `Figure_Lean`'s subplot construction entirely), but `plot_comparative_distance_cost_relationship` returns the **`Figure_Lean` wrapper object** (`:~205`, guarded by `return_figure`). A UI that does `st.pyplot(result)` will get a `Figure_Lean` for that one method and fail. Its own docstring even says `figure : Figure_Lean object` while every sibling promises `matplotlib.fig`.

**META-43 (USABILITY).** Model paths in the table are `./PEC/Base/PEC_Base.md` — resolved by `file_import` → `Path(file_name)` → CWD-relative, not relative to the file that names them. Running the same input file from a different directory silently fails.

*Known upstream?* **NEW.**

## 1.6 Development_Distance_Time_Analysis — **BROKEN (transitively)**

Same story: `:78` builds a `Monte_Carlo_Analysis`. Its own logic (historical-data import, parameter mapping, linear/asymptotic fitting, twin time axes) never touches a removed attribute and is sound. Fix META-8 and this module becomes RUNNABLE.

**META-17 (BUG).** Docstring `:59` declares `Development_Distance_Time_Analysis > Extrapolation Limit > Year : int`. Code `:94` reads `self.inp['Development_Distance_Time_Analysis']['Extrapolation Limit Year']['Value']`. Different middle key **and** different bottom key. This is not a cosmetic docstring nit — `plugin_input_output_processing.extract_input_output_from_docstring` parses exactly this section to build the input-file template, so `pyH2A generate` emits a table the module cannot read, and the user gets `KeyError: 'Extrapolation Limit Year'`. Compare `:57` (`Base Year > Value`), which does match `:93`. Fix the docstring to `Extrapolation Limit Year > Value`.

**META-18 (SMELL).** `:88` `if ...['Log Normalization']['Value'] == 'False':`. `num()` (`input_modification.py:174`) leaves `False` as the string `'False'`, so the shipped-format path works — but a boolean `False`, `0`, `false`, or `no` all fall through to `else` and silently enable log normalisation, which materially changes every distance in the module.

**Input-file gotcha:** `harmonize_monte_carlo_parameters` (`:139-158`) *appends* columns for MC parameters absent from the historical file, then asserts set-equality — but `map_parameters` (`:118-137`) raises `KeyError` for historical columns absent from MC. Asymmetric and worth documenting: the historical file may be a subset of the MC parameters, never a superset.

*Known upstream?* **NEW.**

## 1.7 Optimization_Analysis — **BROKEN**

`:85-87` passes `discounted_cash_flow_function_1D` to `scipy.optimize.differential_evolution`. That function (`Discounted_Cash_Flow.py:80-109`) defaults `attribute='h2_cost'` and does `getattr(dcf, attribute)` at `:102` → `AttributeError` on the very first objective evaluation.

**META-16 (USABILITY).** The class docstring `:29-34` has a `Parameters` header with nothing under it — so `pyH2A generate` produces no prompts for this module at all. Worse, `data/PV_E/Base/PV_E_Base_Optimization.md` ships a `# Optimization_Analysis` table declaring `Algorithm | differential_evolution`, `Target | dcf.h2_cost`, `Direction | minimize`, and **none of the three is ever read** — `process_parameters` (`:53`) only touches `Parameters - Optimization_Analysis`. The `# Optimization_Analysis` header exists purely to satisfy `check_for_meta_module`. Its `Target | dcf.h2_cost` entry is also a fossil of the removed attribute. Either honour those three keys or delete them from the shipped input and document the header as a bare trigger.

**META-15 (BUG, in `Discounted_Cash_Flow.py` but owned by this layer).** Both `discounted_cash_flow_function` (`:9-77`) and `discounted_cash_flow_function_1D` (`:80-109`) default `attribute='h2_cost'`. `discounted_cash_flow_function` additionally declares a `dependent_variable='{Dependent Variables > Levelized Cost > Value, USD/kg}'` parameter at `:12` that appears **nowhere in the body** — a half-landed migration, and its capital-L `Levelized Cost` does not even match the plugin's `Levelized cost` key. The public contract of these two wrappers is the natural seam for a UI to call the engine programmatically, so it should be fixed first: default to resolving the dependent variable from `dcf.inp` and drop `attribute`, or at minimum default `attribute` to something that exists.

**Not multiprocessed, but expensive:** `differential_evolution` over 2 bounds runs hundreds of full DCF evaluations serially. Any UI exposing this needs a progress mechanism and a hard iteration cap.

*Known upstream?* **NEW.**

## 1.8 Classification summary

| module | class | why | fix size |
|---|---|---|---|
| Cost_Contributions_Analysis | **BROKEN** | `base_case.contributions` (META-1) + Quantity unwrap (META-3) + stale group name (META-2) | small, 3 sites |
| Sensitivity_Analysis | **BROKEN** | `dcf.h2_cost` ×2 (META-4) + Quantity unwrap | small, 2 sites |
| Waterfall_Analysis | **BROKEN** | `h2_cost` ×2, fails in `__init__` (META-6) | small, 2 sites + META-7 |
| Monte_Carlo_Analysis | **BROKEN**; **PARTIALLY runnable** via `Input File` | `dcf.h2_cost` (META-8) blocks sampling only | 1 site + 4 independent bugs |
| Comparative_MC_Analysis | **BROKEN (transitive)** | wraps MC | 0 sites of its own |
| Development_Distance_Time_Analysis | **BROKEN (transitive)** | wraps MC | 0 sites; META-17 separate |
| Optimization_Analysis | **BROKEN** | wrapper default `attribute='h2_cost'` (META-14/15) | 1 site in `Discounted_Cash_Flow.py` |

**The whole layer is ~8 read-sites plus one shared unit-unwrap helper.** That is the good news; the bad news is that no test covers any of it, so nothing caught the regression.

## 1.9 Runtime facts a UI must know (multiprocessing, file writes, `show()`)

- **Multiprocessing: none.** The only pool in the codebase is commented out (META-13). Nothing in the meta layer forks. Safe for stlite/Pyodide as-is.
- **File writes:**
  - `Monte_Carlo_Analysis.save_results` → `np.savetxt(Path(file_name), ...)` at `:389`, path taken verbatim from `Monte_Carlo_Analysis > Output File > Value`.
  - `Figure_Lean.save_figure` → `self.fig.savefig(PurePath(self.directory, self.name + suffix))` at `output_utilities.py:163-172`; `.pdf` by default (`pdf=True`), `.png` only when `pdf=False`.
  - `Template_File.write_template_file` → `open(Path(file_name), 'w')` at `plugin_input_output_processing.py:~348`.
  - Figure filenames are `{name}_{input_file_name}` when `append_file_name` is true and `input_file_name` is set (`output_utilities.py:139-142`) — and `run_pyH2A` always sets it for plot methods, so the actual on-disk name is *not* the `name` the user typed in the Arguments table.
- **`plt.show()` calls:** `Figure_Lean.execute` at `output_utilities.py:149` (reached whenever `show: True` — and the shipped `data/PV_E/Base/PV_E_Base_Figures.md` sets `show: True` for `waterfall_chart` and both comparative methods), plus a hardcoded unconditional `plt.show()` in `plot_colored_scatter_3D`. The `else` branch calls `plt.close()` — note this closes the *current* figure, which during nested/comparative plotting is not necessarily the one being finalised.
- **Global state:** `set_font` (`output_utilities.py:30-48`) writes `rcParams['font.family']`, `['font.sans-serif']=['Arial']`, `['font.size']` on **every** `Figure_Lean` construction. Arial is absent from most Linux and all Pyodide environments → per-figure font-fallback warnings and non-deterministic layout.
- **Method dispatch:** `run_pyH2A.execute_module_methods` (`:87-101`) does `getattr(module, table['Method Name'])` and `method(**arguments)`, storing the return in `meta_dict[module_name][row_name]`. Any public method is reachable from an input file — this is arbitrary-attribute dispatch driven by a markdown cell, worth knowing before exposing it to untrusted input.
- **Plot detection (META-30):** `check_for_plotting_method` (`:119-129`) is a substring test on `['plot', 'figure', 'chart']`. Matching methods get `directory` and `input_file_name` injected. Two consequences: a non-plotting method whose name happens to contain `plot` gets two unexpected kwargs; and a genuinely plotting method named without those substrings gets no `directory` and dies inside `Figure_Lean` with `TypeError: missing required argument 'directory'`.
- **Cost (META-31):** `pyH2A.__init__` parses the input file at `:47` and constructs a `Discounted_Cash_Flow` at `:49`; then **each** analysis module re-parses the same file and re-runs its own DCF (`Sensitivity:38-39`, `Waterfall:40-41`, `Cost_Contributions:25`, `Comparative` → one MC per model). A four-module input file runs the DCF at least five times before any sampling. Two independent `inp` dicts also exist per run — `pyH2A.inp` (raw) and `pyH2A.base_case.inp` (plugin-processed) — and `meta_workflow` scans the raw one while the printed result comes from the processed one (`:56`).

---

# 2. Input-table contract of each analysis module

A UI generating input files needs all of this. Trigger rule first, from `input_modification.check_for_meta_module` (`:94-110`): a top-level table is treated as an analysis module iff its name **contains `Analysis`** and contains **none** of `Parameters`, `Methods`, `Arguments`, `Deactivate`. The module name is `key.split(' ')[-1]` (`run_pyH2A.py:70`). Appending ` - Deactivate` is therefore the documented off-switch, and `check_processing`'s `exception_group = 'Analysis'` (`Discounted_Cash_Flow.py:214`) keeps all such tables from triggering "not processed" warnings.

### Universal `Methods - <Module>` table

``markdown
# Methods - <Module_Name>

Name | Method Name | Arguments
--- | --- | ---
<arbitrary row label> | <python method name> | <dict literal> OR <name of an Arguments table>
``

`Name` is only the key under which the return value is stored. `Arguments` is resolved by `get_arguments` (`run_pyH2A.py:103-118`): first tried as `self.inp[<cell>]` (an `# Arguments - ...` table, converted with `convert_dict_to_kwargs_dict`, which `ast.literal_eval`s each `Value`), and on `KeyError` `ast.literal_eval`ed directly as a dict literal. **An omitted `Arguments` column yields `{}`; an empty cell yields the string `'n/a'` and crashes (META-29).** Referenced `# Arguments - ...` tables must have `Name | Value` columns.

### `Cost_Contributions_Analysis`
- Trigger table: `# Cost_Contributions_Analysis` — **body-less**, header alone (documented at `:11-12`). Note the markdown parser (`convert_file_to_dictionary`) yields `{}` for it, which is fine.
- Method: `cost_breakdown_plot(ax, figure_lean, plugin, plugin_property, label_offset, x_label_string, x_label_string_H2, plot_kwargs, **kwargs)`. `plugin`/`plugin_property` select a plugin-local contributions dict (e.g. `'Capital_Cost_Plugin'` / `'direct_contributions'`); both `None` selects the overall breakdown (currently the broken path).

### `Sensitivity_Analysis`
``markdown
# Sensitivity_Analysis

Parameter | Name | Type | Values
--- | --- | --- | ---
Top > Middle > Bottom | <display label> | value|factor | <low>; <high>
``
First column **is** the path (`parse_parameter(key)`, `:53`). `Type` ∈ {`value`, `factor`} → `set_by_path` replaces or multiplies. `Values` is `;`-separated; order irrelevant. A `%` in a value switches the display formatting branch (`:80-86`). Row order is irrelevant (bars are sorted by cost increase).
- Method: `sensitivity_box_plot(ax, figure_lean, height, label_offset, lim_extra, format_cutoff, plot_kwargs, **kwargs)`.

### `Waterfall_Analysis`
``markdown
# Waterfall_Analysis

Parameter | Name | Type | Value | Show Percent
--- | --- | --- | --- | ---
Top > Middle > Bottom | <label> | value|factor | <single value> | True
``
Singular `Value`, not `Values`. **Row order is significant** — changes are applied cumulatively top-to-bottom. `Show Percent` is presence-tested, not value-tested (`:107-113`), so *any* non-empty cell enables percent display.
- Method: `plot_waterfall_chart(ax, figure_lean, width, connection_width, label_offset, plot_sorted, y_axis_label, currency, decimal_places, cutoff, plot_kwargs, **kwargs)`.

### `Monte_Carlo_Analysis` — two tables, both required
``markdown
# Monte_Carlo_Analysis

Name | Value
--- | ---
Samples | 50000                      <- required unless Input File given
Target Price Range ($) | 1.5; 1.6    <- ALWAYS required
Output File | <path>                 <- required iff Input File absent
Input File | <path>                  <- if present, skips simulation entirely

# Parameters - Monte_Carlo_Analysis

Parameter | Name | Type | Values | File Index
--- | --- | --- | --- | ---
Top > Middle > Bottom | <label> | value|factor | Base; 220 | 0
``
`Values` accepts the literals `Base`/`Reference` (`special_values`, `:246`) meaning "current value in the input file". `File Index` is the 0-based column in a saved CSV and is only consulted when the display `Name` differs from the stored one (`:475-491`, see META-11). **Parameter order is semantic**: `Input Index` maps parameter 0 → x-axis, 1 → y-axis, 2 → colour, 3 → z-axis in the scatter plots (`determine_principal_components`, `:637-651`), and `target_price_2D_region` grids only the first two.
- Methods: `plot_complete_histogram`, `plot_colored_scatter` (needs ≥3 params), `plot_colored_scatter_3D` (≥4, and broken — META-12), `plot_distance_histogram`, `plot_distance_cost_relationship`, `plot_target_parameters_by_distance`. `render_parameter_table` is a helper reached only through `table_kwargs`.

### `Comparative_MC_Analysis`
``markdown
# Comparative_MC_Analysis

Name | Value | Image
--- | --- | ---
<arbitrary model key> | <path to that model's input .md> | <optional image path>
``
Each referenced file must itself be a complete Monte-Carlo-configured input. `Image` accepts the `package.subdir~file` form (`file_import`, `:114-152`). All models must declare an **identical** `Target Price Range ($)` — asserted at `:52-58`.
- Methods: `plot_comparative_distance_histogram`, `plot_comparative_distance_cost_relationship` (returns a `Figure_Lean`, META-48), `plot_combined_distance`.

### `Development_Distance_Time_Analysis`
``markdown
# Development_Distance_Time_Analysis

Name | Value
--- | ---
Input File | <tab-separated historical data file>
Log Normalization | False
Base Year | 2020
Extrapolation Limit Year | 2050        <- NOT "Extrapolation Limit | Year", see META-17
``
Also requires a full `Monte_Carlo_Analysis` + `Parameters - Monte_Carlo_Analysis` pair, since it constructs one internally (`:78`). The historical file must be tab-separated with a `#`-prefixed header whose first column is `Year` and whose remaining column names **exactly match** the `Name` values in `Parameters - Monte_Carlo_Analysis` (unmatched columns → `KeyError` at `:135`; missing ones are auto-filled at reference value, `:145-155`).
- Methods: `plot_distance_histogram`, `plot_distance_cost_relationship`, `plot_distance_time_relationship`.

### `Optimization_Analysis`
``markdown
# Optimization_Analysis          <- required as trigger; contents ignored (META-16)

# Parameters - Optimization_Analysis

Parameter | Bounds
--- | ---
Top > Middle > Bottom | 4000; 15000
``
No `Methods` table — `perform_optimization` runs from `__init__` (`:50`) and only prints to stdout. Nothing is returned or stored in `dcf.inp`, so a UI has to capture stdout or refactor. `Bounds` also accepts `Base`/`Reference`.

---

# 3. `plugin_input_output_processing.py` and `pyH2A generate` — statically broken, confirmed

**The claim holds. Three independent hard failures, in execution order.**

**META-22 — `:182`, `Workflow[key]['Type']`.**
``python
data = self.get_docstring_data(key, self.inp_stub['Workflow'][key]['Type'])
``
The `Type` column was removed from the Workflow table (commit 1045570). Current inputs prove it: `Config/Defaults_TEA.md:3` is `Name | Position | Description`, and `src/tests/end_to_end/Testing_Plugin_IO.md:9` is `Name | Position`. `Discounted_Cash_Flow.workflow` (`:198-204`) ignores `Type` entirely — it sorts on `Position` and calls `execute_plugin(key, ...)` with the default `plugin_module=True`, so **everything** in Workflow is now imported from `Plugins/`. Any modern input file therefore gives `KeyError: 'Type'` here. (Legacy files under `Example/` still carry a `Type` column, which is why the breakage is not universal — it is worse: it works on the stale examples and fails on the current ones.)

**META-21 — `:125-133` + `:196`.** Even with `Type` present, `__init__` injects two synthetic Workflow rows:
``python
pre_workflow  = {'Description': ..., 'Position': -1,  'Type': 'function'}
post_workflow = {'Description': ..., 'Position': ..., 'Type': 'function'}
``
and `get_docstring_data` resolves `Type == 'function'` via `getattr(Discounted_Cash_Flow, target_name)` at `:196`. `Discounted_Cash_Flow` now defines exactly `__init__`, `workflow`, `check_processing` (`Discounted_Cash_Flow.py:186-220`). `pre_workflow` and `post_workflow` were deleted by #176 → `AttributeError`. Because `pre_workflow` sits at `Position: -1` it is the **first** key in `sorted_keys`, so this fires immediately, before any plugin is inspected. This is unconditional — it does not depend on the user's input file at all.

**META-20 — `:147-148`.**
``python
self.inp = merge(self.inp,
                 convert_input_to_dictionary(input_file_stub, merge_default = False))
``
`convert_input_to_dictionary(file)` takes exactly one parameter (`input_modification.py:342`). The `merge_default` kwarg vanished with the move to the `# Input files to merge` mechanism. `TypeError: convert_input_to_dictionary() got an unexpected keyword argument`. Unreachable today because META-21 fires first, but it is the third mine on the same path.

**META-23 (SMELL) — the whole approach is obsolete.** `extract_input_output_from_docstring` (`:35-80`) reconstructs the plugin contract by *counting leading spaces* in a docstring (`is_parameter_or_output`, `:7-12`, with a `spaces_cutoff` that differs between plugins and functions: 5 vs 9 at `:197`). Plugins now carry a machine-readable `input_dict`/`output_dict` (see `Capital_Cost_Plugin.py:88+`) and `Utilities/docstring_generation.py` already generates docstrings **from** those specs. Regenerating the template from the specs directly would make META-17-style docstring/code divergence structurally impossible and eliminate the space-counting heuristic. `convert_requirements_to_inp` (`:229-247`) passing `print_info`/`add_processed`/`insert_path` to `insert()` is, for the record, **fine** — that signature is unchanged (`input_modification.py:397-398`).

**What `pyH2A generate` does and whether it works.** `cli_pyH2A.generate` (`:24-33`) takes `-i/--input_file`, `-o/--output_file`, `--origin/--no-origin`, `--comments/--no-comments` and calls `Generate_Template_Input_File(input_file, output_file, origin=..., comment=...)`. Intent: read a stub containing only a `Workflow` table plus analysis headers, walk the workflow in position order, diff each plugin's documented `Parameters` against the accumulated `Output` of everything upstream, and write a markdown template listing every still-unsatisfied input (`generate_requirements`, `:174-189`). It also auto-appends analysis modules to the workflow (`get_analysis_modules`, `:159-172`) so their docstring-declared parameters get prompted too — which is precisely how META-17's wrong key would reach a user.

**Verdict: it does not work on master.** It fails at `:196` for every input, and would fail at `:182` and `:147` afterwards. Note `guide.rst` presents `pyH2A generate -i input.md -o input_full.md --origin --comments` as **step 2 of the documented getting-started flow** — so the first command a new user runs after choosing plugins is broken.

*Known upstream?* **NEW** (no corpus issue/PR references `Generate_Template_Input_File` or `pyH2A generate`).

---

# 4. `LCA/` — what exists, what it needs, what can reach it

**Contents:** `LCA/__init__.py`, `LCA/LCA.py` (317 lines), `LCA/LCA_lib.py` (207 lines, vendored verbatim from openLCA under MPL-2.0 — see its header).

**`LCA_lib.py`** provides `ExportFolder`, `Matrix`, `TechEntry`, `FlowEntry`, `ImpactEntry`, `solve`. It reads an openLCA matrix export directory: index files `index_A` / `index_B` / `index_C` and matrix files `A`, `B`, `C`, `f`, in `.csv` / `.xlsx` / `.npy` / `.npz`.

**`LCA.py`** wraps it: `import_folder` (asserts `has_impacts()`), `load_matrices`, `build_scaling_vector(dcf)`, `perform_LCA` (`g = B @ s`, `h = C @ g`, results into `self.lca_results` keyed by impact name with `{'value', 'unit'}`). `process_LCA_table` maps pyH2A rows to scaling-vector slots by `UUID`, with a hardcoded four-entry conversion table `{('ton','kg'):1000, ('kg','kg'):1, ('kWh','MJ'):3.6, ('MJ','MJ'):1}` — anything else raises `ValueError`. Note this duplicates, badly and in miniature, the `Quantity` unit system that the rest of the codebase now uses.

**What it needs on disk:** a `matrix_folder` (from `# Life Cycle Assessment > Matrix Folder > Value`, e.g. `data/LCA/LCA_Test_Data`) containing `index_A`, `index_B`, `index_C`, `A`, `B`, `C`, `f`. **META-26: `data/LCA/LCA_Test_Data/` contains only `README.md`** — the openLCA format description, no data. The only shipped LCA fixture cannot be loaded. `lcia_example()` at `:~262` hardcodes `ExportFolder('data/LCA/LCA_Test_Data')`, i.e. CWD-relative, and pprints a hardcoded UUID.

**Can anything on master invoke it? No — META-27.** A grep for `LCA` / `Life_Cycle` / `Life Cycle` across `src/pyH2A/Plugins/`, `src/pyH2A/Utilities/`, `Discounted_Cash_Flow.py`, `run_pyH2A.py` and `src/tests/` returns **zero matches**. Three independent reasons it is unreachable:
1. `Plugins/Life_Cycle_Assessment_Plugin.py` does not exist, so no Workflow row can import it.
2. `check_for_meta_module` requires the substring `Analysis`; `Life Cycle Assessment` does not contain it, so the meta path cannot pick it up either.
3. Nothing constructs `LCA(...)` anywhere.

**META-24 makes this actively harmful.** `Config/Defaults_LCA.md:6` and `Config/Defaults_TEA_LCA.md:14` both schedule `Life_Cycle_Assessment_Plugin` (positions 300 and 1000). Any input file whose `# Input files to merge` points at either default gets that row merged into its Workflow, and `import_plugin` (`input_modification.py:48`) does `import_module('pyH2A.Plugins.Life_Cycle_Assessment_Plugin')` → **`ModuleNotFoundError`**. Two of the three shipped default configs are unusable. Either the plugin is missing from the commit or the defaults were written ahead of it; either way a maintainer can confirm in seconds and the fix is trivial (add the plugin, or drop the row until it lands).

**META-25 — `LCA.py:17`, `:67`.** `from pyH2A import Discounted_Cash_Flow` imports the **module** `pyH2A.Discounted_Cash_Flow`, not the class inside it. It is then used as an annotation, `def __init__(self, matrix_folder: str, dcf: Discounted_Cash_Flow)`. Annotations are evaluated at `def` time, and a module object is a legal annotation value, so this does not raise — it is simply wrong, and any tooling that trusts the annotation is misled. Should be `from pyH2A.Discounted_Cash_Flow import Discounted_Cash_Flow`.

**META-28 — `LCA.py:167`.** `total_H2_production = np.sum(dcf.inp['Technical Operating Parameters and Specifications']['Output per Year at Gate']['Value'])`. Hardcodes both the table path and the H2 assumption (contradicting the whole point of the flexible functional unit from #176 — the variable is even named `total_H2_production`), and `np.sum` papers over whether that value is a scalar or an array — the exact ambiguity of issue **#87**. Post-#176 that cell also holds a `Quantity`, on which `np.sum` will not do anything sensible. Related: issue **#110** ("Computing life time H2/product production in production_scaling_plugin… This is what needs to be referenced by the LCA table") is CLOSED as completed, so the intended replacement source likely already exists and this call site was never migrated.

*Known upstream?* META-24/25/26/27 **NEW**. META-28 overlaps **#87** (float-vs-array) and **#110** (production total for LCA). Issue **#132** (circular LCA↔DCF dependency) is closed and is the likely reason the plugin is absent.

---

# 5. Documentation drift catalogue (`doc/`)

**META-36 — `doc/pyH2A/default_settings.rst` — the worst offender.** Its "Default Settings" Workflow block is entirely pre-#176:
- Lists six `function`-type rows (`production` @400, `initial_equity_depreciable_capital` @600, `non_depreciable_capital_costs` @700, `replacement_costs` @900, `fixed_operating_costs` @1200, `variable_operating_costs` @1400). **None of these methods exist**; all DCF math moved into `Discounted_Cash_Flow_Plugin` @900.
- Uses the removed `Type` column.
- Omits `Discounted_Cash_Flow_Plugin` entirely — the plugin that produces the answer.
- Omits the `# Functional Unit` table, which `Discounted_Cash_Flow.__init__:192` reads **unconditionally** and which is now the hardest requirement in the whole input format.
- The `Financial Input Values` table uses the old short-name schema (`ref year`, `equity`, `irr`, `debt | Constant`, `depreciation type | MACRS`) and a broken 4-column-header/3-column-separator markdown table. Current `Config/Defaults_TEA.md` uses long names (`Reference year`, `Fraction equity financing`, `After-tax real IRR`) with a `Unit` column, and has dropped `debt`/`depreciation type` as rows.

This page is referenced from `guide.rst` as the authority on default positions. Replace it with a literal include of `src/pyH2A/Config/Defaults_TEA.md`.

**META-37 — `doc/guide.rst`.**
- `:32-40` teaches the removed `Type` column in the very first Workflow example a new user sees.
- Never mentions `# Functional Unit` or `# Input files to merge`, the two tables now required to get a running model.
- Shows `Levelized cost of hydrogen (base case): 3.5777931317137512 $/kg`. `run_pyH2A.py:57` prints `f'Levelized cost of product (base case): {levelized_cost}'` where `levelized_cost` is a `Quantity` — actual output is `Levelized cost of product (base case): Quantity(3.577…, 'USD/kg')`. Wrong label and wrong format.
- Documents `pyH2A generate` as step 2 of the tutorial; it is broken (§3).
- The `Direct Capital Cost` template snippet shows `Parameter | Value | Comment Value` output that the broken generator can no longer produce.

**META-40 — `doc/plugins/Plugin_Guide.rst`.** Partially updated: it correctly shows `input_dict`/`output_dict` and `input_resolver_function`/`output_inserter_function`. But `:57` gives the constructor as `def __init__(self, dcf, print_info):` doing the work inline, whereas every real plugin uses the three-part shape (`Capital_Cost_Plugin.py:85-91`):
``python
def __init__(self, dcf, print_info, run = True):
    self._set_up(dcf)
    if run:
        self._run(dcf)
``
The `run=True` flag, the `_set_up`/`_run` split, and `self.functional_unit = dcf.functional_unit` are all undocumented — and `run=False` is exactly the hook a UI would want for introspecting a plugin's `input_dict` without executing it. The guide also does not mention `Utilities/docstring_generation.generate_docstring`, even though it closes with "It is important to include the `numpydoc` formatted docstring, since it is used to generate the input file template."

**META-38 — `doc/plugins/`.** `plugins.rst:15` lists `Fixed_Operating_Cost_Plugin`, and `Fixed_Operating_Cost_Plugin.rst:4` does `.. automodule:: pyH2A.Plugins.Fixed_Operating_Cost_Plugin`. **No such module** — the real ones are `Labor_Operating_Cost_Plugin.py` and `Other_Fixed_Operating_Cost_Plugin.py`. Sphinx emits an autodoc import error. Missing pages entirely: `Discounted_Cash_Flow_Plugin` (the most important plugin in the project), `Labor_Operating_Cost_Plugin`, `Other_Fixed_Operating_Cost_Plugin`.

**META-39 — `doc/utilities/utilities.rst:7`.** Toctree entry `Energy_Conversion`; no `doc/utilities/Energy_Conversion.rst` exists. Sphinx: "toctree contains reference to nonexisting document".

**META-40 (cont.) — `doc/analysis/analysis.rst`.** Six modules listed; `Optimization_Analysis` is absent. Also, because every analysis `.rst` is a bare `automodule` of a module whose class docstring documents its input tables, and those docstrings still describe `h2_cost`-era behaviour, the rendered analysis docs describe an engine that no longer exists — `Cost_Contributions_Analysis`'s own docstring (`:8-22`) is a good example: it still says "Reading cost contributions from DCF output" and references `sum_all_tables`, which was replaced by `sum_all_tables_quantity` (`input_modification.py:949`).

**META-41 — `src/pyH2A/Example/` is pre-#176 and cannot run.** All three shipped examples (`210613_PV_E.md`, `210511_Future_PEC_Type_4.md`, `211109_Future_PEC_Type_1_Figure_Test.md`) have a `Type`-column Workflow, **no `# Functional Unit` table, and no `# Input files to merge` table**. `Discounted_Cash_Flow.__init__:192` does `self.inp['Functional Unit']['Functional Unit']['Unit']` with no guard → `KeyError: 'Functional Unit'` before a single plugin runs. They also lack any `Discounted_Cash_Flow_Plugin` row, so even past that they would produce no cost. These files are shipped inside the wheel (`MANIFEST.in` includes `src/pyH2A/Example/*.md` and `*.csv`) and are the only in-package examples a user finds. The maintained equivalents live in the un-packaged `data/` tree.

`Other/` is image assets only (`pyH2A.svg/png`, `Sun.svg`, `PV_E_Clipart`, `PEC_Clipart`, `Photocatalytic_Clipart`, `PCE_Clipart.svg`) plus `__init__.py`, referenced from input files via the `pyH2A.Other~<file>` form and consumed by `output_utilities.insert_image`. `PCE_Clipart.svg` has no `.png` sibling while every other clipart does — and `insert_image` uses `mpimg.imread`, which cannot read SVG. Anything referencing `pyH2A.Other~PCE_Clipart.png` will fail.

**META-42 / META-43 — `data/` input hygiene.** `data/PV_E/Base/PV_E_Base_Figures.md` hardcodes `/Users/Jacob/Documents/Water_Splitting/Techno_Economic_Analysis/data/PV_E/Base/Monte_Carlo_Output.csv` and `/Users/Jacob/Documents/.../Untracked/Testing/historical_data_test.csv`. `Comparative_MC_Analysis` rows use `./PEC/Base/PEC_Base.md` (CWD-relative). `data/LCA/PV_E_Base.md` additionally carries `Grid Electricity > Cost ($/kWh) | 10000.12` — that is issue **#89**, already known; flagging only that it is still present in a shipped fixture.

---

# 6. CLI usability

`cli_pyH2A.py` builds a `click` group (`cli`) with `run` and `generate`; `setup.cfg:33-35` registers `pyH2A = pyH2A.cli_pyH2A:cli`. `__main__.py` is **empty (0 bytes)**, so `python -m pyH2A` silently does nothing and exits 0 — no error, no help, no hint. That is a two-line fix (`from pyH2A.cli_pyH2A import cli; cli()`) and worth doing since `python -m` is the natural invocation when the console script is not on `PATH`.

**Wrong / missing arguments.** Both options are `required=True`, so `click` handles the empty cases well: `pyH2A run` alone gives `Error: Missing option '-i' / '--input_file'.` with exit code 2, and `-h/--help` works at group and command level (`CONTEXT_SETTINGS`). `type=str` means no path validation whatsoever — `click.Path(exists=True, dir_okay=False)` on `-i` and `click.Path(file_okay=False)` on `-o` would convert two of the three failure modes below into clean CLI errors.

**Nonexistent input file.** Falls through to `file_import` → `open(Path(file_name), 'rb')` → raw `FileNotFoundError` traceback from four frames deep. No mention of which option was wrong.

**META-33 — nonexistent output directory.** Not checked anywhere. `output_directory` is stored (`run_pyH2A.py:46`), injected into plot-method kwargs (`:98`), and only touched at `output_utilities.py:163-166` when `save=True`: `PurePath(self.directory, self.name + suffix)` then `fig.savefig(...)`. So the failure happens **after** the full DCF, all analysis modules, and (potentially) a 50,000-sample Monte Carlo have run — the user loses the entire computation to a typo'd path. Worse, if a run has `save: False` on every method (as several shipped inputs do), a garbage `-o` is never noticed at all. Validate `-o` up front.

**Relative paths.** Three inconsistent resolution rules coexist, none documented:
1. `-o` and figure paths → CWD-relative (`PurePath` with no anchoring).
2. Input-file paths *inside* input files (`Input files to merge`, MC `Input File`/`Output File`, DDT `Input File`, Comparative model paths) → also CWD-relative, via `file_import` → `Path(file_name)` — **not** relative to the referring file (META-43).
3. Package resources → the `package.subpackage~filename` form, resolved through `importlib.resources` (`input_modification.py:132-142`).
So the same input file works from the repo root and fails from anywhere else. A UI should resolve (2) against the referring file's directory.

**No exit code on failure.** `run` calls `command_line_pyH2A` and assigns to an unused local (`cli_pyH2A.py:21`). Any engine exception propagates as an unhandled traceback (click exit code 1). Since **every** analysis module currently raises, the realistic user experience today is: DCF completes, levelized cost prints, then an `AttributeError: 'Discounted_Cash_Flow' object has no attribute 'h2_cost'` traceback with no indication that the analysis layer is the culprit. Directly in scope for issue **#141**.

**META-47 — packaging.** `pyproject.toml` declares a full PEP 621 `[project]` table (`name`, `version = "v0.0a8"`, `requires-python >= 3.9`, deps) while `setup.cfg` declares a competing `[metadata]`/`[options]` block (`version = attr: pyH2A.__version__` → `0.0a8`, `python_requires >= 3.7`, a *different* and much shorter `install_requires`). The console-script entry point exists **only** in `setup.cfg`, and `package_dir`/`packages = find:` likewise. This works today but is fragile: as soon as anyone adds `[project.scripts]` or `[tool.setuptools]`, the setup.cfg half stops being consulted and the `pyH2A` command vanishes. Also note the two version strings differ by a `v` prefix, and `pyproject` pulls in `furo`, `numpydoc`, `autodocsumm`, `autopep8` and `pytest` as **runtime** dependencies — a UI bundling this into Pyodide inherits all of them. Consolidate on `pyproject.toml`.

---

# 7. Consolidated UI-FACT list (stlite / Streamlit)

1. **No multiprocessing anywhere** — the only pool is commented out (META-13). Pyodide-safe as-is; do not "fix" it.
2. **Blocking `plt.show()`** at `output_utilities.py:149` and unconditionally in `plot_colored_scatter_3D`. Force `show: False` in every injected Arguments table.
3. **Direct filesystem writes**: `fig.savefig` (`output_utilities.py:166`), `np.savetxt` (`Monte_Carlo_Analysis.py:389`), `open(...,'w')` (template generator). Intercept all three; prefer `figure_lean=True` + capturing the returned `fig`.
4. **`figure_lean` is the escape hatch** — most plot methods return `figure.fig` when `figure_lean=True`. Exceptions: `plot_complete_histogram` and `plot_colored_scatter` always `execute()` and have no `figure_lean` param; `plot_comparative_distance_cost_relationship` returns a `Figure_Lean` wrapper (META-48); `plot_combined_distance` returns a raw `fig`.
5. **`Figure_Lean` requires `directory`** (no default). `run_pyH2A` supplies it only for methods matching `plot|figure|chart` (META-30). Calling any plot method directly from Python without `directory=` is a `TypeError`.
6. **Global `rcParams` mutation to Arial** on every figure (META-35) — expect font warnings and layout drift in-browser. Pre-set a bundled font.
7. **Results are `Quantity`, not floats.** `Dependent Variables > Levelized cost > Value` and every entry of `Levelized cost contributions > Value` are `Quantity` objects with `__slots__`, no `__float__`, no arithmetic. Use `q.unit['USD/kg']` / `q.base_value`. This is the single largest hidden cost in repairing the analysis layer.
8. **DCF re-runs per analysis module** (META-31) — 5+ full DCF evaluations for a 4-module file, plus N per sensitivity value, plus `Samples` per Monte Carlo, plus hundreds for optimization. Budget accordingly and surface progress.
9. **Monte Carlo needs a CSV either way** (META-44) — `Input File` to load, or `Output File` to write. Neither → `KeyError` after the simulation completes.
10. **`@lru_cache` on `read_textfile`** (META-45) means regenerating a CSV within one session returns stale data.
11. **Three incompatible relative-path rules** (§6). Resolve nested input references against the referring file.
12. **Deactivation idiom**: append ` - Deactivate` to any analysis table header to skip it — the cleanest per-module on/off switch for a UI, and already used throughout `data/`.
13. **Arbitrary method dispatch** from markdown (`getattr(module, table['Method Name'])`, `run_pyH2A.py:93`) — do not expose to untrusted input.
14. **`# Functional Unit` is mandatory** (`Discounted_Cash_Flow.py:192`, unguarded) and `# Input files to merge` is how defaults arrive. Every generated input file needs both; the in-package `Example/` files have neither (META-41).

---

# 8. Recommended repair order for maintainers

1. **One helper, eight call sites.** Add a `levelized_cost(dcf)` accessor that reads `dcf.inp['Dependent Variables']['Levelized cost']['Value']` and returns a float via `dcf.functional_unit`. Apply at `Sensitivity:93,172`, `Waterfall:52,102`, `Monte_Carlo:317`, and the two `Discounted_Cash_Flow.py` wrapper defaults (`:13,83`). That resurrects 6 of 7 modules.
2. **Cost_Contributions** needs the analogous `contributions` accessor plus unit-unwrapping of `Data`/`Total` (META-1/2/3).
3. **Delete or fix `pre_workflow`/`post_workflow` in the template generator** (META-21) and drop the `Type` lookup (META-22) — that is `pyH2A generate` back, and it is step 2 of the documented tutorial.
4. **Resolve `Life_Cycle_Assessment_Plugin`** (META-24): ship it or remove the row from `Defaults_LCA.md` / `Defaults_TEA_LCA.md`. Two of three default configs are currently unusable.
5. **The cheap independent bugs**: `is` → `==` (META-9), `sucess` hoist (META-11), waterfall label field (META-7), sensitivity paren (META-5), `Axes3D` (META-12), DDT docstring key (META-17).
6. **Regenerate `default_settings.rst` from `Config/Defaults_TEA.md`**, delete `Fixed_Operating_Cost_Plugin.rst`, add the missing toctree pages, and either refresh or remove `src/pyH2A/Example/`.
7. **Add one end-to-end test per analysis module.** The entire layer regressed silently through a merged refactor because `src/tests/end_to_end/` covers plugins only. A single smoke test asserting each module constructs and produces a figure would have caught all of §1.