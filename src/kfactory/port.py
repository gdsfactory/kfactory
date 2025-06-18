"""Utilities for Ports.

Mainly renaming functions
"""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from enum import IntEnum, IntFlag, auto
from typing import TYPE_CHECKING, Any, Generic, Literal, Self, overload

import klayout.db as kdb
from klayout import rdb
from pydantic import (
    BaseModel,
    model_serializer,
    model_validator,
)
from typing_extensions import TypedDict

from .conf import ANGLE_180, config
from .cross_section import (
    CrossSection,
    CrossSectionSpec,
    DCrossSection,
    SymmetricalCrossSection,
    TCrossSection,
)
from .settings import Info
from .typings import Angle, TPort, TUnit
from .utilities import pprint_ports

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable

    from .kcell import AnyTKCell, KCell
    from .layer import LayerEnum
    from .layout import KCLayout


def create_port_error(
    p1: ProtoPort[Any],
    p2: ProtoPort[Any],
    c1: AnyTKCell,
    c2: AnyTKCell,
    db: rdb.ReportDatabase,
    db_cell: rdb.RdbCell,
    cat: rdb.RdbCategory,
    dbu: float,
) -> None:
    """Create an error report for two ports."""
    it = db.create_item(db_cell, cat)
    if p1.name and p2.name:
        it.add_value(f"Port Names: {c1.name}.{p1.name}/{c2.name}.{p2.name}")
    it.add_value(
        port_polygon(p1.cross_section.width).transformed(p1.trans).to_dtype(dbu)
    )
    it.add_value(
        port_polygon(p2.cross_section.width).transformed(p2.trans).to_dtype(dbu)
    )


class PortCheck(IntFlag):
    """Check for port equality.

    This is used to check if two ports are equal.
    """

    opposite = auto()
    width = auto()
    layer = auto()
    port_type = auto()
    all_opposite = opposite + width + port_type + layer  # type: ignore[operator]
    all_overlap = width + port_type + layer  # type: ignore[operator]


def port_check(
    p1: Port, p2: Port, checks: PortCheck | int = PortCheck.all_opposite
) -> None:
    """Check if two ports are equal."""
    if checks & PortCheck.opposite:
        assert (
            p1.trans == p2.trans * kdb.Trans.R180
            or p1.trans == p2.trans * kdb.Trans.M90
        ), f"Transformations of ports not matching for opposite check{p1=} {p2=}"
    if (checks & PortCheck.opposite) == 0:
        assert p1.trans == p2.trans or p1.trans == p2.trans * kdb.Trans.M0, (
            f"Transformations of ports not matching for overlapping check {p1=} {p2=}"
        )
    if checks & PortCheck.width:
        assert p1.width == p2.width, f"Width mismatch for {p1=} {p2=}"
    if checks & PortCheck.layer:
        assert p1.layer == p2.layer, f"Layer mismatch for {p1=} {p2=}"
    if checks & PortCheck.port_type:
        assert p1.port_type == p2.port_type, f"Port type mismatch for {p1=} {p2=}"


class BasePortDict(TypedDict):
    """TypedDict for the BasePort."""

    name: str | None
    kcl: KCLayout
    cross_section: SymmetricalCrossSection
    trans: kdb.Trans | None
    dcplx_trans: kdb.DCplxTrans | None
    info: Info
    port_type: str


