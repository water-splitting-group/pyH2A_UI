'''References between cells, and the silent failure they hide.

A pyH2A cell can point at another cell instead of holding a number. The syntax is
one brace expression:

    {Technical Operating Parameters and Specifications > Plant modules > Value, -}
     └────────── table ──────────────────────────────┘ └── row ──────┘ └ col ┘ unit

It appears in two shapes, and conflating them is wrong in both directions:

**The row *is* the value.** A reference in the `Value` column means this row
resolves to whatever it points at. `Irradiation Used > Data` is the hourly array
that `Hourly Irradiation` computed — no arithmetic, just an alias.

**The row is a *multiplier* on the value.** A reference in a `Path` column, with a
number in `Value`, means the row is the product. `Electrolyzer CAPEX` reads
`Value = 784`, `Path = {Electrolyzer > Nominal power > Value, kW}`, and the engine
computes `784 × 5500 = 4 312 000 USD`. Presenting that as `784 USD` — or as
`5500` — is a wrong number either way.

The trailing unit is a **conversion request, not a label.** `784 × 5500 = 4 312 000`
only holds if the target is read *in kW*. The requested unit routinely differs from
how the target is stored: in `PV_E_Base.md`, `Irradiation Used > Data` asks `kWh/m2`
of an array stored in `Wh/m2`, and `Battery CAPEX` asks `kWh` of a scalar stored in
`MWh`.

**Why this module exists at all.** Read `input_modification.process_path`: when a
path does not resolve, the engine prints a warning to stdout and *substitutes 1.0*.
Nothing raises. A mistyped table name therefore yields a plausible-looking cost
that is silently wrong, in a run that reports success — the exact failure this
studio is built to make impossible. Every reference is checked here, against the
set of cells that genuinely exist at that point in the run, before the engine is
asked to resolve anything.
'''

import re

BARE_VALUE = 'Value'
BARE_UNIT = 'Unit'
BARE_PATH = 'Path'
VALUE_SUFFIX = '_Value'
UNIT_SUFFIX = '_Unit'
PATH_SUFFIX = '_Path'

NO_PATH = frozenset({'', 'none', 'None', '-', 'n/a'})
'''Cells that mean "this row has no reference". The engine's own files write
`None` in a `Path` column to mean absent.'''

_REFERENCE = re.compile(r'^\{(?P<body>.+)\}$', re.DOTALL)


def looks_like_reference(text):
    '''True when a cell is trying to be a reference.

    Brace-delimited is the test, deliberately loose: `{Foo}` is a *broken*
    reference, not a plain string, and calling it plain would hide the error the
    user needs to see.
    '''

    return isinstance(text, str) and bool(_REFERENCE.match(text.strip()))


def parse(text):
    '''A reference cell as `{'path': (table, row, column), 'unit': str}`.

    Returns
    -------
    dict
        On success: `path`, `unit`, and `text` (normalised). On failure: `error`
        naming what is wrong in words a user can act on, plus whatever was
        recoverable.

    Mirrors `parse_path_with_unit` + `parse_parameter`: split the braces off, take
    the last comma as the unit separator, split the rest on `>`. Exactly three
    components is the only valid shape — the engine warns and substitutes 1.0 for
    anything else, which is why "two components" is reported here as an error
    rather than tolerated.
    '''

    if not isinstance(text, str):
        return {'error': 'not a reference'}

    match = _REFERENCE.match(text.strip())
    if not match:
        return {'error': 'a reference must be wrapped in braces, as {Table > Row > Column, unit}'}

    body = match.group('body')
    if ',' not in body:
        return {'error': 'missing the unit — a reference ends with ", unit", e.g. ", kW" or ", -"'}

    path_text, unit = body.rsplit(',', 1)
    parts = [part.strip() for part in path_text.split('>')]
    unit = unit.strip()

    if len(parts) != 3 or not all(parts):
        return {
            'error': f'a reference needs exactly three parts separated by ">" '
                     f'(table, row, column); this has {len(parts)}',
            'parts': parts,
            'unit': unit,
        }

    return {
        'path': tuple(parts),
        'unit': unit,
        'text': f'{{{parts[0]} > {parts[1]} > {parts[2]}, {unit}}}',
    }


def format_reference(table, row, column, unit='-'):
    '''The reference string that points at one cell.

    The one place this string is built, so click-to-bind and hand-typing can never
    produce different text for the same target.
    '''

    return f'{{{table} > {row} > {column}, {unit or "-"}}}'


