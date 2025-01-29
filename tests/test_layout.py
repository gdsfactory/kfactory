import functools
from unittest.mock import MagicMock

import pytest
from conftest import Layers

import kfactory as kf


def test_cell_decorator(kcl: kf.KCLayout, LAYER: Layers) -> None:
    rectangle_post_process = MagicMock()

    @kcl.cell(post_process=[rectangle_post_process])
    def rectangle(width: float, height: float, layer: kf.kdb.LayerInfo) -> kf.DKCell:
        c = kcl.dkcell()
        c.shapes(layer).insert(kf.kdb.DBox(0, 0, width, height))
        return c

    rectangle_cell = rectangle(10, 10, LAYER.WG)
    rectangle_cell2 = rectangle(10, 10, LAYER.WG)
    rectangle_cell3 = rectangle(10.1, 10.1, LAYER.WG)

    assert rectangle_cell is rectangle_cell2
    assert rectangle_cell is not rectangle_cell3

    rectangle_post_process.assert_any_call(rectangle_cell.base_kcell)
    rectangle_post_process.assert_any_call(rectangle_cell3.base_kcell)
    assert rectangle_post_process.call_count == 2


def test_set_settings_functionality(kcl: kf.KCLayout) -> None:
    @kcl.cell(set_settings=True)
    def test_set_settings(
        name: str = "test_set_settings",
        width: float = 10.0,
        height: float = 5.0,
    ) -> kf.KCell:
        c = kcl.kcell(name=name)
        return c

    cell_with_settings = test_set_settings()
    assert cell_with_settings.settings["width"] == 10.0
    assert cell_with_settings.settings["height"] == 5.0

    @kcl.cell(set_settings=False)
    def test_set_settings_no_settings(
        name: str = "test_set_settings_no",
        width: float = 10.0,
        height: float = 5.0,
    ) -> kf.KCell:
        c = kcl.kcell(name=name)
        return c

    cell_without_settings = test_set_settings_no_settings()
    assert cell_without_settings.settings == kf.KCellSettings()

    test_set_settings_partial = functools.partial(
        test_set_settings,
        name="test_set_settings_partial",
    )
    cell_with_settings_partial = test_set_settings_partial()
    assert cell_with_settings_partial.function_name == "test_set_settings"


def test_overwrite_existing(kcl: kf.KCLayout) -> None:
    @kcl.cell(overwrite_existing=False)
    def test_cell_no_overwrite(name: str) -> kf.KCell:
        return kcl.kcell(name=name)

    cell1 = test_cell_no_overwrite("cell1")
    cell2 = test_cell_no_overwrite("cell1")

    assert cell1.kdb_cell is cell2.kdb_cell

    cell3 = kcl.kcell(name="test_cell_with_overwrite_Ncell3")

    @kcl.cell(overwrite_existing=True)
    def test_cell_with_overwrite(name: str) -> kf.KCell:
        return kcl.kcell(name=name)

    cell4 = test_cell_with_overwrite("cell3")

    assert cell3.kdb_cell is not cell4.kdb_cell
    assert cell3.destroyed()


def test_overwrite_existing_layout_cache(kcl: kf.KCLayout) -> None:
    cell1 = kcl.kcell(name="test_cell_with_overwrite_Ncell3")

    @kcl.cell(overwrite_existing=True, layout_cache=True)
    def test_cell_with_overwrite(name: str) -> kf.KCell:
        return kcl.kcell(name=name)

    cell2 = test_cell_with_overwrite("cell3")

    assert cell1.kdb_cell is not cell2.kdb_cell
    assert cell1.destroyed()


def test_cell_already_locked(kcl: kf.KCLayout) -> None:
    cell1 = kcl.kcell(name="cell1")

    @kcl.cell
    def test_cell_with_overwrite(name: str) -> kf.KCell:
        cell1.lock()
        return cell1

    cell2 = test_cell_with_overwrite("cell1")

    assert cell1.kdb_cell is not cell2.kdb_cell