class BasePort(BaseModel, arbitrary_types_allowed=True):
    """Class representing the base port.

    This does not have any knowledge of units.
    """

    name: str | None
    kcl: KCLayout
    cross_section: SymmetricalCrossSection
    trans: kdb.Trans | None = None
    dcplx_trans: kdb.DCplxTrans | None = None
    info: Info = Info()
    port_type: str

    @model_validator(mode="after")
    def check_exclusivity(self) -> Self:
        """Check if the port has a valid transformation."""
        if self.trans is None and self.dcplx_trans is None:
            raise ValueError("Both trans and dcplx_trans cannot be None.")
        if self.trans is not None and self.dcplx_trans is not None:
            raise ValueError("Only one of trans or dcplx_trans can be set.")
        return self

    def __copy__(self) -> BasePort:
        """Copy the BasePort."""
        return BasePort(
            name=self.name,
            kcl=self.kcl,
            cross_section=self.cross_section,
            trans=self.trans.dup() if self.trans else None,
            dcplx_trans=self.dcplx_trans.dup() if self.dcplx_trans else None,
            info=self.info.model_copy(),
            port_type=self.port_type,
        )

    def transformed(
        self,
        trans: kdb.Trans | kdb.DCplxTrans = kdb.Trans.R0,
        post_trans: kdb.Trans | kdb.DCplxTrans = kdb.Trans.R0,
    ) -> BasePort:
        """Get a transformed copy of the BasePort."""
        base = self.__copy__()
        if (
            base.trans is not None
            and isinstance(trans, kdb.Trans)
            and isinstance(post_trans, kdb.Trans)
        ):
            base.trans = trans * base.trans * post_trans
            base.dcplx_trans = None
            return base
        if isinstance(trans, kdb.Trans):
            trans = kdb.DCplxTrans(trans.to_dtype(self.kcl.dbu))
        if isinstance(post_trans, kdb.Trans):
            post_trans = kdb.DCplxTrans(post_trans.to_dtype(self.kcl.dbu))
        dcplx_trans = self.dcplx_trans or kdb.DCplxTrans(
            t=self.trans.to_dtype(self.kcl.dbu)  # type: ignore[union-attr]
        )

        base.trans = None
        base.dcplx_trans = trans * dcplx_trans * post_trans
        return base

    def transform(
        self,
        trans: kdb.Trans | kdb.DCplxTrans = kdb.Trans.R0,
        post_trans: kdb.Trans | kdb.DCplxTrans = kdb.Trans.R0,
    ) -> Self:
        """Get a transformed copy of the BasePort."""
        base = self
        if (
            base.trans is not None
            and isinstance(trans, kdb.Trans)
            and isinstance(post_trans, kdb.Trans)
        ):
            base.trans = trans * base.trans * post_trans
            base.dcplx_trans = None
            return self
        if isinstance(trans, kdb.Trans):
            trans = kdb.DCplxTrans(trans.to_dtype(self.kcl.dbu))
        if isinstance(post_trans, kdb.Trans):
            post_trans = kdb.DCplxTrans(post_trans.to_dtype(self.kcl.dbu))
        dcplx_trans = self.dcplx_trans or kdb.DCplxTrans(
            t=self.trans.to_dtype(self.kcl.dbu)  # type: ignore[union-attr]
        )

        base.trans = None
        base.dcplx_trans = trans * dcplx_trans * post_trans
        return self

    @model_serializer()
    def ser_model(self) -> BasePortDict:
        """Serialize the BasePort."""
        trans = self.trans.dup() if self.trans is not None else None
        dcplx_trans = self.dcplx_trans.dup() if self.dcplx_trans is not None else None
        return BasePortDict(
            name=self.name,
            kcl=self.kcl,
            cross_section=self.cross_section,
            trans=trans,
            dcplx_trans=dcplx_trans,
            info=self.info.model_copy(),
            port_type=self.port_type,
        )

    def get_trans(self) -> kdb.Trans:
        """Get the transformation."""
        if self.trans is not None:
            return self.trans
        assert self.dcplx_trans is not None, "Both trans and dcplx_trans are None"
        return kdb.ICplxTrans(trans=self.dcplx_trans, dbu=self.kcl.dbu).s_trans()

    def get_dcplx_trans(self) -> kdb.DCplxTrans:
        """Get the complex transformation."""
        if self.dcplx_trans is not None:
            return self.dcplx_trans
        assert self.trans is not None, "Both trans and dcplx_trans are None"
        return kdb.DCplxTrans(self.trans.to_dtype(self.kcl.dbu))

    def __eq__(self, other: object) -> bool:
        """Check if two ports are equal."""
        if not isinstance(other, BasePort):
            return False
        return (
            (self.trans is None and other.trans is None)
            or (
                (
                    self.trans is not None
                    and other.trans is not None
                    and self.trans == other.trans
                )
                and (self.dcplx_trans is None and other.dcplx_trans is None)
            )
            or (
                (
                    self.dcplx_trans is not None
                    and other.dcplx_trans is not None
                    and self.dcplx_trans == other.dcplx_trans
                )
                and self.name == other.name
                and self.kcl == other.kcl
                and self.cross_section == other.cross_section
                and self.port_type == other.port_type
                and self.info == other.info
            )
        )


