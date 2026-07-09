from __future__ import annotations

from typing import TYPE_CHECKING

from ..port import BasePort, Port

if TYPE_CHECKING:
    from .. import kdb
    from ..instance import Instance


class RoutePort:
    __slots__ = ("_dbu", "_materialized_base", "base", "trans")

    def __init__(
        self,
        *,
        base: BasePort,
        trans: kdb.Trans,
        dbu: bool,
        materialized_base: BasePort | None = None,
    ) -> None:
        self.base = base
        self.trans = trans
        self._dbu = dbu
        self._materialized_base = materialized_base

    @classmethod
    def from_port(cls, port: Port) -> RoutePort:
        base = port.base
        if base.trans is not None:
            return cls(base=base, trans=base.trans, dbu=True)
        return cls(
            base=base,
            trans=base.get_trans(),
            dbu=False,
            materialized_base=base,
        )

    @classmethod
    def from_instance_port(cls, inst: Instance, base: BasePort) -> RoutePort:
        if base.trans is not None:
            return cls(base=base, trans=inst.trans * base.trans, dbu=True)
        materialized_base = base.transformed(inst.trans, copy_info=False)
        return cls(
            base=materialized_base,
            trans=materialized_base.get_trans(),
            dbu=False,
            materialized_base=materialized_base,
        )

    @property
    def is_dbu(self) -> bool:
        return self._dbu

    @property
    def name(self) -> str | None:
        return self.base.name

    @property
    def port_type(self) -> str:
        return self.base.port_type

    @property
    def width(self) -> int:
        return self.base.any_cross_section.width

    @property
    def angle(self) -> int:
        return self.trans.angle

    def to_port(self, *, name: str | None = None, copy_info: bool = False) -> Port:
        if self._materialized_base is not None:
            base = self._materialized_base._copy(copy_info=copy_info)
            if name is not None:
                base.name = name
            return Port(base=base)
        return Port(
            base=BasePort._construct(
                name=self.base.name if name is None else name,
                kcl=self.base.kcl,
                cross_section=self.base.cross_section,
                asymmetric_cross_section=self.base.asymmetric_cross_section,
                trans=self.trans.dup(),
                info=self.base.info.model_copy() if copy_info else self.base.info,
                port_type=self.base.port_type,
            )
        )


def route_port(port: Port | RoutePort) -> RoutePort:
    if isinstance(port, RoutePort):
        return port
    return RoutePort.from_port(port)


def port_for_connect(port: Port | RoutePort) -> Port:
    if isinstance(port, RoutePort):
        return port.to_port()
    return port


def instance_route_port(inst: Instance, port_index: int) -> RoutePort:
    return RoutePort.from_instance_port(inst, inst.cell._base.ports[port_index])


def instance_route_port_by_name(inst: Instance, name: str | None) -> RoutePort:
    return RoutePort.from_instance_port(inst, inst.cell.ports._get_base_by_name(name))
