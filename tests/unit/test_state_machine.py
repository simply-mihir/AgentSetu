"""
Phase 5 — Transaction state machine tests.
Verify that only allowed transitions are permitted.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../services/api"))

import pytest
from models.transaction import TransactionState, validate_transition, ALLOWED_TRANSITIONS


class TestAllowedTransitions:
    """Verify the explicit transition map."""

    def test_draft_to_pending_approval(self):
        assert validate_transition(TransactionState.DRAFT, TransactionState.PENDING_APPROVAL)

    def test_draft_to_approved(self):
        assert validate_transition(TransactionState.DRAFT, TransactionState.APPROVED)

    def test_draft_to_cancelled(self):
        assert validate_transition(TransactionState.DRAFT, TransactionState.CANCELLED)

    def test_pending_to_approved(self):
        assert validate_transition(TransactionState.PENDING_APPROVAL, TransactionState.APPROVED)

    def test_approved_to_payment_link(self):
        assert validate_transition(TransactionState.APPROVED, TransactionState.PAYMENT_LINK_CREATED)

    def test_payment_link_to_success(self):
        assert validate_transition(TransactionState.PAYMENT_LINK_CREATED, TransactionState.PAYMENT_SUCCESS)

    def test_payment_link_to_failed(self):
        assert validate_transition(TransactionState.PAYMENT_LINK_CREATED, TransactionState.PAYMENT_FAILED)

    def test_payment_link_to_unknown(self):
        assert validate_transition(TransactionState.PAYMENT_LINK_CREATED, TransactionState.PAYMENT_UNKNOWN)

    def test_payment_success_to_receipt(self):
        assert validate_transition(TransactionState.PAYMENT_SUCCESS, TransactionState.RECEIPT_ISSUED)

    def test_payment_failed_to_recovery(self):
        assert validate_transition(TransactionState.PAYMENT_FAILED, TransactionState.RECOVERY_PROPOSED)

    def test_approved_to_draft_on_price_change(self):
        assert validate_transition(TransactionState.APPROVED, TransactionState.DRAFT)


class TestDisallowedTransitions:
    """Verify illegal transitions are rejected."""

    def test_receipt_is_terminal(self):
        for target in TransactionState:
            assert not validate_transition(TransactionState.RECEIPT_ISSUED, target)

    def test_cancelled_is_terminal(self):
        for target in TransactionState:
            assert not validate_transition(TransactionState.CANCELLED, target)

    def test_recovery_is_terminal(self):
        for target in TransactionState:
            assert not validate_transition(TransactionState.RECOVERY_PROPOSED, target)

    def test_draft_cannot_jump_to_payment(self):
        assert not validate_transition(TransactionState.DRAFT, TransactionState.PAYMENT_LINK_CREATED)

    def test_draft_cannot_jump_to_receipt(self):
        assert not validate_transition(TransactionState.DRAFT, TransactionState.RECEIPT_ISSUED)

    def test_pending_cannot_go_back_to_draft(self):
        assert not validate_transition(TransactionState.PENDING_APPROVAL, TransactionState.DRAFT)

    def test_payment_success_cannot_go_to_failed(self):
        assert not validate_transition(TransactionState.PAYMENT_SUCCESS, TransactionState.PAYMENT_FAILED)


class TestAllStatesHaveTransitionEntry:
    """Every state in the enum should have an entry in ALLOWED_TRANSITIONS."""

    def test_completeness(self):
        for state in TransactionState:
            assert state in ALLOWED_TRANSITIONS, f"{state} missing from ALLOWED_TRANSITIONS"
