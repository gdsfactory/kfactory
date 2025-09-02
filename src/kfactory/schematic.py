"""This is still experimental.

Caution is advised when using this, as the API might suddenly change.
In order to fix bugs etc.
"""

from __future__ import annotations

import keyword
import re
from collections import defaultdict
from operator import attrgetter
from pathlib import Path
from typing import (
    TYPE_CHECKING,
    Annotated,
    Any,
    Concatenate,
    Generic,
    Literal,
    Self,
    cast,
    overload,
)

from pydantic import (
    AfterValidator,
    BaseModel,
    Field,
    PrivateAttr,
    RootModel,
    field_serializer,
    field_validator,
    model_validator,
)
from ruamel.yaml import YAML

from . import kdb
from .conf import PROPID, logger
from .instance import DInstance, Instance, VInstance
from .kcell import DKCell, KCell, ProtoTKCell, VKCell
from .layout import KCLayout, get_default_kcl, kcls
from .netlist import Net, Netlist, NetlistInstance, NetlistPort, PortArrayRef, PortRef
from .port import DPort as DKCellPort
from .port import Port as KCellPort
from .port import ProtoPort
from .typings import KC, JSONSerializable, TUnit, dbu, um

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

    from .cross_section import CrossSection, DCrossSection

__all__ = ["DSchematic", "Schematic", "get_schematic", "read_schematic"]


yaml = YAML(typ="safe")

_schematic_default_imports = {
    "kfactory": "kf",
}


def _valid_varname(name: str) -> str:
    return name if name.isidentifier() and not keyword.iskeyword(name) else f"_{name}"


def _gez(value: TUnit) -> TUnit:
    if value < 0:
        raise ValueError(
            "x of pitch_a and y of pitch_b must be greater or equal to zero."
        )
    return value


class MirrorPlacement(BaseModel, extra="forbid"):
    mirror: bool = False


class Placement(MirrorPlacement, Generic[TUnit], extra="forbid"):
    x: TUnit | PortRef | PortArrayRef = cast("TUnit", 0)
    dx: TUnit = cast("TUnit", 0)
    y: TUnit | PortRef | PortArrayRef = cast("TUnit", 0)
    dy: TUnit = cast("TUnit", 0)
    orientation: float = 0
    port: str | None = None

    @model_validator(mode="after")
    def _require_absolute_or_relative(self) -> Self:
        if self.x is None and self.dx is None:
            raise ValueError("Either x or dx must be defined.")
        if self.y is None and self.dy is None:
            raise ValueError("Either y or dy must be defined.")

        return self

    @model_validator(mode="before")
    @classmethod
    def _replace_rotation_orientation(cls, data: dict[str, Any]) -> dict[str, Any]:
        if "rotation" in data:
            data["orientation"] = data.pop("rotation")
        return data

    def is_placeable(self, placed_instances: set[str], placed_ports: set[str]) -> bool:
        placeable = True
        if isinstance(self.x, PortRef):
            placeable = self.x.instance in placed_instances
        elif isinstance(self.x, Port):
            placeable = placeable and self.x.name in placed_ports
        if isinstance(self.y, PortRef):
            placeable = placeable and self.y.instance in placed_instances
        elif isinstance(self.y, Port):
            placeable = placeable and self.y.name in placed_ports
        return placeable


class RegularArray(BaseModel, Generic[TUnit], extra="forbid"):
    columns: int = Field(gt=0, default=1)
    column_pitch: TUnit
    rows: int = Field(gt=0, default=1)
    row_pitch: TUnit

    def __repr__(self) -> str:
        return f"RegularArray(columns={self.columns}, columns_pitch=)"


class Array(BaseModel, Generic[TUnit], extra="forbid"):
    na: int = Field(gt=1, default=1)
    nb: int = Field(gt=0, default=1)
    pitch_a: tuple[Annotated[TUnit, AfterValidator(_gez)], TUnit]
    pitch_b: tuple[TUnit, Annotated[TUnit, AfterValidator(_gez)]]


class Ports(BaseModel, Generic[TUnit]):
    instance: SchematicInstance[TUnit]

    def __getitem__(self, key: str | tuple[str, int, int]) -> PortRef | PortArrayRef:
        if isinstance(key, tuple):
            if self.instance.array is None:
                raise ValueError(
                    "Cannot use an array port reference if the schema"
                    " instance is not an Array."
                )
            return PortArrayRef(
                instance=self.instance.name, port=key[0], ia=key[1], ib=key[2]
            )
        return PortRef(instance=self.instance.name, port=key)


class SchematicInstance(
    BaseModel, Generic[TUnit], extra="forbid", arbitrary_types_allowed=True
):
    name: str = Field(exclude=True)
    component: str
    settings: dict[str, JSONSerializable] = Field(default_factory=dict)
    array: RegularArray[TUnit] | Array[TUnit] | None = None
    kcl: KCLayout = Field(default_factory=get_default_kcl)
    virtual: bool = False
    _schematic: TSchematic[TUnit] = PrivateAttr()

    @field_validator("kcl", mode="before")
    @classmethod
    def _find_kcl(cls, value: str | KCLayout) -> KCLayout:
        if isinstance(value, str):
            return kcls[value]
        return value

    @field_serializer("kcl")
    def _serialize_kcl(self, kcl: KCLayout) -> str:
        return kcl.name

    @property
    def parent_schematic(self) -> TSchematic[TUnit]:
        if self._schematic is None:
            raise RuntimeError("Schematic instance has no parent set.")
        return self._schematic

    @property
    def placement(self) -> MirrorPlacement | Placement[TUnit] | None:
        return self.parent_schematic.placements.get(self.name)

    def place(
        self,
        x: TUnit | PortRef = 0,
        y: TUnit | PortRef = 0,
        dx: TUnit = 0,
        dy: TUnit = 0,
        orientation: Literal[0, 90, 180, 270] = 0,
        mirror: bool = False,
        port: str | None = None,
    ) -> Placement[TUnit]:
        placement = Placement[TUnit](
            x=x, y=y, dx=dx, dy=dy, orientation=orientation, mirror=mirror, port=port
        )
        self.parent_schematic.placements[self.name] = placement
        return placement

    @overload
    def __getitem__(self, value: str) -> PortRef: ...
    @overload
    def __getitem__(self, value: tuple[str, int, int]) -> PortArrayRef: ...

    def __getitem__(self, value: str | tuple[str, int, int]) -> PortRef:
        if isinstance(value, str):
            return PortRef(instance=self.name, port=value)
        return PortArrayRef(instance=self.name, port=value[0], ia=value[1], ib=value[2])

    def connect(
        self,
        port: str | tuple[str, int, int],
        other: Port[TUnit] | PortRef,
    ) -> Connection[TUnit]:
        if isinstance(port, str):
            pref = PortRef(instance=self.name, port=port)
        else:
            pref = PortArrayRef(
                instance=self.name, port=port[0], ia=port[1], ib=port[2]
            )
        conn = Connection[TUnit]((other, pref))
        self.parent_schematic.connections.append(conn)
        return conn

    @property
    def mirror(self) -> bool:
        if self.placement is None:
            return False
        return self.placement.mirror

    @mirror.setter
    def mirror(self, value: bool) -> None:
        if self.placement is None:
            self.parent_schematic.placements[self.name] = MirrorPlacement(mirror=True)
        else:
            self.placement.mirror = value


