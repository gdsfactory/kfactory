"""Extra tests targeting instance_group.py coverage."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

import kfactory as kf
from kfactory.exceptions import (
    PortLayerMismatchError,
    PortTypeMismatchError,
    PortWidthMismatchError,
)

if TYPE_CHECKING:
    from tests.conftest import Layers


def _make_cell(
    kcl: kf.KCLayout, layers: Layers, width: int = 500, port_type: str = "optical"
) -> kf.KCell:
    c = kcl.kcell()
    c.shapes(layers.WG).insert(kf.kdb.Box(0, 0, 1000, 1000))
    c.create_port(
        name="o1",
        trans=kf.kdb.Trans(0, False, 0, 500),
        width=width,
        layer=kcl.find_layer(layers.WG),
        port_type=port_type,
    )
    c.create_port(
        name="o2",
        trans=kf.kdb.Trans(2, False, 1000, 500),
        width=width,
        layer=kcl.find_layer(layers.WG),
        port_type=port_type,
    )
    return c


def test_instance_group_add(kcl: kf.KCLayout, layers: Layers) -> None:
    parent = kcl.kcell()
    c = _make_cell(kcl, layers)
    g = kf.InstanceGroup()
    g.add(parent << c)
    g.add(parent << c)
    assert len(g.insts) == 2


def test_instance_group_dadd(kcl: kf.KCLayout, layers: Layers) -> None:
    parent = kcl.dkcell()
    c = _make_cell(kcl, layers)
    g = kf.DInstanceGroup()
    g.add(parent << c.to_dtype())
    assert len(g.insts) == 1


def test_instance_group_add_port(kcl: kf.KCLayout, layers: Layers) -> None:
    parent = kcl.kcell()
    c = _make_cell(kcl, layers)
    inst = parent << c
    g = kf.InstanceGroup(insts=[inst])
    g.add_port(port=inst.ports[0], name="p1")
    assert "p1" in [p.name for p in g.ports]


def test_dinstance_group_add_port(kcl: kf.KCLayout, layers: Layers) -> None:
    parent = kcl.dkcell()
    c = _make_cell(kcl, layers)
    inst = parent << c.to_dtype()
    g = kf.DInstanceGroup(insts=[inst])
    g.add_port(port=inst.ports[0], name="p1")
    assert "p1" in [p.name for p in g.ports]


def test_instance_group_connect_to_port(kcl: kf.KCLayout, layers: Layers) -> None:
    parent = kcl.kcell()
    c = _make_cell(kcl, layers)
    inst1 = parent << c
    inst2 = parent << c
    g = kf.InstanceGroup(insts=[inst1])
    g.add_port(port=inst1.ports["o1"], name="g_port")
    inst2.transform(kf.kdb.Trans(0, False, 5000, 0))
    # Connect using the group's own port to inst2's port
    g.connect(port="g_port", other=inst2, other_port_name="o2")


def test_instance_group_connect_port_to_port(kcl: kf.KCLayout, layers: Layers) -> None:
    parent = kcl.kcell()
    c = _make_cell(kcl, layers)
    inst1 = parent << c
    inst2 = parent << c
    g = kf.InstanceGroup(insts=[inst1])
    g.add_port(port=inst1.ports["o1"], name="g_port")
    inst2.transform(kf.kdb.Trans(0, False, 5000, 0))
    # Connect using ports directly
    g.connect(port=g.ports["g_port"], other=inst2.ports["o2"])


def test_instance_group_connect_other_port_name_none_raises(
    kcl: kf.KCLayout, layers: Layers
) -> None:
    parent = kcl.kcell()
    c = _make_cell(kcl, layers)
    inst1 = parent << c
    inst2 = parent << c
    g = kf.InstanceGroup(insts=[inst1])
    g.add_port(port=inst1.ports["o1"], name="g_port")
    with pytest.raises(ValueError, match="portname cannot be None"):
        g.connect(port="g_port", other=inst2, other_port_name=None)


def test_instance_group_connect_width_mismatch_raises(
    kcl: kf.KCLayout, layers: Layers
) -> None:
    parent = kcl.kcell()
    c1 = _make_cell(kcl, layers, width=500)
    c2 = _make_cell(kcl, layers, width=1000)
    inst1 = parent << c1
    inst2 = parent << c2
    g = kf.InstanceGroup(insts=[inst1])
    g.add_port(port=inst1.ports["o1"], name="g_port")
    with pytest.raises(PortWidthMismatchError):
        g.connect(
            port="g_port",
            other=inst2,
            other_port_name="o2",
            allow_width_mismatch=False,
        )


def test_instance_group_connect_type_mismatch_raises(
    kcl: kf.KCLayout, layers: Layers
) -> None:
    parent = kcl.kcell()
    c1 = _make_cell(kcl, layers, port_type="optical")
    c2 = _make_cell(kcl, layers, port_type="electrical")
    inst1 = parent << c1
    inst2 = parent << c2
    g = kf.InstanceGroup(insts=[inst1])
    g.add_port(port=inst1.ports["o1"], name="g_port")
    with pytest.raises(PortTypeMismatchError):
        g.connect(
            port="g_port",
            other=inst2,
            other_port_name="o2",
            allow_type_mismatch=False,
        )


def test_instance_group_connect_layer_mismatch_raises(
    kcl: kf.KCLayout, layers: Layers
) -> None:
    parent = kcl.kcell()
    c1 = _make_cell(kcl, layers)
    c2 = kcl.kcell()
    c2.shapes(layers.METAL1).insert(kf.kdb.Box(0, 0, 1000, 1000))
    c2.create_port(
        name="o1",
        trans=kf.kdb.Trans(0, False, 0, 500),
        width=500,
        layer=kcl.find_layer(layers.METAL1),
    )
    inst1 = parent << c1
    inst2 = parent << c2
    g = kf.InstanceGroup(insts=[inst1])
    g.add_port(port=inst1.ports["o1"], name="g_port")
    with pytest.raises(PortLayerMismatchError):
        g.connect(
            port="g_port",
            other=inst2,
            other_port_name="o1",
            allow_layer_mismatch=False,
        )


def test_instance_group_connect_use_mirror_false(
    kcl: kf.KCLayout, layers: Layers
) -> None:
    parent = kcl.kcell()
    c = _make_cell(kcl, layers)
    inst1 = parent << c
    inst2 = parent << c
    g = kf.InstanceGroup(insts=[inst1])
    g.add_port(port=inst1.ports["o1"], name="g_port")
    inst2.transform(kf.kdb.Trans(0, False, 5000, 0))
    g.connect(port="g_port", other=inst2, other_port_name="o2", use_mirror=False)


def test_instance_group_connect_use_angle_false(
    kcl: kf.KCLayout, layers: Layers
) -> None:
    parent = kcl.kcell()
    c = _make_cell(kcl, layers)
    inst1 = parent << c
    inst2 = parent << c
    g = kf.InstanceGroup(insts=[inst1])
    g.add_port(port=inst1.ports["o1"], name="g_port")
    inst2.transform(kf.kdb.Trans(0, False, 5000, 0))
    g.connect(
        port="g_port",
        other=inst2,
        other_port_name="o2",
        use_mirror=False,
        use_angle=False,
    )


def test_instance_group_name(kcl: kf.KCLayout, layers: Layers) -> None:
    parent = kcl.kcell()
    c = _make_cell(kcl, layers)
    inst1 = parent << c
    g = kf.InstanceGroup(insts=[inst1])
    assert "InstanceGroup" in g.name
    assert "InstanceGroup" in str(g)


def test_instance_group_transform_dtrans(kcl: kf.KCLayout, layers: Layers) -> None:
    parent = kcl.kcell()
    c = _make_cell(kcl, layers)
    inst1 = parent << c
    g = kf.InstanceGroup(insts=[inst1])
    g.add_port(port=inst1.ports["o1"], name="g_port")
    g.transform(kf.kdb.DTrans(0.0, False, 1.0, 1.0))  # ty:ignore[invalid-argument-type]


def test_instance_group_transform_icplx(kcl: kf.KCLayout, layers: Layers) -> None:
    parent = kcl.kcell()
    c = _make_cell(kcl, layers)
    inst1 = parent << c
    g = kf.InstanceGroup(insts=[inst1])
    g.add_port(port=inst1.ports["o1"], name="g_port")
    g.transform(kf.kdb.ICplxTrans.R90)


def test_empty_instance_group_kcl_raises(kcl: kf.KCLayout) -> None:
    g = kf.InstanceGroup()
    with pytest.raises(ValueError, match="empty"):
        _ = g.kcl


def test_instance_group_kcl_setter_raises(kcl: kf.KCLayout, layers: Layers) -> None:
    parent = kcl.kcell()
    c = _make_cell(kcl, layers)
    inst1 = parent << c
    g = kf.InstanceGroup(insts=[inst1])
    with pytest.raises(ValueError, match="KCLayout cannot be set"):
        g.kcl = kcl  # ty:ignore[invalid-assignment]
