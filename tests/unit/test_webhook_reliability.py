"""
Phase 7 — Webhook reliability tests.
Verify duplicate handling, state-machine validation, and signature enforcement.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../services/api"))

import pytest
import json
import hashlib
import hmac
from models.webhook import WebhookEvent
from models.transaction import Transaction, TransactionState


def _make_sig(body: bytes, secret: str = "test_webhook_secret") -> str:
    return hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def _make_payload(event_id: str, reference_id: str, status: str = "paid") -> dict:
    return {
        "id": event_id,
        "event": "payment_link.paid",
        "payload": {
            "payment_link": {
                "entity": {
                    "id": "plink_test",
                    "reference_id": reference_id,
                    "status": status,
                }
            }
        }
    }


class TestWebhookDuplicateHandling:
    """Phase 7: Both RECEIVED and PROCESSED events are caught as duplicates."""

    def test_processed_event_is_duplicate(self, session, client):
        """An event with PROCESSED status should be skipped."""
        wh = WebhookEvent(
            provider="razorpay",
            provider_event_id="evt_already_processed",
            event_type="payment_link.paid",
            payload_hash="abc",
            signature_valid=True,
            processing_status="PROCESSED",
        )
        session.add(wh)
        session.commit()

        payload = _make_payload("evt_already_processed", "txn_xyz")
        body = json.dumps(payload).encode()
        sig = _make_sig(body)

        resp = client.post("/v1/webhooks/razorpay",
            content=body,
            headers={"X-Razorpay-Signature": sig, "Content-Type": "application/json"},
        )
        assert resp.status_code == 200
        assert resp.json()["duplicate"] is True

    def test_received_inflight_event_is_duplicate(self, session, client):
        """Phase 7 fix: An event with RECEIVED (in-flight) status should also be skipped."""
        wh = WebhookEvent(
            provider="razorpay",
            provider_event_id="evt_inflight",
            event_type="payment_link.paid",
            payload_hash="def",
            signature_valid=True,
            processing_status="RECEIVED",
        )
        session.add(wh)
        session.commit()

        payload = _make_payload("evt_inflight", "txn_xyz")
        body = json.dumps(payload).encode()
        sig = _make_sig(body)

        resp = client.post("/v1/webhooks/razorpay",
            content=body,
            headers={"X-Razorpay-Signature": sig, "Content-Type": "application/json"},
        )
        assert resp.status_code == 200
        assert resp.json()["duplicate"] is True

    def test_failed_event_can_be_reprocessed(self, session, client):
        """A FAILED event should NOT be treated as duplicate — allow retry."""
        wh = WebhookEvent(
            provider="razorpay",
            provider_event_id="evt_failed_retry",
            event_type="payment_link.paid",
            payload_hash="ghi",
            signature_valid=True,
            processing_status="FAILED",
        )
        session.add(wh)
        session.commit()

        payload = _make_payload("evt_failed_retry", "txn_nonexistent")
        body = json.dumps(payload).encode()
        sig = _make_sig(body)

        resp = client.post("/v1/webhooks/razorpay",
            content=body,
            headers={"X-Razorpay-Signature": sig, "Content-Type": "application/json"},
        )
        assert resp.status_code == 200
        # Should NOT be duplicate — it was FAILED, not RECEIVED/PROCESSED
        assert resp.json().get("duplicate") is not True


class TestWebhookSignatureValidation:
    """Signature must be verified BEFORE any state mutation."""

    def test_invalid_signature_rejected(self, client):
        payload = _make_payload("evt_invalid_sig", "txn_abc")
        body = json.dumps(payload).encode()

        resp = client.post("/v1/webhooks/razorpay",
            content=body,
            headers={"X-Razorpay-Signature": "bad_signature", "Content-Type": "application/json"},
        )
        assert resp.status_code == 400

    def test_missing_signature_rejected(self, client):
        payload = _make_payload("evt_no_sig", "txn_abc")
        body = json.dumps(payload).encode()

        resp = client.post("/v1/webhooks/razorpay",
            content=body,
            headers={"Content-Type": "application/json"},
        )
        assert resp.status_code == 400


class TestWebhookStateTransition:
    """Phase 7: Webhook must validate state transitions."""

    def test_webhook_updates_valid_transition(self, session, client):
        """Webhook on a PAYMENT_LINK_CREATED txn succeeds."""
        txn = Transaction(
            transaction_id="txn_wh_valid",
            buyer_intent="test",
            state=TransactionState.PAYMENT_LINK_CREATED,
            razorpay_payment_link_id="plink_test",
        )
        session.add(txn)
        session.commit()

        payload = _make_payload("evt_valid_transition", "txn_wh_valid", "paid")
        body = json.dumps(payload).encode()
        sig = _make_sig(body)

        resp = client.post("/v1/webhooks/razorpay",
            content=body,
            headers={"X-Razorpay-Signature": sig, "Content-Type": "application/json"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["matched"] is True
        # Should reach RECEIPT_ISSUED (PAYMENT_SUCCESS → auto-receipt)
        assert data["new_state"] in ["RECEIPT_ISSUED", "PAYMENT_SUCCESS"]

    def test_webhook_skips_illegal_transition(self, session, client):
        """Webhook on a terminal-state txn should be skipped as illegal."""
        txn = Transaction(
            transaction_id="txn_wh_terminal",
            buyer_intent="test",
            state=TransactionState.RECEIPT_ISSUED,
            razorpay_payment_link_id="plink_terminal",
        )
        session.add(txn)
        session.commit()

        payload = _make_payload("evt_illegal_transition", "txn_wh_terminal", "paid")
        body = json.dumps(payload).encode()
        sig = _make_sig(body)

        resp = client.post("/v1/webhooks/razorpay",
            content=body,
            headers={"X-Razorpay-Signature": sig, "Content-Type": "application/json"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("skipped") is True
        assert data.get("reason") == "illegal_transition"
