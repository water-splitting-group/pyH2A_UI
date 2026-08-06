'''Turning one engine value into an honest, JSON-safe record.

Everything the browser displays passes through `describe`. That is deliberate:
there is exactly one place where the rules below are enforced, so a screen cannot
quietly invent its own convention.

**The rule that matters most: show what the user wrote, not the SI base.** A
pyH2A `Quantity` holds two magnitudes — `supplied_value` in `supplied_unit`
(what the file says: `5500 kW`) and `base_value` in `base_unit` (SI:
`5500000 W`). Reading the base while printing the authored unit gives `5,500,000`
labelled `kW`: a wrong number wearing a right-looking label. That exact bug shipped
in an earlier build of this project and is the failure class the whole studio
exists to prevent, so `describe` reports the authored pair and carries the base
alongside, never instead.

**Arrays are digested, not truncated.** An 8,760-hour series cannot cross to the
browser as 8,760 floats seventeen times over, and no screen wants that: screens
want min, max, first, last, and a curve. So an array becomes a digest plus a
decimated envelope, computed at the moment the snapshot is taken — which is the
only moment its values are still the ones that step saw.
'''

import math
import numbers

import numpy as np
from pyH2A.Utilities.Unit_Handler import Quantity

ENVELOPE_POINTS = 96
'''Sample count for an array's drawn envelope. 96 is two per hour of a day, and
wide enough that a 365-point daily series keeps its shape.'''


def _finite(number):
    '''`float(number)`, or None when it is NaN or infinite.

    JSON has no NaN. More usefully, a non-finite value is nearly always a real
    engine result worth showing as a word rather than a broken number.
    '''

    try:
        value = float(number)
    except (TypeError, ValueError):
        return None
    return value if math.isfinite(value) else None


