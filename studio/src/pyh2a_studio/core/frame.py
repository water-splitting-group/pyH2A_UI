'''The view model for one step: what it needs, what it can see, what it makes.

This is the module the worksheet is a rendering of. It answers, for a single step
in the workflow, the three questions that make a pipeline steppable:

**What does this step need?** Its plugin declares the tables and rows it reads,
and — since the refactor — each field's bounds, physical dimension, whether it is
optional, and a sentence describing it. Joined against the file, that gives an
editable form where every field carries its own meaning and its own valid range,
with no lookup table maintained by hand.

**What can it see?** Everything earlier steps wrote, plus every value authored in
the file. The second half matters as much as the first: file values are in scope
at every position, which is what makes them referenceable from anywhere. Cells are
grouped by *when* they arrived, because that is the axis a user reasons along when
deciding whether a reference will resolve.

**What does it make?** The cells it actually wrote, compared against the cells it
declared it would write. Those differ — plugins write more than they declare, and
the audit found declarations that promise rows the code never produces. Showing
both is the only honest option.

Every field also carries its problems, found before the engine runs: a reference
that will not resolve, a value outside its declared bounds, a unit whose dimension
disagrees with the declaration. The engine reports none of these as errors — it
substitutes, converts, and returns a number — so if this module does not catch
them, nothing does.
'''

from pyh2a_studio.core import cells, engine, project as project_module, refs

FAMILIES = {
    'framework': ('Time', 'Inflation', 'Financial', 'Discounted_Cash_Flow'),
    'solar': ('Hourly_Irradiation', 'Photovoltaic', 'Solar', 'Irradiation'),
    'conversion': ('Electrolyzer', 'PEC', 'Photocatalytic', 'Thermal', 'Production'),
    'storage': ('Battery', 'Stored_Power', 'Power_Management'),
    'water': ('Reverse_Osmosis', 'Desalination'),
    'cost': ('Capital_Cost', 'Replacement', 'Labor', 'Operating', 'Utilities'),
    'scale': ('Multiple_Modules',),
}
'''Plugin name fragments to colour families. Colour groups the plant's *parts*, so
a reader can find the solar chain or the money without reading names. Matched on
substrings because plugin names are stable in their nouns, not their suffixes.'''

_DISPLAY_STRIP = ('_Plugin',)


def family_of(plugin_name):
    '''The colour family for a plugin, or `'other'`.'''

    for family, fragments in FAMILIES.items():
        if any(fragment in plugin_name for fragment in fragments):
            return family
    return 'other'


def label_of(plugin_name):
    '''A plugin name as a person would write it: `Electrolyzer_Plugin` → `Electrolyzer`.'''

    label = plugin_name.split('/')[-1]
    for suffix in _DISPLAY_STRIP:
        if label.endswith(suffix):
            label = label[: -len(suffix)]
    return label.replace('_', ' ').strip()


def rail(project):
    '''Every step as a row for the workflow rail.

    Carries what the rail must show without a second request: position, status,
    timing, family, and the count of fields still needing attention — so the rail
    can mark a step that will fail before the user opens it.
    '''

    if not project.run:
        return []

    entries = []
    for index, step in enumerate(project.run.steps):
        problems = _step_problem_count(project, step)
        entries.append({
            'name': step.name,
            'label': label_of(step.name),
            'position': step.position,
            'index': index,
            'family': family_of(step.name),
            'status': step.status,
            'duration_ms': round(step.duration_ms, 3),
            'wrote': len(step.wrote),
            'problems': problems,
        })
    return entries


def _step_problem_count(project, step):
    '''How many fields of this step have a problem the user must resolve.'''

    fields = _fields_for(project, step.name)
    return sum(1 for field in fields if field['problems'])


def build(project, step_name):
    '''The whole frame for one step.

    Raises
    ------
    KeyError
        When `step_name` is not in the workflow, listing what is.
    '''

    step = project.run.step(step_name) if project.run else None
    if step is None:
        raise KeyError(f'"{step_name}" is not a step in this workflow — '
                       f'have: {", ".join(project.order())}')

    summary, docstring = project_module.spec_meta(step_name)
    _, declared_out = project_module.spec(step_name, project.functional_unit())
    order = project.order()

    return {
        'step': {
            'name': step.name,
            'label': label_of(step.name),
            'position': step.position,
            'index': order.index(step_name),
            'total': len(order),
            'family': family_of(step.name),
            'status': step.status,
            'duration_ms': round(step.duration_ms, 3),
            'summary': summary,
            'docstring': docstring,
            'error': step.error,
            'error_type': step.error_type,
            'warnings': step.warnings,
            # Nine of a blank plant's steps come from Defaults_TEA.md, so there is no
            # Workflow row to delete and "remove step" could only ever fail. The panel
            # offered it anyway and explained itself after the click.
            'in_file': step_name in getattr(
                project.document.get('Workflow'), 'rows', {}),
        },
        'needs': _needs(project, step_name),
        'produces': _produces(step, declared_out, project.run.literals),
        'scope': scope(project, step_name),
    }


