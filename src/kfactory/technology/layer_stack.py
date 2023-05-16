from collections import defaultdict
from collections.abc import Callable
from typing import Any, Literal, TypeAlias

from pydantic import BaseModel, Field

from .layer_views import LayerViews

MaterialSpec: TypeAlias = (
    str | float | tuple[float | float] | Callable[..., tuple[float, float]]
)


class LayerLevel(BaseModel):
    """Level for 3D LayerStack.

    Parameters:
        layer: (GDSII Layer number, GDSII datatype).
        thickness: layer thickness in um.
        thickness_tolerance: layer thickness tolerance in um.
        zmin: height position where material starts in um.
        zmin_tolerance: layer height tolerance in um.
        material: material name.
        sidewall_angle: in degrees with respect to normal.
        sidewall_angle_tolerance: in degrees.
        width_to_z: if sidewall_angle, relative z-position
            (0 --> zmin, 1 --> zmin + thickness).
        z_to_bias: parametrizes shrinking/expansion of the design GDS layer
            when extruding from zmin (0) to zmin + thickness (1).
            Defaults no buffering [[0, 1], [0, 0]].
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
        bias: in um for the etch. Can be a single number or 2 numbers (bias_x, bias_y)
        derived_layer: Optional derived layer, used for layer_type='etch' to define the
            slab.
        info: simulation_info and other types of metadata.
    """

    layer: tuple[int, int] = Field(...)
    thickness: float
    thickness_tolerance: float | None = None
    zmin: float
    zmin_tolerance: float | None = None
    material: str | None = None
    sidewall_angle: float = 0.0
    sidewall_angle_tolerance: float | None = None
    width_to_z: float = 0.0
    z_to_bias: tuple[list[float], list[float]] | None = None
    mesh_order: int = 3
    layer_type: Literal["grow", "etch", "implant", "background"] = "grow"
    mode: Literal["octagon", "taper", "round"] | None = None
    into: list[str] | None = None
    doping_concentration: float | None = None
    resistivity: float | None = None
    bias: tuple[float, float] | float | None = None
    derived_layer: tuple[int, int] | None = None
    info: dict[str, Any] = {}


