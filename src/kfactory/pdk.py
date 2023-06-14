"""PDK stores layers, enclosures, cell functions ..."""

from __future__ import annotations

import pathlib
import warnings
from collections.abc import Callable, Iterable
from inspect import getmembers, signature
from pathlib import Path
from types import ModuleType
from typing import Any

from pydantic import BaseModel, Field, validator
from pydantic_settings import BaseSettings

from . import kcell
from .conf import logger

# from .technology import LayerStack
from .typings import CellFactory, CellSpec, PathType
from .utils.enclosure import KCellEnclosure, LayerEnclosure

cell_settings = ["function", "cell", "settings"]
enclosure_settings = ["function", "enclosure", "settings"]

constants = {
    "fiber_array_spacing": 127.0,
    "fiber_spacing": 50.0,
    "fiber_input_to_output_spacing": 200.0,
    "metal_spacing": 10.0,
}

MaterialSpec = str | float | tuple[float, float] | Callable[[str], float]


def get_cells(
    modules: Iterable[ModuleType], verbose: bool = False
) -> dict[str, CellFactory]:
    """Returns PCells (component functions) from a module or list of modules.

    Args:
        modules: module or iterable of modules.
        verbose: prints in case any errors occur.
    """
    cells = {}
    for module in modules:
        for t in getmembers(module):
            if callable(t[1]) and t[0] != "partial":
                try:
                    r = signature(t[1]).return_annotation
                    if r == kcell.KCell or (
                        isinstance(r, str) and r.endswith("kcell.KCell")
                    ):
                        cells[t[0]] = t[1]
                except ValueError:
                    if verbose:
                        print(f"error in {t[0]}")
    return cells


class LayerEnclosureModel(BaseModel):
    layer_map: dict[str, LayerEnclosure] = Field(default={})

    def __getitem__(self, __key: str) -> LayerEnclosure:
        return self.layer_map[__key]

    def __getattr__(self, __key: str) -> LayerEnclosure:
        return self.layer_map[__key]


class CellModel(BaseModel):
    cell_map: dict[str, kcell.KCell] = Field(default={})

    def __getitem__(self, __key: str) -> kcell.KCell:
        return self.cell_map[__key]

    def __getattr__(self, __key: str) -> kcell.KCell:
        return self.cell_map[__key]

    class Config:
        arbitrary_types_allowed = True


class CellFactoryModel(BaseModel):
    cellfactory_map: dict[str, CellFactory] = Field(default={})

    def __getitem__(self, __key: str) -> CellFactory:
        return self.cellfactory_map[__key]

    def __getattr__(self, __key: str) -> CellFactory:
        return self.cellfactory_map[__key]

    class Config:
        arbitrary_types_allowed = True


class Constants(BaseSettings):
    pass


class Pdk(BaseModel):
    """Store layers, enclosures, cell functions, simulation_settings ...

    only one Pdk can be active at a given time.

    Attributes:
        name: PDK name.
        enclosures: dict of enclosures factories.
        cells: dict of str mapping to KCells.
        cell_factories: dict of str mapping to cell factories.
        base_pdk: a pdk to copy from and extend.
        default_decorator: decorate all cells, if not otherwise defined on the cell.
        layers: maps name to gdslayer/datatype.
            Must be of type LayerEnum.
        layer_stack: maps name to layer numbers, thickness, zmin, sidewall_angle.
            if can also contain material properties
            (refractive index, nonlinear coefficient, sheet resistance ...).
        sparameters_path: to store Sparameters simulations.
        interconnect_cml_path: path to interconnect CML (optional).
        grid_size: in um. Defaults to 1nm.
        constants: dict of constants for the PDK.

    """

    name: str | None = None
    layer_enclosures: LayerEnclosureModel
    enclosure: KCellEnclosure

    cell_factories: CellFactoryModel
    cells: CellModel
    layers: kcell.LayerEnum
    sparameters_path: PathType | None
    interconnect_cml_path: PathType | None
    constants: Constants = Field(default_factory=Constants)

    class Config:
        """Configuration."""

        arbitrary_types_allowed = True
        extra = "allow"
        # fields = {
        #     "enclosures": {"exclude": True},
        #     "cells": {"exclude": True},
        #     "default_decorator": {"exclude": True},
        # }

    def __init__(
        self,
        name: str | None = None,
        layer_enclosures: LayerEnclosureModel = LayerEnclosureModel(),
        enclosure: KCellEnclosure | None = None,
        cell_factories: CellFactoryModel = CellFactoryModel(),
        cells: CellModel = CellModel(),
        layers: kcell.LayerEnum | None = None,
        sparameters_path: PathType | None = None,
        interconnect_cml_path: PathType | None = None,
        constants: type[Constants] | None = None,
        base_pdk: Pdk | None = None,
    ) -> None:
        if base_pdk:
            name = name or base_pdk.name
            lm = base_pdk.layer_enclosures.layer_map.copy()
            lm.update(layer_enclosures.layer_map)
            layer_enclosures = LayerEnclosureModel(layer_map=lm)
            enclosure = enclosure or base_pdk.enclosure or KCellEnclosure(enclosures=[])
            cfm = base_pdk.cell_factories.cellfactory_map.copy()
            cfm.update(cell_factories)
            cell_factories = CellFactoryModel(cellfactory_map=cfm)
            cm = base_pdk.cells.cell_map.copy()
            cm.update(cells.cell_map)
            cells = CellModel(cell_map=cm)
            layers = (
                layers
                or base_pdk.layers
                or kcell.LayerEnum("LAYER", {})  # type: ignore[arg-type]
            )
            sparameters_path = sparameters_path or base_pdk.sparameters_path
            interconnect_cml_path = (
                interconnect_cml_path or base_pdk.interconnect_cml_path
            )
            _constants = constants() if constants else base_pdk.constants.copy()
        else:
            name = name
            layer_enclosures = layer_enclosures
            enclosure = enclosure or KCellEnclosure(enclosures=[])
            cell_factories = cell_factories
            layers = layers or kcell.LayerEnum("LAYER", {})  # type: ignore[arg-type]
            sparameters_path = sparameters_path
            interconnect_cml_path = interconnect_cml_path
            _constants = constants() if constants else Constants()

        super().__init__(
            name=name,
            layer_enclosures=layer_enclosures,
            cell_factories=cell_factories,
            layers=layers,
            constants=_constants,
        )
