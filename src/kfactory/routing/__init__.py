"""Module for creating automatic optical and electrical routing."""

from pydantic import BaseModel

from kfactory import kdb
from kfactory.instance import Instance
from kfactory.port import Port

from . import aa, electrical, generic, manhattan, optical


class Route(BaseModel, extra="forbid", arbitrary_types_allowed=True):
    references: list[Instance]
    labels: list[kdb.Shape] | None = None
    ports: tuple[Port, Port]
    length_dbu: int
    length_um: float


__all__ = ["aa", "electrical", "generic", "manhattan", "optical"]
