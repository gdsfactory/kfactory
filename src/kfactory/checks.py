"""Standalone connectivity / overlap checks producing klayout ReportDatabases.

Each check answers a single conceptual question and writes its findings to an
`rdb.ReportDatabase`. They are composed by [`ProtoTKCell.connectivity_check`]
[kfactory.kcell.ProtoTKCell.connectivity_check] for the all-in-one pass-or-fail
verification, but can be called individually for narrower checks.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from kfnetlist import PortCheck, check_connection

from . import kdb, rdb
from .layer import LayerEnum
from .port import create_port_error, port_polygon
from .ports import Ports

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable

    from .instance import ProtoTInstance
    from .kcell import KCell, ProtoTKCell
    from .port import Port, ProtoPort


__all__ = [
    "dangling_ports_check",
    "instance_overlap_check",
    "port_mismatch_check",
    "shape_instance_overlap_check",
]


type CellPortMap = dict[int, dict[tuple[float, float], list[ProtoPort[Any]]]]
type InstPortMap = dict[
    LayerEnum | int,
    dict[tuple[int, int], list[tuple[Port, KCell, str, ProtoTInstance[Any]]]],
]


def _layer_cat_factory(
    db: rdb.ReportDatabase, cell: ProtoTKCell[Any]
) -> Callable[[int], rdb.RdbCategory]:
    """Return a memoised helper that maps a layer index to its RDB category."""
    layer_cats: dict[int, rdb.RdbCategory] = {}

    def layer_cat(layer: int) -> rdb.RdbCategory:
        if layer not in layer_cats:
            if isinstance(layer, LayerEnum):
                ln = str(layer.name)
            else:
                li = cell.kcl.get_info(layer)
                ln = str(li).replace("/", "_")
            layer_cats[layer] = db.category_by_path(ln) or db.create_category(ln)
        return layer_cats[layer]

    return layer_cat


def _get_or_create_subcategory(
    db: rdb.ReportDatabase, parent: rdb.RdbCategory, name: str
) -> rdb.RdbCategory:
    return db.category_by_path(f"{parent.path()}.{name}") or db.create_category(
        parent, name
    )


def _port_polygon_um(cell: ProtoTKCell[Any], port: ProtoPort[Any]) -> kdb.DPolygon:
    if port.base.trans:
        return cell.kcl.to_um(port_polygon(port.iwidth).transformed(port.trans))
    return cell.kcl.to_um(port_polygon(port.iwidth)).transformed(port.dcplx_trans)


def _collect_cell_ports(
    cell: ProtoTKCell[Any],
    port_types: list[str],
    layers: list[int],
) -> CellPortMap:
    """Build the layer -> coord -> [cell ports] mapping used by port checks."""
    cell_ports: CellPortMap = {}
    for port in Ports(kcl=cell.kcl, bases=cell.ports.bases):
        if (port_types and port.port_type not in port_types) or (
            layers and port.layer not in layers
        ):
            continue
        xy = (port.x, port.y)
        cell_ports.setdefault(port.layer, {}).setdefault(xy, []).append(port)
    return cell_ports


def _collect_inst_ports(
    cell: ProtoTKCell[Any],
    port_types: list[str],
    layers: list[int],
) -> InstPortMap:
    """Build the layer -> coord -> [(port, inst_cell, inst_name, inst)] mapping."""
    inst_ports: InstPortMap = {}
    for inst in cell.insts:
        inst_name = inst.name
        inst_cell = inst.cell.to_itype()
        for port in Ports(kcl=cell.kcl, bases=[p.base for p in inst.ports]):
            if (port_types and port.port_type not in port_types) or (
                layers and port.layer not in layers
            ):
                continue
            xy = (port.x, port.y)
            inst_ports.setdefault(port.layer, {}).setdefault(xy, []).append(
                (port, inst_cell, inst_name, inst)
            )
    return inst_ports


def _recurse(
    cell: ProtoTKCell[Any],
    db: rdb.ReportDatabase,
    check: Callable[..., rdb.ReportDatabase],
    **kwargs: Any,
) -> None:
    """Run `check` on every called child cell, bottom-up, with recursive=False."""
    called = cell.called_cells()
    for c in cell.kcl.each_cell_bottom_up():
        if c in called:
            check(cell.kcl[c], db=db, recursive=False, **kwargs)


def _ensure_db(
    cell: ProtoTKCell[Any], db: rdb.ReportDatabase | None, label: str
) -> rdb.ReportDatabase:
    return db or rdb.ReportDatabase(f"{label} {cell.name}")


# ---------------------------------------------------------------------------
# Port mismatch check (width / angle / type / port_overlap / physical-shape)
# ---------------------------------------------------------------------------


def _emit_cell_port(
    cell: ProtoTKCell[Any],
    db: rdb.ReportDatabase,
    db_cell: rdb.RdbCell,
    layer_cat: Callable[[int], rdb.RdbCategory],
    port: ProtoPort[Any],
) -> None:
    c_cat = _get_or_create_subcategory(db, layer_cat(port.layer), "CellPorts")
    it = db.create_item(db_cell, c_cat)
    if port.name:
        it.add_value(f"Port name: {port.name}")
    it.add_value(_port_polygon_um(cell, port))


def _emit_physical_shape_issue(
    cell: ProtoTKCell[Any],
    db: rdb.ReportDatabase,
    db_cell: rdb.RdbCell,
    layer_cat: Callable[[int], rdb.RdbCategory],
    port: ProtoPort[Any],
    *,
    partial: kdb.Edges | None,
) -> None:
    if partial is not None:
        cat = _get_or_create_subcategory(
            db, layer_cat(port.layer), "PartialPhysicalShape"
        )
        it = db.create_item(db_cell, cat)
        it.add_value(
            "Insufficient overlap, partial overlap with polygon of"
            f" {(partial[0].p1 - partial[0].p2).abs()}/{port.width}"
        )
    else:
        cat = _get_or_create_subcategory(
            db, layer_cat(port.layer), "MissingPhysicalShape"
        )
        it = db.create_item(db_cell, cat)
        it.add_value(f"Found no overlapping Edge with Port {port.name or str(port)}")
    it.add_value(_port_polygon_um(cell, port))


def _check_cell_port_physical_shape(
    cell: ProtoTKCell[Any], port: ProtoPort[Any]
) -> tuple[bool, kdb.Edges | None]:
    """Returns (is_ok, partial_overlap_or_none).

    `partial_overlap_or_none` is non-None iff there is some overlap but it is
    insufficient. is_ok=True iff a full port-edge overlap is found.
    """
    rec_it = kdb.RecursiveShapeIterator(
        cell.kcl.layout,
        cell._base.kdb_cell,
        port.layer,
        kdb.Box(2, port.width).transformed(port.trans),
    )
    edges = kdb.Region(rec_it).merge().edges().merge()
    port_edge = kdb.Edge(0, port.width // 2, 0, -port.width // 2)
    if port.base.trans:
        port_edge = port_edge.transformed(port.trans)
    else:
        port_edge = port_edge.transformed(
            kdb.ICplxTrans(port.dcplx_trans, cell.kcl.dbu)
        )
    p_edges = kdb.Edges([port_edge])
    phys_overlap = p_edges & edges
    if phys_overlap.is_empty():
        return False, None
    if phys_overlap[0] != port_edge:
        return False, phys_overlap
    return True, None


def _emit_port_overlap(
    cell: ProtoTKCell[Any],
    db: rdb.ReportDatabase,
    db_cell: rdb.RdbCell,
    layer_cat_for_layer: rdb.RdbCategory,
    ports: list[tuple[Port, KCell, str, ProtoTInstance[Any]]],
    cell_port_at_coord: ProtoPort[Any] | None,
) -> None:
    cat = _get_or_create_subcategory(db, layer_cat_for_layer, "PortOverlap")
    it = db.create_item(db_cell, cat)
    text = "Port Names: "
    values: list[rdb.RdbItemValue] = []
    if cell_port_at_coord is not None:
        text += (
            f"{cell.name}.{cell_port_at_coord.name or cell_port_at_coord.trans.to_s()}/"
        )
        values.append(rdb.RdbItemValue(_port_polygon_um(cell, cell_port_at_coord)))
    for _port, _cell, _inst_name, _inst in ports:
        label = f"{_inst_name}." if _inst_name else f"{_cell.name}."
        text += f"{label}{_port.name or _port.trans.to_s()}/"
        values.append(
            rdb.RdbItemValue(
                cell.kcl.to_um(port_polygon(_port.width).transformed(_port.trans))
            )
        )
    it.add_value(text[:-1])
    for value in values:
        it.add_value(value)


def _resolve_layer_indexes(
    kcl: Any, layers: Iterable[int | kdb.LayerInfo | str] | None
) -> set[int]:
    """Resolve mixed-spec layers (int / LayerInfo / name) to int indexes."""
    if not layers:
        return set()
    out: set[int] = set()
    for spec in layers:
        if isinstance(spec, int):
            out.add(spec)
        elif isinstance(spec, kdb.LayerInfo):
            out.add(kcl.layout.layer(spec))
        else:
            out.add(kcl.find_layer(spec))
    return out


def port_mismatch_check(
    cell: ProtoTKCell[Any],
    *,
    port_types: list[str] | None = None,
    layers: list[int] | None = None,
    db: rdb.ReportDatabase | None = None,
    recursive: bool = True,
    add_cell_ports: bool = False,
    check_width: bool = True,
    check_angle: bool = True,
    check_type: bool = True,
    check_port_overlap: bool = True,
    check_missing_physical_shape: bool = True,
    check_partial_physical_shape: bool = True,
    width_mismatch_ignore_layers: list[int | kdb.LayerInfo | str] | None = None,
) -> rdb.ReportDatabase:
    """Report port-pair / port-shape mismatches as one logical check.

    Aggregates width / angle / port-type mismatches between coincident ports,
    >2-port overlaps, and missing/partial physical layer shapes under the port
    region. Individual sub-rules can be toggled, but this is one connectivity
    check producing one pass/fail outcome for the cell.

    Args:
        cell: Cell to verify.
        port_types: If given, only ports whose `port_type` is in this list are
            considered.
        layers: If given, only ports on these layers are considered.
        db: Reuse an existing report database. A new one is created otherwise.
        recursive: Run the same check on every called child cell as well.
        add_cell_ports: Add a `CellPorts` category listing the cell's own
            (filtered) ports for visual inspection in the report.
        check_width: Emit `WidthMismatch` items.
        check_angle: Emit `AngleMismatch` items.
        check_type: Emit `TypeMismatch` items.
        check_port_overlap: Emit `PortOverlap` items when 2+ instance ports
            share a coord (and either differ from a cell port or pile up >2).
        check_missing_physical_shape: Emit `MissingPhysicalShape` items.
        check_partial_physical_shape: Emit `PartialPhysicalShape` items.
        width_mismatch_ignore_layers: Layers (specified by int index,
            ``kdb.LayerInfo`` or name) on which ``WidthMismatch`` items should
            be suppressed. Useful for metal stacks where mismatched widths at
            a via stack are intentional.
    """
    port_types = port_types or []
    layers = layers or []
    db_ = _ensure_db(cell, db, "Port Mismatch Check")
    ignore_width_layers = _resolve_layer_indexes(cell.kcl, width_mismatch_ignore_layers)
    if recursive:
        _recurse(
            cell,
            db_,
            port_mismatch_check,
            port_types=port_types,
            layers=layers,
            add_cell_ports=add_cell_ports,
            check_width=check_width,
            check_angle=check_angle,
            check_type=check_type,
            check_port_overlap=check_port_overlap,
            check_missing_physical_shape=check_missing_physical_shape,
            check_partial_physical_shape=check_partial_physical_shape,
            width_mismatch_ignore_layers=width_mismatch_ignore_layers,
        )

    db_cell = db_.create_cell(cell.name)
    layer_cat = _layer_cat_factory(db_, cell)
    cell_ports = _collect_cell_ports(cell, port_types, layers)

    # Cell-port physical-shape pass + optional CellPorts annotation.
    for by_coord in cell_ports.values():
        for cell_port_list in by_coord.values():
            for port in cell_port_list:
                if add_cell_ports:
                    _emit_cell_port(cell, db_, db_cell, layer_cat, port)
                if not (check_missing_physical_shape or check_partial_physical_shape):
                    continue
                ok, partial = _check_cell_port_physical_shape(cell, port)
                if ok:
                    continue
                if partial is not None and check_partial_physical_shape:
                    _emit_physical_shape_issue(
                        cell, db_, db_cell, layer_cat, port, partial=partial
                    )
                elif partial is None and check_missing_physical_shape:
                    _emit_physical_shape_issue(
                        cell, db_, db_cell, layer_cat, port, partial=None
                    )

    inst_ports = _collect_inst_ports(cell, port_types, layers)

    def emit_mismatch(
        result: int,
        lc: rdb.RdbCategory,
        p_a: Port,
        p_b: ProtoPort[Any],
        c_a: ProtoTKCell[Any],
        c_b: ProtoTKCell[Any],
        *,
        expect_opposite: bool,
        inst_name1: str | None,
        inst_name2: str | None = None,
    ) -> None:
        angle_ok = bool(
            result & (PortCheck.opposite if expect_opposite else PortCheck.same)
        )
        if (
            check_width
            and not result & PortCheck.width
            and layer not in ignore_width_layers
        ):
            subc = _get_or_create_subcategory(db_, lc, "WidthMismatch")
            create_port_error(
                p_a,
                p_b,
                c_a,
                c_b,
                db_,
                db_cell,
                subc,
                cell.kcl.dbu,
                inst_name1=inst_name1,
                inst_name2=inst_name2,
            )
        if check_angle and not angle_ok:
            subc = _get_or_create_subcategory(db_, lc, "AngleMismatch")
            create_port_error(
                p_a,
                p_b,
                c_a,
                c_b,
                db_,
                db_cell,
                subc,
                cell.kcl.dbu,
                inst_name1=inst_name1,
                inst_name2=inst_name2,
            )
        if check_type and not result & PortCheck.port_type:
            subc = _get_or_create_subcategory(db_, lc, "TypeMismatch")
            create_port_error(
                p_a,
                p_b,
                c_a,
                c_b,
                db_,
                db_cell,
                subc,
                cell.kcl.dbu,
                inst_name1=inst_name1,
                inst_name2=inst_name2,
            )

    for layer, coord_map in inst_ports.items():
        lc = layer_cat(layer)
        for coord, ports in coord_map.items():
            n = len(ports)
            if n == 1:
                if layer in cell_ports and coord in cell_ports[layer]:
                    cell_port = cell_ports[layer][coord][0]
                    result = check_connection(cell_port, ports[0][0])
                    emit_mismatch(
                        result,
                        lc,
                        ports[0][0],
                        cell_port,
                        ports[0][1],
                        cell,
                        expect_opposite=False,
                        inst_name1=ports[0][2],
                    )
                # Dangling case is handled by dangling_ports_check.
            elif n == 2:
                result = check_connection(ports[0][0], ports[1][0])
                emit_mismatch(
                    result,
                    lc,
                    ports[0][0],
                    ports[1][0],
                    ports[0][1],
                    ports[1][1],
                    expect_opposite=True,
                    inst_name1=ports[0][2],
                    inst_name2=ports[1][2],
                )
                if (
                    check_port_overlap
                    and layer in cell_ports
                    and coord in cell_ports[layer]
                ):
                    _emit_port_overlap(
                        cell,
                        db_,
                        db_cell,
                        lc,
                        ports,
                        cell_port_at_coord=cell_ports[layer][coord][0],
                    )
            elif n > 2:
                if check_port_overlap:
                    _emit_port_overlap(
                        cell, db_, db_cell, lc, ports, cell_port_at_coord=None
                    )
            else:
                raise ValueError(f"Unexpected number of ports: {n}")

    return db_


# ---------------------------------------------------------------------------
# Dangling ports check (formerly OrphanPort)
# ---------------------------------------------------------------------------


def _resolve_equivalent_group(
    equivalent_ports: dict[str, list[list[str]]] | None,
    port_cell: ProtoTKCell[Any],
    port_name: str,
) -> set[str] | None:
    """Return the equivalent-port group containing ``port_name`` on ``port_cell``.

    Looks up ``equivalent_ports`` first by ``port_cell.name``, then by its
    ``factory_name`` if available — so callers can key the dict by either the
    concrete cell name or the factory's canonical name. Returns ``None`` if
    no group is found or the port is not in any declared group.
    """
    if not equivalent_ports:
        return None
    groups = equivalent_ports.get(port_cell.name)
    if groups is None and port_cell.has_factory_name():
        groups = equivalent_ports.get(port_cell.factory_name)
    if not groups:
        return None
    for g in groups:
        if port_name in g:
            return set(g)
    return None


def _is_coord_connected(
    layer: int,
    coord: tuple[int, int],
    cell_ports: CellPortMap,
    inst_ports: InstPortMap,
) -> bool:
    """A coord is 'connected' if a cell port or a second instance port lives there."""
    if layer in cell_ports and coord in cell_ports[layer]:
        return True
    return len(inst_ports.get(layer, {}).get(coord, [])) > 1


def _array_element_for_port(
    inst: Any, kcl: Any, port_name: str, port_coord: tuple[int, int]
) -> tuple[int, int] | None:
    """For an array inst, locate the (ia, ib) whose port_name lands at port_coord.

    Returns None for non-array instances (caller treats as the single element).
    """
    if not inst.na or not inst.nb:
        return None
    for ia in range(inst.na):
        for ib in range(inst.nb):
            try:
                sub = inst[port_name, ia, ib]
            except KeyError:
                continue
            for p in Ports(kcl=kcl, bases=[sub.base]):
                if (p.x, p.y) == port_coord:
                    return ia, ib
    return None


def _siblings_connected(
    inst: Any,
    kcl: Any,
    self_port_name: str,
    self_port_coord: tuple[int, int],
    group: set[str],
    cell_ports: CellPortMap,
    inst_ports: InstPortMap,
) -> bool:
    """Whether any equivalent sibling on the same instance / array-element is connected.

    Equivalence is declared per *cell type* via ``equivalent_ports``; the
    check is scoped per array element so a connection on element 0 doesn't
    suppress dangling ports on element 3. Works uniformly for scalar
    instances (treated as a single implicit element) and for ``na``/``nb``
    arrays.
    """
    sibling_names = group - {self_port_name}
    if not sibling_names:
        return False

    element = _array_element_for_port(inst, kcl, self_port_name, self_port_coord)

    def sibling_port_at(name: str) -> Any | None:
        try:
            return inst[name, *element] if element is not None else inst[name]
        except (KeyError, ValueError):
            return None

    for sib_name in sibling_names:
        sib = sibling_port_at(sib_name)
        if sib is None:
            continue
        for p in Ports(kcl=kcl, bases=[sib.base]):
            if _is_coord_connected((p.layer), (p.x, p.y), cell_ports, inst_ports):
                return True
    return False


def dangling_ports_check(
    cell: ProtoTKCell[Any],
    *,
    port_types: list[str] | None = None,
    layers: list[int] | None = None,
    db: rdb.ReportDatabase | None = None,
    recursive: bool = True,
    equivalent_ports: dict[str, list[list[str]]] | None = None,
) -> rdb.ReportDatabase:
    """Report dangling instance ports — ports with no matching counterpart.

    A dangling port is an instance port at a coord where no other instance
    port and no cell port appears. Emitted under the `DanglingPort` category.

    Args:
        cell: Cell to verify.
        port_types: If given, only ports whose `port_type` is in this list are
            considered.
        layers: If given, only ports on these layers are considered.
        db: Reuse an existing report database. A new one is created otherwise.
        recursive: Run the same check on every called child cell as well.
        equivalent_ports: Per-cell groups of electrically-equivalent port
            names (same shape as `Netlist.lvs_equivalent`'s argument).
            When provided, an instance port is **not** reported as dangling if
            any other port in its group on the same instance is connected.
            Typical use is multi-contact pads where ``e1``, ``e2``, ``e3``,
            ``e4`` and ``pad`` are the same electrical node.
    """
    port_types = port_types or []
    layers = layers or []
    db_ = _ensure_db(cell, db, "Dangling Ports Check")
    if recursive:
        _recurse(
            cell,
            db_,
            dangling_ports_check,
            port_types=port_types,
            layers=layers,
            equivalent_ports=equivalent_ports,
        )

    db_cell = db_.create_cell(cell.name)
    layer_cat = _layer_cat_factory(db_, cell)
    cell_ports = _collect_cell_ports(cell, port_types, layers)
    inst_ports = _collect_inst_ports(cell, port_types, layers)

    for layer, coord_map in inst_ports.items():
        lc = layer_cat(layer)
        for coord, ports in coord_map.items():
            if len(ports) != 1:
                continue
            if layer in cell_ports and coord in cell_ports[layer]:
                continue
            port, port_cell, inst_name, inst_obj = ports[0]
            if equivalent_ports:
                group = _resolve_equivalent_group(
                    equivalent_ports, port_cell, port.name or ""
                )
                if (
                    group
                    and len(group) > 1
                    and _siblings_connected(
                        inst_obj,
                        cell.kcl,
                        port.name or "",
                        coord,
                        group,
                        cell_ports,
                        inst_ports,
                    )
                ):
                    continue
            subc = _get_or_create_subcategory(db_, lc, "DanglingPort")
            it = db_.create_item(db_cell, subc)
            port_name = port.name or str(port)
            if inst_name:
                it.add_value(
                    f"Port Name: {inst_name}.{port_name} (cell: {port_cell.name})"
                )
            else:
                it.add_value(f"Port Name: {port_cell.name}.{port_name}")
            if port._base.trans:
                it.add_value(
                    cell.kcl.to_um(
                        port_polygon(port.width).transformed(port._base.trans)
                    )
                )
            else:
                it.add_value(
                    cell.kcl.to_um(port_polygon(port.width)).transformed(
                        port.dcplx_trans
                    )
                )

    return db_


# ---------------------------------------------------------------------------
# Shape ↔ instance-shape overlap checks
# ---------------------------------------------------------------------------


def _iter_check_layers(cell: ProtoTKCell[Any], layers: list[int]) -> list[int]:
    """Layers to scan for shape/instance overlap.

    If `layers` is given, that exact list is returned; otherwise every layer
    in the layout is yielded.
    """
    if layers:
        return list(layers)
    return list(cell.kcl.layout.layer_indexes())


def instance_overlap_check(
    cell: ProtoTKCell[Any],
    *,
    layers: list[int] | None = None,
    db: rdb.ReportDatabase | None = None,
    recursive: bool = True,
) -> rdb.ReportDatabase:
    """Report instance shapes overlapping shapes of other instances.

    For each candidate layer, polygons of one instance that overlap polygons
    of another instance are reported under `InstanceOverlap`.

    Args:
        cell: Cell to verify.
        layers: If given, only check these layers.
        db: Reuse an existing report database. A new one is created otherwise.
        recursive: Run the same check on every called child cell as well.
    """
    layers = layers or []
    db_ = _ensure_db(cell, db, "Instance Overlap Check")
    if recursive:
        _recurse(cell, db_, instance_overlap_check, layers=layers)

    db_cell = db_.create_cell(cell.name)
    layer_cat = _layer_cat_factory(db_, cell)

    for layer in _iter_check_layers(cell, layers):
        error_region = kdb.Region()
        inst_regions: dict[int, kdb.Region] = {}
        inst_region = kdb.Region()
        for i, inst in enumerate(cell.insts):
            inst_region_ = kdb.Region(inst.ibbox(layer))
            inst_shapes: kdb.Region | None = None
            if not (inst_region & inst_region_).is_empty():
                if inst_shapes is None:
                    inst_shapes = kdb.Region()
                    shape_it = cell.begin_shapes_rec_overlapping(
                        layer, inst.bbox(layer)
                    )
                    shape_it.select_cells([inst.cell.cell_index()])
                    shape_it.min_depth = 1
                    shape_it.shape_flags = kdb.Shapes.SRegions
                    for _it in shape_it.each():
                        if _it.path()[0].inst() == inst.instance:
                            inst_shapes.insert(
                                _it.shape().polygon.transformed(_it.trans())
                            )
                for j, _reg in inst_regions.items():
                    if _reg & inst_region_:
                        reg_ = kdb.Region()
                        shape_it = cell.begin_shapes_rec_touching(
                            layer, (_reg & inst_region_).bbox()
                        )
                        shape_it.select_cells([cell.insts[j].cell.cell_index()])
                        shape_it.min_depth = 1
                        shape_it.shape_flags = kdb.Shapes.SRegions
                        for _it in shape_it.each():
                            if _it.path()[0].inst() == cell.insts[j].instance:
                                reg_.insert(
                                    _it.shape().polygon.transformed(_it.trans())
                                )
                        error_region.insert(reg_ & inst_shapes)
            inst_region += inst_region_
            inst_regions[i] = inst_region_

        if not error_region.is_empty():
            sc = _get_or_create_subcategory(db_, layer_cat(layer), "InstanceOverlap")
            for poly in error_region.merge().each():
                it = db_.create_item(db_cell, sc)
                it.add_value(
                    "Instance shapes overlapping with shapes of other instances"
                )
                it.add_value(cell.kcl.to_um(poly.downcast()))

    return db_


def shape_instance_overlap_check(
    cell: ProtoTKCell[Any],
    *,
    layers: list[int] | None = None,
    db: rdb.ReportDatabase | None = None,
    recursive: bool = True,
) -> rdb.ReportDatabase:
    """Report top-level cell shapes overlapping with shapes of instances.

    Polygons drawn directly into the cell that touch polygons from any of its
    instances are reported under `CellShapeInstanceOverlap`.

    Args:
        cell: Cell to verify.
        layers: If given, only check these layers.
        db: Reuse an existing report database. A new one is created otherwise.
        recursive: Run the same check on every called child cell as well.
    """
    layers = layers or []
    db_ = _ensure_db(cell, db, "Shape/Instance Overlap Check")
    if recursive:
        _recurse(cell, db_, shape_instance_overlap_check, layers=layers)

    db_cell = db_.create_cell(cell.name)
    layer_cat = _layer_cat_factory(db_, cell)

    for layer in _iter_check_layers(cell, layers):
        error_region = kdb.Region()
        reg = kdb.Region(cell.shapes(layer))
        for inst in cell.insts:
            inst_region_ = kdb.Region(inst.ibbox(layer))
            if (inst_region_ & reg).is_empty():
                continue
            rec_it = cell.begin_shapes_rec_touching(layer, (inst_region_ & reg).bbox())
            rec_it.min_depth = 1
            error_region += kdb.Region(rec_it) & reg

        if not error_region.is_empty():
            sc = _get_or_create_subcategory(
                db_, layer_cat(layer), "CellShapeInstanceOverlap"
            )
            for poly in error_region.merge().each():
                it = db_.create_item(db_cell, sc)
                it.add_value("Shapes overlapping with shapes of instances")
                it.add_value(cell.kcl.to_um(poly.downcast()))

    return db_
