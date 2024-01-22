"""Utilities to go lyp <-> yaml."""
from __future__ import annotations

import pathlib
from json import loads
from typing import Any

from pydantic import BaseModel, field_validator, model_validator
from pydantic.color import Color
from pydantic.functional_serializers import field_serializer
from ruamel.yaml import YAML

from .. import lay


class LayerPropertiesModel(BaseModel):
    """A leaf node in the layer properties."""

    name: str
    layer: tuple[int, int]
    frame_color: Color | None = None
    fill_color: Color | None = None

    dither_pattern: int = 1
    line_style: int = 1
    visible: bool = True
    width: int = 1
    xfill: bool = False
    layer_to_name: bool = True
    transparent: bool = False
    valid: bool = True

    @model_validator(mode="before")
    def color_to_frame_fill(cls, data: dict[str, Any]) -> dict[str, Any]:
        """Convert a color string to a frame fill."""
        if "color" in data:
            if "fill_color" not in data:
                data["fill_color"] = data["color"]
            if "frame_color" not in data:
                data["frame_color"] = data["color"]
            del data["color"]
        return data

    @field_validator("dither_pattern", mode="before")
    def dither_to_index(cls, v: str | int) -> int:
        """Convert string to the index with the dict dither2index."""
        if isinstance(v, str):
            return dither2index[v]
        else:
            return v

    @field_validator("line_style", mode="before")
    def line_to_index(cls, v: str | int) -> int:
        """Convert string to the index with the dict dither2index."""
        if isinstance(v, str):
            return line2index[v]
        else:
            return v

    # @staticmethod
    @field_serializer("dither_pattern")
    def dither_to_json(value: int) -> str:  # type: ignore[misc]
        """Convert dither int to string key on json dump."""
        return index2dither[value]

    @field_serializer("line_style")
    def line_to_json(value: int) -> str:  # type: ignore[misc]
        """Convert dither int to string key on json dump."""
        return index2line[value]


class LayerGroupModel(BaseModel):
    """A group of layers."""

    name: str
    members: list[LayerPropertiesModel | LayerGroupModel]


class LypModel(BaseModel):
    """Model for the whole lyp."""

    layers: list[LayerGroupModel | LayerPropertiesModel]


def yaml_to_lyp(inp: pathlib.Path | str, out: pathlib.Path | str) -> None:
    """Convert a YAML file to a lyp file readable by KLayout."""
    f = pathlib.Path(inp)
    assert f.exists()

    yaml = YAML()
    lyp_dict = yaml.load(f)
    lyp_m = LypModel.parse_obj(lyp_dict)

    lv = lay.LayoutView()
    iter = lv.end_layers()

    for member in lyp_m.layers:
        if isinstance(member, LayerPropertiesModel):
            lv.insert_layer(iter, lp2kl(member))
            iter.next()
        else:
            lv.insert_layer(iter, group2lp(member))

    lv.save_layer_props(str(out))


def lyp_to_yaml(inp: pathlib.Path | str, out: pathlib.Path | str) -> None:
    """Convert a lyp file to a YAML ffile."""
    f = pathlib.Path(inp).resolve()
    assert f.exists()

    yaml = YAML()

    lv = lay.LayoutView()
    lv.load_layer_props(str(f))

    iter = lv.begin_layers()
    layers: list[LayerGroupModel | LayerPropertiesModel] = []

    while not iter.at_end():
        lpnr = iter.current()
        if lpnr.has_children():
            layers.append(
                LayerGroupModel(name=lpnr.name, members=kl2group(iter.first_child()))
            )
        else:
            layers.append(kl2lp(lpnr))
        iter.next_sibling(1)

    lyp_m = LypModel(layers=layers)

    yaml.dump(loads(lyp_m.model_dump_json()), pathlib.Path(out))


def kl2lp(kl: lay.LayerPropertiesNodeRef) -> LayerPropertiesModel:
    """Convert a KLayout LayerPropertiesNodeRef to a pydantic representation."""
    lp = LayerPropertiesModel(
        name=kl.name.rstrip(f" - {kl.source_layer}/{kl.source_datatype}"),
        layer=(kl.source_layer, kl.source_datatype),
        frame_color=Color(hex(kl.frame_color)) if kl.frame_color else None,
        fill_color=Color(hex(kl.fill_color)) if kl.fill_color else None,
        dither_pattern=index2dither[kl.dither_pattern],
        line_style=index2line[kl.line_style],
        visible=kl.visible,
        width=kl.width,
        xfill=kl.width,
        layer_to_name=kl.name.endswith(f" - {kl.source_layer}/{kl.source_datatype}"),
        transparent=kl.transparent,
        valid=kl.valid,
    )

    return lp


