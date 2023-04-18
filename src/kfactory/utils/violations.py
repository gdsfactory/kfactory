"""Utilities to fix DRC violations.

:py:func:~`fix_spacing_tiled` uses :py:func:~`kdb.Region.space_check` to detect
minimum space violations and then applies a fix.
"""

from typing import overload

from .. import KCell, LayerEnum, kdb


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
    n_threads: int = 4,
    tile_size: tuple[float, float] | None = None,
    overlap: float = 3,
    smooth_factor: float = 0.05,
    smooth_absolute: int | None = None,
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

    Returns:
        fix: Region containing the fixes for the violations

    """
    if tile_size is None:
        min(25 * min_space, 250)
        tile_size = (30 * min_space * c.klib.dbu, 30 * min_space * c.klib.dbu)

    tp = kdb.TilingProcessor()
    tp.frame = c.bbox_per_layer(layer).to_dtype(c.klib.dbu)  # type: ignore
    tp.dbu = c.klib.dbu
    tp.threads = n_threads
    tp.tile_size(*tile_size)  # tile size in um
    tp.tile_border(min_space * overlap * tp.dbu, min_space * overlap * tp.dbu)
    tp.input("reg", c.klib, c.cell_index(), layer)

    fix_reg = kdb.Region()

    tp.output("fix_reg", fix_reg)

    if smooth_factor != 0 or smooth_absolute:
        smooth = (
            min(int(smooth_factor * min_space), 1)
            if not smooth_absolute
            else smooth_absolute
        )
        queue_str = (
            "var tile_reg = reg & (_tile & _frame); "
            f"var sc = tile_reg.space_check({min_space},"
            f" false, Metrics.{metrics.to_s()},"
            f" {ignore_angle}); "
            "var edges = sc.edges(); edges.merge(); "
            f"var r_int = (edges.extended(0, 0, 0, {size_space_check}, true)"
            " + sc.polygons()); r_int.merge();"
            " r_int.insert(tile_reg.interacting(sc.polygons())); "
            f"r_int.merge(); r_int.smooth({smooth}); "
            f"_output(fix_reg, r_int)"
        )
    else:
        queue_str = (
            "var tile_reg = reg & (_tile & _frame);"
            f"var sc = tile_reg.space_check({min_space},"
            f" false, Metrics.{metrics.to_s()},"
            f" {ignore_angle});"
            "var edges = sc.edges(); edges.merge();"
            f"var r_int = (edges.extended(0, 0, 0, {size_space_check}, true)"
            " + sc.polygons()); r_int.merge();"
            " r_int.insert(tile_reg.interacting(sc.polygons()));"
            "r_int.merge(); _output(fix_reg, r_int)"
        )

    tp.queue(queue_str)

    c.klib.start_changes()
    tp.execute("Min Space Fix")
    c.klib.end_changes()

    return fix_reg


def fix_spacing_sizing_tiled(
    c: KCell,
    min_space: int,
    layer: LayerEnum,
    n_threads: int = 4,
    tile_size: tuple[float, float] | None = None,
    overlap: int = 2,
) -> kdb.Region:
    """Fix min space issues by using a dilation & erosion.

    Args:
        c: Input cell
        min_space: Minimum space rule [dbu]
        layer: Input layer index
        metrics: The metrics to use to determine the violation edges
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
        size = min_space * 20 * c.klib.dbu
        tile_size = (size, size)
    tp.frame = c.bbox_per_layer(layer).to_dtype(c.klib.dbu)  # type: ignore
    tp.dbu = c.klib.dbu
    tp.threads = n_threads
    tp.tile_size(*tile_size)  # tile size in um
    tp.tile_border(min_space * overlap * tp.dbu, min_space * overlap * tp.dbu)
    tp.input("reg", c.klib, c.cell_index(), layer)

    fix_reg = kdb.Region()

    tp.output("fix_reg", fix_reg)

    queue_str = (
        "var tile_reg= reg & (_tile & _frame);"
        + f"reg = tile_reg.sized({min_space}).sized({-min_space});"
        + "_output(fix_reg, reg)"
    )

    tp.queue(queue_str)

    c.klib.start_changes()
    tp.execute("Min Space Fix")
    c.klib.end_changes()

    return fix_reg
