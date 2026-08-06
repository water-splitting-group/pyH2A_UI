'''Data for the figures attached to a step.

A figure here belongs to the step that produced it. The cost decomposition is the
Discounted Cash Flow step's output; the hourly calendar is what the Photovoltaic step
made. Parking them on a separate results page would say they are conclusions about the
project; attaching them to a step says what they are — evidence of what that step did,
in the place where you are looking at it. That is the difference between a report and
a worksheet.

**A figure never invents a second opinion.** Everything drawn is an engine value, and
anything that *allocates* one must prove it lost nothing. `contributions` groups eleven
engine-computed cost components into four families, and returns the residual between
its own subtotals and the engine's headline. The tests assert that residual is exactly
zero on all five pathways, so a regrouping that quietly drops a component fails rather
than merely looking plausible.
'''

import numpy as np

from pyh2a_studio.core import cells, engine

FAMILIES = (
    ('capital', 'Capital', 'built once', (
        'Initial equity depreciable capital', 'Non depreciable capital',
        'Replacement costs', 'Working capital reserve',
    )),
    ('operating', 'Operating', 'spent every year the plant runs', (
        'Fixed operating costs', 'Variable operating costs',
    )),
    ('financing', 'Financing & tax', 'debt service and what the state takes', (
        'Interest', 'Principal payment', 'Taxes',
    )),
    ('endoflife', 'End of life', 'decommissioning, less what the parts fetch', (
        'Decommissioning', 'Salvage',
    )),
)
'''The eleven components the engine names, grouped into four families a reader can
hold in their head. The grouping is presentational and the membership is exhaustive —
`_family_of` returns `'other'` for anything unlisted, and the reconciliation check
would catch a component that fell out, but a stray `other` row on screen is the more
useful warning because it names what upstream added.'''


def _family_of(name):
    for key, _, _, members in FAMILIES:
        if name in members:
            return key
    return 'other'


def contributions(result, functional_unit):
    '''The levelized cost broken into its named parts, grouped, with the residual.

    Parameters
    ----------
    result : engine.RunResult
    functional_unit : str
        The denominator token, e.g. `kg` or `kWh`. Never assumed: `pv_e_lcoe` prices
        electricity and every label here is built from the file's own unit.

    Returns
    -------
    dict or None
        None when the run did not complete. Otherwise `rows`, `families`, `total`,
        `unit`, and `residual` — the difference between the sum of the parts and the
        engine's own headline, in the same units. A figure that cannot prove it
        reconciles has no business being drawn.
    '''

    if result is None:
        return None

    data = result.contributions.get('Data') or {}
    total = _magnitude(result.contributions.get('Total'))
    headline = _magnitude(result.levelized_cost)
    if total is None or headline is None:
        return None

    rows = []
    for name, quantity in data.items():
        value = _magnitude(quantity)
        if value is None:
            continue
        rows.append({
            'name': name,
            'value': value,
            'share': value / total if total else 0.0,
            'family': _family_of(name),
        })
    rows.sort(key=lambda row: -abs(row['value']))

    families = []
    for key, label, blurb, _ in FAMILIES:
        members = [row for row in rows if row['family'] == key]
        if not members:
            continue
        subtotal = sum(row['value'] for row in members)
        families.append({
            'key': key, 'label': label, 'blurb': blurb,
            'subtotal': subtotal,
            'share': subtotal / total if total else 0.0,
            'rows': sorted(members, key=lambda row: -abs(row['value'])),
        })

    stray = [row for row in rows if row['family'] == 'other']
    if stray:
        families.append({
            'key': 'other', 'label': 'Unclassified', 'rows': stray,
            'blurb': 'the engine names these; this app has not been told where they belong',
            'subtotal': sum(row['value'] for row in stray),
            'share': sum(row['value'] for row in stray) / total if total else 0.0,
        })

    return {
        'rows': rows,
        'families': families,
        'total': total,
        'headline': headline,
        'unit': f'USD/{functional_unit}',
        # Two independent claims, both checked: the parts sum to the engine's own
        # total, and that total is the headline the masthead shows.
        'residual': sum(row['value'] for row in rows) - total,
        'headline_residual': total - headline,
    }


def _magnitude(quantity):
    '''An engine value as a float in its authored unit, or None.'''

    record = cells.describe(quantity)
    return record.get('value')


