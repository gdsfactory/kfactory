from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Generic, Self, overload

import numpy as np

from . import kdb
from .typings import TUnit

if TYPE_CHECKING:
    from .layer import LayerEnum
    from .layout import KCLayout
    from .protocols import BoxFunction, BoxLike

__all__ = ["DBUGeometricObject", "GeometricObject", "SizeInfo", "UMGeometricObject"]


class SizeInfo(Generic[TUnit]):
    _bf: BoxFunction[TUnit]

    def __init__(self, bbox: BoxFunction[TUnit]) -> None:
        """Initialize this object."""
        super().__init__()
        self._bf = bbox

    def __str__(self) -> str:
        return (
            f"SizeInfo: {self.width=}, {self.height=}, {self.west=}, {self.east=},"
            f" {self.south=}, {self.north=}"
        )

    def __call__(self, layer: int | LayerEnum) -> SizeInfo[TUnit]:
        def layer_bbox() -> BoxLike[TUnit]:
            return self._bf(layer)

        return SizeInfo[TUnit](bbox=layer_bbox)  # type: ignore[arg-type]

    @property
    def west(self) -> TUnit:
        return self._bf().left

    @property
    def east(self) -> TUnit:
        return self._bf().right

    @property
    def south(self) -> TUnit:
        return self._bf().bottom

    @property
    def north(self) -> TUnit:
        return self._bf().top

    @property
    def width(self) -> TUnit:
        return self._bf().width()

    @property
    def height(self) -> TUnit:
        return self._bf().height()

    @property
    def sw(self) -> tuple[TUnit, TUnit]:
        bb = self._bf()
        return (bb.left, bb.bottom)

    @property
    def nw(self) -> tuple[TUnit, TUnit]:
        bb = self._bf()
        return (bb.left, bb.top)

    @property
    def se(self) -> tuple[TUnit, TUnit]:
        bb = self._bf()
        return (bb.right, bb.bottom)

    @property
    def ne(self) -> tuple[TUnit, TUnit]:
        bb = self._bf()
        return (bb.right, bb.top)

    @property
    def cw(self) -> tuple[TUnit, TUnit]:
        bb = self._bf()
        return (bb.left, bb.center().y)

    @property
    def ce(self) -> tuple[TUnit, TUnit]:
        bb = self._bf()
        return (bb.right, bb.center().y)

    @property
    def sc(self) -> tuple[TUnit, TUnit]:
        bb = self._bf()
        return (bb.center().x, bb.bottom)

    @property
    def nc(self) -> tuple[TUnit, TUnit]:
        bb = self._bf()
        return (bb.center().x, bb.top)

    @property
    def cc(self) -> tuple[TUnit, TUnit]:
        c = self._bf().center()
        return (c.x, c.y)

    @property
    def center(self) -> tuple[TUnit, TUnit]:
        c = self._bf().center()
        return (c.x, c.y)


