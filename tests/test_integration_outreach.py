"""End-to-end integration test for the SABAR outreach pipeline.

Simulates Jama Medical Equipment's first outreach cycle through all three features:
- Feature 1: Provider discovery via NPI Registry
- Feature 2: DME compliance checking
- Feature 3: Outreach composition and publish queue
"""

import pytest
from unittest.mock import patch, AsyncMock
from tests.conftest import AsyncMongoCollection
from src.provider_targeting.targeting_service import discover_providers, get_outreach_batch
from src.provider_targeting.provider_store import (
    set_collection,
    flag_existing_partners,
    get_prospects_for_client,
    add_outreach_record,
)
from src.retrieval_graph.outreach_pipeline import run_outreach_cycle
from src.retrieval_graph.dme_compliance import check_dme_compliance


# --- Mock data for NPI search ---
MOCK_NPI_RESULTS_PULMONARY = [
    {
        "npi": "1001001001",
        "provider_name": "Dr. Sarah Chen, MD",
        "specialty": "Pulmonary Disease",
        "practice_name": "Lakeside Pulmonary Associates",
        "practice_address": "1500 N River Rd",
        "city": "Des Plaines",
        "state": "IL",
        "zip": "60016",
        "phone": "847-555-1001",
    },
    {
        "npi": "1002002002",
        "provider_name": "Dr. Michael Torres, MD",
        "specialty": "Pulmonary Disease",
        "practice_name": "Northwest Lung Center",
        "practice_address": "750 Lee St",
        "city": "Des Plaines",
        "state": "IL",
        "zip": "60016",
        "phone": "847-555-1002",
    },
    {
        "npi": "1003003003",
        "provider_name": "Dr. Rachel Kim, DO",
        "specialty": "Pulmonary Disease",
        "practice_name": "Prairie Pulmonary Group",
        "practice_address": "200 S Mount Prospect Rd",
        "city": "Des Plaines",
        "state": "IL",
        "zip": "60016",
        "phone": "847-555-1003",
    },
]

MOCK_NPI_RESULTS_INTERNAL = [
    {
        "npi": "2001001001",
        "provider_name": "Dr. James Wilson, MD",
        "specialty": "Internal Medicine",
        "practice_name": "Des Plaines Family Practice",
        "practice_address": "3200 Dempster St",
        "city": "Des Plaines",
        "state": "IL",
        "zip": "60016",
        "phone": "847-555-2001",
    },
    {
        "npi": "2002002002",
        "provider_name": "Dr. Anna Patel, MD",
        "specialty": "Internal Medicine",
        "practice_name": "Suburban Internal Medicine",
        "practice_address": "800 Central Ave",
        "city": "Des Plaines",
        "state": "IL",
        "zip": "60016",
        "phone": "847-555-2002",
    },
]

JAMA_CONFIG = {
    "brand_name": "Jama Medical Equipment",
    "ordering_method": "Parachute Health",
    "delivery_turnaround": "same-day",
    "delivery_radius": "20 miles",
    "accreditation": "ACHC",
    "phone": "847-555-0100",
    "city": "Des Plaines",
    "state": "IL",
}

EXISTING_PARTNER_NPIS = ["1001001001", "2001001001"]


def _mock_llm():
    """Mock LLM returning compliant content with Parachute Health mention."""
    async def llm(system_prompt, user_message, **kwargs):
        return (
            "Dr. — Jama Medical Equipment makes DME ordering simple. "
            "Search 'Jama Medical' on Parachute Health to place a digital order in under 60 seconds. "
            "We offer same-day delivery within 20 miles of Des Plaines. "
            "ACHC accredited. Medicare and Medicaid accepted. "
            "Call 847-555-0100 with any questions."
        )
    return llm


def _mock_passing_compliance():
    """Compliance check that always passes (content is clean)."""
    async def compliance(content, content_type, client_config, **kwargs):
        return {
            "passed": True,
            "violations": [],
            "high_severity_count": 0,
            "requires_revision": False,
        }
    return compliance


async def _mock_npi_search(taxonomy_description, city, state, radius="20", limit=50):
    """Mock NPI search returning test providers by specialty."""
    if "Pulmonary" in taxonomy_description:
        return MOCK_NPI_RESULTS_PULMONARY
    if "Internal" in taxonomy_description:
        return MOCK_NPI_RESULTS_INTERNAL
    return []


class IntegrationDB:
    """Test database that provides AsyncMongoCollection instances."""

    def __init__(self):
        self._collections = {}

    def __getitem__(self, name):
        if name not in self._collections:
            self._collections[name] = AsyncMongoCollection(name)
        return self._collections[name]