class ProtoPort(Generic[TUnit], ABC):
    """Base class for kf.Port, kf.DPort."""

    yaml_tag: str = "!Port"
    _base: BasePort

    @abstractmethod
    def __init__(
        self,
        name: str | None = None,
        *,
        width: TUnit | None = None,
        layer: int | None = None,
        layer_info: kdb.LayerInfo | None = None,
        port_type: str = "optical",
        trans: kdb.Trans | str | None = None,
        dcplx_trans: kdb.DCplxTrans | str | None = None,
        angle: TUnit | None = None,
        center: tuple[TUnit, TUnit] | None = None,
        mirror_x: bool = False,
        port: Port | None = None,
        kcl: KCLayout | None = None,
        info: dict[str, int | float | str] = ...,
        cross_section: TCrossSection[TUnit] | None = None,
        base: BasePort | None = None,
    ) -> None:
        """Initialise a ProtoPort."""
        ...

    @property
    def base(self) -> BasePort:
        """Get the BasePort associated with this Port."""
        return self._base

    @property
    def kcl(self) -> KCLayout:
        """KCLayout associated to the prot."""
        return self._base.kcl

    @kcl.setter
    def kcl(self, value: KCLayout) -> None:
        self._base.kcl = value

    @property
    @abstractmethod
    def cross_section(self) -> TCrossSection[TUnit]:
        """Get the cross section of the port."""
        ...

    @cross_section.setter
    @abstractmethod
    def cross_section(
        self, value: SymmetricalCrossSection | TCrossSection[Any]
    ) -> None: ...

    @property
    def name(self) -> str | None:
        """Name of the port."""
        return self._base.name

    @name.setter
    def name(self, value: str | None) -> None:
        self._base.name = value

    @property
    def port_type(self) -> str:
        """Type of the port.

        Usually "optical" or "electrical".
        """
        return self._base.port_type

    @port_type.setter
    def port_type(self, value: str) -> None:
        self._base.port_type = value

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
        return self.kcl.find_layer(
            self.cross_section.layer, allow_undefined_layers=True
        )

    @property
    def layer_info(self) -> kdb.LayerInfo:
        """Get the layer info of the port.

        This corresponds to the port's cross section's main layer.
        """
        return self.cross_section.layer

    def __eq__(self, other: object) -> bool:
        """Support for `port1 == port2` comparisons."""
        if isinstance(other, ProtoPort):
            return self._base == other._base
        return False

    @property
    def trans(self) -> kdb.Trans:
        """Simple Transformation of the Port.

        If this is set with the setter, it will overwrite any transformation or
        dcplx transformation
        """
        return (
            self._base.trans
            or kdb.ICplxTrans(self._base.dcplx_trans, self.kcl.layout.dbu).s_trans()
        )

    @trans.setter
    def trans(self, value: kdb.Trans) -> None:
        self._base.trans = value.dup()
        self._base.dcplx_trans = None

    @property
    def dcplx_trans(self) -> kdb.DCplxTrans:
        """Complex transformation (um based).

        If the internal transformation is simple, return a complex copy.

        The setter will set a complex transformation and overwrite the internal
        transformation (set simple to `None` and the complex to the provided value.
        """
        return self._base.dcplx_trans or kdb.DCplxTrans(
            self.trans.to_dtype(self.kcl.layout.dbu)
        )

    @dcplx_trans.setter
    def dcplx_trans(self, value: kdb.DCplxTrans) -> None:
        if value.is_complex() or value.disp != self.kcl.to_um(
            self.kcl.to_dbu(value.disp)
        ):
            self._base.dcplx_trans = value.dup()
            self._base.trans = None
        else:
            self._base.trans = kdb.ICplxTrans(value.dup(), self.kcl.dbu).s_trans()
            self._base.dcplx_trans = None

    def to_itype(self) -> Port:
        """Convert the port to a dbu port."""
        return Port(base=self._base)

    def to_dtype(self) -> DPort:
        """Convert the port to a um port."""
        return DPort(base=self._base)

    @property
    def angle(self) -> Angle:
        """Angle of the transformation.

        In the range of `[0,1,2,3]` which are increments in 90°.
        """
        return self.trans.angle

    @angle.setter
    def angle(self, value: int) -> None:
        self._base.trans = self.trans.dup()
        self._base.dcplx_trans = None
        self._base.trans.angle = value

    @property
    def orientation(self) -> float:
        """Returns orientation in degrees for gdsfactory compatibility.

        In the range of `[0,360)`
        """
        return self.dcplx_trans.angle

    @orientation.setter
    def orientation(self, value: float) -> None:
        """Set the orientation of the port."""
        if not self.dcplx_trans.is_complex():
            dcplx_trans = self.dcplx_trans
            dcplx_trans.angle = value
            self.dcplx_trans = dcplx_trans
        else:
            self._base.dcplx_trans = self.dcplx_trans
            self._base.dcplx_trans.angle = value

    @property
    def mirror(self) -> bool:
        """Returns `True`/`False` depending on the mirror flag on the transformation."""
        return self.trans.is_mirror()

    @mirror.setter
    def mirror(self, value: bool) -> None:
        """Setter for mirror flag on trans."""
        if self._base.trans:
            self._base.trans.mirror = value
        elif self._base.dcplx_trans:
            self._base.dcplx_trans.mirror = value

    @abstractmethod
    def copy(
        self,
        trans: kdb.Trans | kdb.DCplxTrans = kdb.Trans.R0,
        post_trans: kdb.Trans | kdb.DCplxTrans = kdb.Trans.R0,
    ) -> ProtoPort[TUnit]:
        """Copy the port with a transformation."""
        ...

    @property
    def center(self) -> tuple[TUnit, TUnit]:
        """Returns port center."""
        return (self.x, self.y)

    @center.setter
    def center(self, value: tuple[TUnit, TUnit]) -> None:
        self.x = value[0]
        self.y = value[1]

    @property
    @abstractmethod
    def x(self) -> TUnit:
        """X coordinate of the port."""
        ...

    @x.setter
    @abstractmethod
    def x(self, value: TUnit) -> None: ...

    @property
    @abstractmethod
    def y(self) -> TUnit:
        """Y coordinate of the port."""
        ...

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
        return self.trans.disp.x

    @ix.setter
    def ix(self, value: int) -> None:
        if self._base.trans:
            vec = self._base.trans.disp
            vec.x = value
            self._base.trans.disp = vec
        elif self._base.dcplx_trans:
            vec = self.trans.disp
            vec.x = value
            self._base.dcplx_trans.disp = self.kcl.to_um(vec)

    @property
    def iy(self) -> int:
        """Y coordinate of the port in dbu."""
        return self.trans.disp.y

    @iy.setter
    def iy(self, value: int) -> None:
        if self._base.trans:
            vec = self._base.trans.disp
            vec.y = value
            self._base.trans.disp = vec
        elif self._base.dcplx_trans:
            vec = self.trans.disp
            vec.y = value
            self._base.dcplx_trans.disp = self.kcl.to_um(vec)

    @property
    def iwidth(self) -> int:
        """Width of the port in dbu."""
        return self._base.cross_section.width

    @property
    def dx(self) -> float:
        """X coordinate of the port in um."""
        return self.dcplx_trans.disp.x

    @dx.setter
    def dx(self, value: float) -> None:
        vec = self.dcplx_trans.disp
        vec.x = value
        if self._base.trans:
            self._base.trans.disp = self.kcl.to_dbu(vec)
        elif self._base.dcplx_trans:
            self._base.dcplx_trans.disp = vec

    @property
    def dy(self) -> float:
        """Y coordinate of the port in um."""
        return self.dcplx_trans.disp.y

    @dy.setter
    def dy(self, value: float) -> None:
        vec = self.dcplx_trans.disp
        vec.y = value
        if self._base.trans:
            self._base.trans.disp = self.kcl.to_dbu(vec)
        elif self._base.dcplx_trans:
            self._base.dcplx_trans.disp = vec

    @property
    def dcenter(self) -> tuple[float, float]:
        """Coordinate of the port in um."""
        vec = self.dcplx_trans.disp
        return (vec.x, vec.y)

    @dcenter.setter
    def dcenter(self, pos: tuple[float, float]) -> None:
        if self._base.trans:
            self._base.trans.disp = self.kcl.to_dbu(kdb.DVector(*pos))
        elif self._base.dcplx_trans:
            self._base.dcplx_trans.disp = kdb.DVector(*pos)

    @property
    def icenter(self) -> tuple[int, int]:
        """Coordinate of the port in dbu."""
        vec = self.trans.disp
        return (vec.x, vec.y)

    @icenter.setter
    def icenter(self, pos: tuple[int, int]) -> None:
        if self._base.trans:
            self._base.trans.disp = kdb.Vector(*pos)
        elif self._base.dcplx_trans:
            self._base.dcplx_trans.disp = self.kcl.to_um(kdb.Vector(*pos))

    @property
    def dwidth(self) -> float:
        """Width of the port in um."""
        return self.kcl.to_um(self._base.cross_section.width)

    def print(self, print_type: Literal["dbu", "um", None] = None) -> None:
        """Print the port pretty."""
        config.console.print(pprint_ports([self], unit=print_type))

    def __repr__(self) -> str:
        """String representation of port."""
        return (
            f"{self.__class__.__name__}({self.name=}"
            f", {self.width=}, trans={self.dcplx_trans.to_s()}, layer="
            f"{self.layer_info}, port_type={self.port_type})"
        )

    def transform(
        self,
        trans: kdb.Trans | kdb.DCplxTrans = kdb.Trans.R0,
        post_trans: kdb.Trans | kdb.DCplxTrans = kdb.Trans.R0,
    ) -> Self:
        """Get a transformed copy of the BasePort."""
        self.base.transform(trans=trans, post_trans=post_trans)
        return self


