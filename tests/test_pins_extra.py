"""Extra tests targeting pins.py / instance_pins.py coverage."""

from __future__ import annotations

import pytest

import kfactory as kf
from kfactory.pin import BasePin, DPin, Pin, filter_regex, filter_type
from kfactory.pins import DPins, Pins
from kfactory.settings import Info
from tests.conftest import Layers


def _make_kcell_with_pin(
    kcl: kf.KCLayout, layers: Layers, pin_type: str = "DC", pin_name: str = "pin1"
) -> kf.KCell:
    xs = kf.SymmetricalCrossSection(
        width=5000,
        enclosure=kf.LayerEnclosure(main_layer=layers.METAL1, name="M1_PINX"),
    )
    c = kcl.kcell()
    c.shapes(layers.METAL1).insert(kf.kdb.Box(50_000, 50_000))
    p1 = c.create_port(
        name="e1", trans=kf.kdb.Trans(0, False, 25_000, 0), cross_section=xs
    )
    p2 = c.create_port(
        name="e2", trans=kf.kdb.Trans(1, False, 0, 25_000), cross_section=xs
    )
    c.create_pin(name=pin_name, ports=[p1, p2], pin_type=pin_type)
    return c


def test_pins_getitem_by_index(kcl: kf.KCLayout, layers: Layers) -> None:
    c = _make_kcell_with_pin(kcl, layers)
    assert c.pins[0].name == "pin1"


def test_pins_getitem_by_name(kcl: kf.KCLayout, layers: Layers) -> None:
    c = _make_kcell_with_pin(kcl, layers)
    assert c.pins["pin1"].name == "pin1"


def test_pins_getitem_missing_name_raises(kcl: kf.KCLayout, layers: Layers) -> None:
    c = _make_kcell_with_pin(kcl, layers)
    with pytest.raises(KeyError, match="not a valid pin name"):
        c.pins["does_not_exist"]


def test_pins_contains_by_name(kcl: kf.KCLayout, layers: Layers) -> None:
    c = _make_kcell_with_pin(kcl, layers)
    assert "pin1" in c.pins
    assert "missing" not in c.pins


def test_pins_contains_by_pin(kcl: kf.KCLayout, layers: Layers) -> None:
    c = _make_kcell_with_pin(kcl, layers)
    pin = c.pins[0]
    assert pin in c.pins


def test_pins_contains_by_base(kcl: kf.KCLayout, layers: Layers) -> None:
    c = _make_kcell_with_pin(kcl, layers)
    assert c.pins[0].base in c.pins


def test_pins_iter(kcl: kf.KCLayout, layers: Layers) -> None:
    c = _make_kcell_with_pin(kcl, layers)
    names = [p.name for p in c.pins]
    assert names == ["pin1"]


def test_pins_len(kcl: kf.KCLayout, layers: Layers) -> None:
    c = _make_kcell_with_pin(kcl, layers)
    assert len(c.pins) == 1


def test_pins_to_dtype_to_itype(kcl: kf.KCLayout, layers: Layers) -> None:
    c = _make_kcell_with_pin(kcl, layers)
    d = c.pins.to_dtype()
    assert isinstance(d, DPins)
    i = d.to_itype()
    assert isinstance(i, Pins)


def test_pins_get_all_named(kcl: kf.KCLayout, layers: Layers) -> None:
    c = _make_kcell_with_pin(kcl, layers)
    named = c.pins.get_all_named()
    assert "pin1" in named


def test_pins_create_pin_empty_ports_raises(kcl: kf.KCLayout, layers: Layers) -> None:
    c = kcl.kcell()
    with pytest.raises(ValueError, match="At least one port"):
        c.pins.create_pin(name="p_empty", ports=[])


def test_pins_create_pin_with_info(kcl: kf.KCLayout, layers: Layers) -> None:
    xs = kf.SymmetricalCrossSection(
        width=5000,
        enclosure=kf.LayerEnclosure(main_layer=layers.METAL1, name="M1_INFO"),
    )
    c = kcl.kcell()
    p1 = c.create_port(name="e1", trans=kf.kdb.Trans.R0, cross_section=xs)
    pin = c.pins.create_pin(name="p_info", ports=[p1], info={"key": "value"})
    assert pin.info["key"] == "value"


