import json
from ipaddress import ip_network
from typing import List


def serialize_networks(networks: List[ip_network]) -> List[str]:
    return [str(ip_n) for ip_n in networks]


def deserialize_networks(networks: List[str]) -> List[ip_network]:
    return [ip_network(ip_n) for ip_n in networks]


def dump_json(data: (list, dict), filepath: str):
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2)


def load_json(filepath: str) -> (list, dict):
    with open(filepath, 'r') as f:
        return json.load(f)
