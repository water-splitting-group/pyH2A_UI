# First-run review — static build (127.0.0.1:8740)

Cold newcomer pass. Storage cleared before every scenario; static Pyodide build only; Chrome
1512×945 @dpr2 unless noted (also 1280×800 and 1024×768). Screenshots in `notes/shots-firstrun/`.
I did not read `studio/src` at any point; where I name a mechanism it came from the live DOM,
the SOURCE drawer, or from running the downloaded file through the real pyH2A in `pyH2A/src`.

---

## Verdict on the core question

**No. A competent engineer who does not know this app cannot build a pipeline with it.** They can
*read* one, and they can *change numbers that already exist* — that part is genuinely good. But the
moment they add a step, the app writes a malformed row into the markdown file and the model dies
with a raw Python error that names no cell and cannot be fixed from the worksheet.

I tried twice, following the app's own ranking and its own instructions:

| attempt | what the app asked for | what happened |
|---|---|---|
| `+ at 850` → **Reverse Osmosis** (its top-ranked suggestion, "2 of 5 ready") | 3 values, listed with descriptions | wrote a new `# Reverse Osmosis` table with **no `Unit` column**; entering `4` → `TypeError: Expected (<class 'float'>,), but got <class 'int'>`; entering `4.0` → `AttributeError: 'NoneType' object has no attribute 'strip'`. Unrecoverable in the UI. |
| `+ at 650` → **Multiple Modules** | 5 values, all in tables that *already have* `Unit` columns | wrote `Plant modules \| 2` into a `Name \| Value \| Unit \| Comment` table — a 2-cell row under a 4-cell header. Same `AttributeError`. All five unit boxes disappeared the instant a value was typed. `6 ran clean \| 3 never reached`, no cost. |

Both files are genuinely corrupt, not just mis-rendered — real pyH2A rejects the second one with the
identical error:

``
$ python3 -c "from pyH2A.run_pyH2A import pyH2A; pyH2A('studio/scratch/firstrun-mm-source.md', out)"
AttributeError: [Plugin: Multiple_Modules_Plugin] 'NoneType' object has no attribute 'strip'
``

The only escape is the SOURCE drawer: I hand-added a `Unit` column to the header and a unit to each
row, pressed APPLY, and all 10 steps ran clean — 5.5044 USD/kg on an otherwise untouched blank plant,
2.3524 USD/kg in the session where I had also changed the four start-here values. So the studio is
currently a *reader* with a markdown editor bolted on: the worksheet cannot author a new row.
Everything else in this report is downstream of that.

Second-worst finding, independent of the above: **ordinary editing gestures silently corrupt values.**
Triple-click a cell containing `2000`, type `3000`, and the file gets `30002000 kg/day` and the
headline calmly reports **0.0087 USD/kg**. No warning, no validation, a plausible-looking number.

### Boot, measured

| | result |
|---|---|
| warm start (cached) | **1.79 s / 2.04 s** — matches the panel's "starts in a second or two" |
| cold start, HTTP cache disabled, localhost | **3.1 s, 6.5 s, 11.3 s, 24.2 s, 27.8 s** across five runs |
| payload | 10.25 MB over 20 requests |
| longest phase | `loading numpy` — held 6.3 s in one run, ≈21 s in another, with a static label |
| main-thread freezes during boot | ≥515 ms measured by rAF gaps; multi-second stalls in the slow runs (CDP `Runtime.evaluate` itself timed out) |

The prose is honest and calming and the five stage names are real work, not theatre
(`cold-panel-2500ms.png`). The problem is not the wording, it is that the bar is step-proportional
with no elapsed time and no within-step progress, so a slow machine parks it on "loading numpy" for
twenty seconds with nothing moving. This machine was under load from other agents — but that is
exactly the condition a demo laptop with Zoom running will be in.

---

## Defects

Numbered by severity, not by order of discovery. "Fresh blank plant" = `localStorage.clear()`,
reload, wait for the front door, click **A blank plant**.

### Blockers

**1. Any value typed into a row that isn't already in the file is written as a short markdown row, which corrupts the file permanently.**
Repro: fresh blank plant → `+` next to `650` in the rail → **Multiple Modules** → type `2` into
"Plant modules" → Enter → SOURCE. The file now reads:
``
# Technical Operating Parameters and Specifications
Name | Value | Unit | Comment
--- | --- | --- | ---
Plant design capacity | 1000 | kg/day | What the plant is built to make
...
Plant modules | 2                       ← 2 cells under a 4-cell header
``
Same for `Solar collection area | 1000` (3-cell table) and three rows in Fixed Operating Costs.
Run stops: `THIS STEP RAISED ATTRIBUTEERROR 'NoneType' object has no attribute 'strip'`.
Real pyH2A fails on the same file with the same error, so this is a file-writing bug, not a display
bug. `shots-firstrun/53-multiple-modules-filled.png`, `shots-firstrun/54-source-multiple-modules.png`

