from typing import Callable, Dict, Hashable, List, Optional, Union

from .. import kdb
from ..kcell import KCell, Port
from .manhattan import route_manhattan


def connect_elec(
    c: KCell,
    start_port: Port,
    end_port: Port,
    start_straight: Optional[int] = None,
    end_straight: Optional[int] = None,
    route_path_function: Callable[..., list[kdb.Point]] = route_manhattan,
    width: Optional[int] = None,
    layer: Optional[int] = None,
) -> None:

    if width is None:
        width = start_port.width
    if layer is None:
        layer = start_port.layer
    if start_straight is None:
        start_straight = int(width / 2)
    if end_straight is None:
        end_straight = int(width / 2)

    pts = route_path_function(
        start_port.copy(),
        end_port.copy(),
        bend90_radius=0,
        start_straight=start_straight,
        end_straight=end_straight,
        in_dbu=True,
    )

    path = kdb.Path(pts, width)
    c.shapes(layer).insert(path.polygon())
