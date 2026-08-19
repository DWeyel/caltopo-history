# SPDX-FileCopyrightText: 2026 Dennis Weyel
# SPDX-License-Identifier: AGPL-3.0-only

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from typing import Any
from urllib.parse import urlencode

import httpx

from .config import settings


class CalTopoError(RuntimeError):
    pass


def sign_request(method: str, endpoint: str, expires: int, payload_string: str, credential_secret: str) -> str:
    message = f"{method.upper()} {endpoint}\n{expires}\n{payload_string}"
    try:
        secret = base64.b64decode(credential_secret)
    except Exception as exc:
        raise CalTopoError("CALTOPO_CREDENTIAL_SECRET is not valid base64") from exc
    digest = hmac.new(secret, message.encode("utf-8"), hashlib.sha256).digest()
    return base64.b64encode(digest).decode("ascii")


class CalTopoClient:
    def __init__(self, credential_id: str | None = None, credential_secret: str | None = None, base_url: str | None = None):
        self.credential_id = settings.credential_id if credential_id is None else credential_id
        self.credential_secret = settings.credential_secret if credential_secret is None else credential_secret
        self.base_url = (settings.caltopo_base_url if base_url is None else base_url).rstrip("/")
        if not self.credential_id or not self.credential_secret:
            raise CalTopoError("CalTopo credentials are not configured")

    async def request(self, method: str, endpoint: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        method = method.upper()
        payload_string = json.dumps(payload) if payload is not None else ""
        expires = int(time.time() * 1000) + 120_000
        signature = sign_request(method, endpoint, expires, payload_string, self.credential_secret)
        params: dict[str, Any] = {
            "id": self.credential_id,
            "expires": expires,
            "signature": signature,
        }
        body = None
        query = None
        if method == "POST" and payload is not None:
            params["json"] = payload_string
            body = params
        else:
            query = params
        url = f"{self.base_url}{endpoint}"
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=False) as client:
            response = await client.request(method, url, params=query, data=body)
        if response.status_code >= 400:
            raise CalTopoError(f"CalTopo API {response.status_code}: {response.text[:500]}")
        if not response.content:
            return {}
        try:
            data = response.json()
        except Exception as exc:
            raise CalTopoError("CalTopo returned a non-JSON response") from exc
        return data.get("result", data)

    async def get_map(self, map_id: str, since: int = 0) -> dict[str, Any]:
        return await self.request("GET", f"/api/v1/map/{map_id}/since/{since}")

    async def get_team(self, team_id: str, since: int = 0) -> dict[str, Any]:
        return await self.request("GET", f"/api/v1/acct/{team_id}/since/{since}")

    async def add_object(self, map_id: str, object_type: str, feature: dict[str, Any]) -> dict[str, Any]:
        payload = json.loads(json.dumps(feature))
        payload.pop("id", None)
        if isinstance(payload.get("properties"), dict):
            payload["properties"].pop("class", None)
        return await self.request("POST", f"/api/v1/map/{map_id}/{object_type}", payload)

    async def edit_object(self, map_id: str, object_type: str, object_id: str, feature: dict[str, Any]) -> dict[str, Any]:
        payload = json.loads(json.dumps(feature))
        payload["id"] = object_id
        payload.setdefault("properties", {})["class"] = object_type
        return await self.request("POST", f"/api/v1/map/{map_id}/{object_type}/{object_id}", payload)

    async def delete_object(self, map_id: str, object_type: str, object_id: str) -> dict[str, Any]:
        return await self.request("DELETE", f"/api/v1/map/{map_id}/{object_type}/{object_id}")
