from typing import TYPE_CHECKING, Literal

import klayout.db as kdb
import pytest

import kfactory as kf
from kfactory.port import DPort, Port
from kfactory.serialization import check_metadata_type, convert_metadata_type
from kfactory.utilities import (
    check_cell_ports,
    check_inst_ports,
    instance_port_name,
    load_layout_options,
    polygon_from_array,
    pprint_ports,
)
from tests.conftest import Layers

if TYPE_CHECKING:
    from collections.abc import Iterable


def test_convert_metadata_type() -> None:
    assert convert_metadata_type(42) == 42
    assert convert_metadata_type(3.14) == 3.14
    assert convert_metadata_type("test") == "test"
    assert convert_metadata_type(True) is True
    assert convert_metadata_type(None) is None
    assert convert_metadata_type((1, 2, 3)) == (1, 2, 3)
    assert convert_metadata_type([1, 2, 3]) == [1, 2, 3]
    assert convert_metadata_type({"key": "value"}) == {"key": "value"}


def test_check_metadata_type() -> None:
    assert check_metadata_type(42) == 42
    assert check_metadata_type(3.14) == 3.14
    assert check_metadata_type("test") == "test"
    assert check_metadata_type(True) is True
    assert check_metadata_type(None) is None
    assert check_metadata_type((1, 2, 3)) == (1, 2, 3)
    assert check_metadata_type([1, 2, 3]) == [1, 2, 3]
    assert check_metadata_type({"key": "value"}) == {"key": "value"}

    with pytest.raises(ValueError, match="^Values of the info dict only support.*"):
        check_metadata_type({1, 2, 3})  # type: ignore[arg-type]


def test_load_layout_options() -> None:
    load = load_layout_options(gds2_allow_big_records=True)
    assert load.gds2_allow_big_records is True


def test_polygon_from_array() -> None:
    array = [(0, 0), (1, 0), (1, 1), (2, 1), (2, 0), (3, 0), (3, 3), (0, 3)]
    polygon = polygon_from_array(array)
    assert polygon.to_s() == "(0,0;0,3;3,3;3,0;2,0;2,1;1,1;1,0)"


def test_check_inst_ports() -> None:
    p1 = Port(width=10, angle=0, port_type="input", layer=1, center=(0, 0))
    p2 = Port(width=10, angle=2, port_type="input", layer=1, center=(0, 0))
    p3 = Port(width=6, angle=1, port_type="output", layer=1, center=(0, 0))

    assert check_inst_ports(p1, p2) == 0
    assert check_inst_ports(p1, p3) == 7


def test_check_cell_ports() -> None:
    p1 = DPort(
        name="o1", width=10, orientation=0, port_type="input", layer=1, center=(0, 0)
    )
    p2 = DPort(
        name="o1", width=10, orientation=0, port_type="input", layer=1, center=(0, 0)
    )
    p3 = DPort(
        name="o1", width=6, orientation=90, port_type="output", layer=1, center=(0, 0)
    )

    assert check_cell_ports(p1, p2) == 0
    assert check_cell_ports(p1, p3) == 7


def test_instance_port_name(layers: Layers, kcl: kf.KCLayout) -> None:
    c = kcl.kcell()
    straight = kf.factories.straight.straight_dbu_factory(kcl)(
        width=5000, length=10000, layer=layers.WG
    )
    inst = c.create_inst(straight)

    assert (
        instance_port_name(inst, inst.ports[0])
        == 'straight_W5000_L10000_LWG_ENone_0_0["o1"]'
    )


def test_pprint_ports(layers: Layers, kcl: kf.KCLayout) -> None:
    straight = kf.factories.straight.straight_dbu_factory(kcl)(
        width=5000, length=10000, layer=layers.WG
    )
    ports = [straight.ports[0]]
    port2 = straight.ports[0].copy()
    port2.dcplx_trans = kdb.DCplxTrans(mag=2, rot=30)
    a: list[tuple[Literal["um", "dbu"] | None, Iterable[Port]]] = (
        ("um", ports),
        ("dbu", ports),
        (None, ports),
        (None, [port2]),
    )
    for case, ports_ in a:
        pprint_ports(ports_, case)
