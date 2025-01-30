from __future__ import annotations

from typing import Any, Self

from pydantic import BaseModel, model_validator

from .serialization import check_metadata_type, convert_metadata_type
from .typings import MetaData

__all__ = ["Info", "KCellSettings", "KCellSettingsUnits"]


class KCellSettings(BaseModel, extra="allow", validate_assignment=True, frozen=True):
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

    def __getitem__(self, key: str) -> Any:
        """Get the value of a setting."""
        return getattr(self, key)

    def get(self, __key: str, default: Any = None) -> Any:
        """Get the value of a setting."""
        return getattr(self, __key) if hasattr(self, __key) else default

    def __contains__(self, __key: str) -> bool:
        """Check if a setting exists."""
        return hasattr(self, __key)


class KCellSettingsUnits(
    BaseModel, extra="allow", validate_assignment=True, frozen=True
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

    def __getitem__(self, key: str) -> str | None:
        """Get the value of a setting."""
        return getattr(self, key, None)

    def get(self, __key: str, default: str | None = None) -> str | None:
        """Get the value of a setting."""
        return getattr(self, __key, default)

    def __contains__(self, __key: str) -> bool:
        """Check if a setting exists."""
        return hasattr(self, __key)


class Info(BaseModel, extra="allow", validate_assignment=True):
    """Settings for a KCell."""

    def __init__(self, **kwargs: Any) -> None:
        """Initialize the settings."""
        super().__init__(**kwargs)

    @model_validator(mode="before")
    @classmethod
    def restrict_types(
        cls,
        data: dict[str, MetaData],
    ) -> dict[str, MetaData]:
        """Restrict the types of the settings."""
        for name, value in data.items():
            try:
                data[name] = check_metadata_type(value)
            except ValueError as e:
                raise ValueError(
                    "Values of the info dict only support int, float, string ,tuple"
                    ", list, dict or None."
                    f"{name}: {value}, {type(value)}"
                ) from e

        return data

    def __getitem__(self, __key: str) -> Any:
        """Get the value of a setting."""
        return getattr(self, __key)

    def __setitem__(self, __key: str, __val: MetaData) -> None:
        """Set the value of a setting."""
        setattr(self, __key, __val)

    def get(self, __key: str, default: Any | None = None) -> Any:
        """Get the value of a setting."""
        return getattr(self, __key) if hasattr(self, __key) else default

    def update(self, data: dict[str, MetaData]) -> None:
        """Update the settings."""
        for key, value in data.items():
            setattr(self, key, value)

    def __iadd__(self, other: Info) -> Self:
        """Update the settings."""
        for key, value in other.model_dump().items():
            setattr(self, key, value)
        return self

    def __add__(self, other: Info) -> Self:
        """Update the settings."""
        return self.model_copy(update=other.model_dump())

    def __contains__(self, __key: str) -> bool:
        """Check if a setting exists."""
        return hasattr(self, __key)
