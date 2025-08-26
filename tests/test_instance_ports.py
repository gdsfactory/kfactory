import pytest

import kfactory as kf
from tests.conftest import Layers


def test_instance_ports(layers: Layers, kcl: kf.KCLayout) -> None:
    c = kcl.kcell()
    ref = c << kf.cells.straight.straight(width=0.5, length=1, layer=layers.WG)

    instance_ports = ref.ports

    assert len(instance_ports) == 2

    assert ref.ports[0] in instance_ports
    assert ref.ports[0].name is not None
    assert ref.ports[0].name in instance_ports
    assert "o3" not in instance_ports

    assert instance_ports[0] == ref.ports[0]

    assert instance_ports["o2"] == ref.ports["o2"]

    assert len(list(instance_ports)) == 2

    assert len(instance_ports.filter(angle=0)) == 1

    assert [(i_a, i_b) for i_a, i_b, _ in instance_ports.each_by_array_coord()] == [
        (0, 0),
        (0, 0),
    ]

    instance_ports.print()
    instance_ports.copy()


@pytest.fixture
def dinstance_ports(layers: Layers, kcl: kf.KCLayout) -> kf.DInstance:
    c = kcl.dkcell()
    straight = kf.factories.straight.straight_dbu_factory(kcl)(
        width=5000, length=10000, layer=layers.WG
    )
    return c.create_inst(
        straight,
        trans=kf.kdb.DCplxTrans(mag=2),
        a=kf.kdb.DVector(10, 0),
        b=kf.kdb.DVector(0, 10),
        na=2,
        nb=2,
    )


def test_dinstance_ports_length(dinstance_ports: kf.DInstance) -> None:
    instance_ports = dinstance_ports.ports
    assert len(instance_ports) == 8


def test_dinstance_ports_contains(dinstance_ports: kf.DInstance) -> None:
    instance_ports = dinstance_ports.ports
    assert dinstance_ports.ports[0] in instance_ports
    assert dinstance_ports.ports[0].name is not None
    assert dinstance_ports.ports[0].name in instance_ports


def test_dinstance_ports_bases(dinstance_ports: kf.DInstance) -> None:
    instance_ports = dinstance_ports.ports
    assert [port.base for port in instance_ports] == instance_ports.bases


def test_dinstance_ports_filter_angle(dinstance_ports: kf.DInstance) -> None:
    instance_ports = dinstance_ports.ports
    assert len(instance_ports.filter(angle=2)) == 4


def test_dinstance_ports_filter_regex(dinstance_ports: kf.DInstance) -> None:
    instance_ports = dinstance_ports.ports
    assert len(instance_ports.filter(regex=".*1.*")) == 4
    assert len(instance_ports.filter(regex=".*1.*", angle=2)) == 4


def test_dinstance_ports_filter_orientation(dinstance_ports: kf.DInstance) -> None:
    instance_ports = dinstance_ports.ports
    assert len(instance_ports.filter(orientation=180)) == 4


def test_dinstance_ports_filter_port_type(dinstance_ports: kf.DInstance) -> None:
    instance_ports = dinstance_ports.ports
    assert len(instance_ports.filter(port_type="non-optical")) == 0


def test_dinstance_ports_filter_layer(dinstance_ports: kf.DInstance) -> None:
    instance_ports = dinstance_ports.ports
    assert len(instance_ports.filter(layer=0)) == 8


def test_dinstance_ports_access(dinstance_ports: kf.DInstance) -> None:
    instance_ports = dinstance_ports.ports
    assert instance_ports[0] == dinstance_ports.ports[0]
    assert instance_ports["o2", 0, 0] == instance_ports["o2"]
    assert instance_ports["o1", 0, 0] == instance_ports["o1"]


def test_dinstance_ports_index_error(dinstance_ports: kf.DInstance) -> None:
    instance_ports = dinstance_ports.ports
    with pytest.raises(IndexError):
        instance_ports["o1", 3, 0]


def test_dinstance_ports_iter(dinstance_ports: kf.DInstance) -> None:
    instance_ports = dinstance_ports.ports
    assert len(list(instance_ports)) == 8


def test_single_instance_iter(kcl: kf.KCLayout, layers: Layers) -> None:
    c = kcl.kcell()
    ref = c.create_inst(
        kf.cells.straight.straight(width=0.5, length=1, layer=layers.WG),
        trans=kf.kdb.ICplxTrans(mag=2),
    )
    instance_ports = ref.ports
    assert len(list(instance_ports)) == 2


def test_complex_array_iter(kcl: kf.KCLayout, layers: Layers) -> None:
    c = kcl.dkcell()
    ref = c.create_inst(
        kf.cells.straight.straight(width=0.5, length=1, layer=layers.WG),
        trans=kf.kdb.DCplxTrans(mag=2),
        a=kf.kdb.DVector(10, 0),
        b=kf.kdb.DVector(0, 10),
        na=2,
        nb=2,
    )
    instance_ports = ref.ports
    assert len(list(instance_ports)) == 8


