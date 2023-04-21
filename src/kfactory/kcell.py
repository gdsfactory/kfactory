"""Core module of kfactory.

Defines the :py:class:`KCell` providing klayout Cells with Ports
and other convenience functions.

:py:class:`Instance` are the kfactory instances used to also acquire
ports etc from instances.

"""

import functools
import importlib
import json
import socket
from collections.abc import Callable, Hashable, Iterable, Iterator

# from enum import IntEnum
from enum import Enum, IntEnum
from hashlib import sha3_512
from inspect import signature
from pathlib import Path
from tempfile import gettempdir
from typing import Any, Literal, cast, overload  # ParamSpec, # >= python 3.10

# from cachetools import Cache, cached
import cachetools.func
import numpy as np
import ruamel.yaml
from typing_extensions import ParamSpec

from . import kdb
from .config import logger
from .port import rename_clockwise

# import struct
# from abc import abstractmethod


try:
    from __main__ import __file__ as mf
except ImportError:
    mf = "shell"


KCellParams = ParamSpec("KCellParams")


class PROPID(IntEnum):
    """Mapping for GDS properties."""

    NAME = 0


class PortWidthMismatch(ValueError):
    """Error thrown when two ports don't have a matching `width`."""

    @logger.catch
    def __init__(
        self,
        inst: "Instance",
        other_inst: "Instance | Port",
        p1: "Port",
        p2: "Port",
        *args: Any,
    ):
        """Throw error for the two ports `p1`/`p1`."""
        if isinstance(other_inst, Instance):
            super().__init__(
                f'Width mismatch between the ports {inst.cell.name}["{p1.name}"]'
                f'and {other_inst.cell.name}["{p2.name}"] ({p1.width}/{p2.width})',
                *args,
            )
        else:
            super().__init__(
                f'Width mismatch between the ports {inst.cell.name}["{p1.name}"]'
                f' and Port "{p2.name}" ({p1.width}/{p2.width})',
                *args,
            )


class PortLayerMismatch(ValueError):
    """Error thrown when two ports don't have a matching `layer`."""

    @logger.catch
    def __init__(
        self,
        lib: "KLib",
        inst: "Instance",
        other_inst: "Instance | Port",
        p1: "Port",
        p2: "Port",
        *args: Any,
    ):
        """Throw error for the two ports `p1`/`p1`."""
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
                f'Layer mismatch between the ports {inst.cell.name}["{p1.name}"]'
                f' and {other_inst.cell.name}["{p2.name}"] ({l1}/{l2})',
                *args,
            )
        else:
            super().__init__(
                f'Layer mismatch between the ports {inst.cell.name}["{p1.name}"]'
                f' and Port "{p2.name}" ({l1}/{l2})',
                *args,
            )


