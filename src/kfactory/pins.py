from __future__ import annotations

from collections.abc import (
    Iterable,
)
from typing import (
    TYPE_CHECKING,
)

from .port import (
    filter_direction,
    filter_layer,
    filter_orientation,
    filter_port_type,
    filter_regex,
)
from .typings import Angle, TPort

if TYPE_CHECKING:
    from .layer import LayerEnum


__all__ = ["DPorts", "Ports", "ProtoPorts"]


def _filter_ports(
    ports: Iterable[TPort],
    angle: Angle | None = None,
    orientation: float | None = None,
    layer: LayerEnum | int | None = None,
    port_type: str | None = None,
    regex: str | None = None,
) -> list[TPort]:
    if regex:
        ports = filter_regex(ports, regex)
    if layer is not None:
        ports = filter_layer(ports, layer)
    if port_type:
        ports = filter_port_type(ports, port_type)
    if angle is not None:
        ports = filter_direction(ports, angle)
    if orientation is not None:
        ports = filter_orientation(ports, orientation)
    return list(ports)
