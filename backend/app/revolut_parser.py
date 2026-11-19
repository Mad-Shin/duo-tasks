"""
Deterministic Revolut push-notification parser (FR / EN) with strict SecOps DLP.

Security contract:
- Sensitive alerts (login/OTP/2FA codes, 3DS approval prompts, PIN/passcode/
  security/device alerts) and personal-account notifications failing the joint
  keyword filter MUST be marked `drop_silently=True` so the server drops them
  immediately without persisting ANY text, log, or metadata.
- Raw notification text is NEVER returned for persistence.
"""

from __future__ import annotations

import hashlib
import re
import unicodedata
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any

# Security / auth / 3DS / OTP patterns — MUST be dropped silently before any DB write
SENSITIVE_ALERT_PATTERNS: tuple[str, ...] = (
    "code de connexion",
    "code de securite",
    "code de verification",
    "code pin",
    "login code",
    "security code",
    "verification code",
    "passcode",
    "mot de passe",
    "one-time",
    "one time",
    "otp",
    "2fa",
    "3d secure",
    "3-d secure",
    "3ds",
    "approuvez",
    "approuver",
    "approve",
    "confirmez votre",
    "confirmer votre",
    "confirm your",
    "confirm payment",
    "verifiez votre",
    "verify your",
    "autorisez",
    "authorize",
    "authorise",
    "authentif",
    "nouvel appareil",
    "new device",
    "se connecter",
    "connexion detectee",
    "sign in",
    "log in",
    "login attempt",
    "magic link",
    "lien de connexion",
    "cvv",
    "cvc",
    "carte gelee",
    "card frozen",
    "activite suspecte",
    "suspicious",
    "fraude",
    "fraud",
    "reinitialis",
    "reset your",
    "identite",
    "identity",
)

# Standalone OTP / login code pattern (e.g. "code: 482910" or "849-201")
OTP_CODE_REGEX = re.compile(
    r"(?:\bcode\b[^0-9]{0,16}\d{4,8}\b|\b\d{3}[-\s]\d{3}\b)",
    re.IGNORECASE,
)

# Declined / failed payment notifications (non-sensitive, but must not affect balance)
IGNORED_DECLINED_PATTERNS: tuple[str, ...] = (
    "refuse",
    "echoue",
    "annule",
    "insuffisant",
    "insufficient",
    "not enough",
    "declined",
    "failed",
    "canceled",
    "cancelled",
    "reverted",
    "bloque",
    "blocked",
)

IGNORED_PROMO_PATTERNS: tuple[str, ...] = (
    "parrain",
    "invitez",
    "invite friends",
    "revpoints",
    "plan metal",
    "plan ultra",
    "taux de change",
    "exchange rate",
    "weekly summary",
    "resume hebdo",
    "nouvelle fonctionnalite",
    "new feature",
    "cashback offer",
    "offre speciale",
)

REFILL_PATTERNS: tuple[str, ...] = (
    "vous avez recu",
    "recu de",
    "recu un",
    "virement recu",
    "argent recu",
    "ajoute",
    "approvisionn",
    "recharg",
    "rembourse",
    "remboursement",
    "credite",
    "depot",
    "encaisse",
    "you received",
    "received from",
    "received ",
    "money received",
    "added ",
    "top-up",
    "top up",
    "topped up",
    "refund",
    "credited",
    "deposit",
    "sent you",
    "paid you",
    "incoming",
)

EXPENSE_PATTERNS: tuple[str, ...] = (
    "vous avez paye",
    "paye ",
    "depense",
    "paiement",
    "achat",
    "retrait",
    "prelevement",
    "virement vers",
    "envoye a",
    "chez ",
    "you paid",
    "paid ",
    "spent ",
    "payment",
    "purchase",
    "withdrew",
    "withdrawal",
    "direct debit",
    "sent to",
    " at ",
)

GENERIC_TITLES: set[str] = {
    "revolut",
    "compte joint",
    "joint account",
    "paiement",
    "paiement par carte",
    "paiement effectue",
    "card payment",
    "payment",
    "virement",
    "virement recu",
    "transfer",
    "transfer received",
    "rechargement",
    "top-up",
    "top up",
    "depense",
    "argent recu",
    "money received",
    "remboursement",
    "refund",
}

CURRENCY_MAP: dict[str, str] = {
    "€": "EUR",
    "eur": "EUR",
    "$": "USD",
    "usd": "USD",
    "£": "GBP",
    "gbp": "GBP",
    "chf": "CHF",
}

