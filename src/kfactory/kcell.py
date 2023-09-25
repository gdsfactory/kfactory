"""Core module of kfactory.

Defines the [KCell][kfactory.kcell.KCell] providing klayout Cells with Ports
and other convenience functions.

[Instance][kfactory.kcell.Instance] are the kfactory instances used to also acquire
ports and other inf from instances.

"""
from __future__ import annotations

import functools
import importlib
import importlib.util
import inspect
import json
import socket
import types
from collections import UserDict
from collections.abc import Callable, Hashable, Iterable, Iterator
from enum import IntEnum, IntFlag, auto
from hashlib import sha3_512
from pathlib import Path
from tempfile import gettempdir
from typing import Any, Literal, TypeAlias, TypeVar, overload

import cachetools.func
import numpy as np
import ruamel.yaml
from aenum import Enum, constant  # type: ignore[import]
from pydantic import BaseModel, Field, computed_field, model_validator
from pydantic_settings import BaseSettings
from typing_extensions import ParamSpec

from . import kdb, lay, rdb
from .conf import config
from .enclosure import (
    KCellEnclosure,
    LayerEnclosure,
    LayerEnclosureCollection,
    LayerSection,
)
from .port import port_polygon, rename_clockwise

T = TypeVar("T")

KCellParams = ParamSpec("KCellParams")
AnyTrans = TypeVar(
    "AnyTrans", bound=kdb.Trans | kdb.DTrans | kdb.ICplxTrans | kdb.DCplxTrans
)
SerializableShape: TypeAlias = (
    kdb.Box
    | kdb.DBox
    | kdb.Edge
    | kdb.DEdge
    | kdb.EdgePair
    | kdb.DEdgePair
    | kdb.EdgePairs
    | kdb.Edges
    | lay.LayerProperties
    | kdb.Matrix2d
    | kdb.Matrix3d
    | kdb.Path
    | kdb.DPath
    | kdb.Point
    | kdb.DPoint
    | kdb.Polygon
    | kdb.DPolygon
    | kdb.SimplePolygon
    | kdb.DSimplePolygon
    | kdb.Region
    | kdb.Text
    | kdb.DText
    | kdb.Texts
    | kdb.Trans
    | kdb.DTrans
    | kdb.CplxTrans
    | kdb.ICplxTrans
    | kdb.DCplxTrans
    | kdb.VCplxTrans
    | kdb.Vector
    | kdb.DVector
)

kcl: KCLayout


class LayerEnum(int, Enum):  # type: ignore[misc]
    """Class for having the layers stored and a mapping int <-> layer,datatype.

    This Enum can also be treated as a tuple, i.e. it implements `__getitem__`
    and `__len__`.

    Attributes:
        layer: layer number
        datatype: layer datatype
    """

    layer: int
    datatype: int
    kcl: constant[KCLayout]

    def __new__(cls: LayerEnum, layer: int, datatype: int) -> LayerEnum:  # type: ignore
        """Create a new Enum.

        Because it needs to act like an integer an enum is created and expanded.

        Args:
            layer: Layer number of the layer.
            datatype: Datatype of the layer.
            kcl: Base Layout object to register the layer to.
        """
        value = cls.kcl.layer(layer, datatype)
        obj: int = int.__new__(cls, value)
        obj._value_ = value  # type: ignore[attr-defined]
        obj.layer = layer  # type: ignore[attr-defined]
        obj.datatype = datatype  # type: ignore[attr-defined]
        return obj  # type: ignore[return-value]

    def __getitem__(self, key: int) -> int:
        """Retrieve layer number[0] / datatype[1] of a layer."""
        if key == 0:
            return self.layer
        elif key == 1:
            return self.datatype

        else:
            raise ValueError(
                "LayerMap only has two values accessible like"
                " a list, layer == [0] and datatype == [1]"
            )

    def __len__(self) -> int:
        """A layer has length 2, layer number and datatype."""
        return 2

    def __iter__(self) -> Iterator[int]:
        """Allow for loops to iterate over the LayerEnum."""
        yield from [self.layer, self.datatype]

    def __str__(self) -> str:
        """Return the name of the LayerEnum."""
        return self.name  # type: ignore[no-any-return]


class KCellSettings(BaseModel, extra="allow", validate_assignment=True, frozen=True):
    @model_validator(mode="before")
    def restrict_types(
        cls, data: dict[str, Any]
    ) -> dict[str, int | float | SerializableShape | str]:
        for name, value in data.items():
            if not isinstance(value, str | int | float | SerializableShape):
                data[name] = str(value)
        return data

    def __getitem__(self, key: str) -> Any:
        return getattr(self, key)


class Info(BaseModel, extra="allow", validate_assignment=True):
    @model_validator(mode="before")
    def restrict_types(
        cls, data: dict[str, int | float | str]
    ) -> dict[str, int | float | str]:
        for name, value in data.items():
            assert isinstance(value, str | int | float), (
                "Values of the info dict only support int, float, or strings."
                f"{name}: {value}, {type(value)}"
            )

        return data

    def __getitem__(self, __key: str) -> Any:
        return getattr(self, __key)

    def __setitem__(self, __key: str, __val: str | int | float) -> None:
        setattr(self, __key, __val)


class PROPID(IntEnum):
    """Mapping for GDS properties."""

    NAME = 0


class LockedError(AttributeError):
    """Raised when a locked cell is being modified."""

    @config.logger.catch(reraise=True)
    def __init__(self, kcell: KCell):
        """Throw _locked error."""
        super().__init__(
            f"KCell {kcell.name} has been locked already."
            " Modification has been disabled. "
            "Modify the KCell in its autocell function or make a copy."
        )


class PortWidthMismatch(ValueError):
    """Error thrown when two ports don't have a matching `width`."""

    @config.logger.catch(reraise=True)
    def __init__(
        self,
        inst: Instance,
        other_inst: Instance | Port,
        p1: Port,
        p2: Port,
        *args: Any,
    ):
        """Throw error for the two ports `p1`/`p1`."""
        if isinstance(other_inst, Instance):
            super().__init__(
                f'Width mismatch between the ports {inst.cell.name}["{p1.name}"]'
                f'and {other_inst.cell.name}["{p2.name}"] ("{p1.width}"/"{p2.width}")',
                *args,
            )
        else:
            super().__init__(
                f'Width mismatch between the ports {inst.cell.name}["{p1.name}"]'
                f' and Port "{p2.name}" ("{p1.width}"/"{p2.width}")',
                *args,
            )


class PortLayerMismatch(ValueError):
    """Error thrown when two ports don't have a matching `layer`."""

    @config.logger.catch(reraise=True)
    def __init__(
        self,
        kcl: KCLayout,
        inst: Instance,
        other_inst: Instance | Port,
        p1: Port,
        p2: Port,
        *args: Any,
    ):
        """Throw error for the two ports `p1`/`p1`."""
        l1 = (
            f"{p1.layer.name}({p1.layer.__int__()})"
            if isinstance(p1.layer, LayerEnum)
            else str(kcl.layout.get_info(p1.layer))
        )
        l2 = (
            f"{p2.layer.name}({p2.layer.__int__()})"
            if isinstance(p2.layer, LayerEnum)
            else str(kcl.layout.get_info(p2.layer))
        )
        if isinstance(other_inst, Instance):
            super().__init__(
                f'Layer mismatch between the ports {inst.cell.name}["{p1.name}"]'
                f' and {other_inst.cell.name}["{p2.name}"] ("{l1}"/"{l2}")',
                *args,
            )
        else:
            super().__init__(
                f'Layer mismatch between the ports {inst.cell.name}["{p1.name}"]'
                f' and Port "{p2.name}" ("{l1}"/"{l2}")',
                *args,
            )


class PortTypeMismatch(ValueError):
    """Error thrown when two ports don't have a matching `port_type`."""

    @config.logger.catch(reraise=True)
    def __init__(
        self,
        inst: Instance,
        other_inst: Instance | Port,
        p1: Port,
        p2: Port,
        *args: Any,
    ):
        """Throw error for the two ports `p1`/`p1`."""
        if isinstance(other_inst, Instance):
            super().__init__(
                f'Type mismatch between the ports {inst.cell.name}["{p1.name}"]'
                f' and {other_inst.cell.name}["{p2.name}"]'
                f" ({p1.port_type}/{p2.port_type})",
                *args,
            )
        else:
            super().__init__(
                f'Type mismatch between the ports {inst.cell.name}["{p1.name}"]'
                f' and Port "{p2.name}" ({p1.port_type}/{p2.port_type})',
                *args,
            )


class FrozenError(AttributeError):
    """Raised if a KCell has been frozen and shouldn't be modified anymore."""

    pass


def default_save() -> kdb.SaveLayoutOptions:
    """Default options for saving GDS/OAS."""
    save = kdb.SaveLayoutOptions()
    save.gds2_write_cell_properties = True
    save.gds2_write_file_properties = True
    save.gds2_write_timestamps = False
    # save.write_context_info = False  # True

    return save


class PortCheck(IntFlag):
    opposite = auto()
    width = auto()
    layer = auto()
    port_type = auto()
    all_opposite = opposite + width + port_type + layer
    all_overlap = width + port_type + layer


@config.logger.catch(reraise=True)
def port_check(p1: Port, p2: Port, checks: PortCheck = PortCheck.all_opposite) -> None:
    if checks & PortCheck.opposite:
        assert (
            p1.trans == p2.trans * kdb.Trans.R180
            or p1.trans == p2.trans * kdb.Trans.M90
        ), ("Transformations of ports not matching for opposite check" f"{p1=} {p2=}")
    if (checks & PortCheck.opposite) == 0:
        assert (
            p1.trans == p2.trans or p1.trans == p2.trans * kdb.Trans.M0
        ), f"Transformations of ports not matching for overlapping check {p1=} {p2=}"
    if checks & PortCheck.width:
        assert p1.width == p2.width, f"Width mismatch for {p1=} {p2=}"
    if checks & PortCheck.layer:
        assert p1.layer == p2.layer, f"Layer mismatch for {p1=} {p2=}"
    if checks & PortCheck.port_type:
        assert p1.port_type == p2.port_type, f"Port type mismatch for {p1=} {p2=}"


# def get_cells(
#     modules: Iterable[ModuleType], verbose: bool = False
# ) -> dict[str, KCellFactory]:
#     """Returns KCells (KCell functions) from a module or list of modules.

#     Args:
#         modules: module or iterable of modules.
#         verbose: prints in case any errors occur.
#     """
#     cells = {}
#     for module in modules:
#         for t in inspect.getmembers(module):
#             if callable(t[1]) and t[0] != "partial":
#                 try:
#                     r = inspect.signature(t[1]).return_annotation
#                     if r == KCell or (isinstance(r, str) and r.endswith("KCell")):
#                         cells[t[0]] = KCellFactory(name=t[0], factory=t[1])
#                 except ValueError:
#                     if verbose:
#                         print(f"error in {t[0]}")
#     return cells


class LayerEnclosureModel(BaseModel):
    """PDK access model for LayerEnclsoures."""

    enclosure_map: dict[str, LayerEnclosure] = Field(default={})

    def __getitem__(self, __key: str) -> LayerEnclosure:
        """Retrieve element by string key."""
        return self.enclosure_map[__key]

    def __getattr__(self, __key: str) -> LayerEnclosure:
        """Retrieve attribute by key."""
        return self.enclosure_map[__key]