class Route(BaseModel, Generic[TUnit], extra="forbid"):
    name: str = Field(exclude=True)
    links: list[Link[TUnit]]
    routing_strategy: str = "route_bundle"
    settings: dict[str, JSONSerializable]

    @model_validator(mode="before")
    @classmethod
    def _parse_links(cls, data: dict[str, Any]) -> dict[str, Any]:
        links = cast("dict[str, str]| None", data.get("links"))

        if isinstance(links, dict):
            data["links"] = [
                (tuple(str(k).split(",")), tuple(str(v).split(",")))
                for k, v in links.items()
            ]
        if "settings" not in data:
            data["settings"] = {}
        return data


class Port(BaseModel, Generic[TUnit], extra="forbid"):
    name: str = Field(exclude=True)
    x: TUnit | PortRef
    y: TUnit | PortRef
    dx: TUnit = cast("TUnit", 0)
    dy: TUnit = cast("TUnit", 0)
    cross_section: str
    orientation: Literal[0, 90, 180, 270] | PortRef

    def __lt__(self, other: Port[Any] | PortRef) -> bool:
        if isinstance(other, Port):
            return self._as_tuple() < other._as_tuple()
        return True

    def _as_tuple(
        self,
    ) -> tuple[
        str,
        TUnit | PortRef,
        TUnit | PortRef,
        TUnit,
        TUnit,
        Literal[0, 90, 180, 270] | PortRef,
        str,
    ]:
        return (
            self.name,
            self.x,
            self.y,
            self.dx,
            self.dy,
            self.orientation,
            self.cross_section,
        )

    def is_placeable(self, placed_instances: set[str]) -> bool:
        placeable = True
        if isinstance(self.x, PortRef):
            placeable = self.x.instance in placed_instances
        if isinstance(self.y, PortRef):
            placeable = placeable and self.y.instance in placed_instances
        if isinstance(self.orientation, PortRef):
            placeable = placeable and self.orientation.instance in placed_instances
        return placeable

    def place(
        self,
        cell: KCell,
        schematic: TSchematic[TUnit],
        name: str,
        cross_sections: dict[str, CrossSection | DCrossSection],
    ) -> KCellPort:
        if isinstance(self.x, PortRef):
            if isinstance(self.x, PortArrayRef):
                x: float = (
                    cell.insts[self.x.instance]
                    .ports[self.x.port, self.x.ia, self.x.ib]
                    .x
                )
            else:
                x = cell.insts[self.x.instance].ports[self.x.port].x
        else:
            x = self.x
        x += self.dx
        if isinstance(self.y, PortRef):
            if isinstance(self.y, PortArrayRef):
                y: float = (
                    cell.insts[self.y.instance]
                    .ports[self.y.port, self.y.ia, self.y.ib]
                    .y
                )
            else:
                y = cell.insts[self.y.instance].ports[self.y.port].y
        else:
            y = self.y
        y += self.dy
        if isinstance(self.orientation, PortRef):
            orientation = (
                cell.insts[self.orientation.instance]
                .ports[self.orientation.port]
                .orientation
            )
        else:
            orientation = self.orientation

        if schematic.unit == "dbu":
            return cell.create_port(
                dcplx_trans=kdb.DCplxTrans(
                    rot=orientation,
                    x=cell.kcl.to_um(cast("int", x)),
                    y=cell.kcl.to_um(cast("int", y)),
                ),
                cross_section=cross_sections[self.cross_section],
                name=self.name,
            )

        return cell.create_port(
            dcplx_trans=kdb.DCplxTrans(rot=orientation, x=x, y=y),
            cross_section=cross_sections[self.cross_section],
            name=self.name,
        )

    def __str__(self) -> str:
        return f"CellPort[{self.name!r}]"

    def as_call(self) -> str:
        port_str = f"x={self.x}, y={self.y}"
        if self.dx:
            port_str += f", {self.dx}"
        if self.dy:
            port_str += f", {self.dy}"

        return port_str

    def as_python_str(self) -> str:
        return f"schema.ports[{self.name!r}]"


class Link(
    RootModel[
        tuple[
            PortArrayRef | PortRef | Port[TUnit], PortArrayRef | PortRef | Port[TUnit]
        ]
    ],
    Generic[TUnit],
):
    root: tuple[
        PortArrayRef | PortRef | Port[TUnit], PortArrayRef | PortRef | Port[TUnit]
    ]

    @model_validator(mode="after")
    def _sort_data(self) -> Self:
        self.root = tuple(sorted(self.root))  # type: ignore[assignment]
        return self


