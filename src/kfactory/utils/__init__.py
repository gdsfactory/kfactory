import builtins
import json
import os
import socket
import warnings
from pathlib import Path
from tempfile import gettempdir

from .. import kcell, kdb
from . import violations
from .enclosure import Direction, Enclosure

try:
    from __main__ import __file__ as mf
except ImportError:
    mf = "shell"


def show(
    gds: str | kcell.KCell | Path,
    keep_position: bool = True,
    save_options: kdb.SaveLayoutOptions = kcell.default_save(),  # type: ignore[attr-defined]
) -> None:
    """Show GDS in klayout"""

    delete = False

    match gds:
        case str():
            gds_file = Path(gds)
        case kcell.KCell(library=kcell.KLib()):
            if mf == "<stdin>":
                _mf = "stdin"
            else:
                _mf = mf
            tf = Path(gettempdir()) / Path(_mf).with_suffix(".gds")
            gds.write(str(tf), save_options)
            gds_file = tf
            delete = True
        case _:
            if isinstance(gds, Path):
                gds_file = gds
            else:
                raise NotImplementedError(
                    f"unknown type {type(gds)} for streaming to KLayout"
                )

    if not gds_file.is_file():
        raise ValueError(f"{gds_file} does not exist")
    data_dict = {
        "gds": str(gds_file),
        "keep_position": keep_position,
    }
    data = json.dumps(data_dict)
    try:
        conn = socket.create_connection(("127.0.0.1", 8082), timeout=0.5)
        data = data + "\n"
        enc_data = data.encode()  # if hasattr(data, "encode") else data
        conn.sendall(enc_data)
        conn.settimeout(5)
    except OSError:
        warnings.warn("Could not connect to klive server", UserWarning)
    else:
        msg = ""
        try:
            msg = conn.recv(1024).decode("utf-8")
            print("Message from klive:")
            print(msg)
        except OSError:
            print("klive didn't send data, closing")
        finally:
            conn.close()

    if delete:
        Path(gds_file).unlink()


__all__ = ["show", "Enclosure", "violations", "Direction"]
