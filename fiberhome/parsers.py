"""
CLI output parsers for Fiberhome OLT.

Parses raw CLI output into structured dataclasses.
"""

import re
import statistics
from dataclasses import dataclass
from typing import Any

from .constants import (
    PATTERN_ONU_STATUS,
    PATTERN_SIGNAL,
    PONStats,
    PONSignals,
    ONUStatus,
)


def parse_onu_authorization(output: str) -> dict[str, PONStats]:
    """
    Parse 'show authorization slot all pon all' output.

    Output format:
        ----- ONU Auth Table, SLOT = 1, PON = 1, ITEM = 9 -----
        Slot Pon Onu OnuType  ST Lic OST PhyId
        1    1   1   HG260    A  1   up  SHLN3c27de63
        1    1   2   HG260    A  1   dn  ZTEGd1ee503c

    Args:
        output: Raw CLI output

    Returns:
        Dict mapping pon_name (e.g., "1/1") to PONStats
    """
    pon_data: dict[str, dict[str, int]] = {}

    for line in output.splitlines():
        line = line.strip()
        match = PATTERN_ONU_STATUS.match(line)
        if not match:
            continue

        slot = match.group(1)
        pon = match.group(2)
        status = match.group(4)

        pon_name = f"{slot}/{pon}"
        if pon_name not in pon_data:
            pon_data[pon_name] = {"online": 0, "total": 0, "slot": int(slot), "pon": int(pon)}

        pon_data[pon_name]["total"] += 1
        if status == ONUStatus.ONLINE:
            pon_data[pon_name]["online"] += 1

    # Convert to PONStats dataclass
    result: dict[str, PONStats] = {}
    for pon_name, data in pon_data.items():
        result[pon_name] = PONStats(
            slot=str(data["slot"]),
            pon=str(data["pon"]),
            pon_name=pon_name,
            online=data["online"],
            offline=data["total"] - data["online"],
            provisioned=data["total"],
        )

    return result


def parse_pon_signals(output: str, slot: str, pon: str) -> PONSignals | None:
    """
    Parse 'show optic_module_para slot X pon Y' output.

    Output format:
        ----- PON OPTIC MODULE PAR INFO -----
        NAME          VALUE     UNIT
        TYPE         : 20       (KM)
        TEMPERATURE  : 47.38    ('C)
        ...
        ONU_NO  RECV_POWER , ITEM=9
        1       -27.53  (Dbm)
        2       -21.33  (Dbm)

    Args:
        output: Raw CLI output
        slot: Slot number
        pon: PON port number

    Returns:
        PONSignals or None if no signals found
    """
    signals: list[float] = []

    for line in output.splitlines():
        line = line.strip()
        match = PATTERN_SIGNAL.match(line)
        if match:
            try:
                signals.append(float(match.group(1)))
            except ValueError:
                continue

    if not signals:
        return None

    # Convert to absolute values (dBm negative → positive for Zabbix)
    best = abs(min(signals, key=abs))  # Smallest loss = best signal
    poor = abs(max(signals, key=abs))  # Largest loss = poor signal
    median = abs(statistics.median_grouped(signals))

    return PONSignals(
        slot=slot,
        pon=pon,
        pon_name=f"{slot}/{pon}",
        best_signal=round(best, 2),
        poor_signal=round(poor, 2),
        median_signal=round(median, 2),
        onu_count=len(signals),
    )


def extract_pon_pairs(output: str) -> set[tuple[str, str]]:
    """
    Extract unique (slot, pon) pairs from authorization output.

    Args:
        output: Raw CLI output from 'show authorization slot all pon all'

    Returns:
        Set of (slot, pon) tuples
    """
    pon_pairs: set[tuple[str, str]] = set()

    for line in output.splitlines():
        line = line.strip()
        match = PATTERN_ONU_STATUS.match(line)
        if match:
            slot = match.group(1)
            pon = match.group(2)
            pon_pairs.add((slot, pon))

    return pon_pairs
