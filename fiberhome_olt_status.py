#!/usr/bin/env python3
"""
fiberhome_olt_status.py — Master Item for Zabbix Dependent Items.

Collects ONU Online/Offline/Provisioned counts per PON and returns
JSON for Zabbix to parse via JSONPath preprocessing.
"""

import asyncio
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
from typing import Any

from fiberhome.bootstrap import reexec_with_venv

reexec_with_venv(Path(__file__).resolve().parent)

from fiberhome.parsers import parse_onu_authorization
from fiberhome.scrapli_client import FiberhomeClient

if not logging.getLogger().handlers:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        stream=sys.stderr,
    )
logger = logging.getLogger(__name__)


def build_response(
    pon_stats: dict,
    collection_time_ms: float,
    olt_ip: str,
    success: bool = True,
    error: str | None = None,
) -> dict[str, Any]:
    """Build JSON response structure."""
    pon_ports = []
    total_provisioned = 0
    total_online = 0
    total_offline = 0

    for _, stats in sorted(pon_stats.items()):
        pon_ports.append(
            {
                "slot": stats.slot,
                "pon": stats.pon,
                "pon_name": stats.pon_name,
                "online": stats.online,
                "offline": stats.offline,
                "provisioned": stats.provisioned,
            }
        )
        total_provisioned += stats.provisioned
        total_online += stats.online
        total_offline += stats.offline

    return {
        "data": {
            "pon_ports": pon_ports,
            "totals": {
                "provisioned": total_provisioned,
                "online": total_online,
                "offline": total_offline,
            },
            "metadata": {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "collection_time_ms": round(collection_time_ms),
                "olt_ip": olt_ip,
                "success": success,
                "error": error,
            },
        }
    }


async def collect_olt_status(
    ip: str,
    user: str,
    password: str,
    port: int = 23,
) -> dict[str, Any]:
    """Collect OLT status data."""
    start_time = perf_counter()
    pon_stats: dict = {}

    try:
        async with FiberhomeClient(ip, user, password, port) as client:
            auth_output = await client.collect_onu_authorization()
            pon_stats = parse_onu_authorization(auth_output)

        collection_time = (perf_counter() - start_time) * 1000
        logger.info(
            "Collected status from %s: %s PONs, %s ONUs in %.0fms",
            ip,
            len(pon_stats),
            sum(s.provisioned for s in pon_stats.values()),
            collection_time,
        )
        return build_response(pon_stats, collection_time, ip, success=True)
    except Exception as exc:
        collection_time = (perf_counter() - start_time) * 1000
        logger.error("Failed to collect from %s: %s", ip, exc)
        return build_response(
            pon_stats,
            collection_time,
            ip,
            success=False,
            error=str(exc),
        )


def main() -> int:
    """Entry point for Zabbix external check."""
    if len(sys.argv) < 4:
        print(
            json.dumps(
                {"error": "Usage: fiberhome_olt_status.py <ip> <user> <password> [port]"}
            ),
            file=sys.stdout,
        )
        return 1

    ip = sys.argv[1]
    user = sys.argv[2]
    password = sys.argv[3]
    port = int(sys.argv[4]) if len(sys.argv) > 4 else 23

    result = asyncio.run(collect_olt_status(ip, user, password, port))
    print(json.dumps(result, indent=2))
    return 0 if result["data"]["metadata"]["success"] else 1


if __name__ == "__main__":
    sys.exit(main())
