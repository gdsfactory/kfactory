"""Classes used for steps in routers."""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import ConfigDict, RootModel, dataclasses

if TYPE_CHECKING:
    from .manhattan import ManhattanRouterSide


@dataclasses.dataclass
class Step:
    """Abstract base for a routing step."""

    model_config = ConfigDict(extra="allow")

    include_bend: bool | None = None

    def execute(self, router: ManhattanRouterSide, include_bend: bool) -> None:
        """Executes the step."""
        raise NotImplementedError(
            "This function must be implemented in the child class."
        )


@dataclasses.dataclass
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
        _ib = include_bend if self.include_bend is None else self.include_bend
        router.left()
        if self.dist:
            if _ib:
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


@dataclasses.dataclass
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
        _ib = include_bend if self.include_bend is None else self.include_bend
        router.right()
        if self.dist:
            if _ib:
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


@dataclasses.dataclass
class Straight(Step):
    """Adds a straight section to the router."""

    dist: int | None = None

    def execute(self, router: ManhattanRouterSide, include_bend: bool) -> None:
        """Adds a straight section to the router."""
        _ib = include_bend if self.include_bend is None else self.include_bend
        if self.dist:
            if _ib:
                router.straight_nobend(self.dist)
            else:
                router.straight(self.dist)


@dataclasses.dataclass(kw_only=True)
class X(Step):
    """Go to an absolute X coordinate."""

    x: int

    def execute(self, router: ManhattanRouterSide, include_bend: bool) -> None:
        """Adds a straight section to the router."""
        _ib = include_bend if self.include_bend is None else self.include_bend
        if router.t.angle % 2:
            raise ValueError(
                "Cannot go to position {self.x=}, because the router is currently "
                "going in the y direction with position "
                f"{(router.t.disp.x, router.t.disp.y)}"
            )
        if self.x:
            if _ib:
                router.straight_nobend(self.x - router.t.disp.x)
            else:
                router.straight(self.x - router.t.disp.x)


@dataclasses.dataclass(kw_only=True)
class Y(Step):
    """Go to an absolute X coordinate."""

    y: int

    def execute(self, router: ManhattanRouterSide, include_bend: bool) -> None:
        """Adds a straight section to the router."""
        _ib = include_bend if self.include_bend is None else self.include_bend
        if router.t.angle % 2 == 0:
            raise ValueError(
                "Cannot go to position {self.x=}, because the router is currently "
                "going in the y direction with position "
                f"{(router.t.disp.x, router.t.disp.y)}"
            )
        if self.y:
            if _ib:
                router.straight_nobend(self.y - router.t.disp.y)
            else:
                router.straight(self.y - router.t.disp.y)


class Steps(RootModel[list[Step]]):
    """Collection of steps. Runs the execution on them."""

    root: list[Step]

    def execute(self, router: ManhattanRouterSide) -> None:
        """Run all the steps on the given router."""
        try:
            i = 0
            for i, step in enumerate(self.root[:-1]):
                step.execute(router, True)
            i += i
            step.execute(router, False)
        except Exception as e:
            raise ValueError(f"Error in step {i}, {step=}. Error: {str(e)}") from e