**2. The unit box disappears as soon as the value is entered, so a unit can never be supplied through the worksheet.**
Repro: same as above. Before typing, `input[aria-label="Solar collection area unit"]` exists next to
the value box (placeholder `-`). After the first commit it is gone from the DOM — the row was written
without a Unit cell, so the app no longer renders one. This is what makes defect 1 unrecoverable:
the app asks you for a quantity whose declared dimension is `energy / volume`, accepts a bare
number, then removes the only control that could have fixed it.
`shots-firstrun/52-multiple-modules-added.png` (units present), `shots-firstrun/53-multiple-modules-filled.png` (units gone)

**3. Cell editing concatenates instead of replacing — silent numeric corruption.**
Repro: fresh blank plant → step `300 Production` → triple-click the "Plant design capacity" cell
(`2000`) → type `3000` → Enter. Field becomes `30002000`, unit stays `kg/day`, headline shows
**0.0087 USD/kg**, everything "ran clean". Measured cause: the app resets the input's selection on
every keystroke commit — after a triple-click `selectionStart/End = 0/0`; after click + ⌘A they are
`3/3`. So select-all *never* selects, and typed text is inserted around the old value. Second
instance: `0.45` → typed `0.5` → `0.50.45`; then typed `0.45` → `0.450.50.45`. The only way to change
a number is Backspace, one character at a time.
`shots-firstrun/27-triple-click-concat-plant-capacity.png`, `shots-firstrun/25-cell-corrupted-0.50.45.png`, `shots-firstrun/26-after-human-edits.png`

**4. Typing a whole number can hard-stop the model with a raw Python type error.**
Repro: fresh blank plant → `+` at `850` → **Reverse Osmosis** → type `4` into "Power demand" (a field
the app itself flags as `MISSING required`) → Enter.
`THIS STEP RAISED TYPEERROR 'Reverse Osmosis > Power demand > Value' (entry: '4'): Expected (<class 'float'>,), but got <class 'int'>`.
The input already declares `inputmode="decimal"` and the app knows the dimension and the range; it
just passes `4` through. Meanwhile `2000` into Plant design capacity is fine, so the newcomer has no
way to know which fields demand a decimal point.
`shots-firstrun/18-typeerror-after-bare-number.png`

**5. pyH2A's own example input files are rejected in silence.**
Repro: fresh front door → drop (or pick) `pyH2A/src/pyH2A/Example/210613_PV_E.md`. Nothing happens:
no error, `#welcome-error` stays `hidden`, masthead stays "no project", no console output. Same for
`210511_Future_PEC_Type_4.md`. I bisected it: the studio requires an `# Input files to merge` table.
Prepend five lines —
``
# Input files to merge

Name | Value
--- | ---
Default TEA | pyH2A.Config~Defaults_TEA.md
``
— and the identical file loads (12 steps, and then shows a real, well-explained failure). Removing
the `Type` column from `# Workflow` alone does not help. So the man who wrote these files will drag
one in, get absolutely nothing, and conclude the app is broken.
`shots-firstrun/55-drop-real-pyH2A-PV_E.png`, `shots-firstrun/56-drop-real-pyH2A-PEC4.png`, `shots-firstrun/57-real-file-plus-merge-table.png`

**6. Every other bad file is also rejected in silence.**
Repro: fresh front door → drop an empty `.md`, a plain `.md` with no tables, an `.md` whose Workflow
names `Not_A_Real_Plugin`, or a `.csv`. In all four cases: no message, no drop-zone state change,
front door unchanged. Same through the file picker. `#welcome-error` exists in the DOM and is never
shown — I polled it at 80 ms intervals for 3 s to rule out a transient. Three of the four
after-drop screenshots are **byte-identical** (`md5 32b7757447cf…` for `36-bad-file-drop`,
`38-drop-empty` and `41-picker-junk-file`, the last of those via the file picker rather than a drop):
not a subtle miss — for a junk file, an empty file and a picked file the screen does not change by a
single pixel.
`shots-firstrun/38-drop-empty.png`, `shots-firstrun/39-drop-unknown-plugin.png`, `shots-firstrun/40-drop-csv.png`, `shots-firstrun/41-picker-junk-file.png`

