"""BBox drawing for symmetric/asymmetric profiles and integer/micrometer units."""

from typing import Any
from unittest.mock import patch

import pytest

import kfactory as kf
from kfactory.exceptions import LockedError
from kfactory.kcell import ProtoTKCell

type Profile = (
    kf.CrossSection
    | kf.DCrossSection
    | kf.AsymmetricCrossSection
    | kf.DAsymmetricCrossSection
)


@pytest.fixture(params=["symmetric", "asymmetric", "dsymmetric", "dasymmetric"])
def xs(request: pytest.FixtureRequest, kcl: kf.KCLayout) -> Profile:
    kcl.layout.dbu = 0.002
    layer = kf.kdb.LayerInfo(1, 0)
    bbox = {kf.kdb.LayerInfo(2, 0): 2.0, kf.kdb.LayerInfo(3, 0): 0.5}
    profile = (
        kf.DAsymmetricCrossSection(
            kcl=kcl,
            layer=layer,
            section_min=-0.1,
            section_max=0.4,
            bbox_sections=bbox,
            radius=10,
            radius_min=5,
        )
        if "asymmetric" in request.param
        else kf.DCrossSection(
            kcl=kcl,
            layer=layer,
            width=0.5,
            sections=[],
            bbox_layers=list(bbox),
            bbox_offsets=list(bbox.values()),
            radius=10,
            radius_min=5,
        )
    )
    return profile if request.param.startswith("d") else profile.to_itype()


@pytest.fixture(params=[kf.KCell, kf.DKCell, kf.VKCell])
def c(
    request: pytest.FixtureRequest, kcl: kf.KCLayout
) -> kf.KCell | kf.DKCell | kf.VKCell:
    return request.param(kcl=kcl)


@pytest.mark.parametrize("reference", ["cell", "layer", "index", "box", "dbox"])
def test_bbox_reference(
    xs: Profile, c: kf.KCell | kf.DKCell | kf.VKCell, reference: str
) -> None:
    core = kf.kdb.DBox(0, -1, 10, 1)
    c.shapes(xs.layer).insert(core)
    c.shapes(kf.kdb.LayerInfo(9, 0)).insert(kf.kdb.DBox(20, 20, 22, 22))
    ref = {
        "cell": None,
        "layer": xs.layer,
        "index": c.kcl.layer(xs.layer),
        "box": core.to_itype(c.kcl.dbu),
        "dbox": core,
    }[reference]
    bounds = c.dbbox() if reference == "cell" else core.dup()
    metadata = xs.base.model_dump()
    xs.add_bbox(c, ref=ref)
    for layer, offset in xs.to_dtype().bbox_sections.items():
        assert c.dbbox(c.kcl.layer(layer)) == bounds.enlarged(offset)
        if isinstance(c, ProtoTKCell):
            assert all(shape.is_box() for shape in c.shapes(layer).each())
    assert core == kf.kdb.DBox(0, -1, 10, 1)
    assert xs.base.model_dump() == metadata


def test_bbox_around_pending_vinst(
    xs: Profile, c: kf.KCell | kf.DKCell | kf.VKCell
) -> None:
    child = c.kcl.vkcell("bbox_child")
    child.shapes(xs.layer).insert(kf.kdb.DBox(0, -1, 10, 2))
    c.create_vinst(child).dcplx_trans = kf.kdb.DCplxTrans(1, 90, False, 20, 30)
    xs.add_bbox(c)
    bounds = kf.kdb.DBox(18, 30, 21, 40)
    for layer, offset in xs.to_dtype().bbox_sections.items():
        assert c.dbbox(c.kcl.layer(layer)) == bounds.enlarged(offset)
    assert len(c.vinsts) == 1


