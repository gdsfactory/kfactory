from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable, Iterable, Iterator, Sequence
from typing import TYPE_CHECKING, Any, Generic, cast

from . import kdb
from .conf import config
from .layer import LayerEnum
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
from .ports import DPorts, Ports, ProtoPorts
from .typings import TUnit
from .utilities import pprint_ports

if TYPE_CHECKING:
    from .instance import DInstance, Instance, ProtoTInstance, VInstance


class HasCellPorts(Generic[TUnit], ABC):
    @property
    @abstractmethod
    def cell_ports(self) -> ProtoPorts[TUnit]: ...


class ProtoInstancePorts(HasCellPorts[TUnit], ABC): ...


class ProtoTInstancePorts(ProtoInstancePorts[TUnit], ABC):
    """Ports of an Instance.

    These act as virtual ports as the centers needs to change if the
    instance changes etc.


    Attributes:
        cell_ports: A pointer to the [`KCell.ports`][kfactory.kcell.KCell.ports]
            of the cell
        instance: A pointer to the Instance related to this.
            This provides a way to dynamically calculate the ports.
    """

    instance: ProtoTInstance[TUnit]

    def __len__(self) -> int:
        """Return Port count."""
        if not self.instance.is_regular_array():
            return len(self.cell_ports)
        else:
            return len(self.cell_ports) * self.instance.na * self.instance.nb

    def __contains__(self, port: str | ProtoPort[Any]) -> bool:
        """Check whether a port is in this port collection."""
        if isinstance(port, ProtoPort):
            return port.base in [p.base for p in self.instance.ports]
        else:
            for _port in self.instance.ports:
                if _port.name == port:
                    return True
            return False

    @property
    def ports(self) -> ProtoTInstancePorts[TUnit]:
        return self.instance.ports

    @property
    def bases(self) -> list[BasePort]:
        return [p.base for p in self.instance.ports]

    def filter(
        self,
        angle: TUnit | None = None,
        orientation: float | None = None,
        layer: LayerEnum | int | None = None,
        port_type: str | None = None,
        regex: str | None = None,
    ) -> Sequence[ProtoPort[TUnit]]:
        """Filter ports by name.

        Args:
            angle: Filter by angle. 0, 1, 2, 3.
            orientation: Filter by orientation in degrees.
            layer: Filter by layer.
            port_type: Filter by port type.
            regex: Filter by regex of the name.
        """

        ports: Iterable[ProtoPort[TUnit]] = list(self.ports)
        if regex:
            ports = filter_regex(ports, regex)
        if layer is not None:
            ports = filter_layer(ports, layer)
        if port_type:
            ports = filter_port_type(ports, port_type)
        if angle is not None:
            ports = filter_direction(ports, round(angle / 90))
        if orientation is not None:
            ports = filter_orientation(ports, orientation)
        return list(ports)

    def __getitem__(
        self, key: int | str | tuple[int | str | None, int, int] | None
    ) -> ProtoPort[TUnit]:
        """Returns port from instance.

        The key can either be an integer, in which case the nth port is
        returned, or a string in which case the first port with a matching
        name is returned.

        If the instance is an array, the key can also be a tuple in the
        form of `c.ports[key_name, i_a, i_b]`, where `i_a` is the index in
        the `instance.a` direction and `i_b` the `instance.b` direction.

        E.g. `c.ports["a", 3, 5]`, accesses the ports of the instance which is
        3 times in `a` direction (4th index in the array), and 5 times in `b` direction
        (5th index in the array).
        """
        if not self.instance.is_regular_array():
            try:
                p = self.cell_ports[cast(int | str | None, key)]
                if not self.instance.is_complex():
                    return p.copy(self.instance.trans)
                else:
                    return p.copy(self.instance.dcplx_trans)
            except KeyError as e:
                raise KeyError(
                    f"{key=} is not a valid port name or index. "
                    "Make sure the instance is an array when giving it a tuple. "
                    f"Available ports: {[v.name for v in self.cell_ports]}"
                ) from e
        else:
            if isinstance(key, tuple):
                key, i_a, i_b = key
                if i_a >= self.instance.na or i_b >= self.instance.nb:
                    raise IndexError(
                        f"The indexes {i_a=} and {i_b=} must be within the array size"
                        f" instance.na={self.instance.na} and"
                        f" instance.nb={self.instance.nb}"
                    )
            else:
                i_a = 0
                i_b = 0
            p = self.cell_ports[key]
            if not self.instance.is_complex():
                return p.copy(
                    kdb.Trans(self.instance.a * i_a + self.instance.b * i_b)
                    * self.instance.trans
                )
            else:
                return p.copy(
                    kdb.DCplxTrans(self.instance.da * i_a + self.instance.db * i_b)
                    * self.instance.dcplx_trans
                )

    @property
    @abstractmethod
    def cell_ports(self) -> ProtoPorts[TUnit]: ...

    def __iter__(self) -> Iterator[ProtoPort[TUnit]]:
        """Create a copy of the ports to iterate through."""
        if not self.instance.is_regular_array():
            if not self.instance.is_complex():
                yield from (p.copy(self.instance.trans) for p in self.cell_ports)
            else:
                yield from (p.copy(self.instance.dcplx_trans) for p in self.cell_ports)
        else:
            if not self.instance.is_complex():
                yield from (
                    p.copy(
                        kdb.Trans(self.instance.a * i_a + self.instance.b * i_b)
                        * self.instance.trans
                    )
                    for i_a in range(self.instance.na)
                    for i_b in range(self.instance.nb)
                    for p in self.cell_ports
                )
            else:
                yield from (
                    p.copy(
                        kdb.DCplxTrans(self.instance.da * i_a + self.instance.db * i_b)
                        * self.instance.dcplx_trans
                    )
                    for i_a in range(self.instance.na)
                    for i_b in range(self.instance.nb)
                    for p in self.cell_ports
                )

    def each_by_array_coord(self) -> Iterator[tuple[int, int, ProtoPort[TUnit]]]:
        if not self.instance.is_regular_array():
            if not self.instance.is_complex():
                yield from (
                    (0, 0, p.copy(self.instance.trans)) for p in self.cell_ports
                )
            else:
                yield from (
                    (0, 0, p.copy(self.instance.dcplx_trans)) for p in self.cell_ports
                )
        else:
            if not self.instance.is_complex():
                yield from (
                    (
                        i_a,
                        i_b,
                        p.copy(
                            kdb.Trans(self.instance.a * i_a + self.instance.b * i_b)
                            * self.instance.trans
                        ),
                    )
                    for i_a in range(self.instance.na)
                    for i_b in range(self.instance.nb)
                    for p in self.cell_ports
                )
            else:
                yield from (
                    (
                        i_a,
                        i_b,
                        p.copy(
                            kdb.DCplxTrans(
                                self.instance.da * i_a + self.instance.db * i_b
                            )
                            * self.instance.dcplx_trans
                        ),
                    )
                    for i_a in range(self.instance.na)
                    for i_b in range(self.instance.nb)
                    for p in self.cell_ports
                )

    def __repr__(self) -> str:
        """String representation.

        Creates a copy and uses the `__repr__` of
        [Ports][kfactory.kcell.Ports.__repr__].
        """
        return repr(self.copy())

    def print(self) -> None:
        config.console.print(pprint_ports(self.copy()))

    def copy(
        self, rename_function: Callable[[list[Port]], None] | None = None
    ) -> Ports:
        """Creates a copy in the form of [Ports][kfactory.kcell.Ports]."""
        if not self.instance.is_regular_array():
            if not self.instance.is_complex():
                return Ports(
                    kcl=self.instance.kcl,
                    bases=[
                        b.transformed(trans=self.instance.trans)
                        for b in self.cell_ports.bases
                    ],
                )
            else:
                return Ports(
                    kcl=self.instance.kcl,
                    bases=[
                        b.transformed(trans=self.instance.dcplx_trans)
                        for b in self.cell_ports.bases
                    ],
                )
        else:
            if not self.instance.is_complex():
                return Ports(
                    kcl=self.instance.kcl,
                    bases=[
                        b.transformed(
                            self.instance.trans
                            * kdb.Trans(self.instance.a * i_a + self.instance.b * i_b)
                        )
                        for i_a in range(self.instance.na)
                        for i_b in range(self.instance.nb)
                        for b in self.cell_ports.bases
                    ],
                )
            else:
                return Ports(
                    kcl=self.instance.kcl,
                    bases=[
                        b.transformed(
                            self.instance.dcplx_trans
                            * kdb.DCplxTrans(
                                self.instance.db * i_a + self.instance.db * i_b
                            )
                        )
                        for i_a in range(self.instance.na)
                        for i_b in range(self.instance.nb)
                        for b in self.cell_ports.bases
                    ],
                )