### Major

**7. The rail summary stops mentioning a failing step once its inputs are all supplied.**
Repro: fresh blank plant → add Reverse Osmosis → foot reads `8 ran clean | 1 need attention | 1 never reached | 3 inputs unsupplied` (correct, `44-foot-with-unsupplied.png`). Fill all three values
(step still failing with the TypeError) → foot reads **`8 ran clean | 1 never reached`** — 9 of 10
steps accounted for, the failure silently dropped, while the rail still shows `!` and the masthead
still says "no cost — the run stopped". In another state (real PV_E file) the counts exceed the step
count: `0 ran clean | 4 need attention | 11 never reached` with `STEPS 12`.
`shots-firstrun/46-foot-when-all-supplied-but-failing.png`, `shots-firstrun/57-real-file-plus-merge-table.png`

**8. "N values only you can supply" is the most prominent thing on the failure screen and is not clickable.**
Repro: add any plugin that fails → the `.unmet` block lists each missing cell with its description
and "no installed plugin writes this". It contains zero inputs and zero buttons
(`div.unmet` → `querySelectorAll('input').length === 0`). The actual editable fields are the same
three rows again, 200 px below, under "WHAT THIS STEP NEEDS". The block that reads like the call to
action is inert, and the screen says the same thing twice.
`shots-firstrun/16-after-add-reverse-osmosis.png`

**9. Tour: BACK, and every replay from `?`, points the ring at empty dark space.**
Repro: take the tour to stop 5 (which scrolls `#needs` to 462) → press **BACK** twice to stop 3.
The veil hole is at `y = -214` (stop 3) / `y = -369` (stop 2) — entirely above the column, so the
bubble narrates "What this step needs" over a uniformly dimmed screen with no highlight anywhere.
Identical on any second run from `?`, because the scroll is never restored.
`shots-firstrun/D-tour-back-to-3-offscreen.png`, `shots-firstrun/tourB-2.png`, `shots-firstrun/tourB-3.png`

**10. Tour: mouse-only, and not modal.**
Escape does nothing. Arrow keys do nothing. Its own **NEXT** is focusable element **72 of 72** — every
control in the app behind the veil comes first, and there is no focus trap or initial focus (after
boot `document.activeElement` is `BODY`). Clicks pass straight through the veil: at stop 3 I clicked
rail step `900` and the worksheet switched to Discounted Cash Flow while the tour kept describing
the previous step and pointing off-screen. `shots-firstrun/D-tour-clickthrough.png`

**11. The front door cannot be operated without a mouse.**
The five published pathways and "A blank plant" are bare `<li>` elements (`cursor:pointer`, no
`role`, no `tabindex`); the drop zone is a `<label>` wrapping a `hidden` file input, which is not
focusable. Tab from the front door visits exactly seven things — `OPEN A PATHWAY ▾`, `SOURCE`, `?`
and the worksheet search field, **all four of which are behind the overlay** (no `role="dialog"`,
no `aria-modal`) — then the pyH2A link, the name field, the tour checkbox, then wraps. ArrowDown,
Enter, Space, `1`, `b`: no-ops. There is no keyboard route into any of the three doors.
`shots-firstrun/01-frontdoor.png`

**12. Typing a name and pressing Enter does nothing, and nothing on screen says how to start.**
Repro: front door → click "call it", type `Newcomer Plant`, press Enter. No navigation, no start, no
message; the value just sits there (`window.__marker` unchanged, zero frame navigations). The
"START YOUR OWN" column has a labelled text field and no submit control — the only way forward is to
click the "A blank plant" row above the field, which carries no button affordance beyond a pointer
cursor. Filling a form and pressing Enter is the first thing anyone tries.
`shots-firstrun/02-after-enter-in-name.png`

**13. The name you type never reaches the file.**
Repro: name a project `Newcomer Plant` → SOURCE → `# Display Parameters / Name | New pathway` — the
input's *placeholder*, not your name. Download (correctly named `Newcomer_Plant.md`), reopen it
through OPEN A FILE, and the masthead reads **"New pathway"**. pyH2A uses that field for plot titles,
so the name is lost everywhere it matters. `shots-firstrun/32-after-open-downloaded-file.png`

