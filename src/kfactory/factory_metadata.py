"""Factory metadata provider system.

Provides a provider-based system for attaching structured metadata
(device type, ports, models, tags, display hints) to cell factories
without coupling to schematic-driven layout.
"""

from __future__ import annotations

import inspect
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Literal, NotRequired, TypedDict

from pydantic import BaseModel, Field

type JSONSerializable = (
    int
    | float
    | bool
    | str
    | Sequence["JSONSerializable"]
    | Mapping[str, "JSONSerializable"]
    | None
)
type FactoryMetadataProviderKind = Literal[
    "metadata",
    "model",
    "device_type",
    "ports",
    "tags",
    "display",
    "info",
]


class PortSpec(TypedDict):
    """Structured port descriptor for cell metadata.

    Declares a logical port with its kind, physical side, and optional
    cross-section or aliasing information. Used by external tools
    (simulation runners, schematic editors) to understand a cell's
    interface without instantiating it.
    """

    name: str
    kind: str
    side: NotRequired[Literal["left", "right", "top", "bottom"] | None]
    orientation: NotRequired[Literal[0, 90, 180, 270] | None]
    order: NotRequired[int | None]
    cross_section: NotRequired[str | None]
    role: NotRequired[str | None]
    aliases: NotRequired[tuple[str, ...]]


class FactoryMetadata(BaseModel):
    """Resolved metadata for a cell factory.

    Aggregated from all registered providers for a given factory.
    Fields are intentionally loosely typed so consumers (gfp, PDKs,
    simulation packages) can define their own schemas on top.
    """

    device_type: str | None = None
    ports: tuple[PortSpec, ...] = ()
    models: list = Field(default_factory=list)
    tags: tuple[str, ...] = ()
    display: dict = Field(default_factory=dict)
    info: dict[str, JSONSerializable] = Field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class _FactoryMetadataPatch:
    device_type: str | None = None
    ports: tuple[PortSpec, ...] | None = None
    models: list | None = None
    models_position: Literal["append", "prepend"] = "append"
    tags: tuple[str, ...] = ()
    display: dict | None = None
    info: dict[str, JSONSerializable] | None = None


@dataclass(frozen=True, slots=True)
class _FactoryMetadataProviderRecord:
    target_kind: Literal["name", "fqn", "object"]
    target_key: str | int
    kind: FactoryMetadataProviderKind
    provider: Callable[..., Any]
    replace: bool = False
    position: Literal["append", "prepend"] = "append"
    order: int = 0


class FactoryMetadataRegistry:
    """Stores metadata provider registrations and resolves them per factory."""

    def __init__(self) -> None:
        self._records: list[_FactoryMetadataProviderRecord] = []
        self._counter = 0

    def add(
        self,
        *,
        target_kind: Literal["name", "fqn", "object"],
        target_key: str | int,
        kind: FactoryMetadataProviderKind,
        provider: Callable[..., Any],
        replace: bool = False,
        position: Literal["append", "prepend"] = "append",
    ) -> Callable[..., Any]:
        """Register a metadata provider for a target factory."""
        if position not in ("append", "prepend"):
            raise ValueError(f"Unknown model provider position: {position!r}")
        self._counter += 1
        self._records.append(
            _FactoryMetadataProviderRecord(
                target_kind=target_kind,
                target_key=target_key,
                kind=kind,
                provider=provider,
                replace=replace,
                position=position,
                order=self._counter,
            )
        )
        return provider

    def providers_for(
        self,
        *,
        name: str,
        qualified_name: str,
        obj: object,
    ) -> tuple[_FactoryMetadataProviderRecord, ...]:
        """Return all provider records matching a factory by name, FQN, or identity."""
        object_id = id(obj)
        return tuple(
            record
            for record in sorted(self._records, key=lambda r: r.order)
            if (
                (record.target_kind == "name" and record.target_key == name)
                or (record.target_kind == "fqn" and record.target_key == qualified_name)
                or (record.target_kind == "object" and record.target_key == object_id)
            )
        )


def call_provider(provider: Callable[..., Any], params: dict[str, Any]) -> Any:
    """Invoke a provider with the subset of cell params its signature accepts."""
    sig = inspect.signature(provider)
    accepts_kwargs = any(
        p.kind is inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values()
    )
    if accepts_kwargs:
        return provider(**params)

    provider_kwargs: dict[str, Any] = {}
    missing: list[str] = []
    for name, param in sig.parameters.items():
        if param.kind in (
            inspect.Parameter.POSITIONAL_ONLY,
            inspect.Parameter.VAR_POSITIONAL,
        ):
            raise TypeError(
                f"Metadata provider {provider!r} has unsupported parameter {name!r}."
            )
        if name in params:
            provider_kwargs[name] = params[name]
        elif param.default is inspect.Parameter.empty:
            missing.append(name)
    if missing:
        raise TypeError(
            f"Metadata provider {provider!r} requires parameters unavailable "
            f"from the cell factory: {missing!r}."
        )
    return provider(**provider_kwargs)


