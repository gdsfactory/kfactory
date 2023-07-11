"""CLI interface for kfactory.

Use `kf --help` for more info.
"""
import importlib
import os
import runpy
import sys
from pathlib import Path

import click
from pydantic import BaseModel

from ..conf import logger
from ..kcell import KCell
from ..kcell import show as kfshow


class Gds(BaseModel):
    filepath: str


@click.group()
def sea() -> None:
    pass


@click.command()
def upload() -> None:
    pass
