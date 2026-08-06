# Situating synthesis — pyH2A UI, session of 2026-08-05

What this file is: my own verified findings from this session, written for a future
session that has none of today's context. The three companion briefs
(`01-refactor-arc-brief.md`, `02-direction-brief.md`, `03-engine-file-index.md`) are
subagent research; everything below I verified directly against the clone at
`./pyH2A` (master @ a15e7bb) or ran myself.

## What changed since the old attempt (./old)

The `old/` folder is a v1+v2 UI build from ~2 months ago that ran on the then-unmerged,
half-broken `feat/plugin_refactor` branch — the agent had to vendor and patch the engine
(bridges, unit fixes) to make it run. **That whole problem class is gone.** The refactor
landed on master in three merged steps:

- **#151** "Plugin I/O refactor" — every plugin declares `input_dict` (what it reads:
  types, bounds, dimensions, optionality, descriptions) and `output_dict` (what it
  writes), resolved by `input_resolver_function` / `output_inserter_function`.
- **#138** Time + Inflation plugins — one `Time_Plugin` owns all time arrays
  (the "time dict" at `Time > Years > Value`); pre-workflow deleted.
- **#176** "post-workflow" — the DCF math itself became a plugin
  (`Discounted_Cash_Flow_Plugin`, workflow position 900); `Discounted_Cash_Flow.py`
  is now a thin parse→merge-defaults→sort-by-Position→execute loop; the functional
  unit (denominator of the levelized cost) is a user input: `kg` → LCOH,
  `kWh` → LCOE (`src/tests/end_to_end/PV_E_Electricity_Production_Test.md`).

## Verified facts (I ran these)

- `uv sync` needs `UV_PYTHON=3.12` (`.python-version` says 3.14, no interpreter here).
- Master runs end-to-end:
  `pyH2A('src/tests/end_to_end/PV_E_Base_test.md', tmpdir)` →
  `Levelized cost = Quantity(4.194302976489664, 'USD/kg')` — matches the legacy master
  reference (4.194302976489675) to ~1e-14. A run takes ~0.3 s warm.
- The full cost breakdown is served from the input dict, no plugin attribute needed:
  `inp['Dependent Variables']['Levelized cost contributions']['Value']` =
  `{'Data': {11 named Quantity components}, 'Total': Quantity, 'Table Group': 'Total Cost of Product'}`.
- **The Analysis layer is broken on master.** `Cost_Contributions_Analysis`,
  `Sensitivity_Analysis`, `Waterfall_Analysis`, `Monte_Carlo_Analysis` still read
  `dcf.h2_cost` / `dcf.contributions`, which #176 removed. Reproduced:
  activating Cost_Contributions on PV_E raises
  `AttributeError: 'Discounted_Cash_Flow' object has no attribute 'contributions'`.
  The team knows: every shipped example has its Analysis tables renamed
  `...Analysis - Deactivate` (the suffix stops `meta_workflow` from matching them).
- **LCA is not runnable from master.** `Config/Defaults_LCA.md` and
  `Config/Defaults_TEA_LCA.md` reference `Life_Cycle_Assessment_Plugin`, which does
  not exist in `src/pyH2A/Plugins/`. The working LCA lives on `feat/lca-on-master`;
  Homa's LCA+Monte-Carlo PRs (#160/#162/#175) are closed-unmerged pending rework.
- Plugins are UI-introspectable for free: every plugin is
  `__init__(self, dcf, print_info, run=True)` calling `_set_up(dcf)` (declares the
  dicts, side-effect-free) then `_run(dcf)`. Instantiate with `run=False` and read
  `input_dict`/`output_dict` — no execution, no docstring scraping.
  `Utilities/docstring_generation.py` (added by #176) already walks these dicts.

## Corpus

All GitHub discussion is mirrored locally and grep-able:
`corpus/prs/NNN.md` (136 PRs) and `corpus/issues/NNN.md` (43 issues), full bodies +
comments, fetched 2026-08-05.

## Load-bearing design inputs for the UI (with receipts)

1. Audience is explicitly non-programmers — axfache in PR #96/#169: "Target users are
   not necessarily advanced Python developers… reverse engineering the code … can deter
   potential users."
2. Issue #86 is a literal feature request for the dataflow schematic: "a schematic with
   arrows showing the variables going from a plugin to another, or entering one without
   emerging from another … The IO resolver will definitely enable to make it basically
   automatic."
3. Naming is churning: #173 (rename `Financial Input Values`), #174 (rename
   `Discounted_Cash_Flow.py`), #101/#83 (table/variable names), and PR #178 will make
   workflow entries `Subdir/Plugin_Name`. UI must be schema-driven with a display-name
   layer, never hard-coded labels.
4. Jacob's UI feedback from the v1 review (old/1-feedback.md): input page must show
   ALL information available at each workflow stage (not just needed fields), needed
   fields highlighted; process graph strictly linear with variable-labelled edges;
   ONE general table renderer; pages as thin `render_*` orchestrators; markdown as
   the single source of truth; fail-fast (index, don't .get); numpydoc; no clever
   one-liners; imports at top.
5. Deploy strategy fixed by Jacob: Streamlit + stlite (WASM, no backend), like his
   pyKES-O2-H2-App. The old v2-app (`old/v2-app/deploy/build.py` + `index.html`)
   already implements the bundling and is reusable.
6. Warts to surface, not fix: PV_E grid electricity 10000.12 USD/kWh (#89);
   Replacement contributions don't sum (#170); `check_processing` warnings matter (#118).
