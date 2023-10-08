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
        c.auto_rename_ports()
    else:
        c.auto_rename_ports(rename_f)
    c.draw_ports()
    return c


@pytest.mark.parametrize("func", [None, port.rename_clockwise_multi])
def test_rename_default(func: Callable[..., None]) -> None:
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


def test_rename_orientation() -> None:
    cell = port_tests(port.rename_by_direction)

    port_list = cell.ports._ports

    names = (
        [f"E{i}" for i in [3, 0, 2, 4, 1]]
        + [f"N{i}" for i in [3, 4, 2, 0, 1]]
        + [f"W{i}" for i in [3, 4, 2, 0, 1]]
        + [f"S{i}" for i in [3, 0, 2, 4, 1]]
    )

    assert [p.name for p in port_list] == names


def test_rename_setter() -> None:
    kcl = kf.KCLayout("TEST_RENAME")

    assert kcl.rename_function == kf.port.rename_clockwise_multi

    c1 = kf.KCell(kcl=kcl)

    for name, ang, x, y in [
        ("N0", 2, -100, 0),
        ("N1", 2, -100, 500),
        ("N2", 2, -100, 250),
        ("N3", 2, -100, 1000),
        ("W0", 1, 0, 100),
        ("W1", 1, 500, 100),
        ("W2", 1, 250, 100),
        ("W3", 1, 1000, 100),
        ("E0", 0, 100, 1000),
        ("E1", 0, 100, 250),
        ("E2", 0, 100, 500),
        ("E3", 0, 100, 0),
        ("S0", 3, 1000, -100),
        ("S1", 3, 250, -100),
        ("S2", 3, 500, -100),
        ("S3", 3, 0, -100),
    ]:
        c1.create_port(
            trans=kf.kdb.Trans(ang, False, x, y),
            width=1000,
            layer=kcl.layer(1, 0),
            name=name,
        )

    c1.auto_rename_ports()

    for i, _port in enumerate(c1.ports):
        match i % 4:
            case 1:
                assert _port.name is not None and _port.name[1:] == str(i + 2)
            case 2:
                assert _port.name is not None and _port.name[1:] == str(i)
            case _:
                assert _port.name is not None and _port.name[1:] == str(i + 1)

    kcl.rename_function = kf.port.rename_by_direction

    c2 = kf.KCell(kcl=kcl)
    dir_list = [
        ("N0", 2, -100, 0),
        ("N1", 2, -100, 500),
        ("N2", 2, -100, 250),
        ("N3", 2, -100, 1000),
        ("W0", 1, 0, 100),
        ("W1", 1, 500, 100),
        ("W2", 1, 250, 100),
        ("W3", 1, 1000, 100),
        ("E0", 0, 100, 0),
        ("E2", 0, 100, 500),
        ("E1", 0, 100, 250),
        ("E3", 0, 100, 1000),
        ("S3", 3, 0, -100),
        ("S2", 3, 500, -100),
        ("S1", 3, 250, -100),
        ("S0", 3, 1000, -100),
    ]
    for name, ang, x, y in dir_list:
        c2.create_port(
            trans=kf.kdb.Trans(ang, False, x, y),
            width=1000,
            layer=kcl.layer(1, 0),
            name=name,
        )
    c2.auto_rename_ports()
    for i, _port in enumerate(c2.ports):
        match i % 4:
            case 1:
                assert _port.name is not None and _port.name[1:] == str(
                    i % 4 + 1
                ), f"Expected {str(i % 4 + 1)=}, original name {dir_list[i]}"
            case 2:
                assert _port.name is not None and _port.name[1:] == str(
                    i % 4 - 1
                ), f"Expected {str(i % 4 - 1)=}, original name {dir_list[i]}"
            case _:
                assert _port.name is not None and _port.name[1:] == str(
                    i % 4
                ), f"Expected {str(i % 4)=}, original name {dir_list[i]}"

    kcl.rename_function = kf.port.rename_clockwise_multi

    assert c1.ports[0].name == "o1"
    assert c2.ports[0].name == "W0"
