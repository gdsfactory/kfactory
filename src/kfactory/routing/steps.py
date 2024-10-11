from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from pydantic import BaseModel, RootModel, conint

if TYPE_CHECKING:
    from .manhattan import ManhattanRouterSide


class Step(BaseModel, ABC):
    """Abstract base for a routing step."""

    size: conint(gt=0)  # type: ignore[valid-type]
    include_bend: bool = False

    @abstractmethod
    def execute(self, router: ManhattanRouterSide) -> None:
        """Executes the step."""
        ...


class Left(Step):
    def execute(self, router: ManhattanRouterSide) -> None:
        """Make the router turn left and go straight if necessary."""
        if self.include_bend:
            if self.size < 2 * router.router.bend90_radius:
                bend_radius = router.router.bend90_radius
                raise ValueError(
                    "If the next bend should be avoided the step needs to be bigger"
                    f" than {2 * bend_radius=}"
                )
            router.left()
            router.straight_nobend(self.size)
        else:
            if self.size < router.router.bend90_radius:
                bend_radius = router.router.bend90_radius
                raise ValueError(f"The step needs to be bigger than {bend_radius=}")
            router.left()
            router.straight(self.size)


class Right(Step):
    def execute(self, router: ManhattanRouterSide) -> None:
        if self.include_bend:
            if self.size < 2 * router.router.bend90_radius:
                bend_radius = router.router.bend90_radius
                raise ValueError(
                    "If the next bend should be avoided the step needs to be bigger"
                    f" than {2 * bend_radius=}"
                )
            router.right()
            router.straight_nobend(self.size)
        else:
            if self.size < router.router.bend90_radius:
                bend_radius = router.router.bend90_radius
                raise ValueError(f"The step needs to be bigger than {bend_radius=}")
            router.right()
            router.straight(self.size)


class Straight(Step):
    def execute(self, router: ManhattanRouterSide) -> None:
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
