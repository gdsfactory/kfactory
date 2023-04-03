"""Write Sparameters with Lumerical FDTD."""
from __future__ import annotations

import itertools
import shutil
import time

# import gdsfactory as gf
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import omegaconf

import kfactory as kf

from ..config import logger
from ..generic_tech import LayerStack
from ..materials import MaterialSpec
from ..pdk import get_layer_stack
from ..simulation.get_sparameters_path import (
    get_sparameters_path_lumerical as get_sparameters_path,
)
from ..typs import ComponentSpec, PathType
from .simulation_settings import (
    SIMULATION_SETTINGS_LUMERICAL_FDTD,
    SimulationSettingsLumericalFdtd,
)

run_false_warning = """
You have passed run=False to debug the simulation

run=False returns the simulation session for you to debug and make sure it is correct

To compute the Sparameters you need to pass run=True
"""


def set_material(session, structure: str, material: MaterialSpec) -> None:  # type: ignore
    """Sets the material of a structure.

    Args:
        session: lumerical session.
        structure: name of the lumerical structure.
        material: material spec, can be
            a string from lumerical database materials.
            a float or int, representing refractive index.
            a complex for n, k materials.

    """
    if isinstance(material, str):
        session.setnamed(structure, "material", material)
    elif isinstance(material, (int, float)):
        session.setnamed(structure, "index", material)
    elif isinstance(material, complex):
        mat = session.addmaterial("(n,k) Material")
        session.setmaterial(mat, "Refractive Index", material.real)
        session.setmaterial(mat, "Imaginary Refractive Index", material.imag)
        session.setnamed(structure, "material", mat)
    elif isinstance(material, (tuple, list)):
        if len(material) != 2:
            raise ValueError(
                "Complex material requires a tuple or list of two numbers "
                f"(real, imag). Got {material} "
            )
        real, imag = material
        mat = session.addmaterial("(n,k) Material")
        session.setmaterial(mat, "Refractive Index", real)
        session.setmaterial(mat, "Imaginary Refractive Index", imag)
        session.setnamed(structure, "material", mat)
    else:
        raise ValueError(
            f"{material!r} needs to be a float refractive index, a complex number or tuple "
            "or a string from lumerical's material database"
        )

    return None


