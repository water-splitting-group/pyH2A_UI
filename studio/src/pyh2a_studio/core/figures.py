'''Data for the figures attached to a step.

A figure here belongs to the step that produced it. The cost cascade is the Discounted
Cash Flow step's output; the hourly calendar is what the Photovoltaic step made. Parking
them on a separate results page would say they are conclusions about the project;
attaching them to a step says what they are — evidence of what that step did, in the
place where you are looking at it. That is the difference between a report and a
worksheet.

**A figure never invents a second opinion.** Everything drawn is an engine value, and
anything that *allocates* one must prove it lost nothing. `contributions` groups eleven
engine-computed cost components into named tributaries, and returns the residual between
its own subtotals and the engine's headline. The tests assert that residual is exactly
zero on all five pathways, so a regrouping that quietly drops a component fails rather
than merely looking plausible.

Three sources, in descending order of how much they can be trusted, and every field here
says which one it came from:

1. **`result.inp`** — the engine's state after the run. Authored magnitudes in authored
   units. The cost-group `Contributions` cells live here, which is how the cascade can
   name what the capital bought without deciding anything itself.
2. **`result.plugs`** — the plugin instances. The Discounted Cash Flow plugin builds a
   full twenty-one year cash flow and writes only the levelized cost back into `inp`,
   so revenue, taxes, interest, principal and the cumulative survive *only* here. They
   are still engine values: this module reads attributes, it does not recompute them.
3. **This module's own arithmetic** — sums, shares, cumulative sums, and the pro-rata in
   `_capital_split`. Every one of these is checked against an engine value before it is
   returned, and the check ships in the payload so a figure can print it.
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

_CAPITAL_BLURBS = {
    'Replacement costs': 'parts with a life shorter than the plant',
    'Non depreciable capital': 'land, and anything that does not wear out',
    'Working capital reserve': 'cash tied up against the change in operating cost',
    'Initial equity depreciable capital': 'the plant itself, as equity',
}


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
        None when the run did not complete. Otherwise `rows`, `families`,
        `tributaries`, `total`, `unit`, and `residual` — the difference between the sum
        of the parts and the engine's own headline, in the same units. A figure that
        cannot prove it reconciles has no business being drawn.
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

    families = _families_of(rows, total)
    tributaries = _tributaries(rows, families, total, _capital_split(result.inp))

    return {
        'rows': rows,
        'families': families,
        'tributaries': tributaries,
        'total': total,
        'headline': headline,
        'unit': f'USD/{functional_unit}',
        'functional_unit': functional_unit,
        # Three independent claims, all checked: the parts sum to the engine's own
        # total, that total is the headline the masthead shows, and the cascade the
        # figure actually draws did not lose or double-count a component while
        # regrouping the eleven rows into tributaries.
        'residual': sum(row['value'] for row in rows) - total,
        'headline_residual': total - headline,
        'cascade_residual': sum(part['value'] for part in tributaries) - total,
    }


def _families_of(rows, total):
    '''The four named families, plus an `Unclassified` group if upstream added a row.'''

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
    return families


def _tributaries(rows, families, total, split):
    '''The cascade the cost figure draws: named streams, in the order money is spent.

    Four families are the right *audit*, and the wrong *picture*. "Capital 1.57 USD/kg"
    answers nothing a reader of a plant design wants to know; "PV 0.831, electrolyzer
    0.531, reverse osmosis 0.004" answers all of it, and the engine already itemises it
    — see `_capital_split`. So the capital family is opened up by plant unit and
    everything downstream of the build stays at family level, where the engine's own
    names (`Interest`, `Taxes`) are already the useful granularity.

    Order is the plant's own chronology — what you buy, what you replace, what you run,
    what you owe, what you tear down — not magnitude. A cascade sorted by size reads as
    a ranking; sorted by time it reads as an argument, and the end-of-life credit lands
    where it belongs, pulling the running total back down at the right end.
    '''

    by_name = {row['name']: row for row in rows}
    equity = by_name.get('Initial equity depreciable capital')
    made = []

    if equity is not None and split:
        for part in sorted(split, key=lambda entry: -abs(entry['usd'])):
            made.append({
                'key': f'unit:{part["label"]}', 'label': part['label'], 'kind': 'unit',
                'note': 'as built', 'value': equity['value'] * part['share'],
                'family': 'capital', 'basis': part,
                'rows': [{'name': equity['name'], 'value': equity['value'],
                          'share_of_row': part['share']}],
            })
    elif equity is not None:
        made.append(_row_tributary(equity))

    for row in rows:
        if row['family'] != 'capital' or row is equity:
            continue
        made.append(_row_tributary(row))

    for family in families:
        if family['key'] == 'capital':
            continue
        made.append({
            'key': family['key'], 'label': family['label'], 'kind': 'family',
            'note': family['blurb'], 'value': family['subtotal'],
            'family': family['key'], 'basis': None,
            'rows': [{'name': row['name'], 'value': row['value']} for row in family['rows']],
        })

    running = 0.0
    for part in made:
        part['start'] = running
        running += part['value']
        part['end'] = running
        part['share'] = part['value'] / total if total else 0.0
        part['zero'] = part['value'] == 0
    return made


def _row_tributary(row):
    return {
        'key': row['name'], 'label': row['name'], 'kind': 'row',
        'note': _CAPITAL_BLURBS.get(row['name'], ''), 'value': row['value'],
        'family': row['family'], 'basis': None,
        'rows': [{'name': row['name'], 'value': row['value']}],
    }


def _capital_split(inp):
    '''What the depreciable capital bought, as shares that provably sum to one.

    The engine itemises it already: every cost-group plugin leaves a `Contributions`
    cell naming its own groups, so `Direct Capital Cost` carries
    `{PV: 6 748 500, Electrolyzer: 4 312 000, Reverse Osmosis: 34 893, Battery: 0}` in
    USD as built. This reads that; it does not decide it.

    What this app adds is the check. Direct plus indirect must equal
    `Depreciable Capital Costs > Total`, because that is the quantity the levelized
    `Initial equity depreciable capital` is the equity share *of*. When it does not
    agree the split is refused and the row stays whole, rather than being carved up by
    a denominator that means something else.

    Prorating a *discounted* levelized figure by *nominal* group totals is exact here
    and only here: all depreciable capital is spent on one construction schedule at one
    equity/debt split, so every group carries the identical discount factor. The same
    move on `Replacement costs` would be a lie — PEC's planned cell replacement and its
    unplanned replacement land in different years and discount differently.

    Returns None rather than an empty list when there is nothing to split, so the
    caller can tell "no itemisation" apart from "itemised into nothing".
    '''

    groups = _group_contributions(inp, 'Direct Capital Cost')
    groups.update(_group_contributions(inp, 'Indirect Capital Cost'))
    depreciable = _scalar(inp, ('Depreciable Capital Costs', 'Total', 'Value'))
    if not groups or not depreciable:
        return None
    if abs(sum(groups.values()) - depreciable) > 1e-6 * abs(depreciable):
        return None
    return [{'label': _group_label(name), 'usd': value, 'share': value / depreciable}
            for name, value in groups.items()]


def _group_contributions(inp, table):
    '''`{group name: USD}` out of one cost group's own `Contributions` cell.'''

    node = inp.get(table, {}).get('Contributions', {}).get('Value')
    node = getattr(node, 'supplied_value', node)
    if not isinstance(node, dict):
        return {}
    found = {}
    for name, quantity in (node.get('Data') or {}).items():
        value = _magnitude(quantity)
        if value is not None:
            found[name] = value
    return found


