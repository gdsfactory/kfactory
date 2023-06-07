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
            self.name = name or base_pdk.name
            lm = base_pdk.layer_enclosures.layer_map.copy()
            lm.update(layer_enclosures.layer_map)
            self.layer_enclosures = LayerEnclosureModel(layer_map=lm)
            self.enclosure = (
                enclosure or base_pdk.enclosure or KCellEnclosure(enclosures=[])
            )
            cfm = base_pdk.cell_factories.cellfactory_map.copy()
            cfm.update(cell_factories)
            self.cell_factories = CellFactoryModel(cellfactory_map=cfm)
            cm = base_pdk.cells.cell_map.copy()
            cm.update(cells.cell_map)
            self.cells = CellModel(cell_map=cm)
            self.layers = (
                layers
                or base_pdk.layers
                or kcell.LayerEnum("LAYER", {})  # type: ignore[arg-type]
            )
            self.sparameters_path = sparameters_path or base_pdk.sparameters_path
            self.interconnect_cml_path = (
                interconnect_cml_path or base_pdk.interconnect_cml_path
            )
            self.constants = constants() if constants else base_pdk.constants.copy()
        else:
            self.name = name
            self.layer_enclosures = layer_enclosures
            self.enclosure = enclosure or KCellEnclosure(enclosures=[])
            self.cell_factories = cell_factories
            self.layers = layers or kcell.LayerEnum(
                "LAYER", {}  # type: ignore[arg-type]
            )
            self.sparameters_path = sparameters_path
            self.interconnect_cml_path = interconnect_cml_path
            self.constants = constants() if constants else Constants()


# class Pdk(BaseModel):
#     """Store layers, enclosures, cell functions, simulation_settings ...

#     only one Pdk can be active at a given time.

#     Attributes:
#         name: PDK name.
#         enclosures: dict of enclosures factories.
#         cells: dict of str mapping to KCells.
#         cell_factories: dict of str mapping to cell factories.
#         base_pdk: a pdk to copy from and extend.
#         default_decorator: decorate all cells, if not otherwise defined on the cell.
#         layers: maps name to gdslayer/datatype.
#             Must be of type LayerEnum.
#         layer_stack: maps name to layer numbers, thickness, zmin, sidewall_angle.
#             if can also contain material properties
#             (refractive index, nonlinear coefficient, sheet resistance ...).
#         sparameters_path: to store Sparameters simulations.
#         interconnect_cml_path: path to interconnect CML (optional).
#         grid_size: in um. Defaults to 1nm.
#         constants: dict of constants for the PDK.

#     """

#     name: str
#     layer_enclosures: dict[str, LayerEnclosure] = Field(default_factory=dict)
#     enclosure: KCellEnclosure = Field(default=KCellEnclosure(enclosures=[]))

#     cell_factories: dict[str, CellFactory] = Field(default_factory=dict)
#     cells: dict[str, kcell.KCell] = Field(default_factory=dict)
#     base_pdk: Pdk | None = None
#     default_decorator: Callable[[kcell.KCell], None] | None = None
#     layers: type[kcell.LayerEnum]
#     layer_stack: LayerStack | None = None
#     # layer_views: Optional[LayerViews] = None
#     layer_transitions: dict[
#         kcell.LayerEnum | tuple[kcell.LayerEnum, kcell.LayerEnum], CellSpec
#     ] = Field(default_factory=dict)
#     sparameters_path: PathType | None = None
#     # modes_path: Optional[Path] = PATH.modes
#     interconnect_cml_path: PathType | None = None
#     constants: dict[str, Any] = constants

#     class Config:
#         """Configuration."""

#         arbitrary_types_allowed = True
#         extra = "allow"
#         fields = {
#             "enclosures": {"exclude": True},
#             "cells": {"exclude": True},
#             "default_decorator": {"exclude": True},
#         }

#     class PdkCollection(dict):
#         def __setitem__(self, __key: str, __val: Any) -> None:
#             super().__setitem__(__key, __val)
#             self.__setattr__(__key, __val)

#         def update(self, m: dict[str, Any]):
#             super().update(m)
#             for key, val in m.items():
#                 self.__setattr__(key, val)

#     def __init__(self, **data: Any):
#         """Add LayerLevels automatically for subclassed LayerStacks."""
#         super().__init__(**data)
#         self.kcl = kcell.kcl

#     @property
#     def grid_size(self) -> float:
#         return self.kcl.dbu

