from __future__ import annotations

import functools
import inspect
from collections import UserDict, UserList
from collections.abc import Callable, Hashable
from hashlib import sha3_512
from types import FunctionType
from typing import TYPE_CHECKING, Any, overload

import klayout.db as kdb
import numpy as np
import toolz  # type: ignore[import-untyped,unused-ignore]

from .conf import config
from .typings import MetaData, SerializableShape

if TYPE_CHECKING:
    from .kcell import AnyKCell


class DecoratorList(UserList[Any]):
    """Hashable decorator for a list."""

    def __hash__(self) -> int:  # type: ignore[override]
        """Hash the list."""
        return hash(tuple(self.data))


class DecoratorDict(UserDict[Hashable, Any]):
    """Hashable decorator for a dictionary."""

    def __hash__(self) -> int:
        """Hash the dictionary."""
        return hash(tuple(sorted(self.data.items())))


def clean_dict(d: dict[str, Any]) -> dict[str, Any]:
    """Cleans dictionary recursively."""
    return {
        k: clean_dict(dict(v)) if isinstance(v, dict) else clean_value(v)
        for k, v in d.items()
    }


def clean_name(name: str) -> str:
    r"""Ensures that gds cells are composed of [a-zA-Z0-9_\-].

    FIXME: only a few characters are currently replaced.
        This function has been updated only on case-by-case basis
    """
    replace_map = {
        "=": "",
        ",": "_",
        ")": "",
        "(": "",
        "-": "m",
        ".": "p",
        ":": "_",
        "[": "",
        "]": "",
        " ": "_",
        "<": "",
        ">": "",
    }
    for k, v in list(replace_map.items()):
        name = name.replace(k, v)
    return name


def clean_value(
    value: float | np.float64 | dict[Any, Any] | AnyKCell | Callable[..., Any],
) -> str:
    """Makes sure a value is representable in a limited character_space."""
    if isinstance(value, int):  # integer
        return str(value)
    elif isinstance(value, float | np.float64):  # float
        return f"{value}".replace(".", "p").rstrip("0").rstrip("p")
    elif isinstance(value, kdb.LayerInfo):
        return f"{value.name or str(value.layer) + '_' + str(value.datatype)}"
    elif isinstance(value, list | tuple):
        return "_".join(clean_value(v) for v in value)
    elif isinstance(value, dict):
        return dict2name(**value)
    elif hasattr(value, "name"):
        return clean_name(value.name)  # type: ignore[arg-type]
    elif callable(value):
        if isinstance(value, FunctionType) and value.__name__ == "<lambda>":
            raise ValueError(
                "Unable to serialize lambda function. Use a named function instead."
            )
        if isinstance(value, functools.partial):
            sig = inspect.signature(value.func)
            args_as_kwargs = dict(zip(sig.parameters.keys(), value.args, strict=False))
            args_as_kwargs.update(**value.keywords)
            args_as_kwargs = clean_dict(args_as_kwargs)
            # args_as_kwargs.pop("function", None)
            func = value.func
            while hasattr(func, "func"):
                func = func.func
            v = {
                "function": func.__name__,
                "module": func.__module__,
                "settings": args_as_kwargs,
            }
            return clean_value(v)
        elif isinstance(value, toolz.functoolz.Compose):
            return "_".join(
                [clean_value(value.first)] + [clean_value(func) for func in value.funcs]
            )
        else:
            return getattr(value, "__name__", value.__class__.__name__)
    else:
        return clean_name(str(value))


@overload
def _to_hashable(d: dict[Hashable, Any]) -> DecoratorDict: ...


@overload
def _to_hashable(d: list[Any]) -> DecoratorList: ...


def _to_hashable(
    d: dict[Hashable, Any] | list[Any],
) -> DecoratorDict | DecoratorList:
    """Convert a `dict` to a `DecoratorDict`."""
    if isinstance(d, dict):
        ud = DecoratorDict()
        for item, value in sorted(d.items()):
            if isinstance(value, dict | list):
                value_: Any = _to_hashable(value)
            else:
                value_ = value
            ud[item] = value_
        return ud
    else:
        ul = DecoratorList([])
        for _index, value in enumerate(d):
            if isinstance(value, dict | list):
                value_ = _to_hashable(value)
            else:
                value_ = value
            ul.append(value_)
        return ul


@overload
def _hashable_to_original(udl: DecoratorDict) -> dict[Hashable, Any]: ...


