from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

import kfactory as kf  # noqa: TC001

if TYPE_CHECKING:
    import kfactory as kf2


def test_annotated(kcl: kf.KCLayout) -> None:
    @kcl.cell
    def annotated() -> kf.KCell:
        return kcl.kcell()

    @kcl.cell(set_name=False)
    def annotated2() -> kf2.KCell:
        return kcl.kcell()

    @kcl.vcell
    def v_annotated() -> kf.VKCell:
        return kcl.vkcell()

    @kcl.vcell(set_name=False)
    def v_annotated2() -> kf2.VKCell:
        return kcl.vkcell()

    annotated()
    v_annotated()

    with pytest.raises(TypeError):
        annotated2()

    with pytest.raises(TypeError):
        v_annotated2()
