"""This is still experimental.

Caution is advised when using this, as the API might suddenly change.
In order to fix bugs etc.
"""

from __future__ import annotations

import re
from collections import defaultdict
from pathlib import Path
from typing import (
    TYPE_CHECKING,
    Annotated,
    Any,
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
from .conf import PROPID
from .kcell import DKCell, KCell, ProtoTKCell
from .layout import KCLayout, get_default_kcl, kcls
from .netlist import Net, Netlist, NetlistInstance, NetlistPort, PortArrayRef, PortRef
from .typings import KC, JSONSerializable, TUnit, dbu, um

if TYPE_CHECKING:
    from collections.abc import Sequence

    from .instance import DInstance, Instance, ProtoTInstance
    from .port import ProtoPort

yaml = YAML(typ="safe")

__all__ = ["DSchema", "Schema", "read_schema"]


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
    orientation: Literal[0, 90, 180, 270] = 0

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
            orientation = data.pop("rotation")
            data["orientation"] = orientation
        return data

    @property
    def is_absolute(self) -> bool:
        return not (isinstance(self.x, str) or isinstance(self.y, str))

    def is_placeable(self, placed_instances: set[str]) -> bool:
        placeable = True
        if isinstance(self.x, PortRef):
            placeable = self.x.instance in placed_instances
        if isinstance(self.y, PortRef):
            placeable = placeable and self.y.instance in placed_instances
        return placeable


class RegularArray(BaseModel, Generic[TUnit], extra="forbid"):
    columns: int = Field(gt=0, default=1)
    column_pitch: TUnit
    rows: int = Field(gt=0, default=1)
    row_pitch: TUnit


class Array(BaseModel, Generic[TUnit], extra="forbid"):
    na: int = Field(gt=1, default=1)
    nb: int = Field(gt=0, default=1)
    pitch_a: tuple[Annotated[TUnit, AfterValidator(_gez)], TUnit]
    pitch_b: tuple[TUnit, Annotated[TUnit, AfterValidator(_gez)]]


class Ports(BaseModel, Generic[TUnit]):
    instance: SchemaInstance[TUnit]

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


class SchemaInstance(
    BaseModel, Generic[TUnit], extra="forbid", arbitrary_types_allowed=True
):
    name: str = Field(exclude=True)
    component: str
    settings: dict[str, JSONSerializable] = Field(default_factory=dict)
    array: RegularArray[TUnit] | Array[TUnit] | None = None
    kcl: KCLayout = Field(default_factory=get_default_kcl)
    _schema: TSchema[TUnit] = PrivateAttr()

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
    def parent_schema(self) -> TSchema[TUnit]:
        if self._schema is None:
            raise RuntimeError("Schema instance has no parent set.")
        return self._schema

    @property
    def placement(self) -> Placement[TUnit] | None:
        return self.parent_schema.placements.get(self.name)

    def place(
        self,
        x: TUnit | PortRef = 0,
        y: TUnit | PortRef = 0,
        dx: TUnit = 0,
        dy: TUnit = 0,
        orientation: Literal[0, 90, 180, 270] = 0,
        mirror: bool = False,
    ) -> Placement[TUnit]:
        placement = Placement[TUnit](
            x=x, y=y, dx=dx, dy=dy, orientation=orientation, mirror=mirror
        )
        self.parent_schema.placements[self.name] = placement
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
        self, port: str | tuple[str, int, int], other: Port[TUnit] | PortRef
    ) -> Connection[TUnit]:
        if isinstance(port, str):
            pref = PortRef(instance=self.name, port=port)
        else:
            pref = PortArrayRef(
                instance=self.name, port=port[0], ia=port[1], ib=port[2]
            )
        conn = Connection[TUnit]((other, pref))
        self.parent_schema.connections.append(conn)
        return conn


