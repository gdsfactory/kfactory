"""ill Utilities.

Filling empty regions in [KCells][kfactory.kcell.KCell] with filling cells.
"""

from collections.abc import Iterable
from itertools import chain
from typing import Any

from .. import kdb
from ..conf import config, logger
from ..kcell import KCell, ProtoTKCell
from ..layout import KCLayout
from ..typings import um

stop = False


class FillOperator(kdb.TileOutputReceiver):
    """Output Receiver of the TilingProcessor."""

    def __init__(
        self,
        kcl: KCLayout,
        top_cell: KCell,
        fill_cell_index: int,
        fc_bbox: kdb.Box,
        origin: kdb.Point,
        row_step: kdb.Vector,
        column_step: kdb.Vector,
        fill_margin: kdb.Vector | None = None,
        remaining_polygons: kdb.Region | None = None,
        multi: bool = False,
    ) -> None:
        """Initialize the receiver."""
        if fill_margin is None:
            fill_margin = kdb.Vector(0, 0)
        self.kcl = kcl
        self.top_cell = top_cell
        self.fill_cell_index = fill_cell_index
        self.fc_bbox = fc_bbox
        self.row_step = row_step
        self.column_step = column_step
        self.fill_margin = fill_margin
        self.remaining_polygons = remaining_polygons
        self.multi = multi
        self.origin = origin
        self.filled_cells: list[kdb.Cell] = []
        self.temp_ly = kdb.Layout()
        self.temp_tc = self.temp_ly.create_cell(top_cell.name)
        fc = kcl.layout.cell(fill_cell_index)
        self.temp_fc = self.temp_ly.create_cell(fc.name)
        self.temp_fc_ind = self.temp_fc.cell_index()
        self.temp_fc.copy_tree(fc)
        self.temp_ly.start_changes()

    def put(
        self,
        ix: int,
        iy: int,
        tile: kdb.Box,
        region: kdb.Region,
        dbu: float,
        clip: bool,
    ) -> None:
        """Called by the TilingProcessor."""
        if self.multi:
            self.temp_tc.fill_region_multi(
                region=region,
                fill_cell_index=self.temp_fc_ind,
                fc_bbox=self.fc_bbox,
                row_step=self.row_step,
                column_step=self.column_step,
                fill_margin=kdb.Vector(
                    self.row_step.x - self.fc_bbox.width(),
                    self.column_step.y - self.fc_bbox.height(),
                ),
                remaining_polygons=None,
                glue_box=tile,
            )
        else:
            self.temp_tc.fill_region(
                region=region,
                fill_cell_index=self.temp_fc_ind,
                fc_bbox=self.fc_bbox,
                row_step=self.row_step,
                column_step=self.column_step,
                origin=self.origin,
                remaining_parts=None,
                fill_margin=self.fill_margin,
                remaining_polygons=None,
                glue_box=tile,
            )

    def insert_fill(self) -> None:
        """Insert fill cell into the regions."""
        self.temp_ly.end_changes()
        for inst in self.temp_tc.each_inst():
            cell_inst_array = inst.cell_inst
            cell_inst_array.cell_index = self.fill_cell_index
            self.top_cell.insert(cell_inst_array)


class SparseFillOperator(kdb.TileOutputReceiver):
    """Output Receiver of the TilingProcessor."""

    def __init__(
        self,
        kcl: KCLayout,
        top_cell: KCell,
        fill_cell: KCell,
        # fc_bbox: kdb.Box,
        # row_step: kdb.Vector,
        # column_step: kdb.Vector,
        # fill_margin: kdb.Vector | None = None,
        # remaining_polygons: kdb.Region | None = None,
        # multi: bool = False,
    ) -> None:
        """Initialize the receiver."""
        # if fill_margin is None:
        #     fill_margin = kdb.Vector(0, 0)
        self.kcl = kcl
        self.top_cell = top_cell
        self.fill_cell = fill_cell
        self.fill_cell_index = fill_cell.cell_index()
        # self.fc_bbox = fc_bbox
        # self.row_step = row_step
        # self.column_step = column_step
        # self.fill_margin = fill_margin
        # self.remaining_polygons = remaining_polygons
        # self.multi = multi
        self.origin = kdb.Point(0, 0)
        self.filled_cells: list[kdb.Cell] = []
        self.temp_ly = kdb.Layout()
        self.temp_tc = self.temp_ly.create_cell(top_cell.name)
        # fc = kcl.layout.cell(fill_cell_index)

        self.fc_sizings = [50, 30, 10]
        self.sizing_steps = 100
        self.f_region = kdb.Region()
        self.f_region.merged_semantics = False

    def put(
        self,
        ix: int,
        iy: int,
        tile: kdb.Box,
        region: kdb.Region,
        dbu: float,
        clip: bool,
    ) -> None:
        """Called by the TilingProcessor."""

        self.f_region.insert(region)


