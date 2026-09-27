"""Snippe payment gateway client (mobile money USSD push)."""
from __future__ import annotations

import uuid

import requests
from django.conf import settings


class SnippeError(Exception):
    pass


def normalize_phone(raw: str) -> str:
    digits = "".join(c for c in (raw or "") if c.isdigit())
    if digits.startswith("0") and len(digits) == 10:
        digits = "255" + digits[1:]
    if digits.startswith("255") and len(digits) == 12:
        return digits
    if len(digits) == 9 and digits[0] in "67":
        return "255" + digits
    return digits


class SnippeClient:
    def __init__(self):
        self.base_url = (settings.SNIPPE_BASE_URL or "https://api.snippe.sh").rstrip("/")
        self.api_key = settings.SNIPPE_API_KEY or ""

    def _headers(self, idempotency_key: str | None = None) -> dict:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if idempotency_key:
            headers["Idempotency-Key"] = idempotency_key
        return headers

    def create_mobile_payment(
        self,
        *,
        amount: int,
        phone: str,
        firstname: str = "AWAY",
        lastname: str = "Viewer",
        email: str = "viewer@awayvideos.local",
        webhook_url: str = "",
        metadata: dict | None = None,
        idempotency_key: str | None = None,
    ) -> dict:
        phone = normalize_phone(phone)
        payload = {
            "payment_type": "mobile",
            "details": {"amount": int(amount), "currency": "TZS"},
            "phone_number": phone,
            "customer": {
                "firstname": firstname[:40] or "AWAY",
                "lastname": lastname[:40] or "Viewer",
                "email": email or "viewer@awayvideos.local",
            },
            "metadata": metadata or {},
        }
        if webhook_url:
            payload["webhook_url"] = webhook_url

        key = idempotency_key or str(uuid.uuid4())
        try:
            resp = requests.post(
                f"{self.base_url}/v1/payments",
                json=payload,
                headers=self._headers(key),
                timeout=30,
            )
        except requests.RequestException as exc:
            raise SnippeError(f"Network error talking to Snippe: {exc}") from exc

        data = {}
        try:
            data = resp.json()
        except Exception:
            data = {"message": resp.text[:200]}

        if resp.status_code >= 400:
            msg = data.get("message") or data.get("error") or f"HTTP {resp.status_code}"
            raise SnippeError(str(msg))

        return data.get("data") or data

    def get_payment(self, reference: str) -> dict:
        try:
            resp = requests.get(
                f"{self.base_url}/v1/payments/{reference}",
                headers=self._headers(),
                timeout=20,
            )
        except requests.RequestException as exc:
            raise SnippeError(f"Network error talking to Snippe: {exc}") from exc

        data = {}
        try:
            data = resp.json()
        except Exception:
            data = {"message": resp.text[:200]}

        if resp.status_code >= 400:
            msg = data.get("message") or f"HTTP {resp.status_code}"
            raise SnippeError(str(msg))

        return data.get("data") or data


def is_completed(status: str | None) -> bool:
    return str(status or "").lower() in {"completed", "success", "paid"}
