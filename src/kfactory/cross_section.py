from typing import Any, Callable, Dict, List, Optional, Tuple, Union

import pydantic
from pydantic import BaseModel, Field

from kfactory import KCell, kdb

Layer = Tuple[int, int]
LayerSpec = Union[int, Layer, str, None]
LayerSpecs = Optional[Tuple[LayerSpec, ...]]
Floats = Tuple[float, ...]


def get_padding_points(
    kcell: KCell,
    default: float = 50.0,
    top: Optional[float] = None,
    bottom: Optional[float] = None,
    right: Optional[float] = None,
    left: Optional[float] = None,
) -> kdb.DBox:
    """Returns padding points for a kcell outline.

    Args:
        kcell: to add padding.
        default: default padding in um.
        top: north padding in um.
        bottom: south padding in um.
        right: east padding in um.
        left: west padding in um.
    """
    c = kcell
    top = top if top is not None else default
    bottom = bottom if bottom is not None else default
    right = right if right is not None else default
    left = left if left is not None else default
    bbox = c.dbbox()
    return kdb.DBox(
        bbox.p1 + kdb.DVector(-left, -bottom), bbox.p2 + kdb.DVector(right, top)
    )


class Section(BaseModel):
    """CrossSection to extrude a path with a waveguide.

    Parameters:
        width: of the section (um) or parameterized function from 0 to 1.
             the width at t==0 is the width at the beginning of the Path.
             the width at t==1 is the width at the end.
        offset: center offset (um) or function parameterized function from 0 to 1.
             the offset at t==0 is the offset at the beginning of the Path.
             the offset at t==1 is the offset at the end.
        layer: layer spec.
        port_names: Optional port names.
        port_types: optical, electrical, ...
        name: Optional Section name.
        hidden: hide layer.

    .. code::
          0   offset
          |<-------------->|
          |              _____
          |             |     |
          |             |layer|
          |             |_____|
          |              <---->
                         width
    """

    width: Union[float, Callable[..., float]]
    offset: Union[float, Callable[..., float]] = 0
    layer: Union[LayerSpec, Tuple[LayerSpec, LayerSpec]]
    port_names: Tuple[Optional[str], Optional[str]] = (None, None)
    port_types: Tuple[str, str] = ("optical", "optical")
    name: Optional[str] = None
    hidden: bool = False

    class Config:
        """pydantic basemodel config."""

        extra = "forbid"


MaterialSpec = Union[str, float, complex, Tuple[float, float]]


class CrossSection(BaseModel):
    """Waveguide information to extrude a path.

    cladding_layers follow path shape, while bbox_layers are rectangular.

    Parameters:
        layer: main Section layer. Main section name = '_default'.
        width: main Section width (um) or function parameterized from 0 to 1.
            the width at t==0 is the width at the beginning of the Path.
            the width at t==1 is the width at the end.
        offset: main Section center offset (um) or function from 0 to 1.
             the offset at t==0 is the offset at the beginning of the Path.
             the offset at t==1 is the offset at the end.
        radius: main Section bend radius (um).
        width_wide: wide waveguides width (um) for low loss routing.
        auto_widen: taper to wide waveguides for low loss routing.
        auto_widen_minimum_length: minimum straight length for auto_widen.
        taper_length: taper_length for auto_widen.
        bbox_layers: list of layers for rectangular bounding box.
        bbox_offsets: list of bounding box offsets.
        cladding_layers: list of layers to extrude.
        cladding_offsets: list of offset from main Section edge.
        sections: list of Sections(width, offset, layer, ports).
        port_names: for input and output ('o1', 'o2').
        port_types: for input and output: electrical, optical, vertical_te ...
        min_length: defaults to 1nm = 10e-3um for routing.
        start_straight_length: straight length at the beginning of the route.
        end_straight_length: end length at the beginning of the route.
        snap_to_grid: Optional snap points to grid when extruding paths (um).
        aliases: dict of cross_section aliases.
        decorator: function when extruding component. For example add_pins.
        info: dict with extra settings or useful information.
        name: cross_section name.
        add_center_section: whether a section with `width` and `layer`
              is added during extrude.
    """

    layer: LayerSpec
    width: Union[float, Callable[..., float]]
    offset: Union[float, Callable[..., float]] = 0
    radius: Optional[float] = None
    width_wide: Optional[float] = None
    auto_widen: bool = False
    auto_widen_minimum_length: float = 200.0
    taper_length: float = 10.0
    bbox_layers: List[LayerSpec] = Field(default_factory=list)
    bbox_offsets: List[float] = Field(default_factory=list)
    cladding_layers: Optional[LayerSpecs] = None
    cladding_offsets: Optional[Floats] = None
    sections: List[Section] = Field(default_factory=list)
    port_names: Tuple[str, str] = ("o1", "o2")
    port_types: Tuple[str, str] = ("optical", "optical")
    min_length: float = 10e-3
    start_straight_length: float = 10e-3
    end_straight_length: float = 10e-3
    snap_to_grid: Optional[float] = None
    decorator: Optional[Callable] = None
    add_pins: Optional[Callable] = None
    add_bbox: Optional[Callable] = None
    info: Dict[str, Any] = Field(default_factory=dict)
    name: Optional[str] = None
    add_center_section: bool = True

    class Config:
        """Configuration."""

        extra = "forbid"
        fields = {
            "decorator": {"exclude": True},
            "add_pins": {"exclude": True},
            "add_bbox": {"exclude": True},
        }

    def copy(self, width: Optional[float] = None) -> "CrossSection":
        xs = super().copy()
        xs.decorator = self.decorator
        xs.add_pins = self.add_pins
        xs.add_bbox = self.add_bbox

        if width:
            xs.width = width
        return xs

    @property
    def aliases(self) -> Dict[str, Section]:
        s = dict(
            _default=Section(
                width=self.width,
                offset=self.offset,
                layer=self.layer,
                port_names=self.port_names,
                port_types=self.port_types,
                name="_default",
            )
        )
        sections = self.sections or []
        for section in sections:
            if section.name:
                s[section.name] = section
        return s

    def add_bbox_layers(
        self,
        component: KCell,
        top: Optional[float] = None,
        bottom: Optional[float] = None,
        right: Optional[float] = None,
        left: Optional[float] = None,
    ) -> KCell:
        """Add bounding box layers to a component.

        Args:
            component: to add layers.
            top: top padding.
            bottom: bottom padding.
            right: right padding.
            left: left padding.
        """
        # from gdsfactory.add_padding import get_padding_points

        c = component
        x = self
        if x.bbox_layers and x.bbox_offsets:
            padding = []
            for offset in x.bbox_offsets:
                box = get_padding_points(
                    kcell=c,
                    default=0,
                    top=top or offset,
                    bottom=bottom or offset,
                    left=left or offset,
                    right=right or offset,
                )
                padding.append(box)

            for layer, points in zip(x.bbox_layers, padding):
                c.shapes(layer).insert(box)
        return c


