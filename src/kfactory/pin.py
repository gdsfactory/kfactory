from __future__ import annotations

import re
from abc import ABC, abstractmethod
from copy import copy
from typing import TYPE_CHECKING, Any, Generic, Literal, overload

import klayout.db as kdb
from pydantic import (
    BaseModel,
    model_serializer,
)
from typing_extensions import TypedDict

from .conf import config
from .settings import Info
from .typings import TPin, TUnit
from .utilities import pprint_pins

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence

    from .layer import LayerEnum
    from .layout import KCLayout
    from .protocols import PointLike


class BasePinDict(TypedDict):
    """TypedDict for the BasePin."""

    name: str | None
    kcl: KCLayout
    layer_info: kdb.LayerInfo
    width: int
    pos: kdb.Point
    allowed_angles: set[Literal[0, 1, 2, 3]]
    info: Info
    pin_type: str


class BasePin(BaseModel, arbitrary_types_allowed=True):
    """Class representing the base port.

    This does not have any knowledge of units.
    """

    name: str | None
    kcl: KCLayout
    layer_info: kdb.LayerInfo
    width: int
    pos: kdb.Point
    allowed_angles: set[Literal[0, 1, 2, 3]]
    info: Info = Info()
    pin_type: str

    def __copy__(self) -> BasePin:
        """Copy the BasePin."""
        return BasePin(
            name=self.name,
            kcl=self.kcl,
            layer_info=self.layer_info,
            width=self.width,
            pos=self.pos,
            allowed_angles=self.allowed_angles.copy(),
            info=self.info.model_copy(),
            pin_type=self.pin_type,
        )

    def transformed(
        self,
        trans: kdb.Trans | kdb.DCplxTrans = kdb.Trans.R0,
        post_trans: kdb.Trans | kdb.DCplxTrans = kdb.Trans.R0,
    ) -> BasePin:
        """Get a transformed copy of the BasePin."""
        base = copy(self)
        if isinstance(trans, kdb.DCplxTrans):
            trans_: kdb.Trans | kdb.ICplxTrans = trans.to_itrans(self.kcl.dbu)
            transformed_angles: list[Literal[0, 1, 2, 3]] = {
                (a + int(trans.angle()) % 360 // 90) % 4 for a in self.allowed_angles
            }
        else:
            trans_ = trans
            transformed_angles: list[Literal[0, 1, 2, 3]] = {
                (a + trans.angle()) % 4 for a in self.allowed_angles
            }

        if isinstance(post_trans, kdb.DCplxTrans):
            post_trans_: kdb.Trans | kdb.ICplxTrans = post_trans.to_itrans(self.kcl.dbu)
            post_transformed_angles: list[Literal[0, 1, 2, 3]] = {
                (a + int(trans.angle()) % 360 // 90) % 4 for a in transformed_angles
            }
        else:
            post_trans_ = post_trans
            post_transformed_angles: list[Literal[0, 1, 2, 3]] = {
                (a + post_trans.angle()) % 4 for a in transformed_angles
            }

        base.pos = trans_ * self.pos * post_trans_
        base.allowed_angles = post_transformed_angles

        return base

    @model_serializer()
    def ser_model(self) -> BasePinDict:
        """Serialize the BasePin."""
        return BasePinDict(
            name=self.name,
            kcl=self.kcl,
            width=self.width,
            pos=self.pos,
            allowed_angles=self.allowed_angles.copy(),
            layer_info=self.layer_info,
            info=self.info.model_copy(),
            pin_type=self.pin_type,
        )


class ProtoPin(ABC, Generic[TUnit]):
    """Base class for kf.Port, kf.DPort."""

    yaml_tag: str = "!Port"
    _base: BasePin

    @abstractmethod
    def __init__(
        self,
        name: str | None = None,
        *,
        width: TUnit | None = None,
        layer: int | None = None,
        layer_info: kdb.LayerInfo | None = None,
        pin_type: str = "DC",
        pos: kdb.Point | None = None,
        allowed_angles: list[int] | None = None,
        allowed_orientations: list[float] | None = None,
        pin: ProtoPin[Any] | None = None,
        kcl: KCLayout | None = None,
        info: dict[str, int | float | str] = ...,
        base: BasePin | None = None,
    ) -> None:
        """Initialise a ProtoPort."""
        match (allowed_angles, allowed_orientations):
            case None, None:
                raise ValueError(
                    "'allowed_angles' or 'allowed_orientations' must be defined."
                )
            case _, None:
                self.allowed_angles = set(allowed_angles)
            case None, _:
                self.allowed_orientations = set(allowed_orientations)
            case _:
                raise ValueError(
                    "Only one of 'allowed_angles' or 'allowed_orientations' "
                    "should be defined, not both."
                )

    @property
    def base(self) -> BasePin:
        """Get the BasePin associated with this Port."""
        return self._base

    @property
    def kcl(self) -> KCLayout:
        """KCLayout associated to the prot."""
        return self._base.kcl

    @kcl.setter
    def kcl(self, value: KCLayout) -> None:
        self._base.kcl = value

    @property
    def name(self) -> str | None:
        """Name of the port."""
        return self._base.name

    @name.setter
    def name(self, value: str | None) -> None:
        self._base.name = value

    @property
    def pin_type(self) -> str:
        """Type of the port.

        Usually "optical" or "electrical".
        """
        return self._base.pin_type

    @pin_type.setter
    def pin_type(self, value: str) -> None:
        self._base.pin_type = value

    @property
    def info(self) -> Info:
        """Additional info about the port."""
        return self._base.info

    @info.setter
    def info(self, value: Info) -> None:
        self._base.info = value

    @property
    def layer(self) -> LayerEnum | int:
        """Get the layer index of the port.

        This corresponds to the port's cross section's main layer converted to the
        index.
        """
        return self.kcl.find_layer(self.layer_info, allow_undefined_layers=True)

    @property
    def layer_info(self) -> kdb.LayerInfo:
        """Get the layer info of the port.

        This corresponds to the port's cross section's main layer.
        """
        return self.base.layer_info

    def __eq__(self, other: object) -> bool:
        """Support for `pin1 == pin2` comparisons."""
        return self._base == other._base if isinstance(other, ProtoPin) else False

    @property
    @abstractmethod
    def pos(self) -> PointLike[TUnit]: ...

    @pos.setter
    @abstractmethod
    def pos(self, value: PointLike[TUnit]) -> None: ...

    def to_itype(self) -> Pin:
        """Convert the port to a dbu port."""
        return Pin(base=self._base)

    def to_dtype(self) -> DPin:
        """Convert the port to a um port."""
        return DPin(base=self._base)

    @property
    def allowed_angles(self) -> list[Literal[0, 1, 2, 3]]:
        """Angle of the transformation.

        In the range of `[0,1,2,3]` which are increments in 90°.
        """
        return self._allowed_angles

    @allowed_angles.setter
    def allowed_angles(self, value: Sequence[Literal[0, 1, 2, 3]]) -> None:
        self._allowed_angles = list(value)

    @property
    def allowed_orientations(self) -> list[Literal[0, 90, 180, 270]]:
        """Returns orientation in degrees for gdsfactory compatibility.

        In the range of `[0,360)`
        """
        return [a * 90 for a in self.base.allowed_angles]  # type: ignore[misc]

    @allowed_orientations.setter
    def allowed_orientations(self, value: Sequence[float]) -> None:
        """Set the orientation of the port."""
        values = {(a % 360) / 90 for a in value}
        if values - {0, 1, 2, 3} is not None:
            raise ValueError("Only {0,90,180,270} are allowed as orientation.")
        self.base.allowed_angles |= values

    @abstractmethod
    def copy(
        self,
        trans: kdb.Trans | kdb.DCplxTrans = kdb.Trans.R0,
        post_trans: kdb.Trans | kdb.DCplxTrans = kdb.Trans.R0,
    ) -> ProtoPin[TUnit]:
        """Copy the port with a transformation."""
        ...

    @property
    def center(self) -> tuple[TUnit, TUnit]:
        """Returns port center."""
        return (self.pos.x, self.pos.y)

    @center.setter
    def center(self, value: tuple[TUnit, TUnit]) -> None:
        self.x = value[0]
        self.y = value[1]

    @property
    def x(self) -> TUnit:
        """X coordinate of the port."""
        return self.pos.x

    @x.setter
    @abstractmethod
    def x(self, value: TUnit) -> None: ...

    @property
    def y(self) -> TUnit:
        """Y coordinate of the port."""
        return self.pos.y

    @y.setter
    @abstractmethod
    def y(self, value: TUnit) -> None: ...

    @property
    @abstractmethod
    def width(self) -> TUnit:
        """Width of the port."""
        ...

    @property
    def ix(self) -> int:
        """X coordinate of the port in dbu."""
        return self.base.pos.x

    @ix.setter
    def ix(self, value: int) -> None:
        self.base.pos.x = value

    @property
    def iy(self) -> int:
        """Y coordinate of the port in dbu."""
        return self.base.pos.y

    @iy.setter
    def iy(self, value: int) -> None:
        self.base.pos.y = value

    @property
    def iwidth(self) -> int:
        """Width of the port in dbu."""
        return self._base.width

    @property
    def dx(self) -> float:
        """X coordinate of the port in um."""
        return self.kcl.to_um(self.base.pos.x)

    @dx.setter
    def dx(self, value: float) -> None:
        self.base.pos.x = self.kcl.to_dbu(value)

    @property
    def dy(self) -> float:
        """Y coordinate of the port in um."""
        return self.kcl.to_um(self.base.pos.y)

    @dy.setter
    def dy(self, value: float) -> None:
        self.base.pos.y = self.kcl.to_dbu(value)

    @property
    def dcenter(self) -> tuple[float, float]:
        """Coordinate of the port in um."""
        p = self.kcl.to_um(self.base.pos)
        return p.x, p.y

    @dcenter.setter
    def dcenter(self, pos: tuple[float, float]) -> None:
        self.base.pos = kdb.DPoint(*pos).to_itype(self.kcl.dbu)

    @property
    def dwidth(self) -> float:
        """Width of the port in um."""
        return self.kcl.to_um(self._base.width)

    def print(self, print_type: Literal["dbu", "um", None] = None) -> None:
        """Print the port pretty."""
        config.console.print(pprint_pins([self], unit=print_type))

    def __repr__(self) -> str:
        """String representation of port."""
        return (
            f"{self.__class__.__name__}({self.name=}"
            f", {self.width=}, trans={self.dcplx_trans.to_s()}, layer="
            f"{self.layer_info}, pin_type={self.pin_type})"
        )


class Pin(ProtoPin[int]):
    """
    Electrical pin. Equivatelnt to optical port but for electrical connections.

    Attributes:
        name: String to name the pin.
        width: The width of the pin in dbu.
        layer: Index of the layer or a LayerEnum that acts like an integer, but can
            contain layer number and datatype
        layer_info: LayerInfo object containing layer information.
        pin_type: A string defining the type of the pin
        pos: Position of the pin as a kdb.Point
        allowed_angles: Possible connection angles to the pin.
        info: A dictionary with additional info. Not reflected in GDS. Copy will make a
            (shallow) copy of it.
        kcl: Link to the layout this port resides in.
    """

    @overload
    def __init__(
        self,
        name: str | None = None,
        *,
        width: int | None = None,
        layer: int | None = None,
        pin_type: str = "DC",
        pos: kdb.Point | None = None,
        allowed_angles: list[int] | None = None,
        kcl: KCLayout | None = None,
        info: dict[str, int | float | str] = ...,
    ) -> None: ...

    @overload
    def __init__(
        self,
        name: str | None = None,
        *,
        width: int | None = None,
        layer_info: kdb.LayerInfo | None = None,
        pin_type: str = "DC",
        pos: kdb.Point | None = None,
        allowed_angles: list[int] | None = None,
        kcl: KCLayout | None = None,
        info: dict[str, int | float | str] = ...,
    ) -> None: ...

    @overload
    def __init__(self, *, base: BasePin) -> None: ...

    @overload
    def __init__(self, *, pin: ProtoPin[Any]) -> None: ...

    def __init__(
        self,
        name: str | None = None,
        *,
        width: int | None = None,
        layer: int | None = None,
        layer_info: kdb.LayerInfo | None = None,
        pin_type: str = "DC",
        pos: kdb.Point | None = None,
        allowed_angles: list[int] | None = None,
        pin: ProtoPin[Any] | None = None,
        kcl: KCLayout | None = None,
        info: dict[str, int | float | str] = ...,
        base: BasePin | None = None,
    ) -> None:
        if pin is not None:
            self._base = pin.base.__copy__()
            return
        if base is not None:
            self._base = base
            return

        if info is None:
            info = {}
        info_ = Info(**info)

        from .layout import get_default_kcl

        kcl_ = kcl or get_default_kcl()
        if layer_info is None:
            if layer is None:
                raise ValueError(
                    "layer or layer_info for a pin must be defined if"
                    " 'pin and base are None'"
                )
            layer_info = kcl_.layout.get_info(layer)
        if width is None:
            raise ValueError(
                "any width and layer must be given if'pin and base are None'"
            )
        if pos is None:
            raise ValueError("pos for a pin must be defined if 'pin and base are None'")
        if allowed_angles is None:
            raise ValueError(
                "allowed angles for a pin must be defined if 'pin and base are None'"
            )

        self._base = BasePin(
            name=name,
            kcl=kcl_,
            layer_info=layer_info,
            width=width,
            pos=pos,
            allowed_angles=set(allowed_angles),
            info=info_,
            pin_type=pin_type,
        )

    def copy(
        self,
        trans: kdb.Trans | kdb.DCplxTrans = kdb.Trans.R0,
        post_trans: kdb.Trans | kdb.DCplxTrans = kdb.Trans.R0,
    ) -> Pin:
        return Pin(base=self._base.transformed(trans=trans, post_trans=post_trans))

    def copy_polar(
        self, d: int = 0, d_orth: int = 0, angle: int = 2, mirror: bool = False
    ) -> Pin:
        return self.copy(post_trans=kdb.Trans(angle, mirror, d, d_orth))

    @property
    def x(self) -> int:
        return self.ix

    @x.setter
    def x(self, value: int) -> None:
        self.ix = value

    @property
    def y(self) -> int:
        return self.iy

    @y.setter
    def y(self, value: int) -> None:
        self.iy = value

    @property
    def width(self) -> int:
        """Width of the pin in um."""
        return self.iwidth

    @property
    def pos(self) -> kdb.Point:
        return self.base.pos

    @pos.setter
    def pos(self, value: kdb.Point) -> None:
        self.base.pos = value


class DPin(ProtoPin[float]):
    @overload
    def __init__(
        self,
        name: str | None = None,
        *,
        width: float | None = None,
        layer: int | None = None,
        pin_type: str = "DC",
        pos: kdb.DPoint | None = None,
        allowed_orientations: list[float] | None = None,
        kcl: KCLayout | None = None,
        info: dict[str, int | float | str] = ...,
    ) -> None: ...

    @overload
    def __init__(
        self,
        name: str | None = None,
        *,
        width: float | None = None,
        layer_info: kdb.LayerInfo | None = None,
        pin_type: str = "DC",
        pos: kdb.DPoint | None = None,
        allowed_orientations: list[float] | None = None,
        kcl: KCLayout | None = None,
        info: dict[str, int | float | str] = ...,
    ) -> None: ...

    @overload
    def __init__(self, *, base: BasePin) -> None: ...

    @overload
    def __init__(self, *, pin: ProtoPin[Any]) -> None: ...

    def __init__(
        self,
        name: str | None = None,
        *,
        width: float | None = None,
        layer: int | None = None,
        layer_info: kdb.LayerInfo | None = None,
        pin_type: str = "DC",
        pos: kdb.DPoint | None = None,
        allowed_orientations: list[float] | None = None,
        pin: ProtoPin[Any] | None = None,
        kcl: KCLayout | None = None,
        info: dict[str, int | float | str] = ...,
        base: BasePin | None = None,
    ) -> None:
        if pin is not None:
            self._base = pin.base.__copy__()
            return
        if base is not None:
            self._base = base
            return

        if info is None:
            info = {}
        info_ = Info(**info)

        from .layout import get_default_kcl

        kcl_ = kcl or get_default_kcl()
        if layer_info is None:
            if layer is None:
                raise ValueError(
                    "layer or layer_info for a dpin must be defined if"
                    " 'pin and base are None'"
                )
            layer_info = kcl_.layout.get_info(layer)
        if width is None:
            raise ValueError(
                "any width and layer must be given if 'pin and base are None'"
            )
        if pos is None:
            raise ValueError(
                "pos for a dpin must be defined if 'pin and base are None'"
            )
        if allowed_orientations is None:
            raise ValueError(
                "allowed orientations for a dpin must be defined if"
                " 'pin and base are None'"
            )

        self._base = BasePin(
            name=name,
            kcl=kcl_,
            layer_info=layer_info,
            width=self.kcl.to_dbu(width),
            pos=pos.to_itype(self.kcl.dbu),
            allowed_angles={int(a) % 360 // 90 for a in allowed_orientations},
            info=info_,
            pin_type=pin_type,
        )

    def copy(
        self,
        trans: kdb.Trans | kdb.DCplxTrans = kdb.Trans.R0,
        post_trans: kdb.Trans | kdb.DCplxTrans = kdb.Trans.R0,
    ) -> DPin:
        return DPin(base=self._base.transformed(trans=trans, post_trans=post_trans))

    def copy_polar(
        self,
        d: float = 0,
        d_orth: float = 0,
        orientation: float = 180,
        mirror: bool = False,
    ) -> DPin:
        return self.copy(
            post_trans=kdb.DCplxTrans(rot=orientation, mirrx=mirror, x=d, y=d_orth)
        )

    @property
    def x(self) -> float:
        """X coordinate of the pin in um."""
        return self.dx

    @x.setter
    def x(self, value: float) -> None:
        self.dx = value

    @property
    def y(self) -> float:
        """Y coordinate of the pin in um."""
        return self.dy

    @y.setter
    def y(self, value: float) -> None:
        self.dy = value

    @property
    def width(self) -> float:
        """Width of the pin in um."""
        return self.dwidth

    @property
    def pos(self) -> kdb.DPoint:
        return self.base.pos.to_dtype(self.kcl.dbu)

    @pos.setter
    def pos(self, value: kdb.DPoint) -> None:
        self.base.pos = value.to_itype(self.kcl.dbu)


def filter_regex(pins: Iterable[TPin], regex: str) -> filter[TPin]:
    """Filter iterable/sequence of pins by pin name."""
    pattern = re.compile(regex)

    def regex_filter(p: TPin) -> bool:
        if p.name is not None:
            return bool(pattern.match(p.name))
        return False

    return filter(regex_filter, pins)


def filter_layer(pins: Iterable[TPin], layer: int | LayerEnum) -> filter[TPin]:
    """Filter iterable/sequence of pins by layer index / LayerEnum."""

    def layer_filter(p: TPin) -> bool:
        return p.layer == layer

    return filter(layer_filter, pins)


def filter_pin_type(pins: Iterable[TPin], pin_type: str) -> filter[TPin]:
    """Filter iterable/sequence of pins by pin_type."""

    def pt_filter(p: TPin) -> bool:
        return p.pin_type == pin_type

    return filter(pt_filter, pins)


def filter_directions(
    pins: Iterable[TPin], allowed_directons: list[int]
) -> filter[TPin]:
    """Filter iterable/sequence of pins by directions :py:class:~`DIRECTION`."""

    def f_func(p: TPin) -> bool:
        for direction in allowed_directons:
            if direction not in p.base.allowed_angles:
                return False
        return True

    return filter(f_func, pins)


def filter_orientations(
    pins: Iterable[TPin], allowed_orientations: list[float]
) -> filter[TPin]:
    """Filter iterable/sequence of pins by orientations :py:class:~`DIRECTION`."""

    def f_func(p: TPin) -> bool:
        for orientation in allowed_orientations:
            if (int(orientation) % 360 // 90) not in p.base.allowed_angles:
                return False
        return True

    return filter(f_func, pins)
