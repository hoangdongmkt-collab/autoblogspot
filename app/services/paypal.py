import base64
import json
import urllib.error
import urllib.parse
import urllib.request

_LIVE_BASE    = "https://api-m.paypal.com"
_SANDBOX_BASE = "https://api-m.sandbox.paypal.com"


def _base(sandbox: bool) -> str:
    return _SANDBOX_BASE if sandbox else _LIVE_BASE


def _get_access_token(client_id: str, client_secret: str, sandbox: bool) -> str:
    credentials = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
    data = urllib.parse.urlencode({"grant_type": "client_credentials"}).encode()
    req = urllib.request.Request(f"{_base(sandbox)}/v1/oauth2/token", data=data)
    req.add_header("Authorization", f"Basic {credentials}")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read())["access_token"]
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")
        raise ValueError(f"PayPal auth HTTP {e.code}: {body[:300]}")


def create_order(
    client_id: str, client_secret: str,
    plan: str, months: int, amount_usd: str,
    user_id: int,
    return_url: str, cancel_url: str,
    sandbox: bool = False,
) -> dict:
    """Create a PayPal order. Returns {'id': ..., 'approve_url': ...}."""
    token = _get_access_token(client_id, client_secret, sandbox)
    total = f"{round(float(amount_usd) * months, 2):.2f}"

    payload = {
        "intent": "CAPTURE",
        "purchase_units": [{
            "amount": {"currency_code": "USD", "value": total},
            "description": f"AutoBlogspot {plan.title()} x{months} month(s)",
            "custom_id": f"{user_id}:{plan}:{months}",
        }],
        "application_context": {
            "return_url":  return_url,
            "cancel_url":  cancel_url,
            "brand_name":  "AutoBlogspot",
            "user_action": "PAY_NOW",
            "shipping_preference": "NO_SHIPPING",
        },
    }
    data = json.dumps(payload).encode()
    req = urllib.request.Request(f"{_base(sandbox)}/v2/checkout/orders", data=data)
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            result = json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")
        raise ValueError(f"PayPal create-order HTTP {e.code}: {body[:400]}")

    approve_url = next(
        (lnk["href"] for lnk in result.get("links", []) if lnk.get("rel") == "approve"),
        None,
    )
    return {"id": result["id"], "approve_url": approve_url}


def capture_order(
    client_id: str, client_secret: str,
    order_id: str,
    sandbox: bool = False,
) -> dict:
    """Capture an approved PayPal order. Returns the full capture response."""
    token = _get_access_token(client_id, client_secret, sandbox)
    req = urllib.request.Request(
        f"{_base(sandbox)}/v2/checkout/orders/{order_id}/capture",
        data=b"{}",
        method="POST",
    )
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")
        raise ValueError(f"PayPal capture HTTP {e.code}: {body[:400]}")


def verify_webhook_signature(
    client_id: str, client_secret: str,
    webhook_id: str,
    transmission_id: str, transmission_time: str,
    cert_url: str, auth_algo: str, transmission_sig: str,
    body: bytes,
    sandbox: bool = False,
) -> bool:
    """Verify a PayPal webhook via the verify-webhook-signature API."""
    try:
        token = _get_access_token(client_id, client_secret, sandbox)
        payload = json.dumps({
            "transmission_id":   transmission_id,
            "transmission_time": transmission_time,
            "cert_url":          cert_url,
            "auth_algo":         auth_algo,
            "transmission_sig":  transmission_sig,
            "webhook_id":        webhook_id,
            "webhook_event":     json.loads(body),
        }).encode()
        req = urllib.request.Request(
            f"{_base(sandbox)}/v1/notifications/verify-webhook-signature",
            data=payload,
        )
        req.add_header("Authorization", f"Bearer {token}")
        req.add_header("Content-Type", "application/json")
        with urllib.request.urlopen(req, timeout=15) as resp:
            result = json.loads(resp.read())
            return result.get("verification_status") == "SUCCESS"
    except Exception:
        return False
