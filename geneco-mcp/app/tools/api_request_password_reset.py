"""``request_password_reset`` — self-service-portal password reset.

Triggers a password-reset email against the same custom cxchat API
``check_fee_waiver_status`` uses (this service owns its own stored
credentials for it — see ``store/custom_api_credentials.py``). Keyed on
the account holder's registered email address, not an account number —
confirmed empirically against SIT that the vendor API rejects an account
number the same way it rejects an unregistered email.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from geneco_mcp.clients.custom_api_client import ConnectorError, CustomApiClient
from geneco_mcp.store.custom_api_credentials import CustomApiCredentialStore
from geneco_mcp.tools._common import PASSWORD_RESET_NOT_CONFIGURED_ERROR, UNAVAILABLE_ERROR
from geneco_mcp.tools.registry import ToolContext, register


class RequestPasswordResetInput(BaseModel):
    email: str = Field(description="The customer's registered account email address.")


@register(
    "request_password_reset",
    description=(
        "Send a self-service-portal password-reset email to a customer's registered email address."
    ),
    input_model=RequestPasswordResetInput,
)
async def handle(
    ctx: ToolContext, tenant_slug: str, args: RequestPasswordResetInput
) -> dict[str, Any]:
    store = CustomApiCredentialStore(ctx.session, encryption_key=ctx.encryption_key)
    credentials = await store.get_credentials(tenant_slug)
    if credentials is None:
        return {"error": PASSWORD_RESET_NOT_CONFIGURED_ERROR}
    client = CustomApiClient(
        base_url=credentials.base_url, username=credentials.username, password=credentials.password
    )
    try:
        result = await client.request_password_reset(args.email)
    except ConnectorError:
        return {"error": UNAVAILABLE_ERROR}
    return {
        "email": args.email,
        "success": result["success"],
        "message": result["message"],
    }