def fill_tiled(
    c: ProtoTKCell[Any],
    fill_cell: ProtoTKCell[Any],
    fill_layers: Iterable[tuple[kdb.LayerInfo, um]] = [],
    fill_regions: Iterable[tuple[kdb.Region, um]] = [],
    exclude_layers: Iterable[tuple[kdb.LayerInfo, um]] = [],
    exclude_regions: Iterable[tuple[kdb.Region, um]] = [],
    n_threads: int | None = None,
    tile_size: tuple[um, um] | None = None,
    row_step: kdb.DVector | None = None,
    col_step: kdb.DVector | None = None,
    x_space: um = 0,
    y_space: um = 0,
    tile_border: tuple[um, um] = (20, 20),
    multi: bool = False,
) -> None:
    """Fill a [KCell][kfactory.kcell.KCell].

    Args:
        c: Target cell.
        fill_cell: The cell used as a cell to fill the regions.
        fill_layers: Tuples of layer and keepout w.r.t. the regions.
        fill_regions: Specific regions to fill. Also tuples like the layers.
        exclude_layers: Layers to ignore. Tuples like the fill layers
        exclude_regions: Specific regions to ignore. Tuples like the fill layers.
        n_threads: Max number of threads used. Defaults to number of cores of the
            machine.
        tile_size: Size of the tiles in um.
        row_step: DVector for steping to the next instance position in the row.
            x-coordinate must be >= 0.
        col_step: DVector for steping to the next instance position in the column.
            y-coordinate must be >= 0.
        x_space: Spacing between the fill cell bounding boxes in x-direction.
        y_space: Spacing between the fill cell bounding boxes in y-direction.
        tile_border: The tile border to consider for excludes
        multi: Use the region_fill_multi strategy instead of single fill.
    """
    c = KCell(base=c.base)
    fill_cell = KCell(base=fill_cell.base)
    if n_threads is None:
        n_threads = config.n_threads
    tp = kdb.TilingProcessor()
    dbb = c.dbbox()
    for r, ext in fill_regions:
        dbb += r.bbox().to_dtype(c.kcl.dbu).enlarged(ext)
    tp.frame = dbb  # type: ignore[assignment, misc]
    tp.dbu = c.kcl.dbu
    tp.threads = n_threads

    if tile_size is None:
        tile_size = (
            100 * (fill_cell.dbbox().width() + x_space),
            100 * (fill_cell.dbbox().height() + y_space),
        )
    tp.tile_size(*tile_size)
    tp.tile_border(*tile_border)

    layer_names: list[str] = []
    for _layer, _ in fill_layers:
        layer_name = (
            f"layer{_layer.name}"
            if _layer.is_named()
            else f"layer_{_layer.layer}_{_layer.datatype}"
        )
        tp.input(layer_name, c.kcl.layout, c.cell_index(), _layer)
        layer_names.append(layer_name)

    region_names: list[str] = []
    for i, (r, _) in enumerate(fill_regions):
        region_name = f"region{i}"
        tp.input(region_name, r)
        region_names.append(region_name)

    exlayer_names: list[str] = []
    for _layer, _ in exclude_layers:
        layer_name = (
            f"layer{_layer.name}"
            if _layer.is_named()
            else f"layer_{_layer.layer}_{_layer.datatype}"
        )
        tp.input(layer_name, c.kcl.layout, c.cell_index(), _layer)
        exlayer_names.append(layer_name)

    exregion_names: list[str] = []
    for i, (r, _) in enumerate(exclude_regions):
        region_name = f"region{i}"
        tp.input(region_name, r)
        exregion_names.append(region_name)

    if row_step is None:
        row_step_ = c.kcl.to_dbu(kdb.DVector(fill_cell.dbbox().width() + x_space, 0))
    else:
        row_step_ = c.kcl.to_dbu(row_step)
    if col_step is None:
        col_step_ = c.kcl.to_dbu(kdb.DVector(0, fill_cell.dbbox().height() + y_space))
    else:
        col_step_ = c.kcl.to_dbu(col_step)
    fc_bbox = fill_cell.bbox()
    operator = FillOperator(
        c.kcl,
        c,
        fill_cell.cell_index(),
        fc_bbox=fc_bbox,
        row_step=row_step_,
        column_step=col_step_,
        origin=c.bbox().p1,
    )
    tp.output(
        "to_fill",
        operator,
    )

    if layer_names or region_names:
        exlayers = " + ".join(
            [
                layer_name + f".sized({c.kcl.to_dbu(size)})" if size else layer_name
                for layer_name, (_, size) in zip(
                    exlayer_names, exclude_layers, strict=False
                )
            ]
        )
        exregions = " + ".join(
            [
                region_name + f".sized({c.kcl.to_dbu(size)})" if size else region_name
                for region_name, (_, size) in zip(
                    exregion_names, exclude_regions, strict=False
                )
            ]
        )
        layers = " + ".join(
            [
                layer_name + f".sized({c.kcl.to_dbu(size)})" if size else layer_name
                for layer_name, (_, size) in zip(layer_names, fill_layers, strict=False)
            ]
        )
        regions = " + ".join(
            [
                region_name + f".sized({c.kcl.to_dbu(size)})" if size else region_name
                for region_name, (_, size) in zip(
                    region_names, fill_regions, strict=False
                )
            ]
        )

        if exlayer_names or exregion_names:
            queue_str = (
                "var fill= "
                + (f"{layers} + {regions}" if regions and layers else regions + layers)
                + "; var exclude = "
                + (
                    f"{exlayers} + {exregions}"
                    if exregions and exlayers
                    else exregions + exlayers
                )
                + "; var fill_region = _tile.minkowski_sum(Box.new("
                f"0,0,{fc_bbox.width() - 1},{fc_bbox.height() - 1}))"
                " & _frame & fill - exclude; _output(to_fill, fill_region)"
            )
        else:
            queue_str = (
                "var fill= "
                + (f"{layers} + {regions}" if regions and layers else regions + layers)
                + "; var fill_region = _tile.minkowski_sum(Box.new("
                f"0,0,{fc_bbox.width() - 1},{fc_bbox.height() - 1}))"
                " & _frame & fill;"
                " _output(to_fill, fill_region)"
            )
        tp.queue(queue_str)
        c.kcl.start_changes()
        try:
            logger.debug(
                "Filling {} with {}", c.kcl.future_cell_name or c.name, fill_cell.name
            )
            logger.debug("Fill string: '{}'", queue_str)
            tp.execute(f"Fill {c.name}")
            logger.debug("done with calculating fill regions for {}", c.name)
            operator.insert_fill()
        finally:
            c.kcl.end_changes()