@pydantic.validate_arguments
def cross_section(
    width: Union[Callable[..., float], float] = 0.5,
    offset: Union[float, Callable[..., float]] = 0,
    layer: LayerSpec = "WG",
    width_wide: Optional[float] = None,
    auto_widen: bool = False,
    auto_widen_minimum_length: float = 200.0,
    taper_length: float = 10.0,
    radius: Optional[float] = 10.0,
    sections: Optional[Tuple[Section, ...]] = None,
    port_names: Tuple[str, str] = ("o1", "o2"),
    port_types: Tuple[str, str] = ("optical", "optical"),
    min_length: float = 10e-3,
    start_straight_length: float = 10e-3,
    end_straight_length: float = 10e-3,
    snap_to_grid: Optional[float] = None,
    bbox_layers: Optional[List[LayerSpec]] = None,
    bbox_offsets: Optional[List[float]] = None,
    cladding_layers: Optional[LayerSpecs] = None,
    cladding_offsets: Optional[Floats] = None,
    info: Optional[Dict[str, Any]] = None,
    decorator: Optional[Callable] = None,
    add_pins: Optional[Callable] = None,
    add_bbox: Optional[Callable] = None,
    add_center_section: bool = True,
) -> CrossSection:
    """Return CrossSection.

    Args:
        width: main Section width (um) or function parameterized from 0 to 1.
            the width at t==0 is the width at the beginning of the Path.
            the width at t==1 is the width at the end.
        offset: main Section center offset (um) or function from 0 to 1.
             the offset at t==0 is the offset at the beginning of the Path.
             the offset at t==1 is the offset at the end.
        layer: main section layer.
        width_wide: wide waveguides width (um) for low loss routing.
        auto_widen: taper to wide waveguides for low loss routing.
        auto_widen_minimum_length: minimum straight length for auto_widen.
        taper_length: taper_length for auto_widen.
        radius: bend radius (um).
        sections: list of Sections(width, offset, layer, ports).
        port_names: for input and output ('o1', 'o2').
        port_types: for input and output: electrical, optical, vertical_te ...
        min_length: defaults to 1nm = 10e-3um for routing.
        start_straight_length: straight length at the beginning of the route.
        end_straight_length: end length at the beginning of the route.
        snap_to_grid: can snap points to grid when extruding the path.
        bbox_layers: list of layers for rectangular bounding box.
        bbox_offsets: list of bounding box offsets.
        cladding_layers: list of layers to extrude.
        cladding_offsets: list of offset from main Section edge.
        info: settings info.
        decorator: function to run when converting path to component.
        add_pins: optional function to add pins to component.
        add_bbox: optional function to add bounding box to component.
        add_center_section: whether a section with `width` and `layer`
              is added during extrude.

    .. plot::
        :include-source:

        import gdsfactory as gf

        xs = gf.cross_section.cross_section(width=0.5, offset=0, layer='WG')
        p = gf.path.arc(radius=10, angle=45)
        c = p.extrude(xs)
        c.plot()
    """
    return CrossSection(
        width=width,
        offset=offset,
        layer=layer,
        width_wide=width_wide,
        auto_widen=auto_widen,
        auto_widen_minimum_length=auto_widen_minimum_length,
        taper_length=taper_length,
        radius=radius,
        bbox_layers=bbox_layers or [],
        bbox_offsets=bbox_offsets or [],
        cladding_layers=cladding_layers,
        cladding_offsets=cladding_offsets,
        sections=sections or (),
        min_length=min_length,
        start_straight_length=start_straight_length,
        end_straight_length=end_straight_length,
        snap_to_grid=snap_to_grid,
        port_types=port_types,
        port_names=port_names,
        info=info or {},
        decorator=decorator,
        add_bbox=add_bbox,
        add_pins=add_pins,
        add_center_section=add_center_section,
    )


if __name__ == "__main__":
    cross_section()
