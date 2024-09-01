"""CLI interface for kfactory.

Use `kf --help` for more info.
"""

import importlib
import os
import runpy
import sys
from pathlib import Path
from typing import Annotated, Optional

import typer

from ..conf import logger
from ..kcell import KCell
from ..kcell import show as kfshow


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


def build(
    build_ref: Annotated[
        str,
        typer.Argument(
            default=...,
            help="The file|module|function to execute:\n"
            "Accepted Formats:\n- /path/to/file.py::cell_function_name\n"
            "- module.submodule::cell_function_name\n"
            "- /path/to/file.py\n"
            "- module.submodule",
        ),
    ],
    func_kwargs: Annotated[
        Optional[list[str]],  # noqa: UP007
        typer.Argument(
            help="Arguments used for --type function."
            " Doesn't have any influence for other types"
        ),
    ] = None,
    show: Annotated[
        bool, typer.Option(help="Show the file through klive in KLayout")
    ] = True,
) -> None:
    """Run a python modules __main__ or a function if specified."""
    path = sys.path.copy()
    sys.path.append(os.getcwd())

    build_split = build_ref.rsplit("::", 1)
    if len(build_split) == 1:
        mod_file = build_split[0]
        func: str | None = None
    else:
        mod_file, func = build_split

    if mod_file.endswith(".py"):
        file = Path(mod_file).expanduser().resolve()
        if not file.is_file():
            raise ImportError(f"File {file} does not exist")
        sys.path.insert(0, str(file.parent))
        if func is not None:
            logger.debug(f"{mod_file=},{func=}")
            try:
                spec = importlib.util.find_spec(str(file.name.removesuffix(".py")))
                if spec is None or spec.loader is None:
                    raise ImportError
                _mod = importlib.util.module_from_spec(spec)
                sys.modules[file.stem] = _mod
                spec.loader.exec_module(_mod)
                sys.path.pop(0)
                kwargs = {}

                old_arg = ""
                if func_kwargs is not None:
                    for i, kwarg in enumerate(func_kwargs):
                        if i % 2:
                            try:
                                value: int | float | str = int(kwarg)
                            except ValueError:
                                try:
                                    value = float(kwarg)
                                except ValueError:
                                    value = kwarg
                            kwargs[old_arg] = value
                        else:
                            old_arg = kwarg

                cell = getattr(_mod, func)(**kwargs)
                if show and isinstance(cell, KCell):
                    cell.show()
            except ImportError:
                logger.critical(
                    f"Couldn't import function '{func}' from module '"
                    f"{file.with_suffix('')}"
                    "'"
                )
        else:
            runpy.run_path(mod_file, run_name="__main__")
            sys.path.pop(0)
    else:
        sys.path.insert(0, ".")
        if func:
            logger.debug(f"{mod_file=},{func=}")
            try:
                _mod = importlib.import_module(mod_file)
                kwargs = {}

                old_arg = ""
                if func_kwargs is not None:
                    for i, kwarg in enumerate(func_kwargs):
                        if i % 2:
                            try:
                                value = int(kwarg)
                            except ValueError:
                                try:
                                    value = float(kwarg)
                                except ValueError:
                                    value = kwarg
                            kwargs[old_arg] = value
                        else:
                            old_arg = kwarg

                cell = getattr(_mod, func)(**kwargs)
                if show and isinstance(cell, KCell):
                    cell.show()
            except ImportError:
                logger.critical(
                    f"Couldn't import function '{func}' from module '{mod_file}'"
                )
        else:
            runpy.run_module(mod_file, run_name="__main__")
        sys.path.pop(0)

    sys.path = path
