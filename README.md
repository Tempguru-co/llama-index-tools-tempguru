# TempGuru Event Staffing Tools

[TempGuru](https://tempguru.co) is a W-2 compliant event staffing vendor for trade shows, conferences, festivals, concerts, sporting and stadium events, corporate events, and brand activations — single events or multi-city programs — across 345+ US and Canadian cities.

This package gives LlamaIndex agents live access to TempGuru's public event staffing API: city coverage, staffing roles, all-inclusive W-2 hourly rate ranges, booking lead-time guidance, and state-by-state labor compliance summaries, plus one opt-in tool that submits a confirmed staffing plan for a human-reviewed quote.

**No API key required.** The five data tools are read-only and unauthenticated; no credentials or user data are requested or stored. The quote-submission tool is the only write and is opt-in (disable it with one flag for a strictly read-only tool set).

## Installation

```bash
pip install llama-index-tools-tempguru
```

## Usage

```python
from llama_index.tools.tempguru import TempGuruToolSpec
from llama_index.core.agent.workflow import FunctionAgent
from llama_index.llms.openai import OpenAI

tool_spec = TempGuruToolSpec()

agent = FunctionAgent(
    tools=tool_spec.to_tool_list(),
    llm=OpenAI(model="gpt-4o"),
)

print(
    await agent.run(
        "What would 10 brand ambassadors cost per hour in Boston, "
        "and how far ahead should I book for a trade show on August 12?"
    )
)
```

For a strictly read-only tool set (no quote submission):

```python
tool_spec = TempGuruToolSpec(include_quote_submission=False)
```

## Available Functions

| Tool | Description |
| --- | --- |
| `event_staffing_cities` | List the 345+ US/CA cities TempGuru covers, filterable by state/province and market tier. |
| `event_staffing_roles` | The 10-role catalog (brand ambassadors, registration, ushers, hospitality, gate staff, booth monitors, crowd control, guest services, setup/breakdown, team leads) with skill tiers. |
| `event_staffing_availability` | Booking lead-time guidance (`yes` / `tight` / `rush` / `very-rush`) for a city and ISO date. Planning guidance, not a reservation. |
| `event_staffing_pricing` | All-inclusive W-2 hourly rate range for a role in a city (wages, payroll taxes, workers' comp, liability included). Estimates, not binding quotes. |
| `event_staffing_state_compliance` | US-state employment compliance summary: minimum wage, overtime thresholds, state quirks. Operational guidance, not legal advice. |
| `submit_event_staffing_quote_request` | **Opt-in write.** Submits a confirmed staffing plan to TempGuru for a human-reviewed quote (response within one business day). No reservation, no payment. Agents should confirm the full plan with the user first and call it at most once. |

## Data and Endpoints

- REST API base: `https://mcp.tempguru.co/api/v1` ([OpenAPI spec](https://mcp.tempguru.co/openapi.json))
- The same data is exposed as an MCP server at `https://mcp.tempguru.co/mcp` (streamable HTTP, no auth) — usable directly from LlamaIndex via [`llama-index-tools-mcp`](https://pypi.org/project/llama-index-tools-mcp/) if you prefer the MCP transport.
- The underlying HTTP client is the zero-dependency [`tempguru`](https://pypi.org/project/tempguru/) package; this package re-exports its `TempGuruToolSpec` under the LlamaIndex-conventional import path. Pass a custom `TempGuru(base_url=..., timeout=...)` client to the spec to point at a different environment.
- Docs for AI integrations: [tempguru.co/ai](https://tempguru.co/ai)

## Notes for Agent Builders

- Rate ranges are planning estimates, never binding quotes.
- Availability responses are lead-time guidance, never reservations — don't promise availability.
- Compliance summaries are operational guidance, not legal advice.

This package's tests mock all HTTP; nothing in the test suite calls the production API.
