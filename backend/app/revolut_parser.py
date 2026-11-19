"""
Deterministic Revolut push-notification parser (FR / EN) for DuoTasks.

Extracts integer cents, currency, direction (expense vs refill), and merchant
label from Android MacroDroid notification payloads, while safely ignoring
declined payments, authentication prompts, promos, and non-matching accounts.
"""

from __future__ import annotations

import hashlib
import re
import unicodedata
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any

# Declined / failed / security prompts that may contain an amount and MUST be ignored
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
    "carte gelee",
    "card frozen",
    "bloque",
    "blocked",
    "approuvez",
    "approve",
    "confirmez",
    "confirm your",
    "verifiez",
    "verify your",
    "code de securite",
    "security code",
    "3d secure",
    "otp",
    "code pin",
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

# Match either prefix currency (`-€12.50`, `+€200`, `$14.99`) or suffix currency (`-12,50 €`, `1 250,00 EUR`)
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


def parse_number_to_cents(raw_num: str) -> int | None:
    """Convert FR/EN formatted decimal strings ('1 250,50', '1,250.50', '45') to integer cents."""
    cleaned = raw_num.replace(" ", "").strip()
    if not cleaned:
        return None

    # Disambiguate commas and dots
    if "," in cleaned and "." in cleaned:
        # Whichever appears last is the decimal separator
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
    cents = int((dec * Decimal(100)).quantize(Decimal("1")))
    return cents


def _clean_merchant_name(raw: str) -> str:
    name = _clean_spaces(raw)
    # Remove trailing account / card boilerplate
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

    # Fallback: clean title when it looks like a merchant name (e.g. Title="Carrefour", Text="14,80 €")
    clean_title = _clean_merchant_name(title)
    if clean_title and strip_accents(clean_title) not in GENERIC_TITLES and not AMOUNT_REGEX.fullmatch(clean_title):
        # Strip inline amount if title was "Carrefour · 14,80 €"
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
    Build a deterministic idempotence key resilient to Render cold-start retries.
    Uses explicit key if provided; otherwise hashes a 120s time bucket + normalized content.
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

    Returns either:
      {"ignored": True, "reason": "..."}
    or:
      {
        "ignored": False,
        "kind": "expense" | "refill",
        "amount_cents": int,
        "currency": "EUR",
        "merchant": str,
        "raw_text": str,
      }
    """
    clean_title = _clean_spaces(title)
    clean_text = _clean_spaces(text)
    combined = f"{clean_title} {clean_text}".strip()
    folded = strip_accents(combined)

    if not combined:
        return {"ignored": True, "reason": "empty_payload"}

    # 1. Always reject declined/failed/auth/promo notifications first
    for kw in IGNORED_DECLINED_PATTERNS:
        if kw in folded:
            return {"ignored": True, "reason": "declined_or_failed"}

    for kw in IGNORED_PROMO_PATTERNS:
        if kw in folded:
            return {"ignored": True, "reason": "promo_or_non_tx"}

    # 2. Enforce optional joint account keyword filter (comma-separated OR matching)
    kw_setting = _clean_spaces(joint_filter_keyword)
    if kw_setting:
        keywords = [strip_accents(k.strip()) for k in kw_setting.split(",") if k.strip()]
        if keywords and not any(k in folded for k in keywords):
            return {"ignored": True, "reason": "keyword_mismatch"}

    # 3. Extract first valid monetary amount
    match = AMOUNT_REGEX.search(combined)
    if not match:
        return {"ignored": True, "reason": "no_amount_found"}

    raw_num = match.group("num_pre") or match.group("num_post") or ""
    raw_cur = (match.group("cur_pre") or match.group("cur_post") or "€").lower()
    raw_sign = match.group("sign") or ""

    amount_cents = parse_number_to_cents(raw_num)
    if amount_cents is None or amount_cents <= 0:
        return {"ignored": True, "reason": "invalid_amount"}

    currency = CURRENCY_MAP.get(raw_cur, "EUR")

    # 4. Determine direction (expense vs refill)
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
    raw_display = f"{clean_title} — {clean_text}" if clean_title and clean_text else combined

    return {
        "ignored": False,
        "kind": kind,
        "amount_cents": amount_cents,
        "currency": currency,
        "merchant": merchant,
        "raw_text": raw_display[:320],
    }