class LayerStack(BaseModel):
    """For simulation and 3D rendering.

    Parameters:
        layers: dict of layer_levels.
    """

    layers: dict[str, LayerLevel] = Field(default_factory=dict)

    def __init__(self, **data: Any):
        """Add LayerLevels automatically for subclassed LayerStacks."""
        super().__init__(**data)

        for field in self.dict():
            val = getattr(self, field)
            if isinstance(val, LayerLevel):
                self.layers[field] = val

    def get_layer_to_thickness(self) -> dict[tuple[int, int], float]:
        """Returns layer tuple to thickness (um)."""
        layer_to_thickness = {}

        for level in self.layers.values():
            layer = level.layer

            if layer and level.thickness:
                layer_to_thickness[layer] = level.thickness
            elif hasattr(level, "operator"):
                layer_to_thickness[level.layer] = level.thickness

        return layer_to_thickness

    # def get_cell_with_derived_layers(self, cell: KCell) -> KCell:
    #     """Returns cell with derived layers."""
    #     unetched_layers = [
    #         layer_name
    #         for layer_name, level in self.layers.items()
    #         if level.layer and level.layer_type == "grow"
    #     ]
    #     etch_layers = [
    #         layer_name
    #         for layer_name, level in self.layers.items()
    #         if level.layer and level.layer_type == "etch"
    #     ]

    #     # remove all etched layers from the grown layers
    #     unetched_layers_dict = defaultdict(list)
    #     for layer_name in etch_layers:
    #         level = self.layers[layer_name]
    #         into = level.into or []
    #         for layer_name_etched in into:
    #             unetched_layers_dict[layer_name_etched].append(layer_name)
    #             if layer_name_etched in unetched_layers:
    #                 unetched_layers.remove(layer_name_etched)

    #     cell_layers = cell.get_layers()

    #     # Define pure grown layers
    #     unetched_layer_numbers = [
    #         self.layers[layer_name].layer
    #         for layer_name in unetched_layers
    #         if self.layers[layer_name].layer in cell_layers
    #     ]
    #     cell_derived = cell.extract(unetched_layer_numbers)

    #     # Define unetched layers
    #     polygons_to_remove = []
    #     for unetched_layer_name, unetched_layers in unetched_layers_dict.items():
    #         layer = self.layers[unetched_layer_name].layer
    #         polygons = cell.get_polygons(by_spec=layer)

    #         # Add all the etching layers (OR)
    #         for etching_layers in unetched_layers:
    #             layer = self.layers[etching_layers].layer
    #             B_polys = cell.get_polygons(by_spec=layer)
    #             polygons_to_remove = gdstk.boolean(
    #                 operand1=polygons_to_remove,
    #                 operand2=B_polys,
    #                 operation="or",
    #                 layer=layer[0],
    #                 datatype=layer[1],
    #             )

    #             derived_layer = self.layers[etching_layers].derived_layer
    #             if derived_layer:
    #                 slab_polygons = gdstk.boolean(
    #                     operand1=polygons,
    #                     operand2=B_polys,
    #                     operation="and",
    #                     layer=derived_layer[0],
    #                     datatype=derived_layer[1],
    #                 )
    #                 cell_derived.add(slab_polygons)

    #         # Remove all etching layers
    #         layer = self.layers[unetched_layer_name].layer
    #         polygons = cell.get_polygons(by_spec=layer)
    #         unetched_polys = gdstk.boolean(
    #             operand1=polygons,
    #             operand2=polygons_to_remove,
    #             operation="not",
    #             layer=layer[0],
    #             datatype=layer[1],
    #         )
    #         cell_derived.add(unetched_polys)

    #     cell_derived.add_ports(cell.ports)
    #     cell_derived.name = f"{cell.name}_derived_layers"
    #     return cell_derived

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

    def get_layer_to_info(
        self,
    ) -> dict[tuple[int, int], dict[str, dict[str, Any]]]:
        """Returns layer tuple to info dict."""
        return {level.layer: level.info for level in self.layers.values()}

    def to_dict(self) -> dict[str, dict[str, Any]]:
        """Get mapping of layer_name to LayerLevel."""
        return {level_name: dict(level) for level_name, level in self.layers.items()}

    def __getitem__(self, key: str) -> LayerLevel:
        """Access layer stack elements."""
        if key not in self.layers:
            layers = list(self.layers.keys())
            raise ValueError(f"{key!r} not in {layers}")

        return self.layers[key]

    def get_klayout_3d_script(
        self,
        layer_views: LayerViews | None = None,
        dbu: float | None = 0.001,
    ) -> str:
        """Returns script for 2.5D view in KLayout.

        You can include this information in your tech.lyt

        Args:
            layer_views: optional layer_views.
            dbu: Optional database unit. Defaults to 1nm.
        """
        unetched_layers = [
            layer_name
            for layer_name, level in self.layers.items()
            if level.layer and level.layer_type == "grow"
        ]
        etch_layers = [
            layer_name
            for layer_name, level in self.layers.items()
            if level.layer and level.layer_type == "etch"
        ]

        # remove all etched layers from the grown layers
        unetched_layers_dict = defaultdict(list)
        for layer_name in etch_layers:
            level = self.layers[layer_name]
            into = level.into or []
            for layer_name_etched in into:
                unetched_layers_dict[layer_name_etched].append(layer_name)
                if layer_name_etched in unetched_layers:
                    unetched_layers.remove(layer_name_etched)

        # define layers
        out = "\n".join(
            [
                f"{layer_name} = input({level.layer[0]}, {level.layer[1]})"
                for layer_name, level in self.layers.items()
                if level.layer
            ]
        )
        out += "\n"
        out += "\n"

        # define unetched layers
        for layer_name_etched, _etching_layers in unetched_layers_dict.items():
            etching_layers = " - ".join(_etching_layers)
            out += (
                f"unetched_{layer_name_etched} = {layer_name_etched} -"
                f" {etching_layers}\n"
            )

        out += "\n"

        # define slabs
        for layer_name, level in self.layers.items():
            if level.layer_type == "etch":
                into = level.into or []
                for i, layer1 in enumerate(into):
                    out += f"slab_{layer1}_{layer_name}_{i} = {layer1} &amp; {layer_name}\n"

        out += "\n"

        for layer_name, level in self.layers.items():
            layer = level.layer
            zmin = level.zmin
            zmax = zmin + level.thickness
            if dbu:
                rnd_pl = len(str(dbu).split(".")[-1])
                zmin = round(zmin, rnd_pl)
                zmax = round(zmax, rnd_pl)

            if layer is None:
                continue

            elif level.layer_type == "etch":
                name = f"{layer_name}: {level.material}"

                for i, layer1 in enumerate(into):
                    unetched_level = self.layers[layer1]
                    unetched_zmin = unetched_level.zmin
                    unetched_zmax = unetched_zmin + unetched_level.thickness

                    # slab
                    slab_layer_name = f"slab_{layer1}_{layer_name}_{i}"
                    slab_zmin = unetched_level.zmin
                    slab_zmax = unetched_zmax - level.thickness
                    name = f"{slab_layer_name}: {level.material} {layer[0]}/{layer[1]}"
                    txt = (
                        f"z("
                        f"{slab_layer_name}, "
                        f"zstart: {slab_zmin}, "
                        f"zstop: {slab_zmax}, "
                        f"name: '{name}'"
                    )
                    if layer_views:
                        txt += ", "
                        props = layer_views.get_from_tuple(layer)
                        if props.color.fill == props.color.frame:
                            txt += f"color: {props.color.fill}"
                        else:
                            txt += (
                                f"fill: {props.color.fill}, "
                                f"frame: {props.color.frame}"
                            )
                    txt += ")"
                    out += f"{txt}\n"

            elif layer_name in unetched_layers:
                name = f"{layer_name}: {level.material} {layer[0]}/{layer[1]}"

                txt = (
                    f"z("
                    f"{layer_name}, "
                    f"zstart: {zmin}, "
                    f"zstop: {zmax}, "
                    f"name: '{name}'"
                )
                if layer_views:
                    txt += ", "
                    props = layer_views.get_from_tuple(layer)
                    if props.color.fill == props.color.frame:
                        txt += f"color: {props.color.fill}"
                    else:
                        txt += (
                            f"fill: {props.color.fill}, " f"frame: {props.color.frame}"
                        )

                txt += ")"
                out += f"{txt}\n"

        out += "\n"

        for layer_name in unetched_layers_dict:
            unetched_level = self.layers[layer_name]
            layer = unetched_level.layer

            unetched_zmin = unetched_level.zmin
            unetched_zmax = unetched_zmin + unetched_level.thickness
            name = f"{slab_layer_name}: {unetched_level.material}"

            unetched_layer_name = f"unetched_{layer_name}"
            name = f"{unetched_layer_name}: {unetched_level.material} {layer[0]}/{layer[1]}"
            txt = (
                f"z("
                f"{unetched_layer_name}, "
                f"zstart: {unetched_zmin}, "
                f"zstop: {unetched_zmax}, "
                f"name: '{name}'"
            )
            if layer_views:
                txt += ", "
                props = layer_views.get_from_tuple(layer)
                if props.color.fill == props.color.frame:
                    txt += f"color: {props.color.fill}"
                else:
                    txt += f"fill: {props.color.fill}, " f"frame: {props.color.frame}"
            txt += ")"
            out += f"{txt}\n"

        return out

    def filtered(self, layers):
        return type(self)(layers={k: self.layers[k] for k in layers})
