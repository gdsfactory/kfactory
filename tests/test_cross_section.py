import pickle
import tempfile
from pathlib import Path

import pytest

import kfactory as kf
from kfactory.exceptions import (
    AsymmetricMirrorRequiredError,
    CrossSectionSymmetryMismatchError,
)


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

    p1 = c.create_port(name="o1", cross_section=xs, trans=kf.kdb.Trans.R0)
    p2 = c.create_port(
        name="o2",
        cross_section=kf.SymmetricalCrossSection(
            width=1000,
            enclosure=enc,
            name="WG_350",
        ),
        trans=kf.kdb.Trans.R90,
    )

    assert p1.cross_section == c.kcl.get_icross_section(xs)
    assert p2.cross_section == c.kcl.get_icross_section(xs)


def _make_asym(name: str = "asym_test") -> kf.AsymmetricalCrossSection:
    return kf.AsymmetricalCrossSection(
        layer=kf.kdb.LayerInfo(1, 0, "WG"),
        section_min=-250,
        section_max=250,
        sections=(
            kf.CrossSectionLayer(
                layer=kf.kdb.LayerInfo(2, 0, "SLAB"),
                section_min=-100,
                section_max=900,
            ),
        ),
        name=name,
    )


def test_asymmetrical_cross_section_construction() -> None:
    acs = _make_asym()
    assert acs.main_layer.layer == 1
    assert acs.width == 500
    assert len(acs.sections) == 1
    # main strip [-250, 250]; aux strip [-100, 900]
    assert acs.get_xmin() == -250
    assert acs.get_xmax() == 900


def test_asymmetrical_cross_section_invalid_bounds() -> None:
    with pytest.raises(ValueError, match="section_min"):
        kf.AsymmetricalCrossSection(
            layer=kf.kdb.LayerInfo(1, 0), section_min=0, section_max=0
        )
    with pytest.raises(ValueError, match="section_min"):
        kf.CrossSectionLayer(
            layer=kf.kdb.LayerInfo(1, 0), section_min=10, section_max=5
        )


def test_cross_section_name_conflict_across_kinds() -> None:
    """Cross section names must be unique across symmetric and asymmetric kinds."""
    kcl = kf.KCLayout("CONFLICT")
    layer = kf.kdb.LayerInfo(1, 0, "WG")
    enc = kcl.get_enclosure(
        kf.LayerEnclosure(
            sections=[(kf.kdb.LayerInfo(2, 0, "S"), 500)], main_layer=layer
        )
    )
    kcl.get_symmetrical_cross_section(
        kf.SymmetricalCrossSection(width=1000, enclosure=enc, name="shared")
    )
    with pytest.raises(ValueError, match="symmetric"):
        kcl.get_asymmetrical_cross_section(
            kf.AsymmetricalCrossSection(
                layer=layer, section_min=-250, section_max=250, name="shared"
            )
        )

    kcl2 = kf.KCLayout("CONFLICT2")
    kcl2.get_asymmetrical_cross_section(
        kf.AsymmetricalCrossSection(
            layer=layer, section_min=-250, section_max=250, name="shared"
        )
    )
    with pytest.raises(ValueError, match="asymmetric"):
        kcl2.get_symmetrical_cross_section(
            kf.SymmetricalCrossSection(width=1000, enclosure=enc, name="shared")
        )


def test_asymmetrical_cross_section_registration() -> None:
    kcl = kf.KCLayout("ASYM_REG")
    acs = _make_asym()
    stored = kcl.get_asymmetrical_cross_section(acs)
    assert stored == acs
    # second registration with same name + same content is a no-op
    again = kcl.get_asymmetrical_cross_section(acs)
    assert again is stored
    # different content under the same name → error
    different = kf.AsymmetricalCrossSection(
        layer=kf.kdb.LayerInfo(1, 0, "WG"),
        section_min=-300,
        section_max=300,
        name="asym_test",
    )
    with pytest.raises(ValueError, match="already an asymmetrical cross_section"):
        kcl.get_asymmetrical_cross_section(different)


def test_asymmetrical_cross_section_dtype_roundtrip() -> None:
    kcl = kf.KCLayout("ASYM_DTYPE")
    acs = _make_asym()
    dacs = acs.to_dtype(kcl)
    assert dacs.width == kcl.to_um(acs.width)
    acs2 = dacs.to_itype(kcl)
    assert acs2 == acs


