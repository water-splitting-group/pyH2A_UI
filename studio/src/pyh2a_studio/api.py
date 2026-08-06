'''The whole backend as one function: `dispatch(op, payload) -> dict`.

No HTTP, no framework, no globals beyond one open project per session id. `server.py`
maps URLs onto this and nothing else; a Pyodide build would call it directly from
JavaScript with the same arguments and get the same answers.

That constraint is not tidiness. pyH2A runs in Pyodide — an earlier spike in this
repo measured 16 ms warm runs in the browser — so a serverless build of this studio is
reachable, and stays reachable only as long as no request semantics leak into the
core. One function is the cheapest way to keep that true.

Errors are values. Every op returns a dict; a failure returns `{'error': …}` with a
message written for the person who will read it on screen, and the caller decides the
status code. Nothing here raises for a bad file, a bad edit, or a model that blows up
mid-run — those are ordinary states with real screens behind them.
'''

import copy
import time
import traceback

from pyh2a_studio.core import (examples, engine, figures, frame, grammar, graph,
                               project, refs, starters)

SESSIONS = {}
'''Open projects by session id, most recently used last.

A session exists so two browser tabs do not fight over one document. Without it they
do: the tab that opens a pathway last wins, and the other keeps rendering a masthead
from one project beside a body from another. The client mints an id per tab and keeps
it in `sessionStorage`, which survives a reload and does not leak between tabs.
'''

DEFAULT_SESSION = 'main'
MAX_SESSIONS = 24
'''Cap on retained projects. Each holds a full trace with a snapshot per step — a few
megabytes — and a long-running server would otherwise accumulate one per tab ever
opened. The least recently used is dropped; its tab gets a clean "no project open"
and re-opens, which is the correct behaviour for a session that has been idle through
twenty-four others.'''


def dispatch(op, payload=None):
    '''Run one operation. Never raises.

    Parameters
    ----------
    op : str
        Operation name, e.g. `'project.open'`.
    payload : dict, optional
        Operation arguments.

    Returns
    -------
    dict
        The operation's result, or `{'error': str, 'op': str}`. Unexpected
        exceptions additionally carry `'traceback'`, because a studio for people who
        write plugins should hand them the stack rather than hide it.
    '''

    payload = payload or {}
    handler = OPS.get(op)
    if handler is None:
        return {'error': f'unknown operation "{op}"', 'op': op,
                'known': sorted(OPS)}

    started = time.perf_counter()
    try:
        result = handler(payload)
    except (KeyError, ValueError, TypeError) as error:
        return {'error': f'{error.__class__.__name__}: {error}', 'op': op}
    except Exception as error:  # a studio hands the developer the stack  # noqa: BLE001
        return {'error': f'{error.__class__.__name__}: {error}', 'op': op,
                'traceback': traceback.format_exc()}

    result['took_ms'] = round((time.perf_counter() - started) * 1000, 2)
    return result


def _session(payload):
    '''The open project for this payload's session.

    Raises
    ------
    KeyError
        When nothing is open. The client's answer is to call `project.open`, and the
        message says so.
    '''

    key = payload.get('session', DEFAULT_SESSION)
    if key not in SESSIONS:
        raise KeyError(f'no project open in session "{key}" — call project.open first')
    # Touch, so an active tab is never the one evicted.
    opened = SESSIONS.pop(key)
    SESSIONS[key] = opened
    return opened


def _store(payload, opened):
    key = payload.get('session', DEFAULT_SESSION)
    SESSIONS.pop(key, None)
    SESSIONS[key] = opened
    while len(SESSIONS) > MAX_SESSIONS:
        SESSIONS.pop(next(iter(SESSIONS)))
    return opened


