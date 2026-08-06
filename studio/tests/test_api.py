'''The API contract: every op, its shape, and its failure mode.

The client is JavaScript and cannot be type-checked against Python, so this suite is
the only thing holding the two halves together. It asserts the *shape* every op
returns — the keys a screen reads — and that a failure comes back as a value rather
than a traceback.
'''

import json

import numpy as np
import pytest
from pathlib import Path
from pyh2a_studio import api
from pyH2A.Utilities.Unit_Handler.quantity import Quantity

from pyh2a_studio.core import cells, engine
from pyh2a_studio.core import examples, refs


@pytest.fixture(autouse=True)
def clean_sessions():
    api.SESSIONS.clear()
    yield
    api.SESSIONS.clear()


def call(op, **payload):
    result = api.dispatch(op, payload)
    assert 'error' not in result, f'{op}: {result.get("error")}'
    return result


def holds_row(markdown, *cells):
    """True when the file holds a table row with exactly these cells.

    Asserting on raw text (`'Plant modules | 3 |' in markdown`) broke on every one of
    these the day the serializer started padding columns to align the pipes. That was a
    formatting change that moved no number, and eight tests failed for it. The cells are
    the claim; the spacing between them is the serializer's business.

    An empty trailing cell counts, so `holds_row(md, 'Compressor', '250000', '', 'USD')`
    still asserts the unit landed in the fourth column and nothing landed in the third.
    """

    wanted = [cell.strip() for cell in cells]
    return any([cell.strip() for cell in line.split('|')] == wanted
               for line in markdown.splitlines() if '|' in line)


def open_pv_e():
    return call('project.open', example='pv_e')


# ---------------------------------------------------------------- basics


def test_unknown_op_lists_the_known_ones():
    '''A typo in a client call should be self-diagnosing.'''

    result = api.dispatch('project.opne')
    assert 'unknown operation' in result['error']
    assert 'project.open' in result['known']


def test_every_op_is_reachable_and_returns_a_dict():
    for name in api.OPS:
        result = api.dispatch(name, {})
        assert isinstance(result, dict), name


def test_an_op_before_anything_is_open_says_what_to_do():
    result = api.dispatch('step', {'step': 'Time_Plugin'})
    assert 'project.open first' in result['error']


def test_examples_lists_the_bundled_pathways():
    result = call('examples')
    keys = {example['key'] for example in result['examples']}
    assert keys == {'pv_e', 'thermal', 'pec', 'photocatalytic', 'pv_e_lcoe'}
    assert all(example['reference_cost'] > 0 for example in result['examples'])


# ---------------------------------------------------------------- opening


def test_opening_an_example_returns_its_cost_and_its_rail():
    result = open_pv_e()
    assert result['project']['cost']['value'] == pytest.approx(4.1943, abs=5e-5)
    assert result['project']['cost']['unit'] == 'USD/kg'
    assert result['project']['failed'] is None
    assert len(result['rail']) == 17
    assert result['rail'][0]['position'] == 100


def test_opening_reports_the_functional_unit_from_the_file():
    assert call('project.open', example='pv_e')['project']['functional_unit'] == 'kg'
    assert call('project.open', example='pv_e_lcoe')['project']['functional_unit'] == 'kWh'


def test_opening_unparseable_markdown_is_an_answer_not_a_crash():
    '''The user gets a message they can act on, not a stack trace and not silence.

    The refusal used to arrive as `project.error` and the front door dropped it on the
    floor. It is now its own shape, and when the engine produced a real sentence about
    the text that sentence leads — it is more use than any category the app could put
    above it.
    '''

    refused = api.dispatch('project.open', {'markdown': '| leading | pipes |\n'})['refused']
    assert 'pipe' in refused['headline'].lower()
    assert 'Remove the outer pipes' in refused['headline']
    assert 'no `#` headings' in refused['detail']


def test_opening_needs_something_to_open():
    assert 'starter' in api.dispatch('project.open', {})['error']


def test_a_starter_opens_a_project_that_already_runs():
    '''A blank plant is not blank: it is the smallest thing that produces an answer.

    Everything about it is wrong for any real pathway, and that is the point — nothing
    is broken, so every wrong thing is a field you can see and change rather than an
    error you have to clear first.
    '''

    result = call('project.open', starter='tea_mass', name='Jacob test')
    assert result['project']['name'] == 'Jacob test'
    assert result['project']['cost']['value'] == pytest.approx(5.5044, abs=1e-3)
    assert result['project']['failed'] is None
    assert result['project']['problems'] == 0
    assert result['project']['dirty'] is True
    assert len(result['rail']) == 9


def test_a_starter_names_the_first_values_worth_changing():
    '''A running scaffold hands you forty placeholders and no route in.'''

    result = call('project.open', starter='tea_mass')
    wanted = {(entry['table'], entry['row']) for entry in result['teaches']}
    assert ('Direct Capital Costs - Plant', 'Plant') in wanted
    assert ('Technical Operating Parameters and Specifications',
            'Plant design capacity') in wanted


def test_every_field_a_starter_points_at_actually_exists():
    '''A coach mark on a selector that matches nothing is an instruction to nowhere.'''

    call('project.open', starter='tea_mass')
    opened = api.SESSIONS['main']
    present = {(table.name, row)
               for table in opened.effective.values() for row in table.rows}
    for entry in call('project.open', starter='tea_mass')['teaches']:
        assert (entry['table'], entry['row']) in present, entry