def fill_coverage(
    c: ProtoTKCell[Any],
    max_distance: um,
    coverage_cell: ProtoTKCell[Any],
    coverage_layers: Iterable[tuple[kdb.LayerInfo, um]] = [],
    coverage_regions: Iterable[tuple[kdb.Region, um]] = [],
    avoid_layers: Iterable[tuple[kdb.LayerInfo, um]] = [],
    avoid_regions: Iterable[tuple[kdb.Region, um]] = [],
    n_threads: int | None = None,
    tile_size: tuple[um, um] = (500, 500),
) -> None:
    """Cover a Cell with metrology or similar structures.

    These structures usually don't require the same

    Args:
        c: Target cell.
        fill_cell: The cell used as a cell to fill the regions.
        fill_layers: Tuples of layer and keepout w.r.t. the regions.
        fill_regions: Specific regions to fill. Also tuples like the layers.
        exclude_layers: Layers to ignore. Tuples like the fill layers
        exclude_regions: Specific regions to ignore. Tuples like the fill layers.
        n_threads: Max number of threads used. Defaults to number of cores of the
            machine.
        tile_size: Size of the tiles in um.
        row_step: DVector for steping to the next instance position in the row.
            x-coordinate must be >= 0.
        col_step: DVector for steping to the next instance position in the column.
            y-coordinate must be >= 0.
        x_space: Spacing between the fill cell bounding boxes in x-direction.
        y_space: Spacing between the fill cell bounding boxes in y-direction.
        tile_border: The tile border to consider for excludes
        multi: Use the region_fill_multi strategy instead of single fill.
    """
    c = KCell(base=c.base)
    coverage_cell = KCell(base=coverage_cell.base)
    if n_threads is None:
        n_threads = config.n_threads
    tp = kdb.TilingProcessor()
    dbb = c.dbbox()
    for r, ext in coverage_regions:
        dbb += r.bbox().to_dtype(c.kcl.dbu).enlarged(ext)
    tp.frame = dbb  # type: ignore[assignment, misc]
    tp.dbu = c.kcl.dbu
    tp.threads = n_threads

    tp.tile_size(*tile_size)
    _border = max(
        s[1]
        for s in chain(coverage_regions, avoid_regions, avoid_layers, coverage_layers)
    ) + c.kcl.to_um(1)
    tp.tile_border(_border, _border)

    layer_names: list[str] = []
    for _layer, _ in coverage_layers:
        layer_name = (
            f"layer{_layer.name}"
            if _layer.is_named()
            else f"layer_{_layer.layer}_{_layer.datatype}"
        )
        tp.input(layer_name, c.kcl.layout, c.cell_index(), _layer)
        layer_names.append(layer_name)

    region_names: list[str] = []
    for i, (r, _) in enumerate(coverage_regions):
        region_name = f"coverage_region{i}"
        tp.input(region_name, r)
        region_names.append(region_name)

    exlayer_names: list[str] = []
    for _layer, _ in avoid_layers:
        layer_name = (
            f"layer{_layer.name}"
            if _layer.is_named()
            else f"layer_{_layer.layer}_{_layer.datatype}"
        )
        tp.input(layer_name, c.kcl.layout, c.cell_index(), _layer)
        exlayer_names.append(layer_name)

    avoid_region_names: list[str] = []
    for i, (r, _) in enumerate(avoid_regions):
        region_name = f"avoid_region{i}"
        tp.input(region_name, r)
        avoid_region_names.append(region_name)

    coverage_operator = SparseFillOperator(
        c.kcl,
        c,
        coverage_cell,
    )
    tp.output(
        "to_cover",
        coverage_operator,
    )
    avoid_operator = SparseFillOperator(
        c.kcl,
        c,
        coverage_cell,
    )
    tp.output(
        "to_avoid",
        avoid_operator,
    )

    if layer_names or region_names:
        avoid_layers_str = " + ".join(
            [
                layer_name + f".sized({c.kcl.to_dbu(size)})" if size else layer_name
                for layer_name, (_, size) in zip(
                    exlayer_names, avoid_layers, strict=True
                )
            ]
        )
        avoid_regions_str = " + ".join(
            [
                region_name + f".sized({c.kcl.to_dbu(size)})" if size else region_name
                for region_name, (_, size) in zip(
                    avoid_region_names, avoid_regions, strict=True
                )
            ]
        )
        coverage_layers_str = " + ".join(
            [
                layer_name + f".sized({c.kcl.to_dbu(size)})" if size else layer_name
                for layer_name, (_, size) in zip(
                    layer_names, coverage_layers, strict=True
                )
            ]
        )
        coverage_regions_str = " + ".join(
            [
                region_name + f".sized({c.kcl.to_dbu(size)})" if size else region_name
                for region_name, (_, size) in zip(
                    region_names, coverage_regions, strict=True
                )
            ]
        )

        if exlayer_names or avoid_region_names:
            queue_str1 = (
                "var cover = "
                + (
                    f"{coverage_layers_str} + {coverage_regions_str}"
                    if coverage_layers_str and coverage_regions_str
                    else coverage_layers_str + coverage_regions_str
                )
                + "; var cov_region = _tile & _frame & cover; "
                "_output(to_coverage, cov_region);"
            )

            queue_str2 = (
                "var avoid = "
                + (
                    f"{avoid_layers_str} + {avoid_regions_str}"
                    if avoid_regions_str and avoid_layers_str
                    else avoid_regions_str + avoid_layers_str
                )
                + "; var avoid_region = _tile & _frame & fill - exclude; "
                "_output(to_fill, fill_region)"
            )
        else:
            queue_str1 = (
                "var fill= "
                + (
                    f"{coverage_layers_str} + {coverage_regions_str}"
                    if coverage_regions_str and coverage_layers_str
                    else coverage_regions_str + coverage_layers_str
                )
                + "; var fill_region = _tile & _frame & fill;"
                " _output(to_fill, fill_region)"
            )
            queue_str2 = ""
        tp.queue(queue_str1)
        if queue_str2:
            tp.queue(queue_str2)
        c.kcl.start_changes()
        try:
            logger.debug(
                "Filling {} with {}",
                c.kcl.future_cell_name or c.name,
                coverage_cell.name,
            )
            logger.debug("Coverage string: '{}'", queue_str1)
            tp.execute(f"Calculating sparse coverage for {c.name}")
            logger.debug("done with calculating fill regions for {}", c.name)
            cover(
                top_cell=c,
                fill_cell=coverage_cell,
                margin=c.kcl.to_dbu(max_distance),
                cover_region=coverage_operator.f_region,
                avoid_region=avoid_operator.f_region if queue_str2 else kdb.Region(),
            )
        finally:
            c.kcl.end_changes()


