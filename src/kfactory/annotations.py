from __future__ import annotations

import inspect
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Literal

from pydantic import BaseModel, Field, TypeAdapter

type JSONSerializable = (
    int
    | float
    | bool
    | str
    | Sequence["JSONSerializable"]
    | Mapping[str, "JSONSerializable"]
    | None
)
type AnnotationProviderKind = Literal[
    "annotate",
    "model",
    "device_type",
    "ports",
    "tags",
    "display",
    "metadata",
]


class AnnotationPort(BaseModel):
    name: str
    kind: str
    side: Literal["left", "right", "top", "bottom"] | None = None
    orientation: Literal[0, 90, 180, 270] | None = None
    order: int | None = None
    cross_section: str | None = None
    role: str | None = None
    aliases: tuple[str, ...] = ()


class CellAnnotation(BaseModel):
    device_type: str | None = None
    ports: tuple[AnnotationPort, ...] = ()
    models: list = Field(default_factory=list)
    tags: tuple[str, ...] = ()
    display: dict = Field(default_factory=dict)
    metadata: dict[str, JSONSerializable] = Field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class _CellAnnotationPatch:
    device_type: str | None = None
    ports: tuple[AnnotationPort, ...] | None = None
    models: list | None = None
    models_position: Literal["append", "prepend"] = "append"
    tags: tuple[str, ...] = ()
    display: dict | None = None
    metadata: dict[str, JSONSerializable] | None = None


@dataclass(frozen=True, slots=True)
class _AnnotationProviderRecord:
    target_kind: Literal["name", "fqn", "object"]
    target_key: str | int
    kind: AnnotationProviderKind
    provider: Callable[..., Any]
    replace: bool = False
    position: Literal["append", "prepend"] = "append"
    order: int = 0


class AnnotationRegistry:
    def __init__(self) -> None:
        self._records: list[_AnnotationProviderRecord] = []
        self._counter = 0

    def add(
        self,
        *,
        target_kind: Literal["name", "fqn", "object"],
        target_key: str | int,
        kind: AnnotationProviderKind,
        provider: Callable[..., Any],
        replace: bool = False,
        position: Literal["append", "prepend"] = "append",
    ) -> Callable[..., Any]:
        if position not in ("append", "prepend"):
            raise ValueError(f"Unknown model provider position: {position!r}")
        self._counter += 1
        self._records.append(
            _AnnotationProviderRecord(
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
    ) -> tuple[_AnnotationProviderRecord, ...]:
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
                f"Annotation provider {provider!r} has unsupported parameter {name!r}."
            )
        if name in params:
            provider_kwargs[name] = params[name]
        elif param.default is inspect.Parameter.empty:
            missing.append(name)
    if missing:
        raise TypeError(
            f"Annotation provider {provider!r} requires parameters unavailable "
            f"from the cell factory: {missing!r}."
        )
    return provider(**provider_kwargs)


def provider_result_to_patch(
    record: _AnnotationProviderRecord, result: Any
) -> _CellAnnotationPatch:
    match record.kind:
        case "annotate":
            return _annotation_result_to_patch(result)
        case "model":
            models = _coerce_models(result)
            return _CellAnnotationPatch(
                models=models,
                models_position=record.position,
            )
        case "device_type":
            return _CellAnnotationPatch(
                device_type=None if result is None else str(result)
            )
        case "ports":
            return _CellAnnotationPatch(ports=_coerce_ports(result))
        case "tags":
            return _CellAnnotationPatch(tags=_coerce_tags(result))
        case "display":
            return _CellAnnotationPatch(
                display=None if result is None else _coerce_display(result)
            )
        case "metadata":
            if result is None:
                return _CellAnnotationPatch()
            if not isinstance(result, Mapping):
                raise TypeError("metadata provider must return a mapping.")
            return _CellAnnotationPatch(metadata={str(k): v for k, v in result.items()})


def resolve_annotation(
    providers: Iterable[_AnnotationProviderRecord],
    params: dict[str, Any],
) -> CellAnnotation:
    device_type: str | None = None
    ports: tuple[AnnotationPort, ...] | None = None
    models: list = []
    tags: tuple[str, ...] = ()
    display: dict = {}
    metadata: dict[str, JSONSerializable] = {}

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
                    "Conflicting annotation device_type values: "
                    f"{device_type!r} and {patch.device_type!r}."
                )
            device_type = patch.device_type

        if patch.ports is not None:
            if ports is not None and ports != patch.ports and not record.replace:
                raise ValueError("Conflicting annotation port declarations.")
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
                raise ValueError("Conflicting annotation display declarations.")
            display = patch.display

        if patch.metadata:
            for key, value in patch.metadata.items():
                if key in metadata and metadata[key] != value:
                    raise ValueError(f"Conflicting annotation metadata key: {key!r}.")
                metadata[key] = value

    return CellAnnotation(
        device_type=device_type,
        ports=ports or (),
        models=models,
        tags=tags,
        display=display,
        metadata=metadata,
    )


def _annotation_result_to_patch(result: Any) -> _CellAnnotationPatch:
    if result is None:
        return _CellAnnotationPatch()
    if isinstance(result, CellAnnotation):
        return _CellAnnotationPatch(
            device_type=result.device_type,
            ports=result.ports,
            models=list(result.models),
            tags=result.tags,
            display=result.display or None,
            metadata=result.metadata or None,
        )
    if not isinstance(result, Mapping):
        raise TypeError(
            "annotate_for provider must return a mapping or CellAnnotation."
        )

    return _CellAnnotationPatch(
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
        metadata=(
            None
            if result.get("metadata") is None
            else {str(k): v for k, v in dict(result.get("metadata", {})).items()}
        ),
    )


_port_adapter: TypeAdapter[AnnotationPort] = TypeAdapter(AnnotationPort)


def _coerce_ports(value: Any) -> tuple[AnnotationPort, ...]:
    if value is None:
        return ()
    if isinstance(value, AnnotationPort):
        return (value,)
    return tuple(_port_adapter.validate_python(port) for port in value)


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