def column_groups(row_columns):
    '''Group a row's columns into value/unit/path triples, the engine's way.

    Mirrors `identify_bottom_keys`. A row is not a flat list of cells: `Utilities`
    rows carry `Usage_Value | Usage_Unit | Usage_Path | Cost_Value | Cost_Unit |
    …`, which is three logically separate quantities in one row. A UI that renders
    those as six unrelated fields is unreadable, and one that assumes a bare
    `Value` misses them entirely.

    Returns
    -------
    list of dict
        `{'name', 'value', 'unit', 'path'}` in column order. `name` is the group
        label (`''` for the bare group, `'Usage'` for a prefixed one). `unit` and
        `path` are column names or None. Columns belonging to no pair come back as
        their own group with only `value` set — that is how categorical cells like
        `Type` and free text like `Comment` arrive.
    '''

    present = list(row_columns)
    groups = []
    claimed = set()

    for column in present:
        if column == BARE_VALUE and BARE_UNIT in present:
            groups.append({'name': '', 'value': BARE_VALUE, 'unit': BARE_UNIT,
                           'path': BARE_PATH if BARE_PATH in present else None})
            claimed.update({BARE_VALUE, BARE_UNIT, BARE_PATH})
        elif column.endswith(VALUE_SUFFIX):
            prefix = column[: -len(VALUE_SUFFIX)]
            unit_column = prefix + UNIT_SUFFIX
            if unit_column in present:
                path_column = prefix + PATH_SUFFIX
                groups.append({'name': prefix, 'value': column, 'unit': unit_column,
                               'path': path_column if path_column in present else None})
                claimed.update({column, unit_column, path_column})

    for column in present:
        if column not in claimed:
            groups.append({'name': column, 'value': column, 'unit': None, 'path': None})

    return groups


def check(text, available, produced_later=None):
    '''Validate one reference against what actually exists.

    Parameters
    ----------
    text : str
        The cell's raw text.
    available : set or dict
        Keys of the cells in scope, as `(table, row, column)` tuples.
    produced_later : dict, optional
        `{(table, row, column): (step_name, position)}` for cells a later step
        will write. Lets a dangling reference be told apart from a merely *early*
        one, which is a different problem with a different fix.

    Returns
    -------
    dict
        `status` is one of:

        `'ok'`          resolves now.
        `'early'`       the target exists, but not until `step` at `position`.
                        The engine would substitute 1.0 at this point in the run.
        `'dangling'`    nothing anywhere writes this cell. Almost always a typo,
                        and always a silently wrong number.
        `'malformed'`   not parseable as a reference.

        Plus `message` in plain language, and `path`/`unit` when known. A
        `'dangling'` result carries `near`: the closest existing cells, so the UI
        can offer the fix rather than only reporting the fault.
    '''

    parsed = parse(text)
    if 'path' not in parsed:
        return {'status': 'malformed', 'message': parsed['error']}

    path, unit = parsed['path'], parsed['unit']
    if path in available:
        return {'status': 'ok', 'path': path, 'unit': unit,
                'message': f'resolves to {path[0]} > {path[1]}'}

    later = (produced_later or {}).get(path)
    if later:
        step, position = later
        return {
            'status': 'early', 'path': path, 'unit': unit, 'step': step, 'position': position,
            'message': f'{path[0]} > {path[1]} is not written until step {position} '
                       f'({step}); the engine would read 1 here',
        }

    return {
        'status': 'dangling', 'path': path, 'unit': unit,
        'message': f'nothing writes {path[0]} > {path[1]} > {path[2]}; '
                   f'the engine would silently use 1 instead',
        'near': nearest(path, available),
    }


def nearest(path, available, limit=5):
    '''Existing cells closest to a path that does not resolve.

    Scored on shared table name first, then row-name overlap. Crude on purpose: it
    only has to put the intended target in a list of five, which for a mistyped or
    renamed row it reliably does.
    '''

    table, row, column = path
    scored = []
    for candidate in available:
        score = 0
        if candidate[0] == table:
            score += 100
        elif table.lower() in candidate[0].lower() or candidate[0].lower() in table.lower():
            score += 40
        if candidate[1] == row:
            score += 60
        else:
            score += 20 * _overlap(row, candidate[1])
        if candidate[2] == column:
            score += 10
        if score >= 40:
            scored.append((score, candidate))

    scored.sort(key=lambda pair: (-pair[0], pair[1]))
    return [list(candidate) for _, candidate in scored[:limit]]


def _overlap(left, right):
    '''Fraction of words the two names share, 0…1.'''

    left_words = set(left.lower().split())
    right_words = set(right.lower().split())
    if not left_words or not right_words:
        return 0.0
    return len(left_words & right_words) / max(len(left_words), len(right_words))
