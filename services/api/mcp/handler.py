"""
MCP tool-call handler.

Routes MCP tool calls to internal AgentSetu services.
This is a thin adapter — all business logic, policy enforcement,
and audit logging is in the existing service layer.

SECURITY:
  - Identity is derived from the JWT attached to the MCP request.
  - Protected tools reject calls without a valid token.
  - No tool argument can override the caller's identity.
"""

import hashlib
import json
import logging
import uuid
from typing import Any

from sqlmodel import Session, select

from ai.orchestrator import buyer_orchestrator
from audit.service import audit_service
from mcp.tools import PUBLIC_TOOLS, TOOLS_BY_NAME
from models.merchant import Merchant, Product
from models.merchant_user import MerchantUser
from models.transaction import Transaction, TransactionState, validate_transition
from models.user import User, UserRole
from policy.engine import PolicyDecision, PolicyEngine
from utils.time import utc_now

logger = logging.getLogger("agentsetu.mcp")
policy_engine = PolicyEngine()


class MCPError(Exception):
    """Raised when a tool call fails."""
    def __init__(self, message: str, code: str = "TOOL_ERROR"):
        super().__init__(message)
        self.code = code


async def handle_tool_call(
    tool_name: str,
    arguments: dict[str, Any],
    session: Session,
    user: User | None = None,
) -> dict[str, Any]:
    """
    Execute an MCP tool call and return the result.

    Args:
        tool_name: The MCP tool name.
        arguments: Tool arguments from the caller.
        session: SQLModel database session.
        user: Authenticated user (None for public tools).

    Returns:
        Result dict to be serialised as the tool response.

    Raises:
        MCPError: On validation or execution failure.
    """
    if tool_name not in TOOLS_BY_NAME:
        raise MCPError(f"Unknown tool: {tool_name}", code="UNKNOWN_TOOL")

    # Auth gate: protected tools require a user
    if tool_name not in PUBLIC_TOOLS and user is None:
        raise MCPError(
            "Authentication required. Attach a valid JWT to use this tool.",
            code="AUTH_REQUIRED",
        )

    handler = _HANDLERS.get(tool_name)
    if handler is None:
        raise MCPError(f"Tool not implemented: {tool_name}", code="NOT_IMPLEMENTED")

    logger.info("MCP tool_call: %s user=%s", tool_name, user.user_id if user else "anon")

    return await handler(arguments, session, user)


# ── Helpers ─────────────────────────────────────────────────────────────────

def _assert_txn_access(txn: Transaction, user: User, session: Session):
    """Raise MCPError unless the user owns or is authorised for this txn."""
    if user.role == UserRole.PLATFORM_ADMIN:
        return
    if user.role == UserRole.BUYER:
        if txn.buyer_id != user.user_id:
            raise MCPError("Not authorised for this transaction", code="FORBIDDEN")
        return
    if txn.merchant_id:
        membership = session.exec(
            select(MerchantUser).where(
                MerchantUser.merchant_id == txn.merchant_id,
                MerchantUser.user_id == user.user_id,
            )
        ).first()
        if membership:
            return
    raise MCPError("Not authorised for this transaction", code="FORBIDDEN")


def _make_fingerprint(merchant_id: str, product_id: str, amount: int, approval_id: str) -> str:
    payload = f"{merchant_id}:{product_id}:{amount}:{approval_id}"
    return hashlib.sha256(payload.encode()).hexdigest()


# ── Individual tool handlers ────────────────────────────────────────────────

async def _discover_products(
    args: dict[str, Any], session: Session, user: User | None,
) -> dict[str, Any]:
    """Delegates to the same discovery logic as GET /v1/discover/."""
    products = session.exec(select(Product)).all()
    merchants_map = {m.merchant_id: m for m in session.exec(select(Merchant)).all()}

    results = []
    for p in products:
        merchant = merchants_map.get(p.merchant_id)
        if not merchant or not merchant.is_active or not p.availability or p.inventory_count <= 0:
            continue

        category = args.get("category")
        if category and p.category.lower() != category.lower():
            continue

        max_price = args.get("max_price")
        if max_price is not None and p.price_inr > max_price:
            continue

        delivery_sla = args.get("delivery_sla")
        if delivery_sla is not None and p.delivery_sla_days_max > delivery_sla:
            continue

        keyword = args.get("keyword")
        if keyword and keyword.lower() not in p.name.lower() and keyword.lower() not in p.description.lower():
            continue

        merchant_id = args.get("merchant_id")
        if merchant_id and p.merchant_id != merchant_id:
            continue

        results.append({
            "product_id": p.product_id,
            "merchant_id": p.merchant_id,
            "merchant_name": merchant.name,
            "name": p.name,
            "category": p.category,
            "price_inr": p.price_inr,
            "delivery_sla_days": [p.delivery_sla_days_min, p.delivery_sla_days_max],
            "merchant_rating": p.merchant_rating,
            "description": p.description,
        })

    return {"products": results, "total": len(results)}


