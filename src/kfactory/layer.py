from __future__ import annotations

from typing import TYPE_CHECKING, Any, Self

import klayout.db as kdb
from aenum import Enum, constant  # type: ignore[import-untyped,unused-ignore]
from pydantic import BaseModel, ConfigDict, Field, model_validator

from .exceptions import InvalidLayerError
from .settings import Info

if TYPE_CHECKING:
    from collections.abc import Iterator

    from .layout import KCLayout


__all__ = [
    "LayerEnum",
    "LayerInfos",
    "LayerLevel",
    "LayerStack",
    "layerenum_from_dict",
]


class LayerInfos(BaseModel):
    """Class to store and serialize LayerInfos used in KCLayout.

    Args:
        kwargs: kdb.LayerInfo . if any extra field is not a kdb.LayerInfo,
            the validator will raise a ValidationError.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="allow")

    def __init__(self, **kwargs: Any) -> None:
        """Initialize the LayerInfos class.

        Args:
            kwargs: kdb.LayerInfo . if any extra field is not a kdb.LayerInfo,
                the validator will raise a ValidationError.
        """
        super().__init__(**kwargs)

    @model_validator(mode="after")
    def _validate_layers(self) -> Self:
        field_names = set(self.__class__.model_fields.keys())
        if self.model_extra is not None:
            field_names |= self.model_extra.keys()
        for field_name in field_names:
            f = getattr(self, field_name)
            if not isinstance(f, kdb.LayerInfo):
                raise InvalidLayerError(
                    "All fields in LayerInfos must be of type kdb.LayerInfo. "
                    f"Field {field_name} is of type {type(f)}"
                )
            if not f.name:
                f.name = field_name
            if f.layer == -1 or f.datatype == -1:
                raise InvalidLayerError(
                    "Layers must specify layer number and datatype."
                    f" {field_name} didn't specify them"
                )
        return self


class LayerEnum(int, Enum):  # type: ignore[misc]
    """Class for having the layers stored and a mapping int <-> layer,datatype.

    This Enum can also be treated as a tuple, i.e. it implements `__getitem__`
    and `__len__`.

    Attributes:
        layer: layer number
        datatype: layer datatype
    """

    layer: int
    datatype: int
    name: str
    layout: constant[kdb.Layout]

    def __init__(self, layer: int, datatype: int) -> None:
        """Just here to make sure klayout knows the layer name."""
        self.layout.set_info(self, kdb.LayerInfo(self.layer, self.datatype, self.name))

    def __new__(
        cls,
        layer: int,
        datatype: int,
    ) -> Self:
        """Create a new Enum.

        Because it needs to act like an integer an enum is created and expanded.

        Args:
            layer: Layer number of the layer.
            datatype: Datatype of the layer.
            kcl: Base Layout object to register the layer to.
        """
        value = cls.layout.layer(layer, datatype)
        obj: int = int.__new__(cls, value)
        obj._value_ = value  # type: ignore[attr-defined]
        obj.layer = layer  # type: ignore[attr-defined]
        obj.datatype = datatype  # type: ignore[attr-defined]
        return obj  # type: ignore[return-value]

    def __getitem__(self, key: int) -> int:
        """Retrieve layer number[0] / datatype[1] of a layer."""
        if key == 0:
            return self.layer
        if key == 1:
            return self.datatype

        raise ValueError(
            "LayerMap only has two values accessible like"
            " a list, layer == [0] and datatype == [1]"
        )

    def __len__(self) -> int:
        """A layer has length 2, layer number and datatype."""
        return 2

    def __iter__(self) -> Iterator[int]:
        """Allow for loops to iterate over the LayerEnum."""
        yield from [self.layer, self.datatype]

    def __str__(self) -> str:
        """Return the name of the LayerEnum."""
        return self.name


class LayerLevel(BaseModel):
    """Level for 3D LayerStack.

    Parameters:
        layer: (GDSII Layer number, GDSII datatype).
        thickness: layer thickness in um.
        thickness_tolerance: layer thickness tolerance in um.
        zmin: height position where material starts in um.
        material: material name.
        sidewall_angle: in degrees with respect to normal.
        z_to_bias: parametrizes shrinking/expansion of the design GDS layer
            when extruding from zmin (0) to zmin + thickness (1).
            Defaults no buffering [[0, 1], [0, 0]].
        info: simulation_info and other types of metadata.
            mesh_order: lower mesh order (1) will have priority over higher
                mesh order (2) in the regions where materials overlap.
            refractive_index: refractive_index
                can be int, complex or function that depends on wavelength (um).
            type: grow, etch, implant, or background.
            mode: octagon, taper, round.
                https://gdsfactory.github.io/klayout_pyxs/DocGrow.html
            into: etch into another layer.
                https://gdsfactory.github.io/klayout_pyxs/DocGrow.html
            doping_concentration: for implants.
            resistivity: for metals.
            bias: in um for the etch.
    """

    layer: tuple[int, int]
    thickness: float
    thickness_tolerance: float | None = None
    zmin: float
    material: str | None = None
    sidewall_angle: float = 0.0
    z_to_bias: tuple[int, ...] | None = None
    info: Info = Info()

    def __init__(
        self,
        layer: tuple[int, int] | kdb.LayerInfo,
        zmin: float,
        thickness: float,
        thickness_tolerance: float | None = None,
        material: str | None = None,
        sidewall_angle: float = 0.0,
        z_to_bias: tuple[int, ...] | None = None,
        info: Info | None = None,
    ) -> None:
        if isinstance(layer, kdb.LayerInfo):
            layer = (layer.layer, layer.datatype)
        super().__init__(
            layer=layer,
            zmin=zmin,
            thickness=thickness,
            thickness_tolerance=thickness_tolerance,
            material=material,
            sidewall_angle=sidewall_angle,
            z_to_bias=z_to_bias,
            info=info or Info(),
        )


class LayerStack(BaseModel):
    """For simulation and 3D rendering.

    Parameters:
        layers: dict of layer_levels.
    """

    layers: dict[str, LayerLevel] = Field(default_factory=dict)

    def __init__(self, **layers: LayerLevel) -> None:
        """Add LayerLevels automatically for subclassed LayerStacks."""
        super().__init__(layers=layers)

    def get_layer_to_thickness(self) -> dict[tuple[int, int], float]:
        """Returns layer tuple to thickness (um)."""
        return {
            level.layer: level.thickness
            for level in self.layers.values()
            if level.thickness
        }

    def get_layer_to_zmin(self) -> dict[tuple[int, int], float]:
        """Returns layer tuple to z min position (um)."""
        return {
            level.layer: level.zmin for level in self.layers.values() if level.thickness
        }

    def get_layer_to_material(self) -> dict[tuple[int, int], str]:
        """Returns layer tuple to material name."""
        return {
            level.layer: level.material
            for level in self.layers.values()
            if level.thickness and level.material
        }

    def get_layer_to_sidewall_angle(self) -> dict[tuple[int, int], float]:
        """Returns layer tuple to material name."""
        return {
            level.layer: level.sidewall_angle
            for level in self.layers.values()
            if level.thickness
        }

    def get_layer_to_info(self) -> dict[tuple[int, int], Info]:
        """Returns layer tuple to info dict."""
        return {level.layer: level.info for level in self.layers.values()}

    def to_dict(self) -> dict[str, dict[str, dict[str, Any]]]:
        return {
            level_name: level.model_dump() for level_name, level in self.layers.items()
        }

    def __getitem__(self, key: str) -> LayerLevel:
        """Access layer stack elements."""
        if key not in self.layers:
            layers = list(self.layers.keys())
            raise KeyError(f"{key!r} not in {layers}")

        return self.layers[key]

    def __getattr__(self, attr: str) -> Any:
        return self.layers[attr]


def layerenum_from_dict(
    layers: LayerInfos,
    name: str = "LAYER",
    layout: kdb.Layout | None = None,
) -> type[LayerEnum]:
    from .layout import get_default_kcl

    members: dict[str, constant[KCLayout] | tuple[int, int]] = {
        "layout": constant(layout or get_default_kcl().layout)
    }
    for li in layers.model_dump().values():
        members[li.name] = li.layer, li.datatype
    return LayerEnum(
        name,  # type: ignore[arg-type]
        members,  # type: ignore[arg-type]
    )
