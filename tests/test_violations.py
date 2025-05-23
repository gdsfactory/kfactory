import kfactory as kf
from tests.conftest import Layers


def test_min_width_minkowski(straight: kf.KCell, layers: Layers) -> None:
    kf.utils.violations.fix_width_minkowski_tiled(
        c=straight, min_width=500, ref=layers.WG
    )


def test_min_spacing_minkowski(straight: kf.KCell, layers: Layers) -> None:
    kf.utils.violations.fix_spacing_minkowski_tiled(
        c=straight, min_space=500, ref=layers.WG
    )


def test_min_width_and_spacing_minkowski(straight: kf.KCell, layers: Layers) -> None:
    kf.utils.violations.fix_width_and_spacing_minkowski_tiled(
        c=straight, min_space=500, min_width=250, ref=layers.WG
    )


def test_min_spacing_drc(straight: kf.KCell, layers: Layers) -> None:
    kf.utils.violations.fix_spacing_tiled(c=straight, layer=layers.WG, min_space=500)


def test_min_spacing_sizing(straight: kf.KCell, layers: Layers) -> None:
    kf.utils.violations.fix_spacing_sizing_tiled(
        c=straight, min_space=500, layer=layers.WG
    )
