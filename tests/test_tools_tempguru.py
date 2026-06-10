"""Unit tests for TempGuruToolSpec.

All HTTP is mocked at the ``urllib`` boundary (``tempguru.client.urlopen``)
or replaced with an injected mock client — no test ever reaches the live
TempGuru API. In particular, ``submit_event_staffing_quote_request`` writes
a real CRM lead in production, so its tests assert the request is *built*
correctly without ever sending it.
"""

import io
import json
from unittest.mock import MagicMock, Mock, patch
from urllib.error import HTTPError

import pytest
from llama_index.core.tools.tool_spec.base import BaseToolSpec
from llama_index.tools.tempguru import TempGuru, TempGuruError, TempGuruToolSpec

ALL_TOOLS = [
    "event_staffing_cities",
    "event_staffing_roles",
    "event_staffing_availability",
    "event_staffing_pricing",
    "event_staffing_state_compliance",
    "submit_event_staffing_quote_request",
]

QUOTE_KWARGS = {
    "contact_name": "Test Person",
    "contact_email": "test@example.com",
    "company": "Example Co",
    "event_name": "Example Expo",
    "event_type": "trade-show",
    "city": "Boston",
    "event_dates": "June 15-17, 2026",
    "roles": [{"role": "brand-ambassadors", "headcount": 10}],
}


def _fake_response(payload):
    """Build a context-manager mock mimicking urlopen's response object."""
    resp = MagicMock()
    resp.read.return_value = json.dumps(payload).encode("utf-8")
    resp.__enter__.return_value = resp
    resp.__exit__.return_value = False
    return resp


# --- Spec surface -----------------------------------------------------------


def test_class():
    names_of_base_classes = [b.__name__ for b in TempGuruToolSpec.__mro__]
    assert BaseToolSpec.__name__ in names_of_base_classes


def test_spec_functions():
    assert TempGuruToolSpec(client=Mock()).spec_functions == ALL_TOOLS


def test_to_tool_list_exposes_all_tools():
    tools = TempGuruToolSpec(client=Mock()).to_tool_list()
    assert sorted(t.metadata.name for t in tools) == sorted(ALL_TOOLS)


def test_read_only_mode_drops_quote_submission():
    spec = TempGuruToolSpec(client=Mock(), include_quote_submission=False)
    tools = spec.to_tool_list()
    names = [t.metadata.name for t in tools]
    assert len(names) == 5
    assert "submit_event_staffing_quote_request" not in names


def test_read_only_mode_does_not_mutate_other_instances():
    TempGuruToolSpec(client=Mock(), include_quote_submission=False)
    fresh = TempGuruToolSpec(client=Mock())
    assert fresh.spec_functions == ALL_TOOLS


def test_tool_descriptions_come_from_docstrings():
    tools = TempGuruToolSpec(client=Mock()).to_tool_list()
    by_name = {t.metadata.name: t.metadata.description for t in tools}
    assert all(desc and desc.strip() for desc in by_name.values())
    # The write tool must carry its opt-in guardrail into agent prompts.
    assert "OPT-IN WRITE" in by_name["submit_event_staffing_quote_request"]


# --- Argument forwarding to the client --------------------------------------


def test_cities_forwards_filters():
    client = Mock()
    spec = TempGuruToolSpec(client=client)
    spec.event_staffing_cities(state="MA", tier="hub")
    client.cities.assert_called_once_with(state="MA", tier="hub")


def test_cities_maps_empty_strings_to_none():
    client = Mock()
    TempGuruToolSpec(client=client).event_staffing_cities()
    client.cities.assert_called_once_with(state=None, tier=None)


def test_roles_forwards():
    client = Mock()
    TempGuruToolSpec(client=client).event_staffing_roles()
    client.roles.assert_called_once_with()


def test_availability_maps_zero_headcount_to_none():
    client = Mock()
    spec = TempGuruToolSpec(client=client)
    spec.event_staffing_availability(city="Boston", date="2026-08-01")
    client.availability.assert_called_once_with(
        city="Boston", date="2026-08-01", role=None, headcount=None
    )


def test_availability_forwards_all_params():
    client = Mock()
    spec = TempGuruToolSpec(client=client)
    spec.event_staffing_availability(
        city="Boston", date="2026-08-01", role="ushers", headcount=12
    )
    client.availability.assert_called_once_with(
        city="Boston", date="2026-08-01", role="ushers", headcount=12
    )


