"""PDK stores layers, enclosures, cell functions ..."""

from __future__ import annotations

import pathlib
import warnings
from collections.abc import Callable, Iterable
from inspect import getmembers, signature
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, validator

from kfactory.conf import logger
from kfactory.kcell import KCell, KCLayout, LayerEnum, kcl
from kfactory.technology import LayerStack
from kfactory.typings import CellFactory, CellSpec
from kfactory.utils.enclosure import Enclosure

nm = 1e-3
cell_settings = ["function", "cell", "settings"]
enclosure_settings = ["function", "enclosure", "settings"]

constants = {
    "fiber_array_spacing": 127.0,
    "fiber_spacing": 50.0,
    "fiber_input_to_output_spacing": 200.0,
    "metal_spacing": 10.0,
}

MaterialSpec = str | float | tuple[float, float] | Callable[[str], float]


def get_cells(modules, verbose: bool = False) -> dict[str, CellFactory]:
    """Returns PCells (component functions) from a module or list of modules.

    Args:
        modules: module or iterable of modules.
        verbose: prints in case any errors occur.

    """
    modules = modules if isinstance(modules, Iterable) else [modules]

    cells = {}
    for module in modules:
        for t in getmembers(module):
            if callable(t[1]) and t[0] != "partial":
                try:
                    r = signature(t[1]).return_annotation
                    if r == KCell or (isinstance(r, str) and r.endswith("KCell")):
                        cells[t[0]] = t[1]
                except ValueError:
                    if verbose:
                        print(f"error in {t[0]}")
    return cells


