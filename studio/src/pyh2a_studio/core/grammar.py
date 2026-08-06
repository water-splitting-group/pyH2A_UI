'''Raw-preserving input parsing and serialization.

The user's markdown file is the single source of truth. This module keeps a verbatim,
cell-level view of it so that a structured edit rewrites exactly one cell and nothing
else reflows. The line classifier below mirrors pyH2A's
``convert_file_to_dictionary`` (``Utilities/input_modification.py``) exactly — same
states, same transitions — but stores raw cell strings instead of ``num()``-converted
values. The engine still parses the serialized text itself; equivalence is pinned by
``tests/test_project_io.py`` against every shipped end-to-end input.

Grammar note (audit CORE-1..5): the engine's parser silently mis-reads GFM tables with
leading/trailing pipes, duplicate table names, and content before the first header.
``parse_document`` REJECTS those loudly instead — the UI is the boundary where the
grammar becomes safe.
'''

from dataclasses import dataclass, field

from pyH2A.Utilities.input_modification import convert_file_to_dictionary, file_import, merge

from pyh2a_studio.core import engine


@dataclass
class Table:
    '''One markdown table, verbatim.

    Parameters
    ----------
    name : str
        Top key (the ``# Header`` line, stripped).
    columns : list of str
        Header cells in order. ``columns[0]`` labels the row-name column (usually
        ``Name``); the engine ignores its text but the file keeps it.
    rows : dict
        ``{middle_key: {column_name: raw_cell_string}}`` in file order. Missing cells
        (ragged rows) are simply absent.
    '''

    name: str
    columns: list = field(default_factory=list)
    rows: dict = field(default_factory=dict)


class InputGrammarError(ValueError):
    '''A structural problem the engine would mis-parse silently; raised loudly instead.'''


def parse_document(markdown_text):
    '''Parse input markdown into an ordered ``{name: Table}`` dict, cells verbatim.

    Parameters
    ----------
    markdown_text : str
        Full text of a pyH2A input file.

    Returns
    -------
    document : dict
        ``{table_name: Table}`` in file order.

    Raises
    ------
    InputGrammarError
        For leading/trailing-pipe tables, duplicate table names, or table content
        before the first ``#`` header — all cases the engine mis-reads silently.
    '''

    document = {}
    current_table = None
    in_table = False
    expecting_header = False

    lines = markdown_text.splitlines()

    for line_number, line in enumerate(lines, start=1):
        stripped = line.strip()

        if line.startswith('#'):
            current_table = _start_table(document, line, line_number)
            expecting_header = False
            continue

        if stripped == '':
            in_table = False
            expecting_header = True
            continue

        if line.startswith('-'):
            in_table = True
            expecting_header = False
            continue

        # A non-blank content line: either the header row or a table row,
        # matching the engine's classifier states. A LEADING pipe (GFM style) makes
        # the engine read an empty row name — reject loudly. Trailing pipes are
        # harmless (an empty extra cell the engine drops) and shipped files have
        # them, so they are accepted and normalized away on serialize.
        if line.startswith('|'):
            raise InputGrammarError(
                f'line {line_number}: table rows must not start with "|" — '
                f'the engine parses GFM-piped tables as empty. Remove the outer pipes.'
            )

        if expecting_header:
            # The engine keeps overwriting header_entries on every non-blank line
            # until a '---' line arrives; mirror that (last line before '---' wins).
            if current_table is None:
                raise InputGrammarError(
                    f'line {line_number}: content before the first "#" header.'
                )
            current_table.columns = [cell.strip() for cell in line.split('|')]
            continue

        if in_table:
            cells = [cell.strip() for cell in line.split('|')]
            row_name = cells[0]
            row = {}
            for column_name, cell in zip(current_table.columns[1:], cells[1:]):
                row[column_name] = cell
            current_table.rows[row_name] = row
        else:
            raise InputGrammarError(
                f'line {line_number}: unexpected content outside any table '
                f'("{stripped[:60]}") — the engine would ignore or mis-file it.'
            )

    return document


