from collections.abc import Callable
from typing import Any

import kfactory as kf


def test_grid_dbu_1d(
    straight_factory_dbu: Callable[..., kf.KCell],
    gds_regression: Callable[[kf.ProtoTKCell[Any]], None],
    kcl: kf.KCLayout,
) -> None:
    c = kcl.kcell()

    kf.grid_dbu(
        c,
        kcells=[
            straight_factory_dbu(width=width * 2, length=length)
            for width, length in [
                (1722, 11292),
                (2499, 2102),
                (502, 10029),
                (501, 19999),
                (2029, 17201),
                (1920, 9271),
                (939, 18291),
                (1292, 12734),
                (928, 18390),
            ]
        ],
        spacing=5000,
        align_x="origin",
    )
    gds_regression(c)


def test_grid_dbu_2d(
    straight_factory_dbu: Callable[..., kf.KCell],
    gds_regression: Callable[[kf.ProtoTKCell[Any]], None],
    kcl: kf.KCLayout,
) -> None:
    """generated with
    [
      [(randint(500, 2500)*2, randint(2000, 20000)) for _ in range(10)]
      for _ in range(2)
    ]
    """
    c = kcl.kcell()

    kf.grid_dbu(
        c,
        kcells=[
            [
                straight_factory_dbu(width=width, length=length)
                for width, length in width_length
            ]
            for width_length in [
                [
                    (3850, 10846),
                    (2020, 5106),
                    (3252, 4006),
                    (1596, 13095),
                    (3858, 4416),
                    (3530, 15785),
                    (4350, 8922),
                    (1618, 9829),
                    (4310, 9421),
                    (4374, 17872),
                ],
                [
                    (1656, 14447),
                    (4194, 15859),
                    (3746, 19351),
                    (3840, 9823),
                    (2564, 5662),
                    (4124, 5219),
                    (2024, 17803),
                    (3316, 3300),
                    (2056, 15575),
                    (2322, 13183),
                ],
            ]
        ],
        spacing=5000,
        align_x="origin",
    )
    gds_regression(c)


def test_grid_dbu_2d_uneven(
    straight_factory_dbu: Callable[..., kf.KCell],
    gds_regression: Callable[[kf.ProtoTKCell[Any]], None],
    kcl: kf.KCLayout,
) -> None:
    """generated with
    [
      [(randint(500, 2500)*2, randint(2000, 20000)) for _ in range(10+j**2)]
      for j in range(-3,3)
    ]
    """
    c = kcl.kcell()

    kf.grid_dbu(
        c,
        kcells=[
            [
                straight_factory_dbu(width=width, length=length)
                for width, length in width_length
            ]
            for width_length in [
                [
                    (4064, 19576),
                    (4914, 12319),
                    (2690, 9654),
                    (1788, 11165),
                    (4818, 3324),
                    (4970, 19920),
                    (3060, 17260),
                    (3562, 13798),
                    (4338, 7881),
                    (3400, 15904),
                    (4148, 12118),
                    (1156, 4827),
                    (3690, 15051),
                    (1754, 6701),
                    (4532, 2700),
                    (3660, 15186),
                    (1982, 14837),
                    (3374, 19578),
                    (3664, 11765),
                ],
                [
                    (2360, 14620),
                    (1174, 3445),
                    (2150, 15551),
                    (2340, 8909),
                    (1626, 14869),
                    (4794, 19483),
                    (1096, 10129),
                    (2044, 10358),
                    (1002, 7547),
                    (2294, 7191),
                    (3600, 8849),
                    (4722, 13089),
                    (4720, 12018),
                    (3556, 19539),
                ],
                [
                    (1906, 12357),
                    (2458, 8222),
                    (2950, 17769),
                    (2926, 12294),
                    (1480, 5459),
                    (4106, 17048),
                    (3476, 2841),
                    (4504, 4580),
                    (2310, 15963),
                    (1854, 12363),
                    (3160, 9248),
                ],
                [
                    (3282, 9682),
                    (1960, 12403),
                    (1356, 16532),
                    (3454, 17615),
                    (2680, 8179),
                    (3240, 13459),
                    (3194, 15464),
                    (4864, 5418),
                    (1524, 16485),
                    (3980, 19740),
                ],
                [
                    (3704, 4167),
                    (3064, 14791),
                    (2014, 6744),
                    (4354, 5881),
                    (3482, 2763),
                    (2990, 2232),
                    (3656, 19746),
                    (3292, 10967),
                    (4280, 9495),
                    (2086, 4031),
                    (4208, 17797),
                ],
                [
                    (3684, 6605),
                    (4024, 15525),
                    (1362, 6302),
                    (3236, 10107),
                    (2152, 2047),
                    (3716, 15720),
                    (4622, 3591),
                    (2752, 3083),
                    (4304, 5908),
                    (3650, 15184),
                    (1618, 14330),
                    (3872, 13737),
                    (1686, 18151),
                    (2326, 8690),
                ],
            ]
        ],
        spacing=5000,
        align_x="xmin",
        align_y="ymax",
    )
    gds_regression(c)


