from pathlib import Path

from kfactory.technology.layer_views import LayerViews

from ..typings import PathType


def lyp_to_dataclass(lyp_filepath: PathType, overwrite: bool = True) -> str:
    """Returns python LayerMap script from a klayout layer properties file lyp."""
    filepathin = Path(lyp_filepath)
    filepathout = filepathin.with_suffix(".py")

    if filepathout.exists() and not overwrite:
        raise FileExistsError(f"You must delete {filepathout} or set overwrite=True")

    script = """
from pydantic import BaseModel
from kfactory.typings import Layer


class LayerMap(BaseModel):
"""
    lys = LayerViews.from_lyp(filepathin)
    for layer_name, layer in sorted(lys.get_layer_views().items()):
        script += f"    {layer_name}: Layer = ({layer.layer[0]}, {layer.layer[1]})\n"

    script += """
    class Config:
        frozen = True
        extra = "forbid"


LAYER = LayerMap()
"""

    filepathout.write_text(script)
    return script