AMOUNT_REGEX = re.compile(
    r"(?P<sign>[+\-−])?\s*"
    r"(?:"
    r"(?P<cur_pre>€|\$|£|\b(?:EUR|USD|GBP|CHF)\b)\s*(?P<num_pre>\d{1,3}(?:[ \.,]\d{3})*(?:[.,]\d{1,2})?|\d+(?:[.,]\d{1,2})?)"
    r"|"
    r"(?P<num_post>\d{1,3}(?:[ \.,]\d{3})*(?:[.,]\d{1,2})?|\d+(?:[.,]\d{1,2})?)\s*(?P<cur_post>€|\$|£|(?:EUR|USD|GBP|CHF)\b)"
    r")",
    re.IGNORECASE,
)


def strip_accents(value: str) -> str:
    """Fold accents and lowercase for robust FR/EN keyword matching."""
    nfkd = unicodedata.normalize("NFKD", value)
    return "".join(ch for ch in nfkd if not unicodedata.combining(ch)).lower()


def _clean_spaces(text: str) -> str:
    return re.sub(r"[\u00a0\u202f\s]+", " ", text or "").strip()


def is_sensitive_revolut_alert(title: str, text: str) -> bool:
    """Return True if the notification looks like a login/OTP code, 3DS prompt, or security alert."""
    combined = _clean_spaces(f"{title} {text}")
    if not combined:
        return False
    folded = strip_accents(combined)
    if any(kw in folded for kw in SENSITIVE_ALERT_PATTERNS):
        return True
    if OTP_CODE_REGEX.search(folded):
        return True
    return False


def parse_number_to_cents(raw_num: str) -> int | None:
    """Convert FR/EN formatted decimal strings ('1 250,50', '1,250.50', '45') to integer cents."""
    cleaned = raw_num.replace(" ", "").strip()
    if not cleaned:
        return None

    if "," in cleaned and "." in cleaned:
        if cleaned.rfind(",") > cleaned.rfind("."):
            cleaned = cleaned.replace(".", "").replace(",", ".")
        else:
            cleaned = cleaned.replace(",", "")
    elif "," in cleaned:
        parts = cleaned.split(",")
        if len(parts) == 2 and len(parts[1]) <= 2:
            cleaned = f"{parts[0]}.{parts[1]}"
        else:
            cleaned = "".join(parts)
    elif "." in cleaned:
        parts = cleaned.split(".")
        if len(parts) == 2 and len(parts[1]) <= 2:
            cleaned = f"{parts[0]}.{parts[1]}"
        else:
            cleaned = "".join(parts)

    try:
        dec = Decimal(cleaned)
    except InvalidOperation:
        return None
    return int((dec * Decimal(100)).quantize(Decimal("1")))


def _clean_merchant_name(raw: str) -> str:
    name = _clean_spaces(raw)
    name = re.sub(
        r"\s*(?:\(|\b(?:sur votre|depuis votre|avec votre|via|from your|on your|with your|using your|compte joint|joint account)\b).*$",
        "",
        name,
        flags=re.IGNORECASE,
    )
    name = name.strip(" .,:;-–—!•|")
    return name[:100].strip()


def _extract_merchant(title: str, text: str, kind: str) -> str:
    combined = f"{title} — {text}" if title and text else (text or title)

    patterns = (
        [
            r"\b(?:de la part de|recu de|reçu de|from)\s+([^•\n,.!?]+)",
            r"(?:€|\$|£|\bEUR\b|\bUSD\b|\bGBP\b|\bCHF\b)\s+(?:de|d'|from)\s+([^•\n,.!?]+)",
            r"\b(?:chez|at|vers|to)\s+([^•\n,.!?]+)",
        ]
        if kind == "refill"
        else [
            r"\b(?:chez|at)\s+([^•\n,.!?]+)",
            r"\b(?:vers|to|a|à)\s+([A-ZÀ-Ý0-9][^•\n,.!?]{1,60})",
        ]
    )

    for pat in patterns:
        m = re.search(pat, combined, flags=re.IGNORECASE)
        if m:
            candidate = _clean_merchant_name(m.group(1))
            if candidate and strip_accents(candidate) not in GENERIC_TITLES:
                return candidate

    clean_title = _clean_merchant_name(title)
    if clean_title and strip_accents(clean_title) not in GENERIC_TITLES and not AMOUNT_REGEX.fullmatch(clean_title):
        stripped_amt = AMOUNT_REGEX.sub("", clean_title).strip(" ·•-:—")
        if stripped_amt and strip_accents(stripped_amt) not in GENERIC_TITLES:
            return stripped_amt[:100]

    return "Rechargement Revolut" if kind == "refill" else "Paiement Revolut"


