from __future__ import annotations

from abc import ABC, abstractmethod
from functools import cached_property
from typing import TYPE_CHECKING, Any, Generic, NoReturn, overload

from . import kdb
from .conf import config
from .exceptions import (
    PortLayerMismatchError,
    PortTypeMismatchError,
    PortWidthMismatchError,
)
from .geometry import DBUGeometricObject, GeometricObject, UMGeometricObject
from .instance import DInstance, Instance, ProtoTInstance, VInstance
from .port import BasePort, DPort, Port, ProtoPort
from .ports import DCreatePort, DPorts, ICreatePort, Ports, ProtoPorts
from .typings import TInstance_co, TTInstance_co, TUnit

if TYPE_CHECKING:
    from collections.abc import Iterator, Sequence

    from .layout import KCLayout

__all__ = [
    "DInstanceGroup",
    "InstanceGroup",
    "ProtoInstanceGroup",
    "ProtoTInstanceGroup",
    "VInstanceGroup",
]


class ProtoInstanceGroup(GeometricObject[TUnit], Generic[TUnit, TInstance_co], ABC):
    insts: list[TInstance_co]
    _base_ports: list[BasePort]

    def __init__(
        self,
        insts: Sequence[TInstance_co] | None = None,
        ports: Sequence[ProtoPort[Any]] | None = None,
    ) -> None:
        """Initialize the InstanceGroup."""
        self.insts = list(insts) if insts is not None else []
        self._base_ports = [p.base for p in ports] if ports is not None else []

    @property
    def name(self) -> str:
        return str(self)

    def __str__(self) -> str:
        return (
            f"InstanceGroup(insts={[inst.name for inst in self.insts]}, "
            f"ports={[p.name for p in self.ports]})"
        )

    @cached_property
    @abstractmethod
    def ports(self) -> ProtoPorts[TUnit]:
        """Ports of the instance."""
        ...

    @property
    def kcl(self) -> KCLayout:
        try:
            return self.insts[0].kcl
        except IndexError as e:
            raise ValueError(
                "Cannot transform or retrieve the KCLayout "
                "of an instance group if it's empty"
            ) from e

    @kcl.setter
    def kcl(self, val: KCLayout) -> NoReturn:
        raise ValueError("KCLayout cannot be set on an instance group.")

    def transform(
        self, trans: kdb.Trans | kdb.DTrans | kdb.ICplxTrans | kdb.DCplxTrans
    ) -> None:
        """Transform the instance group."""
        for inst in self.insts:
            inst.transform(trans)
        if isinstance(trans, kdb.DTrans):
            trans = trans.to_itype(self.kcl.dbu)
        elif isinstance(trans, kdb.ICplxTrans):
            trans = kdb.DCplxTrans(trans=trans, dbu=self.kcl.dbu)
        for p in self.ports:
            p.transform(trans)

    def ibbox(self, layer: int | None = None) -> kdb.Box:
        """Get the total bounding box or the bounding box of a layer in dbu."""
        bb = kdb.Box()
        for _bb in (inst.ibbox(layer) for inst in self.insts):
            bb += _bb
        return bb

    def dbbox(self, layer: int | None = None) -> kdb.DBox:
        """Get the total bounding box or the bounding box of a layer in um."""
        bb = kdb.DBox()
        for _bb in (inst.dbbox(layer) for inst in self.insts):
            bb += _bb
        return bb

    def __iter__(self) -> Iterator[TInstance_co]:
        return iter(self.insts)

    @overload
    def connect(
        self,
        port: str | ProtoPort[Any] | None,
        other: ProtoPort[Any],
        *,
        mirror: bool = False,
        allow_width_mismatch: bool | None = None,
        allow_layer_mismatch: bool | None = None,
        allow_type_mismatch: bool | None = None,
        use_mirror: bool | None = None,
        use_angle: bool | None = None,
    ) -> None: ...

    @overload
    def connect(
        self,
        port: str | ProtoPort[Any] | None,
        other: ProtoTInstance[Any],
        other_port_name: str | int | tuple[int | str, int, int] | None,
        *,
        mirror: bool = False,
        allow_width_mismatch: bool | None = None,
        allow_layer_mismatch: bool | None = None,
        allow_type_mismatch: bool | None = None,
        use_mirror: bool | None = None,
        use_angle: bool | None = None,
    ) -> None: ...

    def connect(
        self,
        port: str | ProtoPort[Any] | None,
        other: ProtoTInstance[Any] | ProtoPort[Any],
        other_port_name: str | int | tuple[int | str, int, int] | None = None,
        *,
        mirror: bool = False,
        allow_width_mismatch: bool | None = None,
        allow_layer_mismatch: bool | None = None,
        allow_type_mismatch: bool | None = None,
        use_mirror: bool | None = None,
        use_angle: bool | None = None,
    ) -> None:
        """Align port with name `portname` to a port.

        Function to allow to transform this instance so that a port of this instance is
        connected (same center with 180° turn) to another instance.

        Args:
            port: The name of the port of this instance to be connected, or directly an
                instance port. Can be `None` because port names can be `None`.
            other: The other instance or a port. Skip `other_port_name` if it's a port.
            other_port_name: The name of the other port. Ignored if
                `other` is a port.
            mirror: Instead of applying klayout.db.Trans.R180 as a connection
                transformation, use klayout.db.Trans.M90, which effectively means this
                instance will be mirrored and connected.
            allow_width_mismatch: Skip width check between the ports if set.
            allow_layer_mismatch: Skip layer check between the ports if set.
            allow_type_mismatch: Skip port_type check between the ports if set.
            use_mirror: If False mirror flag does not get applied from the connection.
            use_angle: If False the angle does not get applied from the connection.
        """
        if allow_width_mismatch is None:
            allow_width_mismatch = config.allow_width_mismatch
        if allow_layer_mismatch is None:
            allow_layer_mismatch = config.allow_layer_mismatch
        if allow_type_mismatch is None:
            allow_type_mismatch = config.allow_type_mismatch
        if use_mirror is None:
            use_mirror = config.connect_use_mirror
        if use_angle is None:
            use_angle = config.connect_use_angle

        if isinstance(other, ProtoPort):
            op = Port(base=other.base)
        else:
            if other_port_name is None:
                raise ValueError(
                    "portname cannot be None if an Instance Object is given. For"
                    "complex connections (non-90 degree and floating point ports) use"
                    "route_cplx instead"
                )
            op = Port(base=other.ports[other_port_name].base)
        if isinstance(port, ProtoPort):
            p = Port(base=port.base)
        else:
            p = Port(base=self.ports[port].base)

        assert isinstance(p, Port)
        assert isinstance(op, Port)

        if p.width != op.width and not allow_width_mismatch:
            raise PortWidthMismatchError(self, other, p, op)
        if p.layer != op.layer and not allow_layer_mismatch:
            raise PortLayerMismatchError(self.kcl, self, other, p, op)
        if p.port_type != op.port_type and not allow_type_mismatch:
            raise PortTypeMismatchError(self, other, p, op)
        if p.base.dcplx_trans or op.base.dcplx_trans:
            dconn_trans = kdb.DCplxTrans.M90 if mirror else kdb.DCplxTrans.R180
            match (use_mirror, use_angle):
                case True, True:
                    dcplx_trans = (
                        op.dcplx_trans * dconn_trans * p.dcplx_trans.inverted()
                    )
                    self.transform(dcplx_trans)
                case False, True:
                    dconn_trans = (
                        kdb.DCplxTrans.M90
                        if mirror ^ p.dcplx_trans.mirror
                        else kdb.DCplxTrans.R180
                    )
                    opt = op.dcplx_trans
                    opt.mirror = False
                    dcplx_trans = opt * dconn_trans * p.dcplx_trans.inverted()
                    self.transform(dcplx_trans)
                case False, False:
                    self.transform(
                        kdb.DCplxTrans(op.dcplx_trans.disp - p.dcplx_trans.disp)
                    )
                case True, False:
                    self.transform(
                        kdb.DCplxTrans(op.dcplx_trans.disp - p.dcplx_trans.disp)
                    )
                    self.dmirror_y(op.dcplx_trans.disp.y)
                case _:
                    raise NotImplementedError("This shouldn't happen")

        else:
            conn_trans = kdb.Trans.M90 if mirror else kdb.Trans.R180
            match (use_mirror, use_angle):
                case True, True:
                    trans = op.trans * conn_trans * p.trans.inverted()
                    self.transform(trans)
                case False, True:
                    conn_trans = (
                        kdb.Trans.M90 if mirror ^ p.trans.mirror else kdb.Trans.R180
                    )
                    op = op.copy()
                    op.trans.mirror = False
                    trans = op.trans * conn_trans * p.trans.inverted()
                    self.transform(trans)
                case False, False:
                    self.transform(kdb.Trans(op.trans.disp - p.trans.disp))
                case True, False:
                    self.transform(kdb.Trans(op.trans.disp - p.trans.disp))
                    self.dmirror_y(op.dcplx_trans.disp.y)
                case _:
                    raise NotImplementedError("This shouldn't happen")


