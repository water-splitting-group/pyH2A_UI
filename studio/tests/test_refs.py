'''References: the grammar, the two shapes, and the silent 1.0.

The engine substitutes 1.0 for any path it cannot resolve and prints a warning to
stdout. That is the single most dangerous behaviour in the whole system, because it
turns a typo into a plausible cost in a run that reports success. These tests pin
that the studio catches every variant of it, and that it never reports a fault it
cannot explain.
'''

import pytest
from pyh2a_studio.core import examples, grammar, refs, trace


def test_parses_the_canonical_reference():
    parsed = refs.parse('{Electrolyzer > Nominal power > Value, kW}')
    assert parsed['path'] == ('Electrolyzer', 'Nominal power', 'Value')
    assert parsed['unit'] == 'kW'


def test_parses_a_reference_whose_names_contain_spaces_and_dashes():
    '''Real table names are long and punctuated; the parser must not be clever.'''

    parsed = refs.parse(
        '{Direct Capital Costs - Electrolyzer > Electrolyzer CAPEX > Value, USD}'
    )
    assert parsed['path'] == (
        'Direct Capital Costs - Electrolyzer', 'Electrolyzer CAPEX', 'Value'
    )
    assert parsed['unit'] == 'USD'


def test_unit_splits_on_the_last_comma_only():
    '''A comma inside a unit expression must not be mistaken for the separator.'''

    parsed = refs.parse('{A > B > Value, USD/kg}')
    assert parsed['unit'] == 'USD/kg'


@pytest.mark.parametrize('text,fragment', [
    ('Electrolyzer > Nominal power > Value, kW', 'braces'),
    ('{Electrolyzer > Nominal power > Value}', 'unit'),
    ('{Electrolyzer > Nominal power, kW}', 'three parts'),
    ('{Electrolyzer, kW}', 'three parts'),
    ('{ > > , kW}', 'three parts'),
])
def test_every_malformed_shape_is_named_not_just_rejected(text, fragment):
    '''The message has to say what to fix — "invalid" is useless to a user.'''

    parsed = refs.parse(text)
    assert 'path' not in parsed
    assert fragment in parsed['error']


def test_a_two_part_path_is_an_error_not_a_tolerance():
    '''The engine warns and substitutes 1.0 for a two-part path. That is a failure.

    Tolerating it here would reproduce the bug this module exists to prevent.
    '''

    assert 'path' not in refs.parse('{Electrolyzer > Nominal power, kW}')


def test_format_and_parse_are_inverses():
    text = refs.format_reference('Some Table', 'Some Row', 'Value', 'kWh/m2')
    assert refs.parse(text)['path'] == ('Some Table', 'Some Row', 'Value')
    assert refs.parse(text)['unit'] == 'kWh/m2'


def test_a_resolvable_reference_is_ok():
    available = {('Electrolyzer', 'Nominal power', 'Value')}
    verdict = refs.check('{Electrolyzer > Nominal power > Value, kW}', available)
    assert verdict['status'] == 'ok'


def test_a_typo_is_dangling_and_offers_the_intended_target():
    '''The fix matters more than the complaint.

    A row renamed or mistyped should come back with the real row in `near`, so the
    UI can offer it instead of only saying no.
    '''

    available = {
        ('Electrolyzer', 'Nominal power', 'Value'),
        ('Electrolyzer', 'Minimum capacity', 'Value'),
        ('Photovoltaic', 'Nominal power', 'Value'),
    }
    verdict = refs.check('{Electrolyzer > Nominal Power > Value, kW}', available)

    assert verdict['status'] == 'dangling'
    assert 'silently use 1' in verdict['message']
    assert ['Electrolyzer', 'Nominal power', 'Value'] in verdict['near']


def test_a_forward_reference_is_early_not_dangling():
    '''"Not yet" and "not ever" are different problems with different fixes.

    Reporting a forward reference as a typo sends the user hunting for a spelling
    mistake that does not exist; the real fix is a position change.
    '''

    verdict = refs.check(
        '{Electrolyzer > H2 production (yearly) > Value, kg}',
        available=set(),
        produced_later={('Electrolyzer', 'H2 production (yearly)', 'Value'):
                        ('Electrolyzer_Plugin', 203)},
    )
    assert verdict['status'] == 'early'
    assert verdict['position'] == 203
    assert 'not written until step 203' in verdict['message']


