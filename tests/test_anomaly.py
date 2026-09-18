import unittest

from chain_observatory.anomaly import detect_anomalies


class AnomalyTests(unittest.TestCase):
    def test_chain_mismatch_is_critical(self):
        anomalies = detect_anomalies({
            "chain_id_matches_expected": False,
            "health_score": 100,
            "latest_block": {"age_seconds": 1},
        })
        self.assertTrue(any(item["kind"] == "chain-id-mismatch" for item in anomalies))

    def test_latency_spike(self):
        anomalies = detect_anomalies(
            {
                "chain_id_matches_expected": True,
                "health_score": 90,
                "avg_latency_ms": 900,
                "latest_block": {"age_seconds": 1},
            },
            {"avg_latency_ms": 200},
        )
        self.assertTrue(any(item["kind"] == "latency-spike" for item in anomalies))

    def test_healthy_sample_has_no_anomaly(self):
        anomalies = detect_anomalies({
            "chain_id_matches_expected": True,
            "health_score": 95,
            "avg_latency_ms": 120,
            "latest_block": {"age_seconds": 10},
            "progression": {"blocks_advanced": 10, "elapsed_seconds": 900},
        })
        self.assertEqual(anomalies, [])


if __name__ == "__main__":
    unittest.main()