def _needs(project, step_name):
    '''The step's declared inputs as editable tables.'''

    fields = _fields_for(project, step_name)
    tables = {}
    for field in fields:
        tables.setdefault(field['table'], []).append(field)

    return [
        {
            'table': table,
            'fields': table_fields,
            'to_enter': sum(1 for f in table_fields if f['state'] != 'computed'),
            'problems': sum(1 for f in table_fields if f['problems']),
        }
        for table, table_fields in tables.items()
    ]


def fields_of(project, step_name):
    '''A step's declared input fields, joined to the file and to live state.

    Public because the graph needs the same join to work out who feeds whom. Cached on
    the project: the rail asks for every step's problem count, the graph asks again for
    every step's edges, and `build` asks a third time for the open one.
    '''

    return _fields_for(project, step_name)


def _fields_for(project, step_name):
    '''One record per declared input field, joined to the file and to live state.

    Cached on the project because `rail` asks for every step's problem count and
    `build` then asks again for the open one; recomputing means re-walking the whole
    declaration set seventeen times per render.
    '''

    cache = project.field_cache
    if step_name not in cache:
        cache[step_name] = _compute_fields(project, step_name)
    return cache[step_name]


WILDCARD = '<...>'
SPECIAL_ROWS = frozenset({'sum_tables'})
ENGINE_PREFIXES = ('Former ',)
'''`Former Value` is the engine's record of what a cell held before its `Path`
multiplied it, and for a multi-quantity row it writes prefixed variants — `Former
Cost_Value`, `Former Frequency_Value`. Matching the exact string missed those, so two
cells on PV+E were offered as bindable, one of them holding a reference string: binding
it gives you a pointer to a pointer, which is the exact thing this filter exists to
prevent.'''

ENGINE_COLUMNS = frozenset({'Processed', 'Former Value', 'Comment'})
PRODUCED_HIDDEN = ENGINE_COLUMNS | {'Unit', 'Path'}
'''Columns that are never a step's *output*. `Unit` and `Path` are authored
annotations on a value; they change when a table is processed, so they land in the
diff, but listing them as things the step made is wrong and noisy.'''
SCOPE_HIDDEN = ENGINE_COLUMNS | {'Unit', 'Path'}
'''Also hidden from the scope panel: a `Path` cell holds a reference *to* a value,
not a value. Offering `{… > Stored energy (daily) > Path, -}` as something to bind
gives you a pointer to a pointer, and most of them read `None`.'''
'''Columns the engine writes as bookkeeping, never offered as form fields.
`Processed` marks a table as resolved. `Former Value` records what a cell held before
its `Path` multiplied it — genuinely informative, and shown as evidence beside the
result, but not a thing anyone edits.'''
'''`<...>` is what a spec writes where any name will do, and it means two different
things depending on where it appears — both mirrored below from the engine's own
resolver (`Utilities/IO/input_resolver.py`), never guessed at.

In a **table** key it names a *group*: `'<...> Direct Capital Cost <...>'` selects
`Direct Capital Costs - PV`, `- Battery`, `- Electrolyzer` and any other the file
adds. The engine strips the markers, strips whitespace, and tests plain substring
containment — which is looser than a glob, and matters: an anchored pattern misses
the shipped tables entirely, because the spec says "Cost" where the files say
"Costs".

In a **row** key it means *every row of the table*, with no name matching at all.
`Construction > '<...>'` is "each construction year is a fraction between 0 and 1".

`sum_tables` is engine bookkeeping inside a spec, not a row anyone authors.'''


def is_engine_column(column, hidden=ENGINE_COLUMNS):
    '''True for a column the engine keeps for itself rather than one a user reads.'''

    return column in hidden or column.startswith(ENGINE_PREFIXES)


def _matching_tables(pattern, names):
    '''Tables a spec key selects. Mirrors `resolve_table_group`.

    A literal that matches nothing still comes back, because a declared table the
    file does not have is a real missing input the user needs to see. A *wildcard*
    that matches nothing correctly yields nothing — there is no field to show.
    '''

    if WILDCARD not in pattern:
        return [pattern]
    needle = pattern.replace(WILDCARD, '').strip()
    return [name for name in names if needle in name]


def _matching_rows(pattern, row_names):
    '''Rows a spec key selects: itself, or all of them.'''

    if pattern in SPECIAL_ROWS:
        return []
    if WILDCARD not in pattern:
        return [pattern]
    return list(row_names)


