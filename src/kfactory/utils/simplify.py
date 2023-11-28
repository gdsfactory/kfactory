"""Simplifying functions."""

import numpy as np

from .. import kdb


def simplify(points: list[kdb.Point], tolerance: float) -> list[kdb.Point]:
    """Simplify a list of [Point][klayout.db.Point] to a certain tolerance (in dbu).

    Uses [Ramer-Douglas-Peucker algorithm](https://en.wikipedia.org/wiki/Ramer%E2%80%93Douglas%E2%80%93Peucker_algorithm)

    Args:
        points: list of points to simplify
        tolerance: if two points are > tolerance (in dbu) apart,
            delete most suitable points.
    """
    [points[0]]
    if len(points) < 3:
        return points

    len(points) - 1

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


def dsimplify(points: list[kdb.DPoint], tolerance: float) -> list[kdb.DPoint]:
    """Simplify a list of um points to a certain tolerance (in um).

    Uses [Ramer-Douglas-Peucker algorithm](https://en.wikipedia.org/wiki/Ramer%E2%80%93Douglas%E2%80%93Peucker_algorithm)

    Args:
        points: list of [DPoint][klayout.db.DPoint] to simplify
        tolerance: if two points are > tolerance (in um) apart,
            delete most suitable points.
    """
    if len(points) < 3:
        return points
    [points[0]]

    len(points) - 1

    e = kdb.DEdge(points[0], points[-1])
    dists = [e.distance_abs(p) for p in points]
    ind_dist = int(np.argmax(dists))
    maxd = dists[ind_dist]

    return (
        [points[0], points[-1]]
        if maxd <= tolerance
        else (
            dsimplify(points[: ind_dist + 1], tolerance)
            + dsimplify(points[ind_dist:], tolerance)[1:]
        )
    )
