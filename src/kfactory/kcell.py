"""Core module of kfactory.

Defines the [KCell][kfactory.kcell.KCell] providing klayout Cells with Ports
and other convenience functions.

[Instance][kfactory.kcell.Instance] are the kfactory instances used to also acquire
ports and other inf from instances.

"""

from __future__ import annotations

import importlib
import importlib.util
import inspect
import json
import socket
from abc import ABC, abstractmethod
from collections import defaultdict
from collections.abc import (
    Callable,
    ItemsView,
    Iterable,
    Iterator,
    KeysView,
    Mapping,
    Sequence,
    ValuesView,
)
from pathlib import Path
from tempfile import gettempdir
from typing import (
    TYPE_CHECKING,
    Any,
    ClassVar,
    Generic,
    Literal,
    Self,
    TypeAlias,
    overload,
)

import ruamel.yaml
from klayout import __version__ as _klayout_version  # type: ignore[attr-defined]
from pydantic import (
    BaseModel,
    Field,
    PrivateAttr,
)
from ruamel.yaml.constructor import SafeConstructor

from . import kdb, rdb
from .conf import DEFAULT_TRANS, PROPID, CheckInstances, ShowFunction, config, logger
from .cross_section import (
    CrossSection,
    DCrossSection,
    SymmetricalCrossSection,
    TCrossSection,
)
from .exceptions import LockedError, MergeError
from .geometry import DBUGeometricObject, GeometricObject, UMGeometricObject
from .instance import DInstance, Instance, ProtoInstance, ProtoTInstance, VInstance
from .instances import (
    DInstances,
    Instances,
    ProtoInstances,
    ProtoTInstances,
    VInstances,
)
from .layer import LayerEnum
from .merge import MergeDiff
from .netlist import Net, Netlist, NetlistPort, PortArrayRef, PortRef
from .pin import BasePin, DPin, Pin, ProtoPin
from .pins import DPins, Pins, ProtoPins
from .port import (
    BasePort,
    DPort,
    Port,
    PortCheck,
    ProtoPort,
    create_port_error,
    port_check,
    port_polygon,
)
from .ports import DCreatePort, DPorts, ICreatePort, Ports, ProtoPorts
from .serialization import (
    clean_name,
    deserialize_setting,
    serialize_setting,
)
from .settings import Info, KCellSettings, KCellSettingsUnits
from .shapes import VShapes
from .typings import KC_co, MetaData, TBaseCell_co, TUnit
from .utilities import (
    check_cell_ports,
    check_inst_ports,
    instance_port_name,
    load_layout_options,
    save_layout_options,
)

if TYPE_CHECKING:
    from types import ModuleType

    from ruamel.yaml.representer import BaseRepresenter, MappingNode

    from .layout import KCLayout


__all__ = [
    "AnyKCell",
    "AnyTKCell",
    "BaseKCell",
    "CheckInstances",
    "DKCell",
    "DKCells",
    "KCell",
    "KCells",
    "ProtoCells",
    "ProtoKCell",
    "ProtoTKCell",
    "TKCell",
    "TVCell",
    "VKCell",
    "get_cells",
    "show",
]


class BaseKCell(BaseModel, ABC, arbitrary_types_allowed=True):
    """KLayout cell and change its class to KCell.

    A KCell is a dynamic proxy for kdb.Cell. It has all the
    attributes of the official KLayout class. Some attributes have been adjusted
    to return KCell specific sub classes. If the function is listed here in the
    docs, they have been adjusted for KFactory specifically. This object will
    transparently proxy to kdb.Cell. Meaning any attribute not directly
    defined in this class that are available from the KLayout counter part can
    still be accessed. The pure KLayout object can be accessed with
    `kdb_cell`.

    Attributes:
        yaml_tag: Tag for yaml serialization.
        ports: Manages the ports of the cell.
        settings: A dictionary containing settings populated by the
            [cell][kfactory.kcell.cell] decorator.
        info: Dictionary for storing additional info if necessary. This is not
            passed to the GDS and therefore not reversible.
        d: UMKCell object for easy access to the KCell in um units.
        kcl: Library object that is the manager of the KLayout
        boundary: Boundary of the cell.
        insts: List of instances in the cell.
        vinsts: List of virtual instances in the cell.
        size_info: Size information of the cell.
        function_name: Name of the function that created the cell.
    """

    ports: list[BasePort] = Field(default_factory=list)
    pins: list[BasePin] = Field(default_factory=list)
    settings: KCellSettings = Field(default_factory=KCellSettings)
    settings_units: KCellSettingsUnits = Field(default_factory=KCellSettingsUnits)
    vinsts: VInstances
    info: Info
    kcl: KCLayout
    function_name: str | None = None
    basename: str | None = None

    @property
    @abstractmethod
    def locked(self) -> bool:
        """If set the cell shouldn't be modified anymore."""
        ...

    @locked.setter
    @abstractmethod
    def locked(self, value: bool) -> None: ...

    def lock(self) -> None:
        """Lock the cell."""
        self.locked = True

    @property
    @abstractmethod
    def name(self) -> str | None: ...

    @name.setter
    @abstractmethod
    def name(self, value: str) -> None: ...


class ProtoKCell(GeometricObject[TUnit], Generic[TUnit, TBaseCell_co], ABC):
    _base: TBaseCell_co

    @property
    def locked(self) -> bool:
        return self._base.locked

    @locked.setter
    def locked(self, value: bool) -> None:
        self._base.locked = value

    def lock(self) -> None:
        self._base.lock()

    @property
    def name(self) -> str | None:
        return self._base.name

    @name.setter
    def name(self, value: str) -> None:
        self._base.name = value

    @abstractmethod
    def dup(self) -> Self: ...

    @abstractmethod
    def write(
        self,
        filename: str | Path,
        save_options: kdb.SaveLayoutOptions = ...,
        convert_external_cells: bool = ...,
        set_meta_data: bool = ...,
        autoformat_from_file_extension: bool = ...,
    ) -> None: ...

    @property
    def info(self) -> Info:
        return self._base.info

    @info.setter
    def info(self, value: Info) -> None:
        self._base.info = value

    @property
    def settings(self) -> KCellSettings:
        """Settings dictionary set by the [@vcell][kfactory.kcell.vcell] decorator."""
        return self._base.settings

    @settings.setter
    def settings(self, value: KCellSettings) -> None:
        self._base.settings = value

    @property
    def settings_units(self) -> KCellSettingsUnits:
        """Dictionary containing the units of the settings.

        Set by the [@cell][kfactory.kcell.KCLayout.cell] decorator.
        """
        return self._base.settings_units

    @settings_units.setter
    def settings_units(self, value: KCellSettingsUnits) -> None:
        self._base.settings_units = value

    @property
    def function_name(self) -> str | None:
        return self._base.function_name

    @function_name.setter
    def function_name(self, value: str | None) -> None:
        self._base.function_name = value

    @property
    def basename(self) -> str | None:
        return self._base.basename

    @basename.setter
    def basename(self, value: str | None) -> None:
        self._base.basename = value

    @property
    def vinsts(self) -> VInstances:
        return self._base.vinsts

    @property
    def base(self) -> TBaseCell_co:
        return self._base

    @property
    @abstractmethod
    def insts(self) -> ProtoInstances[TUnit, ProtoInstance[TUnit]]: ...

    @abstractmethod
    def shapes(self, layer: int | kdb.LayerInfo) -> kdb.Shapes | VShapes: ...

    @property
    @abstractmethod
    def ports(self) -> ProtoPorts[TUnit]: ...

    @ports.setter
    @abstractmethod
    def ports(self, new_ports: Iterable[ProtoPort[Any]]) -> None: ...

    @property
    @abstractmethod
    def pins(self) -> ProtoPins[TUnit]: ...

    @pins.setter
    @abstractmethod
    def pins(self, new_ports: Iterable[ProtoPin[Any]]) -> None: ...

    def add_port(
        self,
        *,
        port: ProtoPort[Any],
        name: str | None = None,
        keep_mirror: bool = False,
    ) -> ProtoPort[TUnit]:
        """Add an existing port. E.g. from an instance to propagate the port.

        Args:
            port: The port to add.
            name: Overwrite the name of the port
            keep_mirror: Keep the mirror part of the transformation of a port if
                `True`, else set the mirror flag to `False`.
        """
        if self.locked:
            raise LockedError(self)

        return self.ports.add_port(port=port, name=name, keep_mirror=keep_mirror)

    def add_ports(
        self,
        ports: Iterable[ProtoPort[Any]],
        prefix: str = "",
        suffix: str = "",
        keep_mirror: bool = False,
    ) -> None:
        """Add a sequence of ports to the cell.

        Can be useful to add all ports of a instance for example.

        Args:
            ports: list/tuple (anything iterable) of ports.
            prefix: string to add in front of all the port names
            suffix: string to add at the end of all the port names
            keep_mirror: Keep the mirror part of the transformation of a port if
                `True`, else set the mirror flag to `False`.
        """
        if self.locked:
            raise LockedError(self)

        self.ports.add_ports(
            ports=ports, prefix=prefix, suffix=suffix, keep_mirror=keep_mirror
        )

    def layer(self, *args: Any, **kwargs: Any) -> int:
        """Get the layer info, convenience for `klayout.db.Layout.layer`."""
        return self._base.kcl.layout.layer(*args, **kwargs)

    @property
    def factory_name(self) -> str:
        """Return the name under which the factory was registered."""
        factory_name = self._base.basename or self._base.function_name
        if factory_name is not None:
            return factory_name
        raise ValueError(
            f"{self.__class__.__name__} {self.name} has most likely not been registered"
            " automatically as a factory. Therefore it doesn't have an associated name."
        )

    def has_factory_name(self) -> bool:
        return bool(self._base.basename or self._base.function_name)

    def create_vinst(self, cell: AnyKCell) -> VInstance:
        """Insert the KCell as a VInstance into a VKCell or KCell."""
        if self.locked:
            raise LockedError(self)
        vi = VInstance(cell)
        self._base.vinsts.append(vi)
        return vi

    @property
    def kcl(self) -> KCLayout:
        return self._base.kcl

    def __repr__(self) -> str:
        """Return a string representation of the Cell."""
        port_names = [p.name for p in self.ports]
        pin_names = [pin.name for pin in self.pins]
        instances = [inst.name for inst in self.insts]
        return (
            f"{self.__class__.__name__}(name={self.name}, ports={port_names}, "
            f"pins={pin_names}, "
            f"instances={instances}, locked={self.locked}, kcl={self.kcl.name})"
        )


class TKCell(BaseKCell):
    """KLayout cell and change its class to KCell.

    A KCell is a dynamic proxy for kdb.Cell. It has all the
    attributes of the official KLayout class. Some attributes have been adjusted
    to return KCell specific sub classes. If the function is listed here in the
    docs, they have been adjusted for KFactory specifically. This object will
    transparently proxy to kdb.Cell. Meaning any attribute not directly
    defined in this class that are available from the KLayout counter part can
    still be accessed. The pure KLayout object can be accessed with
    `kdb_cell`.

    Attributes:
        kdb_cell: Pure KLayout cell object.
        locked: If set the cell shouldn't be modified anymore.
        function_name: Name of the function that created the cell.
        virtual: If true, the Cell came from a VKCell.
        vtrans: If not None, the cell came from an instance which cannot be snapped
            lossless to the grid. This happens if a was used and the VInstance cannot
            be mapped to the grid without information loss.
    """

    kdb_cell: kdb.Cell
    boundary: kdb.DPolygon | None = None
    lvs_equivalent_ports: list[list[str]] | None = None
    virtual: bool = False
    vtrans: kdb.DCplxTrans | None = None

    def __getattr__(self, name: str) -> Any:
        """If KCell doesn't have an attribute, look in the KLayout Cell."""
        try:
            return super().__getattr__(name)  # type: ignore[misc]
        except Exception:
            return getattr(self.kdb_cell, name)

    @property
    def locked(self) -> bool:
        return self.kdb_cell.is_locked()

    @locked.setter
    def locked(self, value: bool) -> None:
        self.kdb_cell.locked = value

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={self.kdb_cell.name})"

    @property
    def name(self) -> str:
        return self.kdb_cell.name

    @name.setter
    def name(self, value: str) -> None:
        if self.locked:
            raise LockedError(self)
        if (
            value != self.kdb_cell.name
            and value != self.kcl.layout.unique_cell_name(value)
            and not self.kcl.layout.cell(value).is_library_cell()
            and not self.is_library_cell()
        ):
            stack = inspect.stack()
            module = inspect.getmodule(stack[3].frame)
            tkcells = [
                self.kcl.tkcells[cell.cell_index()]
                for cell in self.kcl.layout.cells(value)
                if not cell.is_library_cell()
            ]

            if module is not None and module.__name__ == "kfactory.layout":
                frame_info = stack[5]
                logger.opt(depth=2).error(
                    "Name conflict in "
                    f"{frame_info.frame.f_locals['f'].__code__.co_filename}::"
                    f"{frame_info.frame.f_locals['f'].__name__} at line "
                    f"{frame_info.frame.f_locals['f'].__code__.co_firstlineno}\n"
                    f"Renaming {self.name} (cell_index={self.kdb_cell.cell_index()}) to"
                    f" {value} would cause it to be named the same as:\n"
                    + "\n".join(
                        f" - {tkcell.name} (cell_index={tkcell.kdb_cell.cell_index()}),"
                        f" function_name={tkcell.function_name},"
                        f" basename={tkcell.basename}"
                        for tkcell in tkcells
                    )
                )
                if config.debug_names:
                    raise ValueError(
                        "Name conflict in "
                        f"{frame_info.frame.f_locals['f'].__code__.co_filename}::"
                        f"{frame_info.frame.f_locals['f'].__name__} at line "
                        f"{frame_info.frame.f_locals['f'].__code__.co_firstlineno}\n"
                        f"Renaming {self.name} (cell_index={self.kdb_cell.cell_index()}"
                        f") to {value} would cause it to be named the same as:\n"
                        + "\n".join(
                            f" - {tkcell.name} "
                            f"(cell_index={tkcell.kdb_cell.cell_index()}),"
                            f" function_name={tkcell.function_name},"
                            f" basename={tkcell.basename}"
                            for tkcell in tkcells
                        )
                    )
            else:
                frame_info = stack[3]
                if module is not None:
                    module_name = module.__name__
                    if module_name == "__main__":
                        module_name = frame_info.filename
                    function_name = (
                        "::" + frame_info.function
                        if frame_info.function != "<module>"
                        else ""
                    )
                    logger.opt(depth=3).error(
                        "Name conflict in "
                        f"{module_name}{function_name} at line "
                        f"{frame_info.lineno}\n"
                        f"Renaming {self.name} (cell_index="
                        f"{self.kdb_cell.cell_index()}) to"
                        f" {value} would cause it to be named the same as:\n"
                        + "\n".join(
                            f" - {tkcell.name} "
                            f"(cell_index={tkcell.kdb_cell.cell_index()}),"
                            f" function_name={tkcell.function_name},"
                            f" basename={tkcell.basename}"
                            for tkcell in tkcells
                        )
                    )
                    if config.debug_names:
                        raise ValueError(
                            "Name conflict in "
                            f"{module_name}{function_name} at line "
                            f"{frame_info.lineno}\n"
                            f"Renaming {self.name} (cell_index="
                            f"{self.kdb_cell.cell_index()}) to"
                            f" {value} would cause it to be named the same as:\n"
                            + "\n".join(
                                f" - {tkcell.name} "
                                f"(cell_index={tkcell.kdb_cell.cell_index()}),"
                                f" function_name={tkcell.function_name},"
                                f" basename={tkcell.basename}"
                                for tkcell in tkcells
                            )
                        )
                else:
                    function_name = (
                        "::" + frame_info.function
                        if frame_info.function != "<module>"
                        else ""
                    )
                    logger.opt(depth=3).error(
                        "Name conflict in "
                        f"{frame_info.filename}"
                        f"{function_name} at line {frame_info.lineno}\n"
                        f"Renaming {self.name} (cell_index="
                        f"{self.kdb_cell.cell_index()}) to"
                        f" {value} would cause it to be named the same as:\n"
                        + "\n".join(
                            f" - {tkcell.name} "
                            f"(cell_index={tkcell.kdb_cell.cell_index()}),"
                            f" function_name={tkcell.function_name},"
                            f" basename={tkcell.basename}"
                            for tkcell in tkcells
                        )
                    )
                    if config.debug_names:
                        raise ValueError(
                            "Name conflict in "
                            f"{frame_info.filename}"
                            f"{function_name} at line {frame_info.lineno}\n"
                            f"Renaming {self.name} (cell_index="
                            f"{self.kdb_cell.cell_index()}) to"
                            f" {value} would cause it to be named the same as:\n"
                            + "\n".join(
                                f" - {tkcell.name} "
                                f"(cell_index={tkcell.kdb_cell.cell_index()}),"
                                f" function_name={tkcell.function_name},"
                                f" basename={tkcell.basename}"
                                for tkcell in tkcells
                            )
                        )

        self.kdb_cell.name = value