def _compute_fields(project, step_name):
    declared_in, _ = project_module.spec(step_name, project.functional_unit())
    visible = project.available_at(step_name)
    step = project.run.step(step_name) if project.run else None
    context = {
        'visible': visible,
        # A step's own writes count as available to it. `Capital_Cost` sums
        # `Direct Capital Costs - Gas Processing` and then reads that sum for
        # `Installation Costs`, inside one step; the plugin orders its own work and
        # four shipped pathways depend on it. Excluding them reports those files as
        # containing six dangling references.
        'available': project.visible_to(step_name),
        'later': project.produced_later(step_name),
        'origins': project.origins,
        # A step skipped because an earlier one failed has no honest view of the
        # world: the values it would have been given were never computed. Checks
        # that depend on that view are suppressed for it — otherwise one broken step
        # reports as thirteen, burying the error that actually matters. Checks that
        # read only the file (bounds, dimensions, reference syntax) still run, because
        # the text is right there and is just as wrong as it would have been.
        'evaluated': step is None or step.status != 'skipped',
        # What each cell became once this step ran. A row with a `Path` is a
        # *product* — the engine multiplies its `Value` by whatever the path resolves
        # to — and that product does not exist until the step executes. Showing only
        # the pre-step state renders `Electrolyzer CAPEX` as 784 USD when the engine
        # holds 4,312,000; showing only the post-step state hides the 784 the user
        # typed. Both are carried so the row can be drawn as the equation it is.
        'after': step.wrote if step else {},
    }
    effective = project.effective

    fields = []
    for table_pattern, rows in declared_in.items():
        for table_name in _matching_tables(table_pattern, effective):
            table = effective.get(table_name)
            for row_pattern, declaration in rows.items():
                for row_name in _matching_rows(row_pattern, table.rows if table else {}):
                    row = table.rows.get(row_name, {}) if table else {}
                    fields.extend(_row_fields(table_name, row_name, row, declaration,
                                              context))
    return fields


def _row_fields(table_name, row_name, row, declaration, context):
    '''Every editable field a single row contributes.

    A row absent from every file is not necessarily missing: it is usually *computed*,
    written by an earlier step, and its columns are whatever that step chose to write.
    `Electrolyzer > Yearly operation data` carries `Year_Value`, `Production_Value`
    and `Duration_Value` and no bare `Value` at all — assuming the bare pair reports a
    satisfied input as missing, which is a false alarm on a value the user cannot
    supply and should not be asked to.
    '''

    columns = list(row) or _visible_columns(table_name, row_name, context)
    groups = refs.column_groups(columns) if columns else [
        {'name': '', 'value': refs.BARE_VALUE, 'unit': refs.BARE_UNIT, 'path': None}
    ]
    return [
        _one_field(table_name, row_name, group, row, declaration, context)
        for group in groups
        if not is_engine_column(group['value'])
    ]


def _visible_columns(table_name, row_name, context):
    '''Columns a computed row actually has at this point in the run.'''

    return [key[2] for key in context['visible']
            if key[0] == table_name and key[1] == row_name
            and not is_engine_column(key[2])]


def _one_field(table_name, row_name, group, row, declaration, context):
    '''One editable field: its text, its declaration, its live value, its problems.'''

    value_column = group['value']
    text = row.get(value_column)
    unit_text = row.get(group['unit']) if group['unit'] else None
    path_text = row.get(group['path']) if group['path'] else None

    live = context['visible'].get((table_name, row_name, value_column), {'form': 'absent'})
    after = context['after'].get((table_name, row_name, value_column))
    declared = _declaration_of(declaration, value_column)

    field = {
        'table': table_name,
        'row': row_name,
        'column': value_column,
        'label': _label_for(group, row_name),
        'text': text,
        'origin': context['origins'].get((table_name, row_name, value_column)),
        'unit': {'column': group['unit'], 'text': unit_text},
        'path': _path_of(group, path_text, context),
        'declared': declared,
        'live': live,
        'after': after,
        'is_reference': refs.looks_like_reference(text),
        'state': _state_of(text, live),
    }
    if not context['evaluated']:
        field['state'] = 'unevaluated'
    field['bounds_shown'] = _bounds_shown(declared.get('bounds'), text, unit_text,
                                          declared.get('dimension'))
    field['problems'] = _problems(field, context['available'], context['later'],
                                  context['evaluated'])
    return field


