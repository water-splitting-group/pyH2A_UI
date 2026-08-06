# Work log — pyH2A UI (Paper Plant)

Running log for this project: decisions, paths taken and not taken, and how to resume.
Newest entries at the bottom of §4. Maintained since 2026-08-05.

---

## 1. What this project is

A browser UI (Streamlit now, stlite/WASM for deploy) for
[pyH2A](https://github.com/water-splitting-group/pyH2A) — levelized-cost analysis of
hydrogen (and, post-refactor, any product) from a markdown input file. Client: Jacob
Schneidewind (water-splitting group). Broker: Hrishi (southbridge.ai).

The design language is **Paper Plant** — "a working plant, rendered on paper": cream
canvas, ruled tables, Prussian data ink, flame-test accent colors, exactly one dark
surface (the levelized-cost readout). Full spec in `visual-pack/`.

## 2. Folder catalogue

| Path | What it is |
|---|---|
| `0-get-situated.md` | the original brief for this session arc |
| `pyh2a-audit.md` | **read this before touching the engine** — full audit of master @ a15e7bb: broken examples, dead Analysis layer, silent-wrong-number bugs, the UI's runtime contract (§6) |
| `old/` | the ENTIRE previous attempt (v1 + v2 apps, Jacob's feedback transcript `old/1-feedback.md`, handoff docs `old/handoff/`) — built against a pre-merge engine branch; the engine workarounds are obsolete, the UX lessons are not |
| `pyH2A/` | clone of upstream master (a15e7bb). Env: `UV_PYTHON=3.12 uv sync` (`.python-version` says 3.14 which isn't installed) |
| `corpus/` | all 136 PRs + 43 issues mirrored as markdown (grep-able); fetched 2026-08-05 |
| `notes/` | research briefs: `00-situating-synthesis.md` (verified facts + receipts), `01-refactor-arc-brief.md` (the refactor story + team vocabulary glossary), `02-direction-brief.md` (roadmap/team/UI implications), `03-engine-file-index.md`, plus five `audit-*.md` detail reports backing `pyh2a-audit.md` |
| `visual-pack/` | the design deliverable: `cover.md` (start here), `tokens.md` (palette/type/families), `screens.md` (ASCII mockups of every screen), `assets/` (rendered palette/family/board images), `moodboard/` (71 annotated references), `_workbench/` (raw harvest + manifest with source links) |
| `spike-wasm/` | Pyodide feasibility spike (PASSED: exact LCOH in browser, 16 ms warm runs, no patches; report at the local URI `wasm-spike.md` and summarized below) |
| `app/` | **the product being built** — see §3 |
| `log.md` | this file |

## 3. The app (`app/`)

``
app/
  pyproject.toml            uv project; pyH2A as editable path dep (../pyH2A)
  CONVENTIONS.md            house rules (Jacob's taste + audit contract), ruff-enforced
  examples/                 the 5 inputs that actually run on master (copied from
                            pyH2A/src/tests/end_to_end/ — everything in data/ is broken)
  src/pyh2a_app/
    core/                   NO streamlit imports except session.py
      engine.py             the only doorway to pyH2A: run_dcf (deepcopy + stdout capture
                            + cache_clear), workflow_order, plugin_io (run=False
                            introspection), state_up_to (subset runs), functional_unit_token
      project_io.py         raw-preserving parser (mirrors engine's line classifier, keeps
                            cell text verbatim) + serializer (engine grammar) + engine_dict
                            (parse+merge without temp files) + grammar guards that reject
                            what the engine mis-parses silently
      schema.py             input_dict <-> UI questions: concrete vs group tables, wildcard
                            rows, missing-required, reference strings
      quantity_view.py      Quantity display recipe (audit §6) — never ==/order/float()
      config.py             ALL display metadata: pigments, plugin families, display names,
                            examples registry. Engine names never shown raw.
      session.py            st.session_state model: raw_markdown = truth; edit_cell
                            re-serializes; merged_inp/run_result caches
    ui/
      theme.py              the one CSS injection (Paper Plant tokens) + tiny helpers
      tables.py             THE table renderer (editable + locked modes)
      pages.py              render_load/inputs/run/source orchestrators; ALL error
                            boundaries live here
    streamlit_app/          1-3 line entrypoints (Home.py + pages/)
  tests/                    43 tests: 5 reference pathways at 1e-13, re-run safety,
                            introspection of all 24 plugins, subset runs, roundtrip
                            engine-equivalence, grammar guards
``

**Spin up:**

``bash
cd app
UV_PYTHON=3.12 uv sync
UV_PYTHON=3.12 uv run --with-editable . pytest -q          # 43 passed expected
UV_PYTHON=3.12 uv run --with-editable . streamlit run src/pyh2a_app/streamlit_app/Home.py
``

## 4. Decisions, paths taken and NOT taken

- **Depend on unpatched master** (editable path dep), not a vendored/patched engine.
  The old v2 app vendored + patched `feat/plugin_refactor`; all of that is obsolete —
  master runs the reference pathways to 1e-13. Verified by our own test suite.
- **Raw-preserving twin parser** instead of parse→serialize through the engine's dict:
  the engine `num()`-converts cells at parse (`50%` → 0.5, `5,500` → 5500), so
  re-serializing its dict reflows every formatted cell — the exact complaint from the
  v1 review ("one edit reflows the whole file"). Our parser mirrors the engine's line
  classifier state-for-state but keeps cell text verbatim; equivalence is pinned by
  tests on all 5 examples (engine parses our output to the identical dict).
- **Grammar guards at the UI boundary**: leading-pipe (GFM) tables, duplicate table
  names, content before first header → loud `InputGrammarError` instead of the
  engine's silent mis-parse (audit CORE-1..5). Trailing pipes are ALLOWED — shipped
  files have them and the engine drops the empty cell harmlessly. Ragged rows: the
  engine's zip drops trailing missing cells (key absent, ≠ `'n/a'`) — serializer
  mirrors that by trimming trailing absent columns (found via roundtrip test failure).
- **Defaults overrides are minimal per-cell rows**: the engine merge gives the user
  file per-cell priority, so editing a defaults-supplied value writes a row carrying
  only the edited column (`project_io.ensure_cell`). No defaults inlining — the file
  stays small and honest.
- **Only `calculate_PV_power_ratio` cache is cleared per run** (the identity-hash
  leak); the string-keyed file caches stay (they genuinely hit). Upload staleness is
  handled by unique filenames instead (not yet needed — uploads don't stage data
  files yet).
- **Examples = the 5 end-to-end test inputs**, renamed nicely; `Thermal_Base_Merge`
  excluded (CWD-relative merge reference breaks when copied). Everything under
  upstream `data/` is pre-#176 and does not run (audit finding #1).
- **Sensitivity/Waterfall (P2) will re-run the engine directly** — the upstream
  Analysis layer is dead at three stacked layers (audit finding #2). Not attempted:
  calling/fixing upstream Analysis modules from the UI.
- **stlite verified before building on it**: bare-Pyodide spike ran PV_E to the exact
  reference LCOH (zero rel error), warm runs 16 ms, numpy+scipy only (pandas/
  matplotlib NOT needed by the engine path), total transfer ~23 MB (scipy stub could
  cut to ~9 MB). Gotcha for bundling: package data (Config/*.md, Lookup_Tables/**)
  must ship inside the package tree.

### Session log

**2026-08-05 (a)** — Situating: read `old/` (feedback + handoffs), cloned master,
mirrored the GitHub corpus, three scout briefs → `notes/`. Verified master runs
(LCOH 4.1943 USD/kg) and that the Analysis layer is broken (reproduced
`AttributeError` + `- Deactivate` suffixes). Proposed the UI plan (chat).

**2026-08-05 (b)** — Moodboard session: harvested ~1,700 candidates from Pinterest/
Dribbble (logged-in shared Chrome), curated 71 keepers via contact sheets, built
`visual-pack/` (Paper Plant: cover, tokens, ASCII screens, rendered assets).

**2026-08-05 (c)** — Build start after `pyh2a-audit.md` landed. Foundation done:
scaffold, engine layer, raw-preserving IO, schema/config/session, 43 tests green.
WASM spike PASSED (parallel subagent). P0 screens in progress: theme.py, tables.py,
pages.py written; entrypoints + browser smoke test next. User asked for (1)
intermittent cold design reviews by `designer` subagents ("opus 5 is really good at
interfaces") as the UI takes shape, and (2) this log.

### Open items / next steps

1. Finish P0: entrypoints + `.streamlit/config.toml`, launch, browser smoke test.
2. Cold design review round via `designer` subagent(s); fold findings back.
3. P1: Flowsheet page (issue #86 — edges from input_dict/output_dict + resolved
   paths), Report/export page (.pyh2a zip archive), reference popover polish.
4. P2: Sensitivity/waterfall as engine re-runs; upstream goodwill PRs (analysis-layer
   accessor fix is mechanical, audit META §8).
5. stlite bundle build (reuse `old/v2-app/deploy/build.py` approach; heed spike
   gotchas: package data in tree, numpy+scipy only).
6. UI-side validation for the audit's silent-wrong-number classes (S1 dangling paths,
   S2 path-unit mismatch, S3 decimal commas, S4 basis-year clamp) — the engine won't
   warn; we must.

**2026-08-05 (d)** — P0 loop DONE and browser-verified end-to-end: load PV_E example →
edit Electrolyzer Nominal power 5,500→6,000 kW → Apply → Run → LCOH moved 4.1943 →
4.2624 USD/kg with the ledger sum-check ✓. Fixed along the way (found by smoke test):
(1) missing-required must ignore fields covered by upstream plugin `output_dict`s —
a complete example showed false ⚠ everywhere; coverage now accumulates along the
workflow (`schema.produced_before`/`is_covered`); (2) spec tables fully covered
upstream (Time, Power Generation) render in the locked "available" section, not the
editable form; (3) `render_locked_table` derives real columns (Workflow showed a
bogus Value column before). Server runs as hub process `paperplant` on port 8721
(`hub op:restart name:paperplant` after core/ui edits — Streamlit's watcher misses
package files). Streamlit sessions are per-websocket: hard reloads lose the project
(known P3). Screenshots: /tmp/pp-run.png, /tmp/pp-inputs.png. Cold design review #1
spawned (designer agent → `design-review-1.md`). Next: Flowsheet page (P1).

**2026-08-05 (e)** — P1 + design review round 1. Flowsheet page shipped (issue #86):
edges derived in `core/dataflow.py` from output_dict/input_dict matching + actual
`{...}` references in the file — the PV◀Electrolyzer forward reference shows as a
dashed edge; tested (`tests/test_dataflow.py`). Key rendering lesson: point-to-point
is unreadable because Time/Inflation feed everything — `split_buses` (per
producer-table, ≥3 consumers AND ≥34% of downstream) lists them as utility-bus
chips instead, exactly like steam/power buses on a real process flowsheet. Report
page shipped: input .md / .pyh2a zip (input+results+manifest, `core/report.py`,
round-trip tested) / report.md printout; Home now reopens .pyh2a archives.

Cold design review #1 (designer agent, 35 min, `design-review-1.md`) —
measured, harsh, correct. Headliners all fixed: editable fields had NO affordance
(white border on white — "the app appears not to work"); a global -16px margin
collided kickers app-wide (replaced with a real spacing scale); primary buttons
failed contrast (new action accent #4F7132, 6.4:1 — green now means exactly one
thing: act here); Streamlit Deploy/menu chrome hidden; fonts actually loaded
(Source Serif 4 + IBM Plex Mono via Google Fonts); rail rebuilt as a status list
(rings hidden, family-color left bars, hierarchy indent via generated nth-child
CSS since Streamlit radios can't carry per-option styles); Path column only renders
where a row actually uses one; float noise killed (%.6g); literal 'None' no longer
leaks; contribution palette de-duplicated (11 stable hues in config, families
reserved); readout aside shows Δ vs the pathway's reference cost; docstring dumps
guarded; Source is a real mono editor with dirty marker; flowsheet renders natural-
size. Reviewer's "session lost 4×" was my server restarts during their walkthrough.
Still open from the review (minor): radio rings not fully hidden (selector depth),
graphviz zoom/pan, sticky-apply is CSS-only, `.pyh2a` results not restored on
reopen (input only). 50 tests green, ruff clean.

**2026-08-05 (f)** — The flowsheet-centric pass (see `roadmap.md`). git initialized;
commits at every milestone. Highlights:

- **UI test suite first** (`tests/test_ui_pathways.py`, AppTest, 13→16 pathway tests):
  every page renders per example, edit→apply→run moves the cost, source grammar guard,
  plant run + failure-lights-node. This made the surgery below safe. 71 tests total.
- **THE PLANT** — custom Streamlit component, hand-written protocol (no npm):
  `core/plant_layout.py` computes a deterministic arc-diagram layout (linear spine,
  nested stream lanes with a no-overlap invariant TEST, utility bus rails on the left
  like a real P&ID); `ui/plant_component/frontend/index.html` renders SVG with
  pan/zoom (width-first fit), hover cards carrying LIVE stream values from the last
  run, click→selection back to Python; `ui/plant.py` = landing page after load, side
  panel with quick-edit + Apply & run, node outputs w/ values, stream inspector,
  rail-jump to worksheet. `engine.run_dcf_stepwise` times each plugin and returns
  failure-as-data → failing node turns red, run pulse staggers by real durations.
  Browser-verified full loop: click Electrolyzer → 5,500→6000 → Apply & run →
  readout 4.2624 ▲ +0.0681 vs previous with history sparkline.
- **Density primitives** (`ui/viz.py`): value packages (mono number + unit tag),
  min/max-decimated sparklines for arrays (8760-hr safe), share bars (finance-table
  pattern) in the ledger + timing table; contribution origin chips close story C.
- **CTA unification**: `Apply & run ▸` is THE verb everywhere; `session.run()` removed.
- Inspiration harvest #2 → `visual-pack/moodboard/07-interactive/` (30 keepers,
  NOTES-07.md): finance-table trend bars, Tufte sparklines, status-chip recipe,
  canvas-with-inspector references — all consumed by the above.
- Review round 2 (ColdEye2, designer, cold, flowsheet deep-dive) in flight →
  `design-review-2.md`.

Component gotchas for future sessions: the iframe speaks the component protocol by
hand (`streamlit:componentReady/render/setComponentValue` postMessage); interact in
tests/browser via `page.frames().find(f => f.url().includes('paper_plant_flowsheet'))`.
Streamlit radios can't carry per-option styles — the rail's family colors/indent are
generated nth-child CSS (`theme.rail_css`). Restart `paperplant` hub process after
editing package files; Streamlit's watcher misses them.

**2026-08-05 (g)** — Review round 2 + fix round, all committed (9 commits total this
pass, see `git log`). ColdEye2's verdict was harsh and correct: the flowsheet "hid
the money" (fit left the 7 cost plugins off-canvas), primary buttons regressed to
2.76:1 (Streamlit's inner `<p>` resets button color — fix is
`button[...primary] [stMarkdownContainer] p { color: inherit }`), units truncated to
one character in the panel. All top-10 items executed except two consciously deferred:
ledger→explorer deep links (needs anchor scrolling machinery) and the levelisation
arithmetic line (needs a derivation from the DCF plugin — upstream data exists in
`npv_dict`, good candidate for next pass). Deltas now colored (rust up / olive down)
with "vs previous · what changed"; a failed run never destroys the last good number;
client-side numeric validation blames the right field (the engine blames the wrong
PLUGIN — audit S-class); node cards show principal OUTPUTS (non-zero-preferring)
instead of ms telemetry; overflow is an explicit fade+pill, never silent; families
speak domain words (framework/solar/conversion/storage & power/water/cost) and DCF
moved to the cost family. Verified end-to-end in browser after every batch.
Full review: `design-review-2.md` (379 lines, 68 screenshots — worth reading
whole before the next visual pass).

**2026-08-05 (h)** — Retheme v2 after Hrishi's minimalism ask ("off-white,
fewer cards, spacing, typography"; dembrandt token extractions from
anthropic.com / ia.net / linear.app as reference). `theme.py` rewritten:
#FAF9F5 paper, Source Serif 4 headings (w400/1.1 — the iA/Anthropic move),
body 15/1.55, 1320px container, 0.45rem block gap. Component: orthogonal
elbow stream routing, hover context-dimming (dimmed/lit classes), zoom %
readout, width-aware title truncation. Plant header restructured (link no
longer trapped under readout; overflow pill clears legend). Browser-verified
all six pages; committed `10759ee`.


**2026-08-05 (i)** — `start_here.md` written for future agents: run/verify commands,
architecture map, the seven invariants, history table, open items. Acceptance-tested by
a context-free scout paraphrasing it back; its findings (clone-cwd trap, numpy+scipy not
numpy-only, missing hub start spec, overstated test-coverage claims, six dangling
pointers) all fixed. Design reviews copied into the repo as
`design-review-1.md`/`-2.md` so the doc's pointers outlive `/tmp`.

**2026-08-05 (j)** — Visual pass 3, after Hrishi's verdict: *"reasonably fit for purpose
but feels like a research project. It does not inspire, nor is it good design — which
should always tell you where to look implicitly and help you work."* Plus explicit
licence: *"feel free to completely rip out and redo anything you think right."*

**The diagnosis, in one sentence:** the app visualized the *software* — plugin boxes
labelled `in 2 · out 7`, edges labelled with Python dict paths — while throwing away a
complete physical balance, a 21-year cash flow, 175,200 hourly dispatch values, a second
level of cost decomposition, and 9 ms runs that make sensitivity interactive. Jacob had
already said it in the v1 review (*"the nodes are completely trivial. The interesting
thing is the edges"*) and ColdEye2 had already said it (*"the flowsheet must win on
wiring and money or it is decoration"*). Nobody had built it.

**Method.** Four scouts distilled the accumulated context (design reviews, Jacob's
feedback transcript, the visual pack's unexecuted ambition, and — most usefully — a
domain scout that ran the engine and inventoried what a completed run actually produces).
Then six `designer` subagents workshopped one figure each as a standalone HTML page
against **real extracted engine output**, screenshotting and iterating 6–12 times. I built
the process diagram myself and the Python derivation layers throughout. Brief at
`workshop/BRIEF.md`; per-figure notes at `workshop/NOTES-*.md`.

**The organizing idea.** Hydrogen is drawn at its lower heating value (33.33 kWh/kg), so
sunlight, electricity and product close on **one** energy scale and the plant gets a
single honest headline: **13.5% of the sunlight landing on 37,500 m² leaves as hydrogen.**
For the LCOE pathway the same derivation yields 22.0%, which exactly equals the panel
efficiency — a free check that it is right.

New core layers, every one engine-derived and self-checking:

- `process_flow.py` — units and streams; `cost_layers()` splits cost by the part of the
  plant that incurs it and `check_reconciles()` proves the split is lossless.
- `cashflow.py` — reconstructs the H2A table the DCF plugin computes and *discards*
  (the series are locals; every input to them survives on the instance). Finds payback,
  annotates spikes not trends.
- `sweep.py` — sensitivity by re-running the engine. Reports monotonicity and turning
  points so a caller can refuse to draw a bar where a bar would lie.
- `plausibility.py` — the warnings the engine will not give.
- `payload.py` — one figure payload, fixture-shaped.

**Decisions, and the reasoning:**

- **Keep `Grid Electricity > Cost = 10000.12 USD/kWh` exactly as upstream ships it**, and
  surface it as a plain-language warning instead. Fixing the file would break the
  Δ-vs-published-reference match, which both reviewers called the most trust-building
  thing in the product. Surfacing it turns a trap into the best demonstration of why the
  validation layer exists: *"Grid electricity is priced at 10,000.12 USD/kWh. That is
  about 10,000× outside the plausible range… It reaches the answer through variable
  operating costs, currently 0.8105 of the 4.1943 total (19%)."* This is literally the
  example sentence `visual-pack/tokens.md` §5 specified and nobody had built.
- **Figures are served, not reimplemented.** `figures.py` takes the workshop HTML
  unmodified and shims `fetch`. One copy stays runnable both in the app and standalone
  against `workshop/fixtures/` for iteration.
- **A declared component, not `components.v1.html`.** Only a declared component may report
  a measured height; with a fixed one every figure either clipped or left dead space. The
  host holds a same-origin `srcdoc` frame — same-origin is the point, it is what lets the
  host measure the sheet.
- **Pages run on arrival.** Nine milliseconds never justified a button press, and an empty
  plant read as a broken app.
- **Session persistence** via a `localStorage` component. A hard reload used to lose
  everything; reviewers read that as the app crashing.
- **NOT done: porting `worksheet.html` over the Inputs page.** It is designed and it is
  good — three-column, Jacob's yellow propagating field → table → rail, click-to-bind
  references — but it needs bidirectional editing, and swapping out the one surface where
  edits actually work, late, was not a trade worth making. It is the next pass. The Inputs
  page did get its own fix: the workflow table showed `Time_Plugin` raw, which is what
  issue #96 was filed about.

**Bugs the workshop agents found in my data layer**, all silently wrong rather than
visibly broken, which is the class this app exists to prevent:

1. `direct_electrolysis` was off by 1,621 MWh — after `Power_Management` runs, names in
   `inp` mean *post-allocation leftovers*, not gross flows. Gross terms survive only on
   the plugin instances (`engine.physical_balance`).
2. Capital attribution hard-coded PV/Battery/RO/Electrolyzer, so the three research
   pathways — which name their equipment `PEC Cells`, `Photocatalyst`, `Reactor Baggies` —
   had their capital silently dropped and the layers summed short of the headline.
3. **WsWorksheet's catch, the best of the session:** every table cell carried the SI base
   magnitude while `Unit` carried the authored string. `Nominal power` read 5,500,000
   labelled "kW"; `Plant life` read 630,720,000 labelled "year". Pinned three independent
   ways, including reproducing the documented Grid Electricity typo exactly.
4. LCOE contributions came out in USD/**J** — off by exactly 3,600,000, shares right and
   absolutes wrong (WsGallery).
5. Three of eight bench sweep targets named rows that do not exist (WsBench).

**Also learned:** `tokens.css` sets `svg text { font-family: var(--mono) }`, which beats a
`font-family` presentation attribute — SVG prose needs an inline style or it silently
renders mono and ~25% over its measured width. And a figure written as a standalone page
reasonably calls `history.replaceState`; inside a `srcdoc` frame that throws a
SecurityError and takes the rest of the script with it.

122 tests (`test_figures.py` is new: it asserts the numbers at the *payload* layer, which
iframes hide from AppTest, and which fails on a wrong number rather than a changed label).
ruff clean. Commits `788166e`, `f6e69e3`, and the two after.

**2026-08-05 (k)** — Verification and two review rounds on the visual pass.

Two agents drove the app rather than reading it: one cold designer (`ColdEye3`,
`design-review-3.md`, 451 lines, 84 screenshots) and one correctness sweep
(`PathwaySweep` → `ConfirmSweep`, `verification-pass3.md`, all 5 pathways ×
all 7 pages, twice).

The designer's verdict: *"This build stopped decorating data and started arguing
with it… Thinking is an A; execution is a B−."* Round 2's central charge —
*"it hides the money"* — recorded as answered.

The sweep's verdict was blunter and more useful: **13 defects, engine and payload
layer fully correct, every defect in the figure layer, and four of them one root
cause.** That root cause is worth writing down, because it will recur:

> A figure built as a standalone page re-derives in JavaScript something the
> payload already computes — and the re-derivation is hardcoded to the pathway it
> was written against.

The cost lens re-derived its spine from `Direct Capital Costs - PV / Battery /
Reverse Osmosis / Electrolyzer`, so the research pathways — which call their
equipment `PEC Cells` and `Photocatalyst` — showed a phantom PV array at +0.0000
and lost their real capital, *under a footer still claiming the total reconciled*.
The bench dereferenced a grid-tariff row only PV+E has and died on four of five.
The dispatch calendar got the main payload where it wanted 8,760 numbers and
painted a black rectangle. The process figure formatted a null and stopped.

The fix in each case is the same and is now the rule: **the figure reads the
payload; Python owns the derivation and proves it.** `cost_layers` +
`check_reconciles` existed already — the lens simply was not using them.

Also fixed, and worth remembering:
- Two tabs shared one `localStorage` key, so opening a second pathway silently
  destroyed the first tab's unsaved edits. `sessionStorage` has exactly the right
  semantics: survives a reload, scoped to the tab.
- The delta compared across pathways *and across units* — `0.0286 USD/kWh, down
  185.4147 vs 185.4433`. Loading a project now clears every derived cache.
- `_validate_cell` accepted `5,506000`, which is what you get typing over a
  selected `5,500`. The engine strips the comma and reads 5,506,000: a silent
  thousandfold error in the field just edited.
- The fetch shim fell back to the main payload for *any* unmatched key. A bare
  key may fall back; a suffixed variant may not.
- `workshop/*.html` are now symlinks into `app/src/pyh2a_app/ui/figures/`. The
  duplicate gallery template had already drifted 244 lines before anyone noticed.

**Still open, deliberately:** the worksheet port (designed, iterated, not wired —
it needs bidirectional editing and swapping the one surface where edits apply was
not a late-pass trade); the Source page is still a plain textarea and is where the
Answer sends you to inspect the grid-tariff defect; the results explorer is 43
undifferentiated accordions; and four groupings of the same eleven cost components
coexist across four pages without a printed bridge. All four are in
`start_here.md` open items, and `design-review-3.md` §9 has the argument for
picking one canonical decomposition.

143 tests, ruff clean. Seven of the new tests exist only because a defect was
*silently wrong rather than visibly broken* — they fail on a wrong number, not a
changed label.

---

## 5. The studio — a second app, built from scratch

**2026-08-05 (l)** — Jacob and Hrishi's review of the visual pass reframed the whole
project. Paraphrasing the ask: *the most important thing is to be able to step through
the functions and tell what the input is, what is available so far, and what all the
user inputs are — because those are accessible to all plugins at all times.* Plus: let
the system suggest plugins, let me arrange and add them, and show me the errors as they
come. Of the shipped screens, the one Jacob liked was the input worksheet —
`ui/figures/worksheet.html`, the three-column mock that was designed, iterated and never
wired. *"Build this first."*

That is not a change to Paper Plant. It is a different application, so `studio/` is a
new one, and `app/` is untouched.

### What it is

Three columns. The rail is the workflow as a graph — the engine's execution order down
the page, edges in a gutter showing which step feeds which, and a `+` between every pair
that opens a plugin chooser. The middle is the open step: its declared inputs as
editable fields, each carrying its range, its physical dimension, its description and
which file it came from, then a dark panel of what the step made. The right is
everything in scope at that point in the run, grouped by which step produced it.

Every edit re-runs the engine — around 40 ms — and the masthead reports the move with a
delta.

### The three things that were hard

**The engine mutates one dict in place and later steps redefine earlier names.** After
`Power_Management` runs, `Power Generation > Available energy` means "unspent after
allocation", not "generated"; four steps write it during a PV+E run. So "what could step
7 see" is only answerable while the run happens. `core/trace.py` runs the workflow one
plugin at a time and snapshots around every step. Five pathways trace in 25–90 ms
against 6–9 ms for a plain run. The predecessor re-ran the prefix once per step, which
is quadratic and still cannot say what a step *changed*.

**A cell means two magnitudes and only one is safe to show.** `supplied_value` in
`supplied_unit` is what the file says; `base_value` in `base_unit` is SI. Print the base
beside the authored unit and a 5,500 kW electrolyzer reads `5,500,000 kW`. That shipped
in the previous build. One module turns an engine value into JSON, and it reports the
authored pair.

The inverse holds for validation, and this took two rounds to get right: **bounds are
declared in base units, so validate the base pair and display the authored pair — and
then state the bounds back in the field's own terms.** Shipping only the first half made
six fields display a value apparently outside their own stated range. Shipping the
second half with a single scale factor turned `[250, 500] K` into `-68,038 … -136,075`
beside a field reading `45 degC`, because temperature is affine. Each bound is converted
on its own now.

**A dangling reference is silently worth 1.0.** `process_path` prints a warning to stdout
and substitutes 1.0, so a mistyped table name becomes a plausible cost in a run that
reports success. Every reference is checked against the cells that genuinely exist at
that point, a forward reference is distinguished from a typo, and a typo comes back with
the intended target so the UI can offer the fix.

### What the studio catches that pyH2A does not

Four checks run before the engine does: a reference that will not resolve, a value
outside its declared bounds, a unit whose dimension disagrees with the declaration, and
text in a numeric field. None of these is an error to pyH2A — it substitutes, converts,
and returns a number.

The last one earns its place on one observed failure. Type `banana` into
`Electrolyzer > Nominal power`, a cell owned by step 203, and the engine fails at step
**202** in `Photovoltaic_Plugin`, which never reads that cell: paths resolve lazily, so
whichever plugin first touches a reference to a broken value inherits the blame. The
studio shows both verdicts — the engine's, because it is what happened, and the field's,
because it is the only one that points at the row to fix.

Getting to **zero false positives on the five shipped reference files** taught most of
the rules, each found by the checker crying wolf on a file upstream's own tests assert
is correct: bounds in base units; `<...>` meaning a table *group* matched by substring
containment in one place and *every row* in another; a step being allowed to reference
what it writes itself; dimension strings differing only in spacing.

### Paths not taken

- **Streamlit.** Every good surface in the previous build ended up as hand-written
  HTML in an iframe, and every hard bug was the host's: frame heights, focus theft,
  session state, `AppTest` unable to see inside a component, CSS injection failing
  silently. The studio is a stdlib HTTP server and vanilla ES modules, no build step.
- **A web framework.** `api.dispatch(op, payload) -> dict` is the whole backend, and
  `server.py` does nothing but translate. pyH2A runs in Pyodide (16 ms warm, measured in
  `spike-wasm/`), so a serverless build stays reachable exactly as long as no request
  semantics leak into the core.
- **A revenue line on the annual-cost figure.** The engine discards it; it is recoverable
  only by multiplying the levelized price by annual output, which is true by construction
  and is still this app computing a number the engine did not state.
- **Explaining the year-20 spike.** PV+E bills 19.9 M in its final year against ~3 k the
  year before. An earlier caption asserted the cause was the grid tariff; the arithmetic
  does not support it (the twenty-year grid draw is 13.9 M). The figure names the line,
  which is checkable from the chart, and stops.

### Reviews

Four cold agents, two rounds. Round one: 29 design defects and 13 correctness defects.
Round two, on the fixes: 12 of 13 correctness defects closed with zero regressions, 13 of
29 design defects closed by measurement — and **six new defects, four of them introduced
by the fixes**, including one earlier fix that measured as having had no effect at all.

The pattern worth remembering: nothing was ever wrong with the arithmetic. Every defect
in both rounds was the app misdescribing arithmetic that was correct — a range that
contradicted its field, a unit chip on the wrong operand, a caption promising a lens
drawn in 8 px of the palest ink available, a contrast rule out-specified by 23 later
declarations in its own stylesheet. The three worst were all *reasoned to and never
looked at*.

Reports: `studio-review-1.md`, `studio-verify-1.md`,
`studio-review-2.md`, `studio-verify-2.md`.

**State:** 194 tests, ruff clean. All five pathways reproduce their published cost, zero
field-level problems on shipped files, decomposition residual zero at machine precision,
no dead figure, every payload JSON-safe. `studio/README.md` is the map.


**2026-08-05 (m)** — The building pass. Two review rounds asked the app a question the
first three never had: not "does it show this pathway correctly" but "can I build one".
The answer was no, and the reason was one line — a created row carried only the column
that was edited, so `Plant modules | 2` went under a `Name | Value | Unit | Comment`
header. pyH2A zips a row's cells against the header, so the two missing cells arrived as
`None` and the first plugin to touch one died on `NoneType has no attribute strip`. Real
pyH2A rejects that file exactly as hard, which is how you can tell the file was wrong and
not the reader. Rows are padded now, a new table gets the Unit column its plugin
declares, and the unit written is the declared one — `m2` for an area, `USD` for a cost.

Filling that in properly took three goes, each one caught by a cold agent:

1. Padding a unit cell blank raises `Unknown unit encountered during parsing`; padding
   `-` makes the engine refuse every dimensional field. It has to be the real unit.
2. Fifteen of the twenty-six declared dimensions are compound (`currency / area`,
   `volume / (length * substance)`), and the flat lookup answered `''` for all of them.
   Base units are composed token by token now, with a test that round-trips all
   twenty-six through `Quantity` to prove the engine reads back what was declared.
3. **I was resolving declarations by scanning every installed plugin.** That answers a
   different question from the one being asked, and it was wrong twice: alphabetically,
   so `Solar Input > Mean solar input` got PEC's `{float, int}` on a Solar Thermal
   pathway; and literally, so `<...> Direct Capital Cost <...>` — a *group* declaration
   matching by substring — was never found and every created cost row got a dimensionless
   dash. Declarations resolve against the workflow's own steps, honouring wildcards the
   way `input_resolver` does.

The best thing in the pass came out of the fix rather than the review. Adding
`Multiple_Modules_Plugin` at 650 produced a step that ran clean, reported `ok` on every
field, and changed the levelized cost by not one digit — Labor Operating Cost had already
turned `Staff` into a cost at 600. At 401 the same eight modules take the file from 5.5044
to 4.6791 USD/kg. So a step now reports what it is worth, **measured** by removing it and
running again: *Saves 0.8252 USD/kg*, *Adds 0.8105*, *the pathway does not reach a cost
without this step*, or *this step changes nothing where it is* — with the step it has to
precede and a button that moves it. Inferring it from declared inputs would have been
cheaper and wrong, because `Discounted_Cash_Flow_Plugin` eats whole table groups by
membership and a declaration-based test calls live steps dead.

Everything else was the app lying about itself, and there was a lot of it: pyH2A's own
`Example/*.md` rejected in silence (`#welcome-error` existed from the first build and was
only ever hidden); twelve financial defaults that were editable boxes which took your
typing and threw it away; a rail tally that dropped the step that stopped the run; "N
values only you can supply" as the most prominent thing on the screen and the one thing
you could not click; `Electricity` labelled `Usage`, so changing the price changed the
consumption; a tour quoting forty milliseconds beside a masthead reading 21; a reload
that lost an afternoon in the static build because there is no server to hold it.

**Paths not taken.** I did not "fix" the reviewer's second-worst finding — cell editing
appearing to concatenate — because it was not a defect: CDP's synthetic triple-click and
`Meta+A` do not select text, and a bare `<input>` injected into the same page behaves
identically. Two agents confirmed it independently. Worth remembering: **before
believing an input-behaviour defect, run the same action against a control element.**
Twice more the same discipline paid: a MACRS tamper that changed nothing (wrong column —
every shipped pathway depreciates over twenty years) and a "fix verified" run whose
`.replace` had silently no-opped. A test that changes no number proves nothing.

**State:** 230 tests, ruff clean, both run modes verified in the browser end to end. All
five pathways reproduce their published cost in native *and* WASM; a blank plant can be
named, extended, corrected and reloaded without loss; the build refuses five separate
sabotages, each naming what it found. `studio/README.md` is the map.