class Connection(
    RootModel[
        tuple[
            Port[TUnit] | PortArrayRef | PortRef, Port[TUnit] | PortArrayRef | PortRef
        ]
    ]
):
    root: tuple[PortArrayRef | PortRef | Port[TUnit], PortArrayRef | PortRef]

    @model_validator(mode="after")
    def _sort_data(self) -> Self:
        self.root = tuple(sorted(self.root))  # type: ignore[assignment]
        if isinstance(self.root[1], Port):
            raise TypeError(
                "Two cell ports cannot be connected together. This would cause an "
                "invalid netlist."
            )
        return self

    @classmethod
    def from_list(
        cls, data: list[Any] | tuple[Any, ...] | dict[str, Any]
    ) -> Connection[TUnit]:
        if isinstance(data, list | tuple):
            if isinstance(data[0][0], list | tuple):
                p1 = {
                    "instance": data[0][0][0],
                    "port": data[0][1],
                    "ia": data[0][0][1][0],
                    "ib": data[0][0][1][1],
                }
            else:
                p1 = {"instance": data[0][0], "port": data[0][1]}
            if isinstance(data[1][0], list | tuple):
                p2 = {
                    "instance": data[1][0][0],
                    "port": data[1][1],
                    "ia": data[1][0][1][0],
                    "ib": data[1][0][1][1],
                }
            else:
                p2 = {"instance": data[1][0], "port": data[1][1]}

            return Connection.model_validate((p1, p2))
        return Connection(**data)


