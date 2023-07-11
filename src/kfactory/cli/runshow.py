"""CLI interface for kfactory.

Use `kf --help` for more info.
"""
import importlib
import os
import runpy
import sys
from pathlib import Path

import click

from ..conf import logger
from ..kcell import KCell
from ..kcell import show as kfshow


@click.command()  # type:ignore[arg-type]
@click.argument(
    "file",
    required=True,
    type=str,
)
def show(arg: str, type_: str) -> None:
    """Show a GDS or OAS file in KLayout through klive."""
    path = Path(arg)
    logger.debug("Path = {}", path.resolve())
    if not path.exists():
        logger.critical("{type_} does not exist, exiting", type_=type_)
        return
    if not path.is_file():
        logger.critical("{type_} is not a file, exiting", type_=type_)
        return
    if not os.access(path, os.R_OK):
        logger.critical("No permission to read file {type_}, exiting", type_=type_)
        return
    kfshow(path)


@click.command(  # type: ignore[arg-type]
    context_settings={"ignore_unknown_options": True, "allow_extra_args": True}
)
@click.option(
    "--file",
    "type_",
    flag_value="file",
    help="Run __main__ of a python file",
    default=True,
    show_default=True,
)
@click.option(
    "--module",
    "type_",
    flag_value="module",
    help="Run __main__ of a module",
    show_default=True,
)
@click.option(
    "--function",
    "type_",
    flag_value="function",
    show_default=True,
)
@click.argument(
    "arg",
    required=True,
    type=str,
    # help="Python style module or function to run, e.g 'module.function'",
)
@click.option(
    "--show/--no-show",
    default=True,
    help="Show the KCell if one is returned with --function.",
)
@click.pass_context
def run(
    ctx: click.Context,
    arg: str,
    type_: str,
    show: bool,
) -> None:
    """Run a python modules __main__ or a function if specified."""
    path = sys.path.copy()
    sys.path.append(os.getcwd())
    match type_:
        case "file":
            runpy.run_path(arg, run_name="__main__")
        case "module":
            runpy.run_module(arg, run_name="__main__")
        case "function":
            mod, func = arg.rsplit(".", 1)
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
                for i, arg in enumerate(ctx.args):
                    if i % 2:
                        try:
                            value: int | float | str = int(arg)
                        except ValueError:
                            try:
                                value = float(arg)
                            except ValueError:
                                value = arg
                        kwargs[old_arg] = value
                    else:
                        old_arg = arg

                cell = getattr(_mod, func)(**kwargs)
                if show and isinstance(cell, KCell):
                    cell.show()
            except ImportError:
                logger.critical(
                    f"Couldn't import function '{func}' from module '{mod}'"
                )
    sys.path = path
