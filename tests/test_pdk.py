import kfactory as kf

import pytest

from functools import partial

def test_pdk() -> None:
    pdk = kf.KCLayout("PDK")
    class LAYER(kf.LayerEnum):
        kcl = kf.constant(pdk)
        WG = (1, 0)
        WGEX = (1, 1)
    pdk.layers = LAYER
    assert pdk.layers == LAYER
    "here"
def test_clear() -> None:
    kcl = kf.KCLayout("CLEAR")
    layer = kcl.layer(500, 0)
    kcl.layers = kf.kcell.layerenum_from_dict(kcl=kcl, layers={"WG": (1, 0)})
    assert kcl.layers.WG == 1
    kcl.clear(keep_layers=True)
    assert kcl.layers.WG == 0
def test_kcell_delete() -> None:
    _kcl = kf.KCLayout("DELETE")

    class LAYER(kf.LayerEnum):
        kcl = kf.constant(_kcl)
        WG = (1, 0)

    s = partial(kf.cells.dbu.Straight(_kcl), width=1000, length=10_000, layer=LAYER.WG)

    s1 = s()
    _kcl.delete_cell(s1)
    assert s1._destroyed() == True

    s1 = s()
    assert s1._destroyed() == False
