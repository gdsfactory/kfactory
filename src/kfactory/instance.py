from __future__ import annotations

import functools
from abc import abstractmethod
from hashlib import sha3_512
from typing import (
    TYPE_CHECKING,
    Any,
    ClassVar,
    Generic,
    Self,
    overload,
)

import klayout.db as kdb

from .conf import PROPID, config, logger
from .exceptions import (
    PortLayerMismatchError,
    PortTypeMismatchError,
    PortWidthMismatchError,
)
from .geometry import DBUGeometricObject, GeometricObject, UMGeometricObject
from .port import DPort, Port, ProtoPort
from .serialization import clean_name, get_cell_name
from .typings import TUnit

if TYPE_CHECKING:
    from ruamel.yaml.representer import BaseRepresenter, MappingNode

    from .instance_pins import (
        DInstancePins,
        InstancePins,
        ProtoTInstancePins,
        VInstancePins,
    )
    from .instance_ports import (
        DInstancePorts,
        InstancePorts,
        ProtoInstancePorts,
        ProtoTInstancePorts,
        VInstancePorts,
    )
    from .kcell import AnyKCell, AnyTKCell, DKCell, KCell, ProtoTKCell
    from .layer import LayerEnum
    from .layout import KCLayout

__all__ = ["DInstance", "Instance", "ProtoInstance", "ProtoTInstance", "VInstance"]


class ProtoInstance(GeometricObject[TUnit], Generic[TUnit]):
    """Base class for instances."""

    _kcl: KCLayout

    @property
    def kcl(self) -> KCLayout:
        """KCLayout object."""
        return self._kcl

    @kcl.setter
    def kcl(self, val: KCLayout) -> None:
        self._kcl = val

    @property
    @abstractmethod
    def name(self) -> str | None:
        """Name of the instance."""

    @name.setter
    @abstractmethod
    def name(self, value: str | None) -> None: ...

    @property
    @abstractmethod
    def cell_name(self) -> str | None:
        """Name of the cell the instance refers to."""

    @abstractmethod
    def __getitem__(self, key: int | str | None) -> ProtoPort[TUnit]: ...

    @property
    @abstractmethod
    def ports(self) -> ProtoInstancePorts[TUnit, ProtoInstance[TUnit]]: ...