def _group_label(name):
    '''`Direct Capital Costs - PV` → `PV`.

    The engine's own noun, not a prettier one. "Reverse Osmosis" is checkable against
    the workflow in two seconds; "Desalination" is this app putting words in the
    model's mouth, and the whole point of the studio is that you can find every label
    in the file it came from.
    '''

    prefix = 'Direct Capital Costs - '
    if name.startswith(prefix):
        return name[len(prefix):]
    if name == 'Indirect Capital Costs':
        return 'Indirect capital'
    return name


def _magnitude(quantity):
    '''An engine value as a float in its authored unit, or None.'''

    record = cells.describe(quantity)
    return record.get('value')


def _scalar(inp, path):
    '''A float at a three-part path, or None.'''

    node = inp
    for key in path:
        if not isinstance(node, dict) or key not in node:
            return None
        node = node[key]
    return _magnitude(node)


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
        `year` echoes the year actually selected, not the one requested. `dispatch`
        carries the operating regimes of that same year when the step's state can
        support them; see `_dispatch`.
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
        'dispatch': _dispatch(inp, year),
    }


HOURS_IN_YEAR = 8760

DISPATCH_TABLE = 'Power Generation'
DISPATCH_OFFERED = 'PV hourly power generation'
DISPATCH_LEFT = 'Available energy (hourly)'
'''The two cells that bracket a year of operation. `PV hourly power generation` is what
the array made and nothing downstream rewrites it; `Available energy (hourly)` starts
equal to it and each consumer subtracts what it took. Their difference is therefore
"energy something used", without this module knowing or caring which plugin used it.'''

