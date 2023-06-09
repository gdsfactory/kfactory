"""Utilities to go lyp <-> yaml."""
from __future__ import annotations

import pathlib

from pydantic import BaseModel, field_validator
from pydantic.color import Color
from ruamel.yaml import YAML

from .. import lay


class LayerPropertiesModel(BaseModel):
    """A leaf node in the layer properties."""

    name: str
    layer: tuple[int, int]
    frame_color: Color | None = None
    fill_color: Color | None = None

    dither_pattern: int = 1
    visible: bool = True
    width: int = 1
    xfill: bool = False
    layer_to_name: bool = True
    transparent: bool = False
    valid: bool = True

    @field_validator("dither_pattern", mode="before")
    def dither_to_index(cls, v: str | int) -> int:
        """Convert string to the index with the dict dither2index."""
        if isinstance(v, str):
            return dither2index[v]
        else:
            return v


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


def lp2kl(lp: LayerPropertiesModel) -> lay.LayerPropertiesNode:
    """LayerPropertiesModel to KLayout LayerPropertiesNode."""
    kl_lp = lay.LayerPropertiesNode()

    kl_lp.name = (
        lp.name + f" - {lp.layer[0]}/{lp.layer[1]}" if lp.layer_to_name else lp.name
    )
    kl_lp.source = f"{lp.layer[0]}/{lp.layer[1]}"
    if lp.frame_color:
        kl_lp.frame_color = int(lp.frame_color.as_hex()[1:], 16)
    if lp.fill_color:
        kl_lp.fill_color = int(lp.fill_color.as_hex()[1:], 16)
    kl_lp.dither_pattern = lp.dither_pattern
    kl_lp.visible = lp.visible
    kl_lp.width = lp.width
    kl_lp.xfill = lp.xfill
    kl_lp.transparent = lp.transparent
    kl_lp.valid = lp.valid

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

dither2index = {name: index for index, name in enumerate(dither_patterns)}
index2dither = {index: name for index, name in enumerate(dither_patterns)}
