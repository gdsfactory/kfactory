import kfactory as kf
from pathlib import Path
import os
from graph_tool.all import *  # <- You need to install graph_tool through "conda install -c conda-forge graph-tool"


def save_netlist(nl: kf.kdb.Netlist, filename: str):
    file_name = Path.cwd() / "netlist" / filename
    if not os.path.exists("netlist"):
        os.makedirs("netlist")
    with open(file_name, "w") as f:
        f.write(nl.to_s())


def parse_stored_netlist(filename: str):
    """
    Args:
        A netlist txt file stored by save_netlist function
    Return:
        A list of connected nodes and their connection label. For example,
        [('0', '1', '0_o2-1_o1'), ('1', '2', '1_o2-2_o1'), ('2', '3', '2_o2-3_o1')]
        represent a graph with three edges:
            Edge 1: Connection between vertex 0 and vertex 1, and the detailed connection information is
                    '0_o2-1_o1' meaning that the o2 port of vertex 0 is connected to o1 port of vertex 1.
            Edge 2: Connection between vertex 1 and vertex 2, and the detailed connection information is
                    '1_o2-2_o1' meaning that the o2 port of vertex 1 is connected to o1 port of vertex 2.
            Edge 3: Connection between vertex 2 and vertex 3, and the detailed connection information is
                    '2_o2-3_o1' meaning that the o2 port of vertex 2 is connected to o1 port of vertex 3.
        This list can be sent to Graph() function from graph_tool directly.
    """
    port_connection = []
    device_label_map = {}
    file_name = Path.cwd() / "netlist" / filename
    if not os.path.exists("netlist"):
        os.makedirs("netlist")

    # parse netlist txt file to generate port_connection and device name map
    with open(file_name, "r") as f:
        for line in f:
            if len(line.split(" ")) > 1:
                if line.split(" ")[2] == "subcircuit":
                    port_connection.append(line.split(" ")[-1])
                    device_label_map[
                        line.split(" ")[-2].split("_")[0][1:]
                    ] = line.split(" ")[-2]
    # further extract connection information from port_connection
    input_in_net = []
    output_in_net = []
    for pc in port_connection:
        if pc.split(",")[0].split("=")[-1].startswith("o"):
            input_in_net.append(pc.split(",")[0].split("=")[-1])
        else:
            input_in_net.append(pc.split(",")[0].split("=")[-1][1:-1])
        if pc.split(",")[1].split("=")[-1][0:-3].startswith("o"):
            output_in_net.append(pc.split(",")[1].split("=")[-1][0:-3])
        else:
            output_in_net.append(pc.split(",")[1].split("=")[-1][1:-4])

    # construct a list of connected
    input_for_graph = []
    for i in range(len(input_in_net)):
        if len(input_in_net[i].split("-")) == 2:
            input_for_graph.append(
                (
                    (input_in_net[i].split("-")[0].split("_")[0]),
                    (input_in_net[i].split("-")[1].split("_")[0]),
                    input_in_net[i],
                )
            )

    return input_for_graph


def plot_netlist(
    input_for_graph: list, port_loc: dict = None, save_graph: str = "netlist_graph.pdf"
):

    file_name = Path.cwd() / "netlist" / save_graph
    if not os.path.exists("netlist"):
        os.makedirs("netlist")
    file_name = str(file_name)
    # Creating a graph
    g = Graph(
        input_for_graph, hashed=True, eprops=[("connection", "string")], directed=False
    )  # undirected graph

    # adding vertex property (provide information for vertices' location)
    pos = g.new_vertex_property("vector<double>")
    if port_loc is not None:
        for v in g.vertices():
            pos[v] = port_loc[v]
        graph_draw(
            g,
            vertex_text=g.vertex_index,
            pos=pos,
            edge_text=g.ep.connection,
            vertex_font_size=16,
            edge_font_size=12,
            output_size=(300, 300),
            output=file_name,
        )
    else:
        graph_draw(
            g,
            vertex_text=g.vertex_index,
            edge_text=g.ep.connection,
            edge_font_size=12,
            output=file_name,
        )


if __name__ == "__main__":

    c = kf.KCell()

    b = kf.cells.circular.bend_circular(width=1, radius=10, layer=kf.kcl.layer(1, 0))
    s = kf.cells.waveguide.waveguide(width=1, length=20, layer=kf.kcl.layer(1, 0))

    b1 = c << b
    b2 = c << b
    b2.connect("o1", b1, "o2")
    b3 = c << b
    b3.connect("o1", b2, "o2")
    s1 = c << s
    s1.connect("o1", b3, "o2")
    c.add_port(b1.ports["o1"])
    c.add_port(s1.ports["o2"])

    nl = c.netlist()
    # save a netlist to txt file
    save_netlist(nl, "temp.txt")

    # Define the location of vertex in your graph -> This is not a necessary step.
    # But if you do so, you can better visualize your graph.
    dev_list = [b1, b2, b3, s1]
    port_loc = {}
    for i, d in enumerate(dev_list):
        _x = d.ports["o2"].x
        _y = d.ports["o2"].y
        port_loc[i] = (_x, -_y)

    input_graph = parse_stored_netlist(filename="temp.txt")

    plot_netlist(input_for_graph=input_graph, port_loc=port_loc, save_graph="temp.pdf")
