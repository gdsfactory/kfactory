"""Module for creating automatic optical and electrical routing."""

from pydantic import BaseModel

from .. import kdb
from ..kcell import Instance, Port
from . import aa, electrical, manhattan, optical


class Route(BaseModel, extra="forbid", arbitrary_types_allowed=True):
    references: list[Instance]
    labels: list[kdb.Shape] | None = None
    ports: tuple[Port, Port]
    length_dbu: int
    length_um: float


__all__ = ["electrical", "manhattan", "optical", "aa"]
