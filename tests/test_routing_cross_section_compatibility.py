"""Shared routing profile validation, independent of geometric placement."""

import pytest

import kfactory as kf
from kfactory.routing.generic import _check_cross_section_compatibility


def _port(kcl: kf.KCLayout, symmetric: bool, offset: int = 3000) -> kf.Port:
    layer = kf.kdb.LayerInfo(1, 0)
    if symmetric:
        xs = kf.SymmetricalCrossSection(
            width=500,
            enclosure=kf.LayerEnclosure(
                main_layer=layer, sections=[(kf.kdb.LayerInfo(2, 0), offset)]
            ),
        )
    else:
        xs = kf.AsymmetricalCrossSection(
            layer=layer,
            section_min=-250,
            section_max=250,
            sections=(
                kf.CrossSectionLayer(
                    layer=layer, section_min=offset, section_max=offset + 500
                ),
            ),
        )
    return kf.Port(name="p", cross_section=xs, kcl=kcl, trans=kf.kdb.Trans())


@pytest.mark.parametrize("symmetric", [False, True])
@pytest.mark.parametrize(
    "mirrors", [(False, False), (False, True), (True, False), (True, True)]
)
@pytest.mark.parametrize("dtype", [False, True])
def test_profile_and_mirror_compatibility(
    kcl: kf.KCLayout, symmetric: bool, mirrors: tuple[bool, bool], dtype: bool
) -> None:
    p1 = _port(kcl, symmetric)
    p2 = p1.copy()
    p1.mirror, p2.mirror = mirrors
    # Positions and angles are deliberately unrelated: this is a profile check.
    p2.trans = kf.kdb.Trans(1, mirrors[1], 1000, 2000)
    first, second = (p1.to_dtype(), p2.to_dtype()) if dtype else (p1, p2)
    if symmetric or mirrors[0] != mirrors[1]:
        _check_cross_section_compatibility(first, second)
    else:
        with pytest.raises(ValueError, match="mirror flags must be opposite"):
            _check_cross_section_compatibility(first, second)


@pytest.mark.parametrize("symmetric", [False, True])
@pytest.mark.parametrize("allow_mismatch", [False, True])
def test_full_profile_comparison(
    kcl: kf.KCLayout, symmetric: bool, allow_mismatch: bool
) -> None:
    p1, p2 = _port(kcl, symmetric), _port(kcl, symmetric, offset=4000)
    p2.mirror = True
    assert p1.width == p2.width
    assert p1.layer_info == p2.layer_info
    if symmetric and allow_mismatch:
        _check_cross_section_compatibility(p1, p2, allow_symmetric_mismatch=True)
    else:
        with pytest.raises(ValueError, match="same cross section"):
            _check_cross_section_compatibility(
                p1, p2, allow_symmetric_mismatch=allow_mismatch
            )


@pytest.mark.parametrize("first_symmetric", [False, True])
@pytest.mark.parametrize("allow_mismatch", [False, True])
def test_mixed_symmetry_is_always_rejected(
    kcl: kf.KCLayout, first_symmetric: bool, allow_mismatch: bool
) -> None:
    with pytest.raises(ValueError, match="explicit transition"):
        _check_cross_section_compatibility(
            _port(kcl, first_symmetric),
            _port(kcl, not first_symmetric),
            allow_symmetric_mismatch=allow_mismatch,
        )
