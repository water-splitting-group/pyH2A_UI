/* Figures, drawn where the step that made them is.
 *
 * Three, each answering a question its step's own numbers raise and nothing else on
 * the page answers:
 *
 *   the decomposition   — where the headline number comes from, and proof it adds up
 *   the annual costs    — when the money is spent, which is not when it is counted
 *   the calendar        — every hour of a year at once, which is the only honest way
 *                         to show 8,760 numbers whose shape is seasonal and diurnal
 *
 * All three draw engine values. Nothing is smoothed, nothing is interpolated, and
 * where a figure allocates a value into groups it prints its own residual so the
 * reader can see it lost nothing.
 *
 * They render into `.fig-stage`, about 1,490 px of cream paper with no padding and the
 * full height of the modal. Paper is the ground and the dark band is a zone inside it:
 * the machine speaks on `--dark` in the levelized-cost slab and the calendar's fact
 * band, and everything a reader has to read closely sits on paper where the hairlines
 * are. There is no fixed width on any root here — each one is `width: 100%` with a
 * floor, so a narrow window pans inside `.fig-stage` rather than clipping a figure.
 *
 * Nothing in this file knows what the product is. `pv_e_lcoe` runs the same PV
 * machinery to sell electricity at 0.0286 USD/kWh instead of hydrogen at 4.1943
 * USD/kg, so every axis label, every denominator and every noun is built from
 * `unit` / `functional_unit` / the cell's own declared unit. The word "hydrogen"
 * appears nowhere below on purpose.
 */

import { compact, cost, escape, num } from './format.js';

/**
 * A share as a percentage, without the negative zero.
 *
 * `(-2.89e-5 / 4.19 * 100).toFixed(2)` is `-0.00`, which reads as a sign attached to
 * nothing. End-of-life in PV+E is decommissioning almost exactly cancelled by salvage,
 * and the honest rendering of that is `~0`, not `-0.00%`.
 */
function percent(share, places = 1) {
  const value = share * 100;
  const text = value.toFixed(places);
  if (Number(text) === 0) return value === 0 ? '0 %' : '~0 %';
  return `${text.replace('-', '\u2212')} %`;
}

/**
 * Three significant figures at any magnitude, which `num` alone will not give.
 *
 * `num(v, 3)` reads its second argument as significant figures above 1 and as decimal
 * places below it, so a 0.004062 USD/kg reverse-osmosis row prints `0.004` — one
 * figure, and the digit that distinguishes it from the 0.000675 water-management row
 * on `pec` is gone. Converting figures to places first keeps `0.00406`.
 */
function sig(value, digits = 3) {
  if (value === null || value === undefined || !isFinite(value)) return '\u2014';
  if (value === 0) return '0';
  const exponent = Math.floor(Math.log10(Math.abs(value)));
  const text = num(value, exponent < 0 ? digits - 1 - exponent : digits);
  return text.replace('-', '\u2212');
}

/** `compact` with the typographic minus, for anything that carries a sign. */
function mag(value, digits = 3) {
  return compact(value, digits).replace('-', '\u2212');
}

const SUPERSCRIPT = { '-': '\u207B', '+': '', 0: '\u2070', 1: '\u00B9', 2: '\u00B2',
  3: '\u00B3', 4: '\u2074', 5: '\u2075', 6: '\u2076', 7: '\u2077', 8: '\u2078',
  9: '\u2079' };

/**
 * `8.88e-16` as `8.88 × 10⁻¹⁶`.
 *
 * A residual is read, not compared, and it is the one number on these sheets that is
 * shown at its true float value rather than rounded to a flattering zero.
 */
function scientific(value, digits = 2) {
  if (!isFinite(value)) return '\u2014';
  if (value === 0) return '0';
  const [mantissa, exponent] = value.toExponential(digits).split('e');
  return `${mantissa.replace('-', '\u2212')} \u00D7 10${
    [...exponent].map((character) => SUPERSCRIPT[character] ?? character).join('')}`;
}

/** A value and its unit as one package, never truncated. */
function qty(text, unit) {
  return `<b>${text}</b>${unit ? `<i class="u">${escape(unit)}</i>` : ''}`;
}

/** A label, a dotted leader, and a number — the drafting idiom for a summary row. */
function leader(label, value, className = '') {
  return `<div class="leader ${className}"><span class="lf">${label}</span>
    <span class="ld"></span><span class="lv">${value}</span></div>`;
}

/**
 * A tick step that lands on a number a person would have chosen.
 *
 * 2.5 is in the list because the `pec` cascade runs to 139.4189 USD/kg: at a target of
 * six intervals the raw step is 23.2, and without 2.5 the only candidate left is 100,
 * which labels the axis `0` and `100` and nothing else.
 */
function niceStep(raw) {
  const power = 10 ** Math.floor(Math.log10(raw));
  return ([1, 2, 2.5, 5, 10].find((factor) => factor * power >= raw) ?? 10) * power;
}

/** Ticks from zero to `ceiling`, inclusive of both ends where they land. */
function upTicks(ceiling, target = 6) {
  const step = niceStep(ceiling / target);
  const out = [];
  for (let value = 0; value <= ceiling * (1 + 1e-9); value += step) out.push(value);
  return out;
}

/** Ticks either side of a zero datum, anchored on zero so the datum is always one. */
function spanTicks(low, high, target = 9) {
  const step = niceStep((high - low) / target);
  const out = [];
  for (let value = 0; value <= high; value += step) out.push(value);
  for (let value = -step; value >= low; value -= step) out.push(value);
  return out.sort((a, b) => a - b);
}

/* ------------------------------------------------------------ decomposition
 *
 * A cascade, not a stacked bar. One horizontal scale runs across the lane and each
 * row draws its bar starting at the running total, so a row's *length* is its
 * magnitude and its *position* is everything that came before it. Read down and the
 * bars march left to right and land on the dark slab that carries the headline.
 *
 * The rows are `data.tributaries`, not `data.rows`. Four families are the right audit
 * and the wrong picture — "Capital 1.52 USD/kg" answers nothing about a plant — so the
 * engine's own itemisation of what the capital bought is opened up by plant unit and
 * everything downstream of the build stays at family level, where `Interest` and
 * `Taxes` are already the useful granularity. The families are still drawn, as
 * dimension lines over their own runs, and the Σ band proves the two agree.
 */

const FAMILY_INK = {
  capital: 'var(--fam-framework)',
  operating: 'var(--fam-solar)',
  financing: 'var(--potassium)',
  endoflife: 'var(--fam-scale)',
  other: 'var(--strontium)',
};

/*
 * What a figure calls itself.
 *
 * The modal used to print its own kicker and title from the catalogue — generic strings
 * chosen before the run — and then each plate printed a second pair underneath, built
 * from the run itself. You read "Where the money goes" and, two lines below it, "Where
 * the kWh price comes from", which is the same sentence with the answer in it.
 *
 * The plate's version wins, because only the renderer knows the tributary count, the
 * analysis span, or whether the plant pays back at all. It is handed up to the modal
 * instead of drawn twice: one title, in the sticky head, where it survives scrolling.
 */
export function decompositionHead(data) {
  const denominator = data && data.functional_unit;
  const unit = (data && data.unit) || '';
  return {
    kicker: `cost cascade · ${data.tributaries.length} tributaries`
      + ` · discounted, per ${denominator}`,
    title: `Where the ${unit.split('/')[1] || denominator} price comes from`,
  };
}

export function annualHead(data) {
  const span = data.span;
  return {
    kicker: `discounted cash flow · ${span} analysis years, nominal`,
    title: data.payback ? 'When the plant pays for itself'
      : 'Where the money goes, year by year',
  };
}