class ProtoTInstance(ProtoInstance[TUnit], Generic[TUnit]):
    _instance: kdb.Instance

    @property
    def instance(self) -> kdb.Instance:
        return self._instance

    def ibbox(self, layer: int | None = None) -> kdb.Box:
        if layer is None:
            return self._instance.bbox()
        return self._instance.bbox(layer)

    def dbbox(self, layer: int | None = None) -> kdb.DBox:
        if layer is None:
            return self._instance.dbbox()
        return self._instance.dbbox(layer)

    @property
    def cell_name(self) -> str:
        return self._instance.cell.name

    def to_itype(self) -> Instance:
        return Instance(kcl=self.kcl, instance=self._instance)

    def to_dtype(self) -> DInstance:
        return DInstance(kcl=self.kcl, instance=self._instance)

    @abstractmethod
    def __getitem__(
        self, key: int | str | tuple[int | str | None, int, int] | None
    ) -> ProtoPort[TUnit]: ...

    def __getattr__(self, name: str) -> Any:
        """If we don't have an attribute, get it from the instance."""
        try:
            return super().__getattr__(name)  # type: ignore[misc]
        except Exception:
            return getattr(self._instance, name)

    def is_named(self) -> bool:
        return self.instance.property(PROPID.NAME) is not None

    @property
    def name(self) -> str:
        """Name of instance in GDS."""
        prop = self.instance.property(PROPID.NAME)
        if prop is not None:
            return str(prop)
        name = f"{self.cell.name}_{self.trans.disp.x}_{self.trans.disp.y}"
        if self.cplx_trans.angle != 0:
            if self.cplx_trans.angle.is_integer():
                name += f"_A{int(self.cplx_trans.angle)}"
            else:
                name += f"_A{str(self.cplx_trans.angle).replace('.', 'p')}"
        if self.cplx_trans.is_mirror():
            name += "_M"
        return name

    @name.setter
    def name(self, value: str | None) -> None:
        self.instance.set_property(PROPID.NAME, value)

    @property
    @abstractmethod
    def parent_cell(self) -> ProtoTKCell[TUnit]: ...

    @property
    def purpose(self) -> str | None:
        """Purpose value of instance in GDS."""
        return self._instance.property(PROPID.PURPOSE)  # type: ignore[no-any-return]

    @purpose.setter
    def purpose(self, value: str | None) -> None:
        self._instance.set_property(PROPID.PURPOSE, value)

    @property
    def cell_index(self) -> int:
        """Get the index of the cell this instance refers to."""
        return self._instance.cell_index

    @cell_index.setter
    def cell_index(self, value: int) -> None:
        self._instance.cell_index = value

    @property
    @abstractmethod
    def cell(self) -> ProtoTKCell[TUnit]:
        """Parent KCell  of the Instance."""
        ...

    @cell.setter
    @abstractmethod
    def cell(self, value: ProtoTKCell[Any]) -> None: ...

    @property
    @abstractmethod
    def ports(self) -> ProtoTInstancePorts[TUnit]:
        """Ports of the instance."""
        ...

    @property
    @abstractmethod
    def pins(self) -> ProtoTInstancePins[TUnit]:
        """Ports of the instance."""
        ...

    @property
    def a(self) -> kdb.Vector:
        """Returns the displacement vector for the 'a' axis."""
        return self._instance.a

    @a.setter
    def a(self, vec: kdb.Vector | kdb.DVector) -> None:
        self._instance.a = vec  # type: ignore[assignment]

    @property
    def b(self) -> kdb.Vector:
        """Returns the displacement vector for the 'b' axis."""
        return self._instance.b

    @b.setter
    def b(self, vec: kdb.Vector | kdb.DVector) -> None:
        self._instance.b = vec  # type: ignore[assignment]

    @property
    def cell_inst(self) -> kdb.CellInstArray:
        """Gets the basic CellInstArray object associated with this instance."""
        return self._instance.cell_inst

    @cell_inst.setter
    def cell_inst(self, cell_inst: kdb.CellInstArray | kdb.DCellInstArray) -> None:
        self._instance.cell_inst = cell_inst  # type: ignore[assignment]

    @property
    def cplx_trans(self) -> kdb.ICplxTrans:
        """Gets the complex transformation of the instance.

        Or the first instance in the array.
        """
        return self._instance.cplx_trans

    @cplx_trans.setter
    def cplx_trans(self, trans: kdb.ICplxTrans | kdb.DCplxTrans) -> None:
        self._instance.cplx_trans = trans  # type: ignore[assignment]

    @property
    def dcplx_trans(self) -> kdb.DCplxTrans:
        """Gets the complex transformation of the instance.

        Or the first instance in the array.
        """
        return self._instance.dcplx_trans

    @dcplx_trans.setter
    def dcplx_trans(self, trans: kdb.DCplxTrans) -> None:
        self._instance.dcplx_trans = trans

    @property
    def dtrans(self) -> kdb.DTrans:
        """Gets the complex transformation of the instance.

        Or the first instance in the array.
        """
        return self._instance.dtrans

    @dtrans.setter
    def dtrans(self, trans: kdb.DTrans) -> None:
        self._instance.dtrans = trans

    @property
    def trans(self) -> kdb.Trans:
        """Gets the complex transformation of the instance.

        Or the first instance in the array.
        """
        return self._instance.trans

    @trans.setter
    def trans(self, trans: kdb.Trans | kdb.DTrans) -> None:
        self._instance.trans = trans  # type: ignore[assignment]

    @property
    def na(self) -> int:
        """Returns the displacement vector for the 'a' axis."""
        return self._instance.na

    @na.setter
    def na(self, value: int) -> None:
        self._instance.na = value

    @property
    def nb(self) -> int:
        """Returns the number of instances in the 'b' axis."""
        return self._instance.nb

    @nb.setter
    def nb(self, value: int) -> None:
        self._instance.nb = value

    @property
    def prop_id(self) -> int:
        """Gets the properties ID associated with the instance."""
        return self._instance.prop_id

    @prop_id.setter
    def prop_id(self, value: int) -> None:
        self._instance.prop_id = value

    @property
    def hash(self) -> bytes:
        """Hash the instance."""
        h = sha3_512()
        h.update(self.cell.hash())
        if not self.is_complex():
            h.update(self.trans.hash().to_bytes(8, "big"))
        else:
            h.update(self.dcplx_trans.hash().to_bytes(8, "big"))
        return h.digest()

    @overload
    def connect(
        self,
        port: str | ProtoPort[Any] | None,
        other: ProtoPort[Any],
        *,
        mirror: bool = False,
        allow_width_mismatch: bool | None = None,
        allow_layer_mismatch: bool | None = None,
        allow_type_mismatch: bool | None = None,
        use_mirror: bool | None = None,
        use_angle: bool | None = None,
    ) -> None: ...

    @overload
    def connect(
        self,
        port: str | ProtoPort[Any] | None,
        other: ProtoTInstance[Any],
        other_port_name: str | int | tuple[int | str, int, int] | None,
        *,
        mirror: bool = False,
        allow_width_mismatch: bool | None = None,
        allow_layer_mismatch: bool | None = None,
        allow_type_mismatch: bool | None = None,
        use_mirror: bool | None = None,
        use_angle: bool | None = None,
    ) -> None: ...

    @overload
    def connect(
        self,
        port: str | ProtoPort[Any] | None,
        other: VInstance,
        other_port_name: str | int | None,
        *,
        mirror: bool = False,
        allow_width_mismatch: bool | None = None,
        allow_layer_mismatch: bool | None = None,
        allow_type_mismatch: bool | None = None,
        use_mirror: bool | None = None,
        use_angle: bool | None = None,
    ) -> None: ...

    def connect(
        self,
        port: str | ProtoPort[Any] | None,
        other: ProtoInstance[Any] | ProtoPort[Any],
        other_port_name: str | int | tuple[int | str, int, int] | None = None,
        *,
        mirror: bool = False,
        allow_width_mismatch: bool | None = None,
        allow_layer_mismatch: bool | None = None,
        allow_type_mismatch: bool | None = None,
        use_mirror: bool | None = None,
        use_angle: bool | None = None,
    ) -> None:
        """Align port with name `portname` to a port.

        Function to allow to transform this instance so that a port of this instance is
        connected (same center with 180° turn) to another instance.

        Args:
            port: The name of the port of this instance to be connected, or directly an
                instance port. Can be `None` because port names can be `None`.
            other: The other instance or a port. Skip `other_port_name` if it's a port.
            other_port_name: The name of the other port. Ignored if
                `other` is a port.
            mirror: Instead of applying klayout.db.Trans.R180 as a connection
                transformation, use klayout.db.Trans.M90, which effectively means this
                instance will be mirrored and connected.
            allow_width_mismatch: Skip width check between the ports if set.
            allow_layer_mismatch: Skip layer check between the ports if set.
            allow_type_mismatch: Skip port_type check between the ports if set.
            use_mirror: If False mirror flag does not get applied from the connection.
            use_angle: If False the angle does not get applied from the connection.
        """
        if allow_width_mismatch is None:
            allow_width_mismatch = config.allow_width_mismatch
        if allow_layer_mismatch is None:
            allow_layer_mismatch = config.allow_layer_mismatch
        if allow_type_mismatch is None:
            allow_type_mismatch = config.allow_type_mismatch
        if use_mirror is None:
            use_mirror = config.connect_use_mirror
        if use_angle is None:
            use_angle = config.connect_use_angle

        if isinstance(other, ProtoPort):
            op = Port(base=other.base)
        else:
            if other_port_name is None:
                raise ValueError(
                    "portname cannot be None if an Instance Object is given. For"
                    "complex connections (non-90 degree and floating point ports) use"
                    "route_cplx instead"
                )
            op = Port(base=other.ports[other_port_name].base)  # type: ignore[index]
        if isinstance(port, ProtoPort):
            p = Port(base=port.base.transformed(self.dcplx_trans.inverted()))
        else:
            p = Port(base=self.cell.ports[port].base)

        assert isinstance(p, Port)
        assert isinstance(op, Port)

        if p.width != op.width and not allow_width_mismatch:
            raise PortWidthMismatchError(self, other, p, op)
        if p.layer != op.layer and not allow_layer_mismatch:
            raise PortLayerMismatchError(self.cell.kcl, self, other, p, op)
        if p.port_type != op.port_type and not allow_type_mismatch:
            raise PortTypeMismatchError(self, other, p, op)
        if p.base.dcplx_trans or op.base.dcplx_trans:
            dconn_trans = kdb.DCplxTrans.M90 if mirror else kdb.DCplxTrans.R180
            match (use_mirror, use_angle):
                case True, True:
                    dcplx_trans = (
                        op.dcplx_trans * dconn_trans * p.dcplx_trans.inverted()
                    )
                    self._instance.dcplx_trans = dcplx_trans
                case False, True:
                    dconn_trans = (
                        kdb.DCplxTrans.M90
                        if mirror ^ self.dcplx_trans.mirror
                        else kdb.DCplxTrans.R180
                    )
                    opt = op.dcplx_trans
                    opt.mirror = False
                    dcplx_trans = opt * dconn_trans * p.dcplx_trans.inverted()
                    self._instance.dcplx_trans = dcplx_trans
                case False, False:
                    self._instance.dcplx_trans = kdb.DCplxTrans(
                        op.dcplx_trans.disp - p.dcplx_trans.disp
                    )
                case True, False:
                    self._instance.dcplx_trans = kdb.DCplxTrans(
                        op.dcplx_trans.disp - p.dcplx_trans.disp
                    )
                    self.dmirror_y(op.dcplx_trans.disp.y)
                case _:
                    raise NotImplementedError("This shouldn't happen")

        else:
            conn_trans = kdb.Trans.M90 if mirror else kdb.Trans.R180
            match (use_mirror, use_angle):
                case True, True:
                    trans = op.trans * conn_trans * p.trans.inverted()
                    self._instance.trans = trans
                case False, True:
                    conn_trans = (
                        kdb.Trans.M90 if mirror ^ self.trans.mirror else kdb.Trans.R180
                    )
                    op = op.copy()
                    op.trans.mirror = False
                    trans = op.trans * conn_trans * p.trans.inverted()
                    self._instance.trans = trans
                case False, False:
                    self._instance.trans = kdb.Trans(op.trans.disp - p.trans.disp)
                case True, False:
                    self._instance.trans = kdb.Trans(op.trans.disp - p.trans.disp)
                    self.dmirror_y(op.dcplx_trans.disp.y)
                case _:
                    raise NotImplementedError("This shouldn't happen")

    def __repr__(self) -> str:
        """Return a string representation of the instance."""
        port_names = [p.name for p in self.ports]
        return (
            f"{self.parent_cell.name}: ports {port_names}, {self.kcl[self.cell_index]}"
        )

    def transform(
        self,
        trans: kdb.Trans | kdb.DTrans | kdb.ICplxTrans | kdb.DCplxTrans,
        /,
    ) -> None:
        self._instance.transform(trans)

    def flatten(self, levels: int | None = None) -> None:
        """Flatten all or just certain instances.

        Args:
            levels: If level < #hierarchy-levels -> pull the sub instances to self,
                else pull the polygons. None will always flatten all levels.
        """
        if levels:
            self._instance.flatten(levels)
        else:
            self._instance.flatten()