def test_the_catalogue_offers_both_published_pathways_and_scaffolds():
    result = call('examples')
    assert {entry['key'] for entry in result['examples']} == {
        'pv_e', 'thermal', 'pec', 'photocatalytic', 'pv_e_lcoe'}
    assert [entry['key'] for entry in result['starters']] == ['tea_mass']


def test_source_returns_the_exact_text_that_was_opened():
    '''The download must reproduce the numbers on screen. Byte-for-byte is the test.'''


    open_pv_e()
    assert call('project.source')['markdown'] == examples.get('pv_e').markdown()


# ---------------------------------------------------------------- stepping


def test_a_step_frame_carries_needs_scope_and_produces():
    open_pv_e()
    built = call('step', step='Electrolyzer_Plugin')['frame']

    assert built['step']['position'] == 203
    assert built['step']['summary']
    assert any(table['table'] == 'Electrolyzer' for table in built['needs'])
    assert built['scope']['total'] > 80
    assert built['produces']['count'] > 0


def test_asking_for_a_step_that_does_not_exist_lists_the_ones_that_do():
    open_pv_e()
    result = api.dispatch('step', {'step': 'Nope_Plugin'})
    assert 'not a step' in result['error']
    assert 'Electrolyzer_Plugin' in result['error']


# ---------------------------------------------------------------- editing


def test_an_edit_reports_the_cost_on_both_sides():
    '''The consequence arrives with the change, not on another screen.'''

    open_pv_e()
    result = call('cell.edit', table='Electrolyzer', row='Nominal power',
                  column='Value', text='6000')

    assert result['before'] == pytest.approx(4.1943, abs=5e-5)
    assert result['after'] == pytest.approx(4.2624, abs=5e-4)
    assert result['project']['dirty'] is True


def test_an_edit_persists_into_the_source():
    open_pv_e()
    call('cell.edit', table='Electrolyzer', row='Nominal power', column='Value',
         text='6000')
    assert holds_row(call('project.source')['markdown'],
                 'Nominal power', '6000', 'kW',
                 'Production of ca. 1 t of H2 per day to compare with PEC and '
                 'photocatalytic models')


def test_an_edit_can_return_the_open_step_in_the_same_round_trip():
    open_pv_e()
    result = call('cell.edit', table='Electrolyzer', row='Nominal power',
                  column='Value', text='6000', step='Electrolyzer_Plugin')
    field = next(f for table in result['frame']['needs'] for f in table['fields']
                 if f['row'] == 'Nominal power')
    assert field['text'] == '6000'


def test_an_edit_that_breaks_the_model_is_a_result_not_an_error():
    '''The failure arrives located — and the engine locates it wrongly.

    Typing `banana` into `Electrolyzer > Nominal power`, a cell belonging to step 203,
    makes the engine fail at step **202**, `Photovoltaic_Plugin`, with
    `can't multiply sequence by non-int of type 'float'`. Photovoltaic never reads that
    cell: paths resolve lazily, so whichever plugin first touches a reference to a
    broken value inherits the blame.

    Both facts are asserted, because the studio has to show both. The engine's verdict
    is what actually happened and cannot be suppressed; the field-level check is the
    only thing that points at the row the user must fix.
    '''

    open_pv_e()
    result = call('cell.edit', table='Electrolyzer', row='Nominal power',
                  column='Value', text='banana')

    assert result['after'] is None
    assert result['project']['failed'] == 'Photovoltaic_Plugin'

    flagged = {entry['label'] for entry in result['rail'] if entry['problems']}
    assert 'Electrolyzer' in flagged


def test_editing_a_cell_that_does_not_exist_refuses_by_default():
    '''Creating a row as a side effect of a typo is how files grow dead cells.'''

    open_pv_e()
    result = api.dispatch('cell.edit', {'table': 'Electrolyzer', 'row': 'Nomnal power',
                                        'column': 'Value', 'text': '1'})
    assert 'error' in result


def test_editing_can_create_a_cell_when_asked():
    open_pv_e()
    result = call('cell.edit', table='Electrolyzer', row='Stack lifetime',
                  column='Value', text='42', create=True)
    assert result['project']['cost'] is not None
    assert any(row.strip().startswith('Stack lifetime')
               and row.split('|')[1].strip() == '42'
               for row in call('project.source')['markdown'].splitlines()
               if '|' in row)


def test_replacing_the_source_reopens_the_project():
    open_pv_e()
    markdown = call('project.source')['markdown'].replace('Nominal power | 5,500',
                                                          'Nominal power | 7,000')
    result = call('source.replace', markdown=markdown)
    assert result['project']['cost']['value'] == pytest.approx(4.2267, abs=1e-3)


# ---------------------------------------------------------------- references


def test_reference_check_validates_against_a_step_position():
    '''The same string is fine at one step and early at another.

    `Electrolyzer > H2 production (yearly)` is written at 203. Asked at 900 it
    resolves; asked at 100 it does not exist yet and the engine would read 1.
    '''

    open_pv_e()
    text = '{Electrolyzer > H2 production (yearly) > Value, kg}'

    late = call('reference.check', text=text, step='Discounted_Cash_Flow_Plugin')
    assert late['check']['status'] == 'ok'

    early = call('reference.check', text=text, step='Time_Plugin')
    assert early['check']['status'] == 'early'
    assert early['check']['position'] == 203