class Port(ProtoPort[int]):
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
        d: Access port info in micrometer basis such as width and center / angle.
        kcl: Link to the layout this port resides in.
    """

    @overload
    def __init__(
        self,
        *,
        name: str | None = None,
        width: int,
        layer: LayerEnum | int,
        trans: kdb.Trans | str,
        kcl: KCLayout | None = None,
        port_type: str = "optical",
        info: dict[str, int | float | str] = ...,
    ) -> None: ...

    @overload
    def __init__(
        self,
        *,
        name: str | None = None,
        width: int,
        layer: LayerEnum | int,
        dcplx_trans: kdb.DCplxTrans | str,
        kcl: KCLayout | None = None,
        port_type: str = "optical",
        info: dict[str, int | float | str] = ...,
    ) -> None: ...

    @overload
    def __init__(
        self,
        name: str | None = None,
        *,
        width: int,
        layer: LayerEnum | int,
        port_type: str = "optical",
        angle: int,
        center: tuple[int, int],
        mirror_x: bool = False,
        kcl: KCLayout | None = None,
        info: dict[str, int | float | str] = ...,
    ) -> None: ...

    @overload
    def __init__(
        self,
        name: str | None = None,
        *,
        width: int,
        layer_info: kdb.LayerInfo,
        trans: kdb.Trans | str,
        kcl: KCLayout | None = None,
        port_type: str = "optical",
        info: dict[str, int | float | str] = ...,
    ) -> None: ...

    @overload
    def __init__(
        self,
        name: str | None = None,
        *,
        width: int,
        layer_info: kdb.LayerInfo,
        dcplx_trans: kdb.DCplxTrans | str,
        kcl: KCLayout | None = None,
        port_type: str = "optical",
        info: dict[str, int | float | str] = ...,
    ) -> None: ...

    @overload
    def __init__(
        self,
        name: str | None = None,
        *,
        width: int,
        layer_info: kdb.LayerInfo,
        port_type: str = "optical",
        angle: int,
        center: tuple[int, int],
        mirror_x: bool = False,
        kcl: KCLayout | None = None,
        info: dict[str, int | float | str] = ...,
    ) -> None: ...

    @overload
    def __init__(
        self,
        name: str | None = None,
        *,
        cross_section: CrossSection | SymmetricalCrossSection,
        port_type: str = "optical",
        angle: int,
        center: tuple[int, int],
        mirror_x: bool = False,
        kcl: KCLayout | None = None,
        info: dict[str, int | float | str] = ...,
    ) -> None: ...

    @overload
    def __init__(
        self,
        name: str | None = None,
        *,
        cross_section: CrossSection | SymmetricalCrossSection,
        trans: kdb.Trans | str,
        kcl: KCLayout | None = None,
        info: dict[str, int | float | str] = ...,
        port_type: str = "optical",
    ) -> None: ...

    @overload
    def __init__(
        self,
        name: str | None = None,
        *,
        cross_section: CrossSection | SymmetricalCrossSection,
        dcplx_trans: kdb.DCplxTrans | str,
        kcl: KCLayout | None = None,
        info: dict[str, int | float | str] = ...,
        port_type: str = "optical",
    ) -> None: ...

    @overload
    def __init__(self, *, base: BasePort) -> None: ...

    @overload
    def __init__(self, *, port: ProtoPort[Any]) -> None: ...

    def __init__(
        self,
        name: str | None = None,
        *,
        width: int | None = None,
        layer: int | None = None,
        layer_info: kdb.LayerInfo | None = None,
        port_type: str = "optical",
        trans: kdb.Trans | str | None = None,
        dcplx_trans: kdb.DCplxTrans | str | None = None,
        angle: int | None = None,
        center: tuple[int, int] | None = None,
        mirror_x: bool = False,
        port: ProtoPort[Any] | None = None,
        kcl: KCLayout | None = None,
        info: dict[str, int | float | str] | None = None,
        cross_section: CrossSection | SymmetricalCrossSection | None = None,
        base: BasePort | None = None,
    ) -> None:
        """Create a port from dbu or um based units."""
        if info is None:
            info = {}
        if base is not None:
            self._base = base
            return
        if port is not None:
            self._base = port.base.__copy__()
            return
        info_ = Info(**info)
        from .layout import get_default_kcl

        kcl_ = kcl or get_default_kcl()
        if cross_section is None:
            if layer_info is None:
                if layer is None:
                    raise ValueError("layer or layer_info for a port must be defined")
                layer_info = kcl_.layout.get_info(layer)
            if width is None:
                raise ValueError(
                    "any width and layer, or a cross_section must be given if the"
                    " 'port is None'"
                )
            cross_section_ = kcl_.get_symmetrical_cross_section(
                CrossSectionSpec(layer=layer_info, width=width)
            )
        elif isinstance(cross_section, SymmetricalCrossSection):
            cross_section_ = cross_section
        else:
            cross_section_ = cross_section.base
        if trans is not None:
            trans_ = kdb.Trans.from_s(trans) if isinstance(trans, str) else trans.dup()
            self._base = BasePort(
                name=name,
                kcl=kcl_,
                cross_section=cross_section_,
                trans=trans_,
                info=info_,
                port_type=port_type,
            )
        elif dcplx_trans is not None:
            if isinstance(dcplx_trans, str):
                dcplx_trans_ = kdb.DCplxTrans.from_s(dcplx_trans)
            else:
                dcplx_trans_ = dcplx_trans.dup()
            self._base = BasePort(
                name=name,
                kcl=kcl_,
                cross_section=cross_section_,
                trans=kdb.Trans.R0,
                info=info_,
                port_type=port_type,
            )
            self.dcplx_trans = dcplx_trans_
        elif angle is not None:
            assert center is not None
            trans_ = kdb.Trans(angle, mirror_x, *center)
            self._base = BasePort(
                name=name,
                kcl=kcl_,
                cross_section=cross_section_,
                trans=trans_,
                info=info_,
                port_type=port_type,
            )
        else:
            raise ValueError("Missing port parameters given")

    def copy(
        self,
        trans: kdb.Trans | kdb.DCplxTrans = kdb.Trans.R0,
        post_trans: kdb.Trans | kdb.DCplxTrans = kdb.Trans.R0,
    ) -> Port:
        """Get a copy of a port.

        Transformation order which results in `copy.trans`:
            - Trans: `trans * port.trans * post_trans`
            - DCplxTrans: `trans * port.dcplx_trans * post_trans`

        Args:
            trans: an optional transformation applied to the port to be copied.
            post_trans: transformation to apply to the port after copying.

        Returns:
            port: a copy of the port
        """
        return Port(base=self._base.transformed(trans=trans, post_trans=post_trans))

    def copy_polar(
        self, d: int = 0, d_orth: int = 0, angle: int = 2, mirror: bool = False
    ) -> Port:
        """Get a polar copy of the port.

        This will return a port which is transformed relatively to the original port's
        transformation (orientation, angle and position).

        Args:
            d: The distance to the old port
            d_orth: Orthogonal distance (positive is positive y for a port which is
                facing angle=0°)
            angle: Relative angle to the original port (0=0°,1=90°,2=180°,3=270°).
            mirror: Whether to mirror the port relative to the original port.

        Returns:
            Port copied relative to it's current position and angle/orientation.
        """
        return self.copy(post_trans=kdb.Trans(angle, mirror, d, d_orth))

    @property
    def x(self) -> int:
        """X coordinate of the port in dbu."""
        return self.ix

    @x.setter
    def x(self, value: int) -> None:
        self.ix = value

    @property
    def y(self) -> int:
        """Y coordinate of the port in dbu."""
        return self.iy

    @y.setter
    def y(self, value: int) -> None:
        self.iy = value

    @property
    def width(self) -> int:
        """Width of the port in um."""
        return self.iwidth

    @property
    def cross_section(self) -> CrossSection:
        """Get the cross section of the port."""
        return CrossSection(kcl=self._base.kcl, base=self._base.cross_section)

    @cross_section.setter
    def cross_section(
        self, value: SymmetricalCrossSection | TCrossSection[Any]
    ) -> None:
        if isinstance(value, SymmetricalCrossSection):
            self._base.cross_section = value
            return
        self._base.cross_section = value.base


class DPort(ProtoPort[float]):
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
        d: Access port info in micrometer basis such as width and center / angle.
        kcl: Link to the layout this port resides in.
    """

    @overload
    def __init__(
        self,
        name: str | None = None,
        *,
        width: float,
        layer: LayerEnum | int,
        trans: kdb.Trans | str,
        kcl: KCLayout | None = None,
        port_type: str = "optical",
        info: dict[str, int | float | str] = ...,
    ) -> None: ...

    @overload
    def __init__(
        self,
        name: str | None = None,
        *,
        width: float,
        layer: LayerEnum | int,
        dcplx_trans: kdb.DCplxTrans | str,
        kcl: KCLayout | None = None,
        port_type: str = "optical",
        info: dict[str, int | float | str] = ...,
    ) -> None: ...

    @overload
    def __init__(
        self,
        name: str | None = None,
        *,
        width: float,
        layer: LayerEnum | int,
        port_type: str = "optical",
        orientation: float,
        center: tuple[float, float] = (0, 0),
        mirror_x: bool = False,
        kcl: KCLayout | None = None,
        info: dict[str, int | float | str] = ...,
    ) -> None: ...

    @overload
    def __init__(
        self,
        name: str | None = None,
        *,
        width: float,
        layer_info: kdb.LayerInfo,
        trans: kdb.Trans | str,
        kcl: KCLayout | None = None,
        port_type: str = "optical",
        info: dict[str, int | float | str] = ...,
    ) -> None: ...

    @overload
    def __init__(
        self,
        name: str | None = None,
        *,
        width: float,
        layer_info: kdb.LayerInfo,
        dcplx_trans: kdb.DCplxTrans | str,
        kcl: KCLayout | None = None,
        port_type: str = "optical",
        info: dict[str, int | float | str] = ...,
    ) -> None: ...

    @overload
    def __init__(
        self,
        name: str | None = None,
        *,
        width: float,
        layer_info: kdb.LayerInfo,
        port_type: str = "optical",
        orientation: float,
        center: tuple[float, float] = (0, 0),
        mirror_x: bool = False,
        kcl: KCLayout | None = None,
        info: dict[str, int | float | str] = ...,
    ) -> None: ...

    @overload
    def __init__(
        self,
        name: str | None = None,
        *,
        cross_section: DCrossSection | SymmetricalCrossSection,
        port_type: str = "optical",
        orientation: float,
        center: tuple[float, float],
        mirror_x: bool = False,
        kcl: KCLayout | None = None,
        info: dict[str, int | float | str] = ...,
    ) -> None: ...

    @overload
    def __init__(
        self,
        name: str | None = None,
        *,
        cross_section: DCrossSection | SymmetricalCrossSection,
        trans: kdb.Trans | str,
        kcl: KCLayout | None = None,
        info: dict[str, int | float | str] = ...,
        port_type: str = "optical",
    ) -> None: ...

    @overload
    def __init__(
        self,
        name: str | None = None,
        *,
        cross_section: DCrossSection | SymmetricalCrossSection,
        dcplx_trans: kdb.DCplxTrans | str,
        kcl: KCLayout | None = None,
        info: dict[str, int | float | str] = ...,
        port_type: str = "optical",
    ) -> None: ...

    @overload
    def __init__(self, *, base: BasePort) -> None: ...

    @overload
    def __init__(self, *, port: ProtoPort[Any]) -> None: ...

    def __init__(
        self,
        name: str | None = None,
        *,
        width: float | None = None,
        layer: int | None = None,
        layer_info: kdb.LayerInfo | None = None,
        port_type: str = "optical",
        trans: kdb.Trans | str | None = None,
        dcplx_trans: kdb.DCplxTrans | str | None = None,
        orientation: float = 0,
        center: tuple[float, float] = (0, 0),
        mirror_x: bool = False,
        port: ProtoPort[Any] | None = None,
        kcl: KCLayout | None = None,
        info: dict[str, int | float | str] | None = None,
        cross_section: DCrossSection | SymmetricalCrossSection | None = None,
        base: BasePort | None = None,
    ) -> None:
        """Create a port from dbu or um based units."""
        if info is None:
            info = {}
        if base is not None:
            self._base = base
            return
        if port is not None:
            self._base = port.base.__copy__()
            return
        info_ = Info(**info)

        from .layout import get_default_kcl

        kcl_ = kcl or get_default_kcl()
        if cross_section is None:
            if layer_info is None:
                if layer is None:
                    raise ValueError("layer or layer_info for a port must be defined")
                layer_info = kcl_.layout.get_info(layer)
            if width is None:
                raise ValueError(
                    "If a cross_section is not given a width must be defined."
                )
            width_ = kcl_.to_dbu(width)
            if width_ % 2:
                raise ValueError(
                    f"width needs to be even to snap to grid. Got {width}."
                    "Ports must have a grid width of multiples of 2."
                )
            cross_section_ = kcl_.get_symmetrical_cross_section(
                CrossSectionSpec(layer=layer_info, width=kcl_.to_dbu(width))
            )
        elif isinstance(cross_section, SymmetricalCrossSection):
            cross_section_ = cross_section
        else:
            cross_section_ = cross_section.base
        if trans is not None:
            trans_ = kdb.Trans.from_s(trans) if isinstance(trans, str) else trans.dup()
            self._base = BasePort(
                name=name,
                kcl=kcl_,
                cross_section=cross_section_,
                trans=trans_,
                info=info_,
                port_type=port_type,
            )
        elif dcplx_trans is not None:
            if isinstance(dcplx_trans, str):
                dcplx_trans_ = kdb.DCplxTrans.from_s(dcplx_trans)
            else:
                dcplx_trans_ = dcplx_trans.dup()
            self._base = BasePort(
                name=name,
                kcl=kcl_,
                cross_section=cross_section_,
                dcplx_trans=dcplx_trans_,
                info=info_,
                port_type=port_type,
            )
        else:
            assert center is not None
            dcplx_trans_ = kdb.DCplxTrans.R0
            self._base = BasePort(
                name=name,
                kcl=kcl_,
                cross_section=cross_section_,
                dcplx_trans=dcplx_trans_,
                info=info_,
                port_type=port_type,
            )
            self.center = center
            self.orientation = orientation
            self.mirror_x = mirror_x

    def copy(
        self,
        trans: kdb.Trans | kdb.DCplxTrans = kdb.Trans.R0,
        post_trans: kdb.Trans | kdb.DCplxTrans = kdb.Trans.R0,
    ) -> DPort:
        """Get a copy of a port.

        Transformation order which results in `copy.trans`:
            - Trans: `trans * port.trans * post_trans`
            - DCplxTrans: `trans * port.dcplx_trans * post_trans`

        Args:
            trans: an optional transformation applied to the port to be copied.
            post_trans: transformation to apply to the port after copying.

        Returns:
            port: a copy of the port
        """
        return DPort(base=self._base.transformed(trans=trans, post_trans=post_trans))

    def copy_polar(
        self,
        d: float = 0,
        d_orth: float = 0,
        orientation: float = 180,
        mirror: bool = False,
    ) -> DPort:
        """Get a polar copy of the port.

        This will return a port which is transformed relatively to the original port's
        transformation (orientation, angle and position).

        Args:
            d: The distance to the old port
            d_orth: Orthogonal distance (positive is positive y for a port which is
                facing angle=0°)
            orientation: Relative angle to the original port, in degrees.
            mirror: Whether to mirror the port relative to the original port.
        """
        return self.copy(
            post_trans=kdb.DCplxTrans(rot=orientation, mirrx=mirror, x=d, y=d_orth)
        )

    @property
    def x(self) -> float:
        """X coordinate of the port in um."""
        return self.dx

    @x.setter
    def x(self, value: float) -> None:
        self.dx = value

    @property
    def y(self) -> float:
        """Y coordinate of the port in um."""
        return self.dy

    @y.setter
    def y(self, value: float) -> None:
        self.dy = value

    @property
    def width(self) -> float:
        """Width of the port in um."""
        return self.dwidth

    @property
    def cross_section(self) -> DCrossSection:
        """Get the cross section of the port."""
        return DCrossSection(kcl=self._base.kcl, base=self._base.cross_section)

    @cross_section.setter
    def cross_section(
        self, value: SymmetricalCrossSection | TCrossSection[Any]
    ) -> None:
        if isinstance(value, SymmetricalCrossSection):
            self._base.cross_section = value
            return
        self._base.cross_section = value.base


