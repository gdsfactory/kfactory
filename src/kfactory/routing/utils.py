import contextlib
from typing import Any

from pydantic import BaseModel, Field

from .. import kdb
from ..typings import DShapeLike, MarkerConfig

default_fanin_color = 0x19B058
default_waypoints_color = 0xB07419
default_fanout_color = 0x1921B0


class RouteDebug(BaseModel, arbitrary_types_allowed=True):
    fan_in_region: kdb.Region = Field(default_factory=kdb.Region)
    fan_in_marker_config: MarkerConfig = Field(
        default=MarkerConfig(
            color=default_fanin_color,
            dismissable=True,
            dither_pattern=0,
            halo=-1,
            frame_color=default_fanin_color,
            line_style=0,
            line_width=1,
            vertex_size=1,
        )
    )
    fan_out_region: kdb.Region = Field(default_factory=kdb.Region)
    fan_out_marker_config: MarkerConfig = Field(
        default=MarkerConfig(
            color=default_fanout_color,
            dismissable=True,
            dither_pattern=0,
            halo=-1,
            frame_color=default_fanout_color,
            line_style=0,
            line_width=1,
            vertex_size=1,
        )
    )
    waypoints_region: kdb.Region = Field(default_factory=kdb.Region)
    waypoints_marker_config: MarkerConfig = Field(
        default=MarkerConfig(
            color=default_fanin_color,
            dismissable=True,
            dither_pattern=0,
            halo=-1,
            frame_color=default_waypoints_color,
            line_style=0,
            line_width=1,
            vertex_size=1,
        )
    )

    def model_post_init(self, context: Any) -> None:
        self.fan_in_region.merged_semantics = False
        self.fan_out_region.merged_semantics = False
        self.waypoints_region.merged_semantics = False

    def to_dict(self) -> dict[str, str]:
        return {name: value.to_s() for name, value in iter(self)}

    def to_markers(self, dbu: float) -> list[tuple[DShapeLike, MarkerConfig]]:
        marker_list = []
        for poly in self.fan_in_region.each():
            marker_list.append((poly.to_dtype(dbu), self.fan_in_marker_config))
            for prop in poly.properties().values():
                with contextlib.suppress(Exception):
                    text = kdb.Text.from_s(prop).to_dtype(dbu)
                    marker_list.append((text, self.fan_in_marker_config))
        for poly in self.fan_out_region.each():
            marker_list.append((poly.to_dtype(dbu), self.fan_out_marker_config))
            for prop in poly.properties().values():
                with contextlib.suppress(Exception):
                    text = kdb.Text.from_s(prop).to_dtype(dbu)
                    marker_list.append((text, self.fan_out_marker_config))
        for poly in self.waypoints_region.each():
            marker_list.append((poly.to_dtype(dbu), self.waypoints_marker_config))
            for prop in poly.properties().values():
                with contextlib.suppress(Exception):
                    text = kdb.Text.from_s(prop).to_dtype(dbu)
                    marker_list.append((text, self.waypoints_marker_config))

        return marker_list
