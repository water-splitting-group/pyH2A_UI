# First-run review, round 2 — confirming the fixes

Same method as `studio-firstrun.md`: cold newcomer, storage cleared before each scenario, static
Pyodide build at `127.0.0.1:8740` as the primary target, native at `127.0.0.1:8730` spot-checked
wherever the two builds could plausibly diverge. Chrome 1512×945 @dpr2 unless noted; also 1280×800
and 1024×768. Screenshots in `notes/shots-firstrun-2/`.

Two departures from round 1, both deliberate. I read `studio/src/pyh2a_studio/core/engine.py` once,
after observing a defect, to name its cause precisely — that is flagged where it happens. And I ran
three studio-authored files through the real pyH2A in `pyH2A/src` from `/tmp` to check the numbers
against the engine rather than against the screen.

---

## Answer to the blocking question

**Yes. A competent engineer who does not know this app can now build a pipeline with it** — three of
the four plugins I added from a blank plant reached a levelized cost, the real engine agrees with the
screen to the last digit, and the fourth failed for a reason the app explained and then offered to
fix. One caveat, and it has nothing to do with adding steps: **the twelve financial fields that come
from `Defaults_TEA.md` are text boxes that accept your typing and then discard it** (new defect N1).

The four attempts:

| what I did | what happened |
|---|---|
| `+ at 850` → **Reverse Osmosis**, typed `4`, `0.9`, `0.5` | `10 ran clean`, 5.5044 USD/kg. The app wrote `4.0`, added a `Unit` column, and filled it `J / m3` by itself. |
| `+ at 1000` → **Multiple Modules**, typed 5 values | `11 ran clean`, 5.5044 USD/kg; panel said the step was inert *and where it belonged*; **move to 550** → 4.8442, exactly the number it predicted. Real pyH2A on the downloaded file: `Quantity(4.8441825062073, 'USD/kg')`. |
| `+ at 350` → **Solar Thermal**, typed `0.2`, `250`, `0.3` | Stopped with the *same raw TypeError as round 1* — `250` was written as an int (defect 4, partial). Retyping `250.0` gave `10 ran clean`, 5.5060; real pyH2A: `Quantity(5.506000029928913, 'USD/kg')`. |
| `+ at 250` → **Battery**, typed 4 values | Honest dead end, correctly explained: one input is a dict a plugin must write. The panel named the three plugins that write it **as buttons**; clicking *Photovoltaic* inserted it at 225, ahead of Battery. That is the right answer to a hard question. |

Round 1's blocker — the ragged markdown row and the `'NoneType' object has no attribute 'strip'` —
is gone, and gone at the file level, not the display level. That was the whole pitch and it now works.

Round 1's second-worst finding was **not a defect at all**. My own instrument was lying: CDP's
`mouse.click({clickCount:3})` and `Meta+A` do not select text. An `<input>` I injected into the same
page behaves identically (triple-click → `selectionStart/End = 2/2`, type `30` → `2030`); the app
field differs only in where the caret lands, which is `text-align: right`. Given a real selection,
both replace correctly. Verified three ways: `2500`→`3000`, `22%`→`25%`, and Shift+Home from the
keyboard (`0/4` → replaced). I was wrong, and the record should say so.

---

## Per-defect verdict

