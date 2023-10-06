import kfactory as kf


def test_instance_xsize(LAYER: kf.LayerEnum) -> None:
    c = kf.KCell()
    ref = c << kf.cells.straight.straight(width=0.5, length=1, layer=LAYER.WG)
    assert ref.xsize
