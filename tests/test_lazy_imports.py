"""`import kfactory` must work without the native pygit2 / rpack packages."""

import subprocess
import sys
import textwrap

import pytest

BLOCK = textwrap.dedent(
    """
    import importlib.abc, sys

    class Block(importlib.abc.MetaPathFinder):
        def find_spec(self, name, path=None, target=None):
            if name.split(".")[0] in {"pygit2", "rpack"}:
                raise ModuleNotFoundError(f"blocked {name}", name=name)
            return None

    sys.meta_path.insert(0, Block())
    """
)


def _run(code: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603
        [sys.executable, "-c", BLOCK + textwrap.dedent(code)],
        capture_output=True,
        text=True,
        check=False,
    )


def test_import_without_native_packages() -> None:
    r = _run(
        """
        import kfactory
        assert "pygit2" not in sys.modules and "rpack" not in sys.modules
        """
    )
    assert r.returncode == 0, r.stderr


@pytest.mark.parametrize(
    ("code", "name"),
    [
        ("import kfactory as kf; kf.config.project_dir", "pygit2"),
        ("import kfactory as kf; kf.packing.pack_instances(None, [])", "rpack"),
    ],
)
def test_clear_error_when_used(code: str, name: str) -> None:
    r = _run(code)
    assert r.returncode != 0
    assert f"ImportError: {name} is required" in r.stderr, r.stderr