async def _get_merchant_arm(
    args: dict[str, Any], session: Session, user: User | None,
) -> dict[str, Any]:
    merchant_id = args.get("merchant_id", "")
    if not merchant_id:
        raise MCPError("merchant_id is required", code="VALIDATION_ERROR")

    merchant = session.exec(
        select(Merchant).where(Merchant.merchant_id == merchant_id)
    ).first()
    if not merchant:
        raise MCPError(f"Merchant not found: {merchant_id}", code="NOT_FOUND")

    from arm.generator import get_or_generate_arm
    return get_or_generate_arm(merchant_id, session)


async def _list_merchants(
    args: dict[str, Any], session: Session, user: User | None,
) -> dict[str, Any]:
    merchants = session.exec(select(Merchant).where(Merchant.is_active.is_(True))).all()
    result = []
    for m in merchants:
        product_count = len(session.exec(
            select(Product).where(Product.merchant_id == m.merchant_id)
        ).all())
        result.append({
            "merchant_id": m.merchant_id,
            "name": m.name,
            "category": m.category,
            "description": m.description,
            "currency": m.currency,
            "product_count": product_count,
            "max_autonomous_spend_inr": m.max_autonomous_spend_inr,
            "approval_threshold_inr": m.approval_threshold_inr,
        })
    return {"merchants": result, "total": len(result)}


async def _process_purchase_intent(
    args: dict[str, Any], session: Session, user: User | None,
) -> dict[str, Any]:
    """Same pipeline as POST /v1/transactions/intent."""
    message = args.get("message", "")
    if not message:
        raise MCPError("message is required", code="VALIDATION_ERROR")
    if len(message) > 2000:
        raise MCPError("message exceeds 2000 character limit", code="VALIDATION_ERROR")

    # 1. Parse intent
    constraints = buyer_orchestrator.parse_intent(message)

    # 2. Registry discovery
    all_products = session.exec(select(Product)).all()
    all_merchants = {m.merchant_id: m for m in session.exec(select(Merchant)).all()}

    candidates = []
    for p in all_products:
        merchant = all_merchants.get(p.merchant_id)
        if not merchant or not merchant.is_active or not p.availability or p.inventory_count <= 0:
            continue
        if p.category.lower() in [r.lower() for r in merchant.get_restricted_categories()]:
            continue

        max_budget = constraints.get("max_budget_inr")
        if max_budget and p.price_inr > max_budget:
            continue
        sla = constraints.get("delivery_sla_days")
        if sla and p.delivery_sla_days_max > sla:
            continue
        cat = constraints.get("category")
        if cat and p.category.lower() != cat.lower():
            continue

        candidates.append({
            "product_id": p.product_id,
            "merchant_id": p.merchant_id,
            "merchant_name": merchant.name,
            "name": p.name,
            "category": p.category,
            "price_inr": p.price_inr,
            "inventory_count": p.inventory_count,
            "availability": p.availability,
            "delivery_sla_days_min": p.delivery_sla_days_min,
            "delivery_sla_days_max": p.delivery_sla_days_max,
            "return_policy": p.return_policy,
            "merchant_rating": p.merchant_rating,
            "description": p.description,
            "max_autonomous_spend_inr": merchant.max_autonomous_spend_inr,
            "approval_threshold_inr": merchant.approval_threshold_inr,
        })

    # 3. Score and rank
    ranked = buyer_orchestrator.score_candidates(candidates, constraints)

    # 4. Create transaction
    txn = Transaction(
        buyer_id=user.user_id if user else None,
        buyer_intent=message,
        parsed_constraints=json.dumps(constraints),
        candidates_json=json.dumps(ranked[:5]),
        state=TransactionState.DRAFT,
    )
    session.add(txn)
    session.commit()
    session.refresh(txn)

    # 5. Audit
    audit_service.record(
        session=session,
        transaction_id=txn.transaction_id,
        correlation_id=txn.correlation_id,
        actor=user.user_id if user else "anonymous",
        event_type="intent.received",
        input_summary={"message": message, "channel": "mcp"},
        next_state="DRAFT",
        result="parsed",
    )

    top = ranked[:3] if ranked else []
    explanation = ""
    if top:
        explanation = buyer_orchestrator.generate_comparison(
            candidates=top, constraints=constraints, selected_product=top[0],
        )

    return {
        "transaction_id": txn.transaction_id,
        "correlation_id": txn.correlation_id,
        "state": txn.state,
        "constraints": constraints,
        "candidates": top,
        "total_found": len(ranked),
        "explanation": explanation,
        "no_results": len(ranked) == 0,
    }