| # | defect (round 1) | verdict | evidence |
|---|---|---|---|
| 1 | Short markdown row corrupts the file | **fixed** | `# Reverse Osmosis` written as `Name \| Value \| Unit` with 3-cell rows; `Plant modules \| 2 \| - \|` padded to a 4-column header; `Solar collection area \| 1000 \| m2` in a 3-column table. Real pyH2A on the 11-step file: `4.8441825062073 USD/kg` = the studio's 4.8442. `08-ro-filled.png`, `10-mm-filled.png` |
| 2 | Unit box disappears once a value is entered | **fixed** | Unit input survives commit and is pre-filled with the plugin's declared base unit: `J / m3` (energy/volume), `m2` (area), `-` (dimensionless). `08-ro-filled.png` |
| 3 | Cell editing concatenates | **was never a defect** | Control test: injected bare `<input>` gives the identical collapsed selection and identical concatenation under CDP. See above. |
| 4 | Bare integer hard-stops the model | **partial** | `4` → `4.0` on Reverse Osmosis. But `250` on Solar Thermal's `Solar Input > Mean solar input` is written `250` and raises `Expected (<class 'float'>,), but got <class 'int'>` — round 1's error verbatim. See N-note below for the cause. `21-solar-thermal-filled.png` |
| 5 | pyH2A's own Example files rejected in silence | **fixed** | Named cause, an explanation of the refactor, the exact five lines previewed, and a remedy button. Remedy loads the file (12 steps) and shows the 5 rows it genuinely lacks. Real pyH2A on the same merged file gives the identical `KeyError … 'Array azimuth'`. `25-drop-real-pyH2A-PV_E.png`, `26-remedy-taken-PV_E.png`, `49-native-drop-PEC4.png` |
| 6 | Every other bad file rejected in silence | **fixed** | Empty, junk prose, `.csv`, unknown plugin — each gets a specific message naming the cause plus the engine's own words. Same through the file picker. `23-drop-empty.png`, `24-drop-junk.png`, `24-drop-csv.png`, `24-drop-nop.png`, `27-picker-junk.png` |
| 7 | Rail tally drops a failing step / exceeds the step count | **fixed** | Partition holds in every state I produced: `8/1/1` of 10, `10/1` of 11, `2/1/7` of 10, `1/12` of 13, `1/11` of 12. |
| 8 | "N values only you can supply" is inert | **fixed** | Each gap is a `.gap.jump` that focuses its field scrolled into view (`20-unmet-jump-focus.png`), and gaps a plugin could fill carry `.fix` buttons that install it at the right position (`19-after-add-photovoltaic-from-gap.png`). |
| 9 | Tour BACK / replay points at empty dark space | **partial** | BACK is fixed — all six back-steps in view. The **first** forward arrival at stop 5 on a long step is still off-screen: hole at `y = 2465` in a 945-px viewport, and the whole viewport measures `151,150,149` (uniformly dimmed, no highlight anywhere). `05-tour-stop5-ring-offscreen.png` |
| 10 | Tour is mouse-only and not modal | **partial** | Escape closes it; ArrowRight/Left step; initial focus is `#tour-bubble`; tab order starts SKIP/BACK/NEXT. Still no focus trap (4th Tab lands on `#open-button`), no `role="dialog"`/`aria-modal`, and `#tour { pointer-events: none }` — clicks pass straight through the veil. `03-tour-clickthrough-attempt.png` |
| 11 | Front door cannot be operated without a mouse | **partial** | All six doors are `role="button" tabindex="0"` with real aria-labels, the overlay comes first in the tab order, and Enter opens them (Solar Thermal → 3.2706). Still unreachable: the drop zone (`<label class="dropzone">` wrapping a `hidden` file input, no tabindex/role) and the in-app **OPEN A PATHWAY** chooser (`#chooser-list li`, no tabindex, no role). Tab still visits the four masthead controls behind the overlay. `01-frontdoor.png` |
| 12 | Enter in the name field does nothing | **fixed** | Type `Newcomer Plant`, Enter → masthead "Newcomer Plant", 9 steps, 5.5044 USD/kg. |
| 13 | The typed name never reaches the file | **fixed** | SOURCE: `# Display Parameters / Name \| Newcomer Plant`. |
| 14 | Nothing survives a reload | **fixed, both builds** | Edit `Plant design capacity` → 2500 (4.3396), ⌘R: name, cost, step count and the file's `Plant design capacity \| 2500 \| kg/day` all survive. Same on native. `33-after-reload.png`, `34-native-after-reload.png` |
| 15 | Utility name dropped; band lands on the wrong row | **fixed** | Rows read `Electricity · Usage` / `Electricity · Cost` / `Electricity · Price Conversion Factor`, each labelled with its source column (`column Cost_Value`). The band's Electricity entry focuses the `0.07` price. `35-band-electricity.png` |
| 16 | Stop 6 promises a delta that does not exist; quotes 40 ms | **fixed** | The delta is real, as a toast: `5.5044 → 4.3396 (-21.16%)`, `4.5879 → 5.6059 (+22.19%)`. The "forty milliseconds" claim is gone. `40-delta-toast.png` |
| 17 | Stop 1 contains a broken sentence | **fixed** | "Hover a step to light the edges that touch it, and dim the rest. Click any step to open it." |
| 18 | Stop 5 shows raw markdown | **fixed** | "…those are marked as processed, and not counted as output." No asterisks. |
| 19 | "walk me through it the first time" stays ticked and does nothing | **broken** | Second visit with `paperplant.seen` set: `checked === true`, label unchanged, blank plant → `#tour` `display:none`. Identical to round 1. |
| 20 | "A blank plant / new / kg" reads like a failed template | **broken** | `<span class="c">new<em>kg</em></span>`, unchanged. `01-frontdoor.png` |
| 21 | SOURCE says "untitled.md" for a named project | **broken** | Project "Newcomer Plant", drawer header `75 lines · untitled.md`. |
| 22 | Picker truncates the useful end of every requirement | **partial** | Still head-truncated on screen (`…ation › Available energy (yearly)`), and still no filter field — but every line now carries `title="Power Generation › Available energy (yearly)"`, so the full path is recoverable on hover. `47-picker-truncation.png` |
| 23 | An added step can run clean, change nothing, and the app never says so | **fixed** | `.effect.inert`: "This step changes nothing where it is. Remove it and the cost stays 5.5044 USD/kg: it writes its values after everything that would read them has already run." Plus, where a better position exists, the position and the number it would give. `11-mm-inert-with-move.png` |
| 24 | The same 90-word docstring under every row of a table | **partial** | Three verbatim copies still fill one screen in `# Utilities`. The clipped label (`Price_Conversion_Fac`) is fixed. `35-band-electricity.png` |
| 25 | Front door cut off at laptop heights | **broken** | 1024×768: panel 949 px, fifth pathway's bottom at 833, tour opt-in at y=878 (110 px below the fold). 1280×800: opt-in 28 px below. `body` still `overflow:hidden`, only the overlay scrolls, no fade or scrollbar cue. `44-frontdoor-1024x768.png` |
| 26 | Copy-to-clipboard is silent | **fixed** | Rows now carry a visible `COPY` affordance and clicking one raises `copied {Non-Depreciable Capital Costs > Cost of land > Value, USD/acre}`. `38-copy-toast.png` |
| 27 | Rail keyboard navigation undiscoverable and inconsistent | **broken** | Steps are `role="button"` but still `tabindex="-1"`; every `+` is `tabindex="-1"`, so **adding a step is unreachable by keyboard**. `j`/`k` move; ArrowDown/ArrowUp do nothing; nothing on screen mentions `j`/`k`. |
| 28 | Boot progress has no time signal | **partial** | The bar now advances *within* a stage (0 → 36 → 45 px during "fetching the Python runtime"; 45 → 164 → 190 during "loading numpy"), and the final line is a genuine proof of life: "ready — reference pathway reproduces 4.1943 USD/kg in 125 ms". Still no elapsed counter and no bytes on the 10 MB fetch. `46-boot-panel-numpy.png` |
| 29 | Two focus-ring conventions and one system-blue control | **broken, slightly worse** | Now three rings: amber `rgb(231,183,60)` masthead, navy `rgb(36,54,91)` inputs and links, olive `rgb(79,113,50)` doors. Checkbox still `accent-color: auto`. `45-focus-ring-frontdoor.png` |
| 30 | Removing a step drops you at the top of the pipeline | **broken** | REMOVE STEP on `850 Reverse Osmosis` opens `100 Time`. `41-after-remove-step.png` |
| 31 | Grammar in the rail foot | **fixed** | "1 stopped the run", "1 input nothing supplies", "1 never reached". |
| 32 | The band's exit is unearned | **partial** | There is a farewell now — `that is the shape of it — the rest is the same move, anywhere on any step` (`39-band-farewell-toast.png`). The strike-through is still never seen: instrumented, exactly one mutation fires at **166 ms** after the fourth commit and it sets `hidden = true` while the fourth link is still `|Electricity` with no `done` class. Still no way to bring the band back. |

