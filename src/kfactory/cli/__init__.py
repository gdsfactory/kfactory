"""CLI interface for kfactory.

Use `kf --help` for more info.
"""

from typing import Annotated

import typer

from .. import __version__
from .build import build, show

app = typer.Typer(name="kf")


app.command()(build)
app.command()(show)


@app.callback(invoke_without_command=True)
def version_callback(
    version: Annotated[
        bool, typer.Option("--version", "-V", help="Show version of the CLI")
    ] = False,
) -> None:
    """Show the version of the cli."""
    if version:
        print(f"KFactory CLI Version: {__version__}")  # noqa: T201
        raise typer.Exit
