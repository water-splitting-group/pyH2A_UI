'''Build the studio into a folder of static files that needs no server.

    cd studio && UV_PYTHON=3.12 uv run python deploy/build.py

Output lands in `deploy/dist/`. Open `index.html` from any static host — a directory
served by `python -m http.server`, GitHub Pages, an S3 bucket, a USB stick behind a
local web server — and the whole app runs in the browser. No Python installed, no
process to keep alive, no port.

**How it can work at all.** `api.dispatch(op, payload) -> dict` has no HTTP in it and
`server.py` does nothing but translate; `deploy/boot.js` replaces that translation with
a `window.fetch` interception for one URL. The frontend is byte-identical between the
two modes — the same `studio.js` runs against the local server and against Pyodide, and
does not know which.

**What ships.** The web assets as they are; `pyh2a_studio` and `pyH2A` as one zip,
base64'd so it can be `fetch`ed as text and unpacked in memory; the bundled examples and
the starter templates. Pyodide, numpy and scipy come from jsdelivr at runtime and are
cached by the browser — vendoring them would add ~40 MB to a repository for no gain, and
the CDN copy is the one Pyodide's own docs pin.

The build refuses to write a bundle it has not verified: it imports the packaged tree in
a clean interpreter and checks the reference pathway still reproduces 4.1943 USD/kg. A
deploy that silently drops a data file is exactly the failure this whole app exists to
prevent, and it costs one run to rule out.
'''

import argparse
import base64
import io
import json
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

import scipy.constants as real_scipy_constants

STUDIO = Path(__file__).resolve().parent.parent
ROOT = STUDIO.parent
ENGINE = ROOT / 'pyH2A' / 'src'


EXPECTED_EXACT = {
    'pv_e': 4.194302976489664,
    'thermal': 3.2705814097046098,
    'pec': 139.41887561917213,
    'photocatalytic': 185.44329282256817,
    'pv_e_lcoe': 0.02858462133297927,
    'tea_mass': 5.5043552237656455,
}
"""What each pathway computes on this machine, to full precision. Pinned so that a
bundle missing a lookup table fails the build rather than reaching a reader as a
plausible number."""

PUBLISHED = {
    'pv_e': 4.1943, 'thermal': 3.2706, 'pec': 139.4189,
    'photocatalytic': 185.4433, 'pv_e_lcoe': 0.0286,
}
"""pyH2A's own published figures, to the four decimals they are quoted at. Checked
separately from the exact floats: this one moving means the *engine* changed, which is
news rather than a broken build."""

BOOT_PANEL = '''<div id="boot">
  <div class="boot-panel">
    <div class="boot-mark" id="boot-mark" data-waiting aria-hidden="true"></div>
    <span class="kicker">paper plant · studio</span>
    <h1>Starting the engine</h1>
    <p class="boot-lede">pyH2A runs here in your browser — nothing is uploaded and there
      is no server. The first visit downloads the Python runtime; after that it is
      cached and starts in a second or two.</p>
    <div class="boot-track"><div id="boot-bar"></div></div>
    <p id="boot-note">fetching the Python runtime</p>
    <p id="boot-detail"></p>
  </div>
</div>
'''

BOOT_CSS = '''
/* ============================================================ the WASM boot

   Only present in the static build. A blank screen for fifteen seconds reads as broken,
   and this is somebody's first impression of the tool. */

#boot {
  position: fixed;
  inset: 0;
  z-index: 60;
  background: var(--paper);
  display: flex;
  align-items: center;
  justify-content: center;
}
#boot[hidden] { display: none; }
.boot-panel { width: min(560px, 84vw); text-align: center; }
/* The mark inherits currentColor, and the boot ground is paper, so give it the ink the
   rest of the panel is set in rather than leaving it to a browser default. */
.boot-panel .boot-mark { color: var(--prussian); }
.boot-panel h1 {
  font-family: var(--serif);
  font-size: 34px;
  font-weight: 400;
  margin: var(--sp-2) 0 var(--sp-3);
}
.boot-lede { font-size: 14px; color: var(--graphite); line-height: 1.6; margin: 0 0 var(--sp-5); }
.boot-track {
  height: 3px;
  background: var(--rule);
  border-radius: 2px;
  overflow: hidden;
}
#boot-bar {
  height: 100%;
  width: 0;
  background: var(--act);
  transition: width 420ms var(--ease);
}
#boot-bar.bad { background: var(--strontium); }
#boot-note {
  font-family: var(--mono);
  font-size: 12px;
  color: var(--ink);
  margin: var(--sp-3) 0 4px;
}
#boot-detail {
  font-family: var(--mono);
  font-size: 11px;
  color: var(--ash);
  line-height: 1.6;
  margin: 0;
}
'''


