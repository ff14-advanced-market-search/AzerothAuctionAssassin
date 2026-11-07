"""Check that slow recovery work cannot make the timed scan wait for it."""

import ast
from pathlib import Path
from datetime import datetime
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

from utils import forever


class RecoverySchedulingTests(unittest.TestCase):
    def test_untracked_recovery_uses_separate_pool_without_waiting(self):
        tree = ast.parse(Path("mega_alerts.py").read_text())
        main = next(
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef) and node.name == "main"
        )
        owner = SimpleNamespace(running=True, progress=Mock(), completed=Mock())
        pending = Mock()
        pending.done.return_value = False
        pools = []

        class Pool:
            def __init__(self, max_workers):
                self.recovery = not pools
                self.feeds = []
                self.shutdown_calls = []
                pools.append(self)

            def submit(self, fn, feed):
                self.feeds.append(feed)
                if not self.recovery:
                    fn(feed)
                return pending

            def shutdown(self, wait=True, cancel_futures=False):
                self.shutdown_calls.append((wait, cancel_futures))
                if self.recovery and wait:
                    raise AssertionError("Timed scans waited for untracked recovery")

        data = SimpleNamespace(
            REGION="NAFOREVER",
            REFRESH_ALERTS=False,
            EXTRA_ALERTS=False,
            THREADS=1,
            SCAN_TIME_MIN=-1,
            SCAN_TIME_MAX=3,
            get_upload_time_list=lambda: [{"dataSetID": 110, "lastUploadMinute": 0}],
            get_untracked_forever_feeds=lambda: [-110],
        )
        pull = Mock()
        ns = {
            "self": owner,
            "mega_data": data,
            "datetime": datetime,
            "forever": forever,
            "ThreadPoolExecutor": Pool,
            "is_in_scan_window": lambda *args: True,
            "pull_single_realm_data": pull,
            "time": SimpleNamespace(sleep=lambda _: setattr(owner, "running", False)),
        }
        exec(compile(ast.Module(body=[main], type_ignores=[]), "scheduler", "exec"), ns)
        ns["main"]()
        self.assertEqual(pools[0].feeds, [-110])
        self.assertEqual(pools[1].feeds, [110])
        self.assertEqual(pools[0].shutdown_calls, [(False, True)])
        pull.assert_called_once_with(110)
        pending.result.assert_not_called()


if __name__ == "__main__":
    unittest.main()
