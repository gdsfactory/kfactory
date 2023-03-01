import abc
import functools
import importlib
import json
import socket
import struct
from abc import ABC, abstractmethod
from dataclasses import InitVar, dataclass

# from enum import IntEnum
from enum import Enum
from hashlib import sha3_512
from inspect import signature
from pathlib import Path
from tempfile import gettempdir
from typing import (  # ParamSpec, # >= python 3.10
    Any,
    Callable,
    Concatenate,
    Generic,
    Hashable,
    Iterable,
    Iterator,
    Optional,
    Protocol,
    Sequence,
    Type,
    TypeAlias,
    TypeGuard,
    TypeVar,
    Union,
    cast,
    overload,
)

# from cachetools import Cache, cached
import cachetools.func
import numpy as np
import ruamel.yaml
from typing_extensions import ParamSpec

from . import kdb, lay
from .config import logger
from .port import rename_clockwise

try:
    from __main__ import __file__ as mf
except ImportError:
    mf = "shell"


KCellParams = ParamSpec("KCellParams")
OP = ParamSpec("OP")


def is_simple_port(port: "Port | DPort | ICplxPort | DCplxPort") -> "TypeGuard[Port]":
    return port.int_based() and not port.complex()


class PortWidthMismatch(ValueError):
    @logger.catch
    def __init__(
        self,
        inst: "Instance",
        other_inst: "Instance | Port | DPort | ICplxPort | DCplxPort",
        p1: "Port | DPort | ICplxPort | DCplxPort",
        p2: "Port | DPort | ICplxPort | DCplxPort",
        *args: Any,
    ):
        if isinstance(other_inst, Instance):
            super().__init__(
                f'Width mismatch between the ports {inst.cell.name}["{p1.name}"] and {other_inst.cell.name}["{p2.name}"] ({p1.width}/{p2.width})',
                *args,
            )
        else:
            super().__init__(
                f'Width mismatch between the ports {inst.cell.name}["{p1.name}"] and Port "{p2.name}" ({p1.width}/{p2.width})',
                *args,
            )


class PortLayerMismatch(ValueError):
    @logger.catch
    def __init__(
        self,
        lib: "KLib",
        inst: "Instance",
        other_inst: "Instance | Port | DPort | ICplxPort | DCplxPort",
        p1: "Port | DPort | ICplxPort | DCplxPort",
        p2: "Port | DPort | ICplxPort | DCplxPort",
        *args: Any,
    ):
        l1 = (
            f"{p1.layer.name}({p1.layer.__int__()})"
            if isinstance(p1.layer, LayerEnum)
            else str(lib.get_info(p1.layer))
        )
        l2 = (
            f"{p2.layer.name}({p2.layer.__int__()})"
            if isinstance(p2.layer, LayerEnum)
            else str(lib.get_info(p2.layer))
        )
        if isinstance(other_inst, Instance):
            super().__init__(
                f'Layer mismatch between the ports {inst.cell.name}["{p1.name}"] and {other_inst.cell.name}["{p2.name}"] ({l1}/{l2})',
                *args,
            )
        else:
            super().__init__(
                f'Layer mismatch between the ports {inst.cell.name}["{p1.name}"] and Port "{p2.name}" ({l1}/{l2})',
                *args,
            )


class PortTypeMismatch(ValueError):
    @logger.catch
    def __init__(
        self,
        inst: "Instance",
        other_inst: "Instance | Port | DPort | ICplxPort | DCplxPort",
        p1: "Port | DPort | ICplxPort | DCplxPort",
        p2: "Port | DPort | ICplxPort | DCplxPort",
        *args: Any,
    ):
        if isinstance(other_inst, Instance):
            super().__init__(
                f'Type mismatch between the ports {inst.cell.name}["{p1.name}"] and {other_inst.cell.name}["{p2.name}"] ({p1.port_type}/{p2.port_type})',
                *args,
            )
        else:
            super().__init__(
                f'Type mismatch between the ports {inst.cell.name}["{p1.name}"] and Port "{p2.name}" ({p1.port_type}/{p2.port_type})',
                *args,
            )


class FrozenError(AttributeError):
    """Raised if a KCell has been frozen and shouldn't be modified anymore"""

    pass


def default_save() -> kdb.SaveLayoutOptions:
    save = kdb.SaveLayoutOptions()
    save.gds2_write_cell_properties = True
    save.gds2_write_file_properties = True
    save.gds2_write_timestamps = False

    return save


class KLib(kdb.Layout):
    """This is a small extension to the ``klayout.db.Layout``. It adds tracking for the :py:class:`~kfactory.kcell.KCell` objects
    instead of only the :py:class:`klayout.db.Cell` objects. Additionally it allows creation and registration through :py:func:`~create_cell`

    All attributes of ``klayout.db.Layout`` are transparently accessible

    Attributes:
        editable: Whether the layout should be opened in editable mode (default: True)
        rename_function: function that takes an Iterable[Port] and renames them
    """

    def __init__(self, editable: bool = True) -> None:
        self.kcells: dict[int, "KCell | CplxKCell"] = {}  # dict[str, "KCell"] = {}
        kdb.Layout.__init__(self, editable)
        self.rename_function: Callable[..., None] = rename_clockwise

    def dup(self, init_cells: bool = True) -> "KLib":
        """Create a duplication of the `~KLib` object

        Args:
            init_cells: initialize the all cells in the new KLib object

        Returns:
            Copy of itself
        """
        klib = KLib()
        klib.assign(super().dup())
        if init_cells:
            klib.kcells = {
                i: KCell(name=kc.name, klib=klib, kdb_cell=klib.cell(kc.name))
                for i, kc in self.kcells.items()
            }
        klib.rename_function = self.rename_function
        return klib

    def create_cell(  # type: ignore[override]
        self,
        name: str,
        *args: Union[
            list[str], list[Union[str, dict[str, Any]]], list[Union[str, str]]
        ],
        allow_duplicate: bool = False,
    ) -> kdb.Cell:
        """Create a new cell in the library. This shouldn't be called manually. The constructor of KCell will call this method.

        Args:
            kcell: The KCell to be registered in the Layout.
            name: The (initial) name of the cell. Can be changed through :py:func:`~update_cell_name`
            allow_duplicate: Allow the creation of a cell with the same name which already is registered in the Layout.\
            This will create a cell with the name :py:attr:`name` + `$1` or `2..n` increasing by the number of existing duplicates
            args: additional arguments passed to :py:func:`~klayout.db.Layout.create_cell`
            kwargs: additional keyword arguments passed to :py:func:`klayout.db.Layout.create_cell`

        Returns:
            klayout.db.Cell: klayout.db.Cell object created in the Layout

        """

        if allow_duplicate or (self.cell(name) is None):
            # self.kcells[name] = kcell
            return kdb.Layout.create_cell(self, name, *args)
        else:
            raise ValueError(
                f"Cellname {name} already exists. Please make sure the cellname is unique or pass `allow_duplicate` when creating the library"
            )

    def delete_cell(self, cell: "KCell | CplxKCell | int") -> None:
        if isinstance(cell, int):
            cell = self[self.cell(cell).name]
        super().delete_cell(cell.cell_index())

    def register_cell(
        self, kcell: "KCell | CplxKCell", allow_reregister: bool = False
    ) -> None:
        """Register an existing cell in the KLib object

        Args:
            kcell: KCell to be registered in the KLib
        """

        def check_name(other: "KCell | CplxKCell") -> bool:
            return other.name == kcell.name

        if (kcell.cell_index() not in self.kcells) or allow_reregister:
            self.kcells[kcell.cell_index()] = kcell
        else:
            raise ValueError(
                "Cannot register a new cell with a name that already exists in the library"
            )

    def __getitem__(self, obj: str | int) -> "KCell | CplxKCell":
        if isinstance(obj, int):
            try:
                return self.kcells[obj]
            except KeyError:
                if self.cell(obj) is None:
                    raise

                c = self.cell(obj)
                return KCell(name=c.name, klib=self, kdb_cell=self.cell(obj))
        else:
            if self.cell(obj) is not None:
                try:
                    return self.kcells[self.cell(obj).cell_index()]
                except KeyError:
                    c = self.cell(obj)
                    return KCell(name=c.name, klib=self, kdb_cell=self.cell(obj))
            from pprint import pformat

            raise ValueError(
                f"Library doesn't have a KCell named {obj}, available KCells are {pformat(sorted([cell.name for cell in self.kcells.values()]))}"
            )

    def read(
        self,
        filename: str | Path,
        options: Optional[kdb.LoadLayoutOptions] = None,
        register_cells: bool = True,
    ) -> kdb.LayerMap:
        if register_cells:
            cells = set(self.cells("*"))
        fn = str(Path(filename).resolve())
        if options is None:
            lm = kdb.Layout.read(self, fn)
        else:
            lm = kdb.Layout.read(self, fn, options)

        if register_cells:
            new_cells = set(self.cells("*")) - cells
            for c in new_cells:
                KCell(kdb_cell=c, klib=self)

        return lm

    def write(  # type: ignore[override]
        self,
        filename: str | Path,
        gzip: bool = False,
        options: kdb.SaveLayoutOptions = default_save(),
    ) -> None:
        return kdb.Layout.write(self, str(filename), options)


klib = (
    KLib()
)  #: Default library object. :py:class:`~kfactory.kcell.KCell` uses this object unless another one is specified in the constructor


def __getattr__(name: str) -> "KLib":
    if name != "library":
        raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
    logger.bind(with_backtrace=True).opt(ansi=True).warning(
        "<red>DeprecationWarning</red>: library has been renamed to klib since version 0.4.0 and library will be removed with 0.5.0, update your code to use klib instead"
    )
    return klib


