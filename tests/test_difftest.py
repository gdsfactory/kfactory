"""Tests for kfactory.utils.difftest module."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

import kfactory as kf
from kfactory.utils.difftest import (
    GeometryDifferenceError,
    diff,
    difftest,
    overwrite,
    read_top_cell,
    xor,
)
from tests.conftest import Layers

if TYPE_CHECKING:
    from pathlib import Path


def _write_simple_cell(
    name: str, layer: kf.kdb.LayerInfo, path: Path, box: kf.kdb.Box | None = None
) -> kf.KCLayout:
    """Write a small KCLayout with a top cell containing a box."""
    kcl = kf.KCLayout(name, infos=Layers)
    c = kcl.kcell(name)
    c.shapes(kcl.find_layer(layer)).insert(box or kf.kdb.Box(0, 0, 1000, 500))
    kcl.write(str(path))
    return kcl


def test_read_top_cell(tmp_path: Path, layers: Layers) -> None:
    f = tmp_path / "topcell.gds"
    _write_simple_cell("DT_RTC", layers.WG, f)
    cell = read_top_cell(f)
    assert isinstance(cell, kf.DKCell)


def test_diff_identical_files(tmp_path: Path, layers: Layers) -> None:
    f1 = tmp_path / "a.gds"
    f2 = tmp_path / "b.gds"
    _write_simple_cell("DT_A", layers.WG, f1)
    _write_simple_cell("DT_A", layers.WG, f2)
    assert diff(f1, f2, test_name="ident") is False


def test_diff_different_files(tmp_path: Path, layers: Layers) -> None:
    f1 = tmp_path / "a.gds"
    f2 = tmp_path / "b.gds"
    _write_simple_cell("DT_DA", layers.WG, f1)
    _write_simple_cell("DT_DA", layers.WG, f2, box=kf.kdb.Box(0, 0, 2000, 500))
    assert diff(f1, f2, test_name="different") is True


def test_diff_different_files_no_xor(tmp_path: Path, layers: Layers) -> None:
    f1 = tmp_path / "a.gds"
    f2 = tmp_path / "b.gds"
    _write_simple_cell("DT_DAX", layers.WG, f1)
    _write_simple_cell("DT_DAX", layers.WG, f2, box=kf.kdb.Box(0, 0, 2000, 500))
    assert diff(f1, f2, xor=False, test_name="different_no_xor") is True


def test_diff_dbu_mismatch(tmp_path: Path) -> None:
    f1 = tmp_path / "a.gds"
    f2 = tmp_path / "b.gds"
    kcl1 = kf.KCLayout("DT_DBU1", infos=Layers)
    c1 = kcl1.kcell("DT_DBU1")
    c1.shapes(kcl1.find_layer(Layers().WG)).insert(kf.kdb.Box(0, 0, 1000, 500))
    kcl1.write(str(f1))

    kcl2 = kf.KCLayout("DT_DBU2", infos=Layers)
    kcl2.layout.dbu = 0.005
    c2 = kcl2.kcell("DT_DBU2")
    c2.shapes(kcl2.find_layer(Layers().WG)).insert(kf.kdb.Box(0, 0, 1000, 500))
    kcl2.write(str(f2))

    with pytest.raises(ValueError, match=r"dbu is different"):
        diff(f1, f2)


def test_xor_identical_layouts(tmp_path: Path, layers: Layers) -> None:
    f1 = tmp_path / "a.gds"
    f2 = tmp_path / "b.gds"
    _write_simple_cell("DT_XI", layers.WG, f1)
    _write_simple_cell("DT_XI", layers.WG, f2)
    old = read_top_cell(f1)
    new = read_top_cell(f2)
    res = xor(old, new, test_name="ident_xor")
    assert isinstance(res, kf.DKCell)
    assert res.name == "xor_empty"


def test_xor_different_layouts(tmp_path: Path, layers: Layers) -> None:
    f1 = tmp_path / "a.gds"
    f2 = tmp_path / "b.gds"
    _write_simple_cell("DT_XD", layers.WG, f1)
    _write_simple_cell("DT_XD", layers.WG, f2, box=kf.kdb.Box(0, 0, 2000, 500))
    old = read_top_cell(f1)
    new = read_top_cell(f2)
    res = xor(old, new, test_name="diff_xor")
    assert isinstance(res, kf.DKCell)
    # difftest cell should not be the empty marker
    assert res.name == "diff_xor_difftest"


def test_xor_dbu_mismatch(tmp_path: Path) -> None:
    f1 = tmp_path / "a.gds"
    f2 = tmp_path / "b.gds"
    kcl1 = kf.KCLayout("DT_XDBU1", infos=Layers)
    c1 = kcl1.kcell("DT_XDBU1")
    c1.shapes(kcl1.find_layer(Layers().WG)).insert(kf.kdb.Box(0, 0, 1000, 500))
    kcl1.write(str(f1))

    kcl2 = kf.KCLayout("DT_XDBU2", infos=Layers)
    kcl2.layout.dbu = 0.005
    c2 = kcl2.kcell("DT_XDBU2")
    c2.shapes(kcl2.find_layer(Layers().WG)).insert(kf.kdb.Box(0, 0, 1000, 500))
    kcl2.write(str(f2))

    old = read_top_cell(f1)
    new = read_top_cell(f2)
    with pytest.raises(ValueError, match=r"dbu is different"):
        xor(old, new)


def test_difftest_first_run_creates_ref(tmp_path: Path, layers: Layers) -> None:
    kcl = kf.KCLayout("DT_FT", infos=Layers)
    c = kcl.kcell("DT_FT_TOP")
    c.shapes(kcl.find_layer(layers.WG)).insert(kf.kdb.Box(0, 0, 1000, 500))

    ref_dir = tmp_path / "ref"
    run_dir = tmp_path / "run"

    with pytest.raises(AssertionError, match="Reference GDS file"):
        difftest(c, dirpath=ref_dir, dirpath_run=run_dir, test_name="first")
    assert (ref_dir / "first.gds").exists()
    assert (run_dir / "first.gds").exists()


def test_difftest_identical(tmp_path: Path, layers: Layers) -> None:
    kcl = kf.KCLayout("DT_FT_ID", infos=Layers)
    c = kcl.kcell("DT_FT_ID_TOP")
    c.shapes(kcl.find_layer(layers.WG)).insert(kf.kdb.Box(0, 0, 1000, 500))

    ref_dir = tmp_path / "ref"
    run_dir = tmp_path / "run"

    # First run creates the reference and raises
    with pytest.raises(AssertionError):
        difftest(c, dirpath=ref_dir, dirpath_run=run_dir, test_name="ident")
    # Second run should pass since same cell -> same gds
    difftest(c, dirpath=ref_dir, dirpath_run=run_dir, test_name="ident")


def test_overwrite_decline(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, layers: Layers
) -> None:
    ref_file = tmp_path / "ref.gds"
    run_file = tmp_path / "run.gds"
    _write_simple_cell("DT_OW_R", layers.WG, ref_file)
    _write_simple_cell("DT_OW_R", layers.WG, run_file)

    monkeypatch.setattr("builtins.input", lambda *args, **kwargs: "N")
    with pytest.raises(GeometryDifferenceError):
        overwrite(ref_file, run_file)


def test_overwrite_accept(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, layers: Layers
) -> None:
    ref_file = tmp_path / "ref.gds"
    run_file = tmp_path / "run.gds"
    _write_simple_cell("DT_OW_A", layers.WG, ref_file)
    _write_simple_cell("DT_OW_A", layers.WG, run_file, box=kf.kdb.Box(0, 0, 2000, 500))

    monkeypatch.setattr("builtins.input", lambda *args, **kwargs: "Y")
    # Even on accept, the function raises GeometryDifferenceError as a sentinel
    with pytest.raises(GeometryDifferenceError):
        overwrite(ref_file, run_file)
    # The reference should have been replaced with the run file's contents
    assert ref_file.exists()