class TSchematic(BaseModel, Generic[TUnit], extra="forbid"):
    name: str | None = None
    dependencies: list[Path] = Field(default_factory=list)
    instances: dict[str, SchematicInstance[TUnit]] = Field(default_factory=dict)
    placements: dict[str, MirrorPlacement | Placement[TUnit]] = Field(
        default_factory=dict
    )
    connections: list[Connection[TUnit]] = Field(default_factory=list)
    routes: dict[str, Route[TUnit]] = Field(default_factory=dict)
    ports: dict[str, Port[TUnit] | PortRef | PortArrayRef] = Field(default_factory=dict)
    kcl: KCLayout = Field(exclude=True, default_factory=get_default_kcl)
    unit: Literal["dbu", "um"]

    def create_inst(
        self,
        name: str,
        component: str,
        settings: dict[str, JSONSerializable] | None = None,
        array: RegularArray[TUnit] | Array[TUnit] | None = None,
        placement: Placement[TUnit] | None = None,
        kcl: KCLayout | None = None,
    ) -> SchematicInstance[TUnit]:
        """Create a schema instance.

        This would be an SREF or AREF in the resulting GDS cell.

        Args:
            name: Instance name. In a schema, each instance must be named,
                unless created through routing functions.
            component: Factory name of the component to instantiate.
            settings: Settings dictionary to configure the factory.
            array: If the instance should create an array instance (AREF),
                this can be passed here as an `Array` class instance.
            placement: Optional placement for the instance. Can also be configured
                with `inst.place(...)` afterwards.

        Returns:
            Schematic instance representing the args.
        """
        inst = SchematicInstance[TUnit].model_validate(
            {
                "name": name,
                "component": component,
                "settings": settings or {},
                "array": array,
                "kcl": kcl or self.kcl,
            }
        )
        inst._schematic = self

        self.instances[inst.name] = inst
        if placement:
            self.placements[inst.name] = placement
        return inst

    def add_port(
        self, name: str | None = None, *, port: PortRef | PortArrayRef
    ) -> None:
        name = name or port.port
        if name not in self.ports:
            self.ports[name] = port
            return
        raise ValueError(f"Port with name {name} already exists")

    def create_port(
        self,
        name: str,
        cross_section: str,
        x: PortRef | PortArrayRef | TUnit,
        y: PortRef | PortArrayRef | TUnit,
        dx: TUnit = 0,
        dy: TUnit = 0,
        orientation: Literal[0, 90, 180, 270] = 0,
    ) -> Port[TUnit]:
        p = Port(
            name=name,
            x=x,
            y=y,
            dx=dx,
            dy=dy,
            cross_section=cross_section,
            orientation=orientation,
        )
        self.ports[p.name] = p
        return p

    def create_connection(self, port1: PortRef, port2: PortRef) -> Connection[TUnit]:
        conn = Connection[TUnit]((port1, port2))
        if port1.instance not in self.instances:
            raise ValueError(
                f"Cannot create connection to unknown instance {port1.instance}"
            )
        if port2.instance not in self.instances:
            raise ValueError(
                f"Cannot create connection to unknown instance {port2.instance}"
            )
        self.connections.append(conn)
        return conn

    def netlist(self) -> Netlist:
        nets: list[Net] = []
        if self.routes is not None:
            nets.extend(
                [
                    Net(
                        [
                            NetlistPort(name=port.name)
                            if isinstance(port, Port)
                            else port
                            for port in link.root
                        ]
                    )
                    for route in self.routes.values()
                    for link in route.links
                ]
            )
        if self.connections:
            nets.extend(
                [
                    Net(
                        [
                            NetlistPort(name=p.name) if isinstance(p, Port) else p
                            for p in connection.root
                        ]
                    )
                    for connection in self.connections
                ]
            )

        if self.ports:
            nets.extend(
                [
                    Net([NetlistPort(name=name), p])
                    for name, p in self.ports.items()
                    if isinstance(p, PortRef)
                ]
            )

        nl = Netlist(
            instances={
                inst.name: NetlistInstance(
                    name=inst.name,
                    kcl=inst.kcl.name,
                    component=inst.component,
                    settings=inst.settings,
                )
                for inst in self.instances.values()
            }
            if self.instances
            else {},
            nets=nets,
            ports=[NetlistPort(name=name) for name in self.ports],
        )
        nl.sort()
        return nl

    @model_validator(mode="before")
    @classmethod
    def _validate_schematic(cls, data: dict[str, Any]) -> dict[str, Any]:
        data.pop("nets", None)
        if not isinstance(data, dict):
            return data
        if "kcl" in data and isinstance(data["kcl"], str):
            data["kcl"] = kcls[data["kcl"]]
        instances = data.get("instances")
        if instances:
            for name, instance in instances.items():
                instance["name"] = name
        routes = data.get("routes")
        if routes:
            for name, route in routes.items():
                route["name"] = name
        connections = data.get("connections")
        if connections is not None and isinstance(connections, dict):
            built_connections: list[Connection[TUnit]] = []
            connections_: list[tuple[tuple[str, str], tuple[str, str]]] = [
                (k.rsplit(",", 1), v.rsplit(",", 1)) for k, v in connections.items()
            ]
            for connection_ in connections_:
                connection_0: (
                    tuple[str, str] | tuple[tuple[str, tuple[int, ...]], str]
                ) = connection_[0]
                match = re.match(r"(.*?)(<\d+\.\d+>)$", connection_[0][0])
                if match:
                    connection_0 = (
                        (
                            match.group(1),
                            tuple(
                                int(j) for j in match.group(2).strip("<>").split(".")
                            ),
                        ),
                        connection_[0][1],
                    )
                connection_1: (
                    tuple[str, str] | tuple[tuple[str, tuple[int, ...]], str]
                ) = connection_[1]
                match = re.match(r"(.*?)(<\d+\.\d+>)$", connection_[1][0])
                if match:
                    connection_1 = (
                        (
                            match.group(1),
                            tuple(
                                int(j) for j in match.group(2).strip("<>").split(".")
                            ),
                        ),
                        connection_[1][1],
                    )
                built_connections.append(
                    Connection.from_list((connection_0, connection_1))
                )
            data["connections"] = built_connections
        return data

    @model_validator(mode="after")
    def assign_backrefs(self) -> Self:
        for inst in self.instances.values():
            inst._schematic = self
        return self

    def create_cell(
        self,
        output_type: type[KC],
        factories: dict[
            str, Callable[..., KCell] | Callable[..., DKCell] | Callable[..., VKCell]
        ]
        | None = None,
        cross_sections: dict[str, CrossSection | DCrossSection] | None = None,
        routing_strategies: dict[
            str,
            Callable[
                Concatenate[
                    ProtoTKCell[Any],
                    Sequence[ProtoPort[Any]],
                    Sequence[ProtoPort[Any]],
                    ...,
                ],
                Any,
            ],
        ]
        | None = None,
        place_unknown: bool = False,
    ) -> KC:
        c = KCell(kcl=self.kcl)

        # calculate islands -- islands are a bunch of directly connected instances and
        # must be isolated from other islands either through no connection at all or
        # routes
        islands: dict[str, set[str]] = {}
        instance_connections: defaultdict[str, list[Connection[TUnit]]] = defaultdict(
            list
        )

        if routing_strategies is None:
            routing_strategies = c.kcl.routing_strategies

        if cross_sections is None:
            cross_sections = {
                name: c.kcl.get_icross_section(xs)
                for name, xs in c.kcl.cross_sections.cross_sections.items()
            }

        for connection in self.connections:
            pr1, pr2 = connection.root
            if isinstance(pr1, Port):
                continue
            instance_connections[pr1.instance].append(connection)
            instance_connections[pr2.instance].append(connection)
            islands1 = islands.get(pr1.instance)
            islands2 = islands.get(pr2.instance)
            match islands1 is None, islands2 is None:
                case True, True:
                    island = {pr1.instance, pr2.instance}
                    islands[pr1.instance] = island
                    islands[pr2.instance] = island
                case False, True:
                    island = islands[pr1.instance]
                    island.add(pr2.instance)
                    islands[pr2.instance] = island
                case True, False:
                    island = islands[pr2.instance]
                    island.add(pr1.instance)
                    islands[pr1.instance] = island
                case False, False:
                    island = islands[pr1.instance] | islands[pr2.instance]
                    for instance_name in island:
                        islands[instance_name] = island

        for inst_name in self.instances:
            if inst_name not in islands:
                islands[inst_name] = {inst_name}

        placed_insts: set[str] = set()
        placed_ports: set[str] = set()

        for name, port in self.ports.items():
            if port.is_placeable(placed_instances=placed_insts):
                p = port.place(
                    cell=c,
                    schematic=self,
                    name=name,
                    cross_sections=cross_sections,
                )
                placed_ports.add(p.name)  # type: ignore[arg-type]

        instances: dict[str, Instance | VInstance] = {}
        placed_islands: list[set[str]] = []
        seen_islands: set[int] = set()
        unique_islands: list[set[str]] = []
        for island in islands.values():
            island_id = id(island)
            if island_id not in seen_islands:
                seen_islands.add(island_id)
                unique_islands.append(island)
        for i, island in enumerate(unique_islands):
            logger.debug("Placing island {} of schema {}, {}", i, self.name, island)
            if island not in placed_islands:
                _place_island(
                    c,
                    schematic_island=island,
                    instances=instances,
                    connections=instance_connections,
                    schematic_instances=self.instances,
                    placed_insts=placed_insts,
                    placed_ports=placed_ports,
                    schematic=self,
                    cross_sections=cross_sections,
                    factories=factories,
                    place_unknown=place_unknown,
                )
                placed_islands.append(island)
                placed_insts |= island

        # routes
        for route in self.routes.values():
            start_ports: list[ProtoPort[Any]] = []
            end_ports: list[ProtoPort[Any]] = []
            for link in route.links:
                l1, l2 = link.root[0], link.root[1]
                if isinstance(l1, Port):
                    p1 = c.ports[l1.name]
                elif isinstance(l1, PortArrayRef):
                    p1 = c.insts[l1.instance].ports[l1.port, l1.ia, l1.ib]
                else:
                    p1 = c.insts[l1.instance].ports[l1.port]
                start_ports.append(p1)
                if isinstance(l2, Port):
                    p2 = c.ports[l2.name]
                elif isinstance(l2, PortArrayRef):
                    p2 = c.insts[l2.instance].ports[l2.port, l2.ia, l2.ib]
                else:
                    p2 = c.insts[l2.instance].ports[l2.port]
                end_ports.append(p2)
            route_c = output_type(base=c.base)
            if isinstance(route_c, KCell):
                routing_strategies[route.routing_strategy](
                    output_type(base=c.base), start_ports, end_ports, **route.settings
                )
            else:
                routing_strategies[route.routing_strategy](
                    output_type(base=c.base),
                    [DKCellPort(base=sp.base) for sp in start_ports],
                    [DKCellPort(base=ep.base) for ep in end_ports],
                    **route.settings,
                )

        # verify connections
        port_connection_transformation_errors: list[Connection[TUnit]] = []
        connection_transformation_errors: list[Connection[TUnit]] = []
        for conn in self.connections:
            c1 = conn.root[0]
            c2 = conn.root[1]
            if isinstance(c1, Port):
                p1 = c.ports[c1.name]
                p2 = c.insts[c2.instance].ports[c2.port]
                if p1.dcplx_trans != p2.dcplx_trans:
                    port_connection_transformation_errors.append(conn)
            else:
                if isinstance(c1, PortArrayRef):
                    p1 = c.insts[c1.instance].ports[c1.port, c1.ia, c1.ib]
                else:
                    p1 = c.insts[c1.instance].ports[c1.port]
                if isinstance(c2, PortArrayRef):
                    p2 = c.insts[c2.instance].ports[c2.port, c2.ia, c2.ib]
                else:
                    p2 = c.insts[c2.instance].ports[c2.port]

                t1 = p1.dcplx_trans
                t2 = p2.dcplx_trans
                if (t1 != t2 * kdb.DCplxTrans.R180) and (t1 != t2 * kdb.DCplxTrans.M90):
                    connection_transformation_errors.append(conn)

        if connection_transformation_errors or port_connection_transformation_errors:
            raise ValueError(
                f"Not all connections in schema {self.name}"
                " could be satisfied. Missing or wrong connections:\n"
                + "\n".join(
                    f"{conn.root[0]} - {conn.root[1]}"
                    for conn in connection_transformation_errors
                    + port_connection_transformation_errors
                )
            )

        return output_type(base=c.base)

    def add_route(
        self,
        name: str,
        start_ports: list[PortRef | Port[TUnit]],
        end_ports: list[PortRef | Port[TUnit]],
        routing_strategy: str,
        **settings: JSONSerializable,
    ) -> Route[TUnit]:
        if name in self.routes:
            raise ValueError(f"Route with name {name!r} already exists")
        route = Route[TUnit](
            name=name,
            routing_strategy=routing_strategy,
            links=[
                Link((sp, ep)) for sp, ep in zip(start_ports, end_ports, strict=True)
            ],
            settings=settings,
        )
        self.routes[name] = route
        return route

    def __getitem__(self, key: str) -> Port[TUnit] | PortRef:
        return self.ports[key]

    def code_str(
        self,
        imports: dict[str, str] = _schematic_default_imports,
        kfactory_name: str | None = None,
    ) -> str:
        schematic_cell = ""
        indent = 0

        def _ind() -> str:
            nonlocal indent
            return " " * indent

        kf_name = kfactory_name or imports["kfactory"]

        def _kcls(name: str) -> str:
            return f'{kf_name}.["{name}"]'

        for imp, imp_as in imports.items():
            if imp_as is None:
                schematic_cell += f"import {imp}\n"
            else:
                schematic_cell += f"import {imp} as {imp_as}\n"

        if imports:
            schematic_cell += "\n\n"

        schematic_cell += f"kcl = {_kcls(self.kcl.name)}']\n\n"

        schematic_cell += "@kcl.schematic_cell\n"
        schematic_cell += f"def {self.name}() -> {kf_name}.{self.__class__.__name__}:\n"
        indent = 2

        schematic_cell += f"{_ind()}schematic = Schematic(kcl=kcl)\n\n"

        schematic_cell += f"{_ind()}# Create the schematic instances\n"

        names: dict[str, str] = {}

        for inst in sorted(self.instances.values(), key=attrgetter("name")):
            inst_name = _valid_varname(inst.name)
            names[inst.name] = inst_name
            schematic_cell += f"{_ind()}{inst_name} = schematic.create_inst(\n"
            indent += 2
            schematic_cell += f"{_ind()}name={inst.name!r},\n"
            f"{_ind()}component={inst.component!r},\n"
            f"{_ind()}settings={inst.settings!r},\n"
            f"{_ind()}kcl={inst.kcl.name!r},\n"
            if inst.array is not None:
                arr = inst.array
                if isinstance(arr, RegularArray):
                    schematic_cell += f"{_ind()}array=RegularArray(\n"
                    indent += 2
                    schematic_cell += f"{_ind()}columns={arr.columns},\n"
                    f"{_ind()}columns_pitch={arr.column_pitch},\n"
                    f"{_ind()}rows={arr.rows},\n"
                    f"{_ind()}row_pitch={arr.row_pitch}),\n"
                    indent -= 2
                    schematic_cell += f"{_ind()})\n"
                else:
                    schematic_cell += f"{_ind()}array=Array(\n"
                    indent += 2
                    schematic_cell += f"{_ind()}na={arr.na},\n"
                    f"{_ind()}nb={arr.nb},\n"
                    f"{_ind()}pitch_a={arr.pitch_a},\n"
                    f"{_ind()}pitch_b={arr.pitch_b}),\n"
                    indent -= 2
                    schematic_cell += f"{_ind()})\n"
            indent -= 2
            schematic_cell += f"{_ind()})\n"

        if self.ports:
            schematic_cell += f"{_ind()}# Schematic ports\n"

            for port in sorted(
                self.ports.values(), key=attrgetter("__class__.__name__", "name")
            ):
                if isinstance(port, Port):
                    schematic_cell += f"{_ind()}schematic.create_port(\n"
                    indent += 2
                    schematic_cell += f"{_ind()}name={port.name!r},\n"
                    schematic_cell += f"{_ind()}cross_section={port.cross_section!r},\n"
                    schematic_cell += f"{_ind()}orientation={port.orientation},\n"
                    if isinstance(port.x, PortRef):
                        schematic_cell += (
                            f"{_ind()}x={port.x.as_python_str(names[port.x.name])},\n"
                        )
                    else:
                        schematic_cell += f"{_ind()}x={port.x},\n"
                    if isinstance(port.y, PortRef):
                        schematic_cell += (
                            f"{_ind()}y={port.y.as_python_str(names[port.y.name])},\n"
                        )
                    else:
                        schematic_cell += f"{_ind()}y={port.y},\n"
                    if port.dx:
                        f"{_ind()}dx={port.dx},\n"
                    if port.dy:
                        f"{_ind()}dy={port.dy},\n"
                    indent -= 2
                else:
                    schematic_cell += (
                        f"{_ind()}schematic.add_port("
                        f"{port.as_python_str(names[port.instance])})\n"
                    )
        if self.placements:
            schematic_cell += f"\n{_ind()}# Schematic instance placements\n"

            for name, placement in sorted(
                self.placements.items(), key=lambda p: (isinstance(p, Placement), p[0])
            ):
                inst_name = names[name]
                if isinstance(placement, Placement):
                    schematic_cell += f"{_ind()}{inst_name}.place(\n"
                    indent += 2
                    if placement.x:
                        schematic_cell += f"{_ind()}x={placement.x},\n"
                    if placement.y:
                        schematic_cell += f"{_ind()}y={placement.y},\n"
                    if placement.dx:
                        schematic_cell += f"{_ind()}dx={placement.dx},\n"
                    if placement.dy:
                        schematic_cell += f"{_ind()}dy={placement.dy},\n"
                    if placement.orientation:
                        schematic_cell += (
                            f"{_ind()}orientation={placement.orientation},\n"
                        )
                    if placement.mirror:
                        schematic_cell += f"{_ind()}mirror={placement.mirror},\n"
                    if placement.port is not None:
                        schematic_cell += f"{_ind()}port={placement.port},\n"
                    indent -= 2
                    schematic_cell += f"{_ind()})\n"
                else:
                    schematic_cell += f"{_ind()}{inst_name}.mirror = True\n"

        if self.connections:
            schematic_cell += f"\n{_ind()}# Schematic connections\n"

            for connection in self.connections:
                ref1, ref2 = connection.root
                if isinstance(ref1, PortRef):
                    schematic_cell += f"{_ind()}{names[ref1.instance]}.connect(\n"
                    indent += 2
                    if isinstance(ref1, PortArrayRef):
                        schematic_cell += (
                            f"{_ind()}port=({ref1.port!r},{ref1.ia},{ref1.ib}),\n"
                        )
                    else:
                        schematic_cell += f"{_ind()}port={ref1.port!r},\n"
                    assert isinstance(ref2, PortRef)
                    if isinstance(ref2, PortRef):
                        schematic_cell += (
                            f"{_ind()}other={ref2.as_python_str(names[ref2.name])},\n"
                        )
                    indent -= 2
                    schematic_cell += f"{_ind()})\n"
                else:
                    assert isinstance(ref2, PortRef)
                    schematic_cell += f"{_ind()}{names[ref2.instance]}.connect(\n"
                    indent += 2
                    if isinstance(ref2, PortArrayRef):
                        schematic_cell += (
                            f"{_ind()}port=({ref2.port!r}, {ref2.ia}, {ref2.ib}),\n"
                        )
                    else:
                        schematic_cell += f"{_ind()}port={ref2.port!r},\n"
                    schematic_cell += f"{_ind()}other=schematic.ports[{ref1.name!r}]\n"
                    indent -= 2
                    schematic_cell += f"{_ind()})\n"
        if self.routes:
            schematic_cell += f"\n{_ind()}# Schematic routes\n"
            for route in self.routes.values():
                schematic_cell += f"{_ind()}schematic.add_route(\n"
                indent += 2
                # schematic_cell += f"{_ind()}
                schematic_cell += f"{_ind()}name={route.name!r},\n"
                start_ports: list[str] = []
                end_ports: list[str] = []
                for link in route.links:
                    p1, p2 = link.root
                    if isinstance(p1, Port):
                        start_ports.append(p1.as_python_str())
                    else:
                        start_ports.append(p1.as_python_str(names[p1.instance]))
                    if isinstance(p2, Port):
                        start_ports.append(p2.as_python_str())
                    else:
                        start_ports.append(p2.as_python_str(names[p2.instance]))

                schematic_cell += f"{_ind()}start_ports=[{', '.join(start_ports)}],\n"
                schematic_cell += f"{_ind()}end_ports=[{', '.join(end_ports)}],\n"
                schematic_cell += (
                    f"{_ind()}routing_strategy={route.routing_strategy!r},\n"
                )
                for key, value in route.settings.items():
                    if isinstance(value, str):
                        schematic_cell += f"{_ind()}{key}={value!r},\n"
                    else:
                        schematic_cell += f"{_ind()}{key}={value},\n"
                indent -= 2
                schematic_cell += f"{_ind()})\n"

        schematic_cell += f"{_ind()}return schema"

        return schematic_cell