def test_asymmetrical_cross_section_equality_normalizes_section_order() -> None:
    layer1 = kf.kdb.LayerInfo(2, 0, "SLAB")
    layer2 = kf.kdb.LayerInfo(3, 0, "OTHER")
    a = kf.AsymmetricalCrossSection(
        layer=kf.kdb.LayerInfo(1, 0, "WG"),
        section_min=-250,
        section_max=250,
        sections=(
            kf.CrossSectionLayer(layer=layer1, section_min=-40, section_max=60),
            kf.CrossSectionLayer(layer=layer2, section_min=-80, section_max=120),
        ),
        name="ord",
    )
    b = kf.AsymmetricalCrossSection(
        layer=kf.kdb.LayerInfo(1, 0, "WG"),
        section_min=-250,
        section_max=250,
        sections=(
            kf.CrossSectionLayer(layer=layer2, section_min=-80, section_max=120),
            kf.CrossSectionLayer(layer=layer1, section_min=-40, section_max=60),
        ),
        name="ord",
    )
    assert a == b
    assert hash(a) == hash(b)


def test_asymmetrical_cross_section_sections_dedup() -> None:
    """Identical sections collapse into one."""
    layer = kf.kdb.LayerInfo(2, 0, "SLAB")
    acs = kf.AsymmetricalCrossSection(
        layer=kf.kdb.LayerInfo(1, 0, "WG"),
        section_min=-250,
        section_max=250,
        sections=(
            kf.CrossSectionLayer(layer=layer, section_min=-100, section_max=500),
            kf.CrossSectionLayer(layer=layer, section_min=-100, section_max=500),
        ),
        name="dedup",
    )
    assert len(acs.sections) == 1
    assert acs.sections[0].section_min == -100
    assert acs.sections[0].section_max == 500


def test_asymmetrical_cross_section_sections_merge_overlapping() -> None:
    """Overlapping sections on the same layer are merged into their union."""
    layer = kf.kdb.LayerInfo(2, 0, "SLAB")
    acs = kf.AsymmetricalCrossSection(
        layer=kf.kdb.LayerInfo(1, 0, "WG"),
        section_min=-250,
        section_max=250,
        sections=(
            kf.CrossSectionLayer(layer=layer, section_min=-100, section_max=500),
            kf.CrossSectionLayer(layer=layer, section_min=300, section_max=900),
        ),
        name="overlap",
    )
    assert len(acs.sections) == 1
    assert acs.sections[0].section_min == -100
    assert acs.sections[0].section_max == 900


def test_asymmetrical_cross_section_sections_merge_touching() -> None:
    """Touching sections (max == next.min) on the same layer merge."""
    layer = kf.kdb.LayerInfo(2, 0, "SLAB")
    acs = kf.AsymmetricalCrossSection(
        layer=kf.kdb.LayerInfo(1, 0, "WG"),
        section_min=-250,
        section_max=250,
        sections=(
            kf.CrossSectionLayer(layer=layer, section_min=-100, section_max=300),
            kf.CrossSectionLayer(layer=layer, section_min=300, section_max=700),
        ),
        name="touch",
    )
    assert len(acs.sections) == 1
    assert acs.sections[0].section_min == -100
    assert acs.sections[0].section_max == 700


def test_asymmetrical_cross_section_sections_gap_kept_separate() -> None:
    """Non-touching sections on the same layer stay separate, sorted."""
    layer = kf.kdb.LayerInfo(2, 0, "SLAB")
    acs = kf.AsymmetricalCrossSection(
        layer=kf.kdb.LayerInfo(1, 0, "WG"),
        section_min=-250,
        section_max=250,
        sections=(
            kf.CrossSectionLayer(layer=layer, section_min=600, section_max=700),
            kf.CrossSectionLayer(layer=layer, section_min=-100, section_max=200),
        ),
        name="gap",
    )
    assert len(acs.sections) == 2
    assert (acs.sections[0].section_min, acs.sections[0].section_max) == (-100, 200)
    assert (acs.sections[1].section_min, acs.sections[1].section_max) == (600, 700)


def test_asymmetrical_cross_section_sections_different_layers_independent() -> None:
    """Overlapping sections on different layers are not merged."""
    l1 = kf.kdb.LayerInfo(2, 0, "A")
    l2 = kf.kdb.LayerInfo(3, 0, "B")
    acs = kf.AsymmetricalCrossSection(
        layer=kf.kdb.LayerInfo(1, 0, "WG"),
        section_min=-250,
        section_max=250,
        sections=(
            kf.CrossSectionLayer(layer=l1, section_min=-100, section_max=500),
            kf.CrossSectionLayer(layer=l2, section_min=-200, section_max=400),
        ),
        name="multi",
    )
    assert len(acs.sections) == 2


