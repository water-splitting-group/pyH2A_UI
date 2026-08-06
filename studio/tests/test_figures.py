'''Figures: the numbers they draw, and the proof they lost nothing.

A figure that allocates engine values into groups can be wrong in a way that looks
right — a component silently dropped changes every bar a little and nothing on screen
objects. So the decomposition returns its own residual and these tests assert it is
zero on every pathway, at machine precision, rather than checking that the picture
renders.
'''

import json

import pytest
from pyh2a_studio import api
from pyh2a_studio.core import examples, figures, project

PATHWAYS = [example.key for example in examples.EXAMPLES]


def opened(key):
    example = examples.get(key)
    return project.Project.open(example.markdown(), origin=example.file_name)


@pytest.fixture(autouse=True)
def clean_sessions():
    api.SESSIONS.clear()
    yield
    api.SESSIONS.clear()


# ---------------------------------------------------------------- decomposition


@pytest.mark.parametrize('key', PATHWAYS)
def test_the_parts_sum_to_the_engines_own_total(key):
    '''The claim the figure is making, checked in the figure's own numbers.'''

    project_ = opened(key)
    built = figures.contributions(project_.run.result, project_.functional_unit())
    assert abs(built['residual']) < 1e-9, built['residual']


@pytest.mark.parametrize('key', PATHWAYS)
def test_that_total_is_the_headline_the_masthead_shows(key):
    '''Two numbers on one screen must be the same number.

    `Levelized cost contributions > Total` and `Levelized cost` are separate engine
    values. They agree, and if upstream ever changes so they do not, a chart claiming
    to decompose the headline would be decomposing something else.
    '''

    project_ = opened(key)
    built = figures.contributions(project_.run.result, project_.functional_unit())
    assert built['headline_residual'] == pytest.approx(0, abs=1e-9)


@pytest.mark.parametrize('key', PATHWAYS)
def test_family_subtotals_sum_to_the_total(key):
    project_ = opened(key)
    built = figures.contributions(project_.run.result, project_.functional_unit())
    grouped = sum(family['subtotal'] for family in built['families'])
    assert grouped == pytest.approx(built['total'], abs=1e-9)


@pytest.mark.parametrize('key', PATHWAYS)
def test_every_component_lands_in_a_named_family(key):
    '''An `Unclassified` group is a real state, and it must stay empty here.

    It exists so that a component upstream adds shows up by name rather than
    vanishing. If this ever fails, the fix is to place the new component in
    `figures.FAMILIES`, not to widen the test.
    '''

    project_ = opened(key)
    built = figures.contributions(project_.run.result, project_.functional_unit())
    assert not any(family['key'] == 'other' for family in built['families'])


def test_the_unit_follows_the_functional_unit_not_the_assumption():
    '''`USD/kWh` for the electricity pathway. Nothing here says "hydrogen".'''

    assert figures.contributions(opened('pv_e').run.result, 'kg')['unit'] == 'USD/kg'
    assert figures.contributions(opened('pv_e_lcoe').run.result, 'kWh')['unit'] == 'USD/kWh'


def test_shares_are_fractions_of_the_total():
    built = figures.contributions(opened('pv_e').run.result, 'kg')
    assert sum(row['share'] for row in built['rows']) == pytest.approx(1.0, abs=1e-9)


# ---------------------------------------------------------------- annual costs


def test_annual_costs_read_the_engines_own_arrays():
    '''Each line's total is the sum of the array the engine wrote, not a re-derivation.

    Signed, and the sign is the contract. These are cash flows, not costs: capital and
    replacement are money leaving, so their totals are negative, and the stacked figure
    puts each year's segments on whichever side of the datum its sign chose. Flipping a
    line to a friendlier magnitude would break `net`, which is checked below.
    '''

    costs = figures.annual_costs(opened('pv_e').run.result)
    by_name = {line['name']: line for line in costs['lines']}

    assert by_name['Depreciable capital']['total'] == pytest.approx(-4695969, rel=1e-4)
    assert by_name['Replacement']['total'] == pytest.approx(-2244798, rel=1e-4)
    # Twenty-one analysis years, and they are labelled from −1: the build year is not
    # operation year 0, and a figure that plots one axis against the other without the
    # offset puts every cost a year early.
    assert costs['span'] == 21
    assert costs['years'][0] == -1 and costs['years'][-1] == 19
    assert costs['construction_years'] == 1


