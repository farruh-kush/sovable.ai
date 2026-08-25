"""Transactional email delivery through Alibaba Cloud DirectMail.
Author: Farruh
"""

from __future__ import annotations

import asyncio

from ai_routing_shared.exceptions import EmailDeliveryError
from alibabacloud_dm20151123 import models as dm_models
from alibabacloud_dm20151123.client import Client
from alibabacloud_tea_openapi import models as tea_models

from ..core.config import AuthSettings


def _send_directmail(
    settings: AuthSettings, recipient: str, subject: str, text: str, html: str
) -> None:
    if (
        not settings.directmail_access_key_id
        or not settings.directmail_access_key_secret
        or not settings.directmail_account_name
    ):
        raise EmailDeliveryError("Alibaba DirectMail is not configured")
    config = tea_models.Config(
        access_key_id=settings.directmail_access_key_id,
        access_key_secret=settings.directmail_access_key_secret,
        endpoint=settings.directmail_endpoint,
        connect_timeout=10_000,
        read_timeout=20_000,
    )
    client = Client(config)
    request = dm_models.SingleSendMailRequest(
        account_name=settings.directmail_account_name,
        address_type=1,
        reply_to_address="false",
        subject=subject,
        to_address=recipient,
        from_alias=settings.directmail_from_alias[:15],
        text_body=text,
        html_body=html,
    )
    try:
        client.single_send_mail(request)
    except Exception as exc:
        raise EmailDeliveryError("Alibaba DirectMail request failed") from exc


async def send_activation_email(
    settings: AuthSettings, recipient: str, activation_url: str
) -> None:
    subject = "Activate your Solvable AI account"
    text = (
        "Activate your Solvable AI account by opening this link:\n\n"
        f"{activation_url}\n\n"
        f"This link expires in "
        f"{settings.activation_link_ttl_seconds // 60} minutes and can be used once."
    )
    html = (
        "<p>Activate your Solvable AI account by opening the link below.</p>"
        f'<p><a href="{activation_url}">Activate Solvable AI account</a></p>'
        f"<p>This link expires in "
        f"{settings.activation_link_ttl_seconds // 60} minutes and can be used once.</p>"
    )
    await asyncio.to_thread(_send_directmail, settings, recipient, subject, text, html)