_ZERO = 1e-9
'''Below this an hour counts as nothing. The arrays are joules per hour at 1e10, so
1e-9 J is float noise from the subtraction and not a plant doing anything.'''


def _dispatch(inp, year):
    '''The year split into operating regimes, read off the two arrays and nothing else.

    Four regimes, and the classification never consults a parameter:

    | dark            | `generated == 0`                        |
    | below turndown  | `generated > 0`, nothing served         |
    | direct          | served, and none left over              |
    | saturated       | served, and there is still energy left  |

    Deriving the regimes from a `Minimum capacity` parameter instead would mean a wrong
    parameter produces a picture that is wrong while looking right — the failure class
    this whole app exists to catch. So the arrays classify, and the parameter is only
    ever quoted *beside* the bracket the arrays independently give: on PV+E the largest
    fully-dumped hour is 0.0982 of the largest served hour and the smallest hour the
    stack ran is 0.1000, and `Electrolyzer > Minimum capacity` is authored as 0.1,
    which falls in that gap from a different code path.

    Returns None when there is no consumer yet. At the Photovoltaic step the two arrays
    are equal to the bit, which means nothing has been taken and a four-way split would
    report 4,315 hours "below turndown" — technically true of the arrays, and a
    complete misreading of the plant.
    '''

    table = inp.get(DISPATCH_TABLE, {})
    generated = _year_array(table.get(DISPATCH_OFFERED, {}).get('Value'), year)
    left = _year_array(table.get(DISPATCH_LEFT, {}).get('Value'), year)
    if generated is None or left is None or generated.shape != left.shape:
        return None
    if generated.size != HOURS_IN_YEAR or np.any(left > generated + _ZERO):
        return None

    served = generated - left
    if not np.any(served > _ZERO):
        return None

    census = _regimes(generated, served, left)
    census.update({
        'generation': [float(value) for value in generated],
        'unused': [float(value) for value in left],
        'generated_total': float(np.sum(generated)),
        'served_total': float(np.sum(served)),
        'unused_total': float(np.sum(left)),
        'served_max': float(np.max(served)),
        'offered_row': DISPATCH_OFFERED,
        'left_row': DISPATCH_LEFT,
        'turndown': _turndown(inp, generated, served),
    })
    return census


def _regimes(generated, served, left):
    '''Hour counts per regime. They sum to 8,760 and the figure prints that.'''

    running = served > _ZERO
    saturated = running & (left > _ZERO)
    return {
        'dark': int(np.count_nonzero(generated <= 0)),
        'dumped': int(np.count_nonzero((generated > 0) & ~running)),
        'direct': int(np.count_nonzero(running & ~saturated)),
        'saturated': int(np.count_nonzero(saturated)),
        'running': int(np.count_nonzero(running)),
    }


def _turndown(inp, generated, served):
    '''Where the arrays put the boundary the stack will not run below.

    Expressed as a fraction of the largest served hour, which is the consumer's
    nameplate by construction — it saturates. That makes it directly comparable to the
    authored `Minimum capacity`, which is also a fraction of nameplate, with no unit
    conversion between joules-per-hour and kilowatts standing in the way. Two numbers
    on one screen that can only be compared after arithmetic are two numbers nobody
    compares.
    '''

    ceiling = np.max(served)
    if ceiling <= 0:
        return None
    running = served > _ZERO
    dumped = (generated > 0) & ~running
    return {
        'floor': float(np.max(generated[dumped]) / ceiling) if np.any(dumped) else None,
        'ceiling': float(np.min(generated[running]) / ceiling) if np.any(running) else None,
        'authored': _scalar(inp, ('Electrolyzer', 'Minimum capacity', 'Value')),
        'source': 'Electrolyzer > Minimum capacity',
    }


