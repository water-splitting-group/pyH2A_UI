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
 * All three are inline SVG against real engine values. Nothing is smoothed, nothing is
 * interpolated, and where a figure allocates a value into groups it prints its own
 * residual so the reader can see it lost nothing.
 */

import { compact, escape, num, range } from './format.js';

/**
 * A share as a percentage, without the negative zero.
 *
 * `(-2.89e-5 / 4.19 * 100).toFixed(2)` is `-0.00`, which reads as a sign attached to
 * nothing. End-of-life in PV+E is decommissioning almost exactly cancelled by salvage,
 * and the honest rendering of that is `~0`, not `-0.00%`.
 */
function percent(share, places) {
  const value = share * 100;
  const text = value.toFixed(places);
  if (Number(text) === 0) return value === 0 ? '0%' : '~0%';
  return `${text}%`;
}

const FAMILY_INK = {
  capital: 'var(--fam-framework)',
  operating: 'var(--fam-solar)',
  financing: 'var(--fam-cost)',
  endoflife: 'var(--fam-scale)',
  other: 'var(--strontium)',
};

/* ------------------------------------------------------------ decomposition */

export function decomposition(data) {
  if (!data) return '';

  // One shared scale across every bar, anchored on the largest absolute
  // contribution. Per-row scaling would make a 0.003 USD/kg component look the same
  // size as a 1.6 one, which is the single most common way a cost chart lies.
  const widest = Math.max(...data.rows.map((row) => Math.abs(row.value))) || 1;
  const bar = (value) => {
    const width = (Math.abs(value) / widest) * 100;
    const ink = value < 0 ? 'var(--hydrogen)' : 'currentColor';
    return `<span class="bar"><span style="width:${width.toFixed(2)}%;background:${ink}"></span></span>`;
  };

  const families = data.families.map((family) => `
    <tr class="fam" style="color:${FAMILY_INK[family.key] || 'var(--dark-ash)'}">
      <td class="n"><b>${escape(family.label)}</b> <small>${escape(family.blurb)}</small></td>
      <td class="v">${num(family.subtotal, 4)}</td>
      <td class="s">${percent(family.share, 1)}</td>
      <td>${bar(family.subtotal)}</td>
    </tr>
    ${family.rows.map((row) => `
    <tr class="row" style="color:${FAMILY_INK[family.key]}">
      <td class="n">${escape(row.name)}</td>
      <td class="v">${num(row.value, 4)}</td>
      <td class="s">${percent(row.share, 2)}</td>
      <td>${bar(row.value)}</td>
    </tr>`).join('')}`).join('');

  // The self-audit is the point of the panel, not a footnote to it: a decomposition
  // is only worth reading if it provably decomposes the number it claims to.
  const reconciles = Math.abs(data.residual) < 1e-9 && Math.abs(data.headline_residual) < 1e-9;

  return `<section class="fig">
    <div class="fig-head">
      <span class="kicker">where the ${escape(data.unit.split('/')[1] || 'unit')} price comes from</span>
      <span class="fill"></span>
      <span class="kicker">discounted, per ${escape(data.unit.split('/')[1] || 'unit')}
        · ${data.rows.length} components in ${data.families.length} families</span>
    </div>
    <table class="ledger">${families}
      <tr class="total">
        <td class="n">Levelized cost</td>
        <td class="v">${num(data.total, 5)}</td>
        <td class="s"><span class="u">${escape(data.unit)}</span></td>
        <td></td>
      </tr>
    </table>
    <div class="audit ${reconciles ? 'ok' : 'bad'}">
      <span class="mark">Σ</span>
      ${reconciles
        ? `the ${data.rows.length} components sum to ${num(data.total, 5)}, and that is the
           headline — residual ${data.residual.toExponential(1)}`
        : `these parts do <b>not</b> sum to the headline — residual
           ${data.residual.toExponential(3)} ${escape(data.unit)}`}
    </div>
  </section>`;
}

/* ------------------------------------------------------------ annual costs */

export function annual(data) {
  if (!data) return '';

  const drawn = data.lines.filter((line) => !line.zero);
  const zeroed = data.lines.filter((line) => line.zero);
  if (!drawn.length) return '';

  const width = 700;
  const height = 190;
  const left = 52;
  const columns = data.years;
  const step = (width - left) / columns;
  const scale = data.peak || 1;

  const ink = ['var(--fam-framework)', 'var(--fam-solar)', 'var(--fam-cost)',
    'var(--fam-storage)', 'var(--fam-water)'];

  // Stacked, in a fixed line order, so a bar's segments are comparable year to year.
  const bars = [];
  for (let year = 0; year < columns; year += 1) {
    let base = height - 16;
    drawn.forEach((line, index) => {
      const value = line.values[year] || 0;
      if (value <= 0) return;
      // A 1.2 px floor. Twenty of forty-three bars rendered at exactly zero height —
      // invisible, and with no hit area their tooltips were unreachable, which took the
      // readout away from precisely the bars that needed one.
      const barHeight = Math.max(1.2, (value / scale) * (height - 34));
      base -= barHeight;
      bars.push(`<rect x="${(left + year * step + 1).toFixed(1)}" y="${base.toFixed(1)}"
        width="${(step - 2).toFixed(1)}" height="${barHeight.toFixed(1)}"
        fill="${ink[index % ink.length]}"><title>year ${year} · ${escape(line.name)} · ${compact(value)} USD</title></rect>`);
    });
  }

  const ticks = [0, 5, 10, 15, 20].filter((year) => year < columns).map((year) => `
    <text x="${(left + year * step + step / 2).toFixed(1)}" y="${height - 4}"
      font-size="8.5" fill="var(--dark-ash)" text-anchor="middle">${year}</text>`).join('');

  // A full-height transparent target per year, so every year is hoverable whatever its
  // bars measure.
  const hits = Array.from({ length: columns }, (_, year) => {
    const breakdown = drawn
      .filter((line) => line.values[year])
      .map((line) => `${line.name} ${compact(line.values[year])}`)
      .join(' · ') || 'nothing spent';
    return `<rect x="${(left + year * step).toFixed(1)}" y="0" width="${step.toFixed(1)}"
      height="${height - 16}" fill="transparent"><title>year ${year} — ${escape(breakdown)}
      </title></rect>`;
  }).join('');

  return `<section class="fig">
    <div class="fig-head">
      <span class="kicker">when the money is spent</span>
      <span class="fill"></span>
      <span class="kicker">nominal, not discounted · ${compact(data.lifetime)} USD
        over ${columns} years</span>
    </div>
    <svg viewBox="0 0 ${width} ${height}" class="annual" preserveAspectRatio="none"
         role="img" aria-label="${escape(`annual spend over ${columns} years, peak ${compact(data.peak)} USD in year ${data.peak_year}`)}">
      <line x1="${left}" y1="${height - 16}" x2="${width}" y2="${height - 16}"
        stroke="var(--dark-rule)" stroke-width="1"/>
      <text x="0" y="14" font-size="8.5" fill="var(--dark-ash)">${compact(data.peak)} USD</text>
      <text x="0" y="${height - 20}" font-size="8.5" fill="var(--dark-ash)">0</text>
      ${bars.join('')}${hits}${ticks}
    </svg>
    <div class="legend"><span class="kicker">lifetime totals</span>${drawn.map((line, index) => `
      <span><i style="background:${ink[index % ink.length]}"></i>${escape(line.name)}
        <b>${compact(line.total)}</b></span>`).join('')}
      ${zeroed.length ? `<span class="zeroed">zero in this pathway:
        ${zeroed.map((line) => escape(line.name)).join(', ')}</span>` : ''}
    </div>
    ${data.driver && data.driver.share > 0.5 ? `<p class="note">
      Year ${data.peak_year} is the largest single spend at ${compact(data.peak)} USD —
      ${(data.driver.share * 100).toFixed(0)}% of it is
      <b>${escape(data.driver.name)}</b>. The axis is linear and spans four orders of
      magnitude, so every other year is drawn at a floor rather than to scale; hover any
      year for its figures.</p>` : ''}
  </section>`;
}

/* ------------------------------------------------------------ the calendar */

/**
 * 8,760 hours as 365 columns by 24 rows. One cell per hour, ink is magnitude.
 *
 * This is the only layout that shows both cycles a solar year has at once: the
 * diurnal one down each column, the seasonal one across them. A line chart of the
 * same array is 8,760 points wide and shows neither.
 */
export function calendar(series, label, scaleMax = null) {
  if (!series || series.length !== 8760) return '';

  // The engine's hourly arrays are UTC, and a solar site is rarely at UTC. Dagget,
  // California is UTC-8, so its daylight hours run 14:00-04:00 UTC and the lens wraps
  // across the top and bottom of the plot — which renders a perfectly correct array as
  // an unreadable inverse of itself.
  //
  // The shift is derived from the data, not from a timezone table: take the circular
  // mean of the hour-of-day weighted by magnitude, and rotate so it lands at noon. It
  // is always right for any site, it needs no metadata the payload does not carry, and
  // the amount is printed so a reader can see what was done to the axis.
  const shift = solarNoonShift(series.values);
  const shifted = shift ? rotate(series.values, shift) : series.values;

  // Three geometry decisions, all from measuring the first version. The seasonal swing
  // in day length here is five hours; at 5 user units per row that was ±4 CSS px in a
  // 128 px panel, so the one thing the caption promised was invisible. Rows are now
  // twice as tall and the panel three times as tall.
  const cell = 3;
  const rowHeight = 10;
  const width = 365 * cell;
  const height = 24 * rowHeight;
  const peak = scaleMax || series.max || 1;

  // And the ink ramp had no floor: dawn and dusk — the cells that *form* the lens —
  // sat at 0.08 against a near-black ground. A lit hour now reads as lit. Gamma 0.75
  // keeps the top end from saturating, which a linear ramp did at a median of 0.69.
  // Floor 0.22 so a lit hour reads as lit — the cells that *form* the lens sat at 0.08
  // on near-black before. Gamma 1.3 above that floor: a linear ramp put the median cell
  // at 0.69 and gamma 0.75 pushed it to 0.85, leaving no range to read magnitude by
  // inside the lit band. Darkening the mid-tones gives the interior its structure back
  // without dimming the edges that define the shape.
  const ink = (value) => 0.22 + 0.78 * Math.pow(Math.min(1, value / peak), 1.3);

  const marks = [];
  const dayTotals = new Array(365).fill(0);
  let lit = 0;
  for (let day = 0; day < 365; day += 1) {
    for (let hour = 0; hour < 24; hour += 1) {
      const value = shifted[day * 24 + hour];
      if (!value) continue;
      lit += 1;
      dayTotals[day] += value;
      marks.push(`<rect x="${day * cell}" y="${hour * rowHeight}" width="${cell}"
        height="${rowHeight}" fill="currentColor" opacity="${ink(value).toFixed(3)}"/>`);
    }
  }

  // One hit target per day rather than 8,760 per cell: a column carries the readout a
  // reader actually wants (which day, how much) at 1/24th the DOM.
  const hits = dayTotals.map((total, day) => `<rect x="${day * cell}" y="0"
    width="${cell}" height="${height}" fill="transparent"
    ><title>${dayLabel(day)} · ${compact(total)} ${escape(series.unit)} over the day</title></rect>`);

  const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
    'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  const monthStarts = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334];

  return `<section class="fig cal-fig">
    <div class="fig-head">
      <span class="kicker cal-title">${escape(label)}</span>
      <span class="fill"></span>
      <span class="kicker">${num(lit)} lit hours of 8 760${scaleMax
        ? ' · shared scale' : ''}</span>
    </div>
    <div class="cal">
      <div class="cal-hours">${[0, 6, 12, 18].map((hour) =>
        `<span style="top:${((hour / 24) * 100).toFixed(2)}%">${String(hour).padStart(2, '0')}</span>`).join('')}</div>
      <svg viewBox="0 0 ${width} ${height}" class="cal-grid" preserveAspectRatio="none"
           role="img" aria-label="${escape(`${label}: ${lit} lit hours of 8760, peak ${num(peak)} ${series.unit}`)}">
        ${marks.join('')}${hits.join('')}
      </svg>
    </div>
    <div class="cal-months">${months.map((month, index) =>
      `<span style="left:${((monthStarts[index] / 365) * 100).toFixed(2)}%">${month}</span>`).join('')}</div>
    <div class="cal-key">
      <span class="kicker">hour of day, local solar time</span>
      <span class="fill"></span>
      <span class="ramp" aria-hidden="true"></span>
      <span class="kicker">0 to ${compact(peak)} ${escape(series.unit)}</span>
    </div>
    <p class="note">One cell per hour: 365 columns across the year, 24 rows down the
      day. Ink is magnitude. The band that widens through summer and narrows through
      winter is day length.${shift
        ? ` The array is stored in UTC; the axis is rotated
          <b>${shift > 0 ? '+' : ''}${shift} h</b> so the centre of generation sits at
          noon, and the row labels read local solar time.` : ''}</p>
  </section>`;
}

/** `12 Mar` for a day index, for a tooltip that names a date rather than a number. */
function dayLabel(day) {
  const date = new Date(Date.UTC(2001, 0, 1 + day));
  return `${date.getUTCDate()} ${['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
    'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'][date.getUTCMonth()]}`;
}

function solarNoonShift(values) {
  let x = 0;
  let y = 0;
  for (let index = 0; index < values.length; index += 1) {
    const value = values[index];
    if (!value) continue;
    const angle = ((index % 24) / 24) * 2 * Math.PI;
    x += value * Math.cos(angle);
    y += value * Math.sin(angle);
  }
  if (x === 0 && y === 0) return 0;

  const meanHour = ((Math.atan2(y, x) / (2 * Math.PI)) * 24 + 24) % 24;
  const shift = Math.round(12 - meanHour);
  return ((shift % 24) + 24) % 24 === 0 ? 0 : shift;
}

/** Rotate every day's 24 hours by `shift`, wrapping within the day. */
function rotate(values, shift) {
  const out = new Array(values.length);
  for (let index = 0; index < values.length; index += 1) {
    const day = Math.floor(index / 24);
    const hour = (((index % 24) + shift) % 24 + 24) % 24;
    out[day * 24 + hour] = values[index];
  }
  return out;
}
