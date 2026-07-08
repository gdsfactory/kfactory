# Cell Annotation Implementation Plan

This plan targets the smallest kfactory surface area that can implement the new
annotation system from `schematics.md`.

The plan intentionally avoids preserving metadata-only `schematic_function`
behavior. `schematic_function` remains for real `TSchematic` behavior only.

## Goal

Add a first-class, provider-based metadata annotation system for kfactory cell
factories, with a small public authoring API:

```python
@kcl.annotate_for("mmi1x2")
def mmi1x2_annotation(...) -> dict:
    return {
        "device_type": "mmi-1x2",
        "ports": [
            kf.AnnotationPort(name="o1", kind="optical", side="left"),
            kf.AnnotationPort(name="o2", kind="optical", side="right"),
            kf.AnnotationPort(name="o3", kind="optical", side="right"),
        ],
    }


@kcl.model_for("mmi1x2", position="prepend")
def preferred_mmi_model(...) -> kf.SaxModelSpec:
    return kf.SaxModelSpec(
        name="fast_mmi1x2",
        simulator="sax",
        module="my_pdk.models",
        qualname="fast_mmi1x2",
        port_order=("o1", "o2", "o3"),
    )


@kcl.model_for("gdsfactory.components.mmis.mmi1x2.mmi1x2")
def external_mmi_model(...) -> kf.SaxModelSpec:
    ...
```

The resolved public object remains:

```python
factory.get_annotation(**settings) -> CellAnnotation
```

but patch objects are internal. Users should not have to construct or import
`CellAnnotationPatch` / `ModelPatch`.

## Public API Scope

For the first implementation, support only layout-level decorators:

```python
kcl.annotate_for(...)
kcl.model_for(...)
kcl.device_type_for(...)
kcl.ports_for(...)
kcl.tags_for(...)
kcl.display_for(...)
kcl.metadata_for(...)
```

Do not implement these yet:

```python
factory.annotate(...)
factory.models(...)
@kcl.cell(annotation=...)
@kcl.cell(annotation_function=...)
kcl.annotations.annotate_for(...)
kcl.annotations.models_for(...)
```

Those are useful later, but they increase the initial surface area.

## Target Resolution

Decorator targets should support both registered factory names and fully
qualified names. Registered names are the ergonomic default for PDK-local
annotations:

```python
@kcl.model_for("straight")
...
```

FQNs are required for overlays where short names are ambiguous or where the
annotation source is outside the package that owns the factory:

```python
@kcl.model_for("gdsfactory.components.mmis.mmi1x2.mmi1x2")
...
```

Resolution behavior for a string target:

1. If the target contains `"."`, treat it as an FQN and match
   `factory.qualified_name`.
2. Otherwise treat it as a registered short name and match:
   - `kcl.factories[target]`
   - `kcl.virtual_factories[target]`

The registry should store string targets as provided and also maintain an index
for exact FQN matches. `annotation_providers_for(factory)` should include both
short-name and FQN providers for the resolved wrapper.

The registered short name is enough for most PDK-local annotation and avoids
requiring FQNs in the common case. FQN support is nevertheless part of the first
implementation.

If both a real factory and virtual factory have the same registered name, raise
a clear ambiguity error unless the user passes an explicit wrapper object or an
FQN.

## Current Placement Points

kfactory currently has one wrapper instance per decorated factory:

- `WrappedKCellFunc` in `src/kfactory/decorators.py`
- `WrappedVKCellFunc` in `src/kfactory/decorators.py`

Those wrapper instances are stored in:

- `KCLayout.factories`
- `KCLayout.virtual_factories`

via the `Factories` collection in `src/kfactory/layout.py`.

The initial implementation should keep the current decorator return behavior:
`@cell` and `@vcell` return plain forwarding functions. Do not attach new
methods to the returned callable yet. Keep the registered wrapper as the source
of truth and add annotation resolution methods there.

## Minimal File Surface

