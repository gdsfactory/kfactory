from pathlib import Path
from tempfile import NamedTemporaryFile

import klayout.db as kdb
import pytest
from klayout import lay

import kfactory as kf
from kfactory.serialization import (
    deserialize_info_blob,
    deserialize_setting,
    serialize_info_blob,
    serialize_setting,
)


def _all_shapes() -> dict[str, object]:
    """Every kdb shape kfactory claims to serialize, one sample each."""
    return {
        "Box": kdb.Box(0, 0, 10, 10),
        "DBox": kdb.DBox(0, 0, 1.5, 2.5),
        "Point": kdb.Point(1, 2),
        "DPoint": kdb.DPoint(1.5, 2.5),
        "Vector": kdb.Vector(3, 4),
        "DVector": kdb.DVector(3.5, 4.5),
        "Trans": kdb.Trans(1, False, 10, 20),
        "DTrans": kdb.DTrans(1, False, 1.0, 2.0),
        "CplxTrans": kdb.CplxTrans(2.0),
        "ICplxTrans": kdb.ICplxTrans(2.0),
        "DCplxTrans": kdb.DCplxTrans(1.0, 30.0, False, 1.0, 2.0),
        "VCplxTrans": kdb.VCplxTrans(2.0),
        "Edge": kdb.Edge(0, 0, 10, 10),
        "DEdge": kdb.DEdge(0, 0, 1.0, 1.0),
        "Path": kdb.Path([kdb.Point(0, 0), kdb.Point(10, 0)], 5),
        "DPath": kdb.DPath([kdb.DPoint(0, 0), kdb.DPoint(1, 0)], 0.5),
        "Polygon": kdb.Polygon(kdb.Box(0, 0, 100, 100)),
        "DPolygon": kdb.DPolygon(kdb.DBox(0, 0, 1, 1)),
        "SimplePolygon": kdb.SimplePolygon(kdb.Box(0, 0, 50, 50)),
        "DSimplePolygon": kdb.DSimplePolygon(kdb.DBox(0, 0, 1, 1)),
        "Text": kdb.Text("hi", kdb.Trans()),
        "DText": kdb.DText("hi", kdb.DTrans()),
        "EdgePair": kdb.EdgePair(kdb.Edge(0, 0, 1, 1), kdb.Edge(2, 2, 3, 3)),
        "DEdgePair": kdb.DEdgePair(kdb.DEdge(0, 0, 1, 1), kdb.DEdge(2, 2, 3, 3)),
        "LayerInfo": kdb.LayerInfo(1, 0),
        # collection / matrix wrappers: no from_s, encoded element-wise
        "Region": kdb.Region(
            [kdb.Polygon(kdb.Box(0, 0, 50, 50)), kdb.Polygon(kdb.Box(100, 0, 150, 60))]
        ),
        "Edges": kdb.Edges([kdb.Edge(0, 0, 10, 10), kdb.Edge(1, 1, 2, 2)]),
        "Texts": kdb.Texts([kdb.Text("a", kdb.Trans()), kdb.Text("b", kdb.Trans())]),
        "EdgePairs": kdb.EdgePairs(
            [kdb.EdgePair(kdb.Edge(0, 0, 1, 1), kdb.Edge(2, 2, 3, 3))]
        ),
        "Matrix2d": kdb.Matrix2d(1.5, 2.0, 3.0, 4.0),
        "Matrix3d": kdb.Matrix3d(1, 0, 5, 0, 1, 7, 0, 0, 1),
    }


@pytest.mark.parametrize(("name", "shape"), list(_all_shapes().items()))
def test_serialize_setting_symmetric(name: str, shape: object) -> None:
    """serialize_setting and deserialize_setting round-trip every shape."""
    restored = deserialize_setting(serialize_setting(shape))
    assert type(restored) is type(shape)
    assert restored.to_s() == shape.to_s()  # ty:ignore[unresolved-attribute]


def test_serialize_setting_scalars_and_containers() -> None:
    """Plain metadata passes through; tuples become lists (JSON has no tuple)."""
    assert serialize_setting(42) == 42
    assert serialize_setting("x") == "x"
    assert serialize_setting(True) is True
    assert serialize_setting(None) is None
    nested = {"a": [1, {"b": kdb.Box(0, 0, 5, 5)}]}
    restored = deserialize_setting(serialize_setting(nested))
    assert restored["a"][1]["b"].to_s() == kdb.Box(0, 0, 5, 5).to_s()


def test_info_blob_roundtrip_all_shapes() -> None:
    """The single-blob codec (used by instance info) round-trips every shape."""
    shapes = _all_shapes()
    restored = deserialize_info_blob(serialize_info_blob(shapes))
    for name, shape in shapes.items():
        assert type(restored[name]) is type(shape)
        assert restored[name].to_s() == shape.to_s()


def test_collection_payload_survives_delimiter_characters() -> None:
    """Element strings reuse ';' ')' '\\''; JSON payload must not be confused."""
    texts = kdb.Texts(
        [kdb.Text("has;semi)paren'quote", kdb.Trans()), kdb.Text("b", kdb.Trans())]
    )
    restored = deserialize_setting(serialize_setting(texts))
    assert restored.to_s() == texts.to_s()


def test_cell_info_region_yaml_roundtrip() -> None:
    """Regression: a Region in cell info must survive a YAML roundtrip.

    Before the codec was made symmetric this raised ``AttributeError: type
    object 'Region' has no attribute 'from_s'`` on read.
    """
    kcl = kf.KCLayout("TEST_CELL_INFO_YAML")
    c = kcl.kcell("c")
    c.shapes(kcl.layer(1, 0)).insert(kdb.Box(0, 0, 1000, 1000))
    c.info["reg"] = kdb.Region(kdb.Box(0, 0, 500, 500))
    c.info["n"] = 42

    with NamedTemporaryFile(suffix=".yml", delete=False) as _tf:
        tf = Path(_tf.name)
    kf.placer.cells_to_yaml(tf, cells=c)
    kcl_read = kf.KCLayout("TEST_CELL_INFO_YAML_READ")
    kf.placer.cells_from_yaml(tf, kcl=kcl_read)
    tf.unlink()

    info = kcl_read["c"].info
    assert info["n"] == 42
    assert type(info["reg"]) is kdb.Region
    assert info["reg"].to_s() == kdb.Region(kdb.Box(0, 0, 500, 500)).to_s()


def test_layer_properties_no_longer_serializable() -> None:
    """LayerProperties cannot round-trip anywhere and is rejected up front."""
    kcl = kf.KCLayout("TEST_LP_REJECT")
    c = kcl.kcell("c")
    with pytest.raises((ValueError, TypeError)):
        c.info["lp"] = lay.LayerProperties()
