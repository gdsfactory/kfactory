import kfactory as kf
from collections.abc import Callable
from random import randint


def test_grid_1d(straight_factory: Callable[..., kf.KCell]) -> None:
    c = kf.KCell()

    kf.grid(
        c,
        kcells=[
            straight_factory(
                width=randint(500, 2_500) * 2, length=randint(2_000, 20_000)
            )
            for _ in range(10)
        ],
        spacing=5_000,
        align_x="xmin",
    )

    c.show()


def test_grid_2d(straight_factory: Callable[..., kf.KCell]) -> None:
    c = kf.KCell()

    kf.grid(
        c,
        kcells=[
            [
                straight_factory(
                    width=randint(500, 2_500) * 2, length=randint(2_000, 20_000)
                )
                for _ in range(10)
            ]
            for _ in range(2)
        ],
        spacing=5_000,
        align_x="center",
        align_y="ymax",
    )

    c.show()