class DIRECTION(IntEnum):
    """Alias for KLayout direction to compass directions."""

    E = 0
    N = 1
    W = 2
    S = 3


def autorename(
    c: KCell,
    f: Callable[..., None],
    *args: Any,
    **kwargs: Any,
) -> None:
    """Rename a KCell with a renaming function.

    Args:
        c: KCell to be renamed.
        f: Renaming function.
        args: Arguments for the renaming function.
        kwargs: Keyword arguments for the renaming function.
    """
    f(c.ports, *args, **kwargs)


def rename_clockwise(
    ports: Iterable[ProtoPort[Any]],
    layer: LayerEnum | int | None = None,
    port_type: str | None = None,
    regex: str | None = None,
    prefix: str = "o",
    start: int = 1,
) -> None:
    """Sort and return ports in the clockwise direction.

    Args:
        ports: List of ports to rename.
        layer: Layer index / LayerEnum of port layer.
        port_type: Port type to filter the ports by.
        regex: Regex string to filter the port names by.
        prefix: Prefix to add to all ports.
        start: Start index per orientation.

    ```
             o3  o4
             |___|_
        o2 -|      |- o5
            |      |
        o1 -|______|- o6
             |   |
            o8  o7
    ```
    """
    ports_ = filter_layer_pt_reg(ports, layer, port_type, regex)

    def sort_key(port: ProtoPort[Any]) -> tuple[int, int, int]:
        match port.trans.angle:
            case 2:
                angle = 0
            case 1:
                angle = 1
            case 0:
                angle = 2
            case _:
                angle = 3
        dir_1 = 1 if angle < ANGLE_180 else -1
        dir_2 = -1 if port.angle < ANGLE_180 else 1
        key_1 = dir_1 * (
            port.trans.disp.x if angle % 2 else port.trans.disp.y
        )  # order should be y, x, -y, -x
        key_2 = dir_2 * (
            port.trans.disp.y if angle % 2 else port.trans.disp.x
        )  # order should be x, -y, -x, y

        return angle, key_1, key_2

    for i, p in enumerate(sorted(ports_, key=sort_key), start=start):
        p.name = f"{prefix}{i}"