def test_asymmetrical_cross_section_total_ordering() -> None:
    """AsymmetricalCrossSection and CrossSectionLayer are sortable."""
    layer = kf.kdb.LayerInfo(1, 0, "WG")
    a = kf.AsymmetricalCrossSection(
        layer=layer, section_min=-100, section_max=100, name="a"
    )
    b = kf.AsymmetricalCrossSection(
        layer=layer, section_min=-100, section_max=200, name="b"
    )
    c = kf.AsymmetricalCrossSection(
        layer=kf.kdb.LayerInfo(2, 0, "X"), section_min=-100, section_max=100, name="c"
    )
    assert a < b  # same layer + min, larger max → greater
    assert b < c  # WG < X (name)
    assert sorted([c, b, a]) == [a, b, c]
    assert b > a

    # CrossSectionLayer sortable too
    s1 = kf.CrossSectionLayer(layer=layer, section_min=0, section_max=10)
    s2 = kf.CrossSectionLayer(layer=layer, section_min=0, section_max=20)
    assert s1 < s2
    assert sorted([s2, s1]) == [s1, s2]


def test_asymmetrical_cross_section_pickle() -> None:
    acs = _make_asym()
    restored = pickle.loads(pickle.dumps(acs))  # noqa: S301
    assert isinstance(restored, kf.AsymmetricalCrossSection)
    assert restored == acs


def test_asymmetrical_cross_section_gds_roundtrip() -> None:
    kcl_w = kf.KCLayout("ASYM_GDS_W")
    acs = _make_asym()
    kcl_w.get_asymmetrical_cross_section(acs)
    c = kcl_w.kcell("top")
    c.shapes(kcl_w.layer(kf.kdb.LayerInfo(1, 0, "WG"))).insert(
        kf.kdb.Box(0, 0, 100, 100)
    )

    with tempfile.TemporaryDirectory() as d:
        path = Path(d) / "asym.gds"
        kcl_w.write(path)

        kcl_r = kf.KCLayout("ASYM_GDS_R")
        kcl_r.read(path)

    assert "asym_test" in kcl_r.cross_sections.asymmetrical_cross_sections
    restored = kcl_r.get_asymmetrical_cross_section("asym_test")
    assert restored == acs


def test_connect_symmetric_vs_asymmetric_raises() -> None:
    kcl = kf.KCLayout("ASYM_CONN")
    layer = kf.kdb.LayerInfo(1, 0, "WG")

    parent = kcl.kcell("parent_conn")
    child_a = kcl.kcell("child_a_conn")
    child_a.create_port(name="o1", width=500, layer_info=layer, trans=kf.kdb.Trans.R0)
    child_b = kcl.kcell("child_b_conn")
    child_b.create_port(name="o1", width=500, layer_info=layer, trans=kf.kdb.Trans.R0)

    acs = kcl.get_asymmetrical_cross_section(
        kf.AsymmetricalCrossSection(
            layer=layer, section_min=-250, section_max=250, name="asym_conn"
        )
    )
    # mutate one cell port's cross_section to be asymmetric to simulate the
    # step-2 plumbing
    child_b.ports["o1"].asymmetric_cross_section = acs

    ia = parent << child_a
    ib = parent << child_b

    with pytest.raises(CrossSectionSymmetryMismatchError):
        ia.connect("o1", ib, "o1")
    # not bypassable by allow_width_mismatch
    with pytest.raises(CrossSectionSymmetryMismatchError):
        ia.connect("o1", ib, "o1", allow_width_mismatch=True)


def test_create_port_with_asymmetric_cross_section() -> None:
    kcl = kf.KCLayout("CREATE_PORT_ASYM")
    layer = kf.kdb.LayerInfo(1, 0, "WG")
    acs = kcl.get_asymmetrical_cross_section(
        kf.AsymmetricalCrossSection(
            layer=layer, section_min=-250, section_max=250, name="cp_asym"
        )
    )
    c = kcl.kcell("cp_top")
    c.create_port(name="o1", trans=kf.kdb.Trans.R0, cross_section=acs)

    p = c.ports["o1"]
    assert not p.is_symmetric()
    assert p.asymmetric_cross_section == acs
    assert p.base.cross_section is None
    assert p.base.asymmetric_cross_section is acs
    with pytest.raises(TypeError, match="asymmetric"):
        _ = p.cross_section


