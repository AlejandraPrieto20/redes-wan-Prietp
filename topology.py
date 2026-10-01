"""
Modulo: topology.py
Propósito: cargar y validar topologías desde CSV o JSON, y representar una Topology simple.
Incluye exportación interactiva HTML con pyvis para la interfaz gráfica.
"""

import ipaddress
import json
from typing import Dict, List, Tuple, Any
import pandas as pd

class TopologyError(ValueError):
    pass

class Topology:
    """
    Representación simple de la topología:
    - nodes: dict -> { node_name: { "interfaces": { if_name: ip_str, ... } } }
    - links: list of tuples -> [(node_a, if_a, node_b, if_b), ...]
    """
    def __init__(self):
        self.nodes: Dict[str, Dict[str, Dict[str, str]]] = {}
        self.links: List[Tuple[str, str, str, str]] = []

    def add_node_interface(self, node: str, interface: str, ip: str):
        node = str(node)
        interface = str(interface)
        if node not in self.nodes:
            self.nodes[node] = {"interfaces": {}}
        if interface in self.nodes[node]["interfaces"]:
            raise TopologyError(f"Interfaz duplicada: {node} {interface}")
        self.nodes[node]["interfaces"][interface] = ip

    def add_link(self, node_a: str, if_a: str, node_b: str, if_b: str):
        normalized = (node_a, if_a, node_b, if_b)
        reversed_ = (node_b, if_b, node_a, if_a)
        if normalized in self.links or reversed_ in self.links:
            raise TopologyError(f"Enlace duplicado entre {node_a}:{if_a} y {node_b}:{if_b}")
        self.links.append(normalized)

    def summary(self) -> Dict[str, Any]:
        total_interfaces = sum(len(n["interfaces"]) for n in self.nodes.values())
        return {
            "nodes_count": len(self.nodes),
            "links_count": len(self.links),
            "interfaces_count": total_interfaces
        }

    def to_tables(self) -> Tuple[pd.DataFrame, pd.DataFrame]:
        nodes_rows = []
        for node, info in self.nodes.items():
            for iface, ip in info["interfaces"].items():
                nodes_rows.append({"node": node, "interface": iface, "ip": ip})
        links_rows = []
        for a, ia, b, ib in self.links:
            links_rows.append({"node_a": a, "if_a": ia, "node_b": b, "if_b": ib})
        nodes_df = pd.DataFrame(nodes_rows)
        links_df = pd.DataFrame(links_rows)
        return nodes_df, links_df

    def to_dot(self) -> str:
        lines = ["graph topology {"]
        for node in self.nodes:
            lines.append(f'  "{node}";')
        for a, ia, b, ib in self.links:
            label = f"{ia} - {ib}"
            lines.append(f'  "{a}" -- "{b}" [label="{label}"];')
        lines.append("}")
        return "\n".join(lines)

    def to_pyvis_html(self, height: str = "600px", width: str = "100%") -> str:
        try:
            from pyvis.network import Network
        except Exception as e:
            raise TopologyError(f"pyvis no está instalado: {e}")

        net = Network(height=height, width=width, directed=False, notebook=False)
        net.toggle_physics(True)

        for node, info in self.nodes.items():
            interfaces = info.get("interfaces", {})
            if interfaces:
                title_lines = []
                for iface, ip in interfaces.items():
                    ip_text = ip if ip else "(sin IP)"
                    title_lines.append(f"{iface}: {ip_text}")
                title = "<br>".join(title_lines)
            else:
                title = "Sin interfaces"
            net.add_node(node, label=node, title=title)

        for a, ia, b, ib in self.links:
            label = f"{ia} - {ib}"
            net.add_edge(a, b, title=label, label=label)

        html = net.generate_html()
        return html

# ---------- Parsers y validaciones ----------

def validate_ipv4_address(ip_str: str) -> str:
    ip_str = str(ip_str).strip()
    try:
        if "/" in ip_str:
            ipaddress.ip_interface(ip_str)
        else:
            ipaddress.ip_address(ip_str)
        return ip_str
    except Exception as e:
        raise TopologyError(f"IP inválida: '{ip_str}' -> {e}")


def parse_topology_csv(file_like) -> Topology:
    df = pd.read_csv(file_like, dtype=str).fillna("")
    required_cols = {"node", "interface", "ip", "peer_node", "peer_interface"}
    if not required_cols.issubset(set(df.columns)):
        raise TopologyError(f"CSV debe contener columnas: {', '.join(required_cols)}. Columnas encontradas: {', '.join(df.columns)}")
    topo = Topology()
    for idx, row in df.iterrows():
        node = row["node"].strip()
        interface = row["interface"].strip()
        ip = row["ip"].strip()
        peer_node = row["peer_node"].strip()
        peer_if = row["peer_interface"].strip()

        if not node or not interface:
            raise TopologyError(f"Fila {idx}: node e interface son obligatorios.")
        if ip:
            ip = validate_ipv4_address(ip)
            topo.add_node_interface(node, interface, ip)
        else:
            topo.add_node_interface(node, interface, "")

        if peer_node and peer_if:
            topo.add_link(node, interface, peer_node, peer_if)
    return topo


def parse_topology_json(file_like) -> Topology:
    obj = json.load(file_like)
    if "nodes" not in obj or not isinstance(obj["nodes"], list):
        raise TopologyError("JSON debe tener una clave 'nodes' con una lista de nodos.")
    topo = Topology()
    for node in obj["nodes"]:
        name = node.get("name")
        if not name:
            raise TopologyError("Cada nodo debe tener 'name'.")
        for iface in node.get("interfaces", []):
            if_name = iface.get("name")
            ip = iface.get("ip", "")
            if if_name is None:
                raise TopologyError(f"Nodo {name}: cada interfaz necesita 'name'.")
            if ip:
                ip = validate_ipv4_address(ip)
                topo.add_node_interface(name, if_name, ip)
            else:
                topo.add_node_interface(name, if_name, "")
    for node in obj["nodes"]:
        name = node["name"]
        for iface in node.get("interfaces", []):
            peer = iface.get("peer")
            if peer:
                peer_node = peer.get("node")
                peer_if = peer.get("interface")
                if peer_node and peer_if:
                    try:
                        topo.add_link(name, iface["name"], peer_node, peer_if)
                    except TopologyError:
                        pass
    return topo