class Schematic(TSchematic[dbu]):
    """Schematic with a base unit of dbu for placements."""

    unit: Literal["dbu"] = "dbu"

    def __init__(self, **data: Any) -> None:
        if "unit" in data:
            raise ValueError(
                "Cannot set the unit direct. It needs to be set by the class init."
            )
        super().__init__(unit="dbu", **data)


class DSchematic(TSchematic[um]):
    """Schematic with a base unit of um for placements."""

    unit: Literal["um"] = "um"

    def __init__(self, **data: Any) -> None:
        if "unit" in data:
            raise ValueError(
                "Cannot set the unit direct. It needs to be set by the class init."
            )
        super().__init__(unit="um", **data)


class Schema(Schematic):
    """Schematic with a base unit of dbu for placements."""

    def __init__(self, **data: Any) -> None:
        logger.warning(
            "Schema is deprecated, please use Schematic. "
            "It will be removed in kfactory 2.0"
        )
        if "unit" in data:
            raise ValueError(
                "Cannot set the unit direct. It needs to be set by the class init."
            )
        super().__init__(**data)


class DSchema(DSchematic):
    """Schematic with a base unit of um for placements."""

    def __init__(self, **data: Any) -> None:
        logger.warning(
            "DSchema is deprecated, please use DSchematic. "
            "It will be removed in kfactory 2.0"
        )
        if "unit" in data:
            raise ValueError(
                "Cannot set the unit direct. It needs to be set by the class init."
            )
        super().__init__(**data)


