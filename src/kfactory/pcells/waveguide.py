from .. import KCell, LayerEnum, library
from .dbu.waveguide import waveguide as waveguide_dbu


def waveguide(width: float, length: float, layer: int | LayerEnum) -> KCell:
    return waveguide_dbu(int(width / library.dbu), int(length / library.dbu), layer)