class Pdk(BaseModel):
    """Store layers, enclosures, cell functions, simulation_settings ...

    only one Pdk can be active at a given time.

    Attributes:
        name: PDK name.
        enclosures: dict of enclosures factories.
        cells: dict of parametric cells that return Cells.
        default_symbol_factory:
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

    name: str
    enclosures: dict[str, Enclosure] = Field(default_factory=dict)
    cells: dict[str, CellFactory] = Field(default_factory=dict)
    base_pdk: Pdk | None = None
    default_decorator: Callable[[KCell], None] | None = None
    layers: type[LayerEnum]
    layer_stack: LayerStack | None = None
    # layer_views: Optional[LayerViews] = None
    layer_transitions: dict[LayerEnum | tuple[LayerEnum, LayerEnum], CellSpec] = Field(
        default_factory=dict
    )
    sparameters_path: Path | str | None = None
    # modes_path: Optional[Path] = PATH.modes
    interconnect_cml_path: Path | None = None
    constants: dict[str, Any] = constants

    class Config:
        """Configuration."""

        arbitrary_types_allowed = True
        extra = "allow"
        fields = {
            "enclosures": {"exclude": True},
            "cells": {"exclude": True},
            "default_decorator": {"exclude": True},
        }

    def __init__(self, **data: Any):
        """Add LayerLevels automatically for subclassed LayerStacks."""
        super().__init__(**data)
        self.kcl = kcl

    @property
    def grid_size(self) -> float:
        return self.kcl.dbu

    @grid_size.setter
    def grid_size(self, value: float) -> None:
        self.kcl.dbu = value

    @validator("sparameters_path")
    def is_pathlib_path(cls, path: str | Path) -> Path:
        return pathlib.Path(path)

    def activate(self) -> None:
        """Set current pdk to as the active pdk."""
        logger.info(f"{self.name!r} PDK is now active")

        if self.base_pdk:
            enclosures = self.base_pdk.enclosures
            enclosures.update(self.enclosures)
            self.enclosures = enclosures

            cells = self.base_pdk.cells
            cells.update(self.cells)
            self.cells.update(cells)

            # layers = self.base_pdk.layers
            # TODO dynamic creation
            # class LAYER(BASELAYER):
            #     b = (a,b)

            if not self.default_decorator:
                self.default_decorator = self.base_pdk.default_decorator
        self.kcl.pdk = self

    def register_cells(self, **kwargs: Callable[KCell]) -> None:
        """Register cell factories."""
        for name, cell in kwargs.items():
            if not callable(cell):
                raise ValueError(
                    f"{cell} is not callable, make sure you register "
                    "cells functions that return a KCell"
                )
            if name in self.cells:
                warnings.warn(f"Overwriting cell {name!r}")

            self.cells[name] = cell

    def register_enclosures(self, **kwargs: Enclosure) -> None:
        """Register enclosures factories."""
        for name, enclosure in kwargs.items():
            if name in self.enclosures:
                warnings.warn(f"Overwriting enclosure {name!r}")
            self.enclosures[name] = enclosure

            # def register_cells_yaml(
            #     self,
            #     dirpath: Path | None = None,
            #     update: bool = False,
            #     **kwargs: Any,
            # ) -> None:
            #     """Load *.pic.yml YAML files and register them as cells.

            #     Args:
            #         dirpath: directory to recursive search for YAML cells.
            #         update: does not raise ValueError if cell already registered.

            #     Keyword Args:
            #         cell_name: cell function. To update cells dict.

            #     """

            #     message = "Updated" if update else "Registered"

            #     if dirpath:
            #         dirpath = pathlib.Path(dirpath)

            #         if not dirpath.is_dir():
            #             raise ValueError(f"{dirpath!r} needs to be a directory.")

            #         for filepath in dirpath.glob("*/**/*.pic.yml"):
            #             name = filepath.stem.split(".")[0]
            #             if not update and name in self.cells:
            #                 raise ValueError(
            #                     f"ERROR: Cell name {name!r} from {filepath} already registered."
            #                 )
            #             kf.placer.cells_from_yaml(filepath)
            #             logger.info(f"{message} cell {name!r}")

            #     for k, v in kwargs.items():

    #        if not update and k in self.cells:
    #            raise ValueError(f"ERROR: Cell name {k!r} already registered.")
    #        self.cells[k] = v
    #        logger.info(f"{message} cell {k!r}")

    def remove_cell(self, name: str) -> None:
        """Removes cell from a PDK."""
        if name not in self.cells:
            raise ValueError(f"{name!r} not in {list(self.cells.keys())}")
        self.cells.pop(name)
        logger.info(f"Removed cell {name!r}")

    def get_cell(self, cell: CellSpec, **cell_kwargs: Any) -> KCell:
        """Returns cell from a cell spec.

        Args:
         cell: A CellSpec to get from the Pdk.
         cell_kwargs: settings for the cell.
        """
        return self._get_cell(cell=cell, cells=self.cells, **cell_kwargs)

    def _get_cell(
        self,
        cell: CellSpec,
        cells: dict[str, Callable[..., KCell]],
        **kwargs: Any,
    ) -> KCell:
        """Returns cell from a cell spec."""
        # cell_names = cells.keys()

        if isinstance(cell, KCell):
            if kwargs:
                raise ValueError(f"Cannot apply kwargs {kwargs} to {cell.name!r}")
            return cell
        elif callable(cell):
            return cell(**kwargs)
        elif isinstance(cell, str):
            try:
                cell = cells[cell]
            except KeyError:
                cells_ = list(cells.keys())
                raise ValueError(f"{cell!r} not in PDK {self.name!r} cells: {cells_} ")
            return cell(**kwargs)
        # elif isinstance(cell, dict):
        #     for key in cell:
        #         if key not in cell_settings:
        #             raise ValueError(f"Invalid setting {key!r} not in {cell_settings}")
        #     settings = dict(cell.get("settings", {}))
        #     settings.update(**kwargs)

        #     cell_name = cell.get("cell", None)
        #     cell_name = cell_name or cell.get("function")
        #     if not isinstance(cell_name, str) or cell_name not in cell_names:
        #         cells_ = list(cells.keys())
        #         raise ValueError(
        #             f"{cell_name!r} from PDK {self.name!r} not in cells: {cells_} "
        #         )
        #     cell = cells[cell_name] if cell_name in cells else cells[cell_name]
        #     cell = cell(**settings)
        #     return cell
        else:
            raise ValueError(
                "get_cell expects a CellSpec (KCell, CellFactory, "
                f"string or dict), got {type(cell)}"
            )

    def get_enclosure(self, enclosure: str) -> Enclosure:
        """Returns enclosure from a enclosure spec."""
        return self.enclosures[enclosure]
        # try:
        #     enclosure_factory = self.enclosures[enclosure]
        # except KeyError:
        #     raise ValueError(f"{enclosure!r} not in {enclosures}")
        # return enclosure_factory(**kwargs)
        # elif isinstance(enclosure, (dict, DictConfig)):
        #     for key in enclosure.keys():
        #         if key not in enclosure_settings:
        #             raise ValueError(
        #                 f"Invalid setting {key!r} not in {enclosure_settings}"
        #             )
        #     enclosure_factory_name = enclosure.get("enclosure", None)
        #     enclosure_factory_name = enclosure_factory_name or enclosure.get("function")
        #     if (
        #         not isinstance(enclosure_factory_name, str)
        #         or enclosure_factory_name not in self.enclosures
        #     ):
        #         enclosures = list(self.enclosures.keys())
        #         raise ValueError(f"{enclosure_factory_name!r} not in {enclosures}")
        #     enclosure_factory = self.enclosures[enclosure_factory_name]
        #     settings = dict(enclosure.get("settings", {}))
        #     settings.update(**kwargs)

        #     return enclosure_factory(**settings)

    def get_layer(self, layer: Iterable[int] | int | str) -> LayerEnum:
        """Returns layer from a layer spec."""
        if isinstance(layer, int):
            return self.layers(layer)  # type: ignore[call-arg]
        elif isinstance(layer, str):
            return self.layers[layer]
        else:
            layer = tuple(layer)
            if len(layer) > 2:
                raise ValueError(
                    "layer can only contain 2 elements like (layer, datatype)."
                )
            layer_idx = self.kcl.layer(*layer)
            return self.layers(layer_idx)  # type: ignore[call-arg]

    # def get_layer_views(self) -> LayerViews:
    #     if self.layer_views is None:
    #         raise ValueError(f"layer_views for Pdk {self.name!r} is None")
    #     return self.layer_views