class LayerEnum(int, Enum):
    """Class for having the layers stored and a mapping int <-> layer,datatype

    This Enum can also be treated as a tuple, i.e. it implements __getitem__ and __len__.

    Attributes:
        layer: layer number
        datatype: layer datatype
        lib: library
    """

    layer: int
    datatype: int

    def __new__(  # type: ignore[misc]
        cls: "LayerEnum",
        layer: int,
        datatype: int,
        lib: KLib = klib,
    ) -> "LayerEnum":
        value = lib.layer(layer, datatype)
        obj: int = int.__new__(cls, value)  # type: ignore[call-overload]
        obj._value_ = value  # type: ignore[attr-defined]
        obj.layer = layer  # type: ignore[attr-defined]
        obj.datatype = datatype  # type: ignore[attr-defined]
        return obj  # type: ignore[return-value]

    def __getitem__(self, key: int) -> int:
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
        return 2

    def __iter__(self) -> Iterator[int]:
        yield from [self.layer, self.datatype]

    def __str__(self) -> str:
        return self.name


TT = TypeVar("TT", bound=kdb.Trans | kdb.DTrans | kdb.ICplxTrans | kdb.DCplxTrans)
TD = TypeVar("TD", bound=kdb.DTrans | kdb.DCplxTrans)
TI = TypeVar("TI", bound=kdb.Trans | kdb.ICplxTrans)
TS = TypeVar("TS", bound=kdb.Trans | kdb.DTrans)
TC = TypeVar("TC", bound=kdb.ICplxTrans | kdb.DCplxTrans)
FI = TypeVar("FI", bound=int | float)

PT = TypeVar("PT", bound="Port | DCplxPort")
CellType = TypeVar("CellType", bound="KCell | CplxKCell")


class PortLike(ABC, Generic[TT, FI]):
    yaml_tag: str
    name: str
    width: FI
    layer: int
    trans: TT
    port_type: str

    def move(
        self,
        origin: tuple[FI, FI],
        destination: tuple[FI, FI] = (cast(FI, 0), cast(FI, 0)),
    ) -> None:
        ...

    @property
    @abstractmethod
    def center(self) -> tuple[FI, FI]:
        ...

    @center.setter
    @abstractmethod
    def center(self, value: tuple[FI, FI]) -> None:
        ...

    @property
    @abstractmethod
    def x(self) -> FI:
        ...

    @property
    @abstractmethod
    def y(self) -> FI:
        ...

    @abstractmethod
    def hash(self) -> bytes:
        ...

    @staticmethod
    @abstractmethod
    def complex() -> bool:
        ...

    @staticmethod
    @abstractmethod
    def int_based() -> bool:
        ...

    @abstractmethod
    def dcplx_trans(self, dbu: float) -> kdb.DCplxTrans:
        ...

    def copy_cplx(self, trans: kdb.DCplxTrans, dbu: float) -> "DCplxPort":
        if self.int_based():
            return DCplxPort(
                width=self.width * dbu,
                layer=self.layer,
                name=self.name,
                port_type=self.port_type,
                trans=trans * self.dcplx_trans(dbu),
            )
        else:
            return DCplxPort(
                width=self.width,
                layer=self.layer,
                name=self.name,
                port_type=self.port_type,
                trans=trans * self.dcplx_trans(dbu),
            )

    @abstractmethod
    def copy(self) -> "PortLike[TT, FI]":
        ...


class IPortLike(PortLike[TI, int]):
    """Protocol for integer based ports"""

    @overload
    def __init__(
        self,
        *,
        name: str,
        trans: TI,
        width: int,
        layer: int,
        port_type: str = "optical",
    ) -> None:
        ...

    @overload
    def __init__(
        self,
        *,
        name: Optional[str] = None,
        port: "IPortLike[TI]",
    ) -> None:
        ...

    @overload
    def __init__(
        self,
        *,
        name: str,
        width: int,
        position: tuple[int, int],
        angle: int,
        layer: int,
        port_type: str = "optical",
        mirror_x: bool = False,
    ) -> None:
        ...

    def __init__(
        self,
        *,
        width: Optional[int] = None,
        layer: Optional[int] = None,
        name: Optional[str] = None,
        port_type: str = "optical",
        trans: Optional[TI | str] = None,
        angle: Optional[int] = None,
        position: Optional[tuple[int, int]] = None,
        mirror_x: bool = False,
        port: "Optional[IPortLike[TI]]" = None,
    ):
        ...

    def __repr__(self) -> str:
        return f"Port(name: {self.name}, trans: {self.trans}, width: {self.width}, layer: {f'{self.layer} ({int(self.layer)})' if isinstance(self.layer, LayerEnum) else str(self.layer)}, port_type: {self.port_type})"

    @property
    def position(self) -> tuple[int, int]:
        """Gives the x and y coordinates of the Port. This is info stored in the transformation of the port.

        Returns:
            position: `(self.trans.disp.x, self.trans.disp.y)`
        """
        return (self.trans.disp.x, self.trans.disp.y)

    @property
    def mirror(self) -> bool:
        """Flag to mirror the transformation. Mirroring is in increments of 45° planes.
        E.g. a rotation of 90° and mirror flag result in a mirroring on the 45° plane.
        """
        return self.trans.is_mirror()

    @property
    def x(self) -> int:
        """Convenience for :py:attr:`Port.trans.disp.x`"""
        return self.trans.disp.x

    @property
    def y(self) -> int:
        """Convenience for :py:attr:`Port.trans.disp.y`"""
        return self.trans.disp.y

    def hash(self) -> bytes:
        """Provides a hash function to provide a (hopefully) unique id of a port

        Returns:
            hash-digest: A byte representation from sha3_512()
        """
        h = sha3_512()
        h.update(self.name.encode("UTF-8"))
        h.update(self.trans.hash().to_bytes(8, "big"))
        h.update(self.width.to_bytes(8, "big"))
        h.update(self.port_type.encode("UTF-8"))
        h.update(self.layer.to_bytes(8, "big"))
        return h.digest()

    @classmethod
    def to_yaml(cls, representer, node):  # type: ignore
        """Internal function used by ruamel.yaml to convert Port to yaml"""
        return representer.represent_mapping(
            cls.yaml_tag,
            {
                "name": node.name,
                "width": node.width,
                "layer": node.layer,
                "port_type": node.port_type,
                "trans": node.trans.to_s(),
            },
        )

    @property
    def center(self) -> tuple[int, int]:
        """Returns port position for gdsfactory compatibility."""
        return self.position

    @center.setter
    def center(self, value: tuple[int, int]) -> None:
        self.trans.disp = kdb.Vector(*value)

    @staticmethod
    def int_based() -> bool:
        return True


class DPortLike(PortLike[TD, float]):
    """Protocol for floating number based ports"""

    @overload
    def __init__(
        self,
        *,
        name: str,
        trans: TD,
        width: float,
        layer: int,
        port_type: str = "optical",
    ) -> None:
        ...

    @overload
    def __init__(
        self,
        *,
        name: Optional[str] = None,
        port: "DPortLike[TD]",
    ) -> None:
        ...

    def __init__(
        self,
        *,
        width: Optional[float] = None,
        layer: Optional[int] = None,
        name: Optional[str] = None,
        port_type: str = "optical",
        trans: Optional[TD | str] = None,
        angle: Optional[int] = None,
        position: Optional[tuple[float, float]] = None,
        mirror_x: bool = False,
        port: "Optional[DPortLike[TD]]" = None,
    ):
        ...

    def __repr__(self) -> str:
        return f"Port(name: {self.name}, trans: {self.trans}, width: {self.width}, layer: {f'{self.layer} ({int(self.layer)})' if isinstance(self.layer, LayerEnum) else str(self.layer)}, port_type: {self.port_type})"

    @property
    def position(self) -> tuple[float, float]:
        """Gives the x and y coordinates of the Port. This is info stored in the transformation of the port.

        Returns:
            position: `(self.trans.disp.x, self.trans.disp.y)`
        """
        return (self.trans.disp.x, self.trans.disp.y)

    @property
    def mirror(self) -> bool:
        """Flag to mirror the transformation. Mirroring is in increments of 45° planes.
        E.g. a rotation of 90° and mirror flag result in a mirroring on the 45° plane.
        """
        return self.trans.is_mirror()

    @property
    def x(self) -> float:
        """Convenience for :py:attr:`Port.trans.disp.x`"""
        return self.trans.disp.x

    @property
    def y(self) -> float:
        """Convenience for :py:attr:`Port.trans.disp.y`"""
        return self.trans.disp.y

    def hash(self) -> bytes:
        """Provides a hash function to provide a (hopefully) unique id of a port

        Returns:
            hash-digest: A byte representation from sha3_512()
        """
        h = sha3_512()
        h.update(self.name.encode("UTF-8"))
        h.update(self.trans.hash().to_bytes(8, "big"))
        h.update(self.width.hex().encode("UTF-8"))
        h.update(self.port_type.encode("UTF-8"))
        h.update(self.layer.to_bytes(8, "big"))
        return h.digest()

    @classmethod
    def to_yaml(cls, representer, node):  # type: ignore
        """Internal function used by ruamel.yaml to convert Port to yaml"""
        return representer.represent_mapping(
            cls.yaml_tag,
            {
                "name": node.name,
                "width": node.width,
                "layer": node.layer,
                "port_type": node.port_type,
                "trans": node.trans.to_s(),
            },
        )

    @property
    def center(self) -> tuple[float, float]:
        """Returns port position for gdsfactory compatibility."""
        return self.position

    @center.setter
    def center(self, value: tuple[float, float]) -> None:
        self.trans.disp = kdb.DVector(*value)

    @staticmethod
    def int_based() -> bool:
        return False


