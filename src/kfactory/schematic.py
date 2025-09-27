"""This is still experimental.

Caution is advised when using this, as the API might suddenly change.
In order to fix bugs etc.

Schematic (dbu based schematic) class diagram:
![Schematic's class diagram](/kfactory/_static/schematic.svg)

DSchematic (um based schematic) class diagram:
![DSchematic's class diagram](/kfactory/_static/dschematic.svg)


"""

from __future__ import annotations

import inspect
import keyword
import re
import subprocess
from collections import defaultdict
from functools import cached_property
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
    TypedDict,
    TypeGuard,
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
from .settings import Info
from .typings import KC, JSONSerializable, TUnit, dbu, um

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping, Sequence

    from .cross_section import CrossSection, DCrossSection

__all__ = ["DSchematic", "Schematic", "get_schematic", "read_schematic"]


yaml = YAML(typ="safe")

_schematic_default_imports = {
    "kfactory": "kf",
}


def _valid_varname(name: str) -> str:
    """Return a valid Python identifier for `name`.

    If `name` is not a valid identifier or is a Python keyword, prefix it with "_".
    This is useful when turning instance/port names into Python variables.
    """
    return name if name.isidentifier() and not keyword.iskeyword(name) else f"_{name}"


def _gez(value: TUnit) -> TUnit:
    """Validate that a unit-like value is >= 0.

    Raises:
        ValueError: If `value` is negative.
    """

    if value < 0:
        raise ValueError(
            "x of pitch_a and y of pitch_b must be greater or equal to zero."
        )
    return value


class MirrorPlacement(BaseModel, extra="forbid"):
    """Mirror-only placement toggle for an instance.

    Mirror only placements are used for connections. This ensures that the schematic can
    keep track of the relative mirror in case its placement is defined through
    connections only (i.e. purely relative to neighboring instances).

    Attributes:
        mirror: Whether the instance should be mirrored horizontally.
    """

    mirror: bool = False


class Anchor(BaseModel):
    """Base class for placement anchors.

    Subclasses (e.g. `FixedAnchor`, `PortAnchor`) define reference points used
    to align an instance during placement. Anchors allow to place instances relative to
    to their bounding box or port positions.
    """


class FixedAnchor(Anchor):
    """Anchor an instance to a fixed point of its own bounding box.

    Attributes:
        x: Horizontal anchor relative to the instance bbox ("left", "center", "right").
        y: Vertical anchor relative to the instance bbox ("bottom", "center", "top").
    """

    x: Literal["left", "center", "right"] | None = None
    y: Literal["bottom", "center", "top"] | None = None


class PortAnchor(Anchor):
    """Anchor an instance using one of its ports.

    Attributes:
        port: Name of the port on the instance to use as the anchor point.
    """

    port: str


class FixedAnchorDict(TypedDict):
    x: Literal["left", "center", "right"] | None
    y: Literal["bottom", "center", "top"] | None


class PortAnchorDict(TypedDict):
    port: str


class AnchorRef(BaseModel):
    instance: str


class AnchorRefX(AnchorRef):
    x: Literal["left", "center", "right"] | None = None


class AnchorRefY(AnchorRef):
    y: Literal["bottom", "center", "top"] | None = None


def _is_portdict(d: PortAnchorDict | FixedAnchorDict) -> TypeGuard[PortAnchorDict]:
    return "port" in d


_anchor_mapping: dict[str, FixedAnchorDict] = {
    "center": {"x": "center", "y": "center"},
    "cc": {"x": "center", "y": "center"},
    "ce": {"x": "right", "y": "center"},
    "cw": {"x": "left", "y": "center"},
    "nc": {"x": "center", "y": "top"},
    "ne": {"x": "right", "y": "top"},
    "nw": {"x": "left", "y": "top"},
    "sc": {"x": "center", "y": "bottom"},
    "se": {"x": "right", "y": "bottom"},
    "sw": {"x": "left", "y": "bottom"},
}

_anchorref_mapping: dict[str, str] = {
    "east": "right",
    "west": "left",
    "north": "top",
    "south": "bottom",
    "center": "center",
}


