import pytest

from kfactory import KCell, KCLayout


def test_factory_name(kcl: KCLayout) -> None:
    def test_cell_function() -> KCell:
        return KCell()

    c = test_cell_function()
    with pytest.raises(ValueError):
        c.factory_name  # noqa: B018