class GeometricObject(Generic[TUnit], ABC):
    @property
    @abstractmethod
    def kcl(self) -> KCLayout: ...

    @abstractmethod
    def bbox(self, layer: int | None = None) -> BoxLike[TUnit]: ...

    @abstractmethod
    def ibbox(self, layer: int | None = None) -> kdb.Box: ...

    @abstractmethod
    def dbbox(self, layer: int | None = None) -> kdb.DBox: ...

    @overload
    @abstractmethod
    def _standard_trans(self: GeometricObject[int]) -> type[kdb.Trans]: ...
    @overload
    @abstractmethod
    def _standard_trans(self: GeometricObject[float]) -> type[kdb.DCplxTrans]: ...
    @abstractmethod
    def _standard_trans(self) -> type[kdb.Trans | kdb.DCplxTrans]: ...

    @abstractmethod
    def transform(
        self,
        trans: kdb.Trans | kdb.DTrans | kdb.ICplxTrans | kdb.DCplxTrans,
        /,
    ) -> Any: ...

    @property
    def x(self) -> TUnit:
        """Returns the x-coordinate of the center of the bounding box."""
        return self.bbox().center().x

    @x.setter
    def x(self, __val: TUnit, /) -> None:
        """Moves self so that the bbox's center x-coordinate."""
        self.transform(self._standard_trans()(x=__val - self.bbox().center().x))

    @property
    def y(self) -> TUnit:
        """Returns the y-coordinate of the center of the bounding box."""
        return self.bbox().center().y

    @y.setter
    def y(self, __val: TUnit, /) -> None:
        """Moves self so that the bbox's center y-coordinate."""
        self.transform(self._standard_trans()(y=__val - self.bbox().center().y))

    @property
    def xmin(self) -> TUnit:
        """Returns the x-coordinate of the left edge of the bounding box."""
        return self.bbox().left

    @xmin.setter
    def xmin(self, __val: TUnit, /) -> None:
        """Moves self so that the bbox's left edge x-coordinate."""
        self.transform(self._standard_trans()(x=__val - self.bbox().left))

    @property
    def ymin(self) -> TUnit:
        """Returns the y-coordinate of the bottom edge of the bounding box."""
        return self.bbox().bottom

    @ymin.setter
    def ymin(self, __val: TUnit, /) -> None:
        """Moves self so that the bbox's bottom edge y-coordinate."""
        self.transform(self._standard_trans()(y=__val - self.bbox().bottom))

    @property
    def xmax(self) -> TUnit:
        """Returns the x-coordinate of the right edge of the bounding box."""
        return self.bbox().right

    @xmax.setter
    def xmax(self, __val: TUnit, /) -> None:
        """Moves self so that the bbox's right edge x-coordinate."""
        self.transform(self._standard_trans()(x=__val - self.bbox().right))

    @property
    def ymax(self) -> TUnit:
        """Returns the y-coordinate of the top edge of the bounding box."""
        return self.bbox().top

    @ymax.setter
    def ymax(self, __val: TUnit, /) -> None:
        """Moves self so that the bbox's top edge y-coordinate."""
        self.transform(self._standard_trans()(y=__val - self.bbox().top))

    @property
    def xsize(self) -> TUnit:
        """Returns the width of the bounding box."""
        return self.bbox().width()

    @xsize.setter
    def xsize(self, __val: TUnit, /) -> None:
        """Sets the width of the bounding box."""
        self.transform(self._standard_trans()(x=__val - self.bbox().width()))

    @property
    def ysize(self) -> TUnit:
        """Returns the height of the bounding box."""
        return self.bbox().height()

    @ysize.setter
    def ysize(self, __val: TUnit, /) -> None:
        """Sets the height of the bounding box."""
        self.transform(self._standard_trans()(y=__val - self.bbox().height()))

    @property
    def center(self) -> tuple[TUnit, TUnit]:
        """Returns the coordinate center of the bounding box."""
        center = self.bbox().center()
        return center.x, center.y

    @center.setter
    def center(self, __val: tuple[TUnit, TUnit], /) -> None:
        """Moves self so that the bbox's center coordinate."""
        self.transform(
            self._standard_trans()(
                __val[0] - self.bbox().center().x, __val[1] - self.bbox().center().y
            )
        )

    @overload
    def move(self, destination: tuple[TUnit, TUnit], /) -> Self: ...

    @overload
    def move(
        self, origin: tuple[TUnit, TUnit], destination: tuple[TUnit, TUnit]
    ) -> Self: ...

    def move(
        self,
        origin: tuple[TUnit, TUnit],
        destination: tuple[TUnit, TUnit] | None = None,
    ) -> Self:
        """Move self in dbu.

        Args:
            origin: reference point to move [dbu]
            destination: move origin so that it will land on this coordinate [dbu]
        """
        if destination is None:
            self.transform(self._standard_trans()(*origin))
        else:
            self.transform(
                self._standard_trans()(
                    destination[0] - origin[0], destination[1] - origin[1]
                )
            )
        return self

    @overload
    def movex(self, destination: TUnit, /) -> Self: ...

    @overload
    def movex(self, origin: TUnit, destination: TUnit) -> Self: ...

    def movex(self, origin: TUnit, destination: TUnit | None = None) -> Self:
        """Move self in x-direction in dbu.

        Args:
            origin: reference point to move [dbu]
            destination: move origin so that it will land on this coordinate [dbu]
        """
        if destination is None:
            self.transform(self._standard_trans()(x=origin))
        else:
            self.transform(self._standard_trans()(x=destination - origin))
        return self

    @overload
    def movey(self, destination: TUnit, /) -> Self: ...

    @overload
    def movey(self, origin: TUnit, destination: TUnit) -> Self: ...

    def movey(self, origin: TUnit, destination: TUnit | None = None) -> Self:
        """Move self in y-direction in dbu.

        Args:
            origin: reference point to move [dbu]
            destination: move origin so that it will land on this coordinate [dbu]
        """
        if destination is None:
            self.transform(self._standard_trans()(y=origin))
        else:
            self.transform(self._standard_trans()(y=destination - origin))
        return self

    @abstractmethod
    def rotate(self, angle: TUnit, center: tuple[TUnit, TUnit] | None = None) -> Self:
        """Rotate self."""
        ...

    @abstractmethod
    def mirror(
        self, p1: tuple[TUnit, TUnit] = ..., p2: tuple[TUnit, TUnit] = ...
    ) -> Self:
        """Mirror self at a line."""
        ...

    @abstractmethod
    def mirror_x(self, x: TUnit = ...) -> Self:
        """Mirror self at an y-axis at position x."""
        ...

    @abstractmethod
    def mirror_y(self, y: TUnit = ...) -> Self:
        """Mirror self at an x-axis at position y."""
        ...

    @property
    def ix(self) -> int:
        """Returns the x-coordinate of the center of the bounding box."""
        return self.ibbox().center().x

    @ix.setter
    def ix(self, __val: int, /) -> None:
        """Moves self so that the bbox's center x-coordinate."""
        self.transform(kdb.Trans(__val - self.ibbox().center().x, 0))

    @property
    def iy(self) -> int:
        """Returns the y-coordinate of the center of the bounding box."""
        return self.ibbox().center().y

    @iy.setter
    def iy(self, __val: int, /) -> None:
        """Moves self so that the bbox's center y-coordinate."""
        self.transform(kdb.Trans(0, __val - self.ibbox().center().y))

    @property
    def ixmin(self) -> int:
        """Returns the x-coordinate of the left edge of the bounding box."""
        return self.ibbox().left

    @ixmin.setter
    def ixmin(self, __val: int, /) -> None:
        """Moves self so that the bbox's left x-coordinate."""
        self.transform(kdb.Trans(__val - self.ibbox().left, 0))

    @property
    def iymin(self) -> int:
        """Returns the y-coordinate of the bottom edge of the bounding box."""
        return self.ibbox().bottom

    @iymin.setter
    def iymin(self, __val: int, /) -> None:
        """Moves self so that the bbox's bottom y-coordinate."""
        self.transform(kdb.Trans(0, __val - self.ibbox().bottom))

    @property
    def ixmax(self) -> int:
        """Returns the x-coordinate of the right edge of the bounding box."""
        return self.ibbox().right

    @ixmax.setter
    def ixmax(self, __val: int, /) -> None:
        """Moves self so that the bbox's right x-coordinate."""
        self.transform(kdb.Trans(__val - self.ibbox().right, 0))

    @property
    def iymax(self) -> int:
        """Returns the y-coordinate of the top edge of the bounding box."""
        return self.ibbox().top

    @iymax.setter
    def iymax(self, __val: int, /) -> None:
        """Moves self so that the bbox's top y-coordinate."""
        self.transform(kdb.Trans(0, __val - self.ibbox().top))

    @property
    def ixsize(self) -> int:
        """Returns the width of the bounding box."""
        return self.ibbox().width()

    @ixsize.setter
    def ixsize(self, __val: int, /) -> None:
        """Sets the width of the bounding box."""
        self.transform(kdb.Trans(__val - self.ibbox().width(), 0))

    @property
    def iysize(self) -> int:
        """Returns the height of the bounding box."""
        return self.ibbox().height()

    @iysize.setter
    def iysize(self, __val: int, /) -> None:
        """Sets the height of the bounding box."""
        self.transform(kdb.Trans(0, __val - self.ibbox().height()))

    @property
    def icenter(self) -> tuple[int, int]:
        """Returns the coordinate center of the bounding box."""
        center = self.ibbox().center()
        return center.x, center.y

    @icenter.setter
    def icenter(self, val: tuple[int, int]) -> None:
        """Moves self so that the bbox's center coordinate."""
        self.transform(
            kdb.Trans(
                val[0] - self.ibbox().center().x, val[1] - self.ibbox().center().y
            )
        )

    @overload
    def imove(self, destination: tuple[int, int], /) -> Self: ...

    @overload
    def imove(
        self, origin: tuple[int, int], destination: tuple[int, int] | None = None
    ) -> Self: ...

    def imove(
        self, origin: tuple[int, int], destination: tuple[int, int] | None = None
    ) -> Self:
        """Move self in dbu.

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
        return self

    @overload
    def imovex(self, destination: int, /) -> Self: ...

    @overload
    def imovex(self, origin: int, destination: int | None = None) -> Self: ...

    def imovex(self, origin: int, destination: int | None = None) -> Self:
        """Move self in x-direction in dbu.

        Args:
            origin: reference point to move [dbu]
            destination: move origin so that it will land on this coordinate [dbu]
        """
        if destination is None:
            self.transform(kdb.Trans(origin, 0))
        else:
            self.transform(kdb.Trans(destination - origin, 0))
        return self

    @overload
    def imovey(self, destination: int, /) -> Self: ...

    @overload
    def imovey(self, origin: int, destination: int | None = None) -> Self: ...

    def imovey(self, origin: int, destination: int | None = None) -> Self:
        """Move self in y-direction in dbu.

        Args:
            origin: reference point to move [dbu]
            destination: move origin so that it will land on this coordinate [dbu]
        """
        if destination is None:
            self.transform(kdb.Trans(0, origin))
        else:
            self.transform(kdb.Trans(0, destination - origin))
        return self

    def irotate(self, angle: int, center: tuple[int, int] | None = None) -> Self:
        """Rotate self in increments of 90°."""
        t: kdb.Trans | None = None
        if center:
            t = kdb.Trans(*center)
            self.transform(t.inverted())
        self.transform(kdb.Trans(rot=angle, mirrx=False, x=0, y=0))
        if center and t:
            self.transform(t)
        return self

    def imirror(
        self, p1: tuple[int, int] = (0, 1000), p2: tuple[int, int] = (0, 0)
    ) -> Self:
        """Mirror self at a line."""
        p1_ = kdb.Point(p1[0], p1[1]).to_dtype(self.kcl.dbu)
        p2_ = kdb.Point(p2[0], p2[1]).to_dtype(self.kcl.dbu)
        mirror_v = p2_ - p1_
        disp = kdb.DVector(self.dxmin, self.dymin)
        angle = np.mod(np.rad2deg(np.arctan2(mirror_v.y, mirror_v.x)), 180) * 2
        dedge = kdb.DEdge(p1_, p2_)

        v = kdb.DVector(-mirror_v.y, mirror_v.x)

        dedge_disp = kdb.DEdge(disp.to_p(), (v + disp).to_p())

        cross_point = dedge.cut_point(dedge_disp)

        self.transform(
            kdb.DCplxTrans(1.0, angle, True, (cross_point.to_v() - disp) * 2)
        )

        return self

    def imirror_x(self, x: int = 0) -> Self:
        """Mirror self at an y-axis at position x."""
        self.transform(kdb.Trans(2, True, 2 * x, 0))
        return self

    def imirror_y(self, y: int = 0) -> Self:
        """Mirror self at an x-axis at position y."""
        self.transform(kdb.Trans(0, True, 0, 2 * y))
        return self

    @property
    def dx(self) -> float:
        """X coordinate of the center of the bounding box in um."""
        return self.dbbox().center().x

    @dx.setter
    def dx(self, __val: float, /) -> None:
        """Moves self so that the bbox's center x-coordinate in um."""
        self.transform(kdb.DTrans(__val - self.dbbox().center().x, 0))

    @property
    def dy(self) -> float:
        """Y coordinate of the center of the bounding box in um."""
        return self.dbbox().center().y

    @dy.setter
    def dy(self, __val: float, /) -> None:
        """Moves self so that the bbox's center y-coordinate in um."""
        self.transform(kdb.DTrans(0, __val - self.dbbox().center().y))

    @property
    def dxmin(self) -> float:
        """Returns the x-coordinate of the left edge of the bounding box."""
        return self.dbbox().left

    @dxmin.setter
    def dxmin(self, __val: float, /) -> None:
        """Moves self so that the bbox's left x-coordinate in um."""
        self.transform(kdb.DTrans(__val - self.dbbox().left, 0))

    @property
    def dymin(self) -> float:
        """Returns the y-coordinate of the bottom edge of the bounding box."""
        return self.dbbox().bottom

    @dymin.setter
    def dymin(self, __val: float, /) -> None:
        """Moves self so that the bbox's bottom y-coordinate in um."""
        self.transform(kdb.DTrans(0, __val - self.dbbox().bottom))

    @property
    def dxmax(self) -> float:
        """Returns the x-coordinate of the right edge of the bounding box."""
        return self.dbbox().right

    @dxmax.setter
    def dxmax(self, __val: float, /) -> None:
        """Moves self so that the bbox's right x-coordinate in um."""
        self.transform(kdb.DTrans(__val - self.dbbox().right, 0))

    @property
    def dymax(self) -> float:
        """Returns the y-coordinate of the top edge of the bounding box."""
        return self.dbbox().top

    @dymax.setter
    def dymax(self, __val: float, /) -> None:
        """Moves self so that the bbox's top y-coordinate in um."""
        self.transform(kdb.DTrans(0, __val - self.dbbox().top))

    @property
    def dxsize(self) -> float:
        """Returns the width of the bounding box."""
        return self.dbbox().width()

    @dxsize.setter
    def dxsize(self, __val: float, /) -> None:
        """Sets the width of the bounding box in um."""
        self.transform(kdb.DTrans(__val - self.dbbox().width(), 0))

    @property
    def dysize(self) -> float:
        """Returns the height of the bounding box."""
        return self.dbbox().height()

    @dysize.setter
    def dysize(self, __val: float, /) -> None:
        """Sets the height of the bounding box in um."""
        self.transform(kdb.DTrans(0, __val - self.dbbox().height()))

    @property
    def dcenter(self) -> tuple[float, float]:
        """Coordinate of the center of the bounding box in um."""
        center = self.dbbox().center()
        return center.x, center.y

    @dcenter.setter
    def dcenter(self, val: tuple[float, float]) -> None:
        """Moves self so that the bbox's center coordinate in um."""
        self.transform(
            kdb.DTrans(
                val[0] - self.dbbox().center().x, val[1] - self.dbbox().center().y
            )
        )

    @overload
    def dmove(self, destination: tuple[float, float], /) -> Self: ...

    @overload
    def dmove(
        self,
        origin: tuple[float, float],
        destination: tuple[float, float] | None = None,
    ) -> Self: ...

    def dmove(
        self,
        origin: tuple[float, float],
        destination: tuple[float, float] | None = None,
    ) -> Self:
        """Move self in um.

        Args:
            origin: reference point to move
            destination: move origin so that it will land on this coordinate
        """
        if destination is None:
            self.transform(kdb.DCplxTrans(*origin))
        else:
            self.transform(
                kdb.DCplxTrans(destination[0] - origin[0], destination[1] - origin[1])
            )
        return self

    @overload
    def dmovex(self, destination: float, /) -> Self: ...

    @overload
    def dmovex(self, origin: float, destination: float | None = None) -> Self: ...

    def dmovex(self, origin: float, destination: float | None = None) -> Self:
        """Move self in x-direction in um.

        Args:
            origin: reference point to move
            destination: move origin so that it will land on this coordinate
        """
        if destination is None:
            self.transform(kdb.DCplxTrans(origin, 0))
        else:
            self.transform(kdb.DCplxTrans(destination - origin, 0))
        return self

    @overload
    def dmovey(self, destination: float, /) -> Self: ...

    @overload
    def dmovey(self, origin: float, destination: float | None = None) -> Self: ...

    def dmovey(self, origin: float, destination: float | None = None) -> Self:
        """Move self in y-direction in um.

        Args:
            origin: reference point to move
            destination: move origin so that it will land on this coordinate
        """
        if destination is None:
            self.transform(kdb.DCplxTrans(0, origin))
        else:
            self.transform(kdb.DCplxTrans(0, destination - origin))
        return self

    def drotate(self, angle: float, center: tuple[float, float] | None = None) -> Self:
        """Rotate self by a given angle in degrees.

        Args:
            angle: angle to rotate self
            center: reference point to rotate around
        """
        t: kdb.DCplxTrans | None = None
        if center:
            t = kdb.DCplxTrans(*center)
            self.transform(t.inverted())
        self.transform(kdb.DCplxTrans(rot=angle, mirrx=False, x=0, y=0))
        if center and t:
            self.transform(t)
        return self

    def dmirror(
        self, p1: tuple[float, float] = (0, 1), p2: tuple[float, float] = (0, 0)
    ) -> Self:
        """Mirror self at a line."""
        p1_ = kdb.DPoint(p1[0], p1[1])
        p2_ = kdb.DPoint(p2[0], p2[1])
        mirror_v = p2_ - p1_
        disp = kdb.DVector(self.dxmin, self.dymin)
        angle = np.mod(np.rad2deg(np.arctan2(mirror_v.y, mirror_v.x)), 180) * 2
        dedge = kdb.DEdge(p1_, p2_)

        v = mirror_v
        v = kdb.DVector(-v.y, v.x)

        dedge_disp = kdb.DEdge(disp.to_p(), (v + disp).to_p())

        cross_point = dedge.cut_point(dedge_disp)

        self.transform(
            kdb.DCplxTrans(1.0, angle, True, (cross_point.to_v() - disp) * 2)
        )

        return self

    def dmirror_x(self, x: float = 0) -> Self:
        """Mirror self at an y-axis at position x."""
        self.transform(kdb.DCplxTrans(1, 180, True, 2 * x, 0))
        return self

    def dmirror_y(self, y: float = 0) -> Self:
        """Mirror self at an x-axis at position y."""
        self.transform(kdb.DCplxTrans(1, 0, True, 0, 2 * y))
        return self

    @property
    def size_info(self) -> SizeInfo[TUnit]:
        return SizeInfo[TUnit](self.bbox)

    @property
    def isize_info(self) -> SizeInfo[int]:
        return SizeInfo[int](self.ibbox)

    @property
    def dsize_info(self) -> SizeInfo[float]:
        return SizeInfo[float](self.dbbox)