def _create_kinst(
    c: KCell,
    schematic_inst: SchematicInstance[TUnit],
    factories: dict[
        str, Callable[..., KCell] | Callable[..., DKCell] | Callable[..., VKCell]
    ]
    | None,
) -> Instance | VInstance:
    kinst: Instance | DInstance

    cell_ = (
        factories[schematic_inst.component](**schematic_inst.settings)
        if factories
        else schematic_inst.kcl.get_anycell(
            schematic_inst.component, **schematic_inst.settings
        )
    )
    schematic = schematic_inst._schematic
    unit = schematic.unit
    if isinstance(cell_, ProtoTKCell):
        cell = KCell(base=cell_.base)
        if not schematic_inst.virtual:
            if schematic_inst.array:
                if isinstance(schematic_inst.array, RegularArray):
                    a = _vec(
                        x=schematic_inst.array.column_pitch,
                        y=0,
                        c=c,
                        unit=unit,
                    )
                    b = _vec(
                        x=0,
                        y=schematic_inst.array.row_pitch,
                        c=c,
                        unit=unit,
                    )
                    na = schematic_inst.array.columns
                    nb = schematic_inst.array.rows
                else:
                    a = _vec(*schematic_inst.array.pitch_a, c=c, unit=unit)
                    b = _vec(*schematic_inst.array.pitch_b, c=c, unit=unit)
                    na = schematic_inst.array.na
                    nb = schematic_inst.array.nb
                if schematic_inst.settings:
                    kinst = c.create_inst(
                        cell,
                        a=a,
                        b=b,
                        na=na,
                        nb=nb,
                    )
                else:
                    kinst = c.create_inst(
                        cell,
                        a=a,
                        b=b,
                        na=na,
                        nb=nb,
                    )
            else:
                kinst = c.create_inst(cell)
            kinst.name = schematic_inst.name
            return Instance(kcl=c.kcl, instance=kinst._instance)

    # If the instance is a
    vinst = c.create_vinst(cell)
    if schematic_inst.array:
        if isinstance(schematic_inst.array, RegularArray):
            da = _dvec(x=schematic_inst.array.column_pitch, y=0, c=c, unit=unit)
            db = _dvec(x=0, y=schematic_inst.array.row_pitch, c=c, unit=unit)
            na = schematic_inst.array.columns
            nb = schematic_inst.array.rows
        else:
            da = _dvec(*schematic_inst.array.pitch_a, c=c, unit=unit)
            db = _dvec(*schematic_inst.array.pitch_b, c=c, unit=unit)
            na = schematic_inst.array.na
            nb = schematic_inst.array.nb
        vinst.a = da
        vinst.b = db
        vinst.na = na
        vinst.nb = nb
    if schematic_inst.mirror:
        vinst.transform(kdb.DCplxTrans.M0)
    return vinst