def _summary(opened):
    '''The state every screen needs on every response: cost, status, counts.

    Returned by every op that can change the project, so the client never has to ask
    a second time to find out what an edit did. An edit that moves the cost should
    show the new cost in the same round trip that applied it.
    '''

    if opened.error:
        return {'name': opened.name, 'error': opened.error, 'steps': 0}

    run = opened.run
    result = run.result
    cost = None
    if result is not None:
        cost = {
            'value': float(result.levelized_cost.supplied_value),
            'unit': str(result.levelized_cost.supplied_unit),
        }

    return {
        'name': opened.name,
        'origin': opened.origin,
        'dirty': opened.dirty,
        'functional_unit': opened.functional_unit(),
        'steps': len(run.steps),
        'failed': run.failed,
        'cost': cost,
        'duration_ms': round(sum(step.duration_ms for step in run.steps), 2),
        'trace_ms': round(run.duration_ms, 1),
        'warnings': result.warnings if result else [],
        'problems': len(opened.check_references()),
    }


# ---------------------------------------------------------------- operations


def op_examples(_payload):
    '''Everything the front door can open: published pathways, and scaffolds.'''

    return {
        'examples': [
            {'key': example.key, 'title': example.title, 'blurb': example.blurb,
             'reference_cost': example.reference_cost, 'unit': example.unit}
            for example in examples.EXAMPLES
        ],
        'starters': [
            {'key': starter.key, 'title': starter.title, 'blurb': starter.blurb,
             'unit': starter.unit}
            for starter in starters.STARTERS
        ],
    }


def op_project_open(payload):
    '''Open a bundled example, a starter scaffold, or supplied markdown.'''

    if payload.get('example'):
        example = examples.get(payload['example'])
        opened = project.Project.open(example.markdown(), origin=example.file_name,
                                      title=example.title)
    elif payload.get('starter'):
        starter = starters.get(payload['starter'])
        chosen = payload.get('name') or 'New pathway'
        opened = project.Project.open(starter.markdown(), origin='untitled.md',
                                      title=chosen)
        # The name has to land in the file, not just in the masthead. It used to be an
        # in-memory title only: you typed "Jacob demo", saw it in the header, downloaded
        # the file, opened it again and got "New pathway" — the one thing this app
        # promises is that the file is what you saw.
        opened = opened.edit('Display Parameters', 'Name', 'Value', chosen, create=True)
        opened.dirty = True
    elif 'markdown' in payload:
        origin = payload.get('origin', 'uploaded.md')
        # The guard covers the rail as well as the parse. `frame.rail` imports every
        # plugin the Workflow names, so a file citing one that is not installed raises
        # here — after a clean parse — and used to reach the client as a bare
        # ModuleNotFoundError with a traceback attached.
        try:
            opened = project.Project.open(payload['markdown'], origin=origin)
            if opened.error:
                raise ValueError(str(opened.error))
            response = {'project': _summary(opened), 'rail': frame.rail(opened),
                        'teaches': _teaches(payload, opened)}
        except Exception as failure:  # noqa: BLE001 - the diagnosis is the whole point
            return {'refused': _diagnose(payload['markdown'], failure, origin)}
        _store(payload, opened)
        return response
    else:
        raise ValueError('project.open needs "example", "starter" or "markdown"')

    _store(payload, opened)
    return {'project': _summary(opened), 'rail': frame.rail(opened),
            'teaches': _teaches(payload, opened)}


MERGE_TABLE = ('# Input files to merge\n\nName | Value\n--- | ---\n'
               'Default TEA | pyH2A.Config~Defaults_TEA.md\n')
'''The five lines that bring in pyH2A's own defaults. Every file the engine ships since
the refactor begins with them; none of the files in `pyH2A/src/pyH2A/Example/` do.'''


