'''Starting points for a project that does not exist yet.

Distinct from `examples.py`, which holds pyH2A's own published reference pathways —
those are things to *read* and check against. A starter is a scaffold: the smallest
project that already runs, so a new user gets a number on screen in one click and then
edits their way toward the plant they actually have.

`tea_mass.md` is that scaffold. It merges `Defaults_TEA.md`, which supplies the nine-step
techno-economic backbone every pyH2A model shares — time, inflation, production, capital,
replacement, labour, fixed and variable operating cost, discounted cash flow — and adds
the seven tables those steps require. It costs a placeholder plant at 5.5044 USD/kg with
zero validation problems, which is the point: nothing is broken, everything is wrong, and
every wrong thing is a field you can see.

**There is deliberately no electricity scaffold.** `Production_Plugin`'s spec declares
`Plant design capacity` with dimension `energy/time` and its code then requests `power`,
so for a `kWh` functional unit no unit string satisfies both and the step cannot be
made to run from a scalar. The shipped `PV_E_Electricity_Production.md` sidesteps it by
supplying `Design output by year` as a per-year array written by the PV plugin. Until
that is fixed upstream, the honest advice for an electricity model is to start from that
pathway rather than from a blank one, and the chooser says so.
'''

from dataclasses import dataclass
from pathlib import Path

TEMPLATES_DIR = Path(__file__).resolve().parent.parent.parent.parent / 'templates'


@dataclass(frozen=True)
class Starter:
    '''One scaffold a new project can begin from.

    Attributes
    ----------
    key : str
        Stable id.
    title : str
        Display name.
    file_name : str
        File under `templates/`.
    unit : str
        The functional unit it is built around.
    blurb : str
        One sentence on what it gives you.
    teaches : tuple of str
        What the first edits should be, in order. The welcome flow walks these, so a
        new user's first act is changing a number that matters rather than hunting for
        one.
    '''

    key: str
    title: str
    file_name: str
    unit: str
    blurb: str
    teaches: tuple

    def markdown(self):
        return (TEMPLATES_DIR / self.file_name).read_text()


STARTERS = (
    Starter(
        key='tea_mass',
        title='A blank plant',
        file_name='tea_mass.md',
        unit='kg',
        blurb='Nine steps, a placeholder plant, and a real answer in one click.',
        teaches=(
            'Technical Operating Parameters and Specifications\u0000Plant design capacity',
            'Direct Capital Costs - Plant\u0000Plant',
            'Fixed Operating Costs\u0000Staff',
            'Utilities\u0000Electricity\u0000Cost_Value',
        ),
    ),
)

BY_KEY = {starter.key: starter for starter in STARTERS}


def get(key):
    '''The starter with this key.

    Raises
    ------
    KeyError
        Listing the valid keys, because this is reached from request handling where a
        bad key is a client bug worth naming.
    '''

    if key not in BY_KEY:
        raise KeyError(f'unknown starter "{key}" — have: {", ".join(BY_KEY)}')
    return BY_KEY[key]