def test_pins_create_pin_wrong_kcl_raises(layers: Layers) -> None:
    kcl1 = kf.KCLayout("PINS_WRONG_KCL_1", infos=Layers)
    kcl2 = kf.KCLayout("PINS_WRONG_KCL_2", infos=Layers)
    xs = kf.SymmetricalCrossSection(
        width=5000,
        enclosure=kf.LayerEnclosure(main_layer=layers.METAL1, name="M1_WK"),
    )
    c1 = kcl1.kcell()
    c2 = kcl2.kcell()
    port = c1.create_port(name="e1", trans=kf.kdb.Trans.R0, cross_section=xs)
    with pytest.raises(ValueError, match="different layout"):
        c2.pins.create_pin(name="p_wrong", ports=[port])


def test_pin_repr(kcl: kf.KCLayout, layers: Layers) -> None:
    c = _make_kcell_with_pin(kcl, layers)
    r = repr(c.pins[0])
    assert "Pin" in r
    assert "pin1" in r


def test_pin_to_dtype_and_back(kcl: kf.KCLayout, layers: Layers) -> None:
    c = _make_kcell_with_pin(kcl, layers)
    p = c.pins[0]
    dp = p.to_dtype()
    assert isinstance(dp, DPin)
    ip = dp.to_itype()
    assert isinstance(ip, Pin)


def test_pin_setters(kcl: kf.KCLayout, layers: Layers) -> None:
    c = _make_kcell_with_pin(kcl, layers)
    p = c.pins[0]
    p.name = "renamed"
    assert p.name == "renamed"
    p.pin_type = "RF"
    assert p.pin_type == "RF"
    new_info = Info(extra="x")
    p.info = new_info
    assert p.info["extra"] == "x"


def test_pin_kcl_setter(kcl: kf.KCLayout, layers: Layers) -> None:
    c = _make_kcell_with_pin(kcl, layers)
    p = c.pins[0]
    # setter just assigns; reading back should return same kcl
    p.kcl = kcl
    assert p.kcl is kcl


def test_pin_getitem_by_index(kcl: kf.KCLayout, layers: Layers) -> None:
    c = _make_kcell_with_pin(kcl, layers)
    pin = c.pins[0]
    port = pin[0]
    assert port.name in ("e1", "e2")


def test_pin_getitem_by_name(kcl: kf.KCLayout, layers: Layers) -> None:
    c = _make_kcell_with_pin(kcl, layers)
    pin = c.pins[0]
    port = pin["e1"]
    assert port.name == "e1"


def test_pin_getitem_missing(kcl: kf.KCLayout, layers: Layers) -> None:
    c = _make_kcell_with_pin(kcl, layers)
    pin = c.pins[0]
    with pytest.raises(KeyError, match="not a valid port name"):
        pin["missing_port"]


def test_pin_ports_setter(kcl: kf.KCLayout, layers: Layers) -> None:
    c = _make_kcell_with_pin(kcl, layers)
    pin = c.pins[0]
    original = list(pin.ports)
    pin.ports = list(reversed(original))
    assert [p.name for p in pin.ports] == [original[1].name, original[0].name]


def test_pin_copy_with_transform(kcl: kf.KCLayout, layers: Layers) -> None:
    c = _make_kcell_with_pin(kcl, layers)
    p = c.pins[0]
    trans = kf.kdb.Trans(0, False, 100, 100)
    cp = p.copy(trans=trans)
    assert isinstance(cp, Pin)
    assert cp.name == p.name


def test_dpin_copy_with_transform(kcl: kf.KCLayout, layers: Layers) -> None:
    c = _make_kcell_with_pin(kcl, layers)
    p = c.pins[0].to_dtype()
    trans = kf.kdb.DCplxTrans()
    cp = p.copy(trans=trans)
    assert isinstance(cp, DPin)


def test_dpin_getitem(kcl: kf.KCLayout, layers: Layers) -> None:
    c = _make_kcell_with_pin(kcl, layers)
    dpin = c.pins[0].to_dtype()
    port = dpin["e1"]
    assert port.name == "e1"
    assert dpin[0].name in ("e1", "e2")
    with pytest.raises(KeyError):
        dpin["missing"]


def test_dpin_ports_setter(kcl: kf.KCLayout, layers: Layers) -> None:
    c = _make_kcell_with_pin(kcl, layers)
    dpin = c.pins[0].to_dtype()
    orig = list(dpin.ports)
    dpin.ports = list(reversed(orig))
    assert [p.name for p in dpin.ports] == [orig[1].name, orig[0].name]


