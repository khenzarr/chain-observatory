import unittest
from unittest.mock import patch

from chain_observatory.rpc import parse_hex_int, probe_endpoint, RpcResult


class RpcTests(unittest.TestCase):
    def test_parse_hex_int(self):
        self.assertEqual(parse_hex_int("0x1"), 1)
        self.assertEqual(parse_hex_int("0x13b2"), 5042)
        self.assertIsNone(parse_hex_int("nope"))
        self.assertIsNone(parse_hex_int(None))

    @patch("chain_observatory.rpc._rpc_call")
    def test_probe_endpoint(self, call):
        results = {
            "eth_chainId": RpcResult("eth_chainId", True, 10.0, "0x1"),
            "eth_blockNumber": RpcResult("eth_blockNumber", True, 20.0, "0x64"),
            "eth_gasPrice": RpcResult("eth_gasPrice", True, 30.0, "0x3b9aca00"),
            "web3_clientVersion": RpcResult("web3_clientVersion", True, 40.0, "client/1.0"),
        }
        call.side_effect = lambda url, method, params, timeout: results[method]
        result = probe_endpoint("https://example.invalid")
        self.assertTrue(result["ok"])
        self.assertEqual(result["chain_id"], 1)
        self.assertEqual(result["block_number"], 100)
        self.assertEqual(result["gas_price_wei"], 1_000_000_000)
        self.assertEqual(result["avg_latency_ms"], 25.0)


if __name__ == "__main__":
    unittest.main()