class Instance(ProtoTInstance[int], DBUGeometricObject):
    """An Instance of a KCell.

    An Instance is a reference to a KCell with a transformation.

    Attributes:
        _instance: The internal `kdb.Instance` reference
        ports: Transformed ports of the KCell
        kcl: Pointer to the layout object holding the instance
        d: Helper that allows retrieval of instance information in um
    """

    yaml_tag: ClassVar[str] = "!Instance"

    def __init__(self, kcl: KCLayout, instance: kdb.Instance) -> None:
        """Create an instance from a KLayout Instance."""
        self.kcl = kcl
        self._instance = instance

    @functools.cached_property
    def ports(self) -> InstancePorts:
        """Gets the transformed ports of the KCell."""
        from .instance_ports import InstancePorts

        return InstancePorts(self)

    @functools.cached_property
    def pins(self) -> InstancePins:
        """Gets the transformed pins of the KCell."""
        from .instance_pins import InstancePins

        return InstancePins(self)

    def __getitem__(
        self, key: int | str | tuple[int | str | None, int, int] | None
    ) -> Port:
        """Returns port from instance.

        The key can either be an integer, in which case the nth port is
        returned, or a string in which case the first port with a matching
        name is returned.

        If the instance is an array, the key can also be a tuple in the
        form of `c.ports[key_name, i_a, i_b]`, where `i_a` is the index in
        the `instance.a` direction and `i_b` the `instance.b` direction.

        E.g. `c.ports["a", 3, 5]`, accesses the ports of the instance which is
        3 times in `a` direction (4th index in the array), and 5 times in `b` direction
        (5th index in the array).
        """
        return Port(base=self.ports[key].base)

    @property
    def parent_cell(self) -> KCell:
        """Gets the cell this instance is contained in."""
        return self.kcl[self._instance.parent_cell.cell_index()]

    @parent_cell.setter
    def parent_cell(self, cell: KCell | DKCell | kdb.Cell) -> None:
        if isinstance(cell, KCell | DKCell):
            self.parent_cell.insts.remove(self)
            self._instance.parent_cell = cell.kdb_cell
        else:
            self._instance.parent_cell = cell

    @property
    def cell(self) -> KCell:
        """Parent KCell of the Instance."""
        return self.kcl.kcells[self.cell_index]

    @cell.setter
    def cell(self, value: ProtoTKCell[Any]) -> None:
        self.cell_index = value.cell_index()

    @classmethod
    def to_yaml(cls, representer: BaseRepresenter, node: Self) -> MappingNode:
        """Convert the instance to a yaml representation."""
        d = {
            "cellname": node.cell.name,
            "trans": node._base.trans,
            "dcplx_trans": node._base.dcplx_trans,
        }
        return representer.represent_mapping(cls.yaml_tag, d)