### 1. Add `src/kfactory/annotations.py`

Define public resolved models plus internal provider/patch machinery in one new
module.

Public resolved model:

```python
class CellAnnotation(BaseModel):
    device_type: str | None = None
    ports: tuple[AnnotationPort, ...] = ()
    models: ModelList = Field(default_factory=ModelList)
    tags: tuple[str, ...] = ()
    display: DisplaySpec | None = None
    metadata: dict[str, JSONSerializable] = Field(default_factory=dict)
```

Public field models:

```python
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
```

Model specs:

```python
class BaseModelSpec(BaseModel):
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
    spice_type: Literal["SUBCKT", "MODEL"] | str
    library: str
    sections: tuple[str, ...] = ()
    code: str | None = None
```

Use a discriminated union where practical:

```python
ModelSpec = Annotated[
    SaxModelSpec | SpiceModelSpec | GenericModelSpec,
    Field(discriminator="language"),
]
```

Model selection:

```python
class ModelList(tuple[ModelSpec, ...]):
    def select(
        self,
        *,
        language: str | None = None,
        simulator: str | None = None,
        implementation: str | None = None,
        name: str | None = None,
    ) -> tuple[ModelSpec, ...]: ...
```

Internal only:

```python
class _CellAnnotationPatch(BaseModel): ...
class _ModelPatch(BaseModel): ...
class _ModelSelector(BaseModel): ...
class _AnnotationProviderRecord(BaseModel): ...
```

These are implementation details. Do not export them from `kfactory.__init__`.

Provider call utility:

```python
def call_provider(provider, params: dict[str, Any]) -> Any:
    ...
```

Provider functions may accept only a subset of factory parameters. If a provider
accepts `**kwargs`, pass all resolved params. Otherwise pass only matching
parameter names. Raise if a required provider parameter is unavailable.

Internal normalization:

```python
def provider_result_to_patch(record: _AnnotationProviderRecord, result: Any) -> _CellAnnotationPatch:
    ...
```

Examples:

- `kind="annotate"` provider result may be `CellAnnotation`, `dict`, or a mapping
  with keys like `device_type`, `ports`, `tags`, `display`, `metadata`.
- `kind="model"` provider result may be `ModelSpec` or `Sequence[ModelSpec]`.
- `kind="ports"` provider result is `Sequence[AnnotationPort | Mapping]`.
- `kind="device_type"` provider result is `str | None`.

Merge utility:

```python
def resolve_annotation(
    providers: Iterable[_AnnotationProviderRecord],
    params: dict[str, Any],
) -> CellAnnotation:
    ...
```

Merge rules:

- `device_type`: first non-`None` value wins; conflicting later value is an error
  unless provider record has `replace=True`.
- `ports`: replace as a group; conflicting replacement is an error unless
  `replace=True`.
- `models`: apply `remove`, then `prepend`, then `append`; `replace` can remain
  internal for future use.
- `tags`: deterministic set union.
- `display`: same conflict semantics as `device_type`.
- `metadata`: shallow namespaced merge; un-namespaced key conflicts are errors.

### 2. Modify `src/kfactory/decorators.py`

Add annotation resolution methods to both wrapper classes:

```python
class WrappedKCellFunc:
    def annotation_providers(self) -> tuple[_AnnotationProviderRecord, ...]: ...
    def has_annotation(self) -> bool: ...
    def get_annotation(self, *args, **kwargs) -> CellAnnotation: ...
```

Mirror the same methods on `WrappedVKCellFunc`.

Do not add public `factory.annotate` or `factory.models` methods in the first
implementation.

Store enough signature data on wrappers to resolve provider parameters:

```python
self.signature = sig
self._sig_params = sig_params
```

`get_annotation(*args, **kwargs)` should parse factory parameters the same way
cell creation does:

```python
params = _parse_params(
    self._sig_params.defaults,
    self._sig_params.names,
    self.kcl,
    args,
    kwargs,
)
```