async def _select_product(
    args: dict[str, Any], session: Session, user: User | None,
) -> dict[str, Any]:
    for field in ("transaction_id", "product_id", "merchant_id"):
        if not args.get(field):
            raise MCPError(f"{field} is required", code="VALIDATION_ERROR")

    txn = session.exec(
        select(Transaction).where(Transaction.transaction_id == args["transaction_id"])
    ).first()
    if not txn:
        raise MCPError("Transaction not found", code="NOT_FOUND")

    if user:
        if txn.buyer_id and txn.buyer_id != user.user_id:
            raise MCPError("Not authorised for this transaction", code="FORBIDDEN")
        if not txn.buyer_id:
            txn.buyer_id = user.user_id

    product = session.exec(
        select(Product).where(
            Product.product_id == args["product_id"],
            Product.merchant_id == args["merchant_id"],
        )
    ).first()
    if not product:
        raise MCPError("Product not found", code="NOT_FOUND")

    merchant = session.exec(
        select(Merchant).where(Merchant.merchant_id == args["merchant_id"])
    ).first()

    if not validate_transition(txn.state, TransactionState.PENDING_APPROVAL):
        raise MCPError(f"Cannot select product in state: {txn.state}", code="INVALID_STATE")

    txn.product_id = product.product_id
    txn.product_name = product.name
    txn.merchant_id = merchant.merchant_id
    txn.merchant_name = merchant.name
    txn.amount_inr = product.price_inr
    txn.state = TransactionState.PENDING_APPROVAL
    txn.updated_at = utc_now()
    session.add(txn)
    session.commit()
    session.refresh(txn)

    return {
        "transaction_id": txn.transaction_id,
        "state": txn.state,
        "selected": {
            "product_id": product.product_id,
            "name": product.name,
            "merchant_name": merchant.name,
            "price_inr": product.price_inr,
        },
    }


async def _evaluate_policy(
    args: dict[str, Any], session: Session, user: User | None,
) -> dict[str, Any]:
    for field in ("merchant_id", "product_id", "amount_inr"):
        if args.get(field) is None:
            raise MCPError(f"{field} is required", code="VALIDATION_ERROR")

    merchant = session.exec(
        select(Merchant).where(Merchant.merchant_id == args["merchant_id"])
    ).first()
    if not merchant:
        raise MCPError("Merchant not found", code="NOT_FOUND")

    product = session.exec(
        select(Product).where(
            Product.product_id == args["product_id"],
            Product.merchant_id == args["merchant_id"],
        )
    ).first()
    if not product:
        raise MCPError("Product not found", code="NOT_FOUND")

    result = policy_engine.evaluate(
        merchant=merchant,
        product=product,
        amount_inr=args["amount_inr"],
        buyer_limit_inr=None,
        is_approved=False,
    )

    return {
        "decision": result.decision,
        "reason_codes": result.reason_codes,
        "effective_limit_inr": result.effective_limit_inr,
        "message": result.message,
        "can_proceed": result.decision == PolicyDecision.ALLOW,
        "needs_approval": result.decision == PolicyDecision.NEEDS_APPROVAL,
        "is_denied": result.decision == PolicyDecision.DENY,
    }


