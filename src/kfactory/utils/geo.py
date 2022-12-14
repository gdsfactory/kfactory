import warnings
from typing import Any, List, Sequence

import numpy as np
from numpy.typing import ArrayLike
from scipy.special import binom  # type: ignore[import]

from .. import kdb

__all__ = ["extrude_path"]


def is_manhattan(vector: kdb.Vector) -> bool:
    return bool(vector.x) ^ bool(vector.y)


def t_ang(t1: kdb.Trans, t2: kdb.Trans) -> int:
    return (t2.angle - t1.angle) % 4


def t_dist(t1: kdb.Trans, t2: kdb.Trans) -> float:
    return (t2.disp - t1.disp).abs()


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


def angles_rad(pts: ArrayLike) -> Any:
    """returns the angles (radians) of the connection between each point and the next"""
    _pts = np.roll(pts, -1, 0)
    return np.arctan2(_pts[:, 1] - pts[:, 1], _pts[:, 0] - pts[:, 0])


def angles_deg(pts: ArrayLike) -> Any:
    """returns the angles (degrees) of the connection between each point and the next"""
    return np.rad2deg(angles_rad(pts))


def snap_angle(a: int) -> int:
    """
    a: angle in deg
    Return angle snapped along manhattan angle
    """
    a %= 360
    if -45 < a < 45:
        return 0
    elif 45 < a < 135:
        return 90
    elif 135 < a < 225:
        return 180
    elif 225 < a < 315:
        return 270
    else:
        return 0


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


def extrude(
    points: list[kdb.DPoint],
    d: float,
) -> list[kdb.DPoint]:
    """Extrude a list of points. The orientation is the same as with edges in KLayout. a positive shift is outwards of the "edges". Where edges are represented by the concatenated points (e.g. kdb.DEdge(points[0],points[1]))

    Args:
        points: Backbone to be extruded
        d: distance in µm to the backbone
    """

    pts: list[kdb.DPoint] = []

    p_o = points[0]
    p = points[1]

    r90 = kdb.DTrans.R90

    v = p - p_o
    v90 = r90 * v * d / v.abs()

    pts.append(p_o + v90)

    for i in range(2, len(points)):
        p_n = points[i]
        v = p_n - p_o
        v90 = r90 * v * d / v.abs()
        pts.append(p + v90)
        p_o = p
        p = p_n

    v = p - p_o
    v90 = r90 * v * d / v.abs()
    pts.append(p + v90)

    return pts


def extrude_path(
    points: list[kdb.DPoint],
    width: float,
    snap_to_90: bool = True,
) -> list[kdb.DPoint]:
    points_tuple = extrude_path_separate(points, width, snap_to_90)
    points1 = points_tuple[0]
    points2 = points_tuple[1]
    points2.reverse()
    return points1 + points2


def extrude_path_separate(
    points: list[kdb.DPoint],
    width: float,
    snap_to_90: bool = True,
) -> tuple[list[kdb.DPoint], list[kdb.DPoint]]:
    """Extrude a Path

    Args:
        points: List of points. If the list is consisting of integer points and not list[DPoint] a conversion with dbu has to be done and `dbu` has to be specified
        width: width of the extrusion in `um`
        snap_to_90: snap the ends to 90° port like
        dbu: database unit used for conversion to integer variants and back

    Return:
        (points_side_1, points_side_2): Tuple containing both sides of the extrusion
    """

    Vec = kdb.DVector
    R90 = kdb.DTrans.R90

    p_o = points[0]
    p = points[1]

    v = p - p_o
    if snap_to_90:
        v = Vec(v.x, 0) if abs(v.x) > abs(v.y) else Vec(0, v.y)
    v = R90 * v * width / 2 / v.abs()

    points1 = [p_o + v]
    points2 = [(p_o.to_v() - v).to_p()]

    for i in range(2, len(points)):
        p_n = points[i]

        v = p_n - p_o
        v = R90 * v * width / 2 / v.abs()

        points1.append(p + v)
        points2.append((p.to_v() - v).to_p())

        p_o = p
        p = p_n

    v = p - p_o
    if snap_to_90:
        v = Vec(v.x, 0) if abs(v.x) > abs(v.y) else Vec(0, v.y)
    v = R90 * v * width / 2 / v.abs()

    points1.append(p_n + v)
    points2.append((p_n.to_v() - v).to_p())

    return points1, points2


def extrude_ipath_separate(
    points: list[kdb.Point], width: int, snap_to_90: bool = True, dbu: float = 1
) -> tuple[list[kdb.Point], list[kdb.Point]]:
    dpoints = extrude_path_separate(
        [p.to_dtype(dbu) for p in points],
        width * dbu,
        snap_to_90,
    )
    return [p.to_itype(dbu) for p in dpoints[0]], [p.to_itype(dbu) for p in dpoints[1]]


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
