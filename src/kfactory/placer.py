"""Placer of bends/straights from a route."""

import os  # noqa: I001
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Self, TypeVar

from .port import Port
from .ports import Ports
from .kcell import TKCell, ProtoTKCell
from ruamel.yaml import YAML
from ruamel.yaml.constructor import SafeConstructor

from .enclosure import LayerEnclosure
from .kcell import KCell, AnyTKCell
from .layout import KCLayout
from .layout import kcl as stdkcl

__all__ = ["cells_from_yaml", "cells_to_yaml"]

PathLike = TypeVar("PathLike", str, Path, None)


def cells_to_yaml(
    output: PathLike,
    cells: Sequence[AnyTKCell] | AnyTKCell | Sequence[TKCell] | TKCell,
) -> None:
    """Convert cell(s) to a yaml representations.

    Args:
        output: A stream or string of a path where to dump the yaml. Can also be
            set to sys.stdout
        cells: A single [KCell][kfactory.kcell.KCell] or a list of them.


    Returns:
        yaml dump
    """
    _cells = [cells] if isinstance(cells, ProtoTKCell | TKCell) else list(cells)
    _cells.sort(key=lambda c: c.hierarchy_levels())
    yaml = YAML()
    yaml.register_class(KCell)
    yaml.register_class(Port)
    yaml.register_class(Ports)
    yaml.indent(sequence=4, offset=2)
    yaml.dump(_cells, output)


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
        def __init__(self, name: str | None = None, library: KCLayout = kcl) -> None:
            KCell.__init__(self, name=name, kcl=library)

        @classmethod
        def from_yaml(
            cls,
            constructor: SafeConstructor,
            node: Any,
            verbose: bool = False,
        ) -> Self:
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
        def __init__(
            self, name: str | None = None, library: KCLayout = library
        ) -> None:
            KCell.__init__(self, name=name, kcl=library)

        @classmethod
        def from_yaml(
            cls, constructor: SafeConstructor, node: Any, verbose: bool = False
        ) -> Self:
            return super().from_yaml(constructor, node, verbose=verbose)

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
        def from_yaml(cls, constructor: SafeConstructor, node: Any) -> None:
            d = SafeConstructor.construct_mapping(constructor, node)

            f = Path(d["filename"])
            if f.is_absolute():
                cells_from_yaml(f, library, additional_classes, verbose)
            else:
                cells_from_yaml(
                    (folder / f).resolve(), library, additional_classes, verbose
                )

    return Include
