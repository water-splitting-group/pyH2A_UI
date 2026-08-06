/* Paper Plant Studio — the worksheet.
 *
 * One state object, one render per change, no framework. The app is small enough
 * that a re-render of a panel is cheaper than the machinery for avoiding one, and
 * the resulting code says plainly what is on screen and why.
 *
 * State lives on the server: the open project, its trace, its problems. This file
 * holds only what the *view* needs — which step is open, what is being bound, what
 * the last search returned — so a reload never shows something the file cannot
 * reproduce.
 */

import {
  annual, annualHead, calendar, decomposition, decompositionHead,
} from './figures.js';
import { highlight } from './highlight.js';
import { bounds, clip, cost, escape, ms, num, spark, value } from './format.js';
import { coach, firstVisit, markVisited, refuse, startTour, welcome, wireChooserExtras } from './welcome.js';

const state = {
  project: null,      // summary: name, cost, failed, counts
  rail: [],           // every step, with status and problem count
  step: null,         // open step name
  frame: null,        // that step's whole frame
  graph: null,        // nodes, edges, insertion points, unmet inputs
  lit: null,          // step whose edges are lit
  binding: null,      // {table, row, column, kind} while the picker is armed
  search: null,       // last reference.search result, or null for the full scope
  query: '',
  figures: null,      // what the open step can draw
  series: null,       // one 8,760-hour array, fetched on demand
  teaches: [],        // fields a starter wants edited first
  collapsed: new Set(),
};

const el = (id) => document.getElementById(id);

/* ------------------------------------------------------------------ transport */

/*
 * One session per tab.
 *
 * The server keeps an open project per session id, and until this existed the client
 * never sent one — so every tab shared the single default. Two windows on the same
 * machine, or two people on one server, would silently overwrite each other's project:
 * the second tab to open a pathway won, and the first kept rendering a masthead from
 * one project beside a body from another.
 *
 * `sessionStorage` is exactly the right scope: it survives a reload, and it does not
 * leak between tabs. That is the same reasoning that fixed the equivalent bug in the
 * previous build of this project, where `localStorage` was shared across tabs.
 */
const SESSION = (() => {
  const key = 'paperplant.session';
  let id = sessionStorage.getItem(key);
  if (!id) {
    id = `t${Date.now().toString(36)}${Math.random().toString(36).slice(2, 8)}`;
    sessionStorage.setItem(key, id);
  }
  return id;
})();

/*
 * A copy of the open file, kept in the tab, so a reload cannot lose somebody's work.
 *
 * The native app keeps the project on the server and survives a reload already. The
 * static build has no server: `api.dispatch` runs in the page under Pyodide, so
 * refreshing restarts the interpreter and every edit is gone with no warning. Same app,
 * same screen, and the difference between "your afternoon is safe" and "your afternoon
 * is not" was which URL you happened to be on.
 *
 * `sessionStorage`, matching the session id above: it survives a reload and does not
 * leak between tabs, which is right for an unpublished cost model.
 */
const DRAFT_KEY = 'paperplant.draft';

function keepDraft(markdown, name, origin) {
  try {
    sessionStorage.setItem(DRAFT_KEY, JSON.stringify({ markdown, name, origin }));
  } catch { /* quota or private mode: the draft is a courtesy, never a dependency */ }
}

function takeDraft() {
  try {
    const held = sessionStorage.getItem(DRAFT_KEY);
    return held ? JSON.parse(held) : null;
  } catch { return null; }
}

function dropDraft() {
  try { sessionStorage.removeItem(DRAFT_KEY); } catch { /* nothing to clean up */ }
}

async function call(op, payload = {}) {
  document.body.classList.add('busy');
  try {
    const response = await fetch('/api', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ op, payload: { session: SESSION, ...payload } }),
    });
    const result = await response.json();
    if (result.error) {
      // "no project open" on the very first call is the expected state of a fresh
      // tab, not something to shout about.
      if (!String(result.error).includes('project.open first')) {
        toast(humanize(result.error), true);
      }
      return null;
    }
    return result;
  } catch (error) {
    toast(`the studio server is not answering — ${error.message}`, true);
    return null;
  } finally {
    document.body.classList.remove('busy');
  }
}

/*
 * Turn what the server said into what a person needs to read.
 *
 * `dispatch` formats failures as `ClassName: message`, which is right for a log and
 * wrong for a toast: `KeyError: 'Module tilt'` has no verb, no advice, and a Python
 * class name where the sentence should start. Only the shapes a user can actually
 * provoke are rewritten; anything unrecognised passes through intact rather than being
 * flattened into something vague.
 */
function humanize(message) {
  const text = String(message);
  let match = text.match(/^KeyError: '(.+)'$/);
  if (match) {
    return `there is no “${match[1]}” in this file — add the row before writing to it`;
  }
  match = text.match(/holds no array$/);
  if (match) return 'that value is not a series in this run, so there is nothing to draw';
  match = text.match(/^ModuleNotFoundError: No module named '.*\.(\w+)'$/);
  if (match) return `no plugin named ${match[1]} is installed`;
  return text.replace(/^(ValueError|TypeError|KeyError|RuntimeError): /, '');
}

let toastTimer = null;
function toast(message, bad = false) {
  const node = el('toast');
  node.textContent = message;
  node.classList.toggle('bad', bad);
  node.hidden = false;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => { node.hidden = true; }, bad ? 7000 : 2600);
}

/* ------------------------------------------------------------------ masthead */

function renderMasthead() {
  const project = state.project;
  el('project-name').textContent = project ? project.name : 'no project';
  if (!project) return;

  el('stat-steps').textContent = project.steps;
  el('stat-run').textContent = ms(project.duration_ms);

  const readout = el('stat-cost');
  const label = el('stat-cost-label');
  if (project.cost) {
    label.textContent = 'levelized';
    readout.innerHTML = `${cost(project.cost.value)}<span class="u">${escape(project.cost.unit)}</span>`;
    readout.classList.remove('broken');
  } else {
    // "levelized — did not run" reads as a value called "did not run". The whole
    // readout becomes one statement instead.
    label.textContent = '';
    readout.textContent = 'no cost — the run stopped';
    readout.classList.add('broken');
  }

  const flag = el('flag-button');
  const faults = state.rail.reduce((total, entry) => total + entry.problems, 0);
  const broke = project.failed;
  if (!faults && !broke) {
    flag.hidden = true;
  } else {
    flag.hidden = false;
    flag.classList.toggle('severe', Boolean(broke));
    flag.textContent = broke
      ? `${labelFor(broke)} failed`
      : `${faults} to fix`;
  }
}

function labelFor(name) {
  const entry = state.rail.find((step) => step.name === name);
  return entry ? entry.label : name;
}

/* ------------------------------------------------------------------ rail */

/*
 * The rail is the workflow drawn as a graph, not a list of links.
 *
 * The engine's execution order is the vertical axis and is never re-sorted — it is
 * the one ordering that is true. What a list cannot show, and this does: which steps
 * feed which, by how many values, and where a new step can go. Hovering a step lights
 * its edges; the `+` between any two steps opens the plugin chooser at that position.
 */
function renderRail() {
  const list = el('rail-list');
  const nodes = state.graph ? state.graph.nodes : state.rail;
  el('rail-sub').textContent = `execution order · ${nodes.length} steps`;
  list.innerHTML = '';

  const points = state.graph ? state.graph.insertion_points : [];
  nodes.forEach((entry, index) => {
    if (points[index]) list.append(insertionPoint(points[index]));
    list.append(stepNode(entry, index));
  });
  if (points.length) list.append(insertionPoint(points[points.length - 1]));

  drawEdges(nodes);
  renderLegend(nodes);
  renderPanelBar();
}

function stepNode(entry, index) {
  const item = document.createElement('li');
  item.className = `step ${entry.status === 'ok' ? 'ran' : entry.status}`;
  item.style.setProperty('--fam', `var(--fam-${entry.family})`);
  item.setAttribute('aria-current', String(entry.name === state.step));
  item.setAttribute('role', 'button');
  item.setAttribute('aria-label',
    `step ${entry.position}, ${entry.label}, ${entry.status}`
    + (entry.problems ? `, ${entry.problems} needing attention` : ''));
  item.dataset.name = entry.name;
  item.dataset.index = index;
  // One tab stop for the whole rail; arrows walk it. Interleaved insertion points and
  // steps made 35 stops, and reaching the last step took 33 presses of Tab.
  item.tabIndex = entry.name === state.step ? 0 : -1;
  // A step that can draw something says so. Five of PV + Electrolysis's seventeen steps
  // can, and until this badge existed you found them by opening steps at random.
  const draws = (state.catalogue || []).filter((figure) => figure.step === entry.name);
  item.innerHTML = `
    <span class="pos">${entry.position}</span>
    <span class="dot"></span>
    <span class="name">${escape(entry.label)}</span>
    ${draws.length ? `<button class="figmark" data-figure-step="${escape(entry.name)}"
        title="${escape(draws.map((figure) => figure.title).join(' · '))}"
        aria-label="${escape(`open ${plural(draws.length, 'figure')} for ${entry.label}`)}"
      >${draws.length > 1 ? draws.length : ''}<svg viewBox="0 0 12 12" aria-hidden="true"
        ><path d="M1 9.5 L4 5 L6.5 7 L11 1.5" fill="none" stroke="currentColor"
          stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg></button>` : ''}
    ${entry.problems
      ? `<span class="badge ${entry.status === 'error' ? 'severe' : ''}">${entry.problems}</span>`
      : entry.status === 'error' ? '<span class="badge severe">!</span>' : ''}`;
  const figmark = item.querySelector('.figmark');
  if (figmark) {
    figmark.onclick = (event) => { event.stopPropagation(); openFigures(entry.name); };
  }
  item.onclick = () => { openStep(entry.name); closePanels(); };
  item.onkeydown = (event) => {
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault();
      openStep(entry.name);
    }
    if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
      event.preventDefault();
      const steps = [...el('rail-list').querySelectorAll('.step')];
      const next = steps[index + (event.key === 'ArrowDown' ? 1 : -1)];
      // `openStep` rebuilds the rail, destroying the element just focused, so focus is
      // reclaimed on the node that replaces it. Without this the first arrow works and
      // every one after it goes nowhere.
      if (next) {
        const name = next.dataset.name;
        openStep(name).then(() => {
          const replacement = el('rail-list').querySelector(`[data-name="${name}"]`);
          if (replacement) replacement.focus();
        });
      }
    }
  };
  item.onmouseenter = () => light(entry.name);
  item.onmouseleave = () => light(null);
  return item;
}

