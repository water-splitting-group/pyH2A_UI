'''The studio's only doorway into pyH2A.

Nothing else in this package imports pyH2A. Everything the UI knows about the
engine — execution order, declared inputs and outputs, what a step could see,
what it actually wrote, why it failed — comes through here.

Three facts about the engine shape this module, all established by the audit in
`../../../1-pyh2a-audit.md` and re-verified here:

1. **Plugins mutate one shared dict in place.** `execute_plugin(name, plugs,
   dcf=...)` writes into `dcf.inp`. There is no return value and no isolation, so
   "what did step 7 produce" is only answerable by looking at the dict before and
   after step 7 runs.
2. **A later step can overwrite an earlier step's meaning.** After
   `Power_Management` runs, `Power Generation > Available energy` no longer means
   "generated" — it means "still unspent after allocation". So a value read at the
   end of the run is not the value step 7 saw. Snapshots must be taken in the
   moment.
3. **Plugins accept a duck-typed `dcf`.** They touch only `inp`, `plugs`,
   `print_info` and `functional_unit`, which is what makes a partial run possible
   at all (verified across all 24 plugins).
'''

import copy
import io
import pkgutil
import time
from contextlib import redirect_stdout
import re
from dataclasses import dataclass, field

from pyH2A import Plugins
from pyH2A.Discounted_Cash_Flow import Discounted_Cash_Flow
from pyH2A.Plugins.Hourly_Irradiation_Plugin import calculate_PV_power_ratio
from pyH2A.Utilities.functional_unit import resolve_functional_unit
from pyH2A.Utilities.Unit_Handler import Quantity
from pyH2A.Utilities.input_modification import execute_plugin, import_plugin, num

LEVELIZED_COST_PATH = ('Dependent Variables', 'Levelized cost', 'Value')
CONTRIBUTIONS_PATH = ('Dependent Variables', 'Levelized cost contributions', 'Value')
FUNCTIONAL_UNIT_PATH = ('Functional Unit', 'Functional Unit', 'Unit')


@dataclass
class RunResult:
    '''Outcome of one full engine run.

    Attributes
    ----------
    levelized_cost : Quantity
        ``USD / <functional unit>``. Format through `core.quantity` — never read
        `base_value` for display.
    contributions : dict
        ``{'Data': {name: Quantity}, 'Total': Quantity, ...}``. Entries provably
        sum to the total; ``Salvage`` is stored negative.
    inp : dict
        Engine state after the run. This is the run's own deep copy; the caller's
        dict is never touched.
    plugs : dict
        Plugin instances by name. Gross flows survive only here (see fact 2).
    warnings : list of str
        ``Warning:`` lines the engine printed — silent value substitutions and
        unprocessed-table notices, which are diagnostics rather than noise.
    stdout : str
        Everything the engine printed, verbatim.
    duration_ms : float
        Wall-clock milliseconds.
    '''

    levelized_cost: object
    contributions: dict
    inp: dict
    plugs: dict
    warnings: list = field(default_factory=list)
    stdout: str = ''
    duration_ms: float = 0.0


class _PartialDCF:
    '''Duck-typed `Discounted_Cash_Flow` for running part or all of a workflow.

    Carries exactly the four attributes plugins reach for on their `dcf` argument.
    '''

    def __init__(self, inp):
        self.inp = inp
        self.plugs = {}
        self.print_info = False
        self.functional_unit = resolve_functional_unit(
            inp['Functional Unit']['Functional Unit']['Unit']
        )


class _SchemaDCF:
    '''Stand-in for a schema-only read, where no input dict exists yet.

    A plugin constructed with `run=False` touches only `dcf.functional_unit` while
    declaring its I/O dicts.
    '''

    def __init__(self, functional_unit):
        self.functional_unit = functional_unit


def _warning_lines(text):
    '''The `Warning:` lines out of captured engine stdout.'''

    return [line.strip() for line in text.splitlines() if line.strip().startswith('Warning')]


