from enum import Enum
from hashlib import sha1
from typing import Any, Callable, List, Optional, Sequence, TypeGuard, cast, overload

import numpy as np
from numpy.typing import ArrayLike
from pydantic import BaseModel, PrivateAttr
from scipy.special import binom  # type: ignore[import]

from .. import kdb
from ..config import logger
from ..kcell import KCell, LayerEnum

__all__ = [
    "extrude_path",
    "extrude_path_points",
    "extrude_path_dynamic_points",
    "extrude_path_dynamic",
    "path_pts_to_polygon",
    "Enclosure",
    "Direction",
]


def vec_angle(v: kdb.Vector) -> int:
    """Determine vector angle in increments of 90°"""
    if v.x != 0 and v.y != 0:
        raise NotImplementedError("only manhattan vectors supported")

    match (v.x, v.y):
        case (x, 0) if x > 0:
            return 0
        case (x, 0) if x < 0:
            return 2
        case (0, y) if y > 0:
            return 1
        case (0, y) if y < 0:
            return 3
        case _:
            logger.warning(f"{v} is not a manhattan, cannot determine direction")
    return -1


def is_callable_widths(
    widths: Callable[[float], float] | list[float]
) -> TypeGuard[Callable[[float], float]]:
    return callable(widths)


def clean_points(points: List[kdb.Point]) -> List[kdb.Point]:
    if len(points) < 2:
        return points
    if len(points) == 2:
        return points if points[1] != points[0] else points[:1]
    p_p = points[0]
    p = points[1]

    del_points = []

    for i, p_n in enumerate(points[2:], 2):
        v2 = p_n - p
        v1 = p - p_p
        if (
            (np.sign(v1.x) == np.sign(v2.x)) and (np.sign(v1.y) == np.sign(v2.y))
        ) or v2.abs() == 0:
            del_points.append(i - 1)
        p_p = p
        p = p_n

    for i in reversed(del_points):
        del points[i]

    return points


def simplify(points: list[kdb.Point], tolerance: float) -> list[kdb.Point]:
    simple_pts: list[kdb.Point] = [points[0]]
    if len(points) < 3:
        return points

    start = 0
    last = len(points) - 1

    e = kdb.Edge(points[0], points[-1])
    dists = [e.distance_abs(p) for p in points]
    ind_dist = int(np.argmax(dists))
    maxd = dists[ind_dist]

    return (
        [points[0], points[-1]]
        if maxd <= tolerance
        else (
            simplify(points[: ind_dist + 1], tolerance)
            + simplify(points[ind_dist:], tolerance)[1:]
        )
    )


def bezier_curve(
    t: np.typing.NDArray[np.float64],
    control_points: Sequence[tuple[np.float64 | float, np.float64 | float]],
) -> list[kdb.DPoint]:
    xs = np.zeros(t.shape, dtype=np.float64)
    ys = np.zeros(t.shape, dtype=np.float64)
    n = len(control_points) - 1
    for k in range(n + 1):
        ank = binom(n, k) * (1 - t) ** (n - k) * t**k
        xs += ank * control_points[k][0]
        ys += ank * control_points[k][1]

    return [kdb.DPoint(p[0], p[1]) for p in np.stack([xs, ys])]


def extrude_path_points(
    path: list[kdb.DPoint],
    width: float,
    start_angle: Optional[float] = None,
    end_angle: Optional[float] = None,
) -> tuple[list[kdb.DPoint], list[kdb.DPoint]]:
    """
    Extrude a path from a list of points and a static width

    Args:
        path: list of floating-points points
        width: width in µm
        start_angle: optionally specify a custom starting angle if `None` will be autocalculated from the first two elements
        end_angle: optionally specify a custom ending angle if `None` will be autocalculated from the last two elements
    """

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

    ref_vector = kdb.DCplxTrans(kdb.DVector(0, width / 2))
    vector_top = [start_trans * ref_vector]
    vector_bot = [(start_trans * kdb.DCplxTrans.R180) * ref_vector]

    p_old = path[0]
    p = path[1]

    for point in path[2:]:
        p_new = point
        v = p_new - p_old
        angle = np.rad2deg(np.arctan2(v.y, v.x))
        transformation = kdb.DCplxTrans(1, angle, False, p.x, p.y)
        vector_top.append(transformation * ref_vector)
        vector_bot.append(transformation * kdb.DCplxTrans.R180 * ref_vector)
        p_old = p
        p = p_new

    vector_top.append(end_trans * ref_vector)
    vector_bot.append(end_trans * kdb.DCplxTrans.R180 * ref_vector)

    return [v.disp.to_p() for v in vector_top], [v.disp.to_p() for v in vector_bot]