def rename_clockwise_multi(
    ports: Iterable[ProtoPort[Any]],
    layers: Iterable[LayerEnum | int] | None = None,
    regex: str | None = None,
    type_prefix_mapping: dict[str, str] | None = None,
    start: int = 1,
) -> None:
    """Sort and return ports in the clockwise direction.

    Args:
        ports: List of ports to rename.
        layers: Layer indexes / LayerEnums of port layers to rename.
        type_prefix_mapping: Port type to prefix matching in a dictionary.
        regex: Regex string to filter the port names by.
        start: Start index per orientation.

    ```
             o3  o4
             |___|_
        o2 -|      |- o5
            |      |
        o1 -|______|- o6
             |   |
            o8  o7
    ```
    """
    if type_prefix_mapping is None:
        type_prefix_mapping = {"optical": "o", "electrical": "e"}
    if layers:
        for p_type, prefix in type_prefix_mapping.items():
            for layer in layers:
                rename_clockwise(
                    ports=ports,
                    layer=layer,
                    port_type=p_type,
                    regex=regex,
                    prefix=prefix,
                    start=start,
                )
    else:
        for p_type, prefix in type_prefix_mapping.items():
            rename_clockwise(
                ports=ports,
                layer=None,
                port_type=p_type,
                regex=regex,
                prefix=prefix,
                start=start,
            )