**14. Nothing survives a reload, and nothing warns you.**
Repro: build anything → ⌘R. Back to the front door, "no project", work gone. The only persisted key
is `paperplant.seen` (a timestamp). No autosave, no `beforeunload` guard, no "you have unsaved work"
— in an app whose only save is DOWNLOAD .MD. `shots-firstrun/34-after-reload.png`

**15. The utility's name is dropped from the worksheet, and the start-here band lands on the wrong-looking row.**
The file row is `Electricity | 0.12 | 1/kg | 0.07 | USD | 1. | -` in `# Utilities`. The worksheet
renders a table titled **UTILITIES** with rows `01 Usage`, `02 Cost`, `03 Price_Conversion_Fac` —
"Electricity" appears nowhere. So clicking **Electricity** in the start-here band focuses a field
labelled "Usage" containing `50`, and a newcomer intending to change the electricity *price* changes
its *consumption* instead (I did exactly that: 5.9070 → 2.3524 USD/kg). Two utilities in one file
would be indistinguishable. `shots-firstrun/11-band-entry3-electricity.png`

### Copy and truth of the tour

**16. Stop 6 promises a delta that does not exist, and quotes a run time that contradicts the screen.**
"Every edit re-runs the whole model — about forty milliseconds — and the levelized cost updates with
the delta." I sampled the masthead at 60 ms intervals across four edits: the number is replaced, no
delta is ever rendered, and no element matching `[class*=delta]` exists. The masthead beside the
spotlight reads `RUN 6.6 ms` on the blank plant where the tour runs (24.7 ms on PV + Electrolysis) —
never forty. `shots-firstrun/T1-6.png`, `shots-firstrun/08-band-entry1-changed.png`

**17. Stop 1 contains a broken sentence.** "Hover a step to light its own." — its own what? (The
behaviour is real: hovering adds `edge lit` / `edge dim` to the SVG paths. The sentence just stops.)
`shots-firstrun/T1-1.png`

**18. Stop 5 shows raw markdown.** "A step usually also `*processes*` values you wrote" — literal
asterisks in the one place the product is showing off its prose. `shots-firstrun/T1-5.png`

**19. "walk me through it the first time" stays ticked on later visits but nothing happens.**
Repro: complete one visit (writes `paperplant.seen`) → reload → the box is still checked → start a
blank plant → no tour. A ticked control that does nothing.

### Design and polish

**20. "A blank plant / new / kg"** — the middle door mimics the published rows' value + unit stack
(`4.1943` over `USD/kg · published`) with the word "new" over a bare `kg`. It reads like a template
that failed to fill. Markup: `<span class="c">new<em>kg</em></span>`. `shots-firstrun/01-frontdoor.png`

**21. SOURCE says "untitled.md" for a named project.** Drawer header: `84 lines · untitled.md`, while
DOWNLOAD .MD correctly produces `Newcomer_Plant.md`. Open someone's file and the header is right —
only projects you create are anonymous. `shots-firstrun/30-source-drawer-head.png`

**22. The plugin picker truncates the useful end of every requirement.** Rows read
`…erse osmosis consumption (yearly)`, `…ble Capital Costs › Land required`, `…tion › PV hourly power generation`.
It is head-truncated, so the table name — the part that tells you where the value has to come from —
is exactly what is cut. There is no filter field and no way to see the full path.
`shots-firstrun/14-add-step-panel.png`

