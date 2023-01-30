import re
from enum import IntEnum
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Concatenate,
    Iterable,
    Optional,
    ParamSpec,
    Sequence,
)

if TYPE_CHECKING:
    from . import kdb
    from .kcell import KCell, LayerEnum, Port


class DIRECTION(IntEnum):
    E = 0
    N = 1
    W = 2
    S = 3


def autorename(
    c: "KCell",
    f: Callable[..., None],
    *args: Any,
    **kwargs: Any,
) -> None:
    f(c.ports._ports, *args, **kwargs)


def rename_clockwise(
    ports: "list[Port]",
    layer: "Optional[LayerEnum | int]" = None,
    port_type: Optional[str] = None,
    regex: Optional[str] = None,
    prefix: str = "o",
    start: int = 1,
) -> None:
    """
    Sort and return ports in the clockwise direction.
    .. code::
             o3  o4
             |___|_
        o2 -|      |- o5
            |      |
        o1 -|______|- o6
             |   |
            o8  o7
    """

    _ports = filter_layer_pt_reg(ports, layer, port_type, regex)

    def sort_key(port: "Port") -> tuple[int, int, int]:
        angle = (2 - port.angle) % 4  # angles should follow the order 2, 1, 0, 3
        dir_1 = 1 if angle < 2 else -1
        dir_2 = -1 if port.angle < 2 else 1
        key_1 = dir_1 * (
            port.trans.disp.x if angle % 2 else port.trans.disp.y
        )  # order should be y, x, -y, -x
        key_2 = dir_2 * (
            port.trans.disp.y if angle % 2 else port.trans.disp.x
        )  # order should be x, -y, -x, y

        return angle, key_1, key_2

    for i, p in enumerate(sorted(_ports, key=sort_key), start=start):
        p.name = f"{prefix}{i}"


def rename_by_direction(
    ports: "Iterable[Port]",
    layer: "Optional[LayerEnum | int]" = None,
    port_type: Optional[str] = None,
    regex: Optional[str] = None,
    dir_names: tuple[str, str, str, str] = ("E", "N", "W", "S"),
    prefix: str = "",
) -> None:
    """
    Rename ports by angle of their transformation
    .. code::
             N0  N1
             |___|_
        W1 -|      |- E1
            |      |
        W0 -|______|- E0
             |   |
            S0   S1

    Args:
        ports: list of ports to be renamed
        layer: A layer index to filter by
        port_type: port_type string to filter by
    """
    _ports = filter_layer_pt_reg(ports, layer, port_type, regex)

    for dir in DIRECTION:
        dir_2 = -1 if dir < 2 else 1
        if dir % 2:

            def key_sort(port: "Port") -> tuple[int, int]:
                return (port.trans.disp.x, dir_2 * port.trans.disp.y)

        else:

            def key_sort(port: "Port") -> tuple[int, int]:
                return (port.trans.disp.y, dir_2 * port.trans.disp.x)

        for i, p in enumerate(sorted(filter_direction(_ports, dir), key=key_sort)):
            p.name = f"{prefix}{dir_names[dir]}{i}"


def filter_layer_pt_reg(
    ports: "Iterable[Port]",
    layer: "Optional[LayerEnum | int]" = None,
    port_type: Optional[str] = None,
    regex: Optional[str] = None,
) -> "Iterable[Port]":

    _ports = ports
    if layer is not None:
        _ports = filter_layer(_ports, layer)
    if port_type is not None:
        _ports = filter_port_type(_ports, port_type)
    if regex is not None:
        _ports = filter_regex(_ports, regex)

    return _ports


def filter_direction(ports: "Iterable[Port]", direction: int) -> "filter[Port]":
    def f_func(p: "Port") -> bool:
        return p.trans.angle == direction

    return filter(f_func, ports)


def filter_port_type(ports: "Iterable[Port]", port_type: str) -> "filter[Port]":
    def pt_filter(p: "Port") -> bool:
        return p.port_type == port_type

    return filter(pt_filter, ports)


def filter_layer(ports: "Iterable[Port]", layer: "int | LayerEnum") -> "filter[Port]":
    def layer_filter(p: "Port") -> bool:
        return p.layer == layer

    return filter(layer_filter, ports)


def filter_regex(ports: "Iterable[Port]", regex: str) -> "filter[Port]":
    pattern = re.compile(regex)

    def regex_filter(p: "Port") -> bool:
        return bool(pattern.match(p.name))

    return filter(regex_filter, ports)