@overload
def _hashable_to_original(udl: DecoratorList) -> list[Hashable]: ...


@overload
def _hashable_to_original(udl: Any) -> Any: ...


def _hashable_to_original(
    udl: DecoratorDict | DecoratorList | Any,
) -> dict[str, Any] | list[Any] | Any:
    """Convert `DecoratorDict` to `dict`."""
    if isinstance(udl, DecoratorDict):
        for item, value in udl.items():
            udl[item] = _hashable_to_original(value)
        return udl.data
    elif isinstance(udl, DecoratorList):
        list_ = []
        for v in udl:
            if isinstance(v, DecoratorDict | DecoratorList):
                list_.append(_hashable_to_original(v))
            else:
                list_.append(v)
        return list_
    return udl


def join_first_letters(name: str) -> str:
    """Join the first letter of a name separated with underscores.

    Example::

        "TL" == join_first_letters("taper_length")
    """
    return "".join([x[0] for x in name.split("_") if x])


def dict2name(prefix: str | None = None, **kwargs: dict[str, Any]) -> str:
    """Returns name from a dict."""
    kwargs.pop("self", None)
    label = [prefix] if prefix else []
    for key, value in kwargs.items():
        key = join_first_letters(key)
        label += [f"{key.upper()}{clean_value(value)}"]
    label_ = "_".join(label)
    return clean_name(label_)


def convert_metadata_type(value: Any) -> MetaData:
    """Recursively clean up a MetaData for KCellSettings."""
    if isinstance(value, int | float | bool | str | SerializableShape):
        return value
    elif value is None:
        return None
    elif isinstance(value, tuple):
        return tuple(convert_metadata_type(tv) for tv in value)
    elif isinstance(value, list):
        return list(convert_metadata_type(tv) for tv in value)
    elif isinstance(value, dict):
        return {k: convert_metadata_type(v) for k, v in value.items()}
    return clean_value(value)


def check_metadata_type(value: MetaData) -> MetaData:
    """Recursively check an info value whether it can be stored."""
    if value is None:
        return None
    elif isinstance(value, str | int | float | bool | SerializableShape):
        return value
    elif isinstance(value, tuple):
        return tuple(convert_metadata_type(tv) for tv in value)
    elif isinstance(value, list):
        return list(convert_metadata_type(tv) for tv in value)
    elif isinstance(value, dict):
        return {k: convert_metadata_type(v) for k, v in value.items()}
    raise ValueError(
        "Values of the info dict only support int, float, string, tuple or list."
        f"{value=}, {type(value)=}"
    )


def serialize_setting(setting: MetaData) -> MetaData:
    """Serialize a setting."""
    if isinstance(setting, dict):
        return {name: serialize_setting(_setting) for name, _setting in setting.items()}
    elif isinstance(setting, list):
        return [serialize_setting(s) for s in setting]
    elif isinstance(setting, tuple):
        return tuple(serialize_setting(s) for s in setting)
    elif isinstance(setting, SerializableShape):
        return f"!#{setting.__class__.__name__} {setting!s}"
    return setting


def deserialize_setting(setting: MetaData) -> MetaData:
    """Deserialize a setting."""
    if isinstance(setting, dict):
        return {
            name: deserialize_setting(_setting) for name, _setting in setting.items()
        }
    elif isinstance(setting, list):
        return [deserialize_setting(s) for s in setting]
    elif isinstance(setting, tuple):
        return tuple(deserialize_setting(s) for s in setting)
    elif isinstance(setting, str) and setting.startswith("!#"):
        cls_name, value = setting.removeprefix("!#").split(" ", 1)
        match cls_name:
            case "LayerInfo":
                return getattr(kdb, cls_name).from_string(value)  # type: ignore[no-any-return]
            case _:
                return getattr(kdb, cls_name).from_s(value)  # type: ignore[no-any-return]
    return setting


def get_cell_name(
    cell_type: str, max_cellname_length: int | None = None, **kwargs: dict[str, Any]
) -> str:
    """Convert a cell to a string."""
    name = cell_type
    max_cellname_length = max_cellname_length or config.max_cellname_length

    if kwargs:
        name += f"_{dict2name(None, **kwargs)}"

    if len(name) > max_cellname_length:
        name_hash = sha3_512(name.encode()).hexdigest()[:8]
        name = f"{name[: (max_cellname_length - 9)]}_{name_hash}"

    return name
