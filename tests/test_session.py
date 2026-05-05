import pickle
from pathlib import Path

import pytest

import kfactory as kf
from tests.session import session1, session2, session3, session_func


@pytest.fixture
def session_dir(tmp_path: Path) -> Path:
    """Per-test session directory.

    The default `build/session/kcls` is shared across xdist workers, which
    causes Windows-only races between concurrent save_session/load_session
    calls (rmtree fails or files vanish mid-read). pytest gives each test a
    unique tmp_path even under xdist, so threading it through isolates them.
    """
    return tmp_path / "kcls"


def test_session_cache(session_dir: Path) -> None:
    c = session3.my_cell(a=5)

    f2 = session2.kcl2.factories["my_other_cell"]
    f1 = session1.kcl1.factories["test"]

    assert session1.cell_created
    assert session2.cell_created
    assert session3.cell_created

    kf.save_session(c=c, session_dir=session_dir)

    session1.cell_created = False
    session2.cell_created = False
    session3.cell_created = False

    f1.prune()
    f2.prune()

    kf.load_session(session_dir=session_dir)

    session3.my_cell(a=5)

    assert not session1.cell_created
    assert not session2.cell_created
    assert not session3.cell_created

    f2.prune()

    session1.cell_created = False
    session2.cell_created = False
    session3.cell_created = False

    session3.my_cell(a=5)

    assert not session1.cell_created
    assert session2.cell_created
    assert session3.cell_created

    kf.save_session(session1.test(), session_dir=session_dir)

    f1.prune()
    f2.prune()

    session1.cell_created = False
    session2.cell_created = False
    session3.cell_created = False

    kf.load_session(session_dir=session_dir)

    session3.my_cell(a=5)

    assert not session1.cell_created
    assert session2.cell_created
    assert session3.cell_created


def test_session_cache_function_arg(session_dir: Path) -> None:
    """Test that factories with function arguments can be saved/loaded."""
    c = session_func.cell_with_func_arg(func=session_func.make_box, size=500)
    f = session_func.kcl_func.factories["cell_with_func_arg"]

    assert session_func.cell_created

    kf.save_session(c=c, session_dir=session_dir)

    session_func.cell_created = False
    f.prune()

    kf.load_session(session_dir=session_dir)

    session_func.cell_with_func_arg(func=session_func.make_box, size=500)

    assert not session_func.cell_created


def test_session_cache_lambda_rejected() -> None:
    """Test that FunctionPickler rejects lambda functions."""
    import io

    from kfactory.session_cache import FunctionPickler

    data = {"key": lambda x: x}
    buf = io.BytesIO()
    with pytest.raises(pickle.PicklingError, match="Cannot pickle lambda"):
        FunctionPickler(buf).dump(data)


def test_session_cache_nested_func_rejected() -> None:
    """Test that FunctionPickler rejects nested (closure) functions."""
    import io

    from kfactory.session_cache import FunctionPickler

    def nested_func() -> None:
        pass

    data = {"key": nested_func}
    buf = io.BytesIO()
    with pytest.raises(pickle.PicklingError, match="Cannot pickle nested function"):
        FunctionPickler(buf).dump(data)