def rename_by_direction(
    ports: Iterable[ProtoPort[Any]],
    layer: LayerEnum | int | None = None,
    port_type: str | None = None,
    regex: str | None = None,
    dir_names: tuple[str, str, str, str] = ("E", "N", "W", "S"),
    prefix: str = "",
) -> None:
    """Rename ports by angle of their transformation.

    Args:
        ports: list of ports to be renamed
        layer: A layer index to filter by
        port_type: port_type string to filter by
        regex: Regex string to use to filter the ports to be renamed.
        dir_names: Prefixes for the directions (east, north, west, south).
        prefix: Prefix to add before `dir_names`

    ```
             N0  N1
             |___|_
        W1 -|      |- E1
            |      |
        W0 -|______|- E0
             |   |
            S0   S1
    ```
    """
    for angle in DIRECTION:
        ports_ = filter_layer_pt_reg(ports, layer, port_type, regex)
        dir_2 = -1 if angle < ANGLE_180 else 1
        if angle % 2:

            def key_sort(port: ProtoPort[Any], dir_2: int = dir_2) -> tuple[int, int]:
                return (port.trans.disp.x, dir_2 * port.trans.disp.y)

        else:

            def key_sort(port: ProtoPort[Any], dir_2: int = dir_2) -> tuple[int, int]:
                return (port.trans.disp.y, dir_2 * port.trans.disp.x)

        for i, p in enumerate(sorted(filter_direction(ports_, angle), key=key_sort)):
            p.name = f"{prefix}{dir_names[angle]}{i}"