def kl2group(
    iter: lay.LayerPropertiesIterator,
) -> list[LayerGroupModel | LayerPropertiesModel]:
    """Convert a full LayerPropertiesIterator to a pydantic representation."""
    members: list[LayerGroupModel | LayerPropertiesModel] = []
    while not iter.at_end():
        lpnr = iter.current()
        if lpnr.has_children():
            members.append(
                LayerGroupModel(name=lpnr.name, members=kl2group(iter.first_child()))
            )
        else:
            members.append(kl2lp(lpnr))
        iter.next_sibling(1)
    return members


def lp2kl(lp: LayerPropertiesModel) -> lay.LayerPropertiesNode:
    """LayerPropertiesModel to KLayout LayerPropertiesNode."""
    kl_lp = lay.LayerPropertiesNode()

    kl_lp.name = (
        lp.name + f" - {lp.layer[0]}/{lp.layer[1]}" if lp.layer_to_name else lp.name
    )
    kl_lp.source = f"{lp.layer[0]}/{lp.layer[1]}"
    if lp.frame_color:
        hex_n = lp.frame_color.as_hex()[1:]
        if len(hex_n) < 6:
            hex_n = "".join(x * 2 for x in hex_n)
        kl_lp.frame_color = int(hex_n, 16)
    if lp.fill_color:
        hex_n = lp.fill_color.as_hex()[1:]
        if len(hex_n) < 6:
            hex_n = "".join(x * 2 for x in hex_n)
        kl_lp.fill_color = int(hex_n, 16)

    kl_lp.dither_pattern = lp.dither_pattern
    kl_lp.visible = lp.visible
    kl_lp.width = lp.width
    kl_lp.xfill = lp.xfill
    kl_lp.transparent = lp.transparent
    kl_lp.valid = lp.valid
    kl_lp.line_style = lp.line_style

    return kl_lp


def group2lp(lp: LayerGroupModel) -> lay.LayerPropertiesNode:
    """Convert a group model to a LayerPropertiesNode."""
    kl_lp = lay.LayerPropertiesNode()
    kl_lp.name = lp.name

    for member in lp.members:
        if isinstance(member, LayerPropertiesModel):
            kl_lp.add_child(lp2kl(member))
        else:
            kl_lp.add_child(group2lp(member))

    return kl_lp