def cover(
    top_cell: KCell,
    fill_cell: KCell,
    margin: int,
    cover_region: kdb.Region,
    avoid_region: kdb.Region,
) -> None:
    """Insert fill cell into the regions."""

    margin = 1_500_000
    margine_sizing_steps = [i * 100_000 for i in range(1, 11)]
    logger.debug(
        "Applying static sparse fill to {cell} with {fc} at {margin} static spacing",
        cell=top_cell.name,
        fc=fill_cell.name,
        margin=margin,
    )

    fill_cell_index = fill_cell.cell_index()

    margin_vec = kdb.Vector(margin, margin)

    for origin in [kdb.Point(0, 0), kdb.Point(300_000, 300_000)]:
        coverage = _get_coverage(top_cell, fill_cell_index, margin)
        reg = cover_region - coverage
        if reg.is_empty():
            break
        rem = kdb.Region()
        top_cell.kdb_cell.fill_region(
            region=reg - avoid_region,
            fill_cell_index=fill_cell_index,
            fc_box=fill_cell.bbox().enlarged(50_000),
            origin=origin,
            fill_margin=margin_vec,
            remaining_parts=rem,
        )
        while not rem.is_empty():
            top_cell.kdb_cell.fill_region(
                region=rem,
                fill_cell_index=fill_cell_index,
                fc_box=fill_cell.bbox().enlarged(50_000),
                origin=origin,
                fill_margin=margin_vec,
                remaining_parts=rem,
            )

    reg = cover_region - _get_coverage(top_cell, fill_cell_index, margin)

    if reg.is_empty():
        return

    hulls = cover_region.hulls()
    outer_bbox = hulls.sized(margin) - hulls
    for delta_margin in margine_sizing_steps:
        delta_reg = (
            (
                (cover_region + outer_bbox)
                - _get_coverage(top_cell, fill_cell_index, margin)
            )
            .holes()
            .size(delta_margin)
        )
        rem = kdb.Region()
        top_cell.kdb_cell.fill_region(
            region=(delta_reg & cover_region) - avoid_region,
            fill_cell_index=fill_cell_index,
            fc_box=fill_cell.bbox().enlarged(50_000),
            fill_margin=margin_vec - kdb.Vector(delta_margin, delta_margin),
            remaining_parts=rem,
        )
        while not rem.is_empty():
            top_cell.kdb_cell.fill_region(
                region=rem,
                fill_cell_index=fill_cell_index,
                fc_box=fill_cell.bbox().enlarged(50_000),
                fill_margin=margin_vec - kdb.Vector(delta_margin, delta_margin),
                remaining_parts=rem,
            )
        reg = cover_region - _get_coverage(top_cell, fill_cell_index, margin)
        if reg.is_empty():
            return

    raise ValueError(f"Failed to proper reach coverage in cell {top_cell.name!r}")


def _get_coverage(top_cell: KCell, fill_cell_index: int, margin: int) -> kdb.Region:
    box = kdb.Box(margin)
    coverage = kdb.Region()
    for p in _get_placed_fc(top_cell, fill_cell_index):
        coverage.insert(box.transformed(kdb.Trans(p.to_v())))
    return coverage


def _get_placed_fc(top_cell: KCell, fill_cell_index: int) -> list[kdb.Point]:
    recit = top_cell.begin_instances_rec()
    recit.targets = [fill_cell_index]

    points: list[kdb.Point] = []

    for it in recit.each():
        trans = it.trans() * it.inst_trans()
        points.append(trans.disp.to_p())

    return points