def test_grid_dbu_2d_rotation(
    straight_factory_dbu: Callable[..., kf.KCell],
    gds_regression: Callable[[kf.ProtoTKCell[Any]], None],
    kcl: kf.KCLayout,
) -> None:
    c = kcl.kcell()

    kf.grid_dbu(
        c,
        kcells=[
            [
                straight_factory_dbu(width=width, length=length)
                for width, length in width_length
            ]
            for width_length in [
                [
                    (3680, 17992),
                    (3188, 18605),
                    (2780, 17634),
                    (3818, 17267),
                    (1872, 14891),
                    (2520, 15147),
                    (3514, 18168),
                    (2290, 4455),
                    (3080, 9185),
                    (4620, 19951),
                ],
                [
                    (3602, 8532),
                    (3858, 13956),
                    (4050, 8024),
                    (3782, 17847),
                    (4290, 3306),
                    (1372, 17959),
                    (3586, 5547),
                    (2718, 15863),
                    (1460, 14573),
                    (1346, 7437),
                ],
            ]
        ],
        rotation=1,
        spacing=5000,
        align_x="xmin",
        align_y="ymin",
    )
    gds_regression(c)


def test_grid_dbu_1d_shape(
    straight_factory_dbu: Callable[..., kf.KCell],
    gds_regression: Callable[[kf.ProtoTKCell[Any]], None],
    kcl: kf.KCLayout,
) -> None:
    c = kcl.kcell()

    kf.grid_dbu(
        c,
        kcells=[
            straight_factory_dbu(width=width, length=length)
            for width, length in [
                (4920, 15921),
                (2316, 7403),
                (4246, 5785),
                (2952, 4921),
                (4260, 8308),
                (4348, 17635),
                (3858, 17953),
                (1708, 2237),
                (1616, 5444),
                (4852, 15376),
            ]
        ],
        spacing=5000,
        align_x="origin",
        shape=(1, 10),
    )
    gds_regression(c)


def test_grid_dbu_2d_shape(
    straight_factory_dbu: Callable[..., kf.KCell],
    gds_regression: Callable[[kf.ProtoTKCell[Any]], None],
    kcl: kf.KCLayout,
) -> None:
    c = kcl.kcell()

    kf.grid_dbu(
        c,
        kcells=[
            [
                straight_factory_dbu(width=width, length=length)
                for width, length in width_length
            ]
            for width_length in [
                [
                    (1302, 8120),
                    (4124, 13892),
                    (1602, 6846),
                    (2300, 17367),
                    (4946, 7655),
                    (2060, 18470),
                    (2754, 18202),
                    (4000, 3074),
                    (3268, 13054),
                    (2814, 9430),
                ],
                [
                    (3528, 8637),
                    (3986, 16374),
                    (4354, 7626),
                    (3602, 7344),
                    (3540, 16989),
                    (2958, 3066),
                    (4904, 2607),
                    (3116, 8469),
                    (2498, 9539),
                    (4644, 11368),
                ],
            ]
        ],
        spacing=5000,
        align_x="origin",
        shape=(4, 5),
    )
    gds_regression(c)


def test_grid_dbu_2d_shape_rotation(
    straight_factory_dbu: Callable[..., kf.KCell],
    gds_regression: Callable[[kf.ProtoTKCell[Any]], None],
    kcl: kf.KCLayout,
) -> None:
    c = kcl.kcell()

    kf.grid_dbu(
        c,
        kcells=[
            [
                straight_factory_dbu(width=width, length=length)
                for width, length in width_length
            ]
            for width_length in [
                [
                    (2604, 9810),
                    (3188, 9938),
                    (3258, 7513),
                    (4320, 5703),
                    (3368, 10958),
                    (2906, 7434),
                    (2172, 8646),
                    (4558, 8291),
                    (2244, 16070),
                    (3324, 16189),
                ],
                [
                    (1962, 7957),
                    (4538, 8193),
                    (4152, 10847),
                    (2562, 6484),
                    (4720, 7701),
                    (2406, 17353),
                    (4016, 14245),
                    (3736, 14575),
                    (2806, 9756),
                    (4626, 10961),
                ],
            ]
        ],
        rotation=1,
        spacing=5000,
        align_x="origin",
        shape=(3, 7),
    )
    gds_regression(c)


