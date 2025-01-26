import tempfile
from pathlib import Path

from typer.testing import CliRunner

from kfactory import __version__
from kfactory.cli import app

runner = CliRunner()


def test_version_callback() -> None:
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert f"KFactory CLI Version: {__version__}" in result.output


def test_show_command() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_file = Path(temp_dir) / "test.gds"
        temp_file.touch()

        assert temp_file.exists()

        result = runner.invoke(app, ["show", str(temp_file)])
        assert result.exit_code == 0

        assert temp_file.exists()

    result = runner.invoke(app, ["show", "non_existent_file.gds"])

    with tempfile.TemporaryDirectory() as temp_dir:
        result = runner.invoke(app, ["show", temp_dir])

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_file = Path(temp_dir) / "test.gds"
        temp_file.touch()
        temp_file.chmod(0o000)

        result = runner.invoke(app, ["show", str(temp_file)])


if __name__ == "__main__":
    test_show_command()