class InstancePorts(ProtoTInstancePorts[int]):
    instance: Instance

    def __init__(self, instance: Instance) -> None:
        """Creates the virtual ports object.

        Args:
            instance: The related instance
        """
        self.instance = instance

    @property
    def cell_ports(self) -> Ports:
        return self.instance.cell.ports

    def filter(
        self,
        angle: int | None = None,
        orientation: float | None = None,
        layer: LayerEnum | int | None = None,
        port_type: str | None = None,
        regex: str | None = None,
    ) -> Sequence[Port]:
        return [
            Port(base=p.base)
            for p in super().filter(angle, orientation, layer, port_type, regex)
        ]

    def __getitem__(
        self, key: int | str | tuple[int | str | None, int, int] | None
    ) -> Port:
        return Port(base=super().__getitem__(key).base)


class DInstancePorts(ProtoTInstancePorts[float]):
    instance: DInstance

    def __init__(self, instance: DInstance) -> None:
        """Creates the virtual ports object.

        Args:
            instance: The related instance
        """
        self.instance = instance

    @property
    def cell_ports(self) -> DPorts:
        return self.instance.cell.ports

    def filter(
        self,
        angle: float | None = None,
        orientation: float | None = None,
        layer: LayerEnum | int | None = None,
        port_type: str | None = None,
        regex: str | None = None,
    ) -> Sequence[DPort]:
        return [
            DPort(base=p.base)
            for p in super().filter(angle, orientation, layer, port_type, regex)
        ]

    def __getitem__(
        self, key: int | str | tuple[int | str | None, int, int] | None
    ) -> DPort:
        return DPort(base=super().__getitem__(key).base)


