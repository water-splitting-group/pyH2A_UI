/* The front door, and the walkthrough.
 *
 * Two jobs a worksheet this dense cannot do without. Someone arriving cold needs to be
 * told what the thing is before being asked to choose inside it — and someone who has
 * chosen needs the three columns explained once, against their own data, not against a
 * screenshot.
 *
 * The tour spotlights real elements of the live app. That is deliberate: a tour built
 * from pictures goes stale the moment the layout moves, and it teaches a reader to
 * recognise a diagram rather than the screen in front of them.
 */

import { cost, escape, num } from './format.js';

const SEEN_KEY = 'paperplant.seen';

/* ------------------------------------------------------------------ front door */

/**
 * Show why a file was refused, and offer the fix when the app knows one.
 *
 * `#welcome-error` existed from the first build and was only ever hidden: every bad
 * file — pyH2A's own examples included — was rejected in complete silence.
 *
 * The remedy is not opened from here. It is parked, and the next `welcome()` wires it
 * to the same `done()` every other control on the door calls, so taking the offer
 * resolves the door exactly like clicking a pathway does. Opening it directly left the
 * project loaded behind a door that was still up, with the door's promise never
 * resolving — so the walkthrough and the first-visit mark never ran again.
 */
let parkedRemedy = null;

export function refuse(refused) {
  const box = document.getElementById('welcome-error');
  const remedy = refused.remedy;
  parkedRemedy = remedy ? { ...remedy, origin: refused.origin } : null;
  box.innerHTML = `
    <b>${escape(refused.headline)}</b>
    <span class="d">${escape(refused.detail)}</span>
    ${refused.saw ? `<span class="saw">the engine said: ${escape(refused.saw)}</span>` : ''}
    ${remedy ? `<button type="button" class="remedy">${escape(remedy.label)}</button>
      <pre>${escape(remedy.preview.trim())}</pre>` : ''}`;
  box.hidden = false;
}

/**
 * Show the front door and resolve with what the user chose.
 *
 * Resolves to `{example}`, `{starter, name}`, or `{markdown, origin}` — the exact
 * shape `project.open` takes, so the caller does no translation.
 */

export function welcome(catalogue, { canDismiss = false } = {}) {
  const panel = document.getElementById('welcome');
  const error = document.getElementById('welcome-error');
  // The refusal is deliberately *not* cleared here. A rejected file sends the caller
  // straight back round this loop, and hiding the explanation on the way in is how the
  // door came to be silent about every bad file it was given.

  document.getElementById('welcome-examples').innerHTML = catalogue.examples.map((entry) => `
    <li data-example="${escape(entry.key)}" role="button" tabindex="0"
        aria-label="${escape(`${entry.title} — ${cost(entry.reference_cost)} ${entry.unit}, published`)}">
      <div><h3>${escape(entry.title)}</h3><p>${escape(entry.blurb)}</p></div>
      <span class="c">${cost(entry.reference_cost)}
        <em>${escape(entry.unit)} · published</em></span>
    </li>`).join('');

  document.getElementById('welcome-starters').innerHTML = catalogue.starters.map((entry) => `
    <li data-starter="${escape(entry.key)}" role="button" tabindex="0"
        aria-label="${escape(`${entry.title} — a new project in ${entry.unit}`)}">
      <div><h3>${escape(entry.title)}</h3><p>${escape(entry.blurb)}</p></div>
      <span class="c">new<em>${escape(entry.unit)}</em></span>
    </li>`).join('');

  panel.hidden = false;
  panel.querySelector('.welcome-panel').focus({ preventScroll: true });

  return new Promise((resolve) => {
    const done = (choice) => {
      document.getElementById('welcome-error').hidden = true;
      panel.hidden = true;
      resolve({ ...choice, tour: document.getElementById('welcome-tour').checked });
    };

    // Anything announced as a button has to behave like one. These were bare list
    // items: not focusable, not reachable, and Tab visited four controls *behind* the
    // overlay before reaching anything on the door.
    const activates = (item, choose) => {
      item.onclick = choose;
      item.onkeydown = (event) => {
        if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); choose(); }
      };
    };
    const named = () =>
      document.getElementById('welcome-name').value.trim() || 'New pathway';

    panel.querySelectorAll('[data-example]').forEach((item) => {
      activates(item, () => done({ example: item.dataset.example }));
    });
    panel.querySelectorAll('[data-starter]').forEach((item) => {
      activates(item, () => done({ starter: item.dataset.starter, name: named() }));
    });

    // Typing a name and pressing Enter did nothing, and there was no submit control:
    // the field looked like the way in and was a dead end. Enter now starts the blank
    // plant, which is the only thing the name belongs to.
    const blank = panel.querySelector('[data-starter]');
    document.getElementById('welcome-name').onkeydown = (event) => {
      if (event.key !== 'Enter' || !blank) return;
      event.preventDefault();
      done({ starter: blank.dataset.starter, name: named() });
    };

    // A refusal parked a remedy on the way in. Wire it to the same `done` as everything
    // else on the door, so taking the offer is just another way of choosing a project.
    const offer = error.querySelector('.remedy');
    if (offer && parkedRemedy) {
      const taking = parkedRemedy;
      offer.onclick = () => {
        parkedRemedy = null;
        done({ markdown: taking.markdown, origin: taking.origin });
      };
    }

    wireFile(document.getElementById('welcome-file'),
             document.getElementById('welcome-drop'), done, error);

    if (canDismiss) {
      panel.onclick = (event) => {
        if (event.target === panel) { panel.hidden = true; resolve(null); }
      };
    }
  });
}

