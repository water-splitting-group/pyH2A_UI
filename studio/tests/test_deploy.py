'''What the static build has to contain to work at all.

The frontend is ES modules loaded by the browser, so a missing file is not a build error
and not a test failure — it is a blank page, in the deployed build only, discovered by
whoever opens the URL. These tests check the two things that have actually gone wrong.
'''

import re
from pathlib import Path

import pytest

STUDIO = Path(__file__).resolve().parents[1]
WEB = STUDIO / 'src' / 'pyh2a_studio' / 'web'
DIST = STUDIO / 'deploy' / 'dist'


def _imported_modules():
    '''Every relative module the frontend imports, read from the source.'''

    found = set()
    for source in WEB.glob('*.js'):
        for match in re.finditer(r"from '\./([\w.-]+\.js)'", source.read_text()):
            found.add(match.group(1))
    return found


def test_the_frontend_imports_are_discoverable():
    '''If this fails the scan below is broken, not the build, and the next test is
    vacuous — which is worse than a red one.'''

    imported = _imported_modules()
    assert len(imported) >= 4, imported
    assert 'highlight.js' in imported


def test_every_imported_module_exists_in_the_source_tree():
    for name in sorted(_imported_modules()):
        assert (WEB / name).exists(), name


@pytest.mark.skipif(not DIST.exists(), reason='no build to check; run deploy/build.py')
def test_the_bundle_ships_every_module_the_client_imports():
    '''`build.py` copied a hand-kept list of web files. Adding `highlight.js` to the app
    and forgetting the list would have shipped a frontend whose `studio.js` imports a
    file that is not there.'''

    missing = sorted(name for name in _imported_modules() if not (DIST / name).exists())
    assert not missing, f'the bundle is missing modules the client imports: {missing}'
