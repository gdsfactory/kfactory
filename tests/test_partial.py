import kfactory as kf
from functools import partial
from conftest import Layers


def to_be_partialled(width: float, length: float, layer: kf.kdb.LayerInfo) -> kf.KCell:
    c = kf.KCell()
    box = c.shapes(c.kcl.find_layer(layer)).insert(kf.kdb.DBox(length, width))

    c.create_port(
        trans=kf.kdb.Trans(box.box_width // 2, 0),
        width=box.box_height,
        layer=c.kcl.find_layer(layer),
    )
    c.create_port(
        trans=kf.kdb.Trans(2, False, -box.box_width // 2, 0),
        width=box.box_height,
        layer=c.kcl.find_layer(layer),
    )
    return c


@kf.cell
def partial_cell(partial: partial[kf.KCell]) -> kf.KCell:
    c = kf.KCell()
    c << partial()

    return c


def test_partial(LAYER: Layers) -> None:
    c = partial_cell(partial(to_be_partialled, width=1, length=10, layer=LAYER.WG))
    assert "<" not in c.name
