"""Utilities to fix DRC violations.

:py:func:~`fix_spacing_tiled` uses :py:func:~`kdb.Region.space_check` to detect
minimum space violations and then applies a fix.
"""

from typing import overload

from .. import KCell, LayerEnum, kdb
from ..conf import config, logger

__all__ = [
    "fix_spacing_tiled",
    "fix_spacing_sizing_tiled",
    "fix_spacing_minkowski_tiled",
]


@overload
def fix_spacing_tiled(
    c: KCell,
    min_space: int,
    layer: LayerEnum | int,
    metrics: kdb.Metrics = kdb.Metrics.Euclidian,
    ignore_angle: float = 80,
    size_space_check: int = 5,
    n_threads: int = 4,
    tile_size: tuple[float, float] | None = None,
    overlap: float = 3,
    smooth_factor: float = 0.05,
) -> kdb.Region:
    ...


@overload
def fix_spacing_tiled(
    c: KCell,
    min_space: int,
    layer: LayerEnum | int,
    metrics: kdb.Metrics = kdb.Metrics.Euclidian,
    ignore_angle: float = 80,
    size_space_check: int = 5,
    n_threads: int = 4,
    tile_size: tuple[float, float] | None = None,
    overlap: float = 3,
    *,
    smooth_absolute: int,
) -> kdb.Region:
    ...


def fix_spacing_tiled(
    c: KCell,
    min_space: int,
    layer: LayerEnum | int,
    metrics: kdb.Metrics = kdb.Metrics.Euclidian,
    ignore_angle: float = 80,
    size_space_check: int = 5,
    n_threads: int | None = None,
    tile_size: tuple[float, float] | None = None,
    overlap: float = 3,
    smooth_factor: float = 0.05,
    smooth_absolute: int | None = None,
    smooth_keep_hv: bool = True,
) -> kdb.Region:
    """Fix minimum space violations.

    Fix min space issues by running a drc check on the input region and merging
    it with the affcted polygons.

    Args:
        c: Input cell
        min_space: Minimum space rule [dbu]
        layer: Input layer index
        metrics: The metrics to use to determine the violation edges
        ignore_angle: ignore angles greater or equal to this angle
        size_space_check: Sizing in dbu of the offending edges towards the polygons
        n_threads: on how many threads to run the check simultaneously
        tile_size: tuple determining the size of each sub tile (in um), should be big
            compared to the violation size
        overlap: how many times bigger to make the tile border in relation to the
            violation size. Smaller than 1 can lead to errors
        smooth_factor: how big to smooth the resulting region in relation to the
            violation. 1 == the violation size. Set to 0 to disable
        smooth_absolute: If set will overwrite smooth with an an absolute value, not
            relative to the violation size. If set, this will disable smooth_factor.
            [dbu]
        smooth_keep_hv: Keep horizontal and vertical vertices when smoothing.

    Returns:
        fix: Region containing the fixes for the violations

    """
    if tile_size is None:
        min(25 * min_space, 250)
        tile_size = (30 * min_space * c.kcl.dbu, 30 * min_space * c.kcl.dbu)

    tp = kdb.TilingProcessor()
    tp.frame = c.bbox_per_layer(layer).to_dtype(c.kcl.dbu)  # type: ignore[misc]
    tp.dbu = c.kcl.dbu
    tp.tile_size(*tile_size)  # tile size in um
    tp.tile_border(min_space * overlap * tp.dbu, min_space * overlap * tp.dbu)
    tp.input("reg", c.kcl.layout, c.cell_index(), layer)
    tp.threads = n_threads or config.n_threads

    fix_reg = RegionOperator()
    tp.output("fix_reg", fix_reg)

    if smooth_factor != 0 or smooth_absolute:
        keep = "true" if smooth_keep_hv else "false"
        smooth = (
            min(int(smooth_factor * min_space), 1)
            if not smooth_absolute
            else smooth_absolute
        )
        queue_str = (
            f"var sc = reg.space_check({min_space},"
            f" false, Metrics.{metrics.to_s()},"
            f" {ignore_angle}); "
            "var edges = sc.edges(); edges.merge(); "
            f"var r_int = (edges.extended(0, 0, 0, {size_space_check}, true)"
            " + sc.polygons()); r_int.merge();"
            " r_int.insert(reg.interacting(sc.polygons())); "
            f"r_int.merge(); r_int.smooth({smooth}, {keep}); "
            f"_output(fix_reg, r_int)"
        )
    else:
        queue_str = (
            f"var sc = reg.space_check({min_space},"
            f" false, Metrics.{metrics.to_s()},"
            f" {ignore_angle});"
            "var edges = sc.edges(); edges.merge();"
            f"var r_int = (edges.extended(0, 0, 0, {size_space_check}, true)"
            " + sc.polygons()); r_int.merge();"
            " r_int.insert(reg.interacting(sc.polygons()));"
            "r_int.merge(); _output(fix_reg, r_int)"
        )

    tp.queue(queue_str)

    c.kcl.start_changes()
    tp.execute("Min Space Fix")
    c.kcl.end_changes()

    return fix_reg.region


