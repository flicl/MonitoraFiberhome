"""
Fiberhome OLT Monitoring Module for Zabbix.

Provides async Scrapli-based data collection for:
- ONU Online/Offline/Provisioned status per PON
- Optical signal metrics (best/worst/median dBm) per PON

Replaces legacy telnetlib + zabbix_sender approach with:
- Single connection per collection
- JSON output for Zabbix Dependent Items
- Modern async patterns
"""

__version__ = "2.0.0"
