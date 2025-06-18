import pytest
from pydantic import ValidationError

import kfactory as kf
from tests.conftest import Layers


def test_layer_infos_valid() -> None:
    layer_info = kf.LayerInfos(
        layer1=kf.kdb.LayerInfo(1, 0), layer2=kf.kdb.LayerInfo(2, 0)
    )
    assert layer_info.layer1.layer == 1
    assert layer_info.layer1.datatype == 0
    assert layer_info.layer2.layer == 2
    assert layer_info.layer2.datatype == 0


def test_layer_infos_invalid_type() -> None:
    with pytest.raises(
        ValidationError,
        match=r"All fields in LayerInfos must be of type kdb.LayerInfo.",
    ):
        kf.LayerInfos(layer1="invalid_layer_info")


def test_layer_infos_missing_layer() -> None:
    with pytest.raises(
        ValidationError,
        match=r"Layers must specify layer number and datatype.",
    ):
        kf.LayerInfos(layer1=kf.kdb.LayerInfo(-1, 0))


def test_layer_infos_missing_datatype() -> None:
    with pytest.raises(
        ValidationError,
        match=r"Layers must specify layer number and datatype.",
    ):
        kf.LayerInfos(layer1=kf.kdb.LayerInfo(1, -1))


def test_layer_infos_named_layer() -> None:
    layer_info = kf.LayerInfos(layer1=kf.kdb.LayerInfo(1, 0, name="Layer1"))
    assert layer_info.layer1.name == "Layer1"  # type: ignore[attr-defined]


def test_layer_infos_unnamed_layer() -> None:
    layer_info = kf.LayerInfos(layer1=kf.kdb.LayerInfo(1, 0))
    assert layer_info.layer1.name == "layer1"  # type: ignore[attr-defined]


def test_layer_enum_creation(layers: Layers) -> None:
    layer_enum = kf.layer.layerenum_from_dict(name="LAYER", layers=layers)
    assert layer_enum.WG.layer == 1
    assert layer_enum.WG.datatype == 0


def test_layer_enum_str(layers: Layers) -> None:
    layer_enum = kf.layer.layerenum_from_dict(name="LAYER", layers=layers)
    assert str(layer_enum.WG) == "WG"


def test_layer_enum_getitem(layers: Layers) -> None:
    layer_enum = kf.layer.layerenum_from_dict(name="LAYER", layers=layers)
    assert layer_enum["WG"][0] == 1  # type: ignore[index]
    assert layer_enum["WG"][1] == 0  # type: ignore[index]


def test_layer_enum_len(layers: Layers) -> None:
    layer_enum = kf.layer.layerenum_from_dict(name="LAYER", layers=layers)
    assert len(layer_enum) == 15  # type: ignore[arg-type]


def test_layer_enum_iter(layers: Layers) -> None:
    layer_enum = kf.layer.layerenum_from_dict(name="LAYER", layers=layers)
    values = list(layer_enum.WG)
    assert values == [1, 0]


def test_layer_enum_invalid_index(layers: Layers) -> None:
    layer_enum = kf.layer.layerenum_from_dict(name="LAYER", layers=layers)
    with pytest.raises(ValueError):
        layer_enum["WG"][2]  # type: ignore[index]


def test_layer_stack(pdk: kf.KCLayout) -> None:
    assert pdk.layer_stack.to_dict().keys() == {"wg", "clad"}
    with pytest.raises(KeyError):
        pdk.layer_stack["invalid"]


if __name__ == "__main__":
    pytest.main(["-s", __file__])
