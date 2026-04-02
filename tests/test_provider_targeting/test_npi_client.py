"""Tests for the NPI Registry API client.

Since external HTTP is unavailable in CI, these tests mock the httpx client
while verifying the parsing and error handling logic.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from src.provider_targeting.npi_client import search_providers, get_provider_detail, _parse_provider


# Sample NPI Registry API response
SAMPLE_NPI_RESULT = {
    "number": 1234567890,
    "basic": {
        "first_name": "JOHN",
        "last_name": "DOE",
        "credential": "MD",
        "organization_name": "",
    },
    "addresses": [
        {
            "address_purpose": "LOCATION",
            "address_1": "100 MAIN ST",
            "city": "DES PLAINES",
            "state": "IL",
            "postal_code": "600164321",
            "telephone_number": "847-555-0100",
        }
    ],
    "taxonomies": [
        {"desc": "Pulmonary Disease", "primary": True, "code": "207RP1001X"}
    ],
}

SAMPLE_API_RESPONSE = {
    "result_count": 2,
    "results": [
        SAMPLE_NPI_RESULT,
        {
            "number": 9876543210,
            "basic": {
                "first_name": "JANE",
                "last_name": "SMITH",
                "credential": "DO",
                "organization_name": "",
            },
            "addresses": [
                {
                    "address_purpose": "LOCATION",
                    "address_1": "200 ELM ST",
                    "city": "DES PLAINES",
                    "state": "IL",
                    "postal_code": "600161234",
                    "telephone_number": "847-555-0200",
                }
            ],
            "taxonomies": [
                {"desc": "Pulmonary Disease", "primary": True, "code": "207RP1001X"}
            ],
        },
    ],
}


def _mock_response(data, status=200):
    """Create a mock httpx response."""
    resp = MagicMock()
    resp.status_code = status
    resp.json.return_value = data
    resp.raise_for_status = MagicMock()
    if status >= 400:
        resp.raise_for_status.side_effect = Exception(f"HTTP {status}")
    return resp


@pytest.mark.asyncio
async def test_search_pulmonologists_des_plaines():
    """Search for pulmonologists near Des Plaines, IL. Expect >0 results."""
    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.get = AsyncMock(return_value=_mock_response(SAMPLE_API_RESPONSE))

    with patch("src.provider_targeting.npi_client.httpx.AsyncClient", return_value=mock_client):
        results = await search_providers("Pulmonary Disease", "Des Plaines", "IL")

    assert len(results) > 0
    assert results[0]["city"] == "DES PLAINES"


@pytest.mark.asyncio
async def test_search_returns_required_fields():
    """Each result must have: npi, provider_name, specialty, practice_address."""
    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.get = AsyncMock(return_value=_mock_response(SAMPLE_API_RESPONSE))

    with patch("src.provider_targeting.npi_client.httpx.AsyncClient", return_value=mock_client):
        results = await search_providers("Pulmonary Disease", "Des Plaines", "IL")

    for r in results:
        assert "npi" in r and r["npi"]
        assert "provider_name" in r and r["provider_name"]
        assert "specialty" in r and r["specialty"]
        assert "practice_address" in r


@pytest.mark.asyncio
async def test_search_empty_results():
    """Search for a nonsense specialty. Expect empty list, no crash."""
    empty_response = {"result_count": 0, "results": []}
    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.get = AsyncMock(return_value=_mock_response(empty_response))

    with patch("src.provider_targeting.npi_client.httpx.AsyncClient", return_value=mock_client):
        results = await search_providers("Nonsense Specialty XYZ123", "Nowhere", "ZZ")

    assert results == []


@pytest.mark.asyncio
async def test_get_provider_detail():
    """Get detail for a known NPI. Expect non-None result."""
    detail_response = {"result_count": 1, "results": [SAMPLE_NPI_RESULT]}
    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.get = AsyncMock(return_value=_mock_response(detail_response))

    with patch("src.provider_targeting.npi_client.httpx.AsyncClient", return_value=mock_client):
        result = await get_provider_detail("1234567890")

    assert result is not None
    assert result["npi"] == "1234567890"
    assert result["provider_name"] == "JOHN DOE, MD"


@pytest.mark.asyncio
async def test_get_provider_detail_invalid_npi():
    """Get detail for invalid NPI. Expect None, no crash."""
    empty_response = {"result_count": 0, "results": []}
    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.get = AsyncMock(return_value=_mock_response(empty_response))

    with patch("src.provider_targeting.npi_client.httpx.AsyncClient", return_value=mock_client):
        result = await get_provider_detail("0000000000")

    assert result is None


def test_parse_provider_organization():
    """Test parsing when provider is an organization."""
    result = {
        "number": 1111111111,
        "basic": {"organization_name": "Northwest Pulmonary Associates"},
        "addresses": [
            {
                "address_purpose": "LOCATION",
                "address_1": "300 OAK AVE",
                "city": "CHICAGO",
                "state": "IL",
                "postal_code": "606011234",
                "telephone_number": "312-555-0300",
            }
        ],
        "taxonomies": [{"desc": "Pulmonary Disease", "primary": True}],
    }
    parsed = _parse_provider(result)
    assert parsed["provider_name"] == "Northwest Pulmonary Associates"
    assert parsed["practice_name"] == "Northwest Pulmonary Associates"


@pytest.mark.asyncio
async def test_search_handles_api_error():
    """API error returns empty list, no crash."""
    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.get = AsyncMock(side_effect=Exception("Connection failed"))

    with patch("src.provider_targeting.npi_client.httpx.AsyncClient", return_value=mock_client):
        results = await search_providers("Pulmonary Disease", "Des Plaines", "IL")

    assert results == []