export function decomposition(data) {
  if (!data || !data.tributaries || !data.tributaries.length) return '';

  const unit = data.unit;
  const denominator = data.functional_unit;

  // The ceiling is the widest point the cascade reaches, which is not always the
  // total. Where decommissioning and salvage are drawn as separate streams the running
  // sum overshoots to 4.2636 and the credit pulls it back; scaling to the total would
  // push that overshoot off the end of the lane, and the one row whose job is to come
  // back would be the row you could not see.
  const ceiling = Math.max(data.total, ...data.tributaries.map(
    (part) => Math.max(part.start, part.end)));
  const at = (value) => `${((value / ceiling) * 100).toFixed(4)}%`;

  const groups = new Map();
  data.tributaries.forEach((part) => {
    if (!groups.has(part.family)) groups.set(part.family, []);
    groups.get(part.family).push(part);
  });

  let register = 0;
  const bands = data.families.map((family) => {
    const parts = groups.get(family.key) || [];
    groups.delete(family.key);
    return familyBand(family, parts, () => (register += 1), at, unit);
  }).join('');

  // Anything the engine named that this app has not been told where to file. The
  // reconciliation would catch a component that fell out of the grouping, but a stray
  // run on screen is the more useful warning because it names what upstream added.
  const stray = [...groups.values()].flat();

  const familySum = data.families.reduce((total, family) => total + family.subtotal, 0);
  const reconciles = Math.abs(data.residual) < 1e-9
    && Math.abs(data.headline_residual) < 1e-9
    && Math.abs(data.cascade_residual) < 1e-9
    && Math.abs(familySum - data.total) < 1e-9;

  return `<section class="dc">
    <header class="dc-head">
      <p class="dc-lede">Each stream enters at the part of the plant that incurs it and
        runs to the gate. The bar's length is the stream; where it starts is everything
        bought before it. ${data.rows.length} engine components, regrouped into
        ${data.tributaries.length} streams and audited below against both.</p>
    </header>

    <div class="dc-row dc-axis">
      <span class="dc-reg"></span>
      <span class="dc-name kicker">stream</span>
      <span class="dc-val kicker">${escape(unit)}</span>
      <span class="dc-share kicker">share</span>
      <span class="dc-lane">${upTicks(ceiling).map((tick) => `<i class="dc-tick${
    tick / ceiling > 0.84 ? ' dc-tick-end' : ''}"
        style="left:${at(tick)}"><span>${sig(tick)}</span></i>`).join('')}
        <i class="dc-tick dc-tick-total${data.total / ceiling > 0.84 ? ' dc-tick-end' : ''}"
          style="left:${at(data.total)}"
          ><span>total ${cost(data.total)}</span></i></span>
    </div>

    ${bands}${stray.length ? familyBand({
      key: 'other', label: 'Unclassified', blurb: 'the engine names these; this app has'
        + ' not been told where they belong', subtotal: stray.reduce(
        (total, part) => total + part.value, 0),
      share: stray.reduce((total, part) => total + part.share, 0),
    }, stray, () => (register += 1), at, unit) : ''}

    <div class="dc-row dc-land">
      <span class="dc-reg"></span><span class="dc-name"></span>
      <span class="dc-val"></span><span class="dc-share"></span>
      <span class="dc-lane"><i style="width:${at(data.total)}"></i></span>
    </div>

    <div class="dc-slab">
      <div class="dc-hero">
        <span class="kicker">levelized cost of product</span>
        <div class="dc-hero-n">${qty(cost(data.total), unit)}</div>
        <span class="dc-path">Dependent Variables \u203A Levelized cost</span>
      </div>
      <div class="dc-audit">
        <span class="kicker">self-audit \u00B7 reconciliation at four decimal places</span>
        ${leader(`\u03A3 of ${data.tributaries.length} streams drawn above`,
    qty(cost(data.total + data.cascade_residual), unit))}
        ${leader(`\u03A3 of ${data.rows.length} engine components`,
    qty(cost(data.total + data.residual), unit))}
        ${leader(`\u03A3 of ${data.families.length} family subtotals`,
    qty(cost(familySum), unit))}
        ${leader('headline levelized cost', qty(cost(data.headline), unit))}
        <div class="dc-resid ${reconciles ? 'ok' : 'bad'}">
          <span class="dc-sigma">\u03A3</span>
          <span class="dc-resid-t">${reconciles
    ? `every regrouping lands on the headline. Largest residual
       <b>${scientific(Math.max(Math.abs(data.residual),
      Math.abs(data.cascade_residual), Math.abs(data.headline_residual)))}</b> ${escape(unit)}`
    : `these parts do <b>not</b> sum to the headline \u2014 residual
       <b>${scientific(data.residual, 3)}</b> ${escape(unit)}`}</span>
          <span class="dc-stamp">${reconciles ? 'reconciles' : 'does not reconcile'}</span>
        </div>
      </div>
      <div class="dc-fams">
        <span class="kicker">the same money, in four families</span>
        <div class="dc-fam-cards">${data.families.map((family) => `
          <div class="dc-fam-card" style="--fam:${FAMILY_INK[family.key] || 'var(--ash)'}">
            <span class="kicker">${escape(family.label)}</span>
            <div class="dc-fam-n">${qty(sig(family.subtotal), unit)}</div>
            <span class="dc-fam-s">${percent(family.share)} of total</span>
            <span class="dc-fam-bar"><i style="width:${Math.abs(
    family.share * 100).toFixed(2)}%"></i></span>
          </div>`).join('')}</div>
      </div>
    </div>
  </section>`;
}

/** One family: a header carrying its subtotal as a dimension line, then its streams. */
function familyBand(family, parts, next, at, unit) {
  const ink = FAMILY_INK[family.key] || 'var(--ash)';
  const low = Math.min(...parts.map((part) => Math.min(part.start, part.end)), 0);
  const high = Math.max(...parts.map((part) => Math.max(part.start, part.end)), 0);

  // A family whose one stream carries the family's own name states itself twice: on
  // `pv_e_lcoe` the plate read "Operating · spent every year the plant runs · 0.00313"
  // and then, on the next line, "05 · Operating · spent every year the plant runs ·
  // 0.00313". Three of the four families did it. The subtotal row adds nothing a reader
  // cannot see in the single stream under it, so it is dropped — the family chip moves
  // down so the colour still says which family this is.
  const echo = parts.length === 1 && parts[0].label === family.label;

  return `<div class="dc-band${echo ? ' dc-band-one' : ''}" style="--fam:${ink}">
    ${echo ? '' : `<div class="dc-row dc-fam">
      <span class="dc-reg"><i class="dc-chip"></i></span>
      <span class="dc-name"><b>${escape(family.label)}</b>
        <em>${escape(family.blurb || '')}</em></span>
      <span class="dc-val">${qty(sig(family.subtotal), unit)}</span>
      <span class="dc-share">${percent(family.share)}</span>
      <span class="dc-lane"><i class="dc-dim" style="left:${at(low)};width:${
    at(Math.max(high - low, 0))}"><span>${sig(family.subtotal)} ${escape(unit)}</span></i>
      </span>
    </div>`}
    ${parts.map((part) => streamRow(part, next(), at, unit)).join('')}
  </div>`;
}