def extrude_path(
    target: KCell,
    layer: LayerEnum | int,
    path: list[kdb.DPoint],
    width: float,
    enclosure: Optional["Enclosure"] = None,
    start_angle: Optional[float] = None,
    end_angle: Optional[float] = None,
) -> None:
    """
    Extrude a path from a list of points and a static width

    Args:
        target: the cell where to insert the shapes to (and get the database unit from)
        layer: the main layer that should be extruded
        path: list of floating-points points
        width: width in µm
        enclosure: optoinal enclosure object, specifying necessary layers.this will extrude around the `layer`
        start_angle: optionally specify a custom starting angle if `None` will be autocalculated from the first two elements
        end_angle: optionally specify a custom ending angle if `None` will be autocalculated from the last two elements
    """
    layer_list = {layer: LayerSection(sections=[Section(d_max=0)])}
    if enclosure is not None:
        if layer not in enclosure.layer_sections:
            layer_list |= enclosure.layer_sections
        else:
            ls = layer_list[layer].sections.copy()
            layer_list = enclosure.layer_sections.copy()
            layer_list[layer] = LayerSection(
                sections=list(layer_list[layer].sections) + [ls]
            )

    for layer, layer_sec in layer_list.items():
        reg = kdb.Region()
        for section in layer_sec.sections:
            _r = kdb.Region(
                path_pts_to_polygon(
                    *extrude_path_points(
                        path,
                        width + 2 * section.d_max * target.klib.dbu,
                        start_angle,
                        end_angle,
                    )
                ).to_itype(target.klib.dbu)
            )
            if section.d_min is not None:
                _r -= kdb.Region(
                    path_pts_to_polygon(
                        *extrude_path_points(
                            path,
                            width + 2 * section.d_min * target.klib.dbu,
                            start_angle,
                            end_angle,
                        )
                    ).to_itype(target.klib.dbu)
                )
            reg.insert(_r)
        target.shapes(layer).insert(reg.merge())


def extrude_path_dynamic_points(
    path: list[kdb.DPoint],
    widths: Callable[[float], float] | list[float],
    start_angle: Optional[float] = None,
    end_angle: Optional[float] = None,
) -> tuple[list[kdb.DPoint], list[kdb.DPoint]]:
    """
    Extrude a profile with a list of points and a list of widths

    Args:
        path: list of floating-points points
        width: function (from t==0 to t==1) defining a width profile for the path | list with width for the profile (needs same length as path)
        start_angle: optionally specify a custom starting angle if `None` will be autocalculated from the first two elements
        end_angle: optionally specify a custom ending angle if `None` will be autocalculated from the last two elements
    """
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

    if callable(widths):
        l = sum(((p2 - p1).abs() for p2, p1 in zip(path[:-1], path[1:])))
        z: float = 0
        ref_vector = kdb.DCplxTrans(kdb.DVector(0, widths(z / l) / 2))
        vector_top = [start_trans * ref_vector]
        vector_bot = [start_trans * kdb.DCplxTrans.R180 * ref_vector]
        p_old = path[0]
        p = path[1]
        z += (p - p_old).abs()
        for point in path[2:]:
            ref_vector = kdb.DCplxTrans(kdb.DVector(0, widths(z / l) / 2))
            p_new = point
            v = p_new - p_old
            angle = np.rad2deg(np.arctan2(v.y, v.x))
            transformation = kdb.DCplxTrans(1, angle, False, p.x, p.y)
            vector_top.append(transformation * ref_vector)
            vector_bot.append(transformation * kdb.DCplxTrans.R180 * ref_vector)
            z += (p_new - p).abs()
            p_old = p
            p = p_new
        ref_vector = kdb.DCplxTrans(kdb.DVector(0, widths(z / l) / 2))
    else:
        ref_vector = kdb.DCplxTrans(kdb.DVector(0, widths[0] / 2))
        vector_top = [start_trans * ref_vector]
        vector_bot = [start_trans * kdb.DCplxTrans.R180 * ref_vector]
        p_old = path[0]
        p = path[1]
        for point, w in zip(path[2:], widths[1:-1]):
            ref_vector = kdb.DCplxTrans(kdb.DVector(0, w / 2))
            p_new = point
            v = p_new - p_old
            angle = np.rad2deg(np.arctan2(v.y, v.x))
            transformation = kdb.DCplxTrans(1, angle, False, p.x, p.y)
            vector_top.append(transformation * ref_vector)
            vector_bot.append(transformation * kdb.DCplxTrans.R180 * ref_vector)
            p_old = p
            p = p_new
        ref_vector = kdb.DCplxTrans(kdb.DVector(0, widths[-1] / 2))
    vector_top.append(end_trans * ref_vector)
    vector_bot.append(end_trans * kdb.DCplxTrans.R180 * ref_vector)

    return [v.disp.to_p() for v in vector_top], [v.disp.to_p() for v in vector_bot]


