from datetime import datetime
from uuid import uuid4
from typing import Optional, List
from pymongo.database import Database
from pymongo.errors import DuplicateKeyError
import logging

from app.models import PaymentCreate, PaymentResponse, RefundRequest, RefundResponse
from app.payment_gateway import PaymentGatewaySimulator

logger = logging.getLogger(__name__)

class PaymentService:
    def __init__(self, db: Database):
        self.db = db
        self.payments_collection = db.payments
        self.gateway = PaymentGatewaySimulator()

    def charge(self, payment_data: PaymentCreate) -> PaymentResponse:
        """
        Process a payment charge with idempotency support.

        Args:
            payment_data: Payment information

        Returns:
            PaymentResponse: Payment details with status

        Raises:
            ValueError: If payment already exists with different parameters
        """
        # Check for idempotency
        if payment_data.idempotency_key:
            existing_payment = self._check_idempotency(payment_data.idempotency_key)
            if existing_payment:
                logger.info(f"Returning existing payment for idempotency key: {payment_data.idempotency_key}")
                return PaymentResponse(**existing_payment)

        # Generate payment ID
        payment_id = f"PAY_{uuid4().hex[:12].upper()}"

        # Process payment through gateway
        success, status, reference = self.gateway.process_charge(
            amount=payment_data.amount,
            method=payment_data.method,
            order_id=payment_data.order_id
        )

        # Create payment record
        payment_doc = {
            "payment_id": payment_id,
            "order_id": payment_data.order_id,
            "amount": payment_data.amount,
            "method": payment_data.method,
            "status": status,
            "reference": reference,
            "created": datetime.utcnow(),
            "updated": datetime.utcnow()
        }

        # Add idempotency key if provided
        if payment_data.idempotency_key:
            payment_doc["idempotency_key"] = payment_data.idempotency_key

        try:
            self.payments_collection.insert_one(payment_doc)
            logger.info(f"Payment [payment_id] created with status {status}")
        except DuplicateKeyError:
            # Handle race condition for idempotency
            if payment_data.idempotency_key:
                existing_payment = self._check_idempotency(payment_data.idempotency_key)
                if existing_payment:
                    return PaymentResponse(**existing_payment)
            raise ValueError("Payment already exists")

        return PaymentResponse(**payment_doc)

    def refund(self, refund_request: RefundRequest) -> RefundResponse:
        """
        Process a refund for a successful payment.

        Args:
            refund_request: Refund information

        Returns:
            RefundResponse: Refund details

        Raises:
            ValueError: If payment not found or cannot be refunded
        """
        
        # Find the payment
        payment = self.payments_collection.find_one({"payment_id": refund_request.payment_id})

        if not payment:
            raise ValueError(f"Payment {refund_request.payment_id} not found")

        # Check if payment can be refunded
        if payment["status"] != "SUCCESS":
            raise ValueError(f"Cannot refund payment with status {payment['status']}")

        # Process refund through gateway
        success, message = self.gateway.process_refund(
            payment_reference=payment["reference"],
            amount=payment["amount"],
            payment_id=refund_request.payment_id
        )

        if not success:
            raise ValueError(message)

        # Update payment status
        self.payments_collection.update_one(
            {"payment_id": refund_request.payment_id},
            {
                "$set": {
                    "status": "REFUNDED",
                    "updated": datetime.utcnow(),
                    "refund_reason": refund_request.reason
                }
            }
        )

        logger.info(f"Payment {refund_request.payment_id} refunded successfully")

        return RefundResponse(
            payment_id=payment["payment_id"],
            order_id=payment["order_id"],
            refund_amount=payment["amount"],
            status="REFUNDED",
            refunded_at=datetime.utcnow(),
            message=message
        )

    def get_payment(self, payment_id: str) -> Optional[PaymentResponse]:
        """Get payment details by payment ID"""
        payment = self.payments_collection.find_one({"payment_id": payment_id})

        if not payment:
            return None

        # Remove MongoDB _id field
        payment.pop("_id", None)
        return PaymentResponse(**payment)

    def get_payments_by_order(self, order_id: str) -> List[PaymentResponse]:
        """Get all payments for a specific order"""
        payments = self.payments_collection.find({"order_id": order_id})

        result = []
        for payment in payments:
            payment.pop("_id", None)
            result.append(PaymentResponse(**payment))

        return result

    def get_payments_by_status(self, status: str, limit: int = 100) -> List[PaymentResponse]:
        """Get payments filtered by status"""
        payments = self.payments_collection.find({"status": status}).limit(limit)

        result = []
        for payment in payments:
            payment.pop("_id", None)
            result.append(PaymentResponse(**payment))

        return result

    def _check_idempotency(self, idempotency_key: str) -> Optional[dict]:
        """Check if payment with idempotency key already exists"""
        payment = self.payments_collection.find_one({"idempotency_key": idempotency_key})

        if payment:
            payment.pop("_id", None)
            return payment

        return None





