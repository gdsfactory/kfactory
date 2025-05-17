from __future__ import annotations

import re
from typing import Any, Self

from pydantic import BaseModel, Field, RootModel, model_validator

from .typings import JSONSerializable  # noqa: TC001

__all__ = ["Netlist", "NetlistInstance", "NetlistPort", "PortArrayRef", "PortRef"]


class PortRef(BaseModel, extra="forbid"):
    instance: str
    port: str

    @property
    def name(self) -> str:
        return self.port

    @model_validator(mode="before")
    @classmethod
    def _validate_portref(cls, data: dict[str, Any]) -> dict[str, Any]:
        if isinstance(data, str):
            data = tuple(data.rsplit(",", 1))
        if isinstance(data, tuple):
            return {"instance": data[0], "port": data[1]}
        return data

    def __lt__(self, other: PortRef | PortArrayRef | NetlistPort) -> bool:
        if isinstance(other, NetlistPort):
            return False
        if isinstance(other, PortArrayRef):
            return True
        return (self.instance, self.port) < (other.instance, other.port)


class PortArrayRef(PortRef, extra="forbid"):
    ia: int
    ib: int

    @model_validator(mode="before")
    @classmethod
    def _validate_array_portref(cls, data: dict[str, Any]) -> dict[str, Any]:
        if isinstance(data, str):
            data = tuple(data.rsplit(",", 1))
        if isinstance(data, tuple):
            match = re.match(r"(.*?)<(\d+)\.(\d+)>$", data[0])
            if match:
                return {
                    "instance": match.group(1),
                    "ia": int(match.group(2)),
                    "ib": int(match.group(3)),
                    "port": data[1],
                }
        return data

    def __lt__(self, other: PortRef | NetlistPort | PortArrayRef) -> bool:
        if isinstance(other, NetlistPort | PortRef):
            return False
        return (self.instance, self.port, self.ia, self.ib) < (
            other.instance,
            other.port,
            other.ia,
            other.ib,
        )


class NetlistPort(BaseModel):
    name: str

    def __lt__(self, other: NetlistPort | PortRef) -> bool:
        if isinstance(other, NetlistPort):
            return self.name < other.name
        return True


class Net(RootModel[list[PortArrayRef | PortRef | NetlistPort]]):
    root: list[PortArrayRef | PortRef | NetlistPort]

    def sort(self) -> Self:
        def _port_sort(port: PortRef | NetlistPort) -> tuple[Any, ...]:
            if isinstance(port, PortRef):
                return (port.instance, port.port)
            return (port.name,)

        self.root.sort(key=_port_sort)
        return self

    def __lt__(self, other: Net) -> bool:
        if len(self.root) == 0:
            return False
        if len(other.root) == 0:
            return True
        s0 = self.root[0]
        o0 = other.root[0]
        return s0 < o0

    @model_validator(mode="after")
    def _sort_data(self) -> Self:
        self.root.sort()
        return self


class NetlistArray(BaseModel):
    na: int
    nb: int


class NetlistInstance(BaseModel):
    kcl: str
    component: str
    settings: dict[str, JSONSerializable] = Field(default={})
    array: NetlistArray | None = Field(default=None)


class Netlist(BaseModel, extra="forbid"):
    name: str | None = None
    instances: dict[str, NetlistInstance] = Field(default_factory=dict)
    nets: list[Net] = Field(default_factory=list)
    ports: list[NetlistPort] = Field(default_factory=list)

    def sort(self) -> Self:
        if self.instances:
            self.instances = dict(sorted(self.instances.items()))
        self.nets.sort()
        if self.ports:
            self.ports.sort()
        return self

    @model_validator(mode="before")
    @classmethod
    def _validate_model(cls, data: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(data, dict):
            return data
        instances = data.get("instances")
        if instances:
            for name, instance in instances.items():
                if isinstance(instance, dict):
                    instance["name"] = name
        return data

    def create_port(self, name: str) -> NetlistPort:
        p = NetlistPort(name=name)
        self.ports.append(p)
        return p

    def create_inst(
        self, name: str, kcl: str, component: str, settings: dict[str, JSONSerializable]
    ) -> None:
        self.instances[name] = NetlistInstance(
            kcl=kcl, component=component, settings=settings
        )

    def create_net(self, *ports: PortRef | NetlistPort) -> None:
        net_ports: list[PortRef | NetlistPort] = []
        for port in ports:
            if isinstance(port, PortRef):
                if port.instance not in self.instances:
                    raise ValueError("Unknown instance ", port.instance)
                inst = self.instances[port.instance]
                if isinstance(port, PortArrayRef):
                    if port.ia == 1 and port.ib == 1:
                        net_ports.append(
                            PortRef(instance=port.instance, port=port.port)
                        )
                        continue
                    if not inst.array:
                        raise ValueError(
                            f"Instance {port.instance} is not an array instance. "
                            f"But an array portref was requested {port=}"
                        )
                    if port.ia > inst.array.na:
                        raise ValueError(
                            f"Instance {port.instance} has only {inst.array.na}"
                            " elements in `na` direction"
                        )
                    if port.ib > inst.array.nb:
                        raise ValueError(
                            f"Instance {port.instance} has only {inst.array.nb}"
                            " elements in `na` direction"
                        )
                net_ports.append(port)
            else:
                net_ports.append(NetlistPort(name=port.name))

        self.nets.append(Net(net_ports))