def _bounds_shown(bounds, text, unit_text, dimension=None):
    '''The declared range, written the way the field itself is written.

    Bounds are declared in SI base units. A field is displayed as the user typed it.
    Print the two side by side and they contradict each other: `Temperature coefficient`
    shows `-0.4%` above `range -0.5 … 0.5`, and `Minimum capacity` shows `10%` above
    `range 0 … 1`. Six fields on the shipped files display a value apparently outside
    their own stated range, which teaches a reader that the range annotation is noise.

    Two conversions, in order. The unit, when the authored one differs from the base —
    `deg` against bounds in radians becomes `0 … 180`. Then percent, when the cell is
    written as one, so `0 … 1` becomes `0% … 100%` beside a field reading `10%`.

    Returns `(low, high, suffix)` with either end None for an open bound, or None when
    there is nothing worth stating.
    '''

    if not bounds:
        return None

    low, high = _converted(bounds[0], unit_text), _converted(bounds[1], unit_text)

    percent = isinstance(text, str) and text.strip().endswith('%')
    if percent:
        low = None if low is None else low * 100
        high = None if high is None else high * 100

    shown = {'low': low, 'high': high, 'percent': percent}
    if unit_text and unit_text.strip() not in ('', '-'):
        return shown

    # No authored unit means nothing to convert into, so the numbers are the base
    # unit's — and saying which one matters. `Module tilt` printing `0 … 1.57` two rows
    # above `Array azimuth`'s `0 … 180` is two angle fields in two unit systems with
    # only one of them labelled.
    base = engine.dimension_base_unit(dimension)
    if base and base != '-':
        # `-` is the engine's token for "no unit", so there is nothing to label with.
        shown['unit'] = base
    return shown


def _converted(bound, unit_text):
    '''One bound in the field's authored unit.

    Each bound is converted on its own rather than scaled by a common factor, because
    not every unit is a ratio. Temperature is affine: `convert(1, 'K', 'degC')` is
    -272.15, so scaling by it turned declared bounds of `[250, 500] K` into
    `-68 038 … -136 075` — negative, out of order, and five orders of magnitude wrong,
    directly under a field reading `45`. Converting the ends gives `-23.15 … 226.85`.
    '''

    if bound is None:
        return None
    if not unit_text or unit_text.strip() in ('', '-'):
        return bound
    base = engine.base_unit(unit_text)
    if not base or base == unit_text.strip():
        return bound
    converted = engine.convert(float(bound), base, unit_text.strip())
    return bound if converted is None else converted


BARE_COLUMNS = frozenset({'Value', 'Unit', 'Path'})


def _label_for(group, row_name):
    '''What to call a field on screen.

    `column_groups` names a group after its prefix, and an *unprefixed* column that
    never found a `Unit` partner becomes a group named after itself. For a row the
    file authored that is right — `Comment` should read "Comment". For a computed row,
    whose columns are discovered from the engine's own state, it produces a field
    labelled `Value` under a table heading, which tells the reader nothing: the name
    they need is the row's.

    A row carrying several quantities needs both. `# Utilities` holds
    `Electricity | 50 | 1/kg | 0.07 | USD | 1. | -`, one row with three groups, and
    labelling them `Usage`, `Cost` and `Price_Conversion_Factor` dropped the word
    Electricity from the screen entirely. Clicking `Electricity` in the start-here band
    landed on a field reading `Usage`, and a newcomer meaning to change the electricity
    price changed its consumption instead — 5.9070 to 2.3524 USD/kg, in the right table,
    on the wrong row. Two utilities in one file would have been indistinguishable.
    '''

    if not group['name'] or group['name'] in BARE_COLUMNS:
        return row_name
    return f'{row_name} · {group["name"].replace("_", " ")}'


def _path_of(group, path_text, context, effective=None):
    '''A field's path column, and what the path currently points at.

    Resolving the target here rather than in the browser keeps one rule in one place:
    the studio reads the value the engine holds at *this position in the run*, which
    for a forward reference is nothing at all. A client that fetched the target itself
    would have to re-implement scope to get that right.
    '''

    entry = {'column': group['path'], 'text': path_text, 'target': None}
    if not path_text or path_text.strip() in refs.NO_PATH:
        return entry

    parsed = refs.parse(path_text)
    if 'path' not in parsed:
        return entry

    target = context['visible'].get(parsed['path'])
    entry['target'] = target
    entry['requested_unit'] = parsed['unit']
    if target:
        entry['as_requested'] = _in_requested(target, parsed, context)
    return entry


def _in_requested(target, parsed, context):
    '''The multiplicand, expressed in the unit the reference asked for.

    Two shapes, because a cell changes shape mid-run. Once its own plugin has processed
    the table it is a `Quantity` and carries its own base pair. Before that — which is
    the common case, since a path usually points at a value some *later* step will
    process — it is the plain number the parser produced, and the unit is sitting in the
    `Unit` cell of the same row.

    Reading only the first shape printed the literal word `unresolved` where step 202's
    multiplicand belongs, on a row whose own product proves the value: 8,250 / 1.5 =
    5,500 kW.
    '''

    direct = engine.convert(target.get('base_value'), target.get('base_unit'),
                            parsed['unit'])
    if direct is not None:
        return direct

    magnitude = cells.magnitude(target)
    if magnitude is None:
        return None

    table, row, _ = parsed['path']
    unit_record = context['visible'].get((table, row, 'Unit')) or {}
    authored = unit_record.get('text') or unit_record.get('unit')
    if not authored:
        return magnitude if parsed['unit'] in ('-', '') else None
    return engine.convert(engine.base_magnitude(magnitude, authored),
                          engine.base_unit(authored), parsed['unit'])


