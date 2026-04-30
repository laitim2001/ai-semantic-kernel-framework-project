"""Unit tests for D365 OData Query Builder and helper functions.

Tests cover:
    - ODataQueryBuilder fluent API (select, filter, top, skip, orderby,
      expand, count, build, method chaining)
    - _resolve_entity_set entity name pluralization and lookup
    - _extract_record_id_from_header GUID extraction from OData-EntityId
    - _parse_error_response D365 error JSON parsing

Sprint 129 — D365 MCP Server test suite
"""

import json

import httpx
import pytest
from unittest.mock import MagicMock

from src.integrations.mcp.servers.d365.client import (
    D365ValidationError,
    ENTITY_SET_MAP,
    ODataQueryBuilder,
    _extract_record_id_from_header,
    _parse_error_response,
    _resolve_entity_set,
)


# ---------------------------------------------------------------------------
# TestODataQueryBuilder
# ---------------------------------------------------------------------------


class TestODataQueryBuilder:
    """Tests for the ODataQueryBuilder fluent interface."""

    def test_empty_build(self) -> None:
        """Build with no clauses returns an empty dict."""
        builder = ODataQueryBuilder()
        result = builder.build()

        assert result == {}

    def test_select_single_field(self) -> None:
        """Select with one field produces correct $select value."""
        result = ODataQueryBuilder().select("name").build()

        assert result == {"$select": "name"}

    def test_select_multiple_fields(self) -> None:
        """Select with multiple fields joins them with commas."""
        result = ODataQueryBuilder().select("name", "accountnumber").build()

        assert result == {"$select": "name,accountnumber"}

    def test_filter(self) -> None:
        """Filter sets the $filter query parameter."""
        result = ODataQueryBuilder().filter("statecode eq 0").build()

        assert result == {"$filter": "statecode eq 0"}

    def test_top(self) -> None:
        """Top sets the $top parameter as a string."""
        result = ODataQueryBuilder().top(10).build()

        assert result == {"$top": "10"}

    def test_top_invalid_raises(self) -> None:
        """Top with count < 1 raises D365ValidationError."""
        with pytest.raises(D365ValidationError, match="positive integer"):
            ODataQueryBuilder().top(0)

    def test_top_negative_raises(self) -> None:
        """Top with negative count also raises D365ValidationError."""
        with pytest.raises(D365ValidationError):
            ODataQueryBuilder().top(-5)

    def test_skip(self) -> None:
        """Skip sets the $skip parameter as a string."""
        result = ODataQueryBuilder().skip(5).build()

        assert result == {"$skip": "5"}

    def test_skip_zero_allowed(self) -> None:
        """Skip with count=0 is valid (non-negative)."""
        result = ODataQueryBuilder().skip(0).build()

        assert result == {"$skip": "0"}

    def test_skip_negative_raises(self) -> None:
        """Skip with negative count raises D365ValidationError."""
        with pytest.raises(D365ValidationError, match="non-negative"):
            ODataQueryBuilder().skip(-1)

    def test_orderby_asc(self) -> None:
        """Orderby defaults to ascending."""
        result = ODataQueryBuilder().orderby("name").build()

        assert result == {"$orderby": "name asc"}

    def test_orderby_desc(self) -> None:
        """Orderby with desc=True produces descending clause."""
        result = ODataQueryBuilder().orderby("name", desc=True).build()

        assert result == {"$orderby": "name desc"}

    def test_orderby_multiple(self) -> None:
        """Multiple orderby calls accumulate clauses separated by commas."""
        result = (
            ODataQueryBuilder()
            .orderby("name")
            .orderby("createdon", desc=True)
            .build()
        )

        assert result == {"$orderby": "name asc,createdon desc"}

    def test_expand(self) -> None:
        """Expand sets the $expand parameter."""
        result = ODataQueryBuilder().expand("contact_customer_accounts").build()

        assert result == {"$expand": "contact_customer_accounts"}

    def test_expand_multiple(self) -> None:
        """Expand with multiple navigations joins them with commas."""
        result = (
            ODataQueryBuilder()
            .expand("contact_customer_accounts", "opportunity_parent_account")
            .build()
        )

        assert result == {
            "$expand": "contact_customer_accounts,opportunity_parent_account"
        }

    def test_count(self) -> None:
        """Count sets the $count parameter to 'true'."""
        result = ODataQueryBuilder().count().build()

        assert result == {"$count": "true"}

    def test_combined_query(self) -> None:
        """All clauses can be combined in a single query."""
        result = (
            ODataQueryBuilder()
            .select("name", "accountnumber")
            .filter("statecode eq 0")
            .top(10)
            .skip(20)
            .orderby("name")
            .expand("contact_customer_accounts")
            .count()
            .build()
        )

        assert result == {
            "$select": "name,accountnumber",
            "$filter": "statecode eq 0",
            "$top": "10",
            "$skip": "20",
            "$orderby": "name asc",
            "$expand": "contact_customer_accounts",
            "$count": "true",
        }

    def test_method_chaining(self) -> None:
        """Each method returns the builder instance for chaining."""
        builder = ODataQueryBuilder()

        assert builder.select("name") is builder
        assert builder.filter("x eq 1") is builder
        assert builder.top(5) is builder
        assert builder.skip(0) is builder
        assert builder.orderby("name") is builder
        assert builder.expand("nav") is builder
        assert builder.count() is builder