/** One stream of the cascade. */
function streamRow(part, register, at, unit) {
  const negative = part.value < 0;
  const left = negative ? part.end : part.start;
  const width = Math.abs(part.value);

  // A stream can be four orders of magnitude smaller than its neighbour and still be a
  // real number: `pec` files 0.000675 USD/kg of water management next to 114.84 of cell
  // replacement, 0.0005 % of the lane. It gets a carry tick at its position rather than
  // a bar rounded up to something it is not, and the value is in the row either way.
  const bar = part.zero
    ? `<i class="dc-zero" style="left:${at(left)}"></i>`
    : `<i class="dc-bar ${negative ? 'neg' : ''}" style="left:${at(left)};width:${
      at(width)}"></i>`;

  return `<div class="dc-row dc-stream" title="${escape(`${part.label} · ${
    part.value} ${unit} · runs ${part.start} → ${part.end}`)}">
    <span class="dc-reg">${String(register).padStart(2, '0')}</span>
    <span class="dc-name"><b>${escape(part.label)}</b>
      ${part.note ? `<em>${escape(part.note)}</em>` : ''}
      <small>${streamBasis(part, unit)}</small></span>
    <span class="dc-val">${qty(sig(part.value), unit)}</span>
    <span class="dc-share">${percent(part.share, 2)}</span>
    <span class="dc-lane"><i class="dc-carry" style="left:${at(part.start)}"></i>${bar}
      ${negative ? '<i class="dc-credit" style="left:' + at(part.start)
    + '"><span>credit</span></i>' : ''}</span>
  </div>`;
}

/**
 * The second level, in the terms the engine itemised it in.
 *
 * A `unit` stream carries the as-built USD its group actually cost and the share of
 * depreciable capital that is — the numbers `_capital_split` checked against
 * `Depreciable Capital Costs > Total` before it agreed to divide anything. A `family`
 * stream carries the engine's own component rows, which is where the end-of-life
 * finding lives: decommissioning and salvage are equal and opposite to five figures,
 * and a reader who only saw the family net of −2.89 × 10⁻⁵ would not know why.
 */
function streamBasis(part, unit) {
  if (part.zero) return 'exactly zero \u2014 the engine wrote this stream and it is nil';
  if (part.kind === 'unit' && part.basis) {
    return `${num(part.basis.usd)} USD as built \u00B7 ${percent(part.basis.share)
    } of depreciable capital, pro rata`;
  }
  if (part.rows && part.rows.length > 1) {
    return part.rows.map((row) => `${escape(row.name)} ${sig(row.value)}`)
      .join(' \u00B7 ') + ` ${escape(unit)}`;
  }
  return '';
}

/* ------------------------------------------------------------ annual costs
 *
 * Twenty-one analysis years, stacked, with the nominal cumulative over them and the
 * payback crossing marked. Inflows above the datum and outflows below, per year, on
 * whichever side each line's own sign puts it — a negative tax is a credit and belongs
 * above the zero line, and PV+E books a 5.25 M one in its final year.
 *
 * The axis is a single linear scale over the whole range, and on PV+E that means one
 * bar eight times the height of every other. The prototype this ports from broke the
 * axis 4.4:1 below −8 M to give the mid-run more room, which is a defensible drafting
 * device and the wrong one here: that outlier *is* the finding on this pathway — an
 * authored 10,000.12 USD/kWh tariff, note ③ — and compressing it to a comfortable
 * height makes the sheet's own caption describe something the reader cannot see. The
 * per-year composition that a compressed axis was buying is served instead by the scan
 * band across the top, which carries all twelve lines of whichever year is under the
 * cursor at full precision.
 */

/* Every coordinate in this figure derives from here, so the plot's proportions are set
 * in one place. It was 1160 × 600, an aspect of 1.93, which at the width the modal gives
 * it drew 420px tall beside a summary column 548px tall — a 128px hole under the plot,
 * and bars flattened into a band you could not read a year out of. Taller viewBox, same
 * width: the drawing gains the height rather than being stretched into it. */
const PLOT = { width: 1160, height: 700, left: 46, right: 1104, top: 76, bottom: 620 };

export function annual(data) {
  if (!data || !data.lines || !data.lines.length) return '';

  const lines = data.lines;
  const span = data.span;
  const years = data.years;
  const unit = data.unit;
  const inflow = [];
  const outflow = [];
  for (let index = 0; index < span; index += 1) {
    inflow.push(lines.reduce((sum, line) => sum + Math.max(line.values[index], 0), 0));
    outflow.push(lines.reduce((sum, line) => sum + Math.min(line.values[index], 0), 0));
  }

  // The cumulative is on the same axis as the bars and it leaves their range: PV+E's
  // high water is 13.47 M against a 9.14 M tallest inflow stack. Scaling to the bars
  // alone clipped the line straight through the top of the plot.
  const high = Math.max(...inflow, ...data.cumulative, 0);
  const low = Math.min(...outflow, ...data.cumulative, 0);
  const pad = (high - low) * 0.04 || 1;
  const hi = high + pad;
  const lo = low - pad;

  const step = (PLOT.right - PLOT.left) / span;
  const barWidth = Math.min(38, step * 0.68);
  const x = (index) => PLOT.left + step * (index + 0.5);
  const y = (value) => PLOT.bottom - ((value - lo) / (hi - lo)) * (PLOT.bottom - PLOT.top);
  const datum = y(0);

  const marks = annotations(data, x, y, datum);

  return `<section class="cf">
    <header class="cf-head">
      <div>
        <p class="cf-lede">${span} years of the engine's own cash table: one year built,
          ${span - data.construction_years} operated${data.sales
    ? `, ${mag(data.sales.total)} ${escape(data.sales.unit)} sold` : ''}. Cash in above
          the datum, cash out below, and the line is the running sum of the two.</p>
      </div>
      ${payback(data)}
    </header>

    <div class="cf-body">
      <aside class="cf-side">
        <span class="kicker">whole-project summary</span>
        ${leader('capital, as built', qty(mag(data.capital_as_built), unit))}
        ${leader('lifetime revenue', qty(mag(data.lifetime_revenue), unit))}
        ${data.high_water ? leader('high water',
    `${qty(mag(data.high_water.value), unit)}<span class="ly">yr ${
      data.high_water.year}</span>`) : ''}
        ${data.deepest ? leader('deepest', `${qty(mag(data.deepest.value), unit)
    }<span class="ly">yr ${data.deepest.year}</span>`) : ''}
        ${leader(`cumulative, year ${years[span - 1]}`,
    qty(mag(data.ending_cumulative), unit))}

        <span class="kicker cf-legend-h">all ${span} years \u00B7 lifetime totals</span>
        ${legend(lines, unit)}
        ${data.depreciation ? `<p class="cf-depr">And one array that is
          <b>not</b> drawn: ${escape(data.depreciation.note)} \u2014
          ${mag(data.depreciation.total)} ${escape(unit)} of it. Stacking it would break
          the one property this figure rests on, that a year's segments sum to its
          net.</p>` : ''}
      </aside>

      <div class="cf-plot">
        <svg viewBox="0 0 ${PLOT.width} ${PLOT.height}" role="img"
          aria-label="${escape(`${span} years of nominal cash flow, ${
            mag(data.ending_cumulative)} ${unit} cumulative at year ${years[span - 1]}${
            data.payback ? `, payback in operation year ${data.payback.year}` : ''}`)}">
          ${restBand(data, lines, unit)}
          ${grid(y, datum, unit, hi, lo)}
          ${deficit(data, x, y)}
          ${bars(data, lines, x, y, datum, barWidth, step, unit)}
          ${cumulative(data, x, y)}
          ${marks.svg}
          ${axis(data, x, step)}
        </svg>
      </div>
    </div>

    <footer class="cf-foot">
      <div class="cf-key">
        <span class="kicker">above the datum = cash in \u00B7 below = cash out
          \u00B7 nominal, undiscounted</span>
      </div>
      <div class="cf-notes">${marks.notes}</div>
    </footer>
  </section>`;
}

