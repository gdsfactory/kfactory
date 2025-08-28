import tempfile
from pathlib import Path

from typer.testing import CliRunner

from kfactory import __version__
from kfactory.cli import app
from kfactory.cli.build import show

runner = CliRunner()


def test_version_callback() -> None:
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert f"KFactory CLI Version: {__version__}" in result.output


def test_show_function() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_file = Path(temp_dir) / "test.gds"
        temp_file.touch()

        assert temp_file.exists()

        show(temp_file)

    show(Path("non_existent_file.gds"))

    with tempfile.TemporaryDirectory() as temp_dir:
        show(Path(temp_dir))

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_file = Path(temp_dir) / "test.gds"
        temp_file.touch()
        temp_file.chmod(0o000)

        show(temp_file)
