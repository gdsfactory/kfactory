import kfactory as kf


def test_pack_kcells(kcl: kf.KCLayout) -> None:
    c = kcl.kcell()
    straight = kf.factories.straight.straight_dbu_factory(kcl)(
        width=1000, length=1000, layer=kf.kdb.LayerInfo(1, 0)
    )
    instance_group = kf.packing.pack_kcells(
        c, [straight] * 4, max_height=2000, max_width=2000
    )
    assert instance_group.bbox() == kf.kdb.DBox(0, 0, 2000, 2000)


def test_pack_instances(kcl: kf.KCLayout) -> None:
    c = kcl.kcell()
    straight = kf.factories.straight.straight_dbu_factory(kcl)(
        width=1000, length=1000, layer=kf.kdb.LayerInfo(1, 0)
    )
    ref = c << straight
    ref2 = c << straight
    ref3 = c << straight
    ref4 = c << straight
    instance_group = kf.packing.pack_instances(
        c, [ref, ref2, ref3, ref4], max_height=2000, max_width=2000
    )
    assert instance_group.bbox() == kf.kdb.DBox(0, 0, 2000, 2000)
