from collections.abc import Callable
from random import randint, uniform

import kfactory as kf


def test_grid_dbu_1d(straight_factory_dbu: Callable[..., kf.KCell]) -> None:
    c = kf.KCell()

    kf.grid_dbu(
        c,
        kcells=[
            straight_factory_dbu(
                width=randint(500, 2500) * 2, length=randint(2000, 20_000)
            )
            for _ in range(10)
        ],
        spacing=5000,
        align_x="origin",
    )


def test_grid_dbu_2d(straight_factory_dbu: Callable[..., kf.KCell]) -> None:
    c = kf.KCell()

    kf.grid_dbu(
        c,
        kcells=[
            [
                straight_factory_dbu(
                    width=randint(500, 2500) * 2, length=randint(2000, 20_000)
                )
                for _ in range(10)
            ]
            for _ in range(2)
        ],
        spacing=5000,
        align_x="origin",
    )


def test_grid_dbu_2d_uneven(straight_factory_dbu: Callable[..., kf.KCell]) -> None:
    c = kf.KCell()

    kf.grid_dbu(
        c,
        kcells=[
            [
                straight_factory_dbu(
                    width=randint(500, 2500) * 2, length=randint(2000, 20_000)
                )
                for _ in range(10 + j**2)
            ]
            for j in range(-3, 3)
        ],
        spacing=5000,
        align_x="xmin",
        align_y="ymax",
    )


def test_grid_dbu_2d_rotation(straight_factory_dbu: Callable[..., kf.KCell]) -> None:
    c = kf.KCell()

    kf.grid_dbu(
        c,
        kcells=[
            [
                straight_factory_dbu(
                    width=randint(500, 2500) * 2, length=randint(2000, 20_000)
                )
                for _ in range(10)
            ]
            for _ in range(2)
        ],
        rotation=1,
        spacing=5000,
        align_x="xmin",
        align_y="ymin",
    )


def test_grid_dbu_1d_shape(straight_factory_dbu: Callable[..., kf.KCell]) -> None:
    c = kf.KCell()

    kf.grid_dbu(
        c,
        kcells=[
            straight_factory_dbu(
                width=randint(500, 2500) * 2, length=randint(2000, 20_000)
            )
            for _ in range(10)
        ],
        spacing=5000,
        align_x="origin",
        shape=(1, 10),
    )


def test_grid_dbu_2d_shape(straight_factory_dbu: Callable[..., kf.KCell]) -> None:
    c = kf.KCell()

    kf.grid_dbu(
        c,
        kcells=[
            [
                straight_factory_dbu(
                    width=randint(500, 2500) * 2, length=randint(2000, 20_000)
                )
                for _ in range(10)
            ]
            for _ in range(2)
        ],
        spacing=5000,
        align_x="origin",
        shape=(4, 5),
    )


def test_grid_dbu_2d_shape_rotation(
    straight_factory_dbu: Callable[..., kf.KCell],
) -> None:
    c = kf.KCell()

    kf.grid_dbu(
        c,
        kcells=[
            [
                straight_factory_dbu(
                    width=randint(500, 2500) * 2, length=randint(2000, 20_000)
                )
                for _ in range(10)
            ]
            for _ in range(2)
        ],
        rotation=1,
        spacing=5000,
        align_x="origin",
        shape=(3, 7),
    )


def test_grid_1d(straight_factory_dbu: Callable[..., kf.KCell]) -> None:
    c = kf.DKCell()

    kf.grid(
        c,
        kcells=[
            straight_factory_dbu(
                width=randint(500, 2500) * 2, length=randint(2000, 20_000)
            ).to_dtype()
            for _ in range(10)
        ],
        spacing=5000,
        align_x="origin",
    )


def test_grid_2d(straight_factory_dbu: Callable[..., kf.KCell]) -> None:
    c = kf.DKCell()

    kf.grid(
        c,
        kcells=[
            [
                straight_factory_dbu(
                    width=randint(500, 2500) * 2, length=randint(2000, 20_000)
                ).to_dtype()
                for _ in range(10)
            ]
            for _ in range(2)
        ],
        spacing=5000,
        align_x="origin",
    )


def test_grid_2d_uneven(straight_factory_dbu: Callable[..., kf.KCell]) -> None:
    c = kf.DKCell()

    kf.grid(
        c,
        kcells=[
            [
                straight_factory_dbu(
                    width=randint(500, 2500) * 2, length=randint(2000, 20_000)
                ).to_dtype()
                for _ in range(10 + j**2)
            ]
            for j in range(-3, 3)
        ],
        spacing=5000,
        align_x="xmin",
        align_y="ymax",
    )


def test_grid_2d_rotation(straight_factory_dbu: Callable[..., kf.KCell]) -> None:
    c = kf.DKCell()

    kf.grid(
        c,
        kcells=[
            [
                straight_factory_dbu(
                    width=randint(500, 2500) * 2, length=randint(2000, 20_000)
                ).to_dtype()
                for _ in range(10)
            ]
            for _ in range(2)
        ],
        rotation=1,
        spacing=5000,
        align_x="xmin",
        align_y="ymin",
    )