def _diagnose(markdown, failure, origin):
    '''Why a file was refused, and — when the app can tell — what would fix it.

    Every one of pyH2A's own example inputs is rejected by this app, because none of them
    carry an `# Input files to merge` table: without it nothing merges `Defaults_TEA.md`,
    so `Functional Unit` is unsupplied. Handing a scientist their own project file back
    with the word "KeyError" is not a refusal they can act on, and the front door showed
    nothing at all — the error element existed and was only ever hidden.

    The remedy is offered rather than applied: adding five lines to somebody's input file
    is their decision, and the diff is small enough to show them.
    '''

    detail = str(failure)
    detail = detail.split(':', 1)[1] if ':' in detail else detail
    detail = detail.strip().strip('\'"')

    # A workflow naming a plugin that is not installed raises while the rail imports it,
    # long after a clean parse. That is the single most likely thing to be wrong with a
    # file from another group, and "No module named 'pyH2A.Plugins.Foo'" names the
    # import machinery rather than the row the reader has to change.
    if isinstance(failure, ModuleNotFoundError):
        plugin = str(failure).rsplit('.', 1)[-1].strip('\'"')
        return {'origin': origin, 'saw': str(failure),
                'headline': f'{origin} runs {plugin}, which is not installed here.',
                'detail': 'Its Workflow table names a plugin this copy of pyH2A does not '
                          'have. Either the file comes from a fork with extra plugins, or '
                          'the name is misspelled — the Workflow row is the thing to '
                          'change, and the engine will list what it does have.'}

    # Three different files reach here and want three different first sentences.
    #
    # Someone's notes, or a CSV: no `#` headings and no pipes anywhere. That is not a
    # pre-refactor pyH2A input, it is not a pyH2A input at all, and telling them to add
    # a merge table would send them off to edit the wrong thing.
    #
    # A file that clearly *attempted* a table — pipes, but nothing the parser accepted —
    # gets the engine's own sentence, because "Remove the outer pipes." is worth more
    # than any category the app could put above it.
    headings = sum(1 for line in markdown.splitlines() if line.startswith('#'))
    piped = sum(1 for line in markdown.splitlines() if '|' in line)

    if not headings and not piped:
        return {'origin': origin, 'saw': detail,
                'headline': f'{origin} does not look like a pyH2A input file.',
                'detail': 'A pyH2A project is markdown tables under `#` headings — a '
                          'workflow, a functional unit, and one table per plugin. This '
                          'file has neither headings nor tables, so there was nothing '
                          'to parse.'}

    if not headings:
        return {'origin': origin, 'saw': detail, 'headline': detail,
                'detail': f'{origin} has table rows but no `#` headings, so the engine '
                          'has no table names to file them under. Every pyH2A table sits '
                          'beneath a heading that names it.'}

    missing_merge = '# Input files to merge' not in markdown

    if missing_merge:
        # Two different first symptoms, one cause. A file whose prose starts above any
        # table fails to parse; one that parses fails later for want of a functional
        # unit. Both open once the defaults are merged, so both get the same remedy and
        # an honest account of what was actually seen.
        headline = (f'{origin} does not merge pyH2A\'s defaults'
                    + (f', so nothing supplies {detail}' if 'outside any table' not in detail
                       else ' — and its first line is text rather than a table heading'))
        return {
            'origin': origin,
            'headline': headline + '.',
            'saw': detail,
            'detail': 'Every input file since the refactor opens with a table naming the '
                      'defaults to merge. Files written before it — including the ones in '
                      'pyH2A\'s own Example folder — leave it out, and then there is no '
                      'functional unit, no financial parameters and no workflow defaults '
                      'to fall back on.',
            'remedy': {'label': 'open it with pyH2A\'s defaults merged in',
                       'markdown': MERGE_TABLE + '\n' + markdown,
                       'preview': MERGE_TABLE},
        }

    return {'origin': origin, 'saw': detail,
            'headline': f'{origin} could not be opened: {detail}.',
            'detail': 'The file names the defaults it merges, so this is a fault in the '
                      'file itself rather than a missing scaffold.'}


