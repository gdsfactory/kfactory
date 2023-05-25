import kfactory as kf
from kfactory import port
from typing import Iterable, Callable, Optional
import numpy as np
import pytest


port_x_coords = [-10000, 0, 0, 0, 10000]
port_y_coords = [0, -10000, 0, 10000, 0]
offset = 50000


@kf.cell
def port_tests(rename_f: Optional[Callable[..., None]] = None) -> kf.KCell:
    c = kf.KCell()

    i = 0
    for angle in range(4):
        for x, y in zip(port_x_coords, port_y_coords):
            point = (
                kf.kdb.Trans(angle, False, 0, 0) * kf.kdb.Trans(0, False, offset, 0)
            ) * kf.kdb.Point(x, y)

            c.create_port(
                name=f"{i}",
                trans=kf.kdb.Trans(
                    angle,
                    False,
                    point.to_v(),
                ),
                layer=c.kcl.layer(1, 0),
                width=1 / c.kcl.dbu,
            )
    if rename_f is None:
        c.autorename_ports()
    else:
        c.autorename_ports(rename_f)
    c.draw_ports()
    return c


@pytest.mark.parametrize("func", [None, port.rename_clockwise])
def test_rename_default(func) -> None:
    cell = port_tests(func)
    port_list = cell.ports._ports
    xl = len(port_x_coords)

    indexes = list(range(4 * xl))
    # east:
    inds_east = list(
        sorted(
            indexes[2 * xl : 3 * xl],
            key=lambda i: (-port_y_coords[i - 2 * xl], -port_x_coords[i - 2 * xl]),
        )
    )
    inds_north = list(
        sorted(
            indexes[xl : 2 * xl],
            key=lambda i: (-port_y_coords[i - xl], -port_x_coords[i - xl]),
        )
    )
    inds_west = list(
        sorted(indexes[:xl], key=lambda i: (-port_y_coords[i], -port_x_coords[i]))
    )
    inds_south = list(
        sorted(
            indexes[3 * xl : 4 * xl],
            key=lambda i: (-port_y_coords[i - 3 * xl], -port_x_coords[i - 3 * xl]),
        )
    )

    assert [p.name for p in port_list] == [
        f"o{i+1}" for i in inds_east + inds_north + inds_west + inds_south
    ]


def test_rename_orientatioin() -> None:
    cell = port_tests(port.rename_by_direction)

    dir_names = {0: "E", 1: "N", 2: "W", 3: "S"}

    port_list = cell.ports._ports

    names = (
        [f"E{i}" for i in [3, 0, 2, 4, 1]]
        + [f"N{i}" for i in [3, 4, 2, 0, 1]]
        + [f"W{i}" for i in [3, 4, 2, 0, 1]]
        + [f"S{i}" for i in [3, 0, 2, 4, 1]]
    )

    assert [p.name for p in port_list] == names


def test_rename_setter():
    kcl = kf.KCLayout()

    assert kcl.rename_function == kf.port.rename_clockwise

    c1 = kf.KCell(kcl=kcl)
    c1.create_port(
        trans=kf.kdb.Trans(2, False, 0, 0), width=1000, layer=kcl.layer(1, 0)
    )
    c1.create_port(trans=kf.kdb.Trans(), width=1000, layer=kcl.layer(1, 0))
    c1.autorename_ports()

    kcl.rename_function = kf.port.rename_by_direction

    c2 = kf.KCell(kcl=kcl)
    c2.create_port(
        trans=kf.kdb.Trans(2, False, 0, 0), width=1000, layer=kcl.layer(1, 0)
    )
    c2.create_port(trans=kf.kdb.Trans(), width=1000, layer=kcl.layer(1, 0))
    c2.autorename_ports()

    print(c1.ports)
    print(c2.ports)

    assert c1.ports[0].name == "o1"
    assert c2.ports[0].name == "W0"
