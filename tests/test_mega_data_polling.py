"""Regression tests for conditional auction polling (no live API calls)."""

import io
import unittest
from contextlib import redirect_stdout
from unittest.mock import Mock, patch

import orjson
import requests

from utils.mega_data_setup import MegaData


class ConditionalPollingTests(unittest.TestCase):
    def setUp(self):
        # Avoid constructor file/network setup; exercise the real polling methods.
        self.data = MegaData.__new__(MegaData)
        self.data.REGION = "NACLASSIC"
        self.data.FACTION = "all"
        self.data.WOW_SERVER_NAMES = {"Test Realm": 123}
        self.data.upload_timers = {}
        self.data.session = Mock()
        self.data.check_access_token = Mock(return_value="test-token")
        self.data.wait_for_rate_limit = Mock()
        output = redirect_stdout(io.StringIO())
        output.__enter__()
        self.addCleanup(output.__exit__, None, None, None)
        sleeper = patch("utils.mega_data_setup.time.sleep")
        sleeper.start()
        self.addCleanup(sleeper.stop)

    @staticmethod
    def response(status=200, minute=None, auctions=None, content=None):
        response = requests.Response()
        response.status_code = status
        response.url = "https://example.test/auctions"
        if minute is not None:
            response.headers["last-modified"] = (
                f"Sat, 10 Oct 2026 10:{minute:02d}:00 GMT"
            )
        if content is None:
            content = (
                b"" if status == 304 else orjson.dumps({"auctions": auctions or []})
            )
        response.raw = io.BytesIO(content)
        response.close = Mock(wraps=response.close)
        return response

    def test_classic_continues_past_unchanged_endpoints(self):
        for changed_index in range(3):
            with self.subTest(changed_index=changed_index):
                responses = [self.response(304) for _ in range(3)]
                responses[changed_index] = self.response(auctions=[{"id": 42}])
                self.data.session.get.reset_mock()
                self.data.session.get.side_effect = responses
                self.assertEqual(self.data.get_listings_single(123), [{"id": 42}])
                self.assertEqual(self.data.session.get.call_count, 3)
                for response in responses:
                    response.close.assert_called_once()

    def test_classic_returns_none_only_when_all_endpoints_skipped(self):
        self.data.session.get.side_effect = [self.response(304) for _ in range(3)]
        self.assertIsNone(self.data.get_listings_single(123))
        self.assertEqual(self.data.session.get.call_count, 3)

    def test_changed_empty_endpoint_is_not_all_skipped(self):
        self.data.session.get.side_effect = [
            self.response(304),
            self.response(),
            self.response(304),
        ]
        self.assertEqual(self.data.get_listings_single(123), [])

    def test_classic_timestamps_and_fallback_are_independent(self):
        self.data.session.get.side_effect = [
            self.response(minute=0, auctions=[{"id": 2}]),
            self.response(minute=0, auctions=[{"id": 6}]),
            self.response(minute=5, auctions=[{"id": 7}]),
        ]
        self.assertEqual(
            self.data.get_listings_single(123), [{"id": 2}, {"id": 6}, {"id": 7}]
        )
        for call in self.data.session.get.call_args_list:
            self.assertNotIn("If-Modified-Since", call.kwargs["headers"])
        self.assertEqual(self.data.get_upload_time_minutes(), [0, 5])
        self.assertEqual(
            {timer["dataSetID"] for timer in self.data.get_upload_time_list()}, {123}
        )
        unchanged = self.response(minute=0, content=b"must not be parsed")
        self.data.session.get.reset_mock()
        self.data.session.get.side_effect = [
            self.response(minute=2, auctions=[{"id": 22}]),
            unchanged,
            self.response(304),
        ]
        self.assertEqual(self.data.get_listings_single(123), [{"id": 22}])
        expected_minutes = [0, 0, 5]
        for call, minute in zip(self.data.session.get.call_args_list, expected_minutes):
            self.assertEqual(
                call.kwargs["headers"]["If-Modified-Since"],
                f"Sat, 10 Oct 2026 10:{minute:02d}:00 GMT",
            )
        self.assertFalse(unchanged._content_consumed)
        unchanged.close.assert_called_once()
        self.assertEqual(self.data.get_upload_time_minutes(), [0, 2, 5])

    def test_single_faction_requests_only_its_endpoint(self):
        for faction, endpoint in [
            ("alliance", "/2"),
            ("horde", "/6"),
            ("booty bay", "/7"),
        ]:
            with self.subTest(faction=faction):
                self.data.FACTION = faction
                self.data.session.get.reset_mock()
                self.data.session.get.return_value = self.response(minute=0)
                self.assertEqual(self.data.get_listings_single(123), [])
                self.data.session.get.assert_called_once()
                self.assertIn(
                    f"/auctions{endpoint}?", self.data.session.get.call_args.args[0]
                )
                self.assertIn((123, endpoint), self.data.upload_timers)

    def test_retail_and_commodities_preserve_conditional_polling(self):
        for region, realm in [("NA", 123), ("NA", -1), ("EU", -2)]:
            with self.subTest(region=region, realm=realm):
                self.data.REGION = region
                self.data.upload_timers.clear()
                unchanged = self.response(minute=0, content=b"must not be parsed")
                self.data.session.get.side_effect = [
                    self.response(minute=0, auctions=[{"id": 42}]),
                    unchanged,
                    self.response(304),
                ]
                self.assertEqual(self.data.get_listings_single(realm), [{"id": 42}])
                self.assertIn(realm, self.data.upload_timers)
                self.assertIsNone(self.data.get_listings_single(realm))
                self.assertIsNone(self.data.get_listings_single(realm))
                self.assertFalse(unchanged._content_consumed)
                self.assertEqual(
                    self.data.session.get.call_args.kwargs["headers"][
                        "If-Modified-Since"
                    ],
                    "Sat, 10 Oct 2026 10:00:00 GMT",
                )

    def test_http_errors_close_streams_without_reading_body(self):
        self.data.REGION = "NA"
        for commodity in [False, True]:
            for status in [429, 500, 403]:
                with self.subTest(commodity=commodity, status=status):
                    response = self.response(status)
                    self.data.session.get.return_value = response
                    with self.assertRaisesRegex(Exception, "BLIZZARD"):
                        if commodity:
                            self.data.make_commodity_ah_api_request()
                        else:
                            self.data.make_ah_api_request("https://example.test", 123)
                    response.close.assert_called_once()
                    self.assertFalse(response._content_consumed)

    def test_truncated_dump_retries_without_advancing_timestamp(self):
        self.data.REGION = "NA"
        for realm in [123, -1]:
            with self.subTest(realm=realm):
                self.data.upload_timers.clear()
                self.data.session.get.reset_mock()
                bad = self.response(minute=0, content=b'{"auctions": [')
                good = self.response(minute=0, auctions=[{"id": 42}])
                self.data.session.get.side_effect = [bad, good]
                self.assertEqual(self.data.get_listings_single(realm), [{"id": 42}])
                self.assertEqual(self.data.session.get.call_count, 2)
                for call in self.data.session.get.call_args_list:
                    self.assertNotIn("If-Modified-Since", call.kwargs["headers"])
                bad.close.assert_called_once()
                good.close.assert_called_once()
                self.assertIn(realm, self.data.upload_timers)


if __name__ == "__main__":
    unittest.main()