def test_cell_name_already_exists(kcl: kf.KCLayout) -> None:
    cell1 = kcl.kcell(name="test_cell_name_already_exists_Ncell1")

    @kcl.cell(debug_names=True, set_name=True)
    def test_cell_name_already_exists(name: str) -> kf.KCell:
        kcl.kcell(name=name)
        return cell1

    with pytest.raises(kf.exceptions.CellNameError):
        test_cell_name_already_exists("cell1")


def test_cell_with_different_kcl(kcl: kf.KCLayout) -> None:
    kcl2 = kf.KCLayout(name="kcl2")

    @kcl2.cell(overwrite_existing=True)
    def test_cell_with_overwrite(name: str) -> kf.KCell:
        return kcl.kcell(name=name)

    with pytest.raises(ValueError):
        test_cell_with_overwrite("cell1")


def test_cell_parameters(kcl: kf.KCLayout) -> None:
    @kcl.cell
    def test_cell_with_empty_parameters(
        name: str,
        width: float,
        height: float,
    ) -> kf.KCell:
        cell = kcl.kcell(name=name)
        return cell

    with pytest.raises(TypeError):
        test_cell_with_empty_parameters(name="test_cell_with_empty_parameters")  # type: ignore


def test_check_instances(kcl: kf.KCLayout) -> None:
    def test_cell_with_rotation(name: str) -> kf.DKCell:
        cell = kcl.dkcell()

        layer = kf.kdb.LayerInfo(1, 0)
        cell.shapes(layer).insert(kf.kdb.DBox(0, 0, 1000, 1000))
        parent_cell = kcl.dkcell(name=name)

        inst = parent_cell << cell

        inst.rotate(1.234)
        return parent_cell

    with pytest.raises(ValueError):
        kcl.cell(check_instances=kf.kcell.CHECK_INSTANCES.RAISE)(
            test_cell_with_rotation,
        )("test_rase")

    cell = kcl.cell(check_instances=kf.kcell.CHECK_INSTANCES.FLATTEN)(
        test_cell_with_rotation,
    )("test_flatten")

    assert len(cell.insts) == 0

    cell2 = kcl.cell(check_instances=kf.kcell.CHECK_INSTANCES.VINSTANCES)(
        test_cell_with_rotation,
    )("test_vinstances")

    assert cell2 is not cell
    assert len(cell2.vinsts) == 0
    assert len(cell2.insts) == 1

    kcl.cell(check_instances=kf.kcell.CHECK_INSTANCES.IGNORE)(test_cell_with_rotation)(
        "test_ignore",
    )


def test_cell_decorator_types(kcl: kf.KCLayout) -> None:
    class KCellSubclass(kf.KCell):
        pass

    @kcl.cell(output_type=KCellSubclass)
    def test_cell(name: str) -> kf.KCell:
        cell = kcl.kcell(name=name)
        return cell

    @kcl.cell(layout_cache=True, output_type=kf.KCell)
    def test_kcell(name: str) -> kf.KCell:
        cell = kcl.kcell(name=name)
        return cell

    @kcl.cell(output_type=kf.DKCell)
    def test_k_to_dkcell(name: str) -> kf.KCell:
        cell = kcl.kcell(name=name)
        return cell

    @kcl.cell(output_type=kf.DKCell)
    def test_dkcell(name: str) -> kf.DKCell:
        cell = kcl.dkcell(name=name)
        return cell

    @kcl.cell
    def test_dk_to_kcell(name: str) -> kf.DKCell:
        cell = kcl.dkcell(name=name)
        return cell

    k_to_dkcell = test_k_to_dkcell("test_d_to_kcell")
    kcell = test_kcell("test_lcell")
    cell = test_cell("test_cell")
    dkcell = test_dkcell("test_dkcell")
    dk_to_kcell = test_dk_to_kcell("test_bcell")

    assert isinstance(k_to_dkcell, kf.DKCell)
    assert isinstance(kcell, kf.KCell)
    assert isinstance(cell, KCellSubclass)
    assert isinstance(dkcell, kf.DKCell)
    assert isinstance(dk_to_kcell, kf.DKCell)

    with pytest.raises(ValueError):

        @kcl.cell
        def test_no_output_type():  # type: ignore[no-untyped-def]  # noqa: ANN202
            return kf.KCell()

        test_no_output_type()


if __name__ == "__main__":
    pytest.main(["-s", __file__])
