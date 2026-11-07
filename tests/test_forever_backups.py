"""Forever public backup fallback and safe snapshot replacement tests."""

import ast
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import requests
from utils.api_requests import get_forever_itemnames, get_forever_item_statistics

NAMES = {"3048": "Lambent Scale Legguards", "720": "Brawler Gloves"}
STATS = [
    {
        "itemID": 3048,
        "itemName": "Lambent Scale Legguards",
        "desiredPrice": 1,
        "salesPerDay": 2.5,
    }
]


def response(data):
    return Mock(json=Mock(return_value=data), raise_for_status=Mock())


class ForeverBackupTests(unittest.TestCase):
    @patch("utils.api_requests.requests.get")
    @patch("utils.api_requests.requests.post")
    def test_nonconvertible_unicode_item_id_triggers_names_backup(self, post, get):
        post.return_value = response({"²": "Invalid ID"})
        get.return_value = response(NAMES)
        self.assertEqual(get_forever_itemnames([3048]), {"3048": NAMES["3048"]})
        get.assert_called_once()

    @patch("utils.api_requests.requests.get")
    @patch("utils.api_requests.requests.post")
    def test_names_fall_back_to_github_and_filter_requested_ids(self, post, get):
        post.side_effect = requests.ConnectionError("offline")
        get.return_value = response(NAMES)
        self.assertEqual(get_forever_itemnames([3048]), {"3048": NAMES["3048"]})
        self.assertTrue(
            get.call_args.args[0].endswith("/StaticData/forever_item_names.json")
        )

    @patch("utils.api_requests.requests.get")
    @patch("utils.api_requests.requests.post")
    def test_bad_api_response_uses_matching_region_backup(self, post, get):
        post.return_value = response({"exception": "Unavailable"})
        get.return_value = response(NAMES)
        rows = get_forever_item_statistics("EU")
        self.assertEqual(rows[0]["itemName"], NAMES["3048"])
        self.assertTrue(
            all(row["desiredPrice"] == row["salesPerDay"] == 0 for row in rows)
        )
        self.assertTrue(get.call_args.args[0].endswith("/forever_item_names.json"))

    @patch("utils.api_requests.requests.get")
    @patch("utils.api_requests.requests.post")
    def test_healthy_api_does_not_request_backup(self, post, get):
        post.return_value = response(STATS)
        self.assertEqual(get_forever_item_statistics("NA"), STATS)
        get.assert_not_called()

    @patch("utils.api_requests.requests.get")
    @patch("utils.api_requests.requests.post")
    def test_updater_never_fetches_stale_fallback_on_failure(self, post, get):
        post.side_effect = requests.Timeout("offline")
        with self.assertRaises(requests.Timeout):
            get_forever_itemnames([], use_backup=False)
        get.assert_not_called()

    def load_updater(self, names, statistics):
        path = Path("update-static-saddlebag-data.py")
        tree = ast.parse(path.read_text())
        func = next(
            n
            for n in tree.body
            if isinstance(n, ast.FunctionDef) and n.name == "update_forever_static_data"
        )
        ns = {
            "Path": Path,
            "json": json,
            "get_forever_itemnames": names,
            "get_forever_item_statistics": statistics,
        }
        exec(compile(ast.Module(body=[func], type_ignores=[]), str(path), "exec"), ns)
        return ns[func.name]

    def test_failed_refresh_preserves_existing_backups(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "forever_item_names.json"
            path.write_text("existing snapshot")
            update = self.load_updater(
                Mock(side_effect=requests.HTTPError("down")), Mock()
            )
            with self.assertRaises(requests.HTTPError):
                update(directory)
            self.assertEqual(path.read_text(), "existing snapshot")
            self.assertEqual(len(list(Path(directory).iterdir())), 1)

    def test_filesystem_failure_does_not_stop_other_static_updates(self):
        tree = ast.parse(Path("update-static-saddlebag-data.py").read_text())
        block = next(node for node in tree.body if isinstance(node, ast.Try))
        continued = Mock()
        ns = {
            "requests": requests,
            "update_forever_static_data": Mock(side_effect=OSError("disk error")),
            "continued": continued,
        }
        continuation = ast.parse("continued()").body[0]
        exec(
            compile(
                ast.Module(body=[block, continuation], type_ignores=[]),
                "updater",
                "exec",
            ),
            ns,
        )
        continued.assert_called_once()

    def test_refresh_writes_only_names(self):
        names, statistics = Mock(return_value=NAMES), Mock(return_value=STATS)
        with tempfile.TemporaryDirectory() as directory:
            self.load_updater(names, statistics)(directory)
            names.assert_called_once_with([], use_backup=False)
            self.assertEqual(
                json.loads((Path(directory) / "forever_item_names.json").read_text()),
                NAMES,
            )
            self.assertEqual(len(list(Path(directory).iterdir())), 1)
            statistics.assert_not_called()


if __name__ == "__main__":
    unittest.main()
