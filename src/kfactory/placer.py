import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional, TypeVar, Union

from ruamel.yaml import YAML
from ruamel.yaml.constructor import SafeConstructor

from .kcell import KCell, KLib, Port, Ports
from .kcell import klib as stdlib
from .utils import Enclosure

__all__ = ["cells_to_yaml", "cells_from_yaml"]

PathLike = TypeVar("PathLike", str, Path, None)


def cells_to_yaml(
    output: PathLike, cells: Union[list[KCell], KCell]
) -> None:  # , library: KLib=library):
    """Convert cell(s) to a yaml representations

    Args:
        output: A stream or string of a path where to dump the yaml. Can also be set to sys.stdout
        cells: A single :py:class:`~kfactory.kcell.KCell` or a list of them.
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
    return YAML()


def register_classes(
    yaml: YAML,
    library: KLib = stdlib,
    additional_classes: Optional[list[object]] = None,
    verbose: bool = False,
) -> None:
    class ModKCell(KCell):
        def __init__(self, name: Optional[str] = None, library: KLib = library):
            KCell.__init__(self, name, library)

        @classmethod
        def from_yaml(cls, constructor, node):  # type: ignore[no-untyped-def]
            return super().from_yaml(constructor, node, verbose=verbose)

    yaml.register_class(ModKCell)
    yaml.register_class(Port)
    yaml.register_class(Ports)
    yaml.register_class(Enclosure)

    if additional_classes is not None:
        for c in additional_classes:
            yaml.register_class(c)


def cells_from_yaml(
    inp: Path,
    library: KLib = stdlib,
    additional_classes: Optional[list[object]] = None,
    verbose: bool = False,
) -> None:
    yaml = get_yaml_obj()
    yaml.register_class(
        include_from_loader(inp.parent, library, additional_classes, verbose)
    )

    register_classes(
        yaml,
        library,
        additional_classes,
        verbose,
    )
    yaml.load(inp)


def exploded_yaml(
    inp: os.PathLike[Any],
    library: KLib = stdlib,
    additional_classes: Optional[list[object]] = None,
    verbose: bool = False,
) -> Any:
    yaml = YAML(pure=True)

    class ModKCell(KCell):
        def __init__(self, name: Optional[str] = None, library: KLib = library):
            KCell.__init__(self, name, library)

        @classmethod
        def from_yaml(cls, constructor, node):  # type: ignore[no-untyped-def]
            super().from_yaml(constructor, node, verbose=verbose)

    return yaml.dump(yaml.load(inp), sys.stdout)


def include_from_loader(
    folder: Path,
    library: KLib,
    additional_classes: Optional[list[object]],
    verbose: bool,
) -> Any:
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
