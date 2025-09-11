"""CLI interface for kfactory.

Use `kf --help` for more info.
"""

import importlib
import importlib.util
import os
import runpy
import sys
from enum import Enum
from pathlib import Path
from typing import Annotated

import typer

from ..conf import config, logger
from ..kcell import KCell
from ..kcell import show as kfshow
from ..layout import kcls
from ..utilities import save_layout_options

__all__ = ["build", "show"]


def show(
    file: Path,
) -> None:
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
    kfshow(path, use_libraries=True)


class LayoutSuffix(str, Enum):
    gds = "gds"
    gdsgz = "gds.gz"
    oas = "oas"


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
        list[str] | None,
        typer.Argument(
            help="Arguments used for --type function."
            " Doesn't have any influence for other types"
        ),
    ] = None,
    show: Annotated[
        bool, typer.Option(help="Show the file through klive in KLayout")
    ] = True,
    library: Annotated[
        list[str] | None,
        typer.Option(
            help="Library(s) used by the main layout file. Only works for functions,"
            " not for '__main__' modules"
        ),
    ] = None,
    suffix: Annotated[
        LayoutSuffix, typer.Option(help="Format of the layout files")
    ] = LayoutSuffix.oas,
    write_full: Annotated[
        bool,
        typer.Option(
            help="Write the gds with full library support. Uses libraries passed with"
            " --library. Only works in function mode not on modules"
        ),
    ] = True,
    write_static: Annotated[
        bool,
        typer.Option(
            help="Write a layout where all cells are converted to static (non-library)"
            " cells."
        ),
    ] = False,
    write_nocontext: Annotated[
        bool,
        typer.Option(
            help="Write the layout without any meta infos. This is useful for "
            "submitting the GDS to fabs."
        ),
    ] = False,
    max_vertex_count: Annotated[
        int, typer.Option(help="Maximum number of vertices per polygon.")
    ] = 4000,
    max_cellname_length: Annotated[
        int, typer.Option(help="Maximum number of characters in a cell name.")
    ] = 99,
) -> None:
    """Run a python modules __main__ or a function if specified."""
    path = sys.path.copy()
    sys.path.append(str(Path.cwd()))
    saveopts = save_layout_options()
    saveopts.gds2_max_cellname_length = max_cellname_length
    saveopts.gds2_max_vertex_count = max_vertex_count

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
                    raise ImportError  # noqa: TRY301
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
                if isinstance(cell, KCell):
                    gitpath = config.project_dir
                    if gitpath:
                        root = Path(gitpath) / "build/mask"
                        root.mkdir(parents=True, exist_ok=True)
                    else:
                        root = Path()
                    if show:
                        cell.show()
                    if write_full:
                        if library is not None:
                            for lib in library:
                                kcls[lib].write(root / f"{lib}.{suffix.value}")
                        cell.write(
                            root / f"{cell.name}.{suffix.value}",
                            save_options=saveopts,
                        )
                    if write_static:
                        cell.write(
                            root / f"{cell.name}_STATIC.{suffix.value}",
                            convert_external_cells=True,
                            save_options=saveopts,
                        )
                    if write_nocontext:
                        saveopts.write_context_info = False
                        cell.write(
                            root / f"{cell.name}_NOCONT.{suffix.value}",
                            save_options=saveopts,
                            convert_external_cells=True,
                        )

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
                if isinstance(cell, KCell):
                    gitpath = config.project_dir
                    if gitpath:
                        root = Path(gitpath) / "build/mask"
                        root.mkdir(parents=True, exist_ok=True)
                    else:
                        root = Path()
                    if show:
                        cell.show()
                    if write_full:
                        if library is not None:
                            for lib in library:
                                kcls[lib].write(root / f"{lib}.{suffix.value}")
                        cell.write(
                            root / f"{cell.name}.{suffix.value}",
                            save_options=saveopts,
                        )
                    if write_static:
                        cell.write(
                            root / f"{cell.name}_STATIC.{suffix.value}",
                            convert_external_cells=True,
                            save_options=saveopts,
                        )
                    if write_nocontext:
                        saveopts = save_layout_options()
                        saveopts.write_context_info = False
                        cell.write(
                            root / f"{cell.name}_NOCONT.{suffix.value}",
                            save_options=saveopts,
                            convert_external_cells=True,
                        )
            except ImportError:
                logger.critical(
                    f"Couldn't import function '{func}' from module '{mod_file}'"
                )
        else:
            runpy.run_module(mod_file, run_name="__main__")
        sys.path.pop(0)

    sys.path = path
