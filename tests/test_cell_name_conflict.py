"""Name conflict reporting in the ``KCell.name`` setter.

The setter locates its caller with fixed ``sys._getframe`` offsets. These tests
pin down that the reported location is the code doing the rename, so that a
change in the call chain (pydantic, the ``ProtoTKCell`` wrapper, the ``@cell``
decorator) shows up as a failure instead of silently pointing elsewhere.
"""

import sys
from collections.abc import Iterator
from typing import Any

import pytest

import kfactory as kf
from kfactory.conf import logger
from kfactory.exceptions import DuplicateCellNameError


@pytest.fixture
def kcl(kcl: kf.KCLayout) -> Iterator[kf.KCLayout]:
    """Unregister the layout afterwards.

    These tests leave duplicate cell names behind.
    Using `show()` on the same worker would fail.
    """
    yield kcl
    kcl.delete()


@pytest.fixture
def errors() -> Iterator[list[Any]]:
    records: list[Any] = []
    handler_id = logger.add(
        lambda message: records.append(message.record), level="ERROR"
    )
    yield records
    logger.remove(handler_id)


def test_name_conflict_reports_caller(kcl: kf.KCLayout, errors: list[Any]) -> None:
    kcl.kcell("duplicate")
    cell = kcl.kcell("other")

    lineno = sys._getframe().f_lineno + 1
    cell.name = "duplicate"

    assert len(errors) == 1
    record = errors[0]
    assert record["message"].startswith(
        f"Name conflict in {__name__}::test_name_conflict_reports_caller"
        f" at line {lineno}\n"
    )
    assert record["name"] == __name__
    assert record["function"] == "test_name_conflict_reports_caller"
    assert record["line"] == lineno


def test_name_conflict_reports_cell_function(
    kcl: kf.KCLayout, errors: list[Any]
) -> None:
    kcl.kcell("conflicting_cell")

    def conflicting_cell() -> kf.KCell:
        return kcl.kcell()

    kcl.cell(debug_names=False)(conflicting_cell)()

    assert len(errors) == 1
    code = conflicting_cell.__code__
    assert errors[0]["message"].startswith(
        f"Name conflict in {code.co_filename}::conflicting_cell"
        f" at line {code.co_firstlineno}\n"
    )


def test_name_conflict_raises_with_caller(
    kcl: kf.KCLayout, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(kf.config, "debug_names", True)
    kcl.kcell("duplicate")
    cell = kcl.kcell("other")

    lineno = sys._getframe().f_lineno + 2
    with pytest.raises(DuplicateCellNameError) as exc_info:
        cell.name = "duplicate"

    assert str(exc_info.value).startswith(
        f"Name conflict in {__name__}::test_name_conflict_raises_with_caller"
        f" at line {lineno}\n"
    )
