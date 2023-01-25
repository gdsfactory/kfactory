from enum import Enum
from typing import Any, Callable, Optional, Sequence, Set, TypeGuard

import numpy as np

# import kfactory.kdb as kdb
import kfactory.kdb as kdb
from kfactory.kcell import KCell
from kfactory.tech import LayerEnum

__all__ = ["Enclosure", "Direction"]


def is_Region(r: object) -> TypeGuard[kdb.Region]:
    return isinstance(r, kdb.Region)


def is_int(r: object) -> TypeGuard[int]:
    return isinstance(r, int)


def is_callable(r: object) -> TypeGuard[Callable[..., Any]]:
    return callable(r)


class Direction(Enum):
    X = 1
    Y = 2
    BOTH = 3


class Enclosure:
    yaml_tag = "!Enclosure"

    def __init__(
        self,
        enclosures: Sequence[tuple[int, LayerEnum | int]] = [],
        name: Optional[str] = None,
    ):
        self.enclosures = list(enclosures)
        self._name = name

    def __add__(self, other: "Enclosure") -> "Enclosure":
        encs: Set[tuple[int, LayerEnum | int]] = set(self.enclosures)
        encs.update(other.enclosures)
        name = (
            None
            if other._name is None or self._name is None
            else self.name + other.name
        )
        return Enclosure(list(encs), name)

    def __iadd__(self, other: "Enclosure") -> None:
        encs: Set[tuple[int, LayerEnum | int]] = set(self.enclosures)
        encs.update(other.enclosures)
        self.enclosures = list(encs)

    def add_enclosure(self, enc: tuple[int, LayerEnum | int]) -> None:
        self.enclosures.append(enc)

    def apply_minkowski_enc(
        self,
        c: KCell,
        ref: int | kdb.Region,  # layer index or the region
        direction: Direction = Direction.BOTH,
    ) -> None:
        r = kdb.Region(c.begin_shapes_rec(ref)) if isinstance(ref, int) else ref
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

    @property
    def name(self) -> str:
        if self._name is None:
            return f"enc{self.__hash__()}"
        else:
            return f"enc{self._name}"

    @name.setter
    def name(self, value: str) -> None:
        self._name = value


def extrude_path_static_single(
    path: list[kdb.DPoint],
    width: float,
    start_angle: Optional[float] = None,
    end_angle: Optional[float] = None,
) -> kdb.DPolygon:

    start = path[1] - path[0]
    end = path[-1] - path[-2]
    if start_angle is None:
        start_angle = np.rad2deg(np.arctan2(start.y, start.x))
    if end_angle is None:
        end_angle = np.rad2deg(np.rad2deg(np.arctan2(end.y, end.x)))

    p_start = path[0]
    p_end = path[-1]
    start_trans = kdb.DCplxTrans(1, start_angle, False, p_start.x, p_start.y)
    end_trans = kdb.DCplxTrans(1, end_angle, False, p_end.x, p_end.y)

    ref_point = kdb.DPoint(width, 0)
    points_top = [start_trans * ref_point]
    points_bot = [start_trans * kdb.DCplxTrans.R180 * ref_point]

    p_old = path[0]
    p = path[1]

    for point in path[2:]:
        p_new = point
        v = p_new - p_old
        angle = np.rad2deg(np.arctan2(v.y, v.x))
        transformation = kdb.DCplxTrans(1, angle, False, 0, 0)
        points_top.append(transformation * ref_point)
        points_bot.append(transformation * kdb.DCplxTrans.R180 * ref_point)
        p_old = p
        p = p_new

    points_top.append(end_trans * ref_point)
    points_bot.append(end_trans * kdb.DCplxTrans.R180 * ref_point)

    points_bot.reverse()
    polygon = kdb.DPolygon(points_top + points_bot)
    return polygon


def extrude_path_static(
    target: KCell,
    layer: LayerEnum,
    path: list[kdb.DPoint],
    width: float,
    enclosure: Optional[Enclosure] = None,
    start_angle: Optional[float] = None,
    end_angle: Optional[float] = None,
) -> None:
    _layer_list: list[tuple[int, LayerEnum | int]] = (
        [(0, layer)] if enclosure is None else [(0, layer)] + enclosure.enclosures
    )
    for d, _layer in _layer_list:
        polygon = extrude_path_static_single(
            path, width + d * target.library.dbu, start_angle, end_angle
        )
        target.shapes(_layer).insert(polygon)