class DInstance(ProtoTInstance[float], UMGeometricObject):
    """An Instance of a KCell.

    An Instance is a reference to a KCell with a transformation.

    Attributes:
        _instance: The internal `kdb.Instance` reference
        ports: Transformed ports of the KCell
        kcl: Pointer to the layout object holding the instance
        d: Helper that allows retrieval of instance information in um
    """

    yaml_tag: ClassVar[str] = "!Instance"

    def __init__(self, kcl: KCLayout, instance: kdb.Instance) -> None:
        """Create an instance from a KLayout Instance."""
        self.kcl = kcl
        self._instance = instance

    @functools.cached_property
    def ports(self) -> DInstancePorts:
        """Gets the transformed ports of the KCell."""
        from .instance_ports import DInstancePorts

        return DInstancePorts(self)

    @functools.cached_property
    def pins(self) -> DInstancePins:
        """Gets the transformed ports of the KCell."""
        from .instance_pins import DInstancePins

        return DInstancePins(self)

    @property
    def cell(self) -> DKCell:
        """Parent KCell  of the Instance."""
        return self.kcl.dkcells[self.cell_index]

    @cell.setter
    def cell(self, value: ProtoTKCell[Any]) -> None:
        self.cell_index = value.cell_index()

    @property
    def parent_cell(self) -> DKCell:
        """Gets the cell this instance is contained in."""
        return self.kcl.dkcells[self._instance.parent_cell.cell_index()]

    @parent_cell.setter
    def parent_cell(self, cell: KCell | DKCell | kdb.Cell) -> None:
        if isinstance(cell, KCell | DKCell):
            self.parent_cell.insts.remove(
                Instance(kcl=self.kcl, instance=self._instance)
            )
            self._instance.parent_cell = cell.kdb_cell
        else:
            self.parent_cell.insts.remove(
                Instance(kcl=self.kcl, instance=self._instance)
            )
            self._instance.parent_cell = cell

    def __getitem__(
        self, key: int | str | tuple[int | str | None, int, int] | None
    ) -> DPort:
        """Returns port from instance.

        The key can either be an integer, in which case the nth port is
        returned, or a string in which case the first port with a matching
        name is returned.

        If the instance is an array, the key can also be a tuple in the
        form of `c.ports[key_name, i_a, i_b]`, where `i_a` is the index in
        the `instance.a` direction and `i_b` the `instance.b` direction.

        E.g. `c.ports["a", 3, 5]`, accesses the ports of the instance which is
        3 times in `a` direction (4th index in the array), and 5 times in `b` direction
        (5th index in the array).
        """
        return DPort(base=self.ports[key].base)


