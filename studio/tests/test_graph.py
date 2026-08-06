'''The workflow as a graph, and editing it.

Two claims under test. The edges are real — an edge exists because a later step reads
a cell an earlier step wrote, taken from the trace rather than from declarations, so
it reflects what happened. And the workflow is editable in place: a step can be added
between any two others, moved, or removed, with the model re-running each time.
'''

import json

import pytest
from pyh2a_studio import api
from pyh2a_studio.core import examples, graph, project


@pytest.fixture(scope='module')
def pv_e():
    example = examples.get('pv_e')
    return project.Project.open(example.markdown(), origin=example.file_name)


@pytest.fixture(autouse=True)
def clean_sessions():
    api.SESSIONS.clear()
    yield
    api.SESSIONS.clear()


def call(op, **payload):
    result = api.dispatch(op, payload)
    assert 'error' not in result, f'{op}: {result.get("error")}'
    return result


# ---------------------------------------------------------------- edges


def test_edges_run_forwards_only(pv_e):
    '''A dependency on a later step is not a dependency; it is a bug in the graph.'''

    built = graph.build(pv_e)
    order = [node['name'] for node in built['nodes']]
    for edge in built['edges']:
        assert order.index(edge['from']) < order.index(edge['to']), edge


def test_every_edge_names_the_cells_that_travel_it(pv_e):
    '''An arrow without cargo tells a reader nothing.'''

    for edge in graph.build(pv_e)['edges']:
        assert edge['cells'], edge
        assert edge['count'] == len(edge['cells'])
        assert all(' › ' in cell for cell in edge['cells'])


def test_the_electrolyzer_feeds_the_things_that_consume_hydrogen(pv_e):
    '''A spot check against the physics, not against the code that drew it.'''

    edges = graph.build(pv_e)['edges']
    from_electrolyzer = {edge['to'] for edge in edges if edge['from'] == 'Electrolyzer_Plugin'}
    assert 'Stored_Power_Electrolysis_Plugin' in from_electrolyzer
    assert 'Power_Management_Plugin' in from_electrolyzer


def test_a_file_authored_value_is_not_an_edge(pv_e):
    '''Literals are available everywhere; drawing them would connect everything.'''

    built = graph.build(pv_e)
    time_edges = [edge for edge in built['edges'] if edge['from'] == 'Time_Plugin']
    for edge in time_edges:
        assert all(cell.startswith('Time › ') for cell in edge['cells']), edge


# ---------------------------------------------------------------- insertion


def test_there_is_an_insertion_point_before_after_and_between_every_step(pv_e):
    nodes = graph.build(pv_e)['nodes']
    points = graph.build(pv_e)['insertion_points']
    assert len(points) == len(nodes) + 1
    assert points[0]['after'] is None
    assert points[-1]['before'] is None


def test_every_gap_is_insertable_including_tight_ones(pv_e):
    '''Consecutive positions like 201 and 202 still leave room, because 201.5 sorts.

    The engine parses `Position` with `num()` and sorts on the result, so a fractional
    position is ordinary. Without this, two thirds of a shipped workflow would have
    nowhere to put a step and the user would be told to renumber by hand.
    '''

    for point in graph.build(pv_e)['insertion_points']:
        assert point['position'] is not None, point


def test_an_insertion_position_really_lands_between_its_neighbours(pv_e):
    built = graph.build(pv_e)
    by_name = {node['name']: node['position'] for node in built['nodes']}
    for point in built['insertion_points']:
        if point['after']:
            assert point['position'] > by_name[point['after']]
        if point['before']:
            assert point['position'] < by_name[point['before']]


# ---------------------------------------------------------------- editing


def test_adding_a_plugin_puts_it_in_execution_order():
    call('project.open', example='pv_e')
    result = call('workflow.add', plugin='Solar_Concentrator_Plugin', position=201.5)

    order = [(node['position'], node['name']) for node in result['rail']]
    assert (201.5, 'Solar_Concentrator_Plugin') in order
    assert order.index((201.5, 'Solar_Concentrator_Plugin')) == order.index((202, 'Photovoltaic_Plugin')) - 1


def test_adding_a_plugin_that_lacks_its_inputs_fails_loudly_and_usefully():
    '''The expected outcome of adding a step: it needs things, and it says which.

    This is not an error state to be prevented. Adding a plugin in order to find out
    what it wants is a normal way to work, so the failure has to arrive as a list of
    named gaps rather than as a refusal.
    '''

    call('project.open', example='pv_e')
    call('workflow.add', plugin='Solar_Concentrator_Plugin', position=201.5)
    built = call('graph')['graph']

    assert call('project.state')['project']['failed'] == 'Solar_Concentrator_Plugin'
    rows = {(entry['table'], entry['row']) for entry in built['unmet']}
    assert ('Solar Concentrator', 'Concentration factor') in rows


def test_an_unmet_input_names_the_plugins_that_would_supply_it():
    '''"Missing" is half a message; "PEC writes this" is the other half.'''

    call('project.open', example='pv_e')
    call('workflow.add', plugin='Solar_Concentrator_Plugin', position=201.5)
    unmet = call('graph')['graph']['unmet']

    cells = next(entry for entry in unmet if entry['row'] == 'Number')
    assert [entry['name'] for entry in cells['suggestions']] == ['PEC_Plugin']
    assert cells['suggestions'][0]['label'] == 'PEC'
    assert cells['suggestions'][0]['in_workflow'] is False

    typed = next(entry for entry in unmet if entry['row'] == 'Concentration factor')
    assert typed['suggestions'] == [], 'a value only a person can supply has no supplier'