def _vec(x: float, y: float, c: KCell, unit: Literal["dbu", "um"]) -> kdb.Vector:
    if unit == "um":
        x = c.kcl.to_dbu(x)
        y = c.kcl.to_dbu(y)
    return kdb.Vector(cast("int", x), cast("int", y))


def _dvec(x: float, y: float, c: KCell, unit: Literal["dbu", "um"]) -> kdb.DVector:
    if unit == "dbu":
        x = c.kcl.to_um(cast("int", x))
        y = c.kcl.to_um(cast("int", y))
    return kdb.DVector(x, y)


def _place_island(
    c: KCell,
    schematic_island: set[str],
    instances: dict[str, Instance | VInstance],
    connections: dict[str, list[Connection[TUnit]]],
    schematic_instances: dict[str, SchematicInstance[TUnit]],
    placed_insts: set[str],
    placed_ports: set[str],
    schematic: TSchematic[TUnit],
    cross_sections: dict[str, CrossSection | DCrossSection],
    factories: dict[
        str, Callable[..., KCell] | Callable[..., DKCell] | Callable[..., VKCell]
    ]
    | None = None,
    place_unknown: bool = False,
) -> set[str]:
    target_length = len(schematic_island)

    for inst in schematic_island:
        schema_inst = schematic_instances[inst]
        kinst = _create_kinst(c, schema_inst, factories=factories)
        instances[inst] = kinst
        if schema_inst.placement:
            if isinstance(schema_inst.placement, Placement):
                logger.debug("Placing {}", schema_inst.name)
                p = schema_inst.placement
                assert p is not None
                if p.is_placeable(placed_insts, placed_ports):
                    x = (
                        instances[p.x.instance].ports[p.x.port].x
                        if isinstance(p.x, PortRef)
                        else p.x
                    )
                    y = (
                        instances[p.y.instance].ports[p.y.port].y
                        if isinstance(p.y, PortRef)
                        else p.y
                    )

                    st = kinst._standard_trans()
                    if st is kdb.Trans or st is kdb.ICplxTrans:
                        if p.port is None:
                            kinst.transform(
                                kdb.ICplxTrans(
                                    mag=1,
                                    rot=p.orientation,
                                    mirrx=p.mirror,
                                    x=x + p.dx,
                                    y=y + p.dy,
                                )
                            )
                        else:
                            kinst.transform(
                                kdb.ICplxTrans(
                                    mag=1,
                                    rot=p.orientation,
                                    mirrx=p.mirror,
                                    x=x + p.dx,
                                    y=y + p.dy,
                                )
                                * kdb.ICplxTrans(-kinst.ports[p.port].trans.disp)
                            )
                    elif p.port is None:
                        kinst.transform(
                            kdb.DCplxTrans(
                                mag=1,
                                rot=p.orientation,
                                mirrx=p.mirror,
                                x=x + p.dx,
                                y=y + p.dy,
                            )
                        )
                    else:
                        kinst.transform(
                            kdb.DCplxTrans(
                                mag=1,
                                rot=p.orientation,
                                mirrx=p.mirror,
                                x=x + p.dx,
                                y=y + p.dy,
                            )
                            * kdb.DCplxTrans(-kinst.ports[p.port].dcplx_trans.disp)
                        )
                    placed_insts.add(inst)
            else:
                kinst.transform(kdb.Trans.M0)

    placed_island_insts = placed_insts & schematic_island

    placed = _get_and_place_insts_and_ports(
        c=c,
        placed_insts=placed_insts,
        placed_ports=placed_ports,
        connections=connections,
        schematic=schematic,
        instances=instances,
        placed_island_insts=placed_island_insts,
        cross_sections=cross_sections,
    )

    while placed:
        placed = _get_and_place_insts_and_ports(
            c=c,
            placed_insts=placed_insts,
            placed_ports=placed_ports,
            connections=connections,
            schematic=schematic,
            instances=instances,
            placed_island_insts=placed_island_insts,
            cross_sections=cross_sections,
        )

    if len(placed_island_insts) < target_length:
        if place_unknown:
            place_inst = next(iter(schematic_island - placed_island_insts))
            logger.warning(
                "Cannot determine instance placement. Using implicit placement 0,0 "
                f"with orientation 0 for instance {place_inst!r}"
            )
            schematic.instances[place_inst].place()
            placed_insts.add(place_inst)
            placed_island_insts.add(place_inst)
            placed = True
            while placed:
                placed = _get_and_place_insts_and_ports(
                    c=c,
                    placed_insts=placed_insts,
                    placed_ports=placed_ports,
                    connections=connections,
                    schematic=schematic,
                    instances=instances,
                    placed_island_insts=placed_island_insts,
                    cross_sections=cross_sections,
                )
        if len(placed_island_insts) < target_length:
            raise ValueError(
                "Could not place all instances. This is likely due to missing place "
                "instructions (need at least 1 per individual group of connected"
                " instances)"
            )

    return placed_insts


