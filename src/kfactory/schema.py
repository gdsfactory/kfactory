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
    TypeAlias,
    cast,
    overload,
)

from pydantic import (
    AfterValidator,
    BaseModel,
    Field,
    PrivateAttr,
    RootModel,
    field_validator,
    model_validator,
)
from ruamel.yaml import YAML
from typing_extensions import TypeAliasType

from . import kdb
from .conf import PROPID
from .kcell import DKCell, KCell, ProtoTKCell
from .layout import KCLayout, get_default_kcl, kcls
from .typings import TUnit, dbu, um

if TYPE_CHECKING:
    from collections.abc import Sequence

    from .instance import ProtoTInstance

yaml = YAML(typ="safe")

JSONSerializable = TypeAliasType(
    "JSONSerializable",
    "int | float| bool | str | list[JSONSerializable] | tuple[JSONSerializable, ...]"
    " | dict[str, JSONSerializable]| None",
)


def _gez(value: TUnit) -> TUnit:
    if value < 0:
        raise ValueError(
            "x of pitch_a and y of pitch_b must be greater or equal to zero."
        )
    return value


class Placement(BaseModel, Generic[TUnit], extra="forbid"):
    x: TUnit | PortRef | PortArrayRef = cast("TUnit", 0)
    dx: TUnit = cast("TUnit", 0)
    y: TUnit | PortRef | PortArrayRef = cast("TUnit", 0)
    dy: TUnit = cast("TUnit", 0)
    orientation: Literal[0, 90, 180, 270] = 0
    mirror: bool = False

    @model_validator(mode="after")
    def _require_absolute_or_relative(self) -> Self:
        if self.x is None and self.dx is None:
            raise ValueError("Either x or dx must be defined.")
        if self.y is None and self.dy is None:
            raise ValueError("Either y or dy must be defined.")

        return self

    @property
    def is_absolute(self) -> bool:
        return not (isinstance(self.x, str) or isinstance(self.y, str))


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


CellConfig = RootModel[dict[str, JSONSerializable]]


class SchemaInstance(
    BaseModel, Generic[TUnit], extra="forbid", arbitrary_types_allowed=True
):
    name: str = Field(exclude=True)
    component: str
    settings: CellConfig | None = None
    info: CellConfig | None = None
    array: RegularArray[TUnit] | Array[TUnit] | None = None
    kcl: KCLayout = Field(exclude=True, default_factory=get_default_kcl)
    _schema: TSchema[TUnit] = PrivateAttr()

    @field_validator("kcl", mode="before")
    @classmethod
    def _find_kcl(cls, value: str | KCLayout) -> KCLayout:
        if isinstance(value, str):
            return kcls[value]
        return value

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
    links: list[Link[TUnit]]
    routing_strategy: str | None = None
    settings: dict[str, JSONSerializable]

    @model_validator(mode="before")
    @classmethod
    def _parse_links(cls, data: dict[str, Any]) -> dict[str, Any]:
        links = data.get("links", [])

        if isinstance(links, dict):
            data["links"] = [
                [tuple(k.split(",")), tuple(v.split(","))] for k, v in links.items()
            ]
        return data


class PortRef(BaseModel, extra="forbid"):
    instance: str
    port: str

    @model_validator(mode="before")
    @classmethod
    def _validate_portref(cls, data: dict[str, Any]) -> dict[str, Any]:
        if isinstance(data, str):
            data = tuple(data.rsplit(",", 1))
        if isinstance(data, tuple):
            return {"instance": data[0], "port": data[1]}
        return data

    def __lt__(self, other: PortRef | PortArrayRef | Port[Any]) -> bool:
        if isinstance(other, Port):
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

    def __lt__(self, other: PortRef | Port[Any] | PortArrayRef) -> bool:
        if isinstance(other, Port[Any] | PortRef):
            return False
        return (self.instance, self.port, self.ia, self.ib) < (
            other.instance,
            other.port,
            other.ia,
            other.ib,
        )


