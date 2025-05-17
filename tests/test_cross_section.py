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