def run(inp):
    '''Run the full workflow on a deep copy of `inp`.

    Raises whatever the engine raises, unchanged: the caller owns the error
    boundary and the plain-language translation. Use `trace` when you want a
    failure back as data instead.
    '''

    working_inp = copy.deepcopy(inp)
    calculate_PV_power_ratio.cache_clear()

    captured = io.StringIO()
    started = time.perf_counter()
    with redirect_stdout(captured):
        dcf = Discounted_Cash_Flow(working_inp, print_info=False)
    duration_ms = (time.perf_counter() - started) * 1000

    stdout_text = captured.getvalue()
    return RunResult(
        levelized_cost=dcf.inp['Dependent Variables']['Levelized cost']['Value'],
        contributions=dcf.inp['Dependent Variables']['Levelized cost contributions']['Value'],
        inp=dcf.inp,
        plugs=dcf.plugs,
        warnings=_warning_lines(stdout_text),
        stdout=stdout_text,
        duration_ms=duration_ms,
    )


def workflow_order(inp):
    '''Plugin names in execution order — pyH2A's own ordering, never re-derived.

    Mirrors `Discounted_Cash_Flow.workflow`: a stable sort of the `Workflow` table
    keys by their `Position` value.
    '''

    workflow = inp['Workflow']
    return sorted(workflow, key=lambda name: workflow[name]['Position'])


def workflow_positions(inp):
    '''``{plugin_name: Position}`` as authored, ints where the file gives ints.'''

    return {name: row['Position'] for name, row in inp['Workflow'].items()}


def installed_plugins():
    '''Every plugin module pyH2A ships, by name, sorted.

    This is what makes "add a step" answerable: the set of things that *can* go in a
    workflow is whatever is installed, and it is discoverable rather than a list this
    app would have to keep in step with upstream.

    `Test_Plugin_A` and `Test_Plugin_B` are excluded — they exist to exercise the
    plugin loader and putting them in a chooser would be an invitation to break a
    model.
    '''

    return sorted(
        module.name for module in pkgutil.iter_modules(Plugins.__path__)
        if not module.name.startswith('Test_Plugin')
    )


def plugin_io(plugin_name, functional_unit_token='kg'):
    '''A plugin's declared `input_dict, output_dict` without executing it.

    The declaration carries, per field: `Value.type`, `Value.bounds`,
    `Unit.dimension`, `optional`, `description`. That metadata is the whole reason
    a field in this UI can show its range and its meaning without a lookup table
    maintained by hand.

    Treat the spec as the source for widget generation, not as a guarantee of
    engine behaviour — the audit found places where specs and code disagree.
    '''

    bare_name = plugin_name.split('/')[-1]
    plugin_class = import_plugin(bare_name, plugin_module=True)
    instance = plugin_class(
        _SchemaDCF(resolve_functional_unit(functional_unit_token)),
        print_info=False,
        run=False,
    )
    return getattr(instance, 'input_dict', {}), getattr(instance, 'output_dict', {})


def plugin_docstring(plugin_name):
    '''The plugin class docstring, verbatim and dedented, or ''.'''

    bare_name = plugin_name.split('/')[-1]
    plugin_class = import_plugin(bare_name, plugin_module=True)
    return (plugin_class.__doc__ or '').strip()


def plugin_summary(plugin_name):
    '''First sentence of the plugin docstring, or ''.

    Some upstream docstrings open straight into a numpydoc `Parameters` block; printing
    that as a subtitle reads as a bug, so reST structure yields ''.

    The paragraph split is on the first line that is *blank once stripped*, not on
    `\n\n`. pyH2A separates its summary from `Parameters` with a line of indentation —
    four spaces, or a tab — so splitting on a literal double newline never fired, the
    whole numpydoc block became "the first paragraph", and three plugins with perfectly
    good one-line descriptions rendered as "no description in the plugin".

    Found by comparing the native app against the Pyodide build, where CPython 3.13
    dedents docstrings and the same split therefore *did* fire.
    '''

    lines = []
    for line in plugin_docstring(plugin_name).splitlines():
        if not line.strip():
            break
        lines.append(line)
    collapsed = ' '.join(' '.join(lines).split())
    if '---' in collapsed or collapsed.startswith('Parameters'):
        return ''
    if '. ' in collapsed:
        return collapsed.split('. ')[0] + '.'
    return collapsed


def functional_unit_token(inp):
    '''The functional-unit token from the input dict (e.g. `kg`, `kWh`).'''

    return inp['Functional Unit']['Functional Unit']['Unit']