@pytest.mark.parametrize(
    "reference", ["cell", "layer", "index", "box", "dbox", "instance"]
)
@pytest.mark.parametrize("pending", [False, True])
def test_bbox_pending_vinst_warning(
    xs: Profile,
    c: kf.KCell | kf.DKCell | kf.VKCell,
    reference: str,
    pending: bool,
) -> None:
    core = kf.kdb.DBox(0, -1, 10, 2)
    child = c.kcl.vkcell("bbox_warning_child")
    child.shapes(xs.layer).insert(core)
    if pending:
        c.create_vinst(child)
    else:
        c.shapes(xs.layer).insert(core)
    ref = {
        "cell": None,
        "layer": xs.layer,
        "index": c.kcl.layer(xs.layer),
        "box": c.kcl.to_dbu(core),
        "dbox": core,
        "instance": kf.VInstance(child),
    }[reference]
    with patch("kfactory.cross_section.logger.warning") as warning:
        xs.add_bbox(c, ref=ref)
        if pending and not isinstance(c, kf.VKCell):
            warning.assert_called_once()
            assert "inaccurate until insert_vinsts()" in warning.call_args.args[0]
        else:
            warning.assert_not_called()
    assert len(c.vinsts) == int(pending)
    if pending and not isinstance(c, kf.VKCell):
        c.insert_vinsts()
        with patch("kfactory.cross_section.logger.warning") as warning:
            xs.add_bbox(c, ref=ref)
            warning.assert_not_called()


def test_bbox_edge_overrides(xs: Profile, c: kf.KCell | kf.DKCell | kf.VKCell) -> None:
    unit = (
        xs.kcl.dbu
        if isinstance(xs, kf.CrossSection | kf.AsymmetricCrossSection)
        else 1.0
    )
    # int values are valid micrometer inputs too; their type must not select units.
    xs.add_bbox(c, ref=kf.kdb.DBox(0, -1, 10, 1), top=0, left=int(1 / unit), right=0)
    for layer, offset in xs.to_dtype().bbox_sections.items():
        assert c.dbbox(c.kcl.layer(layer)) == kf.kdb.DBox(-1, -1 - offset, 10, 1)


@pytest.mark.parametrize(
    "reference", [None, kf.kdb.LayerInfo(99, 0), kf.kdb.Box(), kf.kdb.DBox()]
)
def test_bbox_empty(
    xs: Profile,
    c: kf.KCell | kf.DKCell | kf.VKCell,
    reference: kf.kdb.LayerInfo | kf.kdb.Box | kf.kdb.DBox | None,
) -> None:
    xs.add_bbox(c, ref=reference)
    assert c.dbbox().empty()


def test_bbox_locked(xs: Profile, c: kf.KCell | kf.DKCell | kf.VKCell) -> None:
    c.locked = True
    with pytest.raises(LockedError):
        xs.add_bbox(c, ref=kf.kdb.DBox(0, 0, 10, 10))
    assert c.dbbox().empty()


def test_bbox_invalid_reference(
    xs: Profile, c: kf.KCell | kf.DKCell | kf.VKCell
) -> None:
    ref: Any = "WG"
    with pytest.raises(TypeError, match="ref must be"):
        xs.add_bbox(c, ref=ref)
    assert c.dbbox().empty()


@pytest.mark.parametrize("cell_type", [kf.KCell, kf.DKCell, kf.VKCell])
@pytest.mark.parametrize("angle", [90, 30])
@pytest.mark.parametrize("mirror", [False, True])
def test_bbox_instance_reference(
    xs: Profile,
    c: kf.KCell | kf.DKCell | kf.VKCell,
    cell_type: type[kf.KCell] | type[kf.DKCell] | type[kf.VKCell],
    angle: float,
    mirror: bool,
) -> None:
    source = c.kcl
    child = source.kcell()
    core = kf.kdb.DBox(0, -1, 10, 2)
    child.shapes(xs.layer).insert(core)
    parent = cell_type(kcl=source)
    instance = parent << child
    trans = kf.kdb.DCplxTrans(1, angle, mirror, 20, 30)
    instance.dcplx_trans = trans
    # Unrelated parent geometry must not affect the selected instance's bounds.
    parent.shapes(xs.layer).insert(kf.kdb.DBox(100, 100, 200, 200))
    bounds = kf.kdb.DPolygon(core).transformed(trans).bbox()
    if not isinstance(instance, kf.VInstance):
        bounds = bounds.to_itype(source.dbu).to_dtype(source.dbu)
    xs.add_bbox(c, ref=instance, top=0)
    for layer, offset in xs.to_dtype().bbox_sections.items():
        expected = bounds.enlarged(offset)
        expected.top = bounds.top
        if not isinstance(c, kf.VKCell):
            expected = expected.to_itype(c.kcl.dbu).to_dtype(c.kcl.dbu)
        assert c.dbbox(c.kcl.layer(layer)) == expected
    assert child.dbbox() == core
    assert instance.dcplx_trans == trans


