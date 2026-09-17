"""``reverse_fee`` — fee reversal action.

Reverses the applicable fees for an account against the same custom
cxchat API ``check_fee_waiver_status`` uses (this service owns its own
stored credentials for it — see ``store/custom_api_credentials.py``).
Like fee waiver, this is a direct action keyed on account_number — the
custom API has no documented shape for a mobile-number cross-check, so
there's no re-verify step first.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from geneco_mcp.clients.custom_api_client import ConnectorError, CustomApiClient
from geneco_mcp.store.custom_api_credentials import CustomApiCredentialStore
from geneco_mcp.tools._common import FEE_REVERSAL_NOT_CONFIGURED_ERROR, UNAVAILABLE_ERROR
from geneco_mcp.tools.registry import ToolContext, register


class ReverseFeeInput(BaseModel):
    account_number: str = Field(description="The customer's account number.")


@register(
    "reverse_fee",
    description="Reverse the applicable fees for a customer's account, by account number.",
    input_model=ReverseFeeInput,
)
async def handle(ctx: ToolContext, tenant_slug: str, args: ReverseFeeInput) -> dict[str, Any]:
    store = CustomApiCredentialStore(ctx.session, encryption_key=ctx.encryption_key)
    credentials = await store.get_credentials(tenant_slug)
    if credentials is None:
        return {"error": FEE_REVERSAL_NOT_CONFIGURED_ERROR}
    client = CustomApiClient(
        base_url=credentials.base_url, username=credentials.username, password=credentials.password
    )
    try:
        result = await client.reverse_fee(args.account_number)
    except ConnectorError:
        return {"error": UNAVAILABLE_ERROR}
    return {
        "account_number": args.account_number,
        "result": result["result"],
        "remarks": result["remarks"],
    }
