from fastapi import FastAPI, HTTPException, Depends, Header, status
from fastapi.responses import JSONResponse
from typing import Optional, List
from datetime import datetime
import logging

from app.config import get_settings
from app.database import connect_to_mongo, close_mongo_connection, get_database
from app.models import (
    PaymentCreate,
    PaymentResponse,
    RefundRequest,
    RefundResponse,
    PaymentStatus,
    HealthResponse
)

from app.service import PaymentService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
settings = get_settings()
app = FastAPI(
    title="Payment Service API",
    description="Microservice for handling payment transactions, charges, and refunds.",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

@app.on_event("startup")
async def startup_event():
    """Connect to database on startup"""
    logger.info(f"Starting {settings.service_name}")
    connect_to_mongo()

@app.on_event("shutdown")
async def shutdown_event():
    """Close database connection on shutdown"""
    logger.info(f"Shutting down {settings.service_name}")
    close_mongo_connection()

def get_payment_service(db=Depends(get_database)) -> PaymentService:
    """Dependency to get PaymentService instance"""
    return PaymentService(db)

@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check(db=Depends(get_database)):
    """
    Health check endpoint for Kubernetes readiness/liveness probes
    """
    try:
        # Test database connection
        db.command('ping')
        db_status = "connected"
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        db_status = "disconnected"
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database Connection failed"
        )

    return HealthResponse(
        service=settings.service_name,
        status="ok" if db_status == "connected" else "error",
        database=db_status,
        timestamp=datetime.utc()
    )





@app.post(
    "/v1/payments/charge",
    response_model=PaymentResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Payments"]
)
async def charge_payment(
    payment: PaymentCreate,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    service: PaymentService = Depends(get_payment_service)
):
    """
    Process a payment charge.

    Supports idempotency using Idempotency-Key header to prevent duplicate charges.

    - **order_id**: Order ID this payment is for
    - **amount**: Payment amount (must be positive)
    - **method**: Payment method (CREDIT_CARD, DEBIT_CARD, UPI, NET_BANKING, WALLET)
    """
    try:
        # Use idempotency key from header if provided
        if idempotency_key:
            payment.idempotency_key = idempotency_key

        result = service.charge(payment)
        logger.info(f"Payment charged: {result.payment_id} for order {result.order_id}")

        return result

    except ValueError as e:
        logger.error(f"Payment charge failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Unexpected error during payment charge: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Payment processing failed"
        )

@app.post(
    "/v1/payments/refund",
    response_model=RefundResponse,
    tags=["Payments"]
)
async def refund_payment(
    request: RefundRequest,
    service: PaymentService = Depends(get_payment_service)
):
    """
    Process a payment refund.

    - **payment_id**: ID of the payment to refund
    - **amount**: Refund amount (must be <= original payment)
    - **reason**: Reason for refund
    """
    try:
        result = service.refund(request)
        logger.info(f"Refund processed: {result.refund_id} for payment {result.payment_id}")
        return result
    except ValueError as e:
        logger.error(f"Refund failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Unexpected error during refund: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Refund processing failed"
        )
    
@app.get(
    "/v1/payments/{payment_id}",
    response_model=PaymentResponse,
    tags=["Payments"]
)
async def get_payment(
    payment_id: str,
    service: PaymentService = Depends(get_payment_service)
):
    """
    Get payment details by payment ID.
    """
    payment = service.get_payment(payment_id)

    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Payment {payment_id} not found"
        )

    return payment

@app.get(
    "/v1/payments/order/{order_id}",
    response_model=List[PaymentResponse],
    tags=["Payments"]
)
async def get_payments_by_order(
    order_id: str,
    service: PaymentService = Depends(get_payment_service)
):
    """
    Get all payments for a specific order.
    """
    payments = service.get_payments_by_order(order_id)
    return payments


@app.get(
    "/v1/payments",
    response_model=List[PaymentResponse],
    tags=["Payments"]
)
async def get_payments(
    status_filter: Optional[str] = None,
    limit: int = 100,
    service: PaymentService = Depends(get_payment_service)
):
    """
    Get payments with optional status filter.

    - **status**: Filter by payment status (PENDING, SUCCESS, FAILED, REFUNDED)
    - **limit**: Maximum number of results (default: 100)
    """
    if status_filter:
        valid_statuses = ["PENDING", "SUCCESS", "FAILED", "REFUNDED"]
        if status_filter not in valid_statuses:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status. Must be one of: {', '.join(valid_statuses)}"
            )
        payments = service.get_payments_by_status(status_filter, limit)
    else:
        # Return recent payments if no filter
        payments = service.get_payments_by_status("SUCCESS", limit)

    return payments


@app.get("/", tags=["Root"])
async def root():
    """
    Root endpoint with service information.
    """
    return {
        "service": settings.service_name,
        "version": "1.0.0",
        "status": "running",
        "docs": "/api/docs"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=settings.service_port,
        reload=True,
        log_level=settings.log_level.lower()
    )