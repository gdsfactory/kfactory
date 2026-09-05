from __future__ import annotations

import functools
import inspect
import json
from collections import UserDict, UserList
from collections.abc import Callable, Hashable
from hashlib import sha3_512
from types import FunctionType, UnionType
from typing import TYPE_CHECKING, Any, TypeGuard, overload

import numpy as np
import toolz

from . import kdb
from .conf import config
from .exceptions import CellNameError

if TYPE_CHECKING:
    from .cross_section import CrossSectionSpec
    from .kcell import AnyKCell
    from .layout import KCLayout
    from .typings import (
        DShapeLike,
        IShapeLike,
        JSONSerializable,
        MetaData,
        SerializableShape,
    )


class DecoratorList(UserList[Any]):
    """Hashable decorator for a list."""

    def __hash__(self) -> int:
        """Hash the list."""
        return hash(tuple(self.data))

    def __reduce__(self) -> tuple[type[DecoratorList], tuple[list[Any]]]:
        return (DecoratorList, (self.data,))


class DecoratorDict(UserDict[Hashable, Any]):
    """Hashable decorator for a dictionary."""

    def __hash__(self) -> int:
        """Hash the dictionary."""
        return hash(tuple(sorted(self.data.items())))

    def __reduce__(self) -> tuple[type[DecoratorDict], tuple[dict[Hashable, Any]]]:
        return (DecoratorDict, (self.data,))


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


def cell_name_hash(name: str) -> str:
    """Return 8-char hash of a cell name."""
    return sha3_512(name.encode()).hexdigest()[:8]


def clean_value(
    value: float | np.float64 | dict[Any, Any] | AnyKCell | Callable[..., Any],
) -> str:
    """Makes sure a value is representable in a limited character_space."""
    if isinstance(value, int):  # integer
        return str(value)
    if isinstance(value, float | np.float64):  # float
        return f"{value}".replace(".", "p").rstrip("0").rstrip("p")
    if isinstance(value, kdb.LayerInfo):
        return f"{value.name or str(value.layer) + '_' + str(value.datatype)}"
    if isinstance(value, list | tuple):
        return "_".join(clean_value(v) for v in value)
    if isinstance(value, dict):
        try:
            return dict2name(**value)
        except TypeError as e:
            raise CellNameError(
                "Dictionaries passed to functions as args/kwargs"
                " must be of type dict[str, ...] to be properly serialized"
                " for Cell/Component names or similar."
            ) from e
    if hasattr(value, "name"):
        return clean_name(value.name)  # ty:ignore[invalid-argument-type]
    if callable(value):
        if isinstance(value, FunctionType) and value.__name__ == "<lambda>":
            msg = "Unable to serialize lambda function. Use a named function instead."
            raise ValueError(msg)
        if isinstance(value, functools.partial):
            sig = inspect.signature(value.func)
            args_as_kwargs = dict(zip(sig.parameters.keys(), value.args, strict=False))
            args_as_kwargs.update(**value.keywords)
            args_as_kwargs = clean_dict(args_as_kwargs)
            func = value.func
            while hasattr(func, "func"):
                func = func.func
            v = {
                "function": get_function_name(func),  # ty:ignore[invalid-argument-type]
                "module": func.__module__,
                "settings": args_as_kwargs,
            }
            return clean_value(v)
        if isinstance(value, toolz.functoolz.Compose):
            return "_".join(
                [clean_value(value.first)] + [clean_value(func) for func in value.funcs]
            )
        return getattr(value, "__name__", value.__class__.__name__)
    return clean_name(str(value))


@overload
def to_hashable(d: dict[Hashable, Any]) -> DecoratorDict: ...


@overload
def to_hashable(d: list[Any]) -> DecoratorList: ...


def to_hashable(
    d: dict[Hashable, Any] | list[Any],
) -> DecoratorDict | DecoratorList:
    """Convert a `dict` to a `DecoratorDict`."""
    if isinstance(d, dict):
        ud = DecoratorDict()
        for item, value in sorted(d.items()):
            if isinstance(value, dict | list):
                value_: Any = to_hashable(value)
            else:
                value_ = value
            ud[item] = value_
        return ud
    ul = DecoratorList([])
    for _index, value in enumerate(d):
        value_ = to_hashable(value) if isinstance(value, dict | list) else value
        ul.append(value_)
    return ul


@overload
def hashable_to_original(udl: DecoratorDict) -> dict[Hashable, Any]: ...


@overload
def hashable_to_original(udl: DecoratorList) -> list[Hashable]: ...


@overload
def hashable_to_original(udl: Any) -> Any: ...