@pytest.mark.parametrize('key', PATHWAYS)
def test_the_year_totals_are_the_twelve_lines_and_nothing_else(key):
    '''The one property every annotation on the figure rests on.

    A stacked bar whose segments do not sum to the net it is drawn against is a picture
    of nothing. Depreciation is the array this excludes — 13.98 M USD on PV+E, larger
    than the whole capital spend — so if it ever gets stacked, this fails.
    '''

    costs = figures.annual_costs(opened(key).run.result)
    running = 0.0
    for index in range(costs['span']):
        stacked = sum(line['values'][index] for line in costs['lines'])
        assert stacked == pytest.approx(costs['net'][index], rel=1e-9, abs=1e-6)
        running += costs['net'][index]
        assert costs['cumulative'][index] == pytest.approx(running, rel=1e-9, abs=1e-6)


def test_capital_lands_in_the_build_year_and_replacement_in_one_later_year():
    '''A spot check on shape: this is a plant, and it is built before it runs.'''

    costs = figures.annual_costs(opened('pv_e').run.result)
    by_name = {line['name']: line['values'] for line in costs['lines']}

    assert by_name['Depreciable capital'][0] < 0
    assert all(value == 0 for value in by_name['Depreciable capital'][1:])

    replacement = by_name['Replacement']
    spikes = [year for year, value in enumerate(replacement) if value < 0]
    assert len(spikes) == 1 and spikes[0] > 5


def test_the_peak_year_names_what_dominates_it():
    '''An unexplained spike is a question the figure should answer itself.

    PV+E bills its entire twenty-year grid draw in the final year, at the tariff the
    reference file documents as an upstream typo. A reader seeing a bar eight times the
    height of every other one needs the caption to name it without being asked.

    The share is of the year's *outflow* — 19.87 M of the 29.32 M spent in analysis year
    19 — and not of its net. Net would report 98%, which is arithmetic about a number
    that also contains 7.04 M of loan principal, and the caption would be crediting one
    tariff with spending the figure can see went somewhere else.
    '''

    costs = figures.annual_costs(opened('pv_e').run.result)
    assert costs['driver']['name'] == 'Variable operating'
    assert costs['driver']['year'] == 19
    assert costs['driver']['value'] == pytest.approx(19868515, rel=1e-4)
    assert costs['driver']['spent'] == pytest.approx(29320945, rel=1e-4)
    assert costs['driver']['share'] == pytest.approx(0.6776, abs=5e-4)


def test_a_zero_line_is_marked_rather_than_dropped():
    '''"The engine wrote zero" and "the engine wrote nothing" are different facts.

    The electricity pathway has no variable operating cost and no stack to replace, and
    the engine says so with arrays of zeros. Dropping them would hide that the category
    was considered; drawing them as invisible bars would waste the reader's attention.
    They are marked, and the chart lists them.
    '''

    costs = figures.annual_costs(opened('pv_e_lcoe').run.result)
    zeroed = {line['name'] for line in costs['lines'] if line['zero']}
    assert zeroed == {'Variable operating', 'Replacement'}

    for line in figures.annual_costs(opened('pv_e').run.result)['lines']:
        assert line['zero'] is False


def test_the_peak_driver_ignores_lines_the_engine_zeroed():
    '''A line that is zero everywhere cannot be what dominates a year.'''

    costs = figures.annual_costs(opened('pv_e_lcoe').run.result)
    assert costs['driver']['name'] not in ('Variable operating', 'Replacement')


def test_the_peak_driver_is_an_outflow_not_a_credit():
    '''`pec` books a 127.9 M tax credit in year 19, the largest single entry in the run.

    It is money coming *in*. A driver picked by absolute magnitude would nominate it and
    caption a cost figure with a refund; the 62.7 M of cell replacement in the same year
    is what the year actually spent.
    '''

    driver = figures.annual_costs(opened('pec').run.result)['driver']
    assert driver['name'] == 'Replacement'
    assert driver['value'] > 0


# ---------------------------------------------------------------- series


def test_hourly_candidates_are_hourly_and_nothing_else():
    '''365 daily points are a real series and are not a calendar of hours.

    Offering one as the other misstates the resolution of the model. Battery writes
    daily arrays and must offer no calendar; Photovoltaic writes hourly ones and must.
    '''

    project_ = opened('pv_e')
    assert figures.for_step(project_, 'Battery_Plugin').get('hourly') is None

    hourly = figures.for_step(project_, 'Photovoltaic_Plugin')['hourly']
    rows = {entry['row'] for entry in hourly}
    assert 'PV hourly power generation' in rows
    assert 'Available energy (daily)' not in rows


def test_a_series_is_the_full_undecimated_array():
    '''The digest in a trace is 96 points. A calendar needs all 8,760.'''

    found = figures.series(opened('pv_e'), 'Photovoltaic_Plugin',
                           'Power Generation', 'PV hourly power generation', 'Value')
    assert found['length'] == 8760
    assert len(found['values']) == 8760
    assert found['min'] == 0
    assert found['max'] > 0


