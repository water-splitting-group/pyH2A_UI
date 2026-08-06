'''The workflow as a graph: who feeds whom, where a step could go, and what could fill a gap.

The rail in the worksheet is this graph drawn narrow. It is not a picture of the
plugin *code* — the previous build drew that, boxes labelled `in 2 · out 7` with
Python dict paths on the edges, and it told a reader nothing about their plant. It is
a picture of the **values that actually moved**: an edge exists between two steps
because the later one reads a cell the earlier one wrote, and the edge carries the
names of those cells.

That distinction matters for a reason beyond taste. A declared dependency may never
fire, and an undeclared one may carry the whole model. These edges come from the
trace, so they are what happened.

Three things a reader can do here that a list cannot support:

**See what flows.** Hovering a step lights the cells arriving and leaving, by name.

**Add a step.** Between any two consecutive steps there is a position where a new
plugin can go. `insertion_points` names them and the position number to write.

**Be told what would help.** When a step declares a required input nothing supplies,
`suggestions` names the installed plugins whose declared outputs would satisfy it.
That is the difference between "this is missing" and "here is what provides it".
'''

from pyh2a_studio.core import engine, frame, project as project_module


def build(project):
    '''Nodes, edges, insertion points and suggestions for the whole workflow.

    Returns
    -------
    dict
        `nodes` in execution order, each with the rail's fields plus `reads` and
        `writes` counts. `edges` as `{from, to, cells, count}`. `insertion_points`
        as `{after, before, position}`. `unmet` lists required inputs nothing
        supplies, each with `suggestions`.
    '''

    if not project.run:
        return {'nodes': [], 'edges': [], 'insertion_points': [], 'unmet': []}

    nodes = frame.rail(project)
    order = [node['name'] for node in nodes]
    writer = project.first_writers()
    literals = project.run.literals

    edges = _edges(project, order, writer, literals)
    incoming = {name: 0 for name in order}
    outgoing = {name: 0 for name in order}
    for edge in edges:
        outgoing[edge['from']] += edge['count']
        incoming[edge['to']] += edge['count']

    for node in nodes:
        node['reads'] = incoming[node['name']]
        node['writes'] = outgoing[node['name']]

    return {
        'nodes': nodes,
        'edges': edges,
        'insertion_points': _insertion_points(nodes),
        'unmet': _unmet(project, order),
    }


def _edges(project, order, writer, literals):
    '''One edge per producer→consumer pair, carrying the cells that travel it.

    Only cells a consumer *declares* it reads are counted. The alternative — every
    cell visible to it — makes every step depend on every earlier step and draws a
    solid triangle, which is true and useless.
    '''

    index = {name: position for position, name in enumerate(order)}
    bundles = {}

    for name in order:
        for field in frame.fields_of(project, name):
            key = (field['table'], field['row'], field['column'])
            if key in literals or key not in writer:
                continue
            producer, _, producer_index = writer[key]
            if producer == name or producer_index >= index[name]:
                continue
            bundle = bundles.setdefault((producer, name), [])
            label = f'{field["table"]} › {field["row"]}'
            if label not in bundle:
                bundle.append(label)

    edges = [
        {'from': producer, 'to': consumer, 'cells': sorted(cells), 'count': len(cells)}
        for (producer, consumer), cells in bundles.items()
    ]
    edges.sort(key=lambda edge: (index[edge['from']], index[edge['to']]))
    return edges


def _insertion_points(nodes):
    '''Where a new step could go, and the position number it would carry.

    pyH2A orders a workflow by sorting the `Position` column, and `num()` parses that
    cell as a float — verified: a plugin at `201.5` sorts between 201 and 202 and the
    run is unaffected. So *every* gap is insertable, including the tight ones between
    consecutive integers, and no renumbering is ever forced on the user.

    Whole numbers where there is room, one decimal where there is not: `150` reads
    better than `150.0`, and `201.5` is self-explanatory next to its neighbours.
    '''

    points = []
    for index in range(len(nodes) + 1):
        before = nodes[index - 1]['position'] if index > 0 else None
        after = nodes[index]['position'] if index < len(nodes) else None
        points.append({
            'index': index,
            'after': nodes[index - 1]['name'] if index > 0 else None,
            'before': nodes[index]['name'] if index < len(nodes) else None,
            'position': _between(before, after),
        })
    return points


