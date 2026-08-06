'''Prove the build's self-verification is not theatre.

Five sabotages of the things a deploy silently depends on — a priced input, the scipy
stand-in, a lookup table, a bundled template. `deploy/build.py` must refuse every one of
them, and say what it found rather than dying on a traceback.

    cd studio && UV_PYTHON=3.12 uv run --with scipy --with-editable . python deploy/tamper.py

Each trial copies the studio into a temporary directory, breaks one thing, and runs the
real build against it. Nothing here touches the working tree.
'''

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

STUDIO = Path(__file__).resolve().parent.parent


def run(cwd):
    return subprocess.run([sys.executable, 'deploy/build.py', '--out', '/tmp/_tamper_dist'],
                          cwd=cwd, capture_output=True, text=True, check=False)

def trial(name, mutate):
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp) / 'studio'
        shutil.copytree(STUDIO, work, ignore=shutil.ignore_patterns(
            '.venv', '__pycache__', 'dist', 'scratch', '.pytest_cache'))
        # build.py resolves the engine relative to itself, so the sibling must exist.
        (Path(tmp) / 'pyH2A').symlink_to(STUDIO.parent / 'pyH2A')
        mutate(work)
        result = run(work)
        refused = result.returncode != 0
        why = (result.stdout + result.stderr).strip().splitlines()
        print(f'{"REFUSED" if refused else "SHIPPED ":8} {name}')
        if refused:
            print(f'         {why[-1][:150]}')
        return refused

def _corrupt_macrs(work):
    engine = work.parent / 'pyH2A' / 'src' / 'pyH2A'
    real = engine / 'Lookup_Tables' / 'MACRS.csv'
    # The symlinked engine is shared, so copy it into the temp tree before editing.
    local = work.parent / 'pyH2A_local'
    shutil.copytree(work.parent / 'pyH2A', local, symlinks=False)
    (work.parent / 'pyH2A').unlink()
    local.rename(work.parent / 'pyH2A')
    target = work.parent / 'pyH2A' / 'src' / 'pyH2A' / 'Lookup_Tables' / 'MACRS.csv'
    lines = target.read_text().splitlines()
    # The last column is the 20-year schedule, which is the one every shipped pathway
    # uses (Depreciation schedule length | 20). Corrupting the 3-year column instead is
    # inert, and a tamper test that changes nothing proves nothing.
    cells = lines[1].split(chr(9))
    cells[-1] = str(float(cells[-1]) + 1.0)
    lines[1] = chr(9).join(cells)
    target.write_text('\n'.join(lines) + '\n')
    assert real  # keep the reference readable


ok = []
ok.append(trial('PV CAPEX 818 -> 834.36 (a 1.78% wrong LCOE)', lambda w: (
    (w / 'examples' / 'PV_E_Base.md').write_text(
        (w / 'examples' / 'PV_E_Base.md').read_text().replace(
            'PV CAPEX | 818 |', 'PV CAPEX | 834.36 |')))))

ok.append(trial('a shim with no constants at all', lambda w: (
    (w / 'deploy' / 'shim' / 'scipy' / 'constants.py').write_text("'''empty'''\n"))))

ok.append(trial('Avogadro off by one digit', lambda w: (
    (w / 'deploy' / 'shim' / 'scipy' / 'constants.py').write_text(
        'Avogadro = 6.02214076e+24\n'))))

ok.append(trial('the starter template deleted from the bundle', lambda w: (
    (w / 'templates' / 'tea_mass.md').unlink())))

ok.append(trial('the 20-year MACRS depreciation rate off by one point', lambda w: (
    _corrupt_macrs(w))))

print()
# Counted, not written down: this line said "all four" while running five trials, which
# is the exact species of stale claim the rest of this file exists to catch.
print(f'{sum(ok)} of {len(ok)} sabotages refused')
sys.exit(0 if all(ok) else 1)
