from collections.abc import Callable

import pytest

from kfactory import KCell, KCLayout, LayerEnclosure, VKCell, factories
from kfactory.cells import demo
from kfactory.exceptions import FactoriesLockedError

from .conftest import Layers


def test_factory_name(kcl: KCLayout) -> None:
    def test_cell_function() -> KCell:
        return KCell()

    c = test_cell_function()
    with pytest.raises(ValueError):
        c.factory_name  # noqa: B018


def test_factory_basename(kcl: KCLayout) -> None:
    factories.straight.straight_dbu_factory(kcl=kcl)
    factories.straight.straight_dbu_factory(kcl=kcl, basename="straight2")

    f1 = kcl.factories.get_by_name("straight")
    f2 = kcl.factories.get_by_name("straight2")
    assert f1 is not f2


def test_factory_retrieval(
    straight: Callable[..., KCell], layers: Layers, wg_enc: LayerEnclosure
) -> None:
    straight_ = demo.factories["straight"]
    c = straight_(width=1000, length=10_000, layer=layers.WG, enclosure=wg_enc)
    assert isinstance(c, KCell)

    with pytest.raises(
        KeyError,
        match=(
            r"Unknown Factory 'straights', closest 10 name matches: "
            r"\['straight',"
        ),
    ):
        demo.factories["straights"]


def test_factories_unlocked_by_default(kcl: KCLayout) -> None:
    assert kcl.factories.locked is False
    assert kcl.virtual_factories.locked is False
    assert kcl.factories_locked is False


def test_lock_blocks_real_factory_registration(kcl: KCLayout) -> None:
    kcl.lock_factories()
    assert kcl.factories_locked is True

    with pytest.raises(FactoriesLockedError, match="locked_cell"):

        @kcl.cell
        def locked_cell() -> KCell:
            return kcl.kcell()


def test_lock_blocks_virtual_factory_registration(kcl: KCLayout) -> None:
    kcl.lock_factories()

    with pytest.raises(FactoriesLockedError, match="locked_vcell"):

        @kcl.vcell
        def locked_vcell() -> VKCell:
            return VKCell(kcl=kcl)


def test_lock_factories_via_collection(kcl: KCLayout) -> None:
    kcl.factories.lock()
    assert kcl.factories.locked is True
    assert kcl.virtual_factories.locked is False
    assert kcl.factories_locked is False

    with pytest.raises(FactoriesLockedError):
        factories.straight.straight_dbu_factory(kcl=kcl)


def test_factories_can_register_before_lock(kcl: KCLayout) -> None:
    factories.straight.straight_dbu_factory(kcl=kcl)
    kcl.lock_factories()
    assert "straight" in kcl.factories
    assert kcl.factories_locked is True
