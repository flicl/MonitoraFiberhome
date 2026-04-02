#!/usr/bin/env python3
"""
fiberhome_olt_interfaces.py — Zabbix LLD for Physical Network Interfaces.

Discovers physical ethernet interfaces via SNMP IF-MIB and returns
JSON in Zabbix Low-Level Discovery format.

Usage (Zabbix External Check):
    fiberhome_olt_interfaces.py <ip> <community> [port]

Output:
    Zabbix LLD JSON with {#SNMPINDEX}, {#IFNAME}, {#IFTYPE} macros

Replaces: discovery_interfaces.py
"""

import json
import logging
import sys
from pathlib import Path

# Add parent directory to path for imports when running as script
sys.path.insert(0, str(Path(__file__).parent / "fiberhome"))

from interfaces import discover_physical_interfaces, format_zabbix_lld

# Configure logging to stderr (stdout is for JSON output)
if not logging.getLogger().handlers:
    logging.basicConfig(
        level=logging.WARNING,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        stream=sys.stderr,
    )
logger = logging.getLogger(__name__)


def main() -> int:
    """Entry point for Zabbix external check."""
    if len(sys.argv) < 3:
        logger.error("Insufficient arguments")
        print(
            json.dumps({"error": "Usage: fiberhome_olt_interfaces.py <ip> <community> [port]"}),
            file=sys.stdout,
        )
        return 1

    ip = sys.argv[1]
    community = sys.argv[2]
    port = int(sys.argv[3]) if len(sys.argv) > 3 else 161

    try:
        # Discover interfaces
        interfaces = discover_physical_interfaces(ip, community, port)

        # Format as Zabbix LLD
        lld_output = format_zabbix_lld(interfaces)

        # Output JSON to stdout for Zabbix
        print(json.dumps(lld_output, indent=2))

        logger.info(f"Discovered {len(interfaces)} interfaces on {ip}")
        return 0

    except Exception as e:
        logger.error(f"Failed to discover interfaces on {ip}: {e}")
        print(
            json.dumps({"error": str(e)}),
            file=sys.stdout,
        )
        return 1


if __name__ == "__main__":
    sys.exit(main())
