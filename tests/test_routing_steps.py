"""Tests for kfactory.routing.steps module."""

from __future__ import annotations

import pytest

from kfactory import kdb
from kfactory.routing.manhattan import ManhattanRouter
from kfactory.routing.steps import (
    XY,
    Left,
    Right,
    Step,
    Steps,
    Straight,
    X,
    Y,
)


def _make_router(
    bend90_radius: int = 1000,
    start: kdb.Trans | None = None,
    end: kdb.Trans | None = None,
) -> ManhattanRouter:
    return ManhattanRouter(
        bend90_radius=bend90_radius,
        separation=200,
        start_transformation=start or kdb.Trans(0, False, 0, 0),
        end_transformation=end or kdb.Trans(2, False, 50_000, 0),
    )


def test_step_is_abstract() -> None:
    with pytest.raises(TypeError):
        Step()  # type: ignore[abstract]


def test_left_no_dist_executes() -> None:
    router = _make_router()
    start_angle = router.start.t.angle
    Left().execute(router.start, include_bend=False)
    # Left turn rotates +1 mod 4
    assert router.start.t.angle == (start_angle + 1) % 4


def test_left_with_dist_executes() -> None:
    router = _make_router()
    Left(dist=5000).execute(router.start, include_bend=False)
    # After left + straight 5000 from origin facing +x, we are facing +y
    assert router.start.t.angle == 1


def test_left_dist_too_small_raises() -> None:
    router = _make_router(bend90_radius=2000)
    with pytest.raises(ValueError, match="bigger than"):
        Left(dist=100).execute(router.start, include_bend=False)


def test_left_include_bend_too_small_raises() -> None:
    router = _make_router(bend90_radius=2000)
    with pytest.raises(ValueError, match="bigger than"):
        Left(dist=2000).execute(router.start, include_bend=True)


def test_left_include_bend_ok() -> None:
    router = _make_router(bend90_radius=1000)
    Left(dist=10_000).execute(router.start, include_bend=True)
    assert router.start.t.angle == 1


def test_right_no_dist_executes() -> None:
    router = _make_router()
    Right().execute(router.start, include_bend=False)
    assert router.start.t.angle == 3


def test_right_with_dist_executes() -> None:
    router = _make_router()
    Right(dist=5000).execute(router.start, include_bend=False)
    assert router.start.t.angle == 3


def test_right_dist_too_small_raises() -> None:
    router = _make_router(bend90_radius=2000)
    with pytest.raises(ValueError, match="bigger than"):
        Right(dist=100).execute(router.start, include_bend=False)


def test_right_include_bend_too_small_raises() -> None:
    router = _make_router(bend90_radius=2000)
    with pytest.raises(ValueError, match="bigger than"):
        Right(dist=2000).execute(router.start, include_bend=True)


def test_right_include_bend_ok() -> None:
    router = _make_router(bend90_radius=1000)
    Right(dist=10_000).execute(router.start, include_bend=True)
    assert router.start.t.angle == 3


def test_straight_no_dist_noop() -> None:
    router = _make_router()
    pos_before = router.start.t.disp
    Straight().execute(router.start, include_bend=False)
    assert router.start.t.disp == pos_before


def test_straight_with_dist() -> None:
    router = _make_router()
    x_before = router.start.t.disp.x
    Straight(dist=5000).execute(router.start, include_bend=False)
    assert router.start.t.disp.x == x_before + 5000


def test_straight_with_dist_include_bend() -> None:
    router = _make_router(bend90_radius=1000)
    x_before = router.start.t.disp.x
    Straight(dist=5000).execute(router.start, include_bend=True)
    # straight_nobend subtracts the bend radius
    assert router.start.t.disp.x == x_before + 4000


def test_x_step_goes_along_x() -> None:
    router = _make_router()
    X(x=5000).execute(router.start, include_bend=False)
    assert router.start.t.disp.x == 5000


def test_x_step_zero_noop() -> None:
    router = _make_router()
    pos_before = router.start.t.disp
    X(x=0).execute(router.start, include_bend=False)
    assert router.start.t.disp == pos_before


def test_x_step_wrong_angle_raises() -> None:
    # angle 1 is +y direction, X step should error
    router = _make_router(start=kdb.Trans(1, False, 0, 0))
    with pytest.raises(ValueError, match="Cannot go to position"):
        X(x=5000).execute(router.start, include_bend=False)


def test_x_step_include_bend() -> None:
    router = _make_router(bend90_radius=1000)
    X(x=5000).execute(router.start, include_bend=True)
    # straight_nobend subtracts bend radius
    assert router.start.t.disp.x == 4000


def test_y_step_goes_along_y() -> None:
    router = _make_router(start=kdb.Trans(1, False, 0, 0))
    Y(y=5000).execute(router.start, include_bend=False)
    assert router.start.t.disp.y == 5000


def test_y_step_zero_noop() -> None:
    router = _make_router(start=kdb.Trans(1, False, 0, 0))
    pos_before = router.start.t.disp
    Y(y=0).execute(router.start, include_bend=False)
    assert router.start.t.disp == pos_before


def test_y_step_wrong_angle_raises() -> None:
    # angle 0 is +x direction, Y step should error
    router = _make_router()
    with pytest.raises(ValueError, match="Cannot go to position"):
        Y(y=5000).execute(router.start, include_bend=False)


def test_y_step_include_bend() -> None:
    router = _make_router(start=kdb.Trans(1, False, 0, 0), bend90_radius=1000)
    Y(y=5000).execute(router.start, include_bend=True)
    assert router.start.t.disp.y == 4000


def test_xy_step_falls_through_default() -> None:
    # If neither case matches, the step is essentially a no-op
    router = _make_router()
    pos_before = router.start.t.disp
    XY(x=5000, y=2000).execute(router.start, include_bend=False)
    assert router.start.t.disp == pos_before


def test_steps_collection_executes() -> None:
    router = _make_router()
    steps = Steps([Straight(dist=2000), Left(), Straight(dist=2000)])
    steps.execute(router.start)
    # after Left followed by Straight, x stays at 2000+bend, angle 1
    assert router.start.t.angle == 1


def test_steps_invalid_member_raises() -> None:
    with pytest.raises(TypeError, match="must implement"):
        Steps([object()])


def test_steps_propagates_error_with_step_index() -> None:
    router = _make_router(bend90_radius=2000)
    steps = Steps([Straight(dist=5000), Left(dist=100)])
    with pytest.raises(ValueError, match="Error in step"):
        steps.execute(router.start)


def test_steps_empty_runs() -> None:
    router = _make_router()
    pos_before = router.start.t.disp
    Steps([]).execute(router.start)
    assert router.start.t.disp == pos_before


def test_step_include_bend_default_property() -> None:
    s = Left()
    assert s.include_bend is None