def unit_dimension(token):
    '''The physical dimension of a unit string, or None if the engine rejects it.

    Returns strings drawn from the same vocabulary a plugin's spec uses for
    `Unit.dimension` — `'power'`, `'dimensionless'`, `'mass / energy'` — which is
    what makes them directly comparable. A field declared `power` whose file cell
    says `kg` is a mistake catchable before the engine runs, and one worth catching:
    the engine converts what it can and produces a number regardless.

    An unknown or unparseable token returns None. That is not the same as a
    mismatch — an unrecognised unit is its own problem, and the caller reports it
    as one.
    '''

    if not isinstance(token, str) or not token.strip():
        return None
    try:
        return str(Quantity(1, token.strip()).dimension)
    except (ValueError, KeyError, TypeError, SyntaxError):
        return None


def dimension_base_unit(dimension):
    '''The SI base unit for a declared dimension, composed if the dimension is.

    `'angle'` -> `'rad'`; `'energy / volume'` -> `'J / m3'`;
    `'volume / (length * substance)'` -> `'m3 / (m * mol)'`.

    Fifteen of the twenty-six dimensions the shipped plugins declare are compound, so a
    flat lookup answered '' for most of the interesting fields — including every price
    per area and every mass flow. Substituting token by token and leaving the operators
    alone covers all of them with the same table, and anything with an unknown token
    yields '' rather than a half-translated string.
    '''

    text = (dimension or '').strip()
    if not text:
        return ''
    if text in _DIMENSION_BASE:
        return _DIMENSION_BASE[text]

    unknown = False

    def token(match):
        nonlocal unknown
        word = match.group(0)
        if word in _DIMENSION_BASE:
            return _DIMENSION_BASE[word]
        unknown = True
        return word

    out = re.sub(r'[A-Za-z_][A-Za-z_0-9]*', token, text)
    return '' if unknown else out


WILDCARD = '<...>'
'''pyH2A's marker for "any table whose name contains this" and "any row". Declared table
keys like `<...> Direct Capital Cost <...>` match by substring after the marker is
stripped (`input_resolver.table_group_resolver_function`), and inside such a table the
row key is a bare `<...>`.'''


def declared_spec(table_name, row_name, plugins=None):
    '''The declaration governing one location, or None if nothing claims it.

    `plugins` scopes the search to the workflow actually being run, and passing it is
    almost always right. Scanning every installed plugin instead answers a different
    question — "could anything, anywhere, read this?" — and the two disagree: `Solar
    Input > Mean solar input` is declared `{float, int}` by PEC_Plugin and `{float}` by
    Solar_Thermal_Plugin, so an alphabetical scan returned PEC's answer for a Solar
    Thermal pathway that PEC has nothing to do with.

    Wildcards are honoured the way the engine honours them, which a literal
    `inputs[table][row]` lookup did not: every cost table in pyH2A is declared as a
    group, so creating a row in `Direct Capital Costs - Electrolyzer` found no
    declaration, wrote `-` into a currency cell, and produced a file real pyH2A refuses.
    '''

    for plugin_name in (plugins if plugins is not None else installed_plugins()):
        try:
            inputs, _ = plugin_io(plugin_name)
        except Exception:  # noqa: BLE001 - a broken plugin must not block an edit
            continue
        table = _match_table(inputs, table_name)
        if table is None:
            continue
        spec = table.get(row_name) or table.get(WILDCARD)
        if spec:
            return spec
    return None


def _match_table(inputs, table_name):
    '''One plugin's declaration for a table: exact name first, then group wildcard.'''

    if table_name in inputs:
        return inputs[table_name]
    for declared, table in inputs.items():
        if WILDCARD in declared and declared.replace(WILDCARD, '').strip() in table_name:
            return table
    return None


