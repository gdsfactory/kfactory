from collections.abc import Callable
from functools import partial
from typing import Any

import pytest

import kfactory as kf
from tests.conftest import Layers


class GeometryDifferenceError(ValueError):
    """Exception for Geometric differences."""


@pytest.fixture
def cell_params(wg_enc: kf.LayerEnclosure, layers: Layers) -> dict[str, Any]:
    """Returns cell name."""
    return {
        "bend_circular": {
            "width": 1,
            "radius": 10,
            "layer": layers.WG,
            "enclosure": wg_enc,
        },
        "bend_euler": {
            "width": 1,
            "radius": 10,
            "layer": layers.WG,
            "enclosure": wg_enc,
        },
        "bend_s_bezier": {
            "width": 1,
            "height": 10,
            "length": 100,
            "layer": layers.WG,
            "enclosure": wg_enc,
        },
        "bend_s_euler": {
            "width": 1,
            "radius": 30,
            "offset": 10,
            "layer": layers.WG,
            "enclosure": wg_enc,
        },
        "straight": {
            "width": 1000,
            "length": 100_000,
            "layer": layers.WG,
            "enclosure": wg_enc,
        },
        "taper": {
            "width1": 1000,
            "width2": 10_000,
            "length": 50_000,
            "layer": layers.WG,
            "enclosure": wg_enc,
        },
    }


@pytest.fixture
def virtual_cell_params(wg_enc: kf.LayerEnclosure, layers: Layers) -> dict[str, Any]:
    """Returns cell name."""
    return {
        "bend_euler": {
            "width": 1,
            "radius": 10,
            "layer": layers.WG,
            "enclosure": wg_enc,
            "angle": 30,
        },
        "virtual_bend_circular": {
            "width": 1,
            "radius": 10,
            "layer": layers.WG,
            "enclosure": wg_enc,
            "angle": 30,
        },
        "virtual_straight": {
            "width": 0.006,
            "length": 100.0052,
            "layer": layers.WG,
            "enclosure": wg_enc,
        },
    }


@pytest.mark.parametrize(
    "cell_name",
    sorted(set(kf.kcl.factories._by_name) - {"taper_cell"}),
)
def test_cells(
    cell_name: str,
    cell_params: dict[str, Any],
    gds_regression: Callable[[kf.ProtoTKCell[Any]], None],
) -> None:
    """Ensure cells have the same geometry as their golden references."""
    cell = kf.kcl.factories[cell_name](**cell_params.get(cell_name, {}))
    gds_regression(cell)


@pytest.mark.parametrize(
    "cell_name", sorted(set(kf.kcl.virtual_factories._by_name) - {"taper_cell"})
)
def test_virtual_cells(
    cell_name: str,
    virtual_cell_params: dict[str, Any],
    gds_regression: Callable[[kf.ProtoTKCell[Any]], None],
) -> None:
    """Ensure cells have the same geometry as their golden references."""
    cell = kf.KCell()
    vkcell = kf.kcl.virtual_factories[cell_name](
        **virtual_cell_params.get(cell_name, {})
    )
    assert vkcell.name is not None
    cell.name = vkcell.name
    kf.VInstance(vkcell).insert_into_flat(cell, levels=1)

    c = kf.kcl.kcell()
    c << cell

    gds_regression(c)
    c.delete()


def test_additional_info(
    kcl: kf.KCLayout,
    layers: Layers,
    wg_enc: kf.LayerEnclosure,
    gds_regression: Callable[[kf.ProtoTKCell[Any]], None],
) -> None:
    test_bend_euler = partial(
        kf.factories.euler.bend_euler_factory(
            kcl=kcl,
            additional_info={"creation_time": "2023-02-12Z23:00:00"},
            overwrite_existing=True,
        ),
        layer=layers.WG,
        radius=10,
    )

    bend = test_bend_euler(width=1)

    assert bend.locked is True
    assert bend.info.creation_time == "2023-02-12Z23:00:00"  # type: ignore[attr-defined, unused-ignore]

    gds_regression(bend)

    bend.delete()
