"""Factories for generating functions which can produce KCells or VKCells."""

from typing import Any, Protocol

from ..instance import ProtoTInstance
from ..instance_group import ProtoTInstanceGroup
from ..kcell import ProtoTKCell
from . import bezier, circular, euler, straight, taper, virtual


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