def hashable_to_original(
    udl: DecoratorDict | DecoratorList | Any,
) -> dict[str, Any] | list[Any] | Any:
    """Convert `DecoratorDict` to `dict`."""
    if isinstance(udl, DecoratorDict):
        for item, value in udl.items():
            udl[item] = hashable_to_original(value)
        return udl.data
    if isinstance(udl, DecoratorList):
        list_: list[Any] = []
        for v in udl:
            if isinstance(v, DecoratorDict | DecoratorList):
                list_.append(hashable_to_original(v))
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
        key_ = join_first_letters(key)
        label += [f"{key_.upper()}{clean_value(value)}"]
    label_ = "_".join(label)
    return clean_name(label_)


def convert_metadata_type(value: Any) -> MetaData:
    """Recursively clean up a MetaData for KCellSettings."""
    if value is None:
        return None
    if isinstance(value, float):
        if value.is_integer():
            return int(value)
        return value
    if serializible_value_or_shape_guard(value):
        return value
    if isinstance(value, tuple):
        return tuple(convert_metadata_type(tv) for tv in value)
    if isinstance(value, list):
        return [convert_metadata_type(tv) for tv in value]
    if isinstance(value, dict):
        return {k: convert_metadata_type(v) for k, v in value.items()}
    return clean_value(value)


def check_metadata_type(value: Any) -> MetaData:
    """Recursively check an info value whether it can be stored."""
    if value is None:
        return None
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    if serializible_value_or_shape_guard(value):
        return value
    if isinstance(value, tuple):
        return tuple(check_metadata_type(tv) for tv in value)
    if isinstance(value, list):
        return [check_metadata_type(tv) for tv in value]
    if isinstance(value, dict):
        return {k: check_metadata_type(v) for k, v in value.items()}
    msg = (
        "MetaData values of the info dict only support int, float, string"
        f", tuple or list. {value=}, {type(value)=}"
    )
    raise ValueError(msg)


# ``kdb`` collection wrappers have ``to_s`` but no ``from_s``. They are encoded
# element-wise instead: each element (which *does* have ``from_s``) is dumped via
# its own ``to_s`` into a JSON list, so the payload is robust to the delimiter
# characters (``;``, ``)``, ``'``) that ``to_s`` reuses inside and between
# elements. Maps the wrapper class name to (wrapper_class, element_class).
_COLLECTION_SHAPES: dict[str, tuple[type[Any], type[Any]]] = {
    "Region": (kdb.Region, kdb.Polygon),
    "Edges": (kdb.Edges, kdb.Edge),
    "Texts": (kdb.Texts, kdb.Text),
    "EdgePairs": (kdb.EdgePairs, kdb.EdgePair),
}
# ``kdb`` matrices also lack ``from_s``; they are encoded as a JSON list of their
# scalar components and rebuilt through their component constructor.
_MATRIX_SHAPES: frozenset[str] = frozenset({"Matrix2d", "Matrix3d"})


def _serialize_shape(shape: SerializableShape) -> str:
    """Encode a ``kdb`` shape as a ``!#ClassName <payload>`` string."""
    cls_name = type(shape).__name__
    if cls_name in _COLLECTION_SHAPES:
        return f"!#{cls_name} " + json.dumps([e.to_s() for e in shape.each()])
    if cls_name == "Matrix2d":
        return "!#Matrix2d " + json.dumps(
            [shape.m11(), shape.m12(), shape.m21(), shape.m22()]
        )
    if cls_name == "Matrix3d":
        return "!#Matrix3d " + json.dumps(
            [shape.m(i, j) for i in range(3) for j in range(3)]
        )
    return f"!#{cls_name} {shape!s}"


def _deserialize_shape(cls_name: str, payload: str) -> SerializableShape:
    """Rebuild a ``kdb`` shape from a ``!#ClassName <payload>`` string."""
    if cls_name in _COLLECTION_SHAPES:
        wrapper_cls, element_cls = _COLLECTION_SHAPES[cls_name]
        return wrapper_cls([element_cls.from_s(s) for s in json.loads(payload)])
    if cls_name in _MATRIX_SHAPES:
        return getattr(kdb, cls_name)(*json.loads(payload))
    if cls_name == "LayerInfo":
        return kdb.LayerInfo.from_string(payload)
    return getattr(kdb, cls_name).from_s(payload)


def serialize_setting(setting: MetaData) -> JSONSerializable:
    """Serialize a setting to a JSON-compatible form.

    ``kdb`` shapes are encoded as a ``!#ClassName <payload>`` string so they
    survive JSON/YAML/GDS-property stores that cannot hold native ``kdb``
    objects. The inverse is :func:`deserialize_setting`; the two are symmetric
    for every shape in :data:`~kfactory.typings.SerializableShape`.
    """
    if setting is None:
        return None
    if isinstance(setting, dict):
        return {
            str(name): serialize_setting(_setting) for name, _setting in setting.items()
        }
    if isinstance(setting, list):
        return [serialize_setting(s) for s in setting]
    if isinstance(setting, tuple):
        return tuple(serialize_setting(s) for s in setting)
    if serializible_shape_guard(setting):
        return _serialize_shape(setting)
    return setting  # ty:ignore[invalid-return-type]