def test_grid_1d(
    straight_factory_dbu: Callable[..., kf.KCell],
    gds_regression: Callable[[kf.ProtoTKCell[Any]], None],
    kcl: kf.KCLayout,
) -> None:
    c = kcl.dkcell()

    kf.grid(
        c,
        kcells=[
            straight_factory_dbu(width=width, length=length).to_dtype()
            for width, length in [
                (4900, 3574),
                (4864, 6939),
                (3170, 17745),
                (4706, 13591),
                (2710, 6413),
                (2888, 17517),
                (2844, 7490),
                (4624, 4489),
                (4968, 14461),
                (3614, 5349),
            ]
        ],
        spacing=5000,
        align_x="origin",
    )
    gds_regression(c)


def test_grid_2d(
    straight_factory_dbu: Callable[..., kf.KCell],
    gds_regression: Callable[[kf.ProtoTKCell[Any]], None],
    kcl: kf.KCLayout,
) -> None:
    c = kcl.dkcell()

    kf.grid(
        c,
        kcells=[
            [
                straight_factory_dbu(width=width, length=length).to_dtype()
                for width, length in width_length
            ]
            for width_length in [
                [
                    (4026, 4245),
                    (4036, 6850),
                    (1030, 9251),
                    (2660, 2222),
                    (1348, 13354),
                    (4288, 15090),
                    (4012, 2585),
                    (3284, 13454),
                    (3252, 13491),
                    (2794, 4492),
                ],
                [
                    (2328, 13094),
                    (1358, 17439),
                    (2144, 6723),
                    (1196, 16236),
                    (1906, 13328),
                    (2466, 8761),
                    (3590, 12500),
                    (3604, 19505),
                    (1122, 19939),
                    (2246, 14871),
                ],
            ]
        ],
        spacing=5000,
        align_x="origin",
    )
    gds_regression(c)


def test_grid_2d_uneven(
    straight_factory_dbu: Callable[..., kf.KCell],
    gds_regression: Callable[[kf.ProtoTKCell[Any]], None],
    kcl: kf.KCLayout,
) -> None:
    c = kcl.dkcell()

    kf.grid(
        c,
        kcells=[
            [
                straight_factory_dbu(width=width, length=length).to_dtype()
                for width, length in width_length
            ]
            for width_length in [
                [
                    (3472, 17929),
                    (3872, 5529),
                    (4684, 8050),
                    (1844, 9053),
                    (1078, 13294),
                    (2794, 16256),
                    (3008, 17474),
                    (2744, 18836),
                    (1752, 17345),
                    (3630, 7772),
                    (4992, 10667),
                    (2624, 4229),
                    (1292, 15181),
                    (3216, 12543),
                    (1790, 6059),
                    (3168, 18254),
                    (4062, 8891),
                    (3250, 6856),
                    (2370, 6175),
                ],
                [
                    (1686, 17451),
                    (2442, 10720),
                    (1194, 10595),
                    (1586, 7311),
                    (3444, 5494),
                    (2602, 19307),
                    (2882, 19305),
                    (4884, 5681),
                    (4304, 7646),
                    (4978, 6626),
                    (2576, 2769),
                    (4388, 5627),
                    (3894, 12408),
                    (4312, 11623),
                ],
                [
                    (2950, 12995),
                    (1508, 5771),
                    (3260, 16198),
                    (2532, 9854),
                    (2976, 13371),
                    (2082, 4440),
                    (3044, 3243),
                    (2972, 18556),
                    (4582, 16274),
                    (4286, 4673),
                    (3780, 8588),
                ],
                [
                    (1334, 10349),
                    (1846, 6310),
                    (3390, 16672),
                    (3636, 11253),
                    (4918, 11182),
                    (2026, 3047),
                    (4378, 17843),
                    (3188, 17802),
                    (4070, 15018),
                    (4002, 4424),
                ],
                [
                    (4844, 3795),
                    (1040, 6852),
                    (3022, 5260),
                    (4590, 6535),
                    (1950, 9085),
                    (1746, 7179),
                    (4250, 5294),
                    (1194, 12547),
                    (3644, 13032),
                    (4960, 8921),
                    (3538, 6875),
                ],
                [
                    (3012, 6556),
                    (3018, 9128),
                    (4308, 17140),
                    (1136, 2258),
                    (3234, 9113),
                    (4144, 16196),
                    (4722, 7755),
                    (1714, 13380),
                    (1718, 15188),
                    (2556, 11188),
                    (2440, 17950),
                    (4122, 14195),
                    (1128, 17175),
                    (3002, 7404),
                ],
            ]
        ],
        spacing=5000,
        align_x="xmin",
        align_y="ymax",
    )
    gds_regression(c)


