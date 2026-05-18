from __future__ import annotations

from typing import TYPE_CHECKING, Any, Self

from pydantic import BaseModel, model_validator

from .serialization import check_metadata_type, convert_metadata_type

if TYPE_CHECKING:
    from .typings import MetaData

__all__ = ["Info", "KCellSettings", "KCellSettingsUnits", "SettingMixin"]


# Info keys that get int → float coerced before being stored. Several
# gdsfactory factories declare these props as `float` but accept callers
# passing integer literals (e.g. `coupler_ring(length_x: float = 4)`).
# Combined with gdsfactory's value-not-type ``@cell`` cache, the first
# call's Python type wins and kfactory then serialises it literally into
# the ``kfactory:info`` PROPVALUE — ``#l4`` for int, ``##4`` for float —
# producing different GDS bytes for what callers reasonably consider the
# same component. Normalising just these specific length/weight props
# keeps the on-disk META stable across cache orderings, without touching
# KCellSettings (which would change the type seen by user code reading
# back ``cell.settings[...]``).
_NORMALIZE_TO_FLOAT_KEYS: frozenset[str] = frozenset(
    {"length", "route_info_length", "route_info_weight"}
)


def _should_normalize_to_float(key: str) -> bool:
    if key in _NORMALIZE_TO_FLOAT_KEYS:
        return True
    # `route_info_<layer>_length` — layer-dependent name, always a length.
    return key.startswith("route_info_") and key.endswith("_length")


def _maybe_normalize_to_float(key: str, value: Any) -> Any:
    if (
        _should_normalize_to_float(key)
        and isinstance(value, int)
        and not isinstance(value, bool)
    ):
        return float(value)
    return value


class SettingMixin:
    """Mixin class for shared settings functionality."""

    def __getattr__(self, key: str) -> Any:
        """Get the value of a setting."""
        return super().__getattr__(key)  # ty:ignore[unresolved-attribute]

    def __getitem__(self, key: str) -> Any:
        """Get the value of a setting."""
        return getattr(self, key)

    def get(self, __key: str, /, default: Any = None) -> Any:
        """Get the value of a setting."""
        return getattr(self, __key, default)

    def __contains__(self, __key: str, /) -> bool:
        """Check if a setting exists."""
        return hasattr(self, __key)

    def __str__(self) -> str:
        """Return the representation of the settings."""
        return repr(self)


class KCellSettings(
    SettingMixin, BaseModel, extra="allow", validate_assignment=True, frozen=True
):
    """Settings for a BaseKCell."""

    def __init__(self, **kwargs: Any) -> None:
        """Initialize the settings."""
        super().__init__(**kwargs)

    @model_validator(mode="before")
    @classmethod
    def restrict_types(cls, data: dict[str, Any]) -> dict[str, MetaData]:
        """Restrict the types of the settings."""
        for name, value in data.items():
            data[name] = convert_metadata_type(value)
        return data


class KCellSettingsUnits(
    SettingMixin, BaseModel, extra="allow", validate_assignment=True, frozen=True
):
    """Settings for the units of a KCell."""

    def __init__(self, **kwargs: Any) -> None:
        """Initialize the settings."""
        super().__init__(**kwargs)

    @model_validator(mode="before")
    @classmethod
    def restrict_types(cls, data: dict[str, str]) -> dict[str, str]:
        """Restrict the types of the settings."""
        for name, value in data.items():
            data[name] = str(value)
        return data


class Info(SettingMixin, BaseModel, extra="allow"):
    """Info for a KCell.

    `validate_assignment` is intentionally off: combined with a
    `model_validator(mode="before")` it would re-run validation against the
    entire extras dict on every per-field write, which historically silently
    coerced previously-stored values via `clean_value()` (see #944). Per-write
    validation is handled in `__setattr__` and only inspects the new value.
    """

    def __init__(self, **kwargs: Any) -> None:
        """Initialize the settings."""
        super().__init__(**kwargs)

    @model_validator(mode="before")
    @classmethod
    def restrict_types(cls, data: dict[str, MetaData]) -> dict[str, MetaData]:
        """Restrict the types of the settings (runs at construction only)."""
        for name, value in data.items():
            data[name] = cls._check_value(name, value)
        return data

    @staticmethod
    def _check_value(name: str, value: MetaData) -> MetaData:
        try:
            return check_metadata_type(_maybe_normalize_to_float(name, value))
        except ValueError as e:
            raise ValueError(
                "Values of the info dict only support int, float, string, "
                "tuple, list, dict or None."
                f"{name}: {value}, {type(value)}"
            ) from e

    def __setattr__(self, name: str, value: Any) -> None:
        """Validate the assigned value, then store it."""
        if name.startswith("_"):
            super().__setattr__(name, value)
            return
        super().__setattr__(name, self._check_value(name, value))

    def update(self, data: dict[str, MetaData]) -> None:
        """Update the settings."""
        validated = {k: self._check_value(k, v) for k, v in data.items()}
        for key, value in validated.items():
            super().__setattr__(key, value)

    def __setitem__(self, key: str, value: MetaData) -> None:
        """Set the value of a setting."""
        setattr(self, key, value)

    def __iadd__(self, other: Info) -> Self:
        """Update the settings."""
        for key, value in other.model_dump().items():
            setattr(self, key, value)
        return self

    def __add__(self, other: Info) -> Self:
        """Update the settings."""
        return self.model_copy(update=other.model_dump())
