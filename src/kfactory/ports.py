from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import (
    Callable,
    Iterable,
    Iterator,
    Mapping,
    Sequence,
)
from typing import (
    TYPE_CHECKING,
    Any,
    ClassVar,
    Generic,
    Literal,
    Self,
    cast,
    overload,
)

from . import kdb
from .conf import config
from .cross_section import CrossSectionSpec, SymmetricalCrossSection
from .port import (
    BasePort,
    DPort,
    Port,
    ProtoPort,
    filter_direction,
    filter_layer,
    filter_orientation,
    filter_port_type,
    filter_regex,
)
from .typings import TUnit
from .utilities import pprint_ports

if TYPE_CHECKING:
    from ruamel.yaml.constructor import BaseConstructor
    from ruamel.yaml.representer import BaseRepresenter, SequenceNode

    from .layer import LayerEnum
    from .layout import KCLayout


def _filter_ports(
    ports: Iterable[Port],
    angle: int | None = None,
    orientation: float | None = None,
    layer: LayerEnum | int | None = None,
    port_type: str | None = None,
    regex: str | None = None,
) -> list[Port]:
    if regex:
        ports = filter_regex(ports, regex)
    if layer is not None:
        ports = filter_layer(ports, layer)
    if port_type:
        ports = filter_port_type(ports, port_type)
    if angle is not None:
        ports = filter_direction(ports, angle)
    if orientation is not None:
        ports = filter_orientation(ports, orientation)
    return list(ports)


class ProtoPorts(ABC, Generic[TUnit]):
    kcl: KCLayout
    _locked: bool
    _bases: list[BasePort]

    def __init__(
        self,
        *,
        kcl: KCLayout,
        ports: Iterable[ProtoPort[Any]] | None = None,
        bases: list[BasePort] | None = None,
    ) -> None:
        self.kcl = kcl
        if bases is not None:
            self._bases = bases
        elif ports is not None:
            self._bases = [p.base for p in ports]
        else:
            self._bases = []
        self._locked = False

    def __len__(self) -> int:
        """Return Port count."""
        return len(self._bases)

    @property
    def bases(self) -> list[BasePort]:
        return self._bases

    def copy(self, rename_funciton: Callable[[list[Port]], None] | None = None) -> Self:
        """Get a copy of each port."""
        bases = [b.__copy__() for b in self._bases]
        if rename_funciton is not None:
            rename_funciton([Port(base=b) for b in bases])
        return self.__class__(bases=bases, kcl=self.kcl)

    def to_itype(self) -> Ports:
        return Ports(kcl=self.kcl, bases=self._bases)

    def to_dtype(self) -> DPorts:
        return DPorts(kcl=self.kcl, bases=self._bases)

    @abstractmethod
    def __iter__(self) -> Iterator[ProtoPort[TUnit]]: ...

    @abstractmethod
    def add_port(
        self,
        *,
        port: ProtoPort[Any],
        name: str | None = None,
        keep_mirror: bool = False,
    ) -> ProtoPort[TUnit]: ...

    @abstractmethod
    def create_port(self, *args: Any, **kwargs: Any) -> ProtoPort[TUnit]: ...

    @abstractmethod
    def get_all_named(self) -> Mapping[str, ProtoPort[TUnit]]: ...

    @abstractmethod
    def add_ports(
        self,
        ports: Iterable[ProtoPort[Any]],
        prefix: str = "",
        keep_mirror: bool = False,
        suffix: str = "",
    ) -> None: ...

    @abstractmethod
    def __getitem__(self, key: int | str | None) -> ProtoPort[TUnit]: ...

    @abstractmethod
    def filter(
        self,
        angle: int | None = None,
        orientation: float | None = None,
        layer: LayerEnum | int | None = None,
        port_type: str | None = None,
        regex: str | None = None,
    ) -> Sequence[ProtoPort[TUnit]]: ...

    def __contains__(self, port: str | ProtoPort[Any] | BasePort) -> bool:
        """Check whether a port is in this port collection."""
        if isinstance(port, ProtoPort):
            return port.base in self._bases
        if isinstance(port, BasePort):
            return port in self._bases
        return any(_port.name == port for _port in self._bases)

    def clear(self) -> None:
        """Deletes all ports."""
        self._bases.clear()

    def __eq__(self, other: object) -> bool:
        """Support for `ports1 == ports2` comparisons."""
        if isinstance(other, Iterable) and all(
            isinstance(item, ProtoPort) for item in other
        ):
            other_list = cast(list[ProtoPort[Any]], list(other))
            if len(self._bases) != len(other_list):
                return False
            for b1, b2 in zip(self._bases, other_list, strict=False):
                if b1 != b2.base:
                    return False
            return True
        return False


