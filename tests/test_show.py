"""Version checks on the reply klive sends back to ``show()``."""

from collections.abc import Iterator
from typing import Any

import pytest

from kfactory.conf import logger
from kfactory.kcell import _check_klive_versions


@pytest.fixture
def records() -> Iterator[list[Any]]:
    records: list[Any] = []
    handler_id = logger.add(
        lambda message: records.append(message.record), level="DEBUG"
    )
    yield records
    logger.remove(handler_id)


@pytest.mark.parametrize(
    ("klive_version", "out_of_date"),
    [
        ("0.3.3", True),
        ("0.4.0", True),
        ("0.4.1", False),
        ("0.4.3", False),
        ("1.0.0", False),
    ],
)
def test_klive_version_check(
    klive_version: str, out_of_date: bool, records: list[Any]
) -> None:
    _check_klive_versions(klive_version, "0.30.0", "0.30.0")

    warnings = [r for r in records if "klive is out of date" in r["message"]]
    assert len(warnings) == out_of_date


@pytest.mark.parametrize(
    ("gui_version", "level"),
    [
        ("0.28.12", "ERROR"),
        ("0.29.0", "DEBUG"),
        ("0.30.0", None),
        ("0.31.0", None),
    ],
)
def test_klayout_gui_version_check(
    gui_version: str, level: str | None, records: list[Any]
) -> None:
    _check_klive_versions("0.4.3", gui_version, "0.30.0")

    levels = [r["level"].name for r in records if "KLayout GUI version" in r["message"]]
    assert levels == ([level] if level else [])
