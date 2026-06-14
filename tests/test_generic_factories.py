"""Tests for `KCLayout.generic_factories` and the `@kcl.generic_factory` decorator."""

import pytest

import kfactory as kf
from tests.conftest import Layers


def test_generic_factory_registration_and_delegation(
    kcl: kf.KCLayout, layers: Layers, wg_enc: kf.LayerEnclosure
) -> None:
    real_straight = kf.factories.straight.straight_dbu_factory(kcl=kcl)

    @kcl.generic_factory
    def my_straight(length: int) -> kf.KCell:
        return real_straight(
            width=500, length=length, layer=layers.WG, enclosure=wg_enc
        )

    # Registered under the function name and retrievable.
    assert "my_straight" in kcl.generic_factories
    assert kcl.generic_factories["my_straight"] is my_straight

    # Delegation works: calling forwards to the cached real factory.
    c = kcl.generic_factories["my_straight"](length=10_000)
    assert isinstance(c, kf.KCell)
    assert c.kcl is kcl
    # Same args -> cached cell from the underlying factory.
    assert my_straight(length=10_000) is c


def test_generic_factory_guardrail_rejects_foreign_kcl(
    kcl: kf.KCLayout, layers: Layers
) -> None:
    # The global default layout is a *different* layout than the fixture `kcl`.
    other_straight = kf.factories.straight.straight_dbu_factory(kcl=kf.kcl)

    @kcl.generic_factory
    def foreign(length: int) -> kf.KCell:
        # Builds a cell owned by `kf.kcl`, not by `kcl`.
        return other_straight(width=500, length=length, layer=layers.WG)

    with pytest.raises(ValueError, match="returned a cell from KCLayout"):
        foreign(length=10_000)


def test_generic_factories_independent_of_other_registries(
    kcl: kf.KCLayout, layers: Layers
) -> None:
    real_straight = kf.factories.straight.straight_dbu_factory(kcl=kcl)

    @kcl.generic_factory
    def only_generic(length: int) -> kf.KCell:
        return real_straight(width=500, length=length, layer=layers.WG)

    assert "only_generic" in kcl.generic_factories
    assert "only_generic" not in kcl.factories
    assert "only_generic" not in kcl.virtual_factories


def test_generic_factory_custom_name(kcl: kf.KCLayout, layers: Layers) -> None:
    real_straight = kf.factories.straight.straight_dbu_factory(kcl=kcl)

    # Decorator-with-name form.
    @kcl.generic_factory(name="wg")
    def my_straight(length: int) -> kf.KCell:
        return real_straight(width=500, length=length, layer=layers.WG)

    assert "wg" in kcl.generic_factories
    assert "my_straight" not in kcl.generic_factories
    assert isinstance(kcl.generic_factories["wg"](length=10_000), kf.KCell)

    # Direct-call form with a name.
    def another(length: int) -> kf.KCell:
        return real_straight(width=500, length=length, layer=layers.WG)

    kcl.generic_factory(another, name="wg2")
    assert "wg2" in kcl.generic_factories