Tally: **16 fixed, 1 was never a defect, 8 partial, 7 broken.** Of round 1's six blockers, 1, 2, 5
and 6 are fixed, 3 was never a defect, and 4 is a recoverable major; every "broken" line is polish,
keyboard or copy.

---

## New defects

### N1 (major) — the twelve `Defaults_TEA.md` fields accept typing and silently discard it

Repro, both builds. Blank plant → rail `900 Discounted Cash Flow` → the `FINANCIAL INPUT VALUES`
group, headed **"12 to enter"**, every row labelled `from Defaults_TEA.md`. Select
`After-tax real IRR` (`8.0%`), type `20%`, Enter.

Result: the box shows `20%`. The scope column two inches to the right shows
`After-tax real IRR 0.08`. The masthead still reads `5.5044 USD/kg` — the 8% answer. SOURCE is
byte-identical (`1804` chars, no `# Financial Input Values` table). Reload: still 5.5044.
Two contradictory values for one cell, on screen at once. `52-defaults-edit-field-lies.png`

There *is* a message — a toast, `there is no "Financial Input Values" in this file — add the row
before writing to it` — but it is transient while the wrong number is permanent, and its instruction
is not actionable from the worksheet: there is no affordance to add the row. Same on PV + Electrolysis,
where 3 of the 4 editable cells on the first step come from the defaults (`Plant life` 20 → 25:
cost unchanged at 4.1943, file unchanged at 6864 chars). `51-defaults-edit-discarded.png`

