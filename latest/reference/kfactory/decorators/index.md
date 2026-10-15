# decorators

Defines additional decorators than just `@cell`.

## Decorators

Various decorators intended to be attached to a KCLayout.

### \_\_init\_\_

```
__init__(kcl: KCLayout) -> None
```

Just set the standard `@cell` decorator.

### module\_cell

```
module_cell(_func: Callable[KCellParams, KC]) -> Callable[KCellParams, KC]
```

```
module_cell(**kwargs: Unpack[ModuleCellKWargs]) -> Callable[[Callable[KCellParams, KC]], Callable[KCellParams, KC]]
```

```
module_cell(_func: Callable[KCellParams, KC] | None = None, /, **kwargs: Unpack[ModuleCellKWargs]) -> Callable[KCellParams, KC] | Callable[[Callable[KCellParams, KC]], Callable[KCellParams, KC]]
```

Constructs the `@module_cell` decorator on KCLayout.decorators.

## KCellDecorator

Bases: `Protocol`

Signature of the `@cell` decorator.

### \_\_call\_\_

```
__call__(**kwargs: Unpack[KCellDecoratorKWargs]) -> Callable[[Callable[KCellParams, K]], Callable[KCellParams, K]]
```

**call** implementation.

## KCellDecoratorKWargs

Bases: `TypedDict`

KWargs for `@cell`.

## ModuleCellKWargs

Bases: `TypedDict`

KWargs for `@module_cell`.

## ModuleDecorator

Bases: `Protocol`

Signature of the `@module_cell` decorator.

### \_\_call\_\_

```
__call__(**kwargs: Unpack[ModuleCellKWargs]) -> Callable[[Callable[KCellParams, K]], Callable[KCellParams, K]]
```

**call** implementation.

## WrappedKCellFunc

### get\_metadata

```
get_metadata(*args: KCellParams.args, **kwargs: KCellParams.kwargs) -> FactoryMetadata
```

Resolve all metadata providers into a single `FactoryMetadata`.

Accepts the same parameters as the cell factory itself.

### has\_metadata

```
has_metadata() -> bool
```

Whether any metadata providers are registered for this factory.

### metadata\_providers

```
metadata_providers() -> tuple[_FactoryMetadataProviderRecord, ...]
```

Return all metadata provider records registered for this factory.

## WrappedVKCellFunc

### get\_metadata

```
get_metadata(*args: VKCellParams.args, **kwargs: VKCellParams.kwargs) -> FactoryMetadata
```

Resolve all metadata providers into a single `FactoryMetadata`.

Accepts the same parameters as the cell factory itself.

### has\_metadata

```
has_metadata() -> bool
```

Whether any metadata providers are registered for this factory.

### metadata\_providers

```
metadata_providers() -> tuple[_FactoryMetadataProviderRecord, ...]
```

Return all metadata provider records registered for this factory.