function insertionPoint(point) {
  const item = document.createElement('li');
  item.className = 'insert';
  item.innerHTML = `<button tabindex="-1"
      aria-label="add a step at position ${point.position}"
      title="add a step at ${point.position}">+</button>
    <span class="at">${point.position}</span>`;
  item.querySelector('button').onclick = (event) => {
    event.stopPropagation();
    showPlugins(point.position);
  };
  return item;
}

/*
 * Edges are drawn in a gutter to the left of the spine, one lane per edge, routed as
 * an orthogonal bracket: out of the producer, down its lane, into the consumer. Lanes
 * are assigned by interval-packing so two edges share a lane only when they do not
 * overlap vertically — which keeps a seventeen-step workflow inside 60 px.
 */
function drawEdges(nodes) {
  const gutter = el('rail-edges');
  const list = el('rail-list');
  if (!state.graph || !state.graph.edges.length) { gutter.innerHTML = ''; return; }

  const index = new Map(nodes.map((node, position) => [node.name, position]));
  const items = [...list.querySelectorAll('.step')];
  const top = list.getBoundingClientRect().top;
  const centre = new Map(items.map((item) => {
    const box = item.getBoundingClientRect();
    return [item.dataset.name, box.top - top + box.height / 2];
  }));

  const lanes = [];
  const placed = state.graph.edges.map((edge) => {
    const a = centre.get(edge.from);
    const b = centre.get(edge.to);
    if (a === undefined || b === undefined) return null;
    const lane = lanes.findIndex((end) => end <= a - 6);
    const slot = lane === -1 ? lanes.length : lane;
    lanes[slot] = b;
    return { edge, a, b, slot };
  }).filter(Boolean);

  const width = Math.min(86, 10 + lanes.length * 5);
  const height = list.scrollHeight;
  const x = (slot) => width - 5 - (slot % Math.max(1, Math.floor((width - 10) / 5))) * 5;

  gutter.style.width = `${width}px`;
  gutter.innerHTML = `<svg width="${width}" height="${height}" viewBox="0 0 ${width} ${height}">${
    placed.map(({ edge, a, b, slot }) => {
      const lit = state.lit && (edge.from === state.lit || edge.to === state.lit);
      const cls = state.lit ? (lit ? 'lit' : 'dim') : '';
      return `<path class="edge ${cls}" d="M ${width} ${a} H ${x(slot)} V ${b} H ${width}"
        fill="none" stroke="var(--fam-${famOfStep(edge.from)})"
        stroke-width="${lit ? 1.6 : 1}"><title>${escape(edge.cells.join('\n'))}</title></path>`;
    }).join('')
  }</svg>`;
}

function famOfStep(name) {
  const node = (state.graph ? state.graph.nodes : state.rail).find((n) => n.name === name);
  return node ? node.family : 'scale';
}

/*
 * Light a step's edges, and name the values crossing them.
 *
 * The client's own words about this app: *"the nodes are completely trivial. The
 * interesting thing is the edges, which are the individual pieces of information that
 * are passed between them."* The rail drew the edges from the first build and then said
 * only how many values each carried — `12 values in from 4 steps` — which is a fact
 * about the graph, not about the plant. The names were in `edge.cells` all along.
 *
 * Everything is listed, never truncated: the busiest step in any shipped pathway takes
 * twelve values (Discounted Cash Flow on PV + Electrolysis) and the widest single edge
 * carries five. A "+3 more" on a list that short would be hiding nothing at some cost.
 */
function light(name) {
  state.lit = name;
  drawEdges(state.graph ? state.graph.nodes : state.rail);

  const card = el('rail-card');
  if (!name || !state.graph) { card.hidden = true; return; }

  const inbound = state.graph.edges.filter((edge) => edge.to === name);
  const outbound = state.graph.edges.filter((edge) => edge.from === name);
  if (!inbound.length && !outbound.length) { card.hidden = true; return; }

  const node = state.graph.nodes.find((entry) => entry.name === name);
  const side = (edges, peerOf, heading, preposition) => {
    if (!edges.length) return '';
    const total = edges.reduce((sum, edge) => sum + edge.count, 0);
    return `
      <div class="flow-side">
        <div class="flow-head">${plural(total, 'value')} ${heading}</div>
        ${edges.map((edge) => {
          const peer = state.graph.nodes.find((entry) => entry.name === peerOf(edge));
          return `<div class="flow-peer" style="--fam: var(--fam-${peer ? peer.family : 'framework'})">
            <div class="flow-who">${preposition} <b>${escape(peer ? peer.label : peerOf(edge))}</b>
              <span class="flow-pos">${peer ? peer.position : ''}</span></div>
            ${edge.cells.map((cell) => `<div class="flow-cell">${escape(cell)}</div>`).join('')}
          </div>`;
        }).join('')}
      </div>`;
  };

  card.innerHTML = `
    <div class="flow-title">${escape(node ? node.label : name)}</div>
    ${side(inbound, (edge) => edge.from, 'in', 'from')}
    ${side(outbound, (edge) => edge.to, 'out', 'to')}`;
  card.hidden = false;

  // Anchored to the step, clamped to the viewport. A card that runs off the bottom on
  // step 900 is worse than one that sits a little high.
  const anchor = el('rail-list')
    .querySelector(`[data-name="${String(name).replace(/["\\]/g, '\\$&')}"]`);
  if (!anchor) return;
  const box = anchor.getBoundingClientRect();
  const height = card.offsetHeight;
  card.style.top = `${Math.max(52, Math.min(box.top - 4, window.innerHeight - height - 12))}px`;
}

/*
 * The tally under the rail, as a partition: every step is in exactly one bucket, and
 * they add up to the number of steps.
 *
 * They did not before. The buckets were `ok`, `has problems` and `skipped`, so a step
 * with status `error` and no field-level problems belonged to none of them and simply
 * disappeared — a ten-step run stopped at step five read "8 ran clean · 1 never
 * reached". Meanwhile `has problems` overlapped `ok`, so other workflows counted the
 * same step twice and the total came out above the step count.
 */
function renderLegend(nodes) {
  const stopped = nodes.filter((entry) => entry.status === 'error');
  const skipped = nodes.filter((entry) => entry.status === 'skipped');
  const flagged = nodes.filter((entry) => entry.status === 'ok' && entry.problems);
  const clean = nodes.filter((entry) => entry.status === 'ok' && !entry.problems);
  const unmet = state.graph ? state.graph.unmet.length : 0;

  el('rail-legend').innerHTML = [
    clean.length ? `<b>${clean.length}</b> ran clean` : '',
    flagged.length ? `<b>${flagged.length}</b> ran, needing attention` : '',
    stopped.length ? `<b>${stopped.length}</b> stopped the run` : '',
    skipped.length ? `<b>${skipped.length}</b> never reached` : '',
    unmet ? `<b>${unmet}</b> ${unmet === 1 ? 'input' : 'inputs'} still unsupplied` : '',
  ].filter(Boolean).join('<br>');
}

/* ------------------------------------------------------------------ needs */

function renderNeeds() {
  const host = el('needs');
  if (!state.frame) {
    host.innerHTML = '<p class="empty">Choose a step on the left.</p>';
    return;
  }

  const { step, needs, produces } = state.frame;
  const fields = needs.flatMap((table) => table.fields);
  const editable = fields.filter((field) => field.state !== 'computed');
  const faults = fields.filter((field) => field.problems.length).length;

  host.innerHTML = `
    <div class="step-head" style="--fam: var(--fam-${step.family})">
      <div class="numeral">${step.position}</div>
      <div class="titles">
        <h2>${escape(step.label)}</h2>
        <div class="plugin">${escape(step.name)} · <span class="fam-chip">${step.family}</span></div>
      </div>
      <div class="counts">
        ${plural(needs.length, 'table')} · ${plural(fields.length, 'row')}<br>
        ${stepStanding(step, faults)}
        ${step.in_file
          ? `<button class="drop" data-remove="${escape(step.name)}"
              title="take this step out of the workflow; its tables stay in the file"
              >remove step</button>`
          : `<span class="drop off" title="this step comes from the merged defaults, not
              from your file, so there is no Workflow row here to delete"
              >from defaults</span>`}
      </div>
    </div>
    ${step.summary ? `<p class="summary">${escape(step.summary)}</p>` : ''}
    ${failureBand(step)}
    ${unmetBand(step.name)}
    ${effectBand(step)}
    <div class="section-rule">
      <span class="kicker">what this step needs</span>
      <span class="fill"></span>
      <span class="count">${editable.length} to enter · ${fields.length - editable.length} computed</span>
    </div>
    ${needs.length ? needs.map(renderTable).join('') : emptyNeeds()}
    ${renderMade(produces, step)}
    ${renderFigures()}`;

  wireNeeds();
  renderPanelBar();
  coach(state.teaches);
}

/*
 * The engine's own message, cleaned of its transport.
 *
 * pyH2A raises with a `[Plugin: X]` prefix — which duplicates the step title directly
 * above it — and Python's `str(KeyError)` keeps the repr quotes, so the banner read
 * `KeyError: "[Plugin: …] Table 'Solar Concentrator' is required but not found in
 * dcf.inp"`. The words are the engine's and stay verbatim; the wrapping is ours to drop.
 */
function engineText(message) {
  return String(message ?? '')
    .replace(/^"(.*)"$/s, '$1')
    .replace(/^\[Plugin: \w+\]\s*/, '')
    .trim();
}

/*
 * What to tell a reader about a failure, given what the rail actually shows.
 *
 * The static version said "check the flagged fields in the rail *before* this one" — and
 * pointed the wrong way whenever the flagged step came after, which is the common case:
 * paths resolve lazily, so the plugin that *touches* a broken reference fails before the
 * step that owns the cell has run. It also appeared on steps that own their own fault,
 * with the cause named in the panel directly below.
 */