def provider_result_to_patch(
    record: _FactoryMetadataProviderRecord, result: Any
) -> _FactoryMetadataPatch:
    """Convert a provider's return value into a metadata patch."""
    match record.kind:
        case "metadata":
            return _metadata_result_to_patch(result)
        case "model":
            models = _coerce_models(result)
            return _FactoryMetadataPatch(
                models=models,
                models_position=record.position,
            )
        case "device_type":
            return _FactoryMetadataPatch(
                device_type=None if result is None else str(result)
            )
        case "ports":
            return _FactoryMetadataPatch(ports=_coerce_ports(result))
        case "tags":
            return _FactoryMetadataPatch(tags=_coerce_tags(result))
        case "display":
            return _FactoryMetadataPatch(
                display=None if result is None else _coerce_display(result)
            )
        case "info":
            if result is None:
                return _FactoryMetadataPatch()
            if not isinstance(result, Mapping):
                raise TypeError("info provider must return a mapping.")
            return _FactoryMetadataPatch(info={str(k): v for k, v in result.items()})


def resolve_metadata(
    providers: Iterable[_FactoryMetadataProviderRecord],
    params: dict[str, Any],
) -> FactoryMetadata:
    """Resolve all providers for a factory into a single FactoryMetadata."""
    device_type: str | None = None
    ports: tuple[PortSpec, ...] | None = None
    models: list = []
    tags: tuple[str, ...] = ()
    display: dict = {}
    info: dict[str, JSONSerializable] = {}

    for record in providers:
        result = call_provider(record.provider, params)
        patch = provider_result_to_patch(record, result)

        if patch.device_type is not None:
            if (
                device_type is not None
                and device_type != patch.device_type
                and not record.replace
            ):
                raise ValueError(
                    "Conflicting metadata device_type values: "
                    f"{device_type!r} and {patch.device_type!r}."
                )
            device_type = patch.device_type

        if patch.ports is not None:
            if ports is not None and ports != patch.ports and not record.replace:
                raise ValueError("Conflicting metadata port declarations.")
            ports = patch.ports

        if patch.models is not None:
            if patch.models_position == "prepend":
                models = patch.models + models
            else:
                models = models + patch.models

        if patch.tags:
            tags = _merge_tags(tags, patch.tags)

        if patch.display:
            if display and patch.display != display and not record.replace:
                raise ValueError("Conflicting metadata display declarations.")
            display = patch.display

        if patch.info:
            for key, value in patch.info.items():
                if key in info and info[key] != value:
                    raise ValueError(f"Conflicting metadata info key: {key!r}.")
                info[key] = value

    return FactoryMetadata(
        device_type=device_type,
        ports=ports or (),
        models=models,
        tags=tags,
        display=display,
        info=info,
    )


def _metadata_result_to_patch(result: Any) -> _FactoryMetadataPatch:
    if result is None:
        return _FactoryMetadataPatch()
    if isinstance(result, FactoryMetadata):
        return _FactoryMetadataPatch(
            device_type=result.device_type,
            ports=result.ports,
            models=list(result.models),
            tags=result.tags,
            display=result.display or None,
            info=result.info or None,
        )
    if not isinstance(result, Mapping):
        raise TypeError(
            "metadata_for provider must return a mapping or FactoryMetadata."
        )

    return _FactoryMetadataPatch(
        device_type=(
            None
            if result.get("device_type") is None
            else str(result.get("device_type"))
        ),
        ports=(
            None
            if "ports" not in result or result.get("ports") is None
            else _coerce_ports(result.get("ports"))
        ),
        models=_coerce_models(result.get("models", ())),
        tags=_coerce_tags(result.get("tags", ())),
        display=(
            _coerce_display(result.get("display")) if result.get("display") else None
        ),
        info=(
            None
            if result.get("info") is None
            else {str(k): v for k, v in dict(result.get("info", {})).items()}
        ),
    )


def _coerce_ports(value: Any) -> tuple[PortSpec, ...]:
    if value is None:
        return ()
    if isinstance(value, Mapping):
        return (dict(value),)  # type: ignore[return-value]
    return tuple(dict(p) if isinstance(p, Mapping) else p for p in value)  # type: ignore[return-value]


def _coerce_models(value: Any) -> list:
    if value is None:
        return []
    if isinstance(value, Mapping):
        return [dict(value)]
    if isinstance(value, Sequence) and not isinstance(value, str | bytes):
        return [dict(m) if isinstance(m, Mapping) else m for m in value]
    return [value]


def _coerce_display(value: Any) -> dict:
    if value is None:
        return {}
    if isinstance(value, Mapping):
        return dict(value)
    return {"name": str(value)}


def _coerce_tags(value: Any) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        return (value,)
    return tuple(str(tag) for tag in value)


def _merge_tags(existing: tuple[str, ...], new: tuple[str, ...]) -> tuple[str, ...]:
    seen = set(existing)
    merged = list(existing)
    for tag in new:
        if tag not in seen:
            seen.add(tag)
            merged.append(tag)
    return tuple(merged)
