from __future__ import annotations

import functools
import inspect
from collections import UserDict, defaultdict
from collections.abc import (
    Callable,
    Iterable,
    Sequence,
)
from pathlib import Path
from threading import RLock
from typing import Annotated, Any, Literal, cast, get_origin, overload

import cachetools.func
import klayout.db as kdb
import ruamel.yaml
from cachetools import Cache
from cachetools.keys import _HashedTuple  # type: ignore[attr-defined,unused-ignore]
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    model_validator,
)

from . import __version__
from .conf import CheckInstances, config, logger
from .cross_section import (
    CrossSection,
    CrossSectionModel,
    CrossSectionSpec,
    DCrossSection,
    DSymmetricalCrossSection,
    SymmetricalCrossSection,
)
from .decorators import Decorators
from .enclosure import (
    KCellEnclosure,
    LayerEnclosure,
    LayerEnclosureModel,
    LayerEnclosureSpec,
)
from .exceptions import CellNameError, MergeError
from .kcell import (
    AnyTKCell,
    DKCell,
    DKCells,
    KCell,
    KCells,
    ProtoTKCell,
    TKCell,
    TVCell,
    VKCell,
    show,
)
from .layer import LayerEnum, LayerInfos, LayerStack, layerenum_from_dict
from .merge import MergeDiff
from .port import rename_clockwise_multi
from .ports import DPorts, Ports
from .protocols import KCellFunc
from .serialization import (
    DecoratorDict,
    DecoratorList,
    _hashable_to_original,
    _to_hashable,
    get_cell_name,
)
from .settings import Info, KCellSettings, KCellSettingsUnits
from .typings import K, KCellParams, KCellSpec, MetaData, T
from .utilities import load_layout_options, save_layout_options

kcl: KCLayout
kcls: dict[str, KCLayout] = {}

__all__ = ["KCLayout", "cell", "get_default_kcl", "kcl", "kcls", "vcell"]


class Constants(BaseModel):
    """Constant Model class."""

    model_config = ConfigDict(arbitrary_types_allowed=True)


def get_default_kcl() -> KCLayout:
    """Utility function to get the default kcl object."""
    return kcl


class Factories(UserDict[str, Callable[..., T]]):
    tags: dict[str, list[Callable[..., T]]]

    def __init__(self, data: dict[str, Callable[..., T]]) -> None:
        super().__init__(data)
        self.tags = defaultdict(list)

    def __getattr__(self, name: str) -> Any:
        if name != "data":
            return self.data[name]
        else:
            self.__getattribute__(name)

    def for_tags(self, tags: list[str]) -> list[Callable[..., T]]:
        if len(tags) > 0:
            tag_set = set(self.tags[tags[0]])
            for tag in tags[1:]:
                tag_set &= set(self.tags[tag])
            return list(tag_set)
        raise NotImplementedError()


