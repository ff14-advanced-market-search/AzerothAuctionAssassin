"""Run the real worker/GUI coordination methods without a desktop session."""

import ast
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

from utils import forever


class Signal:
    def __init__(self):
        self.listeners = []

    def connect(self, callback):
        self.listeners.append(callback)

    def emit(self, *args):
        for listener in self.listeners:
            listener(*args)


class Thread:
    def __init__(self, parent=None):
        self.finished = Signal()
        self.running = False
        self.starts = 0

    def isRunning(self):
        return self.running

    def start(self):
        self.starts += 1
        self.running = True

    def finish(self):
        self.running = False
        self.finished.emit()


class Frame:
    def __init__(self, rows=None, columns=None):
        self.rows = rows or []
        self.empty = not self.rows

    def sort_values(self, by):
        return self

    def __getitem__(self, key):
        return SimpleNamespace(tolist=lambda: [row[key] for row in self.rows])


def classes():
    tree = ast.parse(Path("AzerothAuctionAssassin.py").read_text())
    worker = next(
        n
        for n in tree.body
        if isinstance(n, ast.ClassDef) and n.name == "Item_And_Pet_Statistics"
    )
    app = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "App")
    app.bases = []
    keep = {
        "statistics_request_finished",
        "statistics_request_failed",
        "clear_statistics",
        "api_data_received",
        "on_region_changed",
        "validate_item_lists",
    }
    app.body = [
        n for n in app.body if isinstance(n, ast.FunctionDef) and n.name in keep
    ]
    ns = {
        "__name__": "legacy_test",
        "QThread": Thread,
        "pyqtSignal": lambda *args: Signal(),
        "pd": SimpleNamespace(DataFrame=Frame),
        "QMessageBox": Mock(),
        "QComboBox": SimpleNamespace(NoInsert=0),
        "forever": forever,
    }
    exec(
        compile(ast.Module(body=[worker, app], type_ignores=[]), "legacy_gui", "exec"),
        ns,
    )
    return ns


class StatisticsTests(unittest.TestCase):
    def setUp(self):
        self.ns = classes()
        self.worker = self.ns["Item_And_Pet_Statistics"]()
        self.app = self.ns["App"]()
        self.app.api_data_thread = self.worker
        for name in ("item_name_input", "pet_name_input", "pet_ilvl_name_input"):
            setattr(self.app, name, Mock())
        self.worker.failed.connect(self.app.statistics_request_failed)
        self.worker.finished.connect(self.app.statistics_request_finished)

    def test_request_failure_still_starts_pending_region(self):
        self.worker.set_region("NA")
        self.app.on_region_changed("EUFOREVER")
        self.worker.load_statistics = Mock(
            side_effect=ValueError("API and backup down")
        )
        self.worker.run()
        self.worker.finish()
        self.assertEqual(self.worker.region, "EUFOREVER")
        self.assertEqual(self.worker.starts, 2)
        self.assertTrue(self.app.item_statistics.empty)
        self.assertTrue(self.app.pet_statistics.empty)

    def test_active_request_failure_clears_data_and_reports_error(self):
        self.worker.set_region("NAFOREVER")
        self.app.item_statistics = Frame([{"itemName": "Old"}])
        self.worker.load_statistics = Mock(side_effect=ValueError("unavailable"))
        self.worker.run()
        self.worker.finish()
        self.assertTrue(self.app.item_statistics.empty)
        self.ns["QMessageBox"].warning.assert_called_once()

    def test_stale_completion_is_ignored_after_new_region_starts(self):
        self.worker.region = self.worker.pending_region = "EUFOREVER"
        self.app.api_data_received("NA", Frame(), Frame([{"itemName": "Old"}]))
        self.app.item_name_input.clear.assert_not_called()

    def test_selection_handlers_connected_once_across_refreshes(self):
        self.app.on_combo_box_pet_changed = Mock()
        self.app.on_combo_box_item_changed = Mock()
        for _ in range(2):
            self.app.api_data_received("EU", Frame(), Frame([{"itemName": "Item"}]))
        self.app.pet_name_input.currentIndexChanged.connect.assert_called_once()
        self.app.item_name_input.currentIndexChanged.connect.assert_called_once()

    def test_forever_requires_items_and_ignores_saved_unsupported_rules(self):
        self.app.wow_region = Mock()
        self.app.wow_region.currentText.return_value = "NAFOREVER"
        self.app.items_list = {}
        self.app.pet_list = {1: 20}
        self.app.ilvl_list = [{"invalid": "not active"}]
        self.assertFalse(self.app.validate_item_lists())
        self.app.items_list = {"3048": 10}
        self.assertTrue(self.app.validate_item_lists())
        self.assertEqual(self.app.ilvl_list, [{"invalid": "not active"}])


if __name__ == "__main__":
    unittest.main()