class Placement(MirrorPlacement, Generic[TUnit], extra="forbid"):
    """Absolute placement and orientation for an instance.

    Coordinates may be absolute (`x`, `y`) with
    relative offsets (`dx`, `dy`), and can reference other instance ports via
    `PortRef`/`PortArrayRef`. These are still considered absolute placements, but
    allow relative

    Attributes:
        x: x position or a port reference providing the x coordinate.
        dx: Relative X offset added to `x`.
        y: y position or a port reference providing the y coordinate.
        dy: Relative Y offset added to `y`.
        orientation: Rotation in degrees (0, 90, 180, 270). Can be a reference
            to another instance's port.
        anchor: Optional `FixedAnchor`/`PortAnchor` to align the instance relative
            to its bounding box or one of its ports.
        mirror: Whether the instance is to be mirrored or not.
    """

    x: TUnit | PortRef | PortArrayRef | AnchorRefX = cast("TUnit", 0)
    dx: TUnit = cast("TUnit", 0)
    y: TUnit | PortRef | PortArrayRef | AnchorRefY = cast("TUnit", 0)
    dy: TUnit = cast("TUnit", 0)
    orientation: float = 0
    anchor: FixedAnchor | PortAnchor | None = None

    @model_validator(mode="before")
    @classmethod
    def _replace_rotation_orientation(cls, data: dict[str, Any]) -> dict[str, Any]:
        if "rotation" in data:
            data["orientation"] = data.pop("rotation")
        return data

    def is_placeable(self, placed_instances: set[str], placed_ports: set[str]) -> bool:
        """Return True if all referenced instances/ports are already placed.

        If true, this means this instance can be placed now.
        """
        placeable = True
        if isinstance(self.x, PortRef):
            placeable = self.x.instance in placed_instances
        elif isinstance(self.x, Port):
            placeable = placeable and self.x.name in placed_ports
        elif isinstance(self.x, AnchorRefX):
            placeable = placeable and self.x.instance in placed_instances
        if isinstance(self.y, PortRef):
            placeable = placeable and self.y.instance in placed_instances
        elif isinstance(self.y, Port):
            placeable = placeable and self.y.name in placed_ports
        elif isinstance(self.y, AnchorRefY):
            placeable = placeable and self.y.instance in placed_instances
        return placeable


class RegularArray(BaseModel, Generic[TUnit], extra="forbid"):
    """Rectangular array with uniform row/column pitch.

    Attributes:
        columns: Number of columns (> 0).
        column_pitch: Distance between columns.
        rows: Number of rows (> 0).
        row_pitch: Distance between rows.
    """

    columns: int = Field(gt=0, default=1)
    column_pitch: TUnit
    rows: int = Field(gt=0, default=1)
    row_pitch: TUnit

    def __repr__(self) -> str:
        return f"RegularArray(columns={self.columns}, columns_pitch=)"


class Array(BaseModel, Generic[TUnit], extra="forbid"):
    """General 2D array parameterization using two pitch vectors.

    Attributes:
        na: Repetition count along vector A. This vector
            needs to have a positive x component.
        nb: Repetition count along vector B. This vector
            needs to have a positive y component
        pitch_a: (dx, dy) pitch for vector A. dx must be >= 0.
        pitch_b: (dx, dy) pitch for vector B. dy must be >= 0.
    """

    na: int = Field(gt=1, default=1)
    nb: int = Field(gt=0, default=1)
    pitch_a: tuple[Annotated[TUnit, AfterValidator(_gez)], TUnit]
    pitch_b: tuple[TUnit, Annotated[TUnit, AfterValidator(_gez)]]


class Ports(BaseModel, Generic[TUnit]):
    """Indexer for an instance's ports to produce `PortRef`/`PortArrayRef`.

    Example:
        `inst.ports["out"]` -> `PortRef`
        `inst.ports["out", 1, 0]` -> `PortArrayRef` (requires instance array)
    """

    instance: SchematicInstance[TUnit]

    def __getitem__(self, key: str | tuple[str, int, int]) -> PortRef | PortArrayRef:
        """Return a port reference for a (standard or array) port."""
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
    """Instance record within a schematic.

    Attributes:
        name: Instance name (unique within the schematic).
        component: Factory (cell function) name used to create the underlying cell.
        settings: Parameters passed to the factory.
        array: Optional array specification (`RegularArray` or `Array`).
        kcl: Layout context (`KCLayout`) to build the instance from. Defaults to
            default object.
        virtual: If True, create a virtual instance (VInstance/ComponentAllAngle).
        placement: Reference to a placement if the instance has a corresponding one.

    Properties:
        parent_schematic: `(D)Schematic` owning this instance.
        ports: Accessing `PortRef`/`PortArrayRef` resulting from this instance.

    Methods:
        place: Declare a placement, saved in the schematic owning this instance.
        connect: Create and register a `Connection` from one of my ports.
    """

    name: str = Field(exclude=True, frozen=True)
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
        x: TUnit | PortRef | AnchorRefX = 0,
        y: TUnit | PortRef | AnchorRefY = 0,
        dx: TUnit = 0,
        dy: TUnit = 0,
        orientation: float = 0,
        mirror: bool = False,
        anchor: FixedAnchorDict | PortAnchorDict | None = None,
    ) -> Placement[TUnit]:
        """Declare placement/orientation/mirroring for this instance.

        Returns:
            The created `Placement` (also stored under `self.placement` which references
            `self.parent_schematic.placements`).
        """
        placement = Placement[TUnit](
            x=x,
            y=y,
            dx=dx,
            dy=dy,
            orientation=orientation,
            mirror=mirror,
        )
        if anchor is not None:
            if _is_portdict(anchor):
                placement.anchor = PortAnchor(port=anchor["port"])
            else:
                fixed = cast("FixedAnchorDict", anchor)
                placement.anchor = FixedAnchor(x=fixed["x"], y=fixed["y"])
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
        """Connect one of my ports to `other` and register it on the schematic."""
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

    @cached_property
    def ports(self) -> Ports[TUnit]:
        return Ports(instance=self)

    @property
    def xmin(self) -> AnchorRefX:
        return AnchorRefX(instance=self.name, x="left")

    @property
    def xmax(self) -> AnchorRefX:
        return AnchorRefX(instance=self.name, x="left")

    @property
    def ymin(self) -> AnchorRefY:
        return AnchorRefY(instance=self.name, y="bottom")

    @property
    def ymax(self) -> AnchorRefY:
        return AnchorRefY(instance=self.name, y="top")

    @property
    def center(self) -> tuple[AnchorRefX, AnchorRefY]:
        return (
            AnchorRefX(instance=self.name, x="center"),
            AnchorRefY(instance=self.name, y="center"),
        )


