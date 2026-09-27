import base64
import hashlib
import hmac
import json
from datetime import datetime
from zoneinfo import ZoneInfo

import requests
from django.conf import settings


class SelcomError(Exception):
    pass


class SelcomClient:
    """Selcom API Gateway checkout client (HMAC HS256 signed requests)."""

    def __init__(self):
        self.base_url = settings.SELCOM_BASE_URL.rstrip("/")
        self.api_key = settings.SELCOM_API_KEY
        self.api_secret = settings.SELCOM_API_SECRET
        self.vendor = settings.SELCOM_VENDOR

    def _headers(self, payload: dict) -> dict:
        timestamp = datetime.now(ZoneInfo("Africa/Dar_es_Salaam")).strftime("%Y-%m-%dT%H:%M:%S%z")
        timestamp = timestamp[:-2] + ":" + timestamp[-2:] if len(timestamp) > 5 else timestamp
        signed_fields = ",".join(payload.keys())
        sign_data = "&".join(f"{key}={value}" for key, value in payload.items())
        digest = base64.b64encode(
            hmac.new(self.api_secret.encode("utf-8"), sign_data.encode("utf-8"), hashlib.sha256).digest()
        ).decode("utf-8")
        authorization = base64.b64encode(self.api_key.encode("utf-8")).decode("utf-8")
        return {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"SELCOM {authorization}",
            "Digest-Method": "HS256",
            "Digest": digest,
            "Timestamp": timestamp,
            "Signed-Fields": signed_fields,
        }

    def _request(self, method: str, path: str, payload: dict) -> dict:
        if not all([self.api_key, self.api_secret, self.vendor]):
            raise SelcomError("Selcom API credentials are not configured.")
        url = f"{self.base_url}{path}"
        headers = self._headers(payload)
        if method == "GET":
            response = requests.get(url, params=payload, headers=headers, timeout=30)
        else:
            response = requests.post(url, json=payload, headers=headers, timeout=30)
        try:
            data = response.json()
        except ValueError as exc:
            raise SelcomError(f"Selcom returned a non-JSON response ({response.status_code}).") from exc
        if response.status_code >= 400:
            raise SelcomError(data.get("message") or f"Selcom request failed ({response.status_code}).")
        return data

    def create_order(self, *, order_id: str, buyer_email: str, buyer_name: str, buyer_phone: str, amount: int, webhook: str) -> dict:
        payload = {
            "vendor": self.vendor,
            "order_id": order_id,
            "buyer_email": buyer_email,
            "buyer_name": buyer_name,
            "buyer_phone": buyer_phone,
            "amount": str(amount),
            "currency": "TZS",
            "buyer_remarks": "Adu Reel video",
            "merchant_remarks": "Adu Reel",
            "no_of_items": "1",
            "webhook": base64.b64encode(webhook.encode("utf-8")).decode("utf-8"),
        }
        return self._request("POST", "/v1/checkout/create-order-minimal", payload)

    def wallet_payment(self, *, transid: str, order_id: str, msisdn: str) -> dict:
        payload = {
            "transid": transid,
            "order_id": order_id,
            "msisdn": msisdn,
        }
        return self._request("POST", "/v1/checkout/wallet-payment", payload)

    def order_status(self, order_id: str) -> dict:
        return self._request("GET", "/v1/checkout/order-status", {"order_id": order_id})


def verify_webhook(headers, body: bytes, secret: str) -> bool:
    signed_fields = headers.get("Signed-Fields") or headers.get("HTTP_SIGNED_FIELDS", "")
    digest = headers.get("Digest") or headers.get("HTTP_DIGEST", "")
    if not signed_fields or not digest:
        return False
    try:
        payload = json.loads(body.decode("utf-8") or "{}")
    except json.JSONDecodeError:
        return False
    values = []
    for field in signed_fields.split(","):
        field = field.strip()
        if field:
            values.append(f"{field}={payload.get(field, '')}")
    sign_data = "&".join(values)
    expected = base64.b64encode(hmac.new(secret.encode("utf-8"), sign_data.encode("utf-8"), hashlib.sha256).digest()).decode("utf-8")
    return hmac.compare_digest(expected, digest)


def is_success_result(data: dict) -> bool:
    result = str(data.get("result") or "").upper()
    status = str(data.get("payment_status") or "").upper()
    code = str(data.get("resultcode") or "")
    return status == "COMPLETED" or (result == "SUCCESS" and code in {"000", "0"})