def test_a_series_can_select_its_year_and_reports_the_one_it_gave():
    '''Twenty years exist; the stack degrades, so they are not the same array.

    And an out-of-range year is clamped *and said so*. Echoing back the requested year
    would caption year 19's data as year 25.
    '''

    project_ = opened('pv_e')
    first = figures.series(project_, 'Photovoltaic_Plugin', 'Power Generation',
                           'PV hourly power generation', 'Value', year=0)
    last = figures.series(project_, 'Photovoltaic_Plugin', 'Power Generation',
                          'PV hourly power generation', 'Value', year=19)
    assert first['sum'] > last['sum']
    assert first['years'] == 20

    clamped = figures.series(project_, 'Photovoltaic_Plugin', 'Power Generation',
                             'PV hourly power generation', 'Value', year=25)
    assert clamped['year'] == 19


def test_a_series_reads_the_state_of_the_step_that_is_asked_for():
    '''A later step may overwrite the cell, and the caption names the earlier one.

    `Battery_Plugin` replaces `Power Generation > Available energy (hourly)` with a
    scalar. Reading the completed run therefore either fails or returns Battery's value
    under Photovoltaic's heading. Every cell a step offers must be servable *for that
    step*, which is only true if the fetch re-runs to it.
    '''

    project_ = opened('pv_e')
    for step_name in project_.order():
        for entry in figures.for_step(project_, step_name).get('hourly', []):
            found = figures.series(project_, step_name, entry['table'], entry['row'],
                                   entry['column'])
            assert found is not None, f'{step_name} offers {entry["row"]} and cannot serve it'
            assert found['length'] == 8760


def test_asking_a_scalar_for_its_series_is_an_error_not_an_empty_chart():
    api.dispatch('project.open', {'example': 'pv_e'})
    result = api.dispatch('series', {'step': 'Electrolyzer_Plugin', 'table': 'Electrolyzer',
                                     'row': 'Nominal power', 'column': 'Value'})
    assert 'holds no array' in result['error']


# ---------------------------------------------------------------- offering


def test_only_steps_that_earn_a_figure_get_one():
    '''Every step could be given a chart; almost none would be improved by one.'''

    project_ = opened('pv_e')
    assert set(figures.for_step(project_, 'Discounted_Cash_Flow_Plugin')) == {
        'contributions', 'annual_costs'}
    assert figures.for_step(project_, 'Time_Plugin') == {}
    assert figures.for_step(project_, 'Inflation_Plugin') == {}


@pytest.mark.parametrize('key', PATHWAYS)
def test_every_step_of_every_pathway_offers_json_safe_figures(key):
    api.dispatch('project.open', {'example': key})
    for entry in api.dispatch('project.state', {})['rail']:
        json.dumps(api.dispatch('figures', {'step': entry['name']}), allow_nan=False)


def test_a_broken_run_offers_no_figures():
    '''A figure over a model that did not finish would be drawing nothing.'''

    api.dispatch('project.open', {'example': 'pv_e'})
    api.dispatch('cell.edit', {'table': 'Electrolyzer', 'row': 'Nominal power',
                               'column': 'Value', 'text': 'banana'})
    result = api.dispatch('figures', {'step': 'Discounted_Cash_Flow_Plugin'})
    assert result['figures'] == {}


@pytest.mark.parametrize('key', PATHWAYS)
def test_a_calendars_colour_ceiling_is_its_own_largest_hour(key):
    '''Not the largest annual total, which is 2,744x larger for this data.

    `hourly_candidates` publishes the ceiling a calendar normalises against. Taking it
    from a per-year record's `max` — the largest annual *sum* — painted every cell at
    the ink floor while the caption claimed ink was magnitude. Six of twenty calendars
    rendered as solid blocks.
    '''

    project_ = opened(key)
    for step_name in project_.order():
        for entry in figures.for_step(project_, step_name).get('hourly', []):
            found = figures.series(project_, step_name, entry['table'], entry['row'],
                                   entry['column'])
            assert entry['max'] == pytest.approx(found['max'], rel=0.02), \
                f'{key} {step_name} {entry["row"]}'


def test_siblings_that_share_a_scale_share_a_unit():
    '''Step 202 offers an irradiance in kWh/m2 beside two energies in J.

    A shared ceiling across those is a factor of 8e13, and prints the Joule magnitude
    under a kWh/m2 label. The client groups by unit before sharing; this pins that the
    payload gives it what it needs to.
    '''

    candidates = figures.for_step(opened('pv_e'), 'Photovoltaic_Plugin')['hourly']
    units = {entry['unit'] for entry in candidates}
    assert len(units) > 1, 'this step is the reason the rule exists'
    assert all(entry['max'] for entry in candidates)