/** The hero: an index, labelled as one, beside the duration it is not. */
function payback(data) {
  if (!data.payback) {
    return `<div class="cf-hero none">
      <b>\u2014</b>
      <span class="kicker">never pays back<br>in nominal terms</span>
      <small>the cumulative does not cross zero from below inside the analysis</small>
    </div>`;
  }
  return `<div class="cf-hero">
    <b>${data.payback.year}</b>
    <span class="kicker">payback in<br>operation year</span>
    <small>cumulative turns positive ${data.payback.elapsed.toFixed(2)} yr after
      start-up \u2014 an index and a duration, and they differ by one</small>
  </div>`;
}

/** Lifetime totals, each with its own bar, against the largest line. */
function legend(lines, unit) {
  const widest = Math.max(...lines.map((line) => Math.abs(line.total))) || 1;
  return `<div class="cf-legend">${lines.map((line) => `
    <div class="cf-leg" style="--ink:var(--cf-${line.family}-${line.tone}, var(--ash))">
      <i class="cf-sw"></i>
      <span class="cf-leg-n">${escape(line.name)}${line.zero
    ? '<em>engine wrote zero</em>' : ''}</span>
      <span class="cf-leg-g"><i style="width:${
      ((Math.abs(line.total) / widest) * 100).toFixed(2)}%"></i></span>
      <span class="cf-leg-v">${mag(line.total)}</span>
    </div>`).join('')}
    <div class="cf-leg cf-leg-sum">
      <i></i><span class="cf-leg-n">${lines.length} lines</span>
      <span class="cf-leg-g"></span>
      <span class="cf-leg-v">${escape(unit)}</span>
    </div>
  </div>`;
}

/**
 * The readout band above the plot: twelve fixed columns, so a year reads like a strip
 * chart rather than a tooltip.
 *
 * The columns are in the same order and the same place for every year, which is the
 * whole point — a reader comparing year 9 to year 10 is comparing two positions, not
 * re-reading two lists. At rest the band carries the self-audit instead: the sum of the
 * twelve lines over all years and the final cumulative are the same number, and if they
 * ever stop being the same number this figure is drawing nothing.
 */
function restBand(data, lines, unit) {
  const netSum = data.net.reduce((sum, value) => sum + value, 0);
  const last = 30 + (Math.ceil(lines.length / SCAN_COLUMNS) - 1) * 13;
  return `<g class="cf-rest" aria-hidden="true">
    <text x="0" y="12" class="cf-scan-k">ALL ${data.span} YEARS</text>
    <text x="${SCAN_HINT}" y="12" class="cf-scan-n">hover a year for its
      ${lines.length} lines at full precision</text>
    <text x="0" y="${last.toFixed(1)}" class="cf-scan-k">\u03A3 NET</text>
    <text x="${PLOT.left}" y="${last.toFixed(1)}" class="cf-scan-b">${mag(netSum)} ${
    escape(unit)}</text>
    <text x="${PLOT.left + 130}" y="${last.toFixed(1)}" class="cf-scan-n">= CUMULATIVE,
      YEAR ${data.years[data.span - 1]} ${mag(data.ending_cumulative)} \u2014 the annual
      detail reconciles to the headline</text>
  </g>`;
}

const SCAN_COLUMNS = 4;

/* The resting band's two rows are label-then-value. The lower label is "Σ NET" and
 * clears the plot's left edge at 46; the upper one is "ALL 21 YEARS" and does not — it
 * runs to 66, so the hint beside it started nine pixels inside the word "YEARS". Only
 * the hint moves: the Σ row's value is aligned to the plot edge on purpose. */
const SCAN_HINT = 76;

/** One year's readout, in the band the plot leaves clear above itself. */
function scanFor(data, lines, index, unit) {
  const width = (PLOT.width - PLOT.left) / SCAN_COLUMNS;
  const cells = lines.map((line, order) => {
    const value = line.values[index];
    if (!value) return '';
    const left = PLOT.left + (order % SCAN_COLUMNS) * width;
    const y = 30 + Math.floor(order / SCAN_COLUMNS) * 13;
    return `<text x="${left.toFixed(1)}" y="${y}" class="cf-scan-n">${
      escape(line.name)}</text>
      <text x="${(left + width - 14).toFixed(1)}" y="${y}" class="cf-scan-v"
        text-anchor="end">${mag(value)}</text>`;
  }).join('');

  return `<g class="cf-scan" aria-hidden="true">
    <text x="0" y="12" class="cf-scan-y">YEAR ${data.years[index]}</text>
    <text x="${PLOT.left}" y="12" class="cf-scan-k">NET</text>
    <text x="${PLOT.left + 34}" y="12" class="cf-scan-b">${mag(data.net[index])} ${
    escape(unit)}</text>
    <text x="${PLOT.left + 190}" y="12" class="cf-scan-k">CUMULATIVE</text>
    <text x="${PLOT.left + 272}" y="12" class="cf-scan-b">${
    mag(data.cumulative[index])} ${escape(unit)}</text>
    ${cells}
  </g>`;
}

/** Gridlines, and the zero datum drawn as an object rather than another gridline. */
function grid(y, datum, unit, hi, lo) {
  const ticks = spanTicks(lo, hi).map((tick) => `
    <line x1="${PLOT.left}" y1="${y(tick).toFixed(1)}" x2="${PLOT.right}"
      y2="${y(tick).toFixed(1)}" class="cf-grid"/>
    <text x="${PLOT.left - 8}" y="${(y(tick) + 3).toFixed(1)}" class="cf-vlab"
      text-anchor="end">${tick === 0 ? '0' : mag(tick)}</text>`).join('');

  return `<g class="cf-grids">${ticks}
    <text x="${PLOT.left - 8}" y="${(PLOT.top - 8).toFixed(1)}" class="cf-vlab"
      text-anchor="end">${escape(unit)}</text>
    <line x1="${PLOT.left - 15}" y1="${datum.toFixed(1)}" x2="${PLOT.right + 8}"
      y2="${datum.toFixed(1)}" class="cf-datum"/>
    <rect x="${PLOT.left - 18}" y="${(datum - 2).toFixed(1)}" width="4" height="4"
      class="cf-datum-cap"/>
  </g>`;
}

/**
 * The deficit: the field between the cumulative and the datum wherever the line is
 * under it.
 *
 * Drawn as the whole area under the line clipped to below the datum, which handles the
 * cases a per-run polygon gets wrong. `pec` and `photocatalytic` cross into profit
 * inside their first operating year, fall back toward zero for three years, and climb
 * again; the field appears twice and both are the same shading.
 */
function deficit(data, x, y) {
  const points = data.cumulative.map((value, index) => `${x(index).toFixed(1)},${
    y(value).toFixed(1)}`).join(' ');
  const datum = y(0).toFixed(1);
  return `<clipPath id="cf-under"><rect x="${PLOT.left}" y="${datum}"
      width="${PLOT.right - PLOT.left}" height="${(PLOT.bottom - y(0)).toFixed(1)}"/>
    </clipPath>
    <polygon class="cf-deficit" clip-path="url(#cf-under)"
      points="${x(0).toFixed(1)},${datum} ${points} ${
    x(data.span - 1).toFixed(1)},${datum}"/>`;
}

/**
 * The bars, and no minimum segment height.
 *
 * A floor would be the obvious kindness — PV+E's 4,902 USD of non-depreciable capital
 * is 0.01 % of the range and renders at six hundredths of a pixel — and it is the wrong
 * one, because the property this figure is built on is that a year's segments sum to
 * that year's net. Twelve floored hairlines would put a visible error on the shortest
 * bars, which are exactly the years where an error is hardest to notice. The scan band
 * carries every line of every year at full precision instead, reachable from a
 * full-height hit target whatever the bars measure.
 */
