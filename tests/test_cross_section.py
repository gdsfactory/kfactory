import kfactory as kf


def test_icross_section_creation() -> None:
    xs = kf.kcl.get_icross_section(
        kf.cross_section.CrossSectionSpec[int](
            name="WG_350",
            sections=[(kf.kdb.LayerInfo(2, 0), 500)],
            layer=kf.kdb.LayerInfo(1, 0),
            width=1000,
        )
    )
    assert xs._base in kf.kcl.cross_sections.cross_sections.values()