This contradicts two things the app says out loud. Tour stop 3: "several are supplied by pyH2A's
defaults rather than by you. **Type in any of them.**" Tour stop 6: "Nothing is staged and there is
no run button: the number on screen is always the number your file produces." A field you cannot
write should not look like a field you can.

The same root cause makes the worth report asymmetric: `.effect` renders for all 8 steps in
PV + Electrolysis's own `# Workflow` table and for **none** of the 9 framework steps, all of which
still offer REMOVE STEP.

### N2 (major) — clearing a wrongly-typed value leaves a cell only SOURCE can reach

Repro, static build, from a blank plant:
1. `+` at `250` → **Battery**.
2. Type `5` into `Available energy (daily)`, Enter. The app flags it correctly:
   `NOT A SCALAR — this field takes a value an earlier step writes, not the number 5 (declared dict)`.
3. Select all, Backspace, Enter — the obvious undo.

The row is not removed. The file keeps `Available energy (daily) |  | J` — an empty Value cell — the
worksheet redraws the row as an un-editable dark `n/a` badge under "1 computed", the `<input>` is
gone from the DOM, and the engine now raises

``
THIS STEP RAISED TYPEERROR
'Power Generation > Available energy (daily) > Value' (entry: 'n/a'): Expected (<class 'dict'>,), but got <class 'str'>
``

The user's only escape is the SOURCE drawer. This is round 1's defect 1 in miniature: a normal
gesture writes a cell the engine rejects and the worksheet cannot unwrite. `54-cleared-cell-becomes-na.png`

### N3 (major, copy) — "Worth X USD/kg" is used for steps that make hydrogen more expensive

`Worth` is `|current − without|` with no sign, and the sentence beside it does not disambiguate.
Four measured instances:

