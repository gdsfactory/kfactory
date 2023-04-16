from .. import KCell, LayerEnum, kdb


def fix_spacing(
    c: KCell,
    min_space: int,
    layer: int,
    fix_sizing: int = 20,
    smooth: int = 5,
    metrics: kdb.Metrics = kdb.Metrics.Projection,
) -> kdb.Region:
    reg = kdb.Region()
    reg.merged_semantics = False
    reg.insert(c.begin_shapes_rec(layer))
    sc = reg.space_check(min_space, False, metrics, 80).polygons()
    r_int = reg.interacting(sc)
    r_int += (
        sc.sized(fix_sizing, 5)
        & ((reg.interacting(sc) + sc) & sc.extents().size(800)).merge().hulls()
    )
    r_int.merge()

    r_int.smooth(smooth)

    return r_int


def fix_spacing_tiled(
    c: KCell,
    min_space: int,
    layer: LayerEnum | int,
    metrics: kdb.Metrics = kdb.Metrics.Euclidian,
    ignore_angle: float = 80,
    size_space_check: int = 5,
    n_threads: int = 4,
    tile_size: tuple[float, float] | None = None,
    overlap: float = 2,
) -> kdb.Region:
    """Fix min space issues by running a drc check on the input region and merging it with the affcted polygons.

    Args:
        c: Input cell
        layer: Input layer index
        metrics: The metrics to use to determine the violation edges
        ignore_angle: ignore angles greater or equal to this angle
        size_space_check: Sizing in dbu of the offending edges towards the polygons
        n_threads: on how many threads to run the check simultaneously
        tile_size: tuple determining the size of each sub tile (in um), should be big compared to the violation size
        overlap: how many times bigger to make the tile border in relation to the violation size. Smaller than 1 can lead to errors

    Returns:
        kdb.Region: Region containing the fixes for the violations

    """
    if tile_size is None:
        min(25 * min_space, 250)
        tile_size = (25 * min_space * c.klib.dbu, 25 * min_space * c.klib.dbu)

    tp = kdb.TilingProcessor()
    tp.frame = c.bbox_per_layer(layer).to_dtype(c.klib.dbu)  # type: ignore
    tp.dbu = c.klib.dbu
    tp.threads = n_threads
    tp.tile_size(*tile_size)  # tile size in um
    tp.tile_border(min_space * overlap * tp.dbu, min_space * overlap * tp.dbu)
    tp.input("reg", c.klib, c.cell_index(), layer)

    fix_reg = kdb.Region()

    tp.output("fix_reg", fix_reg)

    queue_str = (
        "var tile_reg = reg & (_tile & _frame);"
        + f"var sc = tile_reg.space_check({min_space}, false, Metrics.{metrics.to_s()}, {ignore_angle});"
        + "var edges = sc.edges(); edges.merge();"
        + f"var r_int = (edges.extended(0, 0, 0, {size_space_check}, true) + sc.polygons()); r_int.merge();"
        + "r_int.insert(tile_reg.interacting(sc.polygons())); r_int.merge();"
        + "_output(fix_reg, r_int)"
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
        layer: Input layer index
        metrics: The metrics to use to determine the violation edges
        n_threads: on how many threads to run the check simultaneously
        tile_size: tuple determining the size of each sub tile (in um), should be big compared to the violation size
        overlap: how many times bigger to make the tile border in relation to the violation size. Smaller than 1 can lead to errors

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