def test_malformed_reports_malformed_not_dangling():
    verdict = refs.check('{nonsense}', available=set())
    assert verdict['status'] == 'malformed'


def test_every_reference_in_every_bundled_file_resolves():
    '''No shipped pathway contains a broken reference.

    This is the ground truth for the checker: if it flags a shipped file, the
    checker is wrong. Cells are checked against the state at the end of a run,
    which is the full set of names the file ever brings into being.
    '''

    for example in examples.EXAMPLES:
        document = grammar.parse_document(example.markdown())
        traced = trace.build(grammar.engine_dict(example.markdown()))
        available = set(traced.steps[-1].visible)

        for table in document.values():
            for row_name, row in table.rows.items():
                for column, text in row.items():
                    if not refs.looks_like_reference(text):
                        continue
                    verdict = refs.check(text, available)
                    assert verdict['status'] == 'ok', (
                        f'{example.key}: {table.name} > {row_name} > {column} '
                        f'-> {verdict["message"]}'
                    )


def test_a_deliberately_broken_reference_is_caught_before_the_engine_runs():
    '''End to end: the check fires on the exact class of edit that goes wrong.

    And the run really does succeed with a wrong number — asserted here so the
    danger is documented rather than asserted in the abstract.
    '''

    document = grammar.parse_document(examples.get('pv_e').markdown())
    grammar.set_cell(document, 'Direct Capital Costs - Electrolyzer',
                     'Electrolyzer CAPEX', 'Path',
                     '{Electrolyzer > Nominal Power > Value, kW}')
    markdown = grammar.serialize_document(document)

    traced = trace.build(grammar.engine_dict(markdown))
    available = set(traced.steps[-1].visible)
    verdict = refs.check('{Electrolyzer > Nominal Power > Value, kW}', available)
    assert verdict['status'] == 'dangling'

    # The engine does not fail. It quietly prices the electrolyzer at 784 USD.
    assert traced.failed is None
    assert traced.result.levelized_cost.supplied_value < 4.1943


def test_column_groups_splits_a_prefixed_row_into_its_quantities():
    '''A `Utilities` row is three quantities, not nine loose cells.'''

    groups = refs.column_groups([
        'Usage_Value', 'Usage_Path', 'Usage_Unit',
        'Cost_Value', 'Cost_Path', 'Cost_Unit',
        'Price_Conversion_Factor_Value', 'Price_Conversion_Factor_Unit', 'Comment',
    ])
    by_name = {group['name']: group for group in groups}

    assert by_name['Usage'] == {'name': 'Usage', 'value': 'Usage_Value',
                                'unit': 'Usage_Unit', 'path': 'Usage_Path'}
    assert by_name['Price_Conversion_Factor']['path'] is None
    assert by_name['Comment'] == {'name': 'Comment', 'value': 'Comment',
                                  'unit': None, 'path': None}


def test_column_groups_finds_the_bare_triple():
    groups = refs.column_groups(['Value', 'Path', 'Unit', 'Comment'])
    assert groups[0] == {'name': '', 'value': 'Value', 'unit': 'Unit', 'path': 'Path'}


def test_column_groups_leaves_a_value_without_a_unit_alone():
    '''`Value` with no `Unit` column is a plain cell, matching the engine.'''

    groups = refs.column_groups(['Value', 'Comment'])
    assert groups[0] == {'name': 'Value', 'value': 'Value', 'unit': None, 'path': None}


def test_every_row_of_every_bundled_file_groups_without_loss():
    '''No cell falls out of the grouping — an unrendered cell is an invisible input.'''

    for example in examples.EXAMPLES:
        document = grammar.parse_document(example.markdown())
        for table in document.values():
            for row_name, row in table.rows.items():
                grouped = set()
                for group in refs.column_groups(row.keys()):
                    grouped.update(
                        name for name in (group['value'], group['unit'], group['path'])
                        if name
                    )
                missing = set(row) - grouped
                assert not missing, f'{example.key}: {table.name} > {row_name} lost {missing}'
