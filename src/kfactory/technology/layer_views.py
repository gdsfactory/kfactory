"""A GDS layer is a tuple of two integers.

You can maintain LayerViews in YAML (.yaml) or Klayout XML file (.lyp)

"""
from __future__ import annotations

import os
import pathlib
import re
import xml.etree.ElementTree as ET
from typing import TYPE_CHECKING, Any, TypeAlias

import numpy as np
from pydantic import BaseModel, Field, validator
from pydantic.color import Color, ColorType
from ruamel.yaml import YAML

from kfactory.conf import logger
from kfactory.technology.color_utils import ensure_six_digit_hex_color
from kfactory.technology.xml_utils import make_pretty_xml
from kfactory.technology.yaml_utils import (
    add_color_yaml_presenter,
    add_multiline_str_yaml_presenter,
    add_tuple_yaml_presenter,
)

from ..typings import PathType

if TYPE_CHECKING:
    import builtins

    from pydantic.typing import AbstractSetIntStr, DictStrAny, MappingIntStrAny

Layer: TypeAlias = tuple[int, int]


def clean_name(name: str, remove_dots: bool = False) -> str:
    """Return a string with correct characters for a cell name.

    [a-zA-Z0-9]

    FIXME: only a few characters are currently replaced.
        This function has been updated only on case-by-case basis

    """
    replace_map = {
        " ": "_",
        "!": "",
        "?": "",
        "#": "_",
        "%": "_",
        "(": "",
        ")": "",
        "*": "_",
        ",": "_",
        "-": "m",
        ".": "p",
        "/": "_",
        ":": "_",
        "=": "",
        "@": "_",
        "[": "",
        "]": "",
        "{": "",
        "}": "",
        "$": "",
    }

    if remove_dots:
        replace_map["."] = ""
    for k, v in list(replace_map.items()):
        name = name.replace(k, v)
    return name