class Route(BaseModel, Generic[TUnit], extra="forbid"):
    name: str = Field(exclude=True)
    links: list[Link]
    routing_strategy: str = "route_bundle"
    settings: dict[str, JSONSerializable]

    @model_validator(mode="before")
    @classmethod
    def _parse_links(cls, data: dict[str, Any]) -> dict[str, Any]:
        links = cast("dict[str, str]| None", data.get("links"))

        if isinstance(links, dict):
            data["links"] = [
                [tuple(str(k).split(",")), tuple(str(v).split(","))]
                for k, v in links.items()
            ]
        return data


class Port(BaseModel, Generic[TUnit], extra="forbid"):
    name: str = Field(exclude=True)
    x: TUnit | PortRef | PortArrayRef
    y: TUnit | PortRef | PortArrayRef
    dx: TUnit = cast("TUnit", 0)
    dy: TUnit = cast("TUnit", 0)
    cross_section: str
    orientation: Literal[0, 90, 180, 270]

    def __lt__(self, other: Port[Any] | PortRef) -> bool:
        if isinstance(other, Port):
            return self._as_tuple() < other._as_tuple()
        return True

    def _as_tuple(
        self,
    ) -> tuple[
        str,
        TUnit | PortRef | PortArrayRef,
        TUnit | PortRef | PortArrayRef,
        TUnit,
        TUnit,
        Literal[0, 90, 180, 270],
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
        return placeable


class Link(RootModel[tuple[PortArrayRef | PortRef, PortArrayRef | PortRef]]):
    root: tuple[PortArrayRef | PortRef, PortArrayRef | PortRef]

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

            return Connection.model_validate({"p1": p1, "p2": p2})
        return Connection(**data)


class TSchema(BaseModel, Generic[TUnit], extra="forbid"):
    name: str | None = None
    dependencies: list[Path] = Field(default_factory=list)
    instances: dict[str, SchemaInstance[TUnit]] = Field(default_factory=dict)
    placements: dict[str, Placement[TUnit]] = Field(default_factory=dict)
    connections: list[Connection[TUnit]] = Field(default_factory=list)
    routes: dict[str, Route[TUnit]] = Field(default_factory=dict)
    ports: dict[str, Port[TUnit] | PortRef | PortArrayRef] = Field(default_factory=dict)
    kcl: KCLayout = Field(exclude=True, default_factory=get_default_kcl)

    def create_inst(
        self,
        name: str,
        component: str,
        settings: dict[str, JSONSerializable] | None = None,
        array: RegularArray[TUnit] | Array[TUnit] | None = None,
        placement: Placement[TUnit] | None = None,
        kcl: KCLayout | None = None,
    ) -> SchemaInstance[TUnit]:
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
            Schema instance representing the args.
        """
        inst = SchemaInstance[TUnit].model_validate(
            {
                "name": name,
                "component": component,
                "settings": settings or {},
                "array": array,
                "kcl": kcl or self.kcl,
            }
        )
        inst._schema = self

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
                    Net(list(link.root))
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
    def _validate_model(cls, data: dict[str, Any]) -> dict[str, Any]:
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
            inst._schema = self
        return self

    def create_cell(self, output_type: type[KC]) -> KC:
        c = output_type(kcl=self.kcl)

        instances: dict[str, ProtoTInstance[Any]] = {}

        inst_: Instance | DInstance

        # create instances
        for inst in self.instances.values():
            vec_class = kdb.Vector if isinstance(c, KCell) else kdb.DVector
            if inst.array:
                if isinstance(inst.array, RegularArray):
                    a = vec_class(x=inst.array.column_pitch, y=0)  # type: ignore[call-overload]
                    b = vec_class(x=0, y=inst.array.row_pitch)  # type: ignore[call-overload]
                    na = inst.array.columns
                    nb = inst.array.rows
                else:
                    a = vec_class(*inst.array.pitch_a)  # type: ignore[call-overload]
                    b = vec_class(*inst.array.pitch_b)  # type: ignore[call-overload]
                    na = inst.array.na
                    nb = inst.array.nb
                if inst.settings:
                    inst_ = c.create_inst(
                        inst.kcl.get_component(inst.component, **inst.settings),
                        a=a,  # type: ignore[arg-type]
                        b=b,  # type: ignore[arg-type]
                        na=na,
                        nb=nb,
                    )
                else:
                    inst_ = c.create_inst(
                        inst.kcl.get_component(inst.component),
                        a=a,  # type: ignore[arg-type]
                        b=b,  # type: ignore[arg-type]
                        na=na,
                        nb=nb,
                    )
            elif inst.settings:
                inst_ = c.create_inst(
                    inst.kcl.get_component(inst.component, **inst.settings)
                )
            else:
                inst_ = c.create_inst(inst.kcl.get_component(inst.component))

            inst_.name = inst.name
            instances[inst.name] = inst_

        # calculate islands -- islands are a bunch of directly connected instances and
        # must be isolated from other islands either through no connection at all or
        # routes
        islands: dict[str, set[str]] = {}
        instance_connections: defaultdict[str, list[Connection[TUnit]]] = defaultdict(
            list
        )

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
            if inst.name not in islands:
                islands[inst_name] = {inst_name}
        placed_islands: list[set[str]] = []
        placed_insts: set[str] = set()
        for island in islands.values():
            if island not in placed_islands:
                _place_islands(
                    c,
                    island,
                    instances,
                    instance_connections,
                    self.instances,
                    placed_insts,
                )
                placed_islands.append(island)
                placed_insts |= island

        # ports
        for name, port in self.ports.items():
            if isinstance(port, Port):
                if isinstance(port.x, PortArrayRef):
                    ref = port.x
                    port.x = c.insts[ref.instance].ports[ref.port, ref.ia, ref.ib].x
                elif isinstance(port.x, PortRef):
                    port.x = c.insts[ref.instance].ports[ref.port].x
                if isinstance(port.y, PortArrayRef):
                    ref = port.y
                    port.y = c.insts[ref.instance].ports[ref.port, ref.ia, ref.ib].y
                elif isinstance(port.y, PortRef):
                    port.y = c.insts[ref.instance].ports[ref.port].y

                p = c.create_port(
                    name=port.name,
                    center=(port.x, port.y),
                    cross_section=c.get_cross_section(
                        c.kcl.get_symmetrical_cross_section(port.cross_section)
                    ),
                )
                p.orientation = port.orientation
            else:
                c.add_port(port=c.insts[port.instance].ports[port.port], name=name)
        # routes
        for route in self.routes.values():
            start_ports: list[ProtoPort[Any]] = []
            end_ports: list[ProtoPort[Any]] = []
            for link in route.links:
                l1, l2 = link.root[0], link.root[1]
                if isinstance(l1, PortRef):
                    p1 = c.insts[l1.instance].ports[l1.port]
                else:
                    p1 = c.insts[l1.instance].ports[l1.port, l1.ia, l1.ib]
                start_ports.append(p1)
                if isinstance(l2, PortRef):
                    p2 = c.insts[l2.instance].ports[l2.port]
                else:
                    p2 = c.insts[l2.instance].ports[l2.port, l2.ia, l2.ib]
                end_ports.append(p2)
            self.kcl.routing_strategies[route.routing_strategy](
                c, start_ports, end_ports, **route.settings
            )

        # verify connections
        port_connection_errors: list[Connection[TUnit]] = []
        connection_errors: list[Connection[TUnit]] = []
        for conn in self.connections:
            c1 = conn.root[0]
            c2 = conn.root[1]
            if isinstance(c1, Port):
                p1 = c.ports[c1.name]
                p2 = c.insts[c2.instance].ports[c2.port]
                if p1.dcplx_trans != p2.dcplx_trans:
                    port_connection_errors.append(conn)
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
                if t1 * kdb.DCplxTrans.R180 != t2 or t1 * kdb.DCplxTrans.M90:
                    connection_errors.append(conn)

        return c

    def add_route(
        self,
        name: str,
        start_ports: list[PortRef],
        end_ports: list[PortRef],
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


class Schema(TSchema[dbu]):
    """Schema with a base unit of dbu for placements."""


class DSchema(TSchema[um]):
    """Schema with a base unit of um for placements."""


def _place_islands(
    c: ProtoTKCell[TUnit],
    schema_island: set[str],
    instances: dict[str, ProtoTInstance[TUnit]],
    connections: dict[str, list[Connection[TUnit]]],
    schema_instances: dict[str, SchemaInstance[TUnit]],
    placed_insts: set[str],
) -> set[str]:
    target_length = len(schema_island)

    placeable_insts: set[str] = set()

    for inst in schema_island:
        schema_inst = schema_instances[inst]
        kinst = instances[inst]
        if schema_inst.placement:
            p = schema_inst.placement
            assert p is not None
            if p.is_placeable(placed_insts):
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
                    kinst.transform(
                        kdb.ICplxTrans(
                            mag=1,
                            rot=p.orientation,
                            mirrx=p.mirror,
                            x=x + p.dx,
                            y=y + p.dy,
                        )  # type: ignore[call-overload]
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
                    )
            placed_insts.add(inst)

    while len(placed_insts) < target_length:
        placeable_insts = _get_placeable(placed_insts, connections)

        _connect_instances(instances, placeable_insts, connections, placed_insts)
        placed_insts |= placeable_insts

        if not placeable_insts:
            raise ValueError("Could not place all instances.")

    return placed_insts


def _connect_instances(
    instances: dict[str, ProtoTInstance[TUnit]],
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
    placed_insts: set[str], connections: dict[str, list[Connection[TUnit]]]
) -> set[str]:
    placeable_insts: set[str] = set()
    for inst in placed_insts:
        for connection in connections[inst]:
            ref1, ref2 = connection.root
            if isinstance(ref1, Port):
                placeable_insts.add(ref2.instance)
            else:
                placeable_insts |= {ref1.instance, ref2.instance}
    return placeable_insts - placed_insts


@overload
def get_schema(
    c: KCell,
    exclude_port_types: Sequence[str] | None = ("placement", "pad", "bump"),
) -> TSchema[int]: ...


@overload
def get_schema(
    c: DKCell,
    exclude_port_types: Sequence[str] | None = ("placement", "pad", "bump"),
) -> TSchema[float]: ...


def get_schema(
    c: KCell | DKCell,
    exclude_port_types: Sequence[str] | None = ("placement", "pad", "bump"),
) -> TSchema[int] | TSchema[float]:
    if isinstance(c, KCell):
        schema: TSchema[int] | TSchema[float] = Schema(name=c.name)
    else:
        schema = DSchema(name=c.name)

    for inst in c.insts:
        name = inst.property(PROPID.NAME)
        if name is not None:
            schema.create_inst(name, inst.cell.factory_name or inst.cell.name)

    return schema


@overload
def read_schema(file: Path | str, unit: Literal["dbu"] = "dbu") -> Schema: ...


@overload
def read_schema(file: Path | str, unit: Literal["um"]) -> DSchema: ...


def read_schema(
    file: Path | str, unit: Literal["dbu", "um"] = "dbu"
) -> Schema | DSchema:
    file = Path(file).resolve()
    if not file.is_file():
        raise ValueError(f"{file=} is either not a file or does not exist.")
    with file.open(mode="rt") as f:
        yaml_dict = yaml.load(f)
        if unit == "dbu":
            return Schema.model_validate(yaml_dict, strict=True)
        return DSchema.model_validate(yaml_dict)


TSchema[Annotated[int, str]].model_rebuild()
TSchema[Annotated[float, str]].model_rebuild()
SchemaInstance.model_rebuild()
