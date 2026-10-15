from collections.abc import Callable

import pytest
from pydantic import ValidationError

import kfactory as kf
from kfactory.exceptions import ExtrudeConfigConflictError


def _make_asym() -> kf.AsymmetricalCrossSection:
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
    )


def test_extrude_config_unset(
    kcl: kf.KCLayout, sym_enc: Callable[..., kf.LayerEnclosure]
) -> None:
    xs = kf.SymmetricalCrossSection(width=1000, enclosure=sym_enc())
    assert kcl.get_extrude_config(xs) is None


def test_extrude_config_symmetrical(
    kcl: kf.KCLayout, sym_enc: Callable[..., kf.LayerEnclosure]
) -> None:
    xs = kf.SymmetricalCrossSection(width=1000, enclosure=sym_enc(), name="heater")
    config = kf.ExtrudeConfig(
        ports={0: ("o1", "o2", "optical"), 1: ("e1", "e2", "electrical")},
        insets={1: (5000, 5000)},
        simplify=50,
        hidden=frozenset({1}),
        add_bbox=True,
    )
    kcl.set_extrude_config(xs, config)

    assert kcl.get_extrude_config(xs) is config
    assert kcl.get_extrude_config("heater") is config
    assert kcl.get_extrude_config(kf.CrossSection(kcl, base=xs)) is config
    assert kcl.extrude_configs == {xs.auto_name(): config}


def test_extrude_config_unnamed_then_named(
    kcl: kf.KCLayout, sym_enc: Callable[..., kf.LayerEnclosure]
) -> None:
    unnamed = kf.SymmetricalCrossSection(width=1000, enclosure=sym_enc())
    config = kf.ExtrudeConfig(ports={})
    kcl.set_extrude_config(unnamed, config)

    named = kf.SymmetricalCrossSection(width=1000, enclosure=sym_enc(), name="wg")
    assert kcl.get_extrude_config(named) is config
    assert kcl.get_extrude_config("wg") is config


def test_extrude_config_asymmetrical(kcl: kf.KCLayout) -> None:
    xs = _make_asym()
    config = kf.ExtrudeConfig(insets={0: (-500, 0), 1: (0, 1000)})
    kcl.set_extrude_config(xs, config)

    assert kcl.get_extrude_config(xs) is config
    assert kcl.get_extrude_config(xs.name) is config


def test_extrude_config_replace(
    kcl: kf.KCLayout, sym_enc: Callable[..., kf.LayerEnclosure]
) -> None:
    xs = kf.SymmetricalCrossSection(width=1000, enclosure=sym_enc())
    kcl.set_extrude_config(xs, kf.ExtrudeConfig(add_bbox=True))
    config = kf.ExtrudeConfig()
    kcl.set_extrude_config(xs, config)

    assert kcl.get_extrude_config(xs) is config


def test_extrude_config_unknown_strip(
    kcl: kf.KCLayout, sym_enc: Callable[..., kf.LayerEnclosure]
) -> None:
    xs = kf.SymmetricalCrossSection(width=1000, enclosure=sym_enc())
    n_sections = len(xs.get_sections())
    config = kf.ExtrudeConfig(insets={n_sections: (1000, 1000)})
    with pytest.raises(ValueError, match=rf"strips \[{n_sections}\]"):
        kcl.set_extrude_config(xs, config)
    assert kcl.get_extrude_config(xs) is None


@pytest.mark.parametrize(
    "kwargs",
    [
        {"ports": {-1: ("o1", "o2", "optical")}},
        {"hidden": frozenset({-1})},
        {"simplify": -1},
        {"simplify": {0: -1}},
    ],
)
def test_extrude_config_invalid(kwargs: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        kf.ExtrudeConfig.model_validate(kwargs)


def test_extrude_config_section_indices() -> None:
    config = kf.ExtrudeConfig(
        ports={0: ("o1", "o2", "optical")},
        insets={2: (0, 0)},
        simplify={3: 10},
        hidden=frozenset({4}),
    )
    assert config.section_indices() == {0, 2, 3, 4}


def test_extrude_config_conflict_raises(
    kcl: kf.KCLayout, sym_enc: Callable[..., kf.LayerEnclosure]
) -> None:
    xs = kf.SymmetricalCrossSection(width=1000, enclosure=sym_enc())
    config = kf.ExtrudeConfig(ports={})
    kcl.set_extrude_config(xs, config, on_conflict="raise")
    with pytest.raises(ExtrudeConfigConflictError):
        kcl.set_extrude_config(xs, kf.ExtrudeConfig(add_bbox=True), on_conflict="raise")
    assert kcl.get_extrude_config(xs) is config


def test_extrude_config_conflict_equal(
    kcl: kf.KCLayout, sym_enc: Callable[..., kf.LayerEnclosure]
) -> None:
    xs = kf.SymmetricalCrossSection(width=1000, enclosure=sym_enc())
    kcl.set_extrude_config(xs, kf.ExtrudeConfig(insets={0: (10, 10)}))
    equal = kf.ExtrudeConfig(insets={0: (10, 10)})
    kcl.set_extrude_config(xs, equal, on_conflict="raise")
    assert kcl.get_extrude_config(xs) == equal


def test_extrude_config_conflict_named_shares_config(
    kcl: kf.KCLayout, sym_enc: Callable[..., kf.LayerEnclosure]
) -> None:
    unnamed = kf.SymmetricalCrossSection(width=1000, enclosure=sym_enc())
    kcl.set_extrude_config(unnamed, kf.ExtrudeConfig(ports={}))
    named = kf.SymmetricalCrossSection(width=1000, enclosure=sym_enc(), name="wg")
    with pytest.raises(ExtrudeConfigConflictError):
        kcl.set_extrude_config(named, kf.ExtrudeConfig(), on_conflict="raise")
