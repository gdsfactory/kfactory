from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import (
    Annotated,
    Any,
    Generic,
    Literal,
    Self,
    TypeAlias,
    overload,
)
import re

from pydantic import BaseModel, Field, RootModel, model_validator
from ruamel.yaml import YAML
from typing_extensions import TypeAliasType

from .kcell import DKCell, KCell
from .typings import TUnit, dbu, um

yaml = YAML(typ="safe")

JSON_Serializable = TypeAliasType(
    "JSON_Serializable",
    "int | float| bool | str | list[JSON_Serializable] | tuple[JSON_Serializable, ...]"
    " | dict[str, JSON_Serializable]| None",
)


class Placement(BaseModel, Generic[TUnit]):
    port: str | None = None
    x: TUnit | None = None
    dx: TUnit | None = None
    y: TUnit | None = None
    dy: TUnit | None = None
    rotation: Literal[0, 90, 180, 270] | None = None
    mirror: str | bool | None = None

    @model_validator(mode="after")
    def _require_absolute_or_relative(self) -> Self:
        if self.x is None and self.dx is None:
            raise ValueError("Either x or dx must be defined.")
        if self.y is None and self.dy is None:
            raise ValueError("Either y or dy must be defined.")

        return self


class RegularArray(Placement[TUnit]):
    columns: int = Field(gt=0, default=1)
    rows: int = Field(gt=0, default=1)
    column_pitch: TUnit
    row_pitch: TUnit


class Array(Placement[TUnit]):
    na: int = Field(gt=1, default=1)
    nb: int = Field(gt=0, default=1)
    pitch_a: tuple[TUnit, TUnit]
    pitch_b: tuple[TUnit, TUnit]


CellSettings = RootModel[dict[str, JSON_Serializable]]


class NetlistInstance(BaseModel, Generic[TUnit]):
    settings: CellSettings | None = None
    array: RegularArray[TUnit] | Array[TUnit] | None = None


class Route(BaseModel, Generic[TUnit]):
    links: list[list[tuple[str, str]]]
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


class PortRef(BaseModel):
    instance: str
    port_name: str


class PortArrayRef(PortRef):
    ia: int
    ib: int


class Connection(BaseModel):
    p1: PortRef | PortArrayRef
    p2: PortRef | PortArrayRef

    @classmethod
    def from_list(cls, data: Any) -> Connection:
        if isinstance(data, list | tuple):
            if isinstance(data[0][0], list | tuple):
                p1 = {
                    "instance": data[0][0][0],
                    "port_name": data[0][1],
                    "ia": data[0][0][1][0],
                    "ib": data[0][0][1][1],
                }
            else:
                p1 = {"instance": data[0][0], "port_name": data[0][1]}
            if isinstance(data[1][0], list | tuple):
                p2 = {
                    "instance": data[1][0][0],
                    "port_name": data[1][1],
                    "ia": data[1][0][1][0],
                    "ib": data[1][0][1][1],
                }
            else:
                p2 = {"instance": data[1][0], "port_name": data[1][1]}

            return Connection.model_validate({"p1": p1, "p2": p2})
        return Connection(**data)


class TNetlist(BaseModel, Generic[TUnit]):
    name: str | None = None
    dependencies: list[Path] = Field(default_factory=list)
    instances: dict[str, NetlistInstance[TUnit]] | None = None
    placements: (
        dict[
            str,
            Array[TUnit] | RegularArray[TUnit] | Placement[TUnit],
        ]
        | None
    ) = None
    nets: list[tuple[NetlistInstance[TUnit], str]] | None = None
    connections: list[Connection] | None = None
    routes: dict[str, Route[TUnit]] | None = None

    @model_validator(mode="before")
    @classmethod
    def _validate_model(cls, data: dict[str, Any]) -> dict[str, Any]:
        connections = data.get("connections")
        if connections and isinstance(connections, dict):
            built_connections: list[Connection] = []
            connections_: list[tuple[tuple[str, str], tuple[str, str]]] = [
                (k.rsplit(",", 1), v.rsplit(",", 1)) for k, v in connections.items()
            ]
            for i, connection_ in enumerate(connections_):
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


Netlist: TypeAlias = TNetlist[dbu]
DNetlist: TypeAlias = TNetlist[um]


@overload
def get_netlist(
    c: KCell,
    exclude_port_types: Sequence[str] | None = ("placement", "pad", "bump"),
) -> TNetlist[int]: ...


@overload
def get_netlist(
    c: DKCell,
    exclude_port_types: Sequence[str] | None = ("placement", "pad", "bump"),
) -> TNetlist[float]: ...


def get_netlist(
    c: KCell | DKCell,
    exclude_port_types: Sequence[str] | None = ("placement", "pad", "bump"),
) -> TNetlist[int] | TNetlist[float]:
    return Netlist(name=c.name) if isinstance(c, KCell) else DNetlist(name=c.name)


@overload
def read_netlist(file: Path | str, unit: Literal["dbu"] = "dbu") -> Netlist: ...


@overload
def read_netlist(file: Path | str, unit: Literal["um"]) -> DNetlist: ...


def read_netlist(
    file: Path | str, unit: Literal["dbu", "um"] = "dbu"
) -> Netlist | DNetlist:
    file = Path(file).resolve()
    if not file.is_file():
        raise ValueError(f"{file=} is either not a file or does not exist.")
    with file.open(mode="rt") as f:
        yaml_dict = yaml.load(f)
        if unit == "dbu":
            return TNetlist[int].model_validate(yaml_dict, strict=True)
        return TNetlist[float].model_validate(yaml_dict)


# TODO: @sebastian-goeldi
# @overload
# def from_netlist(kcl: KCLayout, netlist: TNetlist[dbu]) -> KCell: ...
# @overload
# def from_netlist(kcl: KCLayout, netlist: TNetlist[um]) -> DKCell[TUnit]: ...
# def from_netlist(kcl: KCLayout, netlist: TNetlist[TUnit]) -> ProtoTKCell[TUnit]:
#     pass


TNetlist[Annotated[int, str]].model_rebuild()
