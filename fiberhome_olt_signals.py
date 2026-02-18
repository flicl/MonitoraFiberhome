#!/usr/bin/env python3
"""
Wrapper for fiberhome_olt_signals.py - Zabbix External Check entry point.

This script must be in /usr/lib/zabbix/externalscripts/ (not in a subdirectory)
because Zabbix doesn't allow '/' in external check keys.
"""
import sys
import os

# Add the fiberhome module to path
script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(script_dir, 'fiberhome'))

# Import and run the actual script
from fiberhome import fiberhome_olt_signals
sys.argv[0] = fiberhome_olt_signals.__file__
sys.exit(fiberhome_olt_signals.main())
