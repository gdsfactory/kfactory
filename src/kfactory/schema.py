from __future__ import annotations

import re
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
    RootModel,
    field_validator,
    model_validator,
)
from ruamel.yaml import YAML
from typing_extensions import TypeAliasType

from .conf import PROPID
from .kcell import DKCell, KCell
from .layout import KCLayout, kcls
from .typings import TUnit, dbu, um

if TYPE_CHECKING:
    from collections.abc import Sequence

yaml = YAML(typ="safe")

JSON_Serializable = TypeAliasType(
    "JSON_Serializable",
    "int | float| bool | str | list[JSON_Serializable] | tuple[JSON_Serializable, ...]"
    " | dict[str, JSON_Serializable]| None",
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


CellConfig = RootModel[dict[str, JSON_Serializable]]


class SchemaInstance(
    BaseModel, Generic[TUnit], extra="forbid", arbitrary_types_allowed=True
):
    name: str = Field(exclude=True)
    kcl: KCLayout = Field(exclude=True, default="DEFAULT")  # type: ignore[assignment]
    component: str
    settings: CellConfig | None = None
    info: CellConfig | None = None
    array: RegularArray[TUnit] | Array[TUnit] | None = None

    @field_validator("kcl", mode="before")
    @classmethod
    def _find_kcl(cls, value: str | KCLayout) -> KCLayout:
        if isinstance(value, str):
            return kcls[value]
        return value


class Route(BaseModel, extra="forbid"):
    name: str = Field(exclude=True)
    links: list[Link]
    routing_strategy: str | None = None
    settings: dict[str, JSON_Serializable]

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


class Port(BaseModel, Generic[TUnit], extra="forbid"):
    name: str = Field(exclude=True)
    x: TUnit | PortRef | PortArrayRef
    y: TUnit | PortRef | PortArrayRef
    dx: TUnit = cast("TUnit", 0)
    dy: TUnit = cast("TUnit", 0)


class Net(RootModel[list[PortArrayRef | PortRef]]):
    root: list[PortArrayRef | PortRef]


class Link(RootModel[tuple[PortArrayRef | PortRef, PortArrayRef | PortRef]]):
    root: tuple[PortArrayRef | PortRef, PortArrayRef | PortRef]


class Connection(BaseModel, extra="forbid"):
    p1: PortArrayRef | PortRef
    p2: PortArrayRef | PortRef

    @classmethod
    def from_list(cls, data: Any) -> Connection:
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
    nets: list[Net]
    ports: dict[str, Port[TUnit]] | None = None


class TSchema(BaseModel, Generic[TUnit], extra="forbid"):
    name: str | None = None
    dependencies: list[Path] = Field(default_factory=list)
    instances: dict[str, SchemaInstance[TUnit]] = Field(default_factory=dict)
    placements: dict[str, Placement[TUnit]] = Field(default_factory=dict)
    connections: list[Connection] = Field(default_factory=list)
    routes: dict[str, Route] = Field(default_factory=dict)
    ports: dict[str, Port[TUnit]] = Field(default_factory=dict)

    def create_inst(
        self,
        name: str,
        component: str,
        settings: CellConfig | None = None,
        info: CellConfig | None = None,
        array: RegularArray[TUnit] | Array[TUnit] | None = None,
    ) -> SchemaInstance[TUnit]:
        inst = SchemaInstance[TUnit].model_validate(
            {
                "name": name,
                "component": component,
                "settings": settings,
                "info": info,
                "array": array,
            }
        )

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

    def create_connection(self, port1: PortRef, port2: PortRef) -> Connection:
        conn = Connection(p1=port1, p2=port2)
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
                [Net([connection.p1, connection.p2]) for connection in self.connections]
            )

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
            built_connections: list[Connection] = []
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