@pytest.mark.asyncio
async def test_end_to_end_jama_outreach():
    """
    Full end-to-end test simulating Jama Medical Equipment's first outreach cycle.

    Steps:
    1. Run provider discovery for specialties: ["Pulmonary Disease", "Internal Medicine"]
    2. Verify providers found > 0
    3. Flag 2 NPIs as existing partners
    4. Get outreach batch of 3
    5. Verify batch excludes existing partners
    6. Run full outreach cycle
    7. Verify items in publish_queue have required fields
    8. Verify content mentions "Parachute Health" or ordering method
    9. Verify content passed DME compliance (no HIGH severity violations)
    10. Verify outreach_history updated on providers
    """
    db = IntegrationDB()
    provider_col = db["provider_prospects"]
    set_collection(provider_col)

    # --- Step 1: Provider Discovery ---
    with patch(
        "src.provider_targeting.targeting_service.search_providers",
        side_effect=_mock_npi_search,
    ):
        summary = await discover_providers(
            client_id="jama_integration",
            specialties=["Pulmonary Disease", "Internal Medicine"],
            city="Des Plaines",
            state="IL",
            radius="20",
            existing_partner_npis=EXISTING_PARTNER_NPIS,
            db=db,
        )

    # --- Step 2: Verify providers found ---
    assert summary["total_found"] > 0, f"Expected providers, got: {summary}"
    assert summary["total_found"] == 5  # 3 pulm + 2 internal

    # --- Step 3: Partners flagged ---
    assert summary["existing_partners"] == 2

    # Verify partner flags in DB
    partner_doc = await provider_col.find_one({"npi": "1001001001"})
    assert partner_doc["is_existing_partner"] is True

    # --- Step 4: Get outreach batch of 3 ---
    batch = await get_outreach_batch("jama_integration", batch_size=3, db=db)

    # --- Step 5: Batch excludes partners ---
    batch_npis = [p["npi"] for p in batch]
    assert "1001001001" not in batch_npis, "Existing partner should be excluded"
    assert "2001001001" not in batch_npis, "Existing partner should be excluded"
    assert len(batch) == 3, f"Expected 3 in batch, got {len(batch)}"

    # --- Step 6: Run full outreach cycle ---
    cycle_summary = await run_outreach_cycle(
        client_id="jama_integration",
        client_config=JAMA_CONFIG,
        batch_size=3,
        db=db,
        _llm_fn=_mock_llm(),
        _compliance_fn=_mock_passing_compliance(),
    )

    assert cycle_summary["composed"] == 3
    assert cycle_summary["queued"] == 3
    assert cycle_summary["failed"] == 0

    # --- Step 7: Verify publish_queue items ---
    queue_col = db["publish_queue"]
    queue_items = await queue_col.find({"client_id": "jama_integration"}).to_list(length=100)
    assert len(queue_items) == 3

    for item in queue_items:
        # Required fields
        assert item["content"], "Content must be non-empty"
        assert item["recipient_npi"], "Must have recipient NPI"
        assert item["recipient_name"], "Must have recipient name"
        assert item["recipient_channel"] in ("email", "fax", "print_dropoff"), \
            f"Invalid channel: {item['recipient_channel']}"
        assert item["status"] == "pending_review"

        # --- Step 8: Content mentions ordering method ---
        assert "Parachute Health" in item["content"] or "parachute" in item["content"].lower(), \
            "Content must mention ordering method"

    # --- Step 9: Verify compliance (all passed) ---
    assert cycle_summary["passed_compliance"] == 3

    # --- Step 10: Verify outreach_history updated ---
    for npi in batch_npis:
        doc = await provider_col.find_one({"client_id": "jama_integration", "npi": npi})
        assert len(doc.get("outreach_history", [])) > 0, \
            f"Provider {npi} should have outreach history"


@pytest.mark.asyncio
async def test_integration_compliance_rejection_flow():
    """
    Integration test: content that fails compliance gets revised,
    and if it keeps failing, gets flagged for manual review.
    """
    db = IntegrationDB()
    provider_col = db["provider_prospects"]
    set_collection(provider_col)

    # Seed one provider
    from src.provider_targeting.provider_store import upsert_provider
    await upsert_provider("jama_rejection_test", {
        "npi": "9999999999",
        "provider_name": "Dr. Reject Test",
        "specialty": "Pulmonary Disease",
        "practice_name": "Test Practice",
        "practice_address": "999 Test St",
        "city": "Des Plaines",
        "state": "IL",
        "zip": "60016",
        "phone": "847-555-9999",
    })

    cycle_summary = await run_outreach_cycle(
        client_id="jama_rejection_test",
        client_config=JAMA_CONFIG,
        batch_size=1,
        db=db,
        _llm_fn=_mock_llm(),
        _compliance_fn=lambda content, ct, cc, **kw: _always_fail_compliance(content, ct, cc),
    )

    assert cycle_summary["passed_compliance"] == 0
    assert cycle_summary["queued"] == 1  # queued with review status

    queue_col = db["publish_queue"]
    items = await queue_col.find({"client_id": "jama_rejection_test"}).to_list(length=100)
    assert any(i["status"] == "compliance_review_needed" for i in items)


async def _always_fail_compliance(content, content_type, client_config):
    return {
        "passed": False,
        "violations": [
            {
                "rule_category": "ANTI-KICKBACK",
                "severity": "HIGH",
                "excerpt": "test",
                "explanation": "Always fails for testing.",
            }
        ],
        "high_severity_count": 1,
        "requires_revision": True,
    }