def test_pricing_forwards():
    client = Mock()
    spec = TempGuruToolSpec(client=client)
    spec.event_staffing_pricing(role="brand-ambassadors", city="Boston")
    client.pricing.assert_called_once_with(role="brand-ambassadors", city="Boston")


def test_compliance_forwards():
    client = Mock()
    TempGuruToolSpec(client=client).event_staffing_state_compliance(state="CA")
    client.compliance.assert_called_once_with(state="CA")


def test_quote_submission_forwards_optional_fields_as_none():
    client = Mock()
    spec = TempGuruToolSpec(client=client)
    spec.submit_event_staffing_quote_request(**QUOTE_KWARGS)
    client.request_quote.assert_called_once_with(
        budget_range=None,
        attire=None,
        special_requirements=None,
        compliance_notes=None,
        **QUOTE_KWARGS,
    )


# --- HTTP layer (urllib mocked, nothing leaves the process) -----------------


@patch("tempguru.client.urlopen")
def test_cities_builds_request_url(mock_urlopen):
    payload = {"cities": [{"city": "Boston", "state": "MA"}]}
    mock_urlopen.return_value = _fake_response(payload)

    result = TempGuruToolSpec().event_staffing_cities(state="MA")

    assert result == payload
    request = mock_urlopen.call_args.args[0]
    assert request.full_url == "https://mcp.tempguru.co/api/v1/cities?state=MA"


@patch("tempguru.client.urlopen")
def test_pricing_url_encodes_query(mock_urlopen):
    mock_urlopen.return_value = _fake_response({"hourly_range_low": 56})

    spec = TempGuruToolSpec()
    spec.event_staffing_pricing(role="brand-ambassadors", city="San Francisco")

    request = mock_urlopen.call_args.args[0]
    assert "/api/v1/pricing?" in request.full_url
    assert "role=brand-ambassadors" in request.full_url
    assert "city=San+Francisco" in request.full_url


@patch("tempguru.client.urlopen")
def test_custom_base_url_via_injected_client(mock_urlopen):
    mock_urlopen.return_value = _fake_response({"roles": []})

    spec = TempGuruToolSpec(client=TempGuru(base_url="https://staging.example"))
    spec.event_staffing_roles()

    request = mock_urlopen.call_args.args[0]
    assert request.full_url == "https://staging.example/api/v1/roles"


@patch("tempguru.client.urlopen")
def test_api_error_maps_to_tempguru_error(mock_urlopen):
    body = {
        "error": {
            "message": "Unknown city 'Bostonn'",
            "code": "not_found",
            "suggestion": {"city": "Boston"},
        }
    }
    mock_urlopen.side_effect = HTTPError(
        "https://mcp.tempguru.co/api/v1/pricing",
        404,
        "Not Found",
        None,
        io.BytesIO(json.dumps(body).encode("utf-8")),
    )

    with pytest.raises(TempGuruError) as excinfo:
        TempGuruToolSpec().event_staffing_pricing(
            role="brand-ambassadors", city="Bostonn"
        )

    assert excinfo.value.code == "not_found"
    assert excinfo.value.suggestion == {"city": "Boston"}


@patch("tempguru.client.urlopen")
def test_quote_submission_posts_json_without_touching_network(mock_urlopen):
    payload = {"submitted": True, "deal_name": "Agent Quote", "next_steps": []}
    mock_urlopen.return_value = _fake_response(payload)

    result = TempGuruToolSpec().submit_event_staffing_quote_request(
        budget_range="$10k-$20k", **QUOTE_KWARGS
    )

    assert result == payload
    mock_urlopen.assert_called_once()
    request = mock_urlopen.call_args.args[0]
    assert request.full_url == "https://mcp.tempguru.co/api/v1/quote-requests"
    assert request.get_method() == "POST"
    body = json.loads(request.data.decode("utf-8"))
    assert body["contact_email"] == "test@example.com"
    assert body["roles"] == [{"role": "brand-ambassadors", "headcount": 10}]
    assert body["budget_range"] == "$10k-$20k"
    assert "attire" not in body  # omitted optionals are not sent


# --- LlamaIndex FunctionTool integration ------------------------------------


def test_function_tool_call_returns_client_payload():
    sentinel = {"cities": ["Boston"], "count": 1}
    client = Mock()
    client.cities.return_value = sentinel

    tools = TempGuruToolSpec(client=client).to_tool_list()
    cities_tool = next(t for t in tools if t.metadata.name == "event_staffing_cities")
    output = cities_tool(state="MA")

    assert output.raw_output == sentinel
    client.cities.assert_called_once_with(state="MA", tier=None)
