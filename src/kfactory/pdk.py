from __future__ import annotations

import hashlib
import pathlib
from copy import deepcopy
from functools import partial
from pathlib import Path
from typing import Any, Optional

import numpy as np

import kfactory as kf
from kfactory.kcell import clean_value
from kfactory.technology import LayerStack
from kfactory.typings import ComponentSpec


def get_kwargs_hash(**kwargs: Any) -> str:
    """Returns kwargs parameters hash."""
    kwargs_list = [f"{key}={clean_value(kwargs[key])}" for key in sorted(kwargs.keys())]
    kwargs_string = "_".join(kwargs_list)
    return hashlib.md5(kwargs_string.encode()).hexdigest()[:8]


def _get_sparameters_path(
    component: kf.KCell,
    dirpath: Optional[Path] = None,
    **kwargs: Any,
) -> Path:
    """Return Sparameters npz filepath hashing simulation settings for \
            a consistent unique name.

    Args:
        component: component or component factory.
        dirpath: directory to store sparameters in CSV.
            Defaults to active Pdk.sparameters_path.
        kwargs: simulation settings.

    """
    dirpath_ = dirpath or get_sparameters_path()
    # component = f.get_component(component)

    dirpath = pathlib.Path(dirpath_)
    dirpath = (
        dirpath / component.function_name
        if hasattr(component, "function_name")
        else dirpath
    )
    dirpath.mkdir(exist_ok=True, parents=True)
    return dirpath / f"{component.hash().hex()}_{get_kwargs_hash(**kwargs)}.npz"


def _get_sparameters_data(
    component: ComponentSpec, **kwargs: Any
) -> np.ndarray[str, np.dtype[Any]]:
    """Returns Sparameters data in a pandas DataFrame.

    Keyword Args:
        component: component.
        dirpath: directory path to store sparameters.
        kwargs: simulation settings.

    """
    component = kf.get_component(component)
    kwargs.update(component=component)
    filepath = _get_sparameters_path(component=component, **kwargs)
    return np.ndarray(np.load(filepath))


get_sparameters_path_meow = partial(_get_sparameters_path, tool="meow")

get_sparameters_path_meep = partial(_get_sparameters_path, tool="meep")
get_sparameters_path_lumerical = partial(_get_sparameters_path, tool="lumerical")
get_sparameters_path_tidy3d = partial(_get_sparameters_path, tool="tidy3d")

get_sparameters_data_meep = partial(_get_sparameters_data, tool="meep")
get_sparameters_data_lumerical = partial(_get_sparameters_data, tool="lumerical")
get_sparameters_data_tidy3d = partial(_get_sparameters_data, tool="tidy3d")


if __name__ == "__main__":
    # c = kf.pcells.taper(length=1.0, width1=0.5, width2=0.5, layer=1)
    # p = get_sparameters_path_lumerical(c)

    # sp = np.load(p)
    # spd = dict(sp)
    # print(spd)

    # test_get_sparameters_path(test=False)
    # test_get_sparameters_path(test=True)
    print("")
