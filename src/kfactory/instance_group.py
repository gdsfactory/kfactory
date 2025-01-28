class ProtoInstanceGroup(Generic[TUnit, TInstance], GeometricObject[TUnit]):
    insts: list[TInstance]

    def __init__(self, insts: Sequence[TInstance]) -> None:
        """Initialize the InstanceGroup."""
        self.insts = list(insts)

    @property
    def kcl(self) -> KCLayout:
        try:
            return self.insts[0].kcl
        except IndexError as e:
            raise ValueError(
                "Cannot transform or retrieve the KCLayout "
                "of an instance group if it's empty"
            ) from e

    @kcl.setter
    def kcl(self, val: KCLayout) -> NoReturn:
        raise ValueError("KCLayout cannot be set on an instance group.")

    def transform(
        self, trans: kdb.Trans | kdb.DTrans | kdb.ICplxTrans | kdb.DCplxTrans
    ) -> None:
        """Transform the instance group."""
        for inst in self.insts:
            inst.transform(trans)

    def ibbox(self, layer: int | None = None) -> kdb.Box:
        """Get the total bounding box or the bounding box of a layer in dbu."""
        bb = kdb.Box()
        for _bb in (inst.ibbox(layer) for inst in self.insts):
            bb += _bb
        return bb

    def dbbox(self, layer: int | None = None) -> kdb.DBox:
        """Get the total bounding box or the bounding box of a layer in um."""
        bb = kdb.DBox()
        for _bb in (inst.dbbox(layer) for inst in self.insts):
            bb += _bb
        return bb


class InstanceGroup(ProtoInstanceGroup[int, Instance], DBUGeometricObject):
    """Group of Instances.

    The instance group can be treated similar to a single instance
    with regards to transformation functions and bounding boxes.

    Args:
        insts: List of the instances of the group.
    """

    ...


class DInstanceGroup(ProtoInstanceGroup[float, DInstance], UMGeometricObject):
    """Group of DInstances.

    The instance group can be treated similar to a single instance
    with regards to transformation functions and bounding boxes.

    Args:
        insts: List of the dinstances of the group.
    """


class VInstanceGroup(ProtoInstanceGroup[float, VInstance], UMGeometricObject):
    """Group of DInstances.

    The instance group can be treated similar to a single instance
    with regards to transformation functions and bounding boxes.

    Args:
        insts: List of the vinstances of the group.
    """