class SPortLike(PortLike[TS, Any]):
    """Protocol for simple transformation based ports"""

    @property
    def angle(self) -> int:
        """Angle of the transformation. In the range of [0,1,2,3] which are increments in 90°. Not to be confused with `rot`
        of the transformation which keeps additional info about the mirror flag."""
        return self.trans.angle

    @property
    def orientation(self) -> float:
        """Returns orientation in degrees for gdsfactory compatibility."""
        return self.trans.angle * 90

    @orientation.setter
    def orientation(self, value: int) -> None:
        self.trans.angle = int(value // 90)

    @staticmethod
    def complex() -> bool:
        return False


class CPortLike(PortLike[TC, Any]):
    """Protocol for complex transformation based ports"""

    trans: TC

    @property
    def angle(self) -> float:
        """Angle of the transformation. In the range of [0,1,2,3] which are increments in 90°. Not to be confused with `rot`
        of the transformation which keeps additional info about the mirror flag."""
        return self.trans.angle

    @property
    def orientation(self) -> float:
        """Returns orientation in degrees for gdsfactory compatibility."""
        return self.trans.angle

    @orientation.setter
    def orientation(self, value: float) -> None:
        self.trans.angle = value

    @staticmethod
    def complex() -> bool:
        return True


class Port(IPortLike[kdb.Trans], SPortLike[kdb.Trans]):
    """A port is similar to a pin in electronics. In addition to the location and layer
    that defines a pin, a port also contains an orientation and a width. This can be fully represented with a transformation, integer and layer_index.
    """

    yaml_tag = "!Port"
    name: str
    width: int
    layer: int
    trans: kdb.Trans
    port_type: str

    def __init__(
        self,
        *,
        width: Optional[int] = None,
        layer: Optional[int] = None,
        name: Optional[str] = None,
        port_type: str = "optical",
        trans: Optional[kdb.Trans | str] = None,
        angle: Optional[int] = None,
        position: Optional[tuple[int, int]] = None,
        mirror_x: bool = False,
        port: Optional["Port"] = None,
    ):
        if port is not None:
            self.name = port.name if name is None else name
            self.trans = port.trans.dup()
            self.port_type = port.port_type
            self.layer = port.layer
            self.width = port.width
        elif name is None or width is None or layer is None:
            raise ValueError("name, width, layer must be given if the 'port is None'")
        else:
            self.name = name
            self.width = width
            self.layer = layer
            self.port_type = port_type
            if trans is not None:
                self.trans = (
                    kdb.Trans.from_s(trans) if isinstance(trans, str) else trans.dup()
                )
            elif angle is None or position is None:
                raise ValueError(
                    "angle and position must be given if creating a gdsfactory like port"
                )
            else:
                self.trans = kdb.Trans(angle, mirror_x, kdb.Vector(*position))

    def move(
        self, origin: tuple[int, int], destination: Optional[tuple[int, int]] = None
    ) -> None:
        """Convenience from the equivalent of gdsfactory. Moves the"""
        dest = kdb.Vector(*(origin if destination is None else destination))
        org = kdb.Vector(0, 0) if destination is None else kdb.Vector(*origin)

        self.trans = self.trans * kdb.Trans(dest - org)

    @classmethod
    def from_yaml(cls: "Type[Port]", constructor, node) -> "Port":  # type: ignore
        """Internal function used by the placer to convert yaml to a Port"""
        d = dict(constructor.construct_pairs(node))
        return cls(**d)

    def rotate(self, angle: int) -> None:
        """Rotate the Port

        Args:
            angle: The angle to rotate in increments of 90°
        """
        self.trans = self.trans * kdb.Trans(angle, False, 0, 0)

    def copy(self, trans: kdb.Trans = kdb.Trans.R0) -> "Port":
        """Get a copy of a port

        Args:
            trans: an optional transformation applied to the port to be copied

        Returns:
            port (:py:class:`Port`): a copy of the port
        """
        _trans = trans * self.trans
        return Port(
            name=self.name,
            trans=_trans,
            layer=self.layer,
            port_type=self.port_type,
            width=self.width,
        )

    def dcplx_trans(self, dbu: float) -> kdb.DCplxTrans:
        return kdb.DCplxTrans(self.trans.to_dtype(dbu))


class DPort(DPortLike[kdb.DTrans], SPortLike[kdb.DTrans]):
    """A port is similar to a pin in electronics. In addition to the location and layer
    that defines a pin, a port also contains an orientation and a width. This can be fully represented with a transformation, integer and layer_index.
    """

    yaml_tag = "!DPort"
    name: str
    width: float
    layer: int
    trans: kdb.DTrans
    port_type: str

    def __init__(
        self,
        *,
        width: Optional[float] = None,
        layer: Optional[int] = None,
        name: Optional[str] = None,
        port_type: str = "optical",
        trans: Optional[kdb.DTrans | str] = None,
        angle: Optional[int] = None,
        position: Optional[tuple[float, float]] = None,
        mirror_x: bool = False,
        port: Optional["DPort"] = None,
    ):
        if port is not None:
            self.name: str = port.name if name is None else name
            self.trans: kdb.DTrans = port.trans.dup()
            self.port_type: str = port.port_type
            self.layer: int = port.layer
            self.width: float = port.width
        elif name is None or width is None or layer is None:
            raise ValueError("name, width, layer must be given if the 'port is None'")
        else:
            self.name = name
            self.width = width
            self.layer = layer
            self.port_type = port_type
            if trans is not None:
                self.trans = (
                    kdb.DTrans.from_s(trans) if isinstance(trans, str) else trans.dup()
                )
            elif angle is None or position is None:
                raise ValueError(
                    "angle and position must be given if creating a gdsfactory like port"
                )
            else:
                self.trans = kdb.DTrans(angle, mirror_x, *position)

    def move(
        self,
        origin: tuple[float, float],
        destination: Optional[tuple[float, float]] = None,
    ) -> None:
        """Convenience from the equivalent of gdsfactory. Moves the"""
        dest = kdb.DVector(*(origin if destination is None else destination))
        org = kdb.DVector(0, 0) if destination is None else kdb.DVector(*origin)

        self.trans = self.trans * kdb.DTrans(dest - org)

    @classmethod
    def from_yaml(cls: "Type[DPort]", constructor: Any, node: Any) -> "DPort":
        """Internal function used by the placer to convert yaml to a Port"""
        d = dict(constructor.construct_pairs(node))
        return cls(**d)

    def rotate(self, angle: int) -> None:
        """Rotate the Port

        Args:
            angle: The angle to rotate in increments of 90°
        """
        self.trans = self.trans * kdb.DTrans(angle, False, 0, 0)

    def copy(self, trans: kdb.DTrans = kdb.DTrans.R0) -> "DPort":
        """Get a copy of a port

        Args:
            trans: an optional transformation applied to the port to be copied

        Returns:
            port (:py:class:`Port`): a copy of the port
        """
        _trans = trans * self.trans
        return DPort(
            name=self.name,
            trans=_trans,
            layer=self.layer,
            port_type=self.port_type,
            width=self.width,
        )

    def dcplx_trans(self, dbu: float) -> kdb.DCplxTrans:
        return kdb.DCplxTrans(self.trans)


class ICplxPort(IPortLike[kdb.ICplxTrans], CPortLike[kdb.ICplxTrans]):
    """A port is similar to a pin in electronics. In addition to the location and layer
    that defines a pin, a port also contains an orientation and a width. This can be fully represented with a transformation, integer and layer_index.
    """

    yaml_tag = "!ICplxPort"
    name: str
    width: int
    layer: int
    trans: kdb.ICplxTrans
    port_type: str

    def __init__(
        self,
        *,
        width: Optional[int] = None,
        layer: Optional[int] = None,
        name: Optional[str] = None,
        port_type: str = "optical",
        trans: Optional[kdb.ICplxTrans | str] = None,
        angle: Optional[int] = None,
        position: Optional[tuple[int, int]] = None,
        mirror_x: bool = False,
        port: Optional["ICplxPort"] = None,
    ):
        if port is not None:
            self.name = port.name if name is None else name
            self.trans = port.trans.dup()
            self.port_type = port.port_type
            self.layer = port.layer
            self.width = port.width
        elif name is None or width is None or layer is None:
            raise ValueError("name, width, layer must be given if the 'port is None'")
        else:
            self.name = name
            self.width = width
            self.layer = layer
            self.port_type = port_type
            if trans is not None:
                self.trans = (
                    kdb.ICplxTrans.from_s(trans)
                    if isinstance(trans, str)
                    else trans.dup()
                )
            elif angle is None or position is None:
                raise ValueError(
                    "angle and position must be given if creating a gdsfactory like port"
                )
            else:
                self.trans = kdb.ICplxTrans(1, angle, mirror_x, *position)

    def move(
        self,
        origin: tuple[int, int],
        destination: Optional[tuple[int, int]] = None,
    ) -> None:
        """Convenience from the equivalent of gdsfactory. Moves the"""
        dest = kdb.Vector(*(origin if destination is None else destination))
        org = kdb.Vector(0, 0) if destination is None else kdb.Vector(*origin)

        self.trans = self.trans * kdb.ICplxTrans(dest - org)

    @classmethod
    def from_yaml(cls: "Type[ICplxPort]", constructor: Any, node: Any) -> "ICplxPort":
        """Internal function used by the placer to convert yaml to a Port"""
        d = dict(constructor.construct_pairs(node))
        return cls(**d)

    def rotate(self, angle: int) -> None:
        """Rotate the Port

        Args:
            angle: The angle to rotate in increments of 90°
        """
        self.trans = self.trans * kdb.ICplxTrans(1, angle, False, 0, 0)

    def copy(self, trans: kdb.ICplxTrans = kdb.ICplxTrans.R0) -> "ICplxPort":
        """Get a copy of a port

        Args:
            trans: an optional transformation applied to the port to be copied

        Returns:
            port (:py:class:`Port`): a copy of the port
        """
        _trans = trans * self.trans
        return ICplxPort(
            name=self.name,
            trans=_trans,
            layer=self.layer,
            port_type=self.port_type,
            width=self.width,
        )

    def dcplx_trans(self, dbu: float) -> kdb.DCplxTrans:
        return self.trans.to_itrans(dbu)


class DCplxPort(DPortLike[kdb.DCplxTrans], CPortLike[kdb.DCplxTrans]):
    """A port is similar to a pin in electronics. In addition to the location and layer
    that defines a pin, a port also contains an orientation and a width. This can be fully represented with a transformation, integer and layer_index.
    """

    yaml_tag = "!DCplxPort"
    name: str
    width: float
    layer: int
    trans: kdb.DCplxTrans
    port_type: str

    def __init__(
        self,
        *,
        width: Optional[float] = None,
        layer: Optional[int] = None,
        name: Optional[str] = None,
        port_type: str = "optical",
        trans: Optional[kdb.DCplxTrans | str] = None,
        angle: Optional[float] = None,
        position: Optional[tuple[float, float]] = None,
        mirror_x: bool = False,
        port: Optional["DCplxPort"] = None,
    ):
        if port is not None:
            self.name: str = port.name if name is None else name
            self.trans: kdb.DCplxTrans = port.trans.dup()
            self.port_type: str = port.port_type
            self.layer: int = port.layer
            self.width: float = port.width
        elif name is None or width is None or layer is None:
            raise ValueError("name, width, layer must be given if the 'port is None'")
        else:
            self.name = name
            self.width = width
            self.layer = layer
            self.port_type = port_type
            if trans is not None:
                self.trans = (
                    kdb.DCplxTrans.from_s(trans)
                    if isinstance(trans, str)
                    else trans.dup()
                )
            elif angle is None or position is None:
                raise ValueError(
                    "angle and position must be given if creating a gdsfactory like port"
                )
            else:
                self.trans = kdb.DCplxTrans(1, angle, mirror_x, *position)

    def move(
        self,
        origin: tuple[float, float],
        destination: Optional[tuple[float, float]] = None,
    ) -> None:
        """Convenience from the equivalent of gdsfactory. Moves the"""
        dest = kdb.DVector(*(origin if destination is None else destination))
        org = kdb.DVector(0, 0) if destination is None else kdb.DVector(*origin)

        self.trans = self.trans * kdb.DCplxTrans(dest - org)

    @classmethod
    def from_yaml(
        cls: "Callable[..., DCplxPort]", constructor: Any, node: Any
    ) -> "DCplxPort":
        """Internal function used by the placer to convert yaml to a Port"""
        d = dict(constructor.construct_pairs(node))
        return cls(**d)

    def rotate(self, angle: int) -> None:
        """Rotate the Port

        Args:
            angle: The angle to rotate in increments of 90°
        """
        self.trans = self.trans * kdb.DCplxTrans(1, angle, False, 0, 0)

    def copy(self, trans: kdb.DCplxTrans = kdb.DCplxTrans.R0) -> "DCplxPort":
        """Get a copy of a port

        Args:
            trans: an optional transformation applied to the port to be copied

        Returns:
            port (:py:class:`Port`): a copy of the port
        """
        _trans = trans * self.trans
        return DCplxPort(
            name=self.name,
            trans=_trans,
            layer=self.layer,
            port_type=self.port_type,
            width=self.width,
        )

    def dcplx_trans(self, dbu: float) -> kdb.DCplxTrans:
        return self.trans.dup()


class ABCKCell(kdb.Cell, ABC, Generic[PT]):

    """Derived from :py:class:`klayout.db.Cell`. Additionally to a standard cell, this one will keep track of :py:class:`Port` and allow to store metadata in a dictionary

    Attributes:
        ports (:py:class:`Ports`):  Contains all the ports of the cell and makes them accessible
        insts (:py:class:`list`[:py:class:`Instance`]): All instances intantiated in this KCell
        settings (:py:class:`dict`): Dictionary containing additional metadata of the KCell. Can be autopopulated by :py:func:`autocell`
        _kdb_cell (:py:class:`klayout.db.Cell`): Internal reference to the :py:class:`klayout.db.Cell` object. Not intended for direct access
    """

    yaml_tag: str = "!NotImplemented"
    _ports: "Ports | CplxPorts"
    complex: bool

    def __new__(
        cls,
        name: Optional[str] = None,
        klib: KLib = klib,
        library: Optional[KLib] = None,
        kdb_cell: Optional[kdb.Cell] = None,
    ) -> "KCell":
        """Create a KLayout cell and change its class to KCell

        Args:
            name: name of the cell, if `None`, it will set the name to "Unnamed_"
            library: KLib object that stores the layout and metadata about the KCells
            kdb_cell
        """

        if library is not None:
            klib = library

        if kdb_cell is None:
            _name = "Unnamed_" if name is None else name
            cell = klib.create_cell(
                name=_name,
            )
        else:
            cell = kdb_cell
        cell.__class__ = cls
        return cell  # type: ignore[return-value]

    def __init__(
        self,
        name: Optional[str] = None,
        klib: KLib = klib,
        library: Optional[KLib] = None,
        kdb_cell: Optional[kdb.Cell] = None,
    ) -> None:
        self.klib = klib
        # TODO: Remove with 0.5.0
        if library is not None:
            logger.bind(with_backtrace=True).opt(ansi=True).warning(
                "<red>DeprecationWarning</red>: library will be deprecated in 0.5.0, use klib instead"
            )
            self.klib = library
        if name is None and kdb_cell is None:
            self.name = f"Unnamed_{self.cell_index()}"
        self.insts: list[Instance] = []
        self.settings: dict[str, Any] = {}
        self._locked = False
        self.info: dict[str, Any] = {}

    @property
    def ports(self) -> "Ports | CplxPorts":
        return self._ports

    @ports.setter
    def ports(self, new_ports: "InstancePorts | Ports | CplxPorts") -> None:
        self._ports = new_ports.copy()

    @overload
    def create_port(
        self,
        *,
        name: str,
        trans: kdb.Trans,
        width: int,
        layer: int | LayerEnum,
        port_type: str = "optical",
    ) -> None:
        ...

    @overload
    def create_port(
        self,
        *,
        name: Optional[str] = None,
        port: Port,
    ) -> None:
        ...

    @overload
    def create_port(
        self,
        *,
        name: str,
        width: int,
        position: tuple[int, int],
        angle: int,
        layer: int | LayerEnum,
        port_type: str = "optical",
        mirror_x: bool = False,
    ) -> None:
        ...

    def create_port(self, **kwargs: Any) -> None:
        """Create a new port. Equivalent to :py:attr:`~add_port(Port(...))`"""
        self.ports.create_port(**kwargs)

    @abstractmethod
    def add_port(self, port: PortLike[TT, FI], name: Optional[str] = None) -> None:
        """Add an existing port. E.g. from an instance to propagate the port

        Args:
            port: The port to add. Port should either be a :py:class:`~Port`, or will be converted to an integer based port with 90° increment
            name: Overwrite the name of the port
        """
        ...

    @overload
    def create_inst(
        self,
        cell: "KCell",
        trans: kdb.Trans | kdb.Vector = kdb.Trans.R0,
        a: Optional[kdb.Vector] = None,
        b: kdb.Vector = kdb.Vector(),
        na: int = 1,
        nb: int = 1,
    ) -> "Instance":
        ...

    @overload
    def create_inst(
        self,
        cell: "CplxKCell",
        trans: kdb.DCplxTrans | kdb.DVector = kdb.DCplxTrans.R0,
        a: Optional[kdb.DVector] = None,
        b: kdb.DVector = kdb.DVector(),
        na: int = 1,
        nb: int = 1,
    ) -> "Instance":
        ...

    def create_inst(
        self,
        cell: CellType,
        trans: kdb.Trans | kdb.DCplxTrans | kdb.Vector | kdb.DVector = kdb.Trans(),
        a: Optional[kdb.Vector | kdb.DVector] = None,
        b: kdb.Vector | kdb.DVector = kdb.Vector(),
        na: int = 1,
        nb: int = 1,
    ) -> "Instance":
        """Add an instance of another KCell

        Args:
            cell: The cell to be added
            trans: The transformation applied to the reference

        Returns:
            :py:class:`~Instance`: The created instance
        """
        if isinstance(cell, KCell):
            ca = (
                self.insert(kdb.CellInstArray(cell, trans))  # type: ignore[arg-type]
                if a is None
                else self.insert(kdb.CellInstArray(cell, trans, a, b, na, nb))  # type: ignore[arg-type]
            )
        elif a is None:
            ca = self.insert(kdb.DCellInstArray(cell, trans))  # type: ignore[arg-type]
        else:
            ca = self.insert(kdb.DCellInstArray(cell, trans, a, b, na, nb))  # type: ignore[arg-type]

        inst = Instance(cell, ca)  # type: ignore[misc]
        self.insts.append(inst)
        return inst

    def _kdb_copy(self) -> kdb.Cell:
        return kdb.Cell.dup(self)

    def layer(self, *args: Any, **kwargs: Any) -> int:
        """Get the layer info, convenience for klayout.db.Layout.layer"""
        return self.klib.layer(*args, **kwargs)

    def __lshift__(self, cell: CellType) -> "Instance":
        """Convenience function for :py:attr:"~create_inst(cell)`

        Args:
            cell: The cell to be added as an instance
        """
        return self.create_inst(cell)  # type: ignore[arg-type]

    def hash(self) -> bytes:
        """Provide a unique hash of the cell"""
        h = sha3_512()
        h.update(self.name.encode("ascii", "ignore"))

        for l in self.layout().layer_indexes():
            h.update(l.to_bytes(8, "big"))
            for shape in self.shapes(l).each(kdb.Shapes.SRegions):
                h.update(shape.polygon.hash().to_bytes(8, "big"))
            for shape in self.shapes(l).each(kdb.Shapes.STexts):
                h.update(shape.text.hash().to_bytes(8, "big"))
        port_hashs = list(sorted(p.hash() for p in self.ports._ports))
        for _hash in port_hashs:
            h.update(_hash)
        insts_hashs = list(sorted(inst.hash() for inst in self.insts))
        for _hash in insts_hashs:
            h.update(_hash)
        return h.digest()

    def autorename_ports(
        self, rename_func: Optional[Callable[..., None]] = None
    ) -> None:
        """Rename the ports with the schema angle -> "NSWE" and sort by x and y

        Args:
            rename_func: Function that takes Iterable[Port] and renames them. This can of course contain a filter and only rename some of the ports
        """

        if rename_func is None:
            self.klib.rename_function(self.ports._ports)
        else:
            rename_func(self.ports._ports)

    def flatten(self, prune: bool = True, merge: bool = True) -> None:  # type: ignore[override]
        """Flatten the cell. Pruning will delete the klayout.db.Cell if unused, but might cause artifacts at the moment

        Args:
            prune: Delete unused child cells if they aren't used in any other KCell
            merge: Merge the shapes on all layers"""
        super().flatten(False)  # prune)
        self.insts = []

        if merge:
            for layer in self.layout().layer_indexes():
                reg = kdb.Region(self.begin_shapes_rec(layer))
                reg.merge()
                self.clear(layer)
                self.shapes(layer).insert(reg)

    def draw_ports(self) -> None:
        """Draw all the ports on their respective :py:attr:`Port.layer`:"""

        for port in self.ports._ports:
            if isinstance(port, IPortLike):
                w = port.width
                poly = kdb.Polygon(
                    [kdb.Point(0, -w // 2), kdb.Point(0, w // 2), kdb.Point(w // 2, 0)]
                )
                self.shapes(port.layer).insert(poly.transformed(port.trans))
                self.shapes(port.layer).insert(
                    kdb.Text(port.name, kdb.Trans.R0).transformed(port.trans)
                )
            elif isinstance(port, DPortLike):
                wd = port.width
                dpoly = kdb.DPolygon(
                    [
                        kdb.DPoint(0, -wd / 2),
                        kdb.DPoint(0, wd / 2),
                        kdb.DPoint(wd / 2, 0),
                    ]
                )
                self.shapes(port.layer).insert(dpoly.transformed(port.trans))
                self.shapes(port.layer).insert(
                    kdb.DText(port.name, kdb.DTrans.R0).transformed(port.trans)
                )

    def write(
        self, filename: str | Path, save_options: kdb.SaveLayoutOptions = default_save()
    ) -> None:
        return super().write(str(filename), save_options)

    @classmethod
    def to_yaml(cls, representer, node):  # type: ignore
        """Internal function to convert the cell to yaml"""
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

    @classmethod
    @abstractmethod
    def from_yaml(
        cls: "Callable[..., ABCKCell[PT]]",
        constructor: Any,
        node: Any,
        verbose: bool = False,
    ) -> "ABCKCell[PT]":
        ...


class KCell(ABCKCell[Port]):
    yaml_tag = "!KCell"

    def __init__(
        self,
        name: Optional[str] = None,
        klib: KLib = klib,
        library: Optional[KLib] = None,
        kdb_cell: Optional[kdb.Cell] = None,
    ):
        super().__init__(name=name, klib=klib, library=library, kdb_cell=kdb_cell)
        self.klib.register_cell(self, allow_reregister=True)
        self.ports: Ports = Ports()
        self.complex = False

    def dup(self) -> "KCell":
        """Copy the full cell

        Returns:
            cell: exact copy of the current cell
        """
        kdb_copy = self._kdb_copy()

        c = KCell(klib=self.klib, kdb_cell=kdb_copy)
        c.ports = self.ports.copy()
        for inst in kdb_copy.each_inst():
            c.insts.append(Instance(cell=self.klib[inst.cell.name], reference=inst))  # type: ignore[misc]
        c._locked = False
        return c

    def __copy__(self) -> "KCell":
        return self.dup()

    def copy(self) -> "KCell":  # type: ignore[override]
        logger.opt(ansi=True).bind(with_backtrace=True).warning(
            "<red>DeprecationWarning:</red> copy will be removed in kfactory 0.5.0. Please use KCell.dup() or copy(KCell) instead"
        )
        return self.dup()

    def add_port(self, port: PortLike[TT, FI], name: Optional[str] = None) -> None:
        """Add an existing port. E.g. from an instance to propagate the port

        Args:
            port: The port to add. Port should either be a :py:class:`~Port`, or will be converted to an integer based port with 90° increment
            name: Overwrite the name of the port
        """

        if isinstance(port, Port):
            self.ports.add_port(port=port, name=name)
        else:
            logger.warning(
                f"Port {str(port)} is not an integer based port, converting to integer based",
            )

            strans = port.trans.s_trans() if port.complex() else port.trans.dup()  # type: ignore[union-attr]
            trans = strans if port.int_based() else strans.to_itype(self.klib.dbu)  # type: ignore[union-attr]
            _port = Port(
                name=port.name,
                width=port.width  # type: ignore[arg-type]
                if port.int_based()
                else int(port.width / self.klib.dbu),
                trans=trans,  # type: ignore[arg-type]
                port_type=port.port_type,
                layer=port.layer,
            )
            self.ports.add_port(port=_port, name=name)

    def add_ports(self, ports: Sequence[PortLike[TT, FI]], prefix: str = "") -> None:
        for port in ports:
            self.add_port(port, name=prefix + port.name)

    @property
    def library(self) -> KLib:  # type: ignore[override]
        logger.opt(ansi=True).warning(
            "<red>DeprecationWarning:</red> library shadows the klayout.dbcore.Cell.library(), please use klib instead. library will be removed in version 0.5.0"
        )
        return self.klib

    @classmethod
    def from_yaml(
        cls: "Callable[..., KCell]",
        constructor: Any,
        node: Any,
        verbose: bool = False,
    ) -> "KCell":
        """Internal function used by the placer to convert yaml to a KCell"""
        d = ruamel.yaml.constructor.SafeConstructor.construct_mapping(
            constructor,
            node,
            deep=True,
        )
        cell = cls(d["name"])
        if verbose:
            print(f"Building {d['name']}")
        cell.ports = d.get("ports", Ports([]))
        cell.settings = d.get("settings", {})
        for inst in d.get("insts", []):
            if "cellname" in inst:
                _cell = cell.klib[inst["cellname"]]
            elif "cellfunction" in inst:
                module_name, fname = inst["cellfunction"].rsplit(".", 1)
                module = importlib.import_module(module_name)
                cellf = getattr(module, fname)
                _cell = cellf(**inst["settings"])
                del module
            else:
                raise NotImplementedError(
                    'To define an instance, either a "cellfunction" or a "cellname" needs to be defined'
                )
            t = inst.get("trans", {})
            if isinstance(t, str):
                cell.create_inst(
                    _cell,  # type: ignore[arg-type]
                    kdb.Trans.from_s(inst["trans"]),
                )
            else:
                angle = t.get("angle", 0)
                mirror = t.get("mirror", False)

                kinst = cell.create_inst(
                    _cell,  # type: ignore[arg-type]
                    kdb.Trans(angle, mirror, 0, 0),
                )

                x0_yml = t.get("x0", DEFAULT_TRANS["x0"])
                y0_yml = t.get("y0", DEFAULT_TRANS["y0"])
                x_yml = t.get("x", DEFAULT_TRANS["x"])
                y_yml = t.get("y", DEFAULT_TRANS["y"])
                margin = t.get("margin", DEFAULT_TRANS["margin"])
                margin_x = margin.get("x", DEFAULT_TRANS["margin"]["x"])  # type: ignore[index]
                margin_y = margin.get("y", DEFAULT_TRANS["margin"]["y"])  # type: ignore[index]
                margin_x0 = margin.get("x0", DEFAULT_TRANS["margin"]["x0"])  # type: ignore[index]
                margin_y0 = margin.get("y0", DEFAULT_TRANS["margin"]["y0"])  # type: ignore[index]
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

                # margins for x0/y0 need to be in with opposite sign of x/y due to them being subtracted later
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
        show(self)

    def _ipython_display_(self) -> None:
        from IPython.display import Image, display  # type: ignore[attr-defined]

        lv = lay.LayoutView()
        l = lv.create_layout(False)

        klib_dup = self.klib.dup(init_cells=False)
        if not isinstance(self, KCell):
            raise NotImplementedError

        kc = klib_dup[self.name]
        kc.ports = self.ports.copy()
        kc.draw_ports()

        lv.active_cellview().layout().assign(klib_dup)
        lv.add_missing_layers()
        lv.active_cellview().cell = kc
        lv.max_hier()
        lv.zoom_fit()
        pb = lv.get_pixels(800, 800)
        # dup.klib.delete_cell(dup.cell_index())
        display(Image(data=pb.to_png_data(), format="png"))  # type: ignore[no-untyped-call]


class CplxKCell(ABCKCell[DCplxPort]):
    """Derived from :py:class:`klayout.db.Cell`. Additionally to a standard cell, this one will keep track of :py:class:`Port` and allow to store metadata in a dictionary

    Attributes:
        ports (:py:class:`Ports`):  Contains all the ports of the cell and makes them accessible
        insts (:py:class:`list`[:py:class:`Instance`]): All instances intantiated in this KCell
        settings (:py:class:`dict`): Dictionary containing additional metadata of the KCell. Can be autopopulated by :py:func:`autocell`
        _kdb_cell (:py:class:`klayout.db.Cell`): Internal reference to the :py:class:`klayout.db.Cell` object. Not intended for direct access
    """

    yaml_tag = "!CplxKCell"

    def __init__(
        self,
        name: Optional[str] = None,
        klib: KLib = klib,
        library: Optional[KLib] = None,
        kdb_cell: Optional[kdb.Cell] = None,
    ):
        super().__init__(name=name, klib=klib, library=library, kdb_cell=kdb_cell)
        self.klib.register_cell(self, allow_reregister=True)
        self.ports: CplxPorts = CplxPorts()
        self.complex = True

    def add_port(self, port: PortLike[TT, FI], name: Optional[str] = None) -> None:
        """Add an existing port. E.g. from an instance to propagate the port

        Args:
            port: The port to add. Port should either be a :py:class:`~Port`, or will be converted to an integer based port with 90° increment
            name: Overwrite the name of the port
        """

        if isinstance(port, DCplxPort):
            self.ports.add_port(port=port, name=name)
        else:
            self.ports.add_port(
                port=port.copy_cplx(kdb.DCplxTrans.R0, self.klib.dbu), name=name
            )

    def dup(self) -> "CplxKCell":
        """Copy the full cell

        Returns:
            cell: exact copy of the current cell
        """
        kdb_copy = self._kdb_copy()

        c = CplxKCell(klib=self.klib, kdb_cell=kdb_copy)
        c.ports = self.ports.copy()
        for inst in kdb_copy.each_inst():
            c.insts.append(Instance(cell=self.klib[inst.cell.name], reference=inst))  # type: ignore[misc]
        c._locked = False
        return c

    def __copy__(self) -> "CplxKCell":
        return self.dup()

    def show(self) -> None:
        show(self)

    @classmethod
    def from_yaml(
        cls: "Callable[..., CplxKCell]",
        constructor: Any,
        node: Any,
        verbose: bool = False,
    ) -> "CplxKCell":
        """Internal function used by the placer to convert yaml to a KCell"""
        d = ruamel.yaml.constructor.SafeConstructor.construct_mapping(
            constructor,
            node,
            deep=True,
        )

        logger.warning(
            "Conversion of YAML to Complex KCells is currently experimental and likely to cause errors or faulty cells"
        )
        cell = cls(d["name"])
        if verbose:
            print(f"Building {d['name']}")
        cell.ports = d.get("ports", Ports([]))
        cell.settings = d.get("settings", {})
        for inst in d.get("insts", []):
            if "cellname" in inst:
                _cell = cell.klib[inst["cellname"]]
            elif "cellfunction" in inst:
                module_name, fname = inst["cellfunction"].rsplit(".", 1)
                module = importlib.import_module(module_name)
                cellf = getattr(module, fname)
                _cell = cellf(**inst["settings"])
                del module
            else:
                raise NotImplementedError(
                    'To define an instance, either a "cellfunction" or a "cellname" needs to be defined'
                )
            t = inst.get("trans", {})
            if isinstance(t, str):
                cell.create_inst(
                    _cell,  # type: ignore[arg-type]
                    kdb.Trans.from_s(inst["trans"]),
                )
            else:
                angle = t.get("angle", 0)
                mirror = t.get("mirror", False)

                kinst = cell.create_inst(
                    _cell,  # type: ignore[arg-type]
                    kdb.Trans(angle, mirror, 0, 0),
                )

                x0_yml = t.get("x0", DEFAULT_TRANS["x0"])
                y0_yml = t.get("y0", DEFAULT_TRANS["y0"])
                x_yml = t.get("x", DEFAULT_TRANS["x"])
                y_yml = t.get("y", DEFAULT_TRANS["y"])
                margin = t.get("margin", DEFAULT_TRANS["margin"])
                margin_x = margin.get("x", DEFAULT_TRANS["margin"]["x"])  # type: ignore[index]
                margin_y = margin.get("y", DEFAULT_TRANS["margin"]["y"])  # type: ignore[index]
                margin_x0 = margin.get("x0", DEFAULT_TRANS["margin"]["x0"])  # type: ignore[index]
                margin_y0 = margin.get("y0", DEFAULT_TRANS["margin"]["y0"])  # type: ignore[index]
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

                # margins for x0/y0 need to be in with opposite sign of x/y due to them being subtracted later
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


class Instance:
    """An Instance of a KCell. An Instance is a reference to a KCell with a transformation

    Attributes:
        cell: The KCell that is referenced
        instance: The internal klayout.db.Instance reference
        ports: Transformed ports of the KCell"""

    yaml_tag = "!Instance"

    def __init__(self, cell: ABCKCell[PT], reference: kdb.Instance) -> None:
        self.cell = cell
        self.instance = reference
        self.ports = InstancePorts(self)

    def hash(self) -> bytes:
        h = sha3_512()
        h.update(self.cell.hash())
        h.update(self.instance.trans.hash().to_bytes(8, "big"))
        return h.digest()

    @overload
    def connect(
        self, portname: str, other: Port | DCplxPort, *, mirror: bool = False
    ) -> None:
        ...

    @overload
    def connect(
        self,
        portname: str,
        other: "Instance",
        other_port_name: str,
        *,
        mirror: bool = False,
    ) -> None:
        ...

    def connect(
        self,
        portname: str,
        other: "Instance | Port | DCplxPort",
        other_port_name: Optional[str] = None,
        *,
        mirror: bool = False,
        allow_width_mismatch: bool = False,
        allow_layer_mismatch: bool = False,
        allow_type_mismatch: bool = False,
    ) -> None:
        """Function to allow to transform this instance so that a port of this instance is connected (same position with 180° turn) to another instance.

        Args:
            portname: The name of the port of this instance to be connected
            other_instance: The other instance or a port
            other_port_name: The name of the other port. Ignored if :py:attr:`~other_instance` is a port.
            mirror: Instead of applying klayout.db.Trans.R180 as a connection transformation, use klayout.db.Trans.M90, which effectively means this instance will be mirrored and connected.
        """
        if isinstance(other, Instance):
            if other_port_name is None:
                raise ValueError(
                    "portname cannot be None if an Instance Object is given. For complex connections (non-90 degree and floating point ports) use connect_cplx instead"
                )
            op = other.ports[other_port_name]
        elif isinstance(other, Port):
            op = other
        else:
            raise ValueError("other_instance must be of type Instance or Port")
        p = self.cell.ports[portname]
        if p.width != op.width and not allow_width_mismatch:
            raise PortWidthMismatch(
                self,
                other,
                p,
                op,
            )
        elif int(p.layer) != int(op.layer) and not allow_layer_mismatch:
            raise PortLayerMismatch(self.cell.klib, self, other, p, op)
        elif p.port_type != op.port_type and not allow_type_mismatch:
            raise PortTypeMismatch(self, other, p, op)
        else:
            if not self.cell.complex:
                if is_simple_port(op):
                    conn_trans = kdb.Trans.M90 if mirror else kdb.Trans.R180
                    self.instance.trans = op.trans * conn_trans * p.trans.inverted()  # type: ignore[operator]
                else:
                    if isinstance(op.trans, DPort):
                        d_conn_trans = kdb.DTrans.M90 if mirror else kdb.DTrans.R180
                        d_p_trans = p.trans.to_dtype(self.cell.klib.dbu).inverted()
                        self.instance.dtrans = op.trans, *d_conn_trans * d_p_trans
                    elif isinstance(op.trans, ICplxPort):
                        icplx_conn_trans = (
                            kdb.ICplxTrans.M90 if mirror else kdb.ICplxTrans.R180
                        )
                        i_p_trans = kdb.ICplxTrans(p.trans).inverted()
                        self.instance.cplx_trans = (
                            op.trans * icplx_conn_trans * i_p_trans
                        )
                    elif isinstance(op.trans, DCplxPort):
                        d_cplx_conn_trans = (
                            kdb.DCplxTrans.M90 if mirror else kdb.DCplxTrans.R180
                        )
                        d_p_trans = kdb.DCplxTrans(
                            p.trans.to_dtype(self.cell.klib.dbu)
                        ).inverted()
                        self.instance.dcplx_trans = (
                            op.trans * d_cplx_conn_trans * d_p_trans
                        )
            else:
                cplx_conn_trans = kdb.DCplxTrans.M90 if mirror else kdb.DCplxTrans.R180

                print()
                self.instance.dcplx_trans = (
                    op.copy_cplx(kdb.DCplxTrans.R0, self.cell.klib.dbu).trans
                    * cplx_conn_trans
                    * p.copy_cplx(
                        kdb.DCplxTrans.R0, self.cell.klib.dbu
                    ).trans.inverted()
                )

    def connect_cplx(
        self,
        portname: str,
        other: "Instance | PortLike[TT, FI]",
        other_port_name: Optional[str] = None,
        *,
        mirror: bool = False,
        allow_width_mismatch: bool = False,
        allow_layer_mismatch: bool = False,
        allow_type_mismatch: bool = False,
    ) -> None:
        if isinstance(other, Instance):
            if other_port_name is None:
                raise ValueError(
                    "portname cannot be None if an Instance Object is given"
                )
            op = other.ports[other_port_name]
        elif isinstance(other, (Port, DPort, ICplxPort, DCplxPort)):
            op = other
        else:
            raise ValueError("other_instance must be of type Instance or Port")
        p = self.cell.ports[portname]
        if p.width != op.width and not allow_width_mismatch:
            if p.int_based() == op.int_based():
                raise PortWidthMismatch(
                    self,
                    other,
                    p,
                    op,
                )
            w1 = p.width * self.cell.klib.dbu if p.int_based() else p.width
            w2 = op.width * self.cell.klib.dbu if op.int_based() else op.width
            if w1 != w2:
                raise PortWidthMismatch(
                    self,
                    other,
                    p,
                    op,
                )
        if int(p.layer) != int(op.layer) and not allow_layer_mismatch:
            raise PortLayerMismatch(self.cell.klib, self, other, p, op)
        if p.port_type != op.port_type and not allow_type_mismatch:
            raise PortTypeMismatch(self, other, p, op)
        # reset the transformation
        self.trans = kdb.Trans.R0
        # apply the transformations piece by piece
        self.transform(op.trans)
        self.transform(kdb.Trans.M90 if mirror else kdb.Trans.R180)
        self.transform(p.trans.inverted())

    def __getattribute__(self, attr_name: str) -> Any:
        return super().__getattribute__(attr_name)

    def _get_attr(self, attr_name: str) -> Any:
        return super().__getattribute__(attr_name)

    def __getattr__(self, attr_name: str) -> Any:
        return kdb.Instance.__getattribute__(self.instance, attr_name)

    def __setattr__(self, attr_name: str, attr_value: Any) -> None:
        if attr_name == "instance":
            super().__setattr__(attr_name, attr_value)
        try:
            kdb.Instance.__setattr__(self._get_attr("instance"), attr_name, attr_value)
        except AttributeError as a:
            super().__setattr__(attr_name, attr_value)

    @classmethod
    def to_yaml(cls, representer, node):  # type: ignore[no-untyped-def]
        d = {"cellname": node.cell.name, "trans": node.instance.trans}
        return representer.represent_mapping(cls.yaml_tag, d)


class Ports:
    """A list of ports. It is not a traditional dictionary. Elements can be retrieved as in a tradional dictionary. But to keep tabs on names etc, the ports are stored as a list

    Attributes:
        _ports: Internal storage of the ports. Normally ports should be retrieved with :py:func:`__getitem__` or with :py:func:`~get_all`
    """

    yaml_tag = "!Ports"

    def __init__(self, ports: Iterable[Port] = []) -> None:
        """Constructor"""
        self._ports: list[Port] = list(ports)
        self.complex = False

    def copy(self) -> "Ports":
        """Get a copy of each port"""
        return Ports(ports=[p.copy() for p in self._ports])

    def contains(self, port: Port) -> bool:
        """Check whether a port is already in the list"""
        return port.hash() in [v.hash() for v in self._ports]

    def __iter__(self) -> Iterator[Port]:
        yield from self._ports

    def each(self) -> Iterator[Port]:
        return self.__iter__()

    def add_port(self, port: Port, name: Optional[str] = None) -> None:
        """Add a port object

        Args:
            port: The port to add
            name: Overwrite the name of the port
        """
        _port = port.copy()
        if name is not None:
            _port.name = name
        if self.get_all().get(_port.name, None) is not None:
            raise ValueError("Port hase already been added to this cell")
        self._ports.append(_port)

    @overload
    def create_port(
        self,
        *,
        name: str,
        trans: kdb.Trans,
        width: int,
        layer: int,
        port_type: str = "optical",
    ) -> Port:
        ...

    @overload
    def create_port(
        self,
        *,
        name: str,
        width: int,
        layer: int,
        position: tuple[int, int],
        angle: int,
        port_type: str = "optical",
    ) -> Port:
        ...

    def create_port(
        self,
        *,
        name: str,
        width: int,
        layer: int,
        port_type: str = "optical",
        trans: Optional[kdb.Trans] = None,
        position: Optional[tuple[int, int]] = None,
        angle: Optional[int] = None,
        mirror_x: bool = False,
    ) -> Port:
        """Create a new port in the list"""

        if trans is not None:
            port = Port(
                name=name, trans=trans, width=width, layer=layer, port_type=port_type
            )
        elif angle is not None and position is not None:
            port = Port(
                name=name,
                width=width,
                layer=layer,
                port_type=port_type,
                angle=angle,
                position=position,
                mirror_x=mirror_x,
            )
        else:
            raise ValueError(
                f"You need to define trans {trans} or angle {angle} and position {position}"
            )

        self._ports.append(port)
        return port

    def get_all(self) -> dict[str, Port]:
        """Get all ports in a dictionary with names as keys"""
        return {v.name: v for v in self._ports}

    def __getitem__(self, key: str) -> Port:
        """Get a specific port by name"""
        try:
            return next(filter(lambda port: port.name == key, self._ports))
        except StopIteration:
            raise ValueError(
                f"{key} is not a port. Available ports: {[v.name for v in self._ports]}"
            )

    def hash(self) -> bytes:
        """Get a hash of the port to compare"""
        h = sha3_512()
        for port in sorted(
            sorted(self._ports, key=lambda port: port.name), key=lambda port: hash(port)
        ):
            h.update(port.name.encode("UTF-8"))
            h.update(port.trans.hash().to_bytes(8, "big"))
            if port.int_based():
                h.update(port.width.to_bytes(8, "big"))
            else:
                h.update(struct.pack("f", port.width))
            h.update(port.port_type.encode("UTF-8"))

        return h.digest()

    def __repr__(self) -> str:
        return repr({v.name: v for v in self._ports})

    @classmethod
    def to_yaml(cls, representer, node):  # type: ignore[no-untyped-def]
        return representer.represent_sequence(
            cls.yaml_tag,
            node._ports,
        )

    @classmethod
    def from_yaml(cls: "Type[Ports]", constructor: Any, node: Any) -> "Ports":
        return cls(constructor.construct_sequence(node))


class CplxPorts:
    """A list of ports. It is not a traditional dictionary. Elements can be retrieved as in a tradional dictionary. But to keep tabs on names etc, the ports are stored as a list

    Attributes:
        _ports: Internal storage of the ports. Normally ports should be retrieved with :py:func:`__getitem__` or with :py:func:`~get_all`
    """

    yaml_tag = "!CplxPorts"

    def __init__(self, ports: Iterable[DCplxPort] = []) -> None:
        """Constructor"""
        self._ports = list(ports)
        self.complex = True

    def copy(self) -> "CplxPorts":
        """Get a copy of each port"""
        return CplxPorts([p.copy() for p in self._ports])

    def contains(self, port: Port) -> bool:
        """Check whether a port is already in the list"""
        return port.hash() in [v.hash() for v in self._ports]

    def __iter__(self) -> Iterator[DCplxPort]:
        yield from self._ports

    def each(self) -> Iterator[DCplxPort]:
        return self.__iter__()

    def add_port(self, port: DCplxPort, name: Optional[str] = None) -> None:
        """Add a port object

        Args:
            port: The port to add
            name: Overwrite the name of the port
        """
        _port = port.copy()
        if name is not None:
            _port.name = name
        if self.get_all().get(_port.name, None) is not None:
            raise ValueError("Port hase already been added to this cell")
        self._ports.append(_port)

    @overload
    def create_port(
        self,
        *,
        name: str,
        trans: kdb.DCplxTrans,
        width: float,
        layer: int,
        port_type: str = "optical",
    ) -> DCplxPort:
        ...

    @overload
    def create_port(
        self,
        *,
        name: str,
        width: float,
        layer: int,
        position: tuple[float, float],
        angle: float,
        port_type: str = "optical",
    ) -> DCplxPort:
        ...

    def create_port(
        self,
        *,
        name: str,
        width: float,
        layer: int,
        port_type: str = "optical",
        trans: Optional[kdb.DCplxTrans] = None,
        position: Optional[tuple[float, float]] = None,
        angle: Optional[float] = None,
        mirror_x: bool = False,
    ) -> DCplxPort:
        """Create a new port in the list"""

        if trans is not None:
            port = DCplxPort(
                name=name, trans=trans, width=width, layer=layer, port_type=port_type
            )
        elif angle is not None and position is not None:
            port = DCplxPort(
                name=name,
                width=width,
                layer=layer,
                port_type=port_type,
                angle=angle,
                position=position,
                mirror_x=mirror_x,
            )
        else:
            raise ValueError(
                f"You need to define trans {trans} or angle {angle} and position {position}"
            )

        self._ports.append(port)
        return port

    def get_all(self) -> dict[str, DCplxPort]:
        """Get all ports in a dictionary with names as keys"""
        return {v.name: v for v in self._ports}

    def __getitem__(self, key: str) -> DCplxPort:
        """Get a specific port by name"""
        try:
            return next(filter(lambda port: port.name == key, self._ports))
        except StopIteration:
            raise ValueError(
                f"{key} is not a port. Available ports: {[v.name for v in self._ports]}"
            )

    def hash(self) -> bytes:
        """Get a hash of the port to compare"""
        h = sha3_512()
        for port in sorted(
            sorted(self._ports, key=lambda port: port.name), key=lambda port: hash(port)
        ):
            h.update(port.name.encode("UTF-8"))
            h.update(port.trans.hash().to_bytes(8, "big"))
            h.update(struct.pack("f", port.width))
            h.update(port.port_type.encode("UTF-8"))
            h.update(port.port_type.encode("UTF-8"))

        return h.digest()

    def __repr__(self) -> str:
        return repr({v.name: v for v in self._ports})

    @classmethod
    def to_yaml(cls, representer, node):  # type: ignore[no-untyped-def]
        return representer.represent_sequence(
            cls.yaml_tag,
            node._ports,
        )

    @classmethod
    def from_yaml(cls: "Type[CplxPorts]", constructor: Any, node: Any) -> "CplxPorts":
        return cls(constructor.construct_sequence(node))


class InstancePorts:
    def __init__(self, instance: Instance) -> None:
        self.cell_ports = instance.cell.ports
        self.instance = instance

    def __getitem__(self, key: str) -> Port | DCplxPort:
        p = self.cell_ports[key]
        return (
            p.copy_cplx(
                trans=self.instance.instance.dcplx_trans,
                dbu=self.instance.cell.klib.dbu,
            )
            if (
                self.instance.instance.is_complex()
                or p.complex()
                or not p.int_based()
                or self.instance.cell.complex
            )
            else p.copy(trans=self.instance.trans)  # type: ignore[arg-type]
        )

    def __iter__(self) -> Iterator[Port | DCplxPort]:
        return (self[port.name] for port in self.cell_ports)

    def __repr__(self) -> str:
        return repr({v: self.__getitem__(v) for v in self.cell_ports.get_all().keys()})

    def get_all(self) -> dict[str, Port | DCplxPort]:
        return {v: self.__getitem__(v) for v in self.cell_ports.get_all().keys()}

    def copy(self) -> Ports | CplxPorts:
        if (
            not self.instance.instance.is_complex()
            and not self.instance.cell.ports.complex
            and not self.instance.cell.complex
        ):
            return Ports(
                [
                    port.copy(trans=self.instance.trans)  # type: ignore[arg-type, misc]
                    for port in self.cell_ports._ports
                ]
            )
        else:
            return CplxPorts(
                [
                    port.copy_cplx(
                        trans=self.instance.cplx_dtrans, dbu=self.instance.cell.klib.dbu
                    )
                    for port in self.cell_ports._ports
                ]
            )


@overload
def autocell(_func: Callable[KCellParams, KCell], /) -> Callable[KCellParams, KCell]:
    ...


@overload
def autocell(
    *,
    set_settings: bool = True,
    set_name: bool = True,
    maxsize: Optional[int] = None,
) -> Callable[[Callable[KCellParams, KCell]], Callable[KCellParams, KCell]]:
    ...


@logger.catch
def autocell(
    _func: Optional[Callable[KCellParams, KCell]] = None,
    /,
    *,
    set_settings: bool = True,
    set_name: bool = True,
    maxsize: Optional[int] = None,
) -> (
    Callable[KCellParams, KCell]
    | Callable[[Callable[KCellParams, KCell]], Callable[KCellParams, KCell]]
):
    """Decorator to cache and auto name the celll. This will use :py:func:`functools.cache` to cache the function call.
    Additionally, if enabled this will set the name and from the args/kwargs of the function and also paste them into a settings dictionary of the :py:class:`~KCell`

    Args:
        set_settings: Copy the args & kwargs into the settings dictionary
        set_name: Auto create the name of the cell to the functionname plus a string created from the args/kwargs
        maxsize: maximum size of cache, cell parameter sets will be evicted if the cell function is called with more different
        parameter sets than there are spaces in the cache, in case there are cell calls with existing parameter set calls
    """

    if maxsize is not None:
        logger.bind(with_backtrace=True).opt(ansi=True).warning(
            "<red>DeprecationWarning</red>: maxsize has no effect on the cache, as it is a simple dict now. Please remove it, the argument will be removed in 0.5.0"
        )

    def decorator_autocell(
        f: Callable[KCellParams, KCell]
    ) -> Callable[KCellParams, KCell]:
        sig = signature(f)

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

            for key, value in params.items():
                if isinstance(value, dict):
                    params[key] = dict_to_frozen_set(value)

            @cachetools.cached(cache=cache)
            @functools.wraps(f)
            def wrapped_cell(
                **params: KCellParams.args,
            ) -> KCell:
                for key, value in params.items():
                    if isinstance(value, frozenset):
                        params[key] = frozenset_to_dict(value)
                cell = f(**params)
                if cell._locked:
                    cell = cell.dup()
                if set_name:
                    name = get_component_name(f.__name__, **params)
                    cell.name = name
                if set_settings:
                    cell.settings.update(params)

                i = 0
                for name, setting in cell.settings.items():
                    while cell.property(i) is not None:
                        i += 1
                    if isinstance(setting, KCell):
                        cell.set_property(i, f"{name}: {setting.name}")
                    else:
                        cell.set_property(i, f"{name}: {str(setting)}")
                    i += 1
                cell._locked = True
                return cell

            return wrapped_cell(**params)

        return wrapper_autocell

    return decorator_autocell if _func is None else decorator_autocell(_func)


def dict_to_frozen_set(d: dict[str, Any]) -> frozenset[tuple[str, Any]]:
    return frozenset(d.items())


def frozenset_to_dict(fs: frozenset[tuple[str, Hashable]]) -> dict[str, Hashable]:
    return dict(fs)


def cell(
    _func: Optional[Callable[..., KCell]] = None,
    *,
    set_settings: bool = True,
    maxsize: int = 512,
) -> (
    Callable[KCellParams, KCell]
    | Callable[[Callable[KCellParams, KCell]], Callable[KCellParams, KCell]]
):
    """Convenience alias for :py:func:`~autocell` with `(set_name=False)`"""
    if _func is None:
        return autocell(set_settings=set_settings, set_name=False)
    else:
        return autocell(_func)


def dict2name(prefix: Optional[str] = None, **kwargs: dict[str, Any]) -> str:
    """returns name from a dict"""
    label = [prefix] if prefix else []
    for key, value in kwargs.items():
        key = join_first_letters(key)
        label += [f"{key.upper()}{clean_value(value)}"]
    _label = "_".join(label)
    return clean_name(_label)


def get_component_name(component_type: str, **kwargs: dict[str, Any]) -> str:
    name = component_type

    if kwargs:
        name += f"_{dict2name(None, **kwargs)}"

    return name


def join_first_letters(name: str) -> str:
    """join the first letter of a name separated with underscores (taper_length -> TL)"""
    return "".join([x[0] for x in name.split("_") if x])


def clean_value(
    value: float | np.float64 | dict[Any, Any] | KCell | Callable[..., Any]
) -> str:
    """returns more readable value (integer)
    if number is < 1:
        returns number units in nm (integer)
    """

    try:
        if isinstance(value, int):  # integer
            return str(value)
        elif type(value) in [float, np.float64]:  # float
            return f"{value:.4f}".replace(".", "p").rstrip("0").rstrip("p")
        elif isinstance(value, list):
            return "_".join(clean_value(v) for v in value)
        elif isinstance(value, tuple):
            return "_".join(clean_value(v) for v in value)
        elif isinstance(value, dict):
            return dict2name(**value)
        elif hasattr(value, "name"):
            return clean_name(value.name)
        elif callable(value):
            return str(value.__name__)
        else:
            return clean_name(str(value))
    except TypeError:  # use the __str__ method
        return clean_name(str(value))


def clean_name(name: str) -> str:
    r"""Ensures that gds cells are composed of [a-zA-Z0-9_\-]::

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


DEFAULT_TRANS: dict[str, Union[str, int, float, dict[str, Union[str, int, float]]]] = {
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
    new_trans: dict[str, Union[str, int, float, dict[str, Union[str, int, float]]]]
) -> None:
    DEFAULT_TRANS.update(new_trans)


def show(
    gds: str | KCell | CplxKCell | Path,
    keep_position: bool = True,
    save_options: kdb.SaveLayoutOptions = default_save(),
) -> None:
    """Show GDS in klayout"""

    delete = False

    if isinstance(gds, (KCell, CplxKCell)):
        _mf = "stdin" if mf == "<stdin>" else mf
        dirpath = Path(gettempdir())
        tf = Path(gettempdir()) / Path(_mf).with_suffix(".gds")
        tf.parent.mkdir(parents=True, exist_ok=True)
        gds.write(str(tf), save_options)
        gds_file = tf
        delete = True
    elif isinstance(gds, (str, Path)):
        gds_file = Path(gds)
    else:
        raise NotImplementedError(f"unknown type {type(gds)} for streaming to KLayout")

    if not gds_file.is_file():
        raise ValueError(f"{gds_file} is not a File")
    data_dict = {
        "gds": str(gds_file),
        "keep_position": keep_position,
    }
    data = json.dumps(data_dict)
    try:
        conn = socket.create_connection(("127.0.0.1", 8082), timeout=0.5)
        data = data + "\n"
        enc_data = data.encode()  # if hasattr(data, "encode") else data
        conn.sendall(enc_data)
        conn.settimeout(5)
    except OSError:
        logger.warning("Could not connect to klive server")
    else:
        msg = ""
        try:
            msg = conn.recv(1024).decode("utf-8")
            logger.info(f"Message from klive: {msg}")
        except OSError:
            logger.warning("klive didn't send data, closing")
        finally:
            conn.close()

    if delete:
        Path(gds_file).unlink()


__all__ = [
    "KCell",
    "Instance",
    "Port",
    "Ports",
    "autocell",
    "cell",
    "library",
    "KLib",
    "default_save",
    "ICplxPort",
    "DCplxPort",
    "DPort",
    "LayerEnum",
]
