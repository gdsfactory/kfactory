# factory\_metadata

Factory metadata provider system.

Provides a provider-based system for attaching structured metadata (device type, ports, models, tags, display hints) to cell factories without coupling to schematic-driven layout.

## FactoryMetadata

Bases: `BaseModel`

Resolved metadata for a cell factory.

Aggregated from all registered providers for a given factory. Fields are intentionally loosely typed so consumers (gfp, PDKs, simulation packages) can define their own schemas on top.

Fields:

- `device_type` (`str | None`)
- `ports` (`tuple[PortSpec, ...]`)
- `models` (`list`)
- `tags` (`tuple[str, ...]`)
- `display` (`dict`)
- `info` (`dict[str, JSONSerializable]`)

## FactoryMetadataRegistry

Stores metadata provider registrations and resolves them per factory.

### add

```
add(*, target_kind: Literal['name', 'fqn', 'object'], target_key: str | int, kind: FactoryMetadataProviderKind, provider: Callable[..., Any], replace: bool = False, position: Literal['append', 'prepend'] = 'append') -> Callable[..., Any]
```

Register a metadata provider for a target factory.

### providers\_for

```
providers_for(*, name: str, qualified_name: str, obj: object) -> tuple[_FactoryMetadataProviderRecord, ...]
```

Return all provider records matching a factory by name, FQN, or identity.

## PortSpec

Bases: `TypedDict`

Structured port descriptor for cell metadata.

Declares a logical port with its kind, physical side, and optional cross-section or aliasing information. Used by external tools (simulation runners, schematic editors) to understand a cell's interface without instantiating it.

## call\_provider

```
call_provider(provider: Callable[..., Any], params: dict[str, Any]) -> Any
```

Invoke a provider with the subset of cell params its signature accepts.

## provider\_result\_to\_patch

```
provider_result_to_patch(record: _FactoryMetadataProviderRecord, result: Any) -> _FactoryMetadataPatch
```

Convert a provider's return value into a metadata patch.

## resolve\_metadata

```
resolve_metadata(providers: Iterable[_FactoryMetadataProviderRecord], params: dict[str, Any]) -> FactoryMetadata
```

Resolve all providers for a factory into a single FactoryMetadata.
