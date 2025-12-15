"""Factories for generating functions which can produce KCells or VKCells."""

from collections.abc import Iterable
from typing import TYPE_CHECKING, Any, Protocol, TypedDict

from ..instance import ProtoTInstance
from ..instance_group import ProtoTInstanceGroup
from ..kcell import ProtoTKCell
from ..typings import MetaData
from . import bezier, circular, euler, straight, taper, virtual

if TYPE_CHECKING:
    from collections.abc import Callable

    from cachetools import Cache

    from ..conf import CheckInstances
    from ..decorators import PortsDefinition
    from ..kcell import ProtoTKCell
    from ..schematic import TSchematic


class CellKwargs(TypedDict, total=False):
    set_settings: bool
    set_name: bool
    check_ports: bool
    check_pins: bool
    check_instances: CheckInstances
    snap_ports: bool
    add_port_layers: bool
    cache: Cache[int, Any] | dict[int, Any]
    basename: str
    drop_params: list[str]
    register_factory: bool
    overwrite_existing: bool
    layout_cache: bool
    info: dict[str, MetaData]
    post_process: Iterable[Callable[[ProtoTKCell[Any]], None]]
    debug_names: bool
    tags: list[str]
    lvs_equivalent_ports: list[list[str]]
    ports: PortsDefinition
    schematic_function: Callable[..., TSchematic[Any]]


class StraightFactoryDBU(Protocol):
    """Factory Protocol for routing.

    A straight factory must return a KCell with only a width and length given.
    """

    def __call__(self, width: int, length: int) -> ProtoTKCell[Any]:
        """Produces the KCell.

        E.g. in a function this would amount to
        `straight_factory(length=10_000, width=1000)`
        """
        ...


class StraightFactoryUM(Protocol):
    """Factory Protocol for routing.

    A straight factory must return a KCell with only a width and length given.
    """

    def __call__(self, width: float, length: float) -> ProtoTKCell[Any]:
        """Produces the KCell.

        E.g. in a function this would amount to
        `straight_factory(length=10_000, width=1000)`
        """
        ...


class SBendFactoryDBU(Protocol):
    def __call__(
        self, *, c: ProtoTKCell[Any], offset: int, length: int, width: int
    ) -> ProtoTInstance[Any] | ProtoTInstanceGroup[Any, Any]: ...


__all__ = [
    "StraightFactoryDBU",
    "StraightFactoryUM",
    "bezier",
    "circular",
    "euler",
    "straight",
    "taper",
    "virtual",
]
