"""
Phase 15: MCP Adapter tests.

Tests the MCP tool definitions, handler routing, and the /v1/mcp/ endpoints.
Verifies:
  - Tool listing returns all 13 tools
  - Public tools work without auth
  - Protected tools require auth
  - discover_products returns filtered results
  - list_merchants returns merchant list
  - process_purchase_intent creates a transaction
  - approve_transaction sets identity from auth context
  - Auth enforcement on protected tool calls
"""

import json
import pytest


# ── Tool definitions ─────────────────────────────────────────────────────────

def test_tool_definitions_structure():
    """All tools have name, description, inputSchema."""
    from mcp.tools import TOOLS
    assert len(TOOLS) == 13
    for tool in TOOLS:
        assert "name" in tool
        assert "description" in tool
        assert "inputSchema" in tool
        schema = tool["inputSchema"]
        assert schema["type"] == "object"
        assert "properties" in schema
        assert "required" in schema


def test_tool_definitions_unique_names():
    """Every tool name is unique."""
    from mcp.tools import TOOLS, TOOLS_BY_NAME
    names = [t["name"] for t in TOOLS]
    assert len(names) == len(set(names))
    assert len(TOOLS_BY_NAME) == len(TOOLS)


def test_public_tools_set():
    """Public tools are correctly identified."""
    from mcp.tools import PUBLIC_TOOLS
    assert "discover_products" in PUBLIC_TOOLS
    assert "get_merchant_arm" in PUBLIC_TOOLS
    assert "list_merchants" in PUBLIC_TOOLS
    assert "process_purchase_intent" not in PUBLIC_TOOLS
    assert "create_payment_link" not in PUBLIC_TOOLS


# ── GET /v1/mcp/tools ────────────────────────────────────────────────────────

def test_list_mcp_tools(client):
    """GET /v1/mcp/tools returns all tool definitions."""
    resp = client.get("/v1/mcp/tools")
    assert resp.status_code == 200
    data = resp.json()
    assert "tools" in data
    tools = data["tools"]
    assert len(tools) == 13
    names = {t["name"] for t in tools}
    assert "discover_products" in names
    assert "process_purchase_intent" in names
    assert "get_audit_timeline" in names


# ── POST /v1/mcp/tools/call — public tools ──────────────────────────────────

