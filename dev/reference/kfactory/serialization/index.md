# serialization

## DecoratorDict

Bases: `UserDict[Hashable, Any]`

Hashable decorator for a dictionary.

### \_\_hash\_\_

```
__hash__() -> int
```

Hash the dictionary.

## DecoratorList

Bases: `UserList[Any]`

Hashable decorator for a list.

### \_\_hash\_\_

```
__hash__() -> int
```

Hash the list.

## DecoratorTuple

Bases: `tuple[Any, ...]`

Tuple whose unhashable elements were converted by `to_hashable`.

## cell\_name\_hash

```
cell_name_hash(name: str) -> str
```

Return 8-char hash of a cell name.

## check\_metadata\_type

```
check_metadata_type(value: Any) -> MetaData
```

Recursively check an info value whether it can be stored.

## clean\_dict

```
clean_dict(d: dict[str, Any]) -> dict[str, Any]
```

Cleans dictionary recursively.

## clean\_name

```
clean_name(name: str) -> str
```

Ensures that gds cells are composed of \[a-zA-Z0-9\_-\].

**only a few characters are currently replaced.**

This function has been updated only on case-by-case basis

## clean\_value

```
clean_value(value: float | float64 | dict[Any, Any] | AnyKCell | Callable[..., Any]) -> str
```

Makes sure a value is representable in a limited character\_space.

## convert\_metadata\_type

```
convert_metadata_type(value: Any) -> MetaData
```

Recursively clean up a MetaData for KCellSettings.

## deserialize\_setting

```
deserialize_setting(setting: JSONSerializable) -> MetaData
```

Deserialize a setting.

## dict2name

```
dict2name(prefix: str | None = None, **kwargs: dict[str, Any]) -> str
```

Returns name from a dict.

## get\_cell\_name

```
get_cell_name(cell_type: str, max_cellname_length: int | None = None, **kwargs: dict[str, Any]) -> str
```

Convert a cell to a string.

## hashable\_to\_original

```
hashable_to_original(udl: DecoratorDict) -> dict[Hashable, Any]
```

```
hashable_to_original(udl: DecoratorList) -> list[Any]
```

```
hashable_to_original(udl: DecoratorTuple) -> tuple[Any, ...]
```

```
hashable_to_original(udl: Any) -> Any
```

```
hashable_to_original(udl: DecoratorDict | DecoratorList | DecoratorTuple | Any) -> dict[Hashable, Any] | list[Any] | tuple[Any, ...] | Any
```

Convert `DecoratorDict`/`DecoratorList`/`DecoratorTuple` back to originals.

## join\_first\_letters

```
join_first_letters(name: str) -> str
```

Join the first letter of a name separated with underscores.

Example::

```
"TL" == join_first_letters("taper_length")
```

## serialize\_setting

```
serialize_setting(setting: MetaData) -> JSONSerializable
```

Serialize a setting.

## to\_hashable

```
to_hashable(d: dict[Any, Any]) -> DecoratorDict
```

```
to_hashable(d: list[Any]) -> DecoratorList
```

```
to_hashable(d: tuple[Any, ...]) -> tuple[Any, ...]
```

```
to_hashable(d: dict[Any, Any] | list[Any] | tuple[Any, ...]) -> DecoratorDict | DecoratorList | tuple[Any, ...]
```

Convert a `dict`/`list` to a `DecoratorDict`/`DecoratorList`.

Tuples are returned as is if already hashable, otherwise as a `DecoratorTuple`.
