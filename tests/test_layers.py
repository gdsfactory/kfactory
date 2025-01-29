import pytest
from conftest import Layers
from pydantic import ValidationError

import kfactory as kf


def test_layer_infos_valid() -> None:
    layer_info = kf.LayerInfos(
        layer1=kf.kdb.LayerInfo(1, 0),
        layer2=kf.kdb.LayerInfo(2, 0),
    )
    assert layer_info.layer1.layer == 1
    assert layer_info.layer1.datatype == 0
    assert layer_info.layer2.layer == 2
    assert layer_info.layer2.datatype == 0


def test_layer_infos_invalid_type() -> None:
    with pytest.raises(
        ValidationError,
        match="All fields in LayerInfos must be of type kdb.LayerInfo.",
    ):
        kf.LayerInfos(layer1="invalid_layer_info")


def test_layer_infos_missing_layer() -> None:
    with pytest.raises(
        ValidationError,
        match="Layers must specify layer number and datatype.",
    ):
        kf.LayerInfos(layer1=kf.kdb.LayerInfo(-1, 0))


def test_layer_infos_missing_datatype() -> None:
    with pytest.raises(
        ValidationError,
        match="Layers must specify layer number and datatype.",
    ):
        kf.LayerInfos(layer1=kf.kdb.LayerInfo(1, -1))


def test_layer_infos_named_layer() -> None:
    layer_info = kf.LayerInfos(layer1=kf.kdb.LayerInfo(1, 0, name="Layer1"))
    assert layer_info.layer1.name == "layer1"  # type: ignore[attr-defined]


def test_layer_infos_unnamed_layer() -> None:
    layer_info = kf.LayerInfos(layer1=kf.kdb.LayerInfo(1, 0))
    assert layer_info.layer1.name == "layer1"  # type: ignore[attr-defined]


def test_layer_enum_creation(LAYER: Layers) -> None:
    layer_enum = kf.layer.layerenum_from_dict(name="LAYER", layers=LAYER)
    assert layer_enum.WG.layer == 1
    assert layer_enum.WG.datatype == 0


def test_layer_enum_str(LAYER: Layers) -> None:
    layer_enum = kf.layer.layerenum_from_dict(name="LAYER", layers=LAYER)
    assert str(layer_enum.WG) == "WG"


def test_layer_enum_getitem(LAYER: Layers) -> None:
    layer_enum = kf.layer.layerenum_from_dict(name="LAYER", layers=LAYER)
    assert layer_enum["WG"][0] == 1  # type: ignore[index]
    assert layer_enum["WG"][1] == 0  # type: ignore[index]


def test_layer_enum_len(LAYER: Layers) -> None:
    layer_enum = kf.layer.layerenum_from_dict(name="LAYER", layers=LAYER)
    assert len(layer_enum) == 7  # type: ignore[arg-type]


def test_layer_enum_iter(LAYER: Layers) -> None:
    layer_enum = kf.layer.layerenum_from_dict(name="LAYER", layers=LAYER)
    values = list(layer_enum.WG)
    assert values == [1, 0]


def test_layer_enum_invalid_index(LAYER: Layers) -> None:
    layer_enum = kf.layer.layerenum_from_dict(name="LAYER", layers=LAYER)
    with pytest.raises(ValueError):
        layer_enum["WG"][2]  # type: ignore[index]


if __name__ == "__main__":
    pytest.main(["-v", __file__])
