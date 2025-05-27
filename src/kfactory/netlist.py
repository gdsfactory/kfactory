"""This is still experimental.

Caution is advised when using this, as the API might suddenly change.
In order to fix bugs etc.
"""

from __future__ import annotations

import re
from collections import defaultdict
from typing import Any, Self

from pydantic import BaseModel, Field, RootModel, model_validator

from .typings import JSONSerializable  # noqa: TC001

__all__ = ["Netlist", "NetlistInstance", "NetlistPort", "PortArrayRef", "PortRef"]


class PortRef(BaseModel, extra="forbid"):
    """Reference to a port in a Netlist or Schema Instance."""

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

    def __hash__(self) -> int:
        return hash((self.instance, self.port))

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, PortRef)
            and len(self.__class__.model_fields) == len(other.__class__.model_fields)
            and self.instance == other.instance
            and self.port == other.port
        )

    def __str__(self) -> str:
        return f"{self.instance}[{self.port!r}]"


class PortArrayRef(PortRef, extra="forbid"):
    """Reference to a port which is in an array instance."""

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

    def __hash__(self) -> int:
        return hash((self.instance, self.port, self.ia, self.ib))

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, PortArrayRef)
            and len(self.model_fields) == len(other.model_fields)
            and self.instance == other.instance
            and self.port == other.port
            and self.ia == other.ia
            and self.ib == other.ib
        )

    def __str__(self) -> str:
        return f"{self.instance}[{self.port!r}, {self.ia}, {self.ib}]"


class NetlistPort(BaseModel):
    """Cell level port in a netlsit."""

    name: str

    def __lt__(self, other: NetlistPort | PortRef) -> bool:
        if isinstance(other, NetlistPort):
            return self.name < other.name
        return True

    def __hash__(self) -> int:
        return hash(self.name)


class Net(RootModel[list[PortArrayRef | PortRef | NetlistPort]]):
    """Net for a Netlist.

    A net is a sequence of port references or netlist ports.
    """

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

    def __hash__(self) -> int:
        return hash(tuple(self.root))


class NetlistArray(BaseModel):
    na: int
    nb: int


class NetlistInstance(BaseModel):
    """Instance reference.

    Attributes:
        kcl: The original KCLayout (PDK) the instance was instantiated from.
        component: The `@cell` decorated function the component was instantiated from.
        settings: Settings used to call the component.
        array: Whether the instance was a AREF.
    """

    kcl: str
    component: str
    settings: dict[str, JSONSerializable] = Field(default={})
    array: NetlistArray | None = Field(default=None)
    name: str = Field(exclude=True)


class Netlist(BaseModel, extra="forbid"):
    """This is still experimental.

    Caution is advised when using this, as the API might suddenly change.
    In order to fix bugs etc.


    Attributes:
        instances: Dictionary with a mapping between instances and their settings.
        nets: Nets of the netlist. This is an abstraction and can in the Schema either
            be a route or a connection.
        ports: Ports/Pins of the netlist. Upstream exposed ports/pins. These can either
            be references to a subcircuit (instance) port or a new one.
    """

    instances: dict[str, NetlistInstance] = Field(default_factory=dict)
    nets: list[Net] = Field(default_factory=list)
    ports: list[NetlistPort] = Field(default_factory=list)

    def sort(self) -> Self:
        if self.instances:
            self.instances = dict(sorted(self.instances.items()))
        for net in self.nets:
            net.sort()
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
            kcl=kcl, component=component, settings=settings, name=name
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

    def lvs_equivalent(
        self,
        cell_name: str,
        equivalent_ports: dict[str, list[list[str]]],
        port_mapping: dict[str, dict[str | None, str]] | None = None,
    ) -> Netlist:
        """Get an equivalent netlist.

        This is is useful for when there are components such as pads which have
        more than one port which electrically are equivalent (same metal plane).

        Args:
            cell_name: Name of the netlist. This is usually `c.name` or similar.
                Used to retrieve equivalent ports for self.
            equivalent_ports: Dict containing cellname mapping vs lists of equivalent
                port names.
            port_mapping: Passed as a dict of
                `{c_name: {port_name: equivalent_name, ...}, ...}`.
                If not given is constructed in function.

        Returns:
            New netlist with equivalent ports mapped to their equivalent (usually first
            port name in the list of equivalents).
        """
        if port_mapping is None:
            port_mapping = defaultdict(dict)
            for cell_name_, list_of_port_lists in equivalent_ports.items():
                for port_list in list_of_port_lists:
                    if port_list:
                        p1 = port_list[0]
                        for port in port_list:
                            port_mapping[cell_name_][port] = p1
        ports_per_inst: dict[str, list[PortRef]] = defaultdict(list)
        net_for_port: dict[PortRef, Net] = {}

        matched_insts: list[str] = [
            inst.name
            for inst in self.instances.values()
            if inst.component in equivalent_ports
        ]
        changed_nets_dict: dict[PortRef, set[Net]] = defaultdict(set)
        all_changed_nets: set[Net] = set()
        nl = self.model_copy(deep=True)
        for net in nl.nets:
            for netport in net.root:
                if isinstance(netport, PortRef):
                    ports_per_inst[netport.instance].append(netport)
                    net_for_port[netport] = net
                    if netport.instance in matched_insts:
                        port_name = port_mapping[
                            nl.instances[netport.instance].component
                        ].get(netport.port)
                        if port_name is not None:
                            netport.port = port_name
                            changed_nets_dict[netport].add(net)
                            all_changed_nets.add(net)

        targets = {net: NetMergeTarget() for net in all_changed_nets}

        for changed_nets in changed_nets_dict.values():
            if len(changed_nets) > 1:
                changed_nets_ = list(changed_nets)
                t = targets[changed_nets_[0]].find_target()
                for net in changed_nets_:
                    target = targets[net].find_target()
                    target.set_target(t)

        nets_per_target: dict[NetMergeTarget, set[Net]] = defaultdict(set)
        for net in all_changed_nets:
            nets_per_target[targets[net].find_target()].add(net)

        del_nets: set[Net] = set()
        new_nets: list[Net] = []
        ports = {port.name: port for port in nl.ports}
        for nets in nets_per_target.values():
            new_net = Net(root=[])
            refs: set[PortRef | NetlistPort] = set()
            for net in nets:
                for portorref in net.root:
                    if isinstance(portorref, PortRef):
                        refs.add(portorref)
                    else:
                        refs.add(ports[port_mapping[cell_name][portorref.name]])
                del_nets.add(net)
            new_net.root.extend(list(refs))
            new_nets.append(new_net)

        nl.ports = list(set(ports.values()))
        nl.nets = list(set(nl.nets) - del_nets) + new_nets

        nl.sort()

        return nl


class NetMergeTarget:
    target: NetMergeTarget | None

    def __init__(self) -> None:
        self.target = None

    def set_target(self, target: NetMergeTarget) -> None:
        if target is not self:
            self.target = target

    def find_target(self) -> NetMergeTarget:
        if self.target is None:
            return self

        return self.target.find_target()