/**
 * A file input plus a drop target, both resolving to `{markdown, origin}`.
 *
 * Read in the page and never sent anywhere. Worth saying out loud on the door itself:
 * these are somebody's unpublished cost models.
 */
function wireFile(input, zone, done, error) {
  // The zone is a <label> around a hidden input: clickable, and until now not reachable
  // by keyboard at all, which made "open a file" a mouse-only door.
  zone.onkeydown = (event) => {
    if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); input.click(); }
  };

  const take = async (file) => {
    if (!file) return;
    if (file.size > 4 * 1024 * 1024) {
      error.textContent = `${file.name} is ${Math.round(file.size / 1024)} kB — a pyH2A input
        is a few tens of kilobytes, so this is probably not one.`;
      error.hidden = false;
      return;
    }
    done({ markdown: await file.text(), origin: file.name });
  };

  input.onchange = () => take(input.files[0]);
  zone.onclick = () => input.click();
  zone.ondragover = (event) => { event.preventDefault(); zone.classList.add('over'); };
  zone.ondragleave = () => zone.classList.remove('over');
  zone.ondrop = (event) => {
    event.preventDefault();
    zone.classList.remove('over');
    take(event.dataTransfer.files[0]);
  };
}

/** Wire the in-app chooser's "start blank" and "open a file" buttons. */
export function wireChooserExtras(onStarter, onFile) {
  const input = document.getElementById('chooser-file');
  document.getElementById('chooser-new').onclick = () => onStarter();
  document.getElementById('chooser-upload').onclick = () => input.click();
  input.onchange = async () => {
    const file = input.files[0];
    if (file) onFile({ markdown: await file.text(), origin: file.name });
    input.value = '';
  };
}

export function firstVisit() {
  return !localStorage.getItem(SEEN_KEY);
}

export function markVisited() {
  try { localStorage.setItem(SEEN_KEY, new Date().toISOString()); } catch { /* private mode */ }
}

/* ------------------------------------------------------------------ walkthrough */

/**
 * Each stop names a live selector, what to say, and optionally a step to open first.
 *
 * Written to be read in order by someone who has never seen a levelized-cost model:
 * where you are, what the step wants, what it can reach, what it made, and then the
 * one thing that makes this a worksheet rather than a report — an edit that moves the
 * answer.
 */
