from collections.abc import Callable

import pytest

from kfactory import KCell, KCLayout, LayerEnclosure, factories
from kfactory.cells import demo

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
