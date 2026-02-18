#!/usr/bin/env python3
"""
Wrapper for fiberhome_olt_signals.py - Zabbix External Check entry point.

This script must be in /usr/lib/zabbix/externalscripts/ (not in a subdirectory)
because Zabbix doesn't allow '/' in external check keys.
"""
import logging
import sys
import os

# Silence all logging to stdout - only stderr allowed for Zabbix
logging.basicConfig(
    level=logging.ERROR,  # Only errors, no INFO/DEBUG
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stderr,
    force=True,
)

# Add the fiberhome module to path
script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(script_dir, 'fiberhome'))

# Import and run the actual script
from fiberhome import fiberhome_olt_signals
sys.argv[0] = fiberhome_olt_signals.__file__
sys.exit(fiberhome_olt_signals.main())