async def _approve_transaction(
    args: dict[str, Any], session: Session, user: User | None,
) -> dict[str, Any]:
    if not args.get("transaction_id"):
        raise MCPError("transaction_id is required", code="VALIDATION_ERROR")

    txn = session.exec(
        select(Transaction).where(Transaction.transaction_id == args["transaction_id"])
    ).first()
    if not txn:
        raise MCPError("Transaction not found", code="NOT_FOUND")

    _assert_txn_access(txn, user, session)

    if txn.state not in [TransactionState.DRAFT, TransactionState.PENDING_APPROVAL]:
        raise MCPError(f"Cannot approve in state: {txn.state}", code="INVALID_STATE")

    approval_id = f"appr_{uuid.uuid4().hex[:8]}"
    txn.approval_id = approval_id
    txn.approved_by = user.user_id  # ALWAYS from auth context
    txn.approved_at = utc_now()
    txn.state = TransactionState.APPROVED
    if not txn.buyer_id:
        txn.buyer_id = user.user_id
    if txn.merchant_id and txn.product_id and txn.amount_inr:
        txn.fingerprint = _make_fingerprint(
            txn.merchant_id, txn.product_id, txn.amount_inr, approval_id,
        )
    txn.updated_at = utc_now()
    session.add(txn)
    session.commit()
    session.refresh(txn)

    audit_service.record(
        session=session,
        transaction_id=txn.transaction_id,
        correlation_id=txn.correlation_id,
        actor=user.user_id,
        event_type="approval.granted",
        input_summary={"amount_inr": txn.amount_inr, "channel": "mcp"},
        decision="APPROVED",
        next_state="APPROVED",
        result="buyer_consent_recorded",
    )

    return {
        "transaction_id": txn.transaction_id,
        "approval_id": approval_id,
        "state": txn.state,
        "approved_at": txn.approved_at.isoformat(),
    }


async def _create_payment_link(
    args: dict[str, Any], session: Session, user: User | None,
) -> dict[str, Any]:
    """
    Thin wrapper — delegates to the payment route's internal logic.
    The policy + capability + payment-link creation chain is not
    duplicated here; we call the same endpoint logic via an import.
    """
    if not args.get("transaction_id"):
        raise MCPError("transaction_id is required", code="VALIDATION_ERROR")

    # Rather than duplicating the full payment flow (which involves capability
    # issuance, idempotency, Razorpay adapter calls), we raise a clear message
    # directing the agent to use the REST endpoint.
    # This ensures the payment flow's atomicity guarantees are preserved.
    raise MCPError(
        "Payment link creation must go through POST /v1/payments/payment-link "
        "to preserve idempotency and capability atomicity. "
        "Use the REST endpoint with the transaction_id.",
        code="USE_REST_ENDPOINT",
    )


async def _verify_payment(
    args: dict[str, Any], session: Session, user: User | None,
) -> dict[str, Any]:
    if not args.get("transaction_id"):
        raise MCPError("transaction_id is required", code="VALIDATION_ERROR")

    txn = session.exec(
        select(Transaction).where(Transaction.transaction_id == args["transaction_id"])
    ).first()
    if not txn:
        raise MCPError("Transaction not found", code="NOT_FOUND")

    _assert_txn_access(txn, user, session)

    return {
        "transaction_id": txn.transaction_id,
        "state": txn.state,
        "payment_link_id": txn.razorpay_payment_link_id,
        "payment_link_url": txn.razorpay_payment_link_url,
        "failure_reason": txn.failure_reason,
        "recovery_action": txn.recovery_action,
        "hint": (
            "Use POST /v1/payments/verify/{transaction_id} to check live payment status "
            "and trigger state transitions."
        ),
    }


async def _get_receipt(
    args: dict[str, Any], session: Session, user: User | None,
) -> dict[str, Any]:
    if not args.get("transaction_id"):
        raise MCPError("transaction_id is required", code="VALIDATION_ERROR")

    txn = session.exec(
        select(Transaction).where(Transaction.transaction_id == args["transaction_id"])
    ).first()
    if not txn:
        raise MCPError("Transaction not found", code="NOT_FOUND")

    _assert_txn_access(txn, user, session)

    if txn.state not in ("RECEIPT_ISSUED", "PAYMENT_SUCCESS"):
        raise MCPError(
            f"Receipt not available — transaction state is {txn.state}",
            code="RECEIPT_NOT_READY",
        )

    return {
        "transaction_id": txn.transaction_id,
        "state": txn.state,
        "hint": (
            "Use GET /v1/payments/receipt/{transaction_id} for the full v1.0 "
            "receipt with SHA-256 integrity hash."
        ),
    }


