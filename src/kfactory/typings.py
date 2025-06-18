from __future__ import annotations

from typing import (
    TYPE_CHECKING,
    Annotated,
    Any,
    NotRequired,
    ParamSpec,
    TypeAlias,
    TypedDict,
    TypeVar,
)

import klayout.db as kdb
from klayout import lay
from typing_extensions import TypeAliasType

if TYPE_CHECKING:
    from collections.abc import Callable

    from .instance import ProtoInstance, ProtoTInstance
    from .kcell import BaseKCell, ProtoKCell, ProtoTKCell, VKCell
    from .layer import LayerEnum
    from .pin import ProtoPin
    from .port import ProtoPort

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
TUnit = TypeVar("TUnit", int, float)
TUnit_co = TypeVar("TUnit_co", bound=int | float, covariant=True)
TUnit_contra = TypeVar("TUnit_contra", bound=int | float, contravariant=True)
TPort = TypeVar("TPort", bound="ProtoPort[Any]")
TPort_co = TypeVar("TPort_co", bound="ProtoPort[Any]", covariant=True)
TPort_contra = TypeVar("TPort_contra", bound="ProtoPort[Any]", contravariant=True)
TPin = TypeVar("TPin", bound="ProtoPin[Any]")
TInstance_co = TypeVar("TInstance_co", bound="ProtoInstance[Any]", covariant=True)
TTInstance_co = TypeVar("TTInstance_co", bound="ProtoTInstance[Any]", covariant=True)
TBaseCell_co = TypeVar("TBaseCell_co", bound="BaseKCell", covariant=True)
KCellParams = ParamSpec("KCellParams")
P = ParamSpec("P")

JSONSerializable = TypeAliasType(
    "JSONSerializable",
    "int | float| bool | str | list[JSONSerializable] | tuple[JSONSerializable, ...] | dict[str, JSONSerializable]| None",  # noqa: E501
)


class KCellSpecDict(TypedDict):
    """Specification for a KCell."""

    component: str
    settings: NotRequired[dict[str, Any]]


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
    | kdb.LayerInfo
)
IShapeLike: TypeAlias = (
    kdb.Polygon
    | kdb.Edge
    | kdb.Path
    | kdb.Box
    | kdb.Text
    | kdb.SimplePolygon
    | kdb.Region
)
DShapeLike: TypeAlias = (
    kdb.DPolygon | kdb.DEdge | kdb.DPath | kdb.DBox | kdb.DText | kdb.DSimplePolygon
)
ShapeLike: TypeAlias = IShapeLike | DShapeLike | kdb.Shape

MetaData: TypeAlias = (
    int
    | float
    | bool
    | str
    | SerializableShape
    | list["MetaData"]
    | tuple["MetaData", ...]
    | dict[str, "MetaData"]
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
Unit: TypeAlias = int | float
"""Database unit or micrometer."""
Angle: TypeAlias = int
"""Integer in the range of `[0,1,2,3]` which are increments in 90°."""
KCellSpec: TypeAlias = (
    "int | str | KCellSpecDict | ProtoTKCell[Any] | Callable[..., ProtoTKCell[Any]]"
)
