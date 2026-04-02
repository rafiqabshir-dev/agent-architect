"""Tests for outreach composer."""

import pytest
from src.retrieval_graph.outreach_composer import compose_outreach, compose_batch


def _make_mock_llm(content_text: str):
    """Create a mock LLM that returns fixed content."""
    async def mock_llm(system_prompt, user_message, **kwargs):
        return content_text
    return mock_llm


def _make_smart_mock_llm():
    """Create a mock LLM that generates content based on the prompt."""
    async def mock_llm(system_prompt, user_message, **kwargs):
        # Extract key info from the prompt to generate relevant content
        content_parts = []

        if "Parachute Health" in user_message:
            content_parts.append(
                "Order through Parachute Health in under 60 seconds."
            )
        if "fax" in user_message.lower() and "847-555-0101" in user_message:
            content_parts.append("Send orders via fax to 847-555-0101.")

        if "same-day" in user_message.lower():
            content_parts.append("We offer same-day delivery within your service area.")
        if "24 hours" in user_message.lower():
            content_parts.append("CMN turnaround within 24 hours.")

        if "ACHC" in user_message:
            content_parts.append("ACHC accredited.")
        if "Jama Medical" in user_message:
            content_parts.insert(0, "Jama Medical Equipment —")

        if not content_parts:
            content_parts.append(
                "We provide quality DME with fast delivery and easy ordering."
            )

        content_parts.append("Medicare and Medicaid accepted. Call us with questions.")
        return " ".join(content_parts)

    return mock_llm


@pytest.mark.asyncio
async def test_compose_outreach_for_pulmonologist():
    """Compose email for a pulmonologist. Content must mention ordering method and delivery."""
    provider = {
        "specialty": "Pulmonary Disease",
        "provider_name": "Dr. Test",
        "practice_name": "Test Pulmonary",
    }
    config = {
        "brand_name": "Jama Medical",
        "ordering_method": "Parachute Health",
        "delivery_turnaround": "same-day",
        "accreditation": "ACHC",
    }
    result = await compose_outreach(provider, config, _llm_fn=_make_smart_mock_llm())
    assert "Parachute Health" in result["content"] or "parachute" in result["content"].lower()
    assert result["content_type"] == "provider_email"
    assert result["channel"] == "email"
    assert result["subject_line"] is not None


@pytest.mark.asyncio
async def test_compose_outreach_for_discharge_planner():
    """Compose for discharge planner. Must mention delivery speed and CMN turnaround."""
    provider = {
        "specialty": "Discharge Planner",
        "provider_name": "Jane Test",
        "practice_name": "Test Hospital",
        "contact_fax": "847-555-9999",
    }
    config = {
        "brand_name": "Jama Medical",
        "ordering_method": "fax",
        "fax_number": "847-555-0101",
        "delivery_turnaround": "same-day",
        "cmn_turnaround": "24 hours",
    }
    result = await compose_outreach(provider, config, _llm_fn=_make_smart_mock_llm())
    assert "fax" in result["content"].lower() or "847-555-0101" in result["content"]


@pytest.mark.asyncio
async def test_compose_batch():
    """Compose for 3 providers. Get 3 results."""
    providers = [
        {"specialty": "Pulmonary Disease", "provider_name": "Dr. A", "practice_name": "Practice A"},
        {"specialty": "Internal Medicine", "provider_name": "Dr. B", "practice_name": "Practice B"},
        {"specialty": "Discharge Planner", "provider_name": "Nurse C", "practice_name": "Hospital C"},
    ]
    config = {
        "brand_name": "Jama Medical",
        "ordering_method": "Parachute Health",
        "delivery_turnaround": "same-day",
        "accreditation": "ACHC",
    }
    results = await compose_batch(providers, config, _llm_fn=_make_smart_mock_llm())
    assert len(results) == 3
    for r in results:
        assert "content" in r
        assert "provider" in r
        assert r["content"]  # non-empty


@pytest.mark.asyncio
async def test_compose_outreach_has_talking_points():
    """Outreach result includes talking points."""
    provider = {"specialty": "Pulmonary Disease", "provider_name": "Dr. X", "practice_name": "X Practice"}
    config = {"brand_name": "Jama Medical", "ordering_method": "Parachute Health", "delivery_turnaround": "same-day", "accreditation": "ACHC"}
    result = await compose_outreach(provider, config, _llm_fn=_make_smart_mock_llm())
    assert isinstance(result["talking_points"], list)
    assert len(result["talking_points"]) > 0