def _declaration_of(declaration, value_column):
    '''The declared metadata for one column of a row's spec.

    A spec keyed `Year_Value` / `Production_Value` describes several columns of one
    row; a spec keyed `Value` describes the bare pair. Look for the exact column
    first, then fall back to `Value`, which is what single-quantity rows use.
    '''

    if not isinstance(declaration, dict):
        return {}

    entry = declaration.get(value_column) or declaration.get(refs.BARE_VALUE) or {}
    bounds = entry.get('bounds') if isinstance(entry, dict) else None
    unit_spec = declaration.get(refs.BARE_UNIT)
    dimension = unit_spec.get('dimension') if isinstance(unit_spec, dict) else None
    if dimension is None and isinstance(entry, dict):
        dimension = entry.get('dimension')

    return {
        'bounds': list(bounds) if bounds and any(bound is not None for bound in bounds) else None,
        'dimension': dimension,
        'optional': bool(declaration.get('optional', False)),
        'description': _prose(declaration.get('description')),
        'types': _type_names(entry.get('type') if isinstance(entry, dict) else None),
    }


def _prose(text):
    '''A docstring sentence as prose: collapsed, and without its markup.

    Plugin descriptions are written for Sphinx, so some carry reST backticks — step
    201's `File` renders as ``Path to a `.csv` file containing hourly irradiance data``.
    A user surface that shows the markup is showing the author's tooling.
    '''

    collapsed = ' '.join((text or '').split())
    return collapsed.replace('``', '').replace('`', '')


def _type_names(types):
    '''Declared Python types as readable names.

    Specs carry these as a `set` of classes, whose `repr` is
    `"{<class 'int'>, <class 'float'>}"` — unusable on screen and not JSON-safe.
    '''

    if not types:
        return []
    if isinstance(types, (set, frozenset, list, tuple)):
        return sorted(getattr(entry, '__name__', str(entry)) for entry in types)
    return [getattr(types, '__name__', str(types))]


def _state_of(text, live):
    '''Whether a field is authored, missing, or computed elsewhere.

    `'computed'` is the case worth naming: the plugin declares it needs this row,
    but the row is produced by an earlier step rather than written in a file. It is
    an input to this step and not a thing the user should be invited to type over,
    so it renders as evidence rather than as a form field.

    `None` and `''` are different facts and used to be one. `None` means there is no
    cell here at all, so a value the engine holds came from somewhere upstream. `''`
    means a cell exists and is empty — the user's own blank, which the app itself writes
    when it creates a row it cannot fully populate. Treating those as computed rendered
    them dark and uneditable: creating `Utilities > Cooling water` with a cost produced
    two blank cells the run needed and the reader could not type into.
    '''

    if text is None:
        return 'computed' if live.get('form') != 'absent' else 'missing'
    return 'missing' if not text.strip() else 'authored'


def _problems(field, available, later, evaluated=True):
    '''Everything wrong with a field, in words, before the engine runs.

    `evaluated` false means the step never ran, so `available` describes a world that
    was never reached. Resolution and presence cannot be judged against it; bounds and
    dimensions can, because they are properties of the text.
    '''

    problems = []
    _check_type(field, problems)
    _check_scalar(field, problems)
    _check_bounds(field, problems)
    _check_dimension(field, problems)
    if evaluated:
        _check_path(field, available, later, problems)
        _check_value_reference(field, available, later, problems)
        _check_required(field, problems)
    return problems


def _check_path(field, available, later, problems):
    text = field['path']['text']
    if not text or text.strip() in refs.NO_PATH:
        return
    verdict = refs.check(text, available, later)
    if verdict['status'] != 'ok':
        problems.append({'kind': f'path-{verdict["status"]}', 'where': 'path',
                         'message': verdict['message'], 'near': verdict.get('near', [])})


def _check_value_reference(field, available, later, problems):
    if not field['is_reference']:
        return
    verdict = refs.check(field['text'], available, later)
    if verdict['status'] != 'ok':
        problems.append({'kind': f'value-{verdict["status"]}', 'where': 'value',
                         'message': verdict['message'], 'near': verdict.get('near', [])})


NUMERIC_TYPES = frozenset({'int', 'float', 'ndarray'})

SCALAR_TYPES = frozenset({'int', 'float'})
'''What a reader can type and have the engine accept as a plain number. `ndarray` is
numeric but nobody types one, which is exactly the distinction `_check_scalar` needs and
`_check_type` does not.'''


