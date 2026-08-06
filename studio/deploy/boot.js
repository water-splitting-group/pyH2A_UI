/* Booting the studio with no server.
 *
 * pyH2A is Python and the studio's backend is Python, so "deploy" here means running
 * both in the browser under Pyodide. The whole trick is one line of architecture that
 * was decided at the start: `api.dispatch(op, payload) -> dict` knows nothing about
 * HTTP, and `server.py` does nothing but translate. So the translation can be replaced.
 *
 * `window.fetch` is intercepted for exactly one URL — `/api` — and routed into Python.
 * Every other request is a real fetch for a real static file. `studio.js` is unchanged
 * and does not know which mode it is in; the same source runs against the local server
 * and against this.
 *
 * The cost is the boot: Pyodide, numpy and scipy are a few tens of megabytes, cached by
 * the browser after the first visit. That is what the progress panel is for — a blank
 * screen for fifteen seconds reads as broken, and this is somebody's first impression.
 */

const PYODIDE = 'https://cdn.jsdelivr.net/pyodide/v0.28.3/full/';

const panel = document.getElementById('boot');
const bar = document.getElementById('boot-bar');
const glyph = document.getElementById('boot-mark');
const note = document.getElementById('boot-note');
const detail = document.getElementById('boot-detail');

const STAGES = [
  [8, 'fetching the Python runtime', 'Pyodide, about 10 MB. Cached after the first visit.'],
  [34, 'loading numpy', 'The only heavyweight the engine path needs.'],
  [62, 'unpacking pyH2A and the studio', 'The engine and this app, as a zip in the page.'],
  [82, 'importing the engine', 'Same code the desktop version runs, byte for byte.'],
  [96, 'warming up', 'One throwaway run so the first real one is fast.'],
];

function stage(index) {
  const [percent, label, why] = STAGES[index];
  bar.style.width = `${percent}%`;
  // The mark fills from the same number as the bar rather than from a timer, so what
  // you are watching rise is the thing that is actually loading. Clearing `data-waiting`
  // stops the idle breath the moment there is real progress to show.
  if (glyph) {
    glyph.style.setProperty('--fill', `${percent}%`);
    glyph.removeAttribute('data-waiting');
  }
  note.textContent = label;
  detail.textContent = why;
}

function fail(error) {
  bar.style.width = '100%';
  bar.classList.add('bad');
  if (glyph) { glyph.removeAttribute('data-waiting'); glyph.style.setProperty('--fill', '100%'); }
  note.textContent = 'could not start';
  detail.innerHTML = `${String(error).replace(/[&<>]/g, (c) =>
    ({ '&': '&amp;', '<': '&lt;', '>': '&gt;' }[c]))}
    <br><br>This build needs WebAssembly and about 40 MB of download. If you are behind a
    proxy that blocks jsdelivr.net, the desktop version has no such dependency —
    see the README.`;
  throw error;
}

const SETUP = `
import io, json, sys, zipfile, base64, pathlib

root = pathlib.Path('/studio')
root.mkdir(exist_ok=True)
with zipfile.ZipFile(io.BytesIO(base64.b64decode(_BUNDLE_B64))) as bundle:
    bundle.extractall(root)
sys.path.insert(0, str(root / 'src'))
sys.path.insert(0, str(root / 'engine'))
# Last on the path: real scipy would win if it were ever installed alongside. The engine
# reads one constant from it, and the stand-in is checked against real scipy at build.
sys.path.append(str(root / 'shim'))

from pyh2a_studio import api
from pyh2a_studio.core import examples, starters

# The packaged layout differs from the checkout: templates and examples sit beside the
# code rather than two directories above it. Repointing here keeps every path in the app
# relative to a package root it can actually find in either.
examples.EXAMPLES_DIR = root / 'examples'
starters.TEMPLATES_DIR = root / 'templates'

def handle(op, payload_json):
    return json.dumps(api.dispatch(op, json.loads(payload_json)), allow_nan=False)

'wired'
`;

const WARM = `
import json
json.loads(handle('project.open', json.dumps({'example': 'pv_e', 'session': '__warm__'})))['project']['cost']['value']
`;

async function boot() {
  try {
    stage(0);
    const script = document.createElement('script');
    script.src = `${PYODIDE}pyodide.js`;
    await new Promise((resolve, reject) => {
      script.onload = resolve;
      script.onerror = () => reject(new Error(`could not load Pyodide from ${PYODIDE}`));
      document.head.append(script);
    });
    const pyodide = await loadPyodide({ indexURL: PYODIDE });

    stage(1);
    await pyodide.loadPackage(['numpy']);

    stage(2);
    const response = await fetch('studio-bundle.b64');
    if (!response.ok) throw new Error('studio-bundle.b64 is missing from this build');
    pyodide.globals.set('_BUNDLE_B64', await response.text());

    stage(3);
    await pyodide.runPythonAsync(SETUP);
    const handle = pyodide.globals.get('handle');

    stage(4);
    const started = performance.now();
    const warm = await pyodide.runPythonAsync(WARM);
    const elapsed = Math.round(performance.now() - started);

    // Prove the engine is intact before handing over. A silent 4.1 instead of 4.1943
    // would be the single worst way for this to go wrong, and it costs one run to rule
    // out — the same check the test suite makes.
    if (Math.abs(warm - 4.194302976489664) > 5e-5) {
      throw new Error(`the engine returned ${warm} for the reference pathway, not 4.1943`);
    }

    // The one seam. `studio.js` calls `fetch('/api', …)` and is never told it is not
    // talking to a server.
    const realFetch = window.fetch.bind(window);
    window.fetch = async (input, init) => {
      const url = typeof input === 'string' ? input : input.url;
      if (!url.endsWith('/api')) return realFetch(input, init);
      const request = JSON.parse((init && init.body) || '{}');
      const body = handle(request.op || '', JSON.stringify(request.payload || {}));
      return new Response(body, {
        status: JSON.parse(body).error ? 400 : 200,
        headers: { 'Content-Type': 'application/json' },
      });
    };

    bar.style.width = '100%';
    note.textContent = `ready — reference pathway reproduces 4.1943 USD/kg in ${elapsed} ms`;
    await new Promise((resolve) => setTimeout(resolve, 420));
    panel.hidden = true;

    await import('./studio.js');
  } catch (error) {
    fail(error);
  }
}

boot();
