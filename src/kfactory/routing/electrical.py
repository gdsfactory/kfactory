"""Utilities for automatically routing electrical connections."""

from collections.abc import Callable

from .. import kdb
from ..kcell import Instance, KCell, Port
from .manhattan import route_manhattan


def route_elec(
    c: KCell,
    p1: Port,
    p2: Port,
    start_straight: int | None = None,
    end_straight: int | None = None,
    route_path_function: Callable[..., list[kdb.Point]] = route_manhattan,
    width: int | None = None,
    layer: int | None = None,
) -> None:
    """Connect two ports with a wire.

    A wire is a path object on a usually metal layer.


    Args:
        c: KCell to place the wire in.
        p1: Beginning
        p2: End
        start_straight: Minimum length of straight at start port.
        end_straight: Minimum length of straight at end port.
        route_path_function: Function to calculate the path. Signature:
            `route_path_function(p1, p2, bend90_radius, start_straight,
            end_straight)`
        width: Overwrite the width of the wire. Calculated by the width of the start
            port if `None`.
        layer: Layer to place the wire on. Calculated from the start port if `None`.
    """
    if width is None:
        width = p1.width
    if layer is None:
        layer = p1.layer
    if start_straight is None:
        start_straight = int(width / 2)
    if end_straight is None:
        end_straight = int(width / 2)

    pts = route_path_function(
        p1.copy(),
        p2.copy(),
        bend90_radius=0,
        start_straight=start_straight,
        end_straight=end_straight,
    )

    path = kdb.Path(pts, width)
    c.shapes(layer).insert(path.polygon())


def route_L(
    c: KCell,
    input_ports: list[Port],
    output_orientation: int = 1,
    wire_spacing: int = 10000,
) -> list[Port]:
    """Route ports towards a bundle in an L shape.

    This function takes a list of input ports and assume they are oriented in the west.
    The output will be a list of ports that have the same y coordinates.
    The function will produce a L-shape routing to connect input ports to output ports
    without any crossings.
    """
    input_ports.sort(key=lambda p: p.y)

    y_max = input_ports[-1].y
    y_min = input_ports[0].y
    x_max = max(p.x for p in input_ports)

    output_ports = []
    if output_orientation == 1:
        for i, p in enumerate(input_ports[::-1]):
            temp_port = p.copy()
            temp_port.trans = kdb.Trans(
                3, False, x_max - wire_spacing * (i + 1), y_max + wire_spacing
            )

            route_elec(c, p, temp_port)
            temp_port.trans.angle = 1
            output_ports.append(temp_port)
    elif output_orientation == 3:
        for i, p in enumerate(input_ports):
            temp_port = p.copy()
            temp_port.trans = kdb.Trans(
                1, False, x_max - wire_spacing * (i + 1), y_min - wire_spacing
            )
            route_elec(c, p, temp_port)
            temp_port.trans.angle = 3
            output_ports.append(temp_port)
    else:
        raise ValueError(
            "Invalid L-shape routing. Please change output_orientaion to 1 or 3."
        )
    return output_ports


