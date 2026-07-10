from __future__ import annotations

import contextlib
import functools
import inspect
from collections import defaultdict
from collections.abc import (
    Callable,
    Hashable,
    Iterable,
    Iterator,
    Mapping,
    Sequence,
)
from functools import cached_property
from pathlib import Path
from pprint import pformat
from threading import RLock
from typing import (
    TYPE_CHECKING,
    Any,
    Concatenate,
    Literal,
    TypedDict,
    cast,
    get_type_hints,
    overload,
)

import ruamel.yaml
from cachetools import Cache
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    PrivateAttr,
    field_validator,
)

from . import __version__, kdb
from .cell_metadata import (
    MetadataProviderKind,
    MetadataRegistry,
    _MetadataProviderRecord,
)
from .conf import CheckInstances, CheckUnnamedCells, config, logger
from .cross_section import (
    AsymmetricalCrossSection,
    AsymmetricCrossSection,
    CrossSection,
    CrossSectionLayer,
    CrossSectionModel,
    CrossSectionSpecDict,
    DAsymmetricalCrossSection,
    DAsymmetricCrossSection,
    DCrossSection,
    DCrossSectionLayer,
    DCrossSectionSpecDict,
    DSymmetricalCrossSection,
    SymmetricalCrossSection,
    TAsymmetricCrossSection,
    TCrossSection,
)
from .decorators import (
    Decorators,
    PortsDefinition,
    WrappedKCellFunc,
    WrappedVKCellFunc,
)
from .enclosure import (
    KCellEnclosure,
    LayerEnclosure,
    LayerEnclosureModel,
    LayerEnclosureSpec,
)
from .exceptions import FactoriesLockedError, MergeError
from .kcell import (
    AnyTKCell,
    BaseKCell,
    DKCell,
    DKCells,
    KCell,
    KCells,
    ProtoTKCell,
    TKCell,
    TVCell,
    VKCell,
    _check_duplicate_cell_names,
    show,
)
from .layer import LayerEnum, LayerInfos, LayerStack, layerenum_from_dict
from .merge import MergeDiff
from .pin import BasePin
from .port import BasePort, ProtoPort, rename_clockwise_multi
from .routing.generic import ManhattanRoute
from .serialization import get_function_name
from .settings import Info, KCellSettings
from .utilities import load_layout_options, save_layout_options

if TYPE_CHECKING:
    from .ports import DPorts, Ports
    from .schematic import TSchematic
    from .typings import (
        KCIN,
        VK,
        KCellParams,
        MetaData,
        T,
    )

kcl: KCLayout
kcls: dict[str, KCLayout] = {}

__all__ = ["KCLayout", "cell", "get_default_kcl", "kcl", "kcls", "vcell"]


class Constants(BaseModel):
    """Constant Model class."""

    model_config = ConfigDict(arbitrary_types_allowed=True)


def get_default_kcl() -> KCLayout:
    """Utility function to get the default kcl object."""
    return kcl


