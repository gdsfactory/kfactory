"""Classes used for steps in routers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Self

from pydantic import ConfigDict, RootModel, model_validator

from ..conf import ANGLE_180, ANGLE_270

if TYPE_CHECKING:
    from .manhattan import ManhattanRouterSide


@dataclass
class Step(ABC):
    """Abstract base for a routing step."""

    @abstractmethod
    def execute(self, router: ManhattanRouterSide, include_bend: bool) -> None:
        """Executes the step."""
        ...

    @property
    def include_bend(self) -> bool | None:
        """Whether the execute should leave space at the end of the step for a bend."""
        return None


@dataclass
class Left(Step):
    """Let the router go left.

    If a size is given, the router will continues that amount
    (including the added bend).
    If include_bend is true, the router will stop before the next bend needs to bed
    placed at size's point.
    """

    dist: int | None = None

    def execute(self, router: ManhattanRouterSide, include_bend: bool) -> None:
        """Make the router turn left and go straight if necessary."""
        ib = include_bend if self.include_bend is None else self.include_bend
        router.left()
        if self.dist:
            if ib:
                if (
                    self.dist is not None
                    and self.dist < 2 * router.router.bend90_radius
                ):
                    bend_radius = router.router.bend90_radius
                    raise ValueError(
                        "If the next bend should be avoided the step needs to be bigger"
                        f" than {2 * bend_radius=}"
                    )
                router.straight_nobend(self.dist)
            else:
                if self.dist < router.router.bend90_radius:
                    bend_radius = router.router.bend90_radius
                    raise ValueError(f"The step needs to be bigger than {bend_radius=}")
                router.straight(self.dist)


@dataclass
class Right(Step):
    """Let the router go right.

    If a size is given, the router will continues that amount
    (including the added bend).
    If include_bend is true, the router will stop before the next bend needs to bed
    placed at size's point.
    """

    dist: int | None = None

    def execute(self, router: ManhattanRouterSide, include_bend: bool) -> None:
        """Adds the bend and potential straight after."""
        ib = include_bend if self.include_bend is None else self.include_bend
        router.right()
        if self.dist:
            if ib:
                if self.dist < 2 * router.router.bend90_radius:
                    bend_radius = router.router.bend90_radius
                    raise ValueError(
                        "If the next bend should be avoided the step needs to be bigger"
                        f" than {2 * bend_radius=}"
                    )
                router.straight_nobend(self.dist)
            else:
                if self.dist < router.router.bend90_radius:
                    bend_radius = router.router.bend90_radius
                    raise ValueError(f"The step needs to be bigger than {bend_radius=}")
                router.straight(self.dist)


@dataclass
class Straight(Step):
    """Adds a straight section to the router."""

    dist: int | None = None

    def execute(self, router: ManhattanRouterSide, include_bend: bool) -> None:
        """Adds a straight section to the router."""
        ib = include_bend if self.include_bend is None else self.include_bend
        if self.dist:
            if ib:
                router.straight_nobend(self.dist)
            else:
                router.straight(self.dist)


@dataclass
class X(Step):
    """Go to an absolute X coordinate."""

    x: int

    def execute(self, router: ManhattanRouterSide, include_bend: bool) -> None:
        """Adds a straight section to the router."""
        ib = include_bend if self.include_bend is None else self.include_bend
        if router.t.angle % 2:
            raise ValueError(
                "Cannot go to position {self.x=}, because the router is currently "
                "going in the y direction with position "
                f"{(router.t.disp.x, router.t.disp.y)}"
            )
        if self.x:
            if ib:
                router.straight_nobend(self.x - router.t.disp.x)
            else:
                router.straight(self.x - router.t.disp.x)


@dataclass
class Y(Step):
    """Go to an absolute X coordinate."""

    y: int

    def execute(self, router: ManhattanRouterSide, include_bend: bool) -> None:
        """Adds a straight section to the router."""
        ib = include_bend if self.include_bend is None else self.include_bend
        if router.t.angle % 2 == 0:
            raise ValueError(
                "Cannot go to position {self.x=}, because the router is currently "
                "going in the y direction with position "
                f"{(router.t.disp.x, router.t.disp.y)}"
            )
        if self.y:
            if ib:
                router.straight_nobend(self.y - router.t.disp.y)
            else:
                router.straight(self.y - router.t.disp.y)


@dataclass
class XY(Step):
    """Go to an absolute XY coordinate."""

    x: int
    y: int

    def execute(self, router: ManhattanRouterSide, include_bend: bool) -> None:
        """Executes the step on a router."""
        ib = include_bend if self.include_bend is None else self.include_bend
        dx = self.x - router.t.disp.x
        dy = self.y - router.t.disp.y
        a = router.t.angle
        match a:
            case 0 | 2 if self.y == router.t.disp.x:
                sign = -1 if a == ANGLE_180 else 1
                if sign * dx < 0:
                    raise ValueError(
                        "XY step cannot go back. It is current pointing at 0"
                        " degrees.\n"
                        f"Current position: {router.t.disp!r}.\n"
                        f"Target Position ({self.x},{self.y})"
                    )
                    if ib:
                        router.straight_nobend(abs(dx))
                    else:
                        router.straight(abs(dx))
                if sign * dx < router.t.disp.x + router.router.bend90_radius:
                    raise ValueError("XY step cannot go back")
                router.straight_nobend(abs(dx))
                if self.y > router.t.disp.y:
                    if a == 0:
                        router.left()
                    else:
                        router.right()
                dy = self.y - router.t.disp.y
                if ib:
                    if abs(dy) < 0:
                        raise ValueError(
                            "XY's y-step is too small. It is current pointing"
                            f" at {router.t.angle * 90}"
                            " degrees.\n"
                            f"Current position: {router.t.disp!r}.\n"
                            f"Target Position ({self.x},{self.y})"
                        )
                    router.straight(abs(dy))
                else:
                    if abs(dy) < router.router.bend90_radius:
                        raise ValueError(
                            "XY's y-step is too small. It is current pointing"
                            f" at {router.t.angle * 90}"
                            " degrees.\n"
                            f"Current position: {router.t.disp!r}.\n"
                            f"Target Position ({self.x},{self.y})\n"
                            "Too small distance to place bend of "
                            f"{router.router.bend90_radius} size"
                        )
                    router.straight_nobend(abs(dy))

            case 1 | 3 if self.x == router.t.disp.x:
                sign = -1 if a == ANGLE_270 else 1
                if sign * dy < 0:
                    raise ValueError(
                        "XY step cannot go back. It is current pointing at 0"
                        " degrees.\n"
                        f"Current position: {router.t.disp!r}.\n"
                        f"Target Position ({self.x},{self.y})"
                    )
                if sign * dy < router.t.disp.y + router.router.bend90_radius:
                    raise ValueError("XY step cannot go back")
                router.straight_nobend(abs(dx))
                if self.x > router.t.disp.x:
                    if a == ANGLE_270:
                        router.left()
                    else:
                        router.right()
                dx = self.x - router.t.disp.x
                if ib:
                    if abs(dy) < 0:
                        raise ValueError(
                            "XY's y-step is too small. It is current pointing"
                            f" at {router.t.angle * 90}"
                            " degrees.\n"
                            f"Current position: {router.t.disp!r}.\n"
                            f"Target Position ({self.x},{self.y})"
                        )
                    router.straight(abs(dy))
                else:
                    if abs(dy) < router.router.bend90_radius:
                        raise ValueError(
                            "XY's y-step is too small. It is current pointing"
                            f" at {router.t.angle * 90}"
                            " degrees.\n"
                            f"Current position: {router.t.disp!r}.\n"
                            f"Target Position ({self.x},{self.y})\n"
                            "Too small distance to place bend of "
                            f"{router.router.bend90_radius} size"
                        )
                    router.straight_nobend(abs(dy))
            case _:
                ...


class Steps(RootModel[list[Any]]):
    """Collection of steps. Runs the execution on them."""

    root: list[Any]

    model_config = ConfigDict(arbitrary_types_allowed=True)

    @model_validator(mode="after")
    def _check_steps(self) -> Self:
        for step in self.root:
            if not isinstance(step, Step):
                raise TypeError(
                    "All Steps must implement an "
                    "'execute(self, router: ManhattanRouterSide, include_bend: bool)"
                )
        return self

    def execute(self, router: ManhattanRouterSide) -> None:
        """Run all the steps on the given router."""
        i = 0
        try:
            if self.root:
                for step in self.root[:-1]:
                    step.execute(router, True)
                i += 1
                step = self.root[-1]
                step.execute(router, False)
        except Exception as e:
            raise ValueError(f"Error in step {i}, {step=}. Error: {e!s}") from e
