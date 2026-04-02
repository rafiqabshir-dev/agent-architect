"""Outreach content composer for provider targeting campaigns."""

import logging
from src.retrieval_graph.utils import load_chat_model

logger = logging.getLogger(__name__)

OUTREACH_TEMPLATES = {
    "provider_email": {
        "pulmonologist": "Lead with: ordering method, delivery turnaround, accreditation. Tone: clinical peer.",
        "internal_medicine": "Lead with: ordering method, delivery turnaround, breadth of equipment. Tone: practical.",
        "discharge_planner": "Lead with: delivery speed, CMN turnaround, zero admin burden. Tone: operational.",
        "nursing_home_don": "Lead with: equipment catalog, reorder process, reliability. Tone: account management.",
    },
    "fax_one_pager": {
        "discharge_planner": "One page. Equipment list, ordering method, delivery radius, direct phone number, accreditation.",
        "nursing_home_don": "One page. Equipment catalog summary, reorder process, direct phone number.",
    },
}

SPECIALTY_TO_ROLE = {
    "Pulmonary Disease": "pulmonologist",
    "Internal Medicine": "internal_medicine",
    "Family Medicine": "internal_medicine",
    "Discharge Planner": "discharge_planner",
    "Nursing Home DON": "nursing_home_don",
}


def _get_template(content_type: str, specialty: str) -> str:
    """Get the appropriate template for a content type and specialty."""
    role = SPECIALTY_TO_ROLE.get(specialty, "internal_medicine")
    templates = OUTREACH_TEMPLATES.get(content_type, OUTREACH_TEMPLATES["provider_email"])
    return templates.get(role, templates.get("internal_medicine", "Professional tone. Lead with ordering method."))


def _determine_channel(provider: dict) -> str:
    """Determine the best outreach channel for a provider."""
    preferred = provider.get("preferred_channel")
    if preferred:
        return preferred
    if provider.get("contact_email"):
        return "email"
    if provider.get("contact_fax"):
        return "fax"
    return "email"


def _determine_content_type(channel: str) -> str:
    """Map channel to content type."""
    if channel == "fax":
        return "fax_one_pager"
    return "provider_email"


async def compose_outreach(
    provider: dict,
    client_config: dict,
    outreach_type: str = "first_touch",
    _llm_fn=None,
) -> dict:
    """
    Generate tailored outreach content for a specific provider.

    Uses client's ordering method (ePrescribing platform name, fax number, or phone)
    to frame the ease-of-referral message.

    Returns:
        {
            "content": str,          # the outreach message
            "content_type": str,     # "provider_email" | "fax_one_pager"
            "channel": str,          # "email" | "fax" | "print_dropoff"
            "subject_line": str | None,  # for emails
            "talking_points": list[str], # for visit brief
        }
    """
    try:
        channel = _determine_channel(provider)
        content_type = _determine_content_type(channel)
        specialty = provider.get("specialty", "Internal Medicine")
        template_guidance = _get_template(content_type, specialty)

        brand = client_config.get("brand_name", "")
        ordering = client_config.get("ordering_method", "")
        delivery = client_config.get("delivery_turnaround", "")
        accreditation = client_config.get("accreditation", "")
        fax_number = client_config.get("fax_number", "")
        cmn_turnaround = client_config.get("cmn_turnaround", "")
        phone = client_config.get("phone", "")

        prompt = (
            f"Write a {outreach_type} outreach message.\n\n"
            f"RECIPIENT:\n"
            f"- Name: {provider.get('provider_name', '')}\n"
            f"- Specialty: {specialty}\n"
            f"- Practice: {provider.get('practice_name', '')}\n\n"
            f"CLIENT (DME Supplier):\n"
            f"- Brand: {brand}\n"
            f"- Ordering method: {ordering}\n"
            f"- Delivery turnaround: {delivery}\n"
            f"- Accreditation: {accreditation}\n"
            f"- Fax: {fax_number}\n"
            f"- CMN turnaround: {cmn_turnaround}\n"
            f"- Phone: {phone}\n\n"
            f"TEMPLATE GUIDANCE: {template_guidance}\n\n"
            f"CHANNEL: {channel}\n"
            f"CONTENT TYPE: {content_type}\n\n"
            "RULES:\n"
            "- Keep it concise and professional\n"
            "- No superlatives or unsubstantiated claims\n"
            "- No kickback implications\n"
            "- Lead with how to order and delivery speed\n"
            "- If ePrescribing platform is used, mention it prominently\n"
            "- End with clear contact information\n"
        )

        llm_fn = _llm_fn or load_chat_model
        content = await llm_fn(
            system_prompt="You are a compliant DME outreach writer. Write professional, regulatory-compliant provider outreach.",
            user_message=prompt,
        )

        # Generate subject line for emails
        subject_line = None
        if channel == "email":
            subject_line = f"{brand} — Streamlined DME Ordering for Your Patients"

        # Generate talking points
        talking_points = [
            f"Ordering via {ordering}" if ordering else "Easy ordering process",
            f"{delivery} delivery" if delivery else "Fast delivery",
            f"{accreditation} accredited" if accreditation else "Fully accredited",
        ]

        return {
            "content": content,
            "content_type": content_type,
            "channel": channel,
            "subject_line": subject_line,
            "talking_points": talking_points,
        }

    except Exception as e:
        logger.error("compose_outreach failed: %s", e)
        raise


async def compose_batch(
    providers: list[dict],
    client_config: dict,
    outreach_type: str = "first_touch",
    _llm_fn=None,
) -> list[dict]:
    """
    Generate outreach for a batch of providers.

    Each item in the returned list contains the outreach content + provider pairing.
    """
    results = []
    for provider in providers:
        try:
            outreach = await compose_outreach(
                provider, client_config, outreach_type, _llm_fn=_llm_fn
            )
            outreach["provider"] = provider
            results.append(outreach)
        except Exception as e:
            logger.error(
                "compose_batch: failed for provider %s: %s",
                provider.get("npi", "unknown"),
                e,
            )
    return results
