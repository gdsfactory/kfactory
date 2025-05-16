import pytest
from pydantic import ValidationError

from kfactory.kcell import Info, KCellSettings, KCellSettingsUnits


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


def test_info_update() -> None:
    info = Info(key1=42)
    info.update({"key1": 100, "key2": "new_value"})
    assert info["key1"] == 100
    assert info["key2"] == "new_value"


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


if __name__ == "__main__":
    test_info_restrict_types()
