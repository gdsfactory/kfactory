"""Placer of bends/straights from a route."""

import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, TypeVar

from ruamel.yaml import YAML
from ruamel.yaml.constructor import SafeConstructor

from .enclosure import LayerEnclosure
from .kcell import KCell, KCLayout, Port, Ports
from .kcell import kcl as stdkcl

__all__ = ["cells_to_yaml", "cells_from_yaml"]

PathLike = TypeVar("PathLike", str, Path, None)


def cells_to_yaml(output: PathLike, cells: list[KCell] | KCell) -> None:
    """Convert cell(s) to a yaml representations.

    Args:
        output: A stream or string of a path where to dump the yaml. Can also be
            set to sys.stdout
        cells: A single [KCell][kfactory.kcell.KCell] or a list of them.


    Returns:
        yaml dump
    """
    yaml = YAML()
    yaml.register_class(KCell)
    yaml.register_class(Port)
    yaml.register_class(Ports)
    yaml.indent(sequence=4, offset=2)
    yaml.dump(cells, output)


def get_yaml_obj() -> YAML:
    """New global yaml object."""
    return YAML()


def register_classes(
    yaml: YAML,
    kcl: KCLayout = stdkcl,
    additional_classes: list[object] | None = None,
    verbose: bool = False,
) -> None:
    """Register a new KCell class compatible with ruamel yaml."""

    class ModKCell(KCell):
        def __init__(self, name: str | None = None, library: KCLayout = kcl):
            KCell.__init__(self, name, library)

        @classmethod
        def from_yaml(cls, constructor, node):  # type: ignore[no-untyped-def]
            return super().from_yaml(constructor, node, verbose=verbose)

    yaml.register_class(ModKCell)
    yaml.register_class(Port)
    yaml.register_class(Ports)
    yaml.register_class(LayerEnclosure)

    if additional_classes is not None:
        for c in additional_classes:
            yaml.register_class(c)


def cells_from_yaml(
    inp: Path,
    kcl: KCLayout = stdkcl,
    additional_classes: list[object] | None = None,
    verbose: bool = False,
) -> None:
    """Recreate cells from a yaml file.

    Args:
        inp: Input file path.
        kcl: KCLayout to load the cells into.
        additional_classes: Additional yaml classes that should be registered.
            This is used for example to enable loading additional yaml files etc.
        verbose: Print more verbose errors etc.
    """
    yaml = get_yaml_obj()
    yaml.register_class(
        include_from_loader(inp.parent, kcl, additional_classes, verbose)
    )

    register_classes(
        yaml,
        kcl,
        additional_classes,
        verbose,
    )
    yaml.load(inp)


def exploded_yaml(
    inp: os.PathLike[Any],
    library: KCLayout = stdkcl,
    additional_classes: list[object] | None = None,
    verbose: bool = False,
) -> Any:
    """Expanded yaml.

    Expand cross-references. Same syntax as :py:func:~`cells_from_yaml`
    """
    yaml = YAML(pure=True)

    class ModKCell(KCell):
        def __init__(self, name: str | None = None, library: KCLayout = library):
            KCell.__init__(self, name, library)

        @classmethod
        def from_yaml(cls, constructor, node):  # type: ignore[no-untyped-def]
            super().from_yaml(constructor, node, verbose=verbose)

    return yaml.dump(yaml.load(inp), sys.stdout)


def include_from_loader(
    folder: Path,
    library: KCLayout,
    additional_classes: list[object] | None,
    verbose: bool,
) -> Any:
    """Expand ruamel to support the `!include` keyword."""

    @dataclass
    class Include:
        filename: str
        yaml_tag: str = "!include"

        @classmethod
        def from_yaml(cls, constructor, node):  # type: ignore[no-untyped-def]
            d = SafeConstructor.construct_mapping(constructor, node)

            f = Path(d["filename"])
            if f.is_absolute():
                cells_from_yaml(f, library, additional_classes, verbose)
            else:
                cells_from_yaml(
                    (folder / f).resolve(), library, additional_classes, verbose
                )

    return Include
