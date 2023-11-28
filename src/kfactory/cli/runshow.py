"""CLI interface for kfactory.

Use `kf --help` for more info.
"""
import importlib
import os
import runpy
import sys
from enum import Enum
from pathlib import Path
from typing import Annotated, Optional

import typer

from ..conf import logger
from ..kcell import KCell
from ..kcell import show as kfshow

# app = typer.Typer(name="show")
# show = typer.Typer(name="show")
# run = typer.Typer(name="run")


class RunType(str, Enum):
    """Enum for type of what to run (file/module/function)."""

    file = "file"
    module = "module"
    function = "function"


def show(file: str) -> None:
    """Show a GDS or OAS file in KLayout through klive."""
    path = Path(file)
    logger.debug("Path = {}", path.resolve())
    if not path.exists():
        logger.critical("{file} does not exist, exiting", file=file)
        return
    if not path.is_file():
        logger.critical("{file} is not a file, exiting", file=file)
        return
    if not os.access(path, os.R_OK):
        logger.critical("No permission to read file {file}, exiting", file=file)
        return
    kfshow(path)


def run(
    file: Annotated[
        str,
        typer.Argument(default=..., help="The file|module|function to execute"),
    ],
    func_kwargs: Annotated[
        Optional[list[str]],  # noqa: UP007
        typer.Argument(
            help="Arguments used for --type function."
            " Doesn't have any influence for other types"
        ),
    ] = None,
    type: Annotated[
        RunType,
        typer.Option(
            help="Run a file or a module (`python -m <module_name>`) or a function"
        ),
    ] = RunType.file,
    show: Annotated[
        bool, typer.Option(help="Show the file through klive in KLayout")
    ] = True,
) -> None:
    """Run a python modules __main__ or a function if specified."""
    path = sys.path.copy()
    sys.path.append(os.getcwd())
    match type:
        case RunType.file:
            runpy.run_path(file, run_name="__main__")
        case RunType.module:
            runpy.run_module(file, run_name="__main__")
        case RunType.function:
            mod, func = file.rsplit(".", 1)
            logger.debug(f"{mod=},{func=}")
            try:
                spec = importlib.util.find_spec(mod)
                if spec is None or spec.loader is None:
                    raise ImportError
                _mod = importlib.util.module_from_spec(spec)
                sys.modules[mod] = _mod
                spec.loader.exec_module(_mod)
                kwargs = {}

                old_arg = ""
                if func_kwargs is not None:
                    for i, file in enumerate(func_kwargs):
                        if i % 2:
                            try:
                                value: int | float | str = int(file)
                            except ValueError:
                                try:
                                    value = float(file)
                                except ValueError:
                                    value = file
                            kwargs[old_arg] = value
                        else:
                            old_arg = file

                cell = getattr(_mod, func)(**kwargs)
                if show and isinstance(cell, KCell):
                    cell.show()
            except ImportError:
                logger.critical(
                    f"Couldn't import function '{func}' from module '{mod}'"
                )
    sys.path = path
