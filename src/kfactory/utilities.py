from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal

from rich.json import JSON
from rich.table import Table

from . import kdb, lay
from .conf import DEFAULT_TRANS, config

if TYPE_CHECKING:
    from collections.abc import Iterable

    from .instance import Instance
    from .kcell import ProtoTKCell
    from .pin import DPin, Pin
    from .port import Port, ProtoPort
    from .typings import DShapeLike, MarkerConfig


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
    save.write_context_info = config.write_context_info
    save.gds2_write_cell_properties = config.write_cell_properties
    save.gds2_write_file_properties = config.write_file_properties
    save.gds2_write_timestamps = config.write_timestamps
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


def check_inst_ports(p1: Port, p2: Port) -> int:
    """Check if two ports are the same.

    Returns:
        int: A bitwise representation of the differences between the two ports.
    """
    check_int = 0
    if p1.width != p2.width:
        check_int += 1
    if p1.angle != ((p2.angle + 2) % 4):
        check_int += 2
    if p1.port_type != p2.port_type:
        check_int += 4
    return check_int


def check_cell_ports(p1: ProtoPort[Any], p2: ProtoPort[Any]) -> int:
    """Check if two ports are the same.

    Returns:
        int: A bitwise representation of the differences between the two ports.
    """
    from .port import Port

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


def instance_port_name(inst: Instance, port: ProtoPort[Any]) -> str:
    """Create a name for an instance port.

    Args:
        inst: The instance.
        port: The port.
    """
    return f'{inst.name}["{port.name}"]'


def pprint_ports(
    ports: Iterable[ProtoPort[Any]], unit: Literal["dbu", "um"] | None = None
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
    table.add_column("Type")
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
                        port.port_type,
                        f"{port.x:_}",
                        f"{port.y:_}",
                        str(port.angle),
                        str(port.mirror),
                        JSON.from_data(port.info.model_dump()),
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
                        port.port_type,
                        f"{dx:_}",
                        f"{dy:_}",
                        str(angle),
                        str(mirror),
                        JSON.from_data(port.info.model_dump()),
                    )
        case "um":
            for port in ports:
                dport = port.to_dtype()
                t = dport.dcplx_trans
                dx = t.disp.x
                dy = t.disp.y
                dwidth = dport.cross_section.width
                angle = t.angle
                mirror = t.mirror
                table.add_row(
                    str(dport.name) + " [um]",
                    f"{dwidth:_}",
                    dport.kcl.get_info(dport.layer).to_s(),
                    dport.port_type,
                    f"{dx:_}",
                    f"{dy:_}",
                    str(angle),
                    str(mirror),
                    JSON.from_data(dport.info.model_dump()),
                )
        case "dbu":
            for port in ports:
                iport = port.to_itype()
                table.add_row(
                    str(iport.name) + " [dbu]",
                    f"{iport.width:_}",
                    iport.kcl.get_info(iport.layer).to_s(),
                    iport.port_type,
                    f"{iport.x:_}",
                    f"{iport.y:_}",
                    str(iport.angle),
                    str(iport.mirror),
                    JSON.from_data(iport.info.model_dump()),
                )

    return table


def pprint_pins(
    pins: Iterable[Pin] | Iterable[DPin], unit: Literal["dbu", "um"] | None = None
) -> Table:
    """Print ports as a table.

    Args:
        pins: The pins which should be printed.
        unit: Define the print type of the ports. If None, any port
            which can be represented accurately by a dbu representation
            will be printed in dbu otherwise in um. 'dbu'/'um' will force
            the printing to enforce one or the other representation
    """
    table = Table(show_lines=True)

    table.add_column("Name")
    table.add_column("Pin Type")
    table.add_column("Ports")
    table.add_column("Info")

    for pin in pins:
        ports = pprint_ports(pin.ports, unit=unit)
        ports.box = None
        table.add_row(
            str(pin.name),
            str(pin.pin_type),
            ports,
            JSON.from_data(pin.info.model_dump()),
        )

    return table


