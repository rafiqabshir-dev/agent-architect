"""Tests for DME compliance checking.

Uses a mock LLM that returns deterministic compliance results
based on content analysis patterns.
"""

import pytest
from src.retrieval_graph.dme_compliance import check_dme_compliance
from src.retrieval_graph.autonomous_graph import compile_graph


def _make_mock_llm(response: dict):
    """Create a mock LLM function that returns a fixed response."""
    async def mock_llm(system_prompt, user_message, **kwargs):
        return response
    return mock_llm


def _analyze_content(content: str) -> dict:
    """
    Rule-based content analyzer that mimics what the LLM would return.
    Used as a deterministic mock for testing.
    """
    violations = []
    content_lower = content.lower()

    # ANTI-KICKBACK checks
    kickback_phrases = [
        "refer", "gift card", "receive a gift", "volume bonus",
        "refer 10 patients", "thank you", "incentive",
    ]
    if any(phrase in content_lower for phrase in ["gift card", "receive a gift", "volume bonus"]):
        violations.append({
            "rule_category": "ANTI-KICKBACK",
            "severity": "HIGH",
            "excerpt": content[:100],
            "explanation": "Content implies financial incentive for referrals, violating Anti-Kickback Statute.",
        })
    elif "refer" in content_lower and ("receive" in content_lower or "reward" in content_lower):
        violations.append({
            "rule_category": "ANTI-KICKBACK",
            "severity": "HIGH",
            "excerpt": content[:100],
            "explanation": "Content implies incentive for referrals.",
        })

    # SUPERLATIVE checks
    superlatives = ["best", "fastest", "most reliable", "leading", "top-rated"]
    for sup in superlatives:
        if sup in content_lower:
            violations.append({
                "rule_category": "SUPERLATIVE AND UNSUBSTANTIATED CLAIMS",
                "severity": "MEDIUM",
                "excerpt": f"...{sup}...",
                "explanation": f"Unsubstantiated superlative '{sup}' used without cited evidence.",
            })
            break  # one is enough

    # CMS CLAIM ACCURACY checks
    coverage_promises = [
        "covers 100%", "fully covered", "guaranteed coverage",
        "medicare covers", "medicaid covers",
    ]
    for phrase in coverage_promises:
        if phrase in content_lower:
            violations.append({
                "rule_category": "CMS CLAIM ACCURACY",
                "severity": "HIGH",
                "excerpt": phrase,
                "explanation": "Content promises specific coverage. Use 'may be covered' instead.",
            })
            break

    # HIPAA checks
    # Look for patterns that suggest patient-specific info
    hipaa_patterns = ["your patient john", "patient john doe", "his compliance", "her treatment"]
    for pattern in hipaa_patterns:
        if pattern in content_lower:
            violations.append({
                "rule_category": "HIPAA MARKETING",
                "severity": "HIGH",
                "excerpt": pattern,
                "explanation": "Content reveals patient-identifiable information.",
            })
            break

    passed = len(violations) == 0
    return {"violations": violations, "passed": passed}


def _make_analyzing_mock():
    """Create a mock LLM that uses rule-based analysis."""
    async def mock_llm(system_prompt, user_message, **kwargs):
        # Extract content from the user message
        if "---\n" in user_message:
            parts = user_message.split("---\n")
            if len(parts) >= 2:
                content = parts[1].split("\n---")[0] if "\n---" in parts[1] else parts[1]
            else:
                content = user_message
        else:
            content = user_message
        return _analyze_content(content)
    return mock_llm


@pytest.mark.asyncio
async def test_clean_content_passes():
    """Content with no violations returns passed=True."""
    content = (
        "Order from Jama Medical Equipment through Parachute Health in under 60 seconds. "
        "We deliver same-day within 20 miles of Des Plaines. ACHC accredited. "
        "Medicare and Medicaid accepted."
    )
    result = await check_dme_compliance(
        content, "provider_email", {}, _llm_fn=_make_analyzing_mock()
    )
    assert result["passed"] is True
    assert result["high_severity_count"] == 0


@pytest.mark.asyncio
async def test_kickback_language_flagged():
    """Content with implied kickback returns HIGH severity violation."""
    content = "Refer 10 patients to us this month and receive a gift card as our thank you."
    result = await check_dme_compliance(
        content, "provider_email", {}, _llm_fn=_make_analyzing_mock()
    )
    assert result["passed"] is False
    assert any(v["rule_category"] == "ANTI-KICKBACK" for v in result["violations"])
    assert any(v["severity"] == "HIGH" for v in result["violations"])


@pytest.mark.asyncio
async def test_superlative_flagged():
    """Content with unsubstantiated superlative returns violation."""
    content = "We are the best DME supplier in the Chicago area with the fastest delivery."
    result = await check_dme_compliance(
        content, "provider_email", {}, _llm_fn=_make_analyzing_mock()
    )
    assert result["passed"] is False
    assert any(
        v["rule_category"] == "SUPERLATIVE AND UNSUBSTANTIATED CLAIMS"
        for v in result["violations"]
    )


@pytest.mark.asyncio
async def test_coverage_promise_flagged():
    """Content that promises coverage returns violation."""
    content = "Medicare covers 100% of your CPAP supplies. Order now."
    result = await check_dme_compliance(
        content, "patient_education", {}, _llm_fn=_make_analyzing_mock()
    )
    assert result["passed"] is False
    assert any(v["rule_category"] == "CMS CLAIM ACCURACY" for v in result["violations"])


@pytest.mark.asyncio
async def test_clean_ease_of_referral_content():
    """Properly framed ease-of-referral content passes."""
    content = (
        "Dr. Smith — referring patients to Jama Medical is simple. "
        "Search 'Jama Medical' on Parachute Health to place a digital order in under 60 seconds. "
        "We deliver within 24 hours to your service area. "
        "Call us directly at 847-555-0100 with questions. "
        "ACHC accredited, Medicare/Medicaid accepted."
    )
    result = await check_dme_compliance(
        content, "provider_email", {}, _llm_fn=_make_analyzing_mock()
    )
    assert result["passed"] is True


@pytest.mark.asyncio
async def test_hipaa_violation_flagged():
    """Content mentioning specific patient returns HIGH violation."""
    content = (
        "We recently delivered a CPAP to your patient John Doe "
        "and wanted to follow up about his compliance."
    )
    result = await check_dme_compliance(
        content, "provider_email", {}, _llm_fn=_make_analyzing_mock()
    )
    assert result["passed"] is False
    assert any(v["rule_category"] == "HIPAA MARKETING" for v in result["violations"])
    assert any(v["severity"] == "HIGH" for v in result["violations"])


@pytest.mark.asyncio
async def test_compliance_error_handled():
    """When the LLM call fails, return requires_revision=True for safety."""
    async def failing_llm(system_prompt, user_message, **kwargs):
        raise Exception("LLM unavailable")

    result = await check_dme_compliance(
        "Some content", "provider_email", {}, _llm_fn=failing_llm
    )
    assert result["passed"] is False
    assert result["requires_revision"] is True


def test_graph_compiles():
    """Verify the autonomous graph compiles without errors."""
    graph = compile_graph()
    assert "nodes" in graph
    assert "dme_compliance_check" in graph["nodes"]
    assert "generate_content" in graph["nodes"]
    assert "revise_content" in graph["nodes"]
    assert "ethics_guardrail" in graph["nodes"]
    assert "queue_for_review" in graph["nodes"]
    assert graph["entry_point"] == "generate_content"