dither_patterns = {
    "solid": "*",
    "hollow": ".",
    "dotted": "*.\n" ".*",
    "coarsely dotted": "*...\n" "....\n" "..*.\n" "....",
    "left-hatched": "*...\n" ".*..\n" "..*.\n" "...*",
    "lightly left-hatched": "*.......\n"
    ".*......\n"
    "..*.....\n"
    "...*....\n"
    "....*...\n"
    ".....*..\n"
    "......*.\n"
    ".......*",
    "strongly left-hatched dense": "**..\n" ".**.\n" "..**\n" "*..*",
    "strongly left-hatched sparse": "**......\n"
    ".**.....\n"
    "..**....\n"
    "...**...\n"
    "....**..\n"
    ".....**.\n"
    "......**\n"
    "*......*",
    "right-hatched": "*...\n" "...*\n" "..*.\n" ".*..",
    "lightly right-hatched": "*.......\n"
    ".......*\n"
    "......*.\n"
    ".....*..\n"
    "....*...\n"
    "...*....\n"
    "..*.....\n"
    ".*......",
    "strongly right-hatched dense": "**..\n" "*..*\n" "..**\n" ".**.",
    "strongly right-hatched sparse": "**......\n"
    "*......*\n"
    "......**\n"
    ".....**.\n"
    "....**..\n"
    "...**...\n"
    "..**....\n"
    ".**.....",
    "cross-hatched": "*...\n" ".*.*\n" "..*.\n" ".*.*",
    "lightly cross-hatched": "*.......\n"
    ".*.....*\n"
    "..*...*.\n"
    "...*.*..\n"
    "....*...\n"
    "...*.*..\n"
    "..*...*.\n"
    ".*.....*",
    "checkerboard 2px": "**..\n" "**..\n" "..**\n" "..**",
    "strongly cross-hatched sparse": "**......\n"
    "***....*\n"
    "..**..**\n"
    "...****.\n"
    "....**..\n"
    "...****.\n"
    "..**..**\n"
    "***....*",
    "heavy checkerboard": "****....\n"
    "****....\n"
    "****....\n"
    "****....\n"
    "....****\n"
    "....****\n"
    "....****\n"
    "....****",
    "hollow bubbles": ".*...*..\n"
    "*.*.....\n"
    ".*...*..\n"
    "....*.*.\n"
    ".*...*..\n"
    "*.*.....\n"
    ".*...*..\n"
    "....*.*.",
    "solid bubbles": ".*...*..\n"
    "***.....\n"
    ".*...*..\n"
    "....***.\n"
    ".*...*..\n"
    "***.....\n"
    ".*...*..\n"
    "....***.",
    "pyramids": ".*......\n"
    "*.*.....\n"
    "****...*\n"
    "........\n"
    "....*...\n"
    "...*.*..\n"
    "..*****.\n"
    "........",
    "turned pyramids": "****...*\n"
    "*.*.....\n"
    ".*......\n"
    "........\n"
    "..*****.\n"
    "...*.*..\n"
    "....*...\n"
    "........",
    "plus": "..*...*.\n"
    "..*.....\n"
    "*****...\n"
    "..*.....\n"
    "..*...*.\n"
    "......*.\n"
    "*...****\n"
    "......*.",
    "minus": "........\n"
    "........\n"
    "*****...\n"
    "........\n"
    "........\n"
    "........\n"
    "*...****\n"
    "........",
    "22.5 degree down": "*......*\n"
    ".**.....\n"
    "...**...\n"
    ".....**.\n"
    "*......*\n"
    ".**.....\n"
    "...**...\n"
    ".....**.",
    "22.5 degree up": "*......*\n"
    ".....**.\n"
    "...**...\n"
    ".**.....\n"
    "*......*\n"
    ".....**.\n"
    "...**...\n"
    ".**.....",
    "67.5 degree down": "*...*...\n"
    ".*...*..\n"
    ".*...*..\n"
    "..*...*.\n"
    "..*...*.\n"
    "...*...*\n"
    "...*...*\n"
    "*...*...",
    "67.5 degree up": "...*...*\n"
    "..*...*.\n"
    "..*...*.\n"
    ".*...*..\n"
    ".*...*..\n"
    "*...*...\n"
    "*...*...\n"
    "...*...*",
    "22.5 degree cross hatched": "*......*\n"
    ".**..**.\n"
    "...**...\n"
    ".**..**.\n"
    "*......*\n"
    ".**..**.\n"
    "...**...\n"
    ".**..**.",
    "zig zag": "..*...*.\n"
    ".*.*.*.*\n"
    "*...*...\n"
    "........\n"
    "..*...*.\n"
    ".*.*.*.*\n"
    "*...*...\n"
    "........",
    "sine": "..***...\n"
    ".*...*..\n"
    "*.....**\n"
    "........\n"
    "..***...\n"
    ".*...*..\n"
    "*.....**\n"
    "........",
    "heavy unordered": "****.*.*\n"
    "**.****.\n"
    "*.**.***\n"
    "*****.*.\n"
    ".**.****\n"
    "**.***.*\n"
    ".****.**\n"
    "*.*.****",
    "light unordered": "....*.*.\n"
    "..*....*\n"
    ".*..*...\n"
    ".....*.*\n"
    "*..*....\n"
    "..*...*.\n"
    "*....*..\n"
    ".*.*....",
    "vertical dense": "*.\n" "*.\n",
    "vertical": ".*..\n" ".*..\n" ".*..\n" ".*..\n",
    "vertical thick": ".**.\n" ".**.\n" ".**.\n" ".**.\n",
    "vertical sparse": "...*....\n" "...*....\n" "...*....\n" "...*....\n",
    "vertical sparse, thick": "...**...\n" "...**...\n" "...**...\n" "...**...\n",
    "horizontal dense": "**\n" "..\n",
    "horizontal": "....\n" "****\n" "....\n" "....\n",
    "horizontal thick": "....\n" "****\n" "****\n" "....\n",
    "horizontal sparse": "........\n"
    "........\n"
    "........\n"
    "********\n"
    "........\n"
    "........\n"
    "........\n"
    "........\n",
    "horizontal sparse, thick": "........\n"
    "........\n"
    "........\n"
    "********\n"
    "********\n"
    "........\n"
    "........\n"
    "........\n",
    "grid dense": "**\n" "*.\n",
    "grid": ".*..\n" "****\n" ".*..\n" ".*..\n",
    "grid thick": ".**.\n" "****\n" "****\n" ".**.\n",
    "grid sparse": "...*....\n"
    "...*....\n"
    "...*....\n"
    "********\n"
    "...*....\n"
    "...*....\n"
    "...*....\n"
    "...*....\n",
    "grid sparse, thick": "...**...\n"
    "...**...\n"
    "...**...\n"
    "********\n"
    "********\n"
    "...**...\n"
    "...**...\n"
    "...**...\n",
}
line_styles = {
    "solid": "",
    "dotted": "*.",
    "dashed": "**..**",
    "dash-dotted": "***..**..***",
    "short dashed": "*..*",
    "short dash-dotted": "**.*.*",
    "long dashed": "*****..*****",
    "dash-double-dotted": "***..*.*..**",
}

dither2index: dict[str, int] = {
    name: index for index, name in enumerate(dither_patterns)
}
index2dither: dict[int, str] = {
    index: name for index, name in enumerate(dither_patterns)
}
line2index: dict[str, int] = {name: index for index, name in enumerate(line_styles)}
index2line: dict[int, str] = {index: name for index, name in enumerate(line_styles)}