def _start_table(document, line, line_number):
    '''Register a new table for a ``#`` header line, rejecting duplicates.'''

    table_name = line.strip(' #')
    if table_name in document:
        raise InputGrammarError(
            f'line {line_number}: duplicate table name "{table_name}" — '
            f'the engine would silently replace the first table.'
        )
    table = Table(name=table_name)
    document[table_name] = table
    return table


OUTLIER_GAP = 24
'''How far clear of the pack a cell must stand, in characters, before the column stops
widening for it.

Columns are padded to their widest cell so the pipes line up, and the whole difficulty is
that one cell can be enormous. `# Utilities` holds `0.0023749510945008` and an 83-character
`pyH2A.Lookup_Tables.Utility_Cost~..._Reference_Case.csv` in the same `Cost_Value` column:
widening to 83 strands 65 spaces on the other row and pushes five further columns off the
screen for nothing.

But width alone cannot tell that case from a column that is *uniformly* wide.
`Photocatalytic > Indirect Capital Costs` names its rows `Engineering and design (fraction
of total direct capital costs)` and three siblings, 57 to 66 characters; clipping those to
any fixed width makes every row ragged and buys nothing. So the test is not how wide the
widest cell is, it is how *lonely*: drop the widest cell only while it stands more than
`OUTLIER_GAP` clear of the next-widest cell in the same column, then pad to what is left.
A width two rows share is never an outlier, which is what keeps
`{PEC Cells > Number > Value, -}` — four identical 31-character references beside one
`None` — setting its column.

24 comes from the corpus. Across the 105 tables in the five shipped pathways plus
`tea_mass`, sort every column by that lonely-widest gap and there is a 13-character dead
zone: the gaps worth clipping are 33, 38, 47, 56 and three at 65, and the next one down is
20 (`Other Fixed Operating Costs > Path`, two references at 51 and 71 — both long, both
worth aligning). Any value from 20 to 32 emits byte-identical files for all six, so 24 sits
in the middle of the insensitive range rather than on an edge.

Outliers are never truncated — that would corrupt the file. They overflow, and only the
cells after them on that one line lose the grid.'''


def _column_widths(header, body):
    '''Padded width per column index for one table's header and body cell-lists.

    The header never votes on the width, it only sets a floor: a column has to be at
    least as wide as its own heading (`Price_Conversion_Factor_Unit` is 28 characters
    over a column of `-`) or the heading stops standing over its column. But letting the
    heading vote would break the other direction — a one-row `# Direct Capital Costs -
    Electrolyzer` would count `Path` as the pack and treat its single 42-character
    reference as the outlier, leaving the heading nothing to sit above.
    '''

    lengths = {}
    for cells in body:
        for index, cell in enumerate(cells):
            lengths.setdefault(index, []).append(len(cell))

    widths = []
    for index in range(max([len(header)] + [len(cells) for cells in body])):
        column = sorted(lengths.get(index, ()), reverse=True)
        at = 0
        while at + 1 < len(column) and column[at] - column[at + 1] > OUTLIER_GAP:
            at += 1
        heading = len(header[index]) if index < len(header) else 0
        widths.append(max(column[at] if column else 0, heading))
    return widths


def _pad(cells, widths):
    '''One table line's cells, padded into columns.

    Every cell but the last is padded; the last is left flush, because trailing
    whitespace is noise and because rows are ragged — most `# Workflow` rows stop after
    `Position`, and padding out to a column a row does not have would be a lie.
    '''

    return [cell.ljust(widths[index]) for index, cell in enumerate(cells[:-1])] + cells[-1:]


