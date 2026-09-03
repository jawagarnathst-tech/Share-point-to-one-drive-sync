import msal
import httpx
from typing import Any, Dict, Optional, Tuple
from app.config import settings
import logging

logger = logging.getLogger(__name__)

class GraphClient:
    def __init__(self):
        self.app = msal.ConfidentialClientApplication(
            settings.client_id,
            authority=f"https://login.microsoftonline.com/{settings.tenant_id}",
            client_credential=settings.client_secret,
        )
        self.scopes = ["https://graph.microsoft.com/.default"]

    def _get_token(self) -> str:
        result = self.app.acquire_token_silent(self.scopes, account=None)
        if not result:
            result = self.app.acquire_token_for_client(scopes=self.scopes)
        if "access_token" in result:
            return result["access_token"]
        raise Exception(f"Failed to acquire token: {result.get('error_description', result.get('error'))}")

    async def _request(self, method: str, url: str, **kwargs) -> httpx.Response:
        token = self._get_token()
        headers = kwargs.pop("headers", {})
        headers["Authorization"] = f"Bearer {token}"
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.request(method, url, headers=headers, **kwargs)
            # basic retry could be added here for 429
            return response

    async def get(self, url: str, **kwargs) -> httpx.Response:
        return await self._request("GET", url, **kwargs)

    async def post(self, url: str, **kwargs) -> httpx.Response:
        return await self._request("POST", url, **kwargs)
    
    async def patch(self, url: str, **kwargs) -> httpx.Response:
        return await self._request("PATCH", url, **kwargs)

graph_client = GraphClient()
