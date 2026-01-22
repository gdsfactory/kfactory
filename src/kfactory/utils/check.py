from typing import Any

from .. import kdb, rdb
from ..conf import logger
from ..kcell import ProtoTKCell


def check_instance_touching(
    c: ProtoTKCell[Any],
    layers: list[kdb.LayerInfo],
    recursive: bool = False,
    db: rdb.ReportDatabase | None = None,
) -> rdb.ReportDatabase:
    logger.warning("starting")
    if db is None:
        db = rdb.ReportDatabase("Touching Instance Check")

    for layer in layers:
        bbox_reg = kdb.Region()
        li = c.kcl.layer(layer)

        inst_shape_index: int = 0
        other_reg = kdb.Region()
        other_reg.merged_semantics = False

        cell_region: dict[int, kdb.Region] = {}

        for i, inst in enumerate(c.insts):
            bb_reg = kdb.Region(inst.ibbox(li))
            logger.warning("testing")
            if not bbox_reg.interacting(bb_reg).is_empty():
                logger.warning("not overlapping")
                for j in range(inst_shape_index, i):
                    other_reg.insert(_get_inst_region(j, c, cell_region, layer))
                inst_reg = _get_inst_region(i, c, cell_region, layer)
                if not (overlap := inst_reg & other_reg).is_empty():
                    cat = db.category_by_path(str(layer)) or db.create_category(
                        str(layer)
                    )
                    cell = db.cell_by_qname(c.name) or db.create_cell(c.name)
                    item = db.create_item(cell, cat)

                    item.add_value(
                        f"Overlapping instances with {inst.cell.name!r} at "
                        f"x={inst.dcplx_trans.disp.x} "
                        f"y={inst.dcplx_trans.disp.y} "
                        f"orientation={inst.dcplx_trans.angle!r}"
                    )
                    for poly in overlap.each():
                        item.add_value(poly.to_dtype(c.kcl.dbu))
                other_reg.insert(inst_reg)
                inst_shape_index = i + 1
            bbox_reg.insert(bb_reg)

    if recursive:
        for ci in c.called_cells():
            check_instance_touching(c.kcl[ci], layers=layers, recursive=False, db=db)

    return db


def _get_inst_region(
    i: int,
    c: ProtoTKCell[Any],
    cell_region: dict[int, kdb.Region],
    layer: kdb.LayerInfo,
) -> kdb.Region:
    inst = c.insts[i]
    ci = inst.cell.cell_index()
    if ci not in cell_region:
        r = kdb.Region()
        r.merged_semantics = False
        r.insert(inst.cell.begin_shapes_rec(c.kcl.layer(layer)))
        cell_region[ci] = r
    return cell_region[ci].transformed(inst.cplx_trans)
