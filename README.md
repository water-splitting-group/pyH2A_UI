# Paper Plant Studio

A browser worksheet for [pyH2A](https://github.com/water-splitting-group/pyH2A), the
levelized-cost framework maintained by Jacob Schneidewind's water-splitting group. It
reproduces pyH2A's published cost for all five of its reference pathways — PV +
Electrolysis at 4.1943 USD/kg, Solar Thermal at 3.2706, Photoelectrochemical at 139.4189,
Photocatalytic at 185.4433, PV Electricity at 0.0286 USD/kWh — and it does it in the page,
with no Python installed and no server running.

A pyH2A project is one markdown file of tables. The engine parses it, runs a workflow of
plugins in order, and returns a discounted-cash-flow cost. **Every screen here is a view
of that one file**, which is the whole design: a structured edit re-serializes to the same
markdown the engine runs, so the forms and the raw text can never disagree, and a
downloaded `.md` reproduces the numbers you were looking at.

It is a worksheet, not a report. You step through the pipeline and at each step see what
it needs, what it can already reach, what it produced, what it is worth, and what is
wrong. Every value is editable in place and every edit re-runs the whole model — about
37 ms end to end on the seventeen-step PV + Electrolysis pathway.

## Run it

```bash
git clone --recurse-submodules git@github.com:hrishioa/pyh2a-ui.git
cd pyh2a-ui/studio
./run          # the app on http://localhost:8730
./run build    # the static build, served on http://localhost:8000
./run test     # ruff, then 233 tests in about seven seconds
```

The only prerequisite is [uv](https://docs.astral.sh/uv/). It fetches its own Python 3.12,
so nothing on your machine needs to match.

## Deploy it

Import the repository on Vercel and accept the settings in `vercel.json`. There is nothing
else to configure: the build installs uv, runs `deploy/build.py`, and serves the folder it
writes.

That build refuses to ship a broken deploy. It unpacks the bundle it is about to write
into a clean interpreter and re-runs all five reference pathways plus the starter, checking
two things separately because they fail differently — the exact computed float to a part in
a billion, which catches a corrupt or missing data file, and the published four-decimal
figure, which catches the engine itself moving. `studio/deploy/tamper.py` is the proof it
is not theatre: five sabotages, each refused with its reason, including a 0.26% drift from
one wrong depreciation rate.

The output is ten static files and a 2 MB bundle. First visit pulls the Pyodide runtime
(about 25 MB) from jsdelivr and caches it; after that the app boots in a few seconds and
runs entirely in the tab. Nothing is uploaded — these are somebody's unpublished cost
models, and the file never leaves the browser.

## The layout

```
studio/     the app. src/pyh2a_studio/core is the engine doorway, web/ is the frontend
pyH2A/      submodule, pinned at a15e7bb — the commit every number here was verified against
docs/       why the app is the shape it is: the working log, the engine audit, four cold reviews
vercel.json
```

Two files repay reading before you change anything. **`studio/README.md`** is the map of
the code: the three things that were hard, the invariants, and the two rules that are
opposites and both right. **`docs/pyh2a-audit.md`** is the map of the engine, and §6 is the
runtime contract this app is built against.

## A thing worth knowing

None of pyH2A's own example inputs in `pyH2A/src/pyH2A/Example/` will open in this app, or
in current pyH2A, without a change: they predate the refactor and carry no
`# Input files to merge` table, so nothing supplies their functional unit. Drop one in and
the app says exactly that and offers to reopen it with the defaults merged. Five lines fix
each file, and they are probably worth fixing upstream.

The engine is pinned rather than tracked because the app is built on each plugin's
declarative `input_dict`/`output_dict` — every field's bounds, physical dimension,
optionality and description comes from there. Bumping the submodule is a deliberate act:
run `./run test` and `./run build` after, and the build will tell you if a published cost
moved.