def _check_scalar(field, problems):
    '''Refuse a bare number in a field that cannot hold one.

    The mirror of `_check_type`, and it exists for the same reason: without it the
    engine fails somewhere else with a message about types. Typing `1` into
    `Hourly Irradiation > File` — declared `str`, described as "Path to a .csv file" —
    got as far as the run before dying, and `Battery > Available energy (daily)`,
    declared `dict`, is not something anyone types at all: it is written by an earlier
    step, and the honest advice is to make that step run rather than to fill the cell.

    Fields whose declared types include `int` or `float` are left alone, so every
    ordinary numeric cell is untouched by this.
    '''

    text = (field['text'] or '').strip()
    types = set(field['declared'].get('types') or ())
    if not text or field['is_reference'] or not types or types & SCALAR_TYPES:
        return
    if engine.parse_number(text) is None:
        return

    wants = ('a path or a name' if types == {'str'}
             else 'a value an earlier step writes' if not types & {'str'}
             else 'a path, or a value an earlier step writes')
    problems.append({
        'kind': 'not-a-scalar', 'where': 'value',
        'message': f'this field takes {wants}, not the number {text} '
                   f'(declared {" or ".join(sorted(types))})',
    })


def _check_type(field, problems):
    '''Refuse text in a field the plugin declares as a number.

    This check exists because of one observed failure and it is the sharpest argument
    in the studio for validating at the field. Type `banana` into
    `Electrolyzer > Nominal power` — a cell belonging to step 203 — and the engine
    fails at step **202**, `Photovoltaic_Plugin`, with
    `can't multiply sequence by non-int of type 'float'`. Photovoltaic does not read
    that cell and has nothing to do with the mistake: paths are resolved lazily, so
    whichever plugin first touches a reference to a broken cell inherits the blame.

    A user handed that message goes looking in the wrong table, in the wrong step, for
    a fault that is one row away in plain sight. Naming the field is the entire value
    added here.

    Only fields whose declared types are *all* numeric are checked. Plenty of cells
    hold strings on purpose — file paths, categoricals — and a reference is text that
    resolves to a number, so both are left alone.
    '''

    text = field['text']
    types = set(field['declared'].get('types') or ())
    if not text or field['is_reference'] or not types or not types <= NUMERIC_TYPES:
        return
    if engine.parse_number(text) is None:
        problems.append({
            'kind': 'not-a-number', 'where': 'value',
            'message': f'"{text}" is not a number, and this field is declared '
                       f'{" or ".join(sorted(types))}',
        })


def _check_bounds(field, problems):
    '''Compare the value against the plugin's declared bounds, in SI base units.

    **Bounds are declared in base units, and display is in authored units.** The two
    conventions are opposite and both are right. `Array azimuth` is declared
    `[0, 3.14159]` — radians — while the file says `180 deg`; `Nominal operating
    temperature` is declared `[250, 500]` — kelvin — while the file says `45 degC`.
    Comparing the authored magnitude against those bounds reports both shipped
    reference files as out of range, which is how this rule was found.

    So: validate the base pair, show the authored pair. A field with no unit has no
    base to convert to and its two magnitudes coincide, which is why plain numbers
    need no special case.
    '''

    bounds = field['declared'].get('bounds')
    if not bounds:
        return
    magnitude, base_unit = _base_of(field)
    if magnitude is None:
        return

    low, high = bounds[0], bounds[1]
    shown = f'{_short(magnitude)}{" " + base_unit if base_unit not in ("", "-") else ""}'
    if low is not None and magnitude < low:
        problems.append({
            'kind': 'below-bounds', 'where': 'value',
            'message': f'{shown} is below the declared minimum of {_short(low)}',
        })
    if high is not None and magnitude > high:
        problems.append({
            'kind': 'above-bounds', 'where': 'value',
            'message': f'{shown} is above the declared maximum of {_short(high)}',
        })


def _base_of(field):
    '''The field's magnitude in SI base units, and that unit's name.

    Two sources, because a cell changes shape mid-run. Once its own plugin has
    processed the table the cell is a `Quantity` carrying its own base pair. Before
    that — which is exactly when this check runs, since a step's inputs are validated
    before the step executes — it is still the plain number the parser produced, and
    the conversion has to be done here from the authored unit.
    '''

    live = field['live']
    if 'base_value' in live:
        return live['base_value'], live.get('base_unit') or ''

    # Before its own step processes the table — and for a step that never ran at all —
    # the cell is still the text the user typed. Read it the way the engine will.
    magnitude = cells.magnitude(live)
    if magnitude is None:
        magnitude = engine.parse_number(field['text'])
    unit_text = field['unit']['text']
    converted = engine.base_magnitude(magnitude, unit_text)
    if converted is None:
        return magnitude, ''
    return converted, engine.base_unit(unit_text)