const STOPS = [
  {
    target: '#rail',
    title: 'The pipeline, in the order it runs',
    body: 'Every step of the model, top to bottom, in the order the engine executes them. '
        + 'The lines on the left are real: an edge means a later step reads a value an '
        + 'earlier one wrote. Hover a step to light the edges that touch it, and dim the rest. Click any step to open it.',
    place: 'right',
  },
  {
    target: '.step-head',
    title: 'The step you are looking at',
    body: 'Its position in the run, what it is, how long it took. If it failed, the '
        + 'engine\u2019s own message appears here — along with a warning that the engine '
        + 'often blames the step that was running rather than the one holding the bad value.',
    place: 'bottom',
  },
  {
    target: '#needs .tbl',
    title: 'What this step needs',
    body: 'The inputs this plugin declares, joined to your file. Each carries its valid '
        + 'range, its physical dimension, a sentence on what it means, and which file it '
        + 'came from — several are supplied by pyH2A\u2019s defaults rather than by you. '
        + 'Type in any of them.',
    place: 'right',
  },
  {
    target: '#scope',
    title: 'What it can already reach',
    body: 'Everything the engine holds by the time this step runs, grouped by which step '
        + 'produced it. Values written in your file are in scope everywhere. Search with '
        + '/ — by table, row or unit. Click any row to copy the reference that points at it.',
    place: 'left',
  },
  {
    target: '.made',
    title: 'What it made',
    body: 'Dark means the engine computed it and you cannot type into it; paper means it '
        + 'is yours. That rule holds everywhere in the app. A step usually also passes through '
        + 'values you wrote — those are marked as processed, and not counted as output.',
    place: 'top',
    scroll: true,
  },
  {
    target: '#stat-cost',
    title: 'Change something and watch this',
    body: 'Every edit re-runs the whole model. The time it took is beside this number, '
        + 'and the change it made appears as it happens. Nothing is staged and there is '
        + 'no run button: the number on screen is always the number your file produces.',
    place: 'bottom',
  },
  {
    target: '#source-button',
    title: 'It is one file, and you can have it',
    body: 'Every screen here is a view of a single markdown file. Open the source to read '
        + 'or edit it whole, and download it — running pyH2A on that file reproduces '
        + 'exactly what you saw.',
    place: 'bottom',
  },
];

let stopIndex = 0;
let onOpenStep = null;

/** Start the walkthrough. `openStep` lets a stop bring its own target into view. */
export function startTour(openStep) {
  onOpenStep = openStep;
  stopIndex = 0;
  document.getElementById('tour').hidden = false;
  showStop();
}

function endTour() {
  document.getElementById('tour').hidden = true;
  markVisited();
}

async function showStop() {
  const stop = STOPS[stopIndex];
  if (!stop) { endTour(); return; }

  const target = document.querySelector(stop.target);
  if (!target) { stopIndex += 1; showStop(); return; }

  // Every stop brings its own target into view, not just the one that was marked
  // `scroll`. Stop 5 scrolled `#needs` and nothing scrolled back, so BACK — and every
  // replay from `?` — measured a target that was no longer on screen and parked the
  // ring at y = -214, pointing at nothing above the window.
  if (!fullyVisible(target)) {
    // Instant, not smooth. The rect is read on the next line, and a smooth scroll is
    // still travelling then: arriving at stop 5 on a long step put the ring at y = 2465
    // in a 945-pixel viewport, which dimmed the whole screen and highlighted nothing.
    target.scrollIntoView({ block: 'center', behavior: 'auto' });
    await new Promise((resolve) => requestAnimationFrame(resolve));
  }

  const box = target.getBoundingClientRect();
  const veil = document.getElementById('tour-veil');
  // Clamped to the viewport: the rail starts at x = 0, so a 6px halo around it hung off
  // the left edge and the ring was drawn with one side missing.
  const pad = 6;
  const left = Math.max(0, box.left - pad);
  const top = Math.max(0, box.top - pad);
  veil.style.left = `${left}px`;
  veil.style.top = `${top}px`;
  veil.style.width = `${Math.min(box.right + pad, window.innerWidth) - left}px`;
  veil.style.height = `${Math.min(box.bottom + pad, window.innerHeight - 20) - top}px`;

  document.getElementById('tour-step').textContent = `${stopIndex + 1} of ${STOPS.length}`;
  document.getElementById('tour-title').textContent = stop.title;
  document.getElementById('tour-body').textContent = stop.body;
  document.getElementById('tour-back').disabled = stopIndex === 0;
  document.getElementById('tour-next').textContent =
    stopIndex === STOPS.length - 1 ? 'done' : 'next';

  const bubble = document.getElementById('tour-bubble');
  place(bubble, box, stop.place);
  // Land the keyboard inside the dialog, so Tab walks its three buttons rather than the
  // seventy-two behind it.
  bubble.focus({ preventScroll: true });
}

