import random
import logging
from typing import Tuple
from uuid import uuid4

logger = logging.getLogger(__name__)

class PaymentGatewaySimulator:
    """
    Simulates a payment gateway for processing charges and refunds.
    In production, this would integrate with actual payment providers like Stripe, PayPal, etc.
    """

    @staticmethod
    def process_charge(amount: float, method: str, order_id: str) -> Tuple[bool, str, str]:
        """
        Simulate payment processing.

        Returns:
            Tuple[bool, str, str]: (success, status, reference)
        """
        # Generate a transaction reference
        reference = f"TXN_{uuid4().hex[:12].upper()}"

        # Simulate payment processing with 95% success rate
        success_probability = 0.95
        is_successful = random.random() < success_probability

        if is_successful:
            logger.info(f"Payment successful for order {order_id}: {reference}")
            return True, "SUCCESS", reference
        else:
            logger.warning(f"Payment failed for order {order_id}")
            return False, "FAILED", reference
    
    @staticmethod
    def process_refund(payment_reference: str, amount: float, payment_id: str) -> Tuple[bool, str]:
        """
        Simulate refund processing.

        Returns:
        Tuple[bool, str]: (success, message)
        """
        # Generate refund reference
        refund_reference = f"REFUND_{uuid4().hex[:12].upper()}"

        # Simulate refund with 98% success rate
        success_probability = 0.98
        is_successful = random.random() < success_probability

        if is_successful:
            logger.info(f"Refund successful for payment {payment_id}: {refund_reference}")
            return True, f"Refund processed successfully. Reference: {refund_reference}"
        else:
            logger.error(f"Refund failed for payment {payment_id}")
            return False, "Refund processing failed. Please contact support."

    @staticmethod
    def validate_payment_method(method: str) -> bool:
        """Validate if payment method is supported"""
        supported_methods = ["CREDIT_CARD", "DEBIT_CARD", "UPI", "NET_BANKING", "WALLET"]
        return method in supported_methods