def route_bundle(
    c: KCell,
    input_ports: list[Port],
    target_ports: list[Port],
    wire_spacing: int = 10000,
) -> None:
    """Connect multiple input ports to output ports.

    This function takes a list of input ports and assume they are all oriented in the
    same direction (could be any of W, S, E, N). The target ports have the opposite
    orientation, i.e. if input ports are oriented to north, and target ports should
    be oriented to south. The function will produce a routing to connect input ports
    to output ports without any crossings.

    Args:
        c: KCell to place the routes in.
        input_ports: List of start ports.
        target_ports: List of end ports.
        wire_spacing: Minimum space between wires. [dbu]
    """
    input_ports.sort(key=lambda p: p.y)

    x_max = max(p.x for p in input_ports)
    x_min = min(p.x for p in input_ports)

    output_ports = []
    input_orientation = input_ports[0].angle if input_ports else 1
    if input_orientation in [1, 3]:
        y_max = input_ports[-1].y
        y_min = input_ports[0].y
        for p in input_ports:
            temp_port = p.copy()
            y_shift = y_max if input_orientation == 1 else y_min
            temp_port.trans = kdb.Trans(4 - input_orientation, False, p.x, y_shift)
            route_elec(c, p, temp_port)
            temp_port.trans.angle = input_orientation
            output_ports.append(temp_port)
        output_ports.sort(key=lambda p: p.x)
        L_count = 0
        R_count = 0
        for i in range(len(output_ports)):
            if target_ports[i].x > output_ports[i].x:
                L_count += 1
                route_elec(
                    c,
                    output_ports[i],
                    target_ports[i],
                    start_straight=abs(target_ports[i].y - output_ports[i].y)
                    - L_count * wire_spacing,
                    end_straight=L_count * wire_spacing,
                )
                R_count = 0
            else:
                R_count += 1
                route_elec(
                    c,
                    output_ports[i],
                    target_ports[i],
                    start_straight=R_count * wire_spacing,
                    end_straight=abs(target_ports[i].y - output_ports[i].y)
                    - R_count * wire_spacing,
                )
                L_count = 0
    else:
        for p in input_ports:
            temp_port = p.copy()
            x_shift = x_max if input_orientation == 0 else x_min
            temp_port.trans = kdb.Trans(2 - input_orientation, False, x_shift, p.y)
            route_elec(c, p, temp_port)
            temp_port.trans.angle = input_orientation
            output_ports.append(temp_port)
        output_ports.sort(key=lambda p: p.y)
        T_count = 0
        B_count = 0
        for i in range(len(output_ports)):
            if target_ports[i].y > output_ports[i].y:
                B_count += 1
                route_elec(
                    c,
                    output_ports[i],
                    target_ports[i],
                    start_straight=abs(target_ports[i].x - output_ports[i].x)
                    - B_count * wire_spacing,
                    end_straight=B_count * wire_spacing,
                )
                T_count = 0
            else:
                T_count += 1
                route_elec(
                    c,
                    output_ports[i],
                    target_ports[i],
                    start_straight=T_count * wire_spacing,
                    end_straight=abs(target_ports[i].y - output_ports[i].y)
                    - T_count * wire_spacing,
                )
                B_count = 0


def get_electrical_ports(c: Instance, port_type: str = "electrical") -> list[Port]:
    """Filter list of an instance by electrical ports."""
    return [p for p in c.ports if p.port_type == port_type]


def route_wire(c: KCell, input_port: Port, output_port: Port) -> None:
    """Connection between two electrical ports *DO NOT USE*.

    This function mainly implements a connection between two electrical ports.
    Not finished yet. Don't use.

    Args:
        c: KCell to place connection in.
        input_port: Start port.
        output_port: End port.
    """
    if (input_port.angle + output_port.angle) % 2 == 0:
        (
            kdb.Point(input_port.x, input_port.y - input_port.width // 2)
            if input_port.angle % 2 == 0
            else kdb.Point(input_port.x - input_port.width // 2, input_port.y)
        )
        (
            kdb.Point(
                (input_port.x + output_port.x) // 2,
                input_port.y + input_port.width // 2,
            )
            if input_port.angle % 2 == 0
            else kdb.Point(
                input_port.x - input_port.width // 2, (input_port.y + output_port.y)
            )
        )
        (
            kdb.Point(output_port.x, output_port.y + input_port.width // 2)
            if input_port.angle % 2 == 0
            else kdb.Point(output_port.x + input_port.width // 2, output_port.y)
        )


def route_dual_rails(
    c: KCell,
    p1: Port,
    p2: Port,
    start_straight: int | None = None,
    end_straight: int | None = None,
    route_path_function: Callable[..., list[kdb.Point]] = route_manhattan,
    width: int | None = None,
    hole_width: int | None = None,
    layer: int | None = None,
) -> None:
    """Connect ports with a dual-wire rail.

    Args:
        c: KCell to place the connection in.
        p1: Start port.
        p2: End port.
        start_straight: Minimum straight after the start port.
        end_straight: Minimum straight before end port.
        route_path_function: Function to calculate the path. Signature:
            `route_path_function(p1, p2, bend90_radius, start_straight,
            end_straight)`
        width: Width of the rail (total). [dbu]
        hole_width: Width of the space between the rails. [dbu]
        layer: layer to place the rail in.
    """
    _width = width or p1.width
    _hole_width = hole_width or p1.width // 2
    _layer = layer or p1.layer
    _start_straight = start_straight or _width // 2
    _end_straight = end_straight or _width // 2

    pts = route_path_function(
        p1.copy(),
        p2.copy(),
        bend90_radius=0,
        start_straight=start_straight,
        end_straight=end_straight,
    )

    path = kdb.Path(pts, _width)
    hole_path = kdb.Path(pts, _hole_width)
    final_poly = kdb.Region(path.polygon()) - kdb.Region(hole_path.polygon())
    c.shapes(_layer).insert(final_poly)
