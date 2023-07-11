"""CLI interface for kfactory.

Use `kf --help` for more info.
"""
import click

from .. import __version__
from ..conf import LogLevel, config
from .runshow import run, show


@click.group(  # type: ignore[arg-type]
    context_settings=dict(help_option_names=["-h", "--help"])
)
@click.version_option(version=str(__version__))
@click.option(
    "--level",
    "-l",
    default="INFO",
    help="Log level to use for kfactory, see "
    "https://gdsfactory.github.io/kfactory/config/#log-level for more info",
)
def kf(level: str) -> None:
    """CLI interface for kfactory."""
    config.logfilter.level = LogLevel[level]


kf.add_command(run)  # type: ignore[attr-defined]
kf.add_command(show)  # type: ignore[attr-defined]


# @kf.command()  # type: ignore[attr-defined, misc, arg-type]
# @click.argument(
#     "file",
#     required=True,
#     type=str,
#     # help="Path to the file to load/reload in KLayout with running klive",
# )
# def show(arg: str, type_: str) -> None:
#     """Show a GDS or OAS file in KLayout through klive."""
#     path = Path(arg)
#     logger.debug("Path = {}", path.resolve())
#     if not path.exists():
#         logger.critical("{type_} does not exist, exiting", type_=type_)
#         return
#     if not path.is_file():
#         logger.critical("{type_} is not a file, exiting", type_=type_)
#         return
#     if not os.access(path, os.R_OK):
#         logger.critical("No permission to read file {type_}, exiting", type_=type_)
#         return
#     kfshow(path)


# @kf.command(  # type: ignore[attr-defined, misc, arg-type]
#     context_settings={"ignore_unknown_options": True, "allow_extra_args": True}
# )
# @click.option(
#     "--file",
#     "type_",
#     flag_value="file",
#     help="Run __main__ of a python file",
#     default=True,
#     show_default=True,
# )
# @click.option(
#     "--module",
#     "type_",
#     flag_value="module",
#     help="Run __main__ of a module",
#     show_default=True,
# )
# @click.option(
#     "--function",
#     "type_",
#     flag_value="function",
#     show_default=True,
# )
# @click.argument(
#     "arg",
#     required=True,
#     type=str,
#     # help="Python style module or function to run, e.g 'module.function'",
# )
# @click.pass_context
# def run(
#     ctx: click.Context,
#     arg: str,
#     type_: str,
# ) -> None:
#     """Run a python modules __main__ or a function if specified."""
#     path = sys.path.copy()
#     sys.path.append(os.getcwd())
#     match type_:
#         case "file":
#             runpy.run_path(arg, run_name="__main__")
#         case "module":
#             runpy.run_module(arg, run_name="__main__")
#         case "function":
#             mod, func = arg.rsplit(".", 1)
#             logger.debug(f"{mod=},{func=}")
#             try:
#                 spec = importlib.util.find_spec(mod)
#                 if spec is None or spec.loader is None:
#                     raise ImportError
#                 _mod = importlib.util.module_from_spec(spec)
#                 sys.modules[mod] = _mod
#                 spec.loader.exec_module(_mod)
#                 kwargs = {}

#                 old_arg = ""
#                 for i, arg in enumerate(ctx.args):
#                     if i % 2:
#                         try:
#                             value: int | float | str = int(arg)
#                         except ValueError:
#                             try:
#                                 value = float(arg)
#                             except ValueError:
#                                 value = arg
#                         kwargs[old_arg] = value
#                     else:
#                         old_arg = arg

#                 getattr(_mod, func)(**kwargs)
#             except ImportError:
#                 logger.critical(
#                     f"Couldn't import function '{func}' from module '{mod}'"
#                 )
#     sys.path = path