| step | with | without | direction | what the app says |
|---|---|---|---|---|
| Multiple Modules @ 550, blank plant | 4.8442 | 5.5044 | **saves** 0.6602 | "Worth 0.6602 USD/kg" |
| Solar Thermal @ 350, blank plant | 5.5060 | 5.5044 | **costs** 0.0016 | "Worth 0.0016 USD/kg" |
| Reverse Osmosis @ 301, PV + E | 4.1935 | 3.3830 | **costs** 0.8105 | "Worth 0.8105 USD/kg" |
| Stored Power Electrolysis @ 205, PV + E | 4.1935 | 3.5840 | **costs** 0.6095 | "Worth 0.6095 USD/kg" |

On PV + Electrolysis every live step *raises* the levelized cost and all three are called "worth"
something. `22-solar-thermal-clean.png` has the masthead (5.5060) and the claim
("Worth 0.0016 … without this step the pathway costs 5.5044") in one frame.
`31-worth-sign-ambiguous.png` is the PV + E case. The arithmetic is right every time; only the word
is wrong. This is a tool whose product is a defensible number; "worth" is a claim about sign.

### N4 (minor) — three inputs share one aria-label

On `800 Variable Operating Cost`, `Electricity · Usage` (50), `Electricity · Cost` (0.07) and
`Electricity · Price Conversion Factor` (1.) all carry
`aria-label="Utilities Electricity value"`. A screen reader announces three identical fields; the
visible labels are correct and distinct, so only assistive tech is misled.

### N5 (minor) — REMOVE STEP is offered on the nine steps it cannot remove

REMOVE STEP on `500 Replacement` (a `Defaults_TEA.md` step) toasts
`Replacement_Plugin is not written in this file's Workflow table` and does nothing. The explanation
is good; it arrives after the click. Disable the button with that sentence as its title.

### N6 (minor) — the copy toast fires even when the clipboard write fails

`insert()` is `await navigator.clipboard.writeText(reference).catch(() => {}); toast(\`copied …\`)`.
In my unfocused CDP tab `writeText` rejects with `NotAllowedError` on every attempt and the toast
still says "copied" — the clipboard never changed across three different rows. A real user in a
focused window will not hit this, so it is low severity, but the toast should follow the promise, not
precede it.

### N7 (minor) — the rail foot calls a plugin-suppliable gap "nothing supplies"

Multiple Modules at 1000: foot reads `5 inputs nothing supplies` while the panel immediately below
splits it `4 VALUES ONLY YOU CAN SUPPLY` + `1 VALUE A PLUGIN COULD SUPPLY … written by PEC
Photocatalytic Photovoltaic Solar Concentrator`. Battery: foot `1 input nothing supplies`, panel
`1 VALUE A PLUGIN COULD SUPPLY`. The foot contradicts the panel it summarises.

---

## The cause of defect 4, named

Read once from `studio/src/pyh2a_studio/core/engine.py`, after observing the failure.
`spell_for_field` walks `installed_plugins()` and **returns on the first plugin that declares the
location**:

``python
spec = inputs.get(table_name, {}).get(row_name)
if not spec:
    continue
declared = (spec.get('Value') or {}).get('type') or set()
if declared == {float}:
    return f'{stripped}.0'
return text          # ← first match wins, even if it is the wrong plugin
``

`Solar Input > Mean solar input` is declared by three plugins. `PEC_Plugin` declares
`{float, int}` and sorts before `Solar_Thermal_Plugin`, which declares `{float}` — so the loop
returns `250` unchanged, and the plugin that actually reads the cell rejects it. Verified live
against the working tree:

``
$ PYTHONPATH=studio/src:pyH2A/src python3 -c "...; print(engine.spell_for_field('Solar Input','Mean solar input','250'))"
250
``

**Eleven locations disagree across plugins, and in every one the float-only declarer loses:**
`Solar Input > Mean solar input`, `Solar-to-Hydrogen Efficiency > STH`,
`Technical Operating Parameters and Specifications > Plant design capacity` (all three float-only in
`Solar_Thermal_Plugin`); five `Electrolyzer` rows (float-only in `Stored_Power_Electrolysis_Plugin`);
`Inflation > Combined inflator` and `Inflation > Inflation correction` (float-only in
`Replacement_Plugin`); `Financial Input Values > Reference year` (`{int}`-only in `Time_Plugin`).
So the bug lands on the whole solar-thermal path, the whole stored-power path, and any pathway with
`Replacement_Plugin`. The fix is to resolve the spec against the plugin that will read the cell — or,
failing that, to intersect every declaration and coerce when *any* declarer is float-only.