def fix_spacing_sizing_tiled(
    c: KCell,
    min_space: int,
    layer: LayerEnum,
    n_threads: int | None = None,
    tile_size: tuple[float, float] | None = None,
    overlap: int = 2,
) -> kdb.Region:
    """Fix min space issues by using a dilation & erosion.

    Args:
        c: Input cell
        min_space: Minimum space rule [dbu]
        layer: Input layer index
        n_threads: on how many threads to run the check simultaneously
        tile_size: tuple determining the size of each sub tile (in um), should be big
            compared to the violation size
        overlap: how many times bigger to make the tile border in relation to the
            violation size. Smaller than 1 can lead to errors

    Returns:
        kdb.Region: Region containing the fixes for the violations

    """
    tp = kdb.TilingProcessor()
    if tile_size is None:
        size = min_space * 20 * c.kcl.dbu
        tile_size = (size, size)
    tp.frame = c.bbox_per_layer(layer).to_dtype(c.kcl.dbu)  # type: ignore[misc]
    tp.dbu = c.kcl.dbu
    tp.tile_size(*tile_size)  # tile size in um
    tp.tile_border(min_space * overlap * tp.dbu, min_space * overlap * tp.dbu)
    tp.input("reg", c.kcl.layout, c.cell_index(), layer)
    tp.threads = n_threads or config.n_threads

    fix_reg = kdb.Region()

    tp.output("fix_reg", fix_reg)

    queue_str = (
        "var tile_reg=reg & (_tile & _frame);"
        + f"reg = tile_reg.sized({min_space}).sized({-min_space});"
        + "_output(fix_reg, reg)"
    )

    tp.queue(queue_str)

    c.kcl.start_changes()
    tp.execute("Min Space Fix")
    c.kcl.end_changes()

    return fix_reg


