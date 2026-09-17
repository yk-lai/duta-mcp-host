"""Shared error messages + re-verify helper used by more than one tool.

Mirrors integration-hub's ``tools/d365_tools.py`` (``NOT_CONFIGURED_ERROR``,
``UNAVAILABLE_ERROR``, ``_verify_and_get_guid``) — same honest-error
messages, now resolved against the local ``CredentialStore`` instead of a
remote connector lookup.
"""

from __future__ import annotations

from typing import Any

from geneco_mcp.clients.d365_connector import ConnectorError, D365Connector
from geneco_mcp.store.crm_resolver import CrmCredentialResolver

NOT_CONFIGURED_ERROR = "Account verification is not available for this workspace right now."
UNAVAILABLE_ERROR = "I can't check that right now — please contact support."
CUSTOM_API_NOT_CONFIGURED_ERROR = "Fee waiver lookup is not available for this workspace right now."
RECONTRACT_ELIGIBILITY_NOT_CONFIGURED_ERROR = (
    "Re-contract eligibility check is not available for this workspace right now."
)
FEE_REVERSAL_NOT_CONFIGURED_ERROR = "Fee reversal is not available for this workspace right now."
PASSWORD_RESET_NOT_CONFIGURED_ERROR = "Password reset is not available for this workspace right now."


async def verify_and_get_guid(
    resolver: CrmCredentialResolver, tenant_slug: str, *, account_id: str, mobile_number: str
) -> tuple[D365Connector | None, str | None, dict[str, Any] | None]:
    """Shared re-verify step for ``create_support_case``/``get_support_cases``.
    Returns ``(connector, account_guid, error_response)`` — ``error_response``
    is set (and the other two ``None``) whenever the caller should return it
    as-is."""
    try:
        connector = await resolver.get_connector(tenant_slug)
    except ConnectorError:
        # The tenant is configured but its vault couldn't be read.
        return None, None, {"error": UNAVAILABLE_ERROR}
    if connector is None:
        return None, None, {"error": NOT_CONFIGURED_ERROR}
    try:
        account = await connector.get_account_by_filter(account_id, mobile_number)
    except ConnectorError:
        return None, None, {"error": UNAVAILABLE_ERROR}
    if account is None:
        return None, None, {
            "error": "Could not verify this account — account number and mobile number "
            "must match before I can do that."
        }
    return connector, account["account_guid"], None
