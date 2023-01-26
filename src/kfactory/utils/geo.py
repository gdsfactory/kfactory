import warnings
from typing import Any, Callable, List, Optional, Sequence, TypeGuard, overload

import numpy as np
from numpy.typing import ArrayLike
from scipy.special import binom  # type: ignore[import]

from .. import kdb
from ..kcell import KCell, LayerEnum
from .enclosure import Enclosure

__all__ = [
    "extrude_path",
    "extrude_path_points",
    "extrude_path_dynamic_points",
    "extrude_path_dynamic",
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
            warnings.warn(f"{v} is not a manhattan, cannot determine direction")
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

    if maxd <= tolerance:
        return [points[0], points[-1]]
    else:
        return (
            simplify(points[: ind_dist + 1], tolerance)
            + simplify(points[ind_dist:], tolerance)[1:]
        )

    return simple_pts


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

    ref_vector = kdb.DCplxTrans(kdb.DVector(0, width))
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
    layer: LayerEnum,
    path: list[kdb.DPoint],
    width: float,
    enclosure: Optional[Enclosure] = None,
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
    _layer_list: list[tuple[int, LayerEnum | int]] = (
        [(0, layer)] if enclosure is None else [(0, layer)] + enclosure.enclosures
    )
    for d, _layer in _layer_list:
        p_top, p_bot = extrude_path_points(
            path, width + 2 * d * target.library.dbu, start_angle, end_angle
        )
        p_bot.reverse()
        target.shapes(_layer).insert(kdb.DPolygon(p_top + p_bot))


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
        ref_vector = kdb.DCplxTrans(kdb.DVector(0, widths(z / l)))
        vector_top = [start_trans * ref_vector]
        vector_bot = [start_trans * kdb.DCplxTrans.R180 * ref_vector]
        p_old = path[0]
        p = path[1]
        z += (p - p_old).abs()
        for point in path[2:]:
            ref_vector = kdb.DCplxTrans(kdb.DVector(0, widths(z / l)))
            p_new = point
            v = p_new - p_old
            angle = np.rad2deg(np.arctan2(v.y, v.x))
            transformation = kdb.DCplxTrans(1, angle, False, p.x, p.y)
            vector_top.append(transformation * ref_vector)
            vector_bot.append(transformation * kdb.DCplxTrans.R180 * ref_vector)
            z += (p_new - p).abs()
            p_old = p
            p = p_new
        ref_vector = kdb.DCplxTrans(kdb.DVector(0, widths(z / l)))
        vector_top.append(end_trans * ref_vector)
        vector_bot.append(end_trans * kdb.DCplxTrans.R180 * ref_vector)

    else:
        ref_vector = kdb.DCplxTrans(kdb.DVector(0, widths[0]))
        vector_top = [start_trans * ref_vector]
        vector_bot = [start_trans * kdb.DCplxTrans.R180 * ref_vector]
        p_old = path[0]
        p = path[1]
        for point, w in zip(path[2:], widths[1:-1]):
            ref_vector = kdb.DCplxTrans(kdb.DVector(0, w))
            p_new = point
            v = p_new - p_old
            angle = np.rad2deg(np.arctan2(v.y, v.x))
            transformation = kdb.DCplxTrans(1, angle, False, p.x, p.y)
            vector_top.append(transformation * ref_vector)
            vector_bot.append(transformation * kdb.DCplxTrans.R180 * ref_vector)
            p_old = p
            p = p_new
        ref_vector = kdb.DCplxTrans(kdb.DVector(0, widths[-1]))
        vector_top.append(end_trans * ref_vector)
        vector_bot.append(end_trans * kdb.DCplxTrans.R180 * ref_vector)

    return [v.disp.to_p() for v in vector_top], [v.disp.to_p() for v in vector_bot]


def extrude_path_dynamic(
    target: KCell,
    layer: LayerEnum,
    path: list[kdb.DPoint],
    widths: Callable[[float], float] | list[float],
    enclosure: Optional[Enclosure] = None,
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

    _layer_list: list[tuple[int, LayerEnum | int]] = (
        [(0, layer)] if enclosure is None else [(0, layer)] + enclosure.enclosures
    )
    if is_callable_widths(widths):
        for d, _layer in _layer_list:

            def d_widths(x: float) -> float:
                return widths(x) + 2 * d * target.library.dbu  # type: ignore[no-any-return, operator]

            p_top, p_bot = extrude_path_dynamic_points(
                path, d_widths, start_angle, end_angle
            )
            p_bot.reverse()
            target.shapes(_layer).insert(kdb.DPolygon(p_top + p_bot))
    else:
        for d, _layer in _layer_list:
            _widths = [w + d * target.library.dbu for w in widths]  # type: ignore[union-attr]
            p_top, p_bot = extrude_path_dynamic_points(
                path, _widths, start_angle, end_angle
            )
            p_bot.reverse()
            target.shapes(_layer).insert(kdb.DPolygon(p_top + p_bot))
