from typing import Any

import kfactory as kf

from .kcell import KCell
from .typs import ComponentSpec


def get_component(component_spec: ComponentSpec, **kwargs: Any) -> KCell:
    if isinstance(component_spec, str):
        try:
            return getattr(kf.pcells, component_spec)(**kwargs)  # type: ignore
        except KeyError:
            raise ValueError(
                f"Invalid component_spec: {component_spec}. "
                "Must be a valid pcell name."
            )
    elif isinstance(component_spec, KCell):
        return component_spec
    elif isinstance(component_spec, dict):
        component_spec.update(kwargs)
        return KCell(**component_spec)
    elif callable(component_spec):
        return component_spec(**kwargs)
    else:
        raise ValueError(
            f"Invalid component_spec: {component_spec}. "
            "Must be a string, a dict, a KCell, or a callable."
        )
