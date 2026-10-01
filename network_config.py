"""
Módulo para generar configuraciones base para Cisco y Huawei a partir de una topología.
"""

import ipaddress
from typing import Dict, Any

def _build_link_description(topo: Any, node_name: str, iface_name: str) -> str:
    links = getattr(topo, "links", [])

    for node_a, if_a, node_b, if_b in links:
        if node_a == node_name and if_a == iface_name:
            return f"Enlace a {node_b} ({if_b})"
        if node_b == node_name and if_b == iface_name:
            return f"Enlace a {node_a} ({if_a})"

    return f"Interface {iface_name}"


def _generate_cisco_interface_block(iface_name: str, ip_value: str, description: str) -> str:
    lines = []
    lines.append(f"interface {iface_name}")
    lines.append(f" description {description}")
    if ip_value and ip_value.strip() != "":
        try:
            iface = ipaddress.ip_interface(ip_value)
            lines.append(f" ip address {iface.ip} {iface.netmask}")
        except ValueError:
            raise ValueError(f"IP inválida para interfaz {iface_name}: {ip_value}")
    else:
        lines.append(" no ip address")
    lines.append(" no shutdown")
    lines.append(" exit")
    return "\n".join(lines)


def _generate_huawei_interface_block(iface_name: str, ip_value: str, description: str) -> str:
    lines = []
    lines.append(f"interface {iface_name}")
    lines.append(f" description {description}")
    if ip_value and ip_value.strip() != "":
        try:
            iface = ipaddress.ip_interface(ip_value)
            lines.append(f" ip address {iface.ip} {iface.netmask}")
        except ValueError:
            raise ValueError(f"IP inválida para interfaz {iface_name}: {ip_value}")
    else:
        lines.append(" undo ip address")
    lines.append(" undo shutdown")
    lines.append(" return")
    return "\n".join(lines)


def generate_cisco_config_for_node(node_name: str, node_interfaces: Dict[str, str], topo: Any) -> str:
    lines = []
    lines.append("enable")
    lines.append("configure terminal")
    lines.append(f"hostname {node_name}")

    for iface_name, ip_value in sorted(node_interfaces.items()):
        description = _build_link_description(topo, node_name, iface_name)
        block = _generate_cisco_interface_block(iface_name, ip_value, description)
        lines.append(block)

    return "\n".join(lines) + "\n"


def generate_huawei_config_for_node(node_name: str, node_interfaces: Dict[str, str], topo: Any) -> str:
    lines = []
    lines.append("system-view")
    lines.append(f"sysname {node_name}")

    for iface_name, ip_value in sorted(node_interfaces.items()):
        description = _build_link_description(topo, node_name, iface_name)
        block = _generate_huawei_interface_block(iface_name, ip_value, description)
        lines.append(block)

    lines.append("return")
    return "\n".join(lines) + "\n"


def generate_vendor_configs(topo: Any, vendor: str) -> Dict[str, str]:
    vendor = vendor.lower().strip()

    if vendor not in ("cisco", "huawei"):
        raise ValueError("Fabricante no soportado. Usa 'cisco' o 'huawei'.")

    result = {}
    for node_name, info in sorted(topo.nodes.items()):
        interfaces = info.get("interfaces", {})
        if vendor == "cisco":
            result[node_name] = generate_cisco_config_for_node(node_name, interfaces, topo)
        else:
            result[node_name] = generate_huawei_config_for_node(node_name, interfaces, topo)

    return result