def test_bbox_cell_reference_rejected(
    xs: Profile, c: kf.KCell | kf.DKCell | kf.VKCell
) -> None:
    ref: Any = c
    with pytest.raises(TypeError, match="ref must be"):
        xs.add_bbox(c, ref=ref)


@pytest.mark.parametrize("cell_type", [kf.KCell, kf.DKCell, kf.VKCell])
def test_bbox_empty_instance(
    xs: Profile,
    c: kf.KCell | kf.DKCell | kf.VKCell,
    cell_type: type[kf.KCell] | type[kf.DKCell] | type[kf.VKCell],
) -> None:
    parent = cell_type(kcl=c.kcl)
    instance = parent << c.kcl.kcell()
    xs.add_bbox(c, ref=instance)
    assert c.dbbox().empty()


@pytest.mark.parametrize("dbu", [0.001, 0.002])
@pytest.mark.parametrize("cell_type", [kf.KCell, kf.DKCell, kf.VKCell])
def test_bbox_different_layout_rejected(
    xs: Profile,
    dbu: float,
    cell_type: type[kf.KCell] | type[kf.DKCell] | type[kf.VKCell],
) -> None:
    target = kf.KCLayout("bbox_target")
    target.layout.dbu = dbu
    target.layer(kf.kdb.LayerInfo(99, 0))
    c = cell_type(kcl=target)
    layers = target.layout.layer_infos()
    with pytest.raises(ValueError, match="same KCLayout"):
        xs.add_bbox(c, ref=0)
    assert target.layout.layer_infos() == layers
    assert c.dbbox().empty()


@pytest.mark.parametrize("cell_type", [kf.KCell, kf.DKCell, kf.VKCell])
def test_bbox_foreign_instance_rejected(
    xs: Profile,
    c: kf.KCell | kf.DKCell | kf.VKCell,
    cell_type: type[kf.KCell] | type[kf.DKCell] | type[kf.VKCell],
) -> None:
    source = kf.KCLayout("bbox_foreign_instance")
    parent = cell_type(kcl=source)
    instance = parent << source.kcell()
    layers = c.kcl.layout.layer_infos()
    with pytest.raises(ValueError, match="same KCLayout"):
        xs.add_bbox(c, ref=instance)
    assert c.kcl.layout.layer_infos() == layers
    assert c.dbbox().empty()


@pytest.mark.parametrize("cell_type", [kf.KCell, kf.DKCell, kf.VKCell])
def test_bbox_target_subclass(
    xs: Profile,
    cell_type: type[kf.KCell] | type[kf.DKCell] | type[kf.VKCell],
) -> None:
    subclass = type("BBoxCell", (cell_type,), {})
    c = subclass(kcl=xs.kcl)
    ref = kf.kdb.DBox(0, -1, 10, 1)
    xs.add_bbox(c, ref=ref)
    for layer, offset in xs.to_dtype().bbox_sections.items():
        assert c.dbbox(c.kcl.layer(layer)) == ref.enlarged(offset)


def test_bbox_invalid_target(xs: Profile) -> None:
    target: Any = object()
    with pytest.raises(TypeError, match="KCell, DKCell, or VKCell"):
        xs.add_bbox(target)


def test_bbox_conversion_before_integer_geometry(
    xs: Profile, c: kf.KCell | kf.DKCell | kf.VKCell
) -> None:
    profile = xs.to_dtype()
    ref = kf.kdb.DBox(0.0012, -1.0012, 10.0012, 1.0012)
    profile.add_bbox(c, ref=ref, top=0.0012)
    for layer, offset in profile.bbox_sections.items():
        if isinstance(c, kf.VKCell):
            expected = ref.enlarged(offset)
            expected.top = ref.top + 0.0012
            assert c.dbbox(c.kcl.layer(layer)) == expected
        else:
            reference = c.kcl.to_dbu(ref)
            expected_dbu = reference.enlarged(c.kcl.to_dbu(offset))
            expected_dbu.top = reference.top + c.kcl.to_dbu(0.0012)
            assert c.ibbox(c.kcl.layer(layer)) == expected_dbu