class Port(BaseModel, Generic[TUnit], extra="forbid"):
    name: str = Field(exclude=True)
    x: TUnit | PortRef | PortArrayRef
    y: TUnit | PortRef | PortArrayRef
    dx: TUnit = cast("TUnit", 0)
    dy: TUnit = cast("TUnit", 0)

    def __lt__(self, other: Port[Any] | PortRef) -> bool:
        if isinstance(other, Port):
            return (self.name, self.x, self.y, self.dx, self.dy) < (
                other.name,
                other.x,
                other.y,
                other.dx,
                other.dy,
            )
        return True


class Net(RootModel[list[PortArrayRef | PortRef | Port[TUnit]]]):
    root: list[PortArrayRef | PortRef | Port[TUnit]]

    def sort(self) -> Self:
        def _port_sort(port: PortRef | Port[Any]) -> tuple[Any, ...]:
            if isinstance(port, PortRef):
                return (port.instance, port.port)
            return (port.name,)

        self.root.sort(key=_port_sort)
        return self

    def __lt__(self, other: Net[Any]) -> bool:
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


class Link(
    RootModel[
        tuple[
            Port[TUnit] | PortArrayRef | PortRef, Port[TUnit] | PortArrayRef | PortRef
        ]
    ]
):
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
    def from_list(cls, data: Any) -> Connection[TUnit]:
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


class TNetlist(BaseModel, Generic[TUnit], extra="forbid"):
    name: str | None = None
    instances: dict[str, SchemaInstance[TUnit]] | None = None
    nets: list[Net[TUnit]]
    ports: dict[str, Port[TUnit]] | None = None

    def sort(self) -> Self:
        if self.instances:
            self.instances = dict(sorted(self.instances.items()))
        self.nets.sort()
        if self.ports:
            self.ports = {p.name: p for p in self.ports.values()}
        return self


class TSchema(BaseModel, Generic[TUnit], extra="forbid"):
    name: str | None = None
    dependencies: list[Path] = Field(default_factory=list)
    instances: dict[str, SchemaInstance[TUnit]] = Field(default_factory=dict)
    placements: dict[str, Placement[TUnit]] = Field(default_factory=dict)
    connections: list[Connection[TUnit]] = Field(default_factory=list)
    routes: dict[str, Route[TUnit]] = Field(default_factory=dict)
    ports: dict[str, Port[TUnit]] = Field(default_factory=dict)
    kcl: KCLayout = Field(exclude=True, default_factory=get_default_kcl)

    def create_inst(
        self,
        name: str,
        component: str,
        settings: CellConfig | None = None,
        info: JSONSerializable | None = None,
        array: RegularArray[TUnit] | Array[TUnit] | None = None,
        placement: Placement[TUnit] | None = None,
        kcl: KCLayout | None = None,
    ) -> SchemaInstance[TUnit]:
        inst = SchemaInstance[TUnit].model_validate(
            {
                "name": name,
                "component": component,
                "settings": settings,
                "info": info,
                "array": array,
                "kcl": kcl or self.kcl,
            }
        )
        inst._schema = self

        self.instances[inst.name] = inst
        return inst

    def add_port(self, name: str, port_ref: PortRef | PortArrayRef) -> Port[TUnit]:
        if name not in self.ports:
            p = Port[TUnit](name=name, x=port_ref, y=port_ref)
            self.ports[name] = p
            return p
        raise ValueError(f"Port with name {name} already exists")

    def create_port(
        self,
        name: str,
        x: PortRef | PortArrayRef | TUnit,
        y: PortRef | PortArrayRef | TUnit,
        dx: TUnit = 0,
        dy: TUnit = 0,
    ) -> Port[TUnit]:
        p = Port(name=name, x=x, y=y, dx=dx, dy=dy)
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

    def netlist(self) -> TNetlist[TUnit]:
        nets: list[Net[TUnit]] = []
        if self.routes is not None:
            nets.extend(
                [
                    Net(list(link.root))
                    for route in self.routes.values()
                    for link in route.links
                ]
            )
        if self.connections:
            nets.extend([Net(list(connection.root)) for connection in self.connections])

        return TNetlist[TUnit](
            name=self.name,
            instances=self.instances.copy() if self.instances else None,
            nets=nets,
            ports=self.ports.copy() if self.ports else None,
        )

    @model_validator(mode="before")
    @classmethod
    def _validate_model(cls, data: dict[str, Any]) -> dict[str, Any]:
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
        if connections and isinstance(connections, dict):
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

    def create_cell(self, output_type: type[ProtoTKCell[TUnit]]) -> ProtoTKCell[TUnit]:
        c = output_type()

        instances: dict[str, ProtoTInstance[TUnit]] = {}

        for inst in self.instances.values():
            if inst.settings:
                inst_ = c.create_inst(
                    inst.kcl.get_component(inst.component, **inst.settings.root)
                )
            else:
                inst_ = c.create_inst(inst.kcl.get_component(inst.component))

            inst_.name = inst.name
            instances[inst.name] = inst_

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
        placed_islands: list[set[str]] = []
        for island in islands.values():
            if island not in placed_islands:
                _place_islands(
                    c, island, instances, instance_connections, self.instances
                )
                placed_islands.append(island)

        return c