#     @grid_size.setter
#     def grid_size(self, value: float) -> None:
#         self.kcl.dbu = value

#     @validator("sparameters_path")
#     def is_pathlib_path(cls, path: str | Path) -> Path:
#         return pathlib.Path(path)

#     def activate(self) -> None:
#         """Set current pdk to as the active pdk."""
#         logger.info(f"{self.name!r} PDK is now active")

#         cell = self.PdkCollection()
#         cell.update(self.cells)
#         self.cells = cell

#         cell_factories = self.PdkCollection()
#         cell_factories.update(self.cell_factories)
#         self.cell_factories = cell_factories

#         if self.base_pdk:
#             enclosures = self.base_pdk.layer_enclosures
#             enclosures.update(self.layer_enclosures)
#             self.layer_enclosures = enclosures

#             cells = self.base_pdk.cells
#             cells.update(self.cells)
#             self.cells.update(cells)

#             cell_factories = self.base_pdk.cell_factories
#             cell_factories.update(self.cell_factories)
#             self.cell_factories = cell_factories
#             # layers = self.base_pdk.layers
#             # TODO dynamic creation
#             # class LAYER(BASELAYER):
#             #     b = (a,b)

#             if not self.default_decorator:
#                 self.default_decorator = self.base_pdk.default_decorator
#         self.kcl.pdk = self

#     def register_cells(self, **kwargs: Callable[..., kcell.KCell]) -> None:
#         """Register cell factories."""
#         for name, cell in kwargs.items():
#             if not callable(cell):
#                 raise ValueError(
#                     f"{cell} is not callable, make sure you register "
#                     "cells functions that return a KCell"
#                 )
#             if name in self.cells:
#                 warnings.warn(f"Overwriting cell {name!r}")

#             self.cells[name] = cell

#     def register_enclosures(self, **kwargs: LayerEnclosure) -> None:
#         """Register enclosures factories."""
#         for name, enclosure in kwargs.items():
#             if name in self.layer_enclosures:
#                 warnings.warn(f"Overwriting enclosure {name!r}")
#             self.layer_enclosures[name] = enclosure

#     def remove_cell(self, name: str) -> None:
#         """Removes cell from a PDK."""
#         if name not in self.cells:
#             raise ValueError(f"{name!r} not in {list(self.cells.keys())}")
#         self.cells.pop(name)
#         logger.info(f"Removed cell {name!r}")

#     def get_cell(self, cell: CellSpec, **cell_kwargs: Any) -> kcell.KCell:
#         """Returns cell from a cell spec.

#         Args:
#          cell: A CellSpec to get from the Pdk.
#          cell_kwargs: settings for the cell.
#         """
#         return self._get_cell(cell=cell, cells=self.cells, **cell_kwargs)

#     def _get_cell(
#         self,
#         cell: CellSpec,
#         cells: dict[str, Callable[..., kcell.KCell]],
#         **kwargs: Any,
#     ) -> kcell.KCell:
#         """Returns cell from a cell spec."""
#         # cell_names = cells.keys()

#         if isinstance(cell, kcell.KCell):
#             if kwargs:
#                 raise ValueError(f"Cannot apply kwargs {kwargs} to {cell.name!r}")
#             return cell
#         elif callable(cell):
#             return cell(**kwargs)
#         elif isinstance(cell, str):
#             try:
#                 cell = cells[cell]
#             except KeyError:
#                 cells_ = list(cells.keys())
#                 raise ValueError(f"{cell!r} not in PDK {self.name!r} cells: {cells_} ")
#             return cell(**kwargs)
#         else:
#             raise ValueError(
#                 "get_cell expects a CellSpec (KCell, CellFactory, "
#                 f"string or dict), got {type(cell)}"
#             )

#     def get_enclosure(self, enclosure: str) -> LayerEnclosure:
#         """Returns enclosure from a enclosure spec."""
#         return self.layer_enclosures[enclosure]

#     def get_layer(self, layer: Iterable[int] | int | str) -> kcell.LayerEnum:
#         """Returns layer from a layer spec."""
#         if isinstance(layer, int):
#             return self.layers(layer)  # type: ignore[call-arg]
#         elif isinstance(layer, str):
#             return self.layers[layer]
#         else:
#             layer = tuple(layer)
#             if len(layer) > 2:
#                 raise ValueError(
#                     "layer can only contain 2 elements like (layer, datatype)."
#                 )
#             layer_idx = self.kcl.layer(*layer)
#             return self.layers(layer_idx)  # type: ignore[call-arg]
