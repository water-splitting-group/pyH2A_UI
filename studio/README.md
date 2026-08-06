# Paper Plant Studio

A UI for [pyH2A](https://github.com/water-splitting-group/pyH2A), the levelized-cost
framework maintained by Jacob Schneidewind's water-splitting group. A pyH2A project is
one markdown file of tables; the engine parses it, runs a workflow of plugins in order,
and produces a discounted-cash-flow cost — the PV + Electrolysis reference pathway
lands at 4.1943 USD/kg.

**This is a worksheet, not a report.** You step through the pipeline and, at each step,
see what it needs, what it can already reach, what it produced, what it is worth, and
what is wrong. Every value is editable in place and every edit re-runs the engine: about
37 ms end to end on the seventeen-step PV + Electrolysis pathway, of which the engine run
itself is the 21 ms the masthead reports.

## Run it

```bash
cd studio
./run          # the app on http://localhost:8730
./run build    # the static build, served on http://localhost:8000
./run test     # the suite and the linter
```

The only prerequisite is [uv](https://docs.astral.sh/uv/); the script clones pyH2A beside
this folder if it is missing and refuses to start against a pre-refactor checkout, which
would otherwise present as empty forms rather than as a wrong branch.

### Two ways, and when each is right

**In a browser, with nothing installed** — `./run build`. Equivalent to:

```bash
UV_PYTHON=3.12 uv run --with scipy --with-editable . python deploy/build.py
python3 -m http.server --directory deploy/dist 8000
```

Open <http://localhost:8000>. pyH2A runs in the page under Pyodide — no Python on the
machine, no process to keep alive, no port to remember. Drop that folder on GitHub Pages
or any static host and the URL is the whole install. It will not work from a `file://`
URL: browsers refuse module scripts and `fetch` from the filesystem, so a web server is
needed even locally.

First visit downloads about 25 MB of runtime from jsdelivr and caches it; after that the
app starts in roughly eight seconds and an edit round-trips in about 350 ms.

**Natively, for development** — `./run`. Faster, and the mode to work in:

An edit round-trips in about 40 ms here. Restart the process after changing anything
under `src/`; the web assets are served from disk and only need a browser refresh.

Engine dependency: `pyproject.toml` points at `../pyH2A` (editable), a clone of upstream
master sitting beside `studio/`. Post-refactor master is required — the whole app is
built on each plugin's declarative `input_dict`/`output_dict`, which carries every
field's bounds, physical dimension, optionality and description. There is no fallback
for the older docstring-scraped format, and there should not be: that metadata is the
reason a field here can show its own range and meaning without a lookup table
maintained by hand.

## What you see first

Three doors. **Read a published pathway** — five of pyH2A's own reference models, each
reproducing its published cost. **Start your own** — a blank plant: the nine-step
techno-economic backbone with a placeholder plant that runs immediately at 5.5044 USD/kg,
so nothing is broken, everything is wrong, and every wrong thing is a field you can see.
**Open a file** — your own `.md`, parsed in the browser and never uploaded. A file it
cannot open says why: pyH2A's own `Example/*.md` predate the refactor and carry no
`# Input files to merge` table, so the door offers to reopen them with the defaults merged
in rather than reporting `KeyError: 'Functional Unit'`.

A new project gets a *start here* band naming the four values worth changing first; each
one opens the step that declares it and puts the field under your cursor. A walkthrough
spotlights seven real parts of the live app, offered on the first visit and always
available from `?` in the masthead. Each tab keeps a copy of the open file, so a reload
cannot lose an afternoon — which matters most in the static build, where there is no
server to hold it.

## Verify it

```bash
cd studio
./run test     # ruff, then 221 tests in about six seconds
```

The build verifies itself too: `deploy/build.py` unpacks the bundle it is about to write
into a clean interpreter and re-runs all five reference pathways plus the starter. It
checks two things separately, because they fail differently — the exact computed float to
a part in a billion, which catches a corrupt or missing data file, and the published
four-decimal figure, which catches the engine itself moving and is news rather than a
broken build. `scratch/tamper.py` proves it is not theatre: five sabotages, each refused
with the reason, including a 0.26% drift from one wrong depreciation rate.

The tests assert engine numbers, not this app's formatting. All five bundled pathways
reproduce their published cost; the trace agrees with a plain engine run to 1e-12; the
cost decomposition's residual is zero at machine precision; and a deliberately broken
reference is caught while the run it corrupts still reports success.

Visual changes need a browser pass as well. Attach to Chrome over CDP, screenshot with
`Page.captureScreenshot`, and *look at the image* — three real bugs in this build were
invisible to every test and obvious in a screenshot, including every number in two dark
panels rendering in near-black on near-black.

## The three things that were hard

Worth knowing before changing anything, because each one shaped the architecture.

**The engine mutates one dict in place, and later steps redefine earlier names.** After
`Power_Management` runs, `Power Generation > Available energy` means "still unspent
after allocation", not "generated" — four steps write it during a run. So "what could
step 7 see" is only answerable while the run happens. `core/trace.py` runs the workflow
one plugin at a time and snapshots the whole dict around every step; differencing two
snapshots gives what a step could see, what it actually wrote, and the file's own
literals. Five pathways trace in 25–90 ms against 6–9 ms for a plain run.

**A cell means two different magnitudes and only one is safe to show.** A pyH2A
`Quantity` holds `supplied_value` in `supplied_unit` (`5500 kW`, what the file says) and
`base_value` in `base_unit` (`5500000 W`, SI). Print the base beside the authored unit
and you get `5,500,000 kW` — a wrong number wearing a right-looking label, which shipped
in an earlier build of this project. `core/cells.py` is the only place an engine value
becomes JSON, and it reports the authored pair.

The inverse holds for validation: **bounds are declared in base units.** `Array azimuth`
is declared `[0, 3.14159]` — radians — while the file says `180 deg`. Validate the base
pair, display the authored pair.

**A dangling reference is silently worth 1.0.** Read `process_path` in
`Utilities/input_modification.py`: a path that does not resolve prints a warning to
stdout and substitutes `1.0`. A mistyped table name becomes a plausible cost in a run
that reports success. `core/refs.py` checks every reference against the cells that
genuinely exist at that point in the run, tells a forward reference apart from a typo,
and returns the intended target so the UI can offer the fix.

## Architecture

```
core/     everything that is not rendering
  grammar.py    markdown <-> ordered tables, cells verbatim; parses the defaults
                files alongside the user's so provenance survives the merge
  engine.py     the ONLY module that imports pyH2A
  trace.py      the workflow run step by step, with a snapshot around each
  cells.py      one engine value -> one JSON-safe record
  refs.py       reference grammar, and the silent-1.0 check
  project.py    an open project: text, parsed form, last run
  frame.py      the view model for one step: needs, scope, produces, problems
  graph.py      who feeds whom, where a step can go, what would fill a gap
  figures.py    data for the three figures, each proving it lost nothing
  examples.py   the five bundled pathways and their published costs

api.py      the whole backend as dispatch(op, payload) -> dict
server.py   stdlib HTTP: static files, and POST /api
web/        one page, no build step, no npm
  index.html    the shell: masthead, three columns, two overlays, the source drawer
  studio.css    layout and components on the shared tokens
  studio.js     one state object, one render per change, no framework
  format.js     one engine record -> readable HTML; the only place `form` is switched on
  figures.js    the three figures, as inline SVG
  welcome.js    the front door and the walkthrough
  tokens.css    pigments, type and rhythm, carried from the previous build

deploy/     the static build
  build.py      assembles dist/ and refuses to ship a bundle it has not verified
  boot.js       Pyodide, then one fetch interception onto api.dispatch
  shim/scipy/   the one constant the engine reads, checked against real scipy at build

templates/  starter scaffolds for a project that does not exist yet
examples/   pyH2A's own reference pathways
```

`api.dispatch` knows nothing about HTTP, and `server.py` does nothing but translate.
That is not tidiness: pyH2A runs in Pyodide (an earlier spike in this repo measured
16 ms warm runs in the browser), so a serverless build stays reachable exactly as long
as no request semantics leak into the core.

## Invariants

1. **The markdown file is the single source of truth.** An edit sets one cell in the
   verbatim document, re-serializes, re-parses, re-traces. Never keep UI state the file
   cannot reproduce.
2. **Only `core/engine.py` imports pyH2A.**
3. **Execution order comes from the engine** (`sorted by Position`). Never re-derive it.
   Positions are floats, so `201.5` sorts between 201 and 202 — which is what makes
   every gap in the rail insertable without renumbering.
4. **Show what the user wrote.** `5,500` and `98%`, never `5500.0` and `0.98`. The
   engine's parser normalises both away; echoing that back into a form silently
   rewrites the file's idiom on the next save.
5. **Dark ground means the engine computed it; paper means you wrote it.** No
   exceptions — it is how a reader learns what they can touch.
6. **A figure never invents a second opinion.** Everything drawn is an engine value, and
   anything that allocates one must prove it lost nothing. `figures.contributions`
   returns its own residual and the tests assert it is zero on every pathway.
7. **The functional unit is not always hydrogen.** `pv_e_lcoe` prices electricity at
   0.0286 USD/kWh. Every noun and unit comes from the file.
8. **The engine will not warn; we must.** Four checks run before the engine does — a
   reference that will not resolve, a value outside its declared bounds, a unit of the
   wrong dimension, and text in a numeric field. None of these is an error to pyH2A: it
   substitutes, converts, and returns a number.
9. **Zero false positives on the shipped files.** A validator that flags pyH2A's own
   reference inputs is worse than none, because it teaches the user to ignore it.
   `test_no_shipped_pathway_reports_a_problem` is that gate.

## Where the engine blames the wrong plugin

Worth its own heading, because it is the sharpest argument for validating at the field.

Type `banana` into `Electrolyzer > Nominal power` — a cell belonging to step 203 — and
the engine fails at step **202**, in `Photovoltaic_Plugin`, with `can't multiply sequence
by non-int of type 'float'`. Photovoltaic never reads that cell. Paths resolve lazily,
so whichever plugin first touches a reference to a broken value inherits the blame.

The studio shows both verdicts: the engine's, because it is what happened, and the
field's, because it is the only one that points at the row to fix.

## Two rules that are opposites, and both are right

They come up constantly and getting either backwards produces a screen that argues with
itself.

**Display the authored pair; validate the base pair.** A cell shows `5,500 kW` and `98%`
because that is what the file says. Its declared bounds are in SI base units, so
`Array azimuth` is checked against `[0, π]` radians while it displays `180 deg`.

**And state the bounds in the field's own terms.** The corollary, learned by shipping the
other half first: printing base-unit bounds beside an authored value makes six shipped
fields appear to hold a value outside their own stated range. `frame._bounds_shown`
converts back — unit first, then percent — so `10%` reads `0% … 100%`.

## What a step is worth

A plugin only reaches the result through the steps that run *after* it, and nothing on a
worksheet of nodes can show that. Add `Multiple_Modules_Plugin` at position 650 and it
writes `Fixed Operating Costs > Staff` exactly as documented — but Labor Operating Cost
ran at 600 and has already turned Staff into a cost, so the levelized cost does not move
by a single digit. At 401, where pyH2A's own examples put it, the same eight modules take
the file from 5.5044 to 4.6791 USD/kg. Identical step, identical numbers, every field
reading `ok`.

So a step reports what it is worth, measured by removing it and running again: *Worth
0.8252 USD/kg*, or *the pathway does not reach a cost without this step*, or — the one
that matters — *this step changes nothing where it is*, with the step it has to precede
and a button that moves it there. For an inert step the app tries every open position and
reports the last one that bites.

**Measured, never inferred.** Reading the declared inputs of later steps would be cheaper
and wrong: `Discounted_Cash_Flow_Plugin` consumes whole table *groups* by membership
rather than naming rows, so a declaration-based test would confidently call live steps
dead. `op_step_effect` costs a second run of the pathway and is fetched after the fields
are painted, like the figures.

## Open items

- **The scope panel does not deep-link.** Clicking a value from step 202 while step 400
  is open should be able to take you to 202; today it copies or binds a reference.
- **No undo.** Every edit returns a fresh `Project` and the old one is discarded, so the
  machinery is there — nothing keeps the history.
- **Reference binding is mouse-first.** `/` focuses the search and Enter inserts the top
  hit, but there is no arrow-key walk through results.
- **Seventeen fields across six plugins are declared float-only where an integer is a
  legitimate value.** Typing `4` into `Reverse Osmosis > Power demand` raised
  `Expected (<class 'float'>,), but got <class 'int'>`, while `Operating capacity factor`
  declares `{float, int}` and takes `2000` happily — so there was no rule to learn either.
  The app writes `4.0` on the float-only ones so nobody meets that message, but the honest
  fix is upstream: declare `{int, float}` wherever an integer is legitimate.
  **Worth a goodwill PR.**
- **There is no starter for an electricity pathway.** `Production_Plugin` declares
  `Plant design capacity` with dimension `energy/time` and its code then requests
  `power`, so for a `kWh` functional unit no unit string satisfies both — `kW`,
  `kWh/h`, `kWh/day` and `kWh/year` all fail, from opposite directions. The shipped
  `PV_E_Electricity_Production.md` sidesteps it by supplying `Design output by year` as a
  per-year array from the PV plugin. **Worth fixing upstream**; until then the front door
  points at that pathway instead of offering a blank one that cannot run.
- **Step 201's three tracking modes cannot be seen side by side.** They now share one
  colour scale, which makes them comparable one at a time; comparison is what they exist
  for and a small-multiple would serve it better.
- **Two-axis tracking collects less than no tracking** in the bundled irradiance table
  (`931` against `953 Wh/m²` peak). That is not physically possible, and it is upstream
  data rather than a rendering fault — but the studio is where a user meets it and gives
  them no way to check. Worth raising with the group.
- **`Grid Electricity > Cost = 10000.12 USD/kWh` stays as upstream ships it.** It is
  roughly 100× a real tariff and it is why PV+E bills 19.9 M in its final year. Fixing
  it in the bundled file would break the match against the published 4.1943, so it stays
  and the annual-cost figure names its own peak instead.

## Reviews

Four rounds of cold review, each by an agent given the running app and no history. Every
defect below is fixed; the reports are worth reading before the next pass, because they
describe the app better than this file does.

| Report | What it holds |
|---|---|
| `../docs/studio-review-1.md` | Cold design review, D1–D29, with measurements — contrast ratios, pixel envelopes, element counts, tab stops. Its central charge, which was right: *the app repeatedly shows the same number twice, differently, in one viewport, which teaches the reader not to trust the numbers.* |
| `../docs/studio-verify-1.md` | Correctness sweep, 13 defects and a 25-item PASSED list. Confirmed the engine layer clean and found that the failures were elsewhere: the app threw work away, and it diagnosed problems that did not exist. |
| `../docs/studio-review-2.md`, `../docs/studio-verify-2.md` | The confirmation round on those fixes. |
| `../docs/studio-firstrun.md` | 32 defects from a cold newcomer trying to *build* something rather than read it, and a blocking verdict: adding a step wrote a row narrower than its own table header, which real pyH2A rejects too. Everything in it is fixed; the report is the best description of what this app is for. |
| `../docs/studio-deploy-check.md` | The static build against the native server, 244 API ops across six pathways and all 74 steps. Every number a user reads is identical; the differences are floating point at the fifteenth digit, from Emscripten's libm against the host's. |

The pattern in the first three rounds: nothing was wrong with the arithmetic. Everything
was wrong with what the app claimed about the arithmetic — a range that contradicted its
field, a unit chip on the wrong operand, a caption promising a lens drawn in 8 pixels of
the palest ink available. Numbers that are right and presentation that is careless is the
same failure as numbers that are wrong, because the reader cannot tell them apart.

The fourth round was different, and worth the distinction. Its defects were not about
description: the app was writing files that could not be read, and running steps that did
nothing while reporting success. Reading a pathway had been exercised to death; building
one had never been tried.
