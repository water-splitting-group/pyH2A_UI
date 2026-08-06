'''The step frame: needs, scope, produces — and the checks that fire before the run.

Two obligations, and the second is the one that is easy to lose. The checker must
catch every fault it claims to catch, *and* it must stay silent on all five shipped
reference files. A validator that cries wolf on pyH2A's own inputs is worse than
none: it trains the user to ignore it.

Both directions are asserted here. `test_no_shipped_pathway_reports_a_problem` is
the silence half; every `test_catches_*` is the noise half.
'''

import json

import pytest
from pyh2a_studio.core import examples, frame, project, refs

PATHWAYS = [example.key for example in examples.EXAMPLES]


def open_project(key='pv_e'):
    example = examples.get(key)
    return project.Project.open(example.markdown(), origin=example.file_name)


@pytest.fixture(scope='module')
def pv_e():
    return open_project('pv_e')


# ---------------------------------------------------------------- silence


@pytest.mark.parametrize('key', PATHWAYS)
def test_no_shipped_pathway_reports_a_problem(key):
    '''Zero false positives on pyH2A's own reference inputs.

    These files are correct by definition — upstream's tests assert their costs. Any
    flag here is a bug in the checker. Three real rules were found this way: bounds
    are declared in SI base units while cells are authored in whatever unit suits
    (`Array azimuth` is `180 deg` against bounds `[0, π]`); `<...>` in a spec key is a
    wildcard, not a row name; and dimension strings differ in spacing between the
    spec and the engine's own renderer.
    '''

    opened = open_project(key)
    flagged = [
        f'{field["table"]} > {field["row"]}: {problem["message"]}'
        for step in frame.rail(opened)
        for table in frame.build(opened, step['name'])['needs']
        for field in table['fields']
        for problem in field['problems']
    ]
    assert flagged == []


@pytest.mark.parametrize('key', PATHWAYS)
def test_every_pathway_builds_a_frame_for_every_step(key):
    '''No step is unopenable — including steps that author nothing.'''

    opened = open_project(key)
    for step in frame.rail(opened):
        built = frame.build(opened, step['name'])
        assert built['step']['name'] == step['name']
        assert built['step']['label']
        assert isinstance(built['needs'], list)
        assert isinstance(built['scope']['groups'], list)


# ---------------------------------------------------------------- noise


def test_catches_a_value_below_its_declared_minimum(pv_e):
    '''`Minimum capacity` is declared `[0, 1]`; -0.5 must be refused.'''

    edited = pv_e.edit('Electrolyzer', 'Minimum capacity', 'Value', '-0.5')
    problems = _problems_for(edited, 'Electrolyzer_Plugin', 'Minimum capacity')
    assert [p['kind'] for p in problems] == ['below-bounds']
    assert 'below the declared minimum of 0' in problems[0]['message']


def test_catches_a_value_above_its_declared_maximum(pv_e):
    edited = pv_e.edit('Electrolyzer', 'Minimum capacity', 'Value', '250%')
    problems = _problems_for(edited, 'Electrolyzer_Plugin', 'Minimum capacity')
    assert [p['kind'] for p in problems] == ['above-bounds']


def test_bounds_are_compared_in_base_units_not_authored_units(pv_e):
    '''`180 deg` passes bounds of `[0, π]`; `180 rad` does not.

    The same number, two units, opposite verdicts — which is the whole reason the
    comparison converts first.
    '''

    assert not _problems_for(pv_e, 'Hourly_Irradiation_Plugin', 'Array azimuth')

    edited = pv_e.edit('Irradiance Area Parameters', 'Array azimuth', 'Unit', 'rad')
    problems = _problems_for(edited, 'Hourly_Irradiation_Plugin', 'Array azimuth')
    assert [p['kind'] for p in problems] == ['above-bounds']