# _ACTIVE_PDK = None


# def get_cell(cell: CellSpec, **kwargs: Any) -> KCell:
#     return _ACTIVE_PDK.get_cell(cell, **kwargs)


# def get_enclosure(enclosure: Enclosure, **kwargs: Any) -> Enclosure:
#     return _ACTIVE_PDK.get_enclosure(enclosure, **kwargs)


# def get_layer(layer: LayerEnum) -> tuple[int, int] | list[int] | Any:
#     return _ACTIVE_PDK.get_layer(layer)


# # def get_layer_views() -> LayerViews:
# #     return _ACTIVE_PDK.get_layer_views()


# def get_active_pdk() -> Pdk:
#     return _ACTIVE_PDK


# def get_grid_size() -> float:
#     return _ACTIVE_PDK.grid_size


# def get_constant(constant_name: Any) -> Any:
#     """If constant_name is a string returns a the value from the dict."""
#     return _ACTIVE_PDK.get_constant(constant_name)


# def get_sparameters_path() -> pathlib.Path | str:
#     if _ACTIVE_PDK.sparameters_path is None:
#         raise ValueError(f"{_ACTIVE_PDK.name!r} has no sparameters_path")
#     return _ACTIVE_PDK.sparameters_path


# def get_interconnect_cml_path() -> pathlib.Path:
#     if _ACTIVE_PDK.interconnect_cml_path is None:
#         raise ValueError(f"{_ACTIVE_PDK.name!r} has no interconnect_cml_path")
#     return _ACTIVE_PDK.interconnect_cml_path


# def _set_active_pdk(pdk: Pdk) -> None:
#     global _ACTIVE_PDK
#     _ACTIVE_PDK = pdk
