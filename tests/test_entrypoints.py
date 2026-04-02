import unittest

import fiberhome_olt_signals
import fiberhome_olt_status


class RootEntrypointTests(unittest.TestCase):
    def test_status_entrypoint_exposes_collection_function(self) -> None:
        self.assertTrue(hasattr(fiberhome_olt_status, "collect_olt_status"))
        self.assertTrue(callable(fiberhome_olt_status.collect_olt_status))
        self.assertFalse(hasattr(fiberhome_olt_status, "fiberhome_olt_status"))

    def test_signals_entrypoint_exposes_collection_function(self) -> None:
        self.assertTrue(hasattr(fiberhome_olt_signals, "collect_olt_signals"))
        self.assertTrue(callable(fiberhome_olt_signals.collect_olt_signals))
        self.assertFalse(hasattr(fiberhome_olt_signals, "fiberhome_olt_signals"))
