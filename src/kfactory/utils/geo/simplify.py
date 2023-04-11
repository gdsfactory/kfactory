import numpy as np

from ... import kdb


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


def dsimplify(points: list[kdb.DPoint], tolerance: float) -> list[kdb.DPoint]:
    if len(points) < 3:
        return points
    simple_pts: list[kdb.DPoint] = [points[0]]

    start = 0
    last = len(points) - 1

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
