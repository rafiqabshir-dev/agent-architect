"""DME-specific compliance checking for outreach content."""

import json
import logging
from src.retrieval_graph.utils import load_chat_model_json

logger = logging.getLogger(__name__)

DME_COMPLIANCE_RULES = """
You are a healthcare DME compliance reviewer. Check the following content against these rules:

ANTI-KICKBACK:
- No implied incentives for referrals (no "refer to us and receive...", no gifts, no volume bonuses)
- No language that could be construed as inducement under the Anti-Kickback Statute safe harbors
- Referral relationships must be presented as patient-benefit-driven, not financially motivated

CMS CLAIM ACCURACY:
- Equipment descriptions must match standard CMS/HCPCS terminology
- Do not promise coverage — say "may be covered" or "check eligibility"
- Do not state specific reimbursement amounts — these vary by payer and region
- Medicare/Medicaid references must be factually accurate

SUPERLATIVE AND UNSUBSTANTIATED CLAIMS:
- No "best", "fastest", "most reliable", "leading", "top-rated" without cited evidence
- No outcome promises ("guaranteed to improve", "will reduce readmissions")
- Comparative claims ("better than", "faster than") require substantiation

EASE-OF-REFERRAL FRAMING:
- Outreach to providers should lead with: how to order, delivery turnaround, CMN process
- Product catalogs should not be the lead message
- If client uses ePrescribing platform, it should be mentioned prominently

HIPAA MARKETING:
- No patient names, conditions, or identifiable information in outreach
- No testimonials that reveal patient identity without explicit written authorization
- No sharing of patient referral patterns or treatment details

For each rule violated, return:
- rule_category: which category above
- severity: "HIGH" (must fix before sending) or "MEDIUM" (should fix) or "LOW" (suggestion)
- excerpt: the specific text that violates
- explanation: why it violates and how to fix

If no violations found, return empty list.

Return as JSON: {"violations": [...], "passed": true/false}
"""


async def check_dme_compliance(
    content: str,
    content_type: str,
    client_config: dict,
    _llm_fn=None,
) -> dict:
    """
    Run DME-specific compliance check on content.

    Args:
        content: the outreach content to check
        content_type: "provider_email" | "discharge_planner_fax" | "patient_education" | "resupply_reminder"
        client_config: client configuration including ordering_method, accreditation, etc.
        _llm_fn: optional override for the LLM call (for testing)

    Returns:
        {
            "passed": bool,
            "violations": [{"rule_category", "severity", "excerpt", "explanation"}],
            "high_severity_count": int,
            "requires_revision": bool
        }
    """
    try:
        config_context = ""
        if client_config:
            config_context = f"\n\nClient context: {json.dumps(client_config, default=str)}"

        user_message = (
            f"Content type: {content_type}\n"
            f"Content to review:\n---\n{content}\n---"
            f"{config_context}\n\n"
            "Analyze this content against the DME compliance rules. "
            "Return your analysis as JSON with keys: violations (list), passed (bool)."
        )

        llm_fn = _llm_fn or load_chat_model_json
        result = await llm_fn(
            system_prompt=DME_COMPLIANCE_RULES,
            user_message=user_message,
        )

        violations = result.get("violations", [])
        passed = result.get("passed", len(violations) == 0)
        high_count = sum(1 for v in violations if v.get("severity") == "HIGH")

        return {
            "passed": passed,
            "violations": violations,
            "high_severity_count": high_count,
            "requires_revision": high_count > 0,
        }

    except Exception as e:
        logger.error("DME compliance check failed: %s", e)
        # Fail safe — flag for manual review
        return {
            "passed": False,
            "violations": [
                {
                    "rule_category": "SYSTEM_ERROR",
                    "severity": "HIGH",
                    "excerpt": "",
                    "explanation": f"Compliance check failed: {e}. Manual review required.",
                }
            ],
            "high_severity_count": 1,
            "requires_revision": True,
        }
