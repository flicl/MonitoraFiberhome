#!/usr/bin/env python3
"""
fiberhome_olt_signals.py — Master Item for Zabbix Dependent Items.

Collects optical signal metrics (best/worst/median dBm) per PON
and returns JSON for Zabbix to parse via JSONPath preprocessing.
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

from fiberhome.parsers import extract_pon_pairs, parse_pon_signals
from fiberhome.scrapli_client import FiberhomeClient

if not logging.getLogger().handlers:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        stream=sys.stderr,
    )
logger = logging.getLogger(__name__)


def build_response(
    pon_signals: list,
    collection_time_ms: float,
    olt_ip: str,
    success: bool = True,
    error: str | None = None,
) -> dict[str, Any]:
    """Build JSON response structure."""
    return {
        "data": {
            "pon_signals": pon_signals,
            "metadata": {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "collection_time_ms": round(collection_time_ms),
                "olt_ip": olt_ip,
                "success": success,
                "error": error,
            },
        }
    }


async def collect_olt_signals(
    ip: str,
    user: str,
    password: str,
    port: int = 23,
) -> dict[str, Any]:
    """Collect OLT optical signal data."""
    start_time = perf_counter()
    pon_signals: list = []

    try:
        async with FiberhomeClient(ip, user, password, port) as client:
            auth_output = await client.collect_onu_authorization()
            pon_pairs = extract_pon_pairs(auth_output)
            logger.info("Discovered %s PONs with ONUs on %s", len(pon_pairs), ip)

            for slot, pon in sorted(pon_pairs):
                signal_output = await client.collect_pon_signals(slot, pon)
                signals = parse_pon_signals(signal_output, slot, pon)
                if signals:
                    pon_signals.append(
                        {
                            "slot": signals.slot,
                            "pon": signals.pon,
                            "pon_name": signals.pon_name,
                            "best_signal": signals.best_signal,
                            "poor_signal": signals.poor_signal,
                            "median_signal": signals.median_signal,
                            "onu_count": signals.onu_count,
                        }
                    )

        collection_time = (perf_counter() - start_time) * 1000
        logger.info(
            "Collected signals from %s: %s PONs in %.0fms",
            ip,
            len(pon_signals),
            collection_time,
        )
        return build_response(pon_signals, collection_time, ip, success=True)
    except Exception as exc:
        collection_time = (perf_counter() - start_time) * 1000
        logger.error("Failed to collect signals from %s: %s", ip, exc)
        return build_response(
            pon_signals,
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
                {"error": "Usage: fiberhome_olt_signals.py <ip> <user> <password> [port]"}
            ),
            file=sys.stdout,
        )
        return 1

    ip = sys.argv[1]
    user = sys.argv[2]
    password = sys.argv[3]
    port = int(sys.argv[4]) if len(sys.argv) > 4 else 23

    result = asyncio.run(collect_olt_signals(ip, user, password, port))
    print(json.dumps(result, indent=2))
    return 0 if result["data"]["metadata"]["success"] else 1


if __name__ == "__main__":
    sys.exit(main())
