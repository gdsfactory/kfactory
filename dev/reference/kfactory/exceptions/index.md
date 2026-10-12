# exceptions

## AsymmetricMirrorRequiredError

Bases: `ValueError`

Raised when connecting two asymmetric ports without `mirror=True`.

Two ports carrying the same `AsymmetricalCrossSection` can only be connected via an M90 (mirror) transformation, since R180 would flip the left/right halves of the profile. Pass `mirror=True` to `connect`.

## CellNameError

Bases: `ValueError`

Raised if a KCell is created and the automatic assigned name is taken.

## CrossSectionNamingConflictError

Bases: `ValueError`

Raised when a second name is registered for an existing structural signature.

Cross sections and enclosures are canonicalized by their name-independent structural signature. A given signature may have at most one *named* canonical entry; attempting to register a second, differently-named entry for the same signature (or to reuse a name for a different signature) raises this error.

## CrossSectionSymmetryMismatchError

Bases: `ValueError`

Raised when connecting ports whose cross sections differ in symmetry.

A symmetric and an asymmetric cross section cannot be connected even with `allow_width_mismatch`, since they are structurally different objects.

## DuplicateCellNameError

Bases: `RuntimeError`

Raised when writing a layout with multiple cells sharing the same name.

GDS/OASIS formats require unique cell names. This error provides details about which names are duplicated and which cells are involved.

## FactoriesLockedError

Bases: `RuntimeError`

Raised when trying to add a factory to a locked Factories collection.

## InvalidLayerError

Bases: `ValueError`

Raised when a layer is not valid.

## LockedError

Bases: `AttributeError`

Raised when a locked cell is being modified.

### \_\_init\_\_

```
__init__(kcell: AnyKCell | BaseKCell) -> None
```

Throw \_locked error.

## MergeError

Bases: `ValueError`

Raised if two layout's have conflicting cell definitions.

## PortLayerMismatchError

Bases: `ValueError`

Error thrown when two ports don't have a matching `layer`.

### \_\_init\_\_

```
__init__(kcl: KCLayout, inst: ProtoInstance[Any] | ProtoInstanceGroup[Any, Any], other_inst: ProtoInstance[Any] | ProtoInstanceGroup[Any, Any] | ProtoPort[Any], p1: ProtoPort[Any], p2: ProtoPort[Any], *args: Any) -> None
```

Throw error for the two ports `p1`/`p1`.

## PortTypeMismatchError

Bases: `ValueError`

Error thrown when two ports don't have a matching `port_type`.

### \_\_init\_\_

```
__init__(inst: ProtoInstance[Any] | ProtoInstanceGroup[Any, Any], other_inst: ProtoInstance[Any] | ProtoInstanceGroup[Any, Any] | ProtoPort[Any], p1: ProtoPort[Any], p2: ProtoPort[Any], *args: Any) -> None
```

Throw error for the two ports `p1`/`p1`.

## PortWidthMismatchError

Bases: `ValueError`

Error thrown when two ports don't have a matching `width`.

### \_\_init\_\_

```
__init__(inst: ProtoInstance[Any] | ProtoInstanceGroup[Any, Any], other_inst: ProtoInstance[Any] | ProtoInstanceGroup[Any, Any] | ProtoPort[Any], p1: ProtoPort[Any], p2: ProtoPort[Any], *args: Any) -> None
```

Throw error for the two ports `p1`/`p1`.