`declared_unit` has the same first-match-wins shape; the only unit disagreement in the installed set
is a `mass / time` vs `mass/time` spelling on `Plant design capacity`, which is harmless today.

---

## What I checked that turned out to be fine

- **All five published costs reproduce exactly**, on a browser that had just been through a full
  authoring session: PV + Electrolysis 4.1943 USD/kg (17 steps, `17 ran clean`), Solar Thermal
  3.2706 (10), Photoelectrochemical 139.4189 (13), Photocatalytic 185.4433 (13), PV Electricity
  0.0286 USD/kWh (12).
- **`Grid Electricity > Cost = 10000.12 USD/kWh`** in `PV_E_Base.md` looks like debris and is not:
  it is upstream pyH2A's own value, present in `old/pyH2A/data/PV_E/Base/PV_E_Base.md` and in
  upstream's end-to-end tests. It is a switch that prices grid power out of the model, and it is
  load-bearing — changing it to `0.12` through SOURCE moves PV + Electrolysis from 4.1943 to
  3.3898 USD/kg. The studio is faithful. But a newcomer who types `grid` into the find field sees
  `Grid Electricity › Cost — 10 000` and concludes the app is broken (`53-grid-electricity-10000.png`).
  One word of provenance on that row would earn a lot.
- **Range validation now exists and is good.** `900000` into `Capital spent in 1st year of
  construction` is flagged at the field: `ABOVE BOUNDS — 900,000 is above the declared maximum of 1`.
  `43-out-of-range-value.png`
- **Type validation before the run works** — `NOT A SCALAR … (declared dict)`, exactly as promised.
- **Native and static agree** everywhere I compared: Reverse Osmosis add-and-fill produced the same
  `4.0` / `J / m3` / `10 ran clean` / 5.5044 and the same file bytes; the refusal messages, remedy,
  reload persistence and the N1 defect are identical.
- **Boot**, warm: 1.66 s. Cold with HTTP cache disabled: 2.94 s, five stages, all real.

---

## The three things I would fix before showing this to Jacob

**1. Make the defaults-provided fields honest (N1).** Twelve boxes under a heading that says
"12 to enter", every one of which takes your keystrokes, keeps them on screen, and runs the model on
a different number. Jacob's first instinct on the DCF step will be to change the IRR — it is the one
input every TEA reviewer reaches for — and the app will show him 20% while quietly costing at 8%.
Either write the row into the project file on commit (the app already knows the table, the row, the
unit and the value), or render these cells read-only with the one-line explanation the toast already
carries. Anything is better than a text box that lies.

**2. Fix `spell_for_field` to consult the plugin that reads the cell (defect 4).** It is fixed for
Reverse Osmosis, which is the case it was written against, and still broken for eleven locations
including all three of Solar Thermal's own inputs. A reviewer who adds Solar Thermal — the second
pathway on the front door — hits round 1's exact Python type error on his third keystroke. The loop
is three lines from correct.

**3. Delete the veil's `pointer-events: none` and give the tour a focus trap (defect 10).** The tour
is the guided demo shown to the author of the engine. Right now a stray click behind the veil
switches the worksheet while the bubble keeps narrating the step you left, and the first forward
arrival at stop 5 on a long step dims the entire screen with the highlight 2,465 px below the fold
(defect 9). Both are visible in thirty seconds of clicking.

*Runner-up:* the word "worth" (N3). Three of the four steps I measured make hydrogen **more
expensive** and the app calls each of them "worth" money. He will notice, and it is a one-line
change: "costs 0.8105 USD/kg — without this step the pathway costs 3.3830".
