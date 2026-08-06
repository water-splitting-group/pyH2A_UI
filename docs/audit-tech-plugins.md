# TECH plugins review (from TechPluginsReviewer yield)

Static source review of the 13 technology plugins in pyH2A/src/pyH2A/Plugins/ at master a15e7bb. 31 findings (TECH-1..TECH-31): 5 confirmed bugs (Photocatalytic homogeneous-catalyst branch is dead code due to a 'Molar Weight' vs 'Molar weight' key mismatch — which is also the real reason #116's bad unit never fired; Power_Management crashes when 'Power Consumption' exists without 'Grid Electricity'; Power_Management's no-generation fallback returns a bare ndarray into code that calls .unit[]; Power_Management zeroes the daily energy bus even when it does nothing; the Electrolyzer→Replacement_Plugin contract charges one spurious full stack replacement in the final year whenever 0 replacements are needed — true for the shipped PV_E test), plus latent bugs (unwrapped hour angle breaks AM/PM sign for non-cardinal array azimuths, hardcoded PVGIS skip_header/skip_footer, cell temperature from fixed-tilt POA reused for tracking configs, float-only type specs that reject integer literals), and a full map of the de-facto public API (which '{Table > Row > Value, unit}' paths each plugin publishes/consumes, per the shipped end_to_end .md files) plus per-plugin UI facts. Report is the markdown document in the final assistant message; all findings carry file:line, severity and a corpus dedup check.

## Per-file findings

### `pyH2A/src/pyH2A/Plugins/Photocatalytic_Plugin.py`
TECH-1/2/10/16/18/19: dead homogeneous-catalyst branch (line 482 'Molar Weight' vs resolver key 'Molar weight'), three latent failures behind it (485 KeyError, 505 'liter/cm/mol' dimension-string mismatch vs input file's 'liter/(cm*mol)', 516 assert with 1e-6 abs tolerance and duplicated '{0}'), unvalidated implicit-per-hour Quantities (478-480), catalyst_properties computed then discarded (518), docstring row names that do not match input_dict

### `pyH2A/src/pyH2A/Plugins/Power_Management_Plugin.py`
TECH-3/4/5/26/28: KeyError on missing optional 'Grid Electricity' (198+229), ndarray fallback feeding .unit[] (212/218 -> 236/240), unconditional zeroing of 'Available/Stored energy (daily)' (154/162), unreachable unknown-type warning (269), dead yearly outputs nothing consumes

### `pyH2A/src/pyH2A/Plugins/Hourly_Irradiation_Plugin.py`
TECH-7/8/9/10/11/29/33/34: unwrapped hour angle + np.sign (306), hardcoded skip_header=17/skip_footer=9 (252-253), lru_cache keyed on Quantity (277, confirms #152), 'Wh/m2' labelling of a W/m2 array (369), cell temperature from fixed-tilt POA reused for SAT/DAT (343), tilt-defaults-to-latitude (199-200, 299-300), dead import_Chang_data (227-230), unclosed file handles

### `pyH2A/src/pyH2A/Plugins/Electrolyzer_Plugin.py`
TECH-6/14/24: calculate_stack_replacement off-by-one at 0 replacements (300-301) feeding Replacement_Plugin via the user-supplied path, docstring claims 'Design output by year'/'Operating capacity factor' outputs it never writes (29-33), min-capacity threshold edges (246-247)

### `pyH2A/src/pyH2A/Plugins/Stored_Power_Electrolysis_Plugin.py`
TECH-12/14/27: float-only type specs that only survive because Electrolyzer_Plugin resolves the shared rows first, docstring 'Design output by year' drift (40), 'Type' output smuggled through an attribute named on_demand

### `pyH2A/src/pyH2A/Plugins/Battery_Plugin.py`
TECH-13/23: scalar Quantity(0,'J') written into a path other plugins type as dict (147), round-trip efficiency applied only on discharge, unused capacity_decrease return, one-cycle-per-day and no charge-power limit (176-193)

### `pyH2A/src/pyH2A/Plugins/Reverse_Osmosis_Plugin.py`
TECH-12/15: float-only specs (69/80/92) and docstring naming a row ('Average daily operating hours') that does not exist and a capacity 'per hour' that is actually m3/year (170-172)

### `pyH2A/src/pyH2A/Plugins/Solar_Thermal_Plugin.py`
TECH-12/22: float-only type specs (39/52/65/78) vs its own shipped input's integer '1,000', and no 'Solar collection area' output so it cannot be combined with Multiple_Modules_Plugin

### `pyH2A/src/pyH2A/Plugins/Solar_Concentrator_Plugin.py`
TECH-20/21: half-spacing land model inconsistent with PEC_Plugin's full spacing (179-180 vs PEC 306-307) and non-idempotent overwrite of 'Solar collection area'/'Land required'

### `pyH2A/src/pyH2A/Plugins/PEC_Plugin.py`
TECH-20/25: land-area convention, plus solar concentration that must be wired by hand in the input file through the Path column

### `pyH2A/src/pyH2A/Plugins/Photovoltaic_Plugin.py`
TECH-17/23: docstring omits 'PV yearly power generation' (124), two paths aliasing one attribute (113/133), land area == module area with an implicit 1000 W/m2 constant (225-229)

### `pyH2A/src/pyH2A/Plugins/Multiple_Modules_Plugin.py`
TECH-25: supervisors counted once across all modules then divided per module (129-135); shift bounds (1,3)

### `pyH2A/src/pyH2A/Plugins/Catalyst_Separation_Plugin.py`
TECH-30 context: only consumer of 'Water Volume > Volume'; yearly cost = V/lifetime * filtration cost (99-104)

### `pyH2A/src/tests/end_to_end/PV_E_Base_test.md`
Reference wiring for the de-facto public API: 'Design output by year' <- {Electrolyzer > H2 production (yearly)}, Planned Replacement frequency <- {Electrolyzer > Actual stack replacement time}, absent 'Module tilt' relying on the latitude default, Grid Electricity 10000.12 USD/kWh (#89)

### `pyH2A/data`
TECH-30: every .md under pyH2A/data (and pyH2A/src/pyH2A/Example) still uses the pre-Quantity syntax (unbraced paths, 'Module Tilt (degrees)', 'Hourly Irradiation > Latitude > Value') and cannot run on this engine; only src/tests/end_to_end/*.md are current

## Architecture note
Each technology plugin is a self-contained unit: _set_up declares input_dict/output_dict specs, _run calls input_resolver_function -> compute -> output_inserter_function. All cross-plugin communication happens through dcf.inp keyed by '{Table > Row > Column}', ordered solely by the Workflow table's Position column (technology plugins at 201-401 interleave with the fixed TEA chain Time 100 / Inflation 200 / Production 300 / Capital 400 / Replacement 500 / Labor 600 / OtherFixed 700 / VariableOpCost 800 / DCF 900 from Config/Defaults_TEA.md). Two coupling styles coexist: (a) plugin-to-plugin via table paths that the *input file* must wire by hand (e.g. Design output by year <- Electrolyzer H2 production), and (b) a mutable 'Power Generation' energy bus (hourly dict -> daily dict -> yearly array) that PV, Electrolyzer, Battery and Power_Management successively overwrite, which is where the type inconsistencies and ordering hazards concentrate.