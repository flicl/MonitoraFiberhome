"""
Physical interfaces discovery via SNMP IF-MIB.

Discovers network physical interfaces (ethernet) using standard IF-MIB OIDs.
Returns data in Zabbix LLD format.
"""

import logging
import re
import subprocess
from dataclasses import dataclass
from typing import Any

from constants import (
    OID_IF_NAME,
    OID_IF_TYPE,
    OID_IF_HIGH_SPEED,
    OID_IF_OPER_STATUS,
    IF_TYPE_ETHERNET_CSMACD,
    IF_TYPE_FAST_ETHERNET,
    IF_TYPE_GIGABIT_ETHERNET,
)

logger = logging.getLogger(__name__)

# Ethernet interface types for filtering
ETHERNET_TYPES = {
    IF_TYPE_ETHERNET_CSMACD,
    IF_TYPE_FAST_ETHERNET,
    IF_TYPE_GIGABIT_ETHERNET,
}


@dataclass(frozen=True)
class NetworkInterface:
    """Represents a physical network interface."""
    index: str
    name: str
    type: int
    oper_status: int | None = None
    speed: int | None = None


def _run_snmpwalk(
    host: str,
    community: str,
    oid: str,
    port: int = 161,
    timeout: int = 2,
) -> str:
    """
    Execute snmpwalk command and return output.

    Args:
        host: Target host IP
        community: SNMP community string
        oid: OID to query
        port: SNMP port
        timeout: Query timeout in seconds

    Returns:
        Raw snmpwalk output
    """
    cmd = [
        "snmpwalk",
        "-On",
        "-v2c",
        "-c", community,
        f"{host}:{port}",
        oid,
    ]

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout,
    )

    if result.returncode != 0:
        logger.error(f"snmpwalk failed for {oid}: {result.stderr}")
        raise RuntimeError(f"SNMP query failed: {result.stderr}")

    return result.stdout


def parse_if_names(output: str) -> dict[str, str]:
    """
    Parse ifDescr/ifName SNMP output.

    Args:
        output: Raw snmpwalk output for OID_IF_NAME

    Returns:
        Dict mapping ifIndex to interface name
    """
    pattern = re.compile(
        rf'{OID_IF_NAME}\.(\d+)\s+=\s+STRING:\s+"([^"]+)"'
    )
    matches = pattern.findall(output)
    return {index: name for index, name in matches}


def parse_if_types(output: str) -> dict[str, int]:
    """
    Parse ifType SNMP output.

    Args:
        output: Raw snmpwalk output for OID_IF_TYPE

    Returns:
        Dict mapping ifIndex to interface type (int)
    """
    pattern = re.compile(
        rf'{OID_IF_TYPE}\.(\d+)\s+=\s+INTEGER:\s+(\d+)'
    )
    matches = pattern.findall(output)
    return {index: int(type_val) for index, type_val in matches}


def parse_if_speed(output: str) -> dict[str, int]:
    """
    Parse ifHighSpeed SNMP output.

    Args:
        output: Raw snmpwalk output for OID_IF_HIGH_SPEED

    Returns:
        Dict mapping ifIndex to speed in Mbps
    """
    pattern = re.compile(
        rf'{OID_IF_HIGH_SPEED}\.(\d+)\s+=\s+(?:Gauge32|Integer32):\s+(\d+)'
    )
    matches = pattern.findall(output)
    return {index: int(speed) for index, speed in matches}


def parse_if_oper_status(output: str) -> dict[str, int]:
    """
    Parse ifOperStatus SNMP output.

    Args:
        output: Raw snmpwalk output for OID_IF_OPER_STATUS

    Returns:
        Dict mapping ifIndex to operational status (1=up, 2=down, etc)
    """
    pattern = re.compile(
        rf'{OID_IF_OPER_STATUS}\.(\d+)\s+=\s+INTEGER:\s+(\d+)'
    )
    matches = pattern.findall(output)
    return {index: int(status) for index, status in matches}


def discover_physical_interfaces(
    host: str,
    community: str,
    port: int = 161,
    timeout: int = 2,
) -> list[NetworkInterface]:
    """
    Discover physical ethernet interfaces via SNMP IF-MIB.

    Args:
        host: OLT IP address
        community: SNMP community string
        port: SNMP port
        timeout: Query timeout in seconds

    Returns:
        List of NetworkInterface objects (ethernet only)
    """
    interfaces: list[NetworkInterface] = []

    try:
        # Query IF-MIB OIDs
        if_name_output = _run_snmpwalk(host, community, OID_IF_NAME, port, timeout)
        if_type_output = _run_snmpwalk(host, community, OID_IF_TYPE, port, timeout)
        if_speed_output = _run_snmpwalk(host, community, OID_IF_HIGH_SPEED, port, timeout)
        if_status_output = _run_snmpwalk(host, community, OID_IF_OPER_STATUS, port, timeout)

        # Parse responses
        if_names = parse_if_names(if_name_output)
        if_types = parse_if_types(if_type_output)
        if_speeds = parse_if_speed(if_speed_output)
        if_statuses = parse_if_oper_status(if_status_output)

        # Build interface list
        for index, if_type in if_types.items():
            if if_type not in ETHERNET_TYPES:
                continue

            name = if_names.get(index, f"if{index}")
            speed = if_speeds.get(index)
            oper_status = if_statuses.get(index)

            interfaces.append(NetworkInterface(
                index=index,
                name=name,
                type=if_type,
                oper_status=oper_status,
                speed=speed,
            ))

        logger.info(f"Discovered {len(interfaces)} ethernet interfaces on {host}")

    except Exception as e:
        logger.error(f"Failed to discover interfaces on {host}: {e}")
        raise

    return interfaces


def format_zabbix_lld(interfaces: list[NetworkInterface]) -> dict[str, Any]:
    """
    Format interfaces as Zabbix LLD JSON.

    Args:
        interfaces: List of NetworkInterface objects

    Returns:
        Zabbix LLD format dict with data array
    """
    lld_data = []

    for iface in interfaces:
        lld_data.append({
            "{#SNMPINDEX}": iface.index,
            "{#IFNAME}": iface.name,
            "{#IFTYPE}": iface.type,
        })

    return {"data": lld_data}