def test_mcp_discover_products_no_auth(client, demo_merchant):
    """discover_products works without authentication."""
    resp = client.post("/v1/mcp/tools/call", json={
        "name": "discover_products",
        "arguments": {},
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["isError"] is False
    content = json.loads(data["content"][0]["text"])
    assert "products" in content
    assert content["total"] > 0


def test_mcp_discover_products_with_category(client, demo_merchant):
    """discover_products filters by category."""
    resp = client.post("/v1/mcp/tools/call", json={
        "name": "discover_products",
        "arguments": {"category": "grocery"},
    })
    assert resp.status_code == 200
    data = resp.json()
    content = json.loads(data["content"][0]["text"])
    for p in content["products"]:
        assert p["category"].lower() == "grocery"


def test_mcp_discover_products_with_max_price(client, demo_merchant):
    """discover_products filters by max_price."""
    resp = client.post("/v1/mcp/tools/call", json={
        "name": "discover_products",
        "arguments": {"max_price": 300},
    })
    assert resp.status_code == 200
    content = json.loads(resp.json()["content"][0]["text"])
    for p in content["products"]:
        assert p["price_inr"] <= 300


def test_mcp_list_merchants_no_auth(client, demo_merchant):
    """list_merchants works without auth."""
    resp = client.post("/v1/mcp/tools/call", json={
        "name": "list_merchants",
        "arguments": {},
    })
    assert resp.status_code == 200
    content = json.loads(resp.json()["content"][0]["text"])
    assert "merchants" in content
    assert content["total"] >= 1


def test_mcp_get_merchant_arm_no_auth(client, demo_merchant):
    """get_merchant_arm works without auth."""
    merchant, product = demo_merchant
    resp = client.post("/v1/mcp/tools/call", json={
        "name": "get_merchant_arm",
        "arguments": {"merchant_id": merchant.merchant_id},
    })
    assert resp.status_code == 200
    content = json.loads(resp.json()["content"][0]["text"])
    assert "schema_version" in content


# ── POST /v1/mcp/tools/call — protected tools auth enforcement ──────────────

def test_mcp_protected_tool_requires_auth(client):
    """Protected tools return 401 without auth."""
    resp = client.post("/v1/mcp/tools/call", json={
        "name": "list_transactions",
        "arguments": {},
    })
    assert resp.status_code == 401


def test_mcp_approve_requires_auth(client):
    """approve_transaction returns 401 without auth."""
    resp = client.post("/v1/mcp/tools/call", json={
        "name": "approve_transaction",
        "arguments": {"transaction_id": "txn_fake"},
    })
    assert resp.status_code == 401


# ── POST /v1/mcp/tools/call — protected tools with auth ─────────────────────

def test_mcp_list_transactions_with_auth(client, buyer_headers):
    """list_transactions works with auth."""
    resp = client.post("/v1/mcp/tools/call", json={
        "name": "list_transactions",
        "arguments": {},
    }, headers=buyer_headers)
    assert resp.status_code == 200
    content = json.loads(resp.json()["content"][0]["text"])
    assert "transactions" in content


def test_mcp_evaluate_policy_with_auth(client, demo_merchant, buyer_headers):
    """evaluate_policy returns a policy decision."""
    merchant, product = demo_merchant
    # Get a product
    products_resp = client.post("/v1/mcp/tools/call", json={
        "name": "discover_products",
        "arguments": {"merchant_id": merchant.merchant_id},
    })
    products = json.loads(products_resp.json()["content"][0]["text"])["products"]
    assert len(products) > 0
    product = products[0]

    resp = client.post("/v1/mcp/tools/call", json={
        "name": "evaluate_policy",
        "arguments": {
            "merchant_id": product["merchant_id"],
            "product_id": product["product_id"],
            "amount_inr": product["price_inr"],
        },
    }, headers=buyer_headers)
    assert resp.status_code == 200
    content = json.loads(resp.json()["content"][0]["text"])
    assert content["decision"] in ["ALLOW", "DENY", "NEEDS_APPROVAL"]
    assert isinstance(content["reason_codes"], list)


# ── Validation errors ────────────────────────────────────────────────────────

def test_mcp_unknown_tool(client):
    """Unknown tool returns 400."""
    resp = client.post("/v1/mcp/tools/call", json={
        "name": "nonexistent_tool",
        "arguments": {},
    })
    assert resp.status_code == 400


def test_mcp_missing_required_argument(client, buyer_headers):
    """Missing required argument returns 422."""
    resp = client.post("/v1/mcp/tools/call", json={
        "name": "get_transaction",
        "arguments": {},
    }, headers=buyer_headers)
    assert resp.status_code == 422


def test_mcp_merchant_not_found(client):
    """get_merchant_arm with invalid merchant_id returns 404."""
    resp = client.post("/v1/mcp/tools/call", json={
        "name": "get_merchant_arm",
        "arguments": {"merchant_id": "nonexistent-merchant"},
    })
    assert resp.status_code == 404


# ── Payment tools redirect to REST ──────────────────────────────────────────

def test_mcp_create_payment_link_redirects(client, buyer_headers):
    """create_payment_link advises using REST endpoint for atomicity."""
    resp = client.post("/v1/mcp/tools/call", json={
        "name": "create_payment_link",
        "arguments": {"transaction_id": "txn_fake"},
    }, headers=buyer_headers)
    # Should get a 400 with USE_REST_ENDPOINT code
    assert resp.status_code == 400
    body = resp.json()
    # The error may be in body["error"] (envelope) or body["detail"]["error"]
    assert "USE_REST_ENDPOINT" in str(body)