function blameHint(step) {
  const flagged = state.rail.filter((entry) => entry.problems && entry.name !== step.name);
  if (!flagged.length) {
    return 'Nothing else in this workflow is flagged, so the cause is on this step.';
  }
  const names = flagged.map((entry) => `${entry.position} ${entry.label}`).join(', ');
  return `The engine blames whichever step was running, which is not always the one that
    owns the bad value — paths resolve lazily. ${flagged.length === 1 ? 'This step is'
    : 'These steps are'} flagged: ${names}.`;
}

function stepStanding(step, faults) {
  // Never say "ran in 0.25 ms" about a step that raised. The timing is real — that is
  // how long it ran before failing — but presenting it as a clean run beside a red
  // error band is the app contradicting itself on one line.
  if (step.status === 'error') return `<span class="bad">failed after ${ms(step.duration_ms)}</span>`;
  if (step.status === 'skipped') return '<span class="bad">never reached</span>';
  if (faults) return `<span class="wait">${faults} need${faults === 1 ? 's' : ''} attention</span>`;
  return `ran in ${ms(step.duration_ms)}`;
}

/*
 * What this step needs that nothing in the project supplies — and, for each gap,
 * which installed plugin declares that row as an output.
 *
 * "Missing" on its own sends a reader hunting. Naming the plugin that writes the row
 * turns the same fact into a next action, and distinguishing "no plugin makes this"
 * tells them the remaining gaps are theirs to type.
 */
/*
 * What this step is worth, measured by taking it out and running again.
 *
 * The counterpart to the unmet panel. That one answers "what does this step need that
 * nobody supplies"; this answers "does anything downstream read what it writes". Both
 * questions are about edges, and a worksheet that only ever shows nodes cannot answer
 * either. The numbers here are measured, never inferred — see `op_step_effect`.
 */
function effectBand(step) {
  const effect = state.effect;
  if (!effect || state.effectFor !== step.name || !effect.measurable) return '';
  if (effect.required) {
    return `<div class="effect required">The pathway does not reach a cost without this
      step${effect.failed ? ` — ${escape(labelFor(effect.failed))} stops` : ''}.</div>`;
  }
  if (!effect.inert) {
    // Direction, not magnitude alone. "Worth 0.0016 USD/kg" read as a saving on all
    // three live steps of PV + Electrolysis, every one of which *raises* the cost —
    // Battery and Stored Power Electrolysis buy reliability and are supposed to.
    const delta = Math.abs(effect.with - effect.without);
    const raises = effect.with > effect.without;
    return `<div class="effect ${raises ? 'costs' : 'saves'}">
      ${raises ? 'Adds' : 'Saves'} <b>${cost(delta)} ${escape(effect.unit)}</b> —
      without this step the pathway costs ${cost(effect.without)} ${escape(effect.unit)},
      with it ${cost(effect.with)}.</div>`;
  }
  const where = effect.would_matter_at;
  return `<div class="effect inert">
    <b>This step changes nothing where it is.</b> Remove it and the cost stays
    ${cost(effect.with)} ${escape(effect.unit)}: it writes its values after everything
    that would read them has already run.
    ${where ? `Run it before ${escape(labelFor(where.before))} and the same numbers give
      ${cost(where.cost)} ${escape(effect.unit)}.
      <button class="fix" data-move-to="${where.position}">move to ${where.position}</button>`
    : 'No other position in this workflow changes the answer either.'}
  </div>`;
}

function unmetBand(stepName) {
  if (!state.graph) return '';
  const gaps = state.graph.unmet.filter((entry) => entry.step === stepName);
  if (!gaps.length) return '';

  // Three different situations were filed under one heading that fitted only the first.
  const yours = gaps.filter((gap) => !gap.suggestions.length);
  const movable = gaps.filter((gap) => gap.suggestions.length && gap.runs_later.length);
  const addable = gaps.filter((gap) => gap.suggestions.length && !gap.runs_later.length);

  // Each row names a cell that exists on this very screen, two hundred pixels below.
  // It used to be inert text, so the block that reads like the call to action was the
  // one thing you could not act on, and the panel said everything twice. The rows a
  // reader has to fill themselves now put the cursor in the field.
  const section = (rows, heading, body, jump = false) => rows.length ? `
    <div class="what">${heading(rows.length)}</div>
    ${rows.map((gap) => `<div class="gap${jump ? ' jump' : ''}"${jump
        ? ` role="button" tabindex="0" data-goto-table="${escape(gap.table)}"`
          + ` data-goto-row="${escape(gap.row)}"`
          + ` aria-label="${escape(`go to ${gap.table} › ${gap.row}`)}"`
        : ''}>
      <span class="cell">${escape(gap.table)} › <b>${escape(gap.row)}</b></span>
      ${body(gap)}
      ${gap.description ? `<div class="d">${escape(gap.description)}</div>` : ''}
    </div>`).join('')}` : '';

  return `<div class="unmet">
    ${section(yours, (n) => `${plural(n, 'value')} only you can supply`,
      () => '<span class="by own">no installed plugin writes this — click to fill it in</span>',
      true)}
    ${section(movable,
      (n) => `${plural(n, 'value')} that ${n === 1 ? 'arrives' : 'arrive'} too late`,
      (gap) => `<span class="by">${escape(gap.runs_later.join(', '))} ${
        gap.runs_later.length === 1 ? 'writes' : 'write'} this, but ${
        gap.runs_later.length === 1 ? 'runs' : 'run'} after ${
        escape(labelFor(gap.step))} — move one of them</span>`)}
    ${section(addable, (n) => `${plural(n, 'value')} a plugin could supply`,
      (gap) => `<span class="by">written by ${gap.suggestions.map((entry) =>
        `<button class="fix" data-add-plugin="${escape(entry.name)}">${escape(entry.label)}</button>`
      ).join(' ')}</span>`)}
  </div>`;
}

function failureBand(step) {
  if (step.status === 'error') {
    return `<div class="failure">
      <div class="what">this step raised ${escape(step.error_type || 'an error')}</div>
      <div class="msg">${escape(engineText(step.error))}</div>
      <div class="hint">${blameHint(step)}</div>
    </div>`;
  }
  if (step.status === 'skipped') {
    return `<div class="failure">
      <div class="what">never reached</div>
      <div class="msg">an earlier step failed, so this one did not run</div>
      <div class="hint">Its fields are shown as written, but nothing here has been checked
        against values that were never computed.</div>
    </div>`;
  }
  return '';
}

function emptyNeeds() {
  return `<p class="empty">This step declares no inputs of its own — it works entirely
    from what earlier steps produced. Everything it can reach is listed on the right.</p>`;
}

function renderTable(table) {
  const open = !state.collapsed.has(table.table);
  const waiting = table.problems > 0;
  return `<div class="tbl ${waiting ? 'waiting' : ''}" data-table="${escape(table.table)}">
    <div class="tbl-head" data-toggle="${escape(table.table)}">
      <span class="caret">${open ? '▾' : '▸'}</span>
      <h3>${escape(table.table)}</h3>
      <span class="fill"></span>
      <span class="note">${sectionCount(table)}</span>
    </div>
    ${open ? table.fields.map((field, index) => renderField(field, index)).join('') : ''}
  </div>`;
}

/*
 * What a section header says about itself.
 *
 * `0 to enter` above four informative rows announced a full section as empty: the
 * counter only knew about editable fields, and the two sections on step 203 holding
 * computed inputs both read `0 to enter`. It now names whatever the section actually
 * has, and counts in English rather than `1 inputs`.
 */
function sectionCount(table) {
  if (table.problems) return `${table.problems} to fix`;
  const computed = table.fields.length - table.to_enter;
  const parts = [];
  if (table.to_enter) parts.push(`${table.to_enter} to enter`);
  if (computed) parts.push(`${computed} computed`);
  return parts.join(' · ') || 'nothing to enter';
}

function plural(count, word) {
  return `${count} ${word}${count === 1 ? '' : 's'}`;
}

function renderField(field, index) {
  const declared = field.declared;
  // `missing` covers two different situations and only one is a problem: a required
  // field nobody supplied, and an optional one nobody needed to. Painting both sodium
  // and captioning both "required" contradicted the field's own meta line, which said
  // `optional` two rows below.
  const waiting = field.state === 'missing' && !field.declared.optional;
  const bad = field.problems.length > 0;
  // A step that never ran still has its authored fields, and one of them is usually the
  // value that stopped the run. Rendering the whole step read-only left no way to fix
  // the field you had just broken: the only escape was to open another step, or reload.
  // A value the *user* wrote stays editable whatever happened downstream; only a value
  // an earlier step was supposed to compute becomes evidence.
  const authored = field.text !== null && field.text !== undefined && field.text !== '';
  const computed = field.state === 'computed'
    || (field.state === 'unevaluated' && !authored);
  const equation = Boolean(field.path.text && field.path.text !== 'None');

  const meta = [
    declared.dimension ? `<span><b>${escape(declared.dimension)}</b></span>` : '',
    bounds(field.bounds_shown) ? `<span>range <b>${bounds(field.bounds_shown)}</b></span>` : '',
    declared.optional ? '<span>optional</span>' : '',
    field.origin && field.origin.includes('~')
      ? `<span>from <b>${escape(field.origin.split('~').pop())}</b></span>` : '',
    field.column !== 'Value' ? `<span>column <b>${escape(field.column)}</b></span>` : '',
  ].filter(Boolean).join('');

  return `<div class="field ${waiting ? 'waiting' : ''} ${bad ? 'bad' : ''}
      ${computed ? 'computed' : ''} ${equation ? 'eqn' : ''}
      ${field.state === 'missing' ? 'absent' : ''}"
      data-table="${escape(field.table)}"
      data-row="${escape(field.row)}"
      data-col="${escape(field.column)}">
    <span class="idx">${String(index + 1).padStart(2, '0')}</span>
    <span class="label">
      <span class="n" title="${escape(`${field.table} › ${field.row}`)}">${escape(field.label)}</span>
      <span class="fill"></span>
      ${!computed && !equation && field.path.column
        ? '<button class="add-path" data-add-path>+ bind a path</button>' : ''}
    </span>
    ${equation ? renderEquation(field) : renderPlain(field, computed, waiting)}
    ${declared.description ? `<div class="desc">${escape(declared.description)}</div>` : ''}
    ${meta ? `<div class="meta">${meta}</div>` : ''}
    ${field.problems.map(renderProblem).join('')}
  </div>`;
}

function renderPlain(field, computed, waiting) {
  if (computed) {
    // A step that never ran has no value to show and no business offering an input
    // box: the value was not missing, it was never computed. An earlier version drew
    // an empty field captioned `required` for every upstream value in a failed run.
    return field.state === 'unevaluated'
      ? '<span class="value-cell pending">not computed — the run stopped earlier</span>'
      : `<span class="value-cell">${value(field.live)}</span>`;
  }
  const numeric = (field.declared.types || []).every((entry) =>
    entry === 'int' || entry === 'float') && !field.is_reference;
  return `<input class="cell ${field.is_reference ? 'ref' : ''}" data-cell
      aria-label="${escape(`${field.table} ${field.label} value`)}"
      ${numeric ? 'inputmode="decimal"' : ''}
      value="${escape(field.text ?? '')}"
      placeholder="${waiting ? 'required' : ''}">
    ${field.unit.column
      ? `<input class="unit" data-unit aria-label="${escape(`${field.label} unit`)}"
           placeholder="-" title="${escape(field.unit.text ?? '')}"
           value="${escape(field.unit.text ?? '')}">`
      : `<span class="idx">${escape(field.unit.text ?? '')}</span>`}`;
}

/*
 * A row with a `Path` is a product, and it is drawn as the equation it is — on ONE
 * line, operands adjacent to their operator:
 *
 *     [784] per kW   ×   {Electrolyzer > Nominal power > Value, kW} 5,500 kW   =   4,312,000 USD
 *
 * Two things this fixes. The operands used to sit four lines apart with two lines of
 * prose between them, so `×` had no visible left operand. And the unit chip beside the
 * multiplier showed the unit of the *result*: `784 [USD]` for a number that is USD per
 * kW, and `1.5 [kW]` for a dimensionless scale factor. An engineer checks units first,
 * and every unit-bearing number in the app's most load-bearing table was mislabelled by
 * the plant's own scale factor.
 *
 * The multiplier's own unit is stated as `per <requested unit>` — derived from the
 * reference, not guessed — or omitted when the row's unit and the reference's unit
 * match, which is the case where the multiplier really is dimensionless.
 */
function renderEquation(field) {
  const path = field.path;
  const per = path.requested_unit && path.requested_unit !== '-'
    && field.unit.text && field.unit.text !== path.requested_unit
    ? `<span class="per">per ${escape(path.requested_unit)}</span>` : '';

  const resolved = path.as_requested !== undefined && path.as_requested !== null
    ? `<span class="q">${num(path.as_requested)}</span>` +
      `<span class="u">${escape(path.requested_unit)}</span>`
    : '<span class="u">unresolved</span>';

  const product = field.after
    ? value(field.after)
    : '<span class="u">not computed</span>';

  return `<div class="eq">
    <input class="cell mult" data-cell aria-label="${escape(`${field.label} multiplier`)}"
      value="${escape(field.text ?? '')}">${per}
    <span class="op">×</span>
    <span class="operand">
      <input data-path spellcheck="false" aria-label="${escape(`${field.label} reference`)}"
        value="${escape(path.text)}">
      <span class="resolved">${resolved}</span>
    </span>
    <span class="op">=</span>
    <span class="product">${product}</span>
  </div>`;
}

function renderProblem(problem) {
  const warn = problem.kind.endsWith('early') ? 'warn' : '';
  // Two suggestions pointing at different columns of one row rendered as two identical
  // buttons. The column is what distinguishes them.
  const shown = new Map((problem.near || []).map((path) => [path.join('\u0000'), path]));
  const ambiguous = new Set();
  const seen = new Set();
  for (const path of shown.values()) {
    if (seen.has(path[1])) ambiguous.add(path[1]);
    seen.add(path[1]);
  }
  const fixes = [...shown.values()].map((path) => `
    <button class="fix" data-fix="${escape(JSON.stringify(path))}"
      title="${escape(path.join(' › '))}">${escape(path[1])}${
      ambiguous.has(path[1]) ? ` <i>${escape(path[2])}</i>` : ''}</button>`).join('');
  return `<div class="problem ${warn}">
    <span class="kind">${escape(problem.kind.replace(/-/g, ' '))}</span>
    <span>${escape(problem.message)}</span>
    ${fixes ? `<span class="fixes">did you mean ${fixes}</span>` : ''}
  </div>`;
}

/*
 * The figures for the open step, below what it made.
 *
 * Below rather than above: the table of values is the primary evidence and the chart
 * is an argument about it. A reader who wants the number should not have to scroll
 * past a picture to reach it.
 */
/*
 * In the step panel, a figure is a door rather than a drawing.
 *
 * These used to render inline in a column about 560 px wide. The dispatch calendar is
 * 365 columns of one-hour cells; the cash flow is 21 stacked years under a cumulative
 * line. Both were being asked to be instruments in the space of a sidebar illustration,
 * and both now open full width instead.
 */
function renderFigures() {
  const offered = (state.catalogue || []).filter((figure) => figure.step === state.step);
  if (!offered.length) return '';

  return `<div class="fig-doors">
    ${offered.map((figure) => `
      <button class="fig-door" data-open-figure="${figure.kind}">
        <span class="kicker">${escape(figure.kicker)}</span>
        <span class="fig-door-title">${escape(figure.title)}</span>
        <span class="fig-door-blurb">${escape(figure.blurb)}</span>
      </button>`).join('')}
  </div>`;
}

function renderHourly(candidates) {
  const chosen = state.series;
  const options = candidates.map((entry, index) => `
    <button class="cal-pick ${chosen && chosen.row === entry.row ? 'on' : ''}"
      data-series="${index}">${escape(entry.row)}${entry.per_year
        ? `<span class="yrs">${entry.years}y</span>` : ''}</button>`).join('');

  // A cell holding twenty years is twenty different arrays, and PV output falls 9%
  // across them as the panels degrade. Drawing one of them captioned "the year" tells
  // the reader something false about a series they cannot inspect otherwise.
  const years = chosen && chosen.years > 1 ? `
    <div class="cal-years">
      <span class="kicker">year</span>
      ${Array.from({ length: chosen.years }, (_, year) => `
        <button class="cal-year ${year === chosen.year ? 'on' : ''}"
          data-year="${year}">${year}</button>`).join('')}
    </div>` : '';

  const label = chosen
    ? `${chosen.table} › ${chosen.row}${chosen.years > 1 ? ` · year ${chosen.year}` : ''}`
    : '';

  // Siblings share one scale — but only siblings measured in the same unit. Step 201's
  // three tracking modes exist to be compared and scaling each to its own maximum
  // (909, 953, 931 Wh/m2) is exactly the normalisation that defeats that. Step 202
  // offers an irradiance in kWh/m2 beside two energies in J, and putting those on one
  // axis ceilings the irradiance at 8.1e13 times its own peak.
  const peers = chosen
    ? candidates.filter((entry) => entry.unit === chosen.unit && entry.max)
    : [];
  const shared = peers.length > 1 ? Math.max(...peers.map((entry) => entry.max)) : null;

  return `<section class="fig fig-hourly">
    <div class="fig-head">
      <span class="kicker">hour by hour</span>
      <span class="fill"></span>
    </div>
    <div class="cal-picks">${options}</div>
    ${years}
    ${chosen ? calendar(chosen, label, shared)
      : '<p class="note">Pick a series above to draw it.</p>'}
  </section>`;
}

/*
 * A column key as a person would read it.
 *
 * The engine names the columns of a multi-quantity row `Duration_Value`, `Cost_Path`,
 * `Price_Conversion_Factor_Unit`. Rendered flush against the row name with no
 * separator they read as one word — the copyable text was literally
 * `Process WaterCost_Path` — and the underscores are engine syntax, not English.
 */
function columnLabel(column) {
  return column.replace(/_/g, ' ').replace(/\bValue\b/, '').trim() || column;
}

function renderMade(produces, step) {
  if (!produces.tables.length) {
    return step.status === 'ok'
      ? '<p class="empty">This step wrote nothing into the model.</p>' : '';
  }

  // Two kinds of write, kept apart. A step's first act is usually to convert its own
  // input cells into engine quantities — those changed, but the user wrote them, and
  // listing them as output buries the values the step genuinely computed.
  const rows = produces.tables.flatMap((table) => [
    `<tr class="tablerow"><td colspan="3">${escape(table.table)}</td></tr>`,
    ...table.rows.map((row) => `
    <tr class="${row.kind}">
      <td class="n">${escape(row.row)}
        ${row.column !== 'Value' ? ` <small>${escape(columnLabel(row.column))}</small>` : ''}
        ${row.kind === 'processed' ? '<span class="rekind">processed</span>'
          : row.declared ? ''
          : '<span class="undeclared" title="the plugin writes this but does not list it in its declared outputs">not declared</span>'}
        ${row.description ? `<br><small title="${escape(row.description)}"
          >${escape(clip(row.description, 92))}</small>` : ''}
      </td>
      <td>${spark(row.record, 78, 15)}</td>
      <td class="v">${value(row.record)}</td>
    </tr>`)].join('')).join('');

  const absent = produces.declared_but_absent.map((entry) => `
    <tr><td class="n absent">${escape(entry.row)}<br>
      <small>declared in ${escape(entry.table)}, never written</small></td>
      <td></td><td class="v absent">absent</td></tr>`).join('');

  return `<div class="made">
    <div class="made-head">
      <span class="kicker">what this step made</span>
      <span class="fill"></span>
      <span class="kicker">${produces.count} new${produces.processed
        ? ` · ${produces.processed} processed` : ''} · ${ms(step.duration_ms)}</span>
    </div>
    <table>${rows}${absent}</table>
  </div>`;
}

/* ------------------------------------------------------------------ scope */