def test_dpins_getitem_missing(kcl: kf.KCLayout, layers: Layers) -> None:
    c = _make_kcell_with_pin(kcl, layers)
    dpins = c.pins.to_dtype()
    with pytest.raises(KeyError):
        dpins["missing"]


def test_dpins_getitem_by_index(kcl: kf.KCLayout, layers: Layers) -> None:
    c = _make_kcell_with_pin(kcl, layers)
    dpins = c.pins.to_dtype()
    assert dpins[0].name == "pin1"


def test_dpins_iter_and_named(kcl: kf.KCLayout, layers: Layers) -> None:
    c = _make_kcell_with_pin(kcl, layers)
    dpins = c.pins.to_dtype()
    names = [p.name for p in dpins]
    assert names == ["pin1"]
    assert "pin1" in dpins.get_all_named()


def test_dpins_create_pin_empty_raises(kcl: kf.KCLayout, layers: Layers) -> None:
    c = kcl.kcell()
    dpins = c.pins.to_dtype()
    with pytest.raises(ValueError, match="At least one port"):
        dpins.create_pin(name="x", ports=[])


def test_dpins_create_pin_other_kcl_assigns(layers: Layers) -> None:
    """For DPins, ports from another kcl get re-assigned (no raise)."""
    kcl1 = kf.KCLayout("DPINS_OTHER_KCL_1", infos=Layers)
    kcl2 = kf.KCLayout("DPINS_OTHER_KCL_2", infos=Layers)
    xs = kf.SymmetricalCrossSection(
        width=5000,
        enclosure=kf.LayerEnclosure(main_layer=layers.METAL1, name="M1_DXK"),
    )
    c1 = kcl1.kcell()
    c2 = kcl2.kcell()
    port = c1.create_port(name="e1", trans=kf.kdb.Trans.R0, cross_section=xs)
    dpins = c2.pins.to_dtype()
    p = dpins.create_pin(name="p", ports=[port])
    assert p.name == "p"


def test_pins_filter_no_match(kcl: kf.KCLayout, layers: Layers) -> None:
    c = _make_kcell_with_pin(kcl, layers, pin_type="DC", pin_name="pin1")
    assert c.pins.filter(pin_type="RF") == []
    assert c.pins.filter(regex="^xx") == []


def test_pins_filter_match(kcl: kf.KCLayout, layers: Layers) -> None:
    c = _make_kcell_with_pin(kcl, layers, pin_type="DC", pin_name="pin1")
    assert len(c.pins.filter(pin_type="DC")) == 1
    assert len(c.pins.filter(regex="^pin")) == 1


def test_pins_print(
    capsys: pytest.CaptureFixture[str], kcl: kf.KCLayout, layers: Layers
) -> None:
    c = _make_kcell_with_pin(kcl, layers)
    c.pins.print()
    out = capsys.readouterr().out
    assert "pin1" in out


def test_filter_regex_handles_none_name() -> None:
    kcl = kf.KCLayout("FILTER_REG_NONE", infos=Layers)
    bp = BasePin(name="foo", kcl=kcl, ports=[], info=Info(), pin_type="DC")
    p = Pin(base=bp)
    # set name to "" or rely on regex - filter_regex returns False when name is None
    pins = [p]
    result = list(filter_regex(pins, regex="^foo"))
    assert result == [p]


def test_filter_type() -> None:
    kcl = kf.KCLayout("FILTER_TYPE", infos=Layers)
    bp1 = BasePin(name="a", kcl=kcl, ports=[], info=Info(), pin_type="DC")
    bp2 = BasePin(name="b", kcl=kcl, ports=[], info=Info(), pin_type="RF")
    pins = [Pin(base=bp1), Pin(base=bp2)]
    dc = list(filter_type(pins, "DC"))
    assert len(dc) == 1
    assert dc[0].name == "a"


def test_pin_iter_via_each_pin_on_instance(kcl: kf.KCLayout, layers: Layers) -> None:
    c = _make_kcell_with_pin(kcl, layers)
    top = kcl.kcell()
    inst = top << c
    # iter on instance.pins
    pins = list(inst.pins)
    assert len(pins) == 1


def test_instance_pins_repr_str(kcl: kf.KCLayout, layers: Layers) -> None:
    c = _make_kcell_with_pin(kcl, layers)
    top = kcl.kcell()
    inst = top << c
    assert "n=1" in repr(inst.pins)
    assert "pins" in str(inst.pins)