class KCLayout(
    BaseModel, arbitrary_types_allowed=True, extra="allow", validate_assignment=True
):
    """Small extension to the klayout.db.Layout.

    It adds tracking for the [KCell][kfactory.kcell.KCell] objects
    instead of only the `klayout.db.Cell` objects.
    Additionally it allows creation and registration through `create_cell`

    All attributes of `klayout.db.Layout` are transparently accessible

    Attributes:
        editable: Whether the layout should be opened in editable mode (default: True)
        rename_function: function that takes an iterable object of ports and renames
            them
    """

    """Store layers, enclosures, cell functions, simulation_settings ...

    only one Pdk can be active at a given time.

    Attributes:
        name: PDK name.
        enclosures: dict of enclosures factories.
        cells: dict of str mapping to KCells.
        cell_factories: dict of str mapping to cell factories.
        base_pdk: a pdk to copy from and extend.
        default_decorator: decorate all cells, if not otherwise defined on the cell.
        layers: maps name to gdslayer/datatype.
            Must be of type LayerEnum.
        layer_stack: maps name to layer numbers, thickness, zmin, sidewall_angle.
            if can also contain material properties
            (refractive index, nonlinear coefficient, sheet resistance ...).
        sparameters_path: to store Sparameters simulations.
        interconnect_cml_path: path to interconnect CML (optional).
        grid_size: in um. Defaults to 1nm.
        constants: dict of constants for the PDK.

    """
    name: str
    layout: kdb.Layout
    layer_enclosures: LayerEnclosureModel
    cross_sections: CrossSectionModel
    enclosure: KCellEnclosure
    library: kdb.Library

    factories: Factories[AnyTKCell]
    virtual_factories: Factories[VKCell]
    tkcells: dict[int, TKCell] = Field(default_factory=dict)
    layers: type[LayerEnum]
    infos: LayerInfos
    layer_stack: LayerStack
    netlist_layer_mapping: dict[LayerEnum | int, LayerEnum | int] = Field(
        default_factory=dict
    )
    sparameters_path: Path | str | None
    interconnect_cml_path: Path | str | None
    constants: Constants
    rename_function: Callable[..., None]
    _registered_functions: dict[int, Callable[..., TKCell]]
    thread_lock: RLock = Field(default_factory=RLock)

    info: Info = Field(default_factory=Info)
    settings: KCellSettings = Field(frozen=True)
    future_cell_name: str | None

    decorators: Decorators
    default_cell_output_type: type[KCell | DKCell] = KCell

    def __init__(
        self,
        name: str,
        layer_enclosures: dict[str, LayerEnclosure] | LayerEnclosureModel | None = None,
        enclosure: KCellEnclosure | None = None,
        infos: type[LayerInfos] | None = None,
        sparameters_path: Path | str | None = None,
        interconnect_cml_path: Path | str | None = None,
        layer_stack: LayerStack | None = None,
        constants: type[Constants] | None = None,
        base_kcl: KCLayout | None = None,
        port_rename_function: Callable[..., None] = rename_clockwise_multi,
        copy_base_kcl_layers: bool = True,
        info: dict[str, MetaData] | None = None,
        default_cell_output_type: type[KCell | DKCell] = KCell,
    ) -> None:
        """Create a new KCLayout (PDK). Can be based on an old KCLayout.

        Args:
            name: Name of the PDK.
            layer_enclosures: Additional KCellEnclosures that should be available
                except the KCellEnclosure
            enclosure: The standard KCellEnclosure of the PDK.
            infos: A LayerInfos describing the layerstack of the PDK.
            sparameters_path: Path to the sparameters config file.
            interconnect_cml_path: Path to the interconnect file.
            layer_stack: maps name to layer numbers, thickness, zmin, sidewall_angle.
                if can also contain material properties
                (refractive index, nonlinear coefficient, sheet resistance ...).
            constants: A model containing all the constants related to the PDK.
            base_kcl: an optional basis of the PDK.
            port_rename_function: Which function to use for renaming kcell ports.
            copy_base_kcl_layers: Copy all known layers from the base if any are
                defined.
            info: Additional metadata to put into info attribute.
        """
        library = kdb.Library()
        layout = library.layout()
        layer_stack = layer_stack or LayerStack()
        constants_ = constants() if constants else Constants()
        infos_ = infos() if infos else LayerInfos()
        if layer_enclosures is not None:
            if isinstance(layer_enclosures, dict):
                layer_enclosures = LayerEnclosureModel(root=layer_enclosures)
        else:
            layer_enclosures = LayerEnclosureModel(root={})
        super().__init__(
            name=name,
            layer_enclosures=layer_enclosures,
            cross_sections=CrossSectionModel(kcl=self),
            enclosure=KCellEnclosure([]),
            infos=infos_,
            layers=LayerEnum,
            factories=Factories({}),
            virtual_factories=Factories({}),
            sparameters_path=sparameters_path,
            interconnect_cml_path=interconnect_cml_path,
            constants=constants_,
            library=library,
            layer_stack=layer_stack,
            layout=layout,
            rename_function=port_rename_function,
            info=Info(**info) if info else Info(),
            future_cell_name=None,
            settings=KCellSettings(
                version=__version__,
                klayout_version=kdb.__version__,  # type: ignore[attr-defined]
                meta_format="v3",
            ),
            decorators=Decorators(self),
            default_cell_output_type=default_cell_output_type,
        )

        self.library.register(self.name)

        enclosure = KCellEnclosure(
            enclosures=[enc.model_copy() for enc in enclosure.enclosures.enclosures]
            if enclosure
            else []
        )
        sparameters_path = sparameters_path
        interconnect_cml_path = interconnect_cml_path
        if enclosure is None:
            enclosure = KCellEnclosure([])
        self.sparameters_path = sparameters_path
        self.enclosure = enclosure
        self.interconnect_cml_path = interconnect_cml_path

        kcls[self.name] = self

    @model_validator(mode="before")
    @classmethod
    def _validate_layers(cls, data: dict[str, Any]) -> dict[str, Any]:
        data["layers"] = layerenum_from_dict(
            layers=data["infos"], layout=data["library"].layout()
        )
        data["library"].register(data["name"])
        return data

    @functools.cached_property
    def dkcells(self) -> DKCells:
        """DKCells is a mapping of int to DKCell."""
        return DKCells(self)

    @functools.cached_property
    def kcells(self) -> KCells:
        """KCells is a mapping of int to KCell."""
        return KCells(self)

    @property
    def dbu(self) -> float:
        """Get the database unit."""
        return self.layout.dbu

    def create_layer_enclosure(
        self,
        sections: Sequence[
            tuple[kdb.LayerInfo, int] | tuple[kdb.LayerInfo, int, int]
        ] = [],
        name: str | None = None,
        main_layer: kdb.LayerInfo | None = None,
        dsections: Sequence[
            tuple[kdb.LayerInfo, float] | tuple[kdb.LayerInfo, float, float]
        ]
        | None = None,
    ) -> LayerEnclosure:
        """Create a new LayerEnclosure in the KCLayout."""
        if name is None:
            if main_layer is not None and main_layer.name != "":
                name = main_layer.name
        enc = LayerEnclosure(
            sections=sections,
            dsections=dsections,
            name=name,
            main_layer=main_layer,
            kcl=self,
        )

        self.layer_enclosures[enc.name] = enc
        return enc

    @overload
    def find_layer(self, name: str) -> LayerEnum: ...

    @overload
    def find_layer(self, info: kdb.LayerInfo) -> LayerEnum: ...

    @overload
    def find_layer(
        self,
        layer: int,
        datatype: int,
    ) -> LayerEnum: ...

    @overload
    def find_layer(
        self,
        layer: int,
        dataytpe: int,
        name: str,
    ) -> LayerEnum: ...

    @overload
    def find_layer(
        self, name: str, *, allow_undefined_layers: Literal[True] = True
    ) -> LayerEnum | int: ...

    @overload
    def find_layer(
        self, info: kdb.LayerInfo, *, allow_undefined_layers: Literal[True] = True
    ) -> LayerEnum | int: ...

    @overload
    def find_layer(
        self, layer: int, datatype: int, *, allow_undefined_layers: Literal[True] = True
    ) -> LayerEnum | int: ...

    @overload
    def find_layer(
        self,
        layer: int,
        dataytpe: int,
        name: str,
        allow_undefined_layers: Literal[True] = True,
    ) -> LayerEnum | int: ...

    def find_layer(
        self,
        *args: int | str | kdb.LayerInfo,
        **kwargs: int | str | kdb.LayerInfo | bool,
    ) -> LayerEnum | int:
        """Try to find a registered layer. Throws a KeyError if it cannot find it.

        Can find a layer either by name, layer and datatype (two args), LayerInfo, or
        all three of layer, datatype, and name.
        """
        allow_undefined_layers = kwargs.pop(
            "allow_undefined_layers", config.allow_undefined_layers
        )
        info = self.layout.get_info(self.layout.layer(*args, **kwargs))
        try:
            return self.layers[info.name]  # type:ignore[no-any-return, index]
        except KeyError as e:
            if allow_undefined_layers:
                return self.layout.layer(info)
            raise KeyError(
                f"Layer '{args=}, {kwargs=}' has not been defined in the KCLayout."
            ) from e

    @overload
    def to_um(self, other: None) -> None: ...
    @overload
    def to_um(self, other: int) -> float: ...

    @overload
    def to_um(self, other: kdb.Point) -> kdb.DPoint: ...

    @overload
    def to_um(self, other: kdb.Vector) -> kdb.DVector: ...

    @overload
    def to_um(self, other: kdb.Box) -> kdb.DBox: ...

    @overload
    def to_um(self, other: kdb.Polygon) -> kdb.DPolygon: ...

    @overload
    def to_um(self, other: kdb.Path) -> kdb.DPath: ...

    @overload
    def to_um(self, other: kdb.Text) -> kdb.DText: ...

    def to_um(
        self,
        other: int
        | kdb.Point
        | kdb.Vector
        | kdb.Box
        | kdb.Polygon
        | kdb.Path
        | kdb.Text
        | None,
    ) -> (
        float
        | kdb.DPoint
        | kdb.DVector
        | kdb.DBox
        | kdb.DPolygon
        | kdb.DPath
        | kdb.DText
        | None
    ):
        """Convert Shapes or values in dbu to DShapes or floats in um."""
        if other is None:
            return None
        return kdb.CplxTrans(self.layout.dbu) * other

    @overload
    def to_dbu(self, other: None) -> None: ...
    @overload
    def to_dbu(self, other: float) -> int: ...

    @overload
    def to_dbu(self, other: kdb.DPoint) -> kdb.Point: ...

    @overload
    def to_dbu(self, other: kdb.DVector) -> kdb.Vector: ...

    @overload
    def to_dbu(self, other: kdb.DBox) -> kdb.Box: ...

    @overload
    def to_dbu(self, other: kdb.DPolygon) -> kdb.Polygon: ...

    @overload
    def to_dbu(self, other: kdb.DPath) -> kdb.Path: ...

    @overload
    def to_dbu(self, other: kdb.DText) -> kdb.Text: ...

    def to_dbu(
        self,
        other: float
        | kdb.DPoint
        | kdb.DVector
        | kdb.DBox
        | kdb.DPolygon
        | kdb.DPath
        | kdb.DText
        | None,
    ) -> (
        int
        | kdb.Point
        | kdb.Vector
        | kdb.Box
        | kdb.Polygon
        | kdb.Path
        | kdb.Text
        | None
    ):
        """Convert Shapes or values in dbu to DShapes or floats in um."""
        if other is None:
            return None
        return kdb.CplxTrans(self.layout.dbu).inverted() * other

    @overload
    def cell(
        self,
        _func: KCellFunc[KCellParams, K],
        /,
    ) -> KCellFunc[KCellParams, K]: ...

    @overload
    def cell(
        self,
        /,
        *,
        set_settings: bool = ...,
        set_name: bool = ...,
        check_ports: bool = ...,
        check_instances: CheckInstances | None = ...,
        snap_ports: bool = ...,
        add_port_layers: bool = ...,
        cache: Cache[int, Any] | dict[int, Any] | None = ...,
        basename: str | None = ...,
        drop_params: list[str] = ...,
        register_factory: bool = ...,
        overwrite_existing: bool | None = ...,
        layout_cache: bool | None = ...,
        info: dict[str, MetaData] | None = ...,
        post_process: Iterable[Callable[[K], None]] = ...,
        debug_names: bool | None = ...,
        tags: list[str] | None = ...,
    ) -> Callable[[KCellFunc[KCellParams, K]], KCellFunc[KCellParams, K]]: ...

    @overload
    def cell(
        self,
        /,
        *,
        output_type: type[K],
        set_settings: bool = ...,
        set_name: bool = ...,
        check_ports: bool = ...,
        check_instances: CheckInstances | None = ...,
        snap_ports: bool = ...,
        add_port_layers: bool = ...,
        cache: Cache[int, Any] | dict[int, Any] | None = ...,
        basename: str | None = ...,
        drop_params: list[str] = ...,
        register_factory: bool = ...,
        overwrite_existing: bool | None = ...,
        layout_cache: bool | None = ...,
        info: dict[str, MetaData] | None = ...,
        post_process: Iterable[Callable[[K], None]] = ...,
        debug_names: bool | None = ...,
        tags: list[str] | None = ...,
    ) -> Callable[[KCellFunc[KCellParams, AnyTKCell]], KCellFunc[KCellParams, K]]: ...

    def cell(
        self,
        _func: KCellFunc[KCellParams, K] | None = None,
        /,
        *,
        output_type: type[K] | None = None,
        set_settings: bool = True,
        set_name: bool = True,
        check_ports: bool = True,
        check_instances: CheckInstances | None = None,
        snap_ports: bool = True,
        add_port_layers: bool = True,
        cache: Cache[int, Any] | dict[int, Any] | None = None,
        basename: str | None = None,
        drop_params: Sequence[str] = ("self", "cls"),
        register_factory: bool = True,
        overwrite_existing: bool | None = None,
        layout_cache: bool | None = None,
        info: dict[str, MetaData] | None = None,
        post_process: Iterable[Callable[[K], None]] = tuple(),
        debug_names: bool | None = None,
        tags: list[str] | None = None,
    ) -> (
        KCellFunc[KCellParams, K]
        | Callable[[KCellFunc[KCellParams, K]], KCellFunc[KCellParams, K]]
        | Callable[[KCellFunc[KCellParams, AnyTKCell]], KCellFunc[KCellParams, K]]
    ):
        """Decorator to cache and auto name the cell.

        This will use `functools.cache` to cache the function call.
        Additionally, if enabled this will set the name and from the args/kwargs of the
        function and also paste them into a settings dictionary of the
        [KCell][kfactory.kcell.KCell].

        Args:
            output_type: The type of the cell to return.
            set_settings: Copy the args & kwargs into the settings dictionary
            set_name: Auto create the name of the cell to the functionname plus a
                string created from the args/kwargs
            check_ports: Check uniqueness of port names.
            check_instances: Check for any complex instances. A complex instance is a an
                instance that has a magnification != 1 or non-90° rotation.
                Depending on the setting, an error is raised, the cell is flattened,
                a VInstance is created instead of a regular instance, or they are
                ignored.
            snap_ports: Snap the centers of the ports onto the grid
                (only x/y, not angle).
            add_port_layers: Add special layers of
                [netlist_layer_mapping][kfactory.kcell.KCLayout.netlist_layer_mapping]
                to the ports if the port layer is in the mapping.
            cache: Provide a user defined cache instead of an internal one. This
                can be used for example to clear the cache.
                expensive if the cell is called often).
            basename: Overwrite the name normally inferred from the function or class
                name.
            drop_params: Drop these parameters before writing the
                [settings][kfactory.kcell.KCell.settings]
            register_factory: Register the resulting KCell-function to the
                [factories][kfactory.kcell.KCLayout.factories]
            layout_cache: If true, treat the layout like a cache, if a cell with the
                same name exists already, pick that one instead of using running the
                function. This only works if `set_name` is true. Can be globally
                configured through `config.cell_layout_cache`.
            overwrite_existing: If cells were created with the same name, delete other
                cells with the same name. Can be globally configured through
                `config.cell_overwrite_existing`.
            info: Additional metadata to put into info attribute.
            post_process: List of functions to call after the cell has been created.
            debug_names: Check on setting the name whether a cell with this name already
                exists.
            tags: Tag cell functions with user defined tags. With this, cell functions
                can then be retrieved with `kcl.factories.tags[my_tag]` or if filtered
                for multiple `kcl.factories.for_tags([my_tag1, my_tag2, ...])`.
        """
        if check_instances is None:
            check_instances = config.check_instances
        if overwrite_existing is None:
            overwrite_existing = config.cell_overwrite_existing
        if layout_cache is None:
            layout_cache = config.cell_layout_cache
        if debug_names is None:
            debug_names = config.debug_names

        def decorator_autocell(
            f: KCellFunc[KCellParams, AnyTKCell] | KCellFunc[KCellParams, K],
        ) -> KCellFunc[KCellParams, K]:
            sig = inspect.signature(f)
            output_cell_type_: type[K] | type[ProtoTKCell[Any]]
            if output_type is not None:
                output_cell_type_ = output_type
            elif sig.return_annotation is not inspect.Signature.empty:
                output_cell_type_ = sig.return_annotation
            else:
                output_cell_type_ = self.default_cell_output_type

            output_cell_type = cast(type[K], output_cell_type_)

            cache_: Cache[_HashedTuple, K] | dict[_HashedTuple, K] = cache or Cache(
                maxsize=float("inf")
            )

            @functools.wraps(f)
            def wrapper_autocell(
                *args: KCellParams.args, **kwargs: KCellParams.kwargs
            ) -> K:
                params: dict[str, Any] = {
                    p.name: p.default for _, p in sig.parameters.items()
                }
                param_units: dict[str, str] = {
                    p.name: p.annotation.__metadata__[0]
                    for p in sig.parameters.values()
                    if get_origin(p.annotation) is Annotated
                }
                arg_par = list(sig.parameters.items())[: len(args)]
                for i, (k, _) in enumerate(arg_par):
                    params[k] = args[i]
                params.update(kwargs)

                del_parameters: list[str] = []

                for key, value in params.items():
                    if isinstance(value, dict | list):
                        params[key] = _to_hashable(value)
                    elif isinstance(value, kdb.LayerInfo):
                        params[key] = self.get_info(self.layer(value))
                    if value is inspect.Parameter.empty:
                        del_parameters.append(key)

                for param in del_parameters:
                    params.pop(param, None)
                    param_units.pop(param, None)

                @cachetools.cached(cache=cache_, lock=RLock())
                @functools.wraps(f)
                def wrapped_cell(**params: Any) -> K:
                    for key, value in params.items():
                        if isinstance(value, DecoratorDict | DecoratorList):
                            params[key] = _hashable_to_original(value)
                    old_future_name: str | None = None
                    if set_name:
                        if basename is not None:
                            name = get_cell_name(basename, **params)
                        else:
                            name = get_cell_name(f.__name__, **params)
                        old_future_name = self.future_cell_name
                        self.future_cell_name = name
                        if layout_cache:
                            if overwrite_existing:
                                for c in list(self._cells(self.future_cell_name)):
                                    self[c.cell_index()].delete()
                            else:
                                layout_cell = self.layout_cell(self.future_cell_name)
                                if layout_cell is not None:
                                    logger.debug(
                                        "Loading {} from layout cache",
                                        self.future_cell_name,
                                    )
                                    return self.get_cell(
                                        layout_cell.cell_index(), output_cell_type
                                    )
                        logger.debug(f"Constructing {self.future_cell_name}")
                        name_: str | None = name
                    else:
                        name_ = None
                    cell = f(**params)  # type: ignore[call-arg]

                    logger.debug("Constructed {}", name_ or cell.name)

                    if cell.locked:
                        # If the cell is locked, it comes from a cache (most likely)
                        # and should be copied first
                        cell = cell.dup()
                    if overwrite_existing:
                        for c in list(self._cells(name_ or cell.name)):
                            if c is not cell.kdb_cell:
                                self[c.cell_index()].delete()
                    if set_name and name_:
                        if debug_names and cell.kcl.layout_cell(name_) is not None:
                            logger.opt(depth=4).error(
                                "KCell with name {name} exists already. Duplicate "
                                "occurrence in module '{module}' at "
                                "line {lno}",
                                name=name_,
                                module=f.__module__,
                                function_name=f.__name__,
                                lno=inspect.getsourcelines(f)[1],
                            )
                            raise CellNameError(
                                f"KCell with name {name_} exists already."
                            )

                        cell.name = name_
                        self.future_cell_name = old_future_name
                    if set_settings:
                        if hasattr(f, "__name__"):
                            cell.function_name = f.__name__
                        elif hasattr(f, "func"):
                            cell.function_name = f.func.__name__
                        else:
                            raise ValueError(f"Function {f} has no name.")
                        cell.basename = basename

                        for param in drop_params:
                            params.pop(param, None)
                            param_units.pop(param, None)
                        cell.settings = KCellSettings(**params)
                        cell.settings_units = KCellSettingsUnits(**param_units)
                    if check_ports:
                        port_names: dict[str | None, int] = defaultdict(int)
                        for port in cell.ports:
                            port_names[port.name] += 1
                        duplicate_names = [
                            (name, n) for name, n in port_names.items() if n > 1
                        ]
                        if duplicate_names:
                            raise ValueError(
                                "Found duplicate port names: "
                                + ", ".join(
                                    [f"{name}: {n}" for name, n in duplicate_names]
                                )
                                + " If this intentional, please pass "
                                "`check_ports=False` to the @cell decorator"
                            )
                    match check_instances:
                        case CheckInstances.RAISE:
                            if any(inst.is_complex() for inst in cell.each_inst()):
                                raise ValueError(
                                    "Most foundries will not allow off-grid "
                                    "instances. Please flatten them or add "
                                    "check_instances=False to the decorator.\n"
                                    "Cellnames of instances affected by this:"
                                    + "\n".join(
                                        inst.cell.name
                                        for inst in cell.each_inst()
                                        if inst.is_complex()
                                    )
                                )
                        case CheckInstances.FLATTEN:
                            if any(inst.is_complex() for inst in cell.each_inst()):
                                cell.flatten()
                        case CheckInstances.VINSTANCES:
                            if any(inst.is_complex() for inst in cell.each_inst()):
                                complex_insts = [
                                    inst
                                    for inst in cell.each_inst()
                                    if inst.is_complex()
                                ]
                                for inst in complex_insts:
                                    vinst = cell.create_vinst(
                                        self[inst.cell.cell_index()]
                                    )
                                    vinst.trans = inst.dcplx_trans
                                    inst.delete()
                        case CheckInstances.IGNORE:
                            pass
                    cell.insert_vinsts(recursive=False)
                    if snap_ports:
                        for port in cell.to_itype().ports:
                            if port.base.dcplx_trans:
                                dup = port.base.dcplx_trans.dup()
                                dup.disp = self.to_um(
                                    self.to_dbu(port.base.dcplx_trans.disp)
                                )
                                port.dcplx_trans = dup
                    if add_port_layers:
                        for port in cell.to_itype().ports:
                            if port.layer in cell.kcl.netlist_layer_mapping:
                                if port.base.trans:
                                    edge = kdb.Edge(
                                        kdb.Point(0, -port.width // 2),
                                        kdb.Point(0, port.width // 2),
                                    )
                                    cell.shapes(
                                        cell.kcl.netlist_layer_mapping[port.layer]
                                    ).insert(port.trans * edge)
                                    if port.name:
                                        cell.shapes(
                                            cell.kcl.netlist_layer_mapping[port.layer]
                                        ).insert(kdb.Text(port.name, port.trans))
                                else:
                                    dwidth = self.to_um(port.width)
                                    dedge = kdb.DEdge(
                                        kdb.DPoint(0, -dwidth / 2),
                                        kdb.DPoint(0, dwidth / 2),
                                    )
                                    cell.shapes(
                                        cell.kcl.netlist_layer_mapping[port.layer]
                                    ).insert(port.dcplx_trans * dedge)
                                    if port.name:
                                        cell.shapes(
                                            cell.kcl.netlist_layer_mapping[port.layer]
                                        ).insert(
                                            kdb.DText(
                                                port.name,
                                                port.dcplx_trans.s_trans(),
                                            )
                                        )
                    # post process the cell
                    for pp in post_process:
                        pp(cell)  # type: ignore[arg-type]
                    cell.base.lock()
                    if cell.kcl != self:
                        raise ValueError(
                            "The KCell created must be using the same"
                            " KCLayout object as the @cell decorator. "
                            f"{self.name!r} != {cell.kcl.name!r}. Please make sure "
                            "to use @kcl.cell and only use @cell for cells which "
                            "are created through kfactory.kcl. To create KCells not"
                            " in the standard KCLayout, use either "
                            "custom_kcl.kcell() or KCell(kcl=custom_kcl)."
                        )
                    return output_cell_type(base=cell.base)

                with self.thread_lock:
                    cell_ = wrapped_cell(**params)
                    if cell_.destroyed():
                        # If any cell has been destroyed, we should clean up the cache.
                        # Delete all the KCell entrances in the cache which have
                        # `destroyed() == True`
                        deleted_cell_hashes: list[_HashedTuple] = [
                            _hash_item
                            for _hash_item, _cell_item in cache_.items()
                            if _cell_item.destroyed()
                        ]
                        for _dch in deleted_cell_hashes:
                            del cache_[_dch]
                        cell_ = wrapped_cell(**params)

                    if info is not None:
                        cell_.info.update(info)

                    return cell_

            if register_factory:
                with self.thread_lock:
                    if hasattr(f, "__name__"):
                        function_name = f.__name__
                    elif hasattr(f, "func"):
                        function_name = f.func.__name__
                    else:
                        raise ValueError(f"Function {f} has no name.")
                    if tags:
                        for tag in tags:
                            self.factories.tags[tag].append(wrapper_autocell)
                    self.factories[basename or function_name] = wrapper_autocell
            return wrapper_autocell

        return (
            cast(
                Callable[[KCellFunc[KCellParams, K]], KCellFunc[KCellParams, K]]
                | Callable[
                    [KCellFunc[KCellParams, AnyTKCell]],
                    KCellFunc[KCellParams, K],
                ],
                decorator_autocell,
            )
            if _func is None
            else decorator_autocell(_func)
        )

    @overload
    def vcell(
        self,
        _func: Callable[KCellParams, VKCell],
        /,
    ) -> Callable[KCellParams, VKCell]: ...

    @overload
    def vcell(
        self,
        /,
        *,
        set_settings: bool = True,
        set_name: bool = True,
        check_ports: bool = True,
        basename: str | None = None,
        drop_params: Sequence[str] = ("self", "cls"),
        register_factory: bool = True,
    ) -> Callable[[Callable[KCellParams, VKCell]], Callable[KCellParams, VKCell]]: ...

    def vcell(
        self,
        _func: Callable[KCellParams, VKCell] | None = None,
        /,
        *,
        set_settings: bool = True,
        set_name: bool = True,
        check_ports: bool = True,
        add_port_layers: bool = True,
        cache: Cache[int, Any] | dict[int, Any] | None = None,
        basename: str | None = None,
        drop_params: Sequence[str] = ("self", "cls"),
        register_factory: bool = True,
    ) -> (
        Callable[KCellParams, VKCell]
        | Callable[[Callable[KCellParams, VKCell]], Callable[KCellParams, VKCell]]
    ):
        """Decorator to cache and auto name the cell.

        This will use `functools.cache` to cache the function call.
        Additionally, if enabled this will set the name and from the args/kwargs of the
        function and also paste them into a settings dictionary of the
        [KCell][kfactory.kcell.KCell].

        Args:
            set_settings: Copy the args & kwargs into the settings dictionary
            set_name: Auto create the name of the cell to the functionname plus a
                string created from the args/kwargs
            check_ports: Check whether there are any non-90° ports in the cell and throw
                a warning if there are
            snap_ports: Snap the centers of the ports onto the grid
                (only x/y, not angle).
            add_port_layers: Add special layers of
                [netlist_layer_mapping][kfactory.kcell.KCLayout.netlist_layer_mapping]
                to the ports if the port layer is in the mapping.
            cache: Provide a user defined cache instead of an internal one. This
                can be used for example to clear the cache.
            rec_dicts: Allow and inspect recursive dictionaries as parameters (can be
                expensive if the cell is called often).
            basename: Overwrite the name normally inferred from the function or class
                name.
            drop_params: Drop these parameters before writing the
                [settings][kfactory.kcell.KCell.settings]
            register_factory: Register the resulting KCell-function to the
                [factories][kfactory.kcell.KCLayout.factories]
        """
        if drop_params is None:
            drop_params = ["self", "cls"]

        def decorator_autocell(
            f: Callable[KCellParams, VKCell],
        ) -> Callable[KCellParams, VKCell]:
            sig = inspect.signature(f)

            # previously was a KCellCache, but dict should do for most case
            cache_ = cache or {}

            @functools.wraps(f)
            def wrapper_autocell(
                *args: KCellParams.args, **kwargs: KCellParams.kwargs
            ) -> VKCell:
                params: dict[str, Any] = {
                    p.name: p.default for p in sig.parameters.values()
                }
                param_units: dict[str, str] = {
                    p.name: p.annotation.__metadata__[0]
                    for p in sig.parameters.values()
                    if get_origin(p.annotation) is Annotated
                }
                arg_par = list(sig.parameters.items())[: len(args)]
                for i, (k, _v) in enumerate(arg_par):
                    params[k] = args[i]
                params.update(kwargs)

                del_parameters: list[str] = []

                for key, value in params.items():
                    if isinstance(value, dict | list):
                        params[key] = _to_hashable(value)
                    elif isinstance(value, kdb.LayerInfo):
                        params[key] = self.get_info(self.layer(value))
                    if value is inspect.Parameter.empty:
                        del_parameters.append(key)

                for param in del_parameters:
                    params.pop(param, None)
                    param_units.pop(param, None)

                @cachetools.cached(cache=cache_)
                @functools.wraps(f)
                def wrapped_cell(**params: Any) -> VKCell:
                    for key, value in params.items():
                        if isinstance(value, DecoratorDict | DecoratorList):
                            params[key] = _hashable_to_original(value)
                    cell = f(**params)  # type: ignore[call-arg]
                    if cell.locked:
                        raise ValueError(
                            "Trying to change a locked VKCell is no allowed. "
                            f"{cell.name=}"
                        )
                    if set_name:
                        if basename is not None:
                            name = get_cell_name(basename, **params)
                        else:
                            name = get_cell_name(f.__name__, **params)
                        cell.name = name
                    if set_settings:
                        if hasattr(f, "__name__"):
                            cell.function_name = f.__name__
                        elif hasattr(f, "func"):
                            cell.function_name = f.func.__name__
                        else:
                            raise ValueError(f"Function {f} has no name.")
                        cell.basename = basename
                        for param in drop_params:
                            params.pop(param, None)
                            param_units.pop(param, None)
                        cell.settings = KCellSettings(**params)
                        cell.settings_units = KCellSettingsUnits(**param_units)
                    if add_port_layers:
                        for port in cell.ports:
                            if port.layer in cell.kcl.netlist_layer_mapping:
                                if port.base.trans:
                                    edge = kdb.Edge(
                                        kdb.Point(0, int(-port.width // 2)),
                                        kdb.Point(0, int(port.width // 2)),
                                    )
                                    cell.shapes(
                                        cell.kcl.netlist_layer_mapping[port.layer]
                                    ).insert(port.trans * edge)
                                    if port.name:
                                        cell.shapes(
                                            cell.kcl.netlist_layer_mapping[port.layer]
                                        ).insert(kdb.Text(port.name, port.trans))
                                else:
                                    dedge = kdb.DEdge(
                                        kdb.DPoint(0, -port.width / 2),
                                        kdb.DPoint(0, port.width / 2),
                                    )
                                    cell.shapes(
                                        cell.kcl.netlist_layer_mapping[port.layer]
                                    ).insert(port.dcplx_trans * dedge)
                                    if port.name:
                                        cell.shapes(
                                            cell.kcl.netlist_layer_mapping[port.layer]
                                        ).insert(
                                            kdb.DText(
                                                port.name, port.dcplx_trans.s_trans()
                                            )
                                        )
                    cell._base.lock()
                    if cell.kcl != self:
                        raise ValueError(
                            "The KCell created must be using the same"
                            " KCLayout object as the @cell decorator. "
                            f"{self.name!r} != {cell.kcl.name!r}. Please make sure to "
                            "use @kcl.cell and only use @cell for cells which are"
                            " created through kfactory.kcl. To create KCells not in "
                            "the standard KCLayout, use either custom_kcl.kcell() or "
                            "KCell(kcl=custom_kcl)."
                        )
                    return cell

                return wrapped_cell(**params)

            if register_factory:
                if hasattr(f, "__name__"):
                    function_name = f.__name__
                elif hasattr(f, "func"):
                    function_name = f.func.__name__
                else:
                    raise ValueError(f"Function {f} has no name.")
                self.virtual_factories[basename or function_name] = wrapper_autocell
            return wrapper_autocell

        return decorator_autocell if _func is None else decorator_autocell(_func)

    def kcell(self, name: str | None = None, ports: Ports | None = None) -> KCell:
        """Create a new cell based ont he pdk's layout object."""
        return KCell(name=name, kcl=self, ports=ports)

    def dkcell(self, name: str | None = None, ports: DPorts | None = None) -> DKCell:
        """Create a new cell based ont he pdk's layout object."""
        return DKCell(name=name, kcl=self, ports=ports)

    def vkcell(self, name: str | None = None) -> VKCell:
        """Create a new cell based ont he pdk's layout object."""
        return VKCell(name=name, kcl=self)

    def set_layers_from_infos(self, name: str, layers: LayerInfos) -> type[LayerEnum]:
        """Create a new LAYER enum based on the pdk's kcl."""
        return layerenum_from_dict(name=name, layers=layers, layout=self.layout)

    def __getattr__(self, name: str) -> Any:
        """If KCLayout doesn't have an attribute, look in the KLayout Cell."""
        if name != "_name" and name not in self.model_fields:
            return self.layout.__getattribute__(name)

    def __setattr__(self, name: str, value: Any) -> None:
        """Use a custom setter to automatically set attributes.

        If the attribute is not in this object, set it on the
        Layout object.
        """
        if name in self.model_fields:
            super().__setattr__(name, value)
        elif hasattr(self.layout, name):
            self.layout.__setattr__(name, value)

    def layerenum_from_dict(
        self, name: str = "LAYER", *, layers: LayerInfos
    ) -> type[LayerEnum]:
        """Create a new [LayerEnum][kfactory.kcell.LayerEnum] from this KCLayout."""
        return layerenum_from_dict(layers=layers, name=name, layout=self.layout)

    def clear(self, keep_layers: bool = True) -> None:
        """Clear the Layout.

        If the layout is cleared, all the LayerEnums and
        """
        self.layout.clear()
        self.tkcells = {}

        if keep_layers:
            self.layers = self.layerenum_from_dict(layers=self.infos)
        else:
            self.layers = self.layerenum_from_dict(layers=LayerInfos())

    def dup(self, init_cells: bool = True) -> KCLayout:
        """Create a duplication of the `~KCLayout` object.

        Args:
            init_cells: initialize the all cells in the new KCLayout object

        Returns:
            Copy of itself
        """
        kcl = KCLayout(self.name + "_DUPLICATE")
        kcl.layout.assign(self.layout.dup())
        if init_cells:
            for i, kc in self.tkcells.items():
                kcl.tkcells[i] = kc.model_copy(update={"kdb_cell": kc.kdb_cell})
        kcl.rename_function = self.rename_function
        return kcl

    def layout_cell(self, name: str | int) -> kdb.Cell | None:
        """Get a cell by name or index from the Layout object."""
        return self.layout.cell(name)

    @overload
    def _cells(self, name: str) -> list[kdb.Cell]: ...

    @overload
    def _cells(self) -> int: ...

    def _cells(self, name: str | None = None) -> int | list[kdb.Cell]:
        if name is None:
            return self.layout.cells()
        return self.layout.cells(name)

    def create_cell(
        self,
        name: str,
        *args: str,
        allow_duplicate: bool = False,
    ) -> kdb.Cell:
        """Create a new cell in the library.

        This shouldn't be called manually.
        The constructor of KCell will call this method.

        Args:
            name: The (initial) name of the cell.
            allow_duplicate: Allow the creation of a cell with the same name which
                already is registered in the Layout.
                This will create a cell with the name `name` + `$1` or `2..n`
                increasing by the number of existing duplicates
            args: additional arguments passed to
                `klayout.db.Layout.create_cell`

        Returns:
            klayout.db.Cell: klayout.db.Cell object created in the Layout

        """
        with self.thread_lock:
            if allow_duplicate or (self.layout_cell(name) is None):
                return self.layout.create_cell(name, *args)
            else:
                raise ValueError(
                    f"Cellname {name} already exists. Please make sure the cellname is"
                    " unique or pass `allow_duplicate` when creating the library"
                )

    def delete_cell(self, cell: AnyTKCell | int) -> None:
        """Delete a cell in the kcl object."""
        with self.thread_lock:
            if isinstance(cell, int):
                self.layout.cell(cell).locked = False
                self.layout.delete_cell(cell)
                self.tkcells.pop(cell, None)
            else:
                ci = cell.cell_index()
                self.layout.cell(ci).locked = False
                self.layout.delete_cell(ci)
                self.tkcells.pop(ci, None)

    def delete_cell_rec(self, cell_index: int) -> None:
        """Deletes a KCell plus all subcells."""
        with self.thread_lock:
            self.layout.delete_cell_rec(cell_index)
            self.rebuild()

    def delete_cells(self, cell_index_list: Sequence[int]) -> None:
        """Delete a sequence of cell by indexes."""
        with self.thread_lock:
            self.layout.delete_cells(cell_index_list)
            self.rebuild()

    def assign(self, layout: kdb.Layout) -> None:
        """Assign a new Layout object to the KCLayout object."""
        with self.thread_lock:
            self.layout.assign(layout)
            self.rebuild()

    def rebuild(self) -> None:
        """Rebuild the KCLayout based on the Layout object."""
        kcells2delete: list[int] = []
        with self.thread_lock:
            for ci, c in self.tkcells.items():
                if c.kdb_cell._destroyed():
                    kcells2delete.append(ci)

            for ci in kcells2delete:
                del self.tkcells[ci]

            for cell in self._cells("*"):
                if cell.cell_index() not in self.tkcells:
                    self.tkcells[cell.cell_index()] = self.get_cell(
                        cell.cell_index(), KCell
                    ).base

    def register_cell(self, kcell: AnyTKCell, allow_reregister: bool = False) -> None:
        """Register an existing cell in the KCLayout object.

        Args:
            kcell: KCell 56 be registered in the KCLayout
            allow_reregister: Overwrite the existing KCell registration with this one.
                Doesn't allow name duplication.
        """
        with self.thread_lock:
            if (kcell.cell_index() not in self.tkcells) or allow_reregister:
                self.tkcells[kcell.cell_index()] = kcell.base
            else:
                raise ValueError(
                    "Cannot register a new cell with a name that already"
                    " exists in the library"
                )

    def __getitem__(self, obj: str | int) -> KCell:
        """Retrieve a cell by name(str) or index(int).

        Attrs:
            obj: name of cell or cell_index
        """
        return self.get_cell(obj)

    def get_cell(self, obj: str | int, cell_type: type[K] = KCell) -> K:  # type: ignore[assignment]
        """Retrieve a cell by name(str) or index(int).

        Attrs:
            obj: name of cell or cell_index
            cell_type: type of cell to return
        """
        if isinstance(obj, int):
            try:
                return cell_type(base=self.tkcells[obj])
            except KeyError:
                kdb_c = self.layout_cell(obj)
                if kdb_c is None:
                    raise
                c = cell_type(name=kdb_c.name, kcl=self, kdb_cell=kdb_c)
                c.get_meta_data()
                return c
        else:
            kdb_c = self.layout_cell(obj)
            if kdb_c is not None:
                try:
                    return cell_type(base=self.tkcells[kdb_c.cell_index()])
                except KeyError:
                    c = cell_type(name=kdb_c.name, kcl=self, kdb_cell=kdb_c)
                    c.get_meta_data()
                    return c
        from pprint import pformat

        raise ValueError(
            f"Library doesn't have a KCell named {obj},"
            " available KCells are"
            f"{pformat(sorted([cell.name for cell in self.kcells.values()]))}"
        )

    def read(
        self,
        filename: str | Path,
        options: kdb.LoadLayoutOptions | None = None,
        register_cells: bool | None = None,
        test_merge: bool = True,
        update_kcl_meta_data: Literal["overwrite", "skip", "drop"] = "skip",
        meta_format: Literal["v1", "v2", "v3"] | None = None,
    ) -> kdb.LayerMap:
        """Read a GDS file into the existing Layout.

        Any existing meta info (KCell.info and KCell.settings) will be overwritten if
        a KCell already exists. Instead of overwriting the cells, they can also be
        loaded into new cells by using the corresponding cell_conflict_resolution.

        This will fail if any of the read cells try to load into a locked KCell.

        Layout meta infos are ignored from the loaded layout.

        Args:
            filename: Path of the GDS file.
            options: KLayout options to load from the GDS. Can determine how merge
                conflicts are handled for example. See
                https://www.klayout.de/doc-qt5/code/class_LoadLayoutOptions.html
            register_cells: If `True` create KCells for all cells in the GDS.
            test_merge: Check the layouts first whether they are compatible
                (no differences).
            update_kcl_meta_data: How to treat loaded KCLayout info.
                overwrite: overwrite existing info entries
                skip: keep existing info values
                drop: don't add any new info
            meta_format: How to read KCell metainfo from the gds. `v1` had stored port
                transformations as strings, never versions have them stored and loaded
                in their native KLayout formats.
        """
        if options is None:
            options = load_layout_options()
        with self.thread_lock:
            if meta_format is None:
                meta_format = config.meta_format
            if register_cells is None:
                register_cells = meta_format == config.meta_format
            layout_b = kdb.Layout()
            layout_b.read(str(filename), options)
            if (
                self.cells() > 0
                and test_merge
                and (
                    options.cell_conflict_resolution
                    != kdb.LoadLayoutOptions.CellConflictResolution.RenameCell
                )
            ):
                self.set_meta_data()
                for kcell in self.kcells.values():
                    kcell.set_meta_data()
                diff = MergeDiff(
                    layout_a=self.layout,
                    layout_b=layout_b,
                    name_a=self.name,
                    name_b=Path(filename).stem,
                )
                diff.compare()
                if diff.dbu_differs:
                    raise MergeError(
                        "Layouts' DBU differ. Check the log for more info."
                    )
                elif diff.diff_xor.cells() > 0:
                    diff_kcl = KCLayout(self.name + "_XOR")
                    diff_kcl.layout.assign(diff.diff_xor)
                    show(diff_kcl)

                    err_msg = (
                        f"Layout {self.name} cannot merge with layout "
                        f"{Path(filename).stem} safely. See the error messages "
                        f"or check with KLayout."
                    )

                    if diff.layout_meta_diff:
                        yaml = ruamel.yaml.YAML(typ=["rt", "string"])
                        err_msg += (
                            "\nLayout Meta Diff:\n```\n"
                            + yaml.dumps(dict(diff.layout_meta_diff))  # type: ignore[attr-defined]
                            + "\n```"
                        )
                    if diff.cells_meta_diff:
                        yaml = ruamel.yaml.YAML(typ=["rt", "string"])
                        err_msg += (
                            "\nLayout Meta Diff:\n```\n"
                            + yaml.dumps(dict(diff.cells_meta_diff))  # type: ignore[attr-defined]
                            + "\n```"
                        )

                    raise MergeError(err_msg)

            cells = set(self._cells("*"))
            fn = str(Path(filename).expanduser().resolve())
            lm = self.layout.read(fn, options)
            info, settings = self.get_meta_data()

            match update_kcl_meta_data:
                case "overwrite":
                    for k, v in info.items():
                        self.info[k] = v
                case "skip":
                    info_ = self.info.model_dump()

                    # for k, v in self.info:
                    #     _info[k] = v
                    info.update(info_)
                    self.info = Info(**info)

                case "drop":
                    pass
                case _:
                    raise ValueError(
                        f"Unknown meta update strategy {update_kcl_meta_data=}"
                        ", available strategies are 'overwrite', 'skip', or 'drop'"
                    )
            meta_format = settings.get("meta_format") or config.meta_format
            load_cells = {
                cell
                for c in layout_b.cells("*")
                if (cell := self.layout_cell(c.name)) is not None
            }
            new_cells = load_cells - cells

            if register_cells:
                for c in sorted(new_cells, key=lambda _c: _c.hierarchy_levels()):
                    kc = KCell(kdb_cell=c, kcl=self)
                    kc.get_meta_data(
                        meta_format=meta_format,
                    )

            for c in load_cells & cells:
                kc = self.kcells[c.cell_index()]
                kc.get_meta_data(meta_format=meta_format)

            return lm

    def get_meta_data(self) -> tuple[dict[str, Any], dict[str, Any]]:
        """Read KCLayout meta info from the KLayout object."""
        settings: dict[str, Any] = {}
        info: dict[str, Any] = {}
        cross_sections: list[dict[str, Any]] = []
        for meta in self.layout.each_meta_info():
            if meta.name.startswith("kfactory:info"):
                info[meta.name.removeprefix("kfactory:info:")] = meta.value
            elif meta.name.startswith("kfactory:settings"):
                settings[meta.name.removeprefix("kfactory:settings:")] = meta.value
            elif meta.name.startswith("kfactory:layer_enclosure:"):
                self.get_enclosure(
                    LayerEnclosure(
                        **meta.value,
                    )
                )
            elif meta.name.startswith("kfactory:cross_section:"):
                cross_sections.append(
                    {
                        "name": meta.name.removeprefix("kfactory:cross_section:"),
                        **meta.value,
                    }
                )

        for cs in cross_sections:
            self.get_symmetrical_cross_section(
                SymmetricalCrossSection(
                    width=cs["width"],
                    enclosure=self.get_enclosure(cs["layer_enclosure"]),
                    name=cs["name"],
                )
            )

        return info, settings

    def set_meta_data(self) -> None:
        """Set the info/settings of the KCLayout."""
        for name, setting in self.settings.model_dump().items():
            self.add_meta_info(
                kdb.LayoutMetaInfo(f"kfactory:settings:{name}", setting, None, True)
            )
        for name, info in self.info.model_dump().items():
            self.add_meta_info(
                kdb.LayoutMetaInfo(f"kfactory:info:{name}", info, None, True)
            )
        for enclosure in self.layer_enclosures.root.values():
            self.add_meta_info(
                kdb.LayoutMetaInfo(
                    f"kfactory:layer_enclosure:{enclosure.name}",
                    enclosure.model_dump(),
                    None,
                    True,
                )
            )
        for cross_section in self.cross_sections.cross_sections.values():
            self.add_meta_info(
                kdb.LayoutMetaInfo(
                    f"kfactory:cross_section:{cross_section.name}",
                    {
                        "width": cross_section.width,
                        "layer_enclosure": cross_section.enclosure.name,
                    },
                    None,
                    True,
                )
            )

    def write(
        self,
        filename: str | Path,
        options: kdb.SaveLayoutOptions | None = None,
        set_meta_data: bool = True,
        convert_external_cells: bool = False,
        autoformat_from_file_extension: bool = True,
    ) -> None:
        """Write a GDS file into the existing Layout.

        Args:
            filename: Path of the GDS file.
            options: KLayout options to load from the GDS. Can determine how merge
                conflicts are handled for example. See
                https://www.klayout.de/doc-qt5/code/class_LoadLayoutOptions.html
            set_meta_data: Make sure all the cells have their metadata set
            convert_external_cells: Whether to make KCells not in this KCLayout to
            autoformat_from_file_extension: Set the format of the output file
                automatically from the file extension of `filename`. This is necessary
                for the options. If not set, this will default to `GDSII`.
        """
        if options is None:
            options = save_layout_options()
        if isinstance(filename, Path):
            filename = str(filename.resolve())
        for kc in list(self.kcells.values()):
            kc.insert_vinsts()
        match (set_meta_data, convert_external_cells):
            case (True, True):
                self.set_meta_data()
                for kcell in self.kcells.values():
                    if not kcell.destroyed():
                        kcell.set_meta_data()
                        if kcell.is_library_cell():
                            kcell.convert_to_static(recursive=True)
            case (True, False):
                self.set_meta_data()
                for kcell in self.kcells.values():
                    if not kcell.destroyed():
                        kcell.set_meta_data()
            case (False, True):
                for kcell in self.kcells.values():
                    if kcell.is_library_cell() and not kcell.destroyed():
                        kcell.convert_to_static(recursive=True)

        if autoformat_from_file_extension:
            options.set_format_from_filename(filename)

        return self.layout.write(filename, options)

    def top_kcells(self) -> list[KCell]:
        """Return the top KCells."""
        return [self[tc.cell_index()] for tc in self.top_cells()]

    def top_kcell(self) -> KCell:
        """Return the top KCell if there is a single one."""
        return self[self.top_cell().cell_index()]

    def clear_kcells(self) -> None:
        """Clears all cells in the Layout object."""
        for kc in self.kcells.values():
            kc.locked = False
        for tc in self.top_kcells():
            tc.kdb_cell.prune_cell()
        self.tkcells = {}

    def get_enclosure(
        self, enclosure: str | LayerEnclosure | LayerEnclosureSpec
    ) -> LayerEnclosure:
        """Gets a layer enclosure by name specification or the layerenclosure itself."""
        return self.layer_enclosures.get_enclosure(enclosure, self)

    def get_symmetrical_cross_section(
        self,
        cross_section: str
        | SymmetricalCrossSection
        | CrossSectionSpec[int]
        | DSymmetricalCrossSection,
    ) -> SymmetricalCrossSection:
        """Get a cross section by name or specification."""
        return self.cross_sections.get_cross_section(cross_section)

    def get_icross_section(
        self,
        cross_section: str
        | SymmetricalCrossSection
        | CrossSectionSpec[int]
        | DSymmetricalCrossSection,
    ) -> CrossSection:
        """Get a cross section by name or specification."""
        return CrossSection(
            kcl=self, base=self.cross_sections.get_cross_section(cross_section)
        )

    def get_dcross_section(
        self,
        cross_section: str
        | SymmetricalCrossSection
        | CrossSectionSpec[float]
        | DSymmetricalCrossSection,
    ) -> DCrossSection:
        """Get a cross section by name or specification."""

        if isinstance(cross_section, dict):
            return DCrossSection(
                kcl=self,
                **cross_section,
            )
        return DCrossSection(
            kcl=self, base=self.cross_sections.get_cross_section(cross_section)
        )

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.name}, n={len(self.kcells)})"

    @overload
    def get_component(
        self, spec: KCellSpec, *, output_type: type[K], **cell_kwargs: Any
    ) -> K: ...

    @overload
    def get_component(
        self,
        spec: int,
    ) -> KCell: ...

    @overload
    def get_component(
        self,
        spec: str,
        **cell_kwargs: Any,
    ) -> ProtoTKCell[Any]: ...

    @overload
    def get_component(
        self,
        spec: Callable[..., K],
        **cell_kwargs: Any,
    ) -> K: ...
    @overload
    def get_component(self, spec: K) -> K: ...

    def get_component(
        self,
        spec: KCellSpec,
        *,
        output_type: type[K] | None = None,
        **cell_kwargs: Any,
    ) -> ProtoTKCell[Any]:
        if output_type:
            return output_type(base=self.get_component(spec, **cell_kwargs).base)
        if callable(spec):
            return spec(**cell_kwargs)
        if isinstance(spec, dict):
            settings = spec.get("settings", {}).copy()
            settings.update(cell_kwargs)
            return self.factories[spec["component"]](**settings)
        elif isinstance(spec, str):
            return self.factories[spec](**cell_kwargs)
        if cell_kwargs:
            raise ValueError(
                "Cell kwargs are not allowed for retrieving static cells by integer "
                "or the cell itself."
            )
        return self.kcells[spec] if isinstance(spec, int) else spec


KCLayout.model_rebuild()
TVCell.model_rebuild()
SymmetricalCrossSection.model_rebuild()


kcl = KCLayout("DEFAULT")
"""Default library object.

Any [KCell][kfactory.kcell.KCell] uses this object unless another one is
specified in the constructor."""
cell = kcl.cell
"""Default kcl @cell decorator."""
vcell = kcl.vcell
"""Default kcl @vcell decorator."""
