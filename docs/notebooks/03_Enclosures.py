import kfactory as kf


class LAYER(kf.LayerEnum):
    WG = (1, 0)
    WGEX = (2, 0)
    SLAB = (3, 0)
    SLABEX = (4, 0)


enc = kf.utils.Enclosure(
    [
        (LAYER.WGEX, 5000),
        (LAYER.SLAB, 5000, 50000),
        (LAYER.SLAB, 55000, 95000),
        (LAYER.SLABEX, 110000),
    ],
    name="WGSLAB",
    main_layer=LAYER.WG,
)


@kf.autocell
def rectangles(
    radius: int,
    width: int,
    pitch: int,
    n: int,
    l_straight: int,
    layer: kf.LayerEnum,
    enclosure: kf.utils.Enclosure,
) -> kf.KCell:
    """Rectangles with eulerbends as corners."""
    c = kf.KCell()
    bend = kf.pcells.euler.bend_euler(
        width=int(width * c.klib.dbu), radius=int(c.klib.dbu * radius), layer=layer
    )

    def wg_f(length: int) -> kf.KCell:
        return kf.pcells.waveguide.waveguide_dbu(
            width=width, length=length, layer=layer
        )

    for i in range(n):
        b1, b2, b3, b4 = (c << bend for _ in range(4))
        b1.transform(kf.kdb.Trans(i * pitch, -i * pitch))
        v = 2 * i * pitch
        if v:
            wg_v = wg_f(v)
            wg1 = c << wg_v
            wg1.align("o1", b1, "o2")
            b2.align("o1", wg1, "o2")
        else:
            b2.align("o1", b1, "o2")
        _l_straight = l_straight + 2 * i * pitch
        if _l_straight:
            wg_h = wg_f(_l_straight)
            wg2 = c << wg_h
            wg2.align("o1", b2, "o2")
            b3.align("o1", wg2, "o2")
        else:
            b3.align("o1", b2, "o2")
        if v:
            wg3 = c << wg_v
            wg3.align("o1", b3, "o2")
            b4.align("o1", wg3, "o2")
        else:
            b4.align("o1", b3, "o2")
        if _l_straight:
            wg4 = c << wg_h
            wg4.align("o1", b4, "o2")

    def shape(d: int) -> kf.kdb.Polygon:
        return kf.kdb.Polygon.ellipse(kf.kdb.Box(2 * d, 2 * d), 64)

    enclosure.apply_minkowski_custom(c=c, shape=shape, ref=layer)

    return c


@kf.autocell
def rectangles_tiled(
    radius: int,
    width: int,
    pitch: int,
    n: int,
    l_straight: int,
    layer: kf.LayerEnum,
    enclosure: kf.utils.Enclosure,
) -> kf.KCell:
    """Rectangles with eulerbends as corners."""
    c = kf.KCell()
    bend = kf.pcells.euler.bend_euler(
        width=int(width * c.klib.dbu), radius=int(c.klib.dbu * radius), layer=layer
    )

    def wg_f(length: int) -> kf.KCell:
        return kf.pcells.waveguide.waveguide_dbu(
            width=width, length=length, layer=layer
        )

    for i in range(n):
        b1, b2, b3, b4 = (c << bend for _ in range(4))
        b1.transform(kf.kdb.Trans(i * pitch, -i * pitch))
        v = 2 * i * pitch
        if v:
            wg_v = wg_f(v)
            wg1 = c << wg_v
            wg1.align("o1", b1, "o2")
            b2.align("o1", wg1, "o2")
        else:
            b2.align("o1", b1, "o2")
        _l_straight = l_straight + 2 * i * pitch
        if _l_straight:
            wg_h = wg_f(_l_straight)
            wg2 = c << wg_h
            wg2.align("o1", b2, "o2")
            b3.align("o1", wg2, "o2")
        else:
            b3.align("o1", b2, "o2")
        if v:
            wg3 = c << wg_v
            wg3.align("o1", b3, "o2")
            b4.align("o1", wg3, "o2")
        else:
            b4.align("o1", b3, "o2")
        if _l_straight:
            wg4 = c << wg_h
            wg4.align("o1", b4, "o2")

    def shape(d: int) -> kf.kdb.Polygon:
        return kf.kdb.Polygon.ellipse(kf.kdb.Box(2 * d, 2 * d), 64)

    enclosure.apply_minkowski_tiled(c=c, ref=layer, n_pts=64)

    return c


# if __name__ == "__main__":
#     #     # kf.show(rectangles(500000, 10000, 120000, 15, 1000000, LAYER.WG, enc))
#     kf.show(rectangles_tiled(500000, 10000, 120000, 15, 1000000, LAYER.WG, enc))
