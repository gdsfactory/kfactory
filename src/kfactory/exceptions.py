from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .instance import ProtoInstance
    from .instance_group import ProtoInstanceGroup
    from .kcell import AnyKCell, BaseKCell
    from .layout import KCLayout
    from .port import ProtoPort

__all__ = [
    "AsymmetricMirrorRequiredError",
    "CellNameError",
    "CrossSectionNamingConflictError",
    "CrossSectionSymmetryMismatchError",
    "FactoriesLockedError",
    "InvalidLayerError",
    "LockedError",
    "MergeError",
    "PortLayerMismatchError",
    "PortTypeMismatchError",
    "PortWidthMismatchError",
]


class LockedError(AttributeError):
    """Raised when a locked cell is being modified."""

    def __init__(self, kcell: AnyKCell | BaseKCell) -> None:
        """Throw _locked error."""
        super().__init__(
            f"{kcell.name!r} is locked and likely stored in cache. Modifications are "
            "disabled as its associated function is decorated with `cell`. To modify, "
            "update the code in the function or create a copy of "
            f"the {kcell.__class__.__name__}."
        )


class FactoriesLockedError(RuntimeError):
    """Raised when trying to add a factory to a locked Factories collection."""


class MergeError(ValueError):
    """Raised if two layout's have conflicting cell definitions."""


class CrossSectionNamingConflictError(ValueError):
    """Raised when a second name is registered for an existing structural signature.

    Cross sections and enclosures are canonicalized by their name-independent
    structural signature. A given signature may have at most one *named* canonical
    entry; attempting to register a second, differently-named entry for the same
    signature (or to reuse a name for a different signature) raises this error.
    """


class PortWidthMismatchError(ValueError):
    """Error thrown when two ports don't have a matching `width`."""

    def __init__(
        self,
        inst: ProtoInstance[Any] | ProtoInstanceGroup[Any, Any],
        other_inst: ProtoInstance[Any] | ProtoInstanceGroup[Any, Any] | ProtoPort[Any],
        p1: ProtoPort[Any],
        p2: ProtoPort[Any],
        *args: Any,
    ) -> None:
        """Throw error for the two ports `p1`/`p1`."""
        from .instance import ProtoInstance

        if isinstance(other_inst, ProtoInstance):
            super().__init__(
                f'Width mismatch between the ports {inst.name}["{p1.name}"] '
                f'and {other_inst.name}["{p2.name}"]'
                f'("{p1.width}"/"{p2.width}")',
                *args,
            )
        else:
            super().__init__(
                f'Width mismatch between the ports {inst.name}["{p1.name}"] '
                f'and Port "{p2.name}" ("{p1.width}"/"{p2.width}")',
                *args,
            )


class PortLayerMismatchError(ValueError):
    """Error thrown when two ports don't have a matching `layer`."""

    def __init__(
        self,
        kcl: KCLayout,
        inst: ProtoInstance[Any] | ProtoInstanceGroup[Any, Any],
        other_inst: ProtoInstance[Any] | ProtoInstanceGroup[Any, Any] | ProtoPort[Any],
        p1: ProtoPort[Any],
        p2: ProtoPort[Any],
        *args: Any,
    ) -> None:
        """Throw error for the two ports `p1`/`p1`."""
        from .instance import ProtoInstance
        from .layer import LayerEnum

        l1 = (
            f"{p1.layer.name}({p1.layer.__int__()})"
            if isinstance(p1.layer, LayerEnum)
            else str(kcl.layout.get_info(p1.layer))
        )
        l2 = (
            f"{p2.layer.name}({p2.layer.__int__()})"
            if isinstance(p2.layer, LayerEnum)
            else str(kcl.layout.get_info(p2.layer))
        )
        if isinstance(other_inst, ProtoInstance):
            super().__init__(
                f'Layer mismatch between the ports {inst.name}["{p1.name}"]'
                f' and {other_inst.name}["{p2.name}"] ("{l1}"/"{l2}")',
                *args,
            )
        else:
            super().__init__(
                f'Layer mismatch between the ports {inst.name}["{p1.name}"]'
                f' and Port "{p2.name}" ("{l1}"/"{l2}")',
                *args,
            )


class PortTypeMismatchError(ValueError):
    """Error thrown when two ports don't have a matching `port_type`."""

    def __init__(
        self,
        inst: ProtoInstance[Any] | ProtoInstanceGroup[Any, Any],
        other_inst: ProtoInstance[Any] | ProtoInstanceGroup[Any, Any] | ProtoPort[Any],
        p1: ProtoPort[Any],
        p2: ProtoPort[Any],
        *args: Any,
    ) -> None:
        """Throw error for the two ports `p1`/`p1`."""
        from .instance import ProtoInstance

        if isinstance(other_inst, ProtoInstance):
            super().__init__(
                f'Type mismatch between the ports {inst.name}["{p1.name}"]'
                f' and {other_inst.name}["{p2.name}"]'
                f" ({p1.port_type}/{p2.port_type})",
                *args,
            )
        else:
            super().__init__(
                f'Type mismatch between the ports {inst.name}["{p1.name}"]'
                f' and Port "{p2.name}" ({p1.port_type}/{p2.port_type})',
                *args,
            )


class AsymmetricMirrorRequiredError(ValueError):
    """Raised when connecting two asymmetric ports without `mirror=True`.

    Two ports carrying the same `AsymmetricalCrossSection` can only be
    connected via an M90 (mirror) transformation, since R180 would flip the
    left/right halves of the profile. Pass `mirror=True` to `connect`.
    """

    def __init__(
        self,
        p1: ProtoPort[Any],
        p2: ProtoPort[Any],
        *args: Any,
    ) -> None:
        super().__init__(
            f"Cannot connect ports {p1.name!r} and {p2.name!r} carrying the same"
            " asymmetric cross section without `mirror=True`. Asymmetric profiles"
            " require an M90 transformation (mirror) — R180 would flip the"
            " left/right halves. Pass `mirror=True` to `connect`.",
            *args,
        )


class CrossSectionSymmetryMismatchError(ValueError):
    """Raised when connecting ports whose cross sections differ in symmetry.

    A symmetric and an asymmetric cross section cannot be connected even with
    `allow_width_mismatch`, since they are structurally different objects.
    """

    def __init__(
        self,
        p1: ProtoPort[Any],
        p2: ProtoPort[Any],
        *args: Any,
    ) -> None:
        kind1 = "symmetric" if p1.base.is_symmetric() else "asymmetric"
        kind2 = "symmetric" if p2.base.is_symmetric() else "asymmetric"
        super().__init__(
            f"Cross section symmetry mismatch between ports {p1.name!r} ({kind1})"
            f" and {p2.name!r} ({kind2}). Symmetric and asymmetric cross sections"
            " cannot be connected.",
            *args,
        )


class CellNameError(ValueError):
    """Raised if a KCell is created and the automatic assigned name is taken."""


class InvalidLayerError(ValueError):
    """Raised when a layer is not valid."""
