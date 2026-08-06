'''One open project: its text, its parsed form, and its last run.

The file is the single source of truth. Everything else here is derived from it and
thrown away when it changes. That is not a purity preference — it is what makes the
studio's central claim checkable: what you see on screen came from text you can
download, and running the engine on that text reproduces it exactly.

So an edit is: set one cell in the verbatim document, re-serialize the whole file,
re-parse it the way the engine does, re-trace. Around 40–100 ms end to end for the
bundled pathways, which is fast enough that there is no reason to invent a faster
path that could disagree with the slow one.

Two derived things are cached rather than recomputed, both because they cannot go
stale within a session: plugin specs are read from Python classes, and the file
cannot change a plugin's declaration.
'''

import copy
from dataclasses import dataclass, field

from pyh2a_studio.core import engine, grammar, refs, trace

_SPEC_CACHE = {}


def spec(plugin_name, functional_unit_token):
    '''A plugin's `(input_dict, output_dict)`, memoised.

    Importing and instantiating a plugin class costs a few milliseconds; a
    seventeen-step worksheet asks for this on every render. The declaration is a
    property of the installed engine, so caching it for the process is safe —
    changing it means editing Python and restarting.
    '''

    key = (plugin_name, functional_unit_token)
    if key not in _SPEC_CACHE:
        _SPEC_CACHE[key] = engine.plugin_io(plugin_name, functional_unit_token)
    return _SPEC_CACHE[key]


def spec_meta(plugin_name):
    '''`(summary, docstring)` for a plugin, memoised alongside its spec.'''

    key = ('meta', plugin_name)
    if key not in _SPEC_CACHE:
        _SPEC_CACHE[key] = (engine.plugin_summary(plugin_name),
                            engine.plugin_docstring(plugin_name))
    return _SPEC_CACHE[key]


@dataclass
class Project:
    '''An open project and everything derived from its text.

    Attributes
    ----------
    markdown : str
        The file. The source of truth; every other attribute is a function of it.
    name : str
        Display name, from `Display Parameters > Name` when the file gives one.
    document : dict
        `{table_name: grammar.Table}` — verbatim cells, for editing and for
        showing the user their own text back.
    inp : dict
        The engine's input dict with defaults merged. What the engine would run.
    run : engine.Trace
        The last run, step by step. Named `run` because `trace` is the module
        that builds it.
    error : str or None
        Set when the text does not parse at all. `document` and `run` are then
        None and the only useful screen is the source editor.
    effective : dict
        `{table_name: grammar.Table}` — the user's file with its merged defaults
        folded in, cells still verbatim. This is the surface a form edits against,
        because it contains the sixty-odd rows a step reads that the user never
        wrote. `document` alone would leave those blank on screen.
    origins : dict
        `{(table, row, column): origin}` — which file supplied each cell.
    '''

    markdown: str
    name: str = ''
    document: dict = None
    inp: dict = None
    run: object = None
    error: str = None
    origin: str = ''
    dirty: bool = False
    effective: dict = field(default_factory=dict)
    origins: dict = field(default_factory=dict)
    field_cache: dict = field(default_factory=dict, repr=False)
    _later: dict = field(default_factory=dict, repr=False)

    @classmethod
    def open(cls, markdown, origin='', title=''):
        '''Parse, merge, and trace. Never raises for a bad file.

        A file that cannot be parsed is a normal state with a real screen behind
        it, not an exception: the user has a text editor and a message naming the
        line. A file that parses but whose *model* fails is even more normal —
        that lands as `run.failed`, with every step before the failure fully
        inspectable, which is the whole point of tracing.
        '''

        project = cls(markdown=markdown, origin=origin)
        try:
            project.document = grammar.parse_document(markdown)
            project.inp = grammar.engine_dict(markdown)
            documents = grammar.merged_documents(markdown, origin=origin or 'this file')
            project.effective = grammar.effective_document(documents)
            project.origins = grammar.cell_origins(documents)
        except grammar.InputGrammarError as error:
            project.error = str(error)
            return project
        except (KeyError, ValueError, TypeError, OSError) as error:
            project.error = f'{error.__class__.__name__}: {error}'
            return project

        project.name = title or _display_name(project.inp, origin)
        project.retrace()
        return project

    def retrace(self):
        '''Re-run the workflow and rebuild the derived indexes.'''

        self.run = trace.build(self.inp)
        self._later = _later_index(self.run)
        self.field_cache.clear()

    def first_writers(self):
        '''`{cell_key: (step_name, position, step_index)}` for every computed cell.

        A cell absent from this mapping was authored in a file rather than computed,
        which is exactly how the scope panel tells the two apart.
        '''

        return self._later

    def functional_unit(self):
        '''The functional-unit token, or `'kg'` when the file omits it.'''

        try:
            return engine.functional_unit_token(self.inp)
        except (KeyError, TypeError):
            return 'kg'

    def order(self):
        '''Plugin names in execution order.'''

        return [step.name for step in self.run.steps] if self.run else []

    def available_at(self, step_name):
        '''Cell keys in scope when `step_name` runs.

        For a step that never ran because an earlier one failed, this is the state
        at the point of failure — which is the honest answer, and the one that
        makes a reference check meaningful in a broken project.
        '''

        step = self.run.step(step_name) if self.run else None
        if step is not None and step.visible:
            return step.visible
        return self.reachable()

    def reachable(self):
        '''Every cell that existed at any point in the run.

        The right denominator for "does this reference point at anything real", and it
        must survive a failure. `run.steps[-1].visible` does not: when a step fails,
        every later step is skipped with an empty snapshot, so reading the last one
        falls back to the file's literals and the checker starts reporting cells the
        engine demonstrably computed as dangling. Breaking `Photovoltaic > Nominal
        power` produced four such accusations, one of them against a cell
        `Hourly_Irradiation_Plugin` had already written.

        Taking the *deepest* snapshot instead — plus everything every step wrote —
        gives the honest set in both the healthy and the broken case.
        '''

        if not self.run:
            return {}
        reached = dict(self.run.literals)
        for step in self.run.steps:
            reached.update(step.visible)
            reached.update(step.wrote)
        return reached

    def visible_to(self, step_name):
        '''What a step may legitimately reference: what it can see, plus its own writes.

        A step may reference what it writes itself — `Capital_Cost` sums a table and
        then reads that sum inside the same step, and four shipped pathways depend on
        it. The frame has always known this; `check_references` and the
        `reference.check` op did not, and between them reported ten false dangling
        references per shipped PEC and Photocatalytic file.
        '''

        step = self.run.step(step_name) if self.run else None
        available = set(self.available_at(step_name))
        if step is not None:
            available |= set(step.wrote)
        return available

    def produced_later(self, step_name):
        '''`{cell_key: (step_name, position)}` for cells written after `step_name`.

        This is what lets a reference say "not until step 300" instead of "broken".

        Strictly *after*: a step may reference what it writes itself. `Capital_Cost`
        sums `Direct Capital Costs - Gas Processing` and then, in the same step, reads
        that sum for `Installation Costs` — and four shipped pathways rely on it.
        Treating same-step writes as unavailable reports pyH2A's own files as broken.
        '''

        order = self.order()
        if step_name not in order:
            return self._later
        cutoff = order.index(step_name)
        return {
            key: (writer, position)
            for key, (writer, position, index) in self._later.items()
            if index > cutoff
        }

    def reopen(self, markdown):
        '''The same project from new text, keeping its identity.'''

        return Project.open(markdown, origin=self.origin, title=self.name)

    def edit(self, table, row, column, text, create=False):
        '''Write one cell and rebuild everything from the new text.

        Parameters
        ----------
        create : bool
            Allow creating a table or row this file does not have. Off by default:
            creating a row as a side effect of a typo'd name is how a file grows cells
            the engine ignores. The UI asks for it explicitly when adding a value.

            A cell the *merged input* already holds is created regardless, because that
            is not a new cell — it is an override of a default, which is what pyH2A's
            merge exists for. Twelve financial values come from `Defaults_TEA.md`, and
            the file itself has no `Financial Input Values` table, so every one of them
            was an editable-looking box that took your typing, showed it, and threw it
            away: type 20% over an 8% IRR and the field reads 20% while the cost does
            not move and the file is byte-identical.

        Returns
        -------
        Project
            A new project. The old one is untouched, so a caller can keep it for
            comparison or undo.

        Raises
        ------
        KeyError
            When the location is in neither the file nor the merged input, and `create`
            is false.
        '''

        document = copy.deepcopy(self.document)
        # Only the Value column carries a number the plugin type-checks; a unit, a
        # reference path or a comment is text and is written exactly as typed.
        # Scoped to this workflow's own steps: two plugins can declare the same location
        # differently, and only the one actually running is authoritative here.
        steps = self.order()
        written = (engine.spell_for_field(table, row, text, steps) if column == 'Value'
                   else text)
        merged_table = (self.inp or {}).get(table)
        if create or (merged_table is not None and row in merged_table):
            # The merged row, so an override inherits the default's other cells instead
            # of having them invented from the plugin's declared dimension.
            grammar.ensure_cell(document, table, row, column, written,
                                plugins=steps, inherit=(merged_table or {}).get(row))
        elif table in document:
            grammar.set_cell(document, table, row, column, written)
        elif merged_table is not None:
            # The table is real — it arrives from a merged defaults file — so blaming the
            # table would send the reader looking for something that is not wrong. The
            # row is what nothing holds.
            raise KeyError(f'"{table}" has no row "{row}", in this file or in the '
                           f'defaults it merges')
        else:
            raise KeyError(f'no table "{table}" in this file or in the defaults it merges')

        updated = self.reopen(grammar.serialize_document(document))
        updated.dirty = True
        return updated

    def check_references(self, step_name=None):
        '''Every reference in the file, verified against real scope.

        Parameters
        ----------
        step_name : str, optional
            Check as of this step's position. Omitted means check against the end
            of the run — the full set of names the file ever creates, which is the
            right test for "does this reference point at anything real".

        Returns
        -------
        list of dict
            One entry per *problem*, each carrying `table`, `row`, `column`, the
            offending `text`, and the verdict from `refs.check`. Empty when the
            file is clean.
        '''

        if not self.run:
            return []

        if step_name:
            available = self.visible_to(step_name)
            later = self.produced_later(step_name)
        else:
            available = set(self.reachable())
            later = {}

        problems = []
        for table in self.document.values():
            for row_name, row in table.rows.items():
                for column, text in row.items():
                    if not refs.looks_like_reference(text):
                        continue
                    verdict = self._verdict(text, available, later)
                    if verdict['status'] != 'ok':
                        problems.append({'table': table.name, 'row': row_name,
                                         'column': column, 'text': text, **verdict})
        return problems

    def _verdict(self, text, available, later):
        '''A reference's verdict, softened to `unreached` when the run stopped early.

        In a project whose run failed, most of the model never executed, so most
        references cannot resolve — and calling them *dangling* accuses the user of a
        typo they did not make. Breaking `Photovoltaic > Nominal power` in PV+E made
        three perfectly good references report "nothing writes this; the engine would
        silently use 1 instead", pointing at cells that only failed to exist because
        the run had already stopped.

        The honest message names the real problem, which is one step earlier and
        already on screen.
        '''

        verdict = refs.check(text, available, later)
        if verdict['status'] != 'dangling' or not self.run or not self.run.failed:
            return verdict

        stopped = self.run.step(self.run.failed)
        return {
            **verdict,
            'status': 'unreached',
            'message': f'the run stopped at {self.run.failed} (position '
                       f'{stopped.position}), so this could not be checked — '
                       f'fix that step first',
        }


def _display_name(inp, origin):
    '''`Display Parameters > Name`, else the file name made readable.

    Only reached for a file opened from disk. A bundled pathway passes its catalogue
    title instead, so the masthead and the chooser agree: `PV_E_Electricity_Production.md`
    carries no `Display Parameters` row and used to render its raw filename, extension
    included, as an `<h1>` beside four typeset names.
    '''

    display = inp.get('Display Parameters', {})
    name = display.get('Name', {}).get('Value') if isinstance(display, dict) else None
    if isinstance(name, str) and name.strip():
        return name.strip()
    if not origin:
        return 'Untitled'
    return origin.rsplit('/', 1)[-1].rsplit('.', 1)[0].replace('_', ' ').strip() or 'Untitled'


def _later_index(traced):
    '''`{cell_key: (writer, position, step_index)}` for the first writer of each cell.

    First writer, not last: the question a reference asks is "when does this become
    available", and that is answered by whoever creates it.
    '''

    index = {}
    for step_index, step in enumerate(traced.steps):
        for key in step.wrote:
            if key not in index:
                index[key] = (step.name, step.position, step_index)
    return index
