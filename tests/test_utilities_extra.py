"""Extra tests for kfactory.utilities module."""

from __future__ import annotations

from typing import TYPE_CHECKING

import kfactory as kf
from kfactory.utilities import (
    dpolygon_from_array,
    ensure_build_directory,
    get_build_path,
    get_session_directory,
    save_layout_options,
    update_default_trans,
)

if TYPE_CHECKING:
    from pathlib import Path

    import pytest


def test_save_layout_options() -> None:
    save = save_layout_options(gds2_write_timestamps=False)
    assert save.gds2_write_timestamps is False


def test_update_default_trans() -> None:
    from kfactory.conf import DEFAULT_TRANS

    snapshot = dict(DEFAULT_TRANS)
    try:
        update_default_trans({"_test_extra_key": "value"})
        assert DEFAULT_TRANS["_test_extra_key"] == "value"
    finally:
        DEFAULT_TRANS.clear()
        DEFAULT_TRANS.update(snapshot)


def test_dpolygon_from_array() -> None:
    poly = dpolygon_from_array([(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)])
    assert isinstance(poly, kf.kdb.DPolygon)


def test_ensure_build_directory_with_project_dir(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(kf.config, "project_dir", tmp_path)
    target = ensure_build_directory("mask", create_gitignore=True)
    assert target is not None
    assert target.exists()
    assert (tmp_path / "build" / ".gitignore").exists()


def test_ensure_build_directory_no_gitignore(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(kf.config, "project_dir", tmp_path)
    target = ensure_build_directory("mask2", create_gitignore=False)
    assert target is not None
    # gitignore may or may not exist depending on prior tests; just verify dir
    assert target.exists()


def test_ensure_build_directory_no_project_dir(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(kf.config, "project_dir", None)
    assert ensure_build_directory() is None


def test_get_build_path_with_project_dir(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(kf.config, "project_dir", tmp_path)
    path, should_delete = get_build_path("myfile", subdirectory="gds")
    assert should_delete is False
    assert path.suffix == ".gds"
    assert path.parent.exists()


def test_get_build_path_no_project_dir(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(kf.config, "project_dir", None)
    path, should_delete = get_build_path("tempfile", file_format="oas")
    assert should_delete is True
    assert path.suffix == ".oas"


def test_get_session_directory_custom_dir(tmp_path: Path) -> None:
    custom = tmp_path / "custom_session"
    assert get_session_directory(custom_dir=custom) == custom


def test_get_session_directory_with_project_dir(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(kf.config, "project_dir", tmp_path)
    target = get_session_directory()
    assert target.exists()


def test_get_session_directory_no_project_dir(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(kf.config, "project_dir", None)
    target = get_session_directory()
    assert "session/kcls" in str(target)