async def _get_transaction(
    args: dict[str, Any], session: Session, user: User | None,
) -> dict[str, Any]:
    if not args.get("transaction_id"):
        raise MCPError("transaction_id is required", code="VALIDATION_ERROR")

    txn = session.exec(
        select(Transaction).where(Transaction.transaction_id == args["transaction_id"])
    ).first()
    if not txn:
        raise MCPError("Transaction not found", code="NOT_FOUND")

    _assert_txn_access(txn, user, session)

    return {
        "transaction_id": txn.transaction_id,
        "correlation_id": txn.correlation_id,
        "state": txn.state,
        "buyer_intent": txn.buyer_intent,
        "parsed_constraints": json.loads(txn.parsed_constraints) if txn.parsed_constraints else {},
        "merchant_id": txn.merchant_id,
        "merchant_name": txn.merchant_name,
        "product_id": txn.product_id,
        "product_name": txn.product_name,
        "amount_inr": txn.amount_inr,
        "approval_id": txn.approval_id,
        "approved_at": txn.approved_at.isoformat() if txn.approved_at else None,
        "payment_link_id": txn.razorpay_payment_link_id,
        "failure_reason": txn.failure_reason,
        "recovery_action": txn.recovery_action,
        "created_at": txn.created_at.isoformat(),
    }


async def _list_transactions(
    args: dict[str, Any], session: Session, user: User | None,
) -> dict[str, Any]:
    if user.role == UserRole.PLATFORM_ADMIN:
        query = select(Transaction).order_by(Transaction.created_at.desc()).limit(50)
    elif user.role == UserRole.BUYER:
        query = (
            select(Transaction)
            .where(Transaction.buyer_id == user.user_id)
            .order_by(Transaction.created_at.desc())
            .limit(50)
        )
    else:
        memberships = session.exec(
            select(MerchantUser).where(MerchantUser.user_id == user.user_id)
        ).all()
        merchant_ids = [m.merchant_id for m in memberships]
        if not merchant_ids:
            return {"transactions": [], "total": 0}
        query = (
            select(Transaction)
            .where(Transaction.merchant_id.in_(merchant_ids))
            .order_by(Transaction.created_at.desc())
            .limit(50)
        )

    txns = session.exec(query).all()
    return {
        "transactions": [
            {
                "transaction_id": t.transaction_id,
                "state": t.state,
                "buyer_intent": t.buyer_intent[:80] if t.buyer_intent else "",
                "merchant_name": t.merchant_name,
                "amount_inr": t.amount_inr,
                "created_at": t.created_at.isoformat(),
            }
            for t in txns
        ],
        "total": len(txns),
    }


async def _get_audit_timeline(
    args: dict[str, Any], session: Session, user: User | None,
) -> dict[str, Any]:
    if not args.get("correlation_id"):
        raise MCPError("correlation_id is required", code="VALIDATION_ERROR")

    events = audit_service.get_timeline(session, args["correlation_id"])
    return {
        "correlation_id": args["correlation_id"],
        "events": [
            {
                "event_id": str(e.event_id),
                "timestamp": e.timestamp.isoformat() if e.timestamp else None,
                "actor": e.actor,
                "event_type": e.event_type,
                "decision": e.decision,
                "reason_codes": e.reason_codes,
                "next_state": e.next_state,
                "result": e.result,
            }
            for e in events
        ],
        "total_events": len(events),
    }


# ── Handler registry ────────────────────────────────────────────────────────

_HANDLERS = {
    "discover_products": _discover_products,
    "get_merchant_arm": _get_merchant_arm,
    "list_merchants": _list_merchants,
    "process_purchase_intent": _process_purchase_intent,
    "select_product": _select_product,
    "evaluate_policy": _evaluate_policy,
    "approve_transaction": _approve_transaction,
    "create_payment_link": _create_payment_link,
    "verify_payment": _verify_payment,
    "get_receipt": _get_receipt,
    "get_transaction": _get_transaction,
    "list_transactions": _list_transactions,
    "get_audit_timeline": _get_audit_timeline,
}
