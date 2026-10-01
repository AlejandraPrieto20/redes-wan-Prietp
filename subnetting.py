"""
Módulo simple de subnetting (IPv4).
Explicación breve: toma una red en formato CIDR (ej. "192.168.0.0/24") y la divide
en subredes con un nuevo prefijo (ej. 26), devolviendo detalles útiles.
Usa la librería estándar `ipaddress`.
"""

import ipaddress
from typing import List, Dict

def validate_network(network_str: str) -> ipaddress.IPv4Network:
    """
    Valida y devuelve un objeto IPv4Network.
    Levanta ValueError si la entrada no es válida.
    Analogía: comprobar que la caja de pizza sea una caja bien etiquetada antes de cortarla.
    """
    try:
        net = ipaddress.ip_network(network_str, strict=True)
        if not isinstance(net, ipaddress.IPv4Network):
            raise ValueError("Solo se permite IPv4 en este módulo inicial.")
        return net
    except Exception as e:
        raise ValueError(f"Red inválida: {e}")

def split_network(network_str: str, new_prefix: int) -> List[Dict]:
    """
    Divide la red `network_str` (ej. "192.168.0.0/24") en subredes con prefijo `new_prefix`.
    Devuelve una lista de diccionarios con: network, prefix, network_address, broadcast, usable_range, hosts_count.
    """
    net = validate_network(network_str)

    if new_prefix < net.prefixlen:
        raise ValueError("El nuevo prefijo debe ser mayor o igual que el prefijo de la red original.")
    if new_prefix > 32:
        raise ValueError("Prefijo inválido. Debe estar entre 0 y 32.")

    if new_prefix == net.prefixlen:
        subnets = [net]
    else:
        subnets = list(net.subnets(new_prefix=new_prefix))

    result = []
    for s in subnets:
        total_hosts = s.num_addresses
        if total_hosts <= 2:
            usable = []
            first_usable = None
            last_usable = None
        else:
            hosts = list(s.hosts())
            first_usable = str(hosts[0])
            last_usable = str(hosts[-1])
            usable = [first_usable, last_usable]

        result.append({
            "network": str(s.with_prefixlen),
            "prefixlen": s.prefixlen,
            "network_address": str(s.network_address),
            "broadcast_address": str(s.broadcast_address),
            "first_usable": first_usable,
            "last_usable": last_usable,
            "usable_range": usable,
            "total_hosts": total_hosts,
            "usable_hosts_count": max(0, total_hosts - 2)
        })

    return result

def split_into_n_subnets(network_str: str, n_subnets: int) -> List[Dict]:
    """
    Divide la red en exactamente n_subnets subredes de tamaño igual, si es posible.
    Calcula el prefijo requerido y usa split_network.
    """
    net = validate_network(network_str)
    if n_subnets <= 0:
        raise ValueError("n_subnets debe ser >= 1")

    import math
    bits_needed = math.ceil(math.log2(n_subnets))
    new_prefix = net.prefixlen + bits_needed
    if new_prefix > 32:
        raise ValueError("No es posible dividir en tantas subredes con IPv4 (prefijo > 32).")

    subnets = split_network(network_str, new_prefix)
    return subnets[:n_subnets]
