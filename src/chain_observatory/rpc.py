from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, asdict
from typing import Any


@dataclass(frozen=True)
class RpcResult:
    method: str
    ok: bool
    latency_ms: float
    result: Any = None
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _rpc_call(url: str, method: str, params: list[Any] | None = None, timeout: float = 12.0) -> RpcResult:
    payload = json.dumps({
        "jsonrpc": "2.0",
        "id": 1,
        "method": method,
        "params": params or [],
    }).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json", "User-Agent": "chain-observatory/0.1"},
        method="POST",
    )
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read().decode("utf-8")
        latency_ms = round((time.perf_counter() - started) * 1000, 2)
        decoded = json.loads(body)
        if "error" in decoded:
            return RpcResult(method, False, latency_ms, error=json.dumps(decoded["error"], sort_keys=True))
        return RpcResult(method, True, latency_ms, result=decoded.get("result"))
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError, OSError) as exc:
        latency_ms = round((time.perf_counter() - started) * 1000, 2)
        return RpcResult(method, False, latency_ms, error=f"{type(exc).__name__}: {exc}")


def parse_hex_int(value: Any) -> int | None:
    if not isinstance(value, str):
        return None
    try:
        return int(value, 16)
    except ValueError:
        return None


def probe_endpoint(url: str, timeout: float = 12.0) -> dict[str, Any]:
    methods = [
        ("eth_chainId", []),
        ("eth_blockNumber", []),
        ("eth_gasPrice", []),
        ("web3_clientVersion", []),
    ]
    calls = [_rpc_call(url, method, params, timeout=timeout) for method, params in methods]
    by_method = {item.method: item for item in calls}
    latencies = [item.latency_ms for item in calls if item.ok]

    chain_id = parse_hex_int(by_method["eth_chainId"].result)
    block_number = parse_hex_int(by_method["eth_blockNumber"].result)
    gas_price_wei = parse_hex_int(by_method["eth_gasPrice"].result)

    return {
        "ok": any(item.ok for item in calls),
        "successful_calls": sum(1 for item in calls if item.ok),
        "total_calls": len(calls),
        "avg_latency_ms": round(sum(latencies) / len(latencies), 2) if latencies else None,
        "chain_id": chain_id,
        "block_number": block_number,
        "gas_price_wei": gas_price_wei,
        "client_version": by_method["web3_clientVersion"].result if by_method["web3_clientVersion"].ok else None,
        "calls": [item.to_dict() for item in calls],
    }
