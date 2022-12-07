try:
    from ._version import version as __version__
    from ._version import version_tuple
except ImportError:
    __version__ = "unknown version"
    version_tuple = (0, 0, "unknown version")  # type: ignore[assignment]


# The import order matters, we need to first import the important stuff
from .kcell import *  # isort: skip

# now we can import the other stuff
from . import kdb, pcells, placer, routing, utils
from .utils import show as show

# import klayout.lay as klay #<- enable when klayout > 0.28