function renderScope() {
  const host = el('scope-body');
  if (!state.frame) { host.innerHTML = ''; return; }

  const scope = state.frame.scope;
  el('scope-sub').textContent =
    `${scope.total} values the engine already holds when ${state.frame.step.label} runs`
    + ` · ${scope.later} arrive later`;
  // Say what is on screen, and separately what exists. Printing the total above forty
  // rows with no truncation notice reported 156 matches and showed 40 — a number the
  // reader cannot act on and cannot check.
  el('find-hint').textContent = state.search
    ? (state.search.total > state.search.shown
        ? `${state.search.shown} of ${state.search.total}`
        : `${state.search.total} match`)
    : '/ to focus';

  renderBinding();
  host.innerHTML = state.search ? renderSearch() : renderGroups(scope);
  wireScope();
}

function renderBinding() {
  const bar = el('binding');
  if (!state.binding) { bar.hidden = true; return; }
  bar.hidden = false;
  const { table, row, column, kind } = state.binding;
  bar.innerHTML = `<span class="lbl">click a value to bind it into</span>
    <span class="tgt">${escape(table)} › ${escape(row)} › ${escape(column)}
      ${kind === 'path' ? '(as a multiplier)' : ''}</span>
    <button data-cancel-bind>cancel</button>`;
}

function renderGroups(scope) {
  const groups = scope.groups.map((group) => {
    const id = `g:${group.name || 'file'}`;
    const open = !state.collapsed.has(id);
    return `<div class="grp" style="--fam: var(--fam-${famOf(group.name)})">
      <div class="grp-head" data-toggle="${escape(id)}">
        ${group.position !== null ? `<span class="pos">${group.position}</span>` : ''}
        <span class="lbl">${escape(group.label)}</span>
        <span class="fill"></span>
        <span class="n">${group.count}</span>
      </div>
      ${open ? group.tables.map(renderScopeTable).join('') : ''}
    </div>`;
  }).join('');

  const pending = scope.pending.length ? renderPending(scope.pending) : '';
  return groups + pending;
}

function renderScopeTable(table) {
  return `<div class="tblgrp">
    <div class="tblgrp-head ${table.reads ? 'reads' : ''}">
      <span class="t">${escape(table.table)}</span>
    </div>
    ${table.rows.map((row) => cellRow(table.table, row)).join('')}
  </div>`;
}

function cellRow(table, row) {
  // A row that has not been processed yet is a plain number with no unit of its own;
  // the unit still exists, in the file, in the column beside it. Show it either way,
  // so a value never appears naked.
  const naked = row.record.form === 'number' && row.unit && row.unit !== '-';
  return `<div class="cell-row" data-ref="${escape(row.reference)}"
       title="${escape(row.reference)}">
    <span class="r" title="${escape(`${table} › ${row.row}`)}">${escape(row.row)}${row.column !== 'Value'
      ? ` <span class="col">${escape(columnLabel(row.column))}</span>` : ''}</span>
    <span class="v">${value(row.record)}${naked
      ? `<span class="u">${escape(row.unit)}</span>` : ''}</span>
    <span>${spark(row.record)}</span>
    <button class="ins" data-insert="${escape(row.reference)}"
      title="${state.binding ? 'bind this into the armed field' : 'copy this reference'}"
      >${state.binding ? 'bind' : 'copy'}</button>
  </div>`;
}

function renderPending(pending) {
  const id = 'g:pending';
  const open = !state.collapsed.has(id);
  const byStep = new Map();
  for (const row of pending) {
    const key = `${row.position} ${row.step}`;
    if (!byStep.has(key)) byStep.set(key, []);
    byStep.get(key).push(row);
  }
  return `<div class="grp pending">
    <div class="grp-head" data-toggle="${id}">
      <span class="lbl">not computed yet</span>
      <span class="fill"></span>
      <span class="n">${pending.length}</span>
    </div>
    ${open ? [...byStep].map(([key, rows]) => `
      <div class="tblgrp">
        <div class="tblgrp-head"><span class="t">${escape(key)}</span></div>
        ${rows.map((row) => `<div class="cell-row pending">
          <span class="r">${escape(row.table)} › ${escape(row.row)}</span>
          <span class="v"></span><span></span>
          <span class="at">${row.position}</span>
        </div>`).join('')}
      </div>`).join('') : ''}
  </div>`;
}

function renderSearch() {
  const hits = state.search.results;
  if (!hits.length) {
    return `<p class="empty" style="padding:24px">Nothing matches “${escape(state.query)}”.</p>`;
  }
  const more = state.search.total - state.search.shown;
  return `<div class="grp">
    <div class="grp-head"><span class="lbl">matches</span><span class="fill"></span>
      <span class="n">${more > 0 ? `${state.search.shown} of ${state.search.total}`
        : state.search.total}</span></div>
    <div class="tblgrp">
      ${hits.map((hit) => hit.pending
        ? `<div class="cell-row pending">
             <span class="r">${escape(hit.table)} › ${escape(hit.row)}</span>
             <span class="v"></span><span></span>
             <span class="at">${hit.pending.position}</span></div>`
        : `<div class="cell-row" data-ref="${escape(hit.reference)}" title="${escape(hit.reference)}">
             <span class="r">${escape(hit.table)} › ${escape(hit.row)}${hit.column !== 'Value'
               ? `<span class="col">${escape(hit.column)}</span>` : ''}</span>
             <span class="v">${value(hit.record)}</span>
             <span>${spark(hit.record)}</span>
             <button class="ins" data-insert="${escape(hit.reference)}"
               >${state.binding ? 'bind' : 'copy'}</button></div>`
      ).join('')}
      ${more > 0 ? `<div class="cell-row pending"><span class="r">
        ${more} more match — narrow the search to see ${more === 1 ? 'it' : 'them'}
        </span><span class="v"></span><span></span><span></span></div>` : ''}
    </div>
  </div>`;
}

function famOf(stepName) {
  const entry = state.rail.find((step) => step.name === stepName);
  return entry ? entry.family : 'scale';
}

/* ------------------------------------------------------------------ wiring */

function wireNeeds() {
  const host = el('needs');

  host.querySelectorAll('[data-toggle]').forEach((node) => {
    node.onclick = () => { toggle(node.dataset.toggle); renderNeeds(); };
  });

  host.querySelectorAll('[data-cell], [data-unit], [data-path]').forEach((input) => {
    const field = input.closest('.field');
    const { table, row, col: column } = field.dataset;
    const target = input.dataset.unit !== undefined ? unitColumnOf(table, row, column)
      : input.dataset.path !== undefined ? pathColumnOf(table, row, column)
      : column;

    // Arm the picker only where pointing at another cell is the obvious action: a
    // reference field. Arming on every focus meant Tab through a form silently armed a
    // binding on each field it passed, and lit 95 invisible buttons in the next column.
    if (input.dataset.path !== undefined) {
      input.onfocus = () => armBinding(table, row, target, 'path');
    }
    input.onkeydown = (event) => {
      if (event.key === 'Enter') { event.preventDefault(); input.blur(); }
      if (event.key === 'Escape') { input.value = input.defaultValue; input.blur(); }
    };
    // `change`, not `blur`. It is the event that means "the user finished editing",
    // fires once whether they pressed Enter or clicked away, and does not fire when
    // they tab through a field without touching it.
    input.onchange = () => {
      if (input.value === input.defaultValue) return;
      // A plugin declares this input, the frame emits a field for it, and the file has
      // no such row — the alternative-input pairs on step 300 are exactly this. Without
      // `create` the box renders, accepts a keystroke, and throws it away with a message
      // naming no way to proceed.
      commit(table, row, target, input.value, field.classList.contains('absent'));
    };
  });

  host.querySelectorAll('[data-add-path]').forEach((button) => {
    button.onclick = () => {
      const field = button.closest('.field');
      const { table, row, col: column } = field.dataset;
      armBinding(table, row, pathColumnOf(table, row, column), 'path');
      el('find').focus();
      toast('pick a value on the right to bind it here');
    };
  });

  host.querySelectorAll('[data-goto-row]').forEach((node) => {
    const go = () => revealField({ table: node.dataset.gotoTable, row: node.dataset.gotoRow,
                                   step: state.step });
    node.onclick = go;
    node.onkeydown = (event) => {
      if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); go(); }
    };
  });
  host.querySelectorAll('[data-move-to]').forEach((button) => {
    button.onclick = async () => {
      const result = await call('workflow.move',
        { plugin: state.step, position: Number(button.dataset.moveTo) });
      if (!result) return;
      await refresh();
      await openStep(state.step);
      await saveDraft();
    };
  });
  host.querySelectorAll('[data-remove]').forEach((button) => {
    button.onclick = () => removeStep(button.dataset.remove);
  });

  host.querySelectorAll('[data-open-figure]').forEach((button) => {
    button.onclick = () => openFigures(state.step, button.dataset.openFigure);
  });

  host.querySelectorAll('[data-add-plugin]').forEach((button) => {
    button.onclick = () => {
      const point = state.graph.insertion_points.find((entry) =>
        entry.before === state.step);
      addPlugin(button.dataset.addPlugin, point ? point.position : 1);
    };
  });

  host.querySelectorAll('[data-fix]:not([data-add-plugin])').forEach((button) => {
    button.onclick = () => {
      const [table, row, column] = JSON.parse(button.dataset.fix);
      const field = button.closest('.field');
      const { table: target, row: targetRow, col: targetColumn } = field.dataset;
      const problem = button.closest('.problem');
      const isPath = Boolean(field.querySelector('[data-path]'))
        && button.closest('.problem').textContent.includes('path');
      const reference = `{${table} > ${row} > ${column}, ${referenceUnit(field, isPath)}}`;
      commit(target, targetRow,
        isPath ? pathColumnOf(target, targetRow, targetColumn) : targetColumn,
        reference);
    };
  });
}

async function loadSeries(entry, year) {
  if (!entry) return;
  const result = await call('series', {
    step: figureState.step || state.step,
    table: entry.table, row: entry.row, column: entry.column, year,
  });
  if (!result) return;
  state.series = { ...result.series, table: entry.table, row: entry.row };
  // Whichever surface is showing the calendar is the one to repaint. Repainting the
  // step panel while the modal is up left the picker looking dead: the click registered,
  // the fetch ran, and the figure the reader was looking at never changed.
  if (!el('figures').hidden) paintFigure();
  else renderNeeds();
}

