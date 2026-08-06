# The written record

Everything here was produced while building the studio, and it is kept for one reason:
each document says why some part of the app is the shape it is. `../studio/README.md` is
the map of the code; this is the map of the reasoning.

Two honest caveats. The review reports cite screenshot folders (`shots-cold/`,
`shots-firstrun/`, and so on) that are not in this repository — 254 images, about 100 MB,
kept out so a clone stays small. And they were written against builds that no longer
exist; a defect described in the present tense was almost certainly fixed the same day.
Read them as a record of what went wrong and why, not as a bug list.

## Start here

| | |
|---|---|
| [`log.md`](log.md) | The working log, oldest to newest. Decisions with reasons, and especially the paths not taken. If you read one thing, read the last three entries. |
| [`pyh2a-audit.md`](pyh2a-audit.md) | **Read before touching the engine.** Full audit of pyH2A at `a15e7bb`: broken examples, the dead analysis layer, the silent-wrong-number bugs, and §6, the runtime contract this app is built against. |

## The engine

Five parallel static reviews of pyH2A's source, about 170 findings with stable IDs
(`CORE-n`, `UNIT-n`, `FIN-n`, `TECH-n`, `META-n`) that `pyh2a-audit.md` cites throughout.

| | |
|---|---|
| [`audit-core-utils.md`](audit-core-utils.md) | Input parsing, reference resolution, the `Quantity` type. `CORE-1..33`. |
| [`audit-unit-system.md`](audit-unit-system.md) | The unit handler, plus a full inventory of the 107 accepted tokens and what they reject. |
| [`audit-finance-plugins.md`](audit-finance-plugins.md) | Capital, replacement, labour, operating cost, discounted cash flow. `FIN-1..31`. |
| [`audit-tech-plugins.md`](audit-tech-plugins.md) | PV, electrolysis, PEC, photocatalytic, thermal. `TECH-1..31`. |
| [`audit-meta-layer.md`](audit-meta-layer.md) | Workflow execution, the analysis modules, plugin discovery. `META-1..50`. |
| [`03-engine-file-index.md`](03-engine-file-index.md) | Where everything lives in the engine tree. |
| [`01-refactor-arc-brief.md`](01-refactor-arc-brief.md) | The declarative-plugin refactor this app depends on, and why the pin matters. |
| [`02-direction-brief.md`](02-direction-brief.md) | Upstream state at the time: 19 open PRs, 20 open issues, and which of them this app touches. |

## Reviews of the studio

Four rounds, each by an agent given the running app and no history. Reports are cited from
`../studio/README.md` where the fix lives.

| | |
|---|---|
| [`studio-review-1.md`](studio-review-1.md) | Cold design review, `D1..D29`, measured — contrast ratios, pixel envelopes, tab stops. Its central charge, which was right: *the app repeatedly shows the same number twice, differently, in one viewport.* |
| [`studio-verify-1.md`](studio-verify-1.md) | Correctness sweep. Found the engine layer clean and the failures elsewhere: the app threw work away and diagnosed problems that did not exist. |
| [`studio-review-2.md`](studio-review-2.md), [`studio-verify-2.md`](studio-verify-2.md) | The confirmation round on those fixes, including four the first round's fixes introduced. |
| [`studio-firstrun.md`](studio-firstrun.md) | The best document here. A newcomer tries to *build* a pathway rather than read one, and cannot: adding a step wrote a table row narrower than its own header, which real pyH2A rejects too. |
| [`studio-numbers-2.md`](studio-numbers-2.md) | Every number the app shows, checked against the engine that produced it. |
| [`studio-firstrun-2.md`](studio-firstrun-2.md) | Per-defect verdicts on all 32, and the answer to the blocking question. |
| [`studio-deploy-check.md`](studio-deploy-check.md) | Static build against the native server: 244 API ops, six pathways, all 74 steps. Every number a reader sees is identical; the differences are floating point at the fifteenth digit, from Emscripten's libm against the host's. |

## The predecessor

Before the studio there was a Streamlit app, also called Paper Plant. It is not in this
repository. These are its reviews, kept because they are why the second app exists — the
verdict that ended it was *"reasonably fit for purpose, but it feels like a research
project."*

| | |
|---|---|
| [`design-review-1.md`](design-review-1.md), [`design-review-2.md`](design-review-2.md), [`design-review-3.md`](design-review-3.md) | Three cold design reviews of the Streamlit build. |
| [`verification-pass3.md`](verification-pass3.md) | Its correctness sweep: every page, every pathway, twice. |
| [`00-situating-synthesis.md`](00-situating-synthesis.md) | The orientation written at the very start, before any of it existed. |