_klayout_line_styles = {
    "solid": "",
    "dotted": "*.",
    "dashed": "**..**",
    "dash-dotted": "***..**..***",
    "short dashed": "*..*",
    "short dash-dotted": "**.*.*",
    "long dashed": "*****..*****",
    "dash-double-dotted": "***..*.*..**",
}
_klayout_dither_patterns = {
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


class HatchPattern(BaseModel):
    """Custom dither pattern. See KLayout documentation for more info.

    Attributes:
        name: Name of the pattern.
        order: Order of pattern.
        custom_pattern: Pattern defining custom shape.
    """

    name: str
    order: int | None = None
    custom_pattern: str | None = None

    class Config:
        """YAML output uses name as the key."""

        fields = {"name": {"exclude": True}}

    @validator("custom_pattern")
    def check_pattern_klayout(cls, pattern: str | None, **kwargs: Any) -> str | None:
        if pattern is None:
            return None
        lines = pattern.splitlines()
        if any(len(list(line)) > 32 for line in lines):
            raise ValueError(
                f"Custom pattern {kwargs['values']['name']}"
                " has more than 32 characters."
            )
        return pattern

    def to_klayout_xml(self) -> ET.Element:
        if self.custom_pattern is None:
            raise KeyError(
                f"Cannot write custom hatch/dither pattern {self.name} to KLayout xml"
                " format because no pattern is present."
            )

        el = ET.Element("custom-dither-pattern")

        subel = ET.SubElement(el, "pattern")
        lines = self.custom_pattern.splitlines()
        if len(lines) == 1:
            subel.text = lines[0]
        else:
            for line in lines:
                ET.SubElement(subel, "line").text = line

        ET.SubElement(el, "order").text = str(self.order)
        ET.SubElement(el, "name").text = self.name
        return el


class LineStyle(BaseModel):
    """Custom line style. See KLayout documentation for more info.

    Attributes:
        name: Name of the line style.
        order: Order of line style.
        custom_style: Line style to use.
    """

    name: str
    order: int | None = None
    custom_style: str

    class Config:
        """YAML output uses name as the key."""

        fields = {"name": {"exclude": True}}

    @validator("custom_style")
    def check_pattern(cls, pattern: str, **kwargs: Any) -> str:
        pattern_list = list(pattern)
        valid_chars = all(char in ["*", "."] for char in pattern_list)
        valid_length = len(pattern_list) <= 32
        if (not valid_chars) or (not valid_length):
            raise ValueError(
                f"Custom line pattern {kwargs['values']['name']} must consist of '*' and '.' characters and be no more than 32 characters long."
            )

        return pattern

    def to_klayout_xml(self) -> ET.Element:
        if self.custom_style is None:
            raise KeyError(
                f"Cannot write custom line style {self.name} to KLayout xml format because no pattern is present."
            )

        el = ET.Element("custom-line-pattern")

        ET.SubElement(el, "pattern").text = str(self.custom_style)
        ET.SubElement(el, "order").text = str(self.order)
        ET.SubElement(el, "name").text = self.name
        return el


class LayerView(BaseModel):
    """KLayout layer properties.

    Docstrings adapted from KLayout documentation:
    https://www.klayout.de/lyp_format.html

    Attributes:
        name: Layer name.
        info: Extra info to include in the LayerView.
        layer: GDSII layer.
        layer_in_name: Whether to display the name as 'name layer/datatype' rather than
            just the layer.
        width: This is the line width of the frame in pixels (or empty for the default
            which is 1).
        line_style: This is the number of the line style used to draw the shape
            boundaries. An empty string is "solid line". The values are "Ix" for
            one of the built-in styles where "I0" is "solid", "I1" is "dotted" etc.
        hatch_pattern: This is the number of the dither pattern used to fill the shapes.
            The values are "Ix" for one of the built-in pattern where "I0" is "solid"
            and "I1" is "clear".
        fill_color: Display color of the layer fill.
        frame_color: Display color of the layer frame.
            Accepts Pydantic Color types.
            See: https://docs.pydantic.dev/usage/types/#color-type for more info.
        fill_brightness: Brightness of the fill.
        frame_brightness: Brightness of the frame.
        animation: This is a value indicating the animation mode.
            0 is "none", 1 is "scrolling", 2 is "blinking" and 3 is "inverse blinking".
            (Only applies to KLayout layer properties)
        xfill: Whether boxes are drawn with a diagonal cross. (Only applies to KLayout
            layer properties)
        marked: Whether the entry is marked (drawn with small crosses). (Only applies
            to KLayout layer properties)
        transparent: Whether the entry is transparent.
        visible: Whether the entry is visible.
        valid: Whether the entry is valid. Invalid layers are drawn but you can't
            select shapes on those layers.
            (Only applies to KLayout layer properties)
        group_members: Add a list of group members to the LayerView.
    """

    name: str | None = None
    info: str | None = None
    layer: Layer
    layer_in_name: bool = False
    frame_color: Color | None = None
    fill_color: Color | None = None
    frame_brightness: int = 0
    fill_brightness: int = 0
    hatch_pattern: HatchPattern
    line_style: LineStyle
    valid: bool = True
    visible: bool = True
    transparent: bool = False
    width: int | None = None
    marked: bool = False
    xfill: bool = False
    animation: int = 0
    group_members: dict[str, LayerView] = Field(default_factory=dict)

    class Config:
        """YAML output uses name as the key."""

        fields = {"name": {"exclude": True}}

    def __init__(
        self,
        gds_layer: int | None = None,
        gds_datatype: int | None = None,
        color: ColorType | None = None,
        brightness: int | None = None,
        **data: Any,
    ):
        """Initialize LayerView object."""
        if (gds_layer is not None) and (gds_datatype is not None):
            if "layer" in data and data["layer"] is not None:
                raise KeyError(
                    "Specify either 'layer' or both 'gds_layer' and 'gds_datatype'."
                )
            data["layer"] = (gds_layer, gds_datatype)

        if color is not None:
            if "fill_color" in data or "frame_color" in data:
                raise KeyError(
                    "Specify either a single 'color' or both 'frame_color' and"
                    " 'fill_color'."
                )
            data["fill_color"] = data["frame_color"] = color
        if brightness is not None:
            if "fill_brightness" in data or "frame_brightness" in data:
                raise KeyError(
                    "Specify either a single 'brightness' or both 'frame_brightness'"
                    " and 'fill_brightness'."
                )
            data["fill_brightness"] = data["frame_brightness"] = brightness

        super().__init__(**data)

        # Iterate through all items, adding group members as needed
        for name, field in self.__fields__.items():
            default = field.get_default()
            if isinstance(default, LayerView):
                self.group_members[name] = default

    def dict(
        self,
        *,
        include: AbstractSetIntStr | MappingIntStrAny | None = None,
        exclude: AbstractSetIntStr | MappingIntStrAny | None = None,
        by_alias: bool = False,
        skip_defaults: bool | None = None,
        exclude_unset: bool = False,
        exclude_defaults: bool = False,
        exclude_none: bool = False,
        simplify: bool = True,
    ) -> DictStrAny:
        """Generate a dictionary representation of the model, optionally specifying which fields to include or exclude.

        Specify "simplify" to consolidate fill and frame color/brightness if they are the same.
        """
        _dict = super().dict(
            include=include,
            exclude=exclude,
            by_alias=by_alias,
            skip_defaults=skip_defaults,
            exclude_unset=exclude_unset,
            exclude_defaults=exclude_defaults,
            exclude_none=exclude_none,
        )

        if simplify:
            replace_keys = ["color", "brightness"]
            for key in replace_keys:
                fill = f"fill_{key}"
                frame = f"frame_{key}"

                if (fill in _dict.keys() and frame in _dict.keys()) and (
                    _dict[fill] == _dict[frame]
                ):
                    _dict[key] = _dict.pop(f"frame_{key}")
                    _dict.pop(f"fill_{key}")
        return _dict

    def __str__(self) -> str:
        """Returns a formatted view of properties and their values."""
        return "LayerView:\n\t" + "\n\t".join(
            [f"{k}: {v}" for k, v in self.dict().items()]
        )

    def __repr__(self) -> str:
        """Returns a formatted view of properties and their values."""
        return self.__str__()

    def get_alpha(self) -> float:
        """Get the alpha value."""
        if not self.visible:
            return 0.0
        elif not self.transparent:
            dither_name = getattr(self.hatch_pattern, "name", self.hatch_pattern)
            if dither_name in ["I0", "solid"]:
                return 0.6
            elif dither_name in ["I1", "hollow"]:
                return 0.1
            else:
                return 0.4
        else:
            return 0.3

    def get_color_dict(self) -> builtins.dict[str, str]:
        if self.fill_color is not None and self.frame_color is not None:
            return {
                "fill_color": ensure_six_digit_hex_color(self.fill_color.as_hex()),
                "frame_color": ensure_six_digit_hex_color(self.frame_color.as_hex()),
            }
        # Colors generated from here: http://phrogz.net/css/distinct-colors.html
        layer_colors = [
            "#3dcc5c",
            "#2b0fff",
            "#cc3d3d",
            "#e5dd45",
            "#7b3dcc",
            "#cc860c",
            "#73ff0f",
            "#2dccb4",
            "#ff0fa3",
            "#0ec2e6",
            "#3d87cc",
            "#e5520e",
        ]
        color = layer_colors[np.mod(self.layer[0], len(layer_colors))]
        return {"fill_color": color, "frame_color": color}

    def _build_klayout_xml_element(
        self,
        tag: str,
        name: str,
        custom_hatch_patterns: builtins.dict[str, str],
        custom_line_styles: builtins.dict[str, str],
    ) -> ET.Element:
        """Get XML Element from attributes."""
        # If hatch pattern name matches a named (built-in) KLayout pattern,
        # use 'I<idx>' notation
        hatch_name = getattr(self.hatch_pattern, "name", self.hatch_pattern)
        assert isinstance(hatch_name, str)
        if hatch_name is None:
            dither_pattern = None
        elif hatch_name in _klayout_dither_patterns:
            dither_pattern = f"I{list(_klayout_dither_patterns).index(hatch_name)}"
        elif hatch_name in custom_hatch_patterns:
            dither_pattern = f"C{list(custom_hatch_patterns).index(hatch_name)}"
        else:
            logger.warning(
                f"Dither pattern {hatch_name!r} does not correspond to any KLayout built-in or custom pattern! Using 'solid' instead."
            )
            dither_pattern = "solid"

        # If line style name matches a named (built-in) KLayout pattern, use 'I<idx>' notation
        ls_name = getattr(self.line_style, "name", self.line_style)
        assert isinstance(ls_name, str)
        if ls_name is None:
            line_style = None
        elif ls_name in _klayout_line_styles:
            line_style = f"I{list(_klayout_line_styles).index(ls_name)}"
        elif ls_name in custom_line_styles:
            line_style = f"C{list(custom_line_styles).index(ls_name)}"
        else:
            logger.warning(
                f"Line style {ls_name!r} does not correspond to any KLayout built-in or custom pattern! Using 'solid' instead."
            )
            line_style = "solid"

        frame_color = (
            ensure_six_digit_hex_color(self.frame_color.as_hex())
            if isinstance(self.frame_color, Color)
            else self.frame_color
        )
        fill_color = (
            ensure_six_digit_hex_color(self.fill_color.as_hex())
            if isinstance(self.fill_color, Color)
            else self.fill_color
        )
        prop_dict = {
            "frame-color": frame_color,
            "fill-color": fill_color,
            "frame-brightness": self.frame_brightness,
            "fill-brightness": self.fill_brightness,
            "dither-pattern": dither_pattern,
            "line-style": line_style,
            "valid": str(self.valid).lower(),
            "visible": str(self.visible).lower(),
            "transparent": str(self.transparent).lower(),
            "width": self.width,
            "marked": str(self.marked).lower(),
            "xfill": str(self.xfill).lower(),
            "animation": self.animation,
            "name": f"{name} {self.layer[0]}/{self.layer[1]}"
            if self.layer_in_name
            else name,
            "source": f"{self.layer[0]}/{self.layer[1]}@1"
            if self.layer is not None
            else "*/*@*",
        }
        el = ET.Element(tag)
        for key, value in prop_dict.items():
            subel = ET.SubElement(el, key)

            if value is None:
                continue

            if isinstance(value, bool):
                value = str(value).lower()

            subel.text = str(value)
        return el

    def to_klayout_xml(
        self,
        custom_hatch_patterns: builtins.dict[str, str],
        custom_line_styles: builtins.dict[str, str],
    ) -> ET.Element:
        """Return an XML representation of the LayerView."""
        assert self.name is not None
        props = self._build_klayout_xml_element(
            "properties",
            name=self.name,
            custom_hatch_patterns=custom_hatch_patterns,
            custom_line_styles=custom_line_styles,
        )
        for member_name, member in self.group_members.items():
            props.append(
                member._build_klayout_xml_element(
                    "group-members",
                    name=member_name,
                    custom_hatch_patterns=custom_hatch_patterns,
                    custom_line_styles=custom_line_styles,
                )
            )
        return props

    @staticmethod
    def _process_name(
        name: str, layer_pattern: str | re.Pattern[str]
    ) -> tuple[str, bool]:
        """Strip layer info from name if it exists.

        Args:
            name: XML-formatted name entry.
            layer_pattern: Regex pattern to match layers with.
        """
        layer_in_name = False
        match = re.search(layer_pattern, name)
        if match:
            name = name[: match.start()].strip()
            layer_in_name = True
        return clean_name(name, remove_dots=True), layer_in_name

    @staticmethod
    def _process_layer(
        layer: str, layer_pattern: str | re.Pattern[str]
    ) -> Layer | None:
        """Convert .lyp XML layer entry to a Layer.

        Args:
            layer: XML-formatted layer entry.
            layer_pattern: Regex pattern to match layers with.
        """
        match = re.search(layer_pattern, layer)
        if not match:
            raise OSError(f"Could not read layer {layer}!")
        v = match.group().split("/")
        return None if "*" in v else (int(v[0]), int(v[1]))

    @classmethod
    def from_xml_element(
        cls, element: ET.Element, layer_pattern: str | re.Pattern[str]
    ) -> LayerView | None:
        """Read properties from .lyp XML and generate LayerViews from them.

        Args:
            element: XML Element to iterate over.
            layer_pattern: Regex pattern to match layers with.
        """
        _name = element.find("name")
        assert isinstance(_name, str)
        name, layer_in_name = cls._process_name(_name.text, layer_pattern)
        if name is None:
            return None

        # Translate KLayout index to hatch name
        hatch_pattern = element.find("dither-pattern")
        assert isinstance(hatch_pattern, str)
        if hatch_pattern and re.match(r"I\d+", hatch_pattern.text):
            hatch_pattern = list(_klayout_dither_patterns.keys())[
                int(hatch_pattern.text[1:])
            ]

        # Translate KLayout index to line style name
        line_style = element.find("line-style")
        if line_style and re.match(r"I\d+", line_style.text):
            line_style = list(_klayout_line_styles.keys())[int(line_style.text[1:])]

        lv = LayerView(
            name=name,
            layer=cls._process_layer(element.find("source").text, layer_pattern),
            fill_color=getattr(element.find("fill-color"), "text", None),
            frame_color=getattr(element.find("frame-color"), "text", None),
            fill_brightness=element.find("fill-brightness").text or 0,
            frame_brightness=element.find("frame-brightness").text or 0,
            hatch_pattern=hatch_pattern or None,
            line_style=line_style or None,
            valid=getattr(element.find("valid"), "text", True),
            visible=getattr(element.find("visible"), "text", True),
            transparent=getattr(element.find("transparent"), "text", False),
            width=getattr(element.find("width"), "text", None),
            marked=getattr(element.find("marked"), "text", False),
            xfill=getattr(element.find("xfill"), "text", False),
            animation=getattr(element.find("animation"), "text", False),
            layer_in_name=layer_in_name,
        )

        # Add only if needed, so we can filter by defaults when dumping to yaml
        group_members = {}
        for member in element.iterfind("group-members"):
            member_lv = cls.from_xml_element(member, layer_pattern)
            if member_lv:
                group_members[member_lv.name] = member_lv

        if group_members != {}:
            lv.group_members = group_members

        return lv


class LayerViews(BaseModel):
    """A container for layer properties for KLayout layer property (.lyp) files.

    Attributes:
        layer_views: Dictionary of LayerViews describing how to display gds layers.
        custom_dither_patterns: Custom dither patterns.
        custom_line_styles: Custom line styles.
        layer_map: Specify a layer_map to get the layer tuple based on the name of the
            LayerView, rather than the 'layer' argument.
    """

    layer_views: dict[str, LayerView] = Field(default_factory=dict)
    custom_dither_patterns: dict[str, HatchPattern] = Field(default_factory=dict)
    custom_line_styles: dict[str, LineStyle] = Field(default_factory=dict)
    layer_map: dict[str, Layer] = Field(default_factory=dict)

    def __init__(
        self,
        layer_map: dict[str, Layer] | BaseModel,
        filepath: PathType | None = None,
        **data: Any,
    ):
        """Initialize LayerViews object.

        Args:
            filepath: can be YAML or LYP.
            layer_map: Optional layermap.
        """
        if filepath is not None:
            filepath = pathlib.Path(filepath)
            if filepath.suffix == ".lyp":
                lvs = LayerViews.from_lyp(filepath=filepath)
                logger.info(
                    "Importing LayerViews from KLayout layer properties file: "
                    f"{str(filepath)!r}."
                )
            elif filepath.suffix in [".yaml", ".yml"]:
                lvs = LayerViews.from_yaml(layer_file=filepath)
                logger.info(f"Importing LayerViews from YAML file: {str(filepath)!r}.")
            else:
                raise ValueError(f"Unable to load LayerViews from {str(filepath)!r}.")

            data["layer_views"] = lvs.layer_views
            data["custom_line_styles"] = lvs.custom_line_styles
            data["custom_dither_patterns"] = lvs.custom_dither_patterns

        if isinstance(layer_map, BaseModel):
            layer_map = layer_map.dict()

        if layer_map is not None:
            data["layer_map"] = layer_map

        super().__init__(**data)

        for name in self.dict():
            lv = getattr(self, name)
            if isinstance(lv, LayerView):
                #
                if (self.layer_map is not None) and (name in self.layer_map.keys()):
                    lv_dict = lv.dict(exclude={"layer", "name"})
                    lv = LayerView(layer=self.layer_map[name], name=name, **lv_dict)
                self.add_layer_view(name=name, layer_view=lv)

    def add_layer_view(
        self, name: str, layer_view: LayerView | None = None, **kwargs: Any
    ) -> None:
        """Adds a layer to LayerViews.

        Args:
            name: Name of the LayerView.
            layer_view: LayerView to add.
        """
        if name in self.layer_views:
            raise ValueError(
                f"Adding {name!r} already defined {list(self.layer_views.keys())}"
            )
        if layer_view is None:
            layer_view = LayerView(name=name, **kwargs)
        if layer_view.name is None:
            layer_view.name = name
        self.layer_views[name] = layer_view

        # If the dither pattern is a CustomDitherPattern, add it to custom_patterns
        dither_pattern = layer_view.hatch_pattern
        if (
            isinstance(dither_pattern, HatchPattern)
            and dither_pattern not in self.custom_dither_patterns.keys()
        ):
            assert dither_pattern.custom_pattern is not None
            self.custom_dither_patterns[
                dither_pattern.name
            ] = dither_pattern.custom_pattern

        # If hatch_pattern is the name of a custom pattern, replace string with the CustomDitherPattern
        elif (
            isinstance(dither_pattern, str)
            and dither_pattern in self.custom_dither_patterns.keys()
        ):
            layer_view.hatch_pattern = self.custom_dither_patterns[dither_pattern]

        line_style = layer_view.line_style
        if (
            isinstance(line_style, LineStyle)
            and line_style not in self.custom_line_styles.keys()
        ):
            assert line_style.custom_style is not None
            self.custom_line_styles[line_style.name] = line_style.custom_style
        elif (
            isinstance(line_style, str) and line_style in self.custom_line_styles.keys()
        ):
            layer_view.line_style = self.custom_line_styles[line_style]

    def get_layer_views(self, exclude_groups: bool = False) -> dict[str, LayerView]:
        """Return all LayerViews.

        Args:
            exclude_groups: Whether to exclude LayerViews that contain other LayerViews.
        """
        layers = {}
        for name, view in self.layer_views.items():
            if view.group_members and not exclude_groups:
                for member_name, member in view.group_members.items():
                    layers[member_name] = member
                continue
            layers[name] = view
        return layers

    def get_layer_view_groups(self) -> dict[str, LayerView]:
        """Return the LayerViews that contain other LayerViews."""
        return {name: lv for name, lv in self.layer_views.items() if lv.group_members}

    def __str__(self) -> str:
        """Prints the number of LayerView objects in the LayerViews object."""
        lvs = self.get_layer_views()
        groups = self.get_layer_view_groups()
        return (
            f"LayerViews: {len(lvs)} layers ({len(groups)} groups)\n"
            f"\tCustomDitherPatterns: {list(self.custom_dither_patterns.keys())}\n"
            f"\tCustomLineStyles: {list(self.custom_line_styles.keys())}\n"
        )

    def get(self, name: str) -> LayerView:
        """Returns Layer from name.

        Args:
            name: Name of layer.
        """
        if name not in self.layer_views:
            raise ValueError(f"Layer {name!r} not in {list(self.layer_views.keys())}")
        else:
            return self.layer_views[name]

    def __getitem__(self, val: str) -> LayerView:
        """Allows accessing to the layer names like ls['gold2'].

        Args:
            val: Layer name to access within the LayerViews.

        Returns:
            self.layers[val]: LayerView in the LayerViews.

        """
        try:
            return self.get_layer_views()[val]
        except Exception as error:
            raise ValueError(
                f"LayerView {val!r} not in LayerViews {list(self.layer_views.keys())}"
            ) from error

    def get_from_tuple(self, layer_tuple: Layer) -> LayerView:
        """Returns LayerView from layer tuple.

        Args:
            layer_tuple: Tuple of (gds_layer, gds_datatype).

        Returns:
            LayerView.
        """
        tuple_to_name = {v.layer: k for k, v in self.get_layer_views().items()}
        if layer_tuple not in tuple_to_name:
            raise ValueError(
                f"LayerView {layer_tuple} not in {list(tuple_to_name.keys())}"
            )

        name = tuple_to_name[layer_tuple]
        return self.get_layer_views()[name]

    def get_layer_tuples(self) -> set[Layer]:
        """Returns a tuple for each layer."""
        return {layer.layer for layer in self.get_layer_views().values()}

    def clear(self) -> None:
        """Deletes all layers in the LayerViews."""
        self.layer_views = {}

    # def preview_layerset(self, size: float = 100.0, spacing: float = 100.0) -> object:
    #     """Generates a Cell with all the layers.

    #     Args:
    #         size: square size in um.
    #         spacing: spacing between each square in um.

    #     """
    #     import kfactory as kf

    #     D = kf.KCell(name="layerset")
    #     scale = size / 100
    #     num_layers = len(self.get_layer_views())
    #     matrix_size = int(np.ceil(np.sqrt(num_layers)))
    #     sorted_layers = sorted(
    #         self.get_layer_views().values(), key=lambda x: (x.layer[0], x.layer[1])
    #     )
    #     for n, layer in enumerate(sorted_layers):
    #         layer_tuple = layer.layer
    #         R = kf.cells.rectangle(size=(100 * scale, 100 * scale), layer=layer_tuple)
    #         T = kf.cells.text(
    #             text=f"{layer.name}\n{layer_tuple[0]} / {layer_tuple[1]}",
    #             size=20 * scale,
    #             position=(50 * scale, -20 * scale),
    #             justify="center",
    #             layer=layer_tuple,
    #         )

    #         xloc = n % matrix_size
    #         yloc = int(n // matrix_size)
    #         D.add_ref(R).movex((100 + spacing) * xloc * scale).movey(
    #             -(100 + spacing) * yloc * scale
    #         )
    #         D.add_ref(T).movex((100 + spacing) * xloc * scale).movey(
    #             -(100 + spacing) * yloc * scale
    #         )
    #     return D

    def to_lyp(self, filepath: PathType, overwrite: bool = True) -> None:
        """Write all layer properties to a KLayout .lyp file.

        Args:
            filepath: to write the .lyp file to (appends .lyp extension if not present).
            overwrite: Whether to overwrite an existing file located at the filepath.

        """
        filepath = pathlib.Path(filepath)
        dirpath = filepath.parent
        dirpath.mkdir(exist_ok=True, parents=True)

        if filepath.exists() and not overwrite:
            raise OSError(f"File {str(filepath)!r} exists, cannot write.")

        root = ET.Element("layer-properties")

        for lv in self.layer_views.values():
            root.append(
                lv.to_klayout_xml(
                    custom_hatch_patterns=self.custom_dither_patterns,
                    custom_line_styles=self.custom_line_styles,
                )
            )

        for dp in self.custom_dither_patterns.values():
            root.append(dp.to_klayout_xml())

        for ls in self.custom_line_styles.values():
            root.append(ls.to_klayout_xml())

        filepath.write_bytes(make_pretty_xml(root))

    @staticmethod
    def from_lyp(
        filepath: PathType,
        layer_pattern: str | re.Pattern | None = None,
    ) -> LayerViews:
        r"""Write all layer properties to a KLayout .lyp file.

        Args:
            filepath: to write the .lyp file to (appends .lyp extension if not present).
            layer_pattern: Regex pattern to match layers with. Defaults to r'(\d+|\*)/(\d+|\*)'.
        """
        layer_pattern = re.compile(layer_pattern or r"(\d+|\*)/(\d+|\*)")

        filepath = pathlib.Path(filepath)

        if not os.path.exists(filepath):
            raise OSError("File not found!")

        tree = ET.parse(filepath)
        root = tree.getroot()
        if root.tag != "layer-properties":
            raise OSError("Layer properties file incorrectly formatted, cannot read.")

        dither_patterns = {}
        for dither_block in root.iter("custom-dither-pattern"):
            name = dither_block.find("name").text
            order = dither_block.find("order").text

            if name is None or order is None:
                continue
            pattern = "\n".join(
                [line.text for line in dither_block.find("pattern").iter()]
            )

            if name in dither_patterns:
                logger.warning(
                    f"Dither pattern named {name!r} already exists. Keeping only the first defined."
                )
                continue

            dither_patterns[name] = HatchPattern(
                name=name,
                order=int(order),
                custom_pattern=pattern.lstrip(),
            )
        line_styles = {}
        for line_block in root.iter("custom-line-style"):
            name = line_block.find("name").text
            order = line_block.find("order").text

            if name is None or order is None:
                continue

            if name in line_styles:
                logger.warning(
                    f"Line style named {name!r} already exists. Keeping only the first defined."
                )
                continue

            line_styles[name] = LineStyle(
                name=name,
                order=int(order),
                custom_style=line_block.find("pattern").text,
            )

        layer_views = {}
        for properties_element in root.iter("properties"):
            lv = LayerView.from_xml_element(
                properties_element, layer_pattern=layer_pattern
            )
            if lv:
                layer_views[lv.name] = lv

        return LayerViews(
            layer_views=layer_views,
            custom_dither_patterns=dither_patterns,
            custom_line_styles=line_styles,
        )

    def to_yaml(self, layer_file: PathType, prefer_named_color: bool = True) -> None:
        """Export layer properties to a YAML file.

        Args:
            layer_file: Name of the file to write LayerViews to.
            prefer_named_color: Write the name of a color instead of its hex representation when possible.
        """
        import yaml

        lf_path = pathlib.Path(layer_file)
        dirpath = lf_path.parent
        dirpath.mkdir(exist_ok=True, parents=True)

        add_tuple_yaml_presenter()
        add_multiline_str_yaml_presenter()
        add_color_yaml_presenter(prefer_named_color=prefer_named_color)

        lvs = {
            name: lv.dict(exclude_none=True, exclude_defaults=True, exclude_unset=True)
            for name, lv in self.layer_views.items()
        }

        out_dict = {"LayerViews": lvs}
        if self.custom_dither_patterns:
            out_dict["CustomDitherPatterns"] = {
                name: dp.dict(
                    exclude_none=True, exclude_defaults=True, exclude_unset=True
                )
                for name, dp in self.custom_dither_patterns.items()
            }
        if self.custom_line_styles:
            out_dict["CustomLineStyles"] = {
                name: ls.dict(
                    exclude_none=True, exclude_defaults=True, exclude_unset=True
                )
                for name, ls in self.custom_line_styles.items()
            }

        lf_path.write_bytes(
            yaml.dump(
                out_dict,
                indent=2,
                sort_keys=False,
                default_flow_style=False,
                encoding="utf-8",
            )
        )

    @staticmethod
    def from_yaml(layer_file: PathType) -> LayerViews:
        """Import layer properties from two yaml files.

        Args:
            layer_file: Name of the file to read LayerViews, CustomDitherPatterns, and CustomLineStyles from.
        """
        layer_file = pathlib.Path(layer_file)
        properties = YAML.load(layer_file.open())

        lvs = {}
        for name, lv in properties["LayerViews"].items():
            if "group_members" in lv:
                lv["group_members"] = {
                    member_name: LayerView(name=member_name, **member_view)
                    for member_name, member_view in lv["group_members"].items()
                }
            lvs[name] = LayerView(name=name, **lv)

        custom_dither_patterns = (
            {
                name: HatchPattern(name=name, **dp)
                for name, dp in properties["CustomDitherPatterns"].items()
            }
            if "CustomDitherPatterns" in properties
            else {}
        )

        custom_line_styles = (
            {
                name: LineStyle(name=name, **ls)
                for name, ls in properties["CustomLineStyles"].items()
            }
            if "CustomLineStyles" in properties
            else {}
        )

        return LayerViews(
            layer_views=lvs,
            custom_dither_patterns=custom_dither_patterns,
            custom_line_styles=custom_line_styles,
        )


def _name_to_short_name(name_str: str) -> str:
    """Maps the name entry of the lyp element to a name of the layer.

    i.e. the dictionary key used to access it.
    Default format of the lyp name are:

        - key - layer/datatype - description
        - key - description

    """
    if name_str is None:
        raise OSError(f"layer {name_str} has no name")
    fields = name_str.split("-")
    name = fields[0].split()[0].strip()
    return clean_name(name, remove_dots=True)


def _name_to_description(name_str) -> str:
    """Gets the description of the layer contained in the lyp name field.

    It is not strictly necessary to have a description. If none there, it returns ''.

    Default format of the lyp name are:

        - key - layer/datatype - description
        - key - description

    """
    if name_str is None:
        raise OSError(f"layer {name_str!r} has no name")
    fields = name_str.split()
    return " ".join(fields[1:]) if len(fields) > 1 else ""


# if __name__ == "__main__":
#     from gdsfactory.config import PATH

#     lys = LayerViews(PATH.klayout_lyp)
#     assert len(lys.layer_views) > 10, len(lys.layer_views)