def _teaches(payload, opened):
    """The first edits a starter wants you to make, resolved to real fields and steps.

    A blank plant runs, which means every number on it is a placeholder producing a
    plausible answer. That is the point and it is also the danger: without a route in, a
    new reader sees 5.5044 USD/kg and has no idea which of forty values is theirs.

    Each entry names the step that declares it, so the client can navigate straight
    there — and an entry no step declares is dropped rather than offered as a link to
    nowhere. An entry may also name the column, which a row carrying several quantities
    needs: `Utilities > Electricity` is a usage, a price and a conversion factor, and
    pointing at the row alone landed on the first of them. The band says "Electricity"
    and a reader following it means the tariff they pay.
    """

    if not payload.get('starter'):
        return []

    owners = {}
    for name in opened.order():
        for field in frame.fields_of(opened, name):
            owners.setdefault((field['table'], field['row']), name)

    wanted = []
    for entry in starters.get(payload['starter']).teaches:
        table, row, *rest = entry.split('\u0000')
        owner = owners.get((table, row))
        if owner:
            found = {'table': table, 'row': row, 'step': owner,
                     'label': frame.label_of(owner)}
            if rest:
                found['column'] = rest[0]
            wanted.append(found)
    return wanted


def op_project_state(payload):
    """What this session holds, or nothing.

    "Nothing is open" is a state, not a failure: it is what every fresh tab reports on
    its first call. Returning an error made that first call a 400 in the console of an
    app behaving perfectly.
    """

    key = payload.get('session', DEFAULT_SESSION)
    if key not in SESSIONS:
        return {'project': None, 'rail': []}
    opened = _session(payload)
    return {'project': _summary(opened), 'rail': frame.rail(opened)}


def op_project_source(payload):
    '''The file text, for the source editor and for download.'''

    opened = _session(payload)
    return {'markdown': opened.markdown, 'name': opened.name, 'origin': opened.origin}


def op_step(payload):
    '''One step's whole frame.'''

    opened = _session(payload)
    name = payload.get('step')
    if not name:
        raise ValueError('step needs a "step" name')
    return {'frame': frame.build(opened, name), 'project': _summary(opened)}


def op_cell_edit(payload):
    '''Write one cell, re-run, and report what moved.

    `before`/`after` name the levelized cost on either side of the edit, so the UI can
    show the consequence at the moment of the change rather than making the user hunt
    for it on another screen. An edit that breaks the model returns normally, with
    `failed` naming the step — that is a result, not an error.
    '''

    opened = _session(payload)
    for key in ('table', 'row', 'column'):
        if not payload.get(key):
            raise ValueError(f'cell.edit needs "{key}"')

    before = _cost_of(opened)
    updated = opened.edit(payload['table'], payload['row'], payload['column'],
                          payload.get('text', ''), create=bool(payload.get('create')))
    _store(payload, updated)

    return {
        'project': _summary(updated),
        'rail': frame.rail(updated),
        'before': before,
        'after': _cost_of(updated),
        'frame': frame.build(updated, payload['step']) if payload.get('step') else None,
    }


def _cost_of(opened):
    if opened.error or opened.run is None or opened.run.result is None:
        return None
    return float(opened.run.result.levelized_cost.supplied_value)


def op_source_replace(payload):
    '''Replace the whole file — the source editor's save.'''

    opened = _session(payload)
    updated = opened.reopen(payload.get('markdown', ''))
    updated.dirty = True
    if updated.error:
        # A file that will not parse is a normal state with a real screen behind it:
        # keep it, so the editor can show the message beside the text that caused it.
        _store(payload, updated)
        return {'project': _summary(updated), 'rail': []}
    return _commit(payload, updated)


def op_reference_check(payload):
    '''Validate a reference string against a step's real scope.

    Called while typing, so it must be cheap: it reads the last trace's snapshots and
    runs nothing.
    '''

    opened = _session(payload)
    step_name = payload.get('step')
    available = opened.visible_to(step_name) if step_name else set(opened.reachable())
    later = opened.produced_later(step_name) if step_name else {}
    return {'check': refs.check(payload.get('text', ''), available, later)}