class Factories[F: WrappedKCellFunc[Any, Any] | WrappedVKCellFunc[Any, Any]](
    Mapping[str, F]
):
    _all: list[F]
    _by_name: dict[str, int]
    _by_tag: defaultdict[str, list[int]]
    _by_function: dict[Callable[..., Any], int]
    _locked: bool

    def __init__(self) -> None:
        self._all = []
        self._by_name = {}
        self._by_tag = defaultdict(list)
        self._by_function = {}
        self._locked = False

    @property
    def locked(self) -> bool:
        """Whether this collection rejects new factories via `add`."""
        return self._locked

    def lock(self) -> None:
        """Prevent further additions through `add`. This is irreversible."""
        self._locked = True

    def add(self, factory: F) -> None:
        if self._locked:
            raise FactoriesLockedError(
                f"Cannot add factory {factory.name!r}: this Factories collection is "
                "locked."
            )
        idx = len(self._all)
        self._all.append(factory)
        for tag in factory.tags:
            self._by_tag[tag].append(idx)
        self._by_name[factory.name] = idx
        self._by_function[factory.__call__] = idx

    def get_by_name(self, name: str) -> F:
        return self._all[self._by_name[name]]

    def is_unique(self) -> bool:
        return len(self._all) == len(self._by_name)

    def rebuild(self) -> None:
        self._by_name = {}
        self._by_tag = defaultdict(list)
        self._by_function = {}

        for idx, factory in enumerate(self._all):
            for tag in factory.tags:
                self._by_tag[tag].append(idx)
            self._by_name[factory.name] = idx
            self._by_function[factory.__call__] = idx

    def get_by_tag(self, tag: str) -> list[F]:
        return [self._all[idx] for idx in self._by_tag[tag]]

    def all(self) -> tuple[F, ...]:
        return tuple(self._all)

    def annotated(self) -> tuple[F, ...]:
        return tuple(factory for factory in self._all if factory.has_metadata())

    def get_all_by_name(self, name: str) -> tuple[F, ...]:
        return tuple(factory for factory in self._all if factory.name == name)

    def get_by_qualified_name(self, qualified_name: str) -> F | None:
        for factory in self._all:
            if factory.qualified_name == qualified_name:
                return factory
        return None

    def __iter__(self) -> Iterator[str]:
        return iter(self._by_name)

    def __len__(self) -> int:
        return len(self._by_name)

    def __contains__(self, key: Any) -> bool:
        if isinstance(key, str):
            return key in self._by_name
        return key in self._all

    def __getitem__(self, key: str) -> F:
        try:
            return self._all[self._by_name[key]]
        except KeyError as e:
            from rapidfuzz import process

            results = pformat(
                [
                    result[0]
                    for result in process.extract(
                        key, list(self._by_name.keys()), limit=10
                    )
                ]
            )

            raise KeyError(
                f"Unknown Factory {key!r}, closest 10 name matches: {results}"
            ) from e

    @overload
    def get(self, key: object, /) -> F | None: ...

    @overload
    def get(self, key: object, /, default: T) -> F | T: ...

    def get(self, key: object, /, default: T | None = None) -> F | T | None:
        if key in self._by_name:
            return self.get_by_name(cast("str", key))
        return default

    def get_by_path(self, path: str | Path) -> list[F]:
        p = Path(path).expanduser().resolve()
        return [factory for factory in self._all if p == factory.file]

    def as_dict(self) -> dict[str, F]:
        return {name: self._all[i] for name, i in self._by_name.items()}


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

    factories: Factories[WrappedKCellFunc[Any, ProtoTKCell[Any]]]
    virtual_factories: Factories[WrappedVKCellFunc[Any, VKCell]]
    generic_factories: dict[
        str, Callable[..., ProtoTKCell[Any]] | Callable[..., VKCell]
    ] = Field(default_factory=dict)
    tkcells: dict[int, TKCell] = Field(default_factory=dict)
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
    _future_cell_name: str | None = PrivateAttr(default=None)
    _metadata_registry: MetadataRegistry = PrivateAttr(
        default_factory=MetadataRegistry
    )

    decorators: Decorators
    default_cell_output_type: type[KCell | DKCell] = KCell
    default_vcell_output_type: type[VKCell] = VKCell

    connectivity: list[
        tuple[kdb.LayerInfo, kdb.LayerInfo]
        | tuple[kdb.LayerInfo, kdb.LayerInfo, kdb.LayerInfo]
    ]

    routing_strategies: dict[
        str,
        Callable[
            Concatenate[
                ProtoTKCell[Any],
                Sequence[Sequence[ProtoPort[Any]]],
                ...,
            ],
            list[ManhattanRoute],
        ],
    ] = Field(default_factory=dict)
    technology_file: Path | None = None

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
        connectivity: Sequence[
            tuple[kdb.LayerInfo, kdb.LayerInfo]
            | tuple[kdb.LayerInfo, kdb.LayerInfo, kdb.LayerInfo]
        ]
        | None = None,
        technology_file: Path | str | None = None,
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
        if technology_file:
            technology_file = Path(technology_file).resolve()
            if not technology_file.is_file():
                raise ValueError(
                    f"{technology_file=} is not an existing file."
                    " Make sure to link it to the .lyt file."
                )
        super().__init__(
            name=name,
            layer_enclosures=layer_enclosures,
            cross_sections=CrossSectionModel(kcl=self),
            enclosure=KCellEnclosure([]),
            infos=infos_,
            factories=Factories[WrappedKCellFunc[Any, ProtoTKCell[Any]]](),
            virtual_factories=Factories[WrappedVKCellFunc[Any, VKCell]](),
            sparameters_path=sparameters_path,
            interconnect_cml_path=interconnect_cml_path,
            constants=constants_,
            library=library,
            layer_stack=layer_stack,
            layout=layout,
            rename_function=port_rename_function,
            info=Info(**info) if info else Info(),
            settings=KCellSettings(
                version=__version__,
                klayout_version=kdb.__version__,  # ty:ignore[unresolved-attribute]
                meta_format="v3",
            ),
            decorators=Decorators(self),
            default_cell_output_type=default_cell_output_type,
            connectivity=connectivity or [],
            technology_file=technology_file,
        )

        self.library.register(self.name)
        # Materialize `layers` so LayerEnum.__init__ registers each layer's name
        # on `self.layout`; otherwise `find_layer(layer, datatype)` called
        # before any `kcl.layers` access would see an unnamed layer.
        _ = self.layers

        enclosure = KCellEnclosure(
            enclosures=[enc.model_copy() for enc in enclosure.enclosures.enclosures]
            if enclosure
            else []
        )
        self.sparameters_path = sparameters_path
        self.enclosure = enclosure
        self.interconnect_cml_path = interconnect_cml_path

        kcls[self.name] = self

    @field_validator("infos", mode="before")
    @classmethod
    def _validate_infos(cls, value: Any) -> LayerInfos:
        if value is None:
            return LayerInfos()
        if isinstance(value, type) and issubclass(value, LayerInfos):
            return value()
        return value

    @cached_property
    def layers(self) -> type[LayerEnum]:
        """LayerEnum derived from `infos`. Cached; invalidated when `infos` is set."""
        return layerenum_from_dict(layers=self.infos, layout=self.library.layout())

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

    @property
    def factories_locked(self) -> bool:
        """Whether both the real and virtual factory collections are locked."""
        return self.factories.locked and self.virtual_factories.locked

    def lock_factories(self) -> None:
        """Prevent further factories (real and virtual) from being registered.

        This is irreversible: once locked, a `KCLayout` will reject any new
        factory registrations (e.g. via `@kcl.cell` / `@kcl.vcell` or direct
        `factories.add` calls). Use this to seal a PDK after registering all
        of its pcell functions.
        """
        self.factories.lock()
        self.virtual_factories.lock()

    def metadata_for(
        self,
        target: str | WrappedKCellFunc[Any, Any] | WrappedVKCellFunc[Any, Any],
        provider: Callable[..., Any] | None = None,
        *,
        replace: bool = False,
    ) -> Callable[..., Any]:
        """Register a full metadata provider for a cell factory.

        The provider should return a ``CellMetadata`` or a dict with any
        subset of its fields. Use the field-specific decorators
        (``device_type_for``, ``ports_for``, etc.) when only one aspect
        is being provided.
        """
        return self._register_metadata_provider(
            "metadata", target, provider, replace=replace
        )

    def model_for(
        self,
        target: str | WrappedKCellFunc[Any, Any] | WrappedVKCellFunc[Any, Any],
        provider: Callable[..., Any] | None = None,
        *,
        position: Literal["append", "prepend"] = "append",
    ) -> Callable[..., Any]:
        """Register a model provider for a cell factory.

        Multiple model providers are concatenated. Use
        ``position="prepend"`` to insert before existing models.
        """
        return self._register_metadata_provider(
            "model", target, provider, position=position
        )

    def device_type_for(
        self,
        target: str | WrappedKCellFunc[Any, Any] | WrappedVKCellFunc[Any, Any],
        provider: Callable[..., Any] | None = None,
        *,
        replace: bool = False,
    ) -> Callable[..., Any]:
        """Register a device-type provider for a cell factory."""
        return self._register_metadata_provider(
            "device_type", target, provider, replace=replace
        )

    def ports_for(
        self,
        target: str | WrappedKCellFunc[Any, Any] | WrappedVKCellFunc[Any, Any],
        provider: Callable[..., Any] | None = None,
        *,
        replace: bool = False,
    ) -> Callable[..., Any]:
        """Register a port-spec provider for a cell factory.

        The provider should return a list of ``PortSpec`` dicts. Port
        providers can be parametric — they may accept any subset of the
        cell factory's parameters.
        """
        return self._register_metadata_provider(
            "ports", target, provider, replace=replace
        )

    def tags_for(
        self,
        target: str | WrappedKCellFunc[Any, Any] | WrappedVKCellFunc[Any, Any],
        provider: Callable[..., Any] | None = None,
    ) -> Callable[..., Any]:
        """Register a tags provider for a cell factory."""
        return self._register_metadata_provider("tags", target, provider)

    def display_for(
        self,
        target: str | WrappedKCellFunc[Any, Any] | WrappedVKCellFunc[Any, Any],
        provider: Callable[..., Any] | None = None,
        *,
        replace: bool = False,
    ) -> Callable[..., Any]:
        """Register a display-hint provider for a cell factory."""
        return self._register_metadata_provider(
            "display", target, provider, replace=replace
        )

    def info_for(
        self,
        target: str | WrappedKCellFunc[Any, Any] | WrappedVKCellFunc[Any, Any],
        provider: Callable[..., Any] | None = None,
    ) -> Callable[..., Any]:
        """Register a free-form info provider for a cell factory."""
        return self._register_metadata_provider("info", target, provider)

    def schematic_for(
        self,
        target: str | WrappedKCellFunc[Any, Any],
        provider: Callable[..., Any] | None = None,
    ) -> Callable[..., Any]:
        """Attach a schematic function to a cell factory after registration."""
        factory = self._resolve_kcell_factory(target)

        def register(f: Callable[..., Any]) -> Callable[..., Any]:
            factory._f_schematic = f
            return f

        if provider is None:
            return register
        return register(provider)

    def _resolve_kcell_factory(
        self, target: str | WrappedKCellFunc[Any, Any]
    ) -> WrappedKCellFunc[Any, Any]:
        if not isinstance(target, str):
            if target in self.factories:
                return target
            raise KeyError(f"Unknown factory target {target!r}.")

        if "." in target:
            factory = self.factories.get_by_qualified_name(target)
            if factory is None:
                raise KeyError(f"Unknown factory FQN {target!r}.")
            return factory

        matches = self.factories.get_all_by_name(target)
        if not matches:
            raise KeyError(f"Unknown factory name {target!r}.")
        if len(matches) > 1:
            raise ValueError(
                f"Ambiguous factory name {target!r}; use a fully-qualified name."
            )
        return matches[0]

    def metadata_providers_for(
        self, factory: WrappedKCellFunc[Any, Any] | WrappedVKCellFunc[Any, Any]
    ) -> tuple[_MetadataProviderRecord, ...]:
        """Return all metadata provider records registered for a factory."""
        return self._metadata_registry.providers_for(
            name=factory.name, qualified_name=factory.qualified_name, obj=factory
        )

    def _register_metadata_provider(
        self,
        kind: MetadataProviderKind,
        target: str | WrappedKCellFunc[Any, Any] | WrappedVKCellFunc[Any, Any],
        provider: Callable[..., Any] | None = None,
        *,
        replace: bool = False,
        position: Literal["append", "prepend"] = "append",
    ) -> Callable[..., Any]:
        target_kind, target_key = self._metadata_target_key(target)

        def register(f: Callable[..., Any]) -> Callable[..., Any]:
            self._metadata_registry.add(
                target_kind=target_kind,
                target_key=target_key,
                kind=kind,
                provider=f,
                replace=replace,
                position=position,
            )
            return f

        if provider is None:
            return register
        return register(provider)

    def _metadata_target_key(
        self, target: str | WrappedKCellFunc[Any, Any] | WrappedVKCellFunc[Any, Any]
    ) -> tuple[Literal["name", "fqn", "object"], str | int]:
        if isinstance(target, str):
            if "." in target:
                factory = self.factories.get_by_qualified_name(target)
                virtual_factory = self.virtual_factories.get_by_qualified_name(target)
                matches = [f for f in (factory, virtual_factory) if f is not None]
                if not matches:
                    raise KeyError(f"Unknown factory FQN {target!r}.")
                if len(matches) > 1:
                    raise ValueError(f"Ambiguous factory FQN {target!r}.")
                return "fqn", target

            matches = [
                *self.factories.get_all_by_name(target),
                *self.virtual_factories.get_all_by_name(target),
            ]
            if not matches:
                raise KeyError(f"Unknown factory name {target!r}.")
            if len(matches) > 1:
                raise ValueError(
                    f"Ambiguous factory name {target!r}; use a fully-qualified name."
                )
            return "name", target

        if target in self.factories or target in self.virtual_factories:
            return "object", id(target)
        raise KeyError(f"Unknown factory target {target!r}.")

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
        if name is None and main_layer is not None and main_layer.name != "":
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

    @cached_property
    def technology(self) -> kdb.Technology:
        if self.technology_file is not None:
            tech = kdb.Technology()
            tech.load(str(self.technology_file))
            kdb.Technology.register_technology(tech)
            return tech
        raise ValueError(f"{self.technology_file} is not a file or is None.")

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
            return self.layers[info.name]
        except KeyError as e:
            if allow_undefined_layers:
                return self.layout.layer(info)
            raise KeyError(
                f"Layer '{args=}, {kwargs=}' has not been defined in the KCLayout. "
                "Have you defined the layer and set it in KCLayout.info?"
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
    def schematic_cell[**KCellParams](
        self,
        _func: Callable[KCellParams, TSchematic[Any]],
        /,
    ) -> Callable[KCellParams, KCell]: ...

    @overload
    def schematic_cell[**KCellParams](
        self,
        /,
        *,
        set_settings: bool = ...,
        set_name: bool = ...,
        check_ports: bool = ...,
        check_pins: bool = ...,
        check_instances: CheckInstances | None = ...,
        snap_ports: bool = ...,
        add_port_layers: bool = ...,
        cache: Cache[Hashable, Any] | dict[Hashable, Any] | None = ...,
        basename: str | None = ...,
        drop_params: list[str] = ...,
        register_factory: bool = ...,
        overwrite_existing: bool | None = ...,
        layout_cache: bool | None = ...,
        info: dict[str, MetaData] | None = ...,
        debug_names: bool | None = ...,
        tags: list[str] | None = ...,
        factories: Mapping[
            str, Callable[..., KCell] | Callable[..., DKCell] | Callable[..., VKCell]
        ]
        | None = None,
        cross_sections: Mapping[str, CrossSection | DCrossSection] | None = None,
        routing_strategies: dict[
            str,
            Callable[
                Concatenate[
                    ProtoTKCell[Any],
                    Sequence[ProtoPort[Any]],
                    Sequence[ProtoPort[Any]],
                    ...,
                ],
                Any,
            ],
        ]
        | None = None,
    ) -> Callable[
        [Callable[KCellParams, TSchematic[Any]]], Callable[KCellParams, KCell]
    ]: ...

    @overload
    def schematic_cell[**KCellParams](
        self,
        /,
        *,
        set_settings: bool = ...,
        set_name: bool = ...,
        check_ports: bool = ...,
        check_pins: bool = ...,
        check_instances: CheckInstances | None = ...,
        snap_ports: bool = ...,
        add_port_layers: bool = ...,
        cache: Cache[Hashable, Any] | dict[Hashable, Any] | None = ...,
        basename: str | None = ...,
        drop_params: list[str] = ...,
        register_factory: bool = ...,
        overwrite_existing: bool | None = ...,
        layout_cache: bool | None = ...,
        info: dict[str, MetaData] | None = ...,
        post_process: Iterable[Callable[[KCell], None]],
        debug_names: bool | None = ...,
        tags: list[str] | None = ...,
        factories: Mapping[
            str, Callable[..., KCell] | Callable[..., DKCell] | Callable[..., VKCell]
        ]
        | None = None,
        cross_sections: Mapping[str, CrossSection | DCrossSection] | None = None,
        routing_strategies: dict[
            str,
            Callable[
                Concatenate[
                    ProtoTKCell[Any],
                    Sequence[ProtoPort[Any]],
                    Sequence[ProtoPort[Any]],
                    ...,
                ],
                Any,
            ],
        ]
        | None = None,
    ) -> Callable[
        [Callable[KCellParams, TSchematic[Any]]], Callable[KCellParams, KCell]
    ]: ...

    @overload
    def schematic_cell[**KCellParams, KC: ProtoTKCell[Any]](
        self,
        /,
        *,
        output_type: type[KC],
        set_settings: bool = ...,
        set_name: bool = ...,
        check_ports: bool = ...,
        check_pins: bool = ...,
        check_instances: CheckInstances | None = ...,
        snap_ports: bool = ...,
        add_port_layers: bool = ...,
        cache: Cache[Hashable, Any] | dict[Hashable, Any] | None = ...,
        basename: str | None = ...,
        drop_params: list[str] = ...,
        register_factory: bool = ...,
        overwrite_existing: bool | None = ...,
        layout_cache: bool | None = ...,
        info: dict[str, MetaData] | None = ...,
        post_process: Iterable[Callable[[KC], None]],
        debug_names: bool | None = ...,
        tags: list[str] | None = ...,
        factories: Mapping[
            str, Callable[..., KCell] | Callable[..., DKCell] | Callable[..., VKCell]
        ]
        | None = None,
        cross_sections: Mapping[str, CrossSection | DCrossSection] | None = None,
        routing_strategies: dict[
            str,
            Callable[
                Concatenate[
                    ProtoTKCell[Any],
                    Sequence[ProtoPort[Any]],
                    Sequence[ProtoPort[Any]],
                    ...,
                ],
                Any,
            ],
        ]
        | None = None,
    ) -> Callable[
        [Callable[KCellParams, TSchematic[Any]]], Callable[KCellParams, KC]
    ]: ...

    @overload
    def schematic_cell[**KCellParams, KC: ProtoTKCell[Any]](
        self,
        /,
        *,
        output_type: type[KC],
        set_settings: bool = ...,
        set_name: bool = ...,
        check_ports: bool = ...,
        check_pins: bool = ...,
        check_instances: CheckInstances | None = ...,
        snap_ports: bool = ...,
        add_port_layers: bool = ...,
        cache: Cache[Hashable, Any] | dict[Hashable, Any] | None = ...,
        basename: str | None = ...,
        drop_params: list[str] = ...,
        register_factory: bool = ...,
        overwrite_existing: bool | None = ...,
        layout_cache: bool | None = ...,
        info: dict[str, MetaData] | None = ...,
        debug_names: bool | None = ...,
        tags: list[str] | None = ...,
        factories: Mapping[
            str, Callable[..., KCell] | Callable[..., DKCell] | Callable[..., VKCell]
        ]
        | None = None,
        cross_sections: Mapping[str, CrossSection | DCrossSection] | None = None,
        routing_strategies: dict[
            str,
            Callable[
                Concatenate[
                    ProtoTKCell[Any],
                    Sequence[ProtoPort[Any]],
                    Sequence[ProtoPort[Any]],
                    ...,
                ],
                Any,
            ],
        ]
        | None = None,
    ) -> Callable[
        [Callable[KCellParams, TSchematic[Any]]], Callable[KCellParams, KC]
    ]: ...

    def schematic_cell[**KCellParams, KC: ProtoTKCell[Any]](
        self,
        _func: Callable[KCellParams, TSchematic[Any]] | None = None,
        /,
        *,
        output_type: type[KC] | None = None,
        set_settings: bool = True,
        set_name: bool = True,
        check_ports: bool = True,
        check_pins: bool = True,
        check_instances: CheckInstances | None = None,
        snap_ports: bool = True,
        add_port_layers: bool = True,
        cache: Cache[Hashable, Any] | dict[Hashable, Any] | None = None,
        basename: str | None = None,
        drop_params: Sequence[str] = ("self", "cls"),
        register_factory: bool = True,
        overwrite_existing: bool | None = None,
        layout_cache: bool | None = None,
        info: dict[str, MetaData] | None = None,
        post_process: Iterable[Callable[[KC], None]] | None = None,
        debug_names: bool | None = None,
        tags: list[str] | None = None,
        factories: Mapping[
            str, Callable[..., KCell] | Callable[..., DKCell] | Callable[..., VKCell]
        ]
        | None = None,
        cross_sections: Mapping[str, CrossSection | DCrossSection] | None = None,
        routing_strategies: dict[
            str,
            Callable[
                Concatenate[
                    ProtoTKCell[Any],
                    Sequence[Sequence[ProtoPort[Any]]],
                    ...,
                ],
                Any,
            ],
        ]
        | None = None,
    ) -> (
        Callable[KCellParams, KCell]
        | Callable[
            [Callable[KCellParams, TSchematic[Any]]],
            Callable[KCellParams, KC],
        ]
        | Callable[
            [Callable[KCellParams, TSchematic[Any]]],
            Callable[KCellParams, KCell],
        ]
    ):
        if _func is None:
            if output_type is None:

                def wrap_f(
                    f: Callable[KCellParams, TSchematic[Any]],
                ) -> Callable[KCellParams, KCell]:
                    @self.cell(
                        output_type=KCell,
                        set_settings=set_settings,
                        set_name=set_name,
                        check_ports=check_ports,
                        check_pins=check_pins,
                        check_instances=check_instances,
                        snap_ports=snap_ports,
                        add_port_layers=add_port_layers,
                        cache=cache,
                        basename=basename,
                        drop_params=list(drop_params),
                        register_factory=register_factory,
                        overwrite_existing=overwrite_existing,
                        layout_cache=layout_cache,
                        info=info,
                        post_process=cast(
                            "Iterable[Callable[[KCell], None]]", post_process or []
                        ),
                        debug_names=debug_names,
                        tags=tags,
                        schematic_function=f,
                    )
                    @functools.wraps(f)
                    def kcell_func(
                        *args: KCellParams.args, **kwargs: KCellParams.kwargs
                    ) -> KCell:
                        schematic = f(*args, **kwargs)
                        if set_name:
                            schematic.name = self._future_cell_name
                        c_ = schematic.create_cell(
                            KCell,
                            factories=factories,
                            cross_sections=cross_sections,
                            routing_strategies=routing_strategies,
                        )
                        c_.schematic = schematic
                        return c_

                    return kcell_func

                return wrap_f

            post_process = cast("Iterable[Callable[[KC], None]]", post_process or [])

            def custom_wrap_f(
                f: Callable[KCellParams, TSchematic[Any]],
            ) -> Callable[KCellParams, KC]:
                @self.cell(
                    output_type=output_type,
                    set_settings=set_settings,
                    set_name=set_name,
                    check_ports=check_ports,
                    check_pins=check_pins,
                    check_instances=check_instances,
                    snap_ports=snap_ports,
                    add_port_layers=add_port_layers,
                    cache=cache,
                    basename=basename,
                    drop_params=list(drop_params),
                    register_factory=register_factory,
                    overwrite_existing=overwrite_existing,
                    layout_cache=layout_cache,
                    info=info,
                    post_process=post_process,
                    debug_names=debug_names,
                    tags=tags,
                    schematic_function=f,
                )
                @functools.wraps(f)
                def custom_kcell_func(
                    *args: KCellParams.args, **kwargs: KCellParams.kwargs
                ) -> KCell:
                    schematic = f(*args, **kwargs)
                    if set_name:
                        schematic.name = self._future_cell_name
                    c_ = schematic.create_cell(
                        KCell,
                        factories=factories,
                        cross_sections=cross_sections,
                        routing_strategies=routing_strategies,
                    )
                    c_.schematic = schematic
                    return c_

                return custom_kcell_func

            return custom_wrap_f

        def simple_wrap_f(
            f: Callable[KCellParams, TSchematic[Any]],
        ) -> Callable[KCellParams, KCell]:
            @self.cell(output_type=KCell, schematic_function=f)
            @functools.wraps(f)
            def kcell_func(
                *args: KCellParams.args, **kwargs: KCellParams.kwargs
            ) -> KCell:
                schematic = f(*args, **kwargs)
                if set_name:
                    schematic.name = self._future_cell_name
                c_ = schematic.create_cell(
                    KCell,
                    factories=factories,
                    cross_sections=cross_sections,
                    routing_strategies=routing_strategies,
                )
                c_.schematic = schematic
                return c_

            return kcell_func

        return simple_wrap_f(_func)

    @overload
    def cell[**KCellParams, KC: ProtoTKCell[Any]](
        self,
        _func: Callable[KCellParams, KC],
        /,
    ) -> Callable[KCellParams, KC]: ...

    @overload
    def cell[**KCellParams, KC: ProtoTKCell[Any]](
        self,
        /,
        *,
        set_settings: bool = ...,
        set_name: bool = ...,
        check_ports: bool = ...,
        check_pins: bool = ...,
        check_instances: CheckInstances | None = ...,
        check_unnamed_cells: CheckUnnamedCells = ...,
        snap_ports: bool = ...,
        add_port_layers: bool = ...,
        cache: Cache[Hashable, Any] | dict[Hashable, Any] | None = ...,
        basename: str | None = ...,
        drop_params: list[str] = ...,
        register_factory: bool = ...,
        overwrite_existing: bool | None = ...,
        layout_cache: bool | None = ...,
        info: dict[str, MetaData] | None = ...,
        debug_names: bool | None = ...,
        tags: list[str] | None = ...,
        lvs_equivalent_ports: list[list[str]] | None = None,
        ports: PortsDefinition | None = None,
        schematic_function: Callable[KCellParams, TSchematic[Any]],
    ) -> Callable[[Callable[KCellParams, KC]], Callable[KCellParams, KC]]: ...

    @overload
    def cell[**KCellParams, KC: ProtoTKCell[Any]](
        self,
        /,
        *,
        set_settings: bool = ...,
        set_name: bool = ...,
        check_ports: bool = ...,
        check_pins: bool = ...,
        check_instances: CheckInstances | None = ...,
        check_unnamed_cells: CheckUnnamedCells = ...,
        snap_ports: bool = ...,
        add_port_layers: bool = ...,
        cache: Cache[Hashable, Any] | dict[Hashable, Any] | None = ...,
        basename: str | None = ...,
        drop_params: list[str] = ...,
        register_factory: bool = ...,
        overwrite_existing: bool | None = ...,
        layout_cache: bool | None = ...,
        info: dict[str, MetaData] | None = ...,
        debug_names: bool | None = ...,
        tags: list[str] | None = ...,
        lvs_equivalent_ports: list[list[str]] | None = None,
        ports: PortsDefinition | None = None,
        schematic_function: None = None,
    ) -> Callable[[Callable[KCellParams, KC]], Callable[KCellParams, KC]]: ...

    @overload
    def cell[**KCellParams, KC: ProtoTKCell[Any]](
        self,
        /,
        *,
        set_settings: bool = ...,
        set_name: bool = ...,
        check_ports: bool = ...,
        check_pins: bool = ...,
        check_instances: CheckInstances | None = ...,
        check_unnamed_cells: CheckUnnamedCells = ...,
        snap_ports: bool = ...,
        add_port_layers: bool = ...,
        cache: Cache[Hashable, Any] | dict[Hashable, Any] | None = ...,
        basename: str | None = ...,
        drop_params: list[str] = ...,
        register_factory: bool = ...,
        overwrite_existing: bool | None = ...,
        layout_cache: bool | None = ...,
        info: dict[str, MetaData] | None = ...,
        post_process: Iterable[Callable[[KC], None]],
        debug_names: bool | None = ...,
        tags: list[str] | None = ...,
        lvs_equivalent_ports: list[list[str]] | None = None,
        ports: PortsDefinition | None = None,
        schematic_function: Callable[KCellParams, TSchematic[Any]],
    ) -> Callable[[Callable[KCellParams, KC]], Callable[KCellParams, KC]]: ...

    @overload
    def cell[**KCellParams, KC: ProtoTKCell[Any]](
        self,
        /,
        *,
        set_settings: bool = ...,
        set_name: bool = ...,
        check_ports: bool = ...,
        check_pins: bool = ...,
        check_instances: CheckInstances | None = ...,
        check_unnamed_cells: CheckUnnamedCells = ...,
        snap_ports: bool = ...,
        add_port_layers: bool = ...,
        cache: Cache[Hashable, Any] | dict[Hashable, Any] | None = ...,
        basename: str | None = ...,
        drop_params: list[str] = ...,
        register_factory: bool = ...,
        overwrite_existing: bool | None = ...,
        layout_cache: bool | None = ...,
        info: dict[str, MetaData] | None = ...,
        post_process: Iterable[Callable[[KC], None]],
        debug_names: bool | None = ...,
        tags: list[str] | None = ...,
        lvs_equivalent_ports: list[list[str]] | None = None,
        ports: PortsDefinition | None = None,
        schematic_function: None = None,
    ) -> Callable[[Callable[KCellParams, KC]], Callable[KCellParams, KC]]: ...

    @overload
    def cell[**KCellParams, KC: ProtoTKCell[Any]](
        self,
        /,
        *,
        output_type: type[KC],
        set_settings: bool = ...,
        set_name: bool = ...,
        check_ports: bool = ...,
        check_pins: bool = ...,
        check_instances: CheckInstances | None = ...,
        check_unnamed_cells: CheckUnnamedCells = ...,
        snap_ports: bool = ...,
        add_port_layers: bool = ...,
        cache: Cache[Hashable, Any] | dict[Hashable, Any] | None = ...,
        basename: str | None = ...,
        drop_params: list[str] = ...,
        register_factory: bool = ...,
        overwrite_existing: bool | None = ...,
        layout_cache: bool | None = ...,
        info: dict[str, MetaData] | None = ...,
        post_process: Iterable[Callable[[KC], None]],
        debug_names: bool | None = ...,
        tags: list[str] | None = ...,
        lvs_equivalent_ports: list[list[str]] | None = None,
        ports: PortsDefinition | None = None,
        schematic_function: Callable[KCellParams, TSchematic[Any]],
    ) -> Callable[
        [Callable[KCellParams, ProtoTKCell[Any]]], Callable[KCellParams, KC]
    ]: ...

    @overload
    def cell[**KCellParams, KC: ProtoTKCell[Any]](
        self,
        /,
        *,
        output_type: type[KC],
        set_settings: bool = ...,
        set_name: bool = ...,
        check_ports: bool = ...,
        check_pins: bool = ...,
        check_instances: CheckInstances | None = ...,
        check_unnamed_cells: CheckUnnamedCells = ...,
        snap_ports: bool = ...,
        add_port_layers: bool = ...,
        cache: Cache[Hashable, Any] | dict[Hashable, Any] | None = ...,
        basename: str | None = ...,
        drop_params: list[str] = ...,
        register_factory: bool = ...,
        overwrite_existing: bool | None = ...,
        layout_cache: bool | None = ...,
        info: dict[str, MetaData] | None = ...,
        post_process: Iterable[Callable[[KC], None]],
        debug_names: bool | None = ...,
        tags: list[str] | None = ...,
        lvs_equivalent_ports: list[list[str]] | None = None,
        ports: PortsDefinition | None = None,
        schematic_function: None = None,
    ) -> Callable[
        [Callable[KCellParams, ProtoTKCell[Any]]], Callable[KCellParams, KC]
    ]: ...

    @overload
    def cell[**KCellParams, KC: ProtoTKCell[Any]](
        self,
        /,
        *,
        output_type: type[KC],
        set_settings: bool = ...,
        set_name: bool = ...,
        check_ports: bool = ...,
        check_pins: bool = ...,
        check_instances: CheckInstances | None = ...,
        check_unnamed_cells: CheckUnnamedCells = ...,
        snap_ports: bool = ...,
        add_port_layers: bool = ...,
        cache: Cache[Hashable, Any] | dict[Hashable, Any] | None = ...,
        basename: str | None = ...,
        drop_params: list[str] = ...,
        register_factory: bool = ...,
        overwrite_existing: bool | None = ...,
        layout_cache: bool | None = ...,
        info: dict[str, MetaData] | None = ...,
        debug_names: bool | None = ...,
        tags: list[str] | None = ...,
        lvs_equivalent_ports: list[list[str]] | None = None,
        ports: PortsDefinition | None = None,
        schematic_function: Callable[KCellParams, TSchematic[Any]],
    ) -> Callable[
        [Callable[KCellParams, ProtoTKCell[Any]]], Callable[KCellParams, KC]
    ]: ...

    @overload
    def cell[**KCellParams, KC: ProtoTKCell[Any]](
        self,
        /,
        *,
        output_type: type[KC],
        set_settings: bool = ...,
        set_name: bool = ...,
        check_ports: bool = ...,
        check_pins: bool = ...,
        check_instances: CheckInstances | None = ...,
        check_unnamed_cells: CheckUnnamedCells = ...,
        snap_ports: bool = ...,
        add_port_layers: bool = ...,
        cache: Cache[Hashable, Any] | dict[Hashable, Any] | None = ...,
        basename: str | None = ...,
        drop_params: list[str] = ...,
        register_factory: bool = ...,
        overwrite_existing: bool | None = ...,
        layout_cache: bool | None = ...,
        info: dict[str, MetaData] | None = ...,
        debug_names: bool | None = ...,
        tags: list[str] | None = ...,
        lvs_equivalent_ports: list[list[str]] | None = None,
        ports: PortsDefinition | None = None,
        schematic_function: None = None,
    ) -> Callable[
        [Callable[KCellParams, ProtoTKCell[Any]]], Callable[KCellParams, KC]
    ]: ...

    def cell[**KCellParams, KC: ProtoTKCell[Any]](
        self,
        _func: Callable[KCellParams, ProtoTKCell[Any]] | None = None,
        /,
        *,
        output_type: type[KC] | None = None,
        set_settings: bool = True,
        set_name: bool = True,
        check_ports: bool = True,
        check_pins: bool = True,
        check_instances: CheckInstances | None = None,
        check_unnamed_cells: CheckUnnamedCells | None = None,
        snap_ports: bool = True,
        add_port_layers: bool = True,
        cache: Cache[Hashable, Any] | dict[Hashable, Any] | None = None,
        basename: str | None = None,
        drop_params: Sequence[str] = ("self", "cls"),
        register_factory: bool = True,
        overwrite_existing: bool | None = None,
        layout_cache: bool | None = None,
        info: dict[str, MetaData] | None = None,
        post_process: Iterable[Callable[[KC], None]] | None = None,
        debug_names: bool | None = None,
        tags: list[str] | None = None,
        lvs_equivalent_ports: list[list[str]] | None = None,
        ports: PortsDefinition | None = None,
        schematic_function: Callable[KCellParams, TSchematic[Any]] | None = None,
    ) -> (
        Callable[KCellParams, KC]
        | Callable[
            [Callable[KCellParams, ProtoTKCell[Any]]],
            Callable[KCellParams, KC],
        ]
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
            check_pins: Check uniqueness of pin names.
            check_instances: Check for any complex instances. A complex instance is a an
                instance that has a magnification != 1 or non-90° rotation.
                Depending on the setting, an error is raised, the cell is flattened,
                a VInstance is created instead of a regular instance, or they are
                ignored.
            check_unnamed_cells: Check for unnamed child cells (matching
                ``Unnamed_\\d+``). ``"error"`` raises, ``"warning"`` logs a warning,
                ``"ignore"`` skips the check.
            snap_ports: Snap the centers of the ports onto the grid
                (only x/y, not angle).
            add_port_layers: Add special layers of `KCLayout.netlist_layer_mapping`
                to the ports if the port layer is in the mapping.
            cache: Provide a user defined cache instead of an internal one. This
                can be used for example to clear the cache.
                expensive if the cell is called often).
            basename: Overwrite the name normally inferred from the function or class
                name.
            drop_params: Drop these parameters before writing the
                [settings][kfactory.kcell.KCell.settings]
            register_factory: Register the resulting KCell-function to the
                `KCLayout.factories`
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
            tags: Tag cell functions with user defined tags.
        Returns:
            A wrapped cell function which caches responses and modifies the cell
            according to settings.
        """
        if check_instances is None:
            check_instances = config.check_instances
        if check_unnamed_cells is None:
            check_unnamed_cells = config.check_unnamed_cells
        if overwrite_existing is None:
            overwrite_existing = config.cell_overwrite_existing
        if layout_cache is None:
            layout_cache = config.cell_layout_cache
        if debug_names is None:
            debug_names = config.debug_names
        if post_process is None:
            post_process = []

        def decorator_autocell(
            f: Callable[KCellParams, KCIN],
        ) -> Callable[KCellParams, KC]:
            sig = inspect.signature(f)
            if output_type is not None:
                output_cell_type_: type[KC | ProtoTKCell[Any]] = output_type
            elif sig.return_annotation is not inspect.Signature.empty:
                # Use get_type_hints to resolve string annotations
                try:
                    type_hints = get_type_hints(f, globalns=f.__globals__)  # ty:ignore[unresolved-attribute]
                    output_cell_type_ = type_hints.get("return", sig.return_annotation)

                except Exception:
                    # Fallback to raw annotation if get_type_hints fails
                    logger.opt(depth=2).warning(
                        "Cannot determine output type ((D)KCell type)"
                        f"from annotation {sig.return_annotation!r}. "
                        "Trying to continue but likely this will fail.",
                    )
                    output_cell_type_ = sig.return_annotation
            else:
                output_cell_type_ = self.default_cell_output_type

            output_cell_type__ = cast("type[KC]", output_cell_type_)

            cache_: Cache[Hashable, Any] | dict[Hashable, Any] = cache or Cache(
                maxsize=float("inf")
            )
            wrapper_autocell: WrappedKCellFunc[KCellParams, KC] = WrappedKCellFunc[
                KCellParams, KC
            ](
                kcl=self,
                f=f,
                sig=sig,
                output_type=output_cell_type__,
                cache=cache_,
                set_settings=set_settings,
                set_name=set_name,
                check_ports=check_ports,
                check_pins=check_pins,
                check_instances=check_instances,
                check_unnamed_cells=check_unnamed_cells,
                snap_ports=snap_ports,
                add_port_layers=add_port_layers,
                basename=basename,
                drop_params=drop_params,
                overwrite_existing=overwrite_existing,
                layout_cache=layout_cache,
                info=info,
                post_process=post_process,  # ty:ignore[invalid-argument-type]
                debug_names=debug_names,
                tags=tags,
                lvs_equivalent_ports=lvs_equivalent_ports,
                ports=ports,
                schematic_function=schematic_function,
            )

            if register_factory:
                with self.thread_lock:
                    if wrapper_autocell.name is None:
                        raise ValueError(f"Function {f} has no name.")
                    self.factories.add(wrapper_autocell)

            @functools.wraps(f)
            def func(*args: KCellParams.args, **kwargs: KCellParams.kwargs) -> KC:
                return wrapper_autocell(*args, **kwargs)

            return func

        return decorator_autocell if _func is None else decorator_autocell(_func)

    @overload
    def vcell[**KCellParams, VK: VKCell](
        self,
        _func: Callable[KCellParams, VK],
        /,
    ) -> Callable[KCellParams, VK]: ...

    @overload
    def vcell[**KCellParams, VK: VKCell](
        self,
        /,
        *,
        set_settings: bool = True,
        set_name: bool = True,
        add_port_layers: bool = True,
        cache: Cache[Hashable, Any] | dict[Hashable, Any] | None = None,
        basename: str | None = None,
        drop_params: Sequence[str] = ("self", "cls"),
        register_factory: bool = True,
        info: dict[str, MetaData] | None = None,
        check_ports: bool = True,
        check_pins: bool = True,
        check_unnamed_cells: CheckUnnamedCells = ...,
        tags: list[str] | None = None,
        lvs_equivalent_ports: list[list[str]] | None = None,
        ports: PortsDefinition | None = None,
    ) -> Callable[[Callable[KCellParams, VK]], Callable[KCellParams, VK]]: ...

    @overload
    def vcell[**KCellParams, VK: VKCell](
        self,
        /,
        *,
        set_settings: bool = True,
        set_name: bool = True,
        add_port_layers: bool = True,
        cache: Cache[Hashable, Any] | dict[Hashable, Any] | None = None,
        basename: str | None = None,
        drop_params: Sequence[str] = ("self", "cls"),
        register_factory: bool = True,
        post_process: Iterable[Callable[[VKCell], None]],
        info: dict[str, MetaData] | None = None,
        check_ports: bool = True,
        check_pins: bool = True,
        check_unnamed_cells: CheckUnnamedCells = ...,
        tags: list[str] | None = None,
        lvs_equivalent_ports: list[list[str]] | None = None,
        ports: PortsDefinition | None = None,
    ) -> Callable[[Callable[KCellParams, VK]], Callable[KCellParams, VK]]: ...

    @overload
    def vcell[**KCellParams, VK: VKCell](
        self,
        /,
        *,
        output_type: type[VK],
        set_settings: bool = True,
        set_name: bool = True,
        add_port_layers: bool = True,
        cache: Cache[Hashable, Any] | dict[Hashable, Any] | None = None,
        basename: str | None = None,
        drop_params: Sequence[str] = ("self", "cls"),
        register_factory: bool = True,
        info: dict[str, MetaData] | None = None,
        check_ports: bool = True,
        check_pins: bool = True,
        check_unnamed_cells: CheckUnnamedCells = ...,
        tags: list[str] | None = None,
        lvs_equivalent_ports: list[list[str]] | None = None,
        ports: PortsDefinition | None = None,
    ) -> Callable[[Callable[KCellParams, VKCell]], Callable[KCellParams, VK]]: ...

    @overload
    def vcell[**KCellParams, VK: VKCell](
        self,
        /,
        *,
        output_type: type[VK],
        set_settings: bool = True,
        set_name: bool = True,
        add_port_layers: bool = True,
        cache: Cache[Hashable, Any] | dict[Hashable, Any] | None = None,
        basename: str | None = None,
        drop_params: Sequence[str] = ("self", "cls"),
        register_factory: bool = True,
        post_process: Iterable[Callable[[VKCell], None]],
        info: dict[str, MetaData] | None = None,
        check_ports: bool = True,
        check_pins: bool = True,
        check_unnamed_cells: CheckUnnamedCells = ...,
        tags: list[str] | None = None,
        lvs_equivalent_ports: list[list[str]] | None = None,
        ports: PortsDefinition | None = None,
    ) -> Callable[[Callable[KCellParams, VKCell]], Callable[KCellParams, VK]]: ...

    def vcell[**KCellParams, VK: VKCell](
        self,
        _func: Callable[KCellParams, VKCell] | None = None,
        /,
        *,
        output_type: type[VK] | None = None,
        set_settings: bool = True,
        set_name: bool = True,
        add_port_layers: bool = True,
        cache: Cache[Hashable, Any] | dict[Hashable, Any] | None = None,
        basename: str | None = None,
        drop_params: Sequence[str] = ("self", "cls"),
        register_factory: bool = True,
        post_process: Iterable[Callable[[VKCell], None]] | None = None,
        info: dict[str, MetaData] | None = None,
        check_ports: bool = True,
        check_pins: bool = True,
        check_unnamed_cells: CheckUnnamedCells = CheckUnnamedCells.WARNING,
        tags: list[str] | None = None,
        lvs_equivalent_ports: list[list[str]] | None = None,
        ports: PortsDefinition | None = None,
    ) -> (
        Callable[KCellParams, VK]
        | Callable[[Callable[KCellParams, VK]], Callable[KCellParams, VK]]
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
            check_ports: Check uniqueness of port names.
            check_pins: Check uniqueness of pin names.
            check_unnamed_cells: Check for unnamed child cells (matching
                ``Unnamed_\\d+``). ``"error"`` raises, ``"warning"`` logs a warning,
                ``"ignore"`` skips the check.
            add_port_layers: Add special layers of `KCLayout.netlist_layer_mapping`
                to the ports if the port layer is in the mapping.
            cache: Provide a user defined cache instead of an internal one. This
                can be used for example to clear the cache.
            basename: Overwrite the name normally inferred from the function or class
                name.
            drop_params: Drop these parameters before writing the
                [settings][kfactory.kcell.KCell.settings]
            register_factory: Register the resulting KCell-function to the
                `KCLayout.factories`
            info: Additional metadata to put into info attribute.
            post_process: List of functions to call after the cell has been created.
        Returns:
            A wrapped vcell function which caches responses and modifies the VKCell
            according to settings.
        """
        if check_unnamed_cells is None:
            check_unnamed_cells = config.check_unnamed_cells
        if post_process is None:
            post_process = ()

        def decorator_autocell(
            f: Callable[KCellParams, VKCell],
        ) -> Callable[KCellParams, VK]:
            sig = inspect.signature(f)
            output_cell_type_: type[VK | VKCell]
            if output_type is not None:
                output_cell_type_ = output_type
            elif sig.return_annotation is not inspect.Signature.empty:
                # Use get_type_hints to resolve string annotations
                try:
                    type_hints = get_type_hints(f, globalns=f.__globals__)  # ty:ignore[unresolved-attribute]
                    output_cell_type_ = type_hints.get("return", sig.return_annotation)

                except Exception:
                    # Fallback to raw annotation if get_type_hints fails
                    logger.opt(depth=2).warning(
                        "Cannot determine output type ((D)KCell type)"
                        f"from annotation {sig.return_annotation!r}. "
                        "Trying to continue but likely this will fail.",
                    )
                    output_cell_type_ = sig.return_annotation
            else:
                output_cell_type_ = self.default_vcell_output_type

            output_cell_type__ = cast("type[VK]", output_cell_type_)
            # previously was a KCellCache, but dict should do for most case
            cache_: Cache[Hashable, VK] | dict[Hashable, VK] = cache or Cache(
                maxsize=float("inf")
            )

            wrapper_autocell = WrappedVKCellFunc(
                kcl=self,
                f=f,
                sig=sig,
                cache=cache_,
                set_settings=set_settings,
                set_name=set_name,
                add_port_layers=add_port_layers,
                basename=basename,
                drop_params=drop_params,
                post_process=post_process,
                output_type=output_cell_type__,
                info=info,
                check_ports=check_ports,
                check_pins=check_pins,
                check_unnamed_cells=check_unnamed_cells,
                tags=tags,
                lvs_equivalent_ports=lvs_equivalent_ports,
                ports=ports,
            )

            if register_factory:
                if wrapper_autocell.name is None:
                    raise ValueError(f"Function {f} has no name.")
                self.virtual_factories.add(wrapper_autocell)  # ty:ignore[invalid-argument-type]

            @functools.wraps(f)
            def func(*args: KCellParams.args, **kwargs: KCellParams.kwargs) -> VK:
                return wrapper_autocell(*args, **kwargs)

            return func

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
        if (
            name not in self.__class__.model_fields
            and name not in self.__class__.__private_attributes__
        ):
            return self.layout.__getattribute__(name)
        return super().__getattr__(name)  # ty:ignore[unresolved-attribute]

    def __setattr__(self, name: str, value: Any) -> None:
        """Use a custom setter to automatically set attributes.

        If the attribute is not in this object, set it on the
        Layout object.
        """
        if (
            name in self.__class__.model_fields
            or name in self.__class__.__private_attributes__
        ):
            super().__setattr__(name, value)
            if name == "infos":
                # Drop the cached `layers` and rebuild it eagerly so the new
                # LayerEnum members register their names with `self.layout`.
                # The AttributeError only fires on the construction path where
                # `layers` hasn't been materialized yet.
                with contextlib.suppress(AttributeError):
                    del self.layers
                _ = self.layers  # make sure the layers are computed
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
        for c in self.layout.cells("*"):
            c.locked = False
        self.layout.clear()
        self.tkcells = {}

        if keep_layers:
            with contextlib.suppress(AttributeError):
                del self.layers
            _ = self.layers  # make sure the layers are computed
        else:
            self.infos = LayerInfos()

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
                kcl.tkcells[i] = kc.model_copy(
                    update={"kdb_cell": kc.kdb_cell, "kcl": kcl}
                )
        kcl.rename_function = self.rename_function
        return kcl

    def layout_cell(self, name: str | int) -> kdb.Cell | None:
        """Get a cell by name or index from the Layout object."""
        return self.layout.cell(name)

    @overload
    def cells(self, name: str) -> list[kdb.Cell]: ...

    @overload
    def cells(self) -> int: ...

    def cells(self, name: str | None = None) -> int | list[kdb.Cell]:
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
            raise ValueError(
                f"Cellname {name} already exists in the layout/KCLayout. "
                "Please make sure the cellname is"
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
            for ci in cell_index_list:
                self.layout.cell(ci).locked = False
                self.tkcells.pop(ci, None)
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

            for cell in self.cells("*"):
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
                    f"Cannot register {kcell} if it has been registered already"
                    " exists in the library"
                )

    def __getitem__(self, obj: str | int) -> KCell:
        """Retrieve a cell by name(str) or index(int).

        Attrs:
            obj: name of cell or cell_index
        """
        return self.get_cell(obj)

    def get_cell[KC: ProtoTKCell[Any]](
        self,
        obj: str | int,
        cell_type: type[KC] = KCell,  # ty:ignore[invalid-parameter-default]
        error_search_limit: int | None = 10,
    ) -> KC:
        """Retrieve a cell by name(str) or index(int).

        Attrs:
            obj: name of cell or cell_index
            cell_type: type of cell to return
        """
        if isinstance(obj, int):
            # search by index
            try:
                return cell_type(base=self.tkcells[obj])
            except KeyError:
                kdb_c = self.layout_cell(obj)
                if kdb_c is None:
                    raise
                return cell_type(name=kdb_c.name, kcl=self, kdb_cell=kdb_c)
        # search by name/key
        kdb_c = self.layout_cell(obj)
        if kdb_c is not None:
            try:
                return cell_type(base=self.tkcells[kdb_c.cell_index()])
            except KeyError:
                c = cell_type(name=kdb_c.name, kcl=self, kdb_cell=kdb_c)
                c.get_meta_data()
                return c
        if error_search_limit:
            # limit the print of available cells
            # and throw closest names with fuzzy search
            from rapidfuzz import process

            closest_names = [
                result[0]
                for result in process.extract(
                    obj,
                    (cell.name for cell in self.kcells.values()),
                    limit=error_search_limit,
                )
            ]
            raise ValueError(
                f"Library doesn't have a KCell named {obj},"
                f" closest {error_search_limit} are: \n"
                f"{pformat(closest_names)}"
            )

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
                if diff.diff_xor.cells() > 0:
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
                            + yaml.dumps(dict(diff.layout_meta_diff))  # ty:ignore[unresolved-attribute]
                            + "\n```"
                        )
                    if diff.cells_meta_diff:
                        yaml = ruamel.yaml.YAML(typ=["rt", "string"])
                        err_msg += (
                            "\nLayout Meta Diff:\n```\n"
                            + yaml.dumps(dict(diff.cells_meta_diff))  # ty:ignore[unresolved-attribute]
                            + "\n```"
                        )

                    raise MergeError(err_msg)

            cells = set(self.cells("*"))
            saveopts = save_layout_options()
            saveopts.gds2_max_cellname_length = (
                kdb.SaveLayoutOptions().gds2_max_cellname_length
            )
            binary_layout = layout_b.write_bytes(saveopts)
            locked_cells = [
                kdb_cell for kdb_cell in self.layout.each_cell() if kdb_cell.locked
            ]
            for kdb_cell in locked_cells:
                kdb_cell.locked = False
            lm = self.layout.read_bytes(binary_layout, options)
            for kdb_cell in locked_cells:
                kdb_cell.locked = True
            info, settings = self.get_meta_data()

            match update_kcl_meta_data:
                case "overwrite":
                    for k, v in info.items():
                        self.info[k] = v
                case "skip":
                    info_ = self.info.model_dump()

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
        asym_cross_sections: list[dict[str, Any]] = []
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
            elif meta.name.startswith("kfactory:asymmetrical_cross_section:"):
                asym_cross_sections.append(
                    {
                        "name": meta.name.removeprefix(
                            "kfactory:asymmetrical_cross_section:"
                        ),
                        **meta.value,
                    }
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
                    radius=cs.get("radius"),
                    radius_min=cs.get("radius_min"),
                )
            )
        for acs in asym_cross_sections:
            self.get_asymmetrical_cross_section(
                AsymmetricalCrossSection(
                    layer=acs["layer"],
                    section_min=acs["section_min"],
                    section_max=acs["section_max"],
                    sections=tuple(
                        CrossSectionLayer(**s) for s in acs.get("sections", ())
                    ),
                    name=acs["name"],
                    radius=acs.get("radius"),
                    radius_min=acs.get("radius_min"),
                    bbox_sections=acs.get("bbox_sections", {}),
                )
            )

        return info, settings

    def set_meta_data(self) -> None:
        """Set the info/settings of the KCLayout."""
        if config.write_kfactory_settings:
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
        for xs in set(self.cross_sections.cross_sections.values()):
            if isinstance(xs, AsymmetricalCrossSection):
                self.add_meta_info(
                    kdb.LayoutMetaInfo(
                        f"kfactory:asymmetrical_cross_section:{xs.name}",
                        {
                            "layer": xs.layer,
                            "section_min": xs.section_min,
                            "section_max": xs.section_max,
                            "sections": [
                                {
                                    "layer": s.layer,
                                    "section_min": s.section_min,
                                    "section_max": s.section_max,
                                }
                                for s in xs.sections
                            ],
                            "radius": xs.radius,
                            "radius_min": xs.radius_min,
                            "bbox_sections": xs.bbox_sections,
                        },
                        None,
                        True,
                    )
                )
            else:
                self.add_meta_info(
                    kdb.LayoutMetaInfo(
                        f"kfactory:cross_section:{xs.name}",
                        {
                            "width": xs.width,
                            "layer_enclosure": xs.enclosure.name,
                            **({"radius": xs.radius} if xs.radius is not None else {}),
                            **(
                                {"radius_min": xs.radius_min}
                                if xs.radius_min is not None
                                else {}
                            ),
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
        deduplicate_cell_names: bool = False,
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
            deduplicate_cell_names: If True, auto-rename duplicate cells with
                ``$1``, ``$2``, … suffixes before writing. If False (the
                default), raise
                :class:`~kfactory.exceptions.DuplicateCellNameError` when
                duplicates are detected.
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
        try:
            return self.layout.write(filename, options)
        except RuntimeError:
            all_indices = {
                c.cell_index() for c in self.layout.each_cell() if not c._destroyed()
            }
            _check_duplicate_cell_names(
                self.layout,
                all_indices,
                auto_rename=deduplicate_cell_names,
                tkcells=self.tkcells,
            )
            return self.layout.write(filename, options)

    def write_bytes(
        self,
        options: kdb.SaveLayoutOptions | None = None,
        convert_external_cells: bool = False,
        set_meta_data: bool = True,
        deduplicate_cell_names: bool = False,
    ) -> bytes:
        if options is None:
            options = save_layout_options()
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

        try:
            return self.layout.write_bytes(options)
        except RuntimeError:
            all_indices = {
                c.cell_index() for c in self.layout.each_cell() if not c._destroyed()
            }
            _check_duplicate_cell_names(
                self.layout,
                all_indices,
                auto_rename=deduplicate_cell_names,
                tkcells=self.tkcells,
            )
            return self.layout.write_bytes(options)

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
        | CrossSectionSpecDict
        | DCrossSectionSpecDict
        | DSymmetricalCrossSection,
    ) -> SymmetricalCrossSection:
        """Get a cross section by name or specification."""
        return self.cross_sections.get_cross_section(cross_section)

    def get_asymmetrical_cross_section(
        self,
        cross_section: str
        | AsymmetricalCrossSection
        | DAsymmetricalCrossSection
        | TAsymmetricCrossSection[Any],
    ) -> AsymmetricalCrossSection:
        """Get an asymmetrical cross section by name or instance."""
        if isinstance(cross_section, TAsymmetricCrossSection):
            cross_section = cross_section.base
        return self.cross_sections.get_asymmetrical_cross_section(cross_section)

    @overload
    def get_base_cross_section(
        self,
        cross_section: str
        | SymmetricalCrossSection
        | CrossSectionSpecDict
        | DCrossSectionSpecDict
        | DSymmetricalCrossSection
        | TCrossSection[Any],
        symmetrical: Literal[True],
    ) -> SymmetricalCrossSection: ...

    @overload
    def get_base_cross_section(
        self,
        cross_section: str
        | AsymmetricalCrossSection
        | DAsymmetricalCrossSection
        | TAsymmetricCrossSection[Any],
        symmetrical: Literal[False],
    ) -> AsymmetricalCrossSection: ...

    @overload
    def get_base_cross_section(
        self,
        cross_section: Any,
        symmetrical: None = None,
    ) -> SymmetricalCrossSection | AsymmetricalCrossSection: ...

    def get_base_cross_section(
        self,
        cross_section: Any,
        symmetrical: bool | None = None,
    ) -> SymmetricalCrossSection | AsymmetricalCrossSection:
        """Get a cross section by name or instance.

        Args:
            cross_section: name, spec, or instance.
            symmetrical: kind filter. `None` (default) returns either kind,
                dispatching by input type (string names are looked up directly).
                `True` returns a symmetric cross section and raises if the resolved
                one is asymmetric. `False` returns an asymmetric cross section and
                raises if the resolved one is symmetric.
        """
        if symmetrical is True:
            return self.get_symmetrical_cross_section(cross_section)
        if symmetrical is False:
            return self.get_asymmetrical_cross_section(cross_section)
        if isinstance(cross_section, str):
            if cross_section in self.cross_sections.cross_sections:
                return self.cross_sections.cross_sections[cross_section]
            raise KeyError(
                f"No cross section named {cross_section!r} (symmetric or asymmetric)."
            )
        if isinstance(
            cross_section,
            (
                AsymmetricalCrossSection,
                DAsymmetricalCrossSection,
                TAsymmetricCrossSection,
            ),
        ):
            return self.get_asymmetrical_cross_section(cross_section)
        # spec dicts (CrossSectionSpec / DCrossSectionSpec) are always symmetric
        return self.get_symmetrical_cross_section(cross_section)

    @overload
    def get_icross_section(
        self,
        cross_section: str
        | SymmetricalCrossSection
        | CrossSectionSpecDict
        | DCrossSectionSpecDict
        | DCrossSection
        | DSymmetricalCrossSection
        | CrossSection,
        symmetrical: Literal[True],
    ) -> CrossSection: ...
    @overload
    def get_icross_section(
        self,
        cross_section: str
        | AsymmetricalCrossSection
        | DAsymmetricalCrossSection
        | TAsymmetricCrossSection[Any],
        symmetrical: Literal[False],
    ) -> AsymmetricCrossSection: ...
    @overload
    def get_icross_section(
        self, cross_section: Any, symmetrical: None = None
    ) -> CrossSection | AsymmetricCrossSection: ...
    def get_icross_section(
        self, cross_section: Any, symmetrical: bool | None = None
    ) -> CrossSection | AsymmetricCrossSection:
        """Get a dbu cross section wrapper (symmetric or asymmetric, see kwarg)."""
        if symmetrical is True:
            return CrossSection(
                kcl=self, base=self.get_symmetrical_cross_section(cross_section)
            )
        if symmetrical is False:
            return AsymmetricCrossSection(
                kcl=self, base=self.get_asymmetrical_cross_section(cross_section)
            )
        xs = self.get_base_cross_section(cross_section)
        if isinstance(xs, AsymmetricalCrossSection):
            return AsymmetricCrossSection(kcl=self, base=xs)
        return CrossSection(kcl=self, base=xs)

    @overload
    def get_dcross_section(
        self,
        cross_section: str
        | SymmetricalCrossSection
        | CrossSectionSpecDict
        | DCrossSectionSpecDict
        | DSymmetricalCrossSection
        | CrossSection
        | DCrossSection,
        symmetrical: Literal[True],
    ) -> DCrossSection: ...
    @overload
    def get_dcross_section(
        self,
        cross_section: str
        | AsymmetricalCrossSection
        | DAsymmetricalCrossSection
        | TAsymmetricCrossSection[Any],
        symmetrical: Literal[False],
    ) -> DAsymmetricCrossSection: ...
    @overload
    def get_dcross_section(
        self, cross_section: Any, symmetrical: None = None
    ) -> DCrossSection | DAsymmetricCrossSection: ...
    def get_dcross_section(
        self, cross_section: Any, symmetrical: bool | None = None
    ) -> DCrossSection | DAsymmetricCrossSection:
        """Get a um cross section wrapper (symmetric or asymmetric, see kwarg)."""
        if symmetrical is True:
            return DCrossSection(
                kcl=self, base=self.get_symmetrical_cross_section(cross_section)
            )
        if symmetrical is False:
            return DAsymmetricCrossSection(
                kcl=self, base=self.get_asymmetrical_cross_section(cross_section)
            )
        xs = self.get_base_cross_section(cross_section)
        if isinstance(xs, AsymmetricalCrossSection):
            return DAsymmetricCrossSection(kcl=self, base=xs)
        return DCrossSection(kcl=self, base=xs)

    def get_iasymmetric_cross_section(
        self,
        cross_section: str
        | AsymmetricalCrossSection
        | DAsymmetricalCrossSection
        | TAsymmetricCrossSection[Any],
    ) -> AsymmetricCrossSection:
        """Get a dbu-flavored asymmetric cross section wrapper."""
        return AsymmetricCrossSection(
            kcl=self, base=self.get_asymmetrical_cross_section(cross_section)
        )

    def get_dasymmetric_cross_section(
        self,
        cross_section: str
        | AsymmetricalCrossSection
        | DAsymmetricalCrossSection
        | TAsymmetricCrossSection[Any],
    ) -> DAsymmetricCrossSection:
        """Get a um-flavored asymmetric cross section wrapper."""
        return DAsymmetricCrossSection(
            kcl=self, base=self.get_asymmetrical_cross_section(cross_section)
        )

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.name}, n={len(self.kcells)})"

    def delete(self) -> None:
        del kcls[self.name]
        self.library.delete()

    def routing_strategy(
        self,
        f: Callable[
            Concatenate[
                ProtoTKCell[Any],
                Sequence[Sequence[ProtoPort[Any]]],
                ...,
            ],
            list[ManhattanRoute],
        ],
    ) -> Callable[
        Concatenate[
            ProtoTKCell[Any],
            Sequence[Sequence[ProtoPort[Any]]],
            ...,
        ],
        list[ManhattanRoute],
    ]:
        self.routing_strategies[get_function_name(f)] = f
        return f

    @overload
    def generic_factory[F: Callable[..., ProtoTKCell[Any]] | Callable[..., VKCell]](
        self, f: F, *, name: str | None = None
    ) -> F: ...
    @overload
    def generic_factory[F: Callable[..., ProtoTKCell[Any]] | Callable[..., VKCell]](
        self, *, name: str | None = None
    ) -> Callable[[F], F]: ...
    def generic_factory[F: Callable[..., ProtoTKCell[Any]] | Callable[..., VKCell]](
        self,
        f: F | None = None,
        *,
        name: str | None = None,
    ) -> F | Callable[[F], F]:
        """Register an arbitrary cell-producing function as a generic factory.

        Generic factories are stored in `KCLayout.generic_factories`, separate
        from the `factories` / `virtual_factories` registries. They are expected
        to delegate to one of the real (cached) factories, so they need no cache
        of their own. On every call the returned cell's `kcl` is checked against
        this layout.

        Can be used bare (`@kcl.generic_factory`), with a custom name
        (`@kcl.generic_factory(name="...")`), or as a direct call
        (`kcl.generic_factory(func, name="...")`).

        Args:
            f: A callable returning a `(D)KCell` or `VKCell`.
            name: Name to register under. Defaults to the function's name.

        Returns:
            The wrapped function (guardrail-checked) registered under `name`.
        """

        def register(func: F) -> F:
            factory_name = name or get_function_name(func)

            @functools.wraps(func)
            def wrapper(*args: Any, **kwargs: Any) -> ProtoTKCell[Any] | VKCell:
                c = func(*args, **kwargs)
                if c.kcl is not self:
                    raise ValueError(
                        f"generic_factory {factory_name!r} returned a cell from"
                        f" KCLayout {c.kcl.name!r}, expected {self.name!r}."
                    )
                return c

            registered = cast(
                "Callable[..., ProtoTKCell[Any]] | Callable[..., VKCell]", wrapper
            )
            self.generic_factories[factory_name] = registered
            return cast("F", registered)

        return register if f is None else register(f)