class ProtoTInstanceGroup(
    ProtoInstanceGroup[TUnit, TTInstance_co],
    GeometricObject[TUnit],
    Generic[TUnit, TTInstance_co],
):
    def to_itype(self) -> InstanceGroup:
        return InstanceGroup(insts=[inst.to_itype() for inst in self.insts])

    def to_dtype(self) -> DInstanceGroup:
        return DInstanceGroup(insts=[inst.to_dtype() for inst in self.insts])


class InstanceGroup(
    ProtoTInstanceGroup[int, Instance], DBUGeometricObject, ICreatePort
):
    """Group of Instances.

    The instance group can be treated similar to a single instance
    with regards to transformation functions and bounding boxes.

    Args:
        insts: List of the instances of the group.
    """

    @cached_property
    def ports(self) -> Ports:
        return Ports(kcl=self.kcl, bases=self._base_ports)

    def add_port(
        self,
        *,
        port: ProtoPort[Any],
        name: str | None = None,
        keep_mirror: bool = False,
    ) -> Port:
        return self.ports.add_port(port=port, name=name, keep_mirror=keep_mirror)


class DInstanceGroup(
    ProtoTInstanceGroup[float, DInstance], UMGeometricObject, DCreatePort
):
    """Group of DInstances.

    The instance group can be treated similar to a single instance
    with regards to transformation functions and bounding boxes.

    Args:
        insts: List of the dinstances of the group.
    """

    @cached_property
    def ports(self) -> DPorts:
        return DPorts(kcl=self.kcl, bases=self._base_ports)

    def add_port(
        self,
        *,
        port: ProtoPort[Any],
        name: str | None = None,
        keep_mirror: bool = False,
    ) -> DPort:
        return self.ports.add_port(port=port, name=name, keep_mirror=keep_mirror)


class VInstanceGroup(
    ProtoInstanceGroup[float, VInstance], UMGeometricObject, DCreatePort
):
    """Group of DInstances.

    The instance group can be treated similar to a single instance
    with regards to transformation functions and bounding boxes.

    Args:
        insts: List of the vinstances of the group.
    """

    @cached_property
    def ports(self) -> DPorts:
        return DPorts(kcl=self.kcl, bases=self._base_ports)

    def add_port(
        self,
        *,
        port: ProtoPort[Any],
        name: str | None = None,
        keep_mirror: bool = False,
    ) -> DPort:
        return self.ports.add_port(port=port, name=name, keep_mirror=keep_mirror)