def test_reference_search_finds_a_cell_by_words_from_its_name():
    open_pv_e()
    result = call('reference.search', query='nominal power',
                  step='Capital_Cost_Plugin')

    rows = [(hit['table'], hit['row']) for hit in result['results']]
    assert ('Electrolyzer', 'Nominal power') in rows
    assert ('Photovoltaic', 'Nominal power') in rows


def test_reference_search_returns_an_insertable_string():
    '''Autocomplete must offer the exact text that will resolve.'''


    open_pv_e()
    available = set(api.SESSIONS['main'].available_at('Capital_Cost_Plugin'))
    for hit in call('reference.search', query='nominal', step='Capital_Cost_Plugin')['results']:
        assert refs.check(hit['reference'], available)['status'] == 'ok', hit


def test_reference_search_ranks_in_scope_before_not_yet():
    '''A value you can use now outranks one you would have to wait for.'''

    open_pv_e()
    results = call('reference.search', query='cost', step='Capital_Cost_Plugin')['results']
    pending = [index for index, hit in enumerate(results) if hit['pending']]
    in_scope = [index for index, hit in enumerate(results) if not hit['pending']]
    assert not in_scope or not pending or max(in_scope) < min(pending)


def test_reference_search_marks_a_pending_hit_with_the_step_that_makes_it():
    open_pv_e()
    results = call('reference.search', query='levelized cost', step='Time_Plugin')['results']
    hit = next(entry for entry in results if entry['row'] == 'Levelized cost')
    assert hit['pending']['position'] == 900


def test_reference_search_narrows_as_words_are_added():
    open_pv_e()
    broad = call('reference.search', query='power', step='Capital_Cost_Plugin')['total']
    narrow = call('reference.search', query='power nominal',
                  step='Capital_Cost_Plugin')['total']
    assert 0 < narrow < broad


# ---------------------------------------------------------------- transport


def test_every_response_is_json_serialisable_without_nan():
    '''NaN is not JSON. A single one blanks the screen it reaches.'''

    open_pv_e()
    for op, payload in [
        ('examples', {}),
        ('project.state', {}),
        ('project.source', {}),
        ('step', {'step': 'Discounted_Cash_Flow_Plugin'}),
        ('reference.search', {'query': 'cost'}),
        ('reference.check', {'text': '{A > B > C, kW}'}),
        ('cell.edit', {'table': 'Electrolyzer', 'row': 'Nominal power',
                       'column': 'Value', 'text': '5600'}),
    ]:
        json.dumps(api.dispatch(op, payload), allow_nan=False)


def test_every_step_of_every_pathway_serialises():
    '''The heaviest payload in the app, on every pathway, through the real encoder.'''

    for key in ('pv_e', 'thermal', 'pec', 'photocatalytic', 'pv_e_lcoe'):
        call('project.open', example=key)
        for entry in call('project.state')['rail']:
            json.dumps(api.dispatch('step', {'step': entry['name']}), allow_nan=False)


def test_sessions_do_not_share_a_project():
    '''Two tabs must not overwrite each other's edits.'''

    call('project.open', example='pv_e', session='a')
    call('project.open', example='thermal', session='b')
    call('cell.edit', session='a', table='Electrolyzer', row='Nominal power',
         column='Value', text='6000')

    assert call('project.state', session='b')['project']['cost']['value'] == pytest.approx(
        3.2706, abs=5e-5)


def test_every_response_reports_its_own_cost_in_milliseconds():
    open_pv_e()
    assert call('step', step='Electrolyzer_Plugin')['took_ms'] >= 0


def test_a_session_survives_many_others_while_it_is_being_used():
    '''An active tab is never the one evicted.

    Sessions are capped because each holds a full trace — a few megabytes — and a
    long-running server would otherwise keep one per tab ever opened. Eviction is
    least-recently-used and *touching* counts as use, so a tab someone is working in
    cannot be dropped by traffic from other tabs.
    '''

    call('project.open', example='pv_e', session='mine')
    for index in range(api.MAX_SESSIONS + 6):
        call('project.open', example='thermal', session=f'other{index}')
        call('project.state', session='mine')

    assert 'mine' in api.SESSIONS
    assert call('project.state', session='mine')['project']['cost']['value'] == pytest.approx(
        4.1943, abs=5e-5)


def test_an_idle_session_is_eventually_dropped():
    '''It comes back as "nothing open", which is what the client handles on first load.

    An op that *needs* a project still says so by name; `project.state` is the one op
    whose honest answer to an unknown session is "nothing", because that is also every
    fresh tab's first call.
    '''

    call('project.open', example='pv_e', session='idle')
    for index in range(api.MAX_SESSIONS + 2):
        call('project.open', example='thermal', session=f'busy{index}')

    assert api.dispatch('project.state', {'session': 'idle'})['project'] is None
    assert 'project.open first' in api.dispatch('step', {'session': 'idle',
                                                         'step': 'Time_Plugin'})['error']


def test_a_failed_op_leaves_the_session_usable():
    '''An edit the app cannot render must not be adopted.

    `frame.rail` imports every plugin the Workflow names, so one typo in a plugin name
    raises *after* the edit is applied. Storing first left the session holding a project
    no screen could render — `project.state`, `graph` and `step` all raised the same
    ModuleNotFoundError forever — while the client, which reads an error response as
    "nothing happened", showed a toast and carried on against a dead session.
    '''

    call('project.open', example='pv_e')
    markdown = call('project.source')['markdown'].replace(
        '\nPhotovoltaic_Plugin |', '\nPhotovoltaik_Plugin |')

    assert 'error' in api.dispatch('source.replace', {'markdown': markdown})

    survived = call('project.state')
    assert survived['project']['cost']['value'] == pytest.approx(4.1943, abs=5e-5)
    assert len(survived['rail']) == 17


def test_adding_an_unknown_plugin_names_it_and_suggests_a_real_one():
    call('project.open', example='pv_e')
    result = api.dispatch('workflow.add', {'plugin': 'Electrolyser_Plugin', 'position': 250})
    assert 'no plugin named Electrolyser_Plugin is installed' in result['error']
    assert 'Electrolyzer_Plugin' in result['error']


def test_a_file_that_does_not_parse_is_kept_so_the_editor_can_show_why():
    '''The text that caused the message is the only thing that can fix it.'''

    call('project.open', example='pv_e')
    result = call('source.replace', markdown='| leading | pipes |\n')
    assert result['project']['error']
    assert result['rail'] == []
    assert call('project.source')['markdown'] == '| leading | pipes |\n'


def test_a_reference_may_point_at_what_its_own_step_writes():
    '''Capital_Cost sums a table and reads that sum inside the same step.

    Four shipped pathways rely on it. `reference.check` excluded a step's own writes and
    so reported ten dangling references per PEC and Photocatalytic file — a validator
    failing its own fixtures.
    '''

    call('project.open', example='pec')
    verdict = call('reference.check',
                   text='{Direct Capital Costs - Gas Processing > Summed total > Value, USD}',
                   step='Capital_Cost_Plugin')['check']
    assert verdict['status'] == 'ok'


def test_a_broken_run_reports_unreached_rather_than_dangling():
    '''"The run stopped earlier" is not "you made a typo".'''

    call('project.open', example='pv_e')
    call('cell.edit', table='Photovoltaic', row='Nominal power', column='Value', text='-1')

    problems = api.SESSIONS['main'].check_references()
    assert problems, 'the broken run should still report something'
    assert {entry['status'] for entry in problems} == {'unreached'}
    assert 'the run stopped at Photovoltaic_Plugin' in problems[0]['message']


def test_a_healthy_pathway_still_reports_nothing():
    for key in ('pv_e', 'thermal', 'pec', 'photocatalytic', 'pv_e_lcoe'):
        call('project.open', example=key, session=key)
        assert api.SESSIONS[key].check_references() == [], key


def test_an_empty_session_reports_nothing_open_rather_than_failing():
    '''Every fresh tab's first call. A 400 in the console of an app behaving perfectly
    trains the reader to ignore the console.'''

    result = api.dispatch('project.state', {'session': 'brand-new'})
    assert 'error' not in result
    assert result['project'] is None
    assert result['rail'] == []


def test_the_masthead_and_the_chooser_call_a_pathway_the_same_thing():
    '''Five names for one pathway is four too many.

    The chooser reads the catalogue; the masthead read `Display Parameters > Name`, which
    four of the five files carry and one does not — so PV Electricity announced itself as
    `PV_E_Electricity_Production.md`, extension included, beside four typeset names. The
    catalogue title now wins for a bundled pathway, and survives every edit.
    '''

    titles = {entry['key']: entry['title'] for entry in call('examples')['examples']}
    for key, title in titles.items():
        assert call('project.open', example=key, session=key)['project']['name'] == title

    call('cell.edit', session='pv_e', table='Electrolyzer', row='Nominal power',
         column='Value', text='6000')
    assert call('project.state', session='pv_e')['project']['name'] == titles['pv_e']


