from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path
from typing import (
    TYPE_CHECKING,
    Annotated,
    Any,
    Generic,
    Literal,
    Self,
    TypeAlias,
    overload,
)

from pydantic import BaseModel, Field, RootModel, model_validator
from ruamel.yaml import YAML
from typing_extensions import TypeAliasType

from .kcell import DKCell, KCell, ProtoTKCell
from .typings import TUnit, dbu, um

if TYPE_CHECKING:
    from .layout import KCLayout

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


class RegularArrayPlacement(Placement[TUnit]):
    columns: int = Field(gt=0, default=1)
    rows: int = Field(gt=0, default=1)
    column_pitch: TUnit
    row_pitch: TUnit


class ArrayPlacement(Placement[TUnit]):
    na: int = Field(gt=1, default=1)
    nb: int = Field(gt=0, default=1)
    pitch_a: tuple[TUnit, TUnit]
    pitch_b: tuple[TUnit, TUnit]


CellSettings = RootModel[dict[str, JSON_Serializable]]


class NetlistInstance(BaseModel, Generic[TUnit]):
    settings: CellSettings | None = None


class Connection(BaseModel):
    pass


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


class TNetlist(BaseModel, Generic[TUnit]):
    name: str | None = None
    dependencies: list[Path] = Field(default_factory=list)
    instances: dict[str, NetlistInstance[TUnit]] | None = None
    placements: (
        dict[
            str,
            Placement[TUnit] | ArrayPlacement[TUnit] | RegularArrayPlacement[TUnit],
        ]
        | None
    ) = None
    nets: list[tuple[NetlistInstance[TUnit], str]] | None = None
    connections: list[tuple[str, str]] | None = None
    routes: dict[str, Route[TUnit]] | None = None


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
            return TNetlist[int].model_validate(yaml_dict)
        return TNetlist[float].model_validate(yaml_dict)


# TODO: @sebastian-goeldi
# @overload
# def from_netlist(kcl: KCLayout, netlist: TNetlist[dbu]) -> KCell: ...
# @overload
# def from_netlist(kcl: KCLayout, netlist: TNetlist[um]) -> DKCell[TUnit]: ...
# def from_netlist(kcl: KCLayout, netlist: TNetlist[TUnit]) -> ProtoTKCell[TUnit]:
#     pass


TNetlist[Annotated[int, str]].model_rebuild()