Then resolve providers from the owning `KCLayout`:

```python
providers = self.kcl.annotation_providers_for(self)
return resolve_annotation(providers, params)
```

Add a `qualified_name` property for required FQN matching and gfp serialization:

```python
@property
def qualified_name(self) -> str:
    return f"{self._f_orig.__module__}.{self._f_orig.__qualname__}"
```

### 3. Modify `src/kfactory/layout.py`

Add a private annotation registry to `KCLayout`:

```python
_annotation_registry: AnnotationRegistry = PrivateAttr(default_factory=AnnotationRegistry)
```

Use a private attribute to keep the public API small. The public decorators live
directly on `KCLayout`.

Add public registration decorators:

```python
def annotate_for(self, target, provider=None, *, replace: bool = False): ...
def model_for(self, target, provider=None, *, position: Literal["append", "prepend"] = "append"): ...
def device_type_for(self, target, provider=None, *, replace: bool = False): ...
def ports_for(self, target, provider=None, *, replace: bool = False): ...
def tags_for(self, target, provider=None): ...
def display_for(self, target, provider=None, *, replace: bool = False): ...
def metadata_for(self, target, provider=None): ...
```

Each method should support decorator use:

```python
@kcl.ports_for("splitter")
def splitter_ports(noutputs: int = 2):
    return [...]
```

and direct registration:

```python
kcl.device_type_for("straight", lambda: "straight")
```

Add internal query:

```python
def annotation_providers_for(self, factory) -> tuple[_AnnotationProviderRecord, ...]:
    ...
```

`annotation_providers_for` should include providers registered by:

- registered short factory name,
- wrapper object identity,
- fully-qualified name.

Add public helper methods to `Factories`:

```python
def all(self) -> tuple[F, ...]:
    return tuple(self._all)


def annotated(self) -> tuple[F, ...]:
    return tuple(f for f in self._all if f.has_annotation())


def get_by_qualified_name(self, qualified_name: str) -> F | None:
    ...
```

The `all()` method gives gfp and tests a public replacement for private `_all`.
The FQN lookup gives external tools a stable alternative to matching short names
and source files.

Do not add `annotation=` or `annotation_function=` kwargs to `cell` / `vcell` in
the first implementation.

### 4. Modify `src/kfactory/__init__.py`

Export only public annotation models:

```python
from .annotations import (
    AnnotationPort,
    CellAnnotation,
    DisplaySpec,
    GenericModelSpec,
    ModelList,
    SaxModelSpec,
    SpiceModelSpec,
)
```

Add them to `__all__`.

Do not export internal patch/provider record classes.

### 5. Modify `src/kfactory/typings.py`

Add thin aliases/protocols only if needed by implementation:

- annotation provider callable,
- model provider callable,
- target spec type.

Do not try to type every decorator overload in the first implementation.

## gdsfactory Surface

No gdsfactory changes are required for the first implementation because the
public decorators live on `KCLayout`.

PDKs can write:

```python
gf.kcl.model_for("mmi1x2", position="prepend")(...)
```

or, inside their own active PDK object:

```python
PDK.kcl.model_for("mmi1x2", position="prepend")(...)
```

gdsfactory passthrough kwargs such as `annotation=` / `annotation_function=` are
deferred.

## Test Plan

Add `tests/test_cell_annotations.py`.

### Model tests

- `ModelList.select(simulator="sax")` returns only SAX models.
- `model_for(..., position="prepend")` prepends before appended/base models.
- duplicate models with the same stable key are de-duplicated deterministically.
- simulator-specific models can coexist for SAX, NgSpice, and Spectre.

### Layout decorator tests

- `@kcl.annotate_for("cell_name")` can provide device type and ports.
- `@kcl.device_type_for("cell_name")` can provide only a device type.
- `@kcl.ports_for("cell_name")` can provide only ports.
- `@kcl.model_for("cell_name")` can provide one model.
- `@kcl.model_for("cell_name")` can provide multiple models.
- `@kcl.model_for("cell_name", position="prepend")` prepends models.
- Provider functions may accept a subset of cell parameters.
- Provider functions with missing required parameters raise a clear error.