def _check_dimension(field, problems):
    '''Compare the authored unit's dimension against the declared one.

    The engine converts whatever it can and returns a number, so a field declared
    `power` holding a mass is a wrong answer rather than a failure. Comparing
    dimensions catches it; comparing unit *strings* would not, since `kW`, `MW` and
    `W` are all correct for `power`.

    `-` on a *filled authored* cell is checked rather than skipped. It used to return
    early, which made the one token the app falls back to when it cannot find a
    declaration the one token the validator would not look at: a created cost row written
    `Compressor | 250000 | -` stopped the run on a dimension mismatch and showed no
    problem at the field.

    Two exclusions, both necessary. A computed field has no unit column at all — its unit
    lives in the engine's record, not in the file — and a row that does not exist yet has
    an empty one; flagging either produced 82 accusations against the five shipped
    pathways, every one of them wrong.
    '''

    declared = field['declared'].get('dimension')
    unit_text = field['unit']['text']
    if not declared:
        return

    bare = (unit_text or '').strip()
    if bare in ('', '-'):
        authored_cell = field['unit']['column'] and field['text']
        if authored_cell and _dimension_key(declared) != _dimension_key('dimensionless'):
            problems.append({
                'kind': 'wrong-dimension', 'where': 'unit',
                'message': f'this field is declared {declared} and its unit cell is '
                           f'{"empty" if not bare else "a dash"}, which the engine reads '
                           f'as dimensionless',
            })
        return

    actual = engine.unit_dimension(unit_text)
    if actual is None:
        problems.append({'kind': 'unknown-unit', 'where': 'unit',
                         'message': f'the engine does not recognise the unit "{unit_text}"'})
        return
    if _dimension_key(actual) != _dimension_key(declared):
        problems.append({
            'kind': 'wrong-dimension', 'where': 'unit',
            'message': f'"{unit_text}" is {actual}, but this field is declared {declared}',
        })


def _dimension_key(dimension):
    '''A dimension string with its spacing normalised.

    A spec writes `1/temperature_diff`; the engine's own `Quantity.dimension` renders
    the same thing as `1 / temperature_diff`. Comparing them raw reports the shipped
    file as wrong.
    '''

    return ''.join((dimension or '').split())


def _check_required(field, problems):
    if field['state'] == 'missing' and not field['declared'].get('optional', True):
        problems.append({'kind': 'missing', 'where': 'value',
                         'message': 'required, and neither this file nor its defaults supply it'})


def _short(number):
    '''A number for a sentence: no trailing zeros, no scientific notation for sane sizes.'''

    if number == int(number) and abs(number) < 1e15:
        return f'{int(number):,}'
    return f'{number:.6g}'


def _produces(step, declared_out, literals):
    '''What the step wrote — and whether it *made* the value or merely processed it.

    A plugin's first act is usually to process its own input tables, converting the
    file's plain numbers into `Quantity` objects. Those cells change, so they appear
    in the diff, but calling them output is wrong twice over: the user wrote them, and
    listing them buries the two or three values the step genuinely computed under a
    dozen that were already on screen in the panel above.

    `kind` separates the two. `'made'` is a cell that did not exist before this step;
    `'processed'` is one that did. Only `'made'` counts toward the headline.

    `declared` marks the ones the plugin's `output_dict` promised. Its absence is
    informative in both directions: a made-but-undeclared cell is a spec that
    understates the plugin, and a declared-but-absent row is a promise the code does
    not keep — the audit found both.
    '''

    declared_rows = {
        (table, row): (spec_entry.get('description') or '').strip()
        for table, rows in declared_out.items()
        for row, spec_entry in rows.items()
        if isinstance(spec_entry, dict)
    }

    units = {(table, row): record.get('text')
             for (table, row, column), record in step.wrote.items()
             if column == 'Unit'}

    tables = {}
    made = 0
    for (table, row, column), record in step.wrote.items():
        if is_engine_column(column, PRODUCED_HIDDEN):
            continue
        kind = 'processed' if (table, row, column) in literals else 'made'
        made += kind == 'made'
        tables.setdefault(table, []).append({
            'row': row,
            'column': column,
            'record': record,
            'unit': units.get((table, row)),
            'kind': kind,
            'declared': (table, row) in declared_rows,
            'description': ' '.join(declared_rows.get((table, row), '').split()),
        })


    for rows in tables.values():
        rows.sort(key=lambda row: (row['kind'] != 'made', row['row'], row['column']))
        # A row split across several value columns — `Yearly operation data` carries
        # Year, Production and Duration — shares one declaration. Repeating its
        # sentence under each turns three lines into twelve and reads as a bug. Run
        # after the sort, so the sentence stays with the row the reader sees first.
        seen = set()
        for row in rows:
            if row['row'] in seen:
                row['description'] = ''
            seen.add(row['row'])

    written = {(table, row) for table, row, _ in step.wrote}
    unkept = [
        {'table': table, 'row': row, 'description': ' '.join(description.split())}
        for (table, row), description in declared_rows.items()
        if (table, row) not in written
    ]

    table_list = [{'table': table, 'rows': rows} for table, rows in tables.items()]
    table_list.sort(key=lambda entry: (not any(row['kind'] == 'made' for row in entry['rows']),
                                       entry['table']))
    return {
        'tables': table_list,
        'count': made,
        'processed': sum(1 for rows in tables.values() for row in rows
                         if row['kind'] == 'processed'),
        'declared_but_absent': unkept,
    }


