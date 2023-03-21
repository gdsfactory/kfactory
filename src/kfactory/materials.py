"""Register materials."""
from __future__ import annotations

from typing import Any, Callable, Dict, Tuple, Union

import numpy as np

MaterialSpec = Union[str, float, Tuple[float, float], Callable[..., float]]

material_name_to_meep: Dict[str, MaterialSpec] = {
    "si": "Si",
    "sin": "Si3N4_NIR",
    "sio2": "SiO2",
}

material_name_to_lumerical: Dict[str, MaterialSpec] = {
    "si": "Si (Silicon) - Palik",
    "sio2": "SiO2 (Glass) - Palik",
    "sin": "Si3N4 (Silicon Nitride) - Phillip",
}


__all__ = [
    "material_name_to_meep",
    "material_name_to_lumerical",
]