def test_a_step_is_never_offered_as_the_supplier_of_its_own_input():
    '''`Solar_Concentrator` declares `Solar collection area` as both an input and an
    output. That is a fact about the spec, not an instruction to add the step you have
    just added — and listing it contradicted the heading the row sat under.'''

    call('project.open', example='pv_e')
    call('workflow.add', plugin='Solar_Concentrator_Plugin', position=201.5)

    area = next(entry for entry in call('graph')['graph']['unmet']
                if entry['row'] == 'Solar collection area')
    assert 'Solar_Concentrator_Plugin' not in [e['name'] for e in area['suggestions']]


def test_a_supplier_that_runs_too_late_is_a_position_not_an_addition():
    '''`Photovoltaic` writes `Solar collection area` and sits half a position after the
    step that needs it. Offering to add a plugin already in the workflow is no answer;
    the fix is to move one of them, and the panel now has what it needs to say so.'''

    call('project.open', example='pv_e')
    call('workflow.add', plugin='Solar_Concentrator_Plugin', position=201.5)

    area = next(entry for entry in call('graph')['graph']['unmet']
                if entry['row'] == 'Solar collection area')
    assert area['runs_later'] == ['Photovoltaic']
    assert any(entry['in_workflow'] for entry in area['suggestions'])


def test_the_scope_payload_carries_no_internal_sort_key():
    '''Ordering is the server's business; the client never reads it.'''

    call('project.open', example='pv_e')
    built = call('step', step='Photovoltaic_Plugin')['frame']
    assert all('sort' not in group for group in built['scope']['groups'])


def test_a_multiplicand_resolves_before_its_own_step_has_processed_it():
    '''Step 202 multiplies 1.5 by the electrolyzer's nominal power, which step 203
    processes. Reading only the Quantity shape printed the word `unresolved` on a row
    whose own product proves the value: 8,250 / 1.5 = 5,500 kW.'''

    call('project.open', example='pv_e')
    field = next(entry for table in call('step', step='Photovoltaic_Plugin')['frame']['needs']
                 for entry in table['fields'] if entry['row'] == 'Nominal power')
    assert field['path']['as_requested'] == pytest.approx(5500)
    assert field['path']['requested_unit'] == 'kW'


def test_removing_a_step_restores_the_original_answer():
    '''Add and remove is a round trip. If it is not, the edit path is losing something.'''

    call('project.open', example='pv_e')
    before = call('project.state')['project']['cost']['value']

    call('workflow.add', plugin='Solar_Concentrator_Plugin', position=201.5)
    call('workflow.remove', plugin='Solar_Concentrator_Plugin')

    assert call('project.state')['project']['cost']['value'] == pytest.approx(before, rel=1e-12)


def test_removing_a_step_keeps_the_tables_it_used():
    '''Taking Battery out of the workflow must not destroy the Battery table.

    Someone removing a step is usually asking "what does the model look like without
    this", and the answer has to be reversible. Deleting their authored data as a side
    effect would make the question expensive to ask.
    '''

    call('project.open', example='pv_e')
    call('workflow.remove', plugin='Battery_Plugin')
    source = call('project.source')['markdown']

    assert '# Battery' in source
    assert 'Battery_Plugin' not in source.split('# Display Parameters')[0]


def test_moving_a_step_changes_execution_order():
    call('project.open', example='pv_e')
    result = call('workflow.move', plugin='Battery_Plugin', position=206)

    order = [node['name'] for node in result['rail']]
    assert order.index('Battery_Plugin') > order.index('Stored_Power_Electrolysis_Plugin')


def test_adding_a_plugin_already_present_is_refused():
    call('project.open', example='pv_e')
    result = api.dispatch('workflow.add', {'plugin': 'Battery_Plugin', 'position': 250})
    assert 'already in this workflow' in result['error']


def test_a_position_is_written_without_a_pointless_decimal():
    '''`202`, not `202.0`. The file is read by people.'''

    call('project.open', example='pv_e')
    call('workflow.add', plugin='Solar_Concentrator_Plugin', position=250.0)
    assert any(row.split('|')[1].strip() == '250'
               for row in call('project.source')['markdown'].splitlines()
               if row.startswith('Solar_Concentrator_Plugin '))


# ---------------------------------------------------------------- catalogue


def test_the_catalogue_lists_every_installed_plugin(pv_e):
    entries = graph.catalogue(pv_e)
    names = {entry['name'] for entry in entries}

    assert len(names) == 22
    assert 'Solar_Thermal_Plugin' in names
    assert not any(name.startswith('Test_Plugin') for name in names)


def test_the_catalogue_marks_what_is_already_in_use(pv_e):
    by_name = {entry['name']: entry for entry in graph.catalogue(pv_e)}
    assert by_name['Battery_Plugin']['in_use'] is True
    assert by_name['Solar_Thermal_Plugin']['in_use'] is False


def test_the_catalogue_ranks_the_plugins_this_project_could_actually_feed(pv_e):
    '''A plugin whose inputs already exist is a better offer than one needing twenty.'''

    entries = [entry for entry in graph.catalogue(pv_e) if not entry['in_use']]
    ratios = [entry['satisfied'] / max(entry['needs'], 1) for entry in entries]
    assert ratios == sorted(ratios, reverse=True)


def test_the_catalogue_says_what_each_plugin_makes(pv_e):
    by_name = {entry['name']: entry for entry in graph.catalogue(pv_e)}
    thermal = by_name['Solar_Thermal_Plugin']
    assert thermal['makes_count'] > 0
    assert all(' › ' in entry for entry in thermal['makes'])


def test_graph_and_catalogue_are_json_safe():

    for key in ('pv_e', 'thermal', 'pec', 'photocatalytic', 'pv_e_lcoe'):
        call('project.open', example=key)
        json.dumps(api.dispatch('graph', {}), allow_nan=False)
        json.dumps(api.dispatch('plugins', {}), allow_nan=False)