function bars(data, lines, x, y, datum, barWidth, step, unit) {
  return data.net.map((_, index) => {
    const left = x(index) - barWidth / 2;
    let up = datum;
    let down = datum;
    const segments = lines.map((line) => {
      const value = line.values[index];
      if (!value) return '';
      const height = Math.abs(y(value) - datum);
      const top = value > 0 ? (up -= height) : down;
      if (value < 0) down += height;
      return `<rect x="${left.toFixed(1)}" y="${top.toFixed(1)}"
        width="${barWidth.toFixed(1)}" height="${height.toFixed(2)}"
        fill="var(--cf-${line.family}-${line.tone}, var(--ash))"/>`;
    }).join('');

    return `<g class="cf-yr">${segments}
      <rect x="${(x(index) - step / 2).toFixed(1)}" y="${PLOT.top}" width="${
      step.toFixed(1)}" height="${(PLOT.bottom - PLOT.top).toFixed(1)}"
        class="cf-hit" fill="none" pointer-events="all"><title>${escape(
      `year ${data.years[index]} · net ${mag(data.net[index])} ${unit} · cumulative ${
        mag(data.cumulative[index])} ${unit}`)}</title></rect>
      <rect x="${(x(index) - step / 2).toFixed(1)}" y="${PLOT.top}" width="${
      step.toFixed(1)}" height="${(PLOT.bottom - PLOT.top).toFixed(1)}"
        class="cf-tint"/>
    </g>`;
  }).join('');
}

/** The nominal cumulative, cased in paper so it stays legible over a bar. */
function cumulative(data, x, y) {
  const points = data.cumulative.map((value, index) => `${x(index).toFixed(1)},${
    y(value).toFixed(1)}`).join(' ');
  const nodes = data.cumulative.map((value, index) => `<circle
    cx="${x(index).toFixed(1)}" cy="${y(value).toFixed(1)}" r="1.8"
    class="cf-node"/>`).join('');
  return `<g class="cf-line">
    <polyline points="${points}" class="cf-case"/>
    <polyline points="${points}" class="cf-cum"/>
    ${nodes}
  </g>`;
}

/**
 * The numbered marks, and the notes they point at.
 *
 * The prose sits in the footer rather than in the plot's whitespace. The sheet this
 * ports from placed captions by computing which band under the bars was clear on each
 * of five fixtures, and listed that geometry as the one place it could still be made to
 * overflow. A numbered mark on the data and the sentence in a footer is the older
 * convention, it cannot collide, and every number in it is read off the payload.
 */
function annotations(data, x, y, datum) {
  const found = [];

  if (data.payback) {
    // Between two year-end nodes, at the fraction of the way the crossing actually
    // happened — not at the year label, which is where the money was booked.
    const crossing = x(data.payback.index - 1)
      + (x(data.payback.index) - x(data.payback.index - 1)) * data.payback.fraction;
    found.push({
      at: [crossing, datum],
      plumb: true,
      text: `<b>Payback \u2014 operation year ${data.payback.year}.</b> The cumulative
        crosses zero ${data.payback.elapsed.toFixed(2)} yr after start-up, inside
        analysis year ${data.payback.year}. Cash is booked at year end, so the crossing
        is at least ${data.payback.year} and at most ${data.payback.year + 1} years
        after start-up; the shaded field is every year the project is under water,
        ${mag(data.deepest.value)} ${escape(data.unit)} at its deepest.`,
    });
  }

  if (data.notch) {
    found.push({
      at: [x(data.notch.index), y(-data.notch.value) + 6],
      text: `<b>${escape(data.notch.name || 'Replacement')} \u2014 year
        ${data.notch.year}.</b> ${mag(data.notch.value)} ${escape(data.unit)} of capital
        in a single year, and the only year it lands in. A mid-life renewal is capital,
        which is why it is drawn in the same ink as the build.`,
    });
  }

  if (data.anomaly) {
    found.push({
      at: [x(data.anomaly.index), y(-data.anomaly.value) + 6],
      fault: true,
      text: `<b>${escape(data.anomaly.line)} \u2014 year ${data.anomaly.year}.</b>
        ${mag(data.anomaly.value)} ${escape(data.unit)} in the terminal year,
        ${num(data.anomaly.ratio, 3)}\u00D7 the largest of the years before it. The
        figure cannot say the price behind this is wrong \u2014 it may be deliberate
        \u2014 but a four-order-of-magnitude outlier does not get to pass as an ordinary
        bar. Detected from the array, so no pathway without one shows this note.`,
    });
  }

  found.push({
    at: [x(data.span - 1), y(data.ending_cumulative)],
    gutter: `${mag(data.ending_cumulative)} ${data.unit}`,
    text: `<b>Ends at ${mag(data.ending_cumulative)} ${escape(data.unit)}.</b> This is a
      <b>nominal, undiscounted</b> running sum, not an NPV. The <i>discounted</i> NPV is
      zero by construction \u2014 the levelized price is <i>defined</i> as the price
      that makes it zero \u2014 so where this line finishes carries no verdict either
      way.`,
  });

  const svg = found.map((note, index) => {
    const [px, py] = note.at;
    const marker = `<g class="cf-mark"><circle cx="${px.toFixed(1)}"
      cy="${py.toFixed(1)}" r="7.5"/><text x="${px.toFixed(1)}"
      y="${(py + 3).toFixed(1)}" text-anchor="middle">${index + 1}</text></g>`;
    const plumb = note.plumb ? `<line x1="${px.toFixed(1)}" y1="${py.toFixed(1)}"
      x2="${px.toFixed(1)}" y2="${PLOT.bottom + 14}" class="cf-plumb"/>` : '';
    const gutter = note.gutter ? `<line x1="${(px + 6).toFixed(1)}"
      y1="${py.toFixed(1)}" x2="${(PLOT.right + 10).toFixed(1)}" y2="${py.toFixed(1)}"
      class="cf-lead"/><text x="${(PLOT.right + 14).toFixed(1)}"
      y="${(py + 3).toFixed(1)}" class="cf-gutter">${escape(note.gutter)}</text>` : '';
    return `${plumb}${gutter}${marker}`;
  }).join('');

  const notes = found.map((note, index) => `<p class="cf-note ${note.fault ? 'fault' : ''}"
    ><span class="cf-note-n">${index + 1}</span>${note.text}</p>`).join('');

  return { svg: `<g class="cf-marks">${svg}</g>`, notes };
}

/** The year axis, and the two brackets that name what the years are. */
function axis(data, x, step) {
  const labels = data.years.map((year, index) => `<text x="${x(index).toFixed(1)}"
    y="${PLOT.bottom + 18}" text-anchor="middle" class="cf-ylab ${
    year % 5 === 0 ? 'on' : ''}">${year}</text>`).join('');

  const build = data.construction_years;
  const bracket = (from, to, label) => {
    const a = x(from) - step / 2;
    const b = x(to) + step / 2;
    return `<path d="M${a.toFixed(1)},${PLOT.bottom + 28} v6 H${b.toFixed(1)} v-6"
        class="cf-bracket"/>
      <text x="${((a + b) / 2).toFixed(1)}" y="${PLOT.bottom + 48}"
        text-anchor="middle" class="cf-brlab">${escape(label)}</text>`;
  };

  return `<g class="cf-axis">${labels}
    <text x="0" y="${PLOT.bottom + 18}" class="cf-vlab">YEAR</text>
    ${build > 0 ? bracket(0, build - 1, build === 1 ? 'build' : `build \u00B7 ${build} yr`) : ''}
    ${bracket(build, data.span - 1,
    `operation \u00B7 ${data.span - build} years`)}
  </g>`;
}

