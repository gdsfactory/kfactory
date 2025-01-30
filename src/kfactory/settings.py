from __future__ import annotations

from typing import Any

from pydantic import BaseModel, model_validator

from .serialization import check_metadata_type, convert_metadata_type
from .typings import MetaData


class KCellSettings(BaseModel, extra="allow", validate_assignment=True, frozen=True):
    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)

    @model_validator(mode="before")
    @classmethod
    def restrict_types(cls, data: dict[str, Any]) -> dict[str, MetaData]:
        for name, value in data.items():
            data[name] = convert_metadata_type(value)
        return data

    def __getitem__(self, key: str) -> Any:
        return getattr(self, key)

    def get(self, __key: str, default: Any = None) -> Any:
        return getattr(self, __key) if hasattr(self, __key) else default

    def __contains__(self, __key: str) -> bool:
        return hasattr(self, __key)


class KCellSettingsUnits(
    BaseModel, extra="allow", validate_assignment=True, frozen=True
):
    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)

    @model_validator(mode="before")
    @classmethod
    def restrict_types(cls, data: dict[str, str]) -> dict[str, str]:
        for name, value in data.items():
            data[name] = str(value)
        return data

    def __getitem__(self, key: str) -> str | None:
        return getattr(self, key, None)

    def get(self, __key: str, default: str | None = None) -> str | None:
        return getattr(self, __key, default)

    def __contains__(self, __key: str) -> bool:
        return hasattr(self, __key)


class Info(BaseModel, extra="allow", validate_assignment=True):
    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)

    @model_validator(mode="before")
    @classmethod
    def restrict_types(
        cls,
        data: dict[str, MetaData],
    ) -> dict[str, MetaData]:
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
        return getattr(self, __key)

    def __setitem__(self, __key: str, __val: MetaData) -> None:
        setattr(self, __key, __val)

    def get(self, __key: str, default: Any | None = None) -> Any:
        return getattr(self, __key) if hasattr(self, __key) else default

    def update(self, data: dict[str, MetaData]) -> None:
        for key, value in data.items():
            setattr(self, key, value)

    def __iadd__(self, other: Info) -> Info:
        for key, value in other.model_dump().items():
            setattr(self, key, value)
        return self

    def __add__(self, other: Info) -> Info:
        return self.model_copy(update=other.model_dump())

    def __contains__(self, __key: str) -> bool:
        return hasattr(self, __key)
