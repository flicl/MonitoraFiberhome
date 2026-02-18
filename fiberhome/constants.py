"""
Constants for Fiberhome OLT monitoring.

Centralizes timeouts, patterns, and configuration values.
"""

from dataclasses import dataclass
from enum import Enum
import re


# Connection timeouts
TELNET_TIMEOUT = 15
CMD_WAIT_SHORT = 0.5
CMD_WAIT_LONG = 30  # Wait for complete ONU listing (800+ ONUs)
CMD_WAIT_SIGNAL = 5  # Wait per-PON signal collection

# Prompt patterns
PROMPT_LOGIN = b"Login:"
PROMPT_PASSWORD = b"Password:"
PROMPT_USER = b"User>"
PROMPT_ADMIN = b"Admin#"
PROMPT_ADMIN_SERVICE = b"Admin\\service#"
PROMPT_ADMIN_ONU = b"Admin\\onu#"
PROMPT_ADMIN_CARD = b"Admin\\card#"

# CLI Commands
CMD_CD_SERVICE = "cd service"
CMD_CD_ONU = "cd onu"
CMD_CD_CARD = "cd card"
CMD_CD_UP = "cd .."
CMD_TERMINAL_LENGTH_0 = "terminal length 0"
CMD_SHOW_AUTH_ALL = "show authorization slot all pon all"
CMD_SHOW_SIGNAL = "show optic_module_para slot {slot} pon {pon}"
CMD_QUIT = "quit"
CMD_EN = "EN"

# Regex patterns for parsing CLI output
# ONU status line: "1    1   1   HG260    A  1   up  SHLN3c27de63"
PATTERN_ONU_STATUS = re.compile(
    r'^(\d+)\s+(\d+)\s+(\d+)\s+\S+\s+\S+\s+\S+\s+(up|dn)\b'
)

# Signal line: "1       -27.53  (Dbm)"
PATTERN_SIGNAL = re.compile(
    r'^\d+\s+(-\d+\.\d+)\s+\(Dbm\)'
)

# SNMP OIDs
OID_PON_PORT_NAME = "1.3.6.1.4.1.5875.800.3.9.3.4.1.2"
OID_PON_PORT_DESCRIPTION = "1.3.6.1.4.1.5875.800.3.9.3.4.1.3"
OID_PON_PORT_TYPE = "1.3.6.1.4.1.5875.800.3.9.3.4.1.1"


class ONUStatus(str, Enum):
    """ONU operational status."""
    ONLINE = "up"
    OFFLINE = "dn"


@dataclass(frozen=True)
class PONStats:
    """Statistics for a single PON port."""
    slot: str
    pon: str
    pon_name: str
    online: int = 0
    offline: int = 0
    provisioned: int = 0


@dataclass(frozen=True)
class PONSignals:
    """Optical signal statistics for a single PON port."""
    slot: str
    pon: str
    pon_name: str
    best_signal: float = 0.0
    poor_signal: float = 0.0
    median_signal: float = 0.0
    onu_count: int = 0
