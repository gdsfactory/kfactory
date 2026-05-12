"""Tests for kfactory.technology.layer_map module."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from ruamel.yaml import YAML

from kfactory.technology.layer_map import (
    LayerGroupModel,
    LayerPropertiesModel,
    LypModel,
    dither2index,
    group2lp,
    index2dither,
    index2line,
    line2index,
    lp2kl,
    lyp_to_lyp_model,
    lyp_to_yaml,
    yaml_to_lyp,
)

if TYPE_CHECKING:
    from pathlib import Path


def test_dither_mappings_consistent() -> None:
    for k, v in dither2index.items():
        assert index2dither[v] == k


def test_line_mappings_consistent() -> None:
    for k, v in line2index.items():
        assert index2line[v] == k


def test_layer_properties_model_defaults() -> None:
    lp = LayerPropertiesModel(name="WG", layer=(1, 0))
    assert lp.name == "WG"
    assert lp.layer == (1, 0)
    assert lp.frame_color is None
    assert lp.fill_color is None
    assert lp.dither_pattern == 1
    assert lp.line_style == 1
    assert lp.visible is True


def test_layer_properties_model_dither_string() -> None:
    lp = LayerPropertiesModel(name="WG", layer=(1, 0), dither_pattern="solid")  # ty:ignore[invalid-argument-type]
    assert lp.dither_pattern == dither2index["solid"]


def test_layer_properties_model_line_style_string() -> None:
    lp = LayerPropertiesModel(name="WG", layer=(1, 0), line_style="dotted")  # ty:ignore[invalid-argument-type]
    assert lp.line_style == line2index["dotted"]


def test_layer_properties_model_color_to_frame_fill() -> None:
    lp = LayerPropertiesModel(name="WG", layer=(1, 0), color="#ff0000")  # ty:ignore[unknown-argument]
    assert lp.frame_color is not None
    assert lp.fill_color is not None


def test_layer_properties_model_color_overrides() -> None:
    # If explicit fill/frame are provided, the shorthand "color" doesn't override
    lp = LayerPropertiesModel(
        name="WG",
        layer=(1, 0),
        color="#ff0000",  # ty:ignore[unknown-argument]
        fill_color="#00ff00",  # ty:ignore[invalid-argument-type]
        frame_color="#0000ff",  # ty:ignore[invalid-argument-type]
    )
    assert lp.fill_color is not None
    assert lp.fill_color.as_hex().startswith("#0")
    assert lp.frame_color is not None


def test_layer_properties_model_serializes_dither() -> None:
    lp = LayerPropertiesModel(name="WG", layer=(1, 0), dither_pattern=0)
    dumped = lp.model_dump()
    assert dumped["dither_pattern"] == index2dither[0]


def test_layer_properties_model_serializes_line_style() -> None:
    lp = LayerPropertiesModel(name="WG", layer=(1, 0), line_style=0)
    dumped = lp.model_dump()
    assert dumped["line_style"] == index2line[0]


def test_layer_group_model_nesting() -> None:
    leaf = LayerPropertiesModel(name="WG", layer=(1, 0))
    inner = LayerGroupModel(name="inner", members=[leaf])
    outer = LayerGroupModel(name="outer", members=[inner, leaf])
    assert len(outer.members) == 2
    assert isinstance(outer.members[0], LayerGroupModel)


def test_lyp_model_with_groups_and_leaves() -> None:
    leaf = LayerPropertiesModel(name="WG", layer=(1, 0))
    group = LayerGroupModel(name="g", members=[leaf])
    m = LypModel(layers=[leaf, group])
    assert len(m.layers) == 2


def test_lp2kl_no_colors() -> None:
    lp = LayerPropertiesModel(name="WG", layer=(1, 0))
    kl = lp2kl(lp)
    assert "1/0" in kl.source


def test_lp2kl_no_layer_to_name() -> None:
    lp = LayerPropertiesModel(name="WG", layer=(1, 0), layer_to_name=False)
    kl = lp2kl(lp)
    assert kl.name == "WG"


def test_lp2kl_with_layer_to_name() -> None:
    lp = LayerPropertiesModel(name="WG", layer=(1, 0), layer_to_name=True)
    kl = lp2kl(lp)
    assert "1/0" in kl.name


def test_lp2kl_with_colors() -> None:
    lp = LayerPropertiesModel(
        name="WG",
        layer=(1, 0),
        frame_color="#abcdef",  # ty:ignore[invalid-argument-type]
        fill_color="#123456",  # ty:ignore[invalid-argument-type]
    )
    kl = lp2kl(lp)
    # KLayout may store with alpha bits; compare only the low 24 bits
    assert kl.frame_color & 0xFFFFFF == int("abcdef", 16)
    assert kl.fill_color & 0xFFFFFF == int("123456", 16)


def test_lp2kl_with_short_hex_colors() -> None:
    # Pydantic Color may normalize "#fff" -> a long form. Force short by using e.g. red.
    lp = LayerPropertiesModel(
        name="WG",
        layer=(1, 0),
        frame_color="red",  # ty:ignore[invalid-argument-type]
        fill_color="red",  # ty:ignore[invalid-argument-type]
    )
    kl = lp2kl(lp)
    assert kl.frame_color > 0
    assert kl.fill_color > 0


def test_group2lp_nested() -> None:
    leaf1 = LayerPropertiesModel(name="WG", layer=(1, 0))
    leaf2 = LayerPropertiesModel(name="M1", layer=(2, 0))
    sub = LayerGroupModel(name="subgroup", members=[leaf2])
    group = LayerGroupModel(name="g", members=[leaf1, sub])
    kl = group2lp(group)
    assert kl.name == "g"


def _build_yaml_file(path: Path) -> None:
    data = {
        "layers": [
            {"name": "WG", "layer": [1, 0], "color": "#ff0000"},
            {
                "name": "G",
                "members": [
                    {"name": "M1", "layer": [2, 0]},
                ],
            },
        ]
    }
    yaml = YAML()
    with path.open("w") as f:
        yaml.dump(data, f)


def test_yaml_to_lyp_and_back(tmp_path: Path) -> None:
    yaml_in = tmp_path / "in.yaml"
    lyp_out = tmp_path / "out.lyp"
    yaml_round = tmp_path / "round.yaml"
    _build_yaml_file(yaml_in)
    yaml_to_lyp(yaml_in, lyp_out)
    assert lyp_out.exists()

    model = lyp_to_lyp_model(lyp_out)
    assert isinstance(model, LypModel)
    assert len(model.layers) >= 1

    lyp_to_yaml(lyp_out, yaml_round)
    assert yaml_round.exists()


def test_yaml_to_lyp_missing_input(tmp_path: Path) -> None:
    bad = tmp_path / "does_not_exist.yaml"
    with pytest.raises(AssertionError):
        yaml_to_lyp(bad, tmp_path / "out.lyp")


def test_lyp_to_lyp_model_missing_input(tmp_path: Path) -> None:
    with pytest.raises(AssertionError):
        lyp_to_lyp_model(tmp_path / "missing.lyp")
