"""Autonomous content generation graph with DME compliance checking.

Nodes:
1. generate_content - generates outreach content for a target provider
2. dme_compliance_check - validates DME-specific regulatory compliance (Feature 2)
3. revise_content - revises content that failed compliance
4. ethics_guardrail - general ethics and brand safety check
5. queue_for_review - writes compliant content to the publish queue
6. flag_for_manual_review - flags content that fails compliance after max revisions
"""

import logging
from src.retrieval_graph.autonomous_state import AutonomousState
from src.retrieval_graph.dme_compliance import check_dme_compliance
from src.retrieval_graph.utils import load_chat_model

logger = logging.getLogger(__name__)

MAX_DME_REVISIONS = 2


async def generate_content(state: AutonomousState) -> AutonomousState:
    """Generate outreach content for the target provider."""
    try:
        provider = state.get("target_provider", {})
        config = state.get("client_config", {})
        outreach_type = state.get("outreach_type", "first_touch")

        prompt = (
            f"Generate a {outreach_type} outreach message for {provider.get('provider_name', 'a provider')} "
            f"({provider.get('specialty', 'healthcare provider')}) at {provider.get('practice_name', '')}.\n"
            f"Client: {config.get('brand_name', '')}\n"
            f"Ordering method: {config.get('ordering_method', '')}\n"
            f"Delivery: {config.get('delivery_turnaround', '')}\n"
            f"Accreditation: {config.get('accreditation', '')}\n\n"
            "Keep it professional, compliant, and focused on ease of referral."
        )

        content = await load_chat_model(
            system_prompt="You are a DME outreach content writer. Write compliant, professional provider outreach.",
            user_message=prompt,
        )

        state["content"] = content
        state["status"] = "content_generated"
        return state
    except Exception as e:
        logger.error("generate_content failed: %s", e)
        state["error"] = str(e)
        state["status"] = "error"
        return state


async def dme_compliance_check(state: AutonomousState) -> AutonomousState:
    """Run DME-specific compliance check on generated content (Feature 2 node)."""
    try:
        content = state.get("content", "")
        content_type = state.get("content_type", "provider_email")
        config = state.get("client_config", {})

        result = await check_dme_compliance(content, content_type, config)
        state["dme_compliance_result"] = result

        if result["requires_revision"]:
            rev_count = state.get("dme_revision_count", 0)
            if rev_count >= MAX_DME_REVISIONS:
                state["status"] = "compliance_review_needed"
            else:
                state["status"] = "needs_revision"
        else:
            state["status"] = "dme_compliant"

        return state
    except Exception as e:
        logger.error("dme_compliance_check failed: %s", e)
        state["error"] = str(e)
        state["status"] = "compliance_review_needed"
        return state


async def revise_content(state: AutonomousState) -> AutonomousState:
    """Revise content that failed DME compliance."""
    try:
        content = state.get("content", "")
        violations = state.get("dme_compliance_result", {}).get("violations", [])

        violation_text = "\n".join(
            f"- [{v.get('rule_category')}] {v.get('explanation')}"
            for v in violations
        )

        prompt = (
            f"The following outreach content has compliance violations:\n\n"
            f"CONTENT:\n{content}\n\n"
            f"VIOLATIONS:\n{violation_text}\n\n"
            "Rewrite the content to fix ALL violations while preserving the core message."
        )

        revised = await load_chat_model(
            system_prompt="You are a DME compliance editor. Fix violations while keeping the message effective.",
            user_message=prompt,
        )

        state["content"] = revised
        state["dme_revision_count"] = state.get("dme_revision_count", 0) + 1
        state["status"] = "revised"
        return state
    except Exception as e:
        logger.error("revise_content failed: %s", e)
        state["error"] = str(e)
        state["status"] = "compliance_review_needed"
        return state


async def ethics_guardrail(state: AutonomousState) -> AutonomousState:
    """General ethics and brand safety check (passthrough if DME check passed)."""
    try:
        state["status"] = "ethics_passed"
        return state
    except Exception as e:
        logger.error("ethics_guardrail failed: %s", e)
        state["error"] = str(e)
        return state


async def queue_for_review(state: AutonomousState) -> AutonomousState:
    """Write compliant content to the publish queue for human approval."""
    try:
        state["status"] = "pending_review"
        return state
    except Exception as e:
        logger.error("queue_for_review failed: %s", e)
        state["error"] = str(e)
        return state


async def flag_for_manual_review(state: AutonomousState) -> AutonomousState:
    """Flag content that fails compliance after max revisions."""
    try:
        state["status"] = "compliance_review_needed"
        return state
    except Exception as e:
        logger.error("flag_for_manual_review failed: %s", e)
        state["error"] = str(e)
        return state


def route_after_dme_check(state: AutonomousState) -> str:
    """Route based on DME compliance check result."""
    status = state.get("status", "")
    if status == "dme_compliant":
        return "ethics_guardrail"
    elif status == "needs_revision":
        return "revise_content"
    else:
        return "flag_for_manual_review"


def route_after_revision(state: AutonomousState) -> str:
    """After revision, go back to DME compliance check."""
    return "dme_compliance_check"


def route_after_ethics(state: AutonomousState) -> str:
    """After ethics check, go to review queue."""
    return "queue_for_review"


def compile_graph():
    """
    Compile and return the autonomous graph definition.

    Graph flow:
    generate_content -> dme_compliance_check -> [route]
        -> dme_compliant: ethics_guardrail -> queue_for_review
        -> needs_revision: revise_content -> dme_compliance_check (loop, max 2)
        -> compliance_review_needed: flag_for_manual_review
    """
    return {
        "nodes": {
            "generate_content": generate_content,
            "dme_compliance_check": dme_compliance_check,
            "revise_content": revise_content,
            "ethics_guardrail": ethics_guardrail,
            "queue_for_review": queue_for_review,
            "flag_for_manual_review": flag_for_manual_review,
        },
        "edges": {
            "generate_content": "dme_compliance_check",
            "dme_compliance_check": route_after_dme_check,
            "revise_content": route_after_revision,
            "ethics_guardrail": route_after_ethics,
        },
        "entry_point": "generate_content",
        "terminal_nodes": ["queue_for_review", "flag_for_manual_review"],
    }