**23. An added step can run clean, change nothing, and the app has the evidence but never says so.**
Repro: fresh blank plant (5.5044 USD/kg) → `+` at `850` → Reverse Osmosis → repair the table in
SOURCE (add the `Unit` column) → APPLY. Result: `10 ran clean`, and the levelized cost is
**still exactly 5.5044 USD/kg**. The step produced real outputs
(`Reverse osmosis consumption (yearly) 1.88e+11 J×20`, `Capacity 14 540 m3/year`) that nothing
consumes. The rail proves the app knows: adding the step added exactly one edge,
`Production → Reverse Osmosis` (titled "Technical Operating Parameters and Specifications › Design
output by year"), and **no edge leaves it** — 21 paths, none starting at the Reverse Osmosis row.
Say it in words ("nothing in this workflow reads this step"), or the user believes they have modelled
a water plant. `shots-firstrun/58-edges-after-reverse-osmosis.png`, `shots-firstrun/24-ro-clean.png`

**24. The same 90-word plugin docstring is repeated under every row of a table.** In `# Utilities`,
the paragraph about `Cost_Path`/`Usage_Path`/`dcf.inflation_correction` appears three times in one
screen, pushing the three actual fields apart. The row label `Price_Conversion_Fac` is also clipped
mid-word with no ellipsis or tooltip. `shots-firstrun/11-band-entry3-electricity.png`

**25. The front door is cut off at laptop heights.** At 1024×768 the welcome panel is 949 px tall:
the fifth pathway's description and the tour opt-in sit 130 px below the fold. At 1280×800, 48 px
below. `body` is `overflow:hidden` and only `.overlay` scrolls, with no fade or scrollbar cue — the
first-run decision "walk me through it the first time" is invisible on a 13" screen until you happen
to scroll. `shots-firstrun/50-front-door-1024-clipped.png`, `shots-firstrun/47-front-door-1280.png`

**26. Copy-to-clipboard is silent.** Clicking a scope row copies a correct reference
(`{Construction > Capital spent in 1st year of construction > Value, -}` — verified via
`navigator.clipboard.readText()`), but nothing on screen changes: no flash, no "copied", no change to
the row or its COPY affordance. The tour promises the behaviour; the app performs it invisibly.
`shots-firstrun/43-row-copy.png`

**27. Rail keyboard navigation exists but is undiscoverable and inconsistent.** Every rail item and
every `+` carries `tabindex="-1"`, so Tab skips the pipeline entirely. `j` / `k` do move between
steps; ArrowDown / ArrowUp do nothing. Nothing in the UI or the tour mentions `j`/`k`.

**28. Boot progress has no time signal.** Five discrete stages, a step-proportional bar, no elapsed
counter, no bytes on the 10 MB fetch, nothing within `loading numpy` — the stage that owns most of
the wait. `shots-firstrun/cold-panel-2500ms.png`

**29. Two focus-ring conventions and one system-blue control.** Masthead buttons focus amber
`rgb(231,183,60)`; inputs focus navy `rgb(36,54,91)`. The front-door checkbox is a default
`accent-color: auto` blue tick in an otherwise paper-and-olive palette.

**30. Removing a step drops you at the top of the pipeline.** REMOVE STEP on `850` opens `100 Time`
rather than a neighbour of what you removed. `shots-firstrun/28-after-remove-step.png`

**31. Grammar in the rail foot.** "1 need attention" (needs), "1 inputs unsupplied" (input).

**32. The start-here band's exit is unearned in the small way that matters.** The fourth entry is
never seen struck through: 2.5 s after the fourth value committed, `#firstedits` was already
`hidden=true` / `display:none` while that fourth `<a>` still carried no `done` class — the band
removes itself before marking the last item, so the one moment it could say "that's all four" is the
one moment you never see. It also leaves without a word — no "you've changed the four that matter,
here is what to look at next" — and nothing in the masthead offers it again, so a completed band and
a band you dismissed with `×` are indistinguishable afterwards. The four navigations themselves are
the best interaction in the app; the ending throws away the payoff.
`shots-firstrun/12-band-all-four-done.png`, `shots-firstrun/13-band-after-4s.png`

---

## What works and must not be lost

1. **The boot copy.** "pyH2A runs here in your browser — nothing is uploaded and there is no server.
   The first visit downloads the Python runtime; after that it is cached and starts in a second or
   two." Every clause is true, including the timing (1.8–2.0 s warm). The five stage names describe
   real work.
2. **The front-door paragraph.** "A worksheet over pyH2A. A project is one markdown file of tables;
   the engine runs a pipeline of plugins over it and returns a levelized cost. This shows you that
   pipeline one step at a time — what each step needs, what it can already reach, what it produced —
   and lets you change any of it and watch the number move." That is the product, in four lines,
   with no adjectives. Keep it verbatim.
3. **The download round trip, verified against the real engine.** The studio showed 2.3524 USD/kg;
   real pyH2A on the downloaded `Newcomer_Plant.md` printed
   `Levelized cost of product (base case): Quantity(2.3524048790990517, 'USD/kg')`. Reopening the
   download in the app reproduces the same worksheet. Tour stop 7's claim is literally true.
4. **The spotlight mechanic.** A real hole punched over a real element (`box-shadow: 0 0 0 9999px`
   at 42%, 0.26 s ease-out), measured: paper `250,249,245` inside the hole vs `154,154,154` outside.
   On a genuine first run all seven stops hit the right element, fully in view, at 1512, 1280 and
   1024 px wide.
5. **Every other tour claim is true.** Hover lights that step's edges; `/` focuses the find field
   (searching `irr` → "14 match"); clicking a scope row copies a real pyH2A path reference; dark =
   computed and contains zero inputs; provenance really is labelled (`from Defaults_TEA.md`).
6. **The failure report, where it exists.** "no cost — the run stopped" in the masthead, the failed
   step marked and the downstream step marked *skipped*, the plugin's own exception verbatim, and the
   honest caveat: "The engine blames whichever step was running, which is not always the one that
   owns the bad value — paths resolve lazily. These steps are flagged: …". Also
   "no installed plugin writes this" — that is the sentence that tells a newcomer what kind of
   problem they have.
7. **The start-here band.** All four entries open the step that declares the value and focus the
   exact field, scrolled into view; each strikes through when changed; the headline moved every time
   (5.5044 → 4.5337 → 4.7517 → 5.9070 → 2.3524). It is the best thing in the new work — modulo
   defect 15 and the fourth entry vanishing before you see it strike.
8. **The plugin picker's ranking.** "at position 850 — ranked by how much of each one this project
   already supplies", with "2 of 5 ready / 40%" per plugin, in-use plugins dimmed and labelled.
   Escape closes it. Good idea, badly truncated (defect 22).
9. **REMOVE STEP** works, restores the previous cost exactly, and its tooltip is honest: "take this
   step out of the workflow; its tables stay in the file."
10. **The blank plant's file comments** — "Replace with the equipment your pathway actually buys",
    "Burdened, including overhead", "A fraction of what the plant cost". Whoever wrote those was
    thinking about the reader.
11. **Published pathways are clean and leak nothing.** After a full new-project session (renamed,
    edited, plugin added and removed, source hand-edited), opening PV + Electrolysis gave 17 steps,
    `17 ran clean`, 4.1943 USD/kg, `PV_E_Base.md`, no start-here band, no tour, no residue.
12. **The tour is offered once** (gated on `paperplant.seen`) and is always available from `?`.

---

## The three things I would fix before showing this to Jacob

**1. Make the worksheet able to write a valid row — then the app can do what it says it does.**
Pad every appended row to its table's header width, keep the unit cell editable after the first
commit (add `| Unit` to the header when the table lacks one), and coerce numeric entry to what the
plugin declares (`4` → `4.0` where a float is required) instead of forwarding a Python type error.
*Reasoning:* this is the whole pitch. The front door says "start your own", the picker invites you to
add a plugin, the failure panel tells you exactly which values only you can supply — and then the
first value you type produces `'NoneType' object has no attribute 'strip'` and a file that Jacob's
own engine rejects. He is the one person who will immediately recognise the ragged markdown, and the
first thing he will do after clicking through the tour is add a plugin. Nothing else on this list
matters if that path dead-ends. (Defects 1, 2, 4, and it also removes the need for defect 8's
inert list to exist at all.)

**2. Fix cell replacement, and never let a bad value pass silently.**
Stop rewriting `input.value` on every keystroke — commit on debounce/blur without touching the
element's selection — so triple-click and ⌘A work like they do in every other text field. Then
validate against the range and dimension the app already displays, and refuse to hand the engine a
value it cannot mean.
*Reasoning:* `30002000 kg/day → 0.0087 USD/kg`, no warning, "ran clean". A tool whose only job is to
produce a defensible number cannot silently produce an indefensible one from a normal editing
gesture. This is the defect that turns "nice demo" into "I would not let a student use this", and the
symptom — a collapsed selection — is one line of observable state away from the cause. (Defect 3.)

**3. Make the third door work for the files it exists to open, and never fail in silence.**
Accept a pyH2A input that has no `# Input files to merge` table (default the merge in, or tell the
user what to add); and whenever a file is refused, say why in `#welcome-error` — which is already in
the DOM, already styled, and never shown.
*Reasoning:* "OPEN A FILE — A pyH2A `.md` input file from your own work" is an explicit invitation to
Jacob. He will drag `210613_PV_E.md` — the file *he* ships in `pyH2A/src/pyH2A/Example/` — onto that
zone in the first minute, and the app will do absolutely nothing: no error, no console message, no
state change. That single non-event costs more credibility than every polish item in this report
combined, and what stands between him and a working screen is a five-line table the app could supply
itself. (Defects 5, 6.)

*Runner-up, if a fourth slot exists:* the tour's two false claims and two broken sentences (defects
16–18). It is a guided demo shown to the author of the engine; "the levelized cost updates with the
delta" beside a masthead that shows no delta, and "about forty milliseconds" beside `RUN 6.6 ms`, are
the kind of thing he will notice out loud.
