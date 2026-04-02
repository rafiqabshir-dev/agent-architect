"""Tests for the provider targeting orchestrator."""

import pytest
from unittest.mock import AsyncMock, patch
from tests.conftest import AsyncMongoCollection
from src.provider_targeting.targeting_service import discover_providers, get_outreach_batch
from src.provider_targeting.provider_store import (
    set_collection,
    upsert_provider,
    flag_existing_partners,
    get_prospects_for_client,
)


MOCK_NPI_RESULTS = [
    {
        "npi": "1111111111",
        "provider_name": "Dr. Alpha",
        "specialty": "Pulmonary Disease",
        "practice_name": "Alpha Pulmonary",
        "practice_address": "100 Main St",
        "city": "Des Plaines",
        "state": "IL",
        "zip": "60016",
        "phone": "847-555-0001",
    },
    {
        "npi": "2222222222",
        "provider_name": "Dr. Beta",
        "specialty": "Pulmonary Disease",
        "practice_name": "Beta Pulmonary",
        "practice_address": "200 Elm St",
        "city": "Des Plaines",
        "state": "IL",
        "zip": "60016",
        "phone": "847-555-0002",
    },
    {
        "npi": "3333333333",
        "provider_name": "Dr. Gamma",
        "specialty": "Internal Medicine",
        "practice_name": "Gamma Internal",
        "practice_address": "300 Oak Ave",
        "city": "Des Plaines",
        "state": "IL",
        "zip": "60016",
        "phone": "847-555-0003",
    },
]


@pytest.fixture
def provider_col():
    col = AsyncMongoCollection("provider_prospects_test")
    set_collection(col)
    return col


@pytest.mark.asyncio
async def test_discover_providers_des_plaines(provider_col):
    """Full discovery for Des Plaines. Expect summary with total_found > 0."""
    async def mock_search(taxonomy_description, city, state, radius="20", limit=50):
        return [r for r in MOCK_NPI_RESULTS if r["specialty"] == taxonomy_description]

    with patch("src.provider_targeting.targeting_service.search_providers", side_effect=mock_search):
        summary = await discover_providers(
            client_id="jama_test",
            specialties=["Pulmonary Disease", "Internal Medicine"],
            city="Des Plaines",
            state="IL",
        )

    assert summary["total_found"] > 0
    assert summary["total_found"] == 3
    assert summary["by_specialty"]["Pulmonary Disease"] == 2
    assert summary["by_specialty"]["Internal Medicine"] == 1


@pytest.mark.asyncio
async def test_existing_partners_flagged(provider_col):
    """Provide partner NPIs. Confirm they are flagged in DB."""
    async def mock_search(taxonomy_description, city, state, radius="20", limit=50):
        return MOCK_NPI_RESULTS[:2]

    with patch("src.provider_targeting.targeting_service.search_providers", side_effect=mock_search):
        summary = await discover_providers(
            client_id="jama_test",
            specialties=["Pulmonary Disease"],
            city="Des Plaines",
            state="IL",
            existing_partner_npis=["1111111111"],
        )

    assert summary["existing_partners"] == 1

    doc = await provider_col.find_one({"client_id": "jama_test", "npi": "1111111111"})
    assert doc["is_existing_partner"] is True


@pytest.mark.asyncio
async def test_get_outreach_batch_respects_exclusions(provider_col):
    """Batch should not include existing partners or inactive providers."""
    # Seed providers
    for r in MOCK_NPI_RESULTS:
        await upsert_provider("jama_test", dict(r))

    # Flag one as partner, one as inactive
    await flag_existing_partners("jama_test", ["1111111111"])
    await provider_col.update_one(
        {"client_id": "jama_test", "npi": "2222222222"},
        {"$set": {"status": "inactive"}},
    )

    batch = await get_outreach_batch("jama_test", batch_size=5)
    npis = [p["npi"] for p in batch]
    assert "1111111111" not in npis  # partner excluded
    assert "2222222222" not in npis  # inactive excluded
    assert "3333333333" in npis      # valid prospect included