class KCell:
    """KLayout cell and change its class to KCell.

    A KCell is a dynamic proxy for kdb.Cell. It has all the
    attributes of the official KLayout class. Some attributes have been adjusted
    to return KCell specific sub classes. If the function is listed here in the
    docs, they have been adjusted for KFactory specifically. This object will
    transparently proxy to kdb.Cell. Meaning any attribute not directly
    defined in this class that are available from the KLayout counter part can
    still be accessed. The pure KLayout object can be accessed with
    `_kdb_cell`.

    Attributes:
        kcl: Library object that is the manager of the KLayout
        settings: A dictionary containing settings populated by the
            [cell][kfactory.kcell.cell] decorator.
        info: Dictionary for storing additional info if necessary. This is not
            passed to the GDS and therefore not reversible.
        _kdb_cell: Pure KLayout cell object.
        _locked: If set the cell shouldn't be modified anymore.
        ports: Manages the ports of the cell.
    """

    yaml_tag: str = "!KCell"
    _ports: Ports
    _settings: KCellSettings
    _info: Info
    d: UMKCell
    kcl: KCLayout
    boundary: kdb.DPolygon | None

    def __init__(
        self,
        name: str | None = None,
        kcl: KCLayout | None = None,
        kdb_cell: kdb.Cell | None = None,
        ports: Ports | None = None,
    ):
        """Constructor of KCell.

        Args:
            name: Name of the cell, if None will autogenerate name to
                "Unnamed_<cell_index>".
            kcl: KCLayout the cell should be attached to.
            kdb_cell: If not `None`, a KCell will be created from and existing
                KLayout Cell
            ports: Attach an existing [Ports][kfactory.kcell.Ports] object to the KCell,
                if `None` create an empty one.
        """
        if kcl is None:
            kcl = _get_default_kcl()
        self.kcl = kcl
        self.insts: Instances = Instances()
        self._settings: KCellSettings = KCellSettings()
        self.info: Info = Info()
        self._locked = False
        if name is None:
            _name = "Unnamed_!"
        else:
            _name = name
        self._kdb_cell = kdb_cell or kcl.create_cell(_name)
        if _name == "Unnamed_!":
            self._kdb_cell.name = f"Unnamed_{self.cell_index()}"
        self.kcl.register_cell(self, allow_reregister=True)
        self.ports: Ports = ports or Ports(self.kcl)
        self.complex = False

        if kdb_cell is not None:
            for inst in kdb_cell.each_inst():
                self.insts.append(Instance(self.kcl, inst))
        self.d = UMKCell(self)

        self.boundary = None

    def __getitem__(self, key: int | str | None) -> Port:
        """Returns port from instance."""
        return self.ports[key]

    @property
    def settings(self) -> KCellSettings:
        """Settings dictionary set by the [@cell][kfactory.kcell.cell] decorator."""
        return self._settings

    @property
    def name(self) -> str:
        """Name of the KCell."""
        return self._kdb_cell.name

    @name.setter
    def name(self, value: str) -> None:
        if self._locked:
            raise LockedError(self)
        self._kdb_cell.name = value

    @property
    def prop_id(self) -> int:
        """Gets the properties ID associated with the cell."""
        return self._kdb_cell.prop_id

    @prop_id.setter
    def prop_id(self, value: int) -> None:
        if self._locked:
            raise LockedError(self)
        self._kdb_cell.prop_id = value

    @property
    def ghost_cell(self) -> bool:
        """Returns a value indicating whether the cell is a "ghost cell"."""
        return self._kdb_cell.ghost_cell

    @ghost_cell.setter
    def ghost_cell(self, value: bool) -> None:
        if self._locked:
            raise LockedError(self)
        self._kdb_cell.ghost_cell = value

    def __getattr__(self, name):  # type: ignore[no-untyped-def]
        """If KCell doesn't have an attribute, look in the KLayout Cell."""
        return getattr(self._kdb_cell, name)

    def dup(self) -> KCell:
        """Copy the full cell.

        Sets `_locked` to `False`

        Returns:
            cell: Exact copy of the current cell.
                The name will have `$1` as duplicate names are not allowed
        """
        kdb_copy = self._kdb_copy()

        c = KCell(kcl=self.kcl, kdb_cell=kdb_copy)
        c.ports = self.ports.copy()

        c._settings = self.settings.model_copy()
        c.info = self.info.model_copy()

        return c

    def __copy__(self) -> KCell:
        """Enables use of `copy.copy` and `copy.deep_copy`."""
        return self.dup()

    def add_port(
        self, port: Port, name: str | None = None, keep_mirror: bool = False
    ) -> Port:
        """Add an existing port. E.g. from an instance to propagate the port.

        Args:
            port: The port to add.
            name: Overwrite the name of the port
            keep_mirror: Keep the mirror part of the transformation of a port if
                `True`, else set the mirror flag to `False`.
        """
        if self._locked:
            raise LockedError(self)
        return self.ports.add_port(port=port, name=name, keep_mirror=keep_mirror)

    def add_ports(
        self, ports: Iterable[Port], prefix: str = "", keep_mirror: bool = False
    ) -> None:
        """Add a sequence of ports to the cells.

        Can be useful to add all ports of a instance for example.

        Args:
            ports: list/tuple (anything iterable) of ports.
            prefix: string to add in front of all the port names
            keep_mirror: Keep the mirror part of the transformation of a port if
                `True`, else set the mirror flag to `False`.
        """
        if self._locked:
            raise LockedError(self)
        self.ports.add_ports(ports=ports, prefix=prefix, keep_mirror=keep_mirror)

    @classmethod
    def from_yaml(
        cls: Callable[..., KCell],
        constructor: Any,
        node: Any,
        verbose: bool = False,
    ) -> KCell:
        """Internal function used by the placer to convert yaml to a KCell."""
        d = ruamel.yaml.constructor.SafeConstructor.construct_mapping(
            constructor,
            node,
            deep=True,
        )
        cell = cls(d["name"])
        if verbose:
            print(f"Building {d['name']}")
        cell.ports = d.get("ports", Ports(ports=[], kcl=cell.kcl))
        cell._settings = KCellSettings(**d.get("settings", {}))
        for inst in d.get("insts", []):
            if "cellname" in inst:
                _cell = cell.kcl[inst["cellname"]]
            elif "cellfunction" in inst:
                module_name, fname = inst["cellfunction"].rsplit(".", 1)
                module = importlib.import_module(module_name)
                cellf = getattr(module, fname)
                _cell = cellf(**inst["settings"])
                del module
            else:
                raise NotImplementedError(
                    'To define an instance, either a "cellfunction" or'
                    ' a "cellname" needs to be defined'
                )
            t = inst.get("trans", {})
            if isinstance(t, str):
                cell.create_inst(
                    _cell,
                    kdb.Trans.from_s(inst["trans"]),
                )
            else:
                angle = t.get("angle", 0)
                mirror = t.get("mirror", False)

                kinst = cell.create_inst(
                    _cell,
                    kdb.Trans(angle, mirror, 0, 0),
                )

                x0_yml = t.get("x0", DEFAULT_TRANS["x0"])
                y0_yml = t.get("y0", DEFAULT_TRANS["y0"])
                x_yml = t.get("x", DEFAULT_TRANS["x"])
                y_yml = t.get("y", DEFAULT_TRANS["y"])
                margin = t.get("margin", DEFAULT_TRANS["margin"])
                margin_x = margin.get(
                    "x", DEFAULT_TRANS["margin"]["x"]  # type: ignore[index]
                )
                margin_y = margin.get(
                    "y", DEFAULT_TRANS["margin"]["y"]  # type: ignore[index]
                )
                margin_x0 = margin.get(
                    "x0", DEFAULT_TRANS["margin"]["x0"]  # type: ignore[index]
                )
                margin_y0 = margin.get(
                    "y0", DEFAULT_TRANS["margin"]["y0"]  # type: ignore[index]
                )
                ref_yml = t.get("ref", DEFAULT_TRANS["ref"])
                if isinstance(ref_yml, str):
                    for i in reversed(cell.insts):
                        if i.cell.name == ref_yml:
                            ref = i
                            break
                    else:
                        IndexError(f"No instance with cell name: <{ref_yml}> found")
                elif isinstance(ref_yml, int) and len(cell.insts) > 1:
                    ref = cell.insts[ref_yml]

                # margins for x0/y0 need to be in with opposite sign of
                # x/y due to them being subtracted later

                # x0
                match x0_yml:
                    case "W":
                        x0 = kinst.bbox().left - margin_x0
                    case "E":
                        x0 = kinst.bbox().right + margin_x0
                    case _:
                        if isinstance(x0_yml, int):
                            x0 = x0_yml
                        else:
                            NotImplementedError("unknown format for x0")
                # y0
                match y0_yml:
                    case "S":
                        y0 = kinst.bbox().bottom - margin_y0
                    case "N":
                        y0 = kinst.bbox().top + margin_y0
                    case _:
                        if isinstance(y0_yml, int):
                            y0 = y0_yml
                        else:
                            NotImplementedError("unknown format for y0")
                # x
                match x_yml:
                    case "W":
                        if len(cell.insts) > 1:
                            x = ref.bbox().left
                            if x_yml != x0_yml:
                                x -= margin_x
                        else:
                            x = margin_x
                    case "E":
                        if len(cell.insts) > 1:
                            x = ref.bbox().right
                            if x_yml != x0_yml:
                                x += margin_x
                        else:
                            x = margin_x
                    case _:
                        if isinstance(x_yml, int):
                            x = x_yml
                        else:
                            NotImplementedError("unknown format for x")
                # y
                match y_yml:
                    case "S":
                        if len(cell.insts) > 1:
                            y = ref.bbox().bottom
                            if y_yml != y0_yml:
                                y -= margin_y
                        else:
                            y = margin_y
                    case "N":
                        if len(cell.insts) > 1:
                            y = ref.bbox().top
                            if y_yml != y0_yml:
                                y += margin_y
                        else:
                            y = margin_y
                    case _:
                        if isinstance(y_yml, int):
                            y = y_yml
                        else:
                            NotImplementedError("unknown format for y")
                kinst.transform(kdb.Trans(0, False, x - x0, y - y0))
        type_to_class: dict[
            str,
            Callable[
                [str],
                kdb.Box
                | kdb.DBox
                | kdb.Polygon
                | kdb.DPolygon
                | kdb.Edge
                | kdb.DEdge
                | kdb.Text
                | kdb.DText,
            ],
        ] = {
            "box": kdb.Box.from_s,
            "polygon": kdb.Polygon.from_s,
            "edge": kdb.Edge.from_s,
            "text": kdb.Text.from_s,
            "dbox": kdb.DBox.from_s,
            "dpolygon": kdb.DPolygon.from_s,
            "dedge": kdb.DEdge.from_s,
            "dtext": kdb.DText.from_s,
        }

        for layer, shapes in dict(d.get("shapes", {})).items():
            linfo = kdb.LayerInfo.from_string(layer)
            for shape in shapes:
                shapetype, shapestring = shape.split(" ", 1)
                cell.shapes(cell.layout().layer(linfo)).insert(
                    type_to_class[shapetype](shapestring)
                )

        return cell

    def show(self) -> None:
        """Stream the gds to klive.

        Will create a temporary file of the gds and load it in KLayout via klive
        """
        show(self)

    def plot(self) -> None:
        """Display cell.

        Usage: Pass the kcell variable as an argument in the cell at the end
        """
        from .widgets.interactive import display_kcell  # type: ignore[attr-defined]

        display_kcell(self)

    def _ipython_display_(self) -> None:
        """Display a cell in a Jupyter Cell.

        Usage: Pass the kcell variable as an argument in the cell at the end
        """
        self.plot()

    def __repr__(self) -> str:
        """Return a string representation of the Cell."""
        port_names = [p.name for p in self.ports]
        return f"{self.name}: ports {port_names}, {len(self.insts)} instances"

    @property
    def ports(self) -> Ports:
        """Ports associated with the cell."""
        return self._ports

    @ports.setter
    def ports(self, new_ports: InstancePorts | Ports) -> None:
        if self._locked:
            raise LockedError(self)
        self._ports = new_ports.copy()

    @overload
    def create_port(
        self,
        *,
        name: str | None = None,
        trans: kdb.Trans,
        width: int,
        layer: LayerEnum | int,
        port_type: str = "optical",
    ) -> Port:
        ...

    @overload
    def create_port(
        self,
        *,
        name: str | None = None,
        dcplx_trans: kdb.DCplxTrans,
        dwidth: float,
        layer: LayerEnum | int,
        port_type: str = "optical",
    ) -> Port:
        ...

    @overload
    def create_port(
        self,
        *,
        name: str | None = None,
        port: Port,
    ) -> Port:
        ...

    @overload
    def create_port(
        self,
        *,
        name: str | None = None,
        width: int,
        position: tuple[int, int],
        angle: int,
        layer: LayerEnum | int,
        port_type: str = "optical",
        mirror_x: bool = False,
    ) -> Port:
        ...

    def create_port(self, **kwargs: Any) -> Port:
        """Proxy for [Ports.create_port][kfactory.kcell.Ports.create_port]."""
        if self._locked:
            raise LockedError(self)
        return self.ports.create_port(**kwargs)

    @overload
    def create_inst(
        self,
        cell: KCell | int,
        trans: kdb.Trans | kdb.ICplxTrans | kdb.Vector = kdb.Trans(),
    ) -> Instance:
        ...

    @overload
    def create_inst(
        self,
        cell: KCell | int,
        trans: kdb.Trans | kdb.ICplxTrans | kdb.Vector = kdb.Trans(),
        *,
        a: kdb.Vector,
        b: kdb.Vector,
        na: int = 1,
        nb: int = 1,
    ) -> Instance:
        ...

    def create_inst(
        self,
        cell: KCell | int,
        trans: kdb.Trans | kdb.Vector | kdb.ICplxTrans = kdb.Trans(),
        a: kdb.Vector | None = None,
        b: kdb.Vector | None = None,
        na: int = 1,
        nb: int = 1,
        libcell_as_static: bool = False,
        static_name_separator: str = "__",
    ) -> Instance:
        """Add an instance of another KCell.

        Args:
            cell: The cell to be added
            trans: The integer transformation applied to the reference
            a: Vector for the array.
                Needs to be in positive X-direction. Usually this is only a
                Vector in x-direction. Some foundries won't allow other Vectors.
            b: Vector for the array.
                Needs to be in positive Y-direction. Usually this is only a
                Vector in x-direction. Some foundries won't allow other Vectors.
            na: Number of elements in direction of `a`
            nb: Number of elements in direction of `b`
            libcell_as_static: If the cell is a Library cell
                (different KCLayout object), convert it to a static cell. This can cause
                name collisions that are automatically resolved by appending $1[..n] on
                the newly created cell.
            static_name_separator: Stringt to separate the KCLayout name from the cell
                name when converting library cells (other KCLayout object than the one
                of this KCell) to static cells (copy them into this KCell's KCLayout).

        Returns:
            The created instance
        """
        if self._locked:
            raise LockedError(self)
        if isinstance(cell, int):
            ci = cell
        else:
            if cell.layout() == self.layout():
                ci = cell.cell_index()
            else:
                assert cell.layout().library() is not None
                lib_ci = self.kcl.layout.add_lib_cell(
                    cell.kcl.library, cell.cell_index()
                )
                kcell = self.kcl[lib_ci]
                for port in cell.ports:
                    pl = port.layer
                    _layer = self.kcl.layer(cell.kcl.get_info(pl))
                    try:
                        _layer = self.kcl.layers(_layer)  # type: ignore[call-arg]
                    except ValueError:
                        pass
                    kcell.create_port(
                        name=port.name,
                        dwidth=port.d.width,
                        dcplx_trans=port.dcplx_trans,
                        layer=_layer,
                    )
                if libcell_as_static:
                    ci = self.kcl.convert_cell_to_static(lib_ci)
                    kcell = self.kcl[ci]
                    for port in cell.ports:
                        pl = port.layer
                        _layer = self.kcl.layer(cell.kcl.get_info(pl))
                        try:
                            _layer = self.kcl.layers(_layer)  # type: ignore[call-arg]
                        except ValueError:
                            pass
                        kcell.create_port(
                            name=port.name,
                            dwidth=port.d.width,
                            dcplx_trans=port.dcplx_trans,
                            layer=_layer,
                        )
                    kcell.name = cell.kcl.name + static_name_separator + cell.name
                else:
                    ci = lib_ci

        if a is None:
            ca = self._kdb_cell.insert(kdb.CellInstArray(ci, trans))
        else:
            if b is None:
                b = kdb.Vector()
            ca = self._kdb_cell.insert(kdb.CellInstArray(ci, trans, a, b, na, nb))
        inst = Instance(self.kcl, ca)
        self.insts.append(inst)
        return inst

    def _kdb_copy(self) -> kdb.Cell:
        return self._kdb_cell.dup()

    def layer(self, *args: Any, **kwargs: Any) -> int:
        """Get the layer info, convenience for `klayout.db.Layout.layer`."""
        return self.kcl.layout.layer(*args, **kwargs)

    def __lshift__(self, cell: KCell) -> Instance:
        """Convenience function for [create_inst][kfactory.kcell.KCell.create_inst].

        Args:
            cell: The cell to be added as an instance
        """
        return self.create_inst(cell)

    def hash(self) -> bytes:
        """Provide a unique hash of the cell."""
        h = sha3_512()
        h.update(self.name.encode("ascii", "ignore"))

        for layer_index in self.layout().layer_indexes():
            h.update(layer_index.to_bytes(8, "big"))
            for shape in self.shapes(layer_index).each(kdb.Shapes.SRegions):
                h.update(shape.polygon.hash().to_bytes(8, "big"))
            for shape in self.shapes(layer_index).each(kdb.Shapes.STexts):
                h.update(shape.text.hash().to_bytes(8, "big"))
        port_hashs = list(sorted(p.hash() for p in self.ports._ports))
        for _hash in port_hashs:
            h.update(_hash)
        insts_hashs = list(sorted(inst.hash for inst in self.insts))
        for _hash in insts_hashs:
            h.update(_hash)
        return h.digest()

    def autorename_ports(self, rename_func: Callable[..., None] | None = None) -> None:
        """Rename the ports with the schema angle -> "NSWE" and sort by x and y.

        Args:
            rename_func: Function that takes Iterable[Port] and renames them.
                This can of course contain a filter and only rename some of the ports
        """
        if self._locked:
            raise LockedError(self)
        if rename_func is None:
            self.kcl.rename_function(self.ports._ports)
        else:
            rename_func(self.ports._ports)

    def flatten(self, prune: bool = True, merge: bool = True) -> None:
        """Flatten the cell.

        Pruning will delete the klayout.db.Cell if unused,
        but might cause artifacts at the moment.

        Args:
            prune: Delete unused child cells if they aren't used in any other KCell
            merge: Merge the shapes on all layers
        """
        if self._locked:
            raise LockedError(self)
        self._kdb_cell.flatten(False)  # prune)
        self.insts = Instances()

        if merge:
            for layer in self.layout().layer_indexes():
                reg = kdb.Region(self.begin_shapes_rec(layer))
                reg.merge()
                self.clear(layer)
                self.shapes(layer).insert(reg)

    def draw_ports(self) -> None:
        """Draw all the ports on their respective layer."""
        polys: dict[int, kdb.Region] = {}

        for port in self.ports:
            w = port.width

            if w in polys:
                poly = polys[w]
            else:
                poly = kdb.Region()
                poly.insert(
                    kdb.Polygon(
                        [
                            kdb.Point(0, -w // 2),
                            kdb.Point(0, w // 2),
                            kdb.Point(w // 2, 0),
                        ]
                    )
                )
                if w > 20:
                    poly -= kdb.Region(
                        kdb.Polygon(
                            [
                                kdb.Point(w // 20, 0),
                                kdb.Point(w // 20, -w // 2 + int(w * 2.5 // 20)),
                                kdb.Point(w // 2 - int(w * 1.41 / 20), 0),
                            ]
                        )
                    )
            polys[w] = poly
            if port._trans:
                self.shapes(port.layer).insert(poly.transformed(port.trans))
                self.shapes(port.layer).insert(
                    kdb.Text(port.name if port.name else "", port.trans)
                )
            else:
                self.shapes(port.layer).insert(poly, port.dcplx_trans)
                self.shapes(port.layer).insert(
                    kdb.Text(port.name if port.name else "", port.trans)
                )

    def write(
        self, filename: str | Path, save_options: kdb.SaveLayoutOptions = default_save()
    ) -> None:
        """Write a KCell to a GDS.

        See [KCLayout.write][kfactory.kcell.KCLayout.write] for more info.
        """
        for kcell in (self.kcl[ci] for ci in self.called_cells()):
            kcell.set_meta_data()
        self.set_meta_data()
        return self._kdb_cell.write(str(filename), save_options)

    @classmethod
    def to_yaml(cls, representer, node):  # type: ignore
        """Internal function to convert the cell to yaml."""
        d = {
            "name": node.name,
            "ports": node.ports,  # Ports.to_yaml(representer, node.ports),
        }

        insts = [
            {"cellname": inst.cell.name, "trans": inst.instance.trans.to_s()}
            for inst in node.insts
        ]
        shapes = {
            node.layout()
            .get_info(layer)
            .to_s(): [shape.to_s() for shape in node.shapes(layer).each()]
            for layer in node.layout().layer_indexes()
            if not node.shapes(layer).is_empty()
        }

        if insts:
            d["insts"] = insts
        if shapes:
            d["shapes"] = shapes
        if len(node.settings) > 0:
            d["settings"] = node.settings
        return representer.represent_mapping(cls.yaml_tag, d)

    def each_inst(self) -> Iterator[Instance]:
        """Iterates over all child instances (which may actually be instance arrays)."""
        yield from (Instance(self.kcl, inst) for inst in self._kdb_cell.each_inst())

    def each_overlapping_inst(self, b: kdb.Box | kdb.DBox) -> Iterator[Instance]:
        """Gets the instances overlapping the given rectangle."""
        yield from (
            Instance(self.kcl, inst) for inst in self._kdb_cell.each_overlapping_inst(b)
        )

    def each_touching_inst(self, b: kdb.Box | kdb.DBox) -> Iterator[Instance]:
        """Gets the instances overlapping the given rectangle."""
        yield from (
            Instance(self.kcl, inst) for inst in self._kdb_cell.each_touching_inst(b)
        )

    @overload
    def insert(
        self, inst: Instance | kdb.CellInstArray | kdb.DCellInstArray
    ) -> Instance:
        ...

    @overload
    def insert(
        self, inst: kdb.CellInstArray | kdb.DCellInstArray, property_id: int
    ) -> Instance:
        ...

    def insert(
        self,
        inst: Instance | kdb.CellInstArray | kdb.DCellInstArray,
        property_id: int | None = None,
    ) -> Instance:
        """Inserts a cell instance given by another reference."""
        if self._locked:
            raise LockedError(self)
        if isinstance(inst, Instance):
            return Instance(self.kcl, self._kdb_cell.insert(inst._instance))
        else:
            if not property_id:
                return Instance(self.kcl, self._kdb_cell.insert(inst))
            else:
                assert isinstance(inst, kdb.CellInstArray | kdb.DCellInstArray)
                return Instance(self.kcl, self._kdb_cell.insert(inst, property_id))

    @overload
    def transform(
        self,
        inst: kdb.Instance,
        trans: kdb.Trans | kdb.DTrans | kdb.ICplxTrans | kdb.DCplxTrans,
        /,
        *,
        no_warn: bool = False,
    ) -> Instance:
        ...

    @overload
    def transform(
        self,
        trans: kdb.Trans | kdb.DTrans | kdb.ICplxTrans | kdb.DCplxTrans,
        /,
        *,
        no_warn: bool = False,
    ) -> None:
        ...

    def transform(
        self,
        inst_or_trans: kdb.Instance
        | kdb.Trans
        | kdb.DTrans
        | kdb.ICplxTrans
        | kdb.DCplxTrans,
        trans: kdb.Trans | kdb.DTrans | kdb.ICplxTrans | kdb.DCplxTrans | None = None,
        /,
        *,
        no_warn: bool = False,
    ) -> Instance | None:
        """Transforms the instance or cell with the transformation given."""
        config.logger.warning(
            "You are transforming the KCell {}. It is highly discouraged to do this."
            " You probably want to transform an instance instead.",
            self.name,
        )
        if self._locked:
            raise LockedError(self)
        if trans:
            return Instance(
                self.kcl,
                self._kdb_cell.transform(
                    inst_or_trans, trans  # type: ignore[arg-type]
                ),
            )
        else:
            return self._kdb_cell.transform(inst_or_trans)  # type:ignore[arg-type]

    def set_meta_data(self) -> None:
        """Set metadata of the Cell.

        Currently, ports, settings and info will be set.
        """
        for i, port in enumerate(self.ports):
            if port.name:
                self.add_meta_info(
                    kdb.LayoutMetaInfo(
                        f"kfactory:ports:{i}:name", port.name, None, True
                    )
                )
            self.add_meta_info(
                kdb.LayoutMetaInfo(
                    f"kfactory:ports:{i}:layer",
                    self.kcl.layout.get_info(port.layer).to_s(),
                    None,
                    True,
                )
            )
            self.add_meta_info(
                kdb.LayoutMetaInfo(f"kfactory:ports:{i}:width", port.width, None, True)
            )
            self.add_meta_info(
                kdb.LayoutMetaInfo(
                    f"kfactory:ports:{i}:port_type", port.port_type, None, True
                )
            )
            if port._trans:
                self.add_meta_info(
                    kdb.LayoutMetaInfo(
                        f"kfactory:ports:{i}:trans", port._trans.to_s(), None, True
                    )
                )
            elif port._dcplx_trans:
                self.add_meta_info(
                    kdb.LayoutMetaInfo(
                        f"kfactory:ports:{i}:dcplx_trans",
                        port._dcplx_trans.to_s(),
                        None,
                        True,
                    )
                )

            info = port.info.model_dump()
            for name, value in port.info:
                info[name] = value

            for name, value in info.items():
                self.add_meta_info(
                    kdb.LayoutMetaInfo(
                        f"kfactory:ports:{i}:info:{name}",
                        value,
                        None,
                        True,
                    )
                )

        for name, setting in self.settings.model_dump().items():
            self.add_meta_info(
                kdb.LayoutMetaInfo(f"kfactory:settings:{name}", setting, None, True)
            )
        for name, info in self.info.model_dump().items():
            self.add_meta_info(
                kdb.LayoutMetaInfo(f"kfactory:info:{name}", info, None, True)
            )
        for name, info in self.info:
            self.add_meta_info(
                kdb.LayoutMetaInfo(f"kfactory:info:{name}", info, None, True)
            )

    def get_meta_data(self) -> None:
        """Read metadata from the KLayout Layout object."""
        port_dict: dict[str, Any] = {}
        settings = {}
        for meta in self.each_meta_info():
            if meta.name.startswith("kfactory:ports"):
                i, _type = meta.name.removeprefix("kfactory:ports:").split(":", 1)
                if i not in port_dict:
                    port_dict[i] = {}
                if not _type.startswith("info"):
                    port_dict[i][_type] = meta.value
                else:
                    if "info" not in port_dict[i]:
                        port_dict[i]["info"] = {}
                    port_dict[i]["info"][_type.removeprefix("info:")] = meta.value
            elif meta.name.startswith("kfactory:info"):
                self.info[meta.name.removeprefix("kfactory:info:")] = meta.value
            elif meta.name.startswith("kfactory:settings"):
                settings[meta.name.removeprefix("kfactory:settings:")] = meta.value

        self._settings = KCellSettings(**settings)

        # ports = Ports()
        self.ports = Ports(self.kcl)
        for index in sorted(port_dict.keys()):
            _d = port_dict[index]
            name = _d.get("name", None)
            port_type = _d["port_type"]
            layer = self.kcl.layout.layer(kdb.LayerInfo.from_string(_d["layer"]))
            width = _d["width"]
            trans = _d.get("trans", None)
            dcplx_trans = _d.get("dcplx_trans", None)
            _port = Port(
                name=name,
                width=width,
                layer=layer,
                trans=kdb.Trans.R0,
                kcl=self.kcl,
                port_type=port_type,
                info=_d.get("info", {}),
            )
            if trans:
                _port.trans = kdb.Trans.from_s(trans)
            elif dcplx_trans:
                _port.dcplx_trans = kdb.DCplxTrans.from_s(dcplx_trans)

            self.add_port(_port, keep_mirror=True)

    @property
    def xmin(self) -> int:
        """Returns the x-coordinate of the left edge of the bounding box."""
        return self._kdb_cell.bbox().left

    @property
    def ymin(self) -> int:
        """Returns the x-coordinate of the left edge of the bounding box."""
        return self._kdb_cell.bbox().bottom

    @property
    def xmax(self) -> int:
        """Returns the x-coordinate of the left edge of the bounding box."""
        return self._kdb_cell.bbox().right

    @property
    def ymax(self) -> int:
        """Returns the x-coordinate of the left edge of the bounding box."""
        return self._kdb_cell.bbox().top

    def l2n(self, port_types: Iterable[str] = ("optical",)) -> kdb.LayoutToNetlist:
        """Generate a LayoutToNetlist object from the port types.

        Args:
            port_types: The port types to consider for the netlist extraction.
        """
        l2n = kdb.LayoutToNetlist(self.name, self.kcl.dbu)
        l2n.extract_netlist()
        il = l2n.internal_layout()

        def filter_port(port: Port) -> bool:
            return port.port_type in port_types

        for ci in self.called_cells():
            c = self.kcl[ci]
            c.circuit(l2n, port_types=port_types)
        self.circuit(l2n, port_types=port_types)
        il.assign(self.kcl.layout)
        return l2n

    def circuit(
        self, l2n: kdb.LayoutToNetlist, port_types: Iterable[str] = ("optical",)
    ) -> None:
        """Create the circuit of the KCell in the given netlist."""
        netlist = l2n.netlist()

        def port_filter(num_port: tuple[int, Port]) -> bool:
            return num_port[1].port_type in port_types

        circ = kdb.Circuit()
        circ.name = self.name
        circ.cell_index = self.cell_index()
        circ.boundary = self.boundary or self.dbbox()

        inst_ports: dict[
            str, dict[str, list[tuple[int, int, Instance, Port, kdb.SubCircuit]]]
        ] = {}
        cell_ports: dict[str, dict[str, list[tuple[int, Port]]]] = {}

        # sort the cell's ports by position and layer

        portnames: set[str] = set()

        for i, port in filter(port_filter, enumerate(self.ports)):
            _trans = port.trans.dup()
            _trans.angle = _trans.angle % 2
            _trans.mirror = False
            layer_info = self.kcl.layout.get_info(port.layer)
            layer = f"{layer_info.layer}_{layer_info.datatype}"

            if port.name in portnames:
                raise ValueError(
                    "Netlist extraction is not possible with"
                    f" colliding port names. Duplicate name: {port.name}"
                )

            v = _trans.disp
            h = f"{v.x}_{v.y}"
            if h not in cell_ports:
                cell_ports[h] = {}
            if layer not in cell_ports[h]:
                cell_ports[h][layer] = []
            cell_ports[h][layer].append((i, port))

            if port.name:
                portnames.add(port.name)

        # create nets and connect pins for each cell_port
        for h, layer_dict in cell_ports.items():
            for layer, _ports in layer_dict.items():
                net = circ.create_net(
                    "-".join(_port[1].name or f"{_port[0]}" for _port in _ports)
                )
                for i, port in _ports:
                    pin = circ.create_pin(port.name or f"{i}")
                    circ.connect_pin(pin, net)

        # sort the ports of all instances by position and layer
        for i, inst in enumerate(self.insts):
            name = inst.name or f"{i}_{inst.cell.name}"
            subc = circ.create_subcircuit(
                netlist.circuit_by_cell_index(inst.cell_index), name
            )
            subc.trans = inst.dcplx_trans

            for j, port in filter(port_filter, enumerate(inst.ports)):
                _trans = port.trans.dup()
                _trans.angle = _trans.angle % 2
                _trans.mirror = False
                v = _trans.disp
                h = f"{v.x}_{v.y}"
                layer_info = self.kcl.layout.get_info(port.layer)
                layer = f"{layer_info.layer}_{layer_info.datatype}"
                if h not in inst_ports:
                    inst_ports[h] = {}
                if layer not in inst_ports[h]:
                    inst_ports[h][layer] = []
                inst_ports[h][layer].append((i, j, inst, port, subc))

        # go through each position and layer and connect ports to their matching cell
        # port or connect the instance ports
        for h, inst_layer_dict in inst_ports.items():
            for layer, ports in inst_layer_dict.items():
                if h in cell_ports and layer in cell_ports[h]:
                    # connect a cell port to its matching instance port
                    cellports = cell_ports[h][layer]

                    assert len(cellports) == 1, (
                        "Netlists with directly connect cell ports"
                        " are currently not supported"
                    )
                    assert len(ports) == 1, (
                        f"Multiple instance {[port[4] for port in ports]}"
                        f"ports connected to the cell port {cellports[0]}"
                        " this is currently not supported and most likely a bug"
                    )

                    inst_port = ports[0]
                    port = inst_port[3]

                    port_check(cellports[0][1], port, PortCheck.all_overlap)
                    subc = inst_port[4]
                    subc.connect_pin(
                        subc.circuit_ref().pin_by_name(port.name or str(inst_port[1])),
                        circ.net_by_name(cellports[0][1].name or f"{cellports[0][0]}"),
                    )
                else:
                    # connect instance ports to each other
                    name = "-".join(
                        [
                            (inst.name or str(i)) + "_" + (port.name or str(j))
                            for i, j, inst, port, subc in ports
                        ]
                    )

                    net = circ.create_net(name)
                    assert len(ports) <= 2, (
                        "Optical connection with more than two ports are not supported "
                        f"{[_port[3] for _port in ports]}"
                    )
                    if len(ports) == 2:
                        port_check(ports[0][3], ports[1][3], PortCheck.all_opposite)
                        for i, j, inst, port, subc in ports:
                            subc.connect_pin(
                                subc.circuit_ref().pin_by_name(port.name or str(j)), net
                            )
        netlist.add(circ)

    def connectivity_check(
        self,
        port_types: list[str] = [],
        layers: list[int] = [],
        db: rdb.ReportDatabase | None = None,
        recursive: bool = True,
        add_cell_ports: bool = False,
        check_layer_connectivity: bool = True,
    ) -> rdb.ReportDatabase:
        """Create a ReportDatabase for port problems.

        Problems are overlapping ports that aren't aligned, more than two ports
        overlapping, width mismatch, port_type mismatch.

        Args:
            port_types: Filter for certain port typers
            layers: Only create the report for certain layers
            db: Use an existing ReportDatabase instead of creating a new one
            recursive: Create the report not only for this cell, but all child cells as
                well.
            add_cell_ports: Also add a category "CellPorts" which contains all the cells
                selected ports.
            check_layer_connectivity: Check whether the layer overlaps with instances.
        """
        if not db:
            db = rdb.ReportDatabase(f"Connectivity Check {self.name}")
        if recursive:
            cc = self.called_cells()
            for c in self.kcl.each_cell_bottom_up():
                if c in cc:
                    self.kcl[c].connectivity_check(
                        port_types=port_types, db=db, recursive=False
                    )
        db_cell = db.create_cell(self.name)
        cell_ports = {}
        layer_cats: dict[int, rdb.RdbCategory] = {}

        def layer_cat(layer: int) -> rdb.RdbCategory:
            if layer not in layer_cats:
                if isinstance(layer, LayerEnum):
                    ln = layer.name
                else:
                    li = self.kcl.get_info(layer)
                    ln = str(li).replace("/", "_")
                layer_cats[layer] = db.category_by_path(ln) or db.create_category(ln)
            return layer_cats[layer]

        for port in self.ports:
            if (not port_types or port.port_type in port_types) and (
                not layers or port.layer in layers
            ):
                if add_cell_ports:
                    c_cat = db.category_by_path(
                        layer_cat(port.layer).path() + ".CellPorts"
                    ) or db.create_category(layer_cat(port.layer), "CellPorts")
                    it = db.create_item(db_cell, c_cat)
                    if port.name:
                        it.add_value(f"Port name: {port.name}")
                    if port._trans:
                        it.add_value(
                            port_polygon(port.width)
                            .transformed(port.trans)
                            .to_dtype(self.kcl.dbu)
                        )
                    else:
                        it.add_value(
                            port_polygon(port.width)
                            .to_dtype(self.kcl.dbu)
                            .transformed(port.dcplx_trans)
                        )
                xy = (port.x, port.y)
                if port.layer not in cell_ports:
                    cell_ports[port.layer] = {xy: [port]}
                else:
                    if xy not in cell_ports[port.layer]:
                        cell_ports[port.layer][xy] = [port]
                    else:
                        cell_ports[port.layer][xy].append(port)
                rec_it = kdb.RecursiveShapeIterator(
                    self.kcl.layout,
                    self._kdb_cell,
                    port.layer,
                    kdb.Box(2, port.width).transformed(port.trans),
                )
                edges = kdb.Region(rec_it).merge().edges().merge()
                port_edge = kdb.Edge(0, port.width // 2, 0, -port.width // 2)
                if port._trans:
                    port_edge = port_edge.transformed(port.trans)
                else:
                    port_edge = port_edge.transformed(
                        port.dcplx_trans.to_itrans(self.kcl.dbu)
                    )
                p_edges = kdb.Edges([port_edge])
                phys_overlap = p_edges & edges
                if not phys_overlap.is_empty() and phys_overlap[0] != port_edge:
                    p_cat = db.category_by_path(
                        layer_cat(port.layer).path() + ".PartialPhysicalShape"
                    ) or db.create_category(
                        layer_cat(port.layer), "PartialPhysicalShape"
                    )
                    it = db.create_item(db_cell, p_cat)
                    it.add_value(
                        "Insufficient overlap, partial overlap with polygon of"
                        f" {(phys_overlap[0].p1- phys_overlap[0].p2).abs()}/"
                        f"{port.width}"
                    )
                    it.add_value(
                        port_polygon(port.width)
                        .transformed(port.trans)
                        .to_dtype(self.kcl.dbu)
                        if port._trans
                        else port_polygon(port.width)
                        .to_dtype(self.kcl.dbu)
                        .transformed(port.dcplx_trans)
                    )
                elif phys_overlap.is_empty():
                    p_cat = db.category_by_path(
                        layer_cat(port.layer).path() + ".MissingPhysicalShape"
                    ) or db.create_category(
                        layer_cat(port.layer), "MissingPhysicalShape"
                    )
                    it = db.create_item(db_cell, p_cat)
                    it.add_value(
                        f"Found no overlapping Edge with Port {port.name or str(port)}"
                    )
                    it.add_value(
                        port_polygon(port.width)
                        .transformed(port.trans)
                        .to_dtype(self.kcl.dbu)
                        if port._trans
                        else port_polygon(port.width)
                        .to_dtype(self.kcl.dbu)
                        .transformed(port.dcplx_trans)
                    )

        inst_ports = {}
        for inst in self.insts:
            for port in inst.ports:
                if (not port_types or port.port_type in port_types) and (
                    not layers or port.layer in layers
                ):
                    xy = (port.x, port.y)
                    if port.layer not in inst_ports:
                        inst_ports[port.layer] = {xy: [(port, inst.cell)]}
                    else:
                        if xy not in inst_ports[port.layer]:
                            inst_ports[port.layer][xy] = [(port, inst.cell)]
                        else:
                            inst_ports[port.layer][xy].append((port, inst.cell))

        for layer, port_coord_mapping in inst_ports.items():
            lc = layer_cat(layer)
            for coord, ports in port_coord_mapping.items():
                match len(ports):
                    case 1:
                        if layer in cell_ports and coord in cell_ports[layer]:
                            ccp = _check_cell_ports(
                                cell_ports[layer][coord][0], ports[0][0]
                            )
                            if ccp & 1:
                                subc = db.category_by_path(
                                    lc.path() + ".WidthMismatch"
                                ) or db.create_category(lc, "WidthMismatch")
                                create_port_error(
                                    ports[0][0],
                                    cell_ports[layer][coord][0],
                                    ports[0][1],
                                    self,
                                    db,
                                    db_cell,
                                    subc,
                                    self.kcl.dbu,
                                )

                            if ccp & 2:
                                subc = db.category_by_path(
                                    lc.path() + ".AngleMismatch"
                                ) or db.create_category(lc, "AngleMismatch")
                                create_port_error(
                                    ports[0][0],
                                    cell_ports[layer][coord][0],
                                    ports[0][1],
                                    self,
                                    db,
                                    db_cell,
                                    subc,
                                    self.kcl.dbu,
                                )
                            if ccp & 4:
                                subc = db.category_by_path(
                                    lc.path() + ".TypeMismatch"
                                ) or db.create_category(lc, "TypeMismatch")
                                create_port_error(
                                    ports[0][0],
                                    cell_ports[layer][coord][0],
                                    ports[0][1],
                                    self,
                                    db,
                                    db_cell,
                                    subc,
                                    self.kcl.dbu,
                                )
                        else:
                            subc = db.category_by_path(
                                lc.path() + ".OrphanPort"
                            ) or db.create_category(lc, "OrphanPort")
                            it = db.create_item(db_cell, subc)
                            it.add_value(
                                f"Port Name: {ports[0][1].name}"
                                f"{ports[0][0].name or str(ports[0][0])})"
                            )
                            if ports[0][0]._trans:
                                it.add_value(
                                    port_polygon(ports[0][0].width)
                                    .transformed(ports[0][0]._trans)
                                    .to_dtype(self.kcl.dbu)
                                )
                            else:
                                it.add_value(
                                    port_polygon(port.width)
                                    .to_dtype(self.kcl.dbu)
                                    .transformed(port.dcplx_trans)
                                )

                    case 2:
                        cip = _check_inst_ports(ports[0][0], ports[1][0])
                        if cip & 1:
                            subc = db.category_by_path(
                                lc.path() + ".WidthMismatch"
                            ) or db.create_category(lc, "WidthMismatch")
                            create_port_error(
                                ports[0][0],
                                ports[1][0],
                                ports[0][1],
                                ports[1][1],
                                db,
                                db_cell,
                                subc,
                                self.kcl.dbu,
                            )

                        if cip & 2:
                            subc = db.category_by_path(
                                lc.path() + ".AngleMismatch"
                            ) or db.create_category(lc, "AngleMismatch")
                            create_port_error(
                                ports[0][0],
                                ports[1][0],
                                ports[0][1],
                                ports[1][1],
                                db,
                                db_cell,
                                subc,
                                self.kcl.dbu,
                            )
                        if cip & 4:
                            subc = db.category_by_path(
                                lc.path() + ".TypeMismatch"
                            ) or db.create_category(lc, "TypeMismatch")
                            create_port_error(
                                ports[0][0],
                                ports[1][0],
                                ports[0][1],
                                ports[1][1],
                                db,
                                db_cell,
                                subc,
                                self.kcl.dbu,
                            )
                        if layer in cell_ports and coord in cell_ports[layer]:
                            subc = db.category_by_path(
                                lc.path() + ".portoverlap"
                            ) or db.create_category(lc, "portoverlap")
                            it = db.create_item(db_cell, subc)
                            text = "Port Names: "
                            values: list[rdb.RdbItemValue] = []
                            cell_port = cell_ports[layer][coord][0]
                            text += (
                                f"{self.name}."
                                f"{cell_port.name or cell_port.trans.to_s()}/"
                            )
                            if cell_port._trans:
                                values.append(
                                    rdb.RdbItemValue(
                                        port_polygon(cell_port.width)
                                        .transformed(cell_port._trans)
                                        .to_dtype(self.kcl.dbu)
                                    )
                                )
                            else:
                                values.append(
                                    rdb.RdbItemValue(
                                        port_polygon(cell_port.width)
                                        .to_dtype(self.kcl.dbu)
                                        .transformed(cell_port.dcplx_trans)
                                    )
                                )
                            for _port in ports:
                                text += (
                                    f"{_port[1].name}."
                                    f"{_port[0].name or _port[0].trans.to_s()}/"
                                )

                                values.append(
                                    rdb.RdbItemValue(
                                        port_polygon(_port[0].width)
                                        .transformed(_port[0].trans)
                                        .to_dtype(self.kcl.dbu)
                                    )
                                )
                            it.add_value(text[:-1])
                            for value in values:
                                it.add_value(value)

                    case x if x > 2:
                        subc = db.category_by_path(
                            lc.path() + ".portoverlap"
                        ) or db.create_category(lc, "portoverlap")
                        it = db.create_item(db_cell, subc)
                        text = "Port Names: "
                        values = []
                        for _port in ports:
                            text += (
                                f"{_port[1].name}."
                                f"{_port[0].name or _port[0].trans.to_s()}/"
                            )

                            values.append(
                                rdb.RdbItemValue(
                                    port_polygon(_port[0].width)
                                    .transformed(_port[0].trans)
                                    .to_dtype(self.kcl.dbu)
                                )
                            )
                        it.add_value(text[:-1])
                        for value in values:
                            it.add_value(value)
            if check_layer_connectivity:
                error_region_shapes = kdb.Region()
                error_region_instances = kdb.Region()
                reg = kdb.Region(self.shapes(layer))
                inst_regions: dict[int, kdb.Region] = {}
                inst_region = kdb.Region()
                for i, inst in enumerate(self.insts):
                    _inst_region = kdb.Region(inst.bbox(layer))
                    inst_shapes: kdb.Region | None = None
                    if not (inst_region & _inst_region).is_empty():
                        if inst_shapes is None:
                            inst_shapes = kdb.Region()
                            shape_it = self.begin_shapes_rec_overlapping(
                                layer, inst.bbox(layer)
                            )
                            shape_it.select_cells([inst.cell.cell_index()])
                            shape_it.min_depth = 1
                            for _it in shape_it.each():
                                if _it.path()[0].inst() == inst._instance:
                                    inst_shapes.insert(
                                        _it.shape().polygon.transformed(_it.trans())
                                    )

                        for j, _reg in inst_regions.items():
                            if _reg & _inst_region:
                                __reg = kdb.Region()
                                shape_it = self.begin_shapes_rec_touching(
                                    layer, (_reg & _inst_region).bbox()
                                )
                                shape_it.select_cells([self.insts[j].cell.cell_index()])
                                shape_it.min_depth = 1
                                for _it in shape_it.each():
                                    if _it.path()[0].inst() == self.insts[j]._instance:
                                        __reg.insert(
                                            _it.shape().polygon.transformed(_it.trans())
                                        )

                                error_region_instances.insert(__reg & inst_shapes)

                    if not (_inst_region & reg).is_empty():
                        rec_it = self.begin_shapes_rec_touching(
                            layer, (_inst_region & reg).bbox()
                        )
                        rec_it.min_depth = 1
                        error_region_shapes += kdb.Region(rec_it) & reg
                    inst_region += _inst_region
                    inst_regions[i] = _inst_region
                if not error_region_shapes.is_empty():
                    sc = db.category_by_path(
                        layer_cat(layer).path() + ".ShapeInstanceshapeOverlap"
                    ) or db.create_category(
                        layer_cat(layer), "ShapeInstanceshapeOverlap"
                    )
                    it = db.create_item(db_cell, sc)
                    it.add_value("Shapes overlapping with shapes of instances")
                    for poly in error_region_shapes.merge().each():
                        it.add_value(poly.to_dtype(self.kcl.dbu))
                if not error_region_instances.is_empty():
                    sc = db.category_by_path(
                        layer_cat(layer).path() + ".InstanceshapeOverlap"
                    ) or db.create_category(layer_cat(layer), "InstanceshapeOverlap")
                    it = db.create_item(db_cell, sc)
                    it.add_value(
                        "Instance shapes overlapping with shapes of other instances"
                    )
                    for poly in error_region_instances.merge().each():
                        it.add_value(poly.to_dtype(self.kcl.dbu))

        return db


def create_port_error(
    p1: Port,
    p2: Port,
    c1: KCell,
    c2: KCell,
    db: rdb.ReportDatabase,
    db_cell: rdb.RdbCell,
    cat: rdb.RdbCategory,
    dbu: float,
) -> None:
    it = db.create_item(db_cell, cat)
    if p1.name and p2.name:
        it.add_value(f"Port Names: {c1.name}.{p1.name}/" f"{c2.name}.{p2.name}")
    it.add_value(port_polygon(p1.width).transformed(p1.trans).to_dtype(dbu))
    it.add_value(port_polygon(p2.width).transformed(p2.trans).to_dtype(dbu))


class Constants(BaseSettings):
    """Constant Model class."""

    pass


class KCLayout(BaseModel, arbitrary_types_allowed=True, extra="allow"):
    """Small extension to the klayout.db.Layout.

    It adds tracking for the [KCell][kfactory.kcell.KCell] objects
    instead of only the `klayout.db.Cell` objects.
    Additionally it allows creation and registration through `create_cell`

    All attributes of `klayout.db.Layout` are transparently accessible

    Attributes:
        editable: Whether the layout should be opened in editable mode (default: True)
        rename_function: function that takes an iterable object of ports and renames
            them
    """

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

    # name: str
    _name: str
    layout: kdb.Layout
    layer_enclosures: LayerEnclosureModel
    enclosure: KCellEnclosure
    library: kdb.Library

    factories: KCellFactories
    kcells: dict[int, KCell]
    layers: type[LayerEnum]
    netlist_layer_mapping: dict[LayerEnum | int, LayerEnum | int] = Field(default={})
    sparameters_path: Path | str | None
    interconnect_cml_path: Path | str | None
    constants: Constants = Field(default_factory=Constants)
    rename_function: Callable[..., None]

    def __init__(
        self,
        name: str,
        layer_enclosures: dict[str, LayerEnclosure] | LayerEnclosureModel | None = None,
        enclosure: KCellEnclosure | None = None,
        # factories: dict[str, KCellFactory] | None = None,
        layers: type[LayerEnum] | None = None,
        sparameters_path: Path | str | None = None,
        interconnect_cml_path: Path | str | None = None,
        constants: type[Constants] | None = None,
        base_kcl: KCLayout | None = None,
        port_rename_function: Callable[..., None] = rename_clockwise,
        copy_base_kcl_layers: bool = True,
    ) -> None:
        """Create a new KCLayout (PDK). Can be based on an old KCLayout.

        Args:
            name: Name of the PDK.
            layer_enclosures: Additional KCellEnclosures that should be available
                except the KCellEnclosure
            enclosure: The standard KCellEnclosure of the PDK.
            cell_factories: Functions for creating pcells from the PDK.
            cells: Fixed cells of the PDK.
            layers: A LayerEnum describing the layerstack of the PDK
            sparameters_path: Path to the sparameters config file.
            interconnect_cml_path: Path to the interconnect file.
            constants: A model containing all the constants related to the PDK.
            base_kcl: an optional basis of the PDK.
            port_rename_function: Which function to use for renaming kcell ports.
            copy_base_kcl_layers: Copy all known layers from the base if any are
                defined.
        """
        if layers is not None:
            layer_dict = {
                _layer.name: (_layer.layer, _layer.datatype)
                for _layer in layers  # type: ignore[attr-defined]
            }
        else:
            layer_dict = {}

        if base_kcl:
            name = name
            # if layers is None:
            if copy_base_kcl_layers:
                base_layer_dict = {
                    _layer.name: (_layer.layer, _layer.datatype)
                    for _layer in base_kcl.layers  # type: ignore[attr-defined]
                }
                base_layer_dict.update(layer_dict)
                layer_dict = base_layer_dict

                layers = self.layerenum_from_dict(
                    name=base_kcl.layers.__name__,
                    layers=layer_dict,
                )
            else:
                layers = layerenum_from_dict(layer_dict, kcl=self)
            sparameters_path = sparameters_path or base_kcl.sparameters_path
            interconnect_cml_path = (
                interconnect_cml_path or base_kcl.interconnect_cml_path
            )
            _constants = constants() if constants else base_kcl.constants.copy()
            if enclosure is None:
                enclosure = base_kcl.enclosure or KCellEnclosure([])
            if layer_enclosures is None:
                layer_enclosures = LayerEnclosureModel()
        else:
            name = name

            if layer_enclosures:
                if isinstance(layer_enclosures, LayerEnclosureModel):
                    layer_enclosures = LayerEnclosureModel(
                        enclosure_mape={
                            name: lenc.copy_to(self)
                            for name, lenc in layer_enclosures.enclosure_map.items()
                        }
                    )
                else:
                    layer_enclosures = LayerEnclosureModel(
                        enclosure_mape={
                            name: lenc.copy_to(self)
                            for name, lenc in layer_enclosures.items()
                        }
                    )
            else:
                layer_enclosures = LayerEnclosureModel(enclosure_map={})

            enclosure = (
                enclosure.copy_to(self) if enclosure else KCellEnclosure(enclosures=[])
            )
            # cell_factories = cell_factories
            layers = self.layerenum_from_dict(name="LAYER", layers=layer_dict)
            sparameters_path = sparameters_path
            interconnect_cml_path = interconnect_cml_path
            _constants = constants() if constants else Constants()
            if enclosure is None:
                enclosure = KCellEnclosure([])
            if layer_enclosures is None:
                layer_enclosures = LayerEnclosureModel()

        library = kdb.Library()
        layout = library.layout()

        super().__init__(
            _name=name,
            kcells={},
            layer_enclosures=layer_enclosures,
            enclosure=enclosure,
            layers=layers,
            factories=KCellFactories({}),
            sparameters_path=sparameters_path,
            interconnect_cml_path=interconnect_cml_path,
            constants=_constants,
            library=library,
            layout=layout,
            rename_function=port_rename_function,
        )
        self._name = name

        self.library.register(self.name)

    def _set_name_and_library(self, name: str) -> None:
        self._name = name
        self.library.register(name)

    @computed_field  # type: ignore[misc]
    @property
    def name(self) -> str:
        """Name of the KCLayout."""
        return self._name

    def kcell(self, name: str | None = None, ports: Ports | None = None) -> KCell:
        """Create a new cell based ont he pdk's layout object."""
        return KCell(name=name, kcl=self, ports=ports)

    def layer_enum(
        self, name: str, layers: dict[str, tuple[int, int]]
    ) -> type[LayerEnum]:
        """Create a new LAYER enum based on the pdk's kcl."""
        return layerenum_from_dict(name=name, layers=layers, kcl=self)

    def __getattr__(self, name):  # type: ignore[no-untyped-def]
        """If KCLayout doesn't have an attribute, look in the KLayout Cell."""
        if name != "_name":
            return self.layout.__getattribute__(name)

    def __setattr__(self, name: str, value: Any) -> None:
        """Use a custom setter to automatically set attributes.

        If the attribute is not in this object, set it on the
        Layout object.
        """
        match name:
            case "_name":
                object.__setattr__(self, name, value)
            case "name":
                self._set_name_and_library(value)
            case _:
                if name in self.model_fields:
                    super().__setattr__(name, value)
                else:
                    self.layout.__setattr__(name, value)

    def layerenum_from_dict(
        self, name: str = "LAYER", *, layers: dict[str, tuple[int, int]]
    ) -> type[LayerEnum]:
        """Create a new [LayerEnum][kfactory.kcell.LayerEnum] from this KCLayout."""
        return layerenum_from_dict(layers=layers, name=name, kcl=self)

    def dup(self, init_cells: bool = True) -> KCLayout:
        """Create a duplication of the `~KCLayout` object.

        Args:
            init_cells: initialize the all cells in the new KCLayout object

        Returns:
            Copy of itself
        """
        kcl = KCLayout(self.name + "_DUPLICATE")
        kcl.layout.assign(self.layout.dup())
        if init_cells:
            for i, kc in self.kcells.items():
                kcl.kcells[i] = KCell(
                    name=kc.name,
                    kcl=kcl,
                    kdb_cell=kcl.layout.cell(kc.name),
                    ports=kc.ports,
                )
                kcl.kcells[i]._settings = kc.settings.model_copy()
                kcl.kcells[i].info = kc.info.model_copy(
                    update={n: v for n, v in kc.info}
                )
        kcl.rename_function = self.rename_function
        return kcl

    def create_cell(
        self,
        name: str,
        *args: str,
        allow_duplicate: bool = False,
    ) -> kdb.Cell:
        """Create a new cell in the library.

        This shouldn't be called manually.
        The constructor of KCell will call this method.

        Args:
            name: The (initial) name of the cell.
            allow_duplicate: Allow the creation of a cell with the same name which
                already is registered in the Layout.
                This will create a cell with the name `name` + `$1` or `2..n`
                increasing by the number of existing duplicates
            args: additional arguments passed to
                `klayout.db.Layout.create_cell`

        Returns:
            klayout.db.Cell: klayout.db.Cell object created in the Layout

        """
        if allow_duplicate or (self.layout.cell(name) is None):
            # self.kcells[name] = kcell
            return self.layout.create_cell(name, *args)
        else:
            raise ValueError(
                f"Cellname {name} already exists. Please make sure the cellname is"
                " unique or pass `allow_duplicate` when creating the library"
            )

    def delete_cell(self, cell: KCell | int) -> None:
        """Delete a cell in the kcl object."""
        if isinstance(cell, int):
            self.layout.delete_cell(cell)
            del self.kcells[cell]
        else:
            ci = cell.cell_index()
            self.layout.delete_cell(ci)
            del self.kcells[ci]

    def register_cell(self, kcell: KCell, allow_reregister: bool = False) -> None:
        """Register an existing cell in the KCLayout object.

        Args:
            kcell: KCell to be registered in the KCLayout
            allow_reregister: Overwrite the existing KCell registration with this one.
                Doesn't allow name duplication.
        """

        def check_name(other: KCell) -> bool:
            return other._kdb_cell.name == kcell._kdb_cell.name

        if (kcell.cell_index() not in self.kcells) or allow_reregister:
            self.kcells[kcell.cell_index()] = kcell
        else:
            raise ValueError(
                "Cannot register a new cell with a name that already"
                " exists in the library"
            )

    def __getitem__(self, obj: str | int) -> KCell:
        """Retrieve a cell by name(str) or index(int).

        Attrs:
            obj: name of cell or cell_index
        """
        if isinstance(obj, int):
            try:
                return self.kcells[obj]
            except KeyError:
                if self.layout.cell(obj) is None:
                    raise

                kdb_c = self.layout.cell(obj)
                c = KCell(name=kdb_c.name, kcl=self, kdb_cell=self.layout.cell(obj))
                c.get_meta_data()
                return c
        else:
            if self.layout.cell(obj) is not None:
                try:
                    return self.kcells[self.layout.cell(obj).cell_index()]
                except KeyError:
                    kdb_c = self.layout.cell(obj)
                    c = KCell(name=kdb_c.name, kcl=self, kdb_cell=self.layout.cell(obj))
                    c.get_meta_data()
                    return c
            from pprint import pformat

            raise ValueError(
                f"Library doesn't have a KCell named {obj},"
                " available KCells are"
                f"{pformat(sorted([cell.name for cell in self.kcells.values()]))}"
            )

    def read(
        self,
        filename: str | Path,
        options: kdb.LoadLayoutOptions | None = None,
        register_cells: bool = False,
    ) -> kdb.LayerMap:
        """Read a GDS file into the existing Layout.

        Args:
            filename: Path of the GDS file.
            options: KLayout options to load from the GDS. Can determine how merge
                conflicts are handled for example. See
                https://www.klayout.de/doc-qt5/code/class_LoadLayoutOptions.html
            register_cells: If `True` create KCells for all cells in the GDS.
        """
        if register_cells:
            cells = set(self.layout.cells("*"))
        fn = str(Path(filename).expanduser().resolve())
        if options is None:
            lm = self.layout.read(fn)
        else:
            lm = self.layout.read(fn, options)

        if register_cells:
            new_cells = set(self.layout.cells("*")) - cells
            for c in new_cells:
                kc = KCell(kdb_cell=c, kcl=self)
                kc.get_meta_data()

        return lm

    @overload
    def write(self, filename: str | Path) -> None:
        ...

    @overload
    def write(
        self,
        filename: str | Path,
        options: kdb.SaveLayoutOptions,
    ) -> None:
        ...

    @overload
    def write(
        self,
        filename: str | Path,
        options: kdb.SaveLayoutOptions = default_save(),
        set_meta: bool = True,
    ) -> None:
        ...

    def write(
        self,
        filename: str | Path,
        options: kdb.SaveLayoutOptions = default_save(),
        set_meta: bool = True,
    ) -> None:
        """Write a GDS file into the existing Layout.

        Args:
            filename: Path of the GDS file.
            options: KLayout options to load from the GDS. Can determine how merge
                conflicts are handled for example. See
                https://www.klayout.de/doc-qt5/code/class_LoadLayoutOptions.html
            set_meta: Make sure all the cells have their metadata set
        """
        for kcell in self.kcells.values():
            kcell.set_meta_data()
        return self.layout.write(str(filename), options)


def layerenum_from_dict(
    layers: dict[str, tuple[int, int]], name: str = "LAYER", kcl: KCLayout | None = None
) -> type[LayerEnum]:
    if kcl is None:
        kcl = _get_default_kcl()

    def update_namespace(ns: dict[str, Any]) -> None:
        ns.update({"kcl": constant(kcl)})
        ns.update(layers)

    return types.new_class(
        name=name,
        bases=(LayerEnum,),
        kwds={},
        exec_body=update_namespace,
    )


class KCellFactories(UserDict[str, Callable[..., KCell]]):
    def __init__(self, data: dict[str, Callable[..., KCell]]) -> None:
        super().__init__(data)

    def __getattr__(self, name: str) -> Any:
        if name != "data":
            return self.data[name]
        else:
            self.__getattribute__(name)


KCLayout.model_rebuild()
LayerSection.model_rebuild()
LayerEnclosure.model_rebuild()
KCellEnclosure.model_rebuild()
LayerEnclosureModel.model_rebuild()
LayerEnclosureCollection.model_rebuild()
kcl = KCLayout("DEFAULT")
"""Default library object.

Any [KCell][kfactory.kcell.KCell] uses this object unless another one is
specified in the constructor."""


def _get_default_kcl() -> KCLayout:
    """Utility function to get the default kcl object."""
    return kcl


class Port:
    """A port is the photonics equivalent to a pin in electronics.

    In addition to the location and layer
    that defines a pin, a port also contains an orientation and a width.
    This can be fully represented with a transformation, integer and layer_index.


    Attributes:
        name: String to name the port.
        width: The width of the port in dbu.
        trans: Transformation in dbu. If the port can be represented in 90° intervals
            this is the safe way to do so.
        dcplx_trans: Transformation in micrometer. The port will autoconvert between
            trans and dcplx_trans on demand.
        port_type: A string defining the type of the port
        layer: Index of the layer or a LayerEnum that acts like an integer, but can
            contain layer number and datatype
        info: A dictionary with additional info. Not reflected in GDS. Copy will make a
            (shallow) copy of it.
        d: Access port info in micrometer basis such as width and position / angle.
        kcl: Link to the layout this port resides in.
    """

    yaml_tag = "!Port"
    name: str | None
    kcl: KCLayout
    width: int
    layer: int | LayerEnum
    _trans: kdb.Trans | None
    _dcplx_trans: kdb.DCplxTrans | None
    info: Info = Info()
    port_type: str
    d: UMPort

    @overload
    def __init__(
        self,
        *,
        name: str | None = None,
        width: int,
        layer: LayerEnum | int,
        trans: kdb.Trans,
        kcl: KCLayout | None = None,
        port_type: str = "optical",
        info: dict[str, int | float | str] = {},
    ):
        ...

    @overload
    def __init__(
        self,
        *,
        name: str | None = None,
        dwidth: float,
        layer: LayerEnum | int,
        dcplx_trans: kdb.DCplxTrans,
        kcl: KCLayout | None = None,
        port_type: str = "optical",
        info: dict[str, int | float | str] = {},
    ):
        ...

    @overload
    def __init__(
        self,
        *,
        name: str | None = None,
        width: int,
        layer: LayerEnum | int,
        port_type: str = "optical",
        angle: int,
        position: tuple[int, int],
        mirror_x: bool = False,
        kcl: KCLayout | None = None,
        info: dict[str, int | float | str] = {},
    ):
        ...

    @overload
    def __init__(
        self,
        *,
        name: str | None = None,
        dwidth: float,
        layer: LayerEnum | int,
        port_type: str = "optical",
        dangle: float,
        dposition: tuple[float, float],
        mirror_x: bool = False,
        kcl: KCLayout | None = None,
        info: dict[str, int | float | str] = {},
    ):
        ...

    def __init__(
        self,
        *,
        name: str | None = None,
        width: int | None = None,
        dwidth: float | None = None,
        layer: int | None = None,
        port_type: str = "optical",
        trans: kdb.Trans | str | None = None,
        dcplx_trans: kdb.DCplxTrans | str | None = None,
        angle: int | None = None,
        dangle: float | None = None,
        position: tuple[int, int] | None = None,
        dposition: tuple[float, float] | None = None,
        mirror_x: bool = False,
        port: Port | None = None,
        kcl: KCLayout | None = None,
        info: dict[str, int | float | str] = {},
    ):
        """Create a port from dbu or um based units."""
        self.kcl = kcl or _get_default_kcl()
        self.d = UMPort(self)
        self.info = Info(**info)
        if port is not None:
            self.name = port.name if name is None else name

            if port.dcplx_trans.is_complex():
                self.dcplx_trans = port.dcplx_trans
            else:
                self.trans = port.trans

            self.port_type = port.port_type
            self.layer = port.layer
            self.width = port.width
        elif (width is None and dwidth is None) or layer is None:
            raise ValueError("width, layer must be given if the 'port is None'")
        else:
            if trans is not None:
                # self.width = cast(int, width)
                if isinstance(trans, str):
                    self.trans = kdb.Trans.from_s(trans)
                else:
                    self.trans = trans.dup()
                assert width is not None
                self.width = width
                self.port_type = port_type
            elif dcplx_trans is not None:
                if isinstance(dcplx_trans, str):
                    self.dcplx_trans = kdb.DCplxTrans.from_s(dcplx_trans)
                else:
                    self.dcplx_trans = dcplx_trans.dup()
                assert dwidth is not None
                self.d.width = dwidth
                assert self.width * self.kcl.layout.dbu == float(
                    dwidth
                ), "When converting to dbu the width does not match the desired width!"
            elif width is not None:
                assert angle is not None
                assert position is not None
                self.trans = kdb.Trans(angle, mirror_x, *position)
                self.width = width
                self.port_type = port_type
            elif dwidth is not None:
                assert dangle is not None
                assert dposition is not None
                self.dcplx_trans = kdb.DCplxTrans(1, dangle, mirror_x, *dposition)

            assert layer is not None
            self.name = name
            self.layer = layer
            self.port_type = port_type

    @classmethod
    def from_yaml(cls: type[Port], constructor, node) -> Port:  # type: ignore
        """Internal function used by the placer to convert yaml to a Port."""
        d = dict(constructor.construct_pairs(node))
        return cls(**d)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Port):
            if (
                self.width == other.width
                and self._trans == other._trans
                and self._dcplx_trans == other._dcplx_trans
                and self.name == other.name
                and self.layer == other.layer
                and self.port_type == other.port_type
                and self.info == other.info
            ):
                return True
        return False

    def copy(self, trans: kdb.Trans | kdb.DCplxTrans = kdb.Trans.R0) -> Port:
        """Get a copy of a port.

        Args:
            trans: an optional transformation applied to the port to be copied

        Returns:
            port: a copy of the port
        """
        info = self.info.model_dump()
        for name, value in self.info:
            info[name] = value
        if self._trans:
            if isinstance(trans, kdb.Trans):
                _trans = trans * self.trans
                return Port(
                    name=self.name,
                    trans=_trans,
                    layer=self.layer,
                    port_type=self.port_type,
                    width=self.width,
                    kcl=self.kcl,
                    info=info,
                )
            elif not trans.is_complex():
                _trans = trans.s_trans().to_itype(self.kcl.layout.dbu) * self.trans
                return Port(
                    name=self.name,
                    trans=_trans,
                    layer=self.layer,
                    port_type=self.port_type,
                    width=self.width,
                    kcl=self.kcl,
                    info=info,
                )
        if isinstance(trans, kdb.Trans):
            dtrans = kdb.DCplxTrans(trans.to_dtype(self.kcl.layout.dbu))
            _dtrans = dtrans * self.dcplx_trans
        else:
            _dtrans = trans * self.dcplx_trans
        return Port(
            name=self.name,
            dcplx_trans=_dtrans,
            dwidth=self.d.width,
            layer=self.layer,
            kcl=self.kcl,
            port_type=self.port_type,
            info=info,
        )

    @property
    def x(self) -> int:
        """X coordinate of the port in dbu."""
        return self.trans.disp.x

    @x.setter
    def x(self, value: int) -> None:
        if self._trans:
            vec = self._trans.disp
            vec.x = value
            self._trans.disp = vec
        elif self._dcplx_trans:
            vec = self.trans.disp
            vec.x = value
            self._dcplx_trans.disp = vec.to_dtype(self.kcl.layout.dbu)

    @property
    def y(self) -> int:
        """Y coordinate of the port in dbu."""
        return self.trans.disp.y

    @y.setter
    def y(self, value: int) -> None:
        if self._trans:
            vec = self._trans.disp
            vec.y = value
            self._trans.disp = vec
        elif self._dcplx_trans:
            vec = self.trans.disp
            vec.y = value
            self._dcplx_trans.disp = vec.to_dtype(self.kcl.layout.dbu)

    @property
    def trans(self) -> kdb.Trans:
        """Simple Transformation of the Port.

        If this is set with the setter, it will overwrite any transformation or
        dcplx transformation
        """
        return self._trans or self.dcplx_trans.s_trans().to_itype(self.kcl.layout.dbu)

    @trans.setter
    def trans(self, value: kdb.Trans) -> None:
        self._trans = value.dup()
        self._dcplx_trans = None

    @property
    def dcplx_trans(self) -> kdb.DCplxTrans:
        """Complex transformation (µm based).

        If the internal transformation is simple, return a complex copy.

        The setter will set a complex transformation and overwrite the internal
        transformation (set simple to `None` and the complex to the provided value.
        """
        return self._dcplx_trans or kdb.DCplxTrans(
            self.trans.to_dtype(self.kcl.layout.dbu)
        )

    @dcplx_trans.setter
    def dcplx_trans(self, value: kdb.DCplxTrans) -> None:
        if value.is_complex() or value.disp != value.disp.to_itype(
            self.kcl.layout.dbu
        ).to_dtype(self.kcl.layout.dbu):
            self._dcplx_trans = value.dup()
            self._trans = None
        else:
            self._trans = value.dup().s_trans().to_itype(self.kcl.layout.dbu)
            self._dcplx_trans = None

    @property
    def angle(self) -> int:
        """Angle of the transformation.

        In the range of `[0,1,2,3]` which are increments in 90°. Not to be confused
        with `rot` of the transformation which keeps additional info about the
        mirror flag.
        """
        return self.trans.angle

    @angle.setter
    def angle(self, value: int) -> None:
        self._trans = self.trans.dup()
        self._dcplx_trans = None
        self._trans.angle = value

    @property
    def orientation(self) -> float:
        """Returns orientation in degrees for gdsfactory compatibility."""
        return self.dcplx_trans.angle

    @orientation.setter
    def orientation(self, value: float) -> None:
        if not self.dcplx_trans.is_complex() and value in [0, 90, 180, 270]:
            self.trans.angle = int(value / 90)
        else:
            self._dcplx_trans = self.dcplx_trans
            self.dcplx_trans.angle = value

    @property
    def mirror(self) -> bool:
        """Returns `True`/`False` depending on the mirror flag on the transformation."""
        return self.trans.is_mirror()

    @mirror.setter
    def mirror(self, value: bool) -> None:
        """Setter for mirror flag on trans."""
        self._trans = self.trans.dup()
        self._dcplx_trans = None
        self._trans.mirror = value

    def hash(self) -> bytes:
        """Hash of Port."""
        h = sha3_512()
        name = self.name if self.name else ""
        h.update(name.encode("UTF-8"))
        h.update(self.trans.hash().to_bytes(8, "big"))
        h.update(self.width.to_bytes(8, "big"))
        h.update(self.port_type.encode("UTF-8"))
        h.update(self.layer.to_bytes(8, "big"))
        return h.digest()

    def __repr__(self) -> str:
        """String representation of port."""
        ln = self.layer.name if isinstance(self.layer, LayerEnum) else self.layer
        if self._trans:
            return (
                f"Port({'name: ' + self.name if self.name else ''}"
                f", width: {self.width}, trans: {self.trans.to_s()}, layer: "
                f"{ln}, port_type: {self.port_type})"
            )
        else:
            return (
                f"Port({'name: ' + self.name if self.name else ''}"
                f", dwidth: {self.d.width}, trans: {self.dcplx_trans.to_s()}, layer: "
                f"{ln}, port_type: {self.port_type})"
            )


class UMPort:
    """Make the port able to dynamically give um based info."""

    def __init__(self, parent: Port):
        """Constructor, just needs a pointer to the port.

        Args:
            parent: port that this should be attached to
        """
        self.parent = parent

    @property
    def x(self) -> float:
        """X coordinate of the port in um."""
        return self.parent.dcplx_trans.disp.x

    @x.setter
    def x(self, value: float) -> None:
        vec = self.parent.dcplx_trans.disp
        vec.x = value
        if self.parent._trans:
            self.parent._trans.disp = vec.to_itype(self.parent.kcl.layout.dbu)
        elif self.parent._dcplx_trans:
            self.parent._dcplx_trans.disp = vec

    @property
    def y(self) -> float:
        """Y coordinate of the port in um."""
        return self.parent.dcplx_trans.disp.y

    @y.setter
    def y(self, value: float) -> None:
        vec = self.parent.dcplx_trans.disp
        vec.y = value
        if self.parent._trans:
            self.parent._trans.disp = vec.to_itype(self.parent.kcl.layout.dbu)
        elif self.parent._dcplx_trans:
            self.parent._dcplx_trans.disp = vec

    @property
    def position(self) -> tuple[float, float]:
        """Coordinate of the port in um."""
        vec = self.parent.dcplx_trans.disp
        return (vec.x, vec.y)

    @position.setter
    def position(self, pos: tuple[float, float]) -> None:
        if self.parent._trans:
            self.parent._trans.disp = kdb.DVector(*pos).to_itype(
                self.parent.kcl.layout.dbu
            )
        elif self.parent._dcplx_trans:
            self.parent._dcplx_trans.disp = kdb.DVector(*pos)

    @property
    def angle(self) -> float:
        """Angle of the port in degrees."""
        return self.parent.dcplx_trans.angle

    @angle.setter
    def angle(self, value: float) -> None:
        if value in [0, 90, 180, 270]:
            if self.parent._trans:
                self.parent._trans.angle = int(value / 90)
                return

        trans = self.parent.dcplx_trans
        trans.angle = value
        self.parent.dcplx_trans = trans

    @property
    def width(self) -> float:
        """Width of the port in um."""
        return self.parent.width * self.parent.kcl.layout.dbu

    @width.setter
    def width(self, value: float) -> None:
        self.parent.width = int(value / self.parent.kcl.layout.dbu)
        assert self.parent.width * self.parent.kcl.layout.dbu == float(value), (
            "When converting to dbu the width does not match the desired width"
            f"({self.width} / {value})!"
        )

    def __repr__(self) -> str:
        """String representation of port."""
        ln = (
            self.parent.layer.name
            if isinstance(self.parent.layer, LayerEnum)
            else self.parent.layer
        )
        return (
            f"Port({'name: ' + self.parent.name if self.parent.name else ''}"
            f", width: {self.width}, position: {self.position}, angle: {self.angle}"
            f", layer: {ln}, port_type: {self.parent.port_type})"
        )


class UMKCell:
    """Make the port able to dynamically give um based info."""

    def __init__(self, parent: KCell):
        """Constructor, just needs a pointer to the port.

        Args:
            parent: port that this should be attached to
        """
        self.parent = parent

    @property
    def xmin(self) -> float:
        """Returns the x-coordinate of the left edge of the bounding box."""
        return self.parent._kdb_cell.dbbox().left

    @property
    def ymin(self) -> float:
        """Returns the x-coordinate of the left edge of the bounding box."""
        return self.parent._kdb_cell.dbbox().bottom

    @property
    def xmax(self) -> float:
        """Returns the x-coordinate of the left edge of the bounding box."""
        return self.parent._kdb_cell.dbbox().right

    @property
    def ymax(self) -> float:
        """Returns the x-coordinate of the left edge of the bounding box."""
        return self.parent._kdb_cell.dbbox().top

    @overload
    def create_inst(
        self,
        cell: KCell | int,
        *,
        trans: kdb.DTrans | kdb.DCplxTrans | kdb.DVector = kdb.DTrans(),
    ) -> Instance:
        ...

    @overload
    def create_inst(
        self,
        cell: KCell | int,
        *,
        trans: kdb.DTrans | kdb.DCplxTrans | kdb.DVector = kdb.DTrans(),
        a: kdb.DVector,
        b: kdb.DVector,
        na: int = 1,
        nb: int = 1,
    ) -> Instance:
        ...

    def create_inst(
        self,
        cell: KCell | int,
        *,
        trans: kdb.DTrans | kdb.DCplxTrans | kdb.DVector = kdb.DTrans(),
        a: kdb.DVector | None = None,
        b: kdb.DVector | None = None,
        na: int = 1,
        nb: int = 1,
    ) -> Instance:
        """Add an instance of another KCell.

        Args:
            cell: The cell to be added
            trans: The integer transformation applied to the reference
            a: Vector for the array.
                Needs to be in positive X-direction. Usually this is only a
                Vector in x-direction. Some foundries won't allow other Vectors.
            b: Vector for the array.
                Needs to be in positive Y-direction. Usually this is only a
                Vector in x-direction. Some foundries won't allow other Vectors.
            na: Number of elements in direction of `a`
            nb: Number of elements in direction of `b`

        Returns:
            The created instance
        """
        if self.parent._locked:
            raise LockedError(self.parent)
        if isinstance(cell, int):
            ci = cell
        else:
            ci = cell.cell_index()

        if a is None:
            ca = self.parent._kdb_cell.insert(kdb.DCellInstArray(ci, trans))
        else:
            if b is None:
                b = kdb.DVector()
            ca = self.parent._kdb_cell.insert(
                kdb.DCellInstArray(ci, trans, a, b, na, nb)
            )
        inst = Instance(self.parent.kcl, ca)
        self.parent.insts.append(inst)
        return inst


class Instance:
    """An Instance of a KCell.

    An Instance is a reference to a KCell with a transformation.

    Attributes:
        _instance: The internal `kdb.Instance` reference
        ports: Transformed ports of the KCell
        kcl: Pointer to the layout object holding the instance
        d: Helper that allows retrieval of instance information in um
    """

    yaml_tag = "!Instance"
    _instance: kdb.Instance
    kcl: KCLayout
    ports: InstancePorts
    d: UMInstance

    def __init__(self, kcl: KCLayout, instance: kdb.Instance) -> None:
        """Create an instance from a KLayout Instance."""
        self._instance = instance
        self.kcl = kcl
        self.ports = InstancePorts(self)
        self.d = UMInstance(self)

    def __getattr__(self, name):  # type: ignore[no-untyped-def]
        """If we don't have an attribute, get it from the instance."""
        return getattr(self._instance, name)

    @property
    def name(self) -> str | None:
        """Name of instance in GDS."""
        prop = self.property(PROPID.NAME)
        return str(prop) if prop is not None else None

    @name.setter
    def name(self, value: str) -> None:
        self.set_property(PROPID.NAME, value)

    @property
    def cell_index(self) -> int:
        """Get the index of the cell this instance refers to."""
        return self._instance.cell_index

    @cell_index.setter
    def cell_index(self, value: int) -> None:
        self._instance_.cell_index = value

    @property
    def cell(self) -> KCell:
        """Parent KCell  of the Instance."""
        return self.kcl[self.cell_index]

    @cell.setter
    def cell(self, value: KCell) -> None:
        self.cell_index = value.cell_index()

    @property
    def a(self) -> kdb.Vector:
        """Returns the displacement vector for the 'a' axis."""
        return self._instance.a

    @a.setter
    def a(self, vec: kdb.Vector | kdb.DVector) -> None:
        self._instance.a = vec  # type: ignore[assignment]

    @property
    def b(self) -> kdb.Vector:
        """Returns the displacement vector for the 'b' axis."""
        return self._instance.b

    @b.setter
    def b(self, vec: kdb.Vector | kdb.DVector) -> None:
        self._instance.b = vec  # type: ignore[assignment]

    @property
    def cell_inst(self) -> kdb.CellInstArray:
        """Gets the basic CellInstArray object associated with this instance."""
        return self._instance.cell_inst

    @cell_inst.setter
    def cell_inst(self, cell_inst: kdb.CellInstArray | kdb.DCellInstArray) -> None:
        self._instance.cell_inst = cell_inst  # type: ignore[assignment]

    @property
    def cplx_trans(self) -> kdb.ICplxTrans:
        """Gets the complex transformation of the instance.

        Or the first instance in the array.
        """
        return self._instance.cplx_trans

    @cplx_trans.setter
    def cplx_trans(self, trans: kdb.ICplxTrans | kdb.DCplxTrans) -> None:
        self._instance.cplx_trans = trans  # type: ignore[assignment]

    @property
    def dcplx_trans(self) -> kdb.DCplxTrans:
        """Gets the complex transformation of the instance.

        Or the first instance in the array.
        """
        return self._instance.dcplx_trans

    @dcplx_trans.setter
    def dcplx_trans(self, trans: kdb.DCplxTrans) -> None:
        self._instance.dcplx_trans = trans

    @property
    def dtrans(self) -> kdb.DTrans:
        """Gets the complex transformation of the instance.

        Or the first instance in the array.
        """
        return self._instance.dtrans

    @dtrans.setter
    def dtrans(self, trans: kdb.DTrans) -> None:
        self._instance.dtrans = trans

    @property
    def trans(self) -> kdb.Trans:
        """Gets the complex transformation of the instance.

        Or the first instance in the array.
        """
        return self._instance.trans

    @trans.setter
    def trans(self, trans: kdb.Trans | kdb.DTrans) -> None:
        self._instance.trans = trans  # type: ignore[assignment]

    @property
    def na(self) -> int:
        """Returns the displacement vector for the 'a' axis."""
        return self._instance.na

    @na.setter
    def na(self, value: int) -> None:
        self._instance.na = value

    @property
    def nb(self) -> int:
        """Returns the number of instances in the 'b' axis."""
        return self._instance.nb

    @nb.setter
    def nb(self, value: int) -> None:
        self._instance.nb = value

    @property
    def parent_cell(self) -> KCell:
        """Gets the cell this instance is contained in."""
        return self.kcl[self._instance.parent_cell.cell_index()]

    @parent_cell.setter
    def parent_cell(self, cell: KCell | kdb.Cell) -> None:
        if isinstance(cell, KCell):
            self._instance.parent_cell = cell._kdb_cell
        else:
            self._instance.parent_cell = cell

    @property
    def prop_id(self) -> int:
        """Gets the properties ID associated with the instance."""
        return self._instance.prop_id

    @prop_id.setter
    def prop_id(self, value: int) -> None:
        self._instance.prop_id = value

    @property
    def hash(self) -> bytes:
        """Hash the instance."""
        h = sha3_512()
        h.update(self.cell.hash())
        if not self.is_complex():
            h.update(self.trans.hash().to_bytes(8, "big"))
        else:
            h.update(self.dcplx_trans.hash().to_bytes(8, "big"))
        return h.digest()

    @overload
    def connect(
        self,
        port: str | Port | None,
        other: Port,
        *,
        mirror: bool = False,
        allow_width_mismatch: bool = False,
        allow_layer_mismatch: bool = False,
        allow_type_mismatch: bool = False,
    ) -> None:
        ...

    @overload
    def connect(
        self,
        port: str | Port | None,
        other: Instance,
        other_port_name: str | None,
        *,
        mirror: bool = False,
        allow_width_mismatch: bool = False,
        allow_layer_mismatch: bool = False,
        allow_type_mismatch: bool = False,
    ) -> None:
        ...

    def connect(
        self,
        port: str | Port | None,
        other: Instance | Port,
        other_port_name: str | None = None,
        *,
        mirror: bool = False,
        allow_width_mismatch: bool = False,
        allow_layer_mismatch: bool = False,
        allow_type_mismatch: bool = False,
    ) -> None:
        """Align port with name `portname` to a port.

        Function to allow to transform this instance so that a port of this instance is
        connected (same position with 180° turn) to another instance.

        Args:
            port: The name of the port of this instance to be connected, or directly an
                instance port. Can be `None` because port names can be `None`.
            other: The other instance or a port. Skip `other_port_name` if it's a port.
            other_port_name: The name of the other port. Ignored if
                `other` is a port.
            mirror: Instead of applying klayout.db.Trans.R180 as a connection
                transformation, use klayout.db.Trans.M90, which effectively means this
                instance will be mirrored and connected.
            allow_width_mismatch: Skip width check between the ports if set.
            allow_layer_mismatch: Skip layer check between the ports if set.
            allow_type_mismatch: Skip port_type check between the ports if set.
        """
        if isinstance(other, Instance):
            if other_port_name is None:
                raise ValueError(
                    "portname cannot be None if an Instance Object is given. For"
                    "complex connections (non-90 degree and floating point ports) use"
                    "route_cplx instead"
                )
            op = other.ports[other_port_name]
        elif isinstance(other, Port):
            op = other
        else:
            raise ValueError("other_instance must be of type Instance or Port")
        if isinstance(port, Port):
            p = port
        else:
            p = self.cell.ports[port]
        if p.width != op.width and not allow_width_mismatch:
            # The ports are not the same width
            raise PortWidthMismatch(
                self,
                other,
                p,
                op,
            )
        if p.layer != op.layer and not allow_layer_mismatch:
            # The ports are not on the same layer
            raise PortLayerMismatch(self.cell.kcl, self, other, p, op)
        if p.port_type != op.port_type and not allow_type_mismatch:
            raise PortTypeMismatch(self, other, p, op)
        if p._dcplx_trans or op._dcplx_trans:
            dconn_trans = kdb.DCplxTrans.M90 if mirror else kdb.DCplxTrans.R180
            self._instance.dcplx_trans = (
                op.dcplx_trans * dconn_trans * p.dcplx_trans.inverted()
            )
        else:
            conn_trans = kdb.Trans.M90 if mirror else kdb.Trans.R180
            self._instance.trans = op.trans * conn_trans * p.trans.inverted()

    @classmethod
    def to_yaml(cls, representer, node):  # type: ignore[no-untyped-def]
        """Convert the instance to a yaml representation."""
        d = {
            "cellname": node.cell.name,
            "trans": node._trans,
            "dcplx_trans": node._dcplx_trans,
        }
        return representer.represent_mapping(cls.yaml_tag, d)

    @overload
    def movex(self, destination: int, /) -> None:
        ...

    @overload
    def movex(self, origin: int, destination: int) -> None:
        ...

    def movex(self, origin: int, destination: int | None = None) -> None:
        """Move the instance in x-direction in dbu.

        Args:
            origin: reference point to move [dbu]
            destination: move origin so that it will land on this coordinate [dbu]
        """
        if destination is None:
            self.transform(kdb.Trans(origin, 0))
        else:
            self.transform(kdb.Trans(destination - origin, 0))

    @overload
    def movey(self, destination: int, /) -> None:
        ...

    @overload
    def movey(self, origin: int, destination: int) -> None:
        ...

    def movey(self, origin: int, destination: int | None = None) -> None:
        """Move the instance in y-direction in dbu.

        Args:
            origin: reference point to move [dbu]
            destination: move origin so that it will land on this coordinate [dbu]
        """
        if destination is None:
            self.transform(kdb.Trans(0, origin))
        else:
            self.transform(kdb.Trans(0, destination - origin))

    @overload
    def move(self, destination: tuple[int, int], /) -> None:
        ...

    @overload
    def move(self, origin: tuple[int, int], destination: tuple[int, int]) -> None:
        ...

    def move(
        self, origin: tuple[int, int], destination: tuple[int, int] | None = None
    ) -> None:
        """Move the instance in dbu.

        Args:
            origin: reference point to move [dbu]
            destination: move origin so that it will land on this coordinate [dbu]
        """
        if destination is None:
            self.transform(kdb.Trans(*origin))
        else:
            self.transform(
                kdb.Trans(destination[0] - origin[0], destination[1] - origin[1])
            )

    def rotate(self, angle: Literal[0, 1, 2, 3]) -> None:
        """Rotate instance in increments of 90°."""
        self.transform(kdb.Trans(angle, False, 0, 0))

    def __repr__(self) -> str:
        """Return a string representation of the instance."""
        port_names = [p.name for p in self.ports]
        return (
            f"{self.parent_cell.name}: ports {port_names}, {self.kcl[self.cell_index]}"
        )

    def mirror_x(self, x: int = 0) -> None:
        """Mirror the instance at an x-axis."""
        self.transform(kdb.Trans(2, True, 2 * x, 0))

    def mirror_y(self, y: int = 0) -> None:
        """Mirror the instance at an y-axis."""
        self.transform(kdb.Trans(0, True, 0, 2 * y))

    @property
    def xmin(self) -> int:
        """Returns the x-coordinate of the left edge of the bounding box."""
        return self._instance.bbox().left

    @xmin.setter
    def xmin(self, __val: int) -> None:
        """Moves the instance so that the bbox's left x-coordinate."""
        self.transform(kdb.Trans(__val - self.bbox().left, 0))

    @property
    def ymin(self) -> int:
        """Returns the x-coordinate of the left edge of the bounding box."""
        return self._instance.bbox().bottom

    @ymin.setter
    def ymin(self, __val: int) -> None:
        """Moves the instance so that the bbox's left x-coordinate."""
        self.transform(kdb.Trans(0, __val - self._instance.bbox().bottom))

    @property
    def xmax(self) -> int:
        """Returns the x-coordinate of the left edge of the bounding box."""
        return self._instance.bbox().right

    @xmax.setter
    def xmax(self, __val: int) -> None:
        """Moves the instance so that the bbox's left x-coordinate."""
        self.transform(kdb.Trans(__val - self.bbox().right, 0))

    @property
    def ymax(self) -> int:
        """Returns the x-coordinate of the left edge of the bounding box."""
        return self._instance.bbox().top

    @ymax.setter
    def ymax(self, __val: int) -> None:
        """Moves the instance so that the bbox's left x-coordinate."""
        self.transform(kdb.Trans(0, __val - self._instance.bbox().top))


class UMInstance:
    """Make the port able to dynamically give um based info."""

    def __init__(self, parent: Instance):
        """Constructor, just needs a pointer to the port.

        Args:
            parent: port that this should be attached to
        """
        self.parent = parent

    @overload
    def movex(self, destination: float, /) -> None:
        ...

    @overload
    def movex(self, origin: float, destination: float) -> None:
        ...

    def movex(self, origin: float, destination: float | None = None) -> None:
        """Move the instance in x-direction in um.

        Args:
            origin: reference point to move
            destination: move origin so that it will land on this coordinate
        """
        if destination is None:
            self.parent.transform(kdb.DTrans(float(origin), 0.0))
        else:
            self.parent.transform(kdb.DTrans(float(destination - origin), 0.0))

    @overload
    def movey(self, destination: float, /) -> None:
        ...

    @overload
    def movey(self, origin: float, destination: float) -> None:
        ...

    def movey(self, origin: float, destination: float | None = None) -> None:
        """Move the instance in y-direction in um.

        Args:
            origin: reference point to move
            destination: move origin so that it will land on this coordinate
        """
        if destination is None:
            self.parent.transform(kdb.DTrans(0.0, float(origin)))
        else:
            self.parent.transform(kdb.DTrans(0.0, float(destination - origin)))

    def rotate(self, angle: float) -> None:
        """Rotate instance in degrees."""
        self.parent.transform(kdb.DCplxTrans(1, angle, False, 0, 0))

    @overload
    def move(self, destination: tuple[float, float], /) -> None:
        ...

    @overload
    def move(
        self, origin: tuple[float, float], destination: tuple[float, float]
    ) -> None:
        ...

    def move(
        self,
        origin: tuple[float, float],
        destination: tuple[float, float] | None = None,
    ) -> None:
        """Move the instance in dbu.

        Args:
            origin: reference point to move [dbu]
            destination: move origin so that it will land on this coordinate [dbu]
        """
        if destination is None:
            self.parent.transform(kdb.DTrans(float(origin[0]), float(origin[1])))
        else:
            self.parent.transform(
                kdb.DTrans(
                    float(destination[0] - origin[0]), float(destination[1] - origin[1])
                )
            )

    def mirror_x(self, x: float = 0) -> None:
        """Mirror the instance at an x-axis."""
        self.parent.transform(kdb.DTrans(2, True, 2 * x, 0))

    def mirror_y(self, y: float = 0) -> None:
        """Mirror the instance at an y-axis."""
        self.parent.transform(kdb.DTrans(0, True, 0, 2 * y))

    @property
    def xmin(self) -> float:
        """Returns the x-coordinate of the left edge of the bounding box."""
        return self.parent._instance.dbbox().left

    @xmin.setter
    def xmin(self, __val: float) -> None:
        """Moves the instance so that the bbox's left x-coordinate."""
        self.parent.transform(kdb.DTrans(__val - self.parent.dbbox().left, 0))

    @property
    def ymin(self) -> float:
        """Returns the x-coordinate of the left edge of the bounding box."""
        return self.parent._instance.dbbox().bottom

    @ymin.setter
    def ymin(self, __val: float) -> None:
        """Moves the instance so that the bbox's left x-coordinate."""
        self.parent.transform(
            kdb.DTrans(0, __val - self.parent._instance.dbbox().bottom)
        )

    @property
    def xmax(self) -> float:
        """Returns the x-coordinate of the left edge of the bounding box."""
        return self.parent._instance.dbbox().right

    @xmax.setter
    def xmax(self, __val: float) -> None:
        """Moves the instance so that the bbox's left x-coordinate."""
        self.parent.transform(kdb.DTrans(__val - self.parent.dbbox().right, 0))

    @property
    def ymax(self) -> float:
        """Returns the x-coordinate of the left edge of the bounding box."""
        return self.parent._instance.dbbox().top

    @ymax.setter
    def ymax(self, __val: int) -> None:
        """Moves the instance so that the bbox's left x-coordinate."""
        self.parent.transform(kdb.DTrans(0, __val - self.parent._instance.dbbox().top))


class Instances:
    """Holder for instances.

    Allows retrieval by name or index
    """

    def __init__(self) -> None:
        """Constructor."""
        self._insts: list[Instance] = []

    def append(self, inst: Instance) -> None:
        """Append a new instance."""
        self._insts.append(inst)

    def __getitem__(self, key: str | int) -> Instance:
        """Retrieve instance by index or by name."""
        if isinstance(key, int):
            return self._insts[key]

        else:
            return next(filter(lambda inst: inst.name == key, self._insts))

    def __len__(self) -> int:
        """Length of the instances."""
        return self._insts.__len__()

    def __iter__(self) -> Iterator[Instance]:
        """Get instance iterator."""
        return self._insts.__iter__()

    def get_inst_names(self) -> dict[str | None, int]:
        """Get count of names of named instances.

        Not named instances will be added to the `None` key.
        """
        names: dict[str | None, int] = {}
        for inst in self._insts:
            if inst.name in names:
                names[inst.name] += 1
            else:
                names[inst.name] = 1
        return names


class Ports:
    """A collection of ports.

    It is not a traditional dictionary. Elements can be retrieved as in a tradional
    dictionary. But to keep tabs on names etc, the ports are stored as a list

    Attributes:
        _ports: Internal storage of the ports. Normally ports should be retrieved with
            [__getitem__][kfactory.kcell.Ports.__getitem__] or with
            [get_all_named][kfactory.kcell.Ports.get_all_named]
    """

    yaml_tag = "!Ports"
    kcl: KCLayout
    _locked: bool

    def __init__(self, kcl: KCLayout, ports: Iterable[Port] = []) -> None:
        """Constructor."""
        self._ports: list[Port] = list(ports)
        self.kcl = kcl

    def copy(self) -> Ports:
        """Get a copy of each port."""
        return Ports(ports=[p.copy() for p in self._ports], kcl=self.kcl)

    def contains(self, port: Port) -> bool:
        """Check whether a port is already in the list."""
        return port.hash() in [v.hash() for v in self._ports]

    def __iter__(self) -> Iterator[Port]:
        """Iterator, that allows for loops etc to directly access the object."""
        yield from self._ports

    def __contains__(self, port: str | Port) -> bool:
        """Check whether a port is in this port collection."""
        if isinstance(port, Port):
            return port in self._ports
        else:
            for _port in self._ports:
                if _port.name == port:
                    return True
            return False

    def add_port(
        self, port: Port, name: str | None = None, keep_mirror: bool = False
    ) -> Port:
        """Add a port object.

        Args:
            port: The port to add
            name: Overwrite the name of the port
            keep_mirror: Keep the mirror flag from the original port if `True`,
                else set [Port.trans.mirror][kfactory.kcell.Port.trans] (or the complex
                equivalent) to `False`.
        """
        _port = port.copy()
        if not keep_mirror:
            if _port._trans:
                _port._trans.mirror = False
            elif _port._dcplx_trans:
                _port._dcplx_trans.mirror = False
        if name is not None:
            _port.name = name
        self._ports.append(_port)
        return _port

    def add_ports(
        self, ports: Iterable[Port], prefix: str = "", keep_mirror: bool = False
    ) -> None:
        """Append a list of ports."""
        for p in ports:
            name = p.name or ""
            self.add_port(port=p, name=prefix + name, keep_mirror=keep_mirror)

    @overload
    def create_port(
        self,
        *,
        trans: kdb.Trans,
        width: int,
        layer: int,
        name: str | None = None,
        port_type: str = "optical",
    ) -> Port:
        ...

    @overload
    def create_port(
        self,
        *,
        dcplx_trans: kdb.DCplxTrans,
        dwidth: int,
        layer: LayerEnum | int,
        name: str | None = None,
        port_type: str = "optical",
    ) -> Port:
        ...

    @overload
    def create_port(
        self,
        *,
        width: int,
        layer: LayerEnum | int,
        position: tuple[int, int],
        angle: Literal[0, 1, 2, 3],
        name: str | None = None,
        port_type: str = "optical",
    ) -> Port:
        ...

    def create_port(
        self,
        *,
        name: str | None = None,
        width: int | None = None,
        dwidth: float | None = None,
        layer: LayerEnum | int,
        port_type: str = "optical",
        trans: kdb.Trans | None = None,
        dcplx_trans: kdb.DCplxTrans | None = None,
        position: tuple[int, int] | None = None,
        angle: Literal[0, 1, 2, 3] | None = None,
        mirror_x: bool = False,
    ) -> Port:
        """Create a new port in the list.

        Args:
            name: Optional name of port.
            width: Width of the port in dbu. If `trans` is set (or the manual creation
                with `position` and `angle`), this needs to be as well.
            dwidth: Width of the port in um. If `dcplx_trans` is set, this needs to be
                as well.
            layer: Layer index of the port.
            port_type: Type of the port (electrical, optical, etc.)
            trans: Transformation object of the port. [dbu]
            dcplx_trans: Complex transformation for the port.
                Use if a non-90° port is necessary.
            position: Tuple of the position. [dbu]
            angle: Angle in 90° increments. Used for simple/dbu transformations.
            mirror_x: Mirror the transformation of the port.
        """
        if trans is not None:
            assert width is not None
            port = Port(
                name=name,
                trans=trans,
                width=width,
                layer=layer,
                port_type=port_type,
                kcl=self.kcl,
            )
        elif dcplx_trans is not None:
            assert dwidth is not None
            port = Port(
                name=name,
                dwidth=dwidth,
                dcplx_trans=dcplx_trans,
                layer=layer,
                port_type=port_type,
                kcl=self.kcl,
            )
        elif angle is not None and position is not None:
            assert width is not None
            port = Port(
                name=name,
                width=width,
                layer=layer,
                port_type=port_type,
                angle=angle,
                position=position,
                mirror_x=mirror_x,
                kcl=self.kcl,
            )
        else:
            raise ValueError(
                f"You need to define width {width} and trans {trans} or angle {angle}"
                f" and position {position} or dcplx_trans {dcplx_trans}"
                f" and dwidth {dwidth}"
            )

        self._ports.append(port)
        return port

    def get_all_named(self) -> dict[str, Port]:
        """Get all ports in a dictionary with names as keys."""
        return {v.name: v for v in self._ports if v.name is not None}

    def __getitem__(self, key: int | str | None) -> Port:
        """Get a specific port by name."""
        if isinstance(key, int):
            return self._ports[key]
        try:
            return next(filter(lambda port: port.name == key, self._ports))
        except StopIteration:
            raise ValueError(
                f"{key} is not a port. Available ports: {[v.name for v in self._ports]}"
            )

    def hash(self) -> bytes:
        """Get a hash of the port to compare."""
        h = sha3_512()
        for port in sorted(self._ports, key=lambda port: hash(port)):
            h.update(port.name.encode("UTF-8") if port.name else b"")
            if port._trans:
                h.update(port.trans.hash().to_bytes(8, "big"))
            else:
                h.update(port.dcplx_trans.hash().to_bytes(8, "big"))
            h.update(port.width.to_bytes(8, "big"))
            h.update(port.port_type.encode("UTF-8"))

        return h.digest()

    def __repr__(self) -> str:
        """Representation of the Ports as strings."""
        return repr([repr(p) for p in self._ports])

    @classmethod
    def to_yaml(cls, representer, node):  # type: ignore[no-untyped-def]
        """Convert the ports to a yaml representations."""
        return representer.represent_sequence(
            cls.yaml_tag,
            node._ports,
        )

    @classmethod
    def from_yaml(cls: type[Ports], constructor: Any, node: Any) -> Ports:
        """Load Ports from a yaml representation."""
        return cls(constructor.construct_sequence(node))


class InstancePorts:
    """Ports of an instance.

    These act as virtual ports as the positions needs to change if the
    instance changes etc.


    Attributes:
        cell_ports: A pointer to the [`KCell.ports`][kfactory.kcell.KCell.ports]
            of the cell
        instance: A pointer to the Instance related to this.
            This provides a way to dynamically calculate the ports.
    """

    cell_ports: Ports
    instance: Instance

    def __init__(self, instance: Instance) -> None:
        """Creates the virtual ports object.

        Args:
            instance: The related instance
        """
        self.cell_ports = instance.cell.ports
        self.instance = instance

    def __getitem__(self, key: int | str | None) -> Port:
        """Get a port by name."""
        p = self.cell_ports[key]
        if self.instance.is_complex():
            return p.copy(self.instance.dcplx_trans)
        else:
            return p.copy(self.instance.trans)

    def __iter__(self) -> Iterator[Port]:
        """Create a copy of the ports to iterate through."""
        if not self.instance.is_complex():
            yield from (p.copy(self.instance.trans) for p in self.cell_ports)
        else:
            yield from (p.copy(self.instance.dcplx_trans) for p in self.cell_ports)

    def __repr__(self) -> str:
        """String representation.

        Creates a copy and uses the `__repr__` of
        [Ports][kfactory.kcell.Ports.__repr__].
        """
        return repr(self.copy())

    def copy(self) -> Ports:
        """Creates a copy in the form of [Ports][kfactory.kcell.Ports]."""
        if not self.instance.is_complex():
            return Ports(
                kcl=self.instance.kcl,
                ports=[p.copy(self.instance.trans) for p in self.cell_ports._ports],
            )
        else:
            return Ports(
                kcl=self.instance.kcl,
                ports=[
                    p.copy(self.instance.dcplx_trans) for p in self.cell_ports._ports
                ],
            )


@overload
def autocell(_func: Callable[KCellParams, KCell], /) -> Callable[KCellParams, KCell]:
    ...


@overload
def autocell(
    *,
    set_settings: bool = True,
    set_name: bool = True,
) -> Callable[[Callable[KCellParams, KCell]], Callable[KCellParams, KCell]]:
    ...


@config.logger.catch(reraise=True)
def autocell(
    _func: Callable[KCellParams, KCell] | None = None,
    /,
    *,
    set_settings: bool = True,
    set_name: bool = True,
    check_ports: bool = True,
    check_instances: bool = True,
) -> (
    Callable[KCellParams, KCell]
    | Callable[[Callable[KCellParams, KCell]], Callable[KCellParams, KCell]]
):
    """Autoname and validate cells.

    .. deprecated:: 0.7.0
        Use [cell][kfactory.kcell.cell] instead.
        `connect` will be removed in 0.8.0
    """
    config.logger.warning("autocell is deprecated, use cell instead")
    return cell(  # type: ignore[no-any-return, call-overload]
        _func,
        set_settings=set_settings,
        set_name=set_name,
        check_ports=check_ports,
        check_instances=check_instances,
    )


@overload
def cell(_func: Callable[KCellParams, KCell], /) -> Callable[KCellParams, KCell]:
    ...


@overload
def cell(
    *,
    set_settings: bool = True,
    set_name: bool = True,
    check_ports: bool = True,
    check_instances: bool = True,
    snap_ports: bool = True,
) -> Callable[[Callable[KCellParams, KCell]], Callable[KCellParams, KCell]]:
    ...


@config.logger.catch(reraise=True)
def cell(
    _func: Callable[KCellParams, KCell] | None = None,
    /,
    *,
    set_settings: bool = True,
    set_name: bool = True,
    check_ports: bool = True,
    check_instances: bool = True,
    snap_ports: bool = True,
    add_port_layers: bool = True,
) -> (
    Callable[KCellParams, KCell]
    | Callable[[Callable[KCellParams, KCell]], Callable[KCellParams, KCell]]
):
    """Decorator to cache and auto name the celll.

    This will use `functools.cache` to cache the function call.
    Additionally, if enabled this will set the name and from the args/kwargs of the
    function and also paste them into a settings dictionary of the
    [KCell][kfactory.kcell.KCell].

    Args:
        set_settings: Copy the args & kwargs into the settings dictionary
        set_name: Auto create the name of the cell to the functionname plus a
            string created from the args/kwargs
        check_ports: Check whether there are any non-90° ports in the cell and throw a
            warning if there are
        check_instances: Check for any complex instances. A complex instance is a an
            instance that has a magnification != 1 or non-90° rotation.
        snap_ports: Snap the centers of the ports onto the grid (only x/y, not angle).
        add_port_layers: Add special layers of
            [kfactory.KCLayout.netlist_layer_mapping][netlist_layer_mapping] to the
            ports if the port layer is in the mapping.
    """

    def decorator_autocell(
        f: Callable[KCellParams, KCell]
    ) -> Callable[KCellParams, KCell]:
        sig = inspect.signature(f)

        # previously was a KCellCache, but dict should do for most case
        cache: dict[int, Any] = {}

        @functools.wraps(f)
        def wrapper_autocell(
            *args: KCellParams.args, **kwargs: KCellParams.kwargs
        ) -> KCell:
            params: dict[str, KCellParams.args] = {
                p.name: p.default for k, p in sig.parameters.items()
            }
            arg_par = list(sig.parameters.items())[: len(args)]
            for i, (k, v) in enumerate(arg_par):
                params[k] = args[i]
            params.update(kwargs)

            del_parameters: list[str] = []

            for key, value in params.items():
                if isinstance(value, dict):
                    params[key] = dict_to_frozen_set(value)
                if value == inspect.Parameter.empty:
                    del_parameters.append(key)

            for param in del_parameters:
                del params[param]

            @cachetools.cached(cache=cache)
            @functools.wraps(f)
            def wrapped_cell(
                **params: KCellParams.args,
            ) -> KCell:
                for key, value in params.items():
                    if isinstance(value, frozenset):
                        params[key] = frozenset_to_dict(value)
                cell = f(**params)
                dbu = cell.kcl.layout.dbu
                if cell._locked:
                    # If the cell is locked, it comes from a cache (most likely)
                    # and should be copied first
                    cell = cell.dup()
                if set_name:
                    if "self" in params:
                        name = get_cell_name(
                            params["self"].__class__.__name__, **params
                        )
                    else:
                        name = get_cell_name(f.__name__, **params)
                    cell.name = name
                if set_settings:
                    settings = cell.settings.model_dump()
                    if "self" in params:
                        settings["function_name"] = params["self"].__class__.__name__
                    else:
                        settings["function_name"] = f.__name__
                    params.pop("self", None)
                    params.pop("cls", None)
                    settings.update(params)
                    cell._settings = KCellSettings(**settings)
                info = cell.info.model_dump()
                for name, value in cell.info:
                    info[name] = value
                cell.info = Info(**info)
                if check_instances:
                    if any(inst.is_complex() for inst in cell.each_inst()):
                        raise ValueError(
                            "Most foundries will not allow off-grid instances. Please "
                            "flatten them or add check_instances=False to the decorator"
                        )
                if snap_ports:
                    for port in cell.ports:
                        if port._dcplx_trans:
                            dup = port._dcplx_trans.dup()
                            dup.disp = port._dcplx_trans.disp.to_itype(dbu).to_dtype(
                                dbu
                            )
                            port.dcplx_trans = dup
                if add_port_layers:
                    for port in cell.ports:
                        if port.layer in cell.kcl.netlist_layer_mapping:
                            if port._trans:
                                edge = kdb.Edge(
                                    kdb.Point(0, -port.width // 2),
                                    kdb.Point(0, port.width // 2),
                                )
                                cell.shapes(
                                    cell.kcl.netlist_layer_mapping[port.layer]
                                ).insert(port.trans * edge)
                                if port.name:
                                    cell.shapes(
                                        cell.kcl.netlist_layer_mapping[port.layer]
                                    ).insert(kdb.Text(port.name, port.trans))
                            else:
                                dedge = kdb.DEdge(
                                    kdb.DPoint(0, -port.d.width / 2),
                                    kdb.DPoint(0, port.d.width / 2),
                                )
                                cell.shapes(
                                    cell.kcl.netlist_layer_mapping[port.layer]
                                ).insert(port.dcplx_trans * dedge)
                                if port.name:
                                    cell.shapes(
                                        cell.kcl.netlist_layer_mapping[port.layer]
                                    ).insert(
                                        kdb.DText(port.name, port.dcplx_trans.s_trans())
                                    )
                cell._locked = True
                return cell

            return wrapped_cell(**params)

        return wrapper_autocell

    return decorator_autocell if _func is None else decorator_autocell(_func)


def dict_to_frozen_set(d: dict[str, Any]) -> frozenset[tuple[str, Any]]:
    """Convert a `dict` to a `frozenset`."""
    return frozenset(d.items())


def frozenset_to_dict(fs: frozenset[tuple[str, Hashable]]) -> dict[str, Hashable]:
    """Convert `frozenset` to `dict`."""
    return dict(fs)


def dict2name(prefix: str | None = None, **kwargs: dict[str, Any]) -> str:
    """Returns name from a dict."""
    kwargs.pop("self", None)
    label = [prefix] if prefix else []
    for key, value in kwargs.items():
        key = join_first_letters(key)
        label += [f"{key.upper()}{clean_value(value)}"]
    _label = "_".join(label)
    return clean_name(_label)


def get_cell_name(cell_type: str, **kwargs: dict[str, Any]) -> str:
    """Convert a cell to a string."""
    name = cell_type

    if kwargs:
        name += f"_{dict2name(None, **kwargs)}"

    return name


def join_first_letters(name: str) -> str:
    """Join the first letter of a name separated with underscores.

    Example::

        "TL" == join_first_letters("taper_length")
    """
    return "".join([x[0] for x in name.split("_") if x])


def clean_dict(d: dict[str, Any]) -> dict[str, Any]:
    """Cleans dictionary recursively."""
    return {
        k: clean_dict(dict(v)) if isinstance(v, dict) else clean_value(v)
        for k, v in d.items()
    }


def clean_value(
    value: float | np.float64 | dict[Any, Any] | KCell | Callable[..., Any]
) -> str:
    """Makes sure a value is representable in a limited character_space."""
    try:
        if isinstance(value, int):  # integer
            return str(value)
        elif type(value) in [float, np.float64]:  # float
            return f"{value}".replace(".", "p").rstrip("0").rstrip("p")
        elif isinstance(value, list):
            return "_".join(clean_value(v) for v in value)
        elif isinstance(value, tuple):
            return "_".join(clean_value(v) for v in value)
        elif isinstance(value, dict):
            return dict2name(**value)
        elif hasattr(value, "name"):
            return clean_name(value.name)
        elif callable(value) and isinstance(value, functools.partial):
            sig = inspect.signature(value.func)
            args_as_kwargs = dict(zip(sig.parameters.keys(), value.args))
            args_as_kwargs.update(**value.keywords)
            args_as_kwargs = clean_dict(args_as_kwargs)
            # args_as_kwargs.pop("function", None)
            func = value.func
            while hasattr(func, "func"):
                func = func.func
            v = {
                "function": func.__name__,
                "module": func.__module__,
                "settings": args_as_kwargs,
            }
            return clean_value(v)
        elif callable(value):
            return getattr(value, "__name__", value.__class__.__name__)
        else:
            return clean_name(str(value))
    except TypeError:  # use the __str__ method
        return clean_name(str(value))


def clean_name(name: str) -> str:
    r"""Ensures that gds cells are composed of [a-zA-Z0-9_\-].

    FIXME: only a few characters are currently replaced.
        This function has been updated only on case-by-case basis
    """
    replace_map = {
        "=": "",
        ",": "_",
        ")": "",
        "(": "",
        "-": "m",
        ".": "p",
        ":": "_",
        "[": "",
        "]": "",
        " ": "_",
    }
    for k, v in list(replace_map.items()):
        name = name.replace(k, v)
    return name


DEFAULT_TRANS: dict[str, str | int | float | dict[str, str | int | float]] = {
    "x": "E",
    "y": "S",
    "x0": "W",
    "y0": "S",
    "margin": {
        "x": 10000,
        "y": 10000,
        "x0": 0,
        "y0": 0,
    },
    "ref": -2,
}


def update_default_trans(
    new_trans: dict[str, str | int | float | dict[str, str | int | float]]
) -> None:
    """Allows to change the default transformation for reading a yaml file."""
    DEFAULT_TRANS.update(new_trans)


def show(
    gds: str | KCell | Path,
    keep_position: bool = True,
    save_options: kdb.SaveLayoutOptions = default_save(),
) -> None:
    """Show GDS in klayout."""
    import inspect

    delete = False

    # Find the file that calls stack
    try:
        stk = inspect.getouterframes(inspect.currentframe())
        frame = stk[2]
        name = (
            Path(frame.filename).stem + "_" + frame.function
            if frame.function != "<module>"
            else Path(frame.filename).stem
        )
    except Exception:
        try:
            from __main__ import __file__ as mf

            name = mf
        except ImportError:
            name = "shell"

    if isinstance(gds, KCell):
        gds_file: Path | None = None
        spec = importlib.util.find_spec("git")
        if spec is not None:
            import git

            try:
                repo = git.repo.Repo(".", search_parent_directories=True)
            except git.InvalidGitRepositoryError:
                pass
            else:
                wtd = repo.working_tree_dir
                if wtd is not None:
                    root = Path(wtd) / "build/gds"
                    root.mkdir(parents=True, exist_ok=True)
                    tf = root / Path(name).with_suffix(".gds")
                    tf.parent.mkdir(parents=True, exist_ok=True)
                    gds.write(str(tf), save_options)
                    gds_file = tf
                    delete = False
        else:
            config.logger.info(
                "git isn't installed. For better file storage, "
                "please install kfactory[git] or gitpython."
            )
        if not gds_file:
            try:
                from __main__ import __file__ as mf
            except ImportError:
                mf = "shell"
            _mf = "stdin" if mf == "<stdin>" else mf
            tf = Path(gettempdir()) / (name + ".gds")
            tf.parent.mkdir(parents=True, exist_ok=True)
            gds.write(str(tf), save_options)
            gds_file = tf
            delete = True

    elif isinstance(gds, str | Path):
        gds_file = Path(gds).resolve()
    else:
        raise NotImplementedError(f"unknown type {type(gds)} for streaming to KLayout")
    if not gds_file.is_file():
        raise ValueError(f"{gds_file} is not a File")
    config.logger.debug("klive file: {}", gds_file)
    data_dict = {
        "gds": str(gds_file),
        "keep_position": keep_position,
    }
    data = json.dumps(data_dict)
    try:
        conn = socket.create_connection(("127.0.0.1", 8082), timeout=0.5)
        data = data + "\n"
        enc_data = data.encode()
        conn.sendall(enc_data)
        conn.settimeout(5)
    except OSError:
        config.logger.warning("Could not connect to klive server")
    else:
        msg = ""
        try:
            msg = conn.recv(1024).decode("utf-8")
            try:
                jmsg = json.loads(msg)
                match jmsg["type"]:
                    case "open":
                        config.logger.info(
                            "klive v{version}: Opened file '{file}'",
                            version=jmsg["version"],
                            file=jmsg["file"],
                        )
                    case "reload":
                        config.logger.info(
                            "klive v{version}: Reloaded file '{file}'",
                            version=jmsg["version"],
                            file=jmsg["file"],
                        )
            except json.JSONDecodeError:
                config.logger.info(f"Message from klive: {msg}")
        except OSError:
            config.logger.warning("klive didn't send data, closing")
        finally:
            conn.close()

    if delete:
        Path(gds_file).unlink()


def polygon_from_array(array: Iterable[tuple[int, int]]) -> kdb.Polygon:
    """Create a DPolygon from a 2D array-like structure. (dbu version).

    Array-like: `[[x1,y1],[x2,y2],...]`
    """
    return kdb.Polygon([kdb.Point(int(x), int(y)) for (x, y) in array])


def dpolygon_from_array(array: Iterable[tuple[float, float]]) -> kdb.DPolygon:
    """Create a DPolygon from a 2D array-like structure. (um version).

    Array-like: `[[x1,y1],[x2,y2],...]`
    """
    return kdb.DPolygon([kdb.DPoint(int(x), int(y)) for (x, y) in array])


def _check_inst_ports(p1: Port, p2: Port) -> int:
    check_int = 0
    if p1.width != p2.width:
        check_int += 1
    if p1.angle != ((p2.angle + 2) % 4):
        check_int += 2
    if p1.port_type != p2.port_type:
        check_int += 4
    return check_int


def _check_cell_ports(p1: Port, p2: Port) -> int:
    check_int = 0
    if p1.width != p2.width:
        check_int += 1
    if p1.angle != p2.angle:
        check_int += 2
    if p1.port_type != p2.port_type:
        check_int += 4
    return check_int


__all__ = [
    "KCell",
    "Instance",
    "Port",
    "Ports",
    "autocell",
    "cell",
    "kcl",
    "KCLayout",
    "default_save",
    "LayerEnum",
    "KCellParams",
]
