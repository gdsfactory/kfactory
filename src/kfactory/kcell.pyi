from abc import ABC, ABCMeta
from enum import Enum
from typing import (
    Any,
    Callable,
    Generic,
    Hashable,
    Iterator,
    Optional,
    Protocol,
    Sequence,
    Type,
    TypeVar,
    Union,
    cast,
    overload,
)

from _typeshed import Incomplete
from cachetools import Cache

from . import kdb

class KLib(kdb.Layout):
    kcells: Incomplete

    def __init__(self, editable: bool = ...) -> None: ...
    def create_cell(  # type: ignore[override]
        self,
        kcell: KCell,
        name: str,
        *args: Union[
            list[str], list[Union[str, dict[str, Any]]], list[Union[str, str]]
        ],
        allow_duplicate: bool = ...,
    ) -> kdb.Cell: ...
    def update_cell_name(self, name: str, new_name: str) -> None: ...

library: Incomplete

class LayerEnum(int, Enum):
    def __new__(  # type: ignore[misc]
        cls: "LayerEnum",
        layer: int,
        datatype: int,
        lib: KLib = library,
    ) -> "LayerEnum": ...
    def __getitem__(self, key: int) -> int: ...
    def __len__(self) -> int: ...
    def __iter(self) -> Iterator[int]: ...
    def __str__(self) -> str: ...

TT = TypeVar("TT", bound=kdb.Trans | kdb.DTrans | kdb.ICplxTrans | kdb.DCplxTrans)
TD = TypeVar("TD", bound=kdb.DTrans | kdb.DCplxTrans)
TI = TypeVar("TI", bound=kdb.Trans | kdb.ICplxTrans)
TS = TypeVar("TS", bound=kdb.Trans | kdb.DTrans)
TC = TypeVar("TC", bound=kdb.ICplxTrans | kdb.DCplxTrans)
FI = TypeVar("FI", bound=int | float)

