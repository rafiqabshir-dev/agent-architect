"""MongoDB connection management for the agent_architect database."""

import os
from motor.motor_asyncio import AsyncIOMotorClient

_client = None
_db = None


def get_db(db_name: str = "agent_architect"):
    """Get the MongoDB database instance. Creates connection on first call."""
    global _client, _db
    if _db is None:
        uri = os.environ.get("MONGODB_URI", "mongodb://localhost:27017")
        _client = AsyncIOMotorClient(uri)
        _db = _client[db_name]
    return _db


def set_db(db):
    """Override the database instance (used for testing)."""
    global _db
    _db = db


def get_collection(name: str):
    """Get a MongoDB collection by name."""
    return get_db()[name]