ManhattanRoute.model_rebuild()
KCLayout.model_rebuild()
SymmetricalCrossSection.model_rebuild()
AsymmetricalCrossSection.model_rebuild()
DAsymmetricalCrossSection.model_rebuild()
CrossSectionLayer.model_rebuild()
DCrossSectionLayer.model_rebuild()
CrossSectionModel.model_rebuild()
TKCell.model_rebuild()
TVCell.model_rebuild()
BasePin.model_rebuild()
BasePort.model_rebuild()
BaseKCell.model_rebuild()
LayerEnclosureModel.model_rebuild()

kcl = KCLayout("DEFAULT")
"""Default library object.

Any [KCell][kfactory.kcell.KCell] uses this object unless another one is
specified in the constructor."""
cell = kcl.cell
"""Default kcl @cell decorator."""
vcell = kcl.vcell
"""Default kcl @vcell decorator."""


class CellKWargs[KC: ProtoTKCell[Any]](TypedDict, total=False):
    set_settings: bool
    set_name: bool
    check_ports: bool
    check_pins: bool
    check_instances: CheckInstances
    snap_ports: bool
    add_port_layers: bool
    cache: Cache[Hashable, Any] | dict[Hashable, Any]
    basename: str
    drop_params: list[str]
    register_factory: bool
    overwrite_existing: bool
    layout_cache: bool
    info: dict[str, MetaData]
    post_process: Iterable[Callable[[KC], None]]
    debug_names: bool
    tags: list[str]
    lvs_equivalent_ports: list[list[str]]
    ports: PortsDefinition
    schematic_function: Callable[..., TSchematic[Any]]
