import kfactory as kf
import pytest
from collections.abc import Callable
from random import randint, uniform


def test_grid_1d(straight_factory: Callable[..., kf.KCell]) -> None:
    c = kf.KCell()

    kf.grid(
        c,
        kcells=[
            straight_factory(
                width=round(uniform(0.5, 2.5), 3) * 2, length=round(uniform(2, 20), 3)
            )
            for _ in range(10)
        ],
        spacing=5,
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
                    width=round(uniform(0.5, 2.5), 3) * 2,
                    length=round(uniform(2, 20), 3),
                )
                for _ in range(10)
            ]
            for _ in range(2)
        ],
        spacing=5,
        align_x="center",
        align_y="ymax",
    )

    c.show()


def test_grid_2d_shape(straight_factory: Callable[..., kf.KCell]) -> None:
    c = kf.KCell()

    kf.grid(
        c,
        kcells=[
            [
                straight_factory(
                    width=round(uniform(0.5, 2.5), 3) * 2,
                    length=round(uniform(2, 20), 3),
                )
                for _ in range(10)
            ]
            for _ in range(2)
        ],
        spacing=5,
        align_x="origin",
        align_y="center",
        shape=(4, 5),
    )

    c.show()


def test_grid_2d_shape_toosmall(straight_factory: Callable[..., kf.KCell]) -> None:
    with pytest.raises(ValueError):
        c = kf.KCell()

        kf.grid(
            c,
            kcells=[
                [
                    straight_factory(
                        width=round(uniform(0.5, 2.5), 3) * 2,
                        length=round(uniform(2, 20), 3),
                    )
                    for _ in range(10)
                ]
                for _ in range(2)
            ],
            spacing=5,
            align_x="origin",
            align_y="center",
            shape=(4, 4),
        )


# def test_grid_flex_1d(straight_factory: Callable[..., kf.KCell]) -> None:
#     c = kf.KCell()

#     kf.grid(
#         c,
#         kcells=[
#             straight_factory(
#                 width=randint(500, 2_500) * 2, length=randint(2_000, 20_000)
#             )
#             for _ in range(10)
#         ],
#         spacing=5_000,
#         align_x="xmin",
#     )

#     c.show()


# def test_grid_2d(straight_factory: Callable[..., kf.KCell]) -> None:
#     c = kf.KCell()

#     kf.grid(
#         c,
#         kcells=[
#             [
#                 straight_factory(
#                     width=randint(500, 2_500) * 2, length=randint(2_000, 20_000)
#                 )
#                 for _ in range(10)
#             ]
#             for _ in range(2)
#         ],
#         spacing=5_000,
#         align_x="center",
#         align_y="ymax",
#     )

#     c.show()


# def test_grid_2d_shape(straight_factory: Callable[..., kf.KCell]) -> None:
#     c = kf.KCell()

#     kf.grid(
#         c,
#         kcells=[
#             [
#                 straight_factory(
#                     width=randint(500, 2_500) * 2, length=randint(2_000, 20_000)
#                 )
#                 for _ in range(10)
#             ]
#             for _ in range(2)
#         ],
#         spacing=5_000,
#         align_x="origin",
#         align_y="center",
#         shape=(4, 5),
#     )

#     c.show()


# def test_grid_2d_shape_toosmall(straight_factory: Callable[..., kf.KCell]) -> None:
#     with pytest.raises(ValueError):
#         c = kf.KCell()

#         kf.grid(
#             c,
#             kcells=[
#                 [
#                     straight_factory(
#                         width=randint(500, 2_500) * 2, length=randint(2_000, 20_000)
#                     )
#                     for _ in range(10)
#                 ]
#                 for _ in range(2)
#             ],
#             spacing=5_000,
#             align_x="origin",
#             align_y="center",
#             shape=(4, 4),
#         )
