import kfactory as kf
import pytest

from collections.abc import Callable


def test_virtual_cell() -> None:
    c = kf.VKCell()
    c.shapes(kf.kcl.layer(1, 0)).insert(
        kf.kdb.DPolygon([kf.kdb.DPoint(0, 0), kf.kdb.DPoint(1, 0), kf.kdb.DPoint(0, 1)])
    )
    print(c.shapes(kf.kcl.layer(1, 0)))


def test_virtual_inst(straight: kf.KCell) -> None:
    c = kf.VKCell()
    inst = c << straight

    print(inst)
