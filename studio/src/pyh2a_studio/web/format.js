/* Turning a cell record into something readable.
 *
 * Every record arriving from Python has a `form` that says what it is; this module
 * is the only place that switches on it. Two rules are enforced here rather than
 * hoped for:
 *
 *   A number never appears without its unit. `4.1943` alone is not an answer to any
 *   question in this app — the same machinery prices hydrogen in USD/kg and
 *   electricity in USD/kWh, so a bare float is genuinely ambiguous.
 *
 *   A series is drawn, not summarised into a lie. `14,680,800 → 14,738,400` renders
 *   at three significant figures as `14,700,000 → 14,700,000`, i.e. "nothing
 *   changes", about a series that changes. `range()` raises precision until the two
 *   ends actually differ.
 */

const NBSP = '\u202F';   // narrow no-break space: digit grouping that never wraps

/** A number with thin-space grouping and sensible precision. */
export function num(value, significant = 4) {
  if (value === null || value === undefined || !isFinite(value)) return '—';
  if (value === 0) return '0';

  const magnitude = Math.abs(value);
  if (magnitude >= 1e7 || magnitude < 1e-4) {
    return value.toExponential(2).replace('e', 'e');
  }
  const decimals = magnitude >= 1000 ? 0
    : magnitude >= 1 ? Math.max(0, significant - 1 - Math.floor(Math.log10(magnitude)))
    : significant;
  const text = value.toFixed(Math.min(decimals, 8));
  const trimmed = text.includes('.') ? text.replace(/0+$/, '').replace(/\.$/, '') : text;
  const [whole, fraction] = trimmed.split('.');
  const grouped = whole.replace(/\B(?=(\d{3})+(?!\d))/g, NBSP);
  return fraction ? `${grouped}.${fraction}` : grouped;
}

const SUPERSCRIPT = { '-': '⁻', 0: '⁰', 1: '¹', 2: '²', 3: '³', 4: '⁴',
  5: '⁵', 6: '⁶', 7: '⁷', 8: '⁸', 9: '⁹' };

/**
 * Two ends of a range, at whatever precision makes them differ, sharing one exponent.
 *
 * Two problems solved together. Precision: `14,680,800 → 14,738,400` at three
 * significant figures is `14,700,000 → 14,700,000`, i.e. "nothing changes", about a
 * series that changes — so precision rises until the ends differ. Width: two
 * independent exponentials (`9.42e+13 → 8.57e+13 J`) do not fit a table column and
 * repeat the same magnitude twice. Factoring the exponent out gives
 * `9.42 → 8.57 ×10¹³`, which is shorter and reads as one measurement.
 */
export function range(low, high, arrow = false) {
  if (low === null || high === null || low === undefined || high === undefined) return '—';

  const scale = Math.max(Math.abs(low), Math.abs(high));
  if (scale >= 1e7 || (scale > 0 && scale < 1e-3)) {
    const exponent = Math.floor(Math.log10(scale));
    const factor = 10 ** exponent;
    const digits = String(exponent).split('').map((c) => SUPERSCRIPT[c]).join('');
    const a = (low / factor).toFixed(2);
    const b = (high / factor).toFixed(2);
    return a === b ? `${a}×10${digits}` : `${a} ${arrow ? '→' : '…'} ${b} ×10${digits}`;
  }

  for (let significant = 3; significant <= 9; significant += 1) {
    const a = num(low, significant);
    const b = num(high, significant);
    if (a !== b) return `${a} ${arrow ? '→' : '…'} ${b}`;
  }
  return num(low, 4);
}

/**
 * The declared range, in the terms the field is written in.
 *
 * `…` deliberately, never `→`: an arrow means "moved from a to b over time" everywhere
 * else in this app, and a range does not move. Sharing the glyph produced rows reading
 * `6.73 → 7.40` beside a byte-identical *descending* sparkline.
 */
export function bounds(shown) {
  if (!shown) return '';
  // A range with no unit beside a value with no unit is two numbers in an unstated
  // system: `Module tilt` printed `0 … 1.57` two rows above `Array azimuth`'s
  // `0 … 180`, radians against degrees with only one of them named.
  const tag = shown.unit ? ` ${shown.unit}` : '';
  const mark = (value) => `${num(value, 3)}${shown.percent ? '%' : ''}`;
  if (shown.low !== null && shown.high !== null) return `${mark(shown.low)} … ${mark(shown.high)}${tag}`;
  if (shown.low !== null) return `≥ ${mark(shown.low)}${tag}`;
  if (shown.high !== null) return `≤ ${mark(shown.high)}${tag}`;
  return '';
}

/** A unit as a tag, or '' when the unit is absent or the placeholder dash. */
export function unitTag(unit) {
  if (!unit || unit === '-') return '';
  return `<span class="u">${escape(unit)}</span>`;
}

/**
 * A record as inline HTML: value plus unit, a range for a series, a word for text.
 *
 * Deliberately terse — this goes in table rows two hundred at a time. Anything
 * needing more room gets its own component.
 */