def plot_sparameters_lumerical(
    component: kf.KCell,
    layer_stack: LayerStack = get_layer_stack(),
    session: Optional[object] = None,
    run: bool = True,
    overwrite: bool = False,
    dirpath: Optional[PathType] = None,
    simulation_settings: SimulationSettingsLumericalFdtd = SIMULATION_SETTINGS_LUMERICAL_FDTD,
    material_name_to_lumerical: Optional[Dict[str, MaterialSpec]] = None,
    delete_fsp_files: bool = True,
    solver: str = "FDTD",
    input_port: str = "o1",
    output_port: str = "o2",
    **settings: Any,
) -> str:
    """Plots and returns component s-parameters using Lumerical INTERCONNECT.

    If simulation exists it returns the Sparameters directly unless overwrite=True
    which forces a re-run of the simulation

    Writes s-parameters in both .npz and .csv format.

    In the npz format you can see `S12m` where `m` stands for magnitude
    and `S12a` where `a` stands for angle in radians

    Your components need to have ports, that will extend over the PML.

    For your Fab technology you can overwrite

    - simulation_settings
    - dirpath
    - layerStack

    converts gdsfactory units (um) to Lumerical units (m)

    Disclaimer: This function tries to extract Sparameters automatically
    is hard to make a function that will fit all your possible simulation settings.
    You can use this function for inspiration to create your own.

    Args:
        component: kfactory component
        layer_stack: kfactory layer stack
        session: lumerical session
        run: if True runs the simulation
        overwrite: if True overwrites the simulation
        dirpath: directory where to write the simulation files
        simulation_settings: simulation settings
        material_name_to_lumerical: dictionary with material names
        delete_fsp_files: if True deletes the .fsp files
        solver: FDTD or MODE
        settings: simulation settings

    Returns:
        result file path

    """

    s_params = []
    insts = []
    trans = []

    component = kf.get_component(component)

    def recurse_insts(comp: kf.KCell, p=None):  # type: ignore
        if p:
            comp.transform(p)
        for inst in comp.insts:
            if inst.trans in trans:
                continue
            if inst.cell.name == component.name:
                continue
            if len(inst.cell.insts) > 0:
                if "sim" in inst.cell.info:
                    trans.append(inst.trans)
                    insts.append(inst)
                    continue
                recurse_insts(inst.cell.dup(), inst.instance.trans)  # type: ignore
            else:
                insts.append(inst)
                trans.append(inst.trans)

    if "sim" not in component.info and "sparameters" not in component.info:
        recurse_insts(component)
    paths: dict[str, Path] = {}
    for inst in insts:
        # paths = {}
        component_ = inst.cell
        if not overwrite:
            if "sparameters" in component_.info:
                path = Path(component_.info["sparameters"])
                if path.exists():
                    s_params.append(path)
                    paths[component_.name] = path
                    continue
            if "components" in component_.info:
                paths = {}
                for component2 in component_.info["components"]:
                    settings_ = component_.info["components"][component2]
                    component_2 = kf.get_component(
                        settings_["component"], **settings_["params"]
                    )
                    path = get_sparameters_path(
                        component_2,
                        dirpath=dirpath,
                        layer_stack=layer_stack or get_layer_stack(),
                        **settings,
                    )
                    if overwrite or not path.exists():
                        try:
                            component_solver = component_.info["components"][
                                component2
                            ]["sim"]
                        except KeyError:
                            component_solver = solver
                        s_params.append(
                            write_sparameters_lumerical(
                                component=component_2,
                                layer_stack=layer_stack,
                                session=session,
                                run=run,
                                overwrite=overwrite,
                                dirpath=dirpath,
                                simulation_settings=simulation_settings,
                                material_name_to_lumerical=material_name_to_lumerical,
                                delete_fsp_files=delete_fsp_files,
                                solver=component_solver,
                                **settings,
                            )
                        )
                    paths[component_2.name] = path

            else:
                print("Simulation exists", component_.name)
                path = get_sparameters_path(
                    component_,
                    dirpath=dirpath,
                    layer_stack=layer_stack or get_layer_stack(),
                    **settings,
                )
                if path.exists():
                    s_params.append(np.load(path))
                    paths[component_.name] = path
                else:
                    s_params.append(
                        write_sparameters_lumerical(
                            component=component_,  # type: ignore
                            layer_stack=layer_stack,
                            session=session,
                            run=run,
                            overwrite=overwrite,
                            dirpath=dirpath,
                            simulation_settings=simulation_settings,
                            material_name_to_lumerical=material_name_to_lumerical,
                            delete_fsp_files=delete_fsp_files,
                            solver=solver,
                            **settings,
                        )
                    )
                paths[component_.name] = path
        else:
            s_params.append(
                write_sparameters_lumerical(
                    component=component_,  # type: ignore
                    layer_stack=layer_stack,
                    session=session,
                    run=run,
                    overwrite=overwrite,
                    dirpath=dirpath,
                    simulation_settings=simulation_settings,
                    material_name_to_lumerical=material_name_to_lumerical,
                    delete_fsp_files=delete_fsp_files,
                    solver=solver,
                    **settings,
                )
            )
            paths[component_.name] = get_sparameters_path(
                component_,
                dirpath=dirpath,
                layer_stack=layer_stack or get_layer_stack(),
                **settings,
            )
    if len(s_params) > 1:
        try:
            import sys

            sys.path.append("C:\\Program Files\\Lumerical\\v231\\api\\python\\")
            import lumapi  # type: ignore
        except ModuleNotFoundError as e:
            print(
                "Cannot import lumapi (Python Lumerical API). "
                "You can add set the PYTHONPATH variable or add it with `sys.path.append()`"
            )
            raise e
        except OSError as e:
            raise e
        s = lumapi.INTERCONNECT()
        s.switchtodesign()
        s.clear()
        s.deleteall()
        s.addelement("Optical Network Analyzer")
        s.set("name", "ONA")
        s.set("number of input ports", len(component.ports.get_all()) - 1)
        s.set("input parameter", 2)
        s.set("start frequency", 3e8 / simulation_settings.wavelength_stop / 1e-6)
        s.set("stop frequency", 3e8 / simulation_settings.wavelength_start / 1e-6)
        s.set("number of points", simulation_settings.wavelength_points)
        components: dict[tuple[float, float], Any] = {}
        for instance in insts:
            for port in instance.ports.get_all().values():
                if port.center in components:
                    components[port.center].update(
                        {port: port.name, "instance2": instance}
                    )
                else:
                    components[port.center] = {port: port.name, "instance1": instance}

        inputs: List[Any] = []
        input = input_port
        outputs: List[Any] = []
        output = output_port
        for value in components.values():
            inv_comp = False
            instances = (
                [value["instance1"], value["instance2"]]
                if "instance2" in value
                else [value["instance1"]]
            )
            for i, instance in enumerate(instances):
                if instance.cell.name not in paths:
                    value[f"instance{i+1}"] = None
                    for key, val in value.items():
                        if key in instance.ports.get_all().values():
                            value[key] = None
                            value.pop(key)
                    inv_comp = True
                    instances.remove(instance)
                    continue
                if paths[instance.cell.name].with_suffix('.ldf').exists():
                    s.addelement("MODE Waveguide")
                    s.setnamed(f"MODE_1", "name", f"{instance.cell.name, instance.hash()}")
                    s.setnamed(
                        f"{instance.cell.name, instance.hash()}", "load from file", True
                    )
                    s.setnamed(
                        f"{instance.cell.name, instance.hash()}",
                        "mode filename",
                        paths[instance.cell.name].with_suffix('.ldf').as_posix(),
                    )
                else:
                    s.addelement("Optical N Port S-Parameter")
                    s.setnamed(f"SPAR_1", "name", f"{instance.cell.name, instance.hash()}")
                    s.setnamed(
                        f"{instance.cell.name, instance.hash()}", "load from file", True
                    )
                    filepath_component = get_sparameters_path(
                        instance, dirpath=dirpath, simulation_settings=simulation_settings
                    )
                    s.setnamed(
                        f"{instance.cell.name, instance.hash()}",
                        "s parameters filename",
                        paths[instance.cell.name].as_posix().replace(".npz", ".dat"),
                    )
                s.setnamed(
                    f"{instance.cell.name, instance.hash()}",
                    "x position",
                    instance.instance.dbbox().center().x * 100,
                )
                s.setnamed(
                    f"{instance.cell.name, instance.hash()}",
                    "y position",
                    instance.instance.dbbox().center().y * 100,
                )

            if inv_comp:
                continue
            ports = [
                value[port]
                for port in value
                if port is not None and port != "instance1" and port != "instance2"
            ]
            ports_ = [
                port
                for port in value
                if port is not None and port != "instance1" and port != "instance2"
            ]
            # ports.remove(None) if None in ports else None
            if len(ports) > 1 and ports[1] not in [
                p.name for p in instances[1].ports.get_all().values()
            ]:
                ports = ports[::-1]
            # if "components" in component.info:
            # for component_ in component.info["components"]:
            #     component__ = component.info["components"][component_]["component"]
            #     settings__ = component.info["components"][component_]["params"]
            #     print(kf.get_component(component__, **settings__).name)
            if len(instances) == 2:
                s.connect(
                    f"{instances[0].cell.name, instances[0].hash()}",
                    ports[0],
                    f"{instances[1].cell.name, instances[1].hash()}",
                    ports[1],
                )
            else:
                print(component.ports, value)
                input_port = (
                    ports[0]
                    if input_port in component.ports.get_all().keys()
                    and ports_[0].center == component.ports[input_port].center
                    else input
                )
                output_port = (
                    ports[0]
                    if output_port in component.ports.get_all().keys()
                    and ports_[0].center == component.ports[output_port].center
                    else output
                )
                inputs = [instances[0], input_port] if input != input_port else inputs
                outputs = (
                    [instances[0], output_port] if output != output_port else outputs
                )
        s.connect(
            "ONA",
            f"input 1",
            f"{inputs[0].cell.name, inputs[0].hash()}",
            f"{inputs[1]}",
        )
        path3 = get_sparameters_path(
            component, dirpath=dirpath, simulation_settings=simulation_settings
        )
        s.save(path3.as_posix().replace(".npz", ".ice"))
        s.connect(
            "ONA",
            "output",
            f"{outputs[0].cell.name, outputs[0].hash()}",
            f"{outputs[1]}",
        )
        s.run()
        s.save(path3.as_posix().replace(".npz", ".ice"))

        s.exportcsvresults(path3.as_posix().replace(".npz", ".csv"))

        return path3.as_posix().replace(".npz", "/ONA.csv")


