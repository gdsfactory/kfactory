import pathlib

import kfactory as kf


def test_connectivity_cell_ports() -> None:
    num_items_per_category = {
        "3_0": {
            "WidthMismatch": 1,
            "TypeMismatch": 1,
            "OrphanPort": 7,
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
            "OrphanPort": 7,
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
            "OrphanPort": 4,
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
