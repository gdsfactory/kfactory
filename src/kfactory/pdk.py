"""PDK stores layers, enclosures, cell functions ..."""

from __future__ import annotations

import pathlib
import warnings
from enum import Enum
from functools import partial
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

from omegaconf import DictConfig
from pydantic import BaseModel, Field, validator

import kfactory as kf
from kfactory.conf import logger
from kfactory.kcell import KCell, LayerEnum
from kfactory.technology import LayerLevel, LayerStack
from kfactory.typings import CellFactory, CellSpec
from kfactory.utils.enclosure import Enclosure

nm = 1e-3
cell_settings = ["function", "cell", "settings"]
enclosure_settings = ["function", "enclosure", "settings"]
layers_required = ["DEVREC", "PORT", "PORTE"]

constants = {
    "fiber_array_spacing": 127.0,
    "fiber_spacing": 50.0,
    "fiber_input_to_output_spacing": 200.0,
    "metal_spacing": 10.0,
}

MaterialSpec = str | float | tuple[float, float] | Callable[[str], float]


class Pdk(BaseModel):
    """Store layers, enclosures, cell functions, simulation_settings ...

    only one Pdk can be active at a given time.

    Parameters:
        name: PDK name.
        enclosures: dict of enclosures factories.
        cells: dict of parametric cells that return Cells.
        symbols: dict of symbols names to functions.
        default_symbol_factory:
        base_pdk: a pdk to copy from and extend.
        default_decorator: decorate all cells, if not otherwise defined on the cell.
        layers: maps name to gdslayer/datatype.
            For example dict(si=(1, 0), sin=(34, 0)).
        layer_stack: maps name to layer numbers, thickness, zmin, sidewall_angle.
            if can also contain material properties
            (refractive index, nonlinear coefficient, sheet resistance ...).
        sparameters_path: to store Sparameters simulations.
        modes_path: to store Sparameters simulations.
        interconnect_cml_path: path to interconnect CML (optional).
        grid_size: in um. Defaults to 1nm.
        warn_off_grid_ports: raises warning when extruding paths with offgrid ports.
            For example, if you try to create a waveguide with 1.5nm length.
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
    grid_size: float = 0.001
    warn_off_grid_ports: bool = False
    constants: dict[str, Any] = constants

    class Config:
        """Configuration."""

        arbitrary_types_allowed = True
        extra = "forbid"
        fields = {
            "enclosures": {"exclude": True},
            "cells": {"exclude": True},
            "default_decorator": {"exclude": True},
        }

    @validator("sparameters_path")
    def is_pathlib_path(cls, path: str | Path) -> Path:
        return pathlib.Path(path)

    def validate_layers(self) -> None:
        for layer in layers_required:
            if layer not in self.layers:
                raise ValueError(
                    f"{layer!r} not in Pdk.layers {list(self.layers.keys())}"
                )

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

            layers = self.base_pdk.layers
            layers.update(self.layers)
            self.layers.update(layers)

            if not self.default_decorator:
                self.default_decorator = self.base_pdk.default_decorator
        self.validate_layers()
        _set_active_pdk(self)

    def register_cells(self, **kwargs: Any) -> None:
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

    def register_enclosures(self, **kwargs: Any) -> None:
        """Register enclosures factories."""
        for name, enclosure in kwargs.items():
            if not callable(enclosure):
                raise ValueError(
                    f"{enclosure} is not callable, make sure you register "
                    "enclosure functions that return a CrossSection"
                )
            if name in self.enclosures:
                warnings.warn(f"Overwriting enclosure {name!r}")
            self.enclosures[name] = enclosure

    def register_cells_yaml(
        self,
        dirpath: Path | None = None,
        update: bool = False,
        **kwargs: Any,
    ) -> None:
        """Load *.pic.yml YAML files and register them as cells.

        Args:
            dirpath: directory to recursive search for YAML cells.
            update: does not raise ValueError if cell already registered.

        Keyword Args:
            cell_name: cell function. To update cells dict.

        """

        message = "Updated" if update else "Registered"

        if dirpath:
            dirpath = pathlib.Path(dirpath)

            if not dirpath.is_dir():
                raise ValueError(f"{dirpath!r} needs to be a directory.")

            for filepath in dirpath.glob("*/**/*.pic.yml"):
                name = filepath.stem.split(".")[0]
                if not update and name in self.cells:
                    raise ValueError(
                        f"ERROR: Cell name {name!r} from {filepath} already registered."
                    )
                kf.placer.cells_from_yaml(filepath)
                logger.info(f"{message} cell {name!r}")

        for k, v in kwargs.items():
            if not update and k in self.cells:
                raise ValueError(f"ERROR: Cell name {k!r} already registered.")
            self.cells[k] = v
            logger.info(f"{message} cell {k!r}")

    def remove_cell(self, name: str) -> None:
        """Removes cell from a PDK."""
        if name not in self.cells:
            raise ValueError(f"{name!r} not in {list(self.cells.keys())}")
        self.cells.pop(name)
        logger.info(f"Removed cell {name!r}")

    def get_cell(self, cell: CellSpec, **kwargs: Any) -> KCell:
        """Returns cell from a cell spec."""
        return self._get_cell(cell=cell, cells=self.cells, **kwargs)

    def get_symbol(self, cell: CellSpec, **kwargs: Any) -> KCell:
        """Returns a cell's symbol from a cell spec."""
        # this is a pretty rough first implementation
        try:
            return self._get_cell(cell=cell, cells=self.cells, **kwargs)
        except ValueError:
            cell = self.get_cell(cell, **kwargs)
            return cell

    def _get_cell(
        self,
        cell: CellSpec,
        cells: dict[str, Callable[..., KCell]],
        **kwargs: Any,
    ) -> KCell:
        """Returns cell from a cell spec."""
        cell_names = set(cells.keys())

        if isinstance(cell, KCell):
            if kwargs:
                raise ValueError(f"Cannot apply kwargs {kwargs} to {cell.name!r}")
            return cell
        elif callable(cell):
            return cell(**kwargs)
        elif isinstance(cell, str):
            if cell not in cell_names:
                cells_ = list(cells.keys())
                raise ValueError(f"{cell!r} not in PDK {self.name!r} cells: {cells_} ")
            cell = cells[cell] if cell in cells else cells[cell]
            return cell(**kwargs)
        elif isinstance(cell, (dict, DictConfig)):
            for key in cell.keys():
                if key not in cell_settings:
                    raise ValueError(f"Invalid setting {key!r} not in {cell_settings}")
            settings = dict(cell.get("settings", {}))
            settings.update(**kwargs)

            cell_name = cell.get("cell", None)
            cell_name = cell_name or cell.get("function")
            if not isinstance(cell_name, str) or cell_name not in cell_names:
                cells_ = list(cells.keys())
                raise ValueError(
                    f"{cell_name!r} from PDK {self.name!r} not in cells: {cells_} "
                )
            cell = cells[cell_name] if cell_name in cells else cells[cell_name]
            cell = cell(**settings)
            return cell
        else:
            raise ValueError(
                "get_cell expects a CellSpec (KCell, CellFactory, "
                f"string or dict), got {type(cell)}"
            )

    def get_enclosure(self, enclosure: Enclosure, **kwargs: Any) -> Enclosure:
        """Returns enclosure from a enclosure spec."""
        if isinstance(enclosure, Enclosure):
            return enclosure.copy(**kwargs)
        elif callable(enclosure):
            return enclosure(**kwargs)
        elif isinstance(enclosure, str):
            if enclosure not in self.enclosures:
                enclosures = list(self.enclosures.keys())
                raise ValueError(f"{enclosure!r} not in {enclosures}")
            enclosure_factory = self.enclosures[enclosure]
            return enclosure_factory(**kwargs)
        elif isinstance(enclosure, (dict, DictConfig)):
            for key in enclosure.keys():
                if key not in enclosure_settings:
                    raise ValueError(
                        f"Invalid setting {key!r} not in {enclosure_settings}"
                    )
            enclosure_factory_name = enclosure.get("enclosure", None)
            enclosure_factory_name = enclosure_factory_name or enclosure.get("function")
            if (
                not isinstance(enclosure_factory_name, str)
                or enclosure_factory_name not in self.enclosures
            ):
                enclosures = list(self.enclosures.keys())
                raise ValueError(f"{enclosure_factory_name!r} not in {enclosures}")
            enclosure_factory = self.enclosures[enclosure_factory_name]
            settings = dict(enclosure.get("settings", {}))
            settings.update(**kwargs)

            return enclosure_factory(**settings)
        else:
            raise ValueError(
                "get_enclosure expects a CrossSectionSpec (CrossSection, "
                f"Enclosure, string or dict), got {type(enclosure)}"
            )

    def get_layer(
        self, layer: tuple[int, int] | list[int] | int | str
    ) -> tuple[int, int] | list[int] | None:
        """Returns layer from a layer spec."""
        if isinstance(layer, (tuple, list)):
            if len(layer) != 2:
                raise ValueError(f"{layer!r} needs two integer numbers.")
            return layer
        elif isinstance(layer, int):
            return (layer, 0)
        elif layer is None:
            return
        else:
            raise ValueError(
                f"{layer!r} needs to be a LayerSpec (string, int or Layer)"
            )

    # def get_layer_views(self) -> LayerViews:
    #     if self.layer_views is None:
    #         raise ValueError(f"layer_views for Pdk {self.name!r} is None")
    #     return self.layer_views

    def get_layer_stack(self) -> LayerStack:
        if self.layer_stack is None:
            raise ValueError(f"layer_stack for Pdk {self.name!r} is None")
        return self.layer_stack

    def get_constant(self, key: str) -> Any:
        if not isinstance(key, str):
            return key
        if key not in self.constants:
            constants = list(self.constants.keys())
            raise ValueError(f"{key!r} not in {constants}")
        return self.constants[key]


