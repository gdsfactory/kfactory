import functools

import pytest

import kfactory as kf
from tests.conftest import Layers


def test_cell_decorator(kcl: kf.KCLayout, layers: Layers) -> None:
    count: int = 0

    def rectangle_post_process(cell: kf.kcell.TKCell) -> None:
        assert cell.name == kf.serialization.clean_name(
            f"rectangle_W{cell.settings['width']}_H{cell.settings['height']}_LWG"
        )
        nonlocal count
        count += 1

    @kcl.cell(post_process=[rectangle_post_process])  # type: ignore[type-var]
    def rectangle(width: float, height: float, layer: kf.kdb.LayerInfo) -> kf.DKCell:
        c = kcl.dkcell()
        c.shapes(layer).insert(kf.kdb.DBox(0, 0, width, height))
        return c

    rectangle_cell = rectangle(10, 10, layers.WG)
    rectangle_cell2 = rectangle(10, 10, layers.WG)
    rectangle_cell3 = rectangle(10.1, 10.1, layers.WG)

    assert rectangle_cell is rectangle_cell2
    assert rectangle_cell is not rectangle_cell3
    assert count == 2


def test_set_settings_functionality(kcl: kf.KCLayout) -> None:
    @kcl.cell(set_settings=True)
    def test_set_settings(
        name: str = "test_set_settings",
        width: float = 10.0,
        height: float = 5.0,
    ) -> kf.KCell:
        return kcl.kcell(name=name)

    cell_with_settings = test_set_settings()
    assert cell_with_settings.settings["width"] == 10.0
    assert cell_with_settings.settings["height"] == 5.0

    @kcl.cell(set_settings=False)
    def test_set_settings_no_settings(
        name: str = "test_set_settings_no",
        width: float = 10.0,
        height: float = 5.0,
    ) -> kf.KCell:
        return kcl.kcell(name=name)

    cell_without_settings = test_set_settings_no_settings()
    assert cell_without_settings.settings == kf.KCellSettings()

    test_set_settings_partial = functools.partial(
        test_set_settings, name="test_set_settings_partial"
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
        return kcl.kcell(name=name)

    with pytest.raises(TypeError):
        test_cell_with_empty_parameters(name="test_cell_with_empty_parameters")  # type: ignore[call-arg]


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
        kcl.cell(check_instances=kf.kcell.CheckInstances.RAISE)(
            test_cell_with_rotation
        )("test_rase")

    cell = kcl.cell(check_instances=kf.kcell.CheckInstances.FLATTEN)(
        test_cell_with_rotation
    )("test_flatten")

    assert len(cell.insts) == 0

    cell2 = kcl.cell(check_instances=kf.kcell.CheckInstances.VINSTANCES)(
        test_cell_with_rotation
    )("test_vinstances")

    assert cell2 is not cell
    assert len(cell2.vinsts) == 0
    assert len(cell2.insts) == 1

    kcl.cell(check_instances=kf.kcell.CheckInstances.IGNORE)(test_cell_with_rotation)(
        "test_ignore"
    )


def test_cell_decorator_types(kcl: kf.KCLayout) -> None:
    class KCellSubclass(kf.KCell):
        pass

    @kcl.cell(output_type=KCellSubclass)
    def test_cell(name: str) -> kf.KCell:
        return kcl.kcell(name=name)

    @kcl.cell(layout_cache=True, output_type=kf.KCell)
    def test_kcell(name: str) -> kf.KCell:
        return kcl.kcell(name=name)

    @kcl.cell(output_type=kf.DKCell)
    def test_k_to_dkcell(name: str) -> kf.KCell:
        return kcl.kcell(name=name)

    @kcl.cell(output_type=kf.DKCell)
    def test_dkcell(name: str) -> kf.DKCell:
        return kcl.dkcell(name=name)

    @kcl.cell
    def test_dk_to_kcell(name: str) -> kf.DKCell:
        return kcl.dkcell(name=name)

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


def test_clear_kcells(kcl: kf.KCLayout, layers: Layers) -> None:
    c = kcl.kcell(name="c")
    straight = kf.factories.straight.straight_dbu_factory(kcl)(
        length=1000, width=1000, layer=layers.WG
    )
    c << straight
    kcl.clear_kcells()
    assert len(kcl.kcells) == 0
    assert straight.destroyed()
    assert c.destroyed()


def test_kclayout_rebuild(kcl: kf.KCLayout, layers: Layers) -> None:
    straight = kf.factories.straight.straight_dbu_factory(kcl)(
        length=1000, width=1000, layer=layers.WG
    )
    del kcl.tkcells[straight.cell_index()]
    assert len(kcl.tkcells) == 0
    assert len(list(kcl.layout.each_cell())) == 1

    kcl.rebuild()
    assert len(kcl.kcells) == 1
    assert len(list(kcl.layout.each_cell())) == 1


def test_kclayout_assign(kcl: kf.KCLayout, layers: Layers) -> None:
    kcl2 = kf.KCLayout(name="kcl2")
    kcl2.infos = layers
    kf.factories.straight.straight_dbu_factory(kcl2)(
        length=1000, width=1000, layer=layers.WG
    )
    kcl.assign(kcl2.layout)
    assert len(kcl2.kcells) == 1
    assert len(list(kcl2.layout.each_cell())) == 1


def test_get_component(layers: Layers) -> None:
    # normal functions
    kf.kcl.get_component(
        "straight", width=1000, length=10_000, layer=kf.kdb.LayerInfo(1, 0)
    ).delete()
    kf.kcl.get_component(
        kf.cells.straight.straight, width=1, length=10, layer=layers.WG
    ).delete()
    kf.kcl.get_component(
        kf.cells.straight.straight(width=1, length=10, layer=layers.WG)
    ).delete()
    kf.kcl.get_component(
        kf.cells.straight.straight(width=1, length=10, layer=layers.WG).cell_index()
    ).delete()

    # output_type functions
    kf.kcl.get_component(
        "straight",
        width=1000,
        length=10_000,
        layer=kf.kdb.LayerInfo(1, 0),
        output_type=kf.DKCell,
    ).delete()
    kf.kcl.get_component(
        {
            "component": "straight",
            "settings": {
                "width": 1000,
                "length": 10_000,
                "layer": kf.kdb.LayerInfo(1, 0),
            },
        },
        output_type=kf.DKCell,
    ).delete()
    kf.kcl.get_component(
        kf.cells.straight.straight,
        width=1,
        length=10,
        layer=layers.WG,
        output_type=kf.DKCell,
    ).delete()
    kf.kcl.get_component(
        kf.cells.straight.straight(width=1, length=10, layer=layers.WG),
        output_type=kf.DKCell,
    ).delete()
    kf.kcl.get_component(
        kf.cells.straight.straight(width=1, length=10, layer=layers.WG).cell_index(),
        output_type=kf.DKCell,
    ).delete()

    # raises errors
    with pytest.raises(ValueError):
        kf.kcl.get_component(
            kf.cells.straight.straight(width=1, length=10, layer=layers.WG),
            output_type=kf.DKCell,
            width=1,
            length=10,
            layer=layers.WG,
        )
    with pytest.raises(ValueError):
        kf.kcl.get_component(
            kf.cells.straight.straight(
                width=1, length=10, layer=layers.WG
            ).cell_index(),
            output_type=kf.DKCell,
            width=1,
            length=10,
            layer=layers.WG,
        )
    with pytest.raises(TypeError):
        kf.kcl.get_component(
            {"component": "straight"},
            output_type=kf.DKCell,
        )
