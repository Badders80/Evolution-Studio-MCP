#!/usr/bin/env python3
"""Proper MCP stdio protocol test."""

import json
import select
import subprocess
import time

try:
    from mcp import types as mcp_types
except Exception:
    mcp_types = None


def send_request(server, request, timeout=15):
    """Send a JSON-RPC request and read a single-line response with timeout."""
    request_str = json.dumps(request) + "\n"
    server.stdin.write(request_str)
    server.stdin.flush()
    ready, _, _ = select.select([server.stdout], [], [], timeout)
    if not ready:
        if server.poll() is not None:
            err = server.stderr.read()
            raise RuntimeError(f"Server exited early. Stderr:\n{err}")
        raise TimeoutError(f"No response after {timeout}s for {request.get('method')}")
    response_str = server.stdout.readline()
    return json.loads(response_str) if response_str else None


def send_notification(server, notification):
    """Send a JSON-RPC notification (no response expected)."""
    notification_str = json.dumps(notification) + "\n"
    server.stdin.write(notification_str)
    server.stdin.flush()


def main():
    # Start MCP server
    server = subprocess.Popen(
        ["python", "main.py"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
    )

    try:
        print("Testing Evolution Studio MCP Server")

        # Initialize session (required by MCP)
        protocol_version = (
            mcp_types.LATEST_PROTOCOL_VERSION if mcp_types else "2025-11-25"
        )
        init_request = {
            "jsonrpc": "2.0",
            "id": 0,
            "method": "initialize",
            "params": {
                "protocolVersion": protocol_version,
                "capabilities": {},
                "clientInfo": {"name": "test_mcp", "version": "0.1.0"},
            },
        }
        _ = send_request(server, init_request)
        send_notification(server, {"jsonrpc": "2.0", "method": "initialized", "params": {}})
        time.sleep(0.1)

        # Test 1: List tools
        tools_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/list",
        }
        response = send_request(server, tools_request)
        tools = response.get("result", {}).get("tools", []) if response else []
        print(f"Found {len(tools)} tools")

        # Test 2: Call list_models
        call_request = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {
                "name": "list_models",
                "arguments": {},
            },
        }
        response = send_request(server, call_request)
        print(f"list_models result: {response.get('result', {}) if response else {}}")

        # Test 3: GPU Status
        gpu_request = {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": "gpu_status",
                "arguments": {},
            },
        }
        response = send_request(server, gpu_request)
        print(f"gpu_status result: {response.get('result', {}) if response else {}}")

        print("All tests completed")
    finally:
        server.terminate()
        server.wait()


if __name__ == "__main__":
    main()
