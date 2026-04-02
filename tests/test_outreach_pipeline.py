"""Tests for the full outreach pipeline."""

import pytest
from datetime import datetime, timezone
from unittest.mock import patch, AsyncMock
from tests.conftest import AsyncMongoCollection
from src.provider_targeting.provider_store import (
    upsert_provider,
    set_collection,
    flag_existing_partners,
)
from src.retrieval_graph.outreach_pipeline import run_outreach_cycle


def _make_mock_llm():
    """Mock LLM that returns compliant content."""
    async def mock_llm(system_prompt, user_message, **kwargs):
        return (
            "Jama Medical Equipment — Order through Parachute Health in under 60 seconds. "
            "Same-day delivery within 20 miles. ACHC accredited. "
            "Medicare and Medicaid accepted. Call 847-555-0100 with questions."
        )
    return mock_llm


def _make_passing_compliance():
    """Mock compliance check that always passes."""
    async def mock_compliance(content, content_type, client_config, **kwargs):
        return {
            "passed": True,
            "violations": [],
            "high_severity_count": 0,
            "requires_revision": False,
        }
    return mock_compliance


def _make_failing_compliance():
    """Mock compliance check that always fails."""
    async def mock_compliance(content, content_type, client_config, **kwargs):
        return {
            "passed": False,
            "violations": [
                {
                    "rule_category": "ANTI-KICKBACK",
                    "severity": "HIGH",
                    "excerpt": "bad content",
                    "explanation": "Violation found.",
                }
            ],
            "high_severity_count": 1,
            "requires_revision": True,
        }
    return mock_compliance


JAMA_CONFIG = {
    "brand_name": "Jama Medical",
    "ordering_method": "Parachute Health",
    "delivery_turnaround": "same-day",
    "accreditation": "ACHC",
    "phone": "847-555-0100",
}

TEST_PROVIDERS = [
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
        "specialty": "Internal Medicine",
        "practice_name": "Beta Internal",
        "practice_address": "200 Elm St",
        "city": "Des Plaines",
        "state": "IL",
        "zip": "60016",
        "phone": "847-555-0002",
    },
    {
        "npi": "3333333333",
        "provider_name": "Dr. Gamma",
        "specialty": "Pulmonary Disease",
        "practice_name": "Gamma Pulmonary",
        "practice_address": "300 Oak Ave",
        "city": "Des Plaines",
        "state": "IL",
        "zip": "60016",
        "phone": "847-555-0003",
    },
    {
        "npi": "4444444444",
        "provider_name": "Dr. Delta",
        "specialty": "Internal Medicine",
        "practice_name": "Delta Internal",
        "practice_address": "400 Pine Rd",
        "city": "Des Plaines",
        "state": "IL",
        "zip": "60016",
        "phone": "847-555-0004",
    },
    {
        "npi": "5555555555",
        "provider_name": "Dr. Epsilon",
        "specialty": "Pulmonary Disease",
        "practice_name": "Epsilon Pulmonary",
        "practice_address": "500 Birch Ln",
        "city": "Des Plaines",
        "state": "IL",
        "zip": "60016",
        "phone": "847-555-0005",
    },
]


@pytest.fixture
def pipeline_db():
    """Set up a mock DB with provider_prospects and publish_queue collections."""

    class MockDB:
        def __init__(self):
            self._collections = {}

        def __getitem__(self, name):
            if name not in self._collections:
                self._collections[name] = AsyncMongoCollection(name)
            return self._collections[name]

    return MockDB()


@pytest.fixture
async def seeded_db(pipeline_db):
    """Seed test providers and set the collection."""
    provider_col = pipeline_db["provider_prospects"]
    set_collection(provider_col)
    for p in TEST_PROVIDERS:
        await upsert_provider("jama_test", dict(p))
    return pipeline_db