class TVCell(BaseKCell):
    _locked: bool = PrivateAttr(default=False)
    shapes: dict[int, VShapes] = Field(default_factory=dict)
    _name: str | None = PrivateAttr(default=None)

    @property
    def locked(self) -> bool:
        return self._locked

    @locked.setter
    def locked(self, value: bool) -> None:
        self._locked = value

    @property
    def name(self) -> str | None:
        return self._name

    @name.setter
    def name(self, value: str) -> None:
        self._name = value


class ProtoTKCell(ProtoKCell[TUnit, TKCell], Generic[TUnit], ABC):
    def __init__(
        self,
        *,
        base: TKCell | None = None,
        name: str | None = None,
        kcl: KCLayout | None = None,
        kdb_cell: kdb.Cell | None = None,
        ports: Iterable[ProtoPort[Any]] | None = None,
        pins: Iterable[ProtoPin[Any]] | None = None,
        info: dict[str, Any] | None = None,
        settings: dict[str, Any] | None = None,
    ) -> None:
        if base is not None:
            self._base = base
            return

        from .layout import get_default_kcl, kcls

        kcl_ = kcl or get_default_kcl()

        if name is None:
            name_ = "Unnamed_!" if kdb_cell is None else kdb_cell.name
        else:
            name_ = name
            if kdb_cell is not None:
                kdb_cell.name = name
        kdb_cell_ = kdb_cell or kcl_.create_cell(name_)
        if name_ == "Unnamed_!":
            kdb_cell_.name = f"Unnamed_{kdb_cell_.cell_index()}"

        self._base = TKCell(
            kcl=kcl_,
            info=Info(**(info or {})),
            settings=KCellSettings(**(settings or {})),
            kdb_cell=kdb_cell_,
            ports=[port.base for port in ports] if ports else [],
            pins=[pin.base for pin in pins] if pins else [],
            vinsts=VInstances(),
        )
        if kdb_cell_.is_library_cell():
            if ports or info or settings or pins:
                raise ValueError(
                    "If a TKCell is created from a library cell (separate PDK/layout), "
                    "ports, info, settings, and pins must not be set."
                    f"Cell {kdb_cell_.name} in {kcl_.name}: {ports=}, {pins=}, {info=},"
                    f" {settings=}"
                )
            kcls[kdb_cell_.library().name()][
                kdb_cell_.library_cell_index()
            ].set_meta_data()
            self.get_meta_data()
        self.kcl.register_cell(self)

    @abstractmethod
    def __getitem__(self, key: int | str | None) -> ProtoPort[TUnit]:
        """Returns port from instance."""
        ...

    @property
    def name(self) -> str:
        return self._base.name

    @name.setter
    def name(self, value: str) -> None:
        self._base.name = value

    @property
    def virtual(self) -> bool:
        return self._base.virtual

    @property
    @property
    @abstractmethod
    def pins(self) -> ProtoPins[TUnit]: ...

    @pins.setter
    @abstractmethod
    def pins(self, new_pins: Iterable[ProtoPin[Any]]) -> None: ...

    def __hash__(self) -> int:
        """Hash the KCell."""
        return hash((self._base.kcl.library.name(), self._base.kdb_cell.cell_index()))

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, ProtoTKCell):
            return False
        return self._base is other._base

    @property
    def prop_id(self) -> int:
        """Gets the properties ID associated with the cell."""
        return self._base.kdb_cell.prop_id

    @prop_id.setter
    def prop_id(self, value: int) -> None:
        if self.locked:
            raise LockedError(self)
        self._base.kdb_cell.prop_id = value

    @property
    def ghost_cell(self) -> bool:
        """Returns a value indicating whether the cell is a "ghost cell"."""
        return self._base.kdb_cell.ghost_cell

    @ghost_cell.setter
    def ghost_cell(self, value: bool) -> None:
        if self.locked:
            raise LockedError(self)
        self._base.kdb_cell.ghost_cell = value

    def __getattr__(self, name: str) -> Any:
        """If KCell doesn't have an attribute, look in the KLayout Cell."""
        try:
            return super().__getattr__(name)  # type: ignore[misc]
        except Exception:
            return getattr(self._base, name)

    def cell_index(self) -> int:
        """Gets the cell index."""
        return self._base.kdb_cell.cell_index()

    def shapes(self, layer: int | kdb.LayerInfo) -> kdb.Shapes:
        return self._base.kdb_cell.shapes(layer)

    @property
    @abstractmethod
    def insts(self) -> ProtoTInstances[TUnit]: ...

    def __copy__(self) -> Self:
        """Enables use of `copy.copy` and `copy.deep_copy`."""
        return self.dup()

    def dup(self, new_name: str | None = None) -> Self:
        """Copy the full cell.

        Sets `_locked` to `False`

        Returns:
            cell: Exact copy of the current cell.
                The name will have `$1` as duplicate names are not allowed
        """
        kdb_copy = self._kdb_copy()
        if new_name:
            if new_name == self.name:
                if config.debug_names:
                    raise ValueError(
                        "When duplicating a Cell, avoid giving the duplicate the same "
                        "name, as this can cause naming conflicts and may render the "
                        "GDS/OASIS file unwritable. If you're using a @cell function, "
                        "ensure that the function has a different name than the one "
                        "being called."
                    )
                logger.error(
                    "When duplicating a Cell, avoid giving the duplicate the same "
                    "name, as this can cause naming conflicts and may render the "
                    "GDS/OASIS file unwritable. If you're using a @cell function, "
                    "ensure that the function has a different name than the one being "
                    "called."
                )
            kdb_copy.name = new_name

        c = self.__class__(kcl=self.kcl, kdb_cell=kdb_copy)
        c.ports = self.ports.copy()

        if self.pins:
            port_mapping = {id(p): i for i, p in enumerate(c.ports)}
            c._base.pins = [
                BasePin(
                    name=p.name,
                    kcl=self.kcl,
                    ports=[c.base.ports[port_mapping[id(port)]] for port in p.ports],
                    pin_type=p.pin_type,
                    info=p.info,
                )
                for p in self._base.pins
            ]

        c._base.settings = self.settings.model_copy()
        c._base.info = self.info.model_copy()
        c._base.vinsts = self._base.vinsts.copy()

        return c

    @property
    def kdb_cell(self) -> kdb.Cell:
        return self._base.kdb_cell

    def destroyed(self) -> bool:
        return self._base.kdb_cell._destroyed()

    @property
    def boundary(self) -> kdb.DPolygon | None:
        return self._base.boundary

    @boundary.setter
    def boundary(self, boundary: kdb.DPolygon | None) -> None:
        self._base.boundary = boundary

    def to_itype(self) -> KCell:
        """Convert the kcell to a dbu kcell."""
        return KCell(base=self._base)

    def to_dtype(self) -> DKCell:
        """Convert the kcell to a um kcell."""
        return DKCell(base=self._base)

    def show(
        self,
        lyrdb: rdb.ReportDatabase | Path | str | None = None,
        l2n: kdb.LayoutToNetlist | Path | str | None = None,
        keep_position: bool = True,
        save_options: kdb.SaveLayoutOptions | None = None,
        use_libraries: bool = True,
        library_save_options: kdb.SaveLayoutOptions | None = None,
        technology: str | None = None,
    ) -> None:
        """Stream the gds to klive.

        Will create a temporary file of the gds and load it in KLayout via klive
        """
        if save_options is None:
            save_options = save_layout_options()
        if library_save_options is None:
            library_save_options = save_layout_options()
        show_f: ShowFunction = config.show_function or show

        kwargs: dict[str, Any] = {}
        if technology is not None:
            kwargs["technology"] = technology
        if l2n is not None:
            kwargs["l2n"] = l2n
        if lyrdb is not None:
            kwargs["lyrdb"] = lyrdb

        show_f(
            self,
            keep_position=keep_position,
            save_options=save_options,
            use_libraries=use_libraries,
            library_save_options=library_save_options,
            **kwargs,
        )

    def plot(
        self,
        lyrdb: Path | str | None = None,
        display_type: Literal["image", "widget"] | None = None,
    ) -> None:
        """Display cell.

        Args:
            lyrdb: Path to the lyrdb file.
            display_type: Type of display. Options are "widget" or "image".

        """
        from .widgets.interactive import display_kcell

        display_kcell(self, lyrdb=lyrdb, display_type=display_type)

    def _ipython_display_(self) -> None:
        """Display a cell in a Jupyter Cell.

        Usage: Pass the kcell variable as an argument in the cell at the end
        """
        self.plot()

    def delete(self) -> None:
        """Delete the cell."""
        ci = self.cell_index()
        self._base.kdb_cell.locked = False
        self.kcl.delete_cell(ci)

    @abstractmethod
    def add_port(
        self,
        *,
        port: ProtoPort[Any],
        name: str | None = None,
        keep_mirror: bool = False,
    ) -> ProtoPort[Any]: ...

    @abstractmethod
    def create_pin(
        self,
        *,
        ports: Iterable[ProtoPort[Any]],
        name: str | None = None,
        pin_type: str = "DC",
        info: dict[str, int | float | str] | None = None,
    ) -> ProtoPin[TUnit]: ...

    @overload
    @abstractmethod
    def create_inst(
        self: ProtoTKCell[int],
        cell: ProtoTKCell[Any] | int,
        trans: kdb.Trans | kdb.Vector | kdb.ICplxTrans | None = None,
        *,
        a: kdb.Vector | None = None,
        b: kdb.Vector | None = None,
        na: int = 1,
        nb: int = 1,
        libcell_as_static: bool = False,
        static_name_separator: str = "__",
    ) -> Instance: ...

    @overload
    @abstractmethod
    def create_inst(
        self: ProtoTKCell[float],
        cell: ProtoTKCell[Any] | int,
        trans: kdb.DTrans | kdb.DVector | kdb.DCplxTrans | None = None,
        *,
        a: kdb.DVector | None = None,
        b: kdb.DVector | None = None,
        na: int = 1,
        nb: int = 1,
        libcell_as_static: bool = False,
        static_name_separator: str = "__",
    ) -> DInstance: ...

    @abstractmethod
    def create_inst(
        self,
        cell: ProtoTKCell[Any] | int,
        trans: kdb.Trans
        | kdb.Vector
        | kdb.ICplxTrans
        | kdb.DTrans
        | kdb.DVector
        | kdb.DCplxTrans
        | None = None,
        *,
        a: kdb.Vector | kdb.DVector | None = None,
        b: kdb.Vector | kdb.DVector | None = None,
        na: int = 1,
        nb: int = 1,
        libcell_as_static: bool = False,
        static_name_separator: str = "__",
    ) -> Instance | DInstance: ...

    def _get_ci(
        self,
        cell: ProtoTKCell[Any],
        libcell_as_static: bool = False,
        static_name_separator: str = "__",
    ) -> int:
        if cell.layout() == self.layout():
            return cell.cell_index()
        assert cell.layout().library() is not None
        lib_ci = self.kcl.layout.add_lib_cell(cell.kcl.library, cell.cell_index())
        if lib_ci not in self.kcl.tkcells:
            kcell = self.kcl[lib_ci]
            kcell.basename = cell.basename
            kcell.function_name = cell.function_name
        if libcell_as_static:
            cell.set_meta_data()
            ci = self.kcl.layout.convert_cell_to_static(lib_ci)
            if ci not in self.kcl.tkcells:
                kcell = self.kcl[ci]
                kcell.copy_meta_info(cell.kdb_cell)
                kcell.name = cell.kcl.name + static_name_separator + cell.name
                if cell.kcl.dbu != self.kcl.dbu:
                    for port, lib_port in zip(kcell.ports, cell.ports, strict=False):
                        port.cross_section = CrossSection(
                            kcl=kcell.kcl,
                            base=cell.kcl.get_symmetrical_cross_section(
                                lib_port.cross_section.base.to_dtype(cell.kcl)
                            ),
                        )
            return ci
        return lib_ci

    def icreate_inst(
        self,
        cell: ProtoTKCell[Any] | int,
        trans: kdb.Trans | kdb.Vector | kdb.ICplxTrans | None = None,
        *,
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
        if trans is None:
            trans = kdb.Trans()
        if isinstance(cell, int):
            ci = cell
        else:
            ci = self._get_ci(cell, libcell_as_static, static_name_separator)

        if a is None:
            inst = self._base.kdb_cell.insert(kdb.CellInstArray(ci, trans))
        else:
            if b is None:
                b = kdb.Vector()
            inst = self._base.kdb_cell.insert(
                kdb.CellInstArray(ci, trans, a, b, na, nb)
            )
        return Instance(kcl=self.kcl, instance=inst)

    def dcreate_inst(
        self,
        cell: ProtoTKCell[Any] | int,
        trans: kdb.DTrans | kdb.DVector | kdb.DCplxTrans | None = None,
        *,
        a: kdb.DVector | None = None,
        b: kdb.DVector | None = None,
        na: int = 1,
        nb: int = 1,
        libcell_as_static: bool = False,
        static_name_separator: str = "__",
    ) -> DInstance:
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
        if trans is None:
            trans = kdb.DTrans()
        if isinstance(cell, int):
            ci = cell
        else:
            ci = self._get_ci(cell, libcell_as_static, static_name_separator)

        if a is None:
            inst = self._base.kdb_cell.insert(kdb.DCellInstArray(ci, trans))
        else:
            if b is None:
                b = kdb.DVector()
            inst = self._base.kdb_cell.insert(
                kdb.DCellInstArray(ci, trans, a, b, na, nb)
            )
        return DInstance(kcl=self.kcl, instance=inst)

    def _kdb_copy(self) -> kdb.Cell:
        return self._base.kdb_cell.dup()

    def layout(self) -> kdb.Layout:
        return self._base.kdb_cell.layout()

    def library(self) -> kdb.Library:
        return self._base.kdb_cell.library()

    @abstractmethod
    def __lshift__(self, cell: AnyTKCell) -> ProtoTInstance[TUnit]: ...

    def auto_rename_ports(self, rename_func: Callable[..., None] | None = None) -> None:
        """Rename the ports with the schema angle -> "NSWE" and sort by x and y.

        Args:
            rename_func: Function that takes Iterable[Port] and renames them.
                This can of course contain a filter and only rename some of the ports
        """
        if self.locked:
            raise LockedError(self)
        if rename_func is None:
            self.kcl.rename_function(self.ports)
        else:
            rename_func(self.ports)

    def flatten(self, merge: bool = True) -> None:
        """Flatten the cell.

        Args:
            merge: Merge the shapes on all layers.
        """
        if self.locked:
            raise LockedError(self)
        for vinst in self._base.vinsts:
            vinst.insert_into_flat(self)
        self._base.vinsts = VInstances()
        self._base.kdb_cell.flatten(False)

        if merge:
            for layer in self.kcl.layout.layer_indexes():
                reg = kdb.Region(self.shapes(layer))
                reg = reg.merge()
                texts = kdb.Texts(self.shapes(layer))
                self.kdb_cell.clear(layer)
                self.shapes(layer).insert(reg)
                self.shapes(layer).insert(texts)

    def convert_to_static(self, recursive: bool = True) -> None:
        """Convert the KCell to a static cell if it is pdk KCell."""
        if self.library().name() == self.kcl.name:
            raise ValueError(f"KCell {self.qname()} is already a static KCell.")
        from .layout import kcls

        lib_cell = kcls[self.library().name()][self.library_cell_index()]
        lib_cell.set_meta_data()
        kdb_cell = self.kcl.layout_cell(
            self.kcl.convert_cell_to_static(self.cell_index())
        )
        assert kdb_cell is not None
        kdb_cell.name = self.qname()
        ci_ = kdb_cell.cell_index()
        old_kdb_cell = self._base.kdb_cell
        kdb_cell.copy_meta_info(lib_cell.kdb_cell)
        self.get_meta_data()

        if recursive:
            for ci in self.called_cells():
                kc = self.kcl[ci]
                if kc.is_library_cell():
                    kc.convert_to_static(recursive=recursive)

        self._base.kdb_cell = kdb_cell
        for ci in old_kdb_cell.caller_cells():
            c = self.kcl.layout_cell(ci)
            assert c is not None
            it = kdb.RecursiveInstanceIterator(self.kcl.layout, c)
            it.targets = [old_kdb_cell.cell_index()]
            it.max_depth = 0
            insts = [instit.current_inst_element().inst() for instit in it.each()]
            locked = c.locked
            c.locked = False
            for inst in insts:
                ca = inst.cell_inst
                ca.cell_index = ci_
                c.replace(inst, ca)
            c.locked = locked

        self.kcl.layout.delete_cell(old_kdb_cell.cell_index())

    def draw_ports(self) -> None:
        """Draw all the ports on their respective layer."""
        locked = self._base.kdb_cell.locked
        self._base.kdb_cell.locked = False
        polys: dict[int, kdb.Region] = {}

        for port in Ports(kcl=self.kcl, bases=self.ports.bases):
            w = port.width

            if w in polys:
                poly = polys[w]
            else:
                poly = kdb.Region()
                poly.insert(
                    kdb.Polygon(
                        [
                            kdb.Point(0, int(-w // 2)),
                            kdb.Point(0, int(w // 2)),
                            kdb.Point(int(w // 2), 0),
                        ]
                    )
                )
                if w > 20:  # noqa: PLR2004
                    poly -= kdb.Region(
                        kdb.Polygon(
                            [
                                kdb.Point(int(w // 20), 0),
                                kdb.Point(
                                    int(w // 20), int(-w // 2 + int(w * 2.5 // 20))
                                ),
                                kdb.Point(int(w // 2 - int(w * 1.41 / 20)), 0),
                            ]
                        )
                    )
            polys[w] = poly
            if port.base.trans:
                self.shapes(port.layer).insert(poly.transformed(port.trans))
                self.shapes(port.layer).insert(kdb.Text(port.name or "", port.trans))
            else:
                self.shapes(port.layer).insert(poly, port.dcplx_trans)
                self.shapes(port.layer).insert(kdb.Text(port.name or "", port.trans))
        self._base.kdb_cell.locked = locked

    def write(
        self,
        filename: str | Path,
        save_options: kdb.SaveLayoutOptions | None = None,
        convert_external_cells: bool = False,
        set_meta_data: bool = True,
        autoformat_from_file_extension: bool = True,
    ) -> None:
        """Write a KCell to a GDS.

        See [KCLayout.write][kfactory.kcell.KCLayout.write] for more info.
        """
        if save_options is None:
            save_options = save_layout_options()
        self.insert_vinsts()
        match set_meta_data, convert_external_cells:
            case True, True:
                self.kcl.set_meta_data()
                for kcell in (self.kcl[ci] for ci in self.called_cells()):
                    if not kcell._destroyed():
                        if kcell.is_library_cell():
                            kcell.convert_to_static(recursive=True)
                        kcell.set_meta_data()
                if self.is_library_cell():
                    self.convert_to_static(recursive=True)
                self.set_meta_data()
            case True, False:
                self.kcl.set_meta_data()
                for kcell in (self.kcl[ci] for ci in self.called_cells()):
                    if not kcell._destroyed():
                        kcell.set_meta_data()
                self.set_meta_data()
            case False, True:
                for kcell in (self.kcl[ci] for ci in self.called_cells()):
                    if kcell.is_library_cell() and not kcell._destroyed():
                        kcell.convert_to_static(recursive=True)
                if self.is_library_cell():
                    self.convert_to_static(recursive=True)
            case _:
                ...

        for kci in set(self._base.kdb_cell.called_cells()) & self.kcl.tkcells.keys():
            kc = self.kcl[kci]
            kc.insert_vinsts()

        filename = str(filename)
        if autoformat_from_file_extension:
            save_options.set_format_from_filename(filename)
        self._base.kdb_cell.write(filename, save_options)

    def read(
        self,
        filename: str | Path,
        options: kdb.LoadLayoutOptions | None = None,
        register_cells: bool = False,
        test_merge: bool = True,
        update_kcl_meta_data: Literal["overwrite", "skip", "drop"] = "drop",
        meta_format: Literal["v1", "v2", "v3"] | None = None,
    ) -> list[int]:
        """Read a GDS file into the existing KCell.

        Any existing meta info (KCell.info and KCell.settings) will be overwritten if
        a KCell already exists. Instead of overwriting the cells, they can also be
        loaded into new cells by using the corresponding cell_conflict_resolution.

        Layout meta infos are ignored from the loaded layout.

        Args:
            filename: Path of the GDS file.
            options: KLayout options to load from the GDS. Can determine how merge
                conflicts are handled for example. See
                https://www.klayout.de/doc-qt5/code/class_LoadLayoutOptions.html
            register_cells: If `True` create KCells for all cells in the GDS.
            test_merge: Check the layouts first whether they are compatible
                (no differences).
            update_kcl_meta_data: How to treat loaded KCLayout info.
                overwrite: overwrite existing info entries
                skip: keep existing info values
                drop: don't add any new info
            meta_format: How to read KCell metainfo from the gds. `v1` had stored port
                transformations as strings, never versions have them stored and loaded
                in their native KLayout formats.
        """
        # see: wait for KLayout update https://github.com/KLayout/klayout/issues/1609
        logger.critical(
            "KLayout <=0.28.15 (last update 2024-02-02) cannot read LayoutMetaInfo on"
            " 'Cell.read'. kfactory uses these extensively for ports, info, and "
            "settings. Therefore proceed at your own risk."
        )
        if meta_format is None:
            meta_format = config.meta_format
        if options is None:
            options = load_layout_options()
        fn = str(Path(filename).expanduser().resolve())
        if test_merge and (
            options.cell_conflict_resolution
            != kdb.LoadLayoutOptions.CellConflictResolution.RenameCell
        ):
            self.kcl.set_meta_data()
            for kcell in self.kcl.kcells.values():
                kcell.set_meta_data()
            layout_b = kdb.Layout()
            layout_b.read(fn, options)
            layout_a = self.kcl.layout.dup()
            layout_a.delete_cell(layout_a.cell(self.name).cell_index())
            diff = MergeDiff(
                layout_a=layout_a,
                layout_b=layout_b,
                name_a=self.name,
                name_b=Path(filename).stem,
            )
            diff.compare()
            if diff.dbu_differs:
                raise MergeError("Layouts' DBU differ. Check the log for more info.")
            if diff.diff_xor.cells() > 0 or diff.layout_meta_diff:
                diff_kcl = KCLayout(self.name + "_XOR")
                diff_kcl.layout.assign(diff.diff_xor)
                show(diff_kcl)

                err_msg = (
                    f"Layout {self.name} cannot merge with layout "
                    f"{Path(filename).stem} safely. See the error messages "
                    f"or check with KLayout."
                )

                if diff.layout_meta_diff:
                    yaml = ruamel.yaml.YAML(typ=["rt", "string"])
                    err_msg += (
                        "\nLayout Meta Diff:\n```\n"
                        + yaml.dumps(dict(diff.layout_meta_diff))
                        + "\n```"
                    )
                if diff.cells_meta_diff:
                    yaml = ruamel.yaml.YAML(typ=["rt", "string"])
                    err_msg += (
                        "\nLayout Meta Diff:\n```\n"
                        + yaml.dumps(dict(diff.cells_meta_diff))
                        + "\n```"
                    )

                raise MergeError(err_msg)

        cell_ids = self._base.kdb_cell.read(fn, options)
        info, settings = self.kcl.get_meta_data()

        match update_kcl_meta_data:
            case "overwrite":
                for k, v in info.items():
                    self.kcl.info[k] = v
            case "skip":
                info_ = self.info.model_dump()

                info.update(info_)
                self.kcl.info = Info(**info)
            case "drop":
                ...
        meta_format = settings.get("meta_format") or meta_format

        if register_cells:
            new_cis = set(cell_ids)

            for c in new_cis:
                kc = self.kcl[c]
                kc.get_meta_data(meta_format=meta_format)
        else:
            cis = self.kcl.tkcells.keys()
            new_cis = set(cell_ids)

            for c in new_cis & cis:
                kc = self.kcl[c]
                kc.get_meta_data(meta_format=meta_format)

        self.get_meta_data(meta_format=meta_format)

        return cell_ids

    def each_inst(self) -> Iterator[Instance]:
        """Iterates over all child instances (which may actually be instance arrays)."""
        yield from (
            Instance(self.kcl, inst) for inst in self._base.kdb_cell.each_inst()
        )

    def each_overlapping_inst(self, b: kdb.Box | kdb.DBox) -> Iterator[Instance]:
        """Gets the instances overlapping the given rectangle."""
        yield from (
            Instance(self.kcl, inst)
            for inst in self._base.kdb_cell.each_overlapping_inst(b)
        )

    def each_touching_inst(self, b: kdb.Box | kdb.DBox) -> Iterator[Instance]:
        """Gets the instances overlapping the given rectangle."""
        yield from (
            Instance(self.kcl, inst)
            for inst in self._base.kdb_cell.each_touching_inst(b)
        )

    @overload
    def insert(
        self, inst: Instance | kdb.CellInstArray | kdb.DCellInstArray
    ) -> Instance: ...

    @overload
    def insert(
        self, inst: kdb.CellInstArray | kdb.DCellInstArray, property_id: int
    ) -> Instance: ...

    def insert(
        self,
        inst: Instance | kdb.CellInstArray | kdb.DCellInstArray,
        property_id: int | None = None,
    ) -> Instance:
        """Inserts a cell instance given by another reference."""
        if self.locked:
            raise LockedError(self)
        if isinstance(inst, Instance):
            return Instance(self.kcl, self._base.kdb_cell.insert(inst.instance))
        if not property_id:
            return Instance(self.kcl, self._base.kdb_cell.insert(inst))
        assert isinstance(inst, kdb.CellInstArray | kdb.DCellInstArray)
        return Instance(self.kcl, self._base.kdb_cell.insert(inst, property_id))

    @overload
    def transform(
        self,
        inst: kdb.Instance,
        trans: kdb.Trans | kdb.DTrans | kdb.ICplxTrans | kdb.DCplxTrans,
        /,
        *,
        transform_ports: bool = True,
    ) -> Instance: ...

    @overload
    def transform(
        self,
        trans: kdb.Trans | kdb.DTrans | kdb.ICplxTrans | kdb.DCplxTrans,
        /,
        *,
        transform_ports: bool = True,
    ) -> None: ...

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
        transform_ports: bool = True,
    ) -> Instance | None:
        """Transforms the instance or cell with the transformation given."""
        if trans:
            return Instance(
                self.kcl,
                self._base.kdb_cell.transform(
                    inst_or_trans,  # type: ignore[arg-type]
                    trans,  # type: ignore[arg-type]
                ),
            )
        self._base.kdb_cell.transform(inst_or_trans)  # type:ignore[arg-type]
        if transform_ports:
            if isinstance(inst_or_trans, kdb.DTrans):
                inst_or_trans = kdb.DCplxTrans(inst_or_trans)
            elif isinstance(inst_or_trans, kdb.ICplxTrans):
                inst_or_trans = kdb.DCplxTrans(inst_or_trans, self.kcl.dbu)

            if isinstance(inst_or_trans, kdb.Trans):
                for port in self.ports:
                    port.trans = inst_or_trans * port.trans
            else:
                for port in self.ports:
                    port.dcplx_trans = inst_or_trans * port.dcplx_trans  # type: ignore[operator]
        return None

    def set_meta_data(self) -> None:
        """Set metadata of the Cell.

        Currently, ports, settings and info will be set.
        """
        self.clear_meta_info()
        if not self.is_library_cell():
            for i, port in enumerate(self.ports):
                if port.base.trans is not None:
                    meta_info: dict[str, MetaData] = {
                        "name": port.name,
                        "cross_section": port.cross_section.name,
                        "trans": port.base.trans,
                        "port_type": port.port_type,
                        "info": port.info.model_dump(),
                    }

                    self.add_meta_info(
                        kdb.LayoutMetaInfo(f"kfactory:ports:{i}", meta_info, None, True)
                    )
                else:
                    meta_info = {
                        "name": port.name,
                        "cross_section": port.cross_section.name,
                        "dcplx_trans": port.dcplx_trans,
                        "port_type": port.port_type,
                        "info": port.info.model_dump(),
                    }

                    self.add_meta_info(
                        kdb.LayoutMetaInfo(f"kfactory:ports:{i}", meta_info, None, True)
                    )
            for i, pin in enumerate(self.pins):
                meta_info = {
                    "name": pin.name,
                    "pin_type": pin.pin_type,
                    "info": pin.info.model_dump(),
                    "ports": [self.base.ports.index(port.base) for port in pin.ports],
                }
                self.add_meta_info(
                    kdb.LayoutMetaInfo(f"kfactory:pins:{i}", meta_info, None, True)
                )
            settings = self.settings.model_dump()
            if settings:
                self.add_meta_info(
                    kdb.LayoutMetaInfo("kfactory:settings", settings, None, True)
                )
            info = self.info.model_dump()
            if info:
                self.add_meta_info(
                    kdb.LayoutMetaInfo("kfactory:info", info, None, True)
                )
            settings_units = self.settings_units.model_dump()
            if settings_units:
                self.add_meta_info(
                    kdb.LayoutMetaInfo(
                        "kfactory:settings_units",
                        settings_units,
                        None,
                        True,
                    )
                )

            if self.function_name is not None:
                self.add_meta_info(
                    kdb.LayoutMetaInfo(
                        "kfactory:function_name", self.function_name, None, True
                    )
                )

            if self.basename is not None:
                self.add_meta_info(
                    kdb.LayoutMetaInfo("kfactory:basename", self.basename, None, True)
                )

    def get_meta_data(
        self,
        meta_format: Literal["v1", "v2", "v3"] | None = None,
    ) -> None:
        """Read metadata from the KLayout Layout object."""
        if meta_format is None:
            meta_format = config.meta_format
        port_dict: dict[str, Any] = {}
        pin_dict: dict[str, Any] = {}
        ports: dict[str, BasePort] = {}
        settings: dict[str, MetaData] = {}
        settings_units: dict[str, str] = {}
        from .layout import kcls

        match meta_format:
            case "v3":
                self.ports.clear()
                meta_iter = (
                    kcls[self.library().name()][
                        self.library_cell_index()
                    ].each_meta_info()
                    if self.is_library_cell()
                    else self.each_meta_info()
                )
                for meta in meta_iter:
                    if meta.name.startswith("kfactory:ports"):
                        i = meta.name.removeprefix("kfactory:ports:")
                        port_dict[i] = meta.value
                    elif meta.name.startswith("kfactory:pins"):
                        i = meta.name.removeprefix("kfactory:pins:")
                        pin_dict[i] = meta.value
                    elif meta.name.startswith("kfactory:info"):
                        self._base.info = Info(**meta.value)
                    elif meta.name.startswith("kfactory:settings_units"):
                        self._base.settings_units = KCellSettingsUnits(**meta.value)
                    elif meta.name.startswith("kfactory:settings"):
                        self._base.settings = KCellSettings(**meta.value)
                    elif meta.name == "kfactory:function_name":
                        self._base.function_name = meta.value
                    elif meta.name == "kfactory:basename":
                        self._base.basename = meta.value

                if not self.is_library_cell():
                    for index in sorted(port_dict.keys()):
                        v = port_dict[index]
                        trans_: kdb.Trans | None = v.get("trans")
                        if trans_ is not None:
                            ports[index] = self.create_port(
                                name=v.get("name"),
                                trans=trans_,
                                cross_section=self.kcl.get_symmetrical_cross_section(
                                    v["cross_section"]
                                ),
                                port_type=v["port_type"],
                                info=v["info"],
                            )
                        else:
                            ports[index] = self.create_port(
                                name=v.get("name"),
                                dcplx_trans=v["dcplx_trans"],
                                cross_section=self.kcl.get_symmetrical_cross_section(
                                    v["cross_section"]
                                ),
                                port_type=v["port_type"],
                                info=v["info"],
                            )
                    for index in sorted(pin_dict.keys()):
                        v = pin_dict[index]
                        self.create_pin(
                            name=v.get("name"),
                            ports=[ports[port_index] for port_index in v["ports"]],  # type: ignore[misc]
                            pin_type=v["pin_type"],
                            info=v["info"],
                        )
                else:
                    lib_name = self.library().name()
                    for index in sorted(port_dict.keys()):
                        v = port_dict[index]
                        trans_ = v.get("trans")
                        lib_kcl = kcls[lib_name]
                        cs = self.kcl.get_symmetrical_cross_section(
                            lib_kcl.get_symmetrical_cross_section(
                                v["cross_section"]
                            ).to_dtype(lib_kcl)
                        )

                        if trans_ is not None:
                            ports[index] = self.create_port(
                                name=v.get("name"),
                                trans=trans_.to_dtype(lib_kcl.dbu).to_itype(
                                    self.kcl.dbu
                                ),
                                cross_section=cs,
                                port_type=v["port_type"],
                            )
                        else:
                            ports[index] = self.create_port(
                                name=v.get("name"),
                                dcplx_trans=v["dcplx_trans"],
                                cross_section=cs,
                                port_type=v["port_type"],
                            )
                    for index in sorted(pin_dict):
                        v = pin_dict[index]
                        self.create_pin(
                            name=v.get("name"),
                            ports=[ports[str(port_index)] for port_index in v["ports"]],  # type: ignore[misc]
                            pin_type=v["pin_type"],
                            info=v["info"],
                        )

            case "v2":
                for meta in self.each_meta_info():
                    if meta.name.startswith("kfactory:ports"):
                        i, type_ = meta.name.removeprefix("kfactory:ports:").split(
                            ":", 1
                        )
                        if i not in port_dict:
                            port_dict[i] = {}
                        if not type_.startswith("info"):
                            port_dict[i][type_] = meta.value
                        else:
                            if "info" not in port_dict[i]:
                                port_dict[i]["info"] = {}
                            port_dict[i]["info"][type_.removeprefix("info:")] = (
                                meta.value
                            )
                    elif meta.name.startswith("kfactory:info"):
                        setattr(
                            self.info,
                            meta.name.removeprefix("kfactory:info:"),
                            meta.value,
                        )
                    elif meta.name.startswith("kfactory:settings_units"):
                        settings_units[
                            meta.name.removeprefix("kfactory:settings_units:")
                        ] = meta.value
                    elif meta.name.startswith("kfactory:settings"):
                        settings[meta.name.removeprefix("kfactory:settings:")] = (
                            meta.value
                        )

                    elif meta.name == "kfactory:function_name":
                        self.function_name = meta.value

                    elif meta.name == "kfactory:basename":
                        self.basename = meta.value

                self.settings = KCellSettings(**settings)
                self.settings_units = KCellSettingsUnits(**settings_units)

                self.ports.clear()
                for index in sorted(port_dict.keys()):
                    d = port_dict[index]
                    name = d.get("name", None)
                    port_type = d["port_type"]
                    layer_info = d["layer"]
                    width = d["width"]
                    trans = d.get("trans", None)
                    dcplx_trans = d.get("dcplx_trans", None)
                    port = Port(
                        name=name,
                        width=width,
                        layer_info=layer_info,
                        trans=kdb.Trans.R0,
                        kcl=self.kcl,
                        port_type=port_type,
                        info=d.get("info", {}),
                    )
                    if trans:
                        port.trans = trans
                    elif dcplx_trans:
                        port.dcplx_trans = dcplx_trans

                    self.add_port(port=port, keep_mirror=True)
            case "v1":
                for meta in self.each_meta_info():
                    if meta.name.startswith("kfactory:ports"):
                        i, type_ = meta.name.removeprefix("kfactory:ports:").split(
                            ":", 1
                        )
                        if i not in port_dict:
                            port_dict[i] = {}
                        if not type_.startswith("info"):
                            port_dict[i][type_] = meta.value
                        else:
                            if "info" not in port_dict[i]:
                                port_dict[i]["info"] = {}
                            port_dict[i]["info"][type_.removeprefix("info:")] = (
                                meta.value
                            )
                    elif meta.name.startswith("kfactory:info"):
                        setattr(
                            self.info,
                            meta.name.removeprefix("kfactory:info:"),
                            meta.value,
                        )
                    elif meta.name.startswith("kfactory:settings_units"):
                        settings_units[
                            meta.name.removeprefix("kfactory:settings_units:")
                        ] = meta.value
                    elif meta.name.startswith("kfactory:settings"):
                        settings[meta.name.removeprefix("kfactory:settings:")] = (
                            meta.value
                        )

                    elif meta.name == "kfactory:function_name":
                        self.function_name = meta.value

                    elif meta.name == "kfactory:basename":
                        self.basename = meta.value

                self.settings = KCellSettings(**settings)
                self.settings_units = KCellSettingsUnits(**settings_units)

                self.ports.clear()
                for index in sorted(port_dict.keys()):
                    d = port_dict[index]
                    name = d.get("name", None)
                    port_type = d["port_type"]
                    layer = d["layer"]
                    width = d["width"]
                    trans = d.get("trans", None)
                    dcplx_trans = d.get("dcplx_trans", None)
                    port = Port(
                        name=name,
                        width=width,
                        layer_info=layer,
                        trans=kdb.Trans.R0,
                        kcl=self.kcl,
                        port_type=port_type,
                        info=d.get("info", {}),
                    )
                    if trans:
                        port.trans = kdb.Trans.from_s(trans)
                    elif dcplx_trans:
                        port.dcplx_trans = kdb.DCplxTrans.from_s(dcplx_trans)

                    self.add_port(port=port, keep_mirror=True)

    def ibbox(self, layer: int | None = None) -> kdb.Box:
        if layer is None:
            return self._base.kdb_cell.bbox()
        return self._base.kdb_cell.bbox(layer)

    def dbbox(self, layer: int | None = None) -> kdb.DBox:
        if layer is None:
            return self._base.kdb_cell.dbbox()
        return self._base.kdb_cell.dbbox(layer)

    def l2n(self, port_types: Iterable[str] = ("optical",)) -> kdb.LayoutToNetlist:
        """Generate a LayoutToNetlist object from the port types.

        Args:
            port_types: The port types to consider for the netlist extraction.
        Returns:
            LayoutToNetlist extracted from instance and cell port positions.
        """
        logger.warning(
            "l2n is deprecated and will be removed in 2.0. Please use `l2n_ports`"
            " instead."
        )
        return self.l2n_ports(port_types=port_types)

    def l2n_ports(
        self,
        port_types: Iterable[str] = ("optical",),
        exclude_purposes: list[str] | None = None,
        ignore_unnamed: bool = False,
        allow_width_mismatch: bool = False,
    ) -> kdb.LayoutToNetlist:
        """Generate a LayoutToNetlist object from the port types.

        Uses kfactory ports as a basis for extraction.

        Args:
            port_types: The port types to consider for the netlist extraction.
            exclude_purpose: List of purposes, if an instance has that purpose, it will
                be ignored.
            ignore_unnamed: Ignore any instance without `.name` set.
        Returns:
            LayoutToNetlist extracted from instance and cell port positions.
        """
        l2n = kdb.LayoutToNetlist(self.name, self.kcl.dbu)
        l2n.extract_netlist()
        il = l2n.internal_layout()
        il.assign(self.kcl.layout)

        called_kcells = [self.kcl[ci] for ci in self.called_cells()]
        called_kcells.sort(key=lambda c: c.hierarchy_levels())

        for c in called_kcells:
            c.circuit(
                l2n,
                port_types=port_types,
                exclude_purposes=exclude_purposes,
                ignore_unnamed=ignore_unnamed,
                allow_width_mismatch=allow_width_mismatch,
            )
        self.circuit(
            l2n,
            port_types=port_types,
            exclude_purposes=exclude_purposes,
            ignore_unnamed=ignore_unnamed,
            allow_width_mismatch=allow_width_mismatch,
        )
        return l2n

    def l2n_elec(
        self,
        mark_port_types: Iterable[str] = ("electrical", "RF", "DC"),
        connectivity: Sequence[
            tuple[kdb.LayerInfo]
            | tuple[kdb.LayerInfo, kdb.LayerInfo]
            | tuple[kdb.LayerInfo, kdb.LayerInfo, kdb.LayerInfo],
        ]
        | None = None,
        port_mapping: dict[str, dict[str | None, str]] | None = None,
    ) -> kdb.LayoutToNetlist:
        """Generate a LayoutToNetlist object from the port types.

        Uses electrical connectivity for extraction.

        Args:
            port_types: The port types to consider for the netlist extraction.
        Returns:
            LayoutToNetlist extracted from electrical connectivity.
        """
        connectivity = connectivity or self.kcl.connectivity
        ly_elec = self.kcl.layout.dup()

        port_mapping = port_mapping or {}
        c_elec: kdb.Cell = ly_elec.cell(self.name)

        for ci in [c_elec.cell_index(), *c_elec.called_cells()]:
            c_ = self.kcl[ci]
            c = ly_elec.cell(c_.name)
            assert c_.name == c.name
            c.locked = False
            mapping = port_mapping.get(
                c_.name,
                port_mapping.get(c_.factory_name, {}) if c_.has_factory_name() else {},
            )
            for port in c_.ports:
                port_name = mapping.get(port.name, port.name)
                if (
                    port_name == port.name
                    and port.port_type in mark_port_types
                    and port.name is not None
                ):
                    c.shapes(port.layer_info).insert(
                        kdb.Text(string=port.name, trans=port.trans)
                    )

        l2n: kdb.LayoutToNetlist = kdb.LayoutToNetlist(
            kdb.RecursiveShapeIterator(
                ly_elec,
                ly_elec.cell(self.name),
                [],
            )
        )

        connectivity = connectivity or self.kcl.connectivity

        layers: dict[int, kdb.Region] = {}

        layer_infos = {
            ly_elec.get_info(ly_elec.layer(info))
            for layer_set in connectivity
            for info in layer_set
        }
        for info in layer_infos:
            l_ = l2n.make_layer(ly_elec.layer(info), info.name)
            layers[ly_elec.layer(info)] = l_
            l2n.connect(l_)
        for conn in connectivity:
            old_layer = layers[ly_elec.layer(conn[0])]

            for layer in conn[1:]:
                li = layers[ly_elec.layer(layer)]
                l2n.connect(old_layer, li)
                old_layer = li
        l2n.extract_netlist()
        l2n.check_extraction_errors()

        return l2n

    def netlist(
        self,
        port_types: Iterable[str] = ("optical",),
        mark_port_types: Iterable[str] = ("electrical", "RF", "DC"),
        connectivity: Sequence[
            tuple[kdb.LayerInfo, kdb.LayerInfo]
            | tuple[kdb.LayerInfo, kdb.LayerInfo, kdb.LayerInfo]
        ]
        | None = None,
        *,
        equivalent_ports: dict[str, list[list[str]]] | None = None,
        ignore_unnamed: bool = False,
        exclude_purposes: list[str] | None = None,
        allow_width_mismatch: bool = False,
    ) -> dict[str, Netlist]:
        if equivalent_ports is None:
            equivalent_ports = {}
            for ci in [self.cell_index(), *self.called_cells()]:
                c_ = self.kcl[ci]
                eqps: list[list[str]] | None = c_.lvs_equivalent_ports or None
                if c_.has_factory_name():
                    if c_.virtual:
                        eqps = c_.kcl.virtual_factories[
                            c_.factory_name
                        ].lvs_equivalent_ports
                    elif c_.is_library_cell():
                        from .layout import kcls

                        eqps = (
                            kcls[c_.library().name()]
                            .factories[c_.factory_name]
                            .lvs_equivalent_ports
                        )
                    else:
                        eqps = c_.kcl.factories[c_.factory_name].lvs_equivalent_ports
                if eqps is not None:
                    equivalent_ports[c_.name] = eqps
        port_mapping: dict[str, dict[str | None, str]] = defaultdict(dict)
        for cell_name, list_of_port_lists in equivalent_ports.items():
            for port_list in list_of_port_lists:
                if port_list:
                    p1 = port_list[0]
                    for port in port_list:
                        port_mapping[cell_name][port] = p1
        l2n_elec = self.l2n_elec(
            mark_port_types=mark_port_types,
            connectivity=connectivity,
            port_mapping=port_mapping,
        )
        l2n_opt = self.l2n_ports(
            port_types=port_types,
            exclude_purposes=exclude_purposes,
            ignore_unnamed=ignore_unnamed,
            allow_width_mismatch=allow_width_mismatch,
        )

        netlists: dict[str, Netlist] = {}

        for cell_name, eqps in equivalent_ports.items():
            for eqp_list in eqps:
                if eqp_list:
                    p1 = eqp_list[0]
                    for p in eqp_list:
                        port_mapping[cell_name][p] = p1

        for ci in [self.cell_index(), *self.called_cells()]:
            c_ = self.kcl[ci]
            name = c_.name

            nl = _get_netlist(
                c=c_,
                l2n_opt=l2n_opt,
                l2n_elec=l2n_elec,
                ignore_unnamed=ignore_unnamed,
                exclude_purposes=exclude_purposes,
            )
            if equivalent_ports.get(c_.name) is not None:
                nl = nl.lvs_equivalent(
                    cell_name=c_.name,
                    equivalent_ports=equivalent_ports,
                    port_mapping=port_mapping,
                )
            netlists[name] = nl
        return netlists

    def circuit(
        self,
        l2n: kdb.LayoutToNetlist,
        port_types: Iterable[str] = ("optical",),
        ignore_unnamed: bool = False,
        exclude_purposes: list[str] | None = None,
        allow_width_mismatch: bool = False,
    ) -> None:
        """Create the circuit of the KCell in the given netlist."""
        netlist = l2n.netlist()

        def port_filter(num_port: tuple[int, ProtoPort[Any]]) -> bool:
            return num_port[1].port_type in port_types

        circ = kdb.Circuit()
        circ.name = self.name
        circ.cell_index = self.cell_index()
        circ.boundary = self.boundary or kdb.DPolygon(self.dbbox())

        inst_ports: dict[
            str,
            dict[str, list[tuple[int, int, Instance, Port, kdb.SubCircuit]]],
        ] = {}
        cell_ports: dict[str, dict[str, list[tuple[int, Port]]]] = {}

        # sort the cell's ports by position and layer

        portnames: set[str] = set()

        for i, port in filter(
            port_filter, enumerate(Ports(kcl=self.kcl, bases=self.ports.bases))
        ):
            trans = port.trans.dup()
            trans.angle %= 2
            trans.mirror = False
            layer_info = self.kcl.layout.get_info(port.layer)
            layer = f"{layer_info.layer}_{layer_info.datatype}"

            if port.name in portnames:
                raise ValueError(
                    "Netlist extraction is not possible with"
                    f" colliding port names. Duplicate name: {port.name}"
                )

            v = trans.disp
            h = f"{v.x}_{v.y}"
            if h not in cell_ports:
                cell_ports[h] = {}
            if layer not in cell_ports[h]:
                cell_ports[h][layer] = []
            cell_ports[h][layer].append((i, port))

            if port.name:
                portnames.add(port.name)

        # create nets and connect pins for each cell_port
        for layer_dict in cell_ports.values():
            for _ports in layer_dict.values():
                net = circ.create_net(
                    "-".join(_port[1].name or f"{_port[0]}" for _port in _ports)
                )
                for i, port in _ports:
                    pin = circ.create_pin(port.name or f"{i}")
                    circ.connect_pin(pin, net)

        # sort the ports of all instances by position and layer
        for i, inst in enumerate(self.insts):
            name = inst.name
            subc = circ.create_subcircuit(
                netlist.circuit_by_cell_index(inst.cell_index), name
            )
            subc.trans = inst.dcplx_trans

            for j, port in filter(
                port_filter,
                enumerate(Ports(kcl=self.kcl, bases=[p.base for p in inst.ports])),
            ):
                trans = port.trans.dup()
                trans.angle %= 2
                trans.mirror = False
                v = trans.disp
                h = f"{v.x}_{v.y}"
                layer_info = self.kcl.layout.get_info(port.layer)
                layer = f"{layer_info.layer}_{layer_info.datatype}"
                if h not in inst_ports:
                    inst_ports[h] = {}
                if layer not in inst_ports[h]:
                    inst_ports[h][layer] = []
                inst_ports[h][layer].append(
                    (
                        i,
                        j,
                        Instance(kcl=self.kcl, instance=inst.instance),
                        port,
                        subc,
                    )
                )

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
                        "Multiple instance "
                        f"{[instance_port_name(p[2], p[3]) for p in ports]}"
                        f"ports connected to the cell port {cellports[0]}"
                        " this is currently not supported and most likely a bug"
                    )

                    inst_port = ports[0]
                    port = inst_port[3]
                    if allow_width_mismatch:
                        port_check(
                            cellports[0][1], port, PortCheck.port_type + PortCheck.layer
                        )
                    else:
                        port_check(cellports[0][1], port, PortCheck.all_overlap)
                    subc = inst_port[4]
                    pin = subc.circuit_ref().pin_by_name(port.name or str(inst_port[1]))
                    net = circ.net_by_name(cellports[0][1].name or f"{cellports[0][0]}")
                    assert pin is not None
                    assert net is not None
                    subc.connect_pin(pin, net)
                else:
                    # connect instance ports to each other
                    name = "-".join(
                        [
                            (inst.name or str(i)) + "_" + (port.name or str(j))
                            for i, j, inst, port, _ in ports
                        ]
                    )

                    net = circ.create_net(name)
                    assert len(ports) <= 2, (  # noqa: PLR2004
                        "Optical connection with more than two ports are not supported "
                        f"{[_port[3] for _port in ports]}"
                    )
                    if len(ports) == 2:  # noqa: PLR2004
                        if allow_width_mismatch:
                            port_check(
                                ports[0][3],
                                ports[1][3],
                                PortCheck.layer
                                + PortCheck.port_type
                                + PortCheck.opposite,
                            )
                        else:
                            port_check(ports[0][3], ports[1][3], PortCheck.all_opposite)
                        for _, j, _, port, subc in ports:
                            subc.connect_pin(
                                subc.circuit_ref().pin_by_name(port.name or str(j)), net
                            )

        del_subcs: list[kdb.SubCircuit] = []
        if ignore_unnamed:
            del_subcs = [
                circ.subcircuit_by_name(inst.name)
                for inst in self.insts
                if not inst.is_named()
            ]
        if exclude_purposes:
            del_subcs.extend(
                circ.subcircuit_by_name(inst.name)
                for inst in self.insts
                if inst.purpose in exclude_purposes
            )

        for subc in del_subcs:
            nets: list[kdb.Net] = []
            for net in circ.each_net():
                for sc_pin in net.each_subcircuit_pin():
                    if sc_pin.subcircuit().id() == subc.id():
                        nets.append(net)
                        break

            if nets:
                target_net = nets[0]
                for net in nets[1:]:
                    spinrefs = [
                        (spin.pin(), spin.subcircuit())
                        for spin in net.each_subcircuit_pin()
                    ]
                    for pin, _subc in spinrefs:
                        _subc.disconnect_pin(pin)
                        if _subc not in del_subcs:
                            _subc.connect_pin(pin, target_net)
                    net_pins = [pinref.pin() for pinref in net.each_pin()]
                    for pin in net_pins:
                        circ.disconnect_pin(pin)
                        circ.connect_pin(pin, target_net)
                    circ.remove_net(net)
        for subc in del_subcs:
            circ.remove_subcircuit(subc)

        netlist.add(circ)

    def connectivity_check(
        self,
        port_types: list[str] | None = None,
        layers: list[int] | None = None,
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
        if layers is None:
            layers = []
        if port_types is None:
            port_types = []
        db_: rdb.ReportDatabase = db or rdb.ReportDatabase(
            f"Connectivity Check {self.name}"
        )
        assert isinstance(db_, rdb.ReportDatabase)
        if recursive:
            cc = self.called_cells()
            for c in self.kcl.each_cell_bottom_up():
                if c in cc:
                    self.kcl[c].connectivity_check(
                        port_types=port_types,
                        db=db_,
                        recursive=False,
                        add_cell_ports=add_cell_ports,
                        layers=layers,
                    )
        db_cell = db_.create_cell(self.name)
        cell_ports: dict[int, dict[tuple[float, float], list[ProtoPort[Any]]]] = {}
        layer_cats: dict[int, rdb.RdbCategory] = {}

        def layer_cat(layer: int) -> rdb.RdbCategory:
            if layer not in layer_cats:
                if isinstance(layer, LayerEnum):
                    ln = str(layer.name)
                else:
                    li = self.kcl.get_info(layer)
                    ln = str(li).replace("/", "_")
                layer_cats[layer] = db_.category_by_path(ln) or db_.create_category(ln)
            return layer_cats[layer]

        for port in Ports(kcl=self.kcl, bases=self.ports.bases):
            if (not port_types or port.port_type in port_types) and (
                not layers or port.layer in layers
            ):
                if add_cell_ports:
                    c_cat = db_.category_by_path(
                        f"{layer_cat(port.layer).path()}.CellPorts"
                    ) or db_.create_category(layer_cat(port.layer), "CellPorts")
                    it = db_.create_item(db_cell, c_cat)
                    if port.name:
                        it.add_value(f"Port name: {port.name}")
                    if port.base.trans:
                        it.add_value(
                            self.kcl.to_um(
                                port_polygon(port.width).transformed(port.trans)
                            )
                        )
                    else:
                        it.add_value(
                            self.kcl.to_um(port_polygon(port.width)).transformed(
                                port.dcplx_trans
                            )
                        )
                xy = (port.x, port.y)
                if port.layer not in cell_ports:
                    cell_ports[port.layer] = {xy: [port]}
                elif xy not in cell_ports[port.layer]:
                    cell_ports[port.layer][xy] = [port]
                else:
                    cell_ports[port.layer][xy].append(port)
                rec_it = kdb.RecursiveShapeIterator(
                    self.kcl.layout,
                    self._base.kdb_cell,
                    port.layer,
                    kdb.Box(2, port.width).transformed(port.trans),
                )
                edges = kdb.Region(rec_it).merge().edges().merge()
                port_edge = kdb.Edge(0, port.width // 2, 0, -port.width // 2)
                if port.base.trans:
                    port_edge = port_edge.transformed(port.trans)
                else:
                    port_edge = port_edge.transformed(
                        kdb.ICplxTrans(port.dcplx_trans, self.kcl.dbu)
                    )
                p_edges = kdb.Edges([port_edge])
                phys_overlap = p_edges & edges
                if not phys_overlap.is_empty() and phys_overlap[0] != port_edge:
                    p_cat = db_.category_by_path(
                        layer_cat(port.layer).path() + ".PartialPhysicalShape"
                    ) or db_.create_category(
                        layer_cat(port.layer), "PartialPhysicalShape"
                    )
                    it = db_.create_item(db_cell, p_cat)
                    it.add_value(
                        "Insufficient overlap, partial overlap with polygon of"
                        f" {(phys_overlap[0].p1 - phys_overlap[0].p2).abs()}/"
                        f"{port.width}"
                    )
                    it.add_value(
                        self.kcl.to_um(port_polygon(port.width).transformed(port.trans))
                        if port.base.trans
                        else self.kcl.to_um(port_polygon(port.width)).transformed(
                            port.dcplx_trans
                        )
                    )
                elif phys_overlap.is_empty():
                    p_cat = db_.category_by_path(
                        layer_cat(port.layer).path() + ".MissingPhysicalShape"
                    ) or db_.create_category(
                        layer_cat(port.layer), "MissingPhysicalShape"
                    )
                    it = db_.create_item(db_cell, p_cat)
                    it.add_value(
                        f"Found no overlapping Edge with Port {port.name or str(port)}"
                    )
                    it.add_value(
                        self.kcl.to_um(port_polygon(port.width).transformed(port.trans))
                        if port.base.trans
                        else self.kcl.to_um(port_polygon(port.width)).transformed(
                            port.dcplx_trans
                        )
                    )

        inst_ports: dict[
            LayerEnum | int, dict[tuple[int, int], list[tuple[Port, KCell]]]
        ] = {}
        for inst in self.insts:
            for port in Ports(kcl=self.kcl, bases=[p.base for p in inst.ports]):
                if (not port_types or port.port_type in port_types) and (
                    not layers or port.layer in layers
                ):
                    xy = (port.x, port.y)
                    if port.layer not in inst_ports:
                        inst_ports[port.layer] = {xy: [(port, inst.cell.to_itype())]}
                    elif xy not in inst_ports[port.layer]:
                        inst_ports[port.layer][xy] = [(port, inst.cell.to_itype())]
                    else:
                        inst_ports[port.layer][xy].append((port, inst.cell.to_itype()))

        for layer, port_coord_mapping in inst_ports.items():
            lc = layer_cat(layer)
            for coord, ports in port_coord_mapping.items():
                match len(ports):
                    case 1:
                        if layer in cell_ports and coord in cell_ports[layer]:
                            ccp = check_cell_ports(
                                cell_ports[layer][coord][0], ports[0][0]
                            )
                            if ccp & 1:
                                subc = db_.category_by_path(
                                    lc.path() + ".WidthMismatch"
                                ) or db_.create_category(lc, "WidthMismatch")
                                create_port_error(
                                    ports[0][0],
                                    cell_ports[layer][coord][0],
                                    ports[0][1],
                                    self,
                                    db_,
                                    db_cell,
                                    subc,
                                    self.kcl.dbu,
                                )

                            if ccp & 2:
                                subc = db_.category_by_path(
                                    lc.path() + ".AngleMismatch"
                                ) or db_.create_category(lc, "AngleMismatch")
                                create_port_error(
                                    ports[0][0],
                                    cell_ports[layer][coord][0],
                                    ports[0][1],
                                    self,
                                    db_,
                                    db_cell,
                                    subc,
                                    self.kcl.dbu,
                                )
                            if ccp & 4:
                                subc = db_.category_by_path(
                                    lc.path() + ".TypeMismatch"
                                ) or db_.create_category(lc, "TypeMismatch")
                                create_port_error(
                                    ports[0][0],
                                    cell_ports[layer][coord][0],
                                    ports[0][1],
                                    self,
                                    db_,
                                    db_cell,
                                    subc,
                                    self.kcl.dbu,
                                )
                        else:
                            subc = db_.category_by_path(
                                lc.path() + ".OrphanPort"
                            ) or db_.create_category(lc, "OrphanPort")
                            it = db_.create_item(db_cell, subc)
                            it.add_value(
                                f"Port Name: {ports[0][1].name}"
                                f"{ports[0][0].name or str(ports[0][0])})"
                            )
                            if ports[0][0]._base.trans:
                                it.add_value(
                                    self.kcl.to_um(
                                        port_polygon(ports[0][0].width).transformed(
                                            ports[0][0]._base.trans
                                        )
                                    )
                                )
                            else:
                                it.add_value(
                                    self.kcl.to_um(
                                        port_polygon(port.width)
                                    ).transformed(port.dcplx_trans)
                                )

                    case 2:
                        cip = check_inst_ports(ports[0][0], ports[1][0])
                        if cip & 1:
                            subc = db_.category_by_path(
                                lc.path() + ".WidthMismatch"
                            ) or db_.create_category(lc, "WidthMismatch")
                            create_port_error(
                                ports[0][0],
                                ports[1][0],
                                ports[0][1],
                                ports[1][1],
                                db_,
                                db_cell,
                                subc,
                                self.kcl.dbu,
                            )

                        if cip & 2:
                            subc = db_.category_by_path(
                                lc.path() + ".AngleMismatch"
                            ) or db_.create_category(lc, "AngleMismatch")
                            create_port_error(
                                ports[0][0],
                                ports[1][0],
                                ports[0][1],
                                ports[1][1],
                                db_,
                                db_cell,
                                subc,
                                self.kcl.dbu,
                            )
                        if cip & 4:
                            subc = db_.category_by_path(
                                lc.path() + ".TypeMismatch"
                            ) or db_.create_category(lc, "TypeMismatch")
                            create_port_error(
                                ports[0][0],
                                ports[1][0],
                                ports[0][1],
                                ports[1][1],
                                db_,
                                db_cell,
                                subc,
                                self.kcl.dbu,
                            )
                        if layer in cell_ports and coord in cell_ports[layer]:
                            subc = db_.category_by_path(
                                lc.path() + ".portoverlap"
                            ) or db_.create_category(lc, "portoverlap")
                            it = db_.create_item(db_cell, subc)
                            text = "Port Names: "
                            values: list[rdb.RdbItemValue] = []
                            cell_port = cell_ports[layer][coord][0]
                            text += (
                                f"{self.name}."
                                f"{cell_port.name or cell_port.trans.to_s()}/"
                            )
                            if cell_port.base.trans:
                                values.append(
                                    rdb.RdbItemValue(
                                        self.kcl.to_um(
                                            port_polygon(cell_port.width).transformed(
                                                cell_port.base.trans
                                            )
                                        )
                                    )
                                )
                            else:
                                values.append(
                                    rdb.RdbItemValue(
                                        self.kcl.to_um(
                                            port_polygon(cell_port.width)
                                        ).transformed(cell_port.dcplx_trans)
                                    )
                                )
                            for _port in ports:
                                text += (
                                    f"{_port[1].name}."
                                    f"{_port[0].name or _port[0].trans.to_s()}/"
                                )

                                values.append(
                                    rdb.RdbItemValue(
                                        self.kcl.to_um(
                                            port_polygon(_port[0].width).transformed(
                                                _port[0].trans
                                            )
                                        )
                                    )
                                )
                            it.add_value(text[:-1])
                            for value in values:
                                it.add_value(value)

                    case x if x > 2:  # noqa: PLR2004
                        subc = db_.category_by_path(
                            lc.path() + ".portoverlap"
                        ) or db_.create_category(lc, "portoverlap")
                        it = db_.create_item(db_cell, subc)
                        text = "Port Names: "
                        values = []
                        for _port in ports:
                            text += (
                                f"{_port[1].name}."
                                f"{_port[0].name or _port[0].trans.to_s()}/"
                            )

                            values.append(
                                rdb.RdbItemValue(
                                    self.kcl.to_um(
                                        port_polygon(_port[0].width).transformed(
                                            _port[0].trans
                                        )
                                    )
                                )
                            )
                        it.add_value(text[:-1])
                        for value in values:
                            it.add_value(value)
                    case _:
                        raise ValueError(f"Unexpected number of ports: {len(ports)}")
            if check_layer_connectivity:
                error_region_shapes = kdb.Region()
                error_region_instances = kdb.Region()
                reg = kdb.Region(self.shapes(layer))
                inst_regions: dict[int, kdb.Region] = {}
                inst_region = kdb.Region()
                for i, inst in enumerate(self.insts):
                    inst_region_ = kdb.Region(inst.ibbox(layer))
                    inst_shapes: kdb.Region | None = None
                    if not (inst_region & inst_region_).is_empty():
                        if inst_shapes is None:
                            inst_shapes = kdb.Region()
                            shape_it = self.begin_shapes_rec_overlapping(
                                layer, inst.bbox(layer)
                            )
                            shape_it.select_cells([inst.cell.cell_index()])
                            shape_it.min_depth = 1
                            for _it in shape_it.each():
                                if _it.path()[0].inst() == inst.instance:
                                    inst_shapes.insert(
                                        _it.shape().polygon.transformed(_it.trans())
                                    )

                        for j, _reg in inst_regions.items():
                            if _reg & inst_region_:
                                reg_ = kdb.Region()
                                shape_it = self.begin_shapes_rec_touching(
                                    layer, (_reg & inst_region_).bbox()
                                )
                                shape_it.select_cells([self.insts[j].cell.cell_index()])
                                shape_it.min_depth = 1
                                for _it in shape_it.each():
                                    if _it.path()[0].inst() == self.insts[j].instance:
                                        reg_.insert(
                                            _it.shape().polygon.transformed(_it.trans())
                                        )

                                error_region_instances.insert(reg_ & inst_shapes)

                    if not (inst_region_ & reg).is_empty():
                        rec_it = self.begin_shapes_rec_touching(
                            layer, (inst_region_ & reg).bbox()
                        )
                        rec_it.min_depth = 1
                        error_region_shapes += kdb.Region(rec_it) & reg
                    inst_region += inst_region_
                    inst_regions[i] = inst_region_
                if not error_region_shapes.is_empty():
                    sc = db_.category_by_path(
                        layer_cat(layer).path() + ".ShapeInstanceshapeOverlap"
                    ) or db_.create_category(
                        layer_cat(layer), "ShapeInstanceshapeOverlap"
                    )
                    for poly in error_region_shapes.merge().each():
                        it = db_.create_item(db_cell, sc)
                        it.add_value("Shapes overlapping with shapes of instances")
                        it.add_value(self.kcl.to_um(poly.downcast()))
                if not error_region_instances.is_empty():
                    sc = db_.category_by_path(
                        layer_cat(layer).path() + ".InstanceshapeOverlap"
                    ) or db_.create_category(layer_cat(layer), "InstanceshapeOverlap")
                    for poly in error_region_instances.merge().each():
                        it = db_.create_item(db_cell, sc)
                        it.add_value(
                            "Instance shapes overlapping with shapes of other instances"
                        )
                        it.add_value(self.kcl.to_um(poly.downcast()))

        return db_

    def insert_vinsts(self, recursive: bool = True) -> None:
        """Insert all virtual instances and create Instances of real KCells."""
        if not self._base.kdb_cell._destroyed():
            for vi in self._base.vinsts:
                vi.insert_into(self)
            self._base.vinsts.clear()
            called_cell_indexes = self._base.kdb_cell.called_cells()
            for c in sorted(
                {
                    self.kcl[ci]
                    for ci in called_cell_indexes
                    if not self.kcl[ci].kdb_cell._destroyed()
                }
                & self.kcl.tkcells.keys(),
                key=lambda c: c.hierarchy_levels(),
            ):
                for vi in c._base.vinsts:
                    vi.insert_into(c)
                c._base.vinsts.clear()

    @abstractmethod
    def get_cross_section(
        self,
        cross_section: str
        | dict[str, Any]
        | Callable[..., CrossSection | DCrossSection]
        | SymmetricalCrossSection,
        **cross_section_kwargs: Any,
    ) -> TCrossSection[TUnit]: ...

    @property
    def lvs_equivalent_ports(self) -> list[list[str]] | None:
        return self._base.lvs_equivalent_ports


class DKCell(ProtoTKCell[float], UMGeometricObject, DCreatePort):
    """Cell with floating point units."""

    yaml_tag: ClassVar[str] = "!DKCell"

    @overload
    def __init__(self, *, base: TKCell) -> None: ...

    @overload
    def __init__(
        self,
        name: str | None = None,
        kcl: KCLayout | None = None,
        kdb_cell: kdb.Cell | None = None,
        ports: Iterable[ProtoPort[Any]] | None = None,
        info: dict[str, Any] | None = None,
        settings: dict[str, Any] | None = None,
        pins: Iterable[ProtoPin[Any]] | None = None,
    ) -> None: ...

    def __init__(
        self,
        name: str | None = None,
        kcl: KCLayout | None = None,
        kdb_cell: kdb.Cell | None = None,
        ports: Iterable[ProtoPort[Any]] | None = None,
        info: dict[str, Any] | None = None,
        settings: dict[str, Any] | None = None,
        pins: Iterable[ProtoPin[Any]] | None = None,
        *,
        base: TKCell | None = None,
    ) -> None:
        """Constructor of KCell.

        Args:
            base: If not `None`, a KCell will be created from and existing
                KLayout Cell
            name: Name of the cell, if None will autogenerate name to
                "Unnamed_<cell_index>".
            kcl: KCLayout the cell should be attached to.
            kdb_cell: If not `None`, a KCell will be created from and existing
                KLayout Cell
            ports: Attach an existing [Ports][kfactory.kcell.Ports] object to the KCell,
                if `None` create an empty one.
            info: Info object to attach to the KCell.
            settings: KCellSettings object to attach to the KCell.
        """
        super().__init__(
            base=base,
            name=name,
            kcl=kcl,
            kdb_cell=kdb_cell,
            ports=ports,
            info=info,
            settings=settings,
            pins=pins,
        )

    @property
    def ports(self) -> DPorts:
        """Ports associated with the cell."""
        return DPorts(kcl=self.kcl, bases=self._base.ports)

    @ports.setter
    def ports(self, new_ports: Iterable[ProtoPort[Any]]) -> None:
        if self.locked:
            raise LockedError(self)
        self._base.ports = [port.base for port in new_ports]

    @property
    def pins(self) -> DPins:
        """Pins associated with the cell."""
        return DPins(kcl=self.kcl, bases=self._base.pins)

    @pins.setter
    def pins(self, new_pins: Iterable[ProtoPin[Any]]) -> None:
        if self.locked:
            raise LockedError(self)
        self._base.pins = [pin.base for pin in new_pins]

    @property
    def insts(self) -> DInstances:
        """Instances associated with the cell."""
        return DInstances(cell=self._base)

    def __lshift__(self, cell: AnyTKCell) -> DInstance:
        """Convenience function for [create_inst][kfactory.kcell.KCell.create_inst].

        Args:
            cell: The cell to be added as an instance
        """
        return DInstance(kcl=self.kcl, instance=self.create_inst(cell).instance)

    def add_port(
        self,
        *,
        port: ProtoPort[Any],
        name: str | None = None,
        keep_mirror: bool = False,
    ) -> DPort:
        """Create a port in the cell."""
        if self.locked:
            raise LockedError(self)

        return self.ports.add_port(
            port=port,
            name=name,
            keep_mirror=keep_mirror,
        )

    def create_pin(
        self,
        *,
        ports: Iterable[ProtoPort[Any]],
        name: str | None = None,
        pin_type: str = "DC",
        info: dict[str, int | float | str] | None = None,
    ) -> DPin:
        """Create a pin in the cell."""
        return self.pins.create_pin(
            name=name, ports=ports, pin_type=pin_type, info=info
        )

    def __getitem__(self, key: int | str | None) -> DPort:
        """Returns port from instance."""
        return self.ports[key]

    def create_inst(
        self,
        cell: ProtoTKCell[Any] | int,
        trans: kdb.DTrans | kdb.DVector | kdb.DCplxTrans | None = None,
        *,
        a: kdb.DVector | None = None,
        b: kdb.DVector | None = None,
        na: int = 1,
        nb: int = 1,
        libcell_as_static: bool = False,
        static_name_separator: str = "__",
    ) -> DInstance:
        return DInstance(
            kcl=self.kcl,
            instance=self.dcreate_inst(
                cell,
                trans or kdb.DTrans(),
                a=a,
                b=b,
                na=na,
                nb=nb,
                libcell_as_static=libcell_as_static,
                static_name_separator=static_name_separator,
            ).instance,
        )

    def get_cross_section(
        self,
        cross_section: str
        | dict[str, Any]
        | Callable[..., CrossSection | DCrossSection]
        | SymmetricalCrossSection,
        **cross_section_kwargs: Any,
    ) -> DCrossSection:
        if isinstance(cross_section, str):
            return DCrossSection(
                kcl=self.kcl, base=self.kcl.cross_sections[cross_section]
            )
        if isinstance(cross_section, SymmetricalCrossSection):
            return DCrossSection(kcl=self.kcl, base=cross_section)
        if callable(cross_section):
            any_cross_section = cross_section(**cross_section_kwargs)
            return DCrossSection(kcl=self.kcl, base=any_cross_section._base)
        if isinstance(cross_section, dict):
            return DCrossSection(
                kcl=self.kcl,
                name=cross_section.get("name"),
                **cross_section["settings"],
            )
        raise ValueError(
            "Cannot create a cross section from "
            f"{type(cross_section)=} and {cross_section_kwargs=}"
        )


class KCell(ProtoTKCell[int], DBUGeometricObject, ICreatePort):
    """Cell with integer units."""

    yaml_tag: ClassVar[str] = "!KCell"

    @overload
    def __init__(self, *, base: TKCell) -> None: ...

    @overload
    def __init__(
        self,
        name: str | None = None,
        kcl: KCLayout | None = None,
        kdb_cell: kdb.Cell | None = None,
        ports: Iterable[ProtoPort[Any]] | None = None,
        info: dict[str, Any] | None = None,
        settings: dict[str, Any] | None = None,
        pins: Iterable[ProtoPin[Any]] | None = None,
    ) -> None: ...

    def __init__(
        self,
        name: str | None = None,
        kcl: KCLayout | None = None,
        kdb_cell: kdb.Cell | None = None,
        ports: Iterable[ProtoPort[Any]] | None = None,
        info: dict[str, Any] | None = None,
        settings: dict[str, Any] | None = None,
        pins: Iterable[ProtoPin[Any]] | None = None,
        *,
        base: TKCell | None = None,
    ) -> None:
        """Constructor of KCell.

        Args:
            base: If not `None`, a KCell will be created from and existing
                KLayout Cell
            name: Name of the cell, if None will autogenerate name to
                "Unnamed_<cell_index>".
            kcl: KCLayout the cell should be attached to.
            kdb_cell: If not `None`, a KCell will be created from and existing
                KLayout Cell
            ports: Attach an existing [Ports][kfactory.kcell.Ports] object to the KCell,
                if `None` create an empty one.
            info: Info object to attach to the KCell.
            settings: KCellSettings object to attach to the KCell.
        """
        super().__init__(
            base=base,
            name=name,
            kcl=kcl,
            kdb_cell=kdb_cell,
            ports=ports,
            info=info,
            settings=settings,
            pins=pins,
        )

    @property
    def ports(self) -> Ports:
        """Ports associated with the cell."""
        return Ports(kcl=self.kcl, bases=self._base.ports)

    @ports.setter
    def ports(self, new_ports: Iterable[ProtoPort[Any]]) -> None:
        if self.locked:
            raise LockedError(self)
        self._base.ports = [port.base for port in new_ports]

    @property
    def pins(self) -> Pins:
        """Pins associated with the cell."""
        return Pins(kcl=self.kcl, bases=self._base.pins)

    @pins.setter
    def pins(self, new_pins: Iterable[ProtoPin[Any]]) -> None:
        if self.locked:
            raise LockedError(self)
        self._base.pins = [pin.base for pin in new_pins]

    @property
    def insts(self) -> Instances:
        """Instances associated with the cell."""
        return Instances(cell=self._base)

    def __lshift__(self, cell: AnyTKCell) -> Instance:
        """Convenience function for [create_inst][kfactory.kcell.KCell.create_inst].

        Args:
            cell: The cell to be added as an instance
        """
        return self.create_inst(cell)

    def add_port(
        self,
        *,
        port: ProtoPort[Any],
        name: str | None = None,
        keep_mirror: bool = False,
    ) -> Port:
        """Create a port in the cell."""
        if self.locked:
            raise LockedError(self)

        return self.ports.add_port(
            port=port,
            name=name,
            keep_mirror=keep_mirror,
        )

    def create_pin(
        self,
        *,
        ports: Iterable[ProtoPort[Any]],
        name: str | None = None,
        pin_type: str = "DC",
        info: dict[str, int | float | str] | None = None,
    ) -> Pin:
        """Create a pin in the cell."""
        return self.pins.create_pin(
            name=name, ports=ports, pin_type=pin_type, info=info
        )

    def __getitem__(self, key: int | str | None) -> Port:
        """Returns port from instance."""
        return self.ports[key]

    def create_inst(
        self,
        cell: AnyTKCell | int,
        trans: kdb.Trans | kdb.Vector | kdb.ICplxTrans | None = None,
        *,
        a: kdb.Vector | None = None,
        b: kdb.Vector | None = None,
        na: int = 1,
        nb: int = 1,
        libcell_as_static: bool = False,
        static_name_separator: str = "__",
    ) -> Instance:
        return Instance(
            kcl=self.kcl,
            instance=self.icreate_inst(
                cell,
                trans or kdb.Trans(),
                a=a,
                b=b,
                na=na,
                nb=nb,
                libcell_as_static=libcell_as_static,
                static_name_separator=static_name_separator,
            ).instance,
        )

    @classmethod
    def from_yaml(
        cls,
        constructor: SafeConstructor,
        node: Any,
        verbose: bool = False,
    ) -> Self:
        """Internal function used by the placer to convert yaml to a KCell."""
        d = SafeConstructor.construct_mapping(
            constructor,
            node,
            deep=True,
        )
        cell = cls(name=d["name"])
        if verbose:
            logger.info(f"Building {d['name']}")
        for _d in d.get("ports", Ports(ports=[], kcl=cell.kcl)):
            layer_as_string = (
                str(_d["layer"]).replace("[", "").replace("]", "").replace(", ", "/")
            )
            if "dcplx_trans" in _d:
                cell.create_port(
                    name=str(_d["name"]),
                    dcplx_trans=kdb.DCplxTrans.from_s(_d["dcplx_trans"]),
                    width=_d["dwidth"],
                    layer=cell.kcl.layer(kdb.LayerInfo.from_string(layer_as_string)),
                    port_type=_d["port_type"],
                )
            else:
                cell.create_port(
                    name=str(_d["name"]),
                    trans=kdb.Trans.from_s(_d["trans"]),
                    width=int(_d["width"]),
                    layer=cell.kcl.layer(kdb.LayerInfo.from_string(layer_as_string)),
                    port_type=_d["port_type"],
                )
        cell.settings = KCellSettings(
            **{
                name: deserialize_setting(setting)
                for name, setting in d.get("settings", {}).items()
            }
        )
        cell.info = Info(
            **{
                name: deserialize_setting(setting)
                for name, setting in d.get("info", {}).items()
            }
        )
        for inst in d.get("insts", []):
            if "cellname" in inst:
                cell_ = cell.kcl[inst["cellname"]]
            elif "cellfunction" in inst:
                module_name, fname = inst["cellfunction"].rsplit(".", 1)
                module = importlib.import_module(module_name)
                cellf = getattr(module, fname)
                cell_ = cellf(**inst["settings"])
                del module
            else:
                raise NotImplementedError(
                    'To define an instance, either a "cellfunction" or'
                    ' a "cellname" needs to be defined'
                )
            t = inst.get("trans", {})
            if isinstance(t, str):
                cell.create_inst(
                    cell_,
                    kdb.Trans.from_s(inst["trans"]),
                )
            else:
                angle = t.get("angle", 0)
                mirror = t.get("mirror", False)

                kinst = cell.create_inst(
                    cell_,
                    kdb.Trans(angle, mirror, 0, 0),
                )

                x0_yml = t.get("x0", DEFAULT_TRANS["x0"])
                y0_yml = t.get("y0", DEFAULT_TRANS["y0"])
                x_yml = t.get("x", DEFAULT_TRANS["x"])
                y_yml = t.get("y", DEFAULT_TRANS["y"])
                margin = t.get("margin", DEFAULT_TRANS["margin"])
                margin_x = margin.get(
                    "x",
                    DEFAULT_TRANS["margin"]["x"],  # type: ignore[index]
                )
                margin_y = margin.get(
                    "y",
                    DEFAULT_TRANS["margin"]["y"],  # type: ignore[index]
                )
                margin_x0 = margin.get(
                    "x0",
                    DEFAULT_TRANS["margin"]["x0"],  # type: ignore[index]
                )
                margin_y0 = margin.get(
                    "y0",
                    DEFAULT_TRANS["margin"]["y0"],  # type: ignore[index]
                )
                ref_yml = t.get("ref", DEFAULT_TRANS["ref"])
                if isinstance(ref_yml, str):
                    i: Instance
                    for i in reversed(cell.insts):
                        if i.cell.name == ref_yml:
                            ref = i
                            break
                    else:
                        raise IndexError(
                            f"No instance with cell name: <{ref_yml}> found"
                        )
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
                            raise NotImplementedError("unknown format for x0")
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
                            raise NotImplementedError("unknown format for y0")
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
                            raise NotImplementedError("unknown format for x")
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
                            raise NotImplementedError("unknown format for y")
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

    @classmethod
    def to_yaml(cls, representer: BaseRepresenter, node: Self) -> MappingNode:
        """Internal function to convert the cell to yaml."""
        d: dict[str, Any] = {"name": node.name}

        insts = [
            {"cellname": inst.cell.name, "trans": inst.instance.trans.to_s()}
            for inst in node.insts
        ]
        shapes = {
            node.layout().get_info(layer).to_s(): [
                shape.to_s() for shape in node.shapes(layer).each()
            ]
            for layer in node.layout().layer_indexes()
            if not node.shapes(layer).is_empty()
        }
        ports: list[dict[str, Any]] = []
        for port in node.ports:
            l_ = node.kcl.get_info(port.layer)
            p: dict[str, Any] = {
                "name": port.name,
                "layer": [l_.layer, l_.datatype],
                "port_type": port.port_type,
            }
            if port.base.trans:
                p["trans"] = port.base.trans.to_s()
                p["width"] = port.width
            else:
                assert port.base.dcplx_trans is not None
                p["dcplx_trans"] = port.base.dcplx_trans.to_s()
                p["dwidth"] = port.dwidth
            p["info"] = {
                name: serialize_setting(setting)
                for name, setting in node.info.model_dump().items()
            }
            ports.append(p)

        d["ports"] = ports

        if insts:
            d["insts"] = insts
        if shapes:
            d["shapes"] = shapes
        d["settings"] = {
            name: serialize_setting(setting)
            for name, setting in node.settings.model_dump().items()
        }
        d["info"] = {
            name: serialize_setting(info)
            for name, info in node.info.model_dump().items()
        }
        return representer.represent_mapping(cls.yaml_tag, d)

    def get_cross_section(
        self,
        cross_section: str
        | dict[str, Any]
        | Callable[..., CrossSection | DCrossSection]
        | SymmetricalCrossSection,
        **cross_section_kwargs: Any,
    ) -> CrossSection:
        if isinstance(cross_section, str):
            return CrossSection(
                kcl=self.kcl, base=self.kcl.cross_sections[cross_section]
            )
        if isinstance(cross_section, SymmetricalCrossSection):
            return CrossSection(kcl=self.kcl, base=cross_section)
        if callable(cross_section):
            any_cross_section = cross_section(**cross_section_kwargs)
            return CrossSection(kcl=self.kcl, base=any_cross_section._base)
        if isinstance(cross_section, dict):
            return CrossSection(
                kcl=self.kcl,
                name=cross_section.get("name"),
                **cross_section["settings"],
            )
        raise ValueError(
            "Cannot create a cross section from "
            f"{type(cross_section)=} and {cross_section_kwargs=}"
        )


class VKCell(ProtoKCell[float, TVCell], UMGeometricObject, DCreatePort):
    """Emulate `[klayout.db.Cell][klayout.db.Cell]`."""

    @overload
    def __init__(self, *, base: TVCell) -> None: ...

    @overload
    def __init__(
        self,
        *,
        name: str | None = None,
        kcl: KCLayout | None = None,
        info: dict[str, Any] | None = None,
        settings: dict[str, Any] | None = None,
    ) -> None: ...

    def __init__(
        self,
        *,
        base: TVCell | None = None,
        name: str | None = None,
        kcl: KCLayout | None = None,
        info: dict[str, Any] | None = None,
        settings: dict[str, Any] | None = None,
    ) -> None:
        from .layout import get_default_kcl

        if base is not None:
            self._base = base
        else:
            kcl_ = kcl or get_default_kcl()
            self._base = TVCell(
                kcl=kcl_,
                info=Info(**(info or {})),
                settings=KCellSettings(**(settings or {})),
                vinsts=VInstances(),
            )
            if name:
                self._base.name = name

    def ibbox(self, layer: int | None = None) -> kdb.Box:
        return self.dbbox(layer).to_itype(self.kcl.dbu)

    def transform(
        self,
        trans: kdb.Trans | kdb.DTrans | kdb.ICplxTrans | kdb.DCplxTrans,
        /,
    ) -> None:
        shapes = self.base.shapes
        for key, vshape in shapes.items():
            shapes[key] = vshape.transform(trans)

    @property
    def ports(self) -> DPorts:
        """Ports associated with the cell."""
        return DPorts(kcl=self.kcl, bases=self._base.ports)

    @ports.setter
    def ports(self, new_ports: Iterable[ProtoPort[Any]]) -> None:
        if self.locked:
            raise LockedError(self)
        self._base.ports = [port.base for port in new_ports]

    @property
    def pins(self) -> DPins:
        """Ports associated with the cell."""
        return DPins(kcl=self.kcl, bases=self._base.pins)

    @pins.setter
    def pins(self, new_pins: Iterable[ProtoPin[Any]]) -> None:
        if self.locked:
            raise LockedError(self)
        self._base.pins = [pin.base for pin in new_pins]

    def dbbox(self, layer: int | LayerEnum | None = None) -> kdb.DBox:
        layers_ = set(self.shapes().keys())

        layers = layers_ if layer is None else {layer} & layers_
        box = kdb.DBox()
        for layer_ in layers:
            layer__ = layer_
            if isinstance(layer__, LayerEnum):
                layer__ = layer__.layout.layer(layer__.layer, layer__.datatype)
            box += self.shapes(layer__).bbox()

        for vinst in self.insts:
            box += vinst.dbbox()

        return box

    def __getitem__(self, key: int | str | None) -> DPort:
        """Returns port from instance."""
        return self.ports[key]

    @property
    def insts(self) -> VInstances:
        return self._base.vinsts

    def dup(self, new_name: str | None = None) -> Self:
        """Copy the full cell.

        Removes lock if the original cell was locked.

        Returns:
            cell: Exact copy of the current cell.
                The name will have `$1` as duplicate names are not allowed
        """
        c = self.__class__(
            kcl=self.kcl, name=new_name or self.name + "$1" if self.name else None
        )
        c.ports = DPorts(kcl=self.kcl, ports=self.ports.copy())

        c.settings = self.settings.model_copy()
        c.settings_units = self.settings_units.model_copy()
        c.info = self._base.info.model_copy()
        for layer, shapes in self.shapes().items():
            for shape in shapes:
                c.shapes(layer).insert(shape)

        return c

    def show(
        self,
        lyrdb: rdb.ReportDatabase | Path | str | None = None,
        l2n: kdb.LayoutToNetlist | Path | str | None = None,
        keep_position: bool = True,
        save_options: kdb.SaveLayoutOptions | None = None,
        use_libraries: bool = True,
        library_save_options: kdb.SaveLayoutOptions | None = None,
        technology: str | None = None,
    ) -> None:
        """Stream the gds to klive.

        Will create a temporary file of the gds and load it in KLayout via klive
        """
        if save_options is None:
            save_options = save_layout_options()
        if library_save_options is None:
            library_save_options = save_layout_options()
        c = self.kcl.kcell()
        if self.name is not None:
            c.name = self.name
        VInstance(self).insert_into_flat(c, levels=0)
        c.add_ports(self.ports)
        c.info = self.info.model_copy()
        c.base.settings = self.settings.model_copy()

        kwargs: dict[str, Any] = {}
        if technology is not None:
            kwargs["technology"] = technology
        if l2n is not None:
            kwargs["l2n"] = l2n
        if lyrdb is not None:
            kwargs["lyrdb"] = lyrdb

        c.show(keep_position=keep_position, **kwargs)

    def plot(self) -> None:
        """Display cell.

        Usage: Pass the vkcell variable as an argument in the cell at the end
        """
        from .widgets.interactive import display_kcell

        c = self.kcl.kcell()
        if self.name is not None:
            c.name = self.name
        VInstance(self).insert_into_flat(c, levels=0)

        display_kcell(c)
        c.delete()

    def _ipython_display_(self) -> None:
        """Display a cell in a Jupyter Cell.

        Usage: Pass the kcell variable as an argument in the cell at the end
        """
        self.plot()

    def __repr__(self) -> str:
        """Return a string representation of the Cell."""
        port_names = [p.name for p in self.ports]
        pin_names = [pin.name for pin in self.pins]
        return (
            f"{self.name}: ports {port_names}, pins {pin_names}, {len(self.insts)} "
            "instances"
        )

    def add_port(
        self,
        *,
        port: ProtoPort[Any],
        name: str | None = None,
        keep_mirror: bool = False,
    ) -> DPort:
        """Proxy for [Ports.create_port][kfactory.kcell.Ports.create_port]."""
        if self.locked:
            raise LockedError(self)
        return self.ports.add_port(
            port=port,
            name=name,
            keep_mirror=keep_mirror,
        )

    def create_inst(
        self, cell: AnyKCell, trans: kdb.DCplxTrans | None = None
    ) -> VInstance:
        if self.locked:
            raise LockedError(self)
        inst = VInstance(cell=cell, trans=trans or kdb.DCplxTrans())
        self.insts.append(inst)
        return inst

    def auto_rename_ports(self, rename_func: Callable[..., None] | None = None) -> None:
        """Rename the ports with the schema angle -> "NSWE" and sort by x and y.

        Args:
            rename_func: Function that takes Iterable[Port] and renames them.
                This can of course contain a filter and only rename some of the ports
        """
        if self.locked:
            raise LockedError(self)
        if rename_func is None:
            self.kcl.rename_function(self.ports)
        else:
            rename_func(self.ports)

    def __lshift__(self, cell: AnyKCell) -> VInstance:
        return self.create_inst(cell=cell)

    def create_vinst(self, cell: AnyKCell) -> VInstance:
        if self.locked:
            raise LockedError(self)
        vi = VInstance(cell)
        self.vinsts.append(vi)
        return vi

    @overload
    def shapes(self, layer: None = ...) -> dict[int, VShapes]: ...

    @overload
    def shapes(self, layer: int | kdb.LayerInfo) -> VShapes: ...

    def shapes(
        self, layer: int | kdb.LayerInfo | None = None
    ) -> VShapes | dict[int, VShapes]:
        if layer is None:
            return self._base.shapes
        if isinstance(layer, kdb.LayerInfo):
            layer = self.kcl.layout.layer(layer)
        if layer not in self._base.shapes:
            self._base.shapes[layer] = VShapes(cell=self)
        return self._base.shapes[layer]

    def flatten(self) -> None:
        if self.locked:
            raise LockedError(self)
        for inst in self.insts:
            inst.insert_into_flat(self, inst.trans)

    def draw_ports(self) -> None:
        """Draw all the ports on their respective layer."""
        polys: dict[float, kdb.DPolygon] = {}

        for port in self.ports:
            w = port.width

            if w in polys:
                poly = polys[w]
            else:
                if w < 2:  # noqa: PLR2004
                    poly = kdb.DPolygon(
                        [
                            kdb.DPoint(0, -w / 2),
                            kdb.DPoint(0, w / 2),
                            kdb.DPoint(w / 2, 0),
                        ]
                    )
                else:
                    poly = kdb.DPolygon(
                        [
                            kdb.DPoint(0, -w / 2),
                            kdb.DPoint(0, w / 2),
                            kdb.DPoint(w / 2, 0),
                            kdb.DPoint(w * 19 / 20, 0),
                            kdb.DPoint(w / 20, w * 9 / 20),
                            kdb.DPoint(w / 20, -w * 9 / 20),
                            kdb.DPoint(w * 19 / 20, 0),
                            kdb.DPoint(w / 2, 0),
                        ]
                    )
                polys[w] = poly
            self.shapes(port.layer).insert(poly.transformed(port.dcplx_trans))
            self.shapes(port.layer).insert(kdb.Text(port.name or "", port.trans))

    def write(
        self,
        filename: str | Path,
        save_options: kdb.SaveLayoutOptions | None = None,
        convert_external_cells: bool = False,
        set_meta_data: bool = True,
        autoformat_from_file_extension: bool = True,
    ) -> None:
        """Write a KCell to a GDS.

        See [KCLayout.write][kfactory.kcell.KCLayout.write] for more info.
        """
        if save_options is None:
            save_options = save_layout_options()
        c = self.kcl.kcell()
        if self.name is not None:
            c.name = self.name
        c.settings = self.settings
        c.settings_units = self.settings_units
        c.info = self.info
        VInstance(self).insert_into_flat(c, levels=1)

        c.write(
            filename=filename,
            save_options=save_options,
            convert_external_cells=convert_external_cells,
            set_meta_data=set_meta_data,
            autoformat_from_file_extension=autoformat_from_file_extension,
        )

    def l2n(
        self, port_types: Iterable[str] = ("optical",)
    ) -> tuple[KCell, kdb.LayoutToNetlist]:
        """Generate a LayoutToNetlist object from the port types.

        Args:
            port_types: The port types to consider for the netlist extraction.
        """
        c = self.kcl.kcell()
        if self.name is not None:
            c.name = self.name
        c.settings = self.settings
        c.settings_units = self.settings_units
        c.info = self.info
        VInstance(self).insert_into(c)
        return c, c.l2n()

    def connectivity_check(
        self,
        port_types: list[str] | None = None,
        layers: list[int] | None = None,
        db: rdb.ReportDatabase | None = None,
        recursive: bool = True,
        add_cell_ports: bool = False,
        check_layer_connectivity: bool = True,
    ) -> tuple[KCell, rdb.ReportDatabase]:
        if layers is None:
            layers = []
        if port_types is None:
            port_types = []
        c = self.kcl.kcell()
        if self.name is not None:
            c.name = self.name
        c.settings = self.settings
        c.settings_units = self.settings_units
        c.info = self.info
        VInstance(self).insert_into_flat(c, levels=0)
        return c, c.connectivity_check(
            port_types=port_types,
            layers=layers,
            db=db,
            recursive=recursive,
            add_cell_ports=add_cell_ports,
            check_layer_connectivity=check_layer_connectivity,
        )


def show(
    layout: KCLayout | AnyKCell | Path | str,
    lyrdb: rdb.ReportDatabase | Path | str | None = None,
    l2n: kdb.LayoutToNetlist | Path | str | None = None,
    technology: str | None = None,
    keep_position: bool = True,
    save_options: kdb.SaveLayoutOptions | None = None,
    use_libraries: bool = True,
    library_save_options: kdb.SaveLayoutOptions | None = None,
    set_technology: bool = True,
    file_format: Literal["oas", "gds"] = "oas",
) -> None:
    """Show GDS in klayout.

    Args:
        layout: The object to show. This can be a KCell, KCLayout, Path, or string.
        lyrdb: A KLayout report database (.lyrdb/.rdb) file or object to show with the
            layout.
        l2n: A KLayout LayoutToNetlist object or file (.l2n) to show with the layout.
        keep_position: Keep the current KLayout position if a view is already open.
        save_options: Custom options for saving the gds/oas.
        use_libraries: Save other KCLayouts as libraries on write.
        library_save_options: Specific saving options for Cells which are in a library
            and not the main KCLayout.
    """
    from .layout import KCLayout, kcls

    delete = False
    delete_lyrdb = False
    delete_l2n = False

    if save_options is None:
        save_options = save_layout_options()
    if library_save_options is None:
        library_save_options = save_layout_options()

    # Find the file that calls stack
    try:
        stk = inspect.getouterframes(inspect.currentframe())
        frame = stk[2]
        frame_filename_stem = Path(frame.filename).stem
        if frame_filename_stem.startswith("<ipython-input"):  # IPython Case
            name = "ipython"
        elif frame.function != "<module>":
            name = clean_name(frame_filename_stem + "_" + frame.function)
        else:
            name = clean_name(frame_filename_stem)
    except Exception:
        try:
            from __main__ import __file__ as mf

            name = clean_name(mf)
        except ImportError:
            name = "shell"

    kcl_paths: list[dict[str, str]] = []

    if isinstance(layout, KCLayout):
        gitpath = config.project_dir
        if gitpath:
            root = Path(gitpath) / "build/mask"
            root.mkdir(parents=True, exist_ok=True)
            tf = root / Path(name).with_suffix(f".{file_format}")
            tf.parent.mkdir(parents=True, exist_ok=True)
            layout.write(str(tf), save_options)
            file = tf
            delete = False
        else:
            try:
                from __main__ import __file__ as mf
            except ImportError:
                mf = "shell"
            tf = Path(gettempdir()) / (name + f".{file_format}")
            tf.parent.mkdir(parents=True, exist_ok=True)
            layout.write(tf, save_options)
            file = tf
            delete = True
        if use_libraries:
            dir_ = tf.parent
            kcls_ = list(kcls.values())
            kcls_.remove(layout)
            for _kcl in kcls_:
                if save_options.gds2_max_cellname_length:
                    p = (
                        (dir_ / _kcl.name[: save_options.gds2_max_cellname_length])
                        .with_suffix(f".{file_format}")
                        .resolve()
                    )
                else:
                    p = (dir_ / _kcl.name).with_suffix(f".{file_format}").resolve()
                _kcl.write(p, library_save_options)
                kcl_paths.append({"name": _kcl.name, "file": str(p)})
        if technology is None and layout.technology_file is not None:
            technology = layout.technology.name

    elif isinstance(layout, ProtoKCell):
        gitpath = config.project_dir
        if gitpath:
            root = Path(gitpath) / "build/gds"
            root.mkdir(parents=True, exist_ok=True)
            tf = root / Path(name).with_suffix(".oas")
            tf.parent.mkdir(parents=True, exist_ok=True)
            layout.write(str(tf), save_options)
            file = tf
            delete = False
        else:
            try:
                from __main__ import __file__ as mf
            except ImportError:
                mf = "shell"
            tf = Path(gettempdir()) / (name + ".gds")
            tf.parent.mkdir(parents=True, exist_ok=True)
            layout.write(tf, save_options)
            file = tf
            delete = True
        if use_libraries:
            dir_ = tf.parent
            kcls_ = list(kcls.values())
            kcls_.remove(layout.kcl)
            for _kcl in kcls_:
                p = (dir_ / _kcl.name).with_suffix(".oas").resolve()
                _kcl.write(p, library_save_options)
                kcl_paths.append({"name": _kcl.name, "file": str(p)})
        if technology is None and layout.kcl.technology_file is not None:
            technology = layout.kcl.technology.name

    elif isinstance(layout, str | Path):
        file = Path(layout).expanduser().resolve()
    else:
        raise NotImplementedError(
            f"Unknown type {type(layout)} for streaming to KLayout"
        )
    if not file.is_file():
        raise ValueError(f"{file} is not a File")
    logger.debug("klive file: {}", file)
    data_dict = {
        "gds": str(file),
        "keep_position": keep_position,
        "libraries": kcl_paths,
    }

    if lyrdb is not None:
        if isinstance(lyrdb, rdb.ReportDatabase):
            gitpath = config.project_dir
            if gitpath:
                root = Path(gitpath) / "build/mask"
                root.mkdir(parents=True, exist_ok=True)
                tf = root / Path(name).with_suffix(".lyrdb")
                tf.parent.mkdir(parents=True, exist_ok=True)
                lyrdb.save(str(tf))
                lyrdbfile = tf
                delete_lyrdb = False
            else:
                try:
                    from __main__ import __file__ as mf
                except ImportError:
                    mf = "shell"
                tf = Path(gettempdir()) / (name + ".lyrdb")
                tf.parent.mkdir(parents=True, exist_ok=True)
                lyrdb.save(str(tf))
                lyrdbfile = tf
                delete_lyrdb = True
        elif isinstance(lyrdb, str | Path):
            lyrdbfile = Path(lyrdb).expanduser().resolve()
        else:
            raise NotImplementedError(
                f"Unknown type {type(lyrdb)} for streaming to KLayout"
            )
        if not lyrdbfile.is_file():
            raise ValueError(f"{lyrdbfile} is not a File")
        data_dict["lyrdb"] = str(lyrdbfile)

    if l2n is not None:
        if isinstance(l2n, kdb.LayoutToNetlist):
            gitpath = config.project_dir
            if gitpath:
                root = Path(gitpath) / "build/mask"
                root.mkdir(parents=True, exist_ok=True)
                tf = root / Path(name).with_suffix(".l2n")
                tf.parent.mkdir(parents=True, exist_ok=True)
                l2n.write(str(tf))
                l2nfile = tf
                delete_l2n = False
            else:
                try:
                    from __main__ import __file__ as mf
                except ImportError:
                    mf = "shell"
                tf = Path(gettempdir()) / (name + ".l2n")
                tf.parent.mkdir(parents=True, exist_ok=True)
                l2n.write(str(tf))
                l2nfile = tf
                delete_l2n = True
        elif isinstance(l2n, str | Path):
            l2nfile = Path(l2n).expanduser().resolve()
        else:
            raise NotImplementedError(
                f"Unknown type {type(l2n)} for streaming to KLayout"
            )
        if not l2nfile.is_file():
            raise ValueError(f"{lyrdbfile} is not a File")
        data_dict["l2n"] = str(l2nfile)

    if set_technology and technology is not None:
        data_dict["technology"] = technology

    data = json.dumps(data_dict)
    try:
        conn = socket.create_connection(("127.0.0.1", 8082), timeout=0.5)
        data += "\n"
        enc_data = data.encode()
        conn.sendall(enc_data)
        conn.settimeout(5)
    except OSError:
        logger.warning("Could not connect to klive server")
    else:
        msg = ""
        try:
            msg = conn.recv(1024).decode("utf-8")
            try:
                jmsg = json.loads(msg)
                match jmsg["type"]:
                    case "open":
                        info = jmsg.get("info")
                        if info:
                            (
                                logger.info(
                                    "klive v{version}: Opened file '{file}'"
                                    ", Messages: {info}",
                                    version=jmsg["version"],
                                    file=jmsg["file"],
                                    info=info,
                                ),
                            )
                        else:
                            logger.info(
                                "klive v{version}: Opened file '{file}'",
                                version=jmsg["version"],
                                file=jmsg["file"],
                            )
                    case "reload":
                        info = jmsg.get("info")
                        if info:
                            logger.info(
                                "klive v{version}: Reloaded file '{file}'"
                                ", Messages: {info}",
                                version=jmsg["version"],
                                file=jmsg["file"],
                                info=info,
                            )
                        else:
                            logger.info(
                                "klive v{version}: Reloaded file '{file}'",
                                version=jmsg["version"],
                                file=jmsg["file"],
                            )
                # check klive version
                klive_version = [int(s) for s in jmsg["version"].split(".")]
                rec_klive_version = (0, 3, 3)
                klive_ok = True
                for dv in (
                    kv - rkv
                    for kv, rkv in zip(klive_version, rec_klive_version, strict=True)
                ):
                    if dv > 0:
                        break
                    if dv < 0:
                        logger.warning(
                            f"klive is out of date. Installed:{jmsg['version']}/"
                            "Recommended:"
                            f"{'.'.join(str(s) for s in rec_klive_version)}. Please "
                            "update it in KLayout"
                        )
                        klive_ok = False
                        break

                if klive_ok:
                    klayout_version = [
                        int(s) for s in jmsg["klayout_version"].split(".")
                    ]
                    kfactory_version = [int(s) for s in _klayout_version.split(".")]

                    for dv in (
                        kv - kfkv
                        for kv, kfkv in zip(
                            klayout_version, kfactory_version, strict=True
                        )
                    ):
                        if dv > 0:
                            break
                        if dv < 0:
                            if klayout_version < [0, 28, 13]:
                                log = logger.error
                            else:
                                log = logger.debug

                            log(
                                f"KLayout GUI version ({jmsg['klayout_version']}) "
                                "is older than the Python version "
                                f"({_klayout_version}). This may cause issues. Please "
                                "update the GUI to match or exceed the Python version."
                            )
                            break

            except json.JSONDecodeError:
                logger.info(f"Message from klive: {msg}")
        except OSError:
            logger.warning("klive didn't send data, closing")
        finally:
            conn.close()

    if delete:
        Path(file).unlink()
    if delete_lyrdb and lyrdb is not None:
        Path(lyrdbfile).unlink()
    if delete_l2n and l2n is not None:
        Path(l2nfile).unlink()


class ProtoCells(Mapping[int, KC_co], ABC):
    _kcl: KCLayout

    def __init__(self, kcl: KCLayout) -> None:
        self._kcl = kcl

    @abstractmethod
    def __getitem__(self, key: int | str) -> KC_co: ...

    def __delitem__(self, key: int | str) -> None:
        """Delete a cell by key (name or index)."""
        if isinstance(key, int):
            del self._kcl.tkcells[key]
        else:
            cell_index = self._kcl[key].cell_index()
            del self._kcl.tkcells[cell_index]

    @abstractmethod
    def _generate_dict(self) -> dict[int, KC_co]: ...

    def __iter__(self) -> Iterator[int]:
        return iter(self._kcl.tkcells)

    def __len__(self) -> int:
        return len(self._kcl.tkcells)

    def items(self) -> ItemsView[int, KC_co]:
        return self._generate_dict().items()

    def values(self) -> ValuesView[KC_co]:
        return self._generate_dict().values()

    def keys(self) -> KeysView[int]:
        return self._generate_dict().keys()

    def __contains__(self, key: object) -> bool:
        if isinstance(key, int | str):
            return key in self._kcl.tkcells
        return False

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self._kcl.name}, n={len(self)})"

    def __str__(self) -> str:
        return (
            f"{self.__class__.__name__}({self._kcl.name}, {self._kcl.tkcells})".replace(
                "TKCell", (self.__class__.__name__).replace("Cells", "Cell")
            )
        )


class DKCells(ProtoCells[DKCell]):
    def __getitem__(self, key: int | str) -> DKCell:
        return DKCell(base=self._kcl[key].base)

    def _generate_dict(self) -> dict[int, DKCell]:
        return {i: DKCell(base=self._kcl[i].base) for i in self._kcl.tkcells}


class KCells(ProtoCells[KCell]):
    def __getitem__(self, key: int | str) -> KCell:
        return KCell(base=self._kcl[key].base)

    def _generate_dict(self) -> dict[int, KCell]:
        return {i: KCell(base=self._kcl[i].base) for i in self._kcl.tkcells}


def get_cells(
    modules: Iterable[ModuleType], verbose: bool = False
) -> dict[str, Callable[..., KCell]]:
    """Returns KCells (KCell functions) from a module or list of modules.

    Args:
        modules: module or iterable of modules.
        verbose: prints in case any errors occur.
    """
    cells: dict[str, Callable[..., KCell]] = {}
    for module in modules:
        for t in inspect.getmembers(module):
            if callable(t[1]) and t[0] != "partial":
                try:
                    r = inspect.signature(t[1]).return_annotation
                    if r == KCell or (isinstance(r, str) and r.endswith("KCell")):
                        cells[t[0]] = t[1]
                except ValueError:
                    if verbose:
                        logger.error(f"error in {t[0]}")
    return cells


AnyKCell: TypeAlias = ProtoKCell[Any, Any]
AnyTKCell: TypeAlias = ProtoTKCell[Any]


def _get_netlist(
    c: ProtoTKCell[Any],
    l2n_opt: kdb.LayoutToNetlist,
    l2n_elec: kdb.LayoutToNetlist,
    ignore_unnamed: bool = False,
    exclude_purposes: list[str] | None = None,
) -> Netlist:
    opt_circ = l2n_opt.netlist().circuit_by_name(c.name)
    elec_circ = l2n_elec.netlist().circuit_by_name(c.name)
    nl = Netlist(nets=[])
    exclude_purposes = exclude_purposes or []
    keep_name = not ignore_unnamed

    for inst in c.insts:
        if (keep_name or inst.is_named()) and (inst.purpose not in exclude_purposes):
            if inst.cell.has_factory_name():
                nl.create_inst(
                    name=inst.name,
                    kcl=inst.cell.library().name()
                    if inst.cell.is_library_cell()
                    else inst.cell.kcl.name,
                    component=inst.cell.factory_name,
                    settings={
                        k: serialize_setting(v)
                        for k, v in inst.cell.settings.model_dump().items()
                    },
                )
            else:
                nl.create_inst(
                    name=inst.name,
                    kcl=inst.cell.library().name()
                    if inst.cell.is_library_cell()
                    else inst.cell.kcl.name,
                    component=inst.cell.name,
                    settings={
                        k: serialize_setting(v)
                        for k, v in inst.cell.settings.model_dump().items()
                    },
                )

    for net in opt_circ.each_net():
        net_refs: list[PortRef | NetlistPort] = []
        for pinref in net.each_pin():
            p = nl.create_port(pinref.pin().name())
            net_refs.append(p)
        for subc_pin in net.each_subcircuit_pin():
            subc = subc_pin.subcircuit()
            circ_ref = subc.circuit_ref()
            circ = subc.circuit()
            pin = subc_pin.pin()
            recit = kdb.RecursiveInstanceIterator(
                c.kcl.layout, c.kcl.layout.cell(circ.name)
            )
            recit.max_depth = 0
            recit.targets = [circ_ref.cell_index]
            for it in recit.each():
                inst_el = it.current_inst_element()
                if inst_el.specific_cplx_trans() == kdb.ICplxTrans(
                    trans=subc.trans, dbu=c.kcl.dbu
                ):
                    if inst_el.ia() < 0:
                        net_refs.append(PortRef(instance=subc.name, port=pin.name()))
                    else:
                        net_refs.append(
                            PortArrayRef(
                                instance=subc.name,
                                port=pin.name(),
                                ia=inst_el.ia(),
                                ib=inst_el.ib(),
                            )
                        )
                    break
        if len(net_refs) > 1:
            nl.nets.append(Net(net_refs))
    if elec_circ:
        instances_per_transformation: dict[
            kdb.DCplxTrans, list[ProtoTInstance[Any]]
        ] = defaultdict(list)
        for inst in c.insts:
            instances_per_transformation[inst.dcplx_trans].append(inst)
        for net in elec_circ.each_net():
            net_refs = []
            for pinref in net.each_pin():
                p = nl.create_port(pinref.pin().name())
                net_refs.append(p)
            for subc_pin in net.each_subcircuit_pin():
                subc = subc_pin.subcircuit()
                circ_ref = subc.circuit_ref()
                circ = subc.circuit()
                pin = subc_pin.pin()
                recit = kdb.RecursiveInstanceIterator(
                    c.kcl.layout,
                    c.kcl.layout.cell(circ.name),
                    box=kdb.Box(2).transformed(
                        kdb.ICplxTrans(trans=subc.trans, dbu=c.kcl.dbu)
                    ),
                )
                recit.max_depth = 0
                recit.targets = [
                    c.kcl[
                        l2n_elec.internal_layout().cell(circ_ref.cell_index).name
                    ].cell_index()
                ]
                recit.overlapping = True
                for it in recit.each():
                    inst_el = it.current_inst_element()
                    if (
                        inst_el.specific_cplx_trans()
                        == kdb.ICplxTrans(trans=subc.trans, dbu=c.kcl.dbu)
                        and pin.name() != ""
                    ):
                        inst = Instance(kcl=c.kcl, instance=inst_el.inst())
                        purpose = inst.property(PROPID.PURPOSE)
                        name = inst.property(PROPID.NAME)
                        if (name is None and ignore_unnamed) or (
                            purpose in exclude_purposes
                        ):
                            continue
                        if inst_el.ia() < 0:
                            net_refs.append(
                                PortRef(instance=inst.name, port=pin.name())
                            )
                        else:
                            net_refs.append(
                                PortArrayRef(
                                    instance=subc.name,
                                    port=pin.name(),
                                    ia=inst_el.ia(),
                                    ib=inst_el.ib(),
                                )
                            )
                        break
            if len(net_refs) > 1:
                nl.create_net(*net_refs)
    nl.sort()
    return nl