/* ------------------------------------------------------------ the calendar
 *
 * 8,760 hours as 365 columns by 24 rows. One cell per hour, ink is magnitude.
 *
 * This is the only layout that shows both cycles a solar year has at once: the diurnal
 * one down each column, the seasonal one across them. A line chart of the same array is
 * 8,760 points wide and shows neither.
 *
 * Two layers, and which is which is decided by the data rather than by the caller. The
 * series the reader picked is the ink. Where the step's state also carries the array
 * this cell is a *remainder* of, the difference is drawn behind it as a faint ground —
 * so at the Photovoltaic step the plot is a solid lens of everything generated, and at
 * the Electrolyzer step it is a faint lens of the energy the stack took with a firm
 * core of the energy it refused. If the two arrays are equal the ground draws nothing
 * and nothing has to know why.
 */

const CELL = 3;
const ROW = 13;
const GRID_WIDTH = 365 * CELL;
const GRID_HEIGHT = 24 * ROW;
const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
  'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
const MONTH_STARTS = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334];

export function calendar(series, label, scaleMax = null) {
  if (!series || series.length !== 8760) return '';

  // The engine's hourly arrays are UTC, and a solar site is rarely at UTC. Daggett,
  // California is UTC−8, so its daylight hours run 14:00–04:00 UTC and the lens wraps
  // across the top and bottom of the plot — which renders a perfectly correct array as
  // an unreadable inverse of itself.
  //
  // The shift is derived from the data, not from a timezone table: take the circular
  // mean of the hour-of-day weighted by magnitude, and rotate so it lands at noon. It
  // is always right for any site, it needs no metadata the payload does not carry, and
  // both the centroid and the amount are printed so a reader can check the axis.
  const noon = solarNoon(series.values);
  const values = noon.shift ? rotate(series.values, noon.shift) : series.values;

  const dispatch = series.dispatch;
  const whole = dispatch && dispatch.generation
    ? (noon.shift ? rotate(dispatch.generation, noon.shift) : dispatch.generation)
    : null;
  // The ground is the part of each hour that went somewhere other than this cell. When
  // the picked series *is* the whole, every entry is zero and the layer costs nothing.
  const ground = whole ? whole.map((total, index) => Math.max(total - values[index], 0)) : null;
  const groundPeak = ground ? Math.max(...ground) : 0;

  const peak = scaleMax || series.max || 1;
  const frame = whole || values;

  const census = readCells(values, frame);
  const unit = series.unit;

  return `<section class="cal">
    ${factBand(series, census, noon, dispatch, unit)}

    <div class="cal-months">${MONTHS.map((month, index) => `<span
      style="left:${((MONTH_STARTS[index] / 365) * 100).toFixed(3)}%">${month}</span>`)
    .join('')}</div>

    <div class="cal-frame">
      <div class="cal-hours">${[0, 3, 6, 9, 12, 15, 18, 21].map((hour) => `<span
        style="top:${((hour / 24) * 100).toFixed(3)}%">${
        String(hour).padStart(2, '0')}:00</span>`).join('')}</div>

      <div class="cal-plate">
        <svg class="cal-grid" viewBox="0 0 ${GRID_WIDTH} ${GRID_HEIGHT}"
          preserveAspectRatio="none" role="img"
          aria-label="${escape(`${label}: ${census.lit} hours carry a value of 8760, peak ${
            sig(peak)} ${unit}`)}">
          ${cells(ground, groundPeak, 'cal-ground')}
          ${cells(values, peak, 'cal-ink')}
          ${dayHits(values, frame, unit)}
        </svg>
        ${darkBands(census)}
      </div>

      <div class="cal-hod">
        <span class="kicker">hour of day<br>\u03A3 over 365 d</span>
        <svg viewBox="0 0 100 ${GRID_HEIGHT}" preserveAspectRatio="none"
          aria-hidden="true">${hourHistogram(census)}</svg>
        <span class="cal-hod-peak" style="top:${
      ((census.peakHour + 0.5) / 24 * 100).toFixed(3)}%">${
      mag(census.byHour[census.peakHour])}</span>
      </div>
    </div>

    <div class="cal-frame cal-daily">
      <div class="cal-hours"><span class="kicker" style="top:0">daily<br>total</span></div>
      <div class="cal-plate">
        <svg viewBox="0 0 ${GRID_WIDTH} 88" preserveAspectRatio="none"
          aria-hidden="true">${dayHistogram(census)}</svg>
        ${dayCallouts(census, unit)}
      </div>
      <div class="cal-hod"><span class="kicker">365 pts<br>mean ${
    mag(census.total / 365)}</span></div>
    </div>

    ${regimeStrip(dispatch)}

    <div class="cal-read">
      ${lookingAt(series, census, label, noon, whole, dispatch, unit)}
      ${dispatch ? regimeTable(dispatch, unit) : rampKey(series, census, peak, unit)}
      ${extent(series, census, dispatch, unit, peak)}
    </div>
  </section>`;
}

/**
 * Everything the two arrays say about the year, counted once.
 *
 * One pass, because five separate passes over 8,760 entries for the lit count, the
 * day totals, the hour totals, the day lengths and the all-dark rows is five times
 * the work for the same answer.
 */
function readCells(values, frame) {
  const byDay = new Array(365).fill(0);
  const byHour = new Array(24).fill(0);
  const litPerDay = new Array(365).fill(0);
  const rowLit = new Array(24).fill(0);
  let lit = 0;
  let total = 0;
  let frameDark = 0;

  for (let day = 0; day < 365; day += 1) {
    for (let hour = 0; hour < 24; hour += 1) {
      const index = day * 24 + hour;
      const value = values[index];
      if (value) {
        lit += 1;
        total += value;
        byDay[day] += value;
        byHour[hour] += value;
      }
      if (frame[index]) {
        litPerDay[day] += 1;
        rowLit[hour] += 1;
      } else {
        frameDark += 1;
      }
    }
  }

  const best = byDay.indexOf(Math.max(...byDay));
  const worst = byDay.reduce((low, value, day) => (value > 0
    && (byDay[low] === 0 || value < byDay[low]) ? day : low), 0);

  return {
    byDay, byHour, litPerDay, lit, total, frameDark,
    peakHour: byHour.indexOf(Math.max(...byHour)),
    hourPeak: Math.max(...byHour) || 1,
    dayPeak: Math.max(...byDay) || 1,
    dayMean: byDay.reduce((sum, value) => sum + value, 0) / 365,
    best,
    worst,
    // Rows with no value on any of the 365 days. On PV+E ten of the twenty-four are
    // dark every single day of the year, which is 3,650 of the 4,445 dark hours; the
    // remaining 795 are winter mornings and evenings *inside* the band, and saying
    // which is which is the difference between describing the plot and explaining it.
    alwaysDark: rowLit.reduce((rows, count, hour) => (count ? rows : [...rows, hour]), []),
    shortest: Math.min(...litPerDay),
    longest: Math.max(...litPerDay),
    shortestDay: litPerDay.indexOf(Math.min(...litPerDay)),
    longestDay: litPerDay.indexOf(Math.max(...litPerDay)),
  };
}

/**
 * One rect per hour that carries a value.
 *
 * The ink ramp has a floor and a gamma, both measured rather than chosen. Without a
 * floor the cells that *form* the lens — dawn and dusk — sat at 0.08 and the shape had
 * no edge. Gamma above the floor darkens the mid-tones: a linear ramp put the median
 * cell at 0.69, which leaves no range to read magnitude by inside the lit band.
 */
function cells(source, peak, className) {
  if (!source || peak <= 0) return '';
  const floor = className === 'cal-ground' ? 0.06 : 0.18;
  const ceiling = className === 'cal-ground' ? 0.34 : 1;
  const out = [];
  for (let day = 0; day < 365; day += 1) {
    for (let hour = 0; hour < 24; hour += 1) {
      const value = source[day * 24 + hour];
      if (!value) continue;
      const ink = floor + (ceiling - floor) * (Math.min(1, value / peak) ** 1.3);
      out.push(`<rect x="${day * CELL}" y="${hour * ROW}" width="${CELL}" height="${ROW}"
        opacity="${ink.toFixed(3)}"/>`);
    }
  }
  return `<g class="${className}">${out.join('')}</g>`;
}

