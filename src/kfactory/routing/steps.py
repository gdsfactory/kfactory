from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, RootModel

if TYPE_CHECKING:
    from .manhattan import ManhattanRouterSide


class Step(BaseModel):
    """Abstract base for a routing step."""

    model_config = ConfigDict(extra="allow")

    size: int | None = None
    include_bend: bool = False

    def execute(self, router: ManhattanRouterSide) -> None:
        """Executes the step."""
        raise NotImplementedError(
            "This function must be implemented in the child class."
        )


class Left(Step):
    def execute(self, router: ManhattanRouterSide) -> None:
        """Make the router turn left and go straight if necessary."""
        router.left()
        if self.size:
            if self.include_bend:
                if (
                    self.size is not None
                    and self.size < 2 * router.router.bend90_radius
                ):
                    bend_radius = router.router.bend90_radius
                    raise ValueError(
                        "If the next bend should be avoided the step needs to be bigger"
                        f" than {2 * bend_radius=}"
                    )
                router.straight_nobend(self.size)
            else:
                if self.size < router.router.bend90_radius:
                    bend_radius = router.router.bend90_radius
                    raise ValueError(f"The step needs to be bigger than {bend_radius=}")
                router.straight(self.size)


class Right(Step):
    def execute(self, router: ManhattanRouterSide) -> None:
        router.right()
        if self.size:
            if self.include_bend:
                if self.size < 2 * router.router.bend90_radius:
                    bend_radius = router.router.bend90_radius
                    raise ValueError(
                        "If the next bend should be avoided the step needs to be bigger"
                        f" than {2 * bend_radius=}"
                    )
                router.straight_nobend(self.size)
            else:
                if self.size < router.router.bend90_radius:
                    bend_radius = router.router.bend90_radius
                    raise ValueError(f"The step needs to be bigger than {bend_radius=}")
                router.straight(self.size)


class Straight(Step):
    def execute(self, router: ManhattanRouterSide) -> None:
        if self.size:
            if self.include_bend:
                router.straight_nobend(self.size)
            else:
                router.straight(self.size)


class Steps(RootModel[list[Step]]):
    root: list[Step]

    def execute(self, router: ManhattanRouterSide) -> None:
        try:
            for i, step in enumerate(self.root):
                step.execute(router)
        except Exception as e:
            raise ValueError(f"Error in step {i}, {step=}. Error: {str(e)}") from e