def test_regular_array_iter(kcl: kf.KCLayout, layers: Layers) -> None:
    c = kcl.dkcell()
    ref = c.create_inst(
        kf.cells.straight.straight(width=0.5, length=1, layer=layers.WG),
        a=kf.kdb.DVector(10, 0),
        b=kf.kdb.DVector(0, 10),
        na=2,
        nb=2,
    )
    instance_ports = ref.ports
    assert len(list(instance_ports)) == 8


def test_single_instance_each_by_array_coord(kcl: kf.KCLayout, layers: Layers) -> None:
    c = kcl.kcell()
    ref = c.create_inst(
        kf.cells.straight.straight(width=0.5, length=1, layer=layers.WG),
        trans=kf.kdb.ICplxTrans(mag=2),
    )
    instance_ports = ref.ports
    assert [(i_a, i_b) for i_a, i_b, _ in instance_ports.each_by_array_coord()] == [
        (0, 0),
        (0, 0),
    ]
    instance_ports.copy()


def test_complex_array_each_by_array_coord(kcl: kf.KCLayout, layers: Layers) -> None:
    c = kcl.dkcell()
    ref = c.create_inst(
        kf.cells.straight.straight(width=0.5, length=1, layer=layers.WG),
        trans=kf.kdb.DCplxTrans(mag=2),
        a=kf.kdb.DVector(10, 0),
        b=kf.kdb.DVector(0, 10),
        na=2,
        nb=2,
    )
    instance_ports = ref.ports
    assert [(i_a, i_b) for i_a, i_b, _ in instance_ports.each_by_array_coord()] == [
        (0, 0),
        (0, 0),
        (0, 1),
        (0, 1),
        (1, 0),
        (1, 0),
        (1, 1),
        (1, 1),
    ]

    instance_ports.copy()


def test_regular_array_each_by_array_coord(kcl: kf.KCLayout, layers: Layers) -> None:
    c = kcl.dkcell()
    ref = c.create_inst(
        kf.cells.straight.straight(width=0.5, length=1, layer=layers.WG),
        a=kf.kdb.DVector(10, 0),
        b=kf.kdb.DVector(0, 10),
        na=2,
        nb=1,
    )
    instance_ports = ref.ports
    assert [(i_a, i_b) for i_a, i_b, _ in instance_ports.each_by_array_coord()] == [
        (0, 0),
        (0, 0),
        (1, 0),
        (1, 0),
    ]
    instance_ports.copy()


def test_vinstance_ports_filter(kcl: kf.KCLayout, layers: Layers) -> None:
    c = kcl.vkcell()
    ref = c.create_inst(
        kf.factories.straight.straight_dbu_factory(kcl)(
            width=5000, length=10000, layer=layers.WG
        ),
        trans=kf.kdb.DCplxTrans(mag=2),
    )
    instance_ports = ref.ports

    assert len(instance_ports.filter(angle=0)) == 1
    assert len(instance_ports.filter(angle=1)) == 0
    assert len(instance_ports.filter(angle=2)) == 1
    assert len(instance_ports.filter(angle=3)) == 0

    assert len(instance_ports.filter(orientation=0)) == 1
    assert len(instance_ports.filter(orientation=180)) == 1

    assert len(instance_ports.filter(layer=0)) == 2
    assert len(instance_ports.filter(layer=1)) == 0

    assert len(instance_ports.filter(regex="o.*")) == 2
    assert len(instance_ports.filter(regex="o3")) == 0

    assert len(instance_ports.filter(port_type="optical")) == 2
    assert len(instance_ports.filter(port_type="non-optical")) == 0

    instance_ports.copy()

    repr(instance_ports)

    assert len(list(iter(instance_ports))) == 2

    assert instance_ports[0] == ref.ports[0]

    assert instance_ports["o2"] == ref.ports["o2"]

    str(instance_ports)


def test_vinstance_ports_contains(kcl: kf.KCLayout, layers: Layers) -> None:
    c = kcl.vkcell()
    ref = c.create_inst(
        kf.factories.straight.straight_dbu_factory(kcl)(
            width=5000, length=10000, layer=layers.WG
        ),
        trans=kf.kdb.DCplxTrans(mag=2),
    )
    assert ref.ports[0] in ref.ports
    assert ref.ports[0].name is not None
    assert ref.ports[0].name in ref.ports


def test_iter(kcl: kf.KCLayout, layers: Layers) -> None:
    kcell = kcl.kcell()
    _straight_factory = kf.factories.straight.straight_dbu_factory(kcl)
    iref = kcell.create_inst(
        _straight_factory(width=5000, length=10000, layer=layers.WG),
        trans=kf.kdb.ICplxTrans(mag=2),
    )
    assert len(list(iref.ports)) == 2
    assert all(isinstance(p, kf.Port) for p in iref.ports)

    dkcell = kcl.dkcell()
    dref = dkcell.create_inst(
        _straight_factory(width=5000, length=10000, layer=layers.WG),
        trans=kf.kdb.DCplxTrans(mag=2),
    )
    assert len(list(dref.ports)) == 2
    assert all(isinstance(p, kf.DPort) for p in dref.ports)


def test_dinstance_ports_repr(dinstance_ports: kf.DInstance) -> None:
    assert repr(dinstance_ports.ports)
