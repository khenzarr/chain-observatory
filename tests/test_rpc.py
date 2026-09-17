import unittest
from datetime import datetime, timezone
from unittest.mock import patch

from chain_observatory.rpc import parse_hex_int, probe_endpoint, RpcResult, _health_score, _latest_block_metrics


class RpcTests(unittest.TestCase):
    def test_parse_hex_int(self):
        self.assertEqual(parse_hex_int("0x1"), 1)
        self.assertEqual(parse_hex_int("0x13b2"), 5042)
        self.assertIsNone(parse_hex_int("nope"))
        self.assertIsNone(parse_hex_int(None))

    def test_health_score_bounds(self):
        self.assertEqual(_health_score(success_ratio=1.0, latency_ms=100, block_age_seconds=5, chain_id_matches_expected=True), 100)
        self.assertGreaterEqual(_health_score(success_ratio=0.0, latency_ms=None, block_age_seconds=9999, chain_id_matches_expected=False), 0)

    def test_latest_block_metrics(self):
        now = datetime.fromtimestamp(110, tz=timezone.utc)
        block = {
            "number": "0x64",
            "timestamp": "0x64",
            "gasLimit": "0x64",
            "gasUsed": "0x32",
            "baseFeePerGas": "0x1",
            "transactions": ["a", "b"],
            "hash": "0xabc",
        }
        result = _latest_block_metrics(block, now)
        self.assertEqual(result["number"], 100)
        self.assertEqual(result["age_seconds"], 10)
        self.assertEqual(result["transaction_count"], 2)
        self.assertEqual(result["gas_utilization_pct"], 50.0)

    @patch("chain_observatory.rpc._rpc_call")
    def test_probe_endpoint(self, call):
        results = {
            "eth_chainId": RpcResult("eth_chainId", True, 10.0, "0x1"),
            "eth_blockNumber": RpcResult("eth_blockNumber", True, 20.0, "0x64"),
            "eth_gasPrice": RpcResult("eth_gasPrice", True, 30.0, "0x3b9aca00"),
            "web3_clientVersion": RpcResult("web3_clientVersion", True, 40.0, "client/1.0"),
            "eth_getBlockByNumber": RpcResult("eth_getBlockByNumber", True, 50.0, {"number":"0x64","timestamp":"0x1","gasLimit":"0x64","gasUsed":"0x32","transactions":[]}),
            "eth_feeHistory": RpcResult("eth_feeHistory", True, 60.0, {"oldestBlock":"0x60","baseFeePerGas":["0x1","0x2"],"gasUsedRatio":[0.5],"reward":[["0x1","0x2","0x3"]]}),
            "eth_syncing": RpcResult("eth_syncing", True, 70.0, False),
            "net_peerCount": RpcResult("net_peerCount", True, 80.0, "0x8"),
            "net_version": RpcResult("net_version", True, 90.0, "1"),
        }
        call.side_effect = lambda url, method, params, timeout: results[method]
        result = probe_endpoint("https://example.invalid", expected_chain_id=1)
        self.assertTrue(result["ok"])
        self.assertEqual(result["chain_id"], 1)
        self.assertEqual(result["block_number"], 100)
        self.assertEqual(result["gas_price_wei"], 1_000_000_000)
        self.assertEqual(result["avg_latency_ms"], 50.0)
        self.assertEqual(result["peer_count"], 8)
        self.assertTrue(result["chain_id_matches_expected"])


if __name__ == "__main__":
    unittest.main()
