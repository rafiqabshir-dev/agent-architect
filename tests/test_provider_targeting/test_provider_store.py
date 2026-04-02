"""Tests for provider_store MongoDB CRUD operations using mongomock."""

import pytest
from datetime import datetime, timedelta, timezone
from tests.conftest import AsyncMongoCollection
from src.provider_targeting.provider_store import (
    upsert_provider,
    get_prospects_for_client,
    update_provider_status,
    add_engagement_signal,
    add_outreach_record,
    get_hot_leads,
    get_warm_leads,
    flag_existing_partners,
    set_collection,
)


@pytest.fixture
def provider_col():
    """Fresh async MongoDB collection for each test."""
    col = AsyncMongoCollection("provider_prospects_test")
    set_collection(col)
    return col


def _make_provider(npi="1234567890", **overrides):
    """Create a sample provider dict."""
    data = {
        "npi": npi,
        "provider_name": f"Dr. Test {npi[-4:]}",
        "specialty": "Pulmonary Disease",
        "practice_name": "Test Practice",
        "practice_address": "100 Main St",
        "city": "Des Plaines",
        "state": "IL",
        "zip": "60016",
        "phone": "847-555-0100",
    }
    data.update(overrides)
    return data


@pytest.mark.asyncio
async def test_upsert_new_provider(provider_col):
    """Insert a new provider. Confirm it exists in DB."""
    provider = _make_provider()
    doc_id = await upsert_provider("client_1", provider)
    assert doc_id

    doc = await provider_col.find_one({"client_id": "client_1", "npi": "1234567890"})
    assert doc is not None
    assert doc["provider_name"] == "Dr. Test 7890"
    assert doc["status"] == "new"


@pytest.mark.asyncio
async def test_upsert_existing_provider_updates(provider_col):
    """Upsert same NPI twice. Confirm only one document, updated fields."""
    provider = _make_provider()
    await upsert_provider("client_1", provider)

    updated = _make_provider(provider_name="Dr. Updated Name")
    await upsert_provider("client_1", updated)

    count = await provider_col.count_documents({"client_id": "client_1", "npi": "1234567890"})
    assert count == 1

    doc = await provider_col.find_one({"client_id": "client_1", "npi": "1234567890"})
    assert doc["provider_name"] == "Dr. Updated Name"


@pytest.mark.asyncio
async def test_get_prospects_excludes_existing_partners(provider_col):
    """Insert partner and non-partner. Get with exclude=True. Only non-partner returned."""
    await upsert_provider("client_1", _make_provider("1111111111"))
    await upsert_provider(
        "client_1",
        _make_provider("2222222222", is_existing_partner=True),
    )
    # Manually set the partner flag (since upsert uses $setOnInsert)
    await provider_col.update_one(
        {"npi": "2222222222"},
        {"$set": {"is_existing_partner": True}},
    )

    results = await get_prospects_for_client("client_1", exclude_existing_partners=True)
    npis = [r["npi"] for r in results]
    assert "1111111111" in npis
    assert "2222222222" not in npis


@pytest.mark.asyncio
async def test_add_engagement_signal(provider_col):
    """Add a signal. Confirm it appears in the provider's record."""
    await upsert_provider("client_1", _make_provider())
    signal = {"signal_type": "website_visit", "detail": "Viewed CPAP page"}
    result = await add_engagement_signal("client_1", "1234567890", signal)
    assert result is True

    doc = await provider_col.find_one({"client_id": "client_1", "npi": "1234567890"})
    assert len(doc["engagement_signals"]) == 1
    assert doc["engagement_signals"][0]["signal_type"] == "website_visit"


@pytest.mark.asyncio
async def test_add_outreach_record(provider_col):
    """Add an outreach record. Confirm it appears in history."""
    await upsert_provider("client_1", _make_provider())
    record = {"channel": "email", "content_id": "abc123", "action": "sent"}
    result = await add_outreach_record("client_1", "1234567890", record)
    assert result is True

    doc = await provider_col.find_one({"client_id": "client_1", "npi": "1234567890"})
    assert len(doc["outreach_history"]) == 1
    assert doc["outreach_history"][0]["channel"] == "email"


@pytest.mark.asyncio
async def test_update_provider_status(provider_col):
    """Update status from new to contacted."""
    await upsert_provider("client_1", _make_provider())
    result = await update_provider_status("client_1", "1234567890", "contacted")
    assert result is True

    doc = await provider_col.find_one({"client_id": "client_1", "npi": "1234567890"})
    assert doc["status"] == "contacted"


@pytest.mark.asyncio
async def test_get_hot_leads(provider_col):
    """Add 3 signals in last 7 days for one provider. Confirm it appears as hot lead."""
    await upsert_provider("client_1", _make_provider("3333333333"))
    now = datetime.now(timezone.utc)
    for i in range(3):
        await add_engagement_signal(
            "client_1",
            "3333333333",
            {"signal_type": "visit", "detail": f"visit {i}", "date": now - timedelta(days=i)},
        )

    leads = await get_hot_leads("client_1", days=7, min_signals=2)
    npis = [l["npi"] for l in leads]
    assert "3333333333" in npis


@pytest.mark.asyncio
async def test_get_warm_leads(provider_col):
    """Add signal 30 days ago, nothing since. Confirm it appears as warm lead."""
    await upsert_provider("client_1", _make_provider("4444444444"))
    old_date = datetime.now(timezone.utc) - timedelta(days=35)
    await add_engagement_signal(
        "client_1",
        "4444444444",
        {"signal_type": "email_open", "detail": "opened email", "date": old_date},
    )

    leads = await get_warm_leads("client_1", quiet_days=28)
    npis = [l["npi"] for l in leads]
    assert "4444444444" in npis


@pytest.mark.asyncio
async def test_flag_existing_partners(provider_col):
    """Flag specific NPIs as partners. Confirm they are flagged."""
    await upsert_provider("client_1", _make_provider("5555555555"))
    await upsert_provider("client_1", _make_provider("6666666666"))

    count = await flag_existing_partners("client_1", ["5555555555"])
    assert count == 1

    doc = await provider_col.find_one({"client_id": "client_1", "npi": "5555555555"})
    assert doc["is_existing_partner"] is True

    doc2 = await provider_col.find_one({"client_id": "client_1", "npi": "6666666666"})
    assert doc2.get("is_existing_partner") is not True