class PortTypeMismatch(ValueError):
    """Error thrown when two ports don't have a matching `port_type`."""

    @logger.catch
    def __init__(
        self,
        inst: "Instance",
        other_inst: "Instance | Port",
        p1: "Port",
        p2: "Port",
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

    return save


class KLib(kdb.Layout):
    """Small extension to the ``klayout.db.Layout``.

    It adds tracking for the :py:class:`~kfactory.kcell.KCell` objects
    instead of only the :py:class:`klayout.db.Cell` objects.
    Additionally it allows creation and registration through :py:func:`~create_cell`

    All attributes of ``klayout.db.Layout`` are transparently accessible

    Attributes:
        editable: Whether the layout should be opened in editable mode (default: True)
        rename_function: function that takes an Iterable[Port] and renames them
    """

    def __init__(self, editable: bool = True) -> None:
        """Crete a library of cells.

        Args:
            editable: Open the KLayout Layout in editable mode if `True`.
        """
        self.kcells: dict[int, "KCell"] = {}
        kdb.Layout.__init__(self, editable)
        self.rename_function: Callable[..., None] = rename_clockwise

    def dup(self, init_cells: bool = True) -> "KLib":
        """Create a duplication of the `~KLib` object.

        Args:
            init_cells: initialize the all cells in the new KLib object

        Returns:
            Copy of itself
        """
        klib = KLib()
        klib.assign(super().dup())
        if init_cells:
            for i, kc in self.kcells.items():
                klib.kcells[i] = KCell(
                    name=kc.name,
                    klib=klib,
                    kdb_cell=klib.cell(kc.name),
                    ports=kc.ports,
                )
        klib.rename_function = self.rename_function
        return klib

    def create_cell(  # type: ignore[override]
        self,
        name: str,
        *args: str,
        allow_duplicate: bool = False,
    ) -> kdb.Cell:
        """Create a new cell in the library.

        This shouldn't be called manually.
        The constructor of KCell will call this method.

        Args:
            kcell: The KCell to be registered in the Layout.
            name: The (initial) name of the cell. Can be changed through
                :py:func:`~update_cell_name`
            allow_duplicate: Allow the creation of a cell with the same name which
                already is registered in the Layout.
                This will create a cell with the name :py:attr:`name` + `$1` or `2..n`
                increasing by the number of existing duplicates
            args: additional arguments passed to
                :py:func:`~klayout.db.Layout.create_cell`

        Returns:
            klayout.db.Cell: klayout.db.Cell object created in the Layout

        """
        if allow_duplicate or (self.cell(name) is None):
            # self.kcells[name] = kcell
            return kdb.Layout.create_cell(self, name, *args)
        else:
            raise ValueError(
                f"Cellname {name} already exists. Please make sure the cellname is"
                " unique or pass `allow_duplicate` when creating the library"
            )

    def delete_cell(self, cell: "KCell | int") -> None:
        """Delete a cell in the klib object."""
        if isinstance(cell, int):
            super().delete_cell(cell)
            del self.kcells[cell]
        else:
            ci = cell.cell_index()
            super().delete_cell(ci)
            del self.kcells[ci]

    def register_cell(self, kcell: "KCell", allow_reregister: bool = False) -> None:
        """Register an existing cell in the KLib object.

        Args:
            kcell: KCell to be registered in the KLib
            allow_reregister: Overwrite the existing KCell registration with this one.
                Doesn't allow name duplication.
        """

        def check_name(other: "KCell") -> bool:
            return other._kdb_cell.name == kcell._kdb_cell.name

        if (kcell.cell_index() not in self.kcells) or allow_reregister:
            self.kcells[kcell.cell_index()] = kcell
        else:
            raise ValueError(
                "Cannot register a new cell with a name that already"
                " exists in the library"
            )

    def __getitem__(self, obj: str | int) -> "KCell":
        """Retrieve a cell by name(str) or index(int).

        Attrs:
            obj: name of cell or cell_index
        """
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
        """Write a GDS file into the existing Layout.

        Args:
            filename: Path of the GDS file.
            gzip: directly make the GDS a .gds.gz file.
            options: KLayout options to load from the GDS. Can determine how merge
                conflicts are handled for example. See
                https://www.klayout.de/doc-qt5/code/class_LoadLayoutOptions.html
        """
        return kdb.Layout.write(self, str(filename), options)


klib = KLib()
"""Default library object.

:py:class:`~kfactory.kcell.KCell` uses this object unless another one is
specified in the constructor."""


class LayerEnum(int, Enum):
    """Class for having the layers stored and a mapping int <-> layer,datatype.

    This Enum can also be treated as a tuple, i.e. it implements __getitem__ and __len__

    Attributes:
        layer: layer number
        datatype: layer datatype
    """

    layer: int
    datatype: int

    def __new__(  # type: ignore[misc]
        cls: "LayerEnum",
        layer: int,
        datatype: int,
        lib: KLib = klib,
    ) -> "LayerEnum":
        """Create a new Enum.

        Because it needs to act like an integer an enum is created and expanded.

        Args:
            layer: Layer number of the layer.
            datatype: Datatype of the layer.
            lib: :py:class:~`KLib` to register the layer to.
        """
        value = lib.layer(layer, datatype)
        obj: int = int.__new__(cls, value)  # type: ignore[call-overload]
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
        return self.name


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
    """

    yaml_tag = "!Port"
    name: str | None
    width: int
    layer: int
    _trans: kdb.Trans | None
    _dcplx_trans: kdb.DCplxTrans | None
    port_type: str

    @overload
    def __init__(
        self,
        *,
        name: str | None = None,
        width: int,
        layer: LayerEnum | int,
        trans: kdb.Trans,
        klib: KLib = klib,
        port_type: str = "optical",
        info: dict[str, Any] = {},
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
        klib: KLib = klib,
        port_type: str = "optical",
        info: dict[str, Any] = {},
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
        klib: KLib = klib,
        info: dict[str, Any] = {},
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
        klib: KLib = klib,
        info: dict[str, Any] = {},
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
        port: "Port | None" = None,
        klib: KLib = klib,
        info: dict[str, Any] = {},
    ):
        """Create a port from dbu or um based units."""
        self.klib = klib
        self.d = DPart(self)
        self.info = info.copy()
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
                assert self.width * self.klib.dbu == float(
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
    def from_yaml(cls: "type[Port]", constructor, node) -> "Port":  # type: ignore
        """Internal function used by the placer to convert yaml to a Port."""
        d = dict(constructor.construct_pairs(node))
        return cls(**d)

    def copy(self, trans: kdb.Trans | kdb.DCplxTrans = kdb.Trans.R0) -> "Port":
        """Get a copy of a port.

        Args:
            trans: an optional transformation applied to the port to be copied

        Returns:
            port (:py:class:`Port`): a copy of the port
        """
        if self._trans:
            if isinstance(trans, kdb.Trans):
                _trans = trans * self.trans
                return Port(
                    name=self.name,
                    trans=_trans,
                    layer=self.layer,
                    port_type=self.port_type,
                    width=self.width,
                    klib=self.klib,
                )
            elif not trans.is_complex():
                _trans = trans.s_trans().to_itype(self.klib.dbu) * self.trans
                return Port(
                    name=self.name,
                    trans=_trans,
                    layer=self.layer,
                    port_type=self.port_type,
                    width=self.width,
                    klib=self.klib,
                )
        if isinstance(trans, kdb.Trans):
            dtrans = kdb.DCplxTrans(trans.to_dtype(self.klib.dbu))
            _dtrans = dtrans * self.dcplx_trans
        else:
            _dtrans = trans * self.dcplx_trans
        return Port(
            name=self.name,
            dcplx_trans=_dtrans,
            dwidth=self.d.width,
            layer=self.layer,
            klib=self.klib,
            port_type=self.port_type,
            info=self.info,
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
            self._dcplx_trans.disp = vec.to_dtype(self.klib.dbu)

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
            self._dcplx_trans.disp = vec.to_dtype(self.klib.dbu)

    @property
    def trans(self) -> kdb.Trans:
        """Simple Transformation of the Port.

        If this is set with the setter, it will overwrite any transformation or
        dcplx transformation
        """
        return self._trans or self.dcplx_trans.s_trans().to_itype(self.klib.dbu)

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
        return self._dcplx_trans or kdb.DCplxTrans(self.trans.to_dtype(self.klib.dbu))

    @dcplx_trans.setter
    def dcplx_trans(self, value: kdb.DCplxTrans) -> None:
        self._dcplx_trans = value.dup()
        self._trans = None

    @property
    def angle(self) -> int:
        """Angle of the transformation.

        In the range of [0,1,2,3] which are increments in 90°. Not to be confused
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


class DPart:
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
            self.parent._trans.disp = vec.to_itype(self.parent.klib.dbu)
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
            self.parent._trans.disp = vec.to_itype(self.parent.klib.dbu)
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
            self.parent._trans.disp = kdb.DVector(*pos).to_itype(self.parent.klib.dbu)
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
        return self.parent.width * self.parent.klib.dbu

    @width.setter
    def width(self, value: float) -> None:
        self.parent.width = int(value / self.parent.klib.dbu)
        assert self.parent.width * self.parent.klib.dbu == float(value), (
            "When converting to dbu the width does not match the desired width"
            f"({self.width} / {value})!"
        )


class KCell:
    """KLayout cell and change its class to KCell.

    A KCell is a dynamic proxy for :py:class:~`kdb.Cell`. It has all the
    attributes of the official KLayout class. Some attributes have been adjusted
    to return KCell specific sub classes. If the function is listed here in the
    docs, they have been adjusted for KFactory specifically. This object will
    transparently proxy to :py:class:`kdb.Cell`. Meaning any attribute not directly
    defined in this class that are available from the KLayout counter part can
    still be accessed. The pure KLayout object can be accessed with
    :py:attr:`KCell._kdb_cell`.

    Attributes:
        klib: Library object that is the manager of the KLayout
            :py:class:`kdb.Layout`
        settings: A dictionary containing settings populated by:py:func:`autocell`
        info: Dictionary for storing additional info if necessary. This is not
            passed to the GDS and therefore not reversible.
        _kdb_cell: Pure KLayout cell object.
        _locked: If set the cell shouldn't be modified anymore.
        ports: Manages the ports of the cell.
    """

    yaml_tag = "!KCell"
    _ports: "Ports"

    def __init__(
        self,
        name: str | None = None,
        klib: KLib = klib,
        kdb_cell: kdb.Cell | None = None,
        ports: "Ports | None" = None,
    ):
        """Constructor of KCell.

        Args:
            name: Name of the cell, if None will autogenerate name to
                "Unnamed_<cell_index>".
            klib: KLib the cell should be attached to.
            kdb_cell: If not `None`, a KCell will be created from and existing
                KLayout Cell
            ports: Attach an existing :py:class:`~Ports` object to the KCell,
                if `None` create an empty one.
        """
        self.klib = klib
        self.insts: Instances = Instances()
        self.settings: dict[str, Any] = {}
        self.info: dict[str, Any] = {}
        self._locked = False
        if name is None:
            _name = "Unnamed_!"
        else:
            _name = name
        self._kdb_cell = kdb_cell or klib.create_cell(_name)
        if _name == "Unnamed_!":
            self._kdb_cell.name = f"Unnamed_{self.cell_index()}"
        self.klib.register_cell(self, allow_reregister=True)
        self.ports: Ports = ports or Ports(self.klib)
        self.complex = False

        if kdb_cell is not None:
            for inst in kdb_cell.each_inst():
                self.insts.append(Instance(self.klib, inst))

    @property
    def name(self) -> str:
        """Name of the KCell."""
        return self._kdb_cell.name

    @name.setter
    def name(self, value: str) -> None:
        self._kdb_cell.name = value

    @property
    def prop_id(self) -> int:
        """Gets the properties ID associated with the cell."""
        return self._kdb_cell.prop_id

    @prop_id.setter
    def prop_id(self, value: int) -> None:
        self._kdb_cell.prop_id = value

    @property
    def ghost_cell(self) -> bool:
        """Returns a value indicating whether the cell is a "ghost cell"."""
        return self._kdb_cell.ghost_cell

    @ghost_cell.setter
    def ghost_cell(self, value: bool) -> None:
        self._kdb_cell.ghost_cell = value

    def __getattr__(self, name):  # type: ignore[no-untyped-def]
        """If KCell doesn't have an attribute, look in the KLayout Cell."""
        return getattr(self._kdb_cell, name)

    def dup(self) -> "KCell":
        """Copy the full cell.

        Sets :py:attr:_locked to `False`

        Returns:
            cell: Exact copy of the current cell.
                The name will have `$1` as duplicate names are not allowed
        """
        kdb_copy = self._kdb_copy()

        c = KCell(klib=self.klib, kdb_cell=kdb_copy)
        c.ports = self.ports.copy()
        for inst in kdb_copy.each_inst():
            c.insts.append(Instance(self.klib, instance=inst))
        c._locked = False
        return c

    def __copy__(self) -> "KCell":
        """Enables use of :py:func:`copy.copy` and :py:func:`copy.deep_copy`."""
        return self.dup()

    def add_port(
        self, port: Port, name: str | None = None, keep_mirror: bool = False
    ) -> None:
        """Add an existing port. E.g. from an instance to propagate the port.

        Args:
            port: The port to add. Port should either be a :py:class:`~Port`,
                or will be converted to an integer based port with 90° increment
            name: Overwrite the name of the port
            keep_mirror: Keep the mirror part of the transformation of a port if
                `True`, else set the mirror flag to `False`.
        """
        self.ports.add_port(port=port, name=name)

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
        self.ports.add_ports(ports=ports, prefix=prefix, keep_mirror=keep_mirror)

    @classmethod
    def from_yaml(
        cls: "Callable[..., KCell]",
        constructor: Any,
        node: Any,
        verbose: bool = False,
    ) -> "KCell":
        """Internal function used by the placer to convert yaml to a KCell."""
        d = ruamel.yaml.constructor.SafeConstructor.construct_mapping(
            constructor,
            node,
            deep=True,
        )
        cell = cls(d["name"])
        if verbose:
            print(f"Building {d['name']}")
        cell.ports = d.get("ports", Ports(ports=[], klib=cell.klib))
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

    def _ipython_display_(self) -> None:
        """Display a cell in a Jupyter Cell.

        Usage: Pass the kcell variable as an argument in the cell at the end
        """
        from .widgets.interactive import display_kcell

        display_kcell(self)

    @property
    def ports(self) -> "Ports":
        """Ports associated with the cell."""
        return self._ports

    @ports.setter
    def ports(self, new_ports: "InstancePorts | Ports") -> None:
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
    ) -> None:
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
    ) -> None:
        ...

    @overload
    def create_port(
        self,
        *,
        name: str | None = None,
        port: Port,
    ) -> None:
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
    ) -> None:
        ...

    def create_port(self, **kwargs: Any) -> None:
        """Proxy for :py:func:`Ports.create_port`."""
        self.ports.create_port(**kwargs)

    @overload
    def create_inst(
        self,
        cell: "KCell | int",
        trans: kdb.Trans | kdb.ICplxTrans | kdb.Vector = kdb.Trans(),
    ) -> "Instance":
        ...

    @overload
    def create_inst(
        self,
        cell: "KCell | int",
        *,
        dtrans: kdb.DTrans | kdb.DCplxTrans | kdb.DVector,
    ) -> "Instance":
        ...

    @overload
    def create_inst(
        self,
        cell: "KCell | int",
        trans: kdb.Trans | kdb.ICplxTrans | kdb.Vector,
        *,
        a: kdb.Vector,
        b: kdb.Vector,
        na: int = 1,
        nb: int = 1,
    ) -> "Instance":
        ...

    @overload
    def create_inst(
        self,
        cell: "KCell | int",
        *,
        dtrans: kdb.DTrans | kdb.DCplxTrans,
        a: kdb.DVector,
        b: kdb.DVector,
        na: int = 1,
        nb: int = 1,
    ) -> "Instance":
        ...

    def create_inst(
        self,
        cell: "KCell | int",
        trans: kdb.Trans | kdb.Vector | kdb.ICplxTrans = kdb.Trans(),
        dtrans: kdb.DTrans | kdb.DCplxTrans | kdb.DVector | None = None,
        a: kdb.Vector | kdb.DVector | None = None,
        b: kdb.Vector | kdb.DVector | None = None,
        na: int = 1,
        nb: int = 1,
    ) -> "Instance":
        """Add an instance of another KCell.

        Args:
            cell: The cell to be added
            trans: The integer transformation applied to the reference
            dtrans: um transformation of the reference. If not `None`,
                will overwrite :py:attr:`trans`
            a: Vector (DVector if trans is um based) for the array.
                Needs to be in positive X-direction
            b: Vector (DVector if trans is um based) for the array.
                Needs to be in positive Y-direction
            na: Number of elements in direction of :py:attr:`a`
            nb: Number of elements in direction of :py:attr:`b`

        Returns:
            :py:class:`~Instance`: The created instance
        """
        if isinstance(cell, int):
            ci = cell
        else:
            ci = cell.cell_index()

        if dtrans is None:
            if a is None:
                ca = self._kdb_cell.insert(kdb.CellInstArray(ci, trans))
            else:
                if b is None:
                    b = kdb.Vector()
                cast(kdb.DVector, a)
                cast(kdb.DVector, b)
                ca = self._kdb_cell.insert(
                    kdb.CellInstArray(ci, trans, a, b, na, nb)  # type: ignore[arg-type]
                )
        else:
            if a is None:
                ca = self._kdb_cell.insert(kdb.DCellInstArray(ci, dtrans))
            else:
                if b is None:
                    b = kdb.DVector()
                cast(kdb.DVector, a)
                cast(kdb.DVector, b)
                ca = self._kdb_cell.insert(
                    kdb.DCellInstArray(
                        ci, dtrans, a, b, na, nb  # type: ignore[arg-type]
                    )
                )
        inst = Instance(self.klib, ca)
        self.insts.append(inst)
        return inst

    def _kdb_copy(self) -> kdb.Cell:
        return self._kdb_cell.dup()

    def layer(self, *args: Any, **kwargs: Any) -> int:
        """Get the layer info, convenience for klayout.db.Layout.layer."""
        return self.klib.layer(*args, **kwargs)

    def __lshift__(self, cell: "KCell") -> "Instance":
        """Convenience function for :py:attr:"~create_inst(cell)`.

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
        if rename_func is None:
            self.klib.rename_function(self.ports._ports)
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
        self._kdb_cell.flatten(False)  # prune)
        self.insts = Instances()

        if merge:
            for layer in self.layout().layer_indexes():
                reg = kdb.Region(self.begin_shapes_rec(layer))
                reg.merge()
                self.clear(layer)
                self.shapes(layer).insert(reg)

    def draw_ports(self) -> None:
        """Draw all the ports on their respective :py:attr:`Port.layer`:."""
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
        """Write a KCell to a GDS. See :py:func:`KLib.write` for more info."""
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

    def each_inst(self) -> Iterator["Instance"]:
        """Iterates over all child instances (which may actually be instance arrays)."""
        yield from (Instance(self.klib, inst) for inst in self._kdb_cell.each_inst())

    def each_overlapping_inst(self, b: kdb.Box | kdb.DBox) -> Iterator["Instance"]:
        """Gets the instances overlapping the given rectangle."""
        yield from (
            Instance(self.klib, inst)
            for inst in self._kdb_cell.each_overlapping_inst(b)
        )

    def each_touching_inst(self, b: kdb.Box | kdb.DBox) -> Iterator["Instance"]:
        """Gets the instances overlapping the given rectangle."""
        yield from (
            Instance(self.klib, inst) for inst in self._kdb_cell.each_touching_inst(b)
        )

    @overload
    def insert(
        self, inst: "Instance | kdb.CellInstArray | kdb.DCellInstArray"
    ) -> "Instance":
        ...

    @overload
    def insert(
        self, inst: "kdb.CellInstArray | kdb.DCellInstArray", property_id: int
    ) -> "Instance":
        ...

    def insert(
        self,
        inst: "Instance | kdb.CellInstArray | kdb.DCellInstArray",
        property_id: int | None = None,
    ) -> "Instance":
        """Inserts a cell instance given by another reference."""
        if isinstance(inst, Instance):
            return Instance(self.klib, self._kdb_cell.insert(inst._instance))
        else:
            if not property_id:
                return Instance(self.klib, self._kdb_cell.insert(inst))
            else:
                assert isinstance(inst, kdb.CellInstArray | kdb.DCellInstArray)
                return Instance(self.klib, self._kdb_cell.insert(inst, property_id))


class Instance:
    """An Instance of a KCell.

    An Instance is a reference to a KCell with a transformation.

    Attributes:
        _instance: The internal :py:class:~`kdb.Instance` reference
        ports: Transformed ports of the KCell
    """

    yaml_tag = "!Instance"

    def __init__(self, klib: KLib, instance: kdb.Instance) -> None:
        """Create an instance from a KLayout Instance."""
        self._instance = instance
        self.klib = klib
        self.ports = InstancePorts(self)

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
        return self.klib[self.cell_index]

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
        return self.klib[self._instance.parent_cell.cell_index()]

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
        self, port: str | Port | None, other: Port, *, mirror: bool = False
    ) -> None:
        ...

    @overload
    def connect(
        self,
        port: str | Port | None,
        other: "Instance",
        other_port_name: str | None,
        *,
        mirror: bool = False,
    ) -> None:
        ...

    def connect(
        self,
        port: str | Port | None,
        other: "Instance | Port",
        other_port_name: str | None = None,
        *,
        mirror: bool = False,
        allow_width_mismatch: bool = False,
        allow_layer_mismatch: bool = False,
        allow_type_mismatch: bool = False,
    ) -> None:
        """Align port with name ``portname`` to a port.

        .. deprecated:: 0.6.0
            Use :py:func:`align` instead.
            :py:func:`connect` will be removed in 0.7.0

        Function to allow to transform this instance so that a port of this instance is
        aligned (same position with 180° turn) to another instance.

        Args:
            port: The name of the port of this instance to be connected, or directly an
                instance port. Can be `None` because port names can be `None`.
            other: The other instance or a port. Skip `other_port_name` if it's a port.
            other_port_name: The name of the other port. Ignored if
                :py:attr:`~other_instance` is a port.
            mirror: Instead of applying klayout.db.Trans.R180 as a connection
                transformation, use klayout.db.Trans.M90, which effectively means this
                instance will be mirrored and connected.
            allow_width_mismatch: Skip width check between the ports if set.
            allow_layer_mismatch: Skip layer check between the ports if set.
            allow_type_mismatch: Skip port_type check between the ports if set.
        """
        logger.warning(
            "Instance.connect will be removed in 0.7.0, please use Instance.align"
        )
        self.align(  # type: ignore[call-overload]
            port=port,
            other=other,
            other_port_name=other_port_name,
            mirror=mirror,
            allow_width_mismatch=allow_layer_mismatch,
            allow_layer_mismatch=allow_layer_mismatch,
            allow_type_mismatch=allow_type_mismatch,
        )

    @overload
    def align(
        self, port: str | Port | None, other: Port, *, mirror: bool = False
    ) -> None:
        ...

    @overload
    def align(
        self,
        port: str | Port | None,
        other: "Instance",
        other_port_name: str | None,
        *,
        mirror: bool = False,
    ) -> None:
        ...

    def align(
        self,
        port: str | Port | None,
        other: "Instance | Port",
        other_port_name: str | None = None,
        *,
        mirror: bool = False,
        allow_width_mismatch: bool = False,
        allow_layer_mismatch: bool = False,
        allow_type_mismatch: bool = False,
    ) -> None:
        """Align port with name ``portname`` to a port.

        Function to allow to transform this instance so that a port of this instance is
        aligned (same position with 180° turn) to another instance.

        Args:
            port: The name of the port of this instance to be connected, or directly an
                instance port. Can be `None` because port names can be `None`.
            other: The other instance or a port. Skip `other_port_name` if it's a port.
            other_port_name: The name of the other port. Ignored if
                :py:attr:`~other_instance` is a port.
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
                    "connect_cplx instead"
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
            if p._dcplx_trans or op._dcplx_trans:
                dconn_trans = kdb.DCplxTrans.M90 if mirror else kdb.DCplxTrans.R180
                self.dcplx_trans = (
                    op.dcplx_trans * dconn_trans * p.dcplx_trans.inverted()
                )
            else:
                conn_trans = kdb.Trans.M90 if mirror else kdb.Trans.R180
                self.trans = op.trans * conn_trans * p.trans.inverted()

    @classmethod
    def to_yaml(cls, representer, node):  # type: ignore[no-untyped-def]
        """Convert the instance to a yaml representation."""
        d = {
            "cellname": node.cell.name,
            "trans": node._trans,
            "dcplx_trans": node._dcplx_trans,
        }
        return representer.represent_mapping(cls.yaml_tag, d)


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
            :py:func:`__getitem__` or with :py:func:`~get_all`
    """

    yaml_tag = "!Ports"

    def __init__(self, klib: KLib, ports: Iterable[Port] = []) -> None:
        """Constructor."""
        self._ports: list[Port] = list(ports)
        self.klib = klib

    def copy(self) -> "Ports":
        """Get a copy of each port."""
        return Ports(ports=[p.copy() for p in self._ports], klib=self.klib)

    def contains(self, port: Port) -> bool:
        """Check whether a port is already in the list."""
        return port.hash() in [v.hash() for v in self._ports]

    def __iter__(self) -> Iterator[Port]:
        """Iterator, that allows for loops etc to directly access the object."""
        yield from self._ports

    def add_port(
        self, port: Port, name: str | None = None, keep_mirror: bool = False
    ) -> None:
        """Add a port object.

        Args:
            port: The port to add
            name: Overwrite the name of the port
            keep_mirror: Keep the mirror flag from the original port if `True`,
                else set :py:attr:~`Port.trans.mirror` (or the complex equivalent)
                to `False`.
        """
        _port = port.copy()
        if not keep_mirror:
            if port._trans:
                port._trans.mirror = False
            elif port._dcplx_trans:
                port._dcplx_trans.mirror = False
        if name is not None:
            _port.name = name
        self._ports.append(_port)

    def add_ports(
        self, ports: Iterable[Port], prefix: str = "", keep_mirror: bool = False
    ) -> None:
        """Append a list of ports."""
        for p in ports:
            name = p.name or ""
            self.add_port(port=p, name=prefix + name)

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
                klib=self.klib,
            )
        elif dcplx_trans is not None:
            assert dwidth is not None
            port = Port(
                name=name,
                dwidth=dwidth,
                dcplx_trans=dcplx_trans,
                layer=layer,
                port_type=port_type,
                klib=self.klib,
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
                klib=self.klib,
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
    def from_yaml(cls: "type[Ports]", constructor: Any, node: Any) -> "Ports":
        """Load Ports from a yaml representation."""
        return cls(constructor.construct_sequence(node))


class InstancePorts:
    """Ports of an instance.

    These act as virtual ports as the positions needs to change if the
    instance changes etc.


    Attributes:
        cell_ports: A pointer to the :py:class:~`Ports` of the cell
        instance: A pointer to the :py:class:~`Instance` related to this.
            This provides a way to dynamically calculate the ports.
    """

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
        :py:class:~`Ports`.
        """
        return repr(self.copy())

    def copy(self) -> Ports:
        """Creates a copy in the form of :py:class:~`Ports`."""
        if not self.instance.is_complex():
            return Ports(
                klib=self.instance.klib,
                ports=[p.copy(self.instance.trans) for p in self.cell_ports._ports],
            )
        else:
            return Ports(
                klib=self.instance.klib,
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


@logger.catch
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
    """Decorator to cache and auto name the celll.

    This will use :py:func:`functools.cache` to cache the function call.
    Additionally, if enabled this will set the name and from the args/kwargs of the
    function and also paste them into a settings dictionary of the :py:class:`~KCell`.

    Args:
        set_settings: Copy the args & kwargs into the settings dictionary
        set_name: Auto create the name of the cell to the functionname plus a
            string created from the args/kwargs
        check_ports: Check whether there are any non-90° ports in the cell and throw a
            warning if there are
        check_instances: Check for any complex instances. A complex instance is a an
            instance that has a magnification != 1 or non-90° rotation.
    """

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
    """Convert a `dict` to a `frozenset`."""
    return frozenset(d.items())


def frozenset_to_dict(fs: frozenset[tuple[str, Hashable]]) -> dict[str, Hashable]:
    """Convert `frozenset` to `dict`."""
    return dict(fs)


def cell(
    _func: Callable[..., KCell] | None = None,
    *,
    set_settings: bool = True,
    maxsize: int = 512,
) -> (
    Callable[KCellParams, KCell]
    | Callable[[Callable[KCellParams, KCell]], Callable[KCellParams, KCell]]
):
    """Convenience alias for :py:func:`~autocell` with `(set_name=False)`."""
    if _func is None:
        return autocell(set_settings=set_settings, set_name=False)
    else:
        return autocell(_func)


def dict2name(prefix: str | None = None, **kwargs: dict[str, Any]) -> str:
    """Returns name from a dict."""
    label = [prefix] if prefix else []
    for key, value in kwargs.items():
        key = join_first_letters(key)
        label += [f"{key.upper()}{clean_value(value)}"]
    _label = "_".join(label)
    return clean_name(_label)


def get_component_name(component_type: str, **kwargs: dict[str, Any]) -> str:
    """Convert a component to a string."""
    name = component_type

    if kwargs:
        name += f"_{dict2name(None, **kwargs)}"

    return name


def join_first_letters(name: str) -> str:
    """Join the first letter of a name separated with underscores.

    Example::

        "TL" == join_first_letters("taper_length")
    """
    return "".join([x[0] for x in name.split("_") if x])


def clean_value(
    value: float | np.float64 | dict[Any, Any] | KCell | Callable[..., Any]
) -> str:
    """Makes sure a value is representable in a limited character_space."""
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
    delete = False

    if isinstance(gds, KCell):
        _mf = "stdin" if mf == "<stdin>" else mf
        tf = Path(gettempdir()) / Path(_mf).with_suffix(".gds")
        tf.parent.mkdir(parents=True, exist_ok=True)
        gds.write(str(tf), save_options)
        gds_file = tf
        delete = True
    elif isinstance(gds, str | Path):
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
        enc_data = data.encode()
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
    "klib",
    "KLib",
    "default_save",
    "LayerEnum",
]