@pytest.mark.asyncio
async def test_full_outreach_cycle(seeded_db):
    """
    Integration test:
    1. Seed 5 test providers in provider_prospects_test
    2. Run outreach cycle
    3. Verify items appear in publish_queue with recipient info
    4. Verify all items passed compliance
    5. Verify each queue item has: content, recipient_name, recipient_npi, channel
    """
    summary = await run_outreach_cycle(
        client_id="jama_test",
        client_config=JAMA_CONFIG,
        batch_size=5,
        db=seeded_db,
        _llm_fn=_make_mock_llm(),
        _compliance_fn=_make_passing_compliance(),
    )

    assert summary["composed"] > 0
    assert summary["passed_compliance"] == summary["composed"]
    assert summary["queued"] == summary["composed"]
    assert summary["failed"] == 0

    # Verify queue items
    queue_col = seeded_db["publish_queue"]
    items = await queue_col.find({"client_id": "jama_test"}).to_list(length=100)
    assert len(items) > 0

    for item in items:
        assert item["content"]  # non-empty
        assert item["recipient_npi"]
        assert item["recipient_name"]
        assert item["recipient_channel"] in ("email", "fax", "print_dropoff")
        assert item["status"] == "pending_review"


@pytest.mark.asyncio
async def test_compliance_failure_routes_to_revision(seeded_db):
    """
    Seed a provider. Mock compliance to fail, then pass on retry.
    Verify the content gets revised.
    """
    call_count = {"n": 0}

    async def fail_then_pass(content, content_type, client_config, **kwargs):
        call_count["n"] += 1
        if call_count["n"] <= 1:
            return {
                "passed": False,
                "violations": [{"rule_category": "TEST", "severity": "HIGH", "excerpt": "", "explanation": ""}],
                "high_severity_count": 1,
                "requires_revision": True,
            }
        return {
            "passed": True,
            "violations": [],
            "high_severity_count": 0,
            "requires_revision": False,
        }

    summary = await run_outreach_cycle(
        client_id="jama_test",
        client_config=JAMA_CONFIG,
        batch_size=1,
        db=seeded_db,
        _llm_fn=_make_mock_llm(),
        _compliance_fn=fail_then_pass,
    )

    # Compliance was called multiple times (initial + retry)
    assert call_count["n"] >= 2
    assert summary["passed_compliance"] >= 1


@pytest.mark.asyncio
async def test_max_revisions_routes_to_manual_review(seeded_db):
    """
    Seed a provider. Mock compliance to always fail.
    After 2 revisions, verify item is queued with status 'compliance_review_needed'.
    """
    summary = await run_outreach_cycle(
        client_id="jama_test",
        client_config=JAMA_CONFIG,
        batch_size=1,
        db=seeded_db,
        _llm_fn=_make_mock_llm(),
        _compliance_fn=_make_failing_compliance(),
    )

    assert summary["passed_compliance"] == 0
    assert summary["queued"] >= 1  # still queued, but with review status

    queue_col = seeded_db["publish_queue"]
    items = await queue_col.find({"client_id": "jama_test"}).to_list(length=100)
    review_items = [i for i in items if i["status"] == "compliance_review_needed"]
    assert len(review_items) >= 1


@pytest.mark.asyncio
async def test_existing_partners_excluded_from_batch(seeded_db):
    """
    Seed 5 providers, flag 2 as existing partners.
    Run outreach cycle with batch_size=5. Verify only 3 items in queue.
    """
    await flag_existing_partners("jama_test", ["1111111111", "2222222222"])

    summary = await run_outreach_cycle(
        client_id="jama_test",
        client_config=JAMA_CONFIG,
        batch_size=5,
        db=seeded_db,
        _llm_fn=_make_mock_llm(),
        _compliance_fn=_make_passing_compliance(),
    )

    assert summary["composed"] == 3  # 5 - 2 partners
    queue_col = seeded_db["publish_queue"]
    items = await queue_col.find({"client_id": "jama_test"}).to_list(length=100)
    npis = [i["recipient_npi"] for i in items]
    assert "1111111111" not in npis
    assert "2222222222" not in npis
