from __future__ import annotations

from typing import TYPE_CHECKING, Generic, NoReturn

from . import kdb
from .geometry import DBUGeometricObject, GeometricObject, UMGeometricObject
from .instance import ProtoTInstance, VInstance
from .typings import TInstance_co, TUnit

if TYPE_CHECKING:
    from collections.abc import Iterator, Sequence

    from .layout import KCLayout

__all__ = [
    "DInstanceGroup",
    "InstanceGroup",
    "ProtoInstanceGroup",
    "ProtoTInstanceGroup",
    "VInstanceGroup",
]


class ProtoInstanceGroup(GeometricObject[TUnit], Generic[TUnit, TInstance_co]):
    insts: list[TInstance_co]

    def __init__(self, insts: Sequence[TInstance_co] | None = None) -> None:
        """Initialize the InstanceGroup."""
        self.insts = list(insts) if insts is not None else []

    @property
    def kcl(self) -> KCLayout:
        try:
            return self.insts[0].kcl
        except IndexError as e:
            raise ValueError(
                "Cannot transform or retrieve the KCLayout "
                "of an instance group if it's empty"
            ) from e

    @kcl.setter
    def kcl(self, val: KCLayout) -> NoReturn:
        raise ValueError("KCLayout cannot be set on an instance group.")

    def transform(
        self, trans: kdb.Trans | kdb.DTrans | kdb.ICplxTrans | kdb.DCplxTrans
    ) -> None:
        """Transform the instance group."""
        for inst in self.insts:
            inst.transform(trans)

    def ibbox(self, layer: int | None = None) -> kdb.Box:
        """Get the total bounding box or the bounding box of a layer in dbu."""
        bb = kdb.Box()
        for _bb in (inst.ibbox(layer) for inst in self.insts):
            bb += _bb
        return bb

    def dbbox(self, layer: int | None = None) -> kdb.DBox:
        """Get the total bounding box or the bounding box of a layer in um."""
        bb = kdb.DBox()
        for _bb in (inst.dbbox(layer) for inst in self.insts):
            bb += _bb
        return bb

    def __iter__(self) -> Iterator[TInstance_co]:
        return iter(self.insts)


class ProtoTInstanceGroup(
    ProtoInstanceGroup[TUnit, ProtoTInstance[TUnit]],
    Generic[TUnit],
    GeometricObject[TUnit],
):
    def to_itype(self) -> InstanceGroup:
        return InstanceGroup(insts=[inst.to_itype() for inst in self.insts])

    def to_dtype(self) -> DInstanceGroup:
        return DInstanceGroup(insts=[inst.to_dtype() for inst in self.insts])


class InstanceGroup(ProtoTInstanceGroup[int], DBUGeometricObject):
    """Group of Instances.

    The instance group can be treated similar to a single instance
    with regards to transformation functions and bounding boxes.

    Args:
        insts: List of the instances of the group.
    """


class DInstanceGroup(ProtoTInstanceGroup[float], UMGeometricObject):
    """Group of DInstances.

    The instance group can be treated similar to a single instance
    with regards to transformation functions and bounding boxes.

    Args:
        insts: List of the dinstances of the group.
    """


class VInstanceGroup(ProtoInstanceGroup[float, VInstance], UMGeometricObject):
    """Group of DInstances.

    The instance group can be treated similar to a single instance
    with regards to transformation functions and bounding boxes.

    Args:
        insts: List of the vinstances of the group.
    """
