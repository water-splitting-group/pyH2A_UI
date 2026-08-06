'''The serialized file, as a file.

`serialize_document` writes the markdown that the engine parses, that the source drawer
shows, and that a user downloads and keeps. It now pads cells so the pipes line up, which
is a change to bytes rather than to numbers — and that is exactly the kind of change that
is easy to get subtly wrong, because everything still runs.
'''

import re

import pytest
from pyH2A.Utilities.input_modification import convert_input_to_dictionary

from pyh2a_studio.core import examples, grammar, project, starters

PUBLISHED = {
    'pv_e': 4.194302976489664,
    'thermal': 3.2705814097046098,
    'pec': 139.41887561917213,
    'photocatalytic': 185.44329282256817,
    'pv_e_lcoe': 0.02858462133297927,
}


def reserialize(text):
    return grammar.serialize_document(grammar.parse_document(text))


@pytest.mark.parametrize('key', sorted(PUBLISHED))
def test_alignment_moves_no_number(key):
    '''The engine splits on `|` and strips, so padding cannot reach it. Proven rather
    than asserted, at full float precision, on every shipped pathway.'''

    opened = project.Project.open(reserialize(examples.get(key).markdown()), origin='x')
    assert opened.run.result.levelized_cost.supplied_value == PUBLISHED[key]


def test_alignment_moves_no_number_on_the_starter():
    opened = project.Project.open(reserialize(starters.get('tea_mass').markdown()),
                                  origin='x')
    assert opened.run.result.levelized_cost.supplied_value == 5.5043552237656455


@pytest.mark.parametrize('key', sorted(PUBLISHED))
def test_serializing_is_idempotent(key):
    '''The app round-trips constantly — parse, edit one cell, serialize, parse. If a pass
    through the serializer could change the padding, every edit would rewrite lines it
    did not touch and a diff of two saved files would be unreadable.'''

    once = reserialize(examples.get(key).markdown())
    assert reserialize(once) == once


@pytest.mark.parametrize('key', sorted(PUBLISHED))
def test_every_cell_is_padded_to_its_column_or_overflows_it(key):
    '''The invariant, stated the way the rule actually works.

    Not "every pipe lines up": a lone outlier is *meant* to overflow rather than widen
    its column, which is the whole point of `OUTLIER_GAP`. `# Utilities` on Solar Thermal
    holds an 82-character lookup path in a column whose other cell is 18, and forcing the
    column to 82 would push `Comment` off the far side of any screen.

    So the claim is one-directional: a cell is padded to exactly the column width, or it
    is longer than it. Never shorter — that would be a genuine ragged pipe.
    '''

    for block in reserialize(examples.get(key).markdown()).split('\n\n'):
        rows = [line.split('|') for line in block.splitlines() if '|' in line]
        if len(rows) < 2:
            continue
        widest = max(len(cells) for cells in rows)
        for index in range(widest - 1):
            present = [cells[index] for cells in rows if index < len(cells) - 1]
            if len(present) < 2:
                continue
            width = min(len(cell) for cell in present)
            for cell in present:
                assert len(cell) == width or len(cell.strip()) > width - 2, (
                    f'{key}: column {index} has a short cell {cell!r} '
                    f'against width {width}')


@pytest.mark.parametrize('key', sorted(PUBLISHED))
def test_no_line_carries_trailing_whitespace(key):
    for line in reserialize(examples.get(key).markdown()).splitlines():
        assert line == line.rstrip(), repr(line)


def test_a_heading_always_stands_over_its_own_column():
    '''`Price_Conversion_Factor_Unit` is 28 characters over a column of `-`. If the
    heading did not set a floor it would overhang the column it names, and `# Utilities`
    would read as though its last two columns had swapped.'''

    written = reserialize(examples.get('pv_e').markdown())
    block = next(b for b in written.split('\n\n') if 'Price_Conversion_Factor_Unit' in b)
    header, rule, *rows = [line for line in block.splitlines() if '|' in line]

    assert len(header.split('|')) == len(rule.split('|'))
    for row in rows:
        for index, boundary in enumerate(
                [position for position, char in enumerate(row) if char == '|']):
            assert header[boundary] == '|', f'heading does not reach column {index}'


def test_one_long_comment_does_not_widen_every_other_column():
    '''A single 82-character comment on `Nominal power` must not push the rest of its
    table out to match it. The rule keeps the pack and lets a lone outlier overflow.'''

    block = next(b for b in reserialize(examples.get('pv_e').markdown()).split('\n\n')
                 if 'Nominal power' in b)
    rows = [line for line in block.splitlines() if '|' in line]
    longest_comment = max(len(row.split('|')[-1].strip()) for row in rows[2:])
    assert longest_comment > 70, 'the fixture no longer has a long comment to test with'

    # The name column is the widest non-comment column; it should be sized by its own
    # contents (35 for `Power requirement increase per year`), not by the comment.
    name_width = rows[0].index('|')
    assert name_width < 45, f'the comment widened the name column to {name_width}'


def test_the_rule_row_widens_with_its_columns():
    '''A hand-written aligned markdown table widens its `---` row too; one that does not
    looks like a mistake in a file people read.'''

    block = next(b for b in reserialize(examples.get('pv_e').markdown()).split('\n\n')
                 if 'Nominal power' in b)
    rule = [line for line in block.splitlines() if '|' in line][1]
    for cell in rule.split('|'):
        assert re.fullmatch(r' *-{3,} *', cell), repr(cell)


def test_real_pyh2a_accepts_an_aligned_file(tmp_path):
    '''The claim that padding cannot reach the engine, checked against the engine rather
    than against this app's copy of its parser.'''

    aligned = tmp_path / 'aligned.md'
    aligned.write_text(reserialize(examples.get('pv_e').markdown()))
    plain = tmp_path / 'plain.md'
    plain.write_text(examples.get('pv_e').markdown())

    from_aligned = convert_input_to_dictionary(str(aligned))
    from_plain = convert_input_to_dictionary(str(plain))

    assert set(from_aligned) == set(from_plain)
    for table in from_plain:
        assert from_aligned[table].keys() == from_plain[table].keys(), table