def test_port_accessor_setters_route_correctly() -> None:
    kcl = kf.KCLayout("PORT_SETTER")
    layer = kf.kdb.LayerInfo(1, 0, "WG")
    sym = kcl.get_symmetrical_cross_section(
        kf.SymmetricalCrossSection(
            width=500,
            enclosure=kcl.get_enclosure(
                kf.LayerEnclosure(
                    sections=[(kf.kdb.LayerInfo(2, 0, "S"), 500)], main_layer=layer
                )
            ),
            name="setter_sym",
        )
    )
    asym = kcl.get_asymmetrical_cross_section(
        kf.AsymmetricalCrossSection(
            layer=layer, section_min=-250, section_max=250, name="setter_asym"
        )
    )
    c = kcl.kcell("setter_top")
    p = c.create_port(name="o1", trans=kf.kdb.Trans.R0, cross_section=sym)
    assert p.is_symmetric()
    # Switch to asymmetric via setter
    p.asymmetric_cross_section = asym
    assert not p.is_symmetric()
    assert p.base.cross_section is None
    # Switch back
    p.cross_section = sym
    assert p.is_symmetric()
    assert p.base.asymmetric_cross_section is None


def test_port_gds_roundtrip_preserves_asymmetric_kind() -> None:
    kcl_w = kf.KCLayout("PORT_GDS_W")
    layer = kf.kdb.LayerInfo(1, 0, "WG")
    acs = kcl_w.get_asymmetrical_cross_section(
        kf.AsymmetricalCrossSection(
            layer=layer, section_min=-250, section_max=250, name="rt_asym"
        )
    )
    c = kcl_w.kcell("rt_top")
    c.create_port(name="o1", trans=kf.kdb.Trans.R0, cross_section=acs)
    c.shapes(kcl_w.layer(layer)).insert(kf.kdb.Box(0, 0, 100, 100))

    with tempfile.TemporaryDirectory() as d:
        path = Path(d) / "port_rt.gds"
        kcl_w.write(path)
        kcl_r = kf.KCLayout("PORT_GDS_R")
        kcl_r.read(path)

    c_r = kcl_r["rt_top"]
    p_r = c_r.ports["o1"]
    assert not p_r.is_symmetric()
    assert p_r.asymmetric_cross_section.base == acs


def test_asymmetric_wrappers_share_base_and_compare_across_units() -> None:
    kcl = kf.KCLayout("ASYM_WRAP_EQ")
    layer = kf.kdb.LayerInfo(1, 0, "WG")
    # main strip [-200, 300] (offset=50, width=500); aux strip [-100, 900]
    acs = kcl.get_asymmetrical_cross_section(
        kf.AsymmetricalCrossSection(
            layer=layer,
            section_min=-200,
            section_max=300,
            sections=(
                kf.CrossSectionLayer(
                    layer=kf.kdb.LayerInfo(2, 0, "S"),
                    section_min=-100,
                    section_max=900,
                ),
            ),
            name="aw",
        )
    )
    ixs = kf.AsymmetricCrossSection(kcl=kcl, base=acs)
    dxs = ixs.to_dtype()

    # cross-unit equality via shared base
    assert ixs.base is dxs.base
    assert ixs == dxs
    assert dxs == ixs
    # wrapper compares equal to bare base too
    assert ixs == acs
    assert acs == ixs
    assert acs == dxs

    # units differ on the public surface
    assert ixs.width == 500
    assert dxs.width == kcl.to_um(500)
    assert ixs.section_min == -200
    assert dxs.section_min == kcl.to_um(-200)
    assert ixs.section_max == 300
    assert dxs.section_max == kcl.to_um(300)
    assert ixs.get_xmin_xmax() == (-200, 900)
    assert dxs.get_xmin_xmax() == (kcl.to_um(-200), kcl.to_um(900))


def test_asymmetric_wrapper_construct_from_scratch() -> None:
    kcl = kf.KCLayout("ASYM_WRAP_FROM_SCRATCH")
    layer = kf.kdb.LayerInfo(1, 0, "WG")
    ixs = kf.AsymmetricCrossSection(
        kcl,
        section_min=-200,
        section_max=300,
        layer=layer,
        sections=(
            kf.CrossSectionLayer(
                layer=kf.kdb.LayerInfo(2, 0, "S"),
                section_min=-100,
                section_max=900,
            ),
        ),
        name="acs1",
    )
    # builds and registers a base under the hood
    assert "acs1" in kcl.cross_sections.asymmetrical_cross_sections
    # constructing a second wrapper with the same args returns equal wrapper
    ixs2 = kf.AsymmetricCrossSection(kcl=kcl, base=ixs.base)
    assert ixs == ixs2