### Target resolution tests

- target string resolves against `kcl.factories`.
- target string resolves against `kcl.virtual_factories`.
- FQN target resolves against `factory.qualified_name`.
- short-name and FQN providers both apply to the same factory.
- ambiguous real/virtual target names raise.
- FQN can disambiguate an otherwise ambiguous real/virtual short name.
- unknown target raises a clear error.

### Parametric tests

- A cell with parameter-dependent port count returns different annotations for
  different settings.
- A model provider can map parameter-dependent model metadata.

### Factory registry tests

- `kcl.factories.all()` returns every registered wrapper, including name
  collisions.
- `kcl.factories.get_by_qualified_name(...)` resolves an exact FQN.
- `kcl.factories.annotated()` includes factories annotated through `kcl.*_for`.
- `kcl.virtual_factories.annotated()` works.

### Schematic separation tests

- `schematic_function` does not make `has_annotation()` true.
- `get_annotation()` does not call `schematic_function`.
- `get_schematic()` still works for real schematic functions.

## Migration Steps For PDKs

1. Replace helper functions returning `DSchematic(info=...)` with
   `kcl.annotate_for(...)`, `kcl.ports_for(...)`, and `kcl.device_type_for(...)`.
2. Move model metadata into `kcl.model_for(...)` providers.
3. Use registered factory names for local annotations and FQNs for external or
   ambiguous overlays.
4. Remove metadata-only `schematic_function=...`.
5. Update PDK tests to call `factory.get_annotation(...)`.

## Migration Steps For gfp

1. Replace `kfactory.kcl.factories._all` with `kcl.factories.all()`.
2. Replace `factory.get_schematic().info` metadata extraction with
   `factory.get_annotation().model_dump()`.
3. Replace `_f_schematic()` SAX lookup with
   `factory.get_annotation().models.select(simulator="sax")`.
4. Keep runtime fallback for unannotated factories as a separate path.

## Implementation Order

1. Add `annotations.py` public models and internal registry/merge logic.
2. Add `KCLayout` decorator methods:
   - `annotate_for`
   - `model_for`
   - `device_type_for`
   - `ports_for`
   - `tags_for`
   - `display_for`
   - `metadata_for`
3. Add `get_annotation`, `has_annotation`, and `annotation_providers` to
   `WrappedKCellFunc`.
4. Add the same read API to `WrappedVKCellFunc`.
5. Add `Factories.all()`, `Factories.annotated()`, and
   `Factories.get_by_qualified_name()`.
6. Export public annotation models.
7. Add tests.

## Deliberate Deferrals

- Do not expose `CellAnnotationPatch`, `ModelPatch`, or provider record classes.
- Do not implement `factory.annotate(...)` / `factory.models(...)`.
- Do not attach annotation methods to the returned callable from `@cell`.
- Do not add `annotation=` / `annotation_function=` kwargs to `cell` / `vcell`.
- Do not implement a public `kcl.annotations` registry object.
- Do not implement a nyanlib exporter in kfactory. Provide stable
  JSON/Pydantic serialization and let gfp map to nyanlib.
- Do not build a full safe expression AST for model parameter mappings yet.
  Keep `ParamExpr = str` with validation that referenced parameter names exist.
- Do not migrate old `DSchematic.info` metadata automatically. The new API
  should be used directly.

## Open Implementation Questions

- Should external overlays be allowed after `kcl.lock_factories()`?
- Should provider ordering support integer priorities, or is registration order
  plus `model_for(..., position="prepend")` enough?
- Should `annotate_for(...)` accept only mappings, or also `CellAnnotation`
  instances?
- Should `Factories.annotated()` include factories annotated only by FQN overlays
  without resolving every factory, or should it scan `Factories.all()` and match
  FQNs each time?
