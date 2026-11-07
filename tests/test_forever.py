"""Offline Forever scanner coverage, including the Python constructor."""

import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import Mock, patch

import requests
from utils import forever
from utils.mega_data_setup import MegaData


class ForeverTests(unittest.TestCase):
    def test_markets_and_faction_filters(self):
        self.assertEqual(len(forever.FOREVER_MARKETS), 24)
        for region in ("naforever", "euforever"):
            data = json.loads(
                Path(
                    f"AzerothAuctionAssassinData/{region}-wow-connected-realm-ids.json"
                ).read_text()
            )
            self.assertEqual(data, forever.FOREVER_MARKETS)
        for faction in ("horde", "alliance", "booty bay"):
            self.assertEqual(
                len(forever.filter_markets(forever.FOREVER_MARKETS, faction)), 8
            )

    def test_undermine_links_and_existing_list_names(self):
        self.assertEqual(
            forever.undermine_link("EUFOREVER", 111, 2912),
            "https://undermine.exchange/#euf-pve-alliance/2912",
        )
        self.assertEqual(
            forever.undermine_link("NAFOREVER", -125, 2912),
            "https://undermine.exchange/#usf-rppvp-neutral/2912",
        )
        original = {
            "Alliance Auction House 111 — Items": 111,
            "Blackwater Auction House 125 — Commodities": -125,
        }
        self.assertEqual(
            forever.rename_markets(original),
            {
                "Normal Alliance — Items": 111,
                "Roleplay PvP Neutral — Commodities": -125,
            },
        )
        self.assertEqual(forever.rename_markets({"Custom": 111}), {"Custom": 111})

    def test_atomic_market_write_failure_preserves_original(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "markets.json"
            path.write_text('{"Selected":110}')
            with patch.object(Path, "replace", side_effect=OSError("disk error")):
                with self.assertRaises(OSError):
                    forever.save_markets(path, {"New": 111})
            self.assertEqual(json.loads(path.read_text()), {"Selected": 110})
            self.assertEqual(len(list(Path(directory).iterdir())), 1)

    def test_untracked_feeds_remain_eligible_until_first_success(self):
        data = MegaData.__new__(MegaData)
        data.REGION = "NAFOREVER"
        data.WOW_SERVER_NAMES = {"Items": 110, "Commodities": -110}
        data.upload_timers = {-110: {"dataSetID": -110}}
        self.assertEqual(data.get_untracked_forever_feeds(), [110])
        data.upload_timers[110] = {"dataSetID": 110}
        self.assertEqual(data.get_untracked_forever_feeds(), [])

    def test_invalid_market_files_recover_without_overwriting_and_empty_stays_empty(
        self,
    ):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "markets.json"
            for content in (
                "null",
                "[]",
                "{broken",
                '{"Alliance Auction House 111 — Items":"bad"}',
                '{"Custom":"bad"}',
            ):
                path.write_text(content)
                with redirect_stdout(io.StringIO()):
                    self.assertEqual(
                        forever.load_markets(path, migrate=True),
                        forever.FOREVER_MARKETS,
                    )
                self.assertEqual(path.read_text(), content)
            path.write_text("{}")
            self.assertEqual(forever.load_markets(path, migrate=True), {})
            self.assertEqual(path.read_text(), "{}")

    def test_forever_uses_one_attempt_then_backoff_and_resets_on_success(self):
        data = MegaData.__new__(MegaData)
        data.REGION = "NAFOREVER"
        data.forever_failures = {}
        data._make_ah_api_request = Mock(side_effect=requests.Timeout("offline"))
        with redirect_stdout(io.StringIO()), patch(
            "utils.mega_data_setup.time.monotonic", return_value=100
        ):
            self.assertEqual(data.get_listings_single(110), [])
            self.assertIsNone(data.get_listings_single(110))
            self.assertEqual(data._make_ah_api_request.call_count, 1)
            data.forever_failures[110]["next_retry"] = 0
            data._make_ah_api_request.side_effect = None
            data._make_ah_api_request.return_value = {"auctions": []}
            self.assertEqual(data.get_listings_single(110), [])
        self.assertEqual(data.forever_failures, {})

    def test_urls_and_unit_prices(self):
        self.assertIn(
            "us.api.blizzard.com/data/wow/ruleset/1/auctions/110?",
            forever.auction_url("NAFOREVER", 110),
        )
        self.assertIn(
            "/110/commodities?namespace=dynamic-forever-eu",
            forever.auction_url("EUFOREVER", -110),
        )
        self.assertEqual(
            forever.unit_price({"buyout": 200000, "quantity": 2}, "buyout"), 100000
        )
        self.assertEqual(
            forever.unit_price({"unit_price": 110000, "quantity": 20}, "unit_price"),
            110000,
        )
        for quantity in (None, 0, -1):
            self.assertIsNone(
                forever.unit_price({"buyout": 100, "quantity": quantity}, "buyout")
            )
        with self.assertRaises(ValueError):
            forever.auction_url("NAFOREVER", 112)

    def test_constructor_skips_pet_and_ilvl_files_and_remote_catalogs(self):
        with tempfile.TemporaryDirectory() as directory:
            config = Path(directory) / "config.json"
            config.write_text(
                json.dumps(
                    {
                        "WOW_REGION": "NAFOREVER",
                        "FACTION": "horde",
                        "WOW_CLIENT_ID": "test",
                        "WOW_CLIENT_SECRET": "test-secret",
                        "MEGA_WEBHOOK_URL": "unused",
                    }
                )
            )
            items = Path(directory) / "items.json"
            items.write_text('{"3048": 12}')
            invalid = Path(directory) / "invalid.json"
            invalid.write_text("not valid JSON: unsupported lists must never be read")
            with patch.object(
                MegaData, "check_access_token", return_value="test-token"
            ), patch(
                "utils.mega_data_setup.get_forever_itemnames",
                return_value={"3048": "Forever name"},
            ) as names, patch(
                "utils.mega_data_setup.get_bonus_id_sets",
                side_effect=AssertionError("Raidbots requested"),
            ), patch(
                "utils.mega_data_setup.get_petnames",
                side_effect=AssertionError("Pets requested"),
            ), redirect_stdout(
                io.StringIO()
            ):
                data = MegaData(
                    str(config),
                    str(items),
                    str(invalid),
                    str(invalid),
                    str(invalid),
                    str(invalid),
                )
            names.assert_called_once_with([3048])
            self.assertEqual(data.ITEM_NAMES, {3048: "Forever name"})
            self.assertEqual(data.DESIRED_PETS, {})
            self.assertEqual(data.DESIRED_ILVL_LIST, [])
            self.assertEqual(data.DESIRED_PET_ILVL_LIST, [])
            self.assertEqual(len(data.WOW_SERVER_NAMES), 8)

    def test_each_feed_is_polled_and_skipped_independently(self):
        data = MegaData.__new__(MegaData)
        data.REGION = "EUFOREVER"
        data.forever_failures = {}
        data.WOW_SERVER_NAMES = forever.FOREVER_MARKETS
        data.upload_timers = {}
        data.session = Mock()
        data.check_access_token = Mock(return_value="test")
        data.wait_for_rate_limit = Mock()

        def response(status=200):
            r = requests.Response()
            r.status_code = status
            r.url = "https://example.test"
            r.headers["Last-Modified"] = "Fri, 06 Nov 2026 14:00:00 GMT"
            r.raw = io.BytesIO(b'{"auctions":[{"id":1}]}')
            return r

        data.session.get.side_effect = [
            response(),
            response(),
            response(304),
            response(304),
        ]
        with redirect_stdout(io.StringIO()):
            self.assertEqual(data.get_listings_single(110), [{"id": 1}])
            self.assertEqual(data.get_listings_single(-110), [{"id": 1}])
            self.assertIsNone(data.get_listings_single(110))
            self.assertIsNone(data.get_listings_single(-110))
        self.assertEqual(set(data.upload_timers), {110, -110})
        calls = data.session.get.call_args_list
        self.assertNotIn("If-Modified-Since", calls[0].kwargs["headers"])
        self.assertNotIn("If-Modified-Since", calls[1].kwargs["headers"])
        self.assertIn("If-Modified-Since", calls[2].kwargs["headers"])
        self.assertIn("If-Modified-Since", calls[3].kwargs["headers"])
        self.assertEqual(
            data.upload_timers[-110]["tableName"], "EU_forever_110_commodityListings"
        )


if __name__ == "__main__":
    unittest.main()