def test_catches_a_unit_of_the_wrong_dimension(pv_e):
    '''`Nominal power` is declared `power`; kilograms are not power.

    The engine does not object — it converts what it can and returns a number. This
    check is the only thing standing between a slipped unit and a plausible answer.
    '''

    edited = pv_e.edit('Electrolyzer', 'Nominal power', 'Unit', 'kg')
    problems = _problems_for(edited, 'Electrolyzer_Plugin', 'Nominal power')
    assert [p['kind'] for p in problems] == ['wrong-dimension']
    assert 'declared power' in problems[0]['message']


def test_accepts_any_unit_of_the_right_dimension(pv_e):
    '''`MW` and `W` are as valid as `kW` — the check is dimensional, not textual.'''

    for unit in ('MW', 'W', 'GW'):
        edited = pv_e.edit('Electrolyzer', 'Nominal power', 'Unit', unit)
        assert not _problems_for(edited, 'Electrolyzer_Plugin', 'Nominal power'), unit


def test_catches_a_unit_the_engine_cannot_parse(pv_e):
    edited = pv_e.edit('Electrolyzer', 'Nominal power', 'Unit', 'kilowatts')
    problems = _problems_for(edited, 'Electrolyzer_Plugin', 'Nominal power')
    assert [p['kind'] for p in problems] == ['unknown-unit']


def test_catches_a_dangling_path_and_names_the_intended_target(pv_e):
    '''The failure the engine hides: a mistyped path becomes 1.0 and a printed warning.'''

    edited = pv_e.edit('Direct Capital Costs - Electrolyzer', 'Electrolyzer CAPEX', 'Path',
                       '{Electrolyzer > Nominal Power > Value, kW}')
    problems = _problems_for(edited, 'Capital_Cost_Plugin', 'Electrolyzer CAPEX')
    assert [p['kind'] for p in problems] == ['path-dangling']
    assert ['Electrolyzer', 'Nominal power', 'Value'] in problems[0]['near']


def test_a_forward_reference_reports_the_step_that_will_supply_it(pv_e):
    '''"Not until step 900" is a different fix from "no such row".'''

    edited = pv_e.edit('Electrolyzer', 'Nominal power', 'Value',
                       '{Dependent Variables > Levelized cost > Value, USD/kg}')
    problems = _problems_for(edited, 'Electrolyzer_Plugin', 'Nominal power')
    kinds = [p['kind'] for p in problems]
    assert 'value-early' in kinds
    assert '900' in next(p for p in problems if p['kind'] == 'value-early')['message']


def test_a_wildcard_row_spec_expands_over_the_real_rows(pv_e):
    '''`Construction > <...>` means every construction year, not a row called `<...>`.'''

    rows = {
        field['row']
        for table in frame.build(pv_e, 'Time_Plugin')['needs']
        for field in table['fields']
        if field['table'] == 'Construction'
    }
    assert '<...>' not in rows
    assert 'Capital spent in 1st year of construction' in rows


# ---------------------------------------------------------------- shape


def test_a_field_carries_its_range_unit_and_meaning(pv_e):
    '''Jacob's ask, asserted: every value shows what it is and what it may be.'''

    field = _field(pv_e, 'Electrolyzer_Plugin', 'Minimum capacity')

    assert field['text'] == '10%'
    assert field['unit']['text'] == '-'
    assert field['declared']['bounds'] == [0, 1]
    assert field['declared']['dimension'] == 'dimensionless'
    assert field['declared']['optional'] is False
    assert 'Percentage or value between 0 and 1' in field['declared']['description']
    assert field['declared']['types'] == ['float', 'int']


def test_a_field_shows_the_text_the_user_wrote(pv_e):
    '''`5,500` and `98%`, not `5500.0` and `0.98`.

    The engine's parser normalises both away. Echoing its output back into the form
    would silently rewrite the file's own idiom on the next save.
    '''

    assert _field(pv_e, 'Electrolyzer_Plugin', 'Nominal power')['text'] == '5,500'
    assert _field(pv_e, 'Hourly_Irradiation_Plugin', 'Mismatch derating')['text'] == '98%'