def build(out_dir):
    '''Assemble the static build. Returns the output directory.'''

    out_dir = Path(out_dir)
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True)

    # Every asset in `web/`, not a list kept by hand. Adding `highlight.js` to the app
    # and forgetting it here would have shipped a bundle whose `studio.js` imports a file
    # that is not there — a blank page in the static build only, which is the mode
    # nobody runs while developing.
    web = STUDIO / 'src' / 'pyh2a_studio' / 'web'
    shipped = sorted(path for path in web.iterdir()
                     if path.is_file() and path.suffix in {'.html', '.css', '.js'})
    if len(shipped) < 8:
        raise SystemExit(f'only {len(shipped)} web assets found in {web} — expected the '
                         f'whole frontend, so something is wrong with the checkout')
    for path in shipped:
        shutil.copy2(path, out_dir / path.name)

    # The mark is referenced from CSS as `url('assets/mark.svg')`, and a mask whose image
    # 404s renders as nothing at all rather than as a broken-image glyph — so a forgotten
    # copy here is an invisible logo, in the deployed build only.
    if (web / 'assets').is_dir():
        shutil.copytree(web / 'assets', out_dir / 'assets')

    _rewrite_index(out_dir / 'index.html')
    (out_dir / 'studio.css').write_text((out_dir / 'studio.css').read_text() + BOOT_CSS)
    shutil.copy2(STUDIO / 'deploy' / 'boot.js', out_dir / 'boot.js')

    payload = _bundle()
    (out_dir / 'studio-bundle.b64').write_text(base64.b64encode(payload).decode())
    _verify(payload)

    (out_dir / 'README.txt').write_text(_readme())
    return out_dir


def _rewrite_index(path):
    '''Swap the module entry point for the boot, and prepend the boot panel.

    The markup has one source of truth — the app's own `index.html` — so a change to the
    shell cannot land in one mode and not the other.
    '''

    html = path.read_text()
    assert '<script type="module" src="studio.js"></script>' in html, \
        'index.html no longer loads studio.js the way the build expects'
    html = html.replace('<script type="module" src="studio.js"></script>',
                        '<script type="module" src="boot.js"></script>')
    html = html.replace('<body>\n', f'<body>\n\n{BOOT_PANEL}\n')
    path.write_text(html)


def _bundle():
    '''`pyh2a_studio` + `pyH2A` + examples + templates, as one zip.

    Only what the engine path imports. `pandas` and `matplotlib` are absent from that
    path — verified by the original Pyodide spike — and pyH2A's plotting and analysis
    modules come along only because they sit in the same package tree.
    '''

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        _add_tree(archive, STUDIO / 'src' / 'pyh2a_studio', 'src/pyh2a_studio',
                  skip_dirs={'web', '__pycache__'})
        _add_tree(archive, ENGINE / 'pyH2A', 'engine/pyH2A', skip_dirs={'__pycache__'})
        _add_tree(archive, STUDIO / 'examples', 'examples')
        _add_tree(archive, STUDIO / 'templates', 'templates')
        _verify_shim()
        _add_tree(archive, STUDIO / 'deploy' / 'shim', 'shim')
    return buffer.getvalue()


def _verify_shim():
    '''Refuse to ship the scipy stand-in unless it agrees with real scipy exactly.

    The engine reads one value from scipy — `constants.Avogadro` — and carrying the whole
    library into the browser for it costs a large download and several seconds of boot.
    Substituting a literal is safe only if the literal is checked, because a physical
    constant quietly off by a digit is the precise failure class this application exists
    to prevent.
    '''

    shim = {}
    exec((STUDIO / 'deploy' / 'shim' / 'scipy' / 'constants.py').read_text(), shim)

    checked = []
    for name, value in shim.items():
        if name.startswith('_'):
            continue
        expected = getattr(real_scipy_constants, name, None)
        if expected != value:
            raise SystemExit(f'the scipy shim has {name} = {value}, real scipy has {expected}')
        checked.append(name)

    # A shim with nothing in it satisfied every comparison and reported success on an
    # empty list. The engine reads Avogadro; if that ever stops being in the shim, the
    # build must fail rather than congratulate itself.
    if 'Avogadro' not in checked:
        raise SystemExit('the scipy shim does not define Avogadro, which the engine reads')
    print(f'  verified: the scipy stand-in matches real scipy on {", ".join(checked)}')


def _add_tree(archive, source, prefix, skip_dirs=frozenset()):
    for path in sorted(source.rglob('*')):
        if not path.is_file() or path.suffix in ('.pyc', '.pyo'):
            continue
        parts = path.relative_to(source).parts
        if any(part in skip_dirs for part in parts):
            continue
        archive.write(path, f'{prefix}/{"/".join(parts)}')