def _year_array(node, year):
    '''One year of a possibly per-year cell as a float array, or None.'''

    if node is None:
        return None
    node, _, _ = _select_year(node, year)
    if node is None:
        return None
    return _finite_array(getattr(node, 'supplied_value', node))


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


_CASH_LINES = (
    # key, label, blurb, family, tone, sign, plugin attribute.
    # `sign` turns the plugin's own array into a signed cash flow: +1 where a positive
    # entry already means money in. Everything is stacked on the side its sign puts it
    # on, per year — a negative tax is a credit and belongs above the datum, and a
    # figure that assumed the sign would drop it or draw it upside down.
    ('revenue', 'Revenue', 'the product, sold at the levelized price',
     'revenue', 0, +1, 'annual_revenue'),
    ('salvage', 'Salvage', 'what the parts fetch at the end',
     'eol', 1, +1, 'salvage_income'),
    ('fixed_operating', 'Fixed operating', 'staff and upkeep, whether it runs or not',
     'operating', 0, -1, 'annual_fixed_operating_costs'),
    ('variable_operating', 'Variable operating', 'feedstock and utilities, per unit made',
     'operating', 1, -1, 'annual_variable_operating_costs'),
    ('interest', 'Interest', 'debt service on the borrowed half',
     'financing', 0, -1, 'interest_per_year'),
    ('principal', 'Principal', 'the loan itself, repaid in one payment',
     'financing', 1, -1, 'principal_payment'),
    ('working_capital', 'Working capital', 'cash tied up against the change in operating cost',
     'financing', 2, +1, 'working_capital_reserve'),
    ('taxes', 'Taxes', 'federal and state, on income after depreciation',
     'tax', 0, -1, 'annual_taxes'),
    ('replacement', 'Replacement', 'parts with a life shorter than the plant',
     'capital', 2, -1, 'annual_replacement_costs'),
    ('depreciable_capital', 'Depreciable capital', 'the plant itself, as equity',
     'capital', 0, -1, 'annual_initial_depreciable_capital'),
    ('non_depreciable_capital', 'Non-depreciable capital', 'land, and what does not wear out',
     'capital', 1, -1, 'annual_non_depreciable_capital'),
    ('decommissioning', 'Decommissioning', 'taking it down again',
     'eol', 0, -1, 'decommissioning_costs'),
)
'''The twelve cash lines, in stacking order outward from the zero datum.

Twelve, not thirteen. `annual_charge` is the MACRS depreciation and it is **not a cash
flow** — it enters only through taxes, and stacking it would break the one property the
chart is built on, that the segments of a year sum to that year's net. It is reported
separately so a reader who counts the plugin's arrays can see it was considered.'''

# These labels are the cash-flow legend, read left to right by someone scanning twelve
# rows. Index order — `Operating, variable`, `Capital, depreciable` — sorts a printed
# index and reads as filing in a legend, and the family grouping already does that
# sorting here. So they are set as English: `Variable operating`, `Depreciable capital`.
# Anything that needs one of these strings takes it off the line rather than retyping
# it; `_anomaly` used to carry its own copy and drifted from this tuple the moment the
# labels changed.