def extrude_path_dynamic(
    target: KCell,
    layer: LayerEnum | int,
    path: list[kdb.DPoint],
    widths: Callable[[float], float] | list[float],
    enclosure: Optional["Enclosure"] = None,
    start_angle: Optional[float] = None,
    end_angle: Optional[float] = None,
) -> None:
    """
    Extrude a path with dynamic width from a list of points and a list of widths and add an enclosure if specified

    Args:
        target: the cell where to insert the shapes to (and get the database unit from)
        layer: the main layer that should be extruded
        path: list of floating-points points
        width: function (from t==0 to t==1) defining a width profile for the path | list with width for the profile (needs same length as path)
        enclosure: optoinal enclosure object, specifying necessary layers.this will extrude around the `layer`
        start_angle: optionally specify a custom starting angle if `None` will be autocalculated from the first two elements
        end_angle: optionally specify a custom ending angle if `None` will be autocalculated from the last two elements
    """

    layer_list = {layer: LayerSection(sections=[Section(d_max=0)])}
    if enclosure is not None:
        if layer not in enclosure.layer_sections:
            layer_list.update(enclosure.layer_sections)
        else:
            ls = layer_list[layer].sections.copy()
            layer_list = enclosure.layer_sections.copy()
            layer_list[layer] = LayerSection(
                sections=list(layer_list[layer].sections) + [ls]
            )
    if is_callable_widths(widths):
        for layer, layer_sec in layer_list.items():
            reg = kdb.Region()
            for section in layer_sec.sections:

                def w_max(x: float) -> float:
                    return widths(x) + 2 * section.d_max * target.klib.dbu  # type: ignore[operator]

                _r = kdb.Region(
                    path_pts_to_polygon(
                        *extrude_path_dynamic_points(
                            path,
                            w_max,
                            start_angle,
                            end_angle,
                        )
                    ).to_itype(target.klib.dbu)
                )
                if section.d_min is not None:

                    def w_min(x: float) -> float:
                        return widths(x) + 2 * section.d_min * target.klib.dbu  # type: ignore[operator]

                    _r -= kdb.Region(
                        path_pts_to_polygon(
                            *extrude_path_dynamic_points(
                                path,
                                w_min,
                                start_angle,
                                end_angle,
                            )
                        ).to_itype(target.klib.dbu)
                    )
                reg.insert(_r)
            target.shapes(layer).insert(reg.merge())

    else:
        for layer, layer_sec in layer_list.items():
            reg = kdb.Region()
            for section in layer_sec.sections:
                max_widths = [w + 2 * section.d_max * target.klib.dbu for w in widths]  # type: ignore[union-attr]
                _r = kdb.Region(
                    path_pts_to_polygon(
                        *extrude_path_dynamic_points(
                            path,
                            max_widths,
                            start_angle,
                            end_angle,
                        )
                    ).to_itype(target.klib.dbu)
                )
                if section.d_min is not None:
                    min_widths = [w + 2 * section.d_min * target.klib.dbu for w in widths]  # type: ignore[union-attr]
                    _r -= kdb.Region(
                        path_pts_to_polygon(
                            *extrude_path_dynamic_points(
                                path,
                                min_widths,
                                start_angle,
                                end_angle,
                            )
                        ).to_itype(target.klib.dbu)
                    )
                reg.insert(_r)
            target.shapes(layer).insert(reg.merge())


def path_pts_to_polygon(
    pts_top: list[kdb.DPoint], pts_bot: list[kdb.DPoint]
) -> kdb.DPolygon:
    pts_bot.reverse()
    return kdb.DPolygon(pts_top + pts_bot)


def is_Region(r: object) -> TypeGuard[kdb.Region]:
    return isinstance(r, kdb.Region)