def serialize_document(document):
    '''Serialize a ``{name: Table}`` dict back to engine-grammar markdown.

    Emits exactly the grammar the engine parses correctly (audit §6): no outer pipes, a
    blank line before every header, one ``---`` separator per column, verbatim cells.

    Cells are padded so the pipes line up, because a `# Utilities` row is ten cells wide
    and with single spaces around the pipes nothing in it can be read down a column — not
    in the source drawer, and not in the file the user downloads. The engine is unaffected:
    it splits on ``|`` and calls ``strip(' \\n')`` on every piece
    (``Utilities/input_modification.py``), so the padding cannot reach it. And because
    ``parse_document`` strips too, alignment is idempotent — re-serializing a serialized
    file gives the same bytes.

    Parameters
    ----------
    document : dict
        ``{table_name: Table}`` as produced by ``parse_document``.

    Returns
    -------
    markdown_text : str
    '''

    blocks = []
    for table in document.values():
        header = list(table.columns)
        body = []
        for row_name, row in table.rows.items():
            # Ragged rows: the engine's zip drops trailing missing cells entirely
            # (key absent, not 'n/a') — so absent trailing columns must stay absent.
            row_columns = list(table.columns[1:])
            while row_columns and row_columns[-1] not in row:
                row_columns.pop()
            body.append([row_name] + [row.get(column, '') for column in row_columns])

        widths = _column_widths(header, body)
        lines = [f'# {table.name}', '']
        if header:
            padded = _pad(header, widths)
            lines.append(' | '.join(padded).rstrip())
            # The rule underlines the header as emitted, the way a hand-written markdown
            # table does — measured off the padded heading rather than off `widths` so the
            # last column, which is never padded, gets a rule its own length instead of
            # one stretched to a width no cell in it uses. Never fewer than three dashes:
            # two stop being a markdown rule.
            lines.append(' | '.join('-' * max(3, len(cell)) for cell in padded))
        lines.extend(' | '.join(_pad(cells, widths)).rstrip() for cells in body)
        blocks.append('\n'.join(lines))

    return '\n\n'.join(blocks) + '\n'


def set_cell(document, table_name, row_name, column_name, raw_text):
    '''Set one cell (verbatim text) in the document, fail-fast on unknown locations.

    Raises
    ------
    KeyError
        If the table or row does not exist (creating rows is a deliberate,
        separate action in the UI, not a side effect of editing).
    '''

    table = document[table_name]
    row = table.rows[row_name]
    if column_name not in table.columns[1:]:
        raise KeyError(
            f'column "{column_name}" not in table "{table_name}" '
            f'(has: {table.columns[1:]})'
        )
    row[column_name] = raw_text