def test_grid_2d_rotation(
    straight_factory_dbu: Callable[..., kf.KCell],
    gds_regression: Callable[[kf.ProtoTKCell[Any]], None],
    kcl: kf.KCLayout,
) -> None:
    c = kcl.dkcell()

    kf.grid(
        c,
        kcells=[
            [
                straight_factory_dbu(width=width, length=length).to_dtype()
                for width, length in width_length
            ]
            for width_length in [
                [
                    (1276, 6091),
                    (1840, 13393),
                    (1834, 18696),
                    (3598, 9700),
                    (1590, 8273),
                    (2720, 12086),
                    (1528, 3208),
                    (4756, 4653),
                    (3088, 15337),
                    (2578, 3824),
                ],
                [
                    (4630, 18090),
                    (2966, 13155),
                    (1934, 7393),
                    (4164, 17084),
                    (3958, 12958),
                    (1810, 12845),
                    (2110, 16411),
                    (4532, 15034),
                    (2214, 15113),
                    (1564, 9062),
                ],
            ]
        ],
        rotation=1,
        spacing=5000,
        align_x="xmin",
        align_y="ymin",
    )
    gds_regression(c)


def test_grid_1d_shape(
    straight_factory_dbu: Callable[..., kf.KCell],
    gds_regression: Callable[[kf.ProtoTKCell[Any]], None],
    kcl: kf.KCLayout,
) -> None:
    c = kcl.dkcell()

    kf.grid(
        c,
        kcells=[
            [
                straight_factory_dbu(width=width, length=length).to_dtype()
                for width, length in width_length
            ]
            for width_length in [
                [
                    (3242, 19792),
                    (1610, 2176),
                    (1508, 12899),
                    (4422, 5688),
                    (4338, 12408),
                    (1168, 19646),
                    (3622, 11906),
                    (4250, 19549),
                    (2120, 2232),
                    (3246, 4673),
                ],
                [
                    (3536, 5108),
                    (2150, 6949),
                    (3826, 11541),
                    (4744, 9124),
                    (2510, 2821),
                    (4246, 18239),
                    (1642, 9264),
                    (2836, 18958),
                    (1970, 19981),
                    (2536, 2120),
                ],
            ]
        ],
        spacing=5000,
        align_x="origin",
        shape=(2, 10),
    )
    gds_regression(c)


def test_grid_2d_shape(
    straight_factory_dbu: Callable[..., kf.KCell],
    gds_regression: Callable[[kf.ProtoTKCell[Any]], None],
    kcl: kf.KCLayout,
) -> None:
    c = kcl.dkcell()

    kf.grid(
        c,
        kcells=[
            [
                straight_factory_dbu(width=width, length=length).to_dtype()
                for width, length in width_length
            ]
            for width_length in [
                [
                    (3242, 19792),
                    (1610, 2176),
                    (1508, 12899),
                    (4422, 5688),
                    (4338, 12408),
                    (1168, 19646),
                    (3622, 11906),
                    (4250, 19549),
                    (2120, 2232),
                    (3246, 4673),
                ],
                [
                    (3536, 5108),
                    (2150, 6949),
                    (3826, 11541),
                    (4744, 9124),
                    (2510, 2821),
                    (4246, 18239),
                    (1642, 9264),
                    (2836, 18958),
                    (1970, 19981),
                    (2536, 2120),
                ],
            ]
        ],
        spacing=5000,
        align_x="origin",
        shape=(4, 5),
    )
    gds_regression(c)


