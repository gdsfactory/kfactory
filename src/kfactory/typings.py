from __future__ import annotations

from typing import (
    TYPE_CHECKING,
    Annotated,
    Any,
    NotRequired,
    ParamSpec,
    TypedDict,
    TypeVar,
)

import klayout.db as kdb
from klayout import lay

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable

    from cachetools import Cache

    from .conf import CheckInstances
    from .decorators import PortsDefinition, WrappedKCellFunc, WrappedVKCellFunc
    from .instance import ProtoInstance, ProtoTInstance
    from .kcell import BaseKCell, ProtoKCell, ProtoTKCell, VKCell
    from .layer import LayerEnum
    from .pin import ProtoPin
    from .port import ProtoPort
    from .schematic import TSchematic

T = TypeVar("T")
K = TypeVar("K", bound="ProtoKCell[Any, Any]")
KC = TypeVar("KC", bound="ProtoTKCell[Any]")
KCIN = TypeVar("KCIN", bound="ProtoTKCell[Any]")
VK = TypeVar("VK", bound="VKCell")
K_co = TypeVar("K_co", bound="ProtoKCell[Any, Any]", covariant=True)
KC_co = TypeVar("KC_co", bound="ProtoTKCell[Any]", covariant=True)
K_contra = TypeVar("K_contra", bound="ProtoKCell[Any, Any]", contravariant=True)
KC_contra = TypeVar("KC_contra", bound="ProtoTKCell[Any]", contravariant=True)
VK_contra = TypeVar("VK_contra", bound="VKCell", contravariant=True)
type TUnit = int | float
type TPort = ProtoPort[int | float]
TPin = TypeVar("TPin", bound="ProtoPin[Any]")
TInstance_co = TypeVar("TInstance_co", bound="ProtoInstance[Any]", covariant=True)
TTInstance_co = TypeVar("TTInstance_co", bound="ProtoTInstance[Any]", covariant=True)
TBaseCell_co = TypeVar("TBaseCell_co", bound="BaseKCell", covariant=True)
KCellParams = ParamSpec("KCellParams")
SchematicParams = ParamSpec("SchematicParams")
F = TypeVar(
    "F",
    bound="WrappedKCellFunc[Any, Any] | WrappedVKCellFunc[Any, Any]",
)
F_co = TypeVar(
    "F_co",
    bound="WrappedKCellFunc[Any, Any] | WrappedVKCellFunc[Any, Any]",
    covariant=True,
)
P = ParamSpec("P")


type JSONSerializable = (
    int
    | float
    | bool
    | str
    | list[JSONSerializable]
    | tuple[JSONSerializable, ...]
    | dict[str, JSONSerializable]
    | None
)


class KCellSpecDict(TypedDict, total=True):
    """Specification for a KCell."""

    component: str
    settings: NotRequired[dict[str, Any]]
    kcl: NotRequired[str]


AnyTrans = TypeVar(
    "AnyTrans", bound=kdb.Trans | kdb.DTrans | kdb.ICplxTrans | kdb.DCplxTrans
)

type SerializableShape = (
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
    | kdb.LayerInfo
)
type IShapeLike = (
    kdb.Polygon
    | kdb.Edge
    | kdb.Path
    | kdb.Box
    | kdb.Text
    | kdb.SimplePolygon
    | kdb.Region
)
type DShapeLike = (
    kdb.DPolygon | kdb.DEdge | kdb.DPath | kdb.DBox | kdb.DText | kdb.DSimplePolygon
)
type ShapeLike = IShapeLike | DShapeLike | kdb.Shape

type MetaData = (
    int
    | float
    | bool
    | str
    | SerializableShape
    | list[MetaData]
    | tuple[MetaData, ...]
    | dict[str, MetaData]
    | None
)


um = Annotated[float, "um"]
"""Float in micrometer."""
dbu = Annotated[int, "dbu"]
"""Integer in database units."""
deg = Annotated[float, "deg"]
"""Float in degrees."""
rad = Annotated[float, "rad"]
"""Float in radians."""
layer = Annotated["int | LayerEnum", "layer"]
"""Integer or enum index of a Layer."""
layer_info = Annotated[kdb.LayerInfo, "layer info"]
type Unit = int | float
"""Database unit or micrometer."""
type Angle = int
"""Integer in the range of `[0,1,2,3]` which are increments in 90°."""
type KCellSpec = (
    "int | str | KCellSpecDict | ProtoTKCell[Any] | Callable[..., ProtoTKCell[Any]]"
)
type AnyCellSpec = "int | str | KCellSpecDict | ProtoTKCell[Any] | VKCell | Callable[..., ProtoTKCell[Any]] | Callable[..., VKCell]"  # noqa: E501


class CellKwargs(TypedDict, total=False):
    set_settings: bool
    set_name: bool
    check_ports: bool
    check_pins: bool
    check_instances: CheckInstances
    snap_ports: bool
    add_port_layers: bool
    cache: Cache[int, Any] | dict[int, Any]
    basename: str
    drop_params: list[str]
    register_factory: bool
    overwrite_existing: bool
    layout_cache: bool
    info: dict[str, MetaData]
    post_process: Iterable[Callable[[ProtoTKCell[Any]], None]]
    debug_names: bool
    tags: list[str]
    lvs_equivalent_ports: list[list[str]]
    ports: PortsDefinition
    schematic_function: Callable[..., TSchematic[Any]]