def scope(project, step_name):
    '''Everything referenceable at this step, grouped by when it arrived.

    Two levels, because one is unusable. The outer level is *when*: this step's own
    tables, then each upstream step most-recent-first, then the file's own values.
    That is the axis a user reasons along when asking whether a reference will
    resolve. The inner level is *which table*, because the file group alone holds 144
    cells in a bundled pathway and a flat list of 144 is a wall.

    Tables the open step actually declares as inputs are marked `reads`, so a screen
    can float them without a second lookup — those are the rows most likely to be
    examined while this step is open.

    `pending` is the counterpart: cells that will exist, badged with the position
    that creates them. A reference into that set is early rather than broken, and the
    engine would silently read 1 — so it has to be visible, not omitted.
    '''

    if not project.run:
        return {'groups': [], 'total': 0, 'later': 0, 'pending': []}

    order = project.order()
    index = order.index(step_name)
    visible = project.available_at(step_name)
    writer = project.first_writers()
    literals = project.run.literals
    reads = {field['table'] for field in _fields_for(project, step_name)}

    buckets = {}
    units = {(key[0], key[1]): record.get('text') or record.get('unit')
             for key, record in visible.items() if key[2] == 'Unit'}

    for key, record in visible.items():
        # A `Unit` cell is not a value anyone references — it annotates the `Value`
        # beside it. Listing both doubles the panel and offers a reference that
        # resolves to the string "kW". The unit is folded into its value's row instead.
        if is_engine_column(key[2], SCOPE_HIDDEN):
            continue
        # A cell the file authored stays the file's, even though a later step
        # overwrites it — and many are overwritten, because processing a table
        # rewrites its cells as Quantities. Crediting the overwriter would file
        # `Electrolyzer > Nominal power` under whichever step happened to touch it
        # last, and would put groups from *later* positions in a panel that is
        # supposed to show only what exists now.
        origin = None if key in literals else writer.get(key)
        bucket = ('file', None, None) if origin is None else ('step', origin[0], origin[1])
        buckets.setdefault(bucket, []).append((key, record, units.get((key[0], key[1]))))

    groups = [_group(bucket, entries, order, index, reads)
              for bucket, entries in buckets.items()]
    groups.sort(key=lambda group: group['sort'])
    for group in groups:
        del group['sort']   # ordering is the server's business, not the payload's

    pending = _pending(project, step_name, writer, index)
    return {
        'groups': groups,
        'total': sum(group['count'] for group in groups),
        'later': len(pending),
        'pending': pending,
    }


def _group(bucket, entries, order, index, reads):
    '''One scope group — a producing step, or the file — split into its tables.'''

    kind, name, position = bucket
    tables = {}
    for key, record, unit in entries:
        tables.setdefault(key[0], []).append({
            'row': key[1],
            'column': key[2],
            'record': record,
            'unit': unit,
            'reference': refs.format_reference(key[0], key[1], key[2],
                                               record.get('unit') or unit or '-'),
        })

    table_list = [
        {'table': table, 'reads': table in reads,
         'rows': sorted(rows, key=lambda row: (row['row'], row['column']))}
        for table, rows in tables.items()
    ]
    table_list.sort(key=lambda entry: (not entry['reads'], entry['table']))
    count = sum(len(entry['rows']) for entry in table_list)

    if kind == 'file':
        return {'kind': 'file', 'label': 'authored in the file', 'name': None,
                'position': None, 'tables': table_list, 'count': count, 'sort': (2, 0)}

    distance = index - order.index(name) if name in order else 99
    return {
        'kind': 'this' if distance == 0 else 'step',
        'label': label_of(name),
        'name': name,
        'position': position,
        'tables': table_list,
        'count': count,
        'sort': (0 if distance == 0 else 1, distance),
    }


def _pending(project, step_name, writer, index):
    '''Cells that will exist, but not yet — the ones a reference must wait for.'''

    visible = project.available_at(step_name)
    pending = []
    for key, (name, position, step_index) in writer.items():
        if key in visible or step_index < index or is_engine_column(key[2], SCOPE_HIDDEN):
            continue
        pending.append({'table': key[0], 'row': key[1], 'column': key[2],
                        'step': label_of(name), 'position': position})
    pending.sort(key=lambda row: (row['position'] or 0, row['table'], row['row']))
    return pending