def test_grid_2d_shape_rotation(
    straight_factory_dbu: Callable[..., kf.KCell],
    gds_regression: Callable[[kf.ProtoTKCell[Any]], None],
    kcl: kf.KCLayout,
) -> None:
    c = kcl.dkcell()

    kf.grid(
        c,
        kcells=[
            [
                straight_factory_dbu(width=width, length=length).to_dtype()
                for width, length in width_length
            ]
            for width_length in [
                [
                    (4262, 8246),
                    (2832, 3641),
                    (2144, 6686),
                    (3176, 5177),
                    (1924, 14932),
                    (2704, 18272),
                    (2608, 17438),
                    (3688, 17119),
                    (2574, 12801),
                    (3510, 19911),
                ],
                [
                    (1056, 17693),
                    (3982, 15965),
                    (4070, 17103),
                    (4542, 13266),
                    (2562, 14205),
                    (3476, 19330),
                    (1644, 6970),
                    (3648, 4112),
                    (4106, 4205),
                    (2980, 7435),
                ],
            ]
        ],
        rotation=1,
        spacing=5000,
        align_x="origin",
        shape=(3, 7),
    )
    gds_regression(c)


def test_flexgrid_dbu_1d(
    straight_factory_dbu: Callable[..., kf.KCell],
    gds_regression: Callable[[kf.ProtoTKCell[Any]], None],
    kcl: kf.KCLayout,
) -> None:
    c = kcl.dkcell()

    kf.flexgrid_dbu(
        c,
        kcells=[
            straight_factory_dbu(width=width, length=length)
            for width, length in [
                (4832, 18906),
                (1526, 14810),
                (2974, 7405),
                (2966, 2986),
                (1186, 10383),
                (4164, 13126),
                (2926, 19544),
                (3996, 10115),
                (1024, 14910),
                (2304, 15328),
            ]
        ],
        spacing=5000,
        align_x="origin",
    )
    gds_regression(c)


def test_flexgrid_dbu_2d(
    straight_factory_dbu: Callable[..., kf.KCell],
    gds_regression: Callable[[kf.ProtoTKCell[Any]], None],
    kcl: kf.KCLayout,
) -> None:
    c = kcl.dkcell()

    kf.flexgrid_dbu(
        c,
        kcells=[
            [
                straight_factory_dbu(width=width, length=length)
                for width, length in width_length
            ]
            for width_length in [
                [
                    (3498, 11612),
                    (1132, 9501),
                    (3442, 19001),
                    (1162, 10552),
                    (2300, 15331),
                    (4536, 13435),
                    (2220, 12894),
                    (1068, 3392),
                    (1190, 8061),
                    (2772, 2756),
                ],
                [
                    (3678, 12671),
                    (2744, 19710),
                    (3382, 5167),
                    (3834, 14789),
                    (3460, 8919),
                    (3518, 10511),
                    (4436, 10765),
                    (2484, 10569),
                    (3964, 6780),
                    (2916, 13444),
                ],
            ]
        ],
        spacing=5000,
        align_x="origin",
    )
    gds_regression(c)


def test_flexgrid_dbu_2d_rotation(
    straight_factory_dbu: Callable[..., kf.KCell],
    gds_regression: Callable[[kf.ProtoTKCell[Any]], None],
    kcl: kf.KCLayout,
) -> None:
    c = kcl.dkcell()

    kf.flexgrid_dbu(
        c,
        kcells=[
            [
                straight_factory_dbu(width=width, length=length)
                for width, length in width_length
            ]
            for width_length in [
                [
                    (2554, 16210),
                    (4594, 15047),
                    (2726, 9108),
                    (2126, 10594),
                    (2666, 7448),
                    (1462, 5964),
                    (3212, 8794),
                    (1000, 3550),
                    (3984, 18577),
                    (4608, 18712),
                ],
                [
                    (4586, 3479),
                    (3450, 12172),
                    (1536, 4373),
                    (3418, 6376),
                    (1602, 2089),
                    (2002, 10478),
                    (1998, 19338),
                    (4194, 11675),
                    (1164, 13466),
                    (2362, 11162),
                ],
            ]
        ],
        rotation=1,
        spacing=5000,
        align_x="center",
    )
    gds_regression(c)


def test_flexgrid_dbu_1d_shape(
    straight_factory_dbu: Callable[..., kf.KCell],
    gds_regression: Callable[[kf.ProtoTKCell[Any]], None],
    kcl: kf.KCLayout,
) -> None:
    c = kcl.dkcell()

    kf.flexgrid_dbu(
        c,
        kcells=[
            straight_factory_dbu(width=width, length=length)
            for width, length in [
                (4704, 9877),
                (4936, 19122),
                (4134, 3701),
                (4876, 4404),
                (3410, 18867),
                (3362, 7969),
                (3146, 17798),
                (2800, 7581),
                (3946, 13622),
                (2250, 4785),
            ]
        ],
        spacing=5000,
        align_x="origin",
        shape=(1, 10),
    )
    gds_regression(c)


