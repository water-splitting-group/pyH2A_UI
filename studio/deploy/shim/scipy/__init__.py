'''A stand-in for scipy, carrying only what pyH2A's *engine* path imports.

Real scipy is a large download and several seconds of boot under Pyodide, and the
engine reaches exactly one thing in it: `constants.Avogadro`, read once by
`Utilities/Unit_Handler/config.py` to define the `entity` unit.

The Analysis and LCA modules do use scipy properly — `optimize`, `signal`, `stats`,
`sparse` — and the studio never loads them. If that changes, importing any of those
submodules raises an ordinary ImportError naming the missing module, which is the
correct failure: loud, immediate, and pointing at the real dependency.

`deploy/build.py` asserts every value here equals real scipy's before it will write a
bundle. A physical constant quietly off by a digit is exactly the class of silently
wrong number this whole application exists to prevent, so it is checked rather than
trusted.
'''

__all__ = ['constants']