export function value(record) {
  if (!record) return '—';
  switch (record.form) {
    case 'number':
      return `<span class="q">${num(record.value)}</span>`;
    case 'quantity':
      return `<span class="q">${num(record.value)}</span>${unitTag(record.unit)}`;
    case 'array':
    case 'quantity_array': {
      const digest = record.array || {};
      if (digest.kind === 'empty') return '<span class="q">empty</span>';
      if (digest.kind === 'flat') {
        return `<span class="q">${num(digest.min)}</span>${unitTag(record.unit)}`
             + `<span class="u">×${digest.length}</span>`;
      }
      return `<span class="q">${range(digest.min, digest.max)}</span>${unitTag(record.unit)}`;
    }
    case 'years': {
      if (record.min === null) return `<span class="u">${record.count} years</span>`;
      // first → last, chronological, so the arrow is earned. The extent of the same
      // series would be `min … max` and is a different statement.
      return `<span class="q">${range(record.first, record.last, true)}</span>`
           + unitTag(record.unit) + `<span class="u">${record.count}y</span>`;
    }
    case 'text':
      // A mapping the engine keys by name rather than by year arrives as its key
      // list. Printing the keys is noise; their count is the fact.
      if (record.keys) {
        return `<span class="q">${record.keys.length}</span><span class="u">entries</span>`;
      }
      return `<span class="q">${escape(clip(record.text, 40))}</span>`;
    case 'absent':
      return '<span class="u">not yet</span>';
    default:
      return '—';
  }
}

/** The numbers a series carries, for a sparkline. */
export function points(record) {
  if (!record) return null;
  if (record.form === 'years' && record.per_year) {
    return record.per_year.filter((entry) => entry !== null);
  }
  const digest = record.array;
  if (!digest || !digest.envelope || digest.kind === 'flat') return null;
  return digest.envelope;
}

/**
 * A sparkline. An envelope (pairs of floor and peak) is drawn as a band; a plain
 * series is drawn as a line.
 *
 * Bands matter: pyH2A decimates 8,760-hour arrays into strict min/max pairs, so
 * drawing them as a polyline produces a zigzag that is an artefact of the
 * decimation rather than anything in the data.
 */
export function spark(record, width = 92, height = 14) {
  const data = points(record);
  if (!data || data.length < 2) return '';

  const paired = Array.isArray(data[0]);
  const lows = paired ? data.map((pair) => pair[0]) : data;
  const highs = paired ? data.map((pair) => pair[1]) : data;
  const low = Math.min(...lows);
  const high = Math.max(...highs);
  const span = high - low || 1;

  const x = (index) => (index / (data.length - 1)) * (width - 1) + 0.5;
  const y = (v) => height - 1.5 - ((v - low) / span) * (height - 3);

  if (paired) {
    const top = highs.map((v, i) => `${x(i).toFixed(1)},${y(v).toFixed(1)}`).join(' ');
    const bottom = lows.map((v, i) => `${x(i).toFixed(1)},${y(v).toFixed(1)}`)
      .reverse().join(' ');
    return `<svg class="spark" aria-hidden="true" viewBox="0 0 ${width} ${height}" preserveAspectRatio="none">`
         + `<polygon points="${top} ${bottom}" fill="currentColor" opacity="0.22"/>`
         + `<polyline points="${top}" fill="none" stroke="currentColor" stroke-width="1"/>`
         + `</svg>`;
  }

  const line = data.map((v, i) => `${x(i).toFixed(1)},${y(v).toFixed(1)}`).join(' ');
  return `<svg class="spark" aria-hidden="true" viewBox="0 0 ${width} ${height}" preserveAspectRatio="none">`
       + `<polyline points="${line}" fill="none" stroke="currentColor" stroke-width="1.2"/>`
       + `</svg>`;
}

/**
 * A levelized cost, at the precision pyH2A publishes: always four decimals.
 *
 * `num` trims trailing zeros, which is right in a table — nobody wants `2.5000` — and
 * wrong for the headline. An edit taking 4.1943 to 4.1999748 rendered as `4.2`, which
 * sits in the same slot looking like a rounder, less-computed number than it is, and
 * cannot be compared against the published 4.1943 at a glance. Fixed precision also
 * matches how every reference cost in this domain is quoted: 4.1943, 139.4189, 0.0286.
 */
export function cost(value) {
  if (value === null || value === undefined || !isFinite(value)) return '—';
  const [whole, fraction] = Math.abs(value).toFixed(4).split('.');
  const grouped = whole.replace(/\B(?=(\d{3})+(?!\d))/g, NBSP);
  return `${value < 0 ? '−' : ''}${grouped}.${fraction}`;
}

const SI_STEPS = [[1e12, 'T'], [1e9, 'G'], [1e6, 'M'], [1e3, 'k']];

/**
 * A magnitude for a person: `34,221,356` → `34.2 M`.
 *
 * Exponential notation is correct and unreadable at a glance. An axis label, a
 * lifetime total, a legend entry — anywhere a reader is comparing magnitudes rather
 * than checking digits — wants the engineering prefix. Anywhere they might check the
 * arithmetic keeps `num`.
 */
export function compact(value, significant = 3) {
  if (value === null || value === undefined || !isFinite(value)) return '—';
  const magnitude = Math.abs(value);
  for (const [scale, suffix] of SI_STEPS) {
    if (magnitude >= scale) {
      return `${(value / scale).toPrecision(significant).replace(/\.?0+$/, '')} ${suffix}`;
    }
  }
  return num(value, significant);
}

export function escape(text) {
  return String(text ?? '').replace(/[&<>"']/g, (character) => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
  }[character]));
}

export function clip(text, limit) {
  const value = String(text ?? '');
  return value.length > limit ? `${value.slice(0, limit - 1)}…` : value;
}

/** Milliseconds, at a precision that suits the magnitude. */
export function ms(value) {
  if (value === null || value === undefined) return '—';
  if (value < 1) return `${value.toFixed(2)} ms`;
  if (value < 100) return `${value.toFixed(1)} ms`;
  return `${Math.round(value)} ms`;
}