class Ports(ProtoPorts[int]):
    """A collection of ports.

    It is not a traditional dictionary. Elements can be retrieved as in a traditional
    dictionary. But to keep tabs on names etc, the ports are stored as a list

    Attributes:
        _ports: Internal storage of the ports. Normally ports should be retrieved with
            [__getitem__][kfactory.kcell.Ports.__getitem__] or with
            [get_all_named][kfactory.kcell.Ports.get_all_named]
    """

    yaml_tag: ClassVar[str] = "!Ports"

    @overload
    def __init__(self, *, kcl: KCLayout) -> None: ...

    @overload
    def __init__(
        self,
        *,
        kcl: KCLayout,
        ports: Iterable[ProtoPort[Any]] | None = None,
    ) -> None: ...

    @overload
    def __init__(
        self,
        *,
        kcl: KCLayout,
        bases: list[BasePort] | None = None,
    ) -> None: ...

    def __init__(
        self,
        *,
        kcl: KCLayout,
        ports: Iterable[ProtoPort[Any]] | None = None,
        bases: list[BasePort] | None = None,
    ) -> None:
        """Initialize the Ports object."""
        return super().__init__(kcl=kcl, ports=ports, bases=bases)

    def __iter__(self) -> Iterator[Port]:
        """Iterator, that allows for loops etc to directly access the object."""
        yield from (Port(base=b) for b in self._bases)

    def add_port(
        self,
        *,
        port: ProtoPort[Any],
        name: str | None = None,
        keep_mirror: bool = False,
    ) -> Port:
        """Add a port object.

        Args:
            port: The port to add
            name: Overwrite the name of the port
            keep_mirror: Keep the mirror flag from the original port if `True`,
                else set [Port.trans.mirror][kfactory.kcell.Port.trans] (or the complex
                equivalent) to `False`.
        """
        if port.kcl == self.kcl:
            base = port.base.__copy__()
            if not keep_mirror:
                if base.trans is not None:
                    base.trans.mirror = False
                elif base.dcplx_trans is not None:
                    base.dcplx_trans.mirror = False
            if name is not None:
                base.name = name
            self._bases.append(base)
            port_ = Port(base=base)
        else:
            dcplx_trans = port.dcplx_trans.dup()
            if not keep_mirror:
                dcplx_trans.mirror = False
            base = port.base.__copy__()
            base.trans = kdb.Trans.R0
            base.dcplx_trans = None
            base.kcl = self.kcl
            base.cross_section = self.kcl.get_cross_section(
                port.cross_section.to_dtype(port.kcl),
            )
            port_ = Port(base=base)
            port_.dcplx_trans = dcplx_trans
            self._bases.append(port_.base)
        return port_

    def add_ports(
        self,
        ports: Iterable[ProtoPort[Any]],
        prefix: str = "",
        keep_mirror: bool = False,
        suffix: str = "",
    ) -> None:
        """Append a list of ports."""
        for p in ports:
            name = p.name or ""
            self.add_port(port=p, name=prefix + name + suffix, keep_mirror=keep_mirror)

    @overload
    def create_port(
        self,
        *,
        trans: kdb.Trans,
        width: int,
        layer: int,
        name: str | None = None,
        port_type: str = "optical",
    ) -> Port: ...

    @overload
    def create_port(
        self,
        *,
        dcplx_trans: kdb.DCplxTrans,
        width: int,
        layer: LayerEnum | int,
        name: str | None = None,
        port_type: str = "optical",
    ) -> Port: ...

    @overload
    def create_port(
        self,
        *,
        width: int,
        layer: LayerEnum | int,
        center: tuple[int, int],
        angle: Literal[0, 1, 2, 3],
        name: str | None = None,
        port_type: str = "optical",
    ) -> Port: ...

    @overload
    def create_port(
        self,
        *,
        trans: kdb.Trans,
        width: int,
        layer_info: kdb.LayerInfo,
        name: str | None = None,
        port_type: str = "optical",
    ) -> Port: ...

    @overload
    def create_port(
        self,
        *,
        width: int,
        layer_info: kdb.LayerInfo,
        center: tuple[int, int],
        angle: Literal[0, 1, 2, 3],
        name: str | None = None,
        port_type: str = "optical",
    ) -> Port: ...

    def create_port(
        self,
        *,
        name: str | None = None,
        width: int | None = None,
        layer: LayerEnum | int | None = None,
        layer_info: kdb.LayerInfo | None = None,
        port_type: str = "optical",
        trans: kdb.Trans | None = None,
        dcplx_trans: kdb.DCplxTrans | None = None,
        center: tuple[int, int] | None = None,
        angle: Literal[0, 1, 2, 3] | None = None,
        mirror_x: bool = False,
        cross_section: SymmetricalCrossSection | None = None,
    ) -> Port:
        """Create a new port in the list.

        Args:
            name: Optional name of port.
            width: Width of the port in dbu. If `trans` is set (or the manual creation
                with `center` and `angle`), this needs to be as well.
            layer: Layer index of the port.
            layer_info: Layer definition of the port.
            port_type: Type of the port (electrical, optical, etc.)
            trans: Transformation object of the port. [dbu]
            dcplx_trans: Complex transformation for the port.
                Use if a non-90° port is necessary.
            center: Tuple of the center. [dbu]
            angle: Angle in 90° increments. Used for simple/dbu transformations.
            mirror_x: Mirror the transformation of the port.
            cross_section: Cross section of the port. If set, overwrites width and layer
                (info).
        """
        if cross_section is None:
            if width is None:
                msg = (
                    "Either width or dwidth must be set. It can be set through"
                    " a cross section as well."
                )
                raise ValueError(
                    msg,
                )
            if layer_info is None:
                if layer is None:
                    msg = "layer or layer_info must be defined to create a port."
                    raise ValueError(
                        msg,
                    )
                layer_info = self.kcl.get_info(layer)
            assert layer_info is not None
            cross_section = self.kcl.get_cross_section(
                CrossSectionSpec(main_layer=layer_info, width=width),
            )
        if trans is not None:
            port = Port(
                name=name,
                trans=trans,
                cross_section=cross_section,
                port_type=port_type,
                kcl=self.kcl,
            )
        elif dcplx_trans is not None:
            port = Port(
                name=name,
                dcplx_trans=dcplx_trans,
                port_type=port_type,
                cross_section=cross_section,
                kcl=self.kcl,
            )
        elif angle is not None and center is not None:
            port = Port(
                name=name,
                port_type=port_type,
                cross_section=cross_section,
                angle=angle,
                center=center,
                mirror_x=mirror_x,
                kcl=self.kcl,
            )
        else:
            raise ValueError(
                f"You need to define width {width} and trans {trans} or angle {angle}"
                f" and center {center} or dcplx_trans {dcplx_trans}",
            )

        self._bases.append(port.base)
        return port

    def get_all_named(self) -> Mapping[str, Port]:
        """Get all ports in a dictionary with names as keys."""
        return {v.name: Port(base=v) for v in self._bases if v.name is not None}

    def __getitem__(self, key: int | str | None) -> Port:
        """Get a specific port by name."""
        if isinstance(key, int):
            return Port(base=self._bases[key])
        try:
            return Port(base=next(filter(lambda base: base.name == key, self._bases)))
        except StopIteration:
            raise KeyError(
                f"{key=} is not a valid port name or index. "
                f"Available ports: {[v.name for v in self._bases]}",
            )

    def filter(
        self,
        angle: int | None = None,
        orientation: float | None = None,
        layer: LayerEnum | int | None = None,
        port_type: str | None = None,
        regex: str | None = None,
    ) -> Sequence[Port]:
        """Filter ports by name.

        Args:
            angle: Filter by angle. 0, 1, 2, 3.
            orientation: Filter by orientation in degrees.
            layer: Filter by layer.
            port_type: Filter by port type.
            regex: Filter by regex of the name.
        """
        ports: Iterable[Port] = (Port(base=b) for b in self._bases)
        if regex:
            ports = filter_regex(ports, regex)
        if layer is not None:
            ports = filter_layer(ports, layer)
        if port_type:
            ports = filter_port_type(ports, port_type)
        if angle is not None:
            ports = filter_direction(ports, angle)
        if orientation is not None:
            ports = filter_orientation(ports, orientation)
        return list(ports)

    def __repr__(self) -> str:
        """Representation of the Ports as strings."""
        return repr([repr(DPort(base=b)) for b in self._bases])

    def print(self, unit: Literal["dbu", "um", None] = None) -> None:
        """Pretty print ports."""
        config.console.print(pprint_ports(self, unit=unit))

    def pformat(self, unit: Literal["dbu", "um", None] = None) -> str:
        """Pretty print ports."""
        with config.console.capture() as capture:
            config.console.print(pprint_ports(self, unit=unit))
        return capture.get()

    @classmethod
    def to_yaml(cls, representer: BaseRepresenter, node: Self) -> SequenceNode:
        """Convert the ports to a yaml representations."""
        return representer.represent_sequence(cls.yaml_tag, node._bases)

    @classmethod
    def from_yaml(cls, constructor: BaseConstructor, node: Any) -> Self:
        """Load Ports from a yaml representation."""
        return cls(**constructor.construct_sequence(node))


