import pathlib

import kfactory as kf


def test_connectivity_cell_ports() -> None:
    num_items_per_category = {
        "3_0": {
            "WidthMismatch": 1,
            "TypeMismatch": 1,
            "DanglingPort": 7,
            "InstanceshapeOverlap": 16,
            "CellPorts": 31,
        }
    }

    gds_ref = pathlib.Path(__file__).parent / "test_data"

    kcl = kf.KCLayout("TEST_CONNECTIVITY")
    kcl.read(gds_ref / "nxn_chiplets.gds")
    rdb = kcl["nxn_chiplets"].connectivity_check(
        port_types=["optical", "electrical"], add_cell_ports=True
    )

    assert rdb.num_items() == 56

    for category, sub_categories in num_items_per_category.items():
        category_ = rdb.category_by_path(category)
        for sub_category in category_.each_sub_category():
            assert sub_category.name() in sub_categories
            assert sub_category.num_items() == sub_categories[sub_category.name()]

    kf.layout.kcls.pop(kcl.name)


def test_connectivity() -> None:
    num_items_per_category = {
        "3_0": {
            "WidthMismatch": 1,
            "TypeMismatch": 1,
            "DanglingPort": 7,
            "InstanceshapeOverlap": 16,
        }
    }

    gds_ref = pathlib.Path(__file__).parent / "test_data"

    kcl = kf.KCLayout("TEST_CONNECTIVITY")
    kcl.read(gds_ref / "nxn_chiplets.gds")
    rdb = kcl["nxn_chiplets"].connectivity_check(port_types=["optical", "electrical"])

    assert rdb.num_items() == 25

    for category, sub_categories in num_items_per_category.items():
        category_ = rdb.category_by_path(category)
        for sub_category in category_.each_sub_category():
            assert sub_category.name() in sub_categories
            assert sub_category.num_items() == sub_categories[sub_category.name()]

    kf.layout.kcls.pop(kcl.name)


def test_connectivity_no_rec() -> None:
    num_items_per_category = {
        "3_0": {
            "DanglingPort": 4,
            "InstanceshapeOverlap": 16,
        }
    }

    gds_ref = pathlib.Path(__file__).parent / "test_data"

    kcl = kf.KCLayout("TEST_CONNECTIVITY")
    kcl.read(gds_ref / "nxn_chiplets.gds")
    rdb = kcl["nxn_chiplets"].connectivity_check(
        port_types=["optical", "electrical"], add_cell_ports=True, recursive=False
    )

    assert rdb.num_items() == 20

    for category, sub_categories in num_items_per_category.items():
        category_ = rdb.category_by_path(category)
        for sub_category in category_.each_sub_category():
            assert sub_category.name() in sub_categories
            assert sub_category.num_items() == sub_categories[sub_category.name()]

    kf.layout.kcls.pop(kcl.name)


def _load_chiplets() -> kf.KCell:
    gds_ref = pathlib.Path(__file__).parent / "test_data"
    kcl = kf.KCLayout("TEST_CONNECTIVITY")
    kcl.read(gds_ref / "nxn_chiplets.gds")
    return kcl["nxn_chiplets"]


def test_dangling_ports_check_standalone() -> None:
    cell = _load_chiplets()
    rdb = kf.checks.dangling_ports_check(cell, port_types=["optical", "electrical"])

    assert rdb.num_items() == 7
    cat = rdb.category_by_path("3_0.DanglingPort")
    assert cat is not None
    assert cat.num_items() == 7

    kf.layout.kcls.pop(cell.kcl.name)


def test_instance_overlap_check_standalone() -> None:
    cell = _load_chiplets()
    rdb = kf.checks.instance_overlap_check(cell)

    cat = rdb.category_by_path("3_0.InstanceshapeOverlap")
    assert cat is not None
    assert cat.num_items() == 16

    kf.layout.kcls.pop(cell.kcl.name)


def test_shape_instance_overlap_check_standalone() -> None:
    cell = _load_chiplets()
    rdb = kf.checks.shape_instance_overlap_check(cell)

    cat = rdb.category_by_path("3_0.ShapeInstanceshapeOverlap")
    # No top-level shapes overlap with instances in this fixture.
    assert cat is None or cat.num_items() == 0

    kf.layout.kcls.pop(cell.kcl.name)


def test_port_mismatch_check_standalone() -> None:
    cell = _load_chiplets()
    rdb = kf.checks.port_mismatch_check(cell, port_types=["optical", "electrical"])

    width = rdb.category_by_path("3_0.WidthMismatch")
    typ = rdb.category_by_path("3_0.TypeMismatch")
    assert width is not None
    assert width.num_items() == 1
    assert typ is not None
    assert typ.num_items() == 1
    # The mismatch check must not emit DanglingPort items.
    assert rdb.category_by_path("3_0.DanglingPort") is None

    kf.layout.kcls.pop(cell.kcl.name)


def test_port_mismatch_check_toggle_width() -> None:
    cell = _load_chiplets()
    rdb = kf.checks.port_mismatch_check(
        cell, port_types=["optical", "electrical"], check_width=False
    )
    assert rdb.category_by_path("3_0.WidthMismatch") is None
    typ = rdb.category_by_path("3_0.TypeMismatch")
    assert typ is not None
    assert typ.num_items() == 1

    kf.layout.kcls.pop(cell.kcl.name)
