import klayout.db as kdb

from kfactory.utils.simplify import dsimplify, simplify


def test_simplify() -> None:
    points = [kdb.DPoint(0, 0), kdb.DPoint(1, 1), kdb.DPoint(2, 2)]
    simplified = dsimplify(points, 0.1)
    assert len(simplified) == 2


def test_simplify_2() -> None:
    points = [kdb.Point(0, 0), kdb.Point(1, 1), kdb.Point(2, 2)]
    simplified = simplify(points, 0.1)
    assert len(simplified) == 2


def test_simplify_complex() -> None:
    points = [
        kdb.DPoint(0, 0),
        kdb.DPoint(1, 0),
        kdb.DPoint(1, 1),
        kdb.DPoint(2, 1),
        kdb.DPoint(2, 0),
        kdb.DPoint(3, 0),
        kdb.DPoint(3, 3),
        kdb.DPoint(0, 3),
    ]
    tolerance = 0.5
    simplified = dsimplify(points, tolerance)
    assert simplified == [
        kdb.DPoint(0, 0),
        kdb.DPoint(1, 0),
        kdb.DPoint(1, 1),
        kdb.DPoint(3, 0),
        kdb.DPoint(3, 3),
        kdb.DPoint(0, 3),
    ]


def test_simplify_with_tolerance() -> None:
    points = [
        kdb.DPoint(0, 0),
        kdb.DPoint(0.1, 0.1),
        kdb.DPoint(0.2, 0.2),
        kdb.DPoint(1, 1),
        kdb.DPoint(2, 2),
        kdb.DPoint(3, 3),
    ]
    tolerance = 0.15
    simplified = dsimplify(points, tolerance)
    assert simplified == [
        kdb.DPoint(0, 0),
        kdb.DPoint(3, 3),
    ]


def test_simplify_empty() -> None:
    points: list[kdb.Point] = []
    simplified = simplify(points, 0.1)
    assert simplified == []


def test_dsimplify_empty() -> None:
    points: list[kdb.DPoint] = []
    simplified = dsimplify(points, 0.1)
    assert simplified == []


def test_simplify_single_point() -> None:
    points = [kdb.DPoint(0, 0)]
    simplified = dsimplify(points, 0.1)
    assert simplified == points
