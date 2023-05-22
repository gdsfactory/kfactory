import kfactory as kf
import numpy as np
from layers import LAYER
import random


@kf.cell
def star(
    size: float, proportion: float, n_diamonds: int = 3, layer: kf.LayerEnum = LAYER.SI
) -> kf.KCell:
    """Create a diamond star cell

    Args:
        size: size in um
        proportion: width of the center vs size (0 < proportion <= 1)
        n_diamonds: number of diamonds in the star (>=1)

    Returns:
        Star Cell
    """

    c = kf.KCell()

    # the first star diamond, we use a box (int based)

    diamond = kf.kdb.DPolygon(
        [
            kf.kdb.DPoint(-size / 2, 0),
            kf.kdb.DPoint(0, -size / 2 * proportion),
            kf.kdb.DPoint(size / 2, 0),
            kf.kdb.DPoint(0, size / 2 * proportion),
        ]
    )

    c.shapes(layer).insert(diamond)  # place base diamond

    for i in range(1, n_diamonds):
        angle = 180 / (n_diamonds) * i

        c.shapes(layer).insert(
            diamond.transformed(kf.kdb.DCplxTrans(1, angle, False, 0, 0))
        )

    return c


@kf.cell
def merged_star(
    size: float, proportion: float, n_diamonds: int = 3, layer: kf.LayerEnum = LAYER.SI
) -> kf.KCell:
    """Same as star but use the star shapes and merge them to one polygon"""

    c = kf.KCell()

    _star = star(size, proportion, n_diamonds, layer)
    reg = kf.kdb.Region(_star.begin_shapes_rec(layer))
    reg.merge()  # merge the region

    # Insert the region

    c.shapes(layer).insert(reg)

    return c


@kf.cell
def sky_with_stars() -> kf.KCell:
    c = kf.KCell()

    box = kf.kdb.Box(0, 0, 400000, 400000)  # 400umx400um sky (default dbu)
    sky = kf.kdb.Region(box)

    # set a custom seed for random
    seed = 314159
    random.seed(seed)

    star_layer = LAYER.SI

    # create 50 stars
    for _ in range(50):
        x = random.uniform(10, 390)
        y = random.uniform(10, 390)
        angle = random.uniform(0, 360)
        _star = c << merged_star(
            size=random.uniform(5, 25),
            proportion=random.uniform(0.2, 0.3),
            n_diamonds=random.randint(2, 5),
            layer=star_layer,
        )
        _star.transform(kf.kdb.DTrans(angle, False, x, y))

    # remove the stars from the sky

    sky -= kf.kdb.Region(c.begin_shapes_rec(star_layer))

    c.shapes(LAYER.SIEXCLUDE).insert(sky)

    return c


if __name__ == "__main__":
    # kf.show(merged_star(5, 0.25))

    kf.show(sky_with_stars())