/** One hit target per day rather than 8,760 per cell — a column carries the readout. */
function dayHits(values, frame, unit) {
  const out = [];
  for (let day = 0; day < 365; day += 1) {
    let total = 0;
    let hours = 0;
    for (let hour = 0; hour < 24; hour += 1) {
      total += values[day * 24 + hour];
      if (frame[day * 24 + hour]) hours += 1;
    }
    out.push(`<rect x="${day * CELL}" y="0" width="${CELL}" height="${GRID_HEIGHT}"
      class="cal-hit" fill="none" pointer-events="all"><title>${escape(
      `${dayLabel(day)} · ${compact(total)} ${unit} over the day · ${hours} h in the band`
    )}</title></rect>`);
  }
  return out.join('');
}

/** The rows that are dark on every day of the year, named where they sit. */
function darkBands(census) {
  const rows = census.alwaysDark;
  if (!rows.length) return '';
  const runs = [];
  rows.forEach((hour) => {
    const last = runs[runs.length - 1];
    if (last && last[1] === hour - 1) last[1] = hour;
    else runs.push([hour, hour]);
  });
  const widest = runs.reduce((best, run) =>
    (run[1] - run[0] > best[1] - best[0] ? run : best), runs[0]);
  const inside = census.frameDark - rows.length * 365;

  return `<div class="cal-dark" style="top:${(widest[0] / 24 * 100).toFixed(3)}%;
    height:${((widest[1] - widest[0] + 1) / 24 * 100).toFixed(3)}%">
    <span>${rows.length} of 24 hours carry nothing on every day of the year
      \u00B7 ${num(rows.length * 365)} h${inside > 0
    ? ` \u00B7 the other ${num(inside)} fall inside the band` : ''}</span>
  </div>`;
}

/** The hour-of-day marginal: 24 bars, the diurnal shape summed over the year. */
function hourHistogram(census) {
  return census.byHour.map((total, hour) => `<rect x="0" y="${hour * ROW + 1}"
    width="${((total / census.hourPeak) * 100).toFixed(2)}" height="${ROW - 2}"
    class="cal-bar ${hour === census.peakHour ? 'on' : ''}"/>`).join('');
}

/** The daily marginal: 365 bars and the mean, which is the seasonal shape. */
function dayHistogram(census) {
  const bars = census.byDay.map((total, day) => `<rect x="${day * CELL}"
    y="${(88 - (total / census.dayPeak) * 84).toFixed(2)}" width="${CELL}"
    height="${((total / census.dayPeak) * 84).toFixed(2)}" class="cal-bar"/>`).join('');
  const mean = (88 - (census.dayMean / census.dayPeak) * 84).toFixed(2);
  return `${bars}<line x1="0" y1="${mean}" x2="${GRID_WIDTH}" y2="${mean}"
    class="cal-mean"/>`;
}

/** The best and worst day, named and dated, positioned over their own columns. */
function dayCallouts(census, unit) {
  const pin = (day, text, side) => `<span class="cal-pin ${side}"
    style="left:${((day + 0.5) / 365 * 100).toFixed(3)}%">${escape(text)}</span>`;
  return `${pin(census.best, `${compact(census.byDay[census.best])} ${unit} \u00B7 ${
    dayLabel(census.best)}`, census.best > 240 ? 'right' : 'left')}
    ${pin(census.worst, `${compact(census.byDay[census.worst])} \u00B7 ${
    dayLabel(census.worst)}`, census.worst > 240 ? 'right' : 'left')}`;
}

/**
 * The header band: the facts the two arrays support and nothing else.
 *
 * On the dark ground because every number in it was computed, and the axis check sits
 * here rather than in a footnote because a rotated time axis is a thing done *to* the
 * data and the reader is owed the amount.
 */
function factBand(series, census, noon, dispatch, unit) {
  const hero = dispatch
    ? { n: num(dispatch.running), u: 'h', k: 'hours energy was taken',
      sub: `of 8 760 \u00B7 idle ${num(dispatch.dark + dispatch.dumped)} h \u00B7 saturated ${
        num(dispatch.saturated)} h` }
    : { n: num(census.lit), u: 'h', k: 'hours carrying a value',
      sub: `of 8 760 \u00B7 ${num(8760 - census.lit)} h at zero \u00B7 day length ${
        census.shortest} to ${census.longest} h` };

  return `<div class="cal-facts">
    <div class="cal-fact">
      <span class="kicker">\u03A3 over the year</span>
      <div class="cal-fact-n">${qty(mag(series.sum), unit)}</div>
      <small>peak hour ${sig(series.max)} ${escape(unit)} \u00B7 ${
    escape(series.table)} \u203A ${escape(series.row)}</small>
    </div>
    <span class="cal-arrow">\u2192</span>
    <div class="cal-fact cal-fact-hero">
      <span class="kicker">${hero.k}</span>
      <div class="cal-fact-n">${qty(hero.n, hero.u)}</div>
      <small>${hero.sub}</small>
    </div>
    ${dispatch ? `<span class="cal-arrow">\u2192</span>
    <div class="cal-fact">
      <span class="kicker">energy this cell still holds</span>
      <div class="cal-fact-n">${qty(mag(dispatch.unused_total), unit)}</div>
      <small>${percent(dispatch.unused_total / dispatch.generated_total)} of the
        ${mag(dispatch.generated_total)} generated \u00B7 ${
    mag(dispatch.served_total)} taken</small>
    </div>` : ''}
    <div class="cal-check">
      <span class="kicker">axis check</span>
      ${leader('diurnal energy centroid', qty(noon.hour.toFixed(2), 'h UTC'))}
      ${leader('rotation applied', qty(`${noon.shift > 0 ? '+' : ''}${
    String(noon.shift).replace('-', '\u2212')}`, 'h'))}
      ${leader('centroid after rotation',
    qty(((noon.hour + noon.shift + 24) % 24).toFixed(2), 'h local'))}
    </div>
  </div>`;
}

/** The year split into operating regimes, at true width, summing to 8,760. */
function regimeStrip(dispatch) {
  if (!dispatch) return '';
  const parts = [
    ['dark', 'dark', dispatch.dark],
    ['turndown', 'below turndown', dispatch.dumped],
    ['direct', 'direct', dispatch.direct],
    ['saturated', 'saturated', dispatch.saturated],
  ].filter(([, , hours]) => hours > 0);

  return `<div class="cal-regime">
    <span class="kicker">the year by regime \u00B7 8 760 h at true width</span>
    <div class="cal-strip">${parts.map(([key, name, hours]) => `<i class="rg-${key}"
      style="width:${((hours / 8760) * 100).toFixed(3)}%"><b>${escape(name)}</b>
      <span>${num(hours)} h</span></i>`).join('')}</div>
  </div>`;
}