def _get_and_place_insts_and_ports(
    c: KCell,
    placed_insts: set[str],
    placed_ports: set[str],
    connections: dict[str, list[Connection[TUnit]]],
    schematic: TSchematic[TUnit],
    instances: dict[str, Instance | VInstance],
    placed_island_insts: set[str],
    cross_sections: dict[str, CrossSection | DCrossSection],
) -> bool:
    placeable_insts, placeable_ports = _get_placeable(
        placed_insts=placed_insts,
        connections=connections,
        placed_ports=placed_ports,
        schematic=schematic,
    )

    _connect_instances(
        instances=instances,
        place_insts=placeable_insts,
        connections=connections,
        placed_instances=placed_insts,
    )
    for port in placeable_ports:
        schematic.ports[port].place(
            cell=c, schematic=schematic, name=port, cross_sections=cross_sections
        )
        placed_ports.add(port)
    placed_insts |= placeable_insts
    placed_island_insts |= placeable_insts

    return bool(placeable_insts) or bool(placeable_ports)


def _connect_instances(
    instances: dict[str, Instance | VInstance],
    place_insts: set[str],
    connections: dict[str, list[Connection[TUnit]]],
    placed_instances: set[str],
) -> None:
    for inst_name in place_insts:
        inst = instances[inst_name]
        for conn in connections[inst_name]:
            if isinstance(conn.root[0], Port):
                continue
            if (
                conn.root[0].instance == inst_name
                and conn.root[1].instance in placed_instances
            ):
                inst.connect(
                    conn.root[0].port,
                    instances[conn.root[1].instance],
                    conn.root[1].port,
                    use_angle=True,
                    use_mirror=False,
                )
                break
            if conn.root[0].instance in placed_instances:
                inst.connect(
                    conn.root[1].port,
                    instances[conn.root[0].instance],
                    conn.root[0].port,
                    use_angle=True,
                    use_mirror=False,
                )
                break
        else:
            raise ValueError("Could not connect all instances")


def _get_placeable(
    placed_insts: set[str],
    connections: dict[str, list[Connection[TUnit]]],
    placed_ports: set[str],
    schematic: TSchematic[TUnit],
) -> tuple[set[str], set[str]]:
    placeable_insts: set[str] = set()
    placeable_ports: set[str] = set()
    for inst in placed_insts:
        for connection in connections[inst]:
            ref1, ref2 = connection.root
            if isinstance(ref1, Port):
                if ref1 in placed_ports:
                    placeable_insts.add(ref2.instance)
            else:
                placeable_insts |= {ref1.instance, ref2.instance}
    for name, port in schematic.ports.items():
        if name in placed_ports:
            continue
        if isinstance(port, Port):
            add_port = True
            if isinstance(port.x, PortRef) and port.x.instance not in placed_insts:
                add_port = False
            if isinstance(port.y, PortRef) and port.y.instance not in placed_insts:
                add_port = False
            if add_port:
                placeable_ports.add(port.name)
        elif isinstance(port, PortRef) and name not in placed_ports:
            if port.instance in placed_insts:
                placeable_ports.add(name)
    return placeable_insts - placed_insts, placeable_ports


@overload
def get_schematic(
    c: KCell,
    exclude_port_types: Sequence[str] | None = ("placement", "pad", "bump"),
) -> TSchematic[int]: ...


@overload
def get_schematic(
    c: DKCell,
    exclude_port_types: Sequence[str] | None = ("placement", "pad", "bump"),
) -> TSchematic[float]: ...


def get_schematic(
    c: KCell | DKCell,
    exclude_port_types: Sequence[str] | None = ("placement", "pad", "bump"),
) -> TSchematic[int] | TSchematic[float]:
    if isinstance(c, KCell):
        schematic: TSchematic[int] | TSchematic[float] = Schematic(name=c.name)
    else:
        schematic = DSchematic(name=c.name)

    for inst in c.insts:
        name = inst.property(PROPID.NAME)
        if name is not None:
            schematic.create_inst(name, inst.cell.factory_name or inst.cell.name)

    return schematic


@overload
def read_schematic(file: Path | str, unit: Literal["dbu"] = "dbu") -> Schematic: ...


@overload
def read_schematic(file: Path | str, unit: Literal["um"]) -> DSchematic: ...


def read_schematic(
    file: Path | str, unit: Literal["dbu", "um"] = "dbu"
) -> Schematic | DSchematic:
    file = Path(file).resolve()
    if not file.is_file():
        raise ValueError(f"{file=} is either not a file or does not exist.")
    with file.open(mode="rt") as f:
        yaml_dict = yaml.load(f)
        if unit == "dbu":
            return Schematic.model_validate(yaml_dict, strict=True)
        return DSchematic.model_validate(yaml_dict)


TSchematic[Annotated[int, str]].model_rebuild()
TSchematic[Annotated[float, str]].model_rebuild()
SchematicInstance.model_rebuild()
