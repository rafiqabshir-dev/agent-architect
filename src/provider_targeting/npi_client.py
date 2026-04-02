"""Async client for the CMS NPI Registry API (v2.1)."""

import logging
import httpx

logger = logging.getLogger(__name__)

NPI_API_URL = "https://npiregistry.cms.hhs.gov/api/"
DEFAULT_VERSION = "2.1"


def _parse_provider(result: dict) -> dict:
    """Extract a flat provider dict from a raw NPI Registry result."""
    basic = result.get("basic", {})
    addresses = result.get("addresses", [])
    taxonomies = result.get("taxonomies", [])

    # Use practice location address (address_purpose == "LOCATION"), fall back to first
    practice_addr = next(
        (a for a in addresses if a.get("address_purpose") == "LOCATION"),
        addresses[0] if addresses else {},
    )

    primary_taxonomy = next(
        (t for t in taxonomies if t.get("primary")),
        taxonomies[0] if taxonomies else {},
    )

    # Build provider name
    if basic.get("organization_name"):
        provider_name = basic["organization_name"]
    else:
        first = basic.get("first_name", "")
        last = basic.get("last_name", "")
        credential = basic.get("credential", "")
        provider_name = f"{first} {last}".strip()
        if credential:
            provider_name = f"{provider_name}, {credential}"

    return {
        "npi": str(result.get("number", "")),
        "provider_name": provider_name,
        "specialty": primary_taxonomy.get("desc", ""),
        "practice_name": basic.get("organization_name", ""),
        "practice_address": practice_addr.get("address_1", ""),
        "city": practice_addr.get("city", ""),
        "state": practice_addr.get("state", ""),
        "zip": practice_addr.get("postal_code", ""),
        "phone": practice_addr.get("telephone_number", ""),
    }


async def search_providers(
    taxonomy_description: str,
    city: str,
    state: str,
    radius: str = "20",
    limit: int = 50,
) -> list[dict]:
    """
    Query NPI Registry for providers matching specialty and location.

    Returns list of dicts with: npi, provider_name, specialty,
    practice_address, city, state, zip, phone.

    Handles pagination if results exceed limit.
    Returns empty list on failure (logs error).
    """
    all_results = []
    skip = 0
    per_page = min(limit, 200)  # NPI API max is 200 per request

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            while len(all_results) < limit:
                params = {
                    "version": DEFAULT_VERSION,
                    "taxonomy_description": taxonomy_description,
                    "city": city,
                    "state": state,
                    "limit": per_page,
                    "skip": skip,
                }
                response = await client.get(NPI_API_URL, params=params)
                response.raise_for_status()
                data = response.json()

                results = data.get("results", [])
                if not results:
                    break

                for r in results:
                    all_results.append(_parse_provider(r))
                    if len(all_results) >= limit:
                        break

                # If fewer results than requested, no more pages
                if len(results) < per_page:
                    break
                skip += per_page

    except Exception as e:
        logger.error("NPI Registry search failed: %s", e)
        return []

    return all_results


async def get_provider_detail(npi: str) -> dict | None:
    """
    Get full details for a single NPI number.

    Returns parsed provider dict or None if not found.
    """
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            params = {"version": DEFAULT_VERSION, "number": npi}
            response = await client.get(NPI_API_URL, params=params)
            response.raise_for_status()
            data = response.json()

            results = data.get("results", [])
            if not results:
                return None

            return _parse_provider(results[0])

    except Exception as e:
        logger.error("NPI Registry detail lookup failed for %s: %s", npi, e)
        return None
