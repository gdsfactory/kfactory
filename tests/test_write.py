"""Tests for KCell/KCLayout write and write_bytes.

Covers the happy path (a file / bytes are produced) and the duplicate cell name
detection used by ``write``/``write_bytes``: raise a
:class:`~kfactory.exceptions.DuplicateCellNameError` by default, or auto-rename
with ``$1`` suffixes when ``deduplicate_cell_names=True``.
"""

from pathlib import Path

import pytest

import kfactory as kf
from kfactory.exceptions import DuplicateCellNameError
from tests.conftest import Layers


def test_write_and_write_bytes(
    kcl: kf.KCLayout, layers: Layers, tmp_path: Path
) -> None:
    top = kcl.kcell("top")
    child_a = kcl.kcell("child_a")
    child_a.shapes(kcl.find_layer(layers.WG)).insert(kf.kdb.Box(0, 0, 1000, 1000))
    child_b = kcl.kcell("child_b")
    child_b.shapes(kcl.find_layer(layers.WG)).insert(kf.kdb.Box(0, 0, 500, 500))
    top << child_a
    top << child_b

    def make_duplicate() -> None:
        # Force a raw duplicate name, bypassing the KCell name setter which
        # would otherwise log/raise depending on ``config.debug_names``.
        child_b.kdb_cell.name = "child_a"

    def dedup_names() -> list[str]:
        return sorted(c.name for c in kcl.layout.each_cell())

    path = tmp_path / "out.gds"

    # Happy path: no duplicates -> file / bytes are produced.
    kcl.write(path)
    assert path.exists()
    assert len(kcl.write_bytes()) > 0
    top.write(path)
    assert path.exists()
    assert len(top.write_bytes()) > 0

    # KCLayout.write
    make_duplicate()
    with pytest.raises(DuplicateCellNameError):
        kcl.write(path)
    kcl.write(path, deduplicate_cell_names=True)
    assert path.exists()
    assert dedup_names() == ["child_a", "child_a$1", "top"]

    # KCLayout.write_bytes
    make_duplicate()
    with pytest.raises(DuplicateCellNameError):
        kcl.write_bytes()
    assert len(kcl.write_bytes(deduplicate_cell_names=True)) > 0
    assert dedup_names() == ["child_a", "child_a$1", "top"]

    # KCell.write
    make_duplicate()
    with pytest.raises(DuplicateCellNameError):
        top.write(path)
    top.write(path, deduplicate_cell_names=True)
    assert dedup_names() == ["child_a", "child_a$1", "top"]

    # KCell.write_bytes
    make_duplicate()
    with pytest.raises(DuplicateCellNameError):
        top.write_bytes()
    assert len(top.write_bytes(deduplicate_cell_names=True)) > 0
    assert dedup_names() == ["child_a", "child_a$1", "top"]
