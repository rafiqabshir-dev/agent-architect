"""Full outreach pipeline wiring Features 1, 2, and 3 together."""

import logging
from datetime import datetime, timezone

from src.provider_targeting.targeting_service import get_outreach_batch
from src.provider_targeting.provider_store import add_outreach_record
from src.retrieval_graph.outreach_composer import compose_outreach
from src.retrieval_graph.dme_compliance import check_dme_compliance

logger = logging.getLogger(__name__)

MAX_REVISIONS = 2


async def _write_to_publish_queue(
    item: dict,
    client_id: str,
    db=None,
) -> str:
    """Write a composed outreach item to the publish_queue collection."""
    try:
        if db is not None:
            col = db["publish_queue"]
        else:
            from src.retrieval_graph.db import get_collection
            col = get_collection("publish_queue")

        doc = {
            "client_id": client_id,
            "content_type": item.get("content_type", "provider_email"),
            "content": item.get("content", ""),
            "status": item.get("status", "pending_review"),
            "publish_results": [],
            # New outreach fields
            "recipient_npi": item.get("recipient_npi"),
            "recipient_name": item.get("recipient_name"),
            "recipient_practice": item.get("recipient_practice"),
            "recipient_address": item.get("recipient_address"),
            "recipient_channel": item.get("recipient_channel"),
            "recipient_contact": item.get("recipient_contact"),
            "outreach_type": item.get("outreach_type"),
            "subject_line": item.get("subject_line"),
            "talking_points": item.get("talking_points"),
            "cms_volume": item.get("cms_volume"),
            "distance_miles": item.get("distance_miles"),
            "created_at": datetime.now(timezone.utc),
        }

        result = await col.insert_one(doc)
        return str(result.inserted_id)

    except Exception as e:
        logger.error("_write_to_publish_queue failed: %s", e)
        raise


async def run_outreach_cycle(
    client_id: str,
    client_config: dict,
    batch_size: int = 5,
    db=None,
    _llm_fn=None,
    _compliance_fn=None,
) -> dict:
    """
    Full outreach cycle:
    1. Get next batch of providers from provider_prospects (Feature 1)
    2. For each provider, compose tailored outreach (Feature 3)
    3. Run DME compliance check on each piece (Feature 2)
    4. Write compliant, paired items to publish_queue for human approval
    5. Return summary: {composed: int, passed_compliance: int, queued: int, failed: int}

    Items that fail compliance after 2 revision attempts are flagged for
    manual review with status 'compliance_review_needed'.
    """
    summary = {"composed": 0, "passed_compliance": 0, "queued": 0, "failed": 0}

    try:
        # Step 1: Get batch of providers
        batch = await get_outreach_batch(client_id, batch_size=batch_size, db=db)
        if not batch:
            logger.info("No providers in outreach batch for client %s", client_id)
            return summary

        for provider in batch:
            try:
                # Step 2: Compose outreach
                outreach = await compose_outreach(
                    provider, client_config, _llm_fn=_llm_fn
                )
                summary["composed"] += 1
                content = outreach["content"]

                # Step 3: Compliance check loop
                passed = False
                revision_count = 0
                compliance_fn = _compliance_fn or check_dme_compliance

                for attempt in range(MAX_REVISIONS + 1):
                    result = await compliance_fn(
                        content, outreach["content_type"], client_config
                    )

                    if not result["requires_revision"]:
                        passed = True
                        break

                    revision_count += 1
                    if revision_count > MAX_REVISIONS:
                        break

                    # Revise content (simplified — recompose)
                    outreach = await compose_outreach(
                        provider, client_config, _llm_fn=_llm_fn
                    )
                    content = outreach["content"]

                # Step 4: Write to queue
                status = "pending_review" if passed else "compliance_review_needed"
                if passed:
                    summary["passed_compliance"] += 1

                queue_item = {
                    "content_type": outreach["content_type"],
                    "content": content,
                    "status": status,
                    "recipient_npi": provider.get("npi"),
                    "recipient_name": provider.get("provider_name"),
                    "recipient_practice": provider.get("practice_name"),
                    "recipient_address": provider.get("practice_address"),
                    "recipient_channel": outreach["channel"],
                    "recipient_contact": provider.get("contact_email") or provider.get("contact_fax"),
                    "outreach_type": "first_touch",
                    "subject_line": outreach.get("subject_line"),
                    "talking_points": outreach.get("talking_points"),
                    "cms_volume": provider.get("cms_volume"),
                    "distance_miles": provider.get("distance_miles"),
                }

                await _write_to_publish_queue(queue_item, client_id, db=db)
                summary["queued"] += 1

                # Record outreach on the provider
                await add_outreach_record(
                    client_id,
                    provider.get("npi", ""),
                    {
                        "channel": outreach["channel"],
                        "content_id": queue_item.get("recipient_npi", ""),
                        "action": "composed",
                        "status": status,
                    },
                    db=db if db else None,
                )

            except Exception as e:
                logger.error(
                    "Outreach cycle failed for provider %s: %s",
                    provider.get("npi", "unknown"),
                    e,
                )
                summary["failed"] += 1

    except Exception as e:
        logger.error("run_outreach_cycle failed: %s", e)

    return summary