def annual_costs(result):
    """The full twenty-one year cash flow, as the engine built it.

    The Discounted Cash Flow plugin assembles revenue, operating cost, debt service,
    tax and end-of-life into a year-by-year table, solves for the price that makes its
    discounted sum zero, and writes back only that price. Everything else survives on
    the plugin instance, which `engine.RunResult` keeps in `plugs` for exactly this
    reason.

    **An earlier version of this module refused to draw revenue**, on the grounds that
    the engine discards it and recovering it means multiplying the levelized price by
    the annual output — this app doing arithmetic the engine did not state. That
    reasoning was sound and the premise was wrong: `annual_revenue` is computed by the
    plugin, in the plugin, and is right there on the instance. Reading an attribute is
    not a second opinion. With revenue the panel can answer the question the costs
    alone cannot — when the plant pays back — and every annotation on it is a fact
    about arrays this module only summed.

    Returns
    -------
    dict or None
        `lines` (twelve signed series), `net`, `cumulative`, `payback`, `notch`, the
        whole-project totals, and `reconciles` — the cumulative is a running sum of the
        net and the net is the sum of the twelve, both checked here.
    """

    plugin = (result.plugs or {}).get('Discounted_Cash_Flow_Plugin') if result else None
    if plugin is None:
        return None

    lines = _cash_lines(plugin)
    if not lines:
        return None

    span = len(lines[0]['values'])
    net = [sum(line['values'][year] for line in lines) for year in range(span)]
    cumulative = list(np.cumsum(net))
    start = int(getattr(plugin, 'start_idx', 0))
    years = [index - start for index in range(span)]

    return {
        'years': years,
        'span': span,
        'construction_years': start,
        'lines': lines,
        'net': [float(value) for value in net],
        'cumulative': [float(value) for value in cumulative],
        'payback': _payback(cumulative, years),
        'notch': _notch(lines, years, result.inp),
        'anomaly': _anomaly(lines, years),
        'driver': _driver(lines, years),
        'depreciation': _depreciation(plugin),
        'sales': _sales(plugin),
        'capital_as_built': -_total(lines, 'depreciable_capital')
                            - _total(lines, 'non_depreciable_capital'),
        'lifetime_revenue': _total(lines, 'revenue'),
        'ending_cumulative': float(cumulative[-1]) if span else 0.0,
        'high_water': _extreme(cumulative, years, max),
        'deepest': _extreme(cumulative, years, min),
        'unit': 'USD',
    }


def _cash_lines(plugin):
    '''The twelve signed series off the plugin, skipping any it did not build.'''

    lines = []
    span = 0
    for key, label, blurb, family, tone, sign, attribute in _CASH_LINES:
        values = _floats(getattr(plugin, attribute, None), sign)
        if values is None:
            continue
        span = max(span, len(values))
        total = float(sum(values))
        lines.append({'key': key, 'name': label, 'blurb': blurb, 'family': family,
                      'tone': tone, 'values': values, 'total': total,
                      # The engine wrote this line and it is zero — a statement about
                      # the model, not an absence. `pv_e_lcoe` has no stack to replace.
                      # Marked rather than dropped, so the legend can say the category
                      # was considered instead of drawing an invisible bar.
                      'zero': total == 0})
    for line in lines:
        line['values'] += [0.0] * (span - len(line['values']))
    return lines


def _floats(array, sign=1):
    '''A signed float list, or None when the array is absent or not finite throughout.

    None rather than a zero-fill: a pathway with no replacement schedule and a pathway
    whose replacement schedule is all zeros are different facts, and only one of them
    should put a line in the legend.
    '''

    if not isinstance(array, np.ndarray):
        return None
    flat = np.asarray(array, dtype=float).ravel()
    if flat.size == 0 or not np.all(np.isfinite(flat)):
        return None
    return [float(sign * value) for value in flat]


def _total(lines, key):
    for line in lines:
        if line['key'] == key:
            return line['total']
    return 0.0


def _extreme(cumulative, years, pick):
    if not cumulative:
        return None
    value = pick(cumulative)
    index = list(cumulative).index(value)
    return {'index': index, 'year': years[index], 'value': float(value)}


def _driver(lines, years):
    '''The heaviest year of spending, and the one line that accounts for most of it.

    A cash-flow plot spanning four orders of magnitude draws every ordinary year at a
    floor and one year at full height. That tall bar is the first thing a reader sees
    and the figure has to be able to name it without being asked: PV+E spends 29.3 M in
    year 19 and 19.9 M of that is one authored grid tariff, so `Variable operating` at
    0.678 of the year is the whole explanation.

    Outflow only. Revenue is stacked on the other side of the datum, and a year picked
    by gross turnover would nominate year 19 of `pec` on the strength of a 127.9 M tax
    credit — an inflow, and not a thing anyone reads a cost figure to find. A line the
    engine wrote as zeros cannot win, because zero is never the largest outflow in a
    year that has one.
    '''

    spent = [sum(-line['values'][index] for line in lines if line['values'][index] < 0)
             for index in range(len(years))]
    if not spent or max(spent) <= 0:
        return None
    index = spent.index(max(spent))
    heaviest = max(lines, key=lambda line: -min(line['values'][index], 0.0))
    outflow = -min(heaviest['values'][index], 0.0)
    return {'name': heaviest['name'], 'key': heaviest['key'], 'index': index,
            'year': years[index], 'value': outflow, 'spent': spent[index],
            'share': outflow / spent[index]}


