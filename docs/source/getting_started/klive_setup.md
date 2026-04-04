# KLive Setup

[klive](https://github.com/gdsfactory/klive) is a KLayout plug-in that lets kfactory push GDS
files directly into a running KLayout window. Every call to `kf.show(cell)` will open or refresh
the layout instantly — no manual file export required.

## Install klive from KLayout

Open the KLayout package manager under **Tools → Manage Packages**, search for **klive**, and
click Install.

The video below shows the process:

![type:video](../_static/klive.webm)

## How klive works

klive listens on **localhost:8082**. When you call `kf.show(cell)`, kfactory:

1. Exports the cell to a temporary GDS file.
2. Sends a JSON message to port 8082 with the file path.
3. klive loads (or reloads) the file in the open KLayout window.

## Tip: disable KLayout's file-reload dialog

KLayout occasionally shows a "file changed on disk" dialog that can interfere with klive.
Turn it off in **File → Setup → Application → General** by unchecking
**Check files for updates**.

## See Also

| Topic | Where |
|-------|-------|
| Prerequisites (Python, KLayout) | [Getting Started: Prerequisites](prerequisites.md) |
| Installing kfactory | [Getting Started: Installation](installation.md) |
| 5-minute quickstart | [Getting Started: Quickstart](quickstart.py) |