def op_reference_search(payload):
    '''Cells matching a query, for path autocomplete.

    Ranked so that the useful answer is first: exact substring in the row name beats
    the table name, and cells already in scope beat ones that arrive later. Results
    carry the reference string to insert, so the client never builds one itself.
    '''

    opened = _session(payload)
    step_name = payload.get('step')
    query = (payload.get('query') or '').strip().lower()
    limit = int(payload.get('limit', 40))

    # A step's own outputs are searchable at that step. Asking for 'levelized' while
    # standing on the step that computes it returned nothing, which reads as the search
    # being broken rather than as a scope rule.
    visible = dict(opened.available_at(step_name)) if step_name else dict(opened.reachable())
    step = opened.run.step(step_name) if (step_name and opened.run) else None
    if step is not None:
        visible.update(step.wrote)
    later = opened.produced_later(step_name) if step_name else {}

    hits = []
    for key, record in visible.items():
        if frame.is_engine_column(key[2], frame.SCOPE_HIDDEN):
            continue
        score = _score(key, query, record)
        if score is not None:
            hits.append((score, 0, key, record, None))

    for key, (writer, position) in later.items():
        if frame.is_engine_column(key[2], frame.SCOPE_HIDDEN) or key in visible:
            continue
        score = _score(key, query, None)
        if score is not None:
            hits.append((score, 1, key, {'form': 'absent'}, {'step': frame.label_of(writer),
                                                             'position': position}))

    hits.sort(key=lambda hit: (hit[1], -hit[0], hit[2]))
    shown = hits[:limit]
    return {'shown': len(shown), 'limit': limit, 'results': [
        {'table': key[0], 'row': key[1], 'column': key[2], 'record': record,
         'pending': pending,
         'reference': refs.format_reference(key[0], key[1], key[2],
                                            record.get('unit') or '-')}
        for _, _, key, record, pending in shown
    ], 'total': len(hits)}


def _score(key, query, record=None):
    '''Relevance of a cell to a query, or None when it does not match.

    Every query word must appear somewhere in the path — an AND, because typing more
    words should narrow. Position is scored so a hit in the row name outranks one in
    the table name: the row is what the user is naming.

    The **unit** is searchable too. The box advertises "find a value by table, row or
    unit", and typing `kW` matched nothing, because the unit was never in the haystack —
    a promise in a placeholder is a promise.
    '''

    if not query:
        return 1
    table, row, column = key
    unit = (record or {}).get('unit') or ''
    haystack = f'{table} {row} {column} {unit}'.lower()
    words = query.split()
    if not all(word in haystack for word in words):
        return None

    score = 0
    for word in words:
        if word in row.lower():
            score += 10
        if row.lower().startswith(word):
            score += 6
        if word in table.lower():
            score += 3
        if unit and word == unit.lower():
            score += 8
    return score


def op_graph(payload):
    '''The workflow as nodes, edges, insertion points and unmet inputs.'''

    opened = _session(payload)
    return {'graph': graph.build(opened), 'project': _summary(opened)}


def op_plugins(payload):
    '''Every installed plugin, ranked by how much of it this project already supplies.'''

    opened = _session(payload)
    return {'plugins': graph.catalogue(opened)}


def op_workflow_add(payload):
    '''Put a plugin into the workflow at a position.

    Adding a step is one cell: a row in the `Workflow` table whose value is its
    position. The engine sorts on that column and parses it as a float, so a step can
    always be slotted between two others without renumbering anything.

    The new step will almost certainly need inputs the file does not have yet. That is
    the expected state, not an error — it appears immediately in the rail as fields to
    fill, which is the point of adding it.
    '''

    opened = _session(payload)
    name = payload.get('plugin')
    position = payload.get('position')
    if not name:
        raise ValueError('workflow.add needs a "plugin"')
    if position is None:
        raise ValueError('workflow.add needs a "position"')
    if name in opened.order():
        raise ValueError(f'{name} is already in this workflow')
    installed = engine.installed_plugins()
    if name not in installed:
        near = [entry for entry in installed if name.lower()[:6] in entry.lower()]
        raise ValueError(f'no plugin named {name} is installed'
                         + (f' — did you mean {", ".join(near[:3])}?' if near else ''))

    updated = opened.edit('Workflow', name, 'Position', _position_text(position),
                          create=True)
    return _commit(payload, updated, added=name)