class PortLike(ABC, Generic[TT, FI]):  # Protocol[TT, FI]):

    yaml_tag: str
    name: str
    width: FI
    layer: int
    trans: TT
    port_type: str

    def copy(self, trans: TI) -> "PortLike[TT, FI]": ...
    @overload
    def __init__(
        self,
        *,
        name: str,
        trans: TI,
        width: FI,
        layer: int,
        port_type: str = "optical",
    ) -> None: ...
    @overload
    def __init__(
        self,
        *,
        port: "PortLike[TT,FI]",
        name: Optional[str] = None,
    ) -> None: ...
    @overload
    def __init__(
        self,
        *,
        name: str,
        width: FI,
        position: tuple[FI, FI],
        angle: FI,
        layer: int,
        port_type: str = "optical",
        mirror_x: bool = False,
    ) -> None: ...
    def move(
        self,
        origin: tuple[FI, FI],
        destination: tuple[FI, FI] = (cast(FI, 0), cast(FI, 0)),
    ) -> None: ...
    @property
    def center(self) -> tuple[FI, FI]: ...
    @center.setter
    def center(self, value: tuple[FI, FI]) -> None: ...
    @property
    def x(self) -> FI: ...
    @property
    def y(self) -> FI: ...
    def hash(self) -> bytes: ...
    def complex(self) -> bool: ...
    def int_based(self) -> bool: ...
    def dcplx_trans(self, dbu: float) -> kdb.DCplxTrans: ...
    def copy_cplx(self, trans: kdb.DCplxTrans, dbu: float) -> "DCplxPort": ...

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
    ) -> None: ...
    @overload
    def __init__(
        self,
        *,
        name: Optional[str] = None,
        port: "IPortLike[TI]",
    ) -> None: ...
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
    ) -> None: ...
    def __repr__(self) -> str: ...
    @property
    def position(self) -> tuple[int, int]:
        """Gives the x and y coordinates of the Port. This is info stored in the transformation of the port.

        Returns:
            position: `(self.trans.disp.x, self.trans.disp.y)`
        """
        ...
    @property
    def mirror(self) -> bool:
        """Flag to mirror the transformation. Mirroring is in increments of 45° planes.
        E.g. a rotation of 90° and mirror flag result in a mirroring on the 45° plane.
        """
        ...
    @property
    def x(self) -> int:
        """Convenience for :py:attr:`Port.trans.disp.x`"""
        ...
    @property
    def y(self) -> int:
        """Convenience for :py:attr:`Port.trans.disp.y`"""
        ...
    def hash(self) -> bytes:
        """Provides a hash function to provide a (hopefully) unique id of a port

        Returns:
            hash-digest: A byte representation from sha3_512()
        """
        ...
    @classmethod
    def to_yaml(cls, representer, node):  # type: ignore[no-untyped-def]
        """Internal function used by ruamel.yaml to convert Port to yaml"""
        ...
    @property
    def center(self) -> tuple[int, int]:
        """Returns port position for gdsfactory compatibility."""
        ...
    @center.setter
    def center(self, value: tuple[int, int]) -> None: ...
    def int_based(self) -> bool: ...

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
    ) -> None: ...
    @overload
    def __init__(
        self,
        *,
        name: Optional[str] = None,
        port: "DPortLike[TD]",
    ) -> None: ...
    def __repr__(self) -> str: ...
    @property
    def position(self) -> tuple[float, float]:
        """Gives the x and y coordinates of the Port. This is info stored in the transformation of the port.

        Returns:
            position: `(self.trans.disp.x, self.trans.disp.y)`
        """
        ...
    @property
    def mirror(self) -> bool:
        """Flag to mirror the transformation. Mirroring is in increments of 45° planes.
        E.g. a rotation of 90° and mirror flag result in a mirroring on the 45° plane.
        """
        ...
    @property
    def x(self) -> float:
        """Convenience for :py:attr:`Port.trans.disp.x`"""
        ...
    @property
    def y(self) -> float:
        """Convenience for :py:attr:`Port.trans.disp.y`"""
        ...
    def hash(self) -> bytes:
        """Provides a hash function to provide a (hopefully) unique id of a port

        Returns:
            hash-digest: A byte representation from sha3_512()
        """
        ...
    @classmethod
    def to_yaml(cls, representer, node):  # type: ignore[no-untyped-def]
        """Internal function used by ruamel.yaml to convert Port to yaml"""
        ...
    @property
    def center(self) -> tuple[float, float]:
        """Returns port position for gdsfactory compatibility."""
        ...
    @center.setter
    def center(self, value: tuple[float, float]) -> None: ...
    def int_based(self) -> bool: ...

class SPortLike(PortLike[TS, Any]):
    """Protocol for simple transformation based ports"""

    @property
    def angle(self) -> int:
        """Angle of the transformation. In the range of [0,1,2,3] which are increments in 90°. Not to be confused with `rot`
        of the transformation which keeps additional info about the mirror flag."""
        ...
    @property
    def orientation(self) -> float:
        """Returns orientation in degrees for gdsfactory compatibility."""
        ...
    @orientation.setter
    def orientation(self, value: int) -> None: ...
    def complex(self) -> bool: ...

