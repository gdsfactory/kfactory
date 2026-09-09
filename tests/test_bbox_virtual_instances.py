"""Cell bounds include pending virtual instances without materializing them."""

from unittest.mock import patch

import pytest

import kfactory as kf


@pytest.mark.parametrize("cell_type", [kf.KCell, kf.DKCell])
@pytest.mark.parametrize("method", ["bbox", "ibbox", "dbbox"])
@pytest.mark.parametrize("layer_number", [None, 1, 2, 3])
@pytest.mark.parametrize("angle", [0, 30, 90])
@pytest.mark.parametrize("mirror", [False, True])
def test_pending_vinst_bbox(
    kcl: kf.KCLayout,
    cell_type: type[kf.KCell] | type[kf.DKCell],
    method: str,
    layer_number: int | None,
    angle: float,
    mirror: bool,
) -> None:
    kcl.layout.dbu = 0.002
    layers = {i: kcl.layer(i, 0) for i in (1, 2, 3)}
    c = cell_type(kcl=kcl)
    own = kf.kdb.DBox(-5, -3, -4, -2)
    c.shapes(layers[1]).insert(own)
    child = kcl.vkcell("virtual_child")
    child_boxes = {
        1: kf.kdb.DBox(0, -1, 10, 2),
        2: kf.kdb.DBox(20, 20, 22, 23),
    }
    for number, box in child_boxes.items():
        child.shapes(layers[number]).insert(box)
    trans = kf.kdb.DCplxTrans(1, angle, mirror, 30.0012, 40.0012)
    vi = c.create_vinst(child)
    vi.dcplx_trans = trans
    # Check that multiple pending instances are all included.
    trans2 = kf.kdb.DCplxTrans(1, 0, False, -20, 0)
    c.create_vinst(child).dcplx_trans = trans2
    expected = own.dup() if layer_number in (None, 1) else kf.kdb.DBox()
    child_bounds = kf.kdb.DBox()
    for number, box in child_boxes.items():
        if layer_number in (None, number):
            child_bounds += box
    for transform in (trans, trans2):
        # A transformed child bbox can overestimate the transformed geometry.
        expected += child_bounds.transformed(transform)
    layer = layers[layer_number] if layer_number is not None else None
    with patch("kfactory.kcell.logger.warning") as warning:
        actual = getattr(c, method)(layer)
    warning.assert_called_once()
    assert "inaccurate until insert_vinsts()" in warning.call_args.args[0]
    if method == "ibbox" or (method == "bbox" and cell_type is kf.KCell):
        assert isinstance(actual, kf.kdb.Box)
        assert actual == kcl.to_dbu(expected)
    else:
        assert isinstance(actual, kf.kdb.DBox)
        assert actual == expected
    assert len(c.vinsts) == 2
    assert len(c.insts) == 0
    assert vi.dcplx_trans == trans


@pytest.mark.parametrize("cell_type", [kf.KCell, kf.DKCell])
@pytest.mark.parametrize("method", ["bbox", "ibbox", "dbbox"])
def test_bbox_warning_stops_after_insert_vinsts(
    kcl: kf.KCLayout,
    cell_type: type[kf.KCell] | type[kf.DKCell],
    method: str,
) -> None:
    c = cell_type(kcl=kcl)
    layer = kcl.layer(1, 0)
    child = kcl.vkcell("virtual_child")
    child.shapes(layer).insert(kf.kdb.DBox(0, -1, 10, 2))
    c.create_vinst(child).dcplx_trans = kf.kdb.DCplxTrans(1, 90, True, 20, 30)
    with patch("kfactory.kcell.logger.warning") as warning:
        before = getattr(c, method)()
        warning.assert_called_once()
        c.insert_vinsts()
        warning.reset_mock()
        assert getattr(c, method)() == before
        warning.assert_not_called()
    assert len(c.vinsts) == 0
    assert len(c.insts) == 1


@pytest.mark.parametrize("cell_type", [kf.KCell, kf.DKCell, kf.VKCell])
def test_nested_virtual_bbox_layer_filter(
    kcl: kf.KCLayout,
    cell_type: type[kf.KCell] | type[kf.DKCell] | type[kf.VKCell],
) -> None:
    layer = kcl.layer(1, 0)
    other_layer = kcl.layer(2, 0)
    missing_layer = kcl.layer(3, 0)
    child = kcl.vkcell("child")
    child.shapes(layer).insert(kf.kdb.DBox(0, 0, 10, 2))
    child.shapes(other_layer).insert(kf.kdb.DBox(100, 100, 200, 200))
    middle = kcl.vkcell("middle")
    middle.create_vinst(child).dcplx_trans = kf.kdb.DCplxTrans(1, 90, False, 20, 30)
    c = cell_type(kcl=kcl)
    c.create_vinst(middle).dcplx_trans = kf.kdb.DCplxTrans(1, 0, False, 5, 10)
    with patch("kfactory.kcell.logger.warning") as warning:
        assert c.dbbox(layer) == kf.kdb.DBox(23, 40, 25, 50)
        assert c.dbbox(missing_layer).empty()
        assert c.dbbox() == kf.kdb.DBox(-175, 40, 25, 240)
        if cell_type is kf.VKCell:
            warning.assert_not_called()
        else:
            assert warning.call_count == 3


@pytest.mark.parametrize("cell_type", [kf.KCell, kf.DKCell, kf.VKCell])
def test_bbox_without_pending_vinsts_is_silent(
    kcl: kf.KCLayout,
    cell_type: type[kf.KCell] | type[kf.DKCell] | type[kf.VKCell],
) -> None:
    c = cell_type(kcl=kcl)
    with patch("kfactory.kcell.logger.warning") as warning:
        assert c.bbox().empty()
        assert c.ibbox().empty()
        assert c.dbbox().empty()
        warning.assert_not_called()