def _verify(payload):
    '''Unpack the bundle in a clean interpreter and re-run the reference pathway.

    Not a smoke test of the build script — a check that the *bytes about to ship* still
    compute 4.1943. A deploy that quietly drops a lookup table or a defaults file would
    otherwise reach a user as a plausible wrong number.
    '''

    check = '''
import base64, io, json, pathlib, sys, tempfile, zipfile
root = pathlib.Path(tempfile.mkdtemp())
with zipfile.ZipFile(sys.argv[1]) as bundle:
    bundle.extractall(root)
sys.path.insert(0, str(root / 'src'))
sys.path.insert(0, str(root / 'engine'))
from pyh2a_studio import api
from pyh2a_studio.core import examples, starters
examples.EXAMPLES_DIR = root / 'examples'
starters.TEMPLATES_DIR = root / 'templates'
out = {}
def _cost(what, payload):
    r = api.dispatch('project.open', payload)
    if 'error' in r:
        raise SystemExit(f'{what}: {r["error"]}')
    project = r['project']
    if project.get('error'):
        raise SystemExit(f'{what}: {project["error"]}')
    if project.get('failed'):
        raise SystemExit(f'{what}: the run stopped at {project["failed"]}')
    return project['cost']['value']

for key in ('pv_e', 'thermal', 'pec', 'photocatalytic', 'pv_e_lcoe'):
    out[key] = _cost(key, {'example': key, 'session': key})
out['tea_mass'] = _cost('tea_mass', {'starter': 'tea_mass', 'session': 's'})
print(json.dumps(out))
'''
    with io.BytesIO(payload) as _:
        pass
    archive = Path('/tmp/_studio_bundle_check.zip')
    archive.write_bytes(payload)
    script = Path('/tmp/_studio_bundle_check.py')
    script.write_text(check)

    result = subprocess.run([sys.executable, str(script), str(archive)],
                            capture_output=True, text=True, check=False,
                            cwd='/tmp', env={'PATH': '/usr/bin:/bin'})
    if result.returncode != 0:
        raise SystemExit(f'the packaged bundle does not run:\n{result.stderr[-2000:]}')

    costs = json.loads(result.stdout.strip().splitlines()[-1])

    # Two claims, checked separately, because they fail differently.
    #
    # Against the *computed* float, relatively: this catches a corrupted or missing data
    # file. An absolute window cannot — 5e-4 is 0.0001% of the photocatalytic cost and
    # 1.75% of the electricity one, so a bundle mispricing PV CAPEX by two per cent
    # would have shipped silently on the pathway with the smallest number.
    #
    # Against the *published* figure, at the precision it was published: this catches
    # the engine itself drifting, which a relative check against a pinned float would
    # report as a bundle fault when it is nothing of the kind.
    for key, want in EXPECTED_EXACT.items():
        got = costs.get(key)
        if got is None:
            raise SystemExit(f'the packaged bundle did not compute {key}')
        if abs(got - want) > abs(want) * 1e-9:
            raise SystemExit(f'the packaged bundle computes {key} = {got!r}, not {want!r} '
                             f'({abs(got / want - 1) * 100:.4f}% out) — a data file is '
                             f'probably missing or corrupt')

    for key, want in PUBLISHED.items():
        got = costs[key]
        if abs(round(got, 4) - want) > 1e-9:
            raise SystemExit(f'{key} now computes {got!r}, which rounds to {round(got, 4)} '
                             f'and not to the published {want} — the engine has moved')

    print(f'  verified: {len(EXPECTED_EXACT)} pathways reproduce their costs from the '
          f'bundle exactly, and round to their published figures')


def _readme():
    return '''Paper Plant Studio — static build

Everything here is static. Serve this directory over HTTP and open index.html:

    python3 -m http.server 8000

then http://localhost:8000. It will not work from a file:// URL — browsers refuse
module scripts and fetch from the filesystem — so a web server is required even
locally. Any host will do: GitHub Pages, S3, a shared drive behind a web server.

The first load downloads Pyodide, numpy and scipy from jsdelivr (about 40 MB) and
caches them. After that it starts in a second or two. Nothing is uploaded anywhere:
pyH2A runs in the page, and a file you open is read in the browser.

If your network blocks jsdelivr.net, run the desktop version instead — see the
studio README for the one command.
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--out', default=str(STUDIO / 'deploy' / 'dist'))
    arguments = parser.parse_args()

    if not ENGINE.exists():
        raise SystemExit(f'pyH2A source not found at {ENGINE} — clone it beside studio/')

    out = build(arguments.out)
    total = sum(path.stat().st_size for path in out.rglob('*') if path.is_file())
    print(f'  built {out} — {total / 1e6:.1f} MB across {len(list(out.rglob("*")))} files')
    print(f'  serve it: python3 -m http.server --directory {out} 8000')


if __name__ == '__main__':
    main()