def test_flexgrid_dbu_2d_shape(
    straight_factory_dbu: Callable[..., kf.KCell],
    gds_regression: Callable[[kf.ProtoTKCell[Any]], None],
    kcl: kf.KCLayout,
) -> None:
    c = kcl.dkcell()

    kf.flexgrid_dbu(
        c,
        kcells=[
            [
                straight_factory_dbu(width=width, length=length)
                for width, length in width_length
            ]
            for width_length in [
                [
                    (2890, 6450),
                    (4926, 3119),
                    (1162, 12514),
                    (1742, 11141),
                    (4960, 14273),
                    (1424, 5889),
                    (1210, 11818),
                    (4054, 2804),
                    (2782, 8253),
                    (2490, 5196),
                ],
                [
                    (2256, 17981),
                    (4864, 7293),
                    (2736, 6748),
                    (2188, 18353),
                    (1638, 9809),
                    (4166, 7297),
                    (1350, 18577),
                    (2276, 7245),
                    (2468, 18050),
                    (1678, 5687),
                ],
            ]
        ],
        spacing=5000,
        align_x="origin",
        shape=(4, 5),
    )
    gds_regression(c)


def test_flexgrid_dbu_2d_shape_rotation(
    straight_factory_dbu: Callable[..., kf.KCell],
    gds_regression: Callable[[kf.ProtoTKCell[Any]], None],
    kcl: kf.KCLayout,
) -> None:
    c = kcl.dkcell()

    kf.flexgrid_dbu(
        c,
        kcells=[
            [
                straight_factory_dbu(width=width, length=length)
                for width, length in width_length
            ]
            for width_length in [
                [
                    (4748, 12171),
                    (3166, 15486),
                    (4194, 16244),
                    (2832, 18496),
                    (1318, 3595),
                    (3120, 12270),
                    (1684, 2066),
                    (1056, 7820),
                    (4958, 8529),
                    (2160, 2458),
                ],
                [
                    (3946, 9204),
                    (1038, 10733),
                    (2290, 14988),
                    (4278, 3520),
                    (4758, 5839),
                    (4770, 16569),
                    (2286, 19115),
                    (4956, 7416),
                    (4136, 18093),
                    (1374, 14553),
                ],
            ]
        ],
        rotation=1,
        spacing=5000,
        align_x="origin",
        shape=(3, 7),
    )

    gds_regression(c)


def test_flexgrid_2d_shape_rotation(
    straight_factory: Callable[..., kf.KCell],
    gds_regression: Callable[[kf.ProtoTKCell[Any]], None],
    kcl: kf.KCLayout,
) -> None:
    c = kcl.dkcell()

    kf.flexgrid(
        c,
        kcells=[
            [
                straight_factory(
                    width=round(width, 3) * 2, length=round(length, 3)
                ).to_dtype()
                for width, length in width_length
            ]
            for width_length in [
                [
                    (2.321210289756208, 11.09849388615893),
                    (2.486217412526874, 15.921890085607725),
                    (1.9038226439839836, 11.25508733808606),
                    (1.628827324163244, 10.423738084184832),
                    (1.518096864322188, 17.510243028764737),
                    (1.0907637364735538, 13.749844795466037),
                    (2.0784364128601163, 10.870320046337781),
                    (2.1174560456068097, 11.275539940846514),
                    (0.9327558441729038, 13.600295088594706),
                    (2.144349720519438, 5.264599644528424),
                ],
                [
                    (1.9153645548152531, 9.287606899001712),
                    (1.9443236172103493, 15.211026179809899),
                    (1.8630640055552168, 12.37793760390889),
                    (1.5861031596124437, 5.023689268361215),
                    (0.7979856479451111, 12.752888385161807),
                    (1.6693349315304924, 6.560951383995562),
                    (0.6108950822157724, 12.206388875582432),
                    (2.214793736344883, 16.587675807735494),
                    (2.4040386530767366, 4.4575931451702475),
                    (0.6289800295724652, 14.653060023711351),
                ],
            ]
        ],
        rotation=1,
        spacing=5,
        align_x="origin",
        shape=(3, 7),
        target_trans=kf.kdb.DCplxTrans(1, 37, False, 0, 0),
    )
    gds_regression(c)