def _digest_array(array):
    '''Shape, extent and a drawable envelope for an ndarray.

    `kind` distinguishes the three shapes screens must draw differently:
    `'flat'` (every element equal — a line, not a curve), `'ramp'` (a strictly
    increasing index like `Year` 0…19), and `'series'` (anything else).
    '''

    flat = np.asarray(array, dtype=float).ravel()
    finite = flat[np.isfinite(flat)]
    if finite.size == 0:
        return {'length': int(flat.size), 'kind': 'empty'}

    low, high = float(np.min(finite)), float(np.max(finite))
    if low == high:
        kind = 'flat'
    elif finite.size > 2 and np.all(np.diff(finite) > 0):
        kind = 'ramp'
    else:
        kind = 'series'

    # Reduce over the whole bucket matrix at once. The obvious loop —
    # `[[np.min(b), np.max(b)] for b in buckets]` — costs two numpy calls per bucket,
    # which across a traced run came to 118,444 reductions and 90% of the time spent
    # building a trace. Two calls total instead, and the trace went from 151 ms to 32 ms
    # natively and from 1.7 s to under 300 ms under Pyodide.
    step = max(1, int(math.ceil(finite.size / ENVELOPE_POINTS)))
    buckets = finite[: (finite.size // step) * step].reshape(-1, step)
    lows = np.min(buckets, axis=1)
    highs = np.max(buckets, axis=1)
    envelope = [[float(low), float(high)] for low, high in zip(lows, highs)]

    return {
        'length': int(flat.size),
        'kind': kind,
        'min': low,
        'max': high,
        'first': _finite(finite[0]),
        'last': _finite(finite[-1]),
        'mean': _finite(np.mean(finite)),
        'sum': _finite(np.sum(finite)),
        'envelope': envelope,
    }


def _describe_quantity(quantity):
    '''The authored pair, the SI pair, and a digest when the magnitude is an array.'''

    supplied = quantity.supplied_value
    record = {
        'form': 'quantity',
        'unit': quantity.supplied_unit or '',
        'dimension': str(getattr(quantity, 'dimension', '') or ''),
        'base_unit': str(getattr(quantity, 'base_unit', '') or ''),
    }

    if isinstance(supplied, np.ndarray):
        record['form'] = 'quantity_array'
        record['array'] = _digest_array(supplied)
        return record

    record['value'] = _finite(supplied)
    if record['value'] is None:
        record['text'] = str(supplied)
    base = _finite(getattr(quantity, 'base_value', None))
    if base is not None:
        record['base_value'] = base
    return record


def describe(value):
    '''One engine value as a JSON-safe record.

    The `form` field says what a screen is looking at, and every form is
    displayable without further type inspection:

    ==================  ===========================================================
    `'number'`          `value`
    `'quantity'`        `value` + `unit` (authored), `base_value` + `base_unit`
    `'quantity_array'`  `unit` + `array` digest
    `'array'`           `array` digest, no unit known
    `'years'`           `years`: a `{year: digest-or-number}` mapping
    `'text'`            `text`
    `'absent'`          nothing was there
    ==================  ===========================================================
    '''

    if value is None:
        return {'form': 'absent'}

    if isinstance(value, Quantity):
        return _describe_quantity(value)

    if isinstance(value, np.ndarray):
        return {'form': 'array', 'array': _digest_array(value)}

    if isinstance(value, dict):
        return _describe_mapping(value)

    return _describe_scalar(value)


def _describe_scalar(value):
    '''A bool, a number, or anything else that has to become text.'''

    if isinstance(value, bool):
        return {'form': 'text', 'text': 'true' if value else 'false'}

    if isinstance(value, numbers.Number):
        number = _finite(value)
        if number is None:
            return {'form': 'text', 'text': str(value)}
        return {'form': 'number', 'value': number}

    text = str(value)
    return {'form': 'text', 'text': text if len(text) <= 400 else text[:397] + '…'}


def _is_year(key):
    '''True for a whole-number key, int or float.

    The engine keys per-year dicts with whatever arithmetic produced — some plugins
    write `0, 1, 2`, others write `0.0, 1.0, 2.0`. Testing only for `int` sent every
    float-keyed series down the fallback path and rendered a twenty-year array as the
    text `{0.0, 1.0, 2.0, …}`.
    '''

    if isinstance(key, bool):
        return False
    if isinstance(key, (int, np.integer)):
        return True
    return isinstance(key, (float, np.floating)) and float(key).is_integer()


def _describe_mapping(mapping):
    '''A dict value: the per-year shape the engine uses everywhere, or a plain map.

    Several plugins hold `{0: Quantity(ndarray), 1: …}` — one entry per analysis year,
    each year an 8,760-hour array. Describing that recursively is correct and useless:
    three such rows came to 194 KB of a 252 KB panel, and no list view has ever wanted
    twenty separate hourly envelopes.

    What a reader wants from a per-year series is the shape *across* years — does
    production fall as the stack degrades, does the battery fill more in year 10 — so
    that is what this computes: one number per year, plus the overall extent. Each
    year's number is the sum when the year holds an array (an annual total) and the
    value itself when it holds a scalar.

    The hourly detail inside a single year is not lost, it is simply not carried here.
    A screen that draws one year's 8,760 hours asks for that year specifically.
    '''

    if mapping and all(_is_year(key) for key in mapping):
        return _describe_years(mapping)

    return {
        'form': 'text',
        'text': f'{{{", ".join(str(k) for k in list(mapping)[:6])}'
                f'{", …" if len(mapping) > 6 else ""}}}',
        'keys': [str(key) for key in mapping],
    }


def _describe_years(mapping):
    '''One number per analysis year, plus the extent across all of them.'''

    per_year = []
    unit = ''
    inner = 'number'
    inner_length = 0
    inner_max = None
    for key in sorted(mapping):
        record = describe(mapping[key])
        unit = unit or record.get('unit') or ''
        array = record.get('array')
        if array:
            inner = 'array'
            # How long *one year* is. 8,760 is an hour-by-hour year and 365 a daily
            # one; they are drawn completely differently, and a reader offered a
            # 365-point series as an hourly calendar has been lied to about the
            # resolution of the model.
            inner_length = max(inner_length, array.get('length') or 0)
            # The largest *element* across all years, which is a completely different
            # number from the largest annual total and is the only one a per-hour
            # colour scale can use. Ceilinging an hourly calendar at an annual sum is a
            # factor of 2,744 for this data and paints every cell at the ink floor.
            if array.get('max') is not None:
                inner_max = array['max'] if inner_max is None else max(inner_max, array['max'])
            per_year.append(array.get('sum'))
        else:
            per_year.append(record.get('value'))

    present = [value for value in per_year if value is not None]
    return {
        'form': 'years',
        'count': len(per_year),
        'unit': unit,
        'inner': inner,
        'inner_length': inner_length,
        'inner_max': inner_max,
        'per_year': per_year,
        'min': min(present) if present else None,
        'max': max(present) if present else None,
        'first': per_year[0] if per_year else None,
        'last': per_year[-1] if per_year else None,
    }


def is_series(record):
    '''True when a record carries an array digest a screen can draw.'''

    return record.get('form') in ('array', 'quantity_array')


def magnitude(record):
    '''A single comparable float out of any record, or None.

    Used for sorting and for change detection — never for display, which must go
    through the authored pair.
    '''

    if 'value' in record:
        return record['value']
    array = record.get('array')
    if array and 'max' in array:
        return array['max']
    return None