def op_workflow_move(payload):
    '''Change a step's position. Execution order follows immediately.'''

    opened = _session(payload)
    name = payload.get('plugin')
    position = payload.get('position')
    if not name or position is None:
        raise ValueError('workflow.move needs "plugin" and "position"')

    updated = opened.edit('Workflow', name, 'Position', _position_text(position))
    return _commit(payload, updated)


def op_workflow_remove(payload):
    '''Take a step out of the workflow, leaving its tables in the file.

    Deliberately not a delete of the plugin's data. Removing `Battery_Plugin` should
    not silently destroy the `Battery` table the user wrote — they may be trying the
    model without it, and putting the step back has to restore what they had.
    '''

    opened = _session(payload)
    name = payload.get('plugin')
    if not name:
        raise ValueError('workflow.remove needs a "plugin"')
    if name not in opened.order():
        raise ValueError(f'{name} is not in this workflow')

    document = copy.deepcopy(opened.document)
    workflow = document.get('Workflow')
    if workflow is None or name not in workflow.rows:
        raise ValueError(f'{name} is not written in this file\'s Workflow table')
    del workflow.rows[name]

    updated = opened.reopen(grammar.serialize_document(document))
    updated.dirty = True
    return _commit(payload, updated, removed=name)


def _commit(payload, updated, **extra):
    """Build the whole response first, then adopt the project. Order matters.

    `frame.rail` imports and instantiates every plugin the workflow names, so a Workflow
    row naming a plugin that does not exist raises *after* the edit is applied. Storing
    first left the session holding a project no screen could render: `project.state`,
    `graph` and `step` all raised the same ModuleNotFoundError forever, and the client —
    which treats an error response as "nothing happened" — had no idea. One typo in a
    plugin name killed the session for good.

    Building the response first means a project that cannot be rendered is never
    adopted, and the caller keeps the one that works.
    """

    response = {
        'project': _summary(updated),
        'rail': frame.rail(updated),
        'graph': graph.build(updated),
        **extra,
    }
    _store(payload, updated)
    return response


def _position_text(position):
    '''A position as the file should carry it: `202`, not `202.0`.'''

    number = float(position)
    return str(int(number)) if number.is_integer() else str(round(number, 4))


def op_figures(payload):
    '''The figures a step can offer, with their data.

    A separate op rather than part of the step frame: an hourly calendar is 8,760
    numbers and a step frame is fetched on every keystroke-driven re-render. Figures
    are fetched once, when a step opens.
    '''

    opened = _session(payload)
    name = payload.get('step')
    if not name:
        raise ValueError('figures needs a "step" name')
    return {'figures': figures.for_step(opened, name)}


def op_step_effect(payload):
    '''Whether this step changes the answer, measured by removing it and re-running.

    A plugin only reaches the result through the steps that run *after* it. Add
    `Multiple_Modules_Plugin` at 650 and it writes `Fixed Operating Costs > Staff`
    exactly as documented — but Labor Operating Cost ran at 600 and has already turned
    Staff into a cost, so nothing reads the new value and the levelized cost does not
    move by a single digit. At 401, where pyH2A's own examples put it, eight modules
    take the same file from 5.83 to 4.68 USD/kg. The step is identical; only its
    position differs, and the app said nothing about the difference.

    Measured rather than inferred. Reading the declared inputs of later steps would be
    cheaper and wrong: `Discounted_Cash_Flow_Plugin` consumes whole table *groups* by
    membership, not by naming rows, so a "nobody declares this as an input" test would
    confidently call live steps inert. Removing the step and comparing the number is a
    fact about this file.

    Deferred like `figures`, and for the same reason: it costs a second full run, and no
    keystroke should wait on it.
    '''

    opened = _session(payload)
    name = payload.get('step')
    if not name:
        raise ValueError('step.effect needs a "step" name')
    if name not in opened.order():
        raise ValueError(f'{name} is not in this workflow')

    here = _cost_of(opened)
    if here is None:
        # A pathway that does not produce a number cannot be asked what it would lose.
        return {'effect': {'measurable': False, 'reason': 'the run does not reach a cost'}}

    document = copy.deepcopy(opened.document)
    workflow = document.get('Workflow')
    if workflow is None or name not in workflow.rows:
        return {'effect': {'measurable': False, 'reason': 'the step is not written in the file'}}
    del workflow.rows[name]

    try:
        without = opened.reopen(grammar.serialize_document(document))
    except Exception:  # noqa: BLE001 - a pathway that cannot run without it is telling
        return {'effect': {'inert': False, 'measurable': True, 'required': True}}

    gone = _cost_of(without)
    if gone is None:
        return {'effect': {'inert': False, 'measurable': True, 'required': True,
                           'failed': without.run.failed if without.run else None}}

    inert = abs(gone - here) <= abs(here) * 1e-12
    effect = {
        'inert': inert,
        'measurable': True,
        'required': False,
        'with': here,
        'without': gone,
        'unit': opened.run.result.levelized_cost.supplied_unit,
        'position': _position_in(opened, name),
    }
    if inert:
        effect['would_matter_at'] = _positions_that_bite(opened, name, here)
    return {'effect': effect}


