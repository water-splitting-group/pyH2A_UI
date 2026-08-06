'''The bundled pathways, and their published costs.

Five files ship with the studio. They are pyH2A's own end-to-end test inputs,
copied here so the app opens with something real in it and so the test suite has
five genuinely different workflows to check against.

`reference_cost` is what upstream's own test asserts. It is pinned here so a
regression in this app — or in the engine — shows up as a number that stopped
matching rather than as a number nobody recognised.

`Thermal_Base_Merge.md` is deliberately absent: it references its base file by a
path relative to the working directory and breaks the moment it is copied.
'''

from dataclasses import dataclass
from pathlib import Path

EXAMPLES_DIR = Path(__file__).resolve().parent.parent.parent.parent / 'examples'


@dataclass(frozen=True)
class Example:
    '''One bundled pathway.

    Attributes
    ----------
    key : str
        Stable id used in URLs and payloads.
    title : str
        Display name.
    file_name : str
        File under `examples/`.
    reference_cost : float
        Upstream's asserted levelized cost.
    unit : str
        Its unit, e.g. `USD/kg`. Not always per kilogram — `pv_e_lcoe` prices
        electricity, which is why no noun in this app is hard-coded.
    blurb : str
        One sentence.
    '''

    key: str
    title: str
    file_name: str
    reference_cost: float
    unit: str
    blurb: str

    def markdown(self):
        '''The file's text.'''

        return (EXAMPLES_DIR / self.file_name).read_text()


EXAMPLES = (
    Example('pv_e', 'PV + Electrolysis', 'PV_E_Base.md', 4.1943, 'USD/kg',
            'Solar PV powering an electrolyzer, with battery and stored-power operation.'),
    Example('thermal', 'Solar Thermal', 'Thermal_Base.md', 3.2706, 'USD/kg',
            'Concentrated solar thermal water splitting.'),
    Example('pec', 'Photoelectrochemical', 'PEC_Base.md', 139.4189, 'USD/kg',
            'Photoelectrochemical cells under solar concentration.'),
    Example('photocatalytic', 'Photocatalytic', 'Photocatalytic_Base.md', 185.4433, 'USD/kg',
            'Particle photocatalyst baggie reactors.'),
    Example('pv_e_lcoe', 'PV Electricity', 'PV_E_Electricity_Production.md', 0.0286, 'USD/kWh',
            'The same PV machinery selling electricity — the functional unit is not always mass.'),
)

BY_KEY = {example.key: example for example in EXAMPLES}


def get(key):
    '''The example with this key.

    Raises
    ------
    KeyError
        With the valid keys listed, because this is reached from request handling
        where a bad key is a client bug worth naming.
    '''

    if key not in BY_KEY:
        raise KeyError(f'unknown example "{key}" — have: {", ".join(BY_KEY)}')
    return BY_KEY[key]