def ensure_cell(document, table_name, row_name, column_name, raw_text, *,
                plugins=None, inherit=None):
    '''Set one cell, creating the table/row/column if absent (a defaults override).

    A new row is padded to the width of the table it joins. The docstring here used to
    claim a row carrying only the edited column was "a correct, minimal override", on
    the theory that merged defaults would supply the rest. They do not: pyH2A splits a
    row on ``|`` and zips the cells against the header, so a two-cell row under a
    four-column header yields ``None`` for the missing two, and the first plugin to read
    one dies on ``NoneType has no attribute strip``. Adding a step and filling in its
    required value — the whole point of building a pipeline — produced a file that real
    pyH2A rejects as hard as this app did.

    The padding is also what keeps the unit editable. A field reports its unit column by
    looking for one in the row; an unpadded row has no ``Unit`` key, the UI concluded
    there was nowhere to put a unit, and removed the input at the moment the value was
    entered.

    A blank ``Unit`` cell is not acceptable to the engine either — it reads one and
    raises ``Unknown unit encountered during parsing`` — so that column is filled with
    the unit the plugin actually declares for the location (``m2`` for an area), falling
    back to ``-``, pyH2A's dimensionless token, when nothing claims it. Writing the
    declared unit is what turns "add a step and fill it in" into a pipeline that runs:
    with a bare ``-`` the engine correctly refused every dimensional field in turn.

    That declared unit is right for a row nothing holds yet, and wrong for a row the
    merged defaults already carry. ``Plant life`` lives in ``Defaults_TEA.md`` at
    ``20 | year`` and the file has no ``Financial Input Values`` table, so typing 25
    into it creates an override row — and the padding filled the untouched ``Unit``
    from the plugin's dimension, which is the SI base ``s``. The file came back reading
    ``Plant life | 25 | s``, the run died in the Electrolyzer, and nothing on screen
    connected a 25-second plant to the number the user had typed. The same padding
    blanked the ``Value`` of any defaults-backed row whose unit was edited.

    So ``inherit`` — the merged input's own row, when it has one — is consulted first
    for every column this call is not writing. An override then differs from the
    default in exactly the cell that was edited, which is what an override means.

    Parameters
    ----------
    inherit : dict, optional
        The merged input's existing row, as ``{column: value}``. Untouched columns are
        seeded from here before falling back to the plugin's declared unit.
    '''

    units = engine.declared_units(table_name, row_name, plugins)
    held = {column: value for column, value in (inherit or {}).items()
            if value is not None and str(value) != ''}

    fresh = table_name not in document
    if fresh:
        # A table invented to override a default carries the default's own columns, in
        # the default's own order, or the override is a different row. Editing the Unit
        # of `Plant life` built `Financial Input Values` with nothing but a `Unit`
        # column and wrote `Plant life | year` — a row whose value had vanished.
        columns = ['Name'] + [column for column in held if column != 'Name']
        document[table_name] = Table(name=table_name, columns=columns)
    table = document[table_name]

    if column_name not in table.columns[1:]:
        # Defining a column is only ever right for a table this call is inventing. In a
        # table that already exists it means the caller named a column that is not there,
        # and the row that results is nonsense: `# Utilities` holds `Usage_Value`,
        # `Cost_Value` and `Price_Conversion_Factor_Value`, so asking for `Value` appended
        # a ninth column and wrote `Cooling water | | | | | | | | |` — a row real pyH2A
        # refuses and no screen could explain.
        if not fresh:
            raise KeyError(
                f'table "{table_name}" has no column "{column_name}" '
                f'(it has: {", ".join(table.columns[1:])})'
            )
        table.columns.append(column_name)

    # A table invented for a step the user just added starts as `Name | Value`, and a
    # plugin that declares a unit for the row then reads a column that is not there and
    # gets None. Creating `Reverse Osmosis` and filling all three of its fields produced
    # a file that died on `NoneType has no attribute strip` — the same shape as the short
    # row above, one level up.
    if 'Unit' in units and 'Unit' not in table.columns:
        table.columns.append('Unit')

    if row_name not in table.rows:
        table.rows[row_name] = {}

    row = table.rows[row_name]
    row[column_name] = raw_text
    for column in table.columns[1:]:
        # The merged default first, the plugin's declared unit second: an override that
        # invents a unit the default did not have is a different number, silently.
        if column in held:
            row.setdefault(column, str(held[column]))
        else:
            row.setdefault(column, units.get(column, ''))


def engine_dict(markdown_text):
    '''Parse markdown text the way the engine does, including defaults merging.

    Mirrors ``convert_input_to_dictionary`` exactly (same functions, same order) but
    reads from text instead of a file path, so the UI never writes temp files just
    to parse.

    Parameters
    ----------
    markdown_text : str
        Full text of a pyH2A input file.

    Returns
    -------
    inp : dict
        The engine's triple-nested input dict, defaults merged (referenced files
        listed in ``Input files to merge`` are loaded via the engine's own
        ``file_import``, so ``package~file`` references resolve).
    '''

    inp = convert_file_to_dictionary(_ClosableStringIterator(markdown_text))

    if 'Input files to merge' in inp:
        for _, row in inp['Input files to merge'].items():
            referenced_file = row['Value']
            base_inp = convert_file_to_dictionary(file_import(referenced_file, mode='r'))
            inp = merge(base_inp, inp)

    return inp