class CPortLike(PortLike[TC, Any]):
    """Protocol for complex transformation based ports"""

    trans: TC

    @property
    def angle(self) -> float:
        """Angle of the transformation. In the range of [0,1,2,3] which are increments in 90°. Not to be confused with `rot`
        of the transformation which keeps additional info about the mirror flag."""
        ...
    @property
    def orientation(self) -> float:
        """Returns orientation in degrees for gdsfactory compatibility."""
        ...
    @orientation.setter
    def orientation(self, value: float) -> None: ...
    def complex(self) -> bool: ...

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
    ): ...
    def move(
        self, origin: tuple[int, int], destination: Optional[tuple[int, int]] = None
    ) -> None:
        """Convenience from the equivalent of gdsfactory. Moves the"""
        ...
    @classmethod
    def from_yaml(cls: Type[Port], constructor: Any, node: Any) -> Port:
        """Internal function used by the placer to convert yaml to a Port"""
        ...
    def rotate(self, angle: int) -> None:
        """Rotate the Port

        Args:
            angle: The angle to rotate in increments of 90°
        """
        ...
    def copy(self, trans: kdb.Trans = kdb.Trans.R0) -> "Port":  # type: ignore[override]
        """Get a copy of a port

        Args:
            trans: an optional transformation applied to the port to be copied

        Returns:
            port (:py:class:`Port`): a copy of the port
        """
        ...
    def dcplx_trans(self, dbu: float) -> kdb.DCplxTrans: ...

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
    ): ...
    def move(
        self,
        origin: tuple[float, float],
        destination: Optional[tuple[float, float]] = None,
    ) -> None:
        """Convenience from the equivalent of gdsfactory. Moves the"""
        ...
    @classmethod
    def from_yaml(cls: Type[DPort], constructor: Any, node: Any) -> DPort:
        """Internal function used by the placer to convert yaml to a Port"""
        ...
    def rotate(self, angle: int) -> None:
        """Rotate the Port

        Args:
            angle: The angle to rotate in increments of 90°
        """
        ...
    def copy(self, trans: kdb.DTrans = kdb.DTrans.R0) -> "DPort":  # type: ignore[override]
        """Get a copy of a port

        Args:
            trans: an optional transformation applied to the port to be copied

        Returns:
            port (:py:class:`Port`): a copy of the port
        """
        ...
    def dcplx_trans(self, dbu: float) -> kdb.DCplxTrans: ...

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
    ): ...
    def move(
        self,
        origin: tuple[int, int],
        destination: Optional[tuple[int, int]] = None,
    ) -> None:
        """Convenience from the equivalent of gdsfactory. Moves the"""
        ...
    @classmethod
    def from_yaml(cls: Type[ICplxPort], constructor: Any, node: Any) -> ICplxPort:
        """Internal function used by the placer to convert yaml to a Port"""
        ...
    def rotate(self, angle: int) -> None:
        """Rotate the Port

        Args:
            angle: The angle to rotate in increments of 90°
        """
        ...
    def copy(self, trans: kdb.ICplxTrans = kdb.ICplxTrans.R0) -> "ICplxPort":  # type: ignore[override]
        """Get a copy of a port

        Args:
            trans: an optional transformation applied to the port to be copied

        Returns:
            port (:py:class:`Port`): a copy of the port
        """
        ...
    def dcplx_trans(self, dbu: float) -> kdb.DCplxTrans: ...

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
        angle: Optional[int] = None,
        position: Optional[tuple[float, float]] = None,
        mirror_x: bool = False,
        port: Optional["DCplxPort"] = None,
    ): ...
    def move(
        self,
        origin: tuple[float, float],
        destination: Optional[tuple[float, float]] = None,
    ) -> None:
        """Convenience from the equivalent of gdsfactory. Moves the"""
        ...
    @classmethod
    def from_yaml(cls: Type[DCplxPort], constructor: Any, node: Any) -> DCplxPort:
        """Internal function used by the placer to convert yaml to a Port"""
        ...
    def rotate(self, angle: int) -> None:
        """Rotate the Port

        Args:
            angle: The angle to rotate in increments of 90°
        """
        ...
    def copy(self, trans: kdb.DCplxTrans = kdb.DCplxTrans.R0) -> "DCplxPort":  # type: ignore[override]
        """Get a copy of a port

        Args:
            trans: an optional transformation applied to the port to be copied

        Returns:
            port (:py:class:`Port`): a copy of the port
        """
        ...
    def dcplx_trans(self, dbu: float) -> kdb.DCplxTrans: ...