def series(project, step_name, table, row, column, year=0):
    """One cell's full, undecimated array **as the named step left it**.

    Two things this cannot do naively.

    It cannot read the end of the run. A later step may overwrite the cell — in PV+E,
    `Battery_Plugin` replaces `Power Generation > Available energy (hourly)` with a
    scalar — so fetching from the completed state either fails outright or, worse,
    returns a *different array* under an earlier step's heading. A calendar captioned
    with the step that made it must draw what that step made.

    It cannot read the trace either: a snapshot carries a 96-point envelope, which is
    right for a sparkline in a list and useless for 8,760 hours.

    So it re-runs the workflow up to and including `step_name` and reads the live
    array. That costs 10-60 ms, paid once when a reader picks a series, and it is the
    only way the caption and the curve are guaranteed to be about the same thing.

    Returns
    -------
    dict or None
        `values`, `unit`, `length`, the extent, and `years` — how many the cell holds,
        so a caller can offer the choice rather than silently drawing year 0 of twenty.
        `year` echoes the year actually selected, not the one requested.
    """

    if project.run is None or project.run.step(step_name) is None:
        return None

    inp = engine.state_after(project.inp, step_name)
    if inp is None:
        return None

    node = inp.get(table, {}).get(row, {}).get(column)
    if node is None:
        return None

    node, year, years = _select_year(node, year)
    if node is None:
        return None

    unit = str(getattr(node, 'supplied_unit', '') or '')
    flat = _finite_array(getattr(node, 'supplied_value', node))
    if flat is None:
        return None
    finite = flat[np.isfinite(flat)]

    return {
        'values': [float(value) for value in flat],
        'unit': unit,
        'length': int(flat.size),
        'min': float(np.min(finite)),
        'max': float(np.max(finite)),
        'sum': float(np.sum(finite)),
        'table': table,
        'row': row,
        'column': column,
        'year': year,
        'years': years,
        'step': step_name,
    }


HOURS_IN_YEAR = 8760


def _select_year(node, year):
    """One year out of a per-year mapping, clamped; `(node, year, years)`."""

    if not isinstance(node, dict):
        return node, 0, 1
    keys = sorted(node)
    if not keys:
        return None, 0, 0
    chosen = max(0, min(int(year), len(keys) - 1))
    return node[keys[chosen]], chosen, len(keys)


def _finite_array(magnitude):
    """A 1-D float array with at least one finite entry, or None."""

    if not isinstance(magnitude, np.ndarray):
        return None
    flat = np.asarray(magnitude, dtype=float).ravel()
    return flat if np.isfinite(flat).any() else None


def hourly_candidates(step):
    '''Cells this step wrote that an hour-by-hour calendar could draw.

    An 8,760-point array is one value per hour of a year, and that is the only length a
    calendar of 365 columns by 24 rows can honestly claim to be. A 20-point array is a
    year index and a 365-point one is daily; both are real series and neither is a
    calendar, so they are not offered as one.

    Offered from what the step *wrote*, and served by re-running to that step, so the
    two always agree. An earlier version offered from `wrote` and served from the end
    of the run, which left two dead buttons on PV+E and one step whose only offer was
    the broken one.
    '''

    found = []
    for (table, row, column), record in step.wrote.items():
        digest = record.get('array')
        length = digest.get('length') if digest else record.get('inner_length')
        if length != HOURS_IN_YEAR:
            continue
        found.append({
            'table': table, 'row': row, 'column': column,
            'per_year': record.get('form') == 'years',
            'years': record.get('count', 1),
            'unit': record.get('unit', ''),
            # The largest single hour, so a step offering several series can draw them
            # on one scale. Step 201 produces three tracking modes whose entire purpose
            # is comparison, and scaling each to its own maximum is precisely the
            # normalisation that makes them incomparable.
            #
            # For a per-year cell this is `inner_max` and emphatically not `max`: the
            # latter is the largest annual *total*, 2,744x the largest hour here, and
            # using it flattens the calendar to a solid block at the ink floor.
            'max': (digest or {}).get('max') if digest else record.get('inner_max'),
        })
    found.sort(key=lambda entry: (entry['table'], entry['row']))
    return found