def test_get_cross_section_kind_switch() -> None:
    kcl = kf.KCLayout("UNIFIED_GET")
    layer = kf.kdb.LayerInfo(1, 0, "WG")
    enc = kcl.get_enclosure(
        kf.LayerEnclosure(
            sections=[(kf.kdb.LayerInfo(2, 0, "S"), 500)], main_layer=layer
        )
    )
    scs = kcl.get_symmetrical_cross_section(
        kf.SymmetricalCrossSection(width=1000, enclosure=enc, name="wg1000")
    )
    acs = kcl.get_asymmetrical_cross_section(
        kf.AsymmetricalCrossSection(
            layer=layer, section_min=-250, section_max=250, name="aw500"
        )
    )

    assert kcl.get_cross_section(scs) is scs
    assert kcl.get_cross_section("wg1000") is scs
    assert kcl.get_cross_section(scs, kind="symmetric") is scs
    assert kcl.get_cross_section(acs, kind="asymmetric") is acs
    assert kcl.get_cross_section("aw500", kind="asymmetric") is acs
    assert kcl.get_cross_section(scs, kind="any") is scs
    assert kcl.get_cross_section(acs, kind="any") is acs
    assert kcl.get_cross_section("wg1000", kind="any") is scs
    assert kcl.get_cross_section("aw500", kind="any") is acs
    # any with a wrapper resolves to its base
    ixs = kcl.get_iasymmetric_cross_section(acs)
    assert kcl.get_cross_section(ixs, kind="any") is acs
    # unknown name under "any" raises
    with pytest.raises(KeyError):
        kcl.get_cross_section("does_not_exist", kind="any")


def test_metadata_uses_separate_prefix_for_asymmetric() -> None:
    kcl_w = kf.KCLayout("META_SEP_W")
    layer = kf.kdb.LayerInfo(1, 0, "WG")
    enc = kcl_w.get_enclosure(
        kf.LayerEnclosure(
            sections=[(kf.kdb.LayerInfo(2, 0, "S"), 500)], main_layer=layer
        )
    )
    kcl_w.get_symmetrical_cross_section(
        kf.SymmetricalCrossSection(width=1000, enclosure=enc, name="wg1000")
    )
    kcl_w.get_asymmetrical_cross_section(
        kf.AsymmetricalCrossSection(
            layer=layer, section_min=-250, section_max=250, name="aw500"
        )
    )
    c = kcl_w.kcell("meta_top")
    c.shapes(kcl_w.layer(layer)).insert(kf.kdb.Box(0, 0, 100, 100))

    with tempfile.TemporaryDirectory() as d:
        path = Path(d) / "meta.gds"
        kcl_w.write(path)
        kcl_w.set_meta_data()
        names = {meta.name for meta in kcl_w.layout.each_meta_info()}
        assert "kfactory:cross_section:wg1000" in names
        assert "kfactory:asymmetrical_cross_section:aw500" in names
        assert "kfactory:cross_section:aw500" not in names

        kcl_r = kf.KCLayout("META_SEP_R")
        kcl_r.read(path)

    assert "wg1000" in kcl_r.cross_sections.cross_sections
    assert "aw500" in kcl_r.cross_sections.asymmetrical_cross_sections


def test_connect_asym_to_asym_requires_mirror_when_misaligned() -> None:
    """Two R0-facing asymmetric ports cannot connect without a mirror.

    Both ports define their profile in the same port-local frame; an R180
    connection between two R0 ports would flip the left/right halves in
    world coordinates. `mirror=True` produces an M90 connection that keeps
    the profiles aligned.
    """
    kcl = kf.KCLayout("ASYM_CONN_R0")
    layer = kf.kdb.LayerInfo(1, 0, "WG")

    parent = kcl.kcell("parent_conn_r0")
    a = kcl.kcell("child_a_r0")
    a.create_port(name="o1", width=500, layer_info=layer, trans=kf.kdb.Trans.R0)
    b = kcl.kcell("child_b_r0")
    b.create_port(name="o1", width=500, layer_info=layer, trans=kf.kdb.Trans.R0)
    acs = kcl.get_asymmetrical_cross_section(
        kf.AsymmetricalCrossSection(
            layer=layer, section_min=-250, section_max=250, name="asym_r0"
        )
    )
    a.ports["o1"].asymmetric_cross_section = acs
    b.ports["o1"].asymmetric_cross_section = acs

    ia = parent << a
    ib = parent << b
    with pytest.raises(AsymmetricMirrorRequiredError):
        ia.connect("o1", ib, "o1")
    # mirror=True succeeds and produces M90 trans
    ia.connect("o1", ib, "o1", mirror=True)
    assert ia.trans.mirror