def fix_spacing_minkowski_tiled(
    c: KCell,
    min_space: int,
    ref: LayerEnum | kdb.Region,
    n_threads: int | None = None,
    tile_size: tuple[float, float] | None = None,
    overlap: int = 1,
    smooth: int | None = None,
) -> kdb.Region:
    """Fix min space issues by using a dilation & erosion with a box.

    Args:
        c: Input cell
        min_space: Minimum space rule [dbu]
        ref: Input layer index or region
        n_threads: on how many threads to run the check simultaneously
        tile_size: tuple determining the size of each sub tile (in um), should be big
            compared to the violation size
        overlap: how many times bigger to make the tile border in relation to the
            violation size. Smaller than 1 can lead to errors
        smooth: Apply smoothening (simplifying) at the end if > 0

    Returns:
        kdb.Region: Region containing the fixes for the violations
    """
    tp = kdb.TilingProcessor()
    tp.frame = c.dbbox()  # type: ignore[misc]
    tp.dbu = c.kcl.dbu
    tp.threads = n_threads or config.n_threads

    min_tile_size_rec = 10 * min_space * tp.dbu

    if tile_size is None:
        tile_size = (min_tile_size_rec * 2, min_tile_size_rec * 2)

    tp.tile_border(min_space * overlap * tp.dbu, min_space * overlap * tp.dbu)

    tp.tile_size(*tile_size)
    if isinstance(ref, int):
        tp.input("main_layer", c.kcl.layout, c.cell_index(), ref)
    else:
        tp.input("main_layer", ref)

    operator = RegionOperator()
    tp.output("target", operator)
    if smooth is None:
        queue_str = (
            f"var tile_reg = (_tile & _frame).sized({min_space});"
            f"var shape = Box.new({min_space},{min_space});"
            "var reg = main_layer.minkowski_sum(shape); reg.merge();"
            "reg = tile_reg - (tile_reg - reg).minkowski_sum(shape);"
            "_output(target, reg & _tile, true);"
        )
    else:
        queue_str = (
            f"var tile_reg = (_tile & _frame).sized({min_space});"
            f"var shape = Box.new({min_space},{min_space});"
            "var reg = main_layer.minkowski_sum(shape); reg.merge();"
            "reg = tile_reg - (tile_reg - reg).minkowski_sum(shape);"
            f"reg.smooth({smooth});"
            "_output(target, reg & _tile, true);"
        )

    tp.queue(queue_str)
    logger.debug("String queued for {}:  {}", c.name, queue_str)

    c.kcl.start_changes()
    logger.info("Starting minkowski on {}", c.name)
    tp.execute(f"Minkowski {c.name}")
    c.kcl.end_changes()

    return operator.region


def fix_width_minkowski_tiled(
    c: KCell,
    min_width: int,
    ref: LayerEnum | kdb.Region,
    n_threads: int | None = None,
    tile_size: tuple[float, float] | None = None,
    overlap: int = 1,
    smooth: int | None = None,
) -> kdb.Region:
    """Fix min space issues by using a dilation & erosion with a box.

    Args:
        c: Input cell
        min_width: Minimum width rule [dbu]
        ref: Input layer index or region
        n_threads: on how many threads to run the check simultaneously
        tile_size: tuple determining the size of each sub tile (in um), should be big
            compared to the violation size
        overlap: how many times bigger to make the tile border in relation to the
            violation size. Smaller than 1 can lead to errors
        smooth: Apply smoothening (simplifying) at the end if > 0

    Returns:
        kdb.Region: Region containing the fixes for the violations
    """
    tp = kdb.TilingProcessor()
    tp.frame = c.dbbox()  # type: ignore[misc]
    tp.dbu = c.kcl.dbu
    tp.threads = n_threads or config.n_threads

    min_tile_size_rec = 10 * min_width * tp.dbu

    if tile_size is None:
        tile_size = (min_tile_size_rec * 2, min_tile_size_rec * 2)

    tp.tile_border(min_width * overlap * tp.dbu, min_width * overlap * tp.dbu)

    tp.tile_size(*tile_size)
    if isinstance(ref, int):
        tp.input("main_layer", c.kcl.layout, c.cell_index(), ref)
    else:
        tp.input("main_layer", ref)

    operator = RegionOperator()
    tp.output("target", operator)
    if smooth is None:
        queue_str = (
            f"var tile_reg = (_tile & _frame).sized({min_width});"
            f"var shape = Box.new({min_width},{min_width});"
            "var reg = tile_reg - (tile_reg - main_layer).minkowski_sum(shape);"
            "reg = reg.minkowski_sum(shape); reg.merge();"
            "_output(target, reg & _tile, true);"
        )
    else:
        queue_str = (
            f"var tile_reg = (_tile & _frame).sized({min_width});"
            f"var shape = Box.new({min_width},{min_width});"
            "var reg = tile_reg - (tile_reg - main_layer).minkowski_sum(shape);"
            "reg = reg.minkowski_sum(shape); reg.merge();"
            f"reg.smooth({smooth});"
            "_output(target, reg & _tile, true);"
        )

    tp.queue(queue_str)
    logger.debug("String queued for {}:  {}", c.name, queue_str)

    c.kcl.start_changes()
    logger.info("Starting minkowski on {}", c.name)
    tp.execute(f"Minkowski {c.name}")
    c.kcl.end_changes()

    return operator.region