class KCell:
    yaml_tag: str
    library: Incomplete
    ports: Incomplete
    insts: Incomplete
    settings: Incomplete

    def __init__(
        self,
        name: Optional[str] = ...,
        library: KLib = ...,
        kdb_cell: Optional[kdb.Cell] = ...,
    ) -> None: ...
    def copy(self) -> KCell: ...
    @property
    def name(self) -> str: ...
    @name.setter
    def name(self, new_name: str) -> None: ...
    @overload
    def create_port(
        self,
        *,
        name: str,
        trans: kdb.Trans,
        width: int,
        layer: int,
        port_type: str = ...,
    ) -> None: ...
    @overload
    def create_port(self, *, name: Optional[str] = ..., port: Port) -> None: ...
    @overload
    def create_port(
        self,
        *,
        name: str,
        width: int,
        position: tuple[int, int],
        angle: int,
        layer: int,
        port_type: str = ...,
        mirror_x: bool = ...,
    ) -> None: ...
    def add_port(self, port: PortLike[TT, FI], name: Optional[str] = ...) -> None: ...
    def create_inst(self, cell: KCell, trans: kdb.Trans = ...) -> Instance: ...
    def layer(self, *args: Any, **kwargs: Any) -> int: ...
    def __lshift__(self, cell: KCell) -> Instance: ...
    def __getattribute__(self, attr_name: str) -> Any: ...
    def __getattr__(self, attr_name: str) -> Any: ...
    def __setattr__(self, attr_name: str, attr_value: Any) -> None: ...
    def hash(self) -> bytes: ...
    def autorename_ports(self) -> None: ...
    def flatten(self, prune: bool = ..., merge: bool = ...) -> None: ...
    def draw_ports(self) -> None: ...
    @classmethod
    def to_yaml(cls, representer, node): ...  # type: ignore[no-untyped-def]
    @classmethod
    def from_yaml(
        cls: Type[KCell], constructor: Any, node: Any, verbose: bool = ...
    ) -> KCell: ...
    def basic_name(self) -> str: ...
    def bbox(self) -> kdb.Box: ...
    def bbox_per_layer(self, layer_index: int) -> kdb.Box: ...
    def begin_instances_rec(self) -> kdb.RecursiveInstanceIterator: ...
    @overload
    def begin_instances_rec_overlapping(
        self, region: kdb.Box
    ) -> kdb.RecursiveInstanceIterator: ...
    @overload
    def begin_instances_rec_overlapping(
        self, region: kdb.DBox
    ) -> kdb.RecursiveInstanceIterator: ...
    @overload
    def begin_instances_rec_touching(
        self, region: kdb.Box
    ) -> kdb.RecursiveInstanceIterator: ...
    @overload
    def begin_instances_rec_touching(
        self, region: kdb.DBox
    ) -> kdb.RecursiveInstanceIterator: ...
    def begin_shapes_rec(self, layer: int) -> kdb.RecursiveShapeIterator: ...
    @overload
    def begin_shapes_rec_overlapping(
        self, layer: int, region: kdb.Box
    ) -> kdb.RecursiveShapeIterator: ...
    @overload
    def begin_shapes_rec_overlapping(
        self, layer: int, region: kdb.DBox
    ) -> kdb.RecursiveShapeIterator: ...
    @overload
    def begin_shapes_rec_touching(
        self, layer: int, region: kdb.Box
    ) -> kdb.RecursiveShapeIterator: ...
    @overload
    def begin_shapes_rec_touching(
        self, layer: int, region: kdb.DBox
    ) -> kdb.RecursiveShapeIterator: ...
    def called_cells(self) -> Sequence[int]: ...
    def caller_cells(self) -> Sequence[int]: ...
    def cell_index(self) -> int: ...
    def child_cells(self) -> int: ...
    def child_instances(self) -> int: ...
    @overload
    def clear(self) -> None: ...
    @overload
    def clear(self, layer_index: int) -> None: ...
    def clear_insts(self) -> None: ...
    def clear_shapes(self) -> None: ...

    # @overload
    # def copy(self, src: int, dest: int) -> None: ...
    # @overload
    # def copy(self, src_cell: Cell, src_layer: int, dest: int) -> None: ...
    def dbbox(self) -> kdb.DBox: ...
    def dbbox_per_layer(self, layer_index: int) -> kdb.DBox: ...
    def delete(self) -> None: ...
    def delete_property(self, key: str | int) -> None: ...
    def display_titlle(self) -> str: ...
    def dup(self) -> kdb.Cell: ...
    def each_child_cell(self) -> Iterator[int]: ...
    @overload
    def each_overlapping_shape(
        self, layer_index: int, box: kdb.Box, flags: int
    ) -> Iterator[kdb.Shape]: ...
    @overload
    def each_overlapping_shape(
        self, layer_index: int, box: kdb.Box
    ) -> Iterator[kdb.Shape]: ...
    @overload
    def each_overlapping_shape(
        self, layer_index: int, box: kdb.DBox, fflags: int
    ) -> Iterator[kdb.Shape]: ...
    @overload
    def each_overlapping_shape(
        self, layer_index: int, box: kdb.DBox
    ) -> Iterator[kdb.Shape]: ...
    @overload
    def each_shape(self, layer_index: int, flags: int) -> Iterator[kdb.Shape]: ...
    @overload
    def each_shape(self, layer_index: int) -> Iterator[kdb.Shape]: ...
    @overload
    def each_touching_shape(
        self, layer_index: int, box: kdb.Box, flags: int
    ) -> Iterator[kdb.Shape]: ...
    @overload
    def each_touching_shape(
        self, layer_index: int, box: kdb.Box
    ) -> Iterator[kdb.Shape]: ...
    @overload
    def each_touching_shape(
        self, layer_index: int, box: kdb.DBox, flags: int
    ) -> Iterator[kdb.Shape]: ...
    @overload
    def fill_region(
        self,
        region: kdb.Region,
        fill_cell_index: int,
        ffc_box: kdb.Box,
        origin: kdb.Point = kdb.Point(0, 0),
        remaining_parts: Optional[kdb.Region] = None,
        fill_margin: kdb.Vector = kdb.Vector(0, 0),
        remaining_polygons: Optional[kdb.Region] = None,
        glue_box: kdb.Box = kdb.Box(),
    ) -> None: ...
    @overload
    def fill_region(
        self,
        region: kdb.Region,
        fill_cell_index: int,
        fc_bbox: kdb.Box,
        row_step: kdb.Vector,
        column_step: kdb.Vector,
        origin: kdb.Point = kdb.Point(0, 0),
        remaining_parts: Optional[kdb.Region] = None,
        fill_margin: kdb.Vector = kdb.Vector(0, 0),
        remaining_polygons: Optional[kdb.Region] = None,
        glue_box: kdb.Box = kdb.Box(),
    ) -> None: ...

    # @overload
    # def flatten(self, prune: bool) -> None: ...
    # @overload
    # def flatten(self, levels: int, prune: bool) -> None: ...
    def has_prop_id(self) -> bool: ...
    def hierarchy_levels(self) -> int: ...
    @overload
    def insert(self, inst: Instance) -> Instance: ...
    @overload
    def insert(
        self, cell_inst_array: kdb.CellInstArray | kdb.DCellInstArray
    ) -> kdb.Instance: ...
    @overload
    def insert(
        self, cell_inst_array: kdb.CellInstArray | kdb.DCellInstArray, property_id: int
    ) -> kdb.Instance: ...
    def is_empty(self) -> bool: ...
    def is_ghost_cell(self) -> bool: ...
    def is_leaf(self) -> bool: ...
    def is_library_cell(self) -> bool: ...
    @overload
    def is_pcell_variant(self) -> bool: ...
    @overload
    def is_pcell_variant(self, instance: kdb.Instance) -> bool: ...
    def is_proxy(self) -> bool: ...
    def is_top(self) -> bool: ...
    def is_valid(self, instance: kdb.Instance) -> bool: ...
    def layout(self) -> kdb.Layout: ...

    # def library(self) -> Optional[kdb.Library]: ...
    def library_cell_index(self) -> Optional[int]: ...
    @overload
    def move(self, src: int, dest: int) -> None: ...
    @overload
    def move(self, src_cell: kdb.Cell, src: int, dest: int) -> None: ...
    @overload
    def move_shapes(self, source_cell: kdb.Cell) -> None: ...
    @overload
    def move_shapes(
        self, source_cell: kdb.Cell, layer_mapping: kdb.LayerMapping
    ) -> None: ...
    def parent_cells(self) -> int: ...
    def prune_cell(self, levels: int = -1) -> None: ...
    def prune_subcells(self, levels: int = -1) -> None: ...
    def qname(self) -> str: ...
    @overload
    def replace(
        self,
        instance: kdb.Instance,
        cell_inst_array: kdb.CellInstArray | kdb.DCellInstArray,
    ) -> kdb.Instance: ...
    @overload
    def replace(
        self,
        instance: kdb.Instance,
        cell_inst_array: kdb.CellInstArray | kdb.DCellInstArray,
        property_id: int,
    ) -> kdb.Instance: ...
    def replace_prop_id(self, instance: Instance, property_id: int) -> Instance: ...
    def set_property(self, key: str | int, value: str | int | float) -> None: ...
    def shapes(self, layer_index: int) -> kdb.Shapes: ...
    def swap(self, layer_index1: int, layer_index2: int) -> None: ...
    @overload
    def transform(
        self,
        instance: Instance,
        trans: kdb.Trans | kdb.ICplxTrans | kdb.DTrans | kdb.DCplxTrans,
    ) -> Instance: ...
    @overload
    def transform(
        self, trans: kdb.Trans | kdb.DTrans | kdb.ICplxTrans | kdb.DCplxTrans
    ) -> None: ...
    @overload
    def transform_into(
        self,
        instance: Instance,
        trans: kdb.Trans | kdb.DTrans | kdb.ICplxTrans | kdb.DCplxTrans,
    ) -> Instance: ...
    @overload
    def transform_into(
        self, trans: kdb.Trans | kdb.DTrans | kdb.ICplxTrans | kdb.DCplxTrans
    ) -> None: ...
    @overload
    def write(self, file_name: str) -> None: ...
    @overload
    def write(self, file_name: str, options: kdb.SaveLayoutOptions) -> None: ...

