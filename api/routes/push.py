"""Push notification endpoints (M6 Item 5).

- POST /push/subscribe — register a Web Push subscription
- POST /push/unsubscribe — remove a subscription
- POST /push/send — (internal) send push notification to a user's subscriptions
"""
import json
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/push", tags=["push"])

# In-memory store — production would use DB
_subscriptions: dict[str, dict] = {}  # endpoint → subscription_info


class PushSubscription(BaseModel):
    endpoint: str
    keys: dict
    expirationTime: Optional[float] = None


class UnsubscribeRequest(BaseModel):
    endpoint: str


class SendNotificationRequest(BaseModel):
    endpoint: Optional[str] = None  # None = broadcast
    title: str
    body: str
    url: Optional[str] = None


@router.post("/subscribe")
async def subscribe(sub: PushSubscription):
    """Register a push subscription."""
    _subscriptions[sub.endpoint] = sub.model_dump()
    logger.info("Push subscription registered: %s...", sub.endpoint[:50])
    return {"status": "subscribed"}


@router.post("/unsubscribe")
async def unsubscribe(req: UnsubscribeRequest):
    """Remove a push subscription."""
    _subscriptions.pop(req.endpoint, None)
    return {"status": "unsubscribed"}


@router.post("/send")
async def send_notification(req: SendNotificationRequest):
    """Send a push notification.

    Requires VAPID_PRIVATE_KEY and VAPID_CONTACT_EMAIL in env.
    """
    if not settings.vapid_private_key:
        raise HTTPException(status_code=501, detail="VAPID keys not configured")

    try:
        from pywebpush import webpush, WebPushException
    except ImportError:
        raise HTTPException(
            status_code=501,
            detail="pywebpush not installed — pip install pywebpush",
        )

    payload = json.dumps({
        "title": req.title,
        "body": req.body,
        "url": req.url or "/",
    })

    targets = (
        [_subscriptions[req.endpoint]]
        if req.endpoint and req.endpoint in _subscriptions
        else list(_subscriptions.values())
    )

    sent = 0
    for sub_info in targets:
        try:
            webpush(
                subscription_info=sub_info,
                data=payload,
                vapid_private_key=settings.vapid_private_key,
                vapid_claims={"sub": f"mailto:{settings.vapid_contact_email}"},
            )
            sent += 1
        except Exception as exc:
            logger.warning("Push failed for %s: %s", sub_info.get("endpoint", "?")[:50], exc)
            # Remove stale subscriptions on 410 Gone
            if hasattr(exc, "response") and getattr(exc.response, "status_code", 0) == 410:
                _subscriptions.pop(sub_info.get("endpoint", ""), None)

    return {"status": "sent", "count": sent}