def _positions_that_bite(opened, name, here):
    '''Insertion points where an inert step would change the answer. Measured.

    A step that writes a value already consumed by an earlier step is dead where it
    stands. Rather than infer a better home from declared inputs — which cannot see
    `Discounted_Cash_Flow_Plugin` eating whole table groups — this moves the step to each
    open position, re-runs, and keeps the ones where the cost differs. Bounded by the
    number of insertion points, so a seventeen-step pathway costs seventeen runs of a few
    milliseconds each, and only when the step is already known to be doing nothing.
    '''

    document = copy.deepcopy(opened.document)
    workflow = document.get('Workflow')
    original = workflow.rows[name].get('Position')
    found = []

    for candidate in graph.build(opened)['insertion_points']:
        position = candidate['position']
        if _position_text(position) == _position_text(original):
            continue
        workflow.rows[name]['Position'] = _position_text(position)
        try:
            moved = opened.reopen(grammar.serialize_document(document))
        except Exception:  # noqa: BLE001 - an unrunnable position is simply not offered
            continue
        cost = _cost_of(moved)
        if cost is not None and abs(cost - here) > abs(here) * 1e-12:
            found.append({'position': position, 'after': candidate['after'],
                          'before': candidate['before'], 'cost': cost})

    workflow.rows[name]['Position'] = original
    if not found:
        return None

    # Six rows all reading 4.6791 is a table nobody needs. What the reader wants is the
    # boundary: the step this one has to run before. It is the `before` of the last
    # position that still bites — every earlier slot works, every later slot is dead.
    return {
        'cost': found[-1]['cost'],
        'before': found[-1]['before'],
        'position': found[-1]['position'],
        'count': len(found),
    }


def _position_in(opened, name):
    '''The position a step is written at, or None.'''

    workflow = opened.document.get('Workflow')
    row = workflow.rows.get(name, {}) if workflow else {}
    return row.get('Position')


def op_series(payload):
    '''One cell's full, undecimated array — what a calendar of 8,760 hours draws.'''

    opened = _session(payload)
    for key in ('step', 'table', 'row', 'column'):
        if not payload.get(key):
            raise ValueError(f'series needs "{key}"')

    found = figures.series(
        opened, payload['step'],
        payload['table'], payload['row'], payload['column'],
        year=int(payload.get('year', 0)),
    )
    if found is None:
        raise ValueError(
            f'{payload["table"]} > {payload["row"]} > {payload["column"]} holds no array'
        )
    return {'series': found}


OPS = {
    'examples': op_examples,
    'project.open': op_project_open,
    'project.state': op_project_state,
    'project.source': op_project_source,
    'source.replace': op_source_replace,
    'step': op_step,
    'cell.edit': op_cell_edit,
    'reference.check': op_reference_check,
    'reference.search': op_reference_search,
    'graph': op_graph,
    'plugins': op_plugins,
    'workflow.add': op_workflow_add,
    'workflow.move': op_workflow_move,
    'workflow.remove': op_workflow_remove,
    'figures': op_figures,
    'step.effect': op_step_effect,
    'series': op_series,
}
