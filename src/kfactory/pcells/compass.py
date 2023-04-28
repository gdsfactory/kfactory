from __future__ import annotations

from kfactory import KCell, LayerEnum, klib
import kfactory as kf


@kf.pcell
def compass(
    size=(4.0, 2.0),
    layer: int | LayerEnum = 1,
    port_type: None | str = "placement",
    port_inclusion: float = 0.0,
    port_angles=(180, 90, 0, -90),
) -> kf.KCell:
    """Rectangle with ports on each edge (north, south, east, and west).

    Args:
        size: rectangle size.
        layer: tuple (int, int).
        port_type: optical, electrical.
        port_inclusion: from edge.
        port_angles: list of port_angles to add. None add one port only.
    """
    c = kf.KCell()
    dx, dy = size

    points = [
        [-dx / 2.0, -dy / 2.0],
        [-dx / 2.0, dy / 2],
        [dx / 2, dy / 2],
        [dx / 2, -dy / 2.0],
    ]

    c.add_polygon(points, layer=layer)

    if port_type:
        if 180 in port_angles:
            c.create_port(
                name="e1",
                position=(-dx / 2 + port_inclusion, 0),
                width=dy,
                angle=180,
                layer=layer,
                port_type=port_type,
            )
        if 90 in port_angles:
            c.create_port(
                name="e2",
                position=(0, dy / 2 - port_inclusion),
                width=dx,
                angle=90,
                layer=layer,
                port_type=port_type,
            )
        if 0 in port_angles:
            c.create_port(
                name="e3",
                position=(dx / 2 - port_inclusion, 0),
                width=dy,
                angle=0,
                layer=layer,
                port_type=port_type,
            )
        if -90 in port_angles:
            c.create_port(
                name="e4",
                position=(0, -dy / 2 + port_inclusion),
                width=dx,
                angle=-90,
                layer=layer,
                port_type=port_type,
            )
        if port_angles is None:
            c.create_port(
                name="pad",
                position=(0, 0),
                width=dy,
                angle=None,
                layer=layer,
                port_type=port_type,
            )

    return c


if __name__ == "__main__":
    c = compass(size=(1, 2), layer=1)
    c.show()