def _between(before, after):
    '''A position strictly between two others, as a clean number.'''

    if before is None:
        return max(1, float(after) - 100) if after is not None else 100
    if after is None:
        return float(before) + 100

    midpoint = (float(before) + float(after)) / 2
    return int(midpoint) if midpoint.is_integer() else round(midpoint, 4)


def _unmet(project, order):
    '''Required inputs nothing supplies, each with the plugins that would supply it.

    A missing input is only half a message. The other half — which of the twenty-two
    installed plugins declares that row as an output — is mechanical to compute and is
    the part that lets someone act.

    Two rules keep the answer from contradicting itself. **A step is never listed as a
    supplier of its own input**: `Solar_Concentrator` declares `Solar collection area` as
    both, which is a fact about the spec and not an instruction to add the step you have
    just added. And a suggested plugin that is **already in the workflow** is not
    something to add — if it runs later than the step that needs it, the fix is a
    position, so the entry says which one and lets the panel say so.
    '''

    supply = _supply_index(project.functional_unit())
    positions = {node: index for index, node in enumerate(order)}
    unmet = []
    for name in order:
        for field in frame.fields_of(project, name):
            if field['state'] != 'missing' or field['declared'].get('optional'):
                continue
            writers = [writer
                       for writer in sorted(supply.get((field['table'], field['row']), ()))
                       if writer != name]
            unmet.append({
                'step': name,
                'label': frame.label_of(name),
                'table': field['table'],
                'row': field['row'],
                'description': field['declared'].get('description', ''),
                'suggestions': [{'name': writer, 'label': frame.label_of(writer),
                                 'in_workflow': writer in positions}
                                for writer in writers],
                'runs_later': [frame.label_of(writer) for writer in writers
                               if positions.get(writer, -1) > positions[name]],
            })
    return unmet


_SUPPLY_CACHE = {}


def _supply_index(functional_unit_token):
    '''`{(table, row): [plugin, …]}` over every installed plugin's declared outputs.

    Twenty-two plugin imports, memoised for the process: the answer depends only on
    what is installed.
    '''

    if functional_unit_token in _SUPPLY_CACHE:
        return _SUPPLY_CACHE[functional_unit_token]

    index = {}
    for name in engine.installed_plugins():
        try:
            _, declared_out = project_module.spec(name, functional_unit_token)
        except (ImportError, AttributeError, TypeError, ValueError, KeyError):
            continue
        for table, rows in declared_out.items():
            for row in rows:
                index.setdefault((table, row), []).append(name)

    _SUPPLY_CACHE[functional_unit_token] = index
    return index


def catalogue(project):
    '''Every installed plugin, with what it needs and makes, and whether it is in use.

    The chooser behind "add a step". Sorted so the plugins that could consume what
    this workflow already produces come first — a reader adding a step is usually
    extending the chain they can see, not starting a new one.
    '''

    in_use = set(project.order()) if project.run else set()
    available = set(project.run.steps[-1].visible) if project.run else set()
    available_rows = {(table, row) for table, row, _ in available}
    token = project.functional_unit()

    entries = []
    for name in engine.installed_plugins():
        try:
            declared_in, declared_out = project_module.spec(name, token)
            summary, _ = project_module.spec_meta(name)
        except (ImportError, AttributeError, TypeError, ValueError, KeyError) as error:
            entries.append({'name': name, 'label': frame.label_of(name),
                            'error': f'{error.__class__.__name__}: {error}'})
            continue

        needs = [(table, row) for table, rows in declared_in.items() for row in rows]
        makes = [(table, row) for table, rows in declared_out.items() for row in rows]
        satisfied = sum(1 for pair in needs if pair in available_rows)

        entries.append({
            'name': name,
            'label': frame.label_of(name),
            'family': frame.family_of(name),
            'summary': summary,
            'in_use': name in in_use,
            'needs': len(needs),
            'satisfied': satisfied,
            'makes': [f'{table} › {row}' for table, row in makes[:6]],
            'makes_count': len(makes),
        })

    entries.sort(key=lambda entry: (
        entry.get('in_use', False),
        -(entry.get('satisfied', 0) / max(entry.get('needs', 1), 1)),
        entry['label'],
    ))
    return entries
