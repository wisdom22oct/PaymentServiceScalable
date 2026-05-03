# models.py
from pydantic import BaseModel, Field, field_validator
from typing import Optional, Literal
from datetime import datetime
from uuid import uuid4

class PaymentBase(BaseModel):
    order_id: str = Field(..., description="Order ID this payment is for")
    amount: float = Field(..., gt=0, description="Payment amount (must be positive)")
    method: Literal["CREDIT_CARD", "DEBIT_CARD", "UPI", "NET_BANKING", "WALLET"] = Field(
        ..., description="Payment method"
    )

    @field_validator("amount")
    @classmethod
    def validate_amount(cls, v):
        if v <= 0:
            raise ValueError("Amount must be positive")
        # Round to 2 decimal places
        return round(v, 2)

class PaymentCreate(PaymentBase):
    idempotency_key: Optional[str] = Field(
        None,
        description="Idempotency key to prevent duplicate charges"
    )

class PaymentResponse(PaymentBase):
    payment_id: str = Field(..., description="Unique payment ID")
    status: Literal["PENDING", "SUCCESS", "FAILED", "REFUNDED"] = Field(
        ..., description="Payment status"
    )
    reference: Optional[str] = Field(None, description="External payment reference")
    created: datetime = Field(..., description="Payment creation timestamp")
    updated: Optional[datetime] = Field(None, description="Last update timestamp")

    class Config:
        json_schema_extra = {
            "example": {
                "payment_id": "PAY_123456",
                "order_id": "ORD_789",
                "amount": 1575.00,
                "method": "CREDIT_CARD",
                "status": "SUCCESS",
                "reference": "TXN_ABC123",
                "created": "2026-05-02T10:30:00",
                "updated": "2026-05-02T10:30:05"
            }
        }

class RefundRequest(BaseModel):
    payment_id: str = Field(..., description="Payment ID to refund")
    reason: Optional[str] = Field(None, description="Refund reason")

class RefundResponse(BaseModel):
    payment_id: str
    order_id: str
    refund_amount: float
    status: str
    refunded_at: datetime
    message: str


class PaymentStatus(BaseModel):
    payment_id: str
    status: str
    amount: float
    order_id: str
    created: datetime

class HealthResponse(BaseModel):
    status: str
    service: str
    timestamp: datetime
    database: str