# ---------------------------------------------------------------------------
# TestResolveEntitySet
# ---------------------------------------------------------------------------


class TestResolveEntitySet:
    """Tests for the _resolve_entity_set helper function."""

    def test_known_entity_account(self) -> None:
        """Known entity 'account' maps to 'accounts'."""
        assert _resolve_entity_set("account") == "accounts"

    def test_known_entity_incident(self) -> None:
        """Known entity 'incident' maps to 'incidents'."""
        assert _resolve_entity_set("incident") == "incidents"

    def test_known_entity_case_insensitive(self) -> None:
        """Entity name lookup is case-insensitive."""
        assert _resolve_entity_set("Account") == "accounts"
        assert _resolve_entity_set("INCIDENT") == "incidents"

    def test_unknown_entity_simple_plural(self) -> None:
        """Unknown entity gets simple 's' suffix pluralization."""
        assert _resolve_entity_set("widget") == "widgets"

    def test_unknown_entity_es_plural(self) -> None:
        """Unknown entity ending with s/x/z/sh/ch gets 'es' suffix."""
        # Ends with 's'
        assert _resolve_entity_set("address") == "addresses"
        # Ends with 'x'
        assert _resolve_entity_set("box") == "boxes"
        # Ends with 'sh'
        assert _resolve_entity_set("cash") == "cashes"
        # Ends with 'ch'
        assert _resolve_entity_set("batch") == "batches"

    def test_entity_set_map_completeness(self) -> None:
        """ENTITY_SET_MAP contains expected standard D365 entities."""
        expected_keys = [
            "account", "contact", "incident", "systemuser",
            "team", "businessunit", "opportunity", "lead",
        ]
        for key in expected_keys:
            assert key in ENTITY_SET_MAP, f"Missing entity: {key}"


# ---------------------------------------------------------------------------
# TestExtractRecordId
# ---------------------------------------------------------------------------


class TestExtractRecordId:
    """Tests for the _extract_record_id_from_header helper function."""

    def test_valid_header(self) -> None:
        """Extracts GUID from a valid OData-EntityId header."""
        header = (
            "https://org.crm.dynamics.com/api/data/v9.2/"
            "accounts(a1b2c3d4-e5f6-7890-abcd-ef1234567890)"
        )
        result = _extract_record_id_from_header(header)

        assert result == "a1b2c3d4-e5f6-7890-abcd-ef1234567890"

    def test_invalid_header(self) -> None:
        """Returns None when the header does not contain a GUID."""
        result = _extract_record_id_from_header("not-a-valid-header")

        assert result is None

    def test_malformed_guid(self) -> None:
        """Returns None when the parenthesized value is not a valid GUID."""
        header = "https://org.crm.dynamics.com/api/data/v9.2/accounts(not-a-guid)"
        result = _extract_record_id_from_header(header)

        assert result is None

    def test_empty_string(self) -> None:
        """Returns None for an empty string input."""
        result = _extract_record_id_from_header("")

        assert result is None


# ---------------------------------------------------------------------------
# TestParseErrorResponse
# ---------------------------------------------------------------------------


class TestParseErrorResponse:
    """Tests for the _parse_error_response helper function."""

    def test_standard_error(self) -> None:
        """Parses standard D365 error JSON format."""
        error_body = {
            "error": {
                "code": "0x80040217",
                "message": "Record not found",
            }
        }
        response = MagicMock(spec=httpx.Response)
        response.json.return_value = error_body
        response.text = json.dumps(error_body)

        result = _parse_error_response(response)

        assert "[0x80040217]" in result
        assert "Record not found" in result

    def test_missing_error_key(self) -> None:
        """Falls back gracefully when 'error' key is missing."""
        response = MagicMock(spec=httpx.Response)
        response.json.return_value = {"unexpected": "format"}
        response.text = '{"unexpected": "format"}'

        result = _parse_error_response(response)

        # Should still produce a string (falls back to Unknown code
        # and response.text for message)
        assert isinstance(result, str)
        assert "[Unknown]" in result

    def test_json_parse_failure(self) -> None:
        """Falls back to response text when JSON parsing fails."""
        response = MagicMock(spec=httpx.Response)
        response.json.side_effect = ValueError("No JSON")
        response.text = "Bad Gateway"
        response.status_code = 502

        result = _parse_error_response(response)

        assert result == "Bad Gateway"

    def test_json_parse_failure_empty_text(self) -> None:
        """Falls back to HTTP status code when text is also empty."""
        response = MagicMock(spec=httpx.Response)
        response.json.side_effect = ValueError("No JSON")
        response.text = ""
        response.status_code = 500

        result = _parse_error_response(response)

        assert "500" in result