def is_int(r: object) -> TypeGuard[int]:
    return isinstance(r, int)


def is_callable(r: object) -> TypeGuard[Callable[[float], float]]:
    return callable(r)


class Direction(Enum):
    X = 1
    Y = 2
    BOTH = 3


class Section(BaseModel):
    d_min: Optional[int] = None
    d_max: int

    def __hash__(self) -> int:
        return hash((self.d_min, self.d_max))


class LayerSection(BaseModel):
    sections: list[Section] = []

    def add_section(self, sec: Section) -> None:
        if not self.sections:
            self.sections.append(sec)
        else:
            i = 0
            if sec.d_min is not None:
                while i < len(self.sections) and sec.d_min > self.sections[i].d_max:
                    i += 1
                while i < len(self.sections) and sec.d_max >= self.sections[i].d_min:  # type: ignore[operator]
                    sec.d_max = max(self.sections[i].d_max, sec.d_max)
                    sec.d_min = min(self.sections[i].d_min, sec.d_min)  # type: ignore[type-var]
                    self.sections.pop(i)
                    if i == len(self.sections):
                        break
            self.sections.insert(i, sec)

    def __hash__(self) -> int:
        return hash(tuple((s.d_min, s.d_max) for s in self.sections))


class Enclosure(BaseModel):
    layer_sections: dict[LayerEnum | int, LayerSection]
    _name: Optional[str] = PrivateAttr(default=None)
    warn: bool = True

    main_layer: Optional[LayerEnum | int]

    yaml_tag: str = "!Enclosure"

    class Config:
        validate_assignment = True

    def __init__(
        self,
        sections: Sequence[
            tuple[LayerEnum | int, int] | tuple[LayerEnum | int, int, int]
        ] = [],
        name: Optional[str] = None,
        warn: bool = True,
        main_layer: Optional[LayerEnum | int] = None,
    ):
        super().__init__(
            warn=warn,
            layer_sections={},
            main_layer=main_layer,
        )

        self._name = name
        for sec in sorted(sections, key=lambda sec: (sec[0], sec[1])):
            if sec[0] in self.layer_sections:
                ls = self.layer_sections[sec[0]]
            else:
                ls = LayerSection()
                self.layer_sections[sec[0]] = ls
            ls.add_section(Section(d_max=sec[1])) if len(sec) < 3 else ls.add_section(
                Section(d_max=sec[2], d_min=sec[1])  # type:ignore[misc]
            )

    def __hash__(self) -> int:  # make hashable BaseModel subclass
        return hash(
            (str(self), self.main_layer, tuple(list(self.layer_sections.items())))
        )

    def __add__(self, other: "Enclosure") -> "Enclosure":

        enc = Enclosure()

        for layer, secs in self.layer_sections.items():
            for sec in secs.sections:
                enc.add_section(layer, sec)

        for layer, secs in other.layer_sections.items():
            for sec in secs.sections:
                enc.add_section(layer, sec)

        return enc

    def __iadd__(self, other: "Enclosure") -> "Enclosure":
        for layer, secs in other.layer_sections.items():
            for sec in secs.sections:
                self.add_section(layer, sec)
        return self

    def add_section(self, layer: LayerEnum | int, sec: Section) -> None:

        d = self.layer_sections

        if layer in self.layer_sections:
            d[layer].add_section(sec)
        else:
            d[layer] = LayerSection(sections=[sec])

        self.layer_sections = d  # trick pydantic to validate

    def minkowski_region(
        self,
        r: kdb.Region,
        d: Optional[int],
        shape: Callable[[int], list[kdb.Point] | kdb.Box | kdb.Edge | kdb.Polygon],
    ) -> kdb.Region:
        if d is None:
            return kdb.Region()
        elif d == 0:
            return r.dup()
        elif d > 0:
            return r.minkowski_sum(shape(d))
        else:
            _shape = shape(abs(d))
            if isinstance(_shape, list):
                box_shape = kdb.Polygon(_shape)
                bbox_maxsize = max(
                    box_shape.bbox().width(),
                    box_shape.bbox().height(),
                )
            else:
                bbox_maxsize = max(
                    _shape.bbox().width(),
                    _shape.bbox().height(),
                )
            bbox_r = kdb.Region(r.bbox().enlarged(bbox_maxsize))
            return r - (bbox_r - r).minkowski_sum(_shape)

    def apply_minkowski_enc(
        self,
        c: KCell,
        ref: Optional[int | kdb.Region],  # layer index or the region
        direction: Direction = Direction.BOTH,
    ) -> None:

        match direction:
            case Direction.BOTH:

                def box(d: int) -> kdb.Box:
                    return kdb.Box(-d, -d, d, d)

                self.apply_minkowski_custom(c, ref=ref, shape=box)

            case Direction.Y:

                def edge(d: int) -> kdb.Edge:
                    return kdb.Edge(0, -d, 0, d)

                self.apply_minkowski_custom(c, ref=ref, shape=edge)

            case Direction.X:

                def edge(d: int) -> kdb.Edge:
                    return kdb.Edge(-d, 0, d, 0)

                self.apply_minkowski_custom(c, ref=ref, shape=edge)

            case _:
                raise ValueError("Undefined direction")

    def apply_minkowski_y(
        self, c: KCell, ref: Optional[int | kdb.Region] = None
    ) -> None:
        return self.apply_minkowski_enc(c, ref=ref, direction=Direction.Y)

    def apply_minkowski_x(self, c: KCell, ref: Optional[int | kdb.Region]) -> None:
        return self.apply_minkowski_enc(c, ref=ref, direction=Direction.X)

    def apply_minkowski_custom(
        self,
        c: KCell,
        shape: Callable[[int], kdb.Edge | kdb.Polygon | kdb.Box],
        ref: Optional[int | kdb.Region] = None,
    ) -> None:
        if ref is None:
            ref = self.main_layer

        if ref is None:
            raise ValueError(
                "The enclosure doesn't have  a reference `main_layer` defined. Therefore the layer must be defined in calls"
            )
        r = kdb.Region(c.begin_shapes_rec(ref)) if isinstance(ref, int) else ref.dup()
        r.merge()

        for layer, layersec in self.layer_sections.items():
            for section in layersec.sections:
                c.shapes(layer).insert(
                    self.minkowski_region(r, section.d_max, shape)
                    - self.minkowski_region(r, section.d_min, shape)
                )

    def apply_custom(
        self,
        c: KCell,
        shape: Callable[
            [int, Optional[int]], kdb.Edge | kdb.Polygon | kdb.Box | kdb.Region
        ],
    ) -> None:
        for layer, layersec in self.layer_sections.items():
            for sec in layersec.sections:
                c.shapes(layer).insert(shape(sec.d_max, sec.d_min))

    def apply_bbox(self, c: KCell, ref: int | kdb.Region) -> None:
        if is_int(ref):
            _ref = c.bbox_per_layer(ref)
        elif is_Region(ref):
            _ref = ref.bbox()

        def bbox_reg(d_max: int, d_min: Optional[int] = None) -> kdb.Region:
            reg_max = kdb.Region(_ref)
            reg_max.size(d_max)
            if d_min is None:
                return reg_max
            reg_min = kdb.Region(_ref)
            reg_min.size(d_min)
            return reg_max - reg_min

        self.apply_custom(c, bbox_reg)

    @classmethod
    def to_yaml(cls, representer, node):  # type: ignore[no-untyped-def]
        d = dict(node.enclosures)
        return representer.represent_mapping(cls.yaml_tag, d)

    def __str__(self) -> str:
        if self._name is not None:
            return self._name
        list_to_hash: Any = [
            self.main_layer,
        ]
        for layer, layer_section in self.layer_sections.items():
            list_to_hash.append([str(layer), str(layer_section.sections)])
        return sha1(str(list_to_hash).encode("UTF-8")).hexdigest()[-8:]

    def extrude_path(
        self,
        c: KCell,
        path: list[kdb.DPoint],
        main_layer: Optional[int | LayerEnum],
        width: float,
    ) -> None:
        if main_layer is None:
            raise ValueError(
                "The enclosure doesn't have  a reference `main_layer` defined. Therefore the layer must be defined in calls"
            )
        extrude_path(target=c, layer=main_layer, path=path, width=width, enclosure=self)

    def extrude_path_dynamic(
        self,
        c: KCell,
        path: list[kdb.DPoint],
        main_layer: Optional[int | LayerEnum],
        widths: Callable[[float], float] | list[float],
    ) -> None:
        if main_layer is None:
            raise ValueError(
                "The enclosure doesn't have  a reference `main_layer` defined. Therefore the layer must be defined in calls"
            )
        extrude_path_dynamic(
            target=c, layer=main_layer, path=path, widths=widths, enclosure=self
        )
