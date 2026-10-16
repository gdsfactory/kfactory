# exceptions

## AsymmetricCoreMismatchError

Bases: `ValueError`

Raised when the core offsets of two asymmetric ports differ.

Raised with `allow_cross_section_mismatch`, which only requires the cores of asymmetric cross sections to match.

## AsymmetricMirrorRequiredError

Bases: `ValueError`

Raised when connecting two asymmetric ports without `mirror=True`.

Two ports carrying an `AsymmetricalCrossSection` can only be connected via an M90 (mirror) transformation, since R180 would flip the left/right halves of the profile. Pass `mirror=True` to `connect`.

## CellNameError

Bases: `ValueError`

Raised if a KCell is created and the automatic assigned name is taken.

## CrossSectionMismatchError

Bases: `ValueError`

Raised when connecting asymmetric ports with different cross sections.

The ports have the same width and main layer, but their cross sections differ. Pass `allow_cross_section_mismatch=True` to `connect` to only require matching core offsets.

## CrossSectionNamingConflictError

Bases: `ValueError`

Raised when a second name is registered for an existing structural signature.

Cross sections and enclosures are canonicalized by their name-independent structural signature. A given signature may have at most one *named* canonical entry; attempting to register a second, differently-named entry for the same signature (or to reuse a name for a different signature) raises this error.

## CrossSectionSymmetryMismatchError

Bases: `ValueError`

Raised when connecting ports whose cross sections differ in symmetry.

A symmetric and an asymmetric cross section with the same width and layer cannot be connected, since they are structurally different objects. Use `allow_cross_section_mismatch` to connect them anyway.

## DuplicateCellNameError

Bases: `RuntimeError`

Raised when writing a layout with multiple cells sharing the same name.

GDS/OASIS formats require unique cell names. This error provides details about which names are duplicated and which cells are involved.

## ExtrudeConfigConflictError

Bases: `ValueError`

Raised when a cross section already has a different extrude config.

Extrude configs are keyed by the cross section's structural signature, so cross sections with the same geometry share one config.

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