def test_a_field_names_the_file_it_came_from(pv_e):
    '''Defaults are shown, and shown as defaults.

    Sixty of this pathway's 211 cells arrive from `Defaults_TEA.md`. Hiding them
    leaves a step's form incomplete; presenting them as the user's own is a lie about
    a value they may want to override.
    '''

    assert _field(pv_e, 'Electrolyzer_Plugin', 'Nominal power')['origin'] == 'PV_E_Base.md'
    assert _field(pv_e, 'Time_Plugin', 'Plant life')['origin'] == 'pyH2A.Config~Defaults_TEA.md'


def test_a_computed_input_is_not_offered_as_a_form_field(pv_e):
    '''A row an earlier step writes is evidence, not a blank the user must fill.'''

    field = _field(pv_e, 'Stored_Power_Electrolysis_Plugin', 'Yearly operation data')
    assert field['state'] == 'computed'
    assert field['problems'] == []


def test_scope_separates_the_file_from_each_producing_step(pv_e):
    '''Grouped by when a value arrived, nearest step first, file last.'''

    groups = frame.build(pv_e, 'Electrolyzer_Plugin')['scope']['groups']
    labels = [(group['kind'], group['position']) for group in groups]

    assert labels[-1][0] == 'file'
    step_positions = [position for kind, position in labels if kind == 'step']
    assert step_positions == sorted(step_positions, reverse=True)


def test_scope_marks_the_tables_this_step_reads(pv_e):
    '''The rows most likely to be examined float to the top of their group.'''

    groups = frame.build(pv_e, 'Electrolyzer_Plugin')['scope']['groups']
    file_group = next(group for group in groups if group['kind'] == 'file')

    assert file_group['tables'][0]['reads'] is True
    assert file_group['tables'][0]['table'] == 'Electrolyzer'


def test_scope_never_shows_a_value_the_step_cannot_see(pv_e):
    '''The panel's whole claim. A value from a later step must be in `pending`.'''

    built = frame.build(pv_e, 'Electrolyzer_Plugin')
    visible = {
        (table['table'], row['row'])
        for group in built['scope']['groups']
        for table in group['tables']
        for row in table['rows']
    }
    assert ('Dependent Variables', 'Levelized cost') not in visible
    assert any(row['table'] == 'Dependent Variables' for row in built['scope']['pending'])


def test_every_scope_row_carries_a_reference_that_parses(pv_e):
    '''Click-to-bind can only work if the offered string is the real one.'''


    built = frame.build(pv_e, 'Electrolyzer_Plugin')
    available = set(pv_e.available_at('Electrolyzer_Plugin'))
    for group in built['scope']['groups']:
        for table in group['tables']:
            for row in table['rows']:
                assert refs.check(row['reference'], available)['status'] == 'ok', row


def test_produces_reports_what_the_step_actually_wrote(pv_e):
    built = frame.build(pv_e, 'Electrolyzer_Plugin')
    written = {
        (table['table'], row['row'])
        for table in built['produces']['tables']
        for row in table['rows']
    }
    assert ('Electrolyzer', 'H2 production (yearly)') in written
    assert built['produces']['count'] > 0
    assert built['produces']['declared_but_absent'] == []


def test_a_failing_step_is_a_frame_not_an_exception(pv_e):
    '''The error arrives located, with the step's inputs still inspectable.'''

    broken = pv_e.edit('Electrolyzer', 'Nominal power', 'Value', 'not a number')
    built = frame.build(broken, broken.run.failed)

    assert built['step']['status'] == 'error'
    assert built['step']['error']
    assert built['step']['error_type']
    assert built['needs'], 'a failed step must still show what it was given'


def test_the_rail_flags_every_step_a_bad_value_reaches(pv_e):
    '''You can see which steps need attention without visiting seventeen of them.

    And it is *steps*, plural, on purpose. `Electrolyzer > Minimum capacity` is
    declared as an input by two plugins, so a bad value there is a problem in both
    places and the rail says so. Reporting only the first would understate the blast
    radius of the edit — which is exactly what a reader of a rail wants to know.
    '''

    broken = pv_e.edit('Electrolyzer', 'Minimum capacity', 'Value', '-0.5')
    flagged = {entry['label']: entry['problems'] for entry in frame.rail(broken)
               if entry['problems']}
    assert flagged == {'Electrolyzer': 1, 'Stored Power Electrolysis': 1}