/** What the plot is, in the terms of the cell that made it. */
function lookingAt(series, census, label, noon, whole, dispatch, unit) {
  return `<div class="cal-col">
    <span class="kicker">what you are looking at</span>
    <p>One cell per hour of <b>${escape(label)}</b>, 365 columns across the year and 24
      rows down the day, ${num(census.lit)} of them carrying a value. Ink is magnitude
      against ${sig(series.max)} ${escape(unit)}${series.years > 1
    ? `, and this is one of ${series.years} years the cell holds` : ''}.</p>
    <p>The band that widens through summer and narrows through winter is day length:
      ${census.shortest} h on ${dayLabel(census.shortestDay)}, ${census.longest} h on
      ${dayLabel(census.longestDay)}. The best day makes
      ${compact(census.byDay[census.best])} ${escape(unit)} and the worst
      ${compact(census.byDay[census.worst])}.</p>
    ${whole ? `<p>The faint lens behind is the rest of each hour \u2014
      <b>${escape(dispatch.offered_row)}</b> less this cell \u2014 so the firm core is
      the part of the year's generation this cell is still holding, and the ground is
      the part something downstream took.</p>` : ''}
    ${noon.shift ? `<p>The array is stored in UTC and the axis is rotated
      <b>${noon.shift > 0 ? '+' : ''}${String(noon.shift).replace('-', '\u2212')} h</b>,
      derived from the energy centroid rather than from a timezone table, so the row
      labels read local solar time.</p>` : ''}
  </div>`;
}

/** The four regimes, classified by the arrays and never by a parameter. */
function regimeTable(dispatch, unit) {
  const rows = [
    ['dark', 'dark', 'nothing generated', dispatch.dark],
    ['turndown', 'below turndown', 'generated, none taken', dispatch.dumped],
    ['direct', 'direct', 'taken, nothing left over', dispatch.direct],
    ['saturated', 'saturated', 'taken, and this cell still holds some', dispatch.saturated],
  ];
  const turndown = dispatch.turndown;

  return `<div class="cal-col">
    <span class="kicker">4 regimes \u00B7 derived from the two arrays</span>
    <div class="cal-rg">${rows.map(([key, name, blurb, hours]) => `
      <div class="cal-rg-row"><i class="rg-${key}"></i>
        <span class="cal-rg-n">${escape(name)}<em>${escape(blurb)}</em></span>
        <span class="cal-rg-h">${num(hours)} h</span>
        <span class="cal-rg-p">${percent(hours / 8760)}</span>
      </div>`).join('')}
      <div class="cal-rg-row cal-rg-sum"><i></i>
        <span class="cal-rg-n">they sum to the year</span>
        <span class="cal-rg-h">${num(dispatch.dark + dispatch.dumped + dispatch.direct
    + dispatch.saturated)} h</span><span class="cal-rg-p">100 %</span></div>
    </div>
    ${turndown && turndown.floor !== null && turndown.ceiling !== null ? `<p>The arrays
      bracket the boundary the consumer will not run below at
      <b>${percent(turndown.floor, 2)} to ${percent(turndown.ceiling, 2)}</b> of its
      largest served hour${turndown.authored !== null
    ? `, and <code>${escape(turndown.source)}</code> is authored at
       <b>${percent(turndown.authored, 2)}</b>, which falls inside that gap from a
       different code path` : ''}. The classification never consults the parameter: a
      wrong parameter would otherwise produce a picture that is wrong while looking
      right.</p>` : ''}
    <p class="cal-fine">Regimes are counted on the hour, so a fringe hour that ran for
      part of it still counts once. ${escape(unit)} throughout, as the cell declares it.</p>
  </div>`;
}

/** With no regimes to name, the third of the band carries the ink ramp instead. */
function rampKey(series, census, peak, unit) {
  const steps = [0, 0.25, 0.5, 0.75, 1];
  return `<div class="cal-col">
    <span class="kicker">ink is magnitude</span>
    <div class="cal-ramp">${steps.map((step) => `<i
      style="opacity:${(0.18 + 0.82 * (step ** 1.3)).toFixed(3)}"></i>`).join('')}</div>
    <div class="cal-ramp-lab"><span>0</span><span>${sig(peak)} ${escape(unit)}</span></div>
    <p>The ramp has a floor, so an hour that carries anything reads as carrying
      something: dawn and dusk are the cells that form the lens and at a linear ramp
      they sat at eight hundredths against paper.</p>
    ${series.years > 1 ? `<p>This cell holds ${series.years} years and they are not the
      same array \u2014 output falls as the plant degrades \u2014 so the year is named
      above rather than assumed.</p>` : `<p>This cell holds one year, so there is no
      year to choose.</p>`}
    <p class="cal-fine">${num(census.lit)} of 8 760 cells carry a value; the rest are
      paper, not a small number drawn dark.</p>
  </div>`;
}

/** The extent of the array, and where a dispatch census reconciles. */
function extent(series, census, dispatch, unit, peak) {
  return `<div class="cal-col">
    <span class="kicker">summed from the 8 760 h</span>
    ${dispatch ? `
      ${leader(escape(dispatch.offered_row), qty(mag(dispatch.generated_total), unit))}
      ${leader('\u2192 taken by something downstream',
    qty(mag(dispatch.served_total), unit))}
      ${leader('\u2192 still in this cell', qty(mag(dispatch.unused_total), unit))}
      ${leader('largest hour taken', qty(sig(dispatch.served_max), unit))}
      <div class="cal-recon ${Math.abs(dispatch.served_total + dispatch.unused_total
      - dispatch.generated_total) < 1e-6 * Math.abs(dispatch.generated_total)
    ? 'ok' : 'bad'}"><span class="dc-sigma">\u03A3</span>
        <span>taken plus held is what was generated, to
        ${scientific(dispatch.served_total + dispatch.unused_total
      - dispatch.generated_total)} ${escape(unit)} \u2014 the split is a subtraction of
        the engine's own two arrays, not an allocation</span></div>`
    : `
      ${leader('\u03A3 over the year', qty(mag(series.sum), unit))}
      ${leader('largest hour', qty(sig(series.max), unit))}
      ${leader('smallest hour', qty(sig(series.min), unit))}
      ${leader('mean of the hours that carry one',
      qty(sig(census.total / (census.lit || 1)), unit))}
      ${leader('peak hour of day, after rotation',
      qty(`${String(census.peakHour).padStart(2, '0')}:00`, ''))}
      ${leader('scale ceiling for the ink', qty(sig(peak), unit))}
      <p class="cal-fine">${peak === series.max
      ? 'The ceiling is this array\u2019s own largest hour.'
      : 'The ceiling is shared with the sibling cells this step wrote in the same unit,'
        + ' which exist to be compared \u2014 scaling each to its own maximum is the'
        + ' normalisation that defeats that.'}</p>`}
  </div>`;
}

/** `12 Mar` for a day index, for a readout that names a date rather than a number. */
function dayLabel(day) {
  const date = new Date(Date.UTC(2001, 0, 1 + day));
  return `${date.getUTCDate()} ${MONTHS[date.getUTCMonth()]}`;
}

/**
 * Where the day's energy actually sits, and how far that is from noon.
 *
 * The circular mean, weighted by magnitude — an arithmetic mean of the hour index would
 * be pulled by the wrap at midnight and put a 12:15 centroid at 11:00.
 */
function solarNoon(values) {
  let x = 0;
  let y = 0;
  for (let index = 0; index < values.length; index += 1) {
    const value = values[index];
    if (!value) continue;
    const angle = ((index % 24) / 24) * 2 * Math.PI;
    x += value * Math.cos(angle);
    y += value * Math.sin(angle);
  }
  if (x === 0 && y === 0) return { hour: 0, shift: 0 };

  const hour = ((Math.atan2(y, x) / (2 * Math.PI)) * 24 + 24) % 24;
  const shift = Math.round(12 - hour);
  return { hour, shift: ((shift % 24) + 24) % 24 === 0 ? 0 : shift };
}

/** Rotate every day's 24 hours by `shift`, wrapping within the day. */
function rotate(values, shift) {
  const out = new Array(values.length).fill(0);
  for (let index = 0; index < values.length; index += 1) {
    const day = Math.floor(index / 24);
    const hour = (((index % 24) + shift) % 24 + 24) % 24;
    out[day * 24 + hour] = values[index];
  }
  return out;
}
