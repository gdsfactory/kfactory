from __future__ import annotations

from collections.abc import Iterable
from typing import TYPE_CHECKING, Any, Literal

import rich
from rich.table import Table

from . import kdb
from .config import DEFAULT_TRANS, config

if TYPE_CHECKING:
    from .instance import Instance
    from .port import Port, ProtoPort


def load_layout_options(**attributes: Any) -> kdb.LoadLayoutOptions:
    """Default options for loading GDS/OAS.

    Args:
        attributes: Set attributes of the layout load option object. E.g. to set the
            handling of cell name conflicts pass
            `cell_conflict_resolution=kdb.LoadLayoutOptions.CellConflictResolution.OverwriteCell`.
    """
    load = kdb.LoadLayoutOptions()

    load.cell_conflict_resolution = (
        kdb.LoadLayoutOptions.CellConflictResolution.SkipNewCell
    )
    for k, v in attributes.items():
        setattr(load, k, v)

    return load


def save_layout_options(**attributes: Any) -> kdb.SaveLayoutOptions:
    """Default options for saving GDS/OAS.

    Args:
        attributes: Set attributes of the layout save option object. E.g. to save the
            gds without metadata pass `write_context_info=False`
    """
    save = kdb.SaveLayoutOptions()
    save.gds2_write_cell_properties = True
    save.gds2_write_file_properties = True
    save.gds2_write_timestamps = False
    save.write_context_info = config.write_context_info
    save.gds2_max_cellname_length = config.max_cellname_length

    for k, v in attributes.items():
        setattr(save, k, v)

    return save


def update_default_trans(
    new_trans: dict[str, str | int | float | dict[str, str | int | float]],
) -> None:
    """Allows to change the default transformation for reading a yaml file."""
    DEFAULT_TRANS.update(new_trans)


def polygon_from_array(array: Iterable[tuple[int, int]]) -> kdb.Polygon:
    """Create a DPolygon from a 2D array-like structure. (dbu version).

    Array-like: `[[x1,y1],[x2,y2],...]`
    """
    return kdb.Polygon([kdb.Point(int(x), int(y)) for (x, y) in array])


def dpolygon_from_array(array: Iterable[tuple[float, float]]) -> kdb.DPolygon:
    """Create a DPolygon from a 2D array-like structure. (um version).

    Array-like: `[[x1,y1],[x2,y2],...]`
    """
    return kdb.DPolygon([kdb.DPoint(x, y) for (x, y) in array])


def _check_inst_ports(p1: Port, p2: Port) -> int:
    check_int = 0
    if p1.width != p2.width:
        check_int += 1
    if p1.angle != ((p2.angle + 2) % 4):
        check_int += 2
    if p1.port_type != p2.port_type:
        check_int += 4
    return check_int


def _check_cell_ports(p1: ProtoPort[Any], p2: ProtoPort[Any]) -> int:
    p1_ = Port(base=p1.base)
    p2_ = Port(base=p2.base)
    check_int = 0
    if p1_.width != p2_.width:
        check_int += 1
    if p1_.angle != p2_.angle:
        check_int += 2
    if p1_.port_type != p2_.port_type:
        check_int += 4
    return check_int


def _instance_port_name(inst: Instance, port: Port) -> str:
    return f'{inst.name}["{port.name or str(None)}"]'


def pprint_ports(
    ports: Iterable[ProtoPort[Any]], unit: Literal["dbu", "um", None] = None
) -> Table:
    """Print ports as a table.

    Args:
        ports: The ports which should be printed.
        unit: Define the print type of the ports. If None, any port
            which can be represented accurately by a dbu representation
            will be printed in dbu otherwise in um. 'dbu'/'um' will force
            the printing to enforce one or the other representation
    """
    table = Table(show_lines=True)

    table.add_column("Name")
    table.add_column("Width")
    table.add_column("Layer")
    table.add_column("X")
    table.add_column("Y")
    table.add_column("Angle")
    table.add_column("Mirror")
    table.add_column("Info")

    match unit:
        case None:
            for port in ports:
                if port.base.trans is not None:
                    table.add_row(
                        str(port.name) + " [dbu]",
                        f"{port.width:_}",
                        port.kcl.get_info(port.layer).to_s(),
                        f"{port.x:_}",
                        f"{port.y:_}",
                        str(port.angle),
                        str(port.mirror),
                        rich.json.JSON.from_data(port.info.model_dump()),
                    )
                else:
                    t = port.dcplx_trans
                    dx = t.disp.x
                    dy = t.disp.y
                    dwidth = port.kcl.to_um(port.cross_section.width)
                    angle = t.angle
                    mirror = t.mirror
                    table.add_row(
                        str(port.name) + " [um]",
                        f"{dwidth:_}",
                        port.kcl.get_info(port.layer).to_s(),
                        f"{dx:_}",
                        f"{dy:_}",
                        str(angle),
                        str(mirror),
                        rich.json.JSON.from_data(port.info.model_dump()),
                    )
        case "um":
            for port in ports:
                t = port.dcplx_trans
                dx = t.disp.x
                dy = t.disp.y
                dwidth = port.kcl.to_um(port.cross_section.width)
                angle = t.angle
                mirror = t.mirror
                table.add_row(
                    str(port.name) + " [um]",
                    f"{dwidth:_}",
                    port.kcl.get_info(port.layer).to_s(),
                    f"{dx:_}",
                    f"{dy:_}",
                    str(angle),
                    str(mirror),
                    rich.json.JSON.from_data(port.info.model_dump()),
                )
        case "dbu":
            for port in ports:
                table.add_row(
                    str(port.name) + " [dbu]",
                    f"{port.width:_}",
                    port.kcl.get_info(port.layer).to_s(),
                    f"{port.x:_}",
                    f"{port.y:_}",
                    str(port.angle),
                    str(port.mirror),
                    rich.json.JSON.from_data(port.info.model_dump()),
                )

    return table