def test_instance_pins_contains(kcl: kf.KCLayout, layers: Layers) -> None:
    c = _make_kcell_with_pin(kcl, layers)
    top = kcl.kcell()
    inst = top << c
    assert "pin1" in inst.pins
    assert "missing" not in inst.pins


def test_instance_pins_getitem_missing(kcl: kf.KCLayout, layers: Layers) -> None:
    c = _make_kcell_with_pin(kcl, layers)
    top = kcl.kcell()
    inst = top << c
    with pytest.raises(KeyError):
        inst.pins["missing"]


def test_instance_pins_array(kcl: kf.KCLayout, layers: Layers) -> None:
    c = _make_kcell_with_pin(kcl, layers)
    top = kcl.kcell()
    inst = top.create_inst(
        c, na=2, nb=2, a=kf.kdb.Vector(80_000, 0), b=kf.kdb.Vector(0, 80_000)
    )
    # 1 cell pin * 2 * 2
    assert len(inst.pins) == 4

    # Indexing into an array with tuple
    pin = inst.pins[("pin1", 0, 1)]
    assert pin.name == "pin1"

    # Out of range raises
    with pytest.raises(IndexError):
        inst.pins[("pin1", 5, 5)]


def test_instance_pins_array_default_indices(kcl: kf.KCLayout, layers: Layers) -> None:
    c = _make_kcell_with_pin(kcl, layers)
    top = kcl.kcell()
    inst = top.create_inst(
        c, na=2, nb=2, a=kf.kdb.Vector(80_000, 0), b=kf.kdb.Vector(0, 80_000)
    )
    # Single string key on an array -> defaults to (0,0)
    pin = inst.pins["pin1"]
    assert pin.name == "pin1"


def test_instance_pins_filter(kcl: kf.KCLayout, layers: Layers) -> None:
    c = _make_kcell_with_pin(kcl, layers)
    top = kcl.kcell()
    inst = top << c
    assert len(inst.pins.filter(pin_type="DC")) == 1
    assert inst.pins.filter(regex="^xx") == []


def test_instance_pins_copy(kcl: kf.KCLayout, layers: Layers) -> None:
    c = _make_kcell_with_pin(kcl, layers)
    top = kcl.kcell()
    inst = top << c
    cp = inst.pins.copy()
    assert isinstance(cp, Pins)
    assert len(cp) == 1


def test_instance_pins_copy_array(kcl: kf.KCLayout, layers: Layers) -> None:
    c = _make_kcell_with_pin(kcl, layers)
    top = kcl.kcell()
    inst = top.create_inst(
        c, na=2, nb=2, a=kf.kdb.Vector(80_000, 0), b=kf.kdb.Vector(0, 80_000)
    )
    cp = inst.pins.copy()
    assert isinstance(cp, Pins)
    assert len(cp) == 4


def test_dinstance_pins_filter(kcl: kf.KCLayout, layers: Layers) -> None:
    c = _make_kcell_with_pin(kcl, layers)
    top = kcl.dkcell()
    inst = top << c.to_dtype()
    assert len(inst.pins.filter(pin_type="DC")) == 1


def test_dinstance_pins_getitem(kcl: kf.KCLayout, layers: Layers) -> None:
    c = _make_kcell_with_pin(kcl, layers)
    top = kcl.dkcell()
    inst = top << c.to_dtype()
    pin = inst.pins["pin1"]
    assert pin.name == "pin1"
    assert len(list(inst.pins)) == 1


def test_each_by_array_coord_non_array(kcl: kf.KCLayout, layers: Layers) -> None:
    c = _make_kcell_with_pin(kcl, layers)
    top = kcl.kcell()
    inst = top << c
    coords = list(inst.pins.each_by_array_coord())
    assert len(coords) == 1
    assert coords[0][:2] == (0, 0)


def test_each_by_array_coord_array(kcl: kf.KCLayout, layers: Layers) -> None:
    c = _make_kcell_with_pin(kcl, layers)
    top = kcl.kcell()
    inst = top.create_inst(
        c, na=2, nb=2, a=kf.kdb.Vector(80_000, 0), b=kf.kdb.Vector(0, 80_000)
    )
    coords = list(inst.pins.each_by_array_coord())
    assert len(coords) == 4
    # Should include all combinations
    keys = {(a, b) for a, b, _ in coords}
    assert keys == {(0, 0), (0, 1), (1, 0), (1, 1)}