class VInstance(ProtoInstance[float], UMGeometricObject):
    _name: str | None
    cell: AnyKCell
    trans: kdb.DCplxTrans

    def __init__(
        self,
        cell: AnyKCell,
        trans: kdb.DCplxTrans | None = None,
        name: str | None = None,
    ) -> None:
        self.kcl = cell.kcl
        self._name = name
        self.cell = cell
        self.trans = trans or kdb.DCplxTrans()

    @property
    def name(self) -> str | None:
        return self._name

    @name.setter
    def name(self, value: str | None) -> None:
        self._name = value

    @property
    def dcplx_trans(self) -> kdb.DCplxTrans:
        return self.trans

    @dcplx_trans.setter
    def dcplx_trans(self, val: kdb.DCplxTrans) -> None:
        self.trans = val

    @property
    def cell_name(self) -> str | None:
        return self.cell.name

    def ibbox(self, layer: int | LayerEnum | None = None) -> kdb.Box:
        return self.dbbox(layer).to_itype(self.kcl.dbu)

    def dbbox(self, layer: int | LayerEnum | None = None) -> kdb.DBox:
        return self.cell.dbbox(layer).transformed(self.trans)

    def __getitem__(self, key: int | str | None) -> DPort:
        """Returns port from instance.

        The key can either be an integer, in which case the nth port is
        returned, or a string in which case the first port with a matching
        name is returned.

        If the instance is an array, the key can also be a tuple in the
        form of `c.ports[key_name, i_a, i_b]`, where `i_a` is the index in
        the `instance.a` direction and `i_b` the `instance.b` direction.

        E.g. `c.ports["a", 3, 5]`, accesses the ports of the instance which is
        3 times in `a` direction (4th index in the array), and 5 times in `b` direction
        (5th index in the array).
        """
        return self.ports[key]

    @functools.cached_property
    def ports(self) -> VInstancePorts:
        from .instance_ports import VInstancePorts

        return VInstancePorts(self)

    @functools.cached_property
    def pins(self) -> VInstancePins:
        from .instance_pins import VInstancePins

        return VInstancePins(self)

    def __repr__(self) -> str:
        """Return a string representation of the instance."""
        port_names = [p.name for p in self.ports]
        return f"{self.cell.name}: ports {port_names}, transformation {self.trans}"

    def insert_into(
        self,
        cell: AnyTKCell,
        trans: kdb.DCplxTrans | None = None,
    ) -> Instance:
        from .kcell import KCell, ProtoTKCell, VKCell

        if trans is None:
            trans = kdb.DCplxTrans()

        if isinstance(self.cell, VKCell):
            trans_ = trans * self.trans
            base_trans = kdb.DCplxTrans(
                kdb.DCplxTrans(
                    kdb.ICplxTrans(trans_, cell.kcl.dbu)
                    .s_trans()
                    .to_dtype(cell.kcl.dbu)
                )
            )
            trans_ = base_trans.inverted() * trans_
            cell_name = self.cell.name
            if cell_name is None:
                raise ValueError(
                    "Cannot insert a non-flattened VInstance into a VKCell when the"
                    f" name is 'None'. VKCell at {self.trans}"
                )
            if trans_ != kdb.DCplxTrans():
                trans_str = ""
                if trans_.mirror:
                    trans_str += "_M"
                if trans_.angle != 0:
                    f"_A{trans_.angle}"
                if trans_.disp != kdb.DVector(0, 0):
                    trans_str += f"_X{trans_.disp.x}_Y{trans_.disp.y}"
                trans_str = trans_str.replace(".", "p")
                cell_name = get_cell_name(cell_name + clean_name(trans_str))
            if cell.kcl.layout_cell(cell_name) is None:
                cell_ = KCell(kcl=self.cell.kcl, name=cell_name)  # self.cell.dup()
                for layer, shapes in self.cell.shapes().items():
                    for shape in shapes.transform(trans_):
                        cell_.shapes(layer).insert(shape)
                for inst in self.cell.insts:
                    inst.insert_into(cell=cell_, trans=trans_)
                cell_.name = cell_name
                for port in self.cell.ports:
                    cell_.add_port(port=port.copy(trans_))
                for c_shapes in (
                    cell_.shapes(layer) for layer in cell_.kcl.layer_indexes()
                ):
                    if not c_shapes.is_empty():
                        r = kdb.Region(c_shapes)
                        r.merge()
                        c_shapes.clear()
                        c_shapes.insert(r)
                settings = self.cell.settings.model_copy()
                settings_units = self.cell.settings_units.model_copy()
                cell_.settings = settings
                cell_.info = self.cell.info.model_copy(deep=True)
                cell_.settings_units = settings_units
                cell_.function_name = self.cell.function_name
                cell_.basename = self.cell.basename
                cell_._base.virtual = True
                if trans_ != kdb.DCplxTrans.R0:
                    cell_._base.vtrans = trans_
            else:
                cell_ = cell.kcl[cell_name]
            inst_ = cell << cell_
            inst_.transform(base_trans)
            if self._name:
                inst_.name = self._name
            return Instance(kcl=self.cell.kcl, instance=inst_.instance)

        assert isinstance(self.cell, ProtoTKCell)
        trans_ = trans * self.trans
        base_trans = kdb.DCplxTrans(
            kdb.ICplxTrans(trans_, cell.kcl.dbu).s_trans().to_dtype(cell.kcl.dbu)
        )
        trans_ = base_trans.inverted() * trans_
        cell_name = self.cell.name
        if trans_ != kdb.DCplxTrans():
            trans_str = ""
            if trans_.mirror:
                trans_str += "_M"
            if trans_.angle != 0:
                trans_str += f"_A{trans_.angle}"
            if trans_.disp != kdb.DVector(0, 0):
                trans_str += f"_X{trans_.disp.x}_Y{trans_.disp.y}"
            trans_str = trans_str.replace(".", "p")
            cell_name += trans_str
        else:
            inst_ = cell << self.cell
            if self._name:
                inst_.name = self._name
            inst_.transform(base_trans)
            return Instance(kcl=self.cell.kcl, instance=inst_.instance)
        if cell.kcl.layout_cell(cell_name) is None:
            tkcell = self.cell.dup()
            tkcell.name = cell_name
            tkcell.flatten(True)
            for layer in tkcell.kcl.layer_indexes():
                tkcell.shapes(layer).transform(trans_)
            for _port in tkcell.ports:
                _port.dcplx_trans = trans_ * _port.dcplx_trans
            if trans_ != kdb.DCplxTrans.R0:
                tkcell._base.vtrans = trans_
            settings = self.cell.settings.model_copy()
            settings_units = self.cell.settings_units.model_copy()
            tkcell.settings = settings
            tkcell.info = self.cell.info.model_copy(deep=True)
            tkcell.settings_units = settings_units
            tkcell.function_name = self.cell.function_name
            tkcell.basename = self.cell.basename
            tkcell._base.vtrans = trans_
        else:
            tkcell = cell.kcl[cell_name]
        inst_ = cell << tkcell
        inst_.transform(base_trans)
        if self._name:
            inst_.name = self._name
        return Instance(kcl=self.cell.kcl, instance=inst_.instance)

    @overload
    def insert_into_flat(
        self,
        cell: AnyKCell,
        trans: kdb.DCplxTrans | None = None,
        *,
        levels: None = None,
    ) -> None: ...

    @overload
    def insert_into_flat(
        self,
        cell: AnyKCell,
        *,
        trans: kdb.DCplxTrans | None = None,
        levels: int,
    ) -> None: ...

    def insert_into_flat(
        self,
        cell: AnyKCell,
        trans: kdb.DCplxTrans | None = None,
        *,
        levels: int | None = None,
    ) -> None:
        from .kcell import ProtoTKCell, VKCell

        if trans is None:
            trans = kdb.DCplxTrans()

        if isinstance(self.cell, VKCell):
            for layer, shapes in self.cell.shapes().items():
                for shape in shapes.transform(trans * self.trans):
                    cell.shapes(layer).insert(shape)
            for inst in self.cell.insts:
                if levels is not None:
                    if levels > 0:
                        inst.insert_into_flat(
                            cell, trans=trans * self.trans, levels=levels - 1
                        )
                    else:
                        assert isinstance(cell, ProtoTKCell)
                        inst.insert_into(cell, trans=trans * self.trans)
                else:
                    inst.insert_into_flat(cell, trans=trans * self.trans)

        else:
            assert isinstance(self.cell, ProtoTKCell)
            if levels:
                logger.warning(
                    "Levels are not supported if the inserted Instance is a KCell."
                )
            if isinstance(cell, ProtoTKCell):
                for layer in cell.kcl.layer_indexes():
                    reg = kdb.Region(self.cell.kdb_cell.begin_shapes_rec(layer))
                    reg.transform(kdb.ICplxTrans((trans * self.trans), cell.kcl.dbu))
                    cell.shapes(layer).insert(reg)
            else:
                for layer, shapes in self.cell._shapes.items():
                    for shape in shapes.transform(trans * self.trans):
                        cell.shapes(layer).insert(shape)
                for vinst in self.cell.insts:
                    vinst.insert_into_flat(cell, trans=trans * self.trans)

    @overload
    def connect(
        self,
        port: str | ProtoPort[Any] | None,
        other: ProtoPort[Any],
        *,
        mirror: bool = False,
        allow_width_mismatch: bool | None = None,
        allow_layer_mismatch: bool | None = None,
        allow_type_mismatch: bool | None = None,
        use_mirror: bool | None = None,
        use_angle: bool | None = None,
    ) -> None: ...

    @overload
    def connect(
        self,
        port: str | ProtoPort[Any] | None,
        other: ProtoTInstance[Any],
        other_port_name: str | int | tuple[int | str, int, int] | None,
        *,
        mirror: bool = False,
        allow_width_mismatch: bool | None = None,
        allow_layer_mismatch: bool | None = None,
        allow_type_mismatch: bool | None = None,
        use_mirror: bool | None = None,
        use_angle: bool | None = None,
    ) -> None: ...

    @overload
    def connect(
        self,
        port: str | ProtoPort[Any] | None,
        other: VInstance,
        other_port_name: str | int | None,
        *,
        mirror: bool = False,
        allow_width_mismatch: bool | None = None,
        allow_layer_mismatch: bool | None = None,
        allow_type_mismatch: bool | None = None,
        use_mirror: bool | None = None,
        use_angle: bool | None = None,
    ) -> None: ...

    def connect(
        self,
        port: str | ProtoPort[Any] | None,
        other: ProtoInstance[Any] | ProtoPort[Any],
        other_port_name: str | int | tuple[int | str, int, int] | None = None,
        *,
        mirror: bool = False,
        allow_width_mismatch: bool | None = None,
        allow_layer_mismatch: bool | None = None,
        allow_type_mismatch: bool | None = None,
        use_mirror: bool | None = None,
        use_angle: bool | None = None,
    ) -> None:
        """Align port with name `portname` to a port.

        Function to allow to transform this instance so that a port of this instance is
        connected (same center with 180° turn) to another instance.

        Args:
            port: The name of the port of this instance to be connected, or directly an
                instance port. Can be `None` because port names can be `None`.
            other: The other instance or a port. Skip `other_port_name` if it's a port.
            other_port_name: The name of the other port. Ignored if
                `other` is a port.
            mirror: Instead of applying klayout.db.Trans.R180 as a connection
                transformation, use klayout.db.Trans.M90, which effectively means this
                instance will be mirrored and connected.
            allow_width_mismatch: Skip width check between the ports if set.
            allow_layer_mismatch: Skip layer check between the ports if set.
            allow_type_mismatch: Skip port_type check between the ports if set.
            use_mirror: If False mirror flag does not get applied from the connection.
            use_angle: If False the angle does not get applied from the connection.
        """
        if allow_layer_mismatch is None:
            allow_layer_mismatch = config.allow_layer_mismatch
        if allow_width_mismatch is None:
            allow_width_mismatch = config.allow_width_mismatch
        if allow_type_mismatch is None:
            allow_type_mismatch = config.allow_type_mismatch
        if use_mirror is None:
            use_mirror = config.connect_use_mirror
        if use_angle is None:
            use_angle = config.connect_use_angle
        if isinstance(other, ProtoInstance):
            if other_port_name is None:
                raise ValueError(
                    "portname cannot be None if an Instance Object is given. For"
                    "complex connections (non-90 degree and floating point ports) use"
                    "route_cplx instead"
                )
            op = Port(base=other.ports[other_port_name].base)  # type: ignore[index]
        else:
            op = Port(base=other.base)
        if isinstance(port, ProtoPort):
            p = port.copy(self.trans.inverted()).to_itype()
        else:
            p = self.cell.ports[port].to_itype()

        assert isinstance(p, Port)
        assert isinstance(op, Port)

        if p.width != op.width and not allow_width_mismatch:
            raise PortWidthMismatchError(self, other, p, op)
        if p.layer != op.layer and not allow_layer_mismatch:
            raise PortLayerMismatchError(self.cell.kcl, self, other, p, op)
        if p.port_type != op.port_type and not allow_type_mismatch:
            raise PortTypeMismatchError(self, other, p, op)
        dconn_trans = kdb.DCplxTrans.M90 if mirror else kdb.DCplxTrans.R180
        match (use_mirror, use_angle):
            case True, True:
                trans = op.dcplx_trans * dconn_trans * p.dcplx_trans.inverted()
                self.trans = trans
            case False, True:
                dconn_trans = (
                    kdb.DCplxTrans.M90
                    if mirror ^ self.trans.mirror
                    else kdb.DCplxTrans.R180
                )
                opt = op.dcplx_trans
                opt.mirror = False
                dcplx_trans = opt * dconn_trans * p.dcplx_trans.inverted()
                self.trans = dcplx_trans
            case False, False:
                self.trans = kdb.DCplxTrans(op.dcplx_trans.disp - p.dcplx_trans.disp)
            case True, False:
                self.trans = kdb.DCplxTrans(op.dcplx_trans.disp - p.dcplx_trans.disp)
                self.mirror_y(op.dcplx_trans.disp.y)
            case _:
                ...

    def transform(
        self,
        trans: kdb.Trans | kdb.DTrans | kdb.ICplxTrans | kdb.DCplxTrans,
        /,
    ) -> None:
        if isinstance(trans, kdb.Trans):
            trans = trans.to_dtype(self.kcl.dbu)
        self.trans = kdb.DCplxTrans(trans) * self.trans