class DBUGeometricObject(GeometricObject[int], ABC):
    def bbox(self, layer: int | None = None) -> kdb.Box:
        return self.ibbox(layer)

    def _standard_trans(self) -> type[kdb.Trans]:
        return kdb.Trans

    def rotate(self, angle: int, center: tuple[int, int] | None = None) -> Self:
        return self.irotate(angle, center)

    def mirror_x(self, x: int = 0) -> Self:
        return self.imirror_x(x)

    def mirror_y(self, y: int = 0) -> Self:
        return self.imirror_y(y)

    def mirror(
        self, p1: tuple[int, int] = (0, 1000), p2: tuple[int, int] = (0, 0)
    ) -> Self:
        return self.imirror(p1, p2)


class UMGeometricObject(GeometricObject[float], ABC):
    def bbox(self, layer: int | None = None) -> kdb.DBox:
        return self.dbbox(layer)

    def _standard_trans(self) -> type[kdb.DCplxTrans]:
        return kdb.DCplxTrans

    def rotate(self, angle: float, center: tuple[float, float] | None = None) -> Self:
        return self.drotate(angle, center)

    def mirror_x(self, x: float = 0) -> Self:
        return self.dmirror_x(x)

    def mirror_y(self, y: float = 0) -> Self:
        return self.dmirror_y(y)

    def mirror(
        self, p1: tuple[float, float] = (0, 1), p2: tuple[float, float] = (0, 0)
    ) -> Self:
        return self.dmirror(p1, p2)
