from typing import Any

from pydantic import BaseModel, Field

from .. import kdb


class RouteDebug(BaseModel, arbitrary_types_allowed=True):
    fan_in_region: kdb.Region = Field(default_factory=kdb.Region)
    fan_out_region: kdb.Region = Field(default_factory=kdb.Region)
    waypoints_region: kdb.Region = Field(default_factory=kdb.Region)

    def model_post_init(self, context: Any) -> None:
        self.fan_in_region.merged_semantics = False
        self.fan_out_region.merged_semantics = False
        self.waypoints_region.merged_semantics = False

    def to_dict(self) -> dict[str, str]:
        return {name: value.to_s() for name, value in iter(self)}
