"""Utilities for Ports.

Mainly renaming functions
"""

import re
from collections.abc import Callable, Iterable
from enum import IntEnum
from typing import TYPE_CHECKING, Any

from . import kdb

if TYPE_CHECKING:
    from .kcell import KCell, LayerEnum, Port


class DIRECTION(IntEnum):
    """Alias for KLayout direction to compass directions."""

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
    """Rename a KCell with a renaming function.

    Args:
        c: KCell to be renamed.
        f: Renaming function.
        args: Arguments for the renaming function.
        kwargs: Keyword arguments for the renaming function.
    """
    f(c.ports._ports, *args, **kwargs)


def rename_clockwise(
    ports: "Iterable[Port]",
    layer: "LayerEnum | int | None" = None,
    port_type: str | None = None,
    regex: str | None = None,
    prefix: str = "o",
    start: int = 1,
) -> None:
    """Sort and return ports in the clockwise direction.

    Args:
        ports: List of ports to rename.
        layer: Layer index / LayerEnum of port layer.
        port_type: Port type to filter the ports by.
        regex: Regex string to filter the port names by.
        prefix: Prefix to add to all ports.
        start: Start index per orientation.


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
        match port.angle:
            case 2:
                angle = 0
            case 1:
                angle = 1
            case 0:
                angle = 2
            case 3:
                angle = 3
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


def rename_clockwise_multi(
    ports: "Iterable[Port]",
    layers: "Iterable[LayerEnum | int] | None" = None,
    regex: str | None = None,
    type_prefix_mapping: dict[str, str] = {"optical": "o", "electrical": "e"},
    start: int = 1,
) -> None:
    """Sort and return ports in the clockwise direction.

    Args:
        ports: List of ports to rename.
        layers: Layer indexes / LayerEnums of port layers to rename.
        type_prefix_mapping: Port type to prefix matching in a dictionary.
        regex: Regex string to filter the port names by.
        start: Start index per orientation.


             o3  o4
             |___|_
        o2 -|      |- o5
            |      |
        o1 -|______|- o6
             |   |
            o8  o7

    """
    if layers:
        for p_type, prefix in type_prefix_mapping.items():
            for layer in layers:
                rename_clockwise(
                    ports=ports,
                    layer=layer,
                    port_type=p_type,
                    regex=regex,
                    prefix=prefix,
                    start=start,
                )
    else:
        for p_type, prefix in type_prefix_mapping.items():
            rename_clockwise(
                ports=ports,
                layer=None,
                port_type=p_type,
                regex=regex,
                prefix=prefix,
                start=start,
            )


def rename_by_direction(
    ports: "Iterable[Port]",
    layer: "LayerEnum | int | None" = None,
    port_type: str | None = None,
    regex: str | None = None,
    dir_names: tuple[str, str, str, str] = ("E", "N", "W", "S"),
    prefix: str = "",
) -> None:
    """Rename ports by angle of their transformation.

    Args:
        ports: list of ports to be renamed
        layer: A layer index to filter by
        port_type: port_type string to filter by
        regex: Regex string to use to filter the ports to be renamed.
        dir_names: Prefixes for the directions (east, north, west, south).
        prefix: Prefix to add before `dir_names`

             N0  N1
             |___|_
        W1 -|      |- E1
            |      |
        W0 -|______|- E0
             |   |
            S0   S1

    """
    for dir in DIRECTION:
        _ports = filter_layer_pt_reg(ports, layer, port_type, regex)
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
    layer: "LayerEnum | int | None" = None,
    port_type: str | None = None,
    regex: str | None = None,
) -> "Iterable[Port]":
    """Filter ports by layer index, port type and name regex."""
    _ports = ports
    if layer is not None:
        _ports = filter_layer(_ports, layer)
    if port_type is not None:
        _ports = filter_port_type(_ports, port_type)
    if regex is not None:
        _ports = filter_regex(_ports, regex)

    return _ports


def filter_direction(ports: "Iterable[Port]", direction: int) -> "filter[Port]":
    """Filter iterable/sequence of ports by direction :py:class:~`DIRECTION`."""

    def f_func(p: "Port") -> bool:
        return p.trans.angle == direction

    return filter(f_func, ports)


def filter_port_type(ports: "Iterable[Port]", port_type: str) -> "filter[Port]":
    """Filter iterable/sequence of ports by port_type."""

    def pt_filter(p: "Port") -> bool:
        return p.port_type == port_type

    return filter(pt_filter, ports)


def filter_layer(ports: "Iterable[Port]", layer: "int | LayerEnum") -> "filter[Port]":
    """Filter iterable/sequence of ports by layer index / LayerEnum."""

    def layer_filter(p: "Port") -> bool:
        return p.layer == layer

    return filter(layer_filter, ports)


def filter_regex(ports: "Iterable[Port]", regex: str) -> "filter[Port]":
    """Filter iterable/sequence of ports by port name."""
    pattern = re.compile(regex)

    def regex_filter(p: "Port") -> bool:
        if p.name is not None:
            return bool(pattern.match(p.name))
        else:
            return False

    return filter(regex_filter, ports)


polygon_dict: dict[int, kdb.Polygon] = {}


def port_polygon(width: int) -> kdb.Polygon:
    """Gets a polygon representation for a given port width."""
    if width in polygon_dict:
        return polygon_dict[width]
    else:
        poly = kdb.Polygon(
            [
                kdb.Point(0, width // 2),
                kdb.Point(0, -width // 2),
                kdb.Point(width // 2, 0),
            ]
        )

        hole = kdb.Region(poly).sized(-int(width * 0.05) or -1)
        hole -= kdb.Region(kdb.Box(0, 0, width // 2, -width // 2))

        poly.insert_hole(list(list(hole.each())[0].each_point_hull()))
        polygon_dict[width] = poly
        return poly
