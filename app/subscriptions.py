import logging
from datetime import datetime, timedelta, timezone
from app.graph import graph_client
from app.config import settings

logger = logging.getLogger(__name__)

async def create_subscription():
    if not settings.webhook_url or not settings.webhook_client_state:
        logger.error("Webhook URL and Client State must be configured.")
        return

    # Expiration for SharePoint list subscription is typically up to 30 days. Let's use 29 days.
    expiration = (datetime.now(timezone.utc) + timedelta(days=29)).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    
    payload = {
        "changeType": "updated",
        "notificationUrl": settings.webhook_url,
        "resource": f"sites/{settings.source_site_id}/lists/{settings.source_list_id}",
        "expirationDateTime": expiration,
        "clientState": settings.webhook_client_state
    }
    
    response = await graph_client.post("https://graph.microsoft.com/v1.0/subscriptions", json=payload)
    if response.status_code == 201:
        logger.info(f"Subscription created successfully: {response.json()}")
    else:
        logger.error(f"Failed to create subscription: {response.text}")

async def renew_subscription(subscription_id: str):
    expiration = (datetime.now(timezone.utc) + timedelta(days=29)).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    payload = {
        "expirationDateTime": expiration
    }
    response = await graph_client.patch(f"https://graph.microsoft.com/v1.0/subscriptions/{subscription_id}", json=payload)
    if response.status_code == 200:
        logger.info(f"Subscription renewed successfully: {response.json()}")
    else:
        logger.error(f"Failed to renew subscription: {response.text}")