def test_grid_1d_shape(straight_factory_dbu: Callable[..., kf.KCell]) -> None:
    c = kf.DKCell()

    kf.grid(
        c,
        kcells=[
            [
                straight_factory_dbu(
                    width=randint(500, 2500) * 2, length=randint(2000, 20_000)
                ).to_dtype()
                for _ in range(10)
            ]
            for _ in range(2)
        ],
        spacing=5000,
        align_x="origin",
        shape=(2, 10),
    )


def test_grid_2d_shape(straight_factory_dbu: Callable[..., kf.KCell]) -> None:
    c = kf.DKCell()

    kf.grid(
        c,
        kcells=[
            [
                straight_factory_dbu(
                    width=randint(500, 2500) * 2, length=randint(2000, 20_000)
                ).to_dtype()
                for _ in range(10)
            ]
            for _ in range(2)
        ],
        spacing=5000,
        align_x="origin",
        shape=(4, 5),
    )


def test_grid_2d_shape_rotation(
    straight_factory_dbu: Callable[..., kf.KCell],
) -> None:
    c = kf.DKCell()

    kf.grid(
        c,
        kcells=[
            [
                straight_factory_dbu(
                    width=randint(500, 2500) * 2, length=randint(2000, 20_000)
                ).to_dtype()
                for _ in range(10)
            ]
            for _ in range(2)
        ],
        rotation=1,
        spacing=5000,
        align_x="origin",
        shape=(3, 7),
    )


def test_flexgrid_dbu_1d(straight_factory_dbu: Callable[..., kf.KCell]) -> None:
    c = kf.KCell()

    kf.flexgrid_dbu(
        c,
        kcells=[
            straight_factory_dbu(
                width=randint(500, 2500) * 2, length=randint(2000, 20_000)
            )
            for _ in range(10)
        ],
        spacing=5000,
        align_x="origin",
    )


def test_flexgrid_dbu_2d(straight_factory_dbu: Callable[..., kf.KCell]) -> None:
    c = kf.KCell()

    kf.flexgrid_dbu(
        c,
        kcells=[
            [
                straight_factory_dbu(
                    width=randint(500, 2500) * 2, length=randint(2000, 20_000)
                )
                for _ in range(10)
            ]
            for _ in range(2)
        ],
        spacing=5000,
        align_x="origin",
    )


def test_flexgrid_dbu_2d_rotation(
    straight_factory_dbu: Callable[..., kf.KCell],
) -> None:
    c = kf.KCell()

    kf.flexgrid_dbu(
        c,
        kcells=[
            [
                straight_factory_dbu(
                    width=randint(500, 2500) * 2, length=randint(2000, 20_000)
                )
                for _ in range(10)
            ]
            for _ in range(2)
        ],
        rotation=1,
        spacing=5000,
        align_x="center",
    )


def test_flexgrid_dbu_1d_shape(straight_factory_dbu: Callable[..., kf.KCell]) -> None:
    c = kf.KCell()

    kf.flexgrid_dbu(
        c,
        kcells=[
            straight_factory_dbu(
                width=randint(500, 2500) * 2, length=randint(2000, 20_000)
            )
            for _ in range(10)
        ],
        spacing=5000,
        align_x="origin",
        shape=(1, 10),
    )


def test_flexgrid_dbu_2d_shape(straight_factory_dbu: Callable[..., kf.KCell]) -> None:
    c = kf.KCell()

    kf.flexgrid_dbu(
        c,
        kcells=[
            [
                straight_factory_dbu(
                    width=randint(500, 2500) * 2, length=randint(2000, 20_000)
                )
                for _ in range(10)
            ]
            for _ in range(2)
        ],
        spacing=5000,
        align_x="origin",
        shape=(4, 5),
    )


def test_flexgrid_dbu_2d_shape_rotation(
    straight_factory_dbu: Callable[..., kf.KCell],
) -> None:
    c = kf.KCell()

    kf.flexgrid_dbu(
        c,
        kcells=[
            [
                straight_factory_dbu(
                    width=randint(500, 2500) * 2, length=randint(2000, 20_000)
                )
                for _ in range(10)
            ]
            for _ in range(2)
        ],
        rotation=1,
        spacing=5000,
        align_x="origin",
        shape=(3, 7),
    )


def test_flexgrid_2d_shape_rotation(
    straight_factory: Callable[..., kf.KCell],
) -> None:
    c = kf.DKCell()

    kf.flexgrid(
        c,
        kcells=[
            [
                straight_factory(
                    width=round(uniform(0.5, 2.5)) * 2, length=round(uniform(2, 20))
                ).to_dtype()
                for _ in range(10)
            ]
            for _ in range(2)
        ],
        rotation=1,
        spacing=5,
        align_x="origin",
        shape=(3, 7),
        target_trans=kf.kdb.DCplxTrans(1, 37, False, 0, 0),
    )
