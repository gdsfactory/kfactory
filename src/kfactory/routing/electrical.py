from typing import Callable, Optional

from .. import kdb
from ..kcell import DCplxPort, Instance, KCell, Port
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


def connect_L_route(
    c: KCell,
    input_ports: list[Port],
    output_orientation: int = 1,
    wire_spacing: int = 10000,
) -> list[Port]:
    """
    This function takes a list of input ports and assume they are oriented in the west.
    The output will be a list of ports that have the same y coordinates.
    The function will produce a L-shape routing to connect input ports to output ports without any crossings.
    """
    input_ports.sort(key=lambda p: p.y)

    y_max = input_ports[-1].y
    y_min = input_ports[0].y
    x_max = max(p.x for p in input_ports)
    # x_min = min([p.x for p in input_ports])

    output_ports = []
    if output_orientation == 1:
        for i, p in enumerate(input_ports[::-1]):
            temp_port = p.copy()
            # temp_port.trans.disp = kf.kdb.Vector(
            #     x_max - wire_spacing * (i + 1), y_max + wire_spacing
            # )
            # temp_port.trans.angle = 3
            temp_port.trans = kdb.Trans(
                3, False, x_max - wire_spacing * (i + 1), y_max + wire_spacing
            )

            connect_elec(c, p, temp_port)
            temp_port.trans.angle = 1
            output_ports.append(temp_port)
    elif output_orientation == 3:
        for i, p in enumerate(input_ports):
            temp_port = p.copy()
            temp_port.trans = kdb.Trans(
                1, False, x_max - wire_spacing * (i + 1), y_min - wire_spacing
            )
            connect_elec(c, p, temp_port)
            temp_port.trans.angle = 3
            output_ports.append(temp_port)
    else:
        raise ValueError(
            "Invalid L-shape routing. Please change output_orientaion to 1 or 3."
        )
    return output_ports


def connect_bundle(
    c: KCell,
    input_ports: list[Port],
    target_ports: list[Port],
    wire_spacing: int = 10000,
) -> None:
    """
    This function takes a list of input ports and assume they are all oriented in the same direction (could be any of W, S, E, N).
    The target ports have the opposite orientation, i.e. if input ports are oriented to north, and target ports should be oriented to south.
    The function will produce a routing to connect input ports to output ports without any crossings.
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
            connect_elec(c, p, temp_port)
            temp_port.trans.angle = input_orientation
            output_ports.append(temp_port)
        output_ports.sort(key=lambda p: p.x)
        L_count = 0
        R_count = 0
        for i in range(len(output_ports)):
            if target_ports[i].x > output_ports[i].x:
                L_count += 1
                connect_elec(
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
                connect_elec(
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
            connect_elec(c, p, temp_port)
            temp_port.trans.angle = input_orientation
            output_ports.append(temp_port)
        output_ports.sort(key=lambda p: p.y)
        T_count = 0
        B_count = 0
        for i in range(len(output_ports)):
            if target_ports[i].y > output_ports[i].y:
                B_count += 1
                connect_elec(
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
                connect_elec(
                    c,
                    output_ports[i],
                    target_ports[i],
                    start_straight=T_count * wire_spacing,
                    end_straight=abs(target_ports[i].y - output_ports[i].y)
                    - T_count * wire_spacing,
                )
                B_count = 0


def get_electrical_ports(c: Instance) -> list[Port | DCplxPort]:
    return [p for p in c.ports.get_all().values() if p.port_type == "electrical"]


def connect_wire(c: KCell, input_port: Port, output_port: Port) -> None:
    """
    This function mainly implements a connection between two electrical ports.
    Not finished yet. Don't use.
    Args:
        input port: kf.Port
        output port: kf.Port
    """
    if (input_port.angle + output_port.angle) % 2 == 0:
        left_corner = (
            kdb.Point(input_port.x, input_port.y - input_port.width // 2)
            if input_port.angle % 2 == 0
            else kdb.Point(input_port.x - input_port.width // 2, input_port.y)
        )
        middle_top = (
            kdb.Point(
                (input_port.x + output_port.x) // 2,
                input_port.y + input_port.width // 2,
            )
            if input_port.angle % 2 == 0
            else kdb.Point(
                input_port.x - input_port.width // 2, (input_port.y + output_port.y)
            )
        )
        right_corner = (
            kdb.Point(output_port.x, output_port.y + input_port.width // 2)
            if input_port.angle % 2 == 0
            else kdb.Point(output_port.x + input_port.width // 2, output_port.y)
        )


def connect_dual_rails(
    c: KCell,
    start_port: Port,
    end_port: Port,
    start_straight: Optional[int] = None,
    end_straight: Optional[int] = None,
    route_path_function: Callable[..., list[kdb.Point]] = route_manhattan,
    width: Optional[int] = None,
    hole_width: Optional[int] = None,
    layer: Optional[int] = None,
) -> None:

    if width is None:
        width = start_port.width
    if hole_width is None:
        hole_width = start_port.width // 2
    if layer is None:
        layer = start_port.layer
    if start_straight is None:
        start_straight = width // 2
    if end_straight is None:
        end_straight = width // 2

    pts = route_path_function(
        start_port.copy(),
        end_port.copy(),
        bend90_radius=0,
        start_straight=start_straight,
        end_straight=end_straight,
        in_dbu=True,
    )

    path = kdb.Path(pts, width)
    hole_path = kdb.Path(pts, hole_width)
    final_poly = kdb.Region(path.polygon()) - kdb.Region(hole_path.polygon())
    c.shapes(layer).insert(final_poly)
