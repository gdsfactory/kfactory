import pathlib

import kfactory as kf

num_items_per_category = {
    "3_0": {
        "WidthMismatch": 1,
        "TypeMismatch": 1,
        "OrphanPort": 7,
        "InstanceshapeOverlap": 1,
    }
}

gds_ref = pathlib.Path(__file__).parent / "test_data"

kcl = kf.KCLayout("TEST")
kcl.read(gds_ref / "nxn_chiplets.gds")
rdb = kcl["nxn_chiplets"].connectivity_check(port_types=["optical", "electrical"])


for category, sub_categories in num_items_per_category.items():
    category_ = rdb.category_by_path(category)
    for sub_category in category_.each_sub_category():
        assert sub_category.name() in sub_categories
        assert sub_category.num_items() == sub_categories[sub_category.name()]