def fix_width_and_spacing_minkowski_tiled(
    c: KCell,
    min_space: int,
    min_width: int,
    ref: LayerEnum | kdb.Region,
    n_threads: int | None = None,
    tile_size: tuple[float, float] | None = None,
    overlap: int = 1,
    smooth: int | None = None,
) -> kdb.Region:
    """Fix min space and width issues by using a dilation & erosion with a box.

    The algorithm will dilate by min_space, erode by min_width + min_space, and
    finally dilate by min_width

    Args:
        c: Input cell
        min_space: Minimum space rule [dbu]
        min_width: Minimum width rule [dbu]
        ref: Input layer index or region
        n_threads: on how many threads to run the check simultaneously
        tile_size: tuple determining the size of each sub tile (in um), should be big
            compared to the violation size
        overlap: how many times bigger to make the tile border in relation to the
            violation size. Smaller than 1 can lead to errors (overlap*min_space)
        smooth: Apply smoothening (simplifying) at the end if > 0

    Returns:
        kdb.Region: Region containing the fixes for the violations
    """
    tp = kdb.TilingProcessor()
    tp.frame = c.dbbox()  # type: ignore[misc]
    tp.dbu = c.kcl.dbu
    tp.threads = n_threads or config.n_threads

    min_tile_size_rec = 10 * min_space * tp.dbu

    if tile_size is None:
        tile_size = (min_tile_size_rec * 2, min_tile_size_rec * 2)

    border = min_space * tp.dbu * overlap
    tp.tile_border(border, border)

    tp.tile_size(*tile_size)
    if isinstance(ref, int):
        tp.input("main_layer", c.kcl.layout, c.cell_index(), ref)
    else:
        tp.input("main_layer", ref)

    shrink = min_space + min_width

    operator = RegionOperator()
    tp.output("target", operator)
    if smooth is None:
        queue_str = (
            f"var tile_reg = (_tile & _frame).sized({min_space});"
            f"var space_shape = Box.new({min_space},{min_space});"
            f"var shrink_shape = Box.new({shrink},{shrink});"
            f"var width_shape = Box.new({min_width},{min_width});"
            "var reg = main_layer.minkowski_sum(space_shape); reg.merge();"
            "reg = tile_reg - (tile_reg - reg).minkowski_sum(shrink_shape);"
            "reg = reg.minkowski_sum(width_shape);"
            "_output(target, reg & _tile, true);"
        )
    else:
        queue_str = (
            f"var tile_reg = (_tile & _frame).sized({min_space});"
            f"var space_shape = Box.new({min_space},{min_space});"
            f"var shrink_shape = Box.new({shrink},{shrink});"
            f"var width_shape = Box.new({min_width},{min_width});"
            "var reg = main_layer.minkowski_sum(space_shape); reg.merge();"
            "reg = tile_reg - (tile_reg - reg).minkowski_sum(shrink_shape);"
            "reg = reg.minkowski_sum(width_shape);"
            f"reg.smooth({smooth});"
            "_output(target, reg & _tile, true);"
        )

    tp.queue(queue_str)
    logger.debug("String queued for {}:  {}", c.name, queue_str)

    c.kcl.start_changes()
    logger.info("Starting minkowski on {}", c.name)
    tp.execute(f"Minkowski {c.name}")
    c.kcl.end_changes()

    return operator.region


class RegionOperator(kdb.TileOutputReceiver):
    """Region collector. Just getst the tile and inserts it into the target cell."""

    def __init__(self) -> None:
        """Initialization."""
        self.region = kdb.Region()

    def put(
        self,
        ix: int,
        iy: int,
        tile: kdb.Box,
        region: kdb.Region,
        dbu: float,
        clip: bool,
    ) -> None:
        """Tiling Processor output call.

        Args:
            ix: x-axis index of tile.
            iy: y_axis index of tile.
            tile: The bounding box of the tile.
            region: The target object of the :py:class:~`klayout.db.TilingProcessor`
            dbu: dbu used by the processor.
            clip: Whether the target was clipped to the tile or not.
        """
        self.region.insert(region)
