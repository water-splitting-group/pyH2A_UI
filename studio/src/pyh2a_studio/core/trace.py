'''Running a workflow so that every step's view of the world is recorded.

The studio's first requirement is to step through a pipeline and see, at each
step, what it was given, what already existed, and what it produced. The engine
does not offer that: plugins mutate one shared dict in place, and a later plugin
can change what an earlier name means. So the answer has to be captured while the
run happens.

`build` runs the workflow one plugin at a time and takes a snapshot of the whole
input dict immediately before and after each plugin. Two snapshots, differenced,
give the three sets a step needs:

- **visible** — every cell that existed before the step ran. What it could see.
- **wrote** — cells that appeared or changed. What it actually produced, as
  opposed to what its `output_dict` claims it produces.
- **literals** — cells present before the *first* step, i.e. authored in the file
  or merged from defaults. These stay visible at every position, which is what
  makes them the user's standing inputs.

A snapshot is `{(table, row, column): record}` where a record is
`cells.describe`'s output: JSON-safe, authored units, arrays digested. Digesting
at snapshot time is not an optimisation — it is the only moment an array holds the
values that step saw.

Cost: five bundled pathways trace in 25–90 ms, against 6–9 ms for a plain run.
Snapshotting is the bulk of it and it is worth every millisecond, because the
alternative — re-running the prefix once per step, as an earlier build did — is
quadratic and still cannot say what a step *changed*.
'''

import copy
import io
import time
from contextlib import redirect_stdout

from pyH2A.Plugins.Hourly_Irradiation_Plugin import calculate_PV_power_ratio
from pyH2A.Utilities.input_modification import execute_plugin

from pyh2a_studio.core import cells, engine

_SKIP_TABLES = frozenset({'Workflow', 'Display Parameters'})
'''Tables that are studio furniture rather than model state. `Workflow` is the
step list itself and `Display Parameters` configures upstream plotting; neither is
a value any step reads, and both would swamp the diff.'''


def _snapshot(inp):
    '''Every cell in the engine dict as `{(table, row, column): record}`.'''

    flat = {}
    for table_name, table in inp.items():
        if table_name in _SKIP_TABLES or not isinstance(table, dict):
            continue
        for row_name, row in table.items():
            if not isinstance(row, dict):
                flat[(table_name, row_name, '')] = cells.describe(row)
                continue
            for column_name, value in row.items():
                flat[(table_name, row_name, column_name)] = cells.describe(value)
    return flat


def _changed(before, after):
    '''Keys in `after` that are new or whose record differs from `before`.

    Record equality is the right test rather than value equality: two records
    differ exactly when something a screen would draw differs, which is the
    definition of "this step changed it" that matters here.
    '''

    changes = {}
    for key, record in after.items():
        if key not in before or before[key] != record:
            changes[key] = record
    return changes


def build(inp, snapshot_visible=True):
    '''Run the whole workflow step by step, recording each step's world.

    Parameters
    ----------
    inp : dict
        Engine input dict. Never mutated — the trace works on a deep copy.
    snapshot_visible : bool
        Keep the full pre-step snapshot on every step. True is what the worksheet
        needs. False keeps only the diffs and the literals, which is enough for a
        rail or a status strip and roughly halves the memory.

    Returns
    -------
    engine.Trace
        Never raises for a model-level failure: a plugin that throws becomes a
        step with `status='error'` carrying the message, every later step is
        `'skipped'`, and `trace.failed` names it. A malformed input dict — one
        with no `Workflow` or no `Functional Unit` — still raises, because that is
        a broken file rather than a broken model.
    '''

    working_inp = copy.deepcopy(inp)
    calculate_PV_power_ratio.cache_clear()
    order = engine.workflow_order(working_inp)
    positions = engine.workflow_positions(working_inp)

    partial = engine._PartialDCF(working_inp)
    literals = _snapshot(working_inp)

    steps = []
    failed = None
    captured = io.StringIO()
    total_started = time.perf_counter()

    with redirect_stdout(captured):
        before = literals
        for name in order:
            if failed is not None:
                steps.append(engine.Step(name=name, position=positions.get(name),
                                         status='skipped'))
                continue
            step, before = _run_one(name, positions.get(name), partial, before,
                                    snapshot_visible)
            steps.append(step)
            if step.status == 'error':
                failed = name

    duration_ms = (time.perf_counter() - total_started) * 1000
    stdout_text = captured.getvalue()
    _attribute_warnings(steps, stdout_text)

    result = None
    if failed is None:
        result = engine.RunResult(
            levelized_cost=_read(partial.inp, engine.LEVELIZED_COST_PATH),
            contributions=_read(partial.inp, engine.CONTRIBUTIONS_PATH),
            inp=partial.inp,
            plugs=partial.plugs,
            warnings=engine._warning_lines(stdout_text),
            stdout=stdout_text,
            duration_ms=sum(step.duration_ms for step in steps),
        )

    return engine.Trace(steps=steps, result=result, failed=failed,
                        literals=literals, duration_ms=duration_ms)


def _run_one(name, position, partial, before, snapshot_visible):
    '''Execute one plugin between two snapshots; return its Step and the after-state.'''

    started = time.perf_counter()
    try:
        execute_plugin(name, partial.plugs, print_info=False, dcf=partial)
    except Exception as error:  # a model failure is data, not an exception  # noqa: BLE001
        return engine.Step(
            name=name,
            position=position,
            status='error',
            duration_ms=(time.perf_counter() - started) * 1000,
            visible=before if snapshot_visible else {},
            error=str(error) or error.__class__.__name__,
            error_type=error.__class__.__name__,
        ), before

    duration_ms = (time.perf_counter() - started) * 1000
    after = _snapshot(partial.inp)
    return engine.Step(
        name=name,
        position=position,
        status='ok',
        duration_ms=duration_ms,
        visible=before if snapshot_visible else {},
        wrote=_changed(before, after),
    ), after


def _attribute_warnings(steps, stdout_text):
    '''Hand each engine warning to the step that was running when it printed.

    The engine prints warnings to one stream with no step marker, so exact
    attribution is impossible after the fact. What *is* reliable: a warning naming
    a table a step wrote belongs to that step. Anything unattributable lands on the
    trace's own warning list via the RunResult, so nothing is dropped.
    '''

    lines = engine._warning_lines(stdout_text)
    if not lines:
        return
    for step in steps:
        tables = {key[0] for key in step.wrote}
        step.warnings = [line for line in lines if any(table in line for table in tables)]


def _read(inp, path):
    '''`inp[a][b][c]` for a 3-tuple path, or None if any level is missing.'''

    node = inp
    for key in path:
        if not isinstance(node, dict) or key not in node:
            return None
        node = node[key]
    return node