_ACTIVE_PDK = None


def get_cell(cell: CellSpec, **kwargs: Any) -> KCell:
    return _ACTIVE_PDK.get_cell(cell, **kwargs)


def get_enclosure(enclosure: Enclosure, **kwargs: Any) -> Enclosure:
    return _ACTIVE_PDK.get_enclosure(enclosure, **kwargs)


def get_layer(layer: LayerEnum) -> tuple[int, int] | list[int] | Any:
    return _ACTIVE_PDK.get_layer(layer)


# def get_layer_views() -> LayerViews:
#     return _ACTIVE_PDK.get_layer_views()


def get_active_pdk() -> Pdk:
    return _ACTIVE_PDK


def get_grid_size() -> float:
    return _ACTIVE_PDK.grid_size


def get_constant(constant_name: Any) -> Any:
    """If constant_name is a string returns a the value from the dict."""
    return _ACTIVE_PDK.get_constant(constant_name)


def get_sparameters_path() -> pathlib.Path | str:
    if _ACTIVE_PDK.sparameters_path is None:
        raise ValueError(f"{_ACTIVE_PDK.name!r} has no sparameters_path")
    return _ACTIVE_PDK.sparameters_path


def get_interconnect_cml_path() -> pathlib.Path:
    if _ACTIVE_PDK.interconnect_cml_path is None:
        raise ValueError(f"{_ACTIVE_PDK.name!r} has no interconnect_cml_path")
    return _ACTIVE_PDK.interconnect_cml_path


def _set_active_pdk(pdk: Pdk) -> None:
    global _ACTIVE_PDK
    old_pdk = _ACTIVE_PDK
    _ACTIVE_PDK = pdk


if __name__ == "__main__":
    from kfactory import LayerEnum

    class LAYER(LayerEnum):
        """Generic layermap based on book.

        Lukas Chrostowski, Michael Hochberg, "Silicon Photonics Design",
        Cambridge University Press 2015, page 353
        You will need to create a new LayerMap with your specific foundry layers.
        """

        WG = (1, 0)
        WGCLAD = (111, 0)
        SLAB150 = (2, 0)

    p = Pdk(
        name="demo",
        # cells=pcells,
        # enclosures=[],
        layers=LAYER,
        sparameters_path="/home",
    )
    print(p.layers)
