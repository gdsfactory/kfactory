import warnings
from typing import (
    Any,
    Callable,
    Dict,
    Hashable,
    List,
    Literal,
    Optional,
    Sequence,
    Union,
    overload,
)

import numpy as np
from numpy.typing import ArrayLike
from scipy.special import binom  # type: ignore[import]

from .. import kdb

__all__ = ["extrude_path"]

RAD2DEG = 180 / np.pi
DEG2RAD = 1 / 180 * np.pi


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
    return angles_rad(pts) * RAD2DEG


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


# def extrude_path_old(
#     points,
#     width,
#     with_manhattan_facing_angles=True,
#     spike_length=0,
#     start_angle=None,
#     end_angle=None,
#     auto_offset_to_snap=False,
#     width2=None,
#     grid=1,
# ):
#     """
#     Extrude a path of width `width` along a curve defined by `points`

#     Args:
#         points: numpy 2D array of shape (N, 2)
#         width: float
#         auto_offset_to_snap: necessary for some structures where an odd nm
#             value is needed for the width e.g on 5nm grid size structures
#             In that case, also returns the offset to help with port positioning

#     Return
#         numpy 2D array of shape (2*N, 2)
#     """

#     width2 = width2 or width

#     if type(points) == list:
#         points = np.stack([(p.x, p.y) for p in points], axis=0)

#     n_points = points.shape[0]

#     a = angles_deg(points)
#     if with_manhattan_facing_angles:
#         _start_angle = snap_angle(a[0] + 180)
#         _end_angle = snap_angle(a[-2])
#     else:
#         _start_angle = a[0] + 180
#         _end_angle = a[-2]

#     if start_angle == None:
#         start_angle = _start_angle

#     if end_angle == None:
#         end_angle = _end_angle

#     a2 = angles_rad(points) * 0.5
#     a1 = np.roll(a2, 1)

#     a2[-1] = end_angle * DEG2RAD - a2[-2]
#     a1[0] = start_angle * DEG2RAD - a1[1]

#     a_plus = a2 + a1
#     cos_a_min = np.cos(a2 - a1)
#     widths = np.linspace(width, width2, n_points)
#     offsets = (
#         np.column_stack((-np.sin(a_plus) / cos_a_min, np.cos(a_plus) / cos_a_min)) * 0.5
#     )

#     offsets[:, 0] = offsets[:, 0] * widths
#     offsets[:, 1] = offsets[:, 1] * widths

#     points_forward = points + offsets
#     points_back = np.flipud(points - offsets)

#     if auto_offset_to_snap:
#         """
#         Automatically tweak all the points such that start and end port points fall
#         on grid
#         """
#         _p_start = points_forward[0]
#         _p_end = points_forward[-1]
#         dp_start = np.round(_p_start / grid) * grid - _p_start
#         dp_end = np.round(_p_end / grid) * grid - _p_end
#         _n = len(points_forward)
#         ddp = dp_end - dp_start
#         dps = np.array([ddp * i / (_n - 1) for i in range(_n)]) + dp_start
#         points_forward += dps
#         points_back += np.flipud(dps)

#     if spike_length != 0:
#         d = spike_length
#         a_start = start_angle * DEG2RAD
#         a_end = end_angle * DEG2RAD
#         p_start_spike = points[0] + d * np.array([[np.cos(a_start), np.sin(a_start)]])
#         p_end_spike = points[-1] + d * np.array([[np.cos(a_end), np.sin(a_end)]])

#         pts = np.vstack((p_start_spike, points_forward, p_end_spike, points_back))
#     else:
#         pts = np.vstack((points + offsets, points_back))

#     pts = np.round(pts / grid) * grid
#     if auto_offset_to_snap:
#         return pts, dps

#     return pts


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
