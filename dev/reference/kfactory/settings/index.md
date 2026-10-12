# settings

## Info

Bases: `SettingMixin`, `BaseModel`

Info for a KCell.

`validate_assignment` is intentionally off: combined with a `model_validator(mode="before")` it would re-run validation against the entire extras dict on every per-field write, which historically silently coerced previously-stored values via `clean_value()` (see \#944). Per-write validation is handled in `__setattr__` and only inspects the new value.

Validators:

- `restrict_types`

### \_\_add\_\_

```
__add__(other: Info) -> Self
```

Update the settings.

### \_\_iadd\_\_

```
__iadd__(other: Info) -> Self
```

Update the settings.

### \_\_init\_\_

```
__init__(**kwargs: Any) -> None
```

Initialize the settings.

### \_\_setattr\_\_

```
__setattr__(name: str, value: Any) -> None
```

Validate the assigned value, then store it.

### \_\_setitem\_\_

```
__setitem__(key: str, value: MetaData) -> None
```

Set the value of a setting.

### restrict\_types

```
restrict_types(data: dict[str, MetaData]) -> dict[str, MetaData]
```

Restrict the types of the settings (runs at construction only).

### update

```
update(data: dict[str, MetaData]) -> None
```

Update the settings.

## KCellSettings

Bases: `SettingMixin`, `BaseModel`

Settings for a BaseKCell.

Validators:

- `restrict_types`

### \_\_init\_\_

```
__init__(**kwargs: Any) -> None
```

Initialize the settings.

### restrict\_types

```
restrict_types(data: dict[str, Any]) -> dict[str, MetaData]
```

Restrict the types of the settings.

## KCellSettingsUnits

Bases: `SettingMixin`, `BaseModel`

Settings for the units of a KCell.

Validators:

- `restrict_types`

### \_\_init\_\_

```
__init__(**kwargs: Any) -> None
```

Initialize the settings.

### restrict\_types

```
restrict_types(data: dict[str, str]) -> dict[str, str]
```

Restrict the types of the settings.

## SettingMixin

Mixin class for shared settings functionality.

### \_\_contains\_\_

```
__contains__(__key: str) -> bool
```

Check if a setting exists.

### \_\_getattr\_\_

```
__getattr__(key: str) -> Any
```

Get the value of a setting.

### \_\_getitem\_\_

```
__getitem__(key: str) -> Any
```

Get the value of a setting.

### \_\_str\_\_

```
__str__() -> str
```

Return the representation of the settings.

### get

```
get(__key: str, /, default: Any = None) -> Any
```

Get the value of a setting.
