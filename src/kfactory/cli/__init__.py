"""CLI interface for kfactory.

Use `kf --help` for more info.
"""
from typing import Annotated

# import click
import typer

from .. import __version__
from .runshow import run, show
from .sea import app as sea

app = typer.Typer(name="kf")


app.command()(run)
app.command()(show)
app.add_typer(sea)


@app.callback(invoke_without_command=True)
def version_callback(
    version: Annotated[
        bool, typer.Option("--version", "-V", help="Show version of the CLI")
    ] = False,
) -> None:
    """Show the version of the cli."""
    if version:
        print(f"KFactory CLI Version: {__version__}")
        raise typer.Exit()