def declared_units(table_name, row_name, plugins=None):
    '''Every unit column a declaration names, mapped to the unit to write there.

    Usually one entry, `{'Unit': 'USD'}`. A row carrying several quantities names one per
    group with its own dimension — `# Utilities` declares `Usage_Unit` as `1/mass`,
    `Cost_Unit` as `currency` and `Price_Conversion_Factor_Unit` as dimensionless — and
    filling only the column literally called `Unit` left all three blank, which the engine
    reads as `Unknown unit encountered during parsing`.

    Values are never the empty string: `-` is pyH2A's dimensionless token and a blank unit
    cell is an error.
    '''

    spec = declared_spec(table_name, row_name, plugins) or {}
    return {
        key: dimension_base_unit((value or {}).get('dimension')) or '-'
        for key, value in spec.items()
        if key == 'Unit' or key.endswith('_Unit')
    }


def declared_unit(table_name, row_name, plugins=None):
    '''The unit for the column literally named `Unit`, or None if nothing declares one.

    `None` is what tells `ensure_cell` whether a brand-new table needs a Unit column at
    all, which is a different question from what to put in it.
    '''

    return declared_units(table_name, row_name, plugins).get('Unit')


def spell_for_field(table_name, row_name, text, plugins=None):
    '''The user's number, spelled the way the field's plugin will accept it.

    `Reverse_Osmosis_Plugin` declares `Power demand` as `{float}`. Typing `4` into it
    stopped the whole model with `Expected (<class 'float'>,), but got <class 'int'>` —
    a Python type error shown to a chemist, about a distinction between 4 and 4.0 that
    does not exist in their problem. Meanwhile `Operating capacity factor` declares
    `{float, int}` and takes `2000` happily, so there was no rule to learn either.

    `plugins` must be the workflow's own steps. An alphabetical scan of everything
    installed answered with whichever plugin happened to sort first, and they disagree:
    `Solar-to-Hydrogen Efficiency > STH` is `{float, int}` to PEC_Plugin and `{float}` to
    Solar_Thermal_Plugin, so on a Solar Thermal pathway — where PEC does not appear at
    all — typing `1` was left alone and stopped the run.

    Only the spelling changes, and only for a bare integer on a float-only field: `4`
    becomes `4.0`, and the cell then shows `4.0`, so nothing is hidden. Anything with a
    unit, a percent, grouping, an exponent or a decimal point is left exactly as typed —
    this decides how to write a number, never which number to write.
    '''

    stripped = text.strip()
    if not stripped.lstrip('-').isdigit():
        return text

    spec = declared_spec(table_name, row_name, plugins)
    declared = (spec or {}).get('Value', {}).get('type') or set()
    return f'{stripped}.0' if declared == {float} else text


_DIMENSION_BASE = {
    'angle': 'rad', 'time': 's', 'mass': 'kg', 'energy': 'J', 'power': 'W',
    'length': 'm', 'area': 'm2', 'volume': 'm3', 'currency': 'USD',
    'absolute_temperature': 'K', 'temperature_diff': 'delta_K',
    'substance': 'mol', 'dimensionless': '-',
}
'''Only the dimensions the shipped plugins declare. Anything else yields '', and the
range prints unlabelled rather than mislabelled.'''


def base_magnitude(value, unit_token):
    '''An authored magnitude converted to SI base units, or None.

    `base_magnitude(180, 'deg')` is π; `base_magnitude(45, 'degC')` is 318.15, offset
    included. Needed because a plugin declares its bounds in base units, while a cell
    holds what the user wrote — and before a step runs, its own cells are still plain
    numbers with no `Quantity` to ask.
    '''

    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return None
    if not isinstance(unit_token, str) or not unit_token.strip():
        return None
    try:
        return float(Quantity(value, unit_token.strip()).base_value)
    except (ValueError, KeyError, TypeError, SyntaxError, AttributeError):
        return None


def convert(base_value, base_unit_token, target_unit_token):
    '''A base-unit magnitude expressed in another unit, or None if it cannot convert.

    The trailing unit in a reference is a **conversion request, not a label**. The
    engine reads `{Reverse Osmosis > Capacity > Value, m3/h}` as "that value, in cubic
    metres per hour", and the stored value is per *year* — so the multiplication
    `6000 × Capacity` is `6000 × 5.8` and not `6000 × 50,943`. A worksheet that prints
    the stored magnitude beside the product shows arithmetic that does not work, which
    is worse than showing nothing.

    Returns None when the two units have different dimensions. That is a real
    condition worth reporting rather than papering over: the engine will refuse it too.
    '''

    if base_value is None or not base_unit_token or not target_unit_token:
        return None
    try:
        return float(Quantity(base_value, base_unit_token).unit[target_unit_token])
    except (ValueError, KeyError, TypeError, SyntaxError, AttributeError):
        return None