def deserialize_setting(setting: JSONSerializable) -> MetaData:
    """Deserialize a setting produced by :func:`serialize_setting`."""
    if isinstance(setting, dict):
        return {
            name: deserialize_setting(_setting) for name, _setting in setting.items()
        }
    if isinstance(setting, list):
        return [deserialize_setting(s) for s in setting]
    if isinstance(setting, tuple):
        return tuple(deserialize_setting(s) for s in setting)
    if isinstance(setting, str) and setting.startswith("!#"):
        cls_name, payload = setting.removeprefix("!#").split(" ", 1)
        return _deserialize_shape(cls_name, payload)
    return setting


def serialize_info_blob(info: dict[str, MetaData]) -> str:
    """Serialize an info dict to a single JSON blob for string-only stores.

    Used where metadata must round-trip through a single string value (e.g. a
    ``kdb.Instance`` user property, which GDS coerces to a string), as opposed
    to the native per-cell meta info used for cells.
    """
    return json.dumps(serialize_setting(info))


def deserialize_info_blob(blob: str) -> dict[str, MetaData]:
    """Deserialize a JSON info blob produced by :func:`serialize_info_blob`."""
    data = deserialize_setting(json.loads(blob))
    if not isinstance(data, dict):
        raise TypeError(f"Info blob did not decode to a dict: {blob!r}")
    return data


def get_cell_name(
    cell_type: str, max_cellname_length: int | None = None, **kwargs: dict[str, Any]
) -> str:
    """Convert a cell to a string."""
    name = cell_type
    max_cellname_length = max_cellname_length or config.max_cellname_length

    if kwargs:
        name += f"_{dict2name(None, **kwargs)}"

    if len(name) > max_cellname_length:
        name_hash = cell_name_hash(name)
        name = f"{name[: (max_cellname_length - 9)]}_{name_hash}"

    return name


_ISHAPES: UnionType = (
    kdb.Box
    | kdb.Edge
    | kdb.Path
    | kdb.Polygon
    | kdb.Region
    | kdb.SimplePolygon
    | kdb.Text
)
_DSHAPES: UnionType = (
    kdb.DBox | kdb.DEdge | kdb.DPath | kdb.DPolygon | kdb.DSimplePolygon | kdb.DText
)
_SERIALIZABLE_SHAPES: UnionType = (
    kdb.CplxTrans
    | kdb.DCplxTrans
    | kdb.DEdgePair
    | kdb.DPoint
    | kdb.DTrans
    | kdb.DVector
    | kdb.EdgePair
    | kdb.EdgePairs
    | kdb.Edges
    | kdb.ICplxTrans
    | kdb.LayerInfo
    | kdb.Matrix2d
    | kdb.Matrix3d
    | kdb.Point
    | kdb.Texts
    | kdb.Trans
    | kdb.VCplxTrans
    | kdb.Vector
    | _ISHAPES
    | _DSHAPES
)
_SERIALIZABLE_VALUES_OR_SHAPES: UnionType = (
    bool | int | float | str | _SERIALIZABLE_SHAPES
)


def serializible_value_or_shape_guard(
    value: Any,
) -> TypeGuard[int | float | bool | str | SerializableShape]:
    return isinstance(value, _SERIALIZABLE_VALUES_OR_SHAPES)


def serializible_shape_guard(
    value: Any,
) -> TypeGuard[SerializableShape]:
    return isinstance(value, _SERIALIZABLE_SHAPES)


def ishape_guard(value: Any) -> TypeGuard[IShapeLike]:
    return isinstance(value, _ISHAPES)


def dshape_guard(value: Any) -> TypeGuard[DShapeLike]:
    return isinstance(value, _DSHAPES)


def get_function_name(f: Callable[..., Any]) -> str:
    if hasattr(f, "__name__"):
        return str(f.__name__)
    if hasattr(f, "func") and callable(f.func):
        return get_function_name(f.func)
    raise ValueError(f"Function {f} has no name.")


def kcl_cross_section_serializer(
    kcl: KCLayout,
) -> Callable[[CrossSectionSpec], str]:
    def serialize_cross_section_spec(cross_section_spec: CrossSectionSpec) -> str:
        return kcl.get_icross_section(cross_section_spec).name

    return serialize_cross_section_spec