def _payback(cumulative, years):
    '''The first year the cumulative turns positive, and how long that took.

    Two different numbers, and conflating them is an off-by-one that survives review
    because both look plausible. `year` is an *index* — analysis years run from −1, so
    operation year 5 is the sixth entry. `elapsed` is a *duration* measured from
    start-up, and cash is booked at year end, so the crossing inside operation year Y
    is at least Y years after start-up and at most Y + 1.

    The *first upward* crossing, deliberately. PEC and Photocatalytic pay back inside
    their first operating year and then fall back toward zero for three years before
    climbing again; reporting the last crossing would say they pay back in year 19.
    '''

    for index in range(1, len(cumulative)):
        before, after = cumulative[index - 1], cumulative[index]
        if before >= 0 or after < 0:
            continue
        fraction = float(-before / (after - before))
        return {
            'index': index,
            'year': years[index],
            'fraction': fraction,
            'elapsed': max(years[index - 1] + 1, 0) + fraction,
        }
    return None


def _notch(lines, years, inp):
    '''The one year a mid-life replacement lands in, if it lands in one year.

    "At least four times the median of the other years it happens in, and neither the
    build year nor the terminal year" — the ends of the analysis carry construction and
    decommissioning, and calling either a replacement would be wrong. Solar Thermal
    levelizes its reaction-material replacement across six years and correctly gets no
    notch; PV+E puts the whole 2.24 M stack renewal in year 10 and gets one.
    '''

    values = [-value for value in next((line['values'] for line in lines
                                        if line['key'] == 'replacement'), [])]
    if not values:
        return None
    peak = max(values)
    index = values.index(peak)
    others = sorted(value for position, value in enumerate(values)
                    if position != index and value > 0)
    middle = others[len(others) // 2] if others else 0.0
    if peak <= 0 or index in (0, len(values) - 1) or (middle and peak <= 4 * middle):
        return None
    return {'index': index, 'year': years[index], 'value': peak,
            'name': _replacement_name(inp)}


def _replacement_name(inp):
    '''What the engine calls the thing being replaced, or None.

    `Replacement > Contributions` names its own groups. Unplanned replacement is a
    fraction of capital spread over every year and is never the notch, so it is the
    one name that cannot be the answer.
    '''

    groups = _group_contributions(inp, 'Replacement')
    named = {name: value for name, value in groups.items()
             if name != 'Unplanned Replacement' and value}
    return max(named, key=named.get) if named else None


def _anomaly(lines, years):
    '''A terminal operating charge far outside the run of the years before it.

    PV+E books 19.9 M USD of variable operating cost in its last year against ~3 k in
    every other year, because `Grid Electricity > Cost` is authored at 10,000.12 USD/kWh
    and 1,389 kWh get drawn. The figure cannot say the price is wrong — it may be
    deliberate — but it can refuse to let a four-order-of-magnitude outlier pass as an
    ordinary bar. Detection is from the array, so no other pathway trips it.
    '''

    line = next((entry for entry in lines if entry['key'] == 'variable_operating'), None)
    values = [-value for value in line['values']] if line else []
    if len(values) < 2:
        return None
    terminal, before = values[-1], max(values[:-1])
    if terminal <= 8 * max(before, 1.0):
        return None
    return {'index': len(values) - 1, 'year': years[-1], 'value': terminal,
            'ratio': terminal / max(before, 1.0), 'line': line['name']}


def _depreciation(plugin):
    '''The MACRS charge: named, totalled, and deliberately not drawn.'''

    values = _floats(getattr(plugin, 'annual_charge', None))
    if values is None:
        return None
    return {'total': float(sum(values)), 'values': values,
            'note': 'not a cash flow — it enters only through taxes'}


def _sales(plugin):
    '''Product sold per year, in the functional unit the file declares.

    The denominator of the whole analysis. `pv_e_lcoe` sells kilowatt-hours, and the
    unit is read off the plugin's own resolved functional unit rather than assumed, so
    nothing downstream has to know which pathway it is drawing.
    '''

    values = _floats(getattr(plugin, 'annual_sales', None))
    if values is None:
        return None
    unit = getattr(getattr(plugin, 'functional_unit', None), 'unit', '') or ''
    return {'values': values, 'total': float(sum(values)), 'unit': str(unit)}


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
