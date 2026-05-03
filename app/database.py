from pymongo import MongoClient, ASCENDING
from pymongo.errors import ConnectionFailure
from app.config import get_settings
import logging

logger = logging.getLogger(__name__)

class Database:
    client: MongoClient = None
    db = None

db = Database()

def connect_to_mongo():
    """Connect to MongoDB and create indexes"""
    settings = get_settings()
    try:
        db.client = MongoClient(settings.mongodb_url)
        db.db = db.client[settings.database_name]

        # Test connection
        db.client.admin.command('ping')
        logger.info(f"Connected to MongoDB: {settings.database_name}")

        # Create indexes
        create_indexes()

    except ConnectionFailure as e:
        logger.error(f"Failed to connect to MongoDB: {e}")
        raise



def close_mongo_connection():
    """Close MongoDB connection"""
    if db.client:
        db.client.close()
        logger.info("Closed MongoDB connection")

def create_indexes():
    """Create database indexes for performance"""
    try:
        # Payment collection indexes
        payments_collection = db.db.payments

        # Index on payment_id for fast lookups
        payments_collection.create_index([("payment_id", ASCENDING)], unique=True)

        # Index on order_id for order-based queries
        payments_collection.create_index([("order_id", ASCENDING)])

        # Index on idempotency_key for idempotent operations
        payments_collection.create_index([("idempotency_key", ASCENDING)], unique=True, sparse=True)

        # Index on status for filtering
        payments_collection.create_index([("status", ASCENDING)])

        # Index on created timestamp for sorting
        payments_collection.create_index([("created", ASCENDING)])

        # Compound index for order_id and status
        payments_collection.create_index([("order_id", ASCENDING), ("status", ASCENDING)])

        logger.info("Database indexes created successfully")
    except Exception as e:
        logger.error(f"Failed to create indexes: {e}")
        raise



def get_database():
    """Dependency to get database instance"""
    return db.db