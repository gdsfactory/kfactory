from typing import Optional

from .. import KCell, LayerEnum, autocell, kdb, library
from ..utils import Enclosure
from .dbu.taper import taper as taper_dbu

__all__ = ["taper", "taper_dbu"]


def taper(
    width1: float,
    width2: float,
    length: float,
    layer: int | LayerEnum,
    enclosure: Optional[Enclosure] = None,
) -> KCell:
    return taper_dbu(
        width1=width1 * library.dbu,
        width2=width2 * library.dbu,
        length=length * library.dbu,
        layer=layer,
        enclosure=enclosure,
    )
