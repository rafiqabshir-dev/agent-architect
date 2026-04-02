"""MongoDB CRUD operations for the provider_prospects collection."""

import logging
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)

# Default collection name; tests override with provider_prospects_test
COLLECTION_NAME = "provider_prospects"

_collection = None


def _get_collection(db=None):
    """Get the provider_prospects collection."""
    global _collection
    if db is not None:
        return db[COLLECTION_NAME]
    if _collection is None:
        from src.retrieval_graph.db import get_collection
        _collection = get_collection(COLLECTION_NAME)
    return _collection


def set_collection(col):
    """Override the collection (for testing)."""
    global _collection
    _collection = col


async def upsert_provider(client_id: str, provider_data: dict, db=None) -> str:
    """Insert or update provider prospect. Upsert on client_id + npi. Return document ID."""
    try:
        col = _get_collection(db)
        now = datetime.now(timezone.utc)
        provider_data["client_id"] = client_id
        provider_data["updated_at"] = now

        result = await col.update_one(
            {"client_id": client_id, "npi": provider_data["npi"]},
            {
                "$set": provider_data,
                "$setOnInsert": {
                    "created_at": now,
                    "status": provider_data.get("status", "new"),
                    "outreach_history": [],
                    "engagement_signals": [],
                    "is_existing_partner": provider_data.get("is_existing_partner", False),
                    "contact_email": provider_data.get("contact_email"),
                    "contact_fax": provider_data.get("contact_fax"),
                    "preferred_channel": provider_data.get("preferred_channel", "email"),
                    "cms_volume": provider_data.get("cms_volume"),
                    "distance_miles": provider_data.get("distance_miles"),
                    "notes": provider_data.get("notes", ""),
                },
            },
            upsert=True,
        )
        if result.upserted_id:
            return str(result.upserted_id)
        # Return existing doc id
        doc = await col.find_one({"client_id": client_id, "npi": provider_data["npi"]})
        return str(doc["_id"]) if doc else ""
    except Exception as e:
        logger.error("upsert_provider failed: %s", e)
        raise


async def get_prospects_for_client(
    client_id: str,
    status: str | None = None,
    exclude_existing_partners: bool = True,
    limit: int = 50,
    db=None,
) -> list[dict]:
    """Get provider prospects for a client, optionally filtered by status."""
    try:
        col = _get_collection(db)
        query: dict = {"client_id": client_id}
        if status:
            query["status"] = status
        if exclude_existing_partners:
            query["is_existing_partner"] = {"$ne": True}

        cursor = col.find(query).limit(limit)
        return await cursor.to_list(length=limit)
    except Exception as e:
        logger.error("get_prospects_for_client failed: %s", e)
        return []


async def update_provider_status(client_id: str, npi: str, new_status: str, db=None) -> bool:
    """Update a provider's outreach status."""
    try:
        col = _get_collection(db)
        result = await col.update_one(
            {"client_id": client_id, "npi": npi},
            {"$set": {"status": new_status, "updated_at": datetime.now(timezone.utc)}},
        )
        return result.modified_count > 0
    except Exception as e:
        logger.error("update_provider_status failed: %s", e)
        return False


async def add_engagement_signal(client_id: str, npi: str, signal: dict, db=None) -> bool:
    """Append an engagement signal to a provider's record."""
    try:
        col = _get_collection(db)
        signal.setdefault("date", datetime.now(timezone.utc))
        result = await col.update_one(
            {"client_id": client_id, "npi": npi},
            {
                "$push": {"engagement_signals": signal},
                "$set": {"updated_at": datetime.now(timezone.utc)},
            },
        )
        return result.modified_count > 0
    except Exception as e:
        logger.error("add_engagement_signal failed: %s", e)
        return False


async def add_outreach_record(client_id: str, npi: str, record: dict, db=None) -> bool:
    """Append an outreach record to a provider's history."""
    try:
        col = _get_collection(db)
        record.setdefault("date", datetime.now(timezone.utc))
        result = await col.update_one(
            {"client_id": client_id, "npi": npi},
            {
                "$push": {"outreach_history": record},
                "$set": {"updated_at": datetime.now(timezone.utc)},
            },
        )
        return result.modified_count > 0
    except Exception as e:
        logger.error("add_outreach_record failed: %s", e)
        return False


async def get_hot_leads(client_id: str, days: int = 7, min_signals: int = 2, db=None) -> list[dict]:
    """Get providers with multiple engagement signals in the last N days."""
    try:
        col = _get_collection(db)
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)

        cursor = col.find({
            "client_id": client_id,
            "is_existing_partner": {"$ne": True},
        })
        docs = await cursor.to_list(length=500)

        results = []
        for doc in docs:
            signals = doc.get("engagement_signals", [])
            recent = [s for s in signals if _is_recent(s.get("date"), cutoff)]
            if len(recent) >= min_signals:
                doc["recent_signal_count"] = len(recent)
                results.append(doc)

        results.sort(key=lambda d: d.get("recent_signal_count", 0), reverse=True)
        return results
    except Exception as e:
        logger.error("get_hot_leads failed: %s", e)
        return []


async def get_warm_leads(client_id: str, quiet_days: int = 28, db=None) -> list[dict]:
    """Get providers who engaged previously but have been quiet for N days."""
    try:
        col = _get_collection(db)
        cutoff = datetime.now(timezone.utc) - timedelta(days=quiet_days)

        cursor = col.find({
            "client_id": client_id,
            "is_existing_partner": {"$ne": True},
        })
        docs = await cursor.to_list(length=500)

        results = []
        for doc in docs:
            signals = doc.get("engagement_signals", [])
            if not signals:
                continue
            dates = [s.get("date") for s in signals if s.get("date") is not None]
            if not dates:
                continue
            last_date = max(dates)
            # Ensure timezone-aware comparison
            if last_date.tzinfo is None:
                last_date = last_date.replace(tzinfo=timezone.utc)
            if last_date <= cutoff:
                doc["last_signal_date"] = last_date
                results.append(doc)

        results.sort(key=lambda d: d.get("last_signal_date", datetime.min.replace(tzinfo=timezone.utc)), reverse=True)
        return results
    except Exception as e:
        logger.error("get_warm_leads failed: %s", e)
        return []


def _is_recent(date_val, cutoff):
    """Check if a date is more recent than the cutoff, handling timezone awareness."""
    if date_val is None:
        return False
    if date_val.tzinfo is None:
        date_val = date_val.replace(tzinfo=timezone.utc)
    if cutoff.tzinfo is None:
        cutoff = cutoff.replace(tzinfo=timezone.utc)
    return date_val >= cutoff


async def flag_existing_partners(client_id: str, partner_npis: list[str], db=None) -> int:
    """Mark providers as existing partners. Returns count updated."""
    try:
        col = _get_collection(db)
        result = await col.update_many(
            {"client_id": client_id, "npi": {"$in": partner_npis}},
            {"$set": {"is_existing_partner": True, "updated_at": datetime.now(timezone.utc)}},
        )
        return result.modified_count
    except Exception as e:
        logger.error("flag_existing_partners failed: %s", e)
        return 0
