"""
MCP tool definitions for AgentSetu.

Each tool is a dict conforming to the MCP tool schema:
  { name, description, inputSchema: { type, properties, required } }

Tools are grouped by capability:
  - Discovery (public): discover_products, get_merchant_arm, list_merchants
  - Transaction (auth required): process_purchase_intent, select_product,
    evaluate_policy, approve_transaction
  - Payment (auth required): create_payment_link, verify_payment, get_receipt
  - Audit (auth required): get_transaction, list_transactions, get_audit_timeline
"""

from typing import Any

# ── Tool definitions ────────────────────────────────────────────────────────

TOOLS: list[dict[str, Any]] = [
    # ── Discovery (public) ──────────────────────────────────────────────────
    {
        "name": "discover_products",
        "description": (
            "Search the AgentSetu product registry by constraints. "
            "Returns products matching all specified filters, ranked by the "
            "deterministic scoring model (0.45×price + 0.25×delivery + 0.20×rating + 0.10×policy_fit). "
            "No authentication required."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "category": {
                    "type": "string",
                    "description": "Product category filter (e.g. 'grocery', 'electronics', 'spices')",
                },
                "max_price": {
                    "type": "integer",
                    "description": "Maximum price in INR",
                },
                "delivery_sla": {
                    "type": "integer",
                    "description": "Maximum delivery days",
                },
                "keyword": {
                    "type": "string",
                    "description": "Keyword search across product names and descriptions",
                },
                "merchant_id": {
                    "type": "string",
                    "description": "Filter to a specific merchant",
                },
            },
            "required": [],
        },
    },
    {
        "name": "get_merchant_arm",
        "description": (
            "Retrieve the Agent-Readable Manifest (ARM) for a merchant. "
            "The ARM is a machine-readable JSON document containing products, policies, "
            "and capabilities — but never payment credentials. No authentication required."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "merchant_id": {
                    "type": "string",
                    "description": "The merchant's unique identifier",
                },
            },
            "required": ["merchant_id"],
        },
    },
    {
        "name": "list_merchants",
        "description": (
            "List all active merchants in the AgentSetu registry. "
            "Returns merchant name, category, product count, and policy summary. "
            "No authentication required."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    # ── Transaction (auth required) ─────────────────────────────────────────
    {
        "name": "process_purchase_intent",
        "description": (
            "Process a natural-language purchase intent through the full pipeline: "
            "parse → discover → rank → create transaction. Returns ranked candidates "
            "with deterministic scores and a transaction_id for subsequent steps. "
            "Authentication required."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "message": {
                    "type": "string",
                    "description": "Natural-language purchase intent (e.g. 'Buy organic honey under ₹500, deliver in 2 days')",
                    "maxLength": 2000,
                },
            },
            "required": ["message"],
        },
    },
    {
        "name": "select_product",
        "description": (
            "Select a product from the candidates returned by process_purchase_intent. "
            "Transitions the transaction from DRAFT to PENDING_APPROVAL. "
            "Authentication required."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "transaction_id": {
                    "type": "string",
                    "description": "Transaction ID from process_purchase_intent",
                },
                "product_id": {
                    "type": "string",
                    "description": "Selected product's ID",
                },
                "merchant_id": {
                    "type": "string",
                    "description": "Merchant ID of the selected product",
                },
            },
            "required": ["transaction_id", "product_id", "merchant_id"],
        },
    },
    {
        "name": "evaluate_policy",
        "description": (
            "Evaluate whether a purchase is allowed by the deterministic policy engine. "
            "Returns ALLOW, DENY, or NEEDS_APPROVAL with reason codes. "
            "The policy engine is a pure function — no LLM is involved. "
            "Authentication required."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "merchant_id": {
                    "type": "string",
                    "description": "Merchant ID",
                },
                "product_id": {
                    "type": "string",
                    "description": "Product ID",
                },
                "amount_inr": {
                    "type": "number",
                    "description": "Transaction amount in INR",
                },
            },
            "required": ["merchant_id", "product_id", "amount_inr"],
        },
    },
    {
        "name": "approve_transaction",
        "description": (
            "Record buyer approval for a transaction that requires consent "
            "(NEEDS_APPROVAL from policy engine). The approver identity is derived "
            "from the authenticated JWT — never from this request. "
            "Authentication required."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "transaction_id": {
                    "type": "string",
                    "description": "Transaction ID to approve",
                },
            },
            "required": ["transaction_id"],
        },
    },
    # ── Payment (auth required) ─────────────────────────────────────────────
    {
        "name": "create_payment_link",
        "description": (
            "Create a Razorpay Payment Link for an approved transaction. "
            "Requires: policy ALLOW + valid capability + authenticated buyer. "
            "The payment amount is verified server-side against the product database. "
            "No LLM is in this code path. Authentication required."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "transaction_id": {
                    "type": "string",
                    "description": "Transaction ID (must be in APPROVED state)",
                },
            },
            "required": ["transaction_id"],
        },
    },
    {
        "name": "verify_payment",
        "description": (
            "Check the payment status for a transaction. If the payment succeeded, "
            "transitions to RECEIPT_ISSUED. If failed, transitions to RECOVERY_PROPOSED. "
            "Unknown states are held — never silently retried. Authentication required."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "transaction_id": {
                    "type": "string",
                    "description": "Transaction ID to verify",
                },
            },
            "required": ["transaction_id"],
        },
    },
    {
        "name": "get_receipt",
        "description": (
            "Retrieve a machine-readable commerce receipt (v1.0) for a completed "
            "transaction. Includes buyer, merchant, line items, policy details, "
            "approval chain, payment evidence, and a SHA-256 integrity hash. "
            "Authentication required."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "transaction_id": {
                    "type": "string",
                    "description": "Transaction ID",
                },
            },
            "required": ["transaction_id"],
        },
    },
    # ── Audit (auth required) ───────────────────────────────────────────────
    {
        "name": "get_transaction",
        "description": (
            "Get full details of a specific transaction, including state, "
            "product, merchant, policy result, and payment status. "
            "Tenant-scoped: buyers see only their own transactions. "
            "Authentication required."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "transaction_id": {
                    "type": "string",
                    "description": "Transaction ID",
                },
            },
            "required": ["transaction_id"],
        },
    },
    {
        "name": "list_transactions",
        "description": (
            "List the authenticated user's transactions. "
            "Tenant-scoped: buyers see only their own; merchants see their merchant's. "
            "Authentication required."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "get_audit_timeline",
        "description": (
            "Retrieve the complete append-only audit trail for a transaction. "
            "Every material action — intent, discovery, policy decision, approval, "
            "payment, receipt — is recorded with actor, timestamp, and evidence. "
            "Authentication required."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "correlation_id": {
                    "type": "string",
                    "description": "Correlation ID (or transaction ID) to look up",
                },
            },
            "required": ["correlation_id"],
        },
    },
]

# Quick lookup by name
TOOLS_BY_NAME: dict[str, dict[str, Any]] = {t["name"]: t for t in TOOLS}

# Tools that do NOT require authentication
PUBLIC_TOOLS: set[str] = {"discover_products", "get_merchant_arm", "list_merchants"}
