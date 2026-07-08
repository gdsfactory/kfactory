from __future__ import annotations

import inspect
from collections.abc import Callable, Iterable, Iterator, Mapping, Sequence
from dataclasses import dataclass
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, RootModel, TypeAdapter

type ParamExpr = str
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


class DisplaySpec(BaseModel):
    kind: str = "builtin"
    name: str | None = None
    path: str | None = None
    library: str | None = None
    parameters: dict[str, JSONSerializable] = Field(default_factory=dict)


class BaseModelSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    language: str
    simulator: str | None = None
    implementation: str | None = None
    name: str
    port_order: tuple[str, ...] = ()
    params: dict[str, ParamExpr] = Field(default_factory=dict)


class SaxModelSpec(BaseModelSpec):
    language: Literal["sax"] = "sax"
    simulator: str | None = "sax"
    module: str
    qualname: str


class SpiceModelSpec(BaseModelSpec):
    language: Literal["spice", "spectre"]
    spice_type: str
    library: str
    sections: tuple[str, ...] = ()
    code: str | None = None


class GenericModelSpec(BaseModelSpec):
    model_config = ConfigDict(extra="allow")


type ModelSpec = Annotated[
    SaxModelSpec | SpiceModelSpec | GenericModelSpec,
    Field(union_mode="left_to_right"),
]

_model_adapter = TypeAdapter(ModelSpec)
_port_adapter = TypeAdapter(AnnotationPort)
_display_adapter = TypeAdapter(DisplaySpec)


class ModelList(RootModel[tuple[ModelSpec, ...]]):
    root: tuple[ModelSpec, ...] = ()

    def __iter__(self) -> Iterator[ModelSpec]:
        return iter(self.root)

    def __len__(self) -> int:
        return len(self.root)

    def __getitem__(self, idx: int) -> ModelSpec:
        return self.root[idx]

    def select(
        self,
        *,
        language: str | None = None,
        simulator: str | None = None,
        implementation: str | None = None,
        name: str | None = None,
    ) -> tuple[ModelSpec, ...]:
        return tuple(
            model
            for model in self.root
            if (language is None or model.language == language)
            and (simulator is None or model.simulator == simulator)
            and (implementation is None or model.implementation == implementation)
            and (name is None or model.name == name)
        )


class CellAnnotation(BaseModel):
    device_type: str | None = None
    ports: tuple[AnnotationPort, ...] = ()
    models: ModelList = Field(default_factory=ModelList)
    tags: tuple[str, ...] = ()
    display: DisplaySpec | None = None
    metadata: dict[str, JSONSerializable] = Field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class _ModelSelector:
    language: str | None = None
    simulator: str | None = None
    implementation: str | None = None
    name: str | None = None

    def matches(self, model: ModelSpec) -> bool:
        return (
            (self.language is None or model.language == self.language)
            and (self.simulator is None or model.simulator == self.simulator)
            and (
                self.implementation is None
                or model.implementation == self.implementation
            )
            and (self.name is None or model.name == self.name)
        )


@dataclass(frozen=True, slots=True)
class _ModelPatch:
    append: tuple[ModelSpec, ...] = ()
    prepend: tuple[ModelSpec, ...] = ()
    replace: tuple[ModelSpec, ...] | None = None
    remove: tuple[_ModelSelector, ...] = ()


@dataclass(frozen=True, slots=True)
class _CellAnnotationPatch:
    device_type: str | None = None
    ports: tuple[AnnotationPort, ...] | None = None
    models: _ModelPatch = _ModelPatch()
    tags: tuple[str, ...] = ()
    display: DisplaySpec | None = None
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
                models=(
                    _ModelPatch(prepend=models)
                    if record.position == "prepend"
                    else _ModelPatch(append=models)
                )
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
                display=(
                    None if result is None else _display_adapter.validate_python(result)
                )
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
    models: tuple[ModelSpec, ...] = ()
    tags: tuple[str, ...] = ()
    display: DisplaySpec | None = None
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

        if patch.models.replace is not None:
            models = patch.models.replace
        if patch.models.remove:
            models = tuple(
                model
                for model in models
                if not any(selector.matches(model) for selector in patch.models.remove)
            )
        if patch.models.prepend:
            models = (*patch.models.prepend, *models)
        if patch.models.append:
            models = (*models, *patch.models.append)
        models = _dedupe_models(models)

        if patch.tags:
            tags = _merge_tags(tags, patch.tags)

        if patch.display is not None:
            if display is not None and display != patch.display and not record.replace:
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
        models=ModelList(models),
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
            models=_ModelPatch(append=tuple(result.models)),
            tags=result.tags,
            display=result.display,
            metadata=result.metadata,
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
        models=_ModelPatch(append=_coerce_models(result.get("models", ()))),
        tags=_coerce_tags(result.get("tags", ())),
        display=(
            None
            if result.get("display") is None
            else _display_adapter.validate_python(result.get("display"))
        ),
        metadata=(
            None
            if result.get("metadata") is None
            else {str(k): v for k, v in dict(result.get("metadata", {})).items()}
        ),
    )


def _coerce_ports(value: Any) -> tuple[AnnotationPort, ...]:
    if value is None:
        return ()
    if isinstance(value, AnnotationPort):
        return (value,)
    return tuple(_port_adapter.validate_python(port) for port in value)


def _coerce_models(value: Any) -> tuple[ModelSpec, ...]:
    if value is None:
        return ()
    if isinstance(value, BaseModelSpec):
        return (_model_adapter.validate_python(value),)
    if isinstance(value, ModelList):
        return tuple(value)
    if isinstance(value, Sequence) and not isinstance(value, str | bytes):
        return tuple(_model_adapter.validate_python(model) for model in value)
    return (_model_adapter.validate_python(value),)


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


def _model_key(model: ModelSpec) -> tuple[str, str | None, str | None, str]:
    return (model.language, model.simulator, model.implementation, model.name)


def _dedupe_models(models: tuple[ModelSpec, ...]) -> tuple[ModelSpec, ...]:
    seen: set[tuple[str, str | None, str | None, str]] = set()
    deduped: list[ModelSpec] = []
    for model in models:
        key = _model_key(model)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(model)
    return tuple(deduped)
