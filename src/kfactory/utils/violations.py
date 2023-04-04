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
    layer: LayerEnum,
    fix_sizing: int = 20,
    smooth: int = 5,
    metrics: kdb.Metrics = kdb.Metrics.Projection,
    ignore_angle: float = 80,
    size_space_check: int = 5,
    n_threads: int = 4,
) -> kdb.Region:
    tp = kdb.TilingProcessor()
    tp.frame = c.bbox_per_layer(layer).to_dtype(c.klib.dbu)  # type: ignore
    tp.dbu = c.klib.dbu
    tp.threads = n_threads
    tp.tile_size(2500, 2500)  # tile size in um
    tp.input("iter", c.begin_shapes_rec(layer))

    tp.input("reg", kdb.Region())
    fix_reg = kdb.Region()

    tp.output("fix_reg", fix_reg)

    queue_str = (
        "var _iter = iter & (_tile & _frame); reg.merged_semantics = false;"
        + f"reg = iter.sized({min_space}).sized({-min_space});"
        + "_output(fix_reg, reg)"
    )

    ### The no sizing option: Does *not* work yet due to crash
    # queue_str = (
    #     "var _iter = iter & (_tile & _frame); reg.merged_semantics = false;"
    #     + f"var sc = _iter.space_check({min_space}, false);"  # , '{metrics.to_i()}');"  # angle_limit({ignore_angle})); "
    #     + f"var r_int = (sc.edges().merge().extended(0, 0, 0, {size_space_check}, true).merge() + sc.polygons().merge()).merge();"
    #     + "var r_int = sc.polygons().merge() & (_tile & _frame);"
    #     + "_output(fix_reg, r_int)"
    # )

    # print(queue_str)

    tp.queue(queue_str)

    # c.klib.start_changes()
    tp.execute("Min Space Fix")
    # c.klib.end_changes()
    return fix_reg