def compute_dedupe_key(
    title: str,
    text: str,
    timestamp: str | int | float | None = None,
    explicit_key: str | None = None,
) -> str:
    """
    Build a one-way SHA-256 idempotence key resilient to Render cold-start retries.
    Raw notification contents cannot be recovered from this digest.
    """
    if explicit_key and explicit_key.strip():
        return explicit_key.strip()[:128]

    epoch_sec: int | None = None
    if isinstance(timestamp, (int, float)):
        raw_val = float(timestamp)
        epoch_sec = int(raw_val / 1000) if raw_val > 10_000_000_000 else int(raw_val)
    elif isinstance(timestamp, str) and timestamp.strip():
        ts_str = timestamp.strip()
        if ts_str.isdigit():
            raw_int = int(ts_str)
            epoch_sec = raw_int // 1000 if raw_int > 10_000_000_000 else raw_int
        else:
            try:
                iso = ts_str.replace("Z", "+00:00")
                dt = datetime.fromisoformat(iso)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                epoch_sec = int(dt.timestamp())
            except ValueError:
                epoch_sec = None

    if epoch_sec is None:
        epoch_sec = int(datetime.now(timezone.utc).timestamp())

    bucket = epoch_sec // 120
    norm_title = _clean_spaces(title).lower()
    norm_text = _clean_spaces(text).lower()
    digest = hashlib.sha256(f"{bucket}|{norm_title}|{norm_text}".encode("utf-8")).hexdigest()[:40]
    return f"rev_{digest}"


def parse_revolut_notification(
    title: str,
    text: str,
    joint_filter_keyword: str = "",
) -> dict[str, Any]:
    """
    Parse a Revolut push notification into a structured decision dict.
    NEVER returns raw notification text for persistence.
    """
    clean_title = _clean_spaces(title)
    clean_text = _clean_spaces(text)
    combined = f"{clean_title} {clean_text}".strip()
    folded = strip_accents(combined)

    if not combined:
        return {"ignored": True, "reason": "empty_payload", "drop_silently": True}

    # 1. Hard SecOps DLP gate: drop login codes, OTP, 3DS prompts & security alerts BEFORE saving anything
    if is_sensitive_revolut_alert(clean_title, clean_text):
        return {"ignored": True, "reason": "sensitive_alert", "drop_silently": True}

    # 2. Enforce optional joint account keyword filter — drop personal alerts BEFORE saving anything
    kw_setting = _clean_spaces(joint_filter_keyword)
    if kw_setting:
        keywords = [strip_accents(k.strip()) for k in kw_setting.split(",") if k.strip()]
        if keywords and not any(k in folded for k in keywords):
            return {"ignored": True, "reason": "keyword_mismatch", "drop_silently": True}

    # 3. Reject declined/failed/promo notifications
    for kw in IGNORED_DECLINED_PATTERNS:
        if kw in folded:
            return {"ignored": True, "reason": "declined_or_failed", "drop_silently": True}

    for kw in IGNORED_PROMO_PATTERNS:
        if kw in folded:
            return {"ignored": True, "reason": "promo_or_non_tx", "drop_silently": True}

    # 4. Extract first valid monetary amount
    match = AMOUNT_REGEX.search(combined)
    if not match:
        return {"ignored": True, "reason": "no_amount_found", "drop_silently": True}

    raw_num = match.group("num_pre") or match.group("num_post") or ""
    raw_cur = (match.group("cur_pre") or match.group("cur_post") or "€").lower()
    raw_sign = match.group("sign") or ""

    amount_cents = parse_number_to_cents(raw_num)
    if amount_cents is None or amount_cents <= 0:
        return {"ignored": True, "reason": "invalid_amount", "drop_silently": True}

    currency = CURRENCY_MAP.get(raw_cur, "EUR")

    # 5. Determine direction (expense vs refill)
    if raw_sign == "+":
        kind = "refill"
    elif raw_sign in ("-", "−"):
        kind = "expense"
    elif any(kw in folded for kw in REFILL_PATTERNS):
        kind = "refill"
    elif any(kw in folded for kw in EXPENSE_PATTERNS):
        kind = "expense"
    else:
        kind = "expense"

    merchant = _extract_merchant(clean_title, clean_text, kind)

    return {
        "ignored": False,
        "drop_silently": False,
        "kind": kind,
        "amount_cents": amount_cents,
        "currency": currency,
        "merchant": merchant,
    }