/*
 * The unit a corrected reference should carry.
 *
 * For a path row it is the one already inside the broken reference — the user typed a
 * good unit beside a bad row name, and there is no `[data-unit]` input on an equation
 * row to fall back to. Reading that absent input returned `-`, so one click on
 * "did you mean" rewrote `{… > Nominal power > Value, kW}` as `…, -}` and turned a
 * costing error into a dead run: `Dimension mismatch: original dimension 'power', but
 * requested dimension 'dimensionless'`.
 */
function referenceUnit(field, isPath) {
  if (isPath) {
    const path = field.querySelector('[data-path]');
    const match = path && path.value.match(/,\s*([^,}]+)\}\s*$/);
    if (match) return match[1].trim();
  }
  const unit = field.querySelector('[data-unit]');
  return unit && unit.value ? unit.value : '-';
}

function fieldSpec(table, row, column) {
  for (const group of state.frame.needs) {
    for (const field of group.fields) {
      if (field.table === table && field.row === row && field.column === column) return field;
    }
  }
  return null;
}

function unitColumnOf(table, row, column) {
  const field = fieldSpec(table, row, column);
  return (field && field.unit.column) || 'Unit';
}

function pathColumnOf(table, row, column) {
  const field = fieldSpec(table, row, column);
  return (field && field.path.column) || 'Path';
}

function wireScope() {
  const host = el('scope-body');
  host.querySelectorAll('[data-toggle]').forEach((node) => {
    node.onclick = () => { toggle(node.dataset.toggle); renderScope(); };
  });
  host.querySelectorAll('[data-insert]').forEach((button) => {
    button.onclick = (event) => { event.stopPropagation(); insert(button.dataset.insert); };
  });
  host.querySelectorAll('[data-ref]').forEach((node) => {
    node.onclick = () => insert(node.dataset.ref);
  });
}

function toggle(key) {
  if (state.collapsed.has(key)) state.collapsed.delete(key);
  else state.collapsed.add(key);
}

/*
 * Arm or disarm a binding, and redraw everything that depends on it.
 *
 * Every scope row's button reads "bind" while something is armed and "copy" otherwise,
 * so the state and 157 button labels have to move together. They did not: arming
 * redrew only the bar, leaving every button you could reach to perform the bind
 * claiming it would copy instead. `renderScope` redraws the bar as part of its own
 * work, which is why this cannot live in `renderBinding`.
 */
function setBinding(next) {
  state.binding = next;
  renderScope();
}

function armBinding(table, row, column, kind) {
  setBinding({ table, row, column, kind });
}

/**
 * Put a reference into the armed field, or copy it when nothing is armed.
 *
 * Copying is the honest fallback: with no target, the useful thing is the string
 * itself, and silently doing nothing would look broken.
 */
async function insert(reference) {
  if (!state.binding) {
    // The clipboard rejects without a user gesture, on an insecure origin, and when the
    // page is not focused. Reporting a copy that did not happen leaves the reader
    // pasting whatever was there before.
    const copied = await navigator.clipboard.writeText(reference)
      .then(() => true).catch(() => false);
    toast(copied ? `copied ${reference}`
                 : `${reference} — the browser refused the clipboard, so select it here`,
          !copied);
    return;
  }
  const { table, row, column } = state.binding;
  await commit(table, row, column, reference);
}

async function commit(table, row, column, text, create = false) {
  const result = await call('cell.edit', {
    table, row, column, text, step: state.step, create,
  });
  if (!result) { await refresh(); return; }

  state.project = result.project;
  state.rail = result.rail;
  state.frame = result.frame;
  state.binding = null;
  state.series = null;
  state.effect = null;
  state.effectFor = null;
  for (const entry of state.teaches) {
    if (entry.table === table && entry.row === row) entry.done = true;
  }
  if (state.teaches.length && state.teaches.every((entry) => entry.done)) {
    state.teaches = [];
    toast('that is the shape of it — the rest is the same move, anywhere on any step');
  }
  renderFirstEdits();
  await Promise.all([loadGraph(), loadCatalogue()]);
  const drawn = await call('figures', { step: state.step });
  state.figures = drawn ? drawn.figures : null;

  renderMasthead();
  renderRail();
  renderNeeds();
  renderScope();
  reportMove(result.before, result.after);
  await saveDraft();

  // Last, and only after the edit is fully on screen: what this step is now worth costs
  // another run of the pathway. An edit can flip a step from inert to live — filling the
  // last missing field is exactly when that happens — so the answer cannot be cached
  // across edits, only re-measured after them.
  const worth = await call('step.effect', { step: state.step });
  if (worth) {
    state.effect = worth.effect;
    state.effectFor = state.step;
    renderNeeds();
  }
}

function reportMove(before, after) {
  const readout = el('stat-cost');
  if (after === null) {
    toast(`the model stopped at ${labelFor(state.project.failed)}`, true);
    return;
  }
  if (before === null || before === after) return;
  const delta = after - before;
  const percent = (delta / before) * 100;
  readout.classList.add('moved');
  setTimeout(() => readout.classList.remove('moved'), 1400);
  toast(`${cost(before)} → ${cost(after)}  (${delta > 0 ? '+' : ''}${percent.toFixed(2)}%)`);
}

/* ------------------------------------------------------------------ flow */

async function openStep(name) {
  const result = await call('step', { step: name });
  if (!result) return;
  state.step = name;
  state.frame = result.frame;
  state.project = result.project;
  state.search = null;
  state.query = '';
  state.series = null;
  state.figures = null;
  state.effect = null;
  state.effectFor = null;
  el('find').value = '';
  renderMasthead();
  renderRail();
  renderNeeds();
  renderScope();
  el('needs').scrollTop = 0;

  // Figures are fetched after the step is on screen, not before it. They can be
  // 8,760 numbers, and nothing about them should delay the fields the user came for.
  const drawn = await call('figures', { step: name });
  if (drawn && state.step === name) {
    state.figures = drawn.figures;
    renderNeeds();
  }

  // Costs a second run of the whole pathway, and for an inert step one run per open
  // position. Last, after everything the reader came for is already painted.
  const worth = await call('step.effect', { step: name });
  if (worth && state.step === name) {
    state.effect = worth.effect;
    state.effectFor = name;
    renderNeeds();
  }
}

/* Refreshed alongside the graph: adding or removing a step changes which steps can
 * draw, and a stale badge sends the reader to a figure that is no longer there. */
async function loadCatalogue() {
  const result = await call('figures.catalogue');
  state.catalogue = result ? result.catalogue : [];
}

async function loadGraph() {
  const result = await call('graph');
  if (result) state.graph = result.graph;
}

/** Keep a copy of the file as it now stands, so a reload can put it back. */
async function saveDraft() {
  const source = await call('project.source');
  if (source) keepDraft(source.markdown, state.project.name, state.project.origin);
}

/* ------------------------------------------------------------- the figure stage
 *
 * Figures used to render inline in the step panel, in a column about 560 px wide at a
 * 1440 px window. The dispatch calendar is 365 columns of one-hour cells and the cash
 * flow is 21 stacked years with a cumulative line over them; both were being asked to
 * be instruments in the space of a sidebar illustration. They open full width now, and
 * the rail says which steps have one.
 */
let figureState = { step: null, kind: null };

async function openFigures(stepName, kind = null) {
  const offered = (state.catalogue || []).filter((figure) => figure.step === stepName);
  if (!offered.length) return;

  figureState = { step: stepName, kind: kind || offered[0].kind };
  el('figures').hidden = false;
  el('fig-stage').innerHTML = '<p class="fig-wait">drawing…</p>';
  renderFigureTabs(offered);

  // The data is fetched per step, not per figure: one call carries every array the step
  // can draw, and switching tabs after that is instant.
  const drawn = await call('figures', { step: stepName });
  if (!drawn || el('figures').hidden) return;
  figureState.data = drawn.figures;
  // The head drawn a moment ago came from the catalogue, because there was nothing else
  // to draw it from. Now there is.
  renderFigureTabs(offered);
  paintFigure();
  el('figures').querySelector('.fig-panel').focus({ preventScroll: true });
}

/* Which renderer can name a figure once its data has arrived. A kind absent from this
 * map keeps the catalogue's wording, which is the case for the hourly calendar: its
 * plate carries its own controls and its title does not change with the run. */
const FIGURE_HEADS = {
  contributions: decompositionHead,
  annual_costs: annualHead,
};

function renderFigureTabs(offered) {
  const current = offered.find((figure) => figure.kind === figureState.kind) || offered[0];
  // The catalogue's title is written before the run and cannot know the answer. Once
  // the data has arrived the renderer can say it better, so it does.
  const data = figureState.data && figureState.data[figureState.kind];
  const head = data && FIGURE_HEADS[figureState.kind]
    ? FIGURE_HEADS[figureState.kind](data)
    : { kicker: current.kicker, title: current.title };
  // The step is named first so you know where in the run you are, but on the cash-flow
  // figure the step IS "Discounted Cash Flow" and the kicker opens with the same three
  // words: "Discounted Cash Flow · discounted cash flow · 21 analysis years". Say it once.
  const step = labelFor(figureState.step);
  el('fig-kicker').textContent = head.kicker.toLowerCase().startsWith(step.toLowerCase())
    ? head.kicker : `${step} · ${head.kicker}`;
  el('fig-title').textContent = head.title;
  el('fig-tabs').innerHTML = offered.length > 1
    ? offered.map((figure) => `<button class="fig-tab ${figure.kind === figureState.kind
        ? 'on' : ''}" data-fig-kind="${figure.kind}">${escape(figure.kicker)}</button>`).join('')
    : '';
  el('fig-tabs').querySelectorAll('[data-fig-kind]').forEach((button) => {
    button.onclick = () => {
      figureState.kind = button.dataset.figKind;
      renderFigureTabs(offered);
      paintFigure();
    };
  });
}

/* The calendar's own controls: which cell to draw, and which of its twenty years.
 * Shared because the same markup is wired from the step panel and from the modal, and
 * two copies of this drifted apart once already. */
function wireHourly(host) {
  host.querySelectorAll('[data-series]').forEach((button) => {
    button.onclick = () => {
      const candidates = (figureState.data || state.figures || {}).hourly || [];
      loadSeries(candidates[Number(button.dataset.series)], 0);
    };
  });
  host.querySelectorAll('[data-year]').forEach((button) => {
    button.onclick = () => loadSeries(state.series, Number(button.dataset.year));
  });
}

function paintFigure() {
  const stage = el('fig-stage');
  const data = figureState.data;
  if (!data) return;

  if (figureState.kind === 'contributions' && data.contributions) {
    stage.innerHTML = decomposition(data.contributions);
    return;
  }
  if (figureState.kind === 'annual_costs' && data.annual_costs) {
    stage.innerHTML = annual(data.annual_costs);
    return;
  }
  if (figureState.kind === 'hourly' && data.hourly && data.hourly.length) {
    stage.innerHTML = renderHourly(data.hourly);
    wireHourly(stage);
    return;
  }
  stage.innerHTML = '<p class="fig-wait">this step has nothing to draw right now.</p>';
}

function closeFigures() {
  el('figures').hidden = true;
  figureState = { step: null, kind: null };
}

async function refresh() {
  const result = await call('project.state');
  if (!result) return;
  state.project = result.project;
  state.rail = result.rail;
  // The rail paints from `state.graph.nodes` whenever a graph is loaded, and only falls
  // back to `state.rail`. Refreshing one without the other left the workflow drawn from
  // a stale graph: after moving a step the file, the cost and the server's rail all said
  // 550 while the screen kept showing 650, complete with an insertion point at 625 that
  // no longer existed. Nothing but a full page reload corrected it.
  await Promise.all([loadGraph(), loadCatalogue()]);
  renderMasthead();
  renderRail();
}

/**
 * Open whatever the front door or the chooser handed back.
 *
 * `choice` is already the shape `project.open` takes — an example key, a starter, or
 * markdown — so nothing is translated here.
 */
async function openProject(choice) {
  const result = await call('project.open', choice);
  if (!result) return false;

  if (result.refused) {
    // A file that will not open never becomes the open project. The door stays up and
    // says why, in the element built for it — and, when the app knows the fix, offers
    // to reopen the file with it applied.
    refuse(result.refused);
    return false;
  }

  state.project = result.project;
  state.rail = result.rail;
  state.teaches = result.teaches || [];
  state.collapsed.clear();
  el('chooser').hidden = true;
  await Promise.all([loadGraph(), loadCatalogue()]);
  await saveDraft();
  renderMasthead();
  renderRail();
  renderFirstEdits();

  // A new project opens on the first thing it wants you to change; an existing one opens
  // wherever the trouble is, or at the top.
  const wanted = state.teaches.length
    && state.rail.find((entry) => entry.name === state.teaches[0].step);
  const first = state.rail.find((entry) => entry.status === 'error')
    || state.rail.find((entry) => entry.problems)
    || wanted
    || state.rail[0];
  if (first) await openStep(first.name);
  return true;
}

/*
 * The plugin chooser, opened from a `+` between two steps.
 *
 * Ranked by how much of each plugin's declared input this project already supplies,
 * because someone adding a step is usually extending the chain in front of them. The
 * fit fraction is shown rather than hidden behind the ordering: `6 of 6 ready` is a
 * different proposition from `0 of 20`, and the user should be able to choose the
 * second on purpose.
 */
async function showPlugins(position) {
  const result = await call('plugins');
  if (!result) return;

  el('plugins-sub').textContent =
    `at position ${position} — ranked by how much of each one this project already supplies`;
  el('plugins-list').innerHTML = result.plugins.map((plugin) => {
    if (plugin.error) {
      return `<li class="plugin-row in-use"><div class="nm"><h3>${escape(plugin.label)}</h3></div>
        <p>${escape(plugin.error)}</p></li>`;
    }
    const ready = plugin.needs ? Math.round((plugin.satisfied / plugin.needs) * 100) : 100;
    return `<li class="plugin-row ${plugin.in_use ? 'in-use' : ''}"
        style="--fam: var(--fam-${plugin.family})"
        ${plugin.in_use ? '' : `data-add="${escape(plugin.name)}"`}>
      <div>
        <div class="nm"><span class="fam"></span><h3>${escape(plugin.label)}</h3></div>
        <p>${plugin.summary ? escape(plugin.summary)
          : '<span class="nodesc">no description in the plugin</span>'}</p>
      </div>
      <div class="makes">${plugin.makes.slice(0, 3).map((entry) =>
        `<span title="${escape(entry)}">${escape(tail(entry, 46))}</span>`).join('<br>')}${
        plugin.makes_count > 3 ? `<br>+${plugin.makes_count - 3} more` : ''}</div>
      <div class="fit ${plugin.satisfied ? '' : 'none'}">${plugin.in_use ? 'in use'
        : `<b>${plugin.satisfied}</b> of ${plugin.needs} ready<br>${ready}%`}</div>
    </li>`;
  }).join('');

  el('plugins-list').querySelectorAll('[data-add]').forEach((item) => {
    item.onclick = () => addPlugin(item.dataset.add, position);
  });
  el('plugins').hidden = false;
}

/*
 * Take a step out of the workflow. Its tables stay in the file.
 *
 * Adding a step used to be one-way: a plugin whose inputs the project cannot supply
 * stops the run, and the only escape was re-opening the pathway, which discarded
 * everything else. Someone asking "what does this model look like without the battery"
 * needs that question to be cheap to reverse.
 */
async function removeStep(name) {
  const result = await call('workflow.remove', { plugin: name });
  if (!result) return;
  state.project = result.project;
  state.rail = result.rail;
  state.graph = result.graph;
  renderMasthead();
  renderRail();
  const next = state.rail.find((entry) => entry.status === 'error') || state.rail[0];
  if (next) await openStep(next.name);
  await saveDraft();
  toast(`${labelFor(name)} removed — its tables are still in the file`);
}

/*
 * Clip from the *front*, keeping the end.
 *
 * These strings are `Table › Row` pairs that share long prefixes, so clipping the tail
 * turned three different requirements into three identical rows reading
 * `Non-Depreciable Capital Costs › Land re…`. The part that differs is at the end.
 */
function tail(text, limit) {
  const value = String(text ?? '');
  return value.length > limit ? `…${value.slice(value.length - limit + 1)}` : value;
}

async function addPlugin(name, position) {
  el('plugins').hidden = true;
  const result = await call('workflow.add', { plugin: name, position });
  if (!result) return;
  state.project = result.project;
  state.rail = result.rail;
  state.graph = result.graph;
  renderMasthead();
  renderRail();
  await openStep(name);
  await saveDraft();
  const unmet = state.graph.unmet.filter((entry) => entry.step === name);
  toast(unmet.length
    ? `${labelFor(name)} added — it needs ${unmet.length} value${unmet.length === 1 ? '' : 's'} nothing supplies yet`
    : `${labelFor(name)} added at ${position}`);
}

async function showChooser() {
  const result = await call('examples');
  if (!result) return;
  el('chooser-list').innerHTML = result.examples.map((example) => `
    <li data-key="${escape(example.key)}">
      <div><h3>${escape(example.title)}</h3><p>${escape(example.blurb)}</p></div>
      <span class="c">${cost(example.reference_cost)}<span class="u">${escape(example.unit)}</span>
        <em>published</em></span>
    </li>`).join('');
  el('chooser-list').querySelectorAll('li').forEach((item) => {
    item.onclick = () => openProject({ example: item.dataset.key });
  });
  el('chooser').hidden = false;
}

/* ------------------------------------------------------------------ search */

let searchTimer = null;
el('find').addEventListener('input', (event) => {
  state.query = event.target.value.trim();
  clearTimeout(searchTimer);
  searchTimer = setTimeout(async () => {
    if (!state.query) { state.search = null; renderScope(); return; }
    const result = await call('reference.search', { query: state.query, step: state.step });
    if (result) { state.search = result; renderScope(); }
  }, 120);
});

el('find').addEventListener('keydown', (event) => {
  if (event.key === 'Escape') {
    event.target.value = '';
    state.query = '';
    state.search = null;
    renderScope();
    event.target.blur();
  }
  if (event.key === 'Enter') {
    const first = el('scope-body').querySelector('.cell-row[data-ref]');
    if (first) insert(first.dataset.ref);
  }
});

/* ------------------------------------------------------------------ source */

/*
 * The file itself, editable and downloadable.
 *
 * The whole app rests on one claim — that every screen is a view of this text, and a
 * downloaded copy reproduces the numbers you saw. Until this existed the claim was
 * untestable from inside the app: there was no way to see the file, and no way to keep
 * anything you had done to it.
 */
async function showSource() {
  const result = await call('project.source');
  if (!result) return;
  const text = el('source-text');
  text.value = result.markdown;
  el('source-state').textContent =
    `${result.markdown.split('\n').length} lines · ${escape(result.origin || 'untitled')}`;
  el('source').hidden = false;

  // Assigning `.value` leaves the caret at the end of the text, and `focus()` then
  // scrolls to reveal it — so opening a 173-line file dropped you at its bottom-right
  // corner. Harmless-looking on plain grey text, obvious the moment it had colour.
  text.focus();
  text.setSelectionRange(0, 0);
  text.scrollTop = 0;
  text.scrollLeft = 0;
  paintSource();
}

/*
 * Repaint the layer behind the textarea, and keep the two in register.
 *
 * The scroll has to be copied rather than shared: the textarea is the one that scrolls
 * (it has the caret and the wheel), and the <pre> is inert. Copying on every scroll event
 * is cheap — one property assignment — and anything cleverer drifts by a pixel at the
 * bottom of a long file, which is exactly where a reader is checking a number.
 */
function paintSource() {
  const text = el('source-text');
  const layer = el('source-hl');
  layer.firstElementChild.innerHTML = highlight(text.value);
  layer.scrollTop = text.scrollTop;
  layer.scrollLeft = text.scrollLeft;
}

async function applySource() {
  const result = await call('source.replace', { markdown: el('source-text').value });
  if (!result) return;
  state.project = result.project;
  state.rail = result.rail;
  if (!result.project.error) keepDraft(el('source-text').value, result.project.name,
                                       result.project.origin);

  if (result.project.error) {
    // The file did not parse. Keep the editor open with the message: the text that
    // caused it is right there, and closing would hide the only thing that can fix it.
    el('source-state').textContent = result.project.error;
    el('source-state').classList.add('bad');
    renderMasthead();
    return;
  }

  el('source-state').classList.remove('bad');
  el('source').hidden = true;
  await Promise.all([loadGraph(), loadCatalogue()]);
  renderMasthead();
  renderRail();
  const first = state.rail.find((entry) => entry.status === 'error') || state.rail[0];
  if (first) await openStep(first.name);
  toast('file applied');
}

