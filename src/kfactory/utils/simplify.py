"""Simplifying functions."""

from typing import cast

import numpy as np

from kfactory.conf import MIN_POINTS_FOR_SIMPLIFY

from .. import kdb

_DSIMPLIFY_ARRAY_THRESHOLD = 256


def _simplify_from_arrays(
    points: list[kdb.Point] | list[kdb.DPoint],
    tolerance: float,
) -> list[kdb.Point] | list[kdb.DPoint]:
    xs = np.fromiter((p.x for p in points), dtype=np.float64, count=len(points))
    ys = np.fromiter((p.y for p in points), dtype=np.float64, count=len(points))
    indices = _simplify_indices(xs, ys, 0, len(points) - 1, tolerance)
    return cast("list[kdb.Point] | list[kdb.DPoint]", [points[i] for i in indices])


def _simplify_indices(
    xs: np.ndarray,
    ys: np.ndarray,
    start: int,
    end: int,
    tolerance: float,
) -> list[int]:
    if end - start + 1 < MIN_POINTS_FOR_SIMPLIFY:
        return list(range(start, end + 1))

    dx = xs[end] - xs[start]
    dy = ys[end] - ys[start]
    norm = np.hypot(dx, dy)
    if norm == 0:
        xs_ = xs[start : end + 1]
        ys_ = ys[start : end + 1]
        dists = np.hypot(xs_ - xs[start], ys_ - ys[start])
        ind_dist = start + int(np.argmax(dists))
        maxd = float(dists[ind_dist - start])
        return (
            [start, end]
            if maxd <= tolerance
            else _simplify_indices(xs, ys, start, ind_dist, tolerance)
            + _simplify_indices(xs, ys, ind_dist, end, tolerance)[1:]
        )

    xs_ = xs[start : end + 1]
    ys_ = ys[start : end + 1]
    dists = np.abs(dy * xs_ - dx * ys_ + xs[end] * ys[start] - ys[end] * xs[start])
    ind_dist = start + int(np.argmax(dists))
    maxd = float(dists[ind_dist - start] / norm)

    return (
        [start, end]
        if maxd <= tolerance
        else _simplify_indices(xs, ys, start, ind_dist, tolerance)
        + _simplify_indices(xs, ys, ind_dist, end, tolerance)[1:]
    )


def _dsimplify_with_edge(
    points: list[kdb.DPoint], tolerance: float
) -> list[kdb.DPoint]:
    if len(points) < MIN_POINTS_FOR_SIMPLIFY:
        return points

    e = kdb.DEdge(points[0], points[-1])
    dists = [e.distance_abs(p) for p in points]
    ind_dist = int(np.argmax(dists))
    maxd = dists[ind_dist]

    return (
        [points[0], points[-1]]
        if maxd <= tolerance
        else (
            _dsimplify_with_edge(points[: ind_dist + 1], tolerance)
            + _dsimplify_with_edge(points[ind_dist:], tolerance)[1:]
        )
    )


def simplify(points: list[kdb.Point], tolerance: float) -> list[kdb.Point]:
    """Simplify a list of `klayout.db.Point` to a certain tolerance (in dbu).

    Uses [Ramer-Douglas-Peucker algorithm](https://en.wikipedia.org/wiki/Ramer%E2%80%93Douglas%E2%80%93Peucker_algorithm)

    Args:
        points: list of points to simplify
        tolerance: if two points are > tolerance (in dbu) apart,
            delete most suitable points.
    """
    if len(points) < MIN_POINTS_FOR_SIMPLIFY:
        return points

    return cast("list[kdb.Point]", _simplify_from_arrays(points, tolerance))


def dsimplify(points: list[kdb.DPoint], tolerance: float) -> list[kdb.DPoint]:
    """Simplify a list of um points to a certain tolerance (in um).

    Uses [Ramer-Douglas-Peucker algorithm](https://en.wikipedia.org/wiki/Ramer%E2%80%93Douglas%E2%80%93Peucker_algorithm)

    Args:
        points: list of `klayout.db.DPoint` to simplify
        tolerance: if two points are > tolerance (in um) apart,
            delete most suitable points.
    """
    if len(points) < MIN_POINTS_FOR_SIMPLIFY:
        return points

    if len(points) < _DSIMPLIFY_ARRAY_THRESHOLD:
        return _dsimplify_with_edge(points, tolerance)
    return cast("list[kdb.DPoint]", _simplify_from_arrays(points, tolerance))