class DPorts(ProtoPorts[float]):
    """DPorts of an DInstance.

    These act as virtual ports as the centers needs to change if the
    instance changes etc.


    Attributes:
        cell_ports: A pointer to the [`KCell.ports`][kfactory.kcell.KCell.ports]
            of the cell
        instance: A pointer to the Instance related to this.
            This provides a way to dynamically calculate the ports.
    """

    @overload
    def __init__(self, *, kcl: KCLayout) -> None: ...

    @overload
    def __init__(
        self,
        *,
        kcl: KCLayout,
        ports: Iterable[ProtoPort[Any]] | None = None,
    ) -> None: ...

    @overload
    def __init__(
        self,
        *,
        kcl: KCLayout,
        bases: list[BasePort] | None = None,
    ) -> None: ...

    def __init__(
        self,
        *,
        kcl: KCLayout,
        ports: Iterable[ProtoPort[Any]] | None = None,
        bases: list[BasePort] | None = None,
    ) -> None:
        return super().__init__(kcl=kcl, ports=ports, bases=bases)

    def __iter__(self) -> Iterator[DPort]:
        """Iterator, that allows for loops etc to directly access the object."""
        yield from (DPort(base=b) for b in self._bases)

    def add_port(
        self,
        *,
        port: ProtoPort[Any],
        name: str | None = None,
        keep_mirror: bool = False,
    ) -> DPort:
        """Add a port object.

        Args:
            port: The port to add
            name: Overwrite the name of the port
            keep_mirror: Keep the mirror flag from the original port if `True`,
                else set [Port.trans.mirror][kfactory.kcell.Port.trans] (or the complex
                equivalent) to `False`.
        """
        if port.kcl == self.kcl:
            base = port.base.__copy__()
            if not keep_mirror:
                if base.trans is not None:
                    base.trans.mirror = False
                elif base.dcplx_trans is not None:
                    base.dcplx_trans.mirror = False
            if name is not None:
                base.name = name
            self._bases.append(base)
            port_ = DPort(base=base)
        else:
            dcplx_trans = port.dcplx_trans.dup()
            if not keep_mirror:
                dcplx_trans.mirror = False
            base = port.base.__copy__()
            base.trans = kdb.Trans.R0
            base.dcplx_trans = None
            base.kcl = self.kcl
            base.cross_section = self.kcl.get_cross_section(
                port.cross_section.to_dtype(port.kcl),
            )
            port_ = DPort(base=base)
            port_.dcplx_trans = dcplx_trans
            self._bases.append(port_.base)
        return port_

    def add_ports(
        self,
        ports: Iterable[ProtoPort[Any]],
        prefix: str = "",
        keep_mirror: bool = False,
        suffix: str = "",
    ) -> None:
        """Append a list of ports."""
        for p in ports:
            name = p.name or ""
            self.add_port(port=p, name=prefix + name + suffix, keep_mirror=keep_mirror)

    @overload
    def create_port(
        self,
        *,
        trans: kdb.Trans,
        width: float,
        layer: int,
        name: str | None = None,
        port_type: str = "optical",
    ) -> DPort: ...

    @overload
    def create_port(
        self,
        *,
        dcplx_trans: kdb.DCplxTrans,
        width: float,
        layer: LayerEnum | int,
        name: str | None = None,
        port_type: str = "optical",
    ) -> DPort: ...

    @overload
    def create_port(
        self,
        *,
        width: int,
        layer: LayerEnum | int,
        center: tuple[float, float],
        angle: float,
        name: str | None = None,
        port_type: str = "optical",
    ) -> DPort: ...

    @overload
    def create_port(
        self,
        *,
        trans: kdb.Trans,
        width: float,
        layer_info: kdb.LayerInfo,
        name: str | None = None,
        port_type: str = "optical",
    ) -> DPort: ...

    @overload
    def create_port(
        self,
        *,
        dcplx_trans: kdb.DCplxTrans,
        width: float,
        layer_info: kdb.LayerInfo,
        name: str | None = None,
        port_type: str = "optical",
    ) -> DPort: ...

    @overload
    def create_port(
        self,
        *,
        width: int,
        layer_info: kdb.LayerInfo,
        center: tuple[float, float],
        angle: float,
        name: str | None = None,
        port_type: str = "optical",
    ) -> DPort: ...

    def create_port(
        self,
        *,
        name: str | None = None,
        width: float | None = None,
        layer: LayerEnum | int | None = None,
        layer_info: kdb.LayerInfo | None = None,
        port_type: str = "optical",
        trans: kdb.Trans | None = None,
        dcplx_trans: kdb.DCplxTrans | None = None,
        center: tuple[float, float] | None = None,
        angle: float | None = None,
        mirror_x: bool = False,
        cross_section: SymmetricalCrossSection | None = None,
    ) -> DPort:
        """Create a new port in the list.

        Args:
            name: Optional name of port.
            width: Width of the port in dbu. If `trans` is set (or the manual creation
                with `center` and `angle`), this needs to be as well.
            layer: Layer index of the port.
            layer_info: Layer definition of the port.
            port_type: Type of the port (electrical, optical, etc.)
            trans: Transformation object of the port. [dbu]
            dcplx_trans: Complex transformation for the port.
                Use if a non-90° port is necessary.
            center: Tuple of the center. [dbu]
            angle: Angle in 90° increments. Used for simple/dbu transformations.
            mirror_x: Mirror the transformation of the port.
            cross_section: Cross section of the port. If set, overwrites width and layer
                (info).
        """
        if cross_section is None:
            if width is None:
                msg = (
                    "Either width must be set. It can be set through"
                    " a cross section as well."
                )
                raise ValueError(
                    msg,
                )
            if layer_info is None:
                if layer is None:
                    msg = "layer or layer_info must be defined to create a port."
                    raise ValueError(
                        msg,
                    )
                layer_info = self.kcl.get_info(layer)
            assert layer_info is not None
            dwidth = width
            if dwidth <= 0:
                msg = "dwidth needs to be set and be >0"
                raise ValueError(msg)
            width_ = self.kcl.to_dbu(dwidth)
            if width_ % 2:
                raise ValueError(
                    f"dwidth needs to be even to snap to grid. Got {dwidth}."
                    "Ports must have a grid width of multiples of 2.",
                )
            cross_section = self.kcl.get_cross_section(
                CrossSectionSpec(
                    main_layer=layer_info,
                    width=width_,
                ),
            )
        if trans is not None:
            port = DPort(
                name=name,
                trans=trans,
                cross_section=cross_section,
                port_type=port_type,
                kcl=self.kcl,
            )
        elif dcplx_trans is not None:
            port = DPort(
                name=name,
                dcplx_trans=dcplx_trans,
                port_type=port_type,
                cross_section=cross_section,
                kcl=self.kcl,
            )
        elif angle is not None and center is not None:
            port = DPort(
                name=name,
                port_type=port_type,
                cross_section=cross_section,
                angle=angle,
                center=center,
                mirror_x=mirror_x,
                kcl=self.kcl,
            )
        else:
            raise ValueError(
                f"You need to define width {width} and trans {trans} or angle {angle}"
                f" and center {center} or dcplx_trans {dcplx_trans}",
            )

        self._bases.append(port.base)
        return port

    def get_all_named(self) -> Mapping[str, DPort]:
        """Get all ports in a dictionary with names as keys."""
        return {v.name: DPort(base=v) for v in self._bases if v.name is not None}

    def __getitem__(self, key: int | str | None) -> DPort:
        """Get a specific port by name."""
        if isinstance(key, int):
            return DPort(base=self._bases[key])
        try:
            return DPort(base=next(filter(lambda base: base.name == key, self._bases)))
        except StopIteration:
            raise KeyError(
                f"{key=} is not a valid port name or index. "
                f"Available ports: {[v.name for v in self._bases]}",
            )

    def filter(
        self,
        angle: float | None = None,
        orientation: float | None = None,
        layer: LayerEnum | int | None = None,
        port_type: str | None = None,
        regex: str | None = None,
    ) -> Sequence[DPort]:
        """Filter ports by name.

        Args:
            angle: Filter by angle.
            orientation: Alias for angle.
            layer: Filter by layer.
            port_type: Filter by port type.
            regex: Filter by regex of the name.
        """
        ports: Iterable[DPort] = (DPort(base=b) for b in self._bases)
        if regex:
            ports = filter_regex(ports, regex)
        if layer is not None:
            ports = filter_layer(ports, layer)
        if port_type:
            ports = filter_port_type(ports, port_type)
        orientation = orientation or angle
        if orientation is not None:
            ports = filter_orientation(ports, orientation)
        return list(ports)

    def __repr__(self) -> str:
        """Representation of the Ports as strings."""
        return repr([repr(Port(base=b)) for b in self._bases])

    def print(self, unit: Literal["dbu", "um", None] = None) -> None:
        """Pretty print ports."""
        config.console.print(pprint_ports(self, unit=unit))

    def pformat(self, unit: Literal["dbu", "um", None] = None) -> str:
        """Pretty print ports."""
        with config.console.capture() as capture:
            config.console.print(pprint_ports(self, unit=unit))
        return capture.get()
