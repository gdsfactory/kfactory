from kfactory import KCell, kdb


def fix_spacing(
    c: KCell, min_space: int, layer: int, fix_sizing: int = 20, smooth: int = 5
) -> kdb.Region:
    reg = kdb.Region()
    reg.merged_semantics = False
    reg.insert(c.begin_shapes_rec(layer))
    sc = reg.space_check(min_space, False, kdb.Region.Metrics.Projection, 80).polygons()
    r_int = reg.interacting(sc)
    r_int += (
        sc.sized(fix_sizing, 5)
        & ((reg.interacting(sc) + sc) & sc.extents().size(800)).merge().hulls()
    )
    r_int.merge()

    r_int.smooth(smooth)

    return r_int
