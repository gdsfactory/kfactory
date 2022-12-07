from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Hashable, Optional, Sequence, TypeGuard

from .. import kdb
from ..kcell import KCell

__all__ = ["Enclosure", "Direction"]


def is_Region(r: object) -> TypeGuard[kdb.Region]:
    return isinstance(r, kdb.Region)


def is_int(r: object) -> TypeGuard[int]:
    return isinstance(r, int)


class Direction(Enum):
    X = 1
    Y = 2
    BOTH = 3


class Enclosure:
    yaml_tag = "!Enclosure"

    def __init__(self, enclosures: Sequence[tuple[int, int]] = []):
        self.enclosures = list(enclosures)

    def add_enclosure(self, enc: tuple[int, int]) -> None:
        self.enclosures.append(enc)

    def apply_minkowski_enc(
        self,
        c: KCell,
        ref: int | kdb.Region,  # layer index or the region
        direction: Direction = Direction.BOTH,
    ) -> None:
        if isinstance(ref, int):
            r = kdb.Region(c.begin_shapes_rec(ref))
        else:
            r = ref

        r.merge()

        match direction:
            case Direction.BOTH:
                for enc, d in self.enclosures:
                    c.shapes(enc).insert(r.minkowski_sum(kdb.Box(-d, -d, d, d)).merge())
            case Direction.Y:
                for enc, d in self.enclosures:
                    c.shapes(enc).insert(
                        r.minkowski_sum(
                            kdb.Edge(kdb.Point(0, -d), kdb.Point(0, d))
                        ).merge()
                    )
            case Direction.X:
                for enc, d in self.enclosures:
                    c.shapes(enc).insert(
                        r.minkowski_sum(
                            kdb.Edge(kdb.Point(-d, 0), kdb.Point(d, 0))
                        ).merge()
                    )

    def apply_minkowski_y(self, c: KCell, ref: int | kdb.Region) -> None:
        return self.apply_minkowski_enc(c, ref, Direction.Y)

    def apply_minkowski_x(self, c: KCell, ref: int | kdb.Region) -> None:
        return self.apply_minkowski_enc(c, ref, Direction.X)

    def apply_minkowski_custom(
        self,
        c: KCell,
        ref: int | kdb.Region,
        shape: Callable[[int], kdb.Edge | list[kdb.Point] | kdb.Polygon | kdb.Box],
    ) -> None:

        r = kdb.Region(c.begin_shapes_rec(ref)) if isinstance(ref, int) else ref
        r.merge()
        for enc, d in self.enclosures:
            c.shapes(enc).insert(r.minkowski_sum(shape(d)).merge())

    def apply_custom(
        self,
        c: KCell,
        shape: Callable[[int], kdb.Edge | kdb.Polygon | kdb.Box],
    ) -> None:
        for enc, d in self.enclosures:
            c.shapes(enc).insert(shape(d))

    def apply_bbox(self, c: KCell, ref: int | kdb.Region) -> None:
        if is_int(ref):
            _ref = c.bbox_per_layer(ref)
        elif is_Region(ref):
            _ref = ref.bbox()
        return self.apply_custom(c, lambda d: _ref.enlarged(d, d))

    @classmethod
    def to_yaml(cls, representer, node):  # type: ignore[no-untyped-def]
        d = dict(node.enclosures)
        return representer.represent_mapping(cls.yaml_tag, d)

    def __hash__(self) -> int:
        return hash(tuple(self.enclosures))
