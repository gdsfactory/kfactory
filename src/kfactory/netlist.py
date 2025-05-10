from __future__ import annotations

import re
from typing import Any, Self

from pydantic import BaseModel, Field, RootModel, model_validator

from .typings import JSONSerializable  # noqa: TC001


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


class NetlistInstance(BaseModel):
    name: str
    kcl: str
    component: str
    settings: dict[str, JSONSerializable] = Field(default={})


class Netlist(BaseModel, extra="forbid"):
    name: str | None = None
    instances: dict[str, NetlistInstance] | None = None
    nets: list[Net]
    ports: list[NetlistPort] | None = None

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