function downloadSource() {
  const text = el('source-text').value;
  const name = `${(state.project.name || 'project').replace(/[^\w.-]+/g, '_')}.md`;
  const url = URL.createObjectURL(new Blob([text], { type: 'text/markdown' }));
  const link = document.createElement('a');
  link.href = url;
  link.download = name;
  link.click();
  URL.revokeObjectURL(url);
  toast(`downloaded ${name}`);
}

/* ------------------------------------------------------------- narrow screens
 *
 * The drawers are CSS; this is only the state and the ways out. Three of them, because
 * a panel you can open and not close is a trap on a phone: the scrim, Escape, and
 * choosing a step (which is what you opened the workflow drawer to do).
 */
const PANELS = { rail: 'show-rail', scope: 'show-scope' };

function showPanel(which) {
  Object.entries(PANELS).forEach(([panel, button]) => {
    const on = panel === which;
    document.body.classList.toggle(`${panel}-open`, on);
    el(button).setAttribute('aria-expanded', String(on));
  });
  el('scrim').hidden = !which;
  if (which) el(which).focus({ preventScroll: true });
}

function closePanels() { showPanel(null); }

/*
 * Two thresholds, because the columns leave one at a time. Below `tight` the scope
 * panel is a drawer and the rail is still a column; below `narrow` both are drawers.
 * These must stay in step with the two media queries in studio.css — the CSS decides
 * what is drawn and this decides which doors are real.
 */
function narrow() { return window.matchMedia('(max-width: 900px)').matches; }
function tight() { return window.matchMedia('(max-width: 1400px)').matches; }

/* The bar is the only route back to the two panels, so it carries what they head
 * themselves with — otherwise it is two unlabelled doors. */
function renderPanelBar() {
  const bar = el('panelbar');
  bar.hidden = !tight() || !state.project;
  if (bar.hidden) return;
  const nodes = state.graph ? state.graph.nodes : state.rail;
  el('panelbar-steps').textContent = nodes.length ? String(nodes.length) : '';
  el('panelbar-scope').textContent = state.frame && state.frame.scope
    ? String(state.frame.scope.groups.reduce((total, group) =>
        total + group.tables.reduce((sum, table) => sum + table.rows.length, 0), 0))
    : '';
  el('panelbar-here').textContent = state.step ? labelFor(state.step) : '';
}

el('show-rail').onclick = () =>
  showPanel(document.body.classList.contains('rail-open') ? null : 'rail');
el('show-scope').onclick = () =>
  showPanel(document.body.classList.contains('scope-open') ? null : 'scope');
el('scrim').onclick = closePanels;
window.addEventListener('resize', () => {
  // A drawer that has grown back into a column must not keep its scrim: widening the
  // window from 800 to 1200 with the rail open left a veil over the whole app with
  // nothing behind it, and the only way out was to guess that clicking it would help.
  if (!tight() || (!narrow() && document.body.classList.contains('rail-open'))) closePanels();
  renderPanelBar();
});

el('fig-close').onclick = closeFigures;
el('figures').onclick = (event) => { if (event.target.id === 'figures') closeFigures(); };

el('source-button').onclick = showSource;
el('source-apply').onclick = applySource;
el('source-download').onclick = downloadSource;
el('source-close').onclick = () => { el('source').hidden = true; };

// Repaint as it is typed, and follow the scroll. `input` covers typing, paste, cut,
// undo and drag-drop; `scroll` fires for the wheel, the keyboard and the scrollbar.
el('source-text').addEventListener('input', paintSource);
el('source-text').addEventListener('scroll', () => {
  const layer = el('source-hl');
  layer.scrollTop = el('source-text').scrollTop;
  layer.scrollLeft = el('source-text').scrollLeft;
});
el('source').onclick = (event) => {
  if (event.target.id === 'source') el('source').hidden = true;
};

/* ------------------------------------------------------------------ chrome */

el('open-button').onclick = showChooser;
el('chooser').onclick = (event) => {
  if (event.target.id === 'chooser') el('chooser').hidden = true;
};
el('plugins').onclick = (event) => {
  if (event.target.id === 'plugins') el('plugins').hidden = true;
};
el('flag-button').onclick = () => {
  const target = state.rail.find((entry) => entry.status === 'error')
    || state.rail.find((entry) => entry.problems);
  if (target) openStep(target.name);
};

document.addEventListener('keydown', (event) => {
  // `event.target` is not always an Element — a synthetic event can target `document`,
  // which has no `matches` and would take out `/`, `j`/`k` and Escape together.
  const target = event.target;
  if (target instanceof Element && target.matches('input, textarea, select')) return;
  if (event.key === '/') { event.preventDefault(); el('find').focus(); }
  if (event.key === 'Escape') {
    if (state.binding) setBinding(null);
    el('chooser').hidden = true;
    el('plugins').hidden = true;
    el('source').hidden = true;
    closeFigures();
    closePanels();
  }
  if ((event.key === 'j' || event.key === 'k') && state.rail.length) {
    const index = state.rail.findIndex((entry) => entry.name === state.step);
    const next = Math.min(state.rail.length - 1,
      Math.max(0, index + (event.key === 'j' ? 1 : -1)));
    openStep(state.rail[next].name);
  }
});

document.addEventListener('click', (event) => {
  if (event.target.matches('[data-cancel-bind]')) setBinding(null);
});

/* ------------------------------------------------------------------ start */

/*
 * On load: adopt whatever this tab's session already holds, and only open the default
 * pathway when it holds nothing.
 *
 * The first version called `openProject('pv_e')` unconditionally. The session id
 * survived a reload exactly as intended — and then the first thing the client did was
 * overwrite the project that id pointed at, so a refresh silently discarded every edit
 * and every pathway choice. State living on the server is only useful if the client
 * asks the server what it has.
 */
async function start() {
  const existing = await call('project.state');
  if (existing && existing.project && existing.project.steps) {
    state.project = existing.project;
    state.rail = existing.rail;
    await Promise.all([loadGraph(), loadCatalogue()]);
    renderMasthead();
    renderRail();
    const first = state.rail.find((entry) => entry.status === 'error')
      || state.rail.find((entry) => entry.problems)
      || state.rail[0];
    if (first) await openStep(first.name);
    if (existing.project.dirty) toast(`restored ${existing.project.name} with your edits`);
    return;
  }

  // The server has nothing. Before offering the door, look for a draft this tab left
  // behind — in the static build that is the only thing standing between a refresh and
  // an afternoon's work.
  const draft = takeDraft();
  if (draft && draft.markdown) {
    const restored = await call('project.open',
      { markdown: draft.markdown, origin: draft.origin || 'untitled.md' });
    if (restored && !restored.refused) {
      state.project = restored.project;
      state.rail = restored.rail;
      await Promise.all([loadGraph(), loadCatalogue()]);
      renderMasthead();
      renderRail();
      if (state.rail.length) await openStep(state.rail[0].name);
      toast(`restored ${restored.project.name} — this tab kept a copy`);
      return;
    }
    dropDraft();
  }

  // Nothing open and nothing kept: the front door. Not a default project quietly loaded —
  // this app's whole subject is *your* file, and choosing one is the first real act.
  const catalogue = await call('examples');
  if (!catalogue) return;
  const offerTour = firstVisit();
  let choice = null;
  while (!choice) {
    choice = await welcome(catalogue);
    if (!(await openProject(choice))) choice = null;
  }
  markVisited();
  if (choice.tour && offerTour) setTimeout(() => startTour(openStep), 500);
  else if (state.teaches.length) {
    toast(`${plural(state.teaches.length, 'value')} worth changing first — `
        + 'the band above lists them');
  }
}

/*
 * The "start here" band: the handful of values a scaffold wants changed first, each a
 * link that opens its step and puts the field under the cursor.
 *
 * A blank plant runs, which is what makes it useful and also what makes it dangerous:
 * every number on it is a placeholder producing a plausible answer. Coach marks alone
 * were not enough, because the marked fields live on four different steps and a reader
 * has no reason to visit them. Each entry strikes through once its value changes, and
 * the band retires itself when they all have.
 */
function renderFirstEdits() {
  const band = el('firstedits');
  if (!state.teaches.length) { band.hidden = true; return; }

  band.hidden = false;
  el('firstedits-list').innerHTML = state.teaches.map((entry, index) => `
    <a data-goto="${index}" class="${entry.done ? 'done' : ''}"
       title="${escape(entry.table)}">${escape(entry.row)}</a>`).join('');

  el('firstedits-list').querySelectorAll('[data-goto]').forEach((link) => {
    link.onclick = () => revealField(state.teaches[Number(link.dataset.goto)]);
  });
}

async function revealField(entry) {
  if (entry.step && entry.step !== state.step) await openStep(entry.step);

  const escaped = (value) => String(value).replace(/["\\]/g, '\\$&');
  // A row can hold several quantities — `Utilities > Electricity` is a usage, a price
  // and a conversion factor — so an entry may name the column it means. Without one, the
  // first field on the row wins, which is right for the ordinary single-value case.
  const selector = `.field[data-table="${escaped(entry.table)}"][data-row="${escaped(entry.row)}"]`
    + (entry.column ? `[data-col="${escaped(entry.column)}"]` : '');
  const node = el('needs').querySelector(selector);
  if (!node) { toast(`${entry.row} is not on ${entry.label || 'that step'}`, true); return; }

  node.scrollIntoView({ block: 'center', behavior: 'smooth' });
  const input = node.querySelector('input.cell');
  if (input) { input.focus(); input.select(); }
}

wireChooserExtras(
  () => openProject({ starter: 'tea_mass', name: 'New pathway' }),
  (file) => openProject(file),
);
el('help-button').onclick = () => startTour(openStep);
el('firstedits-close').onclick = () => { state.teaches = []; renderFirstEdits(); };

start();