def test_the_envelope_matches_a_naive_per_bucket_reduction():
    '''The vectorised envelope must compute what the loop it replaced computed.

    Building a trace spent 90% of its time in 118,444 numpy reductions, two per envelope
    bucket, from a Python loop. Reducing over the bucket matrix in one call took the
    trace from 151 ms to 38 ms — and would be worthless if it changed a single point.
    '''

    for size in (8760, 365, 97, 20, 3):
        series = np.sin(np.arange(size) / 7.0) * np.arange(size)
        digest = cells.describe(series)['array']
        if 'envelope' not in digest:
            continue

        step = max(1, -(-size // cells.ENVELOPE_POINTS))
        buckets = series[: (size // step) * step].reshape(-1, step)
        naive = [[float(np.min(bucket)), float(np.max(bucket))] for bucket in buckets]
        assert digest['envelope'] == naive, size


def test_a_search_reports_what_it_shows():
    '''A count above forty rows with no truncation notice is a number nobody can act on.

    `reference.search` pages at forty; the client printed the total. On `pv_e` at step
    100 a one-letter query announced 156 matches above exactly 40 rows.
    '''

    call('project.open', example='pv_e')
    result = call('reference.search', query='a', step='Time_Plugin')

    assert result['total'] > result['limit']
    assert result['shown'] == result['limit'] == len(result['results'])


def test_a_search_that_fits_reports_no_truncation():
    call('project.open', example='pv_e')
    result = call('reference.search', query='nominal power', step='Capital_Cost_Plugin')
    assert result['shown'] == result['total'] == len(result['results'])


def test_every_plugin_with_a_docstring_summary_has_one():
    '''pyH2A separates a summary from its Parameters block with a line of indentation.

    Splitting on a literal blank line therefore never fired: the whole numpydoc block
    became "the first paragraph", `'---' in collapsed` was true, and three plugins with
    perfectly good one-line descriptions rendered as "no description in the plugin".
    Found by comparing the native app against the Pyodide build, where CPython 3.13
    dedents docstrings and the same split *did* fire.
    '''

    described = {name: engine.plugin_summary(name)
                 for name in engine.installed_plugins()}
    for name in ('Reverse_Osmosis_Plugin', 'Hourly_Irradiation_Plugin',
                 'Power_Management_Plugin'):
        assert described[name], name
        assert 'Parameters' not in described[name]

    # The one that genuinely opens with a Parameters block still yields nothing, which
    # is the behaviour the empty string exists for.
    assert described['Capital_Cost_Plugin'] == ''
    assert sum(1 for summary in described.values() if summary) >= 21


def test_a_created_row_is_as_wide_as_its_table():
    '''pyH2A zips a row's cells against the header, so a short row poisons the file.

    Adding a step and filling in its required value wrote `Plant modules | 2` under
    `Name | Value | Unit | Comment`. The two missing cells came back as None, and the
    first plugin to read one died on `NoneType has no attribute strip` — in this app and
    in real pyH2A alike, which is the tell that the file was wrong rather than the reader.
    '''

    call('project.open', starter='tea_mass')
    call('workflow.add', plugin='Multiple_Modules_Plugin', position=401)
    field = call('step', step='Multiple_Modules_Plugin')['frame']['needs'][0]['fields'][0]
    call('cell.edit', table=field['table'], row=field['row'], column=field['column'],
         text='2', create=True, step='Multiple_Modules_Plugin')

    written = call('project.source')['markdown']
    block = next(b for b in written.split('\n\n') if 'Plant modules' in b)
    header, _rule, *rows = block.strip().splitlines()
    width = len(header.split('|'))
    for row in rows:
        assert len(row.split('|')) == width, row


def test_a_created_row_carries_the_unit_the_plugin_declares():
    '''An empty Unit cell is `Unknown unit encountered during parsing`; a `-` on an area
    field is a dimension mismatch. Only the declared unit lets the step run.'''

    call('project.open', starter='tea_mass')
    call('workflow.add', plugin='Multiple_Modules_Plugin', position=401)
    for _ in range(8):
        frame = call('step', step='Multiple_Modules_Plugin')['frame']
        missing = [f for group in frame['needs'] for f in group['fields']
                   if f['state'] == 'missing']
        if not missing:
            break
        field = missing[0]
        call('cell.edit', table=field['table'], row=field['row'], column=field['column'],
             text='2', create=True, step='Multiple_Modules_Plugin')

    assert call('step', step='Multiple_Modules_Plugin')['frame']['step']['status'] == 'ok'
    written = call('project.source')['markdown']
    assert holds_row(written, 'Solar collection area', '2', 'm2')


def test_the_unit_stays_editable_after_the_value_is_entered():
    '''The unit box vanished the instant a value was committed, because an unpadded row
    had no Unit key and the field reported nowhere to put one.'''

    call('project.open', starter='tea_mass')
    call('workflow.add', plugin='Multiple_Modules_Plugin', position=401)
    field = call('step', step='Multiple_Modules_Plugin')['frame']['needs'][0]['fields'][0]
    call('cell.edit', table=field['table'], row=field['row'], column=field['column'],
         text='2', create=True, step='Multiple_Modules_Plugin')

    after = call('step', step='Multiple_Modules_Plugin')['frame']['needs'][0]['fields'][0]
    assert after['text'] == '2'
    assert after['unit']['column'] == 'Unit'


def test_a_step_that_runs_after_its_reader_is_reported_as_inert():
    '''Position is the whole difference between a live step and a decorative one.

    `Multiple_Modules_Plugin` writes `Fixed Operating Costs > Staff`. At 650 it writes it
    after Labor Operating Cost (600) has already turned Staff into a cost, so the
    levelized cost does not move by one digit; at 401 the same eight modules take the
    file from 5.5044 to 4.6791 USD/kg. Every field reads "ok" in both cases.
    '''

    def build(position):
        call('project.open', starter='tea_mass')
        call('workflow.add', plugin='Multiple_Modules_Plugin', position=position)
        for _ in range(8):
            frame = call('step', step='Multiple_Modules_Plugin')['frame']
            missing = [f for group in frame['needs'] for f in group['fields']
                       if f['state'] == 'missing']
            if not missing:
                break
            field = missing[0]
            call('cell.edit', table=field['table'], row=field['row'],
                 column=field['column'], step='Multiple_Modules_Plugin', create=True,
                 text='8' if field['row'] == 'Plant modules' else '2')
        return call('step.effect', step='Multiple_Modules_Plugin')['effect']

    late = build(650)
    assert late['inert'] is True
    assert late['with'] == pytest.approx(late['without'])
    # and it names the step it has to beat, with the number that proves it
    assert late['would_matter_at']['before'] == 'Labor_Operating_Cost_Plugin'
    assert late['would_matter_at']['cost'] == pytest.approx(4.6791393268177135)

    early = build(401)
    assert early['inert'] is False
    assert early['with'] == pytest.approx(4.6791393268177135)
    assert early['without'] == pytest.approx(5.5043552237656455)


def test_a_load_bearing_step_is_not_called_inert():
    '''The measurement must not cry wolf on a step the pathway cannot run without.'''

    call('project.open', example='pv_e')
    effect = call('step.effect', step='Photovoltaic_Plugin')['effect']
    assert effect['required'] is True
    assert effect['inert'] is False


def test_a_step_that_comes_from_merged_defaults_says_so():
    '''Inflation is in the workflow but not in the user's file; removing it is not an
    edit this app can make, and claiming to have measured it would be a lie.'''

    call('project.open', starter='tea_mass')
    effect = call('step.effect', step='Inflation_Plugin')['effect']
    assert effect['measurable'] is False
    assert 'not written in the file' in effect['reason']


def test_pyh2as_own_examples_are_refused_with_the_reason_and_the_fix():
    '''Every file in pyH2A's Example folder was rejected in total silence.

    None of them carry an `# Input files to merge` table, so nothing merges
    Defaults_TEA.md and the open dies on `KeyError: 'Functional Unit'`. Handing a
    scientist their own project file back with the word KeyError is not a refusal they
    can act on — and the front door showed nothing at all, because `#welcome-error`
    existed from the first build and was only ever hidden.
    '''

    example = Path(__file__).resolve().parents[2] / 'pyH2A/src/pyH2A/Example/210613_PV_E.md'
    refused = call('project.open', markdown=example.read_text(),
                   origin='210613_PV_E.md')['refused']

    assert 'does not merge' in refused['headline']
    assert refused['saw'] == 'Functional Unit'
    assert '# Input files to merge' in refused['remedy']['markdown']

    # and the offer has to actually work
    taken = call('project.open', markdown=refused['remedy']['markdown'], origin='x.md')
    assert 'refused' not in taken


def test_a_file_with_no_tables_is_not_told_to_add_a_merge_table():
    '''Sending someone off to edit a merge table they do not have is worse than silence.'''

    for text in ('hello, I am not a pyH2A file', '', 'a,b,c\n1,2,3'):
        refused = call('project.open', markdown=text, origin='notes.txt')['refused']
        assert 'does not look like a pyH2A input file' in refused['headline']
        assert 'remedy' not in refused


def test_a_file_that_merges_defaults_but_still_fails_is_not_blamed_on_the_scaffold():
    scaffold = ('# Input files to merge\n\nName | Value\n--- | ---\n'
                'Default TEA | pyH2A.Config~Defaults_TEA.md\n\n'
                '# Workflow\n\nName | Position\n--- | ---\nNo_Such_Plugin | 100\n')
    refused = call('project.open', markdown=scaffold, origin='broken.md')['refused']
    assert refused['headline'] == 'broken.md runs No_Such_Plugin, which is not installed here.'
    assert 'remedy' not in refused

def test_a_whole_number_reaches_a_float_only_field():

    '''`Reverse Osmosis > Power demand` is declared `{float}`. Typing 4 into it stopped
    the model with `Expected (<class 'float'>,), but got <class 'int'>` — a Python type
    error shown to a chemist about a distinction that does not exist in their problem.

    Only the spelling changes. The cell reads 4.0 afterwards, so nothing is hidden.
    '''

    call('project.open', starter='tea_mass')
    call('workflow.add', plugin='Reverse_Osmosis_Plugin', position=850)
    frame = call('step', step='Reverse_Osmosis_Plugin')['frame']
    field = next(f for group in frame['needs'] for f in group['fields']
                 if f['row'] == 'Power demand')
    assert field['declared']['types'] == ['float']

    call('cell.edit', table=field['table'], row=field['row'], column=field['column'],
         text='4', create=True, step='Reverse_Osmosis_Plugin')

    after = next(f for group in call('step', step='Reverse_Osmosis_Plugin')['frame']['needs']
                 for f in group['fields'] if f['row'] == 'Power demand')
    assert after['text'] == '4.0'
    assert holds_row(call('project.source')['markdown'],
                     'Power demand', '4.0', 'J / m3')


def test_a_field_that_takes_ints_keeps_the_integer_as_typed():
    call('project.open', example='pv_e')
    call('cell.edit', table='Technical Operating Parameters and Specifications',
         row='Plant modules', column='Value', text='3')
    assert holds_row(call('project.source')['markdown'], 'Plant modules', '3', '-',
                 'Modelling of 10 modules for calculation of staff cost to '
                 'facilitate comparison with PEC and photocatalytic model')


def test_a_number_in_a_field_that_cannot_hold_one_is_named_before_the_run():
    '''`Hourly Irradiation > File` wants a path; `Battery > Available energy (daily)` is
    written by an earlier step. Both used to reach the engine and fail there.'''

    call('project.open', starter='tea_mass')
    call('workflow.add', plugin='Hourly_Irradiation_Plugin', position=150)
    frame = call('step', step='Hourly_Irradiation_Plugin')['frame']
    field = next(f for group in frame['needs'] for f in group['fields'] if f['row'] == 'File')
    call('cell.edit', table=field['table'], row=field['row'], column=field['column'],
         text='1', create=True, step='Hourly_Irradiation_Plugin')

    after = next(f for group in call('step', step='Hourly_Irradiation_Plugin')['frame']['needs']
                 for f in group['fields'] if f['row'] == 'File')
    assert [p['kind'] for p in after['problems']] == ['not-a-scalar']
    assert 'takes a path or a name' in after['problems'][0]['message']


def test_an_ordinary_numeric_field_is_not_flagged_by_the_scalar_check():
    call('project.open', example='pv_e')
    call('cell.edit', table='Electrolyzer', row='Nominal power', column='Value', text='5500')
    frame = call('step', step='Electrolyzer_Plugin')['frame']
    field = next(f for group in frame['needs'] for f in group['fields']
                 if f['row'] == 'Nominal power')
    assert field['problems'] == []


def test_every_declared_dimension_composes_to_a_unit_the_engine_accepts():
    '''Fifteen of the twenty-six dimensions the shipped plugins declare are compound, and
    a flat lookup answered '' for all of them — including every price per area and every
    mass flow, which is why creating those rows wrote an unusable `-`.'''

    seen = set()
    for plugin in engine.installed_plugins():
        inputs, _ = engine.plugin_io(plugin)
        for rows in inputs.values():
            for spec in rows.values():
                declared = (spec.get('Unit') or {}).get('dimension')
                if declared:
                    seen.add(declared)

    assert len(seen) > 20
    for dimension in seen:
        base = engine.dimension_base_unit(dimension)
        assert base, dimension
        if base == '-':
            assert dimension == 'dimensionless'
            continue
        read_back = str(Quantity(1, base).dimension).replace(' ', '')
        assert read_back == dimension.replace(' ', ''), (dimension, base, read_back)


def test_a_row_carrying_several_quantities_keeps_its_name():
    '''`# Utilities` holds `Electricity | 50 | 1/kg | 0.07 | USD | 1. | -` — one row with
    three quantity groups. Labelling them Usage, Cost and Price_Conversion_Factor dropped
    the word Electricity from the screen, so the start-here band's `Electricity` link
    landed on a field reading `Usage` and changing the price changed the consumption
    instead. Two utilities in one file would have been indistinguishable.
    '''

    call('project.open', starter='tea_mass')
    frame = call('step', step='Variable_Operating_Cost_Plugin')['frame']
    utilities = next(g for g in frame['needs'] if g['table'] == 'Utilities')
    labels = [f['label'] for f in utilities['fields']]

    assert labels == ['Electricity · Usage', 'Electricity · Cost',
                      'Electricity · Price Conversion Factor']


def test_a_single_quantity_row_is_still_labelled_by_its_row():
    call('project.open', example='pv_e')
    frame = call('step', step='Electrolyzer_Plugin')['frame']
    labels = [f['label'] for group in frame['needs'] for f in group['fields']]
    assert 'Nominal power' in labels
    assert not any('·' in label for label in labels)


def test_the_project_name_you_type_is_written_into_the_file():
    '''It used to be an in-memory title: you typed it, saw it in the header, downloaded
    the file, opened it again and got "New pathway".'''

    call('project.open', starter='tea_mass', name='Jacob demo')
    assert holds_row(call('project.source')['markdown'], 'Name', 'Jacob demo')

    reopened = call('project.open', markdown=call('project.source')['markdown'],
                    origin='downloaded.md')
    assert reopened['project']['name'] == 'Jacob demo'


def test_a_teach_can_name_the_column_it_means():
    '''`Utilities > Electricity` is a usage, a price and a conversion factor. The band
    says "Electricity"; a reader following it means the tariff they pay, and it used to
    land on consumption.'''

    teaches = call('project.open', starter='tea_mass')['teaches']
    electricity = next(t for t in teaches if t['row'] == 'Electricity')
    assert electricity['column'] == 'Cost_Value'


def test_the_rail_tally_accounts_for_every_step():
    '''A step with status error and no field-level problems was in no bucket at all, so a
    ten-step run stopped at step five reported "8 ran clean, 1 never reached".'''

    call('project.open', starter='tea_mass')
    call('workflow.add', plugin='Reverse_Osmosis_Plugin', position=850)
    rail = call('project.state')['rail']

    clean = [e for e in rail if e['status'] == 'ok' and not e['problems']]
    flagged = [e for e in rail if e['status'] == 'ok' and e['problems']]
    stopped = [e for e in rail if e['status'] == 'error']
    skipped = [e for e in rail if e['status'] == 'skipped']

    assert len(clean) + len(flagged) + len(stopped) + len(skipped) == len(rail)
    assert len(stopped) == 1


def test_a_row_created_in_a_wildcard_declared_table_gets_its_unit():
    '''Every cost table in pyH2A is declared as a *group* — `<...> Direct Capital Cost
    <...>` matches any table whose name contains that, and the row key inside is a bare
    `<...>`. A literal inputs[table][row] lookup found nothing, so a created cost row was
    padded with `-` and the run died on `Expected dimension 'currency', but got
    'dimensionless'` — in this app and in real pyH2A alike.
    '''

    call('project.open', example='pv_e')
    before = call('project.state')['project']['cost']['value']

    call('cell.edit', table='Direct Capital Costs - Electrolyzer', row='Compressor',
         column='Value', text='250000', create=True)

    state = call('project.state')['project']
    assert state['failed'] is None
    assert state['cost']['value'] > before
    assert holds_row(call('project.source')['markdown'],
                 'Compressor', '250000', '', 'USD', '')


def test_the_spelling_follows_the_workflow_not_the_alphabet():
    '''`Solar-to-Hydrogen Efficiency > STH` is `{float, int}` to PEC_Plugin and `{float}`
    to Solar_Thermal_Plugin. Scanning installed plugins alphabetically returned PEC's
    answer on a Solar Thermal pathway PEC has nothing to do with, so `1` was written
    as-is and stopped the run.
    '''

    call('project.open', example='thermal')
    call('cell.edit', table='Solar-to-Hydrogen Efficiency', row='STH', column='Value',
         text='1')

    state = call('project.state')['project']
    assert state['failed'] is None
    assert any(row.split('|')[1].strip() == '1.0'
               for row in call('project.source')['markdown'].splitlines()
               if row.startswith('STH '))


def test_a_dash_on_a_dimensional_cell_is_named_at_the_field():
    '''`-` used to be skipped by the dimension check, which made the one token the app
    falls back to the one token the validator would not look at.'''

    call('project.open', example='pv_e')
    call('cell.edit', table='Direct Capital Costs - Electrolyzer', row='Compressor',
         column='Value', text='250000', create=True)
    call('cell.edit', table='Direct Capital Costs - Electrolyzer', row='Compressor',
         column='Unit', text='-')

    frame = call('step', step='Capital_Cost_Plugin')['frame']
    field = next(f for group in frame['needs'] for f in group['fields']
                 if f['row'] == 'Compressor')
    assert [p['kind'] for p in field['problems']] == ['wrong-dimension']


def test_no_shipped_pathway_is_accused_of_a_wrong_dimension():
    '''A computed field has no unit column and a missing row has an empty one. Checking
    `-` without excluding both produced 82 accusations against working files.'''

    for key in ('pv_e', 'thermal', 'pec', 'photocatalytic', 'pv_e_lcoe'):
        call('project.open', example=key)
        for entry in call('project.state')['rail']:
            frame = call('step', step=entry['name'])['frame']
            for group in frame['needs']:
                for field in group['fields']:
                    kinds = [p['kind'] for p in field['problems']]
                    assert 'wrong-dimension' not in kinds, (key, field['row'])


def test_editing_a_merged_default_writes_an_override():
    '''Twelve financial values come from Defaults_TEA.md and the file has no
    `Financial Input Values` table, so every one was an editable-looking box that took
    your typing, showed it, and threw it away: 8% IRR typed over as 20% left the cost at
    5.5044 and the file byte-identical.'''

    call('project.open', starter='tea_mass')
    before = call('project.state')['project']['cost']['value']

    call('cell.edit', table='Financial Input Values', row='After-tax real IRR',
         column='Value', text='20%', step='Discounted_Cash_Flow_Plugin')

    state = call('project.state')['project']
    assert state['failed'] is None
    assert state['cost']['value'] > before
    assert holds_row(call('project.source')['markdown'],
                 'After-tax real IRR', '20%', '-')


def test_a_typo_is_still_refused_when_nothing_holds_that_cell():
    '''The override path must not become a way to grow cells the engine ignores.'''

    call('project.open', starter='tea_mass')
    result = api.dispatch('project.state', {})
    assert 'error' not in result
    refused = api.dispatch('cell.edit', {'table': 'Financial Input Values',
                                         'row': 'Typo Row', 'column': 'Value', 'text': '1'})
    assert 'Typo Row' in refused['error']


def test_a_cleared_cell_stays_editable():
    '''An empty cell was classified computed, so clearing a wrong value redrew the row as
    a dark uneditable badge and only the source editor could recover it.'''

    call('project.open', starter='tea_mass')
    call('workflow.add', plugin='Battery_Plugin', position=250)
    frame = call('step', step='Battery_Plugin')['frame']
    field = next(f for group in frame['needs'] for f in group['fields']
                 if f['row'] == 'Available energy (daily)')

    call('cell.edit', table=field['table'], row=field['row'], column=field['column'],
         text='5', create=True, step='Battery_Plugin')
    call('cell.edit', table=field['table'], row=field['row'], column=field['column'],
         text='', step='Battery_Plugin')

    after = next(f for group in call('step', step='Battery_Plugin')['frame']['needs']
                 for f in group['fields'] if f['row'] == 'Available energy (daily)')
    assert after['state'] == 'missing'


def test_a_step_knows_whether_its_workflow_row_is_in_the_file():
    '''Nine of a blank plant's steps come from Defaults_TEA.md, so "remove step" could
    only ever fail — and it explained itself after the click.'''

    call('project.open', starter='tea_mass')
    assert call('step', step='Discounted_Cash_Flow_Plugin')['frame']['step']['in_file'] is False

    call('workflow.add', plugin='Battery_Plugin', position=250)
    assert call('step', step='Battery_Plugin')['frame']['step']['in_file'] is True


def test_the_effect_of_a_step_carries_its_direction():
    '''"Worth 0.8105 USD/kg" read as a saving on three PV+E steps that all raise it.'''

    call('project.open', example='pv_e')
    effect = call('step.effect', step='Reverse_Osmosis_Plugin')['effect']
    assert effect['with'] > effect['without']

    call('project.open', example='pec')
    saves = call('step.effect', step='Hourly_Irradiation_Plugin')['effect']
    assert saves['with'] < saves['without']
