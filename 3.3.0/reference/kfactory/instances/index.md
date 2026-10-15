# instances

## DInstances

Bases: `ProtoTInstances[float]`

Holder for instances.

Allows retrieval by name or index

### \_\_getitem\_\_

```
__getitem__(key: str | int) -> DInstance
```

Retrieve instance by index or by name.

### \_\_iter\_\_

```
__iter__() -> Iterator[DInstance]
```

Get instance iterator.

## Instances

Bases: `ProtoTInstances[int]`

Holder for instances.

Allows retrieval by name or index

### \_\_getitem\_\_

```
__getitem__(key: str | int) -> Instance
```

Retrieve instance by index or by name.

### \_\_iter\_\_

```
__iter__() -> Iterator[Instance]
```

Get instance iterator.

## ProtoTInstances

Bases: `ProtoInstances[T, ProtoTInstance[T]]`, `ABC`

### \_\_init\_\_

```
__init__(cell: TKCell) -> None
```

Constructor.

### \_\_len\_\_

```
__len__() -> int
```

Length of the instances.

### append

```
append(inst: ProtoTInstance[Any]) -> None
```

Append a new instance.

## VInstances

Bases: `ProtoInstances[float, VInstance]`

Holder for VInstances.

Allows retrieval by name or index

### \_\_delitem\_\_

```
__delitem__(item: VInstance | int) -> None
```

Delete an instance by index or instance.

### \_\_getitem\_\_

```
__getitem__(key: str | int) -> VInstance
```

Retrieve instance by index or by name.

### \_\_iter\_\_

```
__iter__() -> Iterator[VInstance]
```

Get instance iterator.

### \_\_len\_\_

```
__len__() -> int
```

Get the number of instances.

### append

```
append(inst: VInstance) -> None
```

Append a new instance.

### clear

```
clear() -> None
```

Clear all instances.

### copy

```
copy() -> VInstances
```

Copy the instances.

### dup

```
dup() -> VInstances
```

Copy the instances.

### remove

```
remove(inst: VInstance) -> None
```

Remove an instance.
