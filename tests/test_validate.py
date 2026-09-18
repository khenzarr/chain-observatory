import unittest

from chain_observatory.validate import validate_payload


class ValidateTests(unittest.TestCase):
    def test_valid_payload(self):
        payload = {
            "schema_version": 3,
            "collected_at_utc": "2026-09-17T12:00:00Z",
            "networks": [{"name": "arc-mainnet", "successful_calls": 8, "total_calls": 9, "health_score": 92}],
        }
        self.assertEqual(validate_payload(payload), [])

    def test_invalid_score(self):
        payload = {
            "schema_version": 3,
            "collected_at_utc": "2026-09-17T12:00:00Z",
            "networks": [{"name": "arc-mainnet", "successful_calls": 1, "total_calls": 1, "health_score": 101}],
        }
        self.assertTrue(validate_payload(payload))


if __name__ == "__main__":
    unittest.main()
