"""Orchestrator for provider discovery and outreach batch selection."""

import logging
from src.provider_targeting.npi_client import search_providers
from src.provider_targeting.provider_store import (
    upsert_provider,
    get_prospects_for_client,
    flag_existing_partners,
    get_hot_leads,
)

logger = logging.getLogger(__name__)


async def discover_providers(
    client_id: str,
    specialties: list[str],
    city: str,
    state: str,
    radius: str = "20",
    existing_partner_npis: list[str] | None = None,
    db=None,
) -> dict:
    """
    Full discovery flow:
    1. Query NPI Registry for each specialty
    2. Deduplicate across specialties
    3. Flag existing partners
    4. Store all in provider_prospects collection
    5. Return summary: {total_found, new_prospects, existing_partners, by_specialty: {}}
    """
    if existing_partner_npis is None:
        existing_partner_npis = []

    seen_npis: set[str] = set()
    by_specialty: dict[str, int] = {}
    total_found = 0

    try:
        for specialty in specialties:
            results = await search_providers(
                taxonomy_description=specialty,
                city=city,
                state=state,
                radius=radius,
            )
            by_specialty[specialty] = 0

            for provider in results:
                npi = provider.get("npi", "")
                if not npi or npi in seen_npis:
                    continue
                seen_npis.add(npi)
                total_found += 1
                by_specialty[specialty] += 1

                await upsert_provider(client_id, provider, db=db)

        # Flag existing partners
        existing_count = 0
        if existing_partner_npis:
            existing_count = await flag_existing_partners(
                client_id, existing_partner_npis, db=db
            )

        return {
            "total_found": total_found,
            "new_prospects": total_found - existing_count,
            "existing_partners": existing_count,
            "by_specialty": by_specialty,
        }

    except Exception as e:
        logger.error("discover_providers failed: %s", e)
        return {
            "total_found": 0,
            "new_prospects": 0,
            "existing_partners": 0,
            "by_specialty": {},
        }


async def get_outreach_batch(
    client_id: str,
    batch_size: int = 5,
    prioritize_by: str = "cms_volume",
    db=None,
) -> list[dict]:
    """
    Get the next batch of providers to generate outreach for.

    Priority: hot leads first, then new prospects sorted by prioritize_by.
    Excludes existing partners and providers with status "inactive".
    """
    try:
        batch: list[dict] = []

        # Hot leads first
        hot = await get_hot_leads(client_id, db=db)
        for lead in hot:
            if lead.get("status") != "inactive" and not lead.get("is_existing_partner"):
                batch.append(lead)
                if len(batch) >= batch_size:
                    return batch

        # Fill remaining with new prospects
        remaining = batch_size - len(batch)
        if remaining > 0:
            prospects = await get_prospects_for_client(
                client_id,
                status="new",
                exclude_existing_partners=True,
                limit=remaining * 2,  # fetch extra to filter
                db=db,
            )
            # Sort by priority field
            sort_key = prioritize_by if prioritize_by in ("cms_volume", "distance_miles") else "cms_volume"

            def sort_value(p):
                val = p.get(sort_key)
                if val is None:
                    return 0
                return val

            prospects.sort(key=sort_value, reverse=(sort_key == "cms_volume"))

            for p in prospects:
                if p.get("status") != "inactive" and not p.get("is_existing_partner"):
                    # Avoid duplicates with hot leads
                    if not any(b.get("npi") == p.get("npi") for b in batch):
                        batch.append(p)
                        if len(batch) >= batch_size:
                            break

        return batch

    except Exception as e:
        logger.error("get_outreach_batch failed: %s", e)
        return []