def filter_layer_pt_reg(
    ports: Iterable[TPort],
    layer: LayerEnum | int | None = None,
    port_type: str | None = None,
    regex: str | None = None,
) -> Iterable[TPort]:
    """Filter ports by layer index, port type and name regex."""
    ports_ = ports
    if layer is not None:
        ports_ = filter_layer(ports_, layer)
    if port_type is not None:
        ports_ = filter_port_type(ports_, port_type)
    if regex is not None:
        ports_ = filter_regex(ports_, regex)

    return ports_


def filter_direction(ports: Iterable[TPort], direction: int) -> filter[TPort]:
    """Filter iterable/sequence of ports by direction :py:class:~`DIRECTION`."""

    def f_func(p: TPort) -> bool:
        return p.trans.angle == direction

    return filter(f_func, ports)


def filter_orientation(ports: Iterable[TPort], orientation: float) -> filter[TPort]:
    """Filter iterable/sequence of ports by direction :py:class:~`DIRECTION`."""

    def f_func(p: TPort) -> bool:
        return p.dcplx_trans.angle == orientation

    return filter(f_func, ports)


def filter_port_type(ports: Iterable[TPort], port_type: str) -> filter[TPort]:
    """Filter iterable/sequence of ports by port_type."""

    def pt_filter(p: TPort) -> bool:
        return p.port_type == port_type

    return filter(pt_filter, ports)


def filter_layer(ports: Iterable[TPort], layer: int | LayerEnum) -> filter[TPort]:
    """Filter iterable/sequence of ports by layer index / LayerEnum."""

    def layer_filter(p: TPort) -> bool:
        return p.layer == layer

    return filter(layer_filter, ports)


def filter_regex(ports: Iterable[TPort], regex: str) -> filter[TPort]:
    """Filter iterable/sequence of ports by port name."""
    pattern = re.compile(regex)

    def regex_filter(p: TPort) -> bool:
        if p.name is not None:
            return bool(pattern.match(p.name))
        return False

    return filter(regex_filter, ports)


polygon_dict: dict[int, kdb.Polygon] = {}


def port_polygon(width: int) -> kdb.Polygon:
    """Gets a polygon representation for a given port width."""
    if width in polygon_dict:
        return polygon_dict[width]
    poly = kdb.Polygon(
        [
            kdb.Point(0, width // 2),
            kdb.Point(0, -width // 2),
            kdb.Point(width // 2, 0),
        ]
    )

    hole = kdb.Region(poly).sized(-int(width * 0.05) or -1)
    hole -= kdb.Region(kdb.Box(0, 0, width // 2, -width // 2))

    poly.insert_hole(list(next(iter(hole.each())).each_point_hull()))
    polygon_dict[width] = poly
    return poly