def extrude_profile_single(
    path: list[kdb.DPoint],
    width: Callable[[float], float] | list[float],
    start_angle: Optional[float] = None,
    end_angle: Optional[float] = None,
) -> kdb.DPolygon:
    start = path[1] - path[0]
    end = path[-1] - path[-2]
    if start_angle is None:
        start_angle = np.rad2deg(np.arctan2(start.y, start.x))
    if end_angle is None:
        end_angle = np.rad2deg(np.rad2deg(np.arctan2(end.y, end.x)))

    p_start = path[0]
    p_end = path[-1]

    start_trans = kdb.DCplxTrans(1, start_angle, False, p_start.x, p_start.y)
    end_trans = kdb.DCplxTrans(1, end_angle, False, p_end.x, p_end.y)

    if callable(width):
        l = sum(((p2 - p1).abs() for p2, p1 in zip(path[:-1], path[1:])))
        z: float = 0
        ref_point = kdb.DPoint(0, width(z / l))
        points_top = [start_trans * ref_point]
        points_bot = [start_trans * kdb.DCplxTrans.R180 * ref_point]
        p_old = path[0]
        p = path[1]
        z += (p - p_old).abs()
        for point in path[2:]:
            ref_point = kdb.DPoint(0, width(z / l))
            p_new = point
            v = p_new - p_old
            angle = np.rad2deg(np.arctan2(v.y, v.x))
            transformation = kdb.DCplxTrans(1, angle, False, p.x, p.y)
            points_top.append(transformation * ref_point)
            points_bot.append(transformation * kdb.DCplxTrans.R180 * ref_point)
            z += (p_new - p).abs()
            p_old = p
            p = p_new
        ref_point = kdb.DPoint(0, width(z / l))
        points_top.append(end_trans * ref_point)
        points_bot.append(end_trans * kdb.DCplxTrans.R180 * ref_point)

    else:
        ref_point = kdb.DPoint(0, width[0])
        points_top = [start_trans * ref_point]
        points_bot = [start_trans * kdb.DCplxTrans.R180 * ref_point]
        p_old = path[0]
        p = path[1]
        for point, w in zip(path[2:], width[1:-1]):
            ref_point = kdb.DPoint(0, w)
            p_new = point
            v = p_new - p_old
            angle = np.rad2deg(np.arctan2(v.y, v.x))
            transformation = kdb.DCplxTrans(1, angle, False, p.x, p.y)
            points_top.append(transformation * ref_point)
            points_bot.append(transformation * kdb.DCplxTrans.R180 * ref_point)
            p_old = p
            p = p_new
        ref_point = kdb.DPoint(0, width[-1])
        points_top.append(end_trans * ref_point)
        points_bot.append(end_trans * kdb.DCplxTrans.R180 * ref_point)

    points_bot.reverse()
    polygon = kdb.DPolygon(points_top + points_bot)
    return polygon


def extrude_profile(
    target: KCell,
    layer: LayerEnum,
    path: list[kdb.DPoint],
    widths: Callable[[float], float] | list[float],
    enclosure: Optional[Enclosure] = None,
    start_angle: Optional[float] = None,
    end_angle: Optional[float] = None,
) -> None:

    _layer_list: list[tuple[int, LayerEnum | int]] = (
        [(0, layer)] if enclosure is None else [(0, layer)] + enclosure.enclosures
    )
    if callable(widths):
        for d, _layer in _layer_list:

            def d_widths(x: float) -> float:
                return widths(x) + d * target.library.dbu

            polygon = extrude_profile_single(path, d_widths, start_angle, end_angle)
            target.shapes(_layer).insert(polygon)
    else:
        for d, _layer in _layer_list:
            _widths = [w + d * target.library.dbu for w in widths]
            polygon = extrude_profile_single(path, _widths, start_angle, end_angle)
            target.shapes(_layer).insert(polygon)