class Route(BaseModel, Generic[TUnit], extra="forbid"):
    """Bundle of `Link`s routed using a named strategy.

    Attributes:
        name: Route identifier (key in `(D)Schematic.routes`).
        links: Pairs of start/end ports to be routed.
        routing_strategy: Name of routing function registered on the
            `Schematic.create_cell` or registered in `KCLayout` if none are given.
        settings: Keyword arguments forwarded to the routing strategy.
    """

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
                (tuple(str(k).rsplit(",", 1)), tuple(str(v).rsplit(",", 1)))
                for k, v in links.items()
            ]
        if "settings" not in data:
            data["settings"] = {}
        return data


class Port(BaseModel, Generic[TUnit], extra="forbid"):
    """A schematic-level, placeable port.

    This port is on the Schematic's cell's level, i.e. equivalent of `(D)KCell.ports`
    (or `Component.ports`).

    The port position/orientation can be absolute or derived from other placed
    instance ports via `PortRef`/`PortArrayRef`.

    Attributes:
        name: Port name (key in schematic).
        x: x position or `PortRef`.
        y: y position or `PortRef`.
        dx: Relative x offset.
        dy: Relative y offset.
        cross_section: Name of the cross-section to apply.
        orientation: Orientation in degrees or `PortRef`.

    Methods:
        is_placeable: True if all references resolve to already placed instances.
        place: Materialize the port on a `KCell` using provided cross-sections.
    """

    name: str = Field(exclude=True)
    x: TUnit | PortRef | AnchorRefX
    y: TUnit | PortRef | AnchorRefY
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
        TUnit | PortRef | AnchorRefX,
        TUnit | PortRef | AnchorRefY,
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
        if isinstance(self.x, PortRef | AnchorRefX):
            placeable = self.x.instance in placed_instances
        if isinstance(self.y, PortRef | AnchorRefY):
            placeable = placeable and self.y.instance in placed_instances
        if isinstance(self.orientation, PortRef):
            placeable = placeable and self.orientation.instance in placed_instances
        return placeable

    def place(
        self,
        cell: KCell,
        schematic: TSchematic[TUnit],
        name: str,
        cross_sections: Mapping[str, CrossSection | DCrossSection],
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
        elif isinstance(self.x, AnchorRefX):
            match self.x.x:
                case "left":
                    x = cell.insts[self.x.instance].xmin
                case "center":
                    x = cell.insts[self.x.instance].bbox().center().x
                case "right":
                    x = cell.insts[self.x.instance].xmax
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
        elif isinstance(self.y, AnchorRefY):
            match self.y.y:
                case "bottom":
                    y = cell.insts[self.y.instance].ymin
                case "center":
                    y = cell.insts[self.y.instance].bbox().center().y
                case "top":
                    y = cell.insts[self.y.instance].ymax
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
        return self.as_python_str()

    def as_call(self) -> str:
        port_str = f"x={self.x}, y={self.y}"
        if self.dx:
            port_str += f", {self.dx}"
        if self.dy:
            port_str += f", {self.dy}"

        return port_str

    def as_python_str(self, schematic_name: str = "schematic") -> str:
        return f"{schematic_name}.ports[{self.name!r}]"


class Link(
    RootModel[
        tuple[
            PortArrayRef | PortRef | Port[TUnit], PortArrayRef | PortRef | Port[TUnit]
        ]
    ],
    Generic[TUnit],
):
    """Undirected association between two ports (refs or schematic ports).

    The pair is stored in sorted order to ensure stable equality and hashing.
    """

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
    """Hard connection between two ports.

    Enforced as {PortRef | PortArrayRef | Port} x {PortRef | PortArrayRef}.
    Two `Port` objects (cell ports) cannot be connected directly.

    Raises:
        TypeError: If connection attempts to join two `Port` objects.
    """

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
        """Parse a Connection from a compact list/tuple/dict representation.

        Used for parsing legacy gdsfactory like connections.

        Supports array addressing like `( (inst, (ia, ib)), port )`.
        """
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
    """Schematic of a cell / component.

    Parameters:
        unit: Base coordinate unit ("dbu" or "um"). Fixed by subclass.
        kcl: `KCLayout` context (excluded from model serialization). Needed for
            referencing and creation of the cell.

    Attributes:
        name: Optional schematic name.
        instances: Mapping of instance name -> `SchematicInstance`.
        placements: Mapping of instance name -> `Placement`/`MirrorPlacement`.
        connections: List of `Connection`s.
        routes: Mapping of route name -> `Route`.
        ports: Mapping of port name -> `Port`/`PortRef`/`PortArrayRef`.
        info: dict which will be mapped to `KCell.info` (or any other derivate like
            Component).
    """

    name: str | None = None
    instances: dict[str, SchematicInstance[TUnit]] = Field(default_factory=dict)
    placements: dict[str, MirrorPlacement | Placement[TUnit]] = Field(
        default_factory=dict
    )
    connections: list[Connection[TUnit]] = Field(default_factory=list)
    routes: dict[str, Route[TUnit]] = Field(default_factory=dict)
    ports: dict[str, Port[TUnit] | PortRef | PortArrayRef] = Field(default_factory=dict)
    kcl: KCLayout = Field(exclude=True, default_factory=get_default_kcl)
    unit: Literal["dbu", "um"]
    info: dict[str, JSONSerializable] = Field(default_factory=dict)

    def create_inst(
        self,
        name: str,
        component: str,
        settings: dict[str, JSONSerializable] | None = None,
        array: RegularArray[TUnit] | Array[TUnit] | None = None,
        placement: Placement[TUnit] | None = None,
        kcl: KCLayout | None = None,
        virtual: bool = False,
    ) -> SchematicInstance[TUnit]:
        """Create a schema instance.

        This would be an SREF or AREF in the resulting GDS cell.

        Args:
            name: Instance name. In a schematic, each instance must be named,
                unless created through routing functions.
            component: Factory name of the component to instantiate.
            settings: Parameters passed to the factory (optional).
            array: If the instance should create an array instance (AREF),
                this can be passed here as an `Array` class instance.
            placement: Optional placement for the instance. Can also be configured
                with `inst.place(...)` afterwards.
            kcl: Optional `KCLayout` override for this instance.


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
                "virtual": virtual,
            }
        )
        inst._schematic = self

        if inst.name in self.instances:
            raise ValueError(
                f"Duplicate instance names are not allowed {inst.name=!r}"
                "already exists."
            )

        self.instances[inst.name] = inst
        if placement:
            self.placements[inst.name] = placement
        return inst

    def add_port(
        self, name: str | None = None, *, port: PortRef | PortArrayRef
    ) -> None:
        """Expose an existing instance port as a schematic top-level port.

        Args:
            name: Name for the schematic port; defaults to the underlying port name.
            port: Port reference to expose.

        Raises:
            ValueError: If a schematic port with `name` already exists.
        """
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
        """Create a schematic-level, placeable port.

        Returns:
            The created `Port`, also stored in `self.ports`.
        """
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

    def create_connection(
        self, port1: PortRef | Port[TUnit], port2: PortRef
    ) -> Connection[TUnit]:
        """Create and register a connection between two instance ports.

        Args:
            port1: First instance port.
            port2: Second instance port.

        Raises:
            ValueError: If either referenced instance is unknown.

        Returns:
            The created `Connection`.
        """

        conn = Connection[TUnit]((port1, port2))
        if isinstance(port1, PortRef):
            if port1.instance not in self.instances:
                raise ValueError(
                    f"Cannot create connection to unknown instance {port1.instance}"
                )
        elif port1 != self.ports.get(port1.name):
            raise ValueError(f"Unknown port {port1=}")
        if port2.instance not in self.instances:
            raise ValueError(
                f"Cannot create connection to unknown instance {port2.instance}"
            )
        self.connections.append(conn)
        return conn

    def netlist(
        self,
        add_defaults: bool = True,
        factories: dict[str, Callable[..., ProtoTKCell[Any]] | Callable[..., VKCell]]
        | None = None,
        external_factories: dict[
            str, dict[str, Callable[..., ProtoTKCell[Any]] | Callable[..., VKCell]]
        ]
        | None = None,
    ) -> Netlist:
        """Compile the schematic into a `Netlist`.

        Includes nets from `connections`, `routes`, and exposed `ports`. Instances
        are serialized with their `kcl`, component, and settings. The resulting
        netlist is sorted for stable output.
        """

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
        if add_defaults:
            kcl_factories: dict[
                str, Callable[..., ProtoTKCell[Any]] | Callable[..., VKCell]
            ]
            if external_factories is None:
                all_factories: dict[
                    str,
                    dict[str, Callable[..., ProtoTKCell[Any]] | Callable[..., VKCell]],
                ] = defaultdict(dict)
                for kcl_ in kcls.values():
                    kcl_factories = {f.name: f._f for f in kcl_.factories.values()}
                    kcl_factories.update(
                        {vf.name: vf._f for vf in kcl_.virtual_factories.values()}
                    )
                    all_factories[kcl_.name] = kcl_factories
            else:
                all_factories = external_factories.copy()
            if factories is not None:
                all_factories[self.kcl.name] = factories
            nl = Netlist(
                instances={
                    inst.name: NetlistInstance(
                        name=inst.name,
                        kcl=inst.kcl.name,
                        component=inst.component,
                        settings=_get_full_settings(
                            inst.settings,
                            inspect.signature(
                                all_factories[inst.kcl.name][inst.component]
                            ),
                        ),
                    )
                    for inst in self.instances.values()
                }
                if self.instances
                else {},
                nets=nets,
                ports=[NetlistPort(name=name) for name in self.ports],
            )
        else:
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
        placements = data.get("placements")
        if placements:
            for placement in placements.values():
                anchor: FixedAnchorDict | None = None
                if "port" in placement:
                    port = placement.pop("port")
                    if port in [
                        "ce",
                        "cw",
                        "nc",
                        "ne",
                        "nw",
                        "sc",
                        "se",
                        "sw",
                        "center",
                        "cc",
                    ]:
                        placement["anchor"] = _anchor_mapping[port]
                    else:
                        placement["anchor"] = {"port": port}
                anchor = placement.get("anchor", {})
                if "xmin" in placement:
                    anchor["x"] = "left"
                    placement["x"] = placement.pop("xmin")
                elif "xmax" in placement:
                    anchor["x"] = "right"
                    placement["y"] = placement.pop("xmax")
                if "ymin" in placement:
                    anchor["y"] = "bottom"
                    placement["y"] = placement.pop("ymin")
                elif "ymax" in placement:
                    anchor["y"] = "top"
                    placement["y"] = placement.pop("ymax")
                placement["anchor"] = anchor
                x_ = placement.get("x")
                if isinstance(x_, str):
                    inst, port = x_.rsplit(",", 1)
                    if port in ["east", "center", "west"]:
                        placement["x"] = {
                            "instance": inst,
                            "x": _anchorref_mapping[port],
                        }
                    else:
                        placement["x"] = {"instance": inst, "port": port}
                y_ = placement.get("y")
                if isinstance(y_, str):
                    inst, port = x_.rsplit(",", 1)
                    if port in ["bottom", "center", "top"]:
                        placement["x"] = {
                            "instance": inst,
                            "y": _anchorref_mapping[port],
                        }
                    else:
                        placement["y"] = {"instance": inst, "port": port}

                if isinstance(placement.get("y"), str):
                    raise NotImplementedError
        return data

    @model_validator(mode="after")
    def assign_backrefs(self) -> Self:
        for inst in self.instances.values():
            inst._schematic = self
        return self

    def create_cell(
        self,
        output_type: type[KC],
        factories: Mapping[
            str, Callable[..., KCell] | Callable[..., DKCell] | Callable[..., VKCell]
        ]
        | None = None,
        cross_sections: Mapping[str, CrossSection | DCrossSection] | None = None,
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
        """Materialize the schematic into a `KCell`/`DKCell`/`Component`.

        Args:
            output_type: Cell type to return (e.g., `KCell`, `DKCell`).
            factories: Optional mapping from factory name to callable returning a cell.
            cross_sections: Optional mapping of cross-section names to definitions.
                If undefined uses `self.kcl`'s cross sections.
            routing_strategies: Strategy functions keyed by name. If none uses
                `self.kcl`'s routing strategies
            place_unknown: If True, place otherwise unplaceable instances at (0, 0).
                This might cause unintended side effects as the schematic is seemingly
                not fully deterministic, therefore this is disabled by default.

        Returns:
            A cell of type `output_type` with instances, ports, and routes realized.

        Raises:
            ValueError: If placement or connection constraints cannot be satisfied.
        """
        c = KCell(kcl=self.kcl)
        c.info = Info(**self.info)

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
                    p1: KCellPort | DKCellPort = c.ports[l1.name]
                elif isinstance(l1, PortArrayRef):
                    if self.instances[l1.instance].virtual:
                        p1 = c.vinsts[l1.instance].ports[l1.port, l1.ia, l1.ib]
                    else:
                        p1 = c.insts[l1.instance].ports[l1.port, l1.ia, l1.ib]
                elif self.instances[l1.instance].virtual:
                    p1 = c.vinsts[l1.instance].ports[l1.port]
                else:
                    p1 = c.insts[l1.instance].ports[l1.port]
                start_ports.append(p1)
                if isinstance(l2, Port):
                    p2: KCellPort | DKCellPort = c.ports[l2.name]
                elif isinstance(l2, PortArrayRef):
                    if self.instances[l2.instance].virtual:
                        p2 = c.vinsts[l2.instance].ports[l2.port, l2.ia, l2.ib]
                    else:
                        p2 = c.insts[l2.instance].ports[l2.port, l2.ia, l2.ib]
                elif self.instances[l2.instance].virtual:
                    p2 = c.vinsts[l2.instance].ports[l2.port]
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
                if self.instances[c1.instance].virtual:
                    inst1: Instance | VInstance = c.vinsts[c1.instance]
                else:
                    inst1 = c.insts[c1.instance]
                if self.instances[c2.instance].virtual:
                    inst2: Instance | VInstance = c.vinsts[c2.instance]
                else:
                    inst2 = c.insts[c2.instance]
                if isinstance(c1, PortArrayRef):
                    p1 = inst1.ports[c1.port, c1.ia, c1.ib]
                else:
                    p1 = inst1.ports[c1.port]
                if isinstance(c2, PortArrayRef):
                    p2 = inst2.ports[c2.port, c2.ia, c2.ib]
                else:
                    p2 = inst2.ports[c2.port]

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
        c.schematic = self
        if self.name:
            c.name = self.name

        return output_type(base=c.base)

    def add_route(
        self,
        name: str,
        start_ports: list[PortRef | Port[TUnit]],
        end_ports: list[PortRef | Port[TUnit]],
        routing_strategy: str,
        **settings: JSONSerializable,
    ) -> Route[TUnit]:
        """Create a multi-link route bundle.

        Args:
            name: Route identifier (must be unique).
            start_ports: Start ports for each link.
            end_ports: End ports for each link.
            routing_strategy: Name of the routing strategy function.
            **settings: Extra keyword args forwarded to the strategy.

        Returns:
            The created `Route`.

        Raises:
            ValueError: If `name` already exists.
        """

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
        ruff_format: bool = True,
    ) -> str:
        """Generate Python code that reconstructs this schematic.

        Args:
            imports: Mapping of module -> alias to emit at top of file.
            kfactory_name: Optional override for the `kfactory` import name.
            ruff_format: If True, format the generated code with `ruff`.

        Returns:
            The generated source code as a string. If `ruff` is unavailable or
            fails, the unformatted string is returned.
        """

        schematic_cell = ""
        indent = 0

        def _ind() -> str:
            nonlocal indent
            return " " * indent

        kf_name = kfactory_name or imports["kfactory"]

        def _kcls(name: str) -> str:
            return f'{kf_name}.kcls["{name}"]'

        for imp, imp_as in imports.items():
            if imp_as is None:
                schematic_cell += f"import {imp}\n"
            else:
                schematic_cell += f"import {imp} as {imp_as}\n"

        if imports:
            schematic_cell += "\n\n"

        schematic_cell += f"kcl = {_kcls(self.kcl.name)}\n\n"

        schematic_cell += f"@kcl.schematic_cell(output_type={kf_name}.DKCell)\n"
        schematic_cell += f"def {self.name}() -> {kf_name}.{self.__class__.__name__}:\n"
        indent = 2

        if isinstance(self, Schematic):
            schematic_cell += f"{_ind()}schematic = {kf_name}.Schematic(kcl=kcl)\n\n"
        else:
            schematic_cell += f"{_ind()}schematic = {kf_name}.DSchematic(kcl=kcl)\n\n"

        schematic_cell += f"{_ind()}# Create the schematic instances\n"

        names: dict[str, str] = {}

        for inst in sorted(self.instances.values(), key=attrgetter("name")):
            inst_name = _valid_varname(inst.name)
            names[inst.name] = inst_name
            schematic_cell += f"{_ind()}{inst_name} = schematic.create_inst(\n"
            indent += 2
            schematic_cell += (
                f"{_ind()}name={inst.name!r},\n"
                f"{_ind()}component={inst.component!r},\n"
                f"{_ind()}settings={inst.settings!r},\n"
            )
            if inst.kcl != self.kcl:
                schematic_cell += f"{_ind()}kcl={_kcls(inst.kcl.name)},\n"
            if inst.virtual:
                schematic_cell += f"{_ind()}virtual=True,\n"
            if inst.array is not None:
                arr = inst.array
                if isinstance(arr, RegularArray):
                    schematic_cell += f"{_ind()}array=RegularArray(\n"
                    indent += 2
                    schematic_cell += (
                        f"{_ind()}columns={arr.columns},\n"
                        f"{_ind()}columns_pitch={arr.column_pitch},\n"
                        f"{_ind()}rows={arr.rows},\n"
                        f"{_ind()}row_pitch={arr.row_pitch}),\n"
                    )
                    indent -= 2
                    schematic_cell += f"{_ind()})\n"
                else:
                    schematic_cell += f"{_ind()}array=Array(\n"
                    indent += 2
                    schematic_cell += (
                        f"{_ind()}na={arr.na},\n"
                        f"{_ind()}nb={arr.nb},\n"
                        f"{_ind()}pitch_a={arr.pitch_a},\n"
                        f"{_ind()}pitch_b={arr.pitch_b}),\n"
                    )
                    indent -= 2
                    schematic_cell += f"{_ind()})\n"
            indent -= 2
            schematic_cell += f"{_ind()})\n"

        if self.ports:
            schematic_cell += f"{_ind()}# Schematic ports\n"

            for name, port in sorted(
                self.ports.items(),
                key=lambda named_port: (
                    named_port[1].__class__.__name__,
                    named_port[0],
                ),
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
                        schematic_cell += f"{_ind()}dx={port.dx},\n"
                    if port.dy:
                        schematic_cell += f"{_ind()}dy={port.dy},\n"
                    indent -= 2
                else:
                    schematic_cell += (
                        f"{_ind()}schematic.add_port("
                        f"name={name!r},"
                        f"port={port.as_python_str(names[port.instance])})\n"
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
                    if placement.anchor:
                        schematic_cell += (
                            f"{_ind()}anchor="
                            f"{placement.anchor.model_dump(exclude_defaults=True)},\n"
                        )
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
                        schematic_cell += f"{_ind()}other={ref2},\n"
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
                    schematic_cell += f"{_ind()}other={ref1}\n"
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

        schematic_cell += f"{_ind()}return schematic"

        if ruff_format:
            try:
                result = subprocess.run(
                    ["ruff", "format", "-"],  # noqa: S607
                    input=schematic_cell,
                    text=True,
                    capture_output=True,
                    check=False,
                )
                if result.returncode != 0:
                    logger.warning(
                        "Ruff errored out, returning unmodified string. Ruff errors:\n"
                        + result.stderr
                    )
                    return schematic_cell

                schematic_cell = result.stdout
            except FileNotFoundError:
                logger.warning(
                    "Ruff not found or installed. Returning unformatted string."
                )

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
    """Deprecated alias for `Schematic` (will be removed in kfactory 2.0)."""

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
    """Deprecated alias for `DSchematic` (will be removed in kfactory 2.0)."""

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
    factories: Mapping[
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
            if schematic_inst.mirror:
                kinst.transform(kdb.DCplxTrans.M0)
            return Instance(kcl=c.kcl, instance=kinst._instance)

    # If the instance is a
    vinst = c.create_vinst(cell_)
    vinst.name = schematic_inst.name
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
    cross_sections: Mapping[str, CrossSection | DCrossSection],
    factories: Mapping[
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
        if schema_inst.placement and isinstance(schema_inst.placement, Placement):
            logger.debug("Placing {}", schema_inst.name)
            p = schema_inst.placement
            assert p is not None

            if p.is_placeable(placed_insts, placed_ports):
                if schematic.unit == "dbu":
                    if isinstance(p.x, PortRef):
                        x: float = KCellPort(
                            base=instances[p.x.instance].ports[p.x.port].base
                        ).x
                    elif isinstance(p.x, AnchorRefX):
                        bb: kdb.Box | kdb.DBox = instances[p.x.instance].ibbox()
                        match p.x.x:
                            case "left":
                                x = bb.left
                            case "right":
                                x = bb.right
                            case _:
                                x = bb.center().x
                    else:
                        x = p.x
                    if isinstance(p.y, PortRef):
                        y: float = KCellPort(
                            base=instances[p.y.instance].ports[p.y.port].base
                        ).y
                    elif isinstance(p.y, AnchorRefY):
                        bb = instances[p.y.instance].ibbox()
                        match p.y.y:
                            case "bottom":
                                y = bb.bottom
                            case "top":
                                y = bb.top
                            case _:
                                y = bb.center().y
                    else:
                        y = p.y
                    if p.anchor is None:
                        kinst.transform(
                            kdb.ICplxTrans(
                                mag=1,
                                rot=p.orientation,
                                x=x + p.dx,
                                y=y + p.dy,
                            )
                        )
                    elif isinstance(p.anchor, PortAnchor):
                        kinst.transform(
                            kdb.ICplxTrans(
                                mag=1,
                                rot=p.orientation,
                                x=x + p.dx,
                                y=y + p.dy,
                            )
                            * kdb.ICplxTrans(-kinst.ports[p.anchor.port].trans.disp)
                        )
                    else:
                        match p.anchor.x:
                            case "left":
                                _x = kinst.ibbox().left
                            case "right":
                                _x = kinst.ibbox().right
                            case "center":
                                _x = kinst.ibbox().center().x
                        match p.anchor.y:
                            case "top":
                                _y = kinst.ibbox().top
                            case "bottom":
                                _y = kinst.ibbox().bottom
                            case "center":
                                _y = kinst.ibbox().center().x

                        kinst.transform(
                            kdb.ICplxTrans(
                                mag=1,
                                rot=p.orientation,
                                x=x + p.dx,
                                y=y + p.dy,
                            )
                            * kdb.ICplxTrans(-kdb.Vector(_x, _y))
                        )
                else:
                    if isinstance(p.x, PortRef):
                        x = DKCellPort(
                            base=instances[p.x.instance].ports[p.x.port].base
                        ).x
                    elif isinstance(p.x, AnchorRefX):
                        bb = instances[p.x.instance].dbbox()
                        match p.x.x:
                            case "left":
                                x = bb.left
                            case "right":
                                x = bb.right
                            case _:
                                x = bb.center().x
                    else:
                        x = p.x
                    if isinstance(p.y, PortRef):
                        y = DKCellPort(
                            base=instances[p.y.instance].ports[p.y.port].base
                        ).y
                    elif isinstance(p.y, AnchorRefY):
                        bb = instances[p.y.instance].dbbox()
                        match p.y.y:
                            case "bottom":
                                y = bb.bottom
                            case "top":
                                y = bb.top
                            case _:
                                y = bb.center().y
                    else:
                        y = p.y
                    if p.anchor is None:
                        kinst.transform(
                            kdb.DCplxTrans(
                                mag=1,
                                rot=p.orientation,
                                x=x + p.dx,
                                y=y + p.dy,
                            )
                        )
                    elif isinstance(p.anchor, PortAnchor):
                        kinst.transform(
                            kdb.DCplxTrans(
                                mag=1,
                                rot=p.orientation,
                                x=x + p.dx,
                                y=y + p.dy,
                            )
                            * kdb.DCplxTrans(
                                -kinst.ports[p.anchor.port].dcplx_trans.disp
                            )
                        )
                    else:
                        match p.anchor.x:
                            case "left":
                                _dx = kinst.dbbox().left
                            case "right":
                                _dx = kinst.dbbox().right
                            case "center":
                                _dx = kinst.dbbox().center().x
                            case _:
                                _dx = 0
                        match p.anchor.y:
                            case "top":
                                _dy = kinst.dbbox().top
                            case "bottom":
                                _dy = kinst.dbbox().bottom
                            case "center":
                                _dy = kinst.dbbox().center().x
                            case _:
                                _dy = 0

                        kinst.transform(
                            kdb.DCplxTrans(
                                mag=1,
                                rot=p.orientation,
                                x=x + p.dx,
                                y=y + p.dy,
                            )
                            * kdb.DCplxTrans(-kdb.DVector(_dx, _dy))
                        )
                placed_insts.add(inst)

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
                f" instances). Unplaced instances: {instances.keys() - placed_insts!r}"
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
    cross_sections: Mapping[str, CrossSection | DCrossSection],
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
    """NOT FUNCTIONAL YET.

    Create a minimal `TSchematic` from an existing cell.

    Currently extracts named instances only. Port extraction is not yet implemented.

    Args:
        c: Source cell.
        exclude_port_types: Port types to ignore (reserved for future use).

    Returns:
        A `Schematic` if `c` is `KCell`, otherwise a `DSchematic`.
    """

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
    """Read a schematic from a YAML file.

    Args:
        file: Path to a YAML file.
        unit: Target coordinate unit; controls which subclass is constructed.

    Returns:
        `Schematic` when `unit="dbu"`, else `DSchematic`.

    Raises:
        ValueError: If `file` does not exist or is not a file.
    """

    file = Path(file).resolve()
    if not file.is_file():
        raise ValueError(f"{file=} is either not a file or does not exist.")
    with file.open(mode="rt") as f:
        yaml_dict = yaml.load(f)
        if unit == "dbu":
            return Schematic.model_validate(yaml_dict, strict=True)
        return DSchematic.model_validate(yaml_dict)


def _get_full_settings(
    settings: dict[str, JSONSerializable], f_sig: inspect.Signature
) -> dict[str, JSONSerializable]:
    params: dict[str, JSONSerializable] = {
        param_name: param.default
        for param_name, param in f_sig.parameters.items()
        if param.default is not inspect._empty
    }

    params.update(settings)

    return params