def annual_costs(result):
    """What the plant spends, year by year, from the engine's own annual arrays.

    The Discounted Cash Flow plugin builds a full annual table and keeps only the
    levelized cost, but every *cost* line it used survives in the input dict as a
    21-element array. Those are read here directly.

    **Revenue is not shown, and that is deliberate.** The engine discards it, and it
    is only recoverable by multiplying the levelized price by the annual output —
    which is true by construction (the price is *defined* as the one making NPV zero)
    but is still this app computing a number the engine did not state. A figure that
    mixes engine values with its own arithmetic, without saying which is which, is
    exactly how a chart stops being checkable. So: costs, labelled as costs.

    What that still shows is worth the panel — the construction year, the flat
    operating band, and the stack replacement landing in one year.

    Returns
    -------
    dict or None
        `lines` (name, description, 21 values), `total` per year, `peak`, and the
        year of the largest single spend.
    """

    if result is None:
        return None

    lines = []
    for name, blurb, path in _COST_LINES:
        values = _array(result.inp, path)
        if values is None:
            continue  # absent from this pathway entirely; see the docstring
        total = float(np.sum(values))
        lines.append({'name': name, 'blurb': blurb,
                      'values': [float(value) for value in values],
                      'total': total,
                      # The engine wrote this line and it is zero — which is a
                      # statement about the model, not an absence. The electricity
                      # pathway has no variable operating cost and no stack to
                      # replace. Marked rather than dropped, so a reader can see the
                      # category was considered; the chart lists it instead of
                      # drawing an invisible bar.
                      'zero': total == 0})

    if not lines:
        return None

    span = max(len(line['values']) for line in lines)
    for line in lines:
        line['values'] += [0.0] * (span - len(line['values']))

    per_year = [sum(line['values'][year] for line in lines) for year in range(span)]
    peak = max(per_year) if per_year else 0.0
    peak_year = per_year.index(peak) if per_year else None

    # Name what dominates the largest year, and say only that. In PV+E the last year
    # is 19.9 M against ~3 k the year before, and a reader seeing that with no label
    # has to go digging. An earlier version of this comment also asserted *why* — the
    # grid tariff — which the arithmetic does not support: the twenty-year grid draw is
    # 13.9 M against a 19.9 M spike. Naming the line is checkable from the chart;
    # explaining the line is a claim this module cannot make.
    driver = None
    drawn = [line for line in lines if not line['zero']]
    if peak_year is not None and peak > 0 and drawn:
        largest = max(drawn, key=lambda line: line['values'][peak_year])
        driver = {
            'name': largest['name'],
            'value': largest['values'][peak_year],
            'share': largest['values'][peak_year] / peak,
        }

    return {
        'years': span,
        'lines': sorted(lines, key=lambda line: -line['total']),
        'per_year': per_year,
        'peak': peak,
        'peak_year': peak_year,
        'driver': driver,
        'lifetime': sum(per_year),
        'unit': 'USD',
    }


_COST_LINES = (
    ('Depreciable capital', 'the plant itself, as equity',
     ('Depreciable Capital Costs', 'Annual equity', 'Value')),
    ('Non-depreciable capital', 'land and anything that does not wear out',
     ('Non-Depreciable Capital Costs', 'Annual', 'Value')),
    ('Fixed operating', 'staff and upkeep, whether it runs or not',
     ('Fixed Operating Costs', 'Annual', 'Value')),
    ('Variable operating', 'feedstock, utilities, everything per unit made',
     ('Variable Operating Costs', 'Annual', 'Value')),
    ('Replacement', 'parts with a life shorter than the plant',
     ('Replacement', 'Total', 'Value')),
)
"""Where each annual line lives in the engine's state after a run. A pathway missing
one is skipped rather than zero-filled: showing a flat zero line for a replacement
schedule that does not exist implies a decision the model never made."""


def _array(inp, path):
    '''A one-dimensional float array at a three-part path, or None.

    None rather than an empty array, so a caller can tell "this pathway has no
    replacement schedule" apart from "it has one and it is all zeros" — a distinction
    the cost figure depends on to avoid drawing a line the model never made.
    '''

    node = inp
    for key in path:
        if not isinstance(node, dict) or key not in node:
            return None
        node = node[key]

    magnitude = getattr(node, 'supplied_value', node)
    if not isinstance(magnitude, np.ndarray):
        return None
    return np.asarray(magnitude, dtype=float).ravel()


def for_step(project, step_name):
    '''Which figures this step can offer, and the data for the primary one.

    Deliberately narrow. Every step could be given a chart; almost none would earn it.
    The three here each answer a question the step's own numbers raise and nothing
    else on the page answers.
    '''

    run = project.run
    step = run.step(step_name) if run else None
    if step is None:
        return {}

    offered = {}
    if step_name.startswith('Discounted_Cash_Flow'):
        offered['contributions'] = contributions(run.result, project.functional_unit())
        offered['annual_costs'] = annual_costs(run.result)

    hourly = hourly_candidates(step)
    if hourly:
        offered['hourly'] = hourly

    return {key: value for key, value in offered.items() if value}