def write_sparameters_lumerical(
    component: ComponentSpec,
    layer_stack: LayerStack = get_layer_stack(),
    session: Optional[object] = None,
    run: bool = True,
    overwrite: bool = False,
    dirpath: Optional[PathType] = None,
    simulation_settings: SimulationSettingsLumericalFdtd = SIMULATION_SETTINGS_LUMERICAL_FDTD,
    material_name_to_lumerical: Optional[Dict[str, MaterialSpec]] = None,
    delete_fsp_files: bool = True,
    solver: str = "FDTD",
    **settings: Any,
) -> np.ndarray[str, np.dtype[Any]] | Any:
    r"""Returns and writes component Sparameters using Lumerical FDTD.

    If simulation exists it returns the Sparameters directly unless overwrite=True
    which forces a re-run of the simulation

    Writes Sparameters both in .npz and .DAT (interconnect format) as well as
    simulation settings in .YAML

    In the npz format you can see `S12m` where `m` stands for magnitude
    and `S12a` where `a` stands for angle in radians

    Your components need to have ports, that will extend over the PML.

    .. image:: https://i.imgur.com/dHAzZRw.png

    For your Fab technology you can overwrite

    - simulation_settings
    - dirpath
    - layerStack

    converts gdsfactory units (um) to Lumerical units (m)

    Disclaimer: This function tries to extract Sparameters automatically
    is hard to make a function that will fit all your possible simulation settings.
    You can use this function for inspiration to create your own.


    TODO:
        mode_selection

    Args:
        component: Component to simulate.
        session: you can pass a session=lumapi.FDTD() or it will create one.
        run: True runs Lumerical, False only draws simulation.
        overwrite: run even if simulation results already exists.
        dirpath: directory to store sparameters in npz.
            Defaults to active Pdk.sparameters_path.
        layer_stack: contains layer to thickness, zmin and material.
            Defaults to active pdk.layer_stack.
        simulation_settings: dataclass with all simulation_settings.
        material_name_to_lumerical: alias to lumerical material's database name
            or refractive index.
            translate material name in LayerStack to lumerical's database name.
        delete_fsp_files: deletes lumerical fsp files after simulation.

    Keyword Args:
        background_material: for the background.
        port_margin: on both sides of the port width (um).
        port_height: port height (um).
        port_extension: port extension (um).
        mesh_accuracy: 2 (1: coarse, 2: fine, 3: superfine).
        zmargin: for the FDTD region (um).
        ymargin: for the FDTD region (um).
        xmargin: for the FDTD region (um).
        wavelength_start: 1.2 (um).
        wavelength_stop: 1.6 (um).
        wavelength_points: 500.
        simulation_time: (s) related to max path length 3e8/2.4*10e-12*1e6 = 1.25mm.
        simulation_temperature: in kelvin (default = 300).
        frequency_dependent_profile: computes mode profiles for different wavelengths.
        field_profile_samples: number of wavelengths to compute field profile.



    .. code::

         top view
              ________________________________
             |                               |
             | xmargin                       | port_extension
             |<------>          port_margin ||<-->
          o2_|___________          _________||_o3
             |           \        /          |
             |            \      /           |
             |             ======            |
             |            /      \           |
          o1_|___________/        \__________|_o4
             |   |                           |
             |   |ymargin                    |
             |   |                           |
             |___|___________________________|

        side view
              ________________________________
             |                               |
             |                               |
             |                               |
             |ymargin                        |
             |<---> _____         _____      |
             |     |     |       |     |     |
             |     |     |       |     |     |
             |     |_____|       |_____|     |
             |       |                       |
             |       |                       |
             |       |zmargin                |
             |       |                       |
             |_______|_______________________|



    Return:
        Sparameters np.ndarray (wavelengths, o1@0,o1@0, o1@0,o2@0 ...)
            suffix `a` for angle in radians and `m` for module.

    """
    s_params = []
    insts = []
    trans = []
    component = kf.get_component(component)

    def recurse_insts(comp: Any, p=None):  # type: ignore
        if p:
            comp.transform(p)
        for inst in comp.insts:
            if inst.trans in trans:
                continue
            if inst.cell.name == component.name:  # type: ignore
                continue
            if len(inst.cell.insts) > 0:
                if "sim" in inst.cell.info:
                    trans.append(inst.trans)
                    insts.append(inst)
                    continue
                recurse_insts(inst.cell.dup(), inst.instance.trans)
            else:
                insts.append(inst)
                trans.append(inst.trans)

    if "sim" not in component.info:
        recurse_insts(component)
    paths: dict[str, Path] = {}
    for inst in insts:
        component_ = inst.cell
        # paths = {}
        if not overwrite:
            if "components" in component_.info:
                paths = {}
                for component2 in component_.info["components"]:
                    settings_ = component_.info["components"][component2]
                    component_2 = kf.get_component(
                        settings_["component"], **settings_["params"]
                    )
                    path = get_sparameters_path(
                        component_2,
                        dirpath=dirpath,
                        layer_stack=layer_stack or get_layer_stack(),
                        **settings,
                    )
                    if overwrite or not path.exists():
                        try:
                            component_solver = component_.info["components"][
                                component2
                            ]["sim"]
                        except KeyError:
                            component_solver = solver
                        s_params.append(
                            write_sparameters_lumerical(
                                component=component_2,
                                layer_stack=layer_stack,
                                session=session,
                                run=run,
                                overwrite=overwrite,
                                dirpath=dirpath,
                                simulation_settings=simulation_settings,
                                material_name_to_lumerical=material_name_to_lumerical,
                                delete_fsp_files=delete_fsp_files,
                                solver=component_solver,
                                **settings,
                            )
                        )
                    paths[component_2.name] = path

            else:
                path = get_sparameters_path(
                    component_,
                    dirpath=dirpath,
                    layer_stack=layer_stack or get_layer_stack(),
                    **settings,
                )
                if path.exists():
                    # s_params.append(np.ndarray(np.load(path)))
                    paths[component_.name] = path
                else:
                    s_params.append(
                        write_sparameters_lumerical(
                            component=component_,
                            layer_stack=layer_stack,
                            session=session,
                            run=run,
                            overwrite=overwrite,
                            dirpath=dirpath,
                            simulation_settings=simulation_settings,
                            material_name_to_lumerical=material_name_to_lumerical,
                            delete_fsp_files=delete_fsp_files,
                            solver=solver,
                            **settings,
                        )
                    )
                paths[component_.name] = path
        else:
            s_params.append(
                write_sparameters_lumerical(
                    component=component_,
                    layer_stack=layer_stack,
                    session=session,
                    run=run,
                    overwrite=overwrite,
                    dirpath=dirpath,
                    simulation_settings=simulation_settings,
                    material_name_to_lumerical=material_name_to_lumerical,
                    delete_fsp_files=delete_fsp_files,
                    solver=solver,
                    **settings,
                )
            )
            paths[component_.name] = get_sparameters_path(
                component_,
                dirpath=dirpath,
                layer_stack=layer_stack or get_layer_stack(),
                **settings,
            )
    sim_settings = dict(simulation_settings)

    layer_stack = layer_stack or get_layer_stack()

    layer_to_thickness = layer_stack.get_layer_to_thickness()
    layer_to_zmin = layer_stack.get_layer_to_zmin()
    layer_to_material = layer_stack.get_layer_to_material()

    if hasattr(component.info, "simulation_settings"):
        sim_settings.update(component.info.simulation_settings)
        logger.info(
            f"Updating {component.name!r} sim settings {component.simulation_settings}"  # type: ignore
        )
    for setting in settings:
        if setting not in sim_settings:
            raise ValueError(
                f"Invalid setting {setting!r} not in ({list(sim_settings.keys())})"
            )

    sim_settings.update(**settings)
    ss = SimulationSettingsLumericalFdtd(**sim_settings)

    component_extended = kf.KCell()
    for port in component.ports.get_all().values():
        component_ref = component_extended << component
        width = port.width * component.klib.dbu if isinstance(port.width, int) else 1
        extension = component_extended.create_inst(
            kf.pcells.waveguide(width, ss.port_extension, layer=port.layer)
        )
        extension.connect("o2", extension, port.name)
        output_port = extension.ports["o1"]
        component_extended.add_port(extension.ports["o1"], name=port.name)

    # ports = component_extended.get_ports_list(port_type="optical")
    # if not ports:
    #     raise ValueError(f"{component.name!r} does not have any optical ports")

    # component.remove_layers(component.layers - set(layer_to_thickness.keys()))
    # component._bb_valid = False
    component_extended.flatten()
    component_extended.name = "top"
    # component.flatten()
    component_extended.draw_ports()
    solver = component.info["sim"] if "sim" in component.info else solver
    filepath_npz = get_sparameters_path(
        component=component,
        dirpath=dirpath,
        layer_stack=layer_stack,
        **settings,
    )
    component_extended.write(filepath_npz.with_suffix(".gds"))
    gdspath = filepath_npz.with_suffix(".gds")
    filepath = filepath_npz.with_suffix(".dat")
    filepath_sim_settings = filepath.with_suffix(".yml")
    filepath_fsp = filepath.with_suffix(".fsp")
    fspdir = filepath.parent / f"{filepath.stem}_s-parametersweep"

    if run and filepath_npz.exists() and not overwrite:
        logger.info(f"Reading Sparameters from {filepath_npz}")
        return np.ndarray(np.load(filepath_npz))

    if not run and session is None:
        print(run_false_warning)

    logger.info(f"Writing Sparameters to {filepath_npz}")
    xmin = component.dbbox().left
    xmax = component.dbbox().right
    ymin = component.dbbox().bottom
    ymax = component.dbbox().top
    x_min = (xmin - ss.xmargin) * 1e-6
    x_max = (xmax + ss.xmargin) * 1e-6
    y_min = (ymin - ss.ymargin) * 1e-6
    y_max = (ymax + ss.ymargin) * 1e-6

    # layers_thickness = [
    #     layer_to_thickness[layer]
    #     for layer in component.get_layers()
    #     if layer in layer_to_thickness
    # ]
    # if not layers_thickness:
    #     raise ValueError(
    #         f"no layers for component {component.get_layers()}"
    #         f"in layer stack {layer_stack}"
    #     )
    # layers_zmin = [
    #     layer_to_zmin[layer]
    #     for layer in component.get_layers()
    #     if layer in layer_to_zmin
    # ]
    # component_thickness = max(layers_thickness)
    # component_zmin = min(layers_zmin)

    # z = (component_zmin + component_thickness) / 2 * 1e-6
    z = 0.0
    z_span = 1e-6

    x_span = x_max - x_min
    y_span = y_max - y_min

    # layers = component.get_layers()
    sim_settings.update(dict(layer_stack=layer_stack.to_dict()))

    # sim_settings = dict(
    #     simulation_settings=sim_settings,
    #     component=component.to_dict(),
    #     # version=__version__,
    # )

    logger.info(
        f"Simulation size = {x_span*1e6:.3f}, {y_span*1e6:.3f}, {z_span*1e6:.3f} um"
    )

    # from pprint import pprint
    # filepath_sim_settings.write_text(omegaconf.OmegaConf.to_yaml(sim_settings))
    # print(filepath_sim_settings)
    # pprint(sim_settings)
    # return

    try:
        import sys

        sys.path.append("C:\\Program Files\\Lumerical\\v231\\api\\python\\")
        import lumapi
    except ModuleNotFoundError as e:
        print(
            "Cannot import lumapi (Python Lumerical API). "
            "You can add set the PYTHONPATH variable or add it with `sys.path.append()`"
        )
        raise e
    except OSError as e:
        raise e

    start = time.time()
    s = (
        session or lumapi.FDTD(hide=False)
        if solver == "FDTD"
        else lumapi.MODE(hide=False)
    )
    s.newproject()
    s.selectall()
    s.deleteall()
    s.addrect(
        x_min=x_min,
        x_max=x_max,
        y_min=y_min,
        y_max=y_max,
        z=z,
        z_span=z_span,
        index=1.5,
        name="clad",
    )

    material_name_to_lumerical_new = material_name_to_lumerical or {}
    material_name_to_lumerical = ss.material_name_to_lumerical.copy()
    material_name_to_lumerical.update(**material_name_to_lumerical_new)

    material = (
        material_name_to_lumerical[ss.background_material] if solver == "FDTD" else None
    )
    set_material(
        session=s, structure="clad", material=material
    ) if solver == "FDTD" and material is not None else None

    s.addfdtd(
        dimension="3D",
        x_min=x_min,
        x_max=x_max,
        y_min=y_min,
        y_max=y_max,
        z=z,
        z_span=z_span,
        mesh_accuracy=ss.mesh_accuracy,
        use_early_shutoff=True,
        simulation_time=ss.simulation_time,
        simulation_temperature=ss.simulation_temperature,
    ) if solver == "FDTD" else s.addeme(
        solver_type="2D XY plane: X prop",
        x_min=x_min,
        group_spans=x_span,
        y_min=y_min,
        y_max=y_max,
        z=z,
        # z_span=z_span,
        # mesh_accuracy=ss.mesh_accuracy,
        # use_early_shutoff=True,
        simulation_temperature=ss.simulation_temperature,
    )

    for layer, level in layer_stack.layers.items():
        material_name = layer_to_material[level.layer]
        if material_name not in material_name_to_lumerical:
            continue
        material = material_name_to_lumerical[material_name]

        zmin = layer_to_zmin[level.layer]
        thickness = layer_to_thickness[level.layer]
        zmax = zmin + thickness
        z = (zmax + zmin) / 2

        path = gdspath
        try:
            s.gdsimport(str(path), "top", f"{level.layer[0]}:{level.layer[1]}")
        except Exception as e:
            continue
        layername = f"GDS_LAYER_{level.layer[0]}:{level.layer[1]}"
        s.setnamed(layername, "z", z * 1e-6)
        s.setnamed(layername, "z span", thickness * 1e-6)
        set_material(session=s, structure=layername, material=material)
        logger.info(f"adding {layer}, thickness = {thickness} um, zmin = {zmin} um ")

    s.deletesweep("s-parameter sweep")

    if solver == "MODE":
        for i in range(2):
            s.select("EME::Ports::port_1")
            s.delete()

    for i, port in enumerate(component.ports.get_all().values()):
        from kfactory.pdk import _ACTIVE_PDK

        zmin = layer_to_zmin[_ACTIVE_PDK.get_layer(port.layer)]  # type: ignore
        thickness = layer_to_thickness[_ACTIVE_PDK.get_layer(port.layer)]  # type: ignore
        z = (zmin + thickness) / 2
        zspan = 2 * ss.port_margin + thickness

        if solver == "FDTD":
            s.addport()
        elif solver == "MODE" and i != 0:
            s.addemeport()
        s.setnamed(
            f"FDTD::ports", "monitor frequency points", ss.wavelength_points
        ) if solver == "FDTD" else None
        p = (
            f"FDTD::ports::port {i+1}"
            if solver == "FDTD"
            else f"EME::Ports::port_{i+1}"
        )
        s.setnamed(p, "x", port.x * 1e-6 / 1000)
        s.setnamed(p, "y", port.y * 1e-6 / 1000)
        s.setnamed(p, "z", z * 1e-6 / 1000)
        s.setnamed(p, "z span", zspan * 1e-6)
        if solver != "MODE":
            s.setnamed(p, "frequency dependent profile", ss.frequency_dependent_profile)
            s.setnamed(p, "number of field profile samples", ss.field_profile_samples)

        deg = int(port.orientation)
        # if port.orientation not in [0, 90, 180, 270]:
        #     raise ValueError(f"{port.orientation} needs to be [0, 90, 180, 270]")

        if -45 <= deg <= 45:
            direction = "Backward"
            injection_axis = "x-axis"
            dxp = 0.0
            dyp = 2 * ss.port_margin + port.width / 1000
        elif 45 < deg < 90 + 45:
            direction = "Backward"
            injection_axis = "y-axis"
            dxp = 2 * ss.port_margin + port.width / 1000
            dyp = 0.0
        elif 90 + 45 < deg < 180 + 45:
            direction = "Forward"
            injection_axis = "x-axis"
            dxp = 0.0
            dyp = 2 * ss.port_margin + port.width / 1000
        elif 180 + 45 < deg < 180 + 45 + 90:
            direction = "Forward"
            injection_axis = "y-axis"
            dxp = 2 * ss.port_margin + port.width / 1000
            dyp = 0.0

        else:
            raise ValueError(
                f"port {port.name!r} orientation {port.orientation} is not valid"
            )

        port_location = (
            "left" if direction == "Forward" and injection_axis == "x-axis" else "right"
        )
        s.setnamed(p, "direction", direction) if solver == "FDTD" else s.setnamed(
            p, "port location", port_location
        )
        s.setnamed(p, "injection axis", injection_axis) if solver == "FDTD" else None
        s.setnamed(p, "y span", dyp * 1e-6)
        s.setnamed(p, "x span", dxp * 1e-6) if solver == "FDTD" else s.setnamed(
            p, "z span", zspan
        )
        # s.setnamed(p, "theta", deg)
        s.setnamed(p, "name", port.name) if solver == "FDTD" else None
        # s.setnamed(p, "name", f"o{i+1}")

        logger.info(
            f"port {p} {port.name!r}: at ({port.x}, {port.y}, 0)"
            f"size = ({dxp}, {dyp}, {zspan})"
        )

    s.setglobalsource("wavelength start", ss.wavelength_start * 1e-6)
    s.setglobalsource("wavelength stop", ss.wavelength_stop * 1e-6)
    # s.setglobalsource("wavelength points", ss.wavelength_points)

    if run and solver == "FDTD":
        s.addsweep(3)
        s.setsweep("s-parameter sweep", "Excite all ports", 0)
        s.setsweep("s-parameter sweep", "auto symmetry", True)
        s.setglobalmonitor("frequency points", ss.wavelength_points)
        s.save(str(filepath_fsp))
        s.runsweep("s-parameter sweep")
        sp = (
            s.getsweepresult("s-parameter sweep", "S parameters")
            if solver == "FDTD"
            else s.getsweepresult("s-parameter sweep", "user s matrix")
        )
        s.exportsweep("s-parameter sweep", str(filepath))
        logger.info(f"wrote sparameters to {filepath}")

        # sp["wavelengths"] = sp.pop("lambda").flatten() * 1e6
        np.savez_compressed(filepath_npz, **sp)

        with open(filepath, "r+") as fd:
            data = fd.read()
            diction = {180: "LEFT", 0: "RIGHT", 90: "TOP", 270: "BOTTOM"}
            for p_ in component.ports.get_all().values():
                data = data.replace(
                    f"{p_.name}, LEFT", f"{p_.name}, {diction[int(p_.orientation)]}"
                )
            fd.seek(0)
            fd.write(data)
        fd.close()
        # keys = [key for key in sp.keys() if key.startswith("S")]
        # ra = {
        #     f"{key.lower()}a": list(np.unwrap(np.angle(sp[key].flatten())))
        #     for key in keys
        # }
        # rm = {f"{key.lower()}m": list(np.abs(sp[key].flatten())) for key in keys}
        # results = {"wavelengths": wavelengths}
        # results.update(ra)
        # results.update(rm)
        # df = pd.DataFrame(results, index=wavelengths)
        # df.to_csv(filepath_npz, index=False)

        end = time.time()
        sim_settings.update(compute_time_seconds=end - start)
        sim_settings.update(compute_time_minutes=(end - start) / 60)
        filepath_sim_settings.write_text(omegaconf.OmegaConf.to_yaml(sim_settings))
        if delete_fsp_files and fspdir.exists():
            shutil.rmtree(fspdir)
            logger.info(
                f"deleting simulation files in {fspdir}. "
                "To keep them, use delete_fsp_files=False flag"
            )

        return np.ndarray(sp)
    elif run and solver == "MODE":
        start = time.time()
        s.run()
        s.setemeanalysis("wavelength sweep", 1)
        s.setemeanalysis("start wavelength", ss.wavelength_start * 1e-6)
        s.setemeanalysis("stop wavelength", ss.wavelength_stop * 1e-6)
        s.setemeanalysis("number of wavelength points", ss.wavelength_points)
        s.emesweep("wavelength sweep")

        sp = s.getemesweep("S_wavelength_sweep")

        s.exportemesweep(str(filepath))

        with open(filepath, "r+") as f:
            text = f.read()
            for i, val in enumerate(component.ports.get_all().values()):
                text = text.replace(f"port {i+1}", val.name)
            f.write(text)
        f.close()

        sp = np.ndarray(sp)
        np.savez_compressed(filepath_npz, **sp)

        end = time.time()

        sim_settings.update(compute_time_seconds=end - start)
        sim_settings.update(compute_time_minutes=(end - start) / 60)
        filepath_sim_settings.write_text(omegaconf.OmegaConf.to_yaml(sim_settings))
        if delete_fsp_files and fspdir.exists():
            shutil.rmtree(fspdir)
            logger.info(
                f"deleting simulation files in {fspdir}. "
                "To keep them, use delete_fsp_files=False flag"
            )

        return sp

    filepath_sim_settings.write_text(omegaconf.OmegaConf.to_yaml(sim_settings))
    return s


if __name__ == "__main__":
    import lumapi

    s = lumapi.FDTD()

    # component = gf.components.straight(length=2.5)
    component = kf.pcells.mzi()

    material_name_to_lumerical = dict(si=(3.45, 2))  # or dict(si=3.45+2j)
    r = write_sparameters_lumerical(
        component=component,
        material_name_to_lumerical=material_name_to_lumerical,  # type: ignore
        run=False,
        session=s,
    )
    # c = gf.components.coupler_ring(length_x=3)
    # c = gf.components.mmi1x2()
    # print(r)
    # print(r.keys())
    # print(component.ports.keys())
