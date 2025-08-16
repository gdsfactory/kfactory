import kfactory as kf


def test_icross_section_creation(kcl: kf.KCLayout) -> None:
    xs = kcl.get_icross_section(
        kf.cross_section.CrossSectionSpec(
            name="WG_350",
            sections=[(kf.kdb.LayerInfo(2, 0), 500)],
            layer=kf.kdb.LayerInfo(1, 0),
            width=1000,
        )
    )
    assert xs.base in kcl.cross_sections.cross_sections.values()


def test_port_cross_section(kcl: kf.KCLayout, layers: kf.LayerInfos) -> None:
    c = kf.kcl.kcell()
    enc = kf.kcl.get_enclosure(
        kf.LayerEnclosure(
            sections=[(kf.kdb.LayerInfo(2, 0), 500)],
            main_layer=kf.kdb.LayerInfo(1, 0),
        ),
    )

    xs = kcl.get_icross_section(
        kf.cross_section.CrossSectionSpec(
            name="WG_350",
            sections=[(kf.kdb.LayerInfo(2, 0), 500)],
            layer=kf.kdb.LayerInfo(1, 0),
            width=1000,
        )
    )

    p1 = c.create_port(cross_section=xs, trans=kf.kdb.Trans.R0)
    p2 = c.create_port(
        cross_section=kf.SymmetricalCrossSection(
            width=1000,
            enclosure=enc,
            name="WG_350",
        ),
        trans=kf.kdb.Trans.R90,
    )

    assert p1.cross_section == c.kcl.get_icross_section(xs)
    assert p2.cross_section == c.kcl.get_icross_section(xs)
