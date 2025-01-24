import pytest

import kfactory as kf


@kf.cell
def unnamed_dkcell(name: str = "a") -> kf.DKCell:
    c = kf.kcl.dkcell(name)
    return c


def test_unnamed_dkcell() -> None:
    c1 = unnamed_dkcell("test_unnamed_dkcell")
    c2 = unnamed_dkcell("test_unnamed_dkcell")
    assert c1 is c2


@kf.cell
def nested_list_dict_dkcell(
    arg1: dict[str, list[dict[str, str | int] | int] | int],
) -> kf.DKCell:
    c = kf.kcl.dkcell("test_nested_list_dict_dkcell")
    return c


def test_nested_dict_list_dkcell() -> None:
    dl: dict[str, list[dict[str, str | int] | int] | int] = {
        "a": 5,
        "b": [5, {"c": "d", "e": 6}],
    }
    c = nested_list_dict_dkcell(dl)
    assert dl == c.settings["arg1"]
    assert dl is not c.settings["arg1"]


def test_dkcell_ports() -> None:
    c = kf.kcl.dkcell("test_dkcell_ports")
    assert isinstance(c.ports, kf.DPorts)
    assert list(c.ports) == []
    p = c.create_port(width=1, layer=1, center=(0, 0), angle=90)
    assert p in c.ports
    assert c.ports == [p]


def test_dkcell_locked() -> None:
    c = kf.kcl.dkcell("test_dkcell_locked")
    assert c.locked is False
    c._base_kcell.locked = True
    assert c.locked is True
    with pytest.raises(kf.kcell.LockedError):
        c.ports = []

    with pytest.raises(kf.kcell.LockedError):
        c.create_port(width=1, layer=1, center=(0, 0), angle=90)


if __name__ == "__main__":
    pytest.main([__file__])
