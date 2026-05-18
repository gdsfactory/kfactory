import pytest
from pydantic import BaseModel, ValidationError

from kfactory.settings import Info, KCellSettings, KCellSettingsUnits


def test_kcell_settings_initialization() -> None:
    settings = KCellSettings(param1=42, param2="test")
    assert settings.param1 == 42
    assert settings.param2 == "test"
    assert settings.get("param1") == 42


def test_kcell_settings_getitem() -> None:
    settings = KCellSettings(param1=42)
    assert settings["param1"] == 42


def test_kcell_settings_contains() -> None:
    settings = KCellSettings(param1=42)
    assert "param1" in settings
    assert "param2" not in settings


def test_kcell_settings_units_initialization() -> None:
    units = KCellSettingsUnits(unit1="nm", unit2="um")
    assert units.unit1 == "nm"
    assert units.unit2 == "um"
    assert units.get("unit1") == "nm"


def test_kcell_settings_units_getitem() -> None:
    units = KCellSettingsUnits(unit1="nm")
    assert units["unit1"] == "nm"


def test_kcell_settings_units_contains() -> None:
    units = KCellSettingsUnits(unit1="nm")
    assert "unit1" in units
    assert "unit2" not in units


def test_info_initialization() -> None:
    info = Info(key1=42, key2="value")
    assert info.key1 == 42
    assert info.key2 == "value"
    assert info.get("key1") == 42


def test_info_getitem() -> None:
    info = Info(key1=42)
    assert info["key1"] == 42


def test_info_setitem() -> None:
    info = Info(key1=42)
    info["key1"] = 100
    assert info["key1"] == 100


def test_info_setitem_rejects_bad_type() -> None:
    info = Info(key1=42)
    with pytest.raises(ValueError, match=r"^Values of the info dict only support"):
        info["bad"] = object()  # ty:ignore[invalid-assignment]
    with pytest.raises(ValueError, match=r"^Values of the info dict only support"):
        info["bad"] = [object()]  # ty:ignore[invalid-assignment]
    assert "bad" not in info


def test_info_setitem_does_not_corrupt_existing_keys() -> None:
    """Regression for gdsfactory/kfactory#944.

    Setting a second key must not silently mutate values stored under
    earlier keys.
    """
    info = Info()
    info["my_data"] = [1, 2, 3]
    info["nested"] = {"a": (4, 5), "b": [6, 7]}
    info["unrelated"] = "hello"
    assert info["my_data"] == [1, 2, 3]
    assert info["nested"] == {"a": (4, 5), "b": [6, 7]}
    assert info["unrelated"] == "hello"


def test_info_rejects_basemodel_in_list() -> None:
    """Exact reproducer from gdsfactory/kfactory#944."""

    class MyModel(BaseModel):
        name: str = "important"
        value: int = 42

    info = Info()
    with pytest.raises(ValueError, match=r"^Values of the info dict only support"):
        info["my_data"] = [MyModel()]  # ty:ignore[invalid-assignment]
    assert "my_data" not in info


def test_info_update() -> None:
    info = Info(key1=42)
    info.update({"key1": 100, "key2": "new_value"})
    assert info["key1"] == 100
    assert info["key2"] == "new_value"


def test_info_update_rejects_bad_type() -> None:
    info = Info(key1=42)
    with pytest.raises(ValueError, match=r"^Values of the info dict only support"):
        info.update({"bad": object()})  # ty:ignore[invalid-argument-type]
    with pytest.raises(ValueError, match=r"^Values of the info dict only support"):
        info.update({"nested_bad": [{"deeper": object()}]})  # ty:ignore[invalid-argument-type]


def test_info_contains() -> None:
    info = Info(key1=42)
    assert "key1" in info
    assert "key2" not in info


def test_info_add() -> None:
    info = Info(key1=42)
    info = info + Info(key2="value")
    assert info.key1 == 42
    assert info.key2 == "value"


def test_info_iadd() -> None:
    info = Info(key1=42)
    info += Info(key2="value")
    assert info.key1 == 42
    assert info.key2 == "value"


def test_info_restrict_types() -> None:
    valid_data = Info(key1=42, key2="value", key3=[1, 2, 3])
    assert valid_data.key1 == 42
    assert valid_data.key2 == "value"
    assert valid_data.key3 == [1, 2, 3]

    with pytest.raises(ValidationError):
        Info(key1={1, 2, 3})

    info_with_none = Info(key1=None)
    assert info_with_none.key1 is None

    nested_data = Info(key1={"subkey": "subvalue"}, key2=(1, 2))
    assert nested_data.key1["subkey"] == "subvalue"
    assert nested_data.key2 == (1, 2)


def test_info_str() -> None:
    info = Info(key1=42)
    assert str(info) == "Info(key1=42)"


def test_settings_str() -> None:
    settings = KCellSettings(param1=42)
    assert str(settings) == "KCellSettings(param1=42)"


def test_info_normalises_length_props_to_float() -> None:
    """``length``-like Info props are coerced to ``float`` to keep META
    bytes stable across call-order-sensitive cache hits.

    Repro for the upstream issue: gdsfactory's ``@cell`` cache hashes
    kwargs by value (``4 == 4.0``), so calling ``foo(length=4)`` and
    ``bar(length=4.0)`` in the same process collapses onto whichever
    Python type came first. The cached cell's ``info`` then serialises
    the wrong type into the ``kfactory:info`` PROPVALUE (``#l4`` vs
    ``##4``), producing a different GDS byte-stream depending on call
    order. Normalising these props eliminates the discrepancy.
    """
    a = Info(length=4)
    b = Info(length=4.0)
    assert a.length == b.length
    assert isinstance(a.length, float)
    assert isinstance(b.length, float)

    # Other route_info_* length/weight props too — they all carry the
    # same length value through gdsfactory's straight() factory.
    info = Info(
        length=4,
        route_info_length=4,
        route_info_weight=4,
        route_info_strip_length=4,
        route_info_metal3_length=4,
    )
    assert isinstance(info.length, float)
    assert isinstance(info.route_info_length, float)
    assert isinstance(info.route_info_weight, float)
    assert isinstance(info.route_info_strip_length, float)
    assert isinstance(info.route_info_metal3_length, float)


def test_info_preserves_int_for_non_length_props() -> None:
    """Only the length/weight allow-list is coerced. Other int values
    (counts, indices, etc.) keep their Python type.
    """
    info = Info(npoints=12, channels=3, layer=4)
    assert info.npoints == 12 and isinstance(info.npoints, int)
    assert info.channels == 3 and isinstance(info.channels, int)
    assert info.layer == 4 and isinstance(info.layer, int)


def test_info_preserves_bool_on_length_key() -> None:
    """``bool`` inherits from ``int`` but carries semantic meaning, so
    even if the key is in the normalise list, a bool stays a bool.
    """
    info = Info(length=True)
    assert info.length is True


def test_info_setitem_coerces_length() -> None:
    """Per-key assignment (``Info.__setattr__``/``__setitem__``) runs the
    same coercion as construction.
    """
    info = Info()
    info["length"] = 4
    assert isinstance(info["length"], float)
    info.length = 5
    assert isinstance(info.length, float)


def test_kcell_settings_does_not_coerce_length() -> None:
    """Coercion is scoped to ``Info``. ``KCellSettings`` keeps the
    caller's Python type — its values are read back by user code (e.g.
    Schematic netlist comparisons) where ``int`` vs ``float`` semantics
    matter.
    """
    s = KCellSettings(length=4)
    assert s.length == 4 and isinstance(s.length, int)