class Instance:
    yaml_tag: str
    cell: Incomplete
    instance: Incomplete
    ports: Incomplete

    def __init__(self, cell: KCell, reference: kdb.Instance) -> None: ...
    def hash(self) -> bytes: ...
    def connect(
        self,
        portname: str,
        other_instance: Union["Instance", Port],
        other_port_name: Optional[str] = ...,
        mirror: bool = ...,
    ) -> None: ...
    def __getattribute__(self, attr_name: str) -> Any: ...
    def __getattr__(self, attr_name: str) -> Any: ...
    def __setattr__(self, attr_name: str, attr_value: Any) -> None: ...
    @classmethod
    def to_yaml(cls, representer, node): ...  # type: ignore[no-untyped-def]

class Ports:
    yaml_tag: str

    def __init__(self, ports: list[Port] = ...) -> None: ...
    def copy(self) -> Ports: ...
    def contains(self, port: Port) -> bool: ...
    def each(self) -> Iterator["Port"]: ...
    def add_port(self, port: PortLike[TT, FI], name: Optional[str] = ...) -> None: ...
    @overload
    def create_port(
        self,
        *,
        name: str,
        trans: kdb.Trans,
        width: int,
        layer: int,
        port_type: str = ...,
    ) -> Port: ...
    @overload
    def create_port(
        self,
        *,
        name: str,
        width: int,
        layer: int,
        position: tuple[int, int],
        angle: int,
        port_type: str = ...,
    ) -> Port: ...
    def get_all(self) -> dict[str, Port]: ...
    def __getitem__(self, key: str) -> Port: ...
    def hash(self) -> bytes: ...
    @classmethod
    def to_yaml(cls, representer, node): ...  # type: ignore[no-untyped-def]
    @classmethod
    def from_yaml(cls: Type[Ports], constructor: Any, node: Any) -> Ports: ...

class InstancePorts:
    cell_ports: Incomplete
    instance: Incomplete

    def __init__(self, instance: Instance) -> None: ...
    def __getitem__(self, key: str) -> Port: ...
    def get_all(self) -> dict[str, Port]: ...

def autocell(
    _func: Optional[Callable[..., KCell]] = ...,
    *,
    set_settings: bool = ...,
    set_name: bool = ...,
    maxsize: int = ...,
) -> Callable[..., KCell]: ...
def cell(
    _func: Optional[Callable[..., KCell]] = ..., *, set_settings: bool = ...
) -> Callable[..., KCell]: ...

class KCellCache(Cache[int, Any]):
    def popitem(self) -> tuple[int, Any]: ...

def default_save() -> kdb.SaveLayoutOptions: ...
