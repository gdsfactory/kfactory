from __future__ import annotations

from collections.abc import Callable
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
import klayout.lay as lay

if TYPE_CHECKING:
    from .instance import ProtoInstance
    from .kcell import BaseKCell, ProtoTKCell
    from .layer import LayerEnum, LayerInfos
    from .layout import Constants
    from .port import ProtoPort

T = TypeVar("T")
K = TypeVar("K", bound="ProtoTKCell[Any]")
KC = TypeVar("KC", bound="ProtoTKCell[Any]", covariant=True)
LI = TypeVar("LI", bound="LayerInfos", covariant=True)
C = TypeVar("C", bound="Constants", covariant=True)
TUnit = TypeVar("TUnit", int, float)
TUnit_co = TypeVar("TUnit_co", bound=int | float, covariant=True)
TUnit_contra = TypeVar("TUnit_contra", bound=int | float, contravariant=True)
TPort = TypeVar("TPort", bound="ProtoPort[Any]")
TInstance = TypeVar("TInstance", bound="ProtoInstance[Any]", covariant=True)
TBaseCell = TypeVar("TBaseCell", bound="BaseKCell", covariant=True)
KCellParams = ParamSpec("KCellParams")


class KCellSpecDict(TypedDict):
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
unit: TypeAlias = int | float
"""Database unit or micrometer."""
Angle: TypeAlias = int
"""Integer in the range of `[0,1,2,3]` which are increments in 90°."""
KCellSpec: TypeAlias = (
    "int | str | KCellSpecDict | ProtoTKCell[Any] | Callable[..., ProtoTKCell[Any]]"
)