def as_png_data(
    c: ProtoTKCell[Any],
    layer_properties: str | Path | None = None,
    resolution: tuple[int, int] = (800, 600),
    synchronous: bool = True,
    markers: list[tuple[DShapeLike, MarkerConfig]] | None = None,
) -> bytes:
    """Render a cell to PNG bytes via a headless ``lay.LayoutView``.

    Args:
        c: cell to render.
        layer_properties: optional ``.lyp`` to apply.
        resolution: ``(width, height)`` in pixels.
        synchronous: ``True`` to render synchronously (default), ``False`` to
            return whatever the view currently has.
        markers: optional list of ``(shape, config)`` pairs. Each shape becomes
            a ``lay.Marker`` overlay on the view; ``config`` is the same
            ``MarkerConfig`` dict that `kfactory.show` accepts (``color``,
            ``line_width``, ``halo``, …). When markers are supplied, the view
            zooms to the union of all marker bounding boxes expanded by 10 %
            instead of fitting the full cell.
    """
    layout_view = lay.LayoutView()
    layout_view.show_layout(c.kcl.layout.dup(), False)
    if layer_properties is not None:
        layer_properties = Path(layer_properties)
        if layer_properties.exists() and layer_properties.is_file():
            layout_view.load_layer_props(str(layer_properties))
    elif c.kcl.technology_file is not None:
        layout_view.active_cellview().technology = c.kcl.technology.name
    layout_view.active_cellview().cell = c.kdb_cell
    layout_view.max_hier()
    layout_view.resize(*resolution)
    layout_view.add_missing_layers()

    # Keep marker references alive — klayout drops markers whose Python
    # handle has been garbage-collected before the screenshot is taken.
    marker_refs: list[lay.Marker] = []
    if markers:
        bbox = kdb.DBox()
        for shape, cfg in markers:
            m = lay.Marker(layout_view)
            if isinstance(shape, kdb.DPolygon | kdb.DSimplePolygon):
                m.set_polygon(
                    shape if isinstance(shape, kdb.DPolygon) else kdb.DPolygon(shape)
                )
            elif isinstance(shape, kdb.DBox):
                m.set_box(shape)
            elif isinstance(shape, kdb.DEdge):
                m.set_edge(shape)
            elif isinstance(shape, kdb.DPath):
                m.set_path(shape)
            elif isinstance(shape, kdb.DText):
                m.set_text(shape)
            else:
                continue
            if (color := cfg.get("color")) is not None:
                m.color = color
            if (frame_color := cfg.get("frame_color")) is not None:
                m.frame_color = frame_color
            if (line_width := cfg.get("line_width")) is not None:
                m.line_width = line_width
            if (line_style := cfg.get("line_style")) is not None:
                m.line_style = line_style
            if (halo := cfg.get("halo")) is not None:
                m.halo = halo
            if (vertex_size := cfg.get("vertex_size")) is not None:
                m.vertex_size = vertex_size
            if (dither_pattern := cfg.get("dither_pattern")) is not None:
                m.dither_pattern = dither_pattern
            if (dismissable := cfg.get("dismissable")) is not None:
                m.dismissable = dismissable
            bbox += shape.bbox()
            marker_refs.append(m)

        if not bbox.empty():
            pad_x = bbox.width() * 0.1 or 1.0
            pad_y = bbox.height() * 0.1 or 1.0
            layout_view.zoom_box(bbox.enlarged(pad_x, pad_y))
        else:
            layout_view.zoom_fit()
    else:
        layout_view.zoom_fit()

    if synchronous:
        return layout_view.get_pixels_with_options(
            width=resolution[0], height=resolution[1]
        ).to_png_data()
    return layout_view.get_screenshot_pixels().to_png_data()


def ensure_build_directory(
    subdirectory: str = "mask", create_gitignore: bool = True
) -> Path | None:
    """Ensure build directory exists with proper gitignore.

    This function consolidates all build directory creation logic, including
    git repository detection and .gitignore creation.

    Args:
        subdirectory: Subdirectory under build/ (e.g., 'mask', 'session/kcls').
        create_gitignore: Whether to create .gitignore in build directory.

    Returns:
        Path to the build subdirectory or None if not in a git repo.
    """
    project_dir = config.project_dir
    if not project_dir:
        return None

    build_dir = Path(project_dir) / "build"
    target_dir = build_dir / subdirectory
    target_dir.mkdir(parents=True, exist_ok=True)

    if create_gitignore:
        gitignore_path = build_dir / ".gitignore"
        if not gitignore_path.exists():
            gitignore_path.write_text("*\n")

    return target_dir


def get_build_path(
    filename: str, subdirectory: str = "mask", file_format: str = "gds"
) -> tuple[Path, bool]:
    """Get the appropriate build path for a file.

    Determines whether to use a git-tracked build directory or temp directory,
    and creates necessary directories.

    Args:
        filename: Base filename (without extension).
        subdirectory: Subdirectory under build/ (e.g., 'mask', 'gds', 'oas').
        file_format: File extension/format (e.g., 'gds', 'oas', 'lyrdb').

    Returns:
        Tuple of (file_path, should_delete):
        - If in git repo: returns build directory path, False
        - Otherwise: returns temp directory path, True
    """
    from tempfile import gettempdir

    build_dir = ensure_build_directory(subdirectory)

    if build_dir:
        filepath = build_dir / Path(filename).with_suffix(f".{file_format}")
        filepath.parent.mkdir(parents=True, exist_ok=True)
        return filepath, False
    filepath = Path(gettempdir()) / Path(filename).with_suffix(f".{file_format}")
    filepath.parent.mkdir(parents=True, exist_ok=True)
    return filepath, True


def get_session_directory(custom_dir: Path | None = None) -> Path:
    """Get or create session cache directory.

    Args:
        custom_dir: Optional custom directory override.

    Returns:
        Path to session/kcls directory.
    """
    if custom_dir:
        return custom_dir

    build_dir = ensure_build_directory("session/kcls", create_gitignore=True)
    if build_dir:
        return build_dir
    # Fallback to current directory
    return Path() / "build/session/kcls"