def _place_islands(
    c: ProtoTKCell[TUnit],
    schema_island: set[str],
    instances: dict[str, ProtoTInstance[TUnit]],
    connections: dict[str, list[Connection[TUnit]]],
    schema_instances: dict[str, SchemaInstance[TUnit]],
) -> None:
    target_length = len(schema_island)
    placed_insts: set[str] = set()

    placable_insts: set[str] = set()

    for inst in schema_island:
        schema_inst = schema_instances[inst]
        kinst = instances[inst]
        if schema_inst.placement:
            p = schema_inst.placement
            if isinstance(p.x, PortRef) or isinstance(p.y, PortRef):
                # TODO @sebastian: needs to properly check whether port placed and available
                continue
            st = kinst._standard_trans()
            if isinstance(st, kdb.Trans | kdb.ICplxTrans):
                kinst.transform(
                    kdb.ICplxTrans(
                        mag=1,
                        rot=p.orientation,
                        mirrx=p.mirror,
                        x=p.x + p.dx,
                        y=p.y + p.dy,
                    )
                )
            else:
                kinst.transform(
                    kdb.DCplxTrans(
                        mag=1,
                        rot=p.orientation,
                        mirrx=p.mirror,
                        x=p.x + p.dx,
                        y=p.y + p.dy,
                    )
                )
            placed_insts.add(inst)

    while len(placed_insts) < target_length:
        placable_insts = _get_placable(placed_insts, connections)

        _connect_instances(instances, placable_insts, connections, placed_insts)
        placed_insts |= placable_insts

        if not placable_insts:
            raise ValueError("Could not place all instances.")


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
                )
                break
            if conn.root[0].instance in placed_instances:
                inst.connect(
                    conn.root[1].port,
                    instances[conn.root[0].instance],
                    conn.root[0].port,
                )
                break
        else:
            raise ValueError("Could not connect all instances")


def _get_placable(
    placed_insts: set[str], connections: dict[str, list[Connection[TUnit]]]
) -> set[str]:
    placable_insts: set[str] = set()
    for inst in placed_insts:
        for connection in connections[inst]:
            ref1, ref2 = connection.root
            if isinstance(ref1, Port):
                placable_insts.add(ref2.instance)
            else:
                placable_insts |= {ref1.instance, ref2.instance}
    return placable_insts - placed_insts


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
            return TSchema[int].model_validate(yaml_dict, strict=True)
        return TSchema[float].model_validate(yaml_dict)


TSchema[Annotated[int, str]].model_rebuild()
TSchema[Annotated[float, str]].model_rebuild()
SchemaInstance.model_rebuild()
Schema: TypeAlias = TSchema[dbu]
DSchema: TypeAlias = TSchema[um]