class VInstancePorts(ProtoInstancePorts[float]):
    """Ports of an instance.

    These act as virtual ports as the centers needs to change if the
    instance changes etc.


    Attributes:
        cell_ports: A pointer to the [`KCell.ports`][kfactory.kcell.KCell.ports]
            of the cell
        instance: A pointer to the Instance related to this.
            This provides a way to dynamically calculate the ports.
    """

    instance: VInstance

    def __init__(self, instance: VInstance) -> None:
        """Creates the virtual ports object.

        Args:
            instance: The related instance
        """
        self.instance = instance

    @property
    def cell_ports(self) -> DPorts:
        return DPorts(
            kcl=self.instance.cell.ports.kcl, bases=self.instance.cell.ports.bases
        )

    def __len__(self) -> int:
        """Return Port count."""
        return len(self.cell_ports)

    def __getitem__(self, key: int | str | None) -> DPort:
        """Get a port by name."""
        p = self.cell_ports[key]
        return p.copy(self.instance.trans)

    def __iter__(self) -> Iterator[DPort]:
        """Create a copy of the ports to iterate through."""
        yield from (p.copy(self.instance.trans) for p in self.cell_ports)

    def __repr__(self) -> str:
        """String representation.

        Creates a copy and uses the `__repr__` of
        [Ports][kfactory.kcell.Ports.__repr__].
        """
        return repr(self.copy())

    def filter(
        self,
        angle: int | None = None,
        orientation: float | None = None,
        layer: LayerEnum | int | None = None,
        port_type: str | None = None,
        regex: str | None = None,
    ) -> list[DPort]:
        """Filter ports by name.

        Args:
            angle: Filter by angle. 0, 1, 2, 3.
            orientation: Filter by orientation in degrees.
            layer: Filter by layer.
            port_type: Filter by port type.
            regex: Filter by regex of the name.
        """
        ports = list(self.instance.ports)
        if regex:
            ports = list(filter_regex(ports, regex))
        if layer is not None:
            ports = list(filter_layer(ports, layer))
        if port_type:
            ports = list(filter_port_type(ports, port_type))
        if angle is not None:
            ports = list(filter_direction(ports, angle))
        if orientation is not None:
            ports = list(filter_orientation(ports, orientation))
        return list(ports)

    def copy(self) -> DPorts:
        """Creates a copy in the form of [Ports][kfactory.kcell.Ports]."""
        return DPorts(
            kcl=self.instance.cell.kcl,
            bases=[b.transformed(self.instance.trans) for b in self.cell_ports.bases],
        )