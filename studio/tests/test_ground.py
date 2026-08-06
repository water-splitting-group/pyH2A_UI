'''The ground: parse, run, trace. If these fail nothing above them is worth reading.

Every assertion here is about a number the engine owns, not about this app's
formatting. That is the point: the studio's whole claim is that what it shows is
what pyH2A computed, so the tests compare against pyH2A's own published costs and
against a plain run of the engine.
'''

import json

import numpy as np
import pytest
from pyh2a_studio.core import cells, engine, examples, grammar, trace


@pytest.mark.parametrize('example', examples.EXAMPLES, ids=lambda e: e.key)
def test_every_example_reproduces_its_published_cost(example):
    '''The headline number matches what upstream's own test asserts.'''

    inp = grammar.engine_dict(example.markdown())
    result = engine.run(inp)
    assert result.levelized_cost.supplied_value == pytest.approx(
        example.reference_cost, abs=5e-5
    )


@pytest.mark.parametrize('example', examples.EXAMPLES, ids=lambda e: e.key)
def test_parse_serialize_round_trips_to_the_same_cost(example):
    '''A structured edit path cannot change the answer when it changes nothing.

    Parse to cells, serialize back, re-parse through the engine: the cost must be
    bit-identical. This is what licenses every form in the app to write markdown.
    '''

    original = example.markdown()
    document = grammar.parse_document(original)
    round_tripped = grammar.serialize_document(document)

    before = engine.run(grammar.engine_dict(original)).levelized_cost.supplied_value
    after = engine.run(grammar.engine_dict(round_tripped)).levelized_cost.supplied_value
    assert before == after


@pytest.mark.parametrize('example', examples.EXAMPLES, ids=lambda e: e.key)
def test_trace_agrees_with_a_plain_run(example):
    '''Stepping the workflow by hand produces the engine's own answer.

    `trace.build` drives `execute_plugin` itself instead of calling
    `Discounted_Cash_Flow`. If the two ever disagree, the trace is lying about the
    model and every screen built on it is lying too.
    '''

    inp = grammar.engine_dict(example.markdown())
    plain = engine.run(inp)
    traced = trace.build(inp)

    assert traced.failed is None
    assert traced.result is not None
    assert traced.result.levelized_cost.supplied_value == pytest.approx(
        plain.levelized_cost.supplied_value, rel=1e-12
    )


@pytest.mark.parametrize('example', examples.EXAMPLES, ids=lambda e: e.key)
def test_every_step_ran_and_is_accounted_for(example):
    '''One step per Workflow entry, in the engine's order, all ok.'''

    inp = grammar.engine_dict(example.markdown())
    order = engine.workflow_order(inp)
    traced = trace.build(inp)

    assert [step.name for step in traced.steps] == order
    assert all(step.status == 'ok' for step in traced.steps)
    assert all(step.duration_ms >= 0 for step in traced.steps)


def test_visible_grows_monotonically_through_the_run():
    '''What a step can see only ever includes what earlier steps could see.

    A cell never disappears mid-run — plugins add and overwrite, never delete. If
    this fails, "available at this position" is not a well-defined idea and the
    worksheet's middle claim collapses.
    '''

    inp = grammar.engine_dict(examples.get('pv_e').markdown())
    traced = trace.build(inp)

    seen = set()
    for step in traced.steps:
        keys = set(step.visible)
        assert seen <= keys, f'{step.name} lost {len(seen - keys)} cells'
        seen = keys


def test_literals_are_visible_to_every_step():
    '''The user's own inputs stay in scope for the whole run.

    This is the property that makes the file worth showing beside every step:
    anything authored is reachable from anywhere, so a reference can always be
    written to it.
    '''

    inp = grammar.engine_dict(examples.get('pv_e').markdown())
    traced = trace.build(inp)

    assert traced.literals
    for step in traced.steps:
        missing = set(traced.literals) - set(step.visible)
        assert not missing, f'{step.name} cannot see {sorted(missing)[:3]}'


def test_a_step_writes_what_it_declares():
    '''Declared outputs actually show up in the diff.

    Not the reverse — plugins legitimately write more than they declare, and the
    audit found specs that lie. But a declared output that never appears means the
    spec cannot be trusted for that plugin, and the UI must not present it as
    truth.
    '''

    inp = grammar.engine_dict(examples.get('pv_e').markdown())
    traced = trace.build(inp)
    step = traced.step('Electrolyzer_Plugin')
    _, declared = engine.plugin_io('Electrolyzer_Plugin', engine.functional_unit_token(inp))

    wrote = {(table, row) for table, row, _ in step.wrote}
    for table, rows in declared.items():
        for row in rows:
            assert (table, row) in wrote, f'declared {table} > {row} never appeared'


def test_overwriting_a_name_is_visible_as_a_change():
    '''Power_Management redefines what an earlier name means, and the trace sees it.

    `Power Generation > Available energy (daily)` means "generated" where the PV
    plugin writes it, and is drawn down by each consumer in turn until
    Power_Management leaves it meaning "still unspent after allocation". Four steps
    write it. An app that reads the end state and labels it with the early meaning is
    wrong; this pins that the trace can tell all four apart.

    The count is load-bearing. An earlier version of `cells.describe` rendered these
    per-year dicts as the text `{0.0, 1.0, 2.0, …}` — their *keys* — which is
    identical at every step no matter how the values move, and reported two writers
    instead of four. A digest that cannot see a change is a digest that hides one.
    '''

    inp = grammar.engine_dict(examples.get('pv_e').markdown())
    traced = trace.build(inp)

    key = ('Power Generation', 'Available energy (daily)', 'Value')
    writers = [step.name for step in traced.steps if key in step.wrote]
    assert writers == ['Photovoltaic_Plugin', 'Electrolyzer_Plugin',
                       'Battery_Plugin', 'Power_Management_Plugin']


def test_a_broken_input_fails_as_data_and_names_the_step():
    '''A plugin that throws becomes a step with an error, not an exception.

    Requirement: the user has to see errors as they happen. That means a failure
    must arrive as a located, described step — with everything before it intact and
    inspectable — rather than as a traceback that discards the run.
    '''

    document = grammar.parse_document(examples.get('pv_e').markdown())
    grammar.set_cell(document, 'Electrolyzer', 'Nominal power', 'Value', 'not a number')
    inp = grammar.engine_dict(grammar.serialize_document(document))

    traced = trace.build(inp)

    assert traced.failed is not None
    failed_step = traced.step(traced.failed)
    assert failed_step.status == 'error'
    assert failed_step.error
    assert failed_step.visible, 'a failed step must still report what it could see'

    order = [step.name for step in traced.steps]
    after = order[order.index(traced.failed) + 1:]
    assert all(traced.step(name).status == 'skipped' for name in after)
    assert traced.result is None


def test_describe_reports_the_authored_magnitude_not_the_si_base():
    '''`5500 kW`, never `5500000 kW`.

    The single most important display rule in the app, pinned on the cell the bug
    originally appeared on. Note *when* it is pinned: a `Value` is a plain number as
    authored and becomes a `Quantity` only once its own plugin processes the table.
    Both stages are visible in a trace and both must read 5500.
    '''

    inp = grammar.engine_dict(examples.get('pv_e').markdown())
    key = ('Electrolyzer', 'Nominal power', 'Value')
    traced = trace.build(inp)

    as_authored = traced.literals[key]
    assert as_authored == {'form': 'number', 'value': pytest.approx(5500)}

    as_processed = traced.steps[-1].visible[key]
    assert as_processed['unit'] == 'kW'
    assert as_processed['value'] == pytest.approx(5500)
    assert as_processed['base_value'] == pytest.approx(5.5e6)


def test_describe_digests_an_hourly_array_without_carrying_it():
    '''8,760 hours become an extent and a drawable envelope.'''

    inp = grammar.engine_dict(examples.get('pv_e').markdown())
    traced = trace.build(inp)
    key = ('Hourly Irradiation', 'No tracking', 'Value')
    record = traced.literals.get(key) or traced.steps[-1].visible[key]

    assert cells.is_series(record)
    digest = record['array']
    assert digest['length'] == 8760
    assert digest['kind'] == 'series'
    assert len(digest['envelope']) <= cells.ENVELOPE_POINTS
    assert digest['min'] <= digest['max']


def test_describe_survives_every_value_in_every_pathway():
    '''No engine value crashes the describer, and every record is JSON-safe.

    The describer is the only path from engine memory to the browser. A type it
    cannot handle is a blank region on a screen, so this walks every cell of every
    pathway's final state.
    '''

    for example in examples.EXAMPLES:
        traced = trace.build(grammar.engine_dict(example.markdown()))
        snapshot = traced.steps[-1].visible
        assert snapshot, example.key
        json.dumps({'/'.join(k): v for k, v in snapshot.items()}, allow_nan=False)


def test_flat_and_ramp_arrays_are_named_as_such():
    '''A constant series is not a curve, and a year index is not data.

    Screens draw these three differently; conflating them produced a meaningless
    line in an earlier build.
    '''

    assert cells.describe(np.zeros(20))['array']['kind'] == 'flat'
    assert cells.describe(np.arange(20.0))['array']['kind'] == 'ramp'
    assert cells.describe(np.array([3.0, 1.0, 2.0]))['array']['kind'] == 'series'


def test_the_functional_unit_is_read_from_the_file():
    '''`pv_e_lcoe` prices electricity; nothing may assume mass.'''

    mass = grammar.engine_dict(examples.get('pv_e').markdown())
    energy = grammar.engine_dict(examples.get('pv_e_lcoe').markdown())

    assert engine.functional_unit_token(mass) == 'kg'
    assert engine.functional_unit_token(energy) == 'kWh'


def test_plugin_spec_carries_bounds_dimension_and_description():
    '''The refactor's metadata is present and is what the worksheet will show.

    Jacob's ask — every value shows its range, its unit and its meaning — is only
    possible because the plugin declares all three. This asserts the shape the UI
    depends on, so an upstream change that drops it fails here rather than
    silently emptying a panel.
    '''

    declared, _ = engine.plugin_io('Electrolyzer_Plugin')
    field = declared['Electrolyzer']['Minimum capacity']

    assert tuple(field['Value']['bounds']) == (0, 1)
    assert field['Unit']['dimension'] == 'dimensionless'
    assert field['optional'] is False
    assert 'between 0 and 1' in field['description']