def _make_asym_wg(kcl: kf.KCLayout, name: str) -> kf.KCell:
    """Asymmetric waveguide cell with the user's convention: o1=R180, o2=M0."""
    layer = kf.kdb.LayerInfo(1, 0, "WG")
    acs = kcl.get_asymmetrical_cross_section(
        kf.AsymmetricalCrossSection(
            layer=layer, section_min=-250, section_max=250, name="aw500"
        )
    )
    c = kcl.kcell(name)
    c.create_port(
        name="o1", width=500, layer_info=layer, trans=kf.kdb.Trans(2, False, 0, 0)
    )
    c.create_port(
        name="o2", width=500, layer_info=layer, trans=kf.kdb.Trans(0, True, 1000, 0)
    )
    c.ports["o1"].asymmetric_cross_section = acs
    c.ports["o2"].asymmetric_cross_section = acs
    return c


def test_asym_waveguide_chain_o2_to_o1_with_mirror_true() -> None:
    """o2 (M0) → o1 (R180) chain succeeds with `mirror=True`, result is unmirrored."""
    kcl = kf.KCLayout("ASYM_WG_CHAIN")
    wg = _make_asym_wg(kcl, "wg")
    parent = kcl.kcell("parent_chain")
    a = parent << wg
    b = parent << wg

    # default connect fails — profiles would misalign
    with pytest.raises(AsymmetricMirrorRequiredError):
        b.connect("o1", a, "o2")

    # mirror=True succeeds and produces a "no-mirror" instance chain
    b.connect("o1", a, "o2", mirror=True)
    assert not a.trans.mirror
    assert not b.trans.mirror


def test_asym_waveguide_o1_to_o1_requires_one_mirror() -> None:
    """o1 (R180) ↔ o1 (R180) succeeds with `mirror=True` and result is mirrored."""
    kcl = kf.KCLayout("ASYM_WG_O1O1")
    wg = _make_asym_wg(kcl, "wg_o1o1")
    parent = kcl.kcell("parent_o1o1")
    a = parent << wg
    b = parent << wg

    with pytest.raises(AsymmetricMirrorRequiredError):
        b.connect("o1", a, "o1")

    b.connect("o1", a, "o1", mirror=True)
    # one instance ends up mirrored
    assert a.trans.mirror ^ b.trans.mirror


def test_asym_connect_check_ignores_input_mirror_flag_when_use_mirror_false() -> None:
    """When use_mirror=False, the geometric check still rejects misaligned results.

    `mirror=True` with a pre-mirrored instance under `use_mirror=False` doesn't
    actually result in M90 — the effective conn_trans is R180. The geometric
    right-direction check catches this, while a naive `mirror`-flag check
    would have wrongly accepted it.
    """
    kcl = kf.KCLayout("ASYM_USE_MIRROR")
    layer = kf.kdb.LayerInfo(1, 0, "WG")
    acs = kcl.get_asymmetrical_cross_section(
        kf.AsymmetricalCrossSection(
            layer=layer, section_min=-250, section_max=250, name="asym_um"
        )
    )
    parent = kcl.kcell("parent_um")
    a = kcl.kcell("a_um")
    a.create_port(name="o1", width=500, layer_info=layer, trans=kf.kdb.Trans.R0)
    a.ports["o1"].asymmetric_cross_section = acs
    b = kcl.kcell("b_um")
    b.create_port(name="o1", width=500, layer_info=layer, trans=kf.kdb.Trans.R0)
    b.ports["o1"].asymmetric_cross_section = acs

    ia = parent << a
    ib = parent << b
    # Pre-mirror ia. Under use_mirror=False the effective M90 vs R180 depends
    # on (mirror XOR existing_mirror). With existing mirror=True and mirror=True,
    # effective is R180 — geometrically wrong for asymmetric.
    ia.trans = kf.kdb.Trans(0, True, 0, 0)
    with pytest.raises(AsymmetricMirrorRequiredError):
        ia.connect("o1", ib, "o1", mirror=True, use_mirror=False)
    # With existing mirror=True and mirror=False, effective is M90 — passes.
    ia.connect("o1", ib, "o1", mirror=False, use_mirror=False)