def test_labels_and_families_are_readable(pv_e):
    assert frame.label_of('Stored_Power_Electrolysis_Plugin') == 'Stored Power Electrolysis'
    assert frame.family_of('Photovoltaic_Plugin') == 'solar'
    assert frame.family_of('Reverse_Osmosis_Plugin') == 'water'
    assert frame.family_of('Wholly_Unknown_Plugin') == 'other'


def test_the_whole_frame_is_json_safe(pv_e):
    '''It crosses to a browser; a non-serialisable value is a blank screen.'''


    for step in frame.rail(pv_e):
        json.dumps(frame.build(pv_e, step['name']), allow_nan=False)


# ---------------------------------------------------------------- helpers


def _field(opened, step_name, row_name):
    for table in frame.build(opened, step_name)['needs']:
        for field in table['fields']:
            if field['row'] == row_name:
                return field
    raise AssertionError(f'{step_name} declares no field for row "{row_name}"')


def _problems_for(opened, step_name, row_name):
    return _field(opened, step_name, row_name)['problems']


def test_a_range_is_stated_in_the_terms_its_field_is_written_in(pv_e):
    '''Otherwise six shipped fields display a value outside their own stated range.'''

    assert _field(pv_e, 'Electrolyzer_Plugin', 'Minimum capacity')['bounds_shown'] == {
        'low': 0, 'high': 100, 'percent': True}
    assert _field(pv_e, 'Hourly_Irradiation_Plugin', 'Array azimuth')['bounds_shown'] == {
        'low': pytest.approx(0), 'high': pytest.approx(180), 'percent': False}


def test_an_offset_unit_converts_its_bounds_end_by_end(pv_e):
    '''Temperature is affine, so a common scale factor is not a conversion.

    `convert(1, 'K', 'degC')` is -272.15. Scaling `[250, 500] K` by it gave
    `-68 038 … -136 075` — negative, out of order, five orders of magnitude wrong, and
    printed directly beneath a field reading `45`.
    '''

    shown = _field(pv_e, 'Hourly_Irradiation_Plugin',
                   'Nominal operating temperature')['bounds_shown']
    assert shown['low'] == pytest.approx(-23.15)
    assert shown['high'] == pytest.approx(226.85)
    assert shown['low'] < 45 < shown['high']


def test_a_range_with_no_authored_unit_names_the_unit_it_is_in(pv_e):
    '''`Module tilt` has no unit cell, so its range is in radians — beside `Array
    azimuth`'s range in degrees. Two angle fields, adjacent, in two unit systems.'''

    shown = _field(pv_e, 'Hourly_Irradiation_Plugin', 'Module tilt')['bounds_shown']
    assert shown['unit'] == 'rad'
    assert shown['high'] == pytest.approx(1.5708, abs=1e-4)


def test_a_never_reached_step_keeps_its_authored_fields_editable(pv_e):
    '''Otherwise you cannot fix the field you just broke.

    Breaking `Electrolyzer > Nominal power` stops the run at Photovoltaic, one step
    earlier, which marks Electrolyzer `unevaluated`. Rendering the whole step read-only
    left the bad value on screen with no way to change it — the only escape was to open
    a different step or reload. A value the user wrote stays theirs to edit whatever
    happened downstream; only a value an earlier step was meant to compute becomes
    evidence.
    '''

    broken = pv_e.edit('Electrolyzer', 'Nominal power', 'Value', 'banana')
    fields = [field for table in frame.build(broken, 'Electrolyzer_Plugin')['needs']
              for field in table['fields']]

    culprit = next(field for field in fields if field['row'] == 'Nominal power')
    assert culprit['state'] == 'unevaluated'
    assert culprit['text'] == 'banana', 'the bad value must still be shown to be fixed'

    authored = [field for field in fields if field['text']]
    assert len(authored) >= 5
