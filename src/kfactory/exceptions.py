from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .instance import ProtoInstance
    from .instance_group import ProtoInstanceGroup
    from .kcell import AnyKCell, BaseKCell
    from .layout import KCLayout
    from .port import ProtoPort

__all__ = [
    "AsymmetricCoreMismatchError",
    "AsymmetricMirrorRequiredError",
    "CellNameError",
    "CrossSectionMismatchError",
    "CrossSectionNamingConflictError",
    "CrossSectionSymmetryMismatchError",
    "DuplicateCellNameError",
    "ExtrudeConfigConflictError",
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


class ExtrudeConfigConflictError(ValueError):
    """Raised when a cross section already has a different extrude config.

    Extrude configs are keyed by the cross section's structural signature, so
    cross sections with the same geometry share one config.
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

    Two ports carrying an `AsymmetricalCrossSection` can only be connected via
    an M90 (mirror) transformation, since R180 would flip the left/right halves
    of the profile. Pass `mirror=True` to `connect`.
    """

    def __init__(
        self,
        p1: ProtoPort[Any],
        p2: ProtoPort[Any],
        *args: Any,
    ) -> None:
        super().__init__(
            f"Cannot connect ports {p1.name!r} and {p2.name!r} carrying"
            " asymmetric cross sections without `mirror=True`. Asymmetric profiles"
            " require an M90 transformation (mirror) — R180 would flip the"
            " left/right halves. Pass `mirror=True` to `connect`.",
            *args,
        )


class CrossSectionMismatchError(ValueError):
    """Raised when connecting asymmetric ports with different cross sections.

    The ports have the same width and main layer, but their cross sections
    differ. Pass `allow_cross_section_mismatch=True` to `connect` to only
    require matching core offsets.
    """

    def __init__(
        self,
        p1: ProtoPort[Any],
        p2: ProtoPort[Any],
        *args: Any,
    ) -> None:
        super().__init__(
            f"Cross section mismatch between the ports {p1.name!r}"
            f" ({p1.base.any_cross_section.name!r}) and {p2.name!r}"
            f" ({p2.base.any_cross_section.name!r}).",
            *args,
        )


class AsymmetricCoreMismatchError(ValueError):
    """Raised when the core offsets of two asymmetric ports differ.

    Raised with `allow_cross_section_mismatch`, which only requires the cores of
    asymmetric cross sections to match.
    """

    def __init__(
        self,
        p1: ProtoPort[Any],
        p2: ProtoPort[Any],
        *args: Any,
    ) -> None:
        xs1 = p1.base.asymmetric_cross_section
        xs2 = p2.base.asymmetric_cross_section
        assert xs1 is not None
        assert xs2 is not None
        super().__init__(
            f"Core offset mismatch between the asymmetric ports {p1.name!r}"
            f" ({xs1.section_min}, {xs1.section_max}) and {p2.name!r}"
            f" ({xs2.section_min}, {xs2.section_max}).",
            *args,
        )


class CrossSectionSymmetryMismatchError(ValueError):
    """Raised when connecting ports whose cross sections differ in symmetry.

    A symmetric and an asymmetric cross section with the same width and layer
    cannot be connected, since they are structurally different objects. Use
    `allow_cross_section_mismatch` to connect them anyway.
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


class DuplicateCellNameError(RuntimeError):
    """Raised when writing a layout with multiple cells sharing the same name.

    GDS/OASIS formats require unique cell names. This error provides details
    about which names are duplicated and which cells are involved.
    """


class InvalidLayerError(ValueError):
    """Raised when a layer is not valid."""
