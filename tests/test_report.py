import json
import tempfile
import unittest
from pathlib import Path

from chain_observatory.report import build_reports


class ReportTests(unittest.TestCase):
    def test_build_reports(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            observations = root / "data" / "observations" / "2026-09-17"
            reports = root / "reports"
            metrics = root / "metrics"
            observations.mkdir(parents=True)
            sample = {
                "schema_version": 2,
                "collected_at_utc": "2026-09-17T12:00:00Z",
                "networks": [{
                    "name": "testnet",
                    "ok": True,
                    "successful_calls": 9,
                    "total_calls": 9,
                    "avg_latency_ms": 10.5,
                    "health_score": 100,
                    "block_number": 100,
                    "chain_id": 123,
                    "gas_price_wei": 1,
                    "client_version": "test-client",
                    "latest_block": {"age_seconds": 2, "gas_utilization_pct": 50.0},
                    "progression": {"estimated_block_time_seconds": 2.0},
                }],
            }
            (observations / "120000Z.json").write_text(json.dumps(sample), encoding="utf-8")
            build_reports(root / "data" / "observations", reports, metrics)
            self.assertTrue((reports / "latest.md").exists())
            self.assertTrue((reports / "daily" / "2026-09-17.md").exists())
            self.assertTrue((metrics / "network-latest.json").exists())
            self.assertTrue((metrics / "daily-history.csv").exists())
            self.assertIn("testnet", (reports / "latest.md").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
