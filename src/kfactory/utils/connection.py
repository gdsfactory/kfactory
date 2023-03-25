import kfactory as kf


@kf.autocell
def connect_sequence(
    seq: tuple[tuple[kf.KCell, str, str]],
    port_map: tuple[tuple[str, int, str]],
    input_port_name: str = "W0",
    output_port_name: str = "E0",
) -> kf.KCell:
    """
    Args:
        seq: is in the format of (component function name, component input port name, component output port name, flip along input angle or not)
        e.g. (DC(), "W0", "E0", False) -> adding a DC KCell, DC(), without flipping/mirroring the device

        port_map: allows you to define extra ports in the connected component sequence,
        and it is in the format of (port name in final KCell, component's order in seq, port name in the component)
        e.g. ("W2", 2, "W1") -> add a port "W2" in final KCell, which is the port "W1" of 2nd component in the connected sequence

        input_port_name: the input port of the connected sequence (the input port of 1st component); default port name is "W0"

        output_port_name: the output port of the connected sequence (the output port of the last component); default port name is "W0"

        Remark: the reason that seq and port_map are all tuples is because it will be hasbable thereby can be decorated by kf.autocell

    Return:
        A KCell that connected the given sequence of components. The input/output port of this KCell is given by the input port of 1st component and output port of last component, and their port names match with the args.
        This KCell will have extra ports if defined in port_map.
    """

    c = kf.KCell()
    beg = c << seq[0][0]  # ()
    port1 = beg.ports[seq[0][1]]
    c.add_port(name=input_port_name, port=port1)
    conn_port = beg.ports[seq[0][2]]
    inst_list = [beg]
    for count, dev_spec in enumerate(seq[1:], start=2):
        print(dev_spec)
        kcell = dev_spec[0]  # ()
        p_1 = dev_spec[1]
        p_2 = dev_spec[2]
        inv = dev_spec[3] if len(dev_spec) >= 4 else False
        inst = c << kcell
        inst.connect(p_1, conn_port, mirror=inv)
        conn_port = inst.ports[p_2]
        inst_list.append(inst)
        if count == len(seq):
            c.add_port(name=output_port_name, port=conn_port)

    for name, alias, alias_port_name in port_map:
        c.add_port(name=name, port=inst_list[alias].ports[alias_port_name])

    return c