def parse_number(text):
    '''A cell's text as the engine reads it: `'98%'` → 0.98, `'5,500'` → 5500.

    Returns None for anything the engine leaves as a string — a reference, a file
    path, a categorical. Uses pyH2A's own `num`, so the studio can never disagree with
    the engine about what a cell means. `num` raises `IndexError` on the empty string,
    which is a shape the UI sees constantly, so that one case is handled here.
    '''

    if not isinstance(text, str) or not text.strip():
        return None
    parsed = num(text.strip())
    return float(parsed) if isinstance(parsed, (int, float)) and not isinstance(parsed, bool) else None


def base_unit(unit_token):
    '''The SI base unit a token converts into, or ''. `'deg'` → `'rad'`.'''

    if not isinstance(unit_token, str) or not unit_token.strip():
        return ''
    try:
        return str(Quantity(1, unit_token.strip()).base_unit)
    except (ValueError, KeyError, TypeError, SyntaxError, AttributeError):
        return ''


def state_after(inp, step_name):
    '''The engine dict immediately after `step_name` ran, on a deep copy.

    A trace snapshot digests arrays down to a 96-point envelope, which is right for a
    sparkline and useless for a figure that draws all 8,760 hours. And the completed run
    is the wrong place to look, because a later step may have overwritten the cell — in
    PV+E, `Battery_Plugin` replaces `Power Generation > Available energy (hourly)` with a
    scalar, so a calendar captioned "Photovoltaic" would either fail or quietly draw
    Battery's numbers.

    So: run the prefix and stop. Costs 10-60 ms, paid on demand.

    Returns None when the step is unknown or when any plugin before it raises — a model
    that did not run has no figure, and showing one would be inventing it.
    '''

    order = workflow_order(inp)
    if step_name not in order:
        return None

    working = copy.deepcopy(inp)
    calculate_PV_power_ratio.cache_clear()
    partial = _PartialDCF(working)

    captured = io.StringIO()
    with redirect_stdout(captured):
        for name in order:
            try:
                execute_plugin(name, partial.plugs, print_info=False, dcf=partial)
            except Exception:  # a broken model has no figure  # noqa: BLE001
                return None
            if name == step_name:
                break
    return partial.inp


@dataclass
class Step:
    '''One plugin's execution, with what it could see and what it wrote.

    Attributes
    ----------
    name : str
        Workflow entry name (e.g. `Electrolyzer_Plugin`).
    position : int or float
        Its authored `Position`.
    status : str
        `'ok'`, `'error'`, or `'skipped'` (never reached because an earlier step
        failed).
    duration_ms : float
        Wall clock for this plugin alone.
    visible : dict
        `{(table, row, column): Cell}` — every value in the dict *before* this
        plugin ran. This is the honest answer to "what could this step see".
    wrote : dict
        `{(table, row, column): Cell}` — cells this plugin created or changed,
        captured immediately after it ran.
    error : str or None
        Exception text.
    error_type : str or None
        Exception class name.
    warnings : list of str
        Engine warnings printed while this plugin ran.
    '''

    name: str
    position: object
    status: str
    duration_ms: float = 0.0
    visible: dict = field(default_factory=dict)
    wrote: dict = field(default_factory=dict)
    error: str = None
    error_type: str = None
    warnings: list = field(default_factory=list)


@dataclass
class Trace:
    '''A whole workflow executed step by step, with a snapshot around every step.

    `steps` is in execution order. `result` is a `RunResult` when the run
    completed, else None — and `failed` names the step that stopped it.

    A trace is the studio's central data structure: one run answers what every
    step saw, what it produced, how long it took, and why it failed.
    '''

    steps: list
    result: RunResult = None
    failed: str = None
    literals: dict = field(default_factory=dict)
    duration_ms: float = 0.0

    def step(self, name):
        '''The step with this name, or None.'''

        for entry in self.steps:
            if entry.name == name:
                return entry
        return None