def merged_documents(markdown_text, origin='this file'):
    '''Every file that contributes cells, parsed verbatim, base files first.

    A pyH2A input file usually carries `# Input files to merge` naming a defaults
    file — `pyH2A.Config~Defaults_TEA.md` for every bundled pathway. The engine
    merges those *values*, so a run sees several dozen rows the user never wrote,
    with no record of where they came from.

    `engine_dict` reproduces the merge for the engine. This reproduces it
    verbatim, keeping each file separate, so a UI can answer the question the merge
    destroys: **is this number mine, or did it arrive from a defaults file, and
    which one?** Without that, a worksheet either hides two thirds of the values a
    step actually reads, or shows them as if the user had typed them.

    Base-file cells are also the only place a default's *authored text* survives.
    The engine's parser runs `num()` over every cell, so a defaults row written
    `2%` reaches `engine_dict` as `0.02` — the same value, a different string. A
    field editor that showed `0.02` and wrote it back would silently rewrite the
    file's own idiom.

    Returns
    -------
    list of (origin, document)
        In merge order: base files first, the user's file last, matching the
        precedence `engine_dict` applies. `origin` is the reference as written
        (`pyH2A.Config~Defaults_TEA.md`) for a base, and `origin` as passed for the
        user's own file.

    Notes
    -----
    A base file that cannot be read or parsed is skipped rather than fatal: the
    engine would have merged it, so the *values* are still correct via
    `engine_dict`; only the provenance for those rows is unavailable. Losing a
    label is not a reason to refuse to open a project.
    '''

    documents = []
    own = parse_document(markdown_text)

    merge_table = own.get('Input files to merge')
    for row in (merge_table.rows.values() if merge_table else ()):
        reference = (row.get('Value') or '').strip()
        if not reference:
            continue
        try:
            with file_import(reference, mode='r') as handle:
                documents.append((reference, parse_document(handle.read())))
        except (OSError, ModuleNotFoundError, InputGrammarError):
            continue

    documents.append((origin, own))
    return documents


def cell_origins(documents):
    '''`{(table, row, column): origin}` — who supplied each cell, last write winning.

    Mirrors the engine's precedence: later documents override earlier ones per
    *cell*, not per row or per table. That granularity is the point — a user file
    overriding one column of a defaults row leaves the rest of that row sourced
    from the default, and a worksheet that rounded this to whole rows would
    mislabel the very cells most likely to be examined.
    '''

    origins = {}
    for origin, document in documents:
        for table in document.values():
            for row_name, row in table.rows.items():
                for column in row:
                    origins[(table.name, row_name, column)] = origin
    return origins


def effective_document(documents):
    '''The documents flattened into one verbatim `{name: Table}`, later winning.

    What the engine effectively parses, with every cell still the string somebody
    actually wrote. This is the surface a worksheet edits against: it contains the
    defaults a step reads, so nothing a plugin needs is missing from the screen.
    '''

    effective = {}
    for _, document in documents:
        for table in document.values():
            target = effective.get(table.name)
            if target is None:
                target = Table(name=table.name, columns=list(table.columns))
                effective[table.name] = target
            for column in table.columns:
                if column not in target.columns:
                    target.columns.append(column)
            for row_name, row in table.rows.items():
                target.rows.setdefault(row_name, {}).update(row)
    return effective


class _ClosableStringIterator:
    '''Line iterator over a string with the ``close()`` the engine's parser calls.

    The engine's ``convert_file_to_dictionary`` iterates a ``TextIO`` and closes it;
    lines must keep their trailing newlines for its state machine.
    '''

    def __init__(self, text):
        if not text.endswith('\n'):
            text = text + '\n'
        self._lines = iter(text.splitlines(keepends=True))

    def __iter__(self):
        return self._lines

    def close(self):
        pass