/** Whether a node is wholly inside the viewport, so a stop need not scroll to it. */
function fullyVisible(node) {
  const box = node.getBoundingClientRect();
  return box.top >= 0 && box.left >= 0
    && box.bottom <= window.innerHeight && box.right <= window.innerWidth;
}

/** Put the bubble beside its target, kept inside the viewport. */
function place(bubble, box, side) {
  const width = 330;
  const height = bubble.offsetHeight || 190;
  const gap = 16;
  let left;
  let top;

  if (side === 'right') { left = box.right + gap; top = box.top; }
  else if (side === 'left') { left = box.left - width - gap; top = box.top + 40; }
  else if (side === 'top') { left = box.left; top = box.top - height - gap; }
  else { left = box.left; top = box.bottom + gap; }

  bubble.style.left = `${Math.max(12, Math.min(left, window.innerWidth - width - 12))}px`;
  bubble.style.top = `${Math.max(12, Math.min(top, window.innerHeight - height - 12))}px`;
}

document.getElementById('tour-next').onclick = () => { stopIndex += 1; showStop(); };
document.getElementById('tour-back').onclick = () => { stopIndex -= 1; showStop(); };
document.getElementById('tour-skip').onclick = endTour;

// A walkthrough you can only leave with a mouse is a trap, and Escape is the first thing
// anyone tries. Arrows move between stops; the handler is on the document because focus
// sits inside the bubble.
document.addEventListener('keydown', (event) => {
  if (document.getElementById('tour').hidden) return;
  if (event.key === 'Tab') {
    // Keep Tab inside the bubble. Without this the fourth press landed on the masthead
    // behind the veil, which is both unreachable by mouse and useless to explain.
    const stops = [...document.querySelectorAll('#tour-bubble button:not([disabled])')];
    if (!stops.length) return;
    const at = stops.indexOf(document.activeElement);
    const next = event.shiftKey ? at - 1 : at + 1;
    if (at === -1 || next < 0 || next >= stops.length) {
      event.preventDefault();
      stops[event.shiftKey ? stops.length - 1 : 0].focus();
    }
    return;
  }
  if (event.key === 'Escape') { event.preventDefault(); endTour(); }
  else if (event.key === 'ArrowRight') { event.preventDefault(); stopIndex += 1; showStop(); }
  else if (event.key === 'ArrowLeft' && stopIndex > 0) {
    event.preventDefault(); stopIndex -= 1; showStop();
  }
});

// The veil is a hole punched over the target, not a shield: clicks landed on whatever was
// behind it, and a stray click during the walkthrough changed the open step underneath.
document.getElementById('tour').addEventListener('click', (event) => {
  if (event.target.closest('#tour-bubble')) return;
  event.preventDefault();
  event.stopPropagation();
}, true);
window.addEventListener('resize', () => {
  if (!document.getElementById('tour').hidden) showStop();
});

/**
 * Mark the fields a starter wants edited first, and say why in one line.
 *
 * A blank plant runs, which is the point and also the trap: every number on it is a
 * placeholder producing a plausible answer, and without a route in a new reader has no
 * idea which of forty values is theirs to change.
 */
export function coach(teaches) {
  document.querySelectorAll('.field.coached').forEach((node) =>
    node.classList.remove('coached'));
  if (!teaches || !teaches.length) return 0;

  let marked = 0;
  for (const entry of teaches) {
    const node = document.querySelector(
      `.field[data-table="${cssEscape(entry.table)}"][data-row="${cssEscape(entry.row)}"]`);
    if (node) { node.classList.add('coached'); marked += 1; }
  }
  return marked;
}

function cssEscape(value) {
  return String(value).replace(/["\\]/g, '\\$&');
}

export { num };
