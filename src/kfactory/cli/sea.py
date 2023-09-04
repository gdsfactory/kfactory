"""CLI interface for kfactory.

Use `kf sea --help` for more info.
"""
import json
from pathlib import Path
from typing import Annotated, Optional

import requests
import rich
import typer

from ..kcell import KCLayout

app = typer.Typer(name="sea")


@app.command()
def upload(
    file: str,
    name: Optional[str] = None,  # noqa: UP007
    description: Optional[str] = None,  # noqa: UP007
    base_url: Annotated[
        str, typer.Option(envvar="GDATASEA_URL")
    ] = "http://localhost:3131",
) -> None:
    """Upload a new project to gdatasea."""
    if name is None:
        kcl = KCLayout("SeaUpload")
        kcl.read(file)
        assert len(kcl.top_cells()) > 0, (
            "Cannot automatically determine name of gdatasea edafile if"
            " there is no name given and the gds is empty"
        )
        name = kcl.top_cells()[0].name

    url = f"{base_url}/project"
    if description:
        params = {"name": name, "description": description}
    else:
        params = {"name": name}

    fp = Path(file)
    assert fp.exists()
    with open(fp, "rb") as f:
        r = requests.post(url, params=params, files={"eda_file": f})
        msg = f"Response from {url}: "
        try:
            msg += rich.pretty.pretty_repr(json.loads(r.text))
            msg = msg.replace("'success': 200", "[green]success: 200[/green]").replace(
                "422", "[red]422[/red]"
            )
        except json.JSONDecodeError:
            msg += rich.pretty.pretty_repr(f"[red]{r.text}[/red]")
        rich.print(msg)


@app.command()
def update(
    file: str,
    project_id: Annotated[int, typer.Option("--project_id", "--id", "-id")],
    name: Optional[str] = None,  # noqa: UP007
    description: Optional[str] = None,  # noqa: UP007
    base_url: Annotated[
        str, typer.Option(envvar="GDATASEA_URL")
    ] = "http://localhost:3131",
) -> None:
    """Update a project on gdatasea."""
    if name is None:
        kcl = KCLayout("SeaUpdate")
        kcl.read(file)
        assert len(kcl.top_cells()) > 0, (
            "Cannot automatically determine name of gdatasea edafile if"
            " there is no name given and the gds is empty"
        )
        name = kcl.top_cells()[0].name

    url = f"{base_url}/project/{project_id}"
    params = {"name": name}
    if description:
        params["description"] = description

    fp = Path(file)
    assert fp.exists()
    with open(fp, "rb") as f:
        r = requests.put(url, params=params, files={"eda_file": f})
        msg = f"Response from {url}: "
        try:
            msg += rich.pretty.pretty_repr(json.loads(r.text))
            msg = msg.replace("'success': 200", "[green]success: 200[/green]").replace(
                "422", "[red]422[/red]"
            )
        except json.JSONDecodeError:
            msg += rich.pretty.pretty_repr(f"[red]{r.text}[/red]")
        rich.print(msg)
