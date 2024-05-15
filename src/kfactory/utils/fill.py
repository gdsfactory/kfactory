"""ill Utilities.

Filling empty regions in [KCells][kfactory.kcell.KCell] with filling cells.
"""

from collections.abc import Iterable

from .. import kdb
from ..conf import config
from ..kcell import KCell, KCLayout, LayerEnum


class FillOperator(kdb.TileOutputReceiver):
    """Output Receiver of the TilingProcessor."""

    def __init__(
        self,
        kcl: KCLayout,
        top_cell: KCell,
        fill_cell_index: int,
        fc_bbox: kdb.Box,
        row_step: kdb.Vector,
        column_step: kdb.Vector,
        fill_margin: kdb.Vector = kdb.Vector(0, 0),
        remaining_polygons: kdb.Region | None = None,
    ) -> None:
        """Initialize the receiver."""
        self.kcl = kcl
        self.top_cell = top_cell
        self.fill_cell_index = fill_cell_index
        self.fc_bbox = fc_bbox
        self.row_step = row_step
        self.column_step = column_step
        self.fill_margin = fill_margin
        self.remaining_polygons = remaining_polygons
        self.glue_box = self.top_cell.bbox()

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
        self.top_cell.fill_region(
            region=region,
            fill_cell_index=self.fill_cell_index,
            fc_bbox=self.fc_bbox,
            row_step=self.row_step,
            column_step=self.column_step,
            origin=self.glue_box.p1,
            remaining_parts=None,
            fill_margin=self.fill_margin,
            remaining_polygons=None,
            glue_box=self.glue_box,
        )


def fill_tiled(
    c: KCell,
    fill_cell: KCell,
    fill_layers: Iterable[tuple[LayerEnum | int, int]] = [],
    fill_regions: Iterable[tuple[kdb.Region, int]] = [],
    exclude_layers: Iterable[tuple[LayerEnum | int, int]] = [],
    exclude_regions: Iterable[tuple[kdb.Region, int]] = [],
    n_threads: int = config.n_threads,
    tile_size: tuple[float, float] | None = None,
    row_step: kdb.DVector | None = None,
    col_step: kdb.DVector | None = None,
    x_space: float = 0,
    y_space: float = 0,
    tile_border: tuple[float, float] = (20, 20),
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
    """
    tp = kdb.TilingProcessor()
    tp.frame = c.bbox().to_dtype(c.kcl.dbu)  # type: ignore
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
        layer_name = f"layer{_layer}"
        tp.input(layer_name, c.kcl.layout, c.cell_index(), c.kcl.get_info(_layer))
        layer_names.append(layer_name)

    region_names: list[str] = []
    for i, (r, _) in enumerate(fill_regions):
        region_name = f"region{i}"
        tp.input(region_name, r)
        region_names.append(region_name)

    exlayer_names: list[str] = []
    for _layer, _ in exclude_layers:
        layer_name = f"layer{_layer}"
        tp.input(layer_name, c.kcl.layout, c.cell_index(), c.kcl.get_info(_layer))
        exlayer_names.append(layer_name)

    exregion_names: list[str] = []
    for i, (r, _) in enumerate(exclude_regions):
        region_name = f"region{i}"
        tp.input(region_name, r)
        exregion_names.append(region_name)

    if row_step is None:
        _row_step = kdb.Vector(fill_cell.bbox().width() + int(x_space / c.kcl.dbu), 0)
    else:
        _row_step = row_step.to_itype(c.kcl.dbu)
    if col_step is None:
        _col_step = kdb.Vector(0, fill_cell.bbox().height() + int(y_space / c.kcl.dbu))
    else:
        _col_step = col_step.to_itype(c.kcl.dbu)
    fc_bbox = fill_cell.bbox()
    tp.output(
        "to_fill",
        FillOperator(
            c.kcl,
            c,
            fill_cell.cell_index(),
            fc_bbox=fc_bbox,
            row_step=_row_step,
            column_step=_col_step,
        ),
    )

    if layer_names or region_names:
        exlayers = " + ".join(
            [
                layer_name + f".sized({int(size / c.kcl.dbu)})" if size else layer_name
                for layer_name, (_, size) in zip(exlayer_names, exclude_layers)
            ]
        )
        exregions = " + ".join(
            [
                region_name + f".sized({int(size / c.kcl.dbu)})"
                if size
                else region_name
                for region_name, (_, size) in zip(exregion_names, exclude_regions)
            ]
        )
        layers = " + ".join(
            [
                layer_name + f".sized({int(size / c.kcl.dbu)})" if size else layer_name
                for layer_name, (_, size) in zip(layer_names, fill_layers)
            ]
        )
        regions = " + ".join(
            [
                region_name + f".sized({int(size / c.kcl.dbu)})"
                if size
                else region_name
                for region_name, (_, size) in zip(region_names, fill_regions)
            ]
        )

        if exlayer_names or exregion_names:
            queue_str = (
                "var fill= "
                + (
                    " + ".join([layers, regions])
                    if regions and layers
                    else regions + layers
                )
                + "; var exclude = "
                + (
                    " + ".join([exlayers, exregions])
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
                + (
                    " + ".join([layers, regions])
                    if regions and layers
                    else regions + layers
                )
                + "; var fill_region = _tile.sized("
                f"{_row_step.x // 2},{_col_step.y // 2}) & _frame & fill;"
                " _output(to_fill, fill_region)"
            )
        tp.queue(queue_str)
        c.kcl.start_changes()
        try:
            config.logger.info("filling {} with {}", c.name, fill_cell.name)
            config.logger.debug("fill string: '{}'", queue_str)
            tp.execute(f"Fill {c.name}")
            config.logger.info("done with filling {}", c.name)
        finally:
            c.kcl.end_changes()
