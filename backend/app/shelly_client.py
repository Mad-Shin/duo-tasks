"""
Shelly Cloud Control API (+ optional Local LAN RPC fallback) client for DuoTasks Domotique.

Supports:
- Shelly 1 Gen3 gas heating relay (ON/OFF + hardware auto-off Boost timer)
- Shelly BLU H&T climate sensor (temperature, humidity, battery via Shelly Cloud or local KVS)
- Future Shelly Wi-Fi bulbs / dimmers / plugs (auto-discovered from Shelly Cloud account)

SecOps invariants:
- SHELLY_AUTH_KEY is read strictly from environment variables and NEVER returned or logged.
- In-memory TTL cache (5s) prevents exceeding Shelly Cloud's 1 req/s rate limit.
"""

from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone
from typing import Any, Optional

import httpx

DEFAULT_SHELLY_SERVER = "https://shelly-315-eu.shelly.cloud"
DEFAULT_HEATING_DEVICE_ID = "80b54e3be384"
CACHE_TTL_SECONDS = 5.0

_CACHE_TS: float = 0.0
_CACHE_DATA: dict[str, Any] | None = None


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def invalidate_cache() -> None:
    global _CACHE_TS, _CACHE_DATA
    _CACHE_TS = 0.0
    _CACHE_DATA = None


def _normalize_id(raw: str) -> str:
    return raw.strip().lower().replace(":", "").replace("-", "")


def _normalize_server_uri(raw: str) -> str:
    uri = (raw or "").strip().rstrip("/")
    if not uri:
        return DEFAULT_SHELLY_SERVER
    if not uri.startswith(("http://", "https://")):
        uri = f"https://{uri}"
    return uri


def _sanitize_error(message: str, auth_key: str) -> str:
    cleaned = str(message or "")
    if auth_key:
        cleaned = cleaned.replace(auth_key, "***")
    return cleaned[:240]


def get_shelly_config() -> dict[str, str]:
    auth_key = os.environ.get("SHELLY_AUTH_KEY", "").strip()
    server_uri = _normalize_server_uri(os.environ.get("SHELLY_SERVER_URI", DEFAULT_SHELLY_SERVER))
    heating_id = _normalize_id(os.environ.get("SHELLY_HEATING_DEVICE_ID", DEFAULT_HEATING_DEVICE_ID))
    climate_id = _normalize_id(os.environ.get("SHELLY_CLIMATE_DEVICE_ID", ""))
    local_host = os.environ.get("SHELLY_LOCAL_HOST", "").strip().rstrip("/")
    return {
        "auth_key": auth_key,
        "server_uri": server_uri,
        "heating_id": heating_id,
        "climate_id": climate_id,
        "local_host": local_host,
    }


def _to_float(val: Any) -> Optional[float]:
    if val is None or isinstance(val, bool):
        return None
    if isinstance(val, (int, float)):
        return round(float(val), 1)
    if isinstance(val, str):
        try:
            return round(float(val.strip().replace(",", ".")), 1)
        except ValueError:
            return None
    return None


def _to_int(val: Any) -> Optional[int]:
    if val is None or isinstance(val, bool):
        return None
    if isinstance(val, (int, float)):
        return int(round(float(val)))
    if isinstance(val, str):
        try:
            return int(round(float(val.strip())))
        except ValueError:
            return None
    return None


def _extract_temperature(dev: dict[str, Any]) -> Optional[float]:
    components = dev.get("components") if isinstance(dev.get("components"), dict) else {}
    for container in (dev, components):
        t0 = container.get("temperature:0")
        if isinstance(t0, dict) and t0.get("tC") is not None:
            return _to_float(t0.get("tC"))
        tmp = container.get("tmp")
        if isinstance(tmp, dict):
            for key in ("tC", "value"):
                if tmp.get(key) is not None:
                    return _to_float(tmp.get(key))
        temp_val = container.get("temperature")
        if isinstance(temp_val, dict):
            for key in ("tC", "value"):
                if temp_val.get(key) is not None:
                    return _to_float(temp_val.get(key))
        elif temp_val is not None:
            return _to_float(temp_val)
    return None


def _extract_humidity(dev: dict[str, Any]) -> Optional[float]:
    components = dev.get("components") if isinstance(dev.get("components"), dict) else {}
    for container in (dev, components):
        h0 = container.get("humidity:0")
        if isinstance(h0, dict) and h0.get("rh") is not None:
            return _to_float(h0.get("rh"))
        hum = container.get("hum")
        if isinstance(hum, dict):
            for key in ("rh", "value"):
                if hum.get(key) is not None:
                    return _to_float(hum.get(key))
        hum_val = container.get("humidity")
        if isinstance(hum_val, dict):
            for key in ("rh", "value"):
                if hum_val.get(key) is not None:
                    return _to_float(hum_val.get(key))
        elif hum_val is not None:
            return _to_float(hum_val)
    return None


def _extract_battery(dev: dict[str, Any]) -> Optional[int]:
    components = dev.get("components") if isinstance(dev.get("components"), dict) else {}
    for container in (dev, components):
        dp = container.get("devicepower:0")
        if isinstance(dp, dict) and isinstance(dp.get("battery"), dict):
            pct = _to_int(dp["battery"].get("percent"))
            if pct is not None:
                return pct
        for key in ("battery", "bat"):
            val = container.get(key)
            if isinstance(val, dict):
                for sub in ("percent", "value"):
                    pct = _to_int(val.get(sub))
                    if pct is not None:
                        return pct
            elif val is not None:
                pct = _to_int(val)
                if pct is not None:
                    return pct
    return None


def _extract_switch_state(dev: dict[str, Any]) -> tuple[bool, Optional[bool], Optional[float], Optional[int]]:
    """Returns (has_switch, is_on, relay_temp_c, timer_remaining_sec)."""
    sw0 = dev.get("switch:0")
    if isinstance(sw0, dict):
        is_on = bool(sw0.get("output", False))
        relay_temp = None
        if isinstance(sw0.get("temperature"), dict):
            relay_temp = _to_float(sw0["temperature"].get("tC"))
        timer_rem = None
        started = sw0.get("timer_started_at")
        duration = sw0.get("timer_duration")
        if isinstance(started, (int, float)) and isinstance(duration, (int, float)) and duration > 0:
            rem = int(round((started + duration) - time.time()))
            if rem > 0:
                timer_rem = rem
        return True, is_on, relay_temp, timer_rem

    relays = dev.get("relays")
    if isinstance(relays, list) and relays and isinstance(relays[0], dict):
        r0 = relays[0]
        is_on = bool(r0.get("ison", False))
        rem = _to_int(r0.get("timer_remaining"))
        return True, is_on, None, (rem if rem and rem > 0 else None)

    return False, None, None, None


def _extract_light_state(dev: dict[str, Any]) -> tuple[bool, Optional[bool], Optional[int]]:
    """Returns (has_light, is_on, brightness_0_100)."""
    for comp_key in ("light:0", "rgbw:0", "rgb:0"):
        comp = dev.get(comp_key)
        if isinstance(comp, dict):
            is_on = bool(comp.get("output", False))
            bright = _to_int(comp.get("brightness"))
            return True, is_on, bright

    lights = dev.get("lights")
    if isinstance(lights, list) and lights and isinstance(lights[0], dict):
        l0 = lights[0]
        is_on = bool(l0.get("ison", False))
        bright = _to_int(l0.get("brightness"))
        if bright is None:
            bright = _to_int(l0.get("gain"))
        return True, is_on, bright

    return False, None, None


def _extract_online(dev: dict[str, Any]) -> bool:
    info = dev.get("_dev_info") if isinstance(dev.get("_dev_info"), dict) else {}
    if "online" in info:
        return bool(info["online"])
    if "online" in dev:
        return bool(dev["online"])
    if isinstance(dev.get("cloud"), dict) and "connected" in dev["cloud"]:
        return bool(dev["cloud"]["connected"])
    return True


def _extract_model(dev: dict[str, Any]) -> str:
    info = dev.get("_dev_info") if isinstance(dev.get("_dev_info"), dict) else {}
    for key in ("code", "model", "type"):
        val = info.get(key) or dev.get(key)
        if isinstance(val, str) and val.strip():
            return val.strip()
    return ""


def _extract_name(dev: dict[str, Any], fallback: str) -> str:
    info = dev.get("_dev_info") if isinstance(dev.get("_dev_info"), dict) else {}
    for candidate in (info.get("name"), dev.get("name")):
        if isinstance(candidate, str) and candidate.strip():
            return candidate.strip()
    return fallback


def _extract_rssi(dev: dict[str, Any]) -> Optional[int]:
    wifi = dev.get("wifi")
    if isinstance(wifi, dict) and wifi.get("rssi") is not None:
        return _to_int(wifi.get("rssi"))
    wifi_sta = dev.get("wifi_sta")
    if isinstance(wifi_sta, dict) and wifi_sta.get("rssi") is not None:
        return _to_int(wifi_sta.get("rssi"))
    return None


def _extract_updated(dev: dict[str, Any]) -> str:
    for key in ("_updated", "updated_at"):
        val = dev.get(key)
        if isinstance(val, str) and val.strip():
            return val.strip()
    return ""


def parse_cloud_devices_status(
    devices_status: dict[str, Any],
    *,
    heating_id_hint: str = DEFAULT_HEATING_DEVICE_ID,
    climate_id_hint: str = "",
) -> tuple[Optional[dict[str, Any]], Optional[dict[str, Any]], list[dict[str, Any]]]:
    """
    Normalizes Shelly Cloud `data.devices_status` into (heating, climate, lights).
    """
    heating: Optional[dict[str, Any]] = None
    climate: Optional[dict[str, Any]] = None
    lights: list[dict[str, Any]] = []

    norm_heating_hint = _normalize_id(heating_id_hint)
    norm_climate_hint = _normalize_id(climate_id_hint)

    switch_candidates: list[dict[str, Any]] = []
    climate_candidates: list[dict[str, Any]] = []

    for raw_dev_id, raw_payload in devices_status.items():
        if not isinstance(raw_payload, dict):
            continue
        dev_id = str(raw_dev_id).strip()
        norm_id = _normalize_id(dev_id)
        sys_mac = _normalize_id(str((raw_payload.get("sys") or {}).get("mac") or ""))
        info = raw_payload.get("_dev_info") if isinstance(raw_payload.get("_dev_info"), dict) else {}
        info_id = _normalize_id(str(info.get("id") or ""))
        model = _extract_model(raw_payload)
        online = _extract_online(raw_payload)
        updated_at = _extract_updated(raw_payload)

        has_light, light_on, brightness = _extract_light_state(raw_payload)
        has_switch, switch_on, relay_temp, timer_rem = _extract_switch_state(raw_payload)
        temp_c = _extract_temperature(raw_payload)
        hum_pct = _extract_humidity(raw_payload)
        bat_pct = _extract_battery(raw_payload)

        is_climate_sensor = (temp_c is not None or hum_pct is not None) and not has_switch and not has_light
        is_blu_ht_model = model.upper().startswith(("SBHT", "SHHT", "SNSN-0013", "S3SN-0U12"))

        if is_climate_sensor or is_blu_ht_model:
            entry = {
                "device_id": dev_id,
                "name": _extract_name(raw_payload, "Capteur Salon (H&T)"),
                "model": model or "Shelly BLU H&T",
                "temperature_c": temp_c,
                "humidity_pct": hum_pct,
                "battery_pct": bat_pct,
                "online": online,
                "updated_at": updated_at,
                "_matched_hint": bool(
                    norm_climate_hint and norm_climate_hint in (norm_id, sys_mac, info_id)
                ),
            }
            climate_candidates.append(entry)
            continue

        if has_light:
            lights.append(
                {
                    "device_id": dev_id,
                    "name": _extract_name(raw_payload, f"Ampoule {dev_id[-4:]}"),
                    "model": model or "Shelly Light",
                    "kind": "light",
                    "channel": 0,
                    "is_on": bool(light_on),
                    "brightness": brightness,
                    "online": online,
                    "updated_at": updated_at,
                }
            )
            continue

        if has_switch:
            matched_heating = bool(
                norm_heating_hint and norm_heating_hint in (norm_id, sys_mac, info_id)
            )
            switch_candidates.append(
                {
                    "device_id": dev_id,
                    "name": _extract_name(raw_payload, "Chauffage gaz"),
                    "model": model or "Shelly Switch",
                    "channel": 0,
                    "is_on": bool(switch_on),
                    "online": online,
                    "relay_temp_c": relay_temp,
                    "rssi": _extract_rssi(raw_payload),
                    "timer_remaining_sec": timer_rem,
                    "updated_at": updated_at,
                    "_matched_hint": matched_heating,
                }
            )

    # Pick heating device: explicit hint first, otherwise first switch
    if switch_candidates:
        switch_candidates.sort(key=lambda item: (not item["_matched_hint"], item["device_id"]))
        chosen = dict(switch_candidates[0])
        chosen.pop("_matched_hint", None)
        heating = chosen

        # Any additional switches/plugs show up in lights/controls automatically
        for extra in switch_candidates[1:]:
            lights.append(
                {
                    "device_id": extra["device_id"],
                    "name": extra["name"] if extra["name"] != "Chauffage gaz" else f"Prise {extra['device_id'][-4:]}",
                    "model": extra["model"],
                    "kind": "switch",
                    "channel": extra["channel"],
                    "is_on": extra["is_on"],
                    "brightness": None,
                    "online": extra["online"],
                    "updated_at": extra["updated_at"],
                }
            )

    if climate_candidates:
        climate_candidates.sort(key=lambda item: (not item["_matched_hint"], item["device_id"]))
        chosen_c = dict(climate_candidates[0])
        chosen_c.pop("_matched_hint", None)
        climate = chosen_c

    return heating, climate, lights


async def _fetch_local_overview(local_host: str, pin_required: bool) -> dict[str, Any]:
    base = local_host if local_host.startswith(("http://", "https://")) else f"http://{local_host}"
    now = _utc_now()
    try:
        async with httpx.AsyncClient(timeout=4.0) as client:
            info_resp = await client.get(f"{base}/rpc/Shelly.GetDeviceInfo")
            info_resp.raise_for_status()
            info = info_resp.json()

            status_resp = await client.get(f"{base}/rpc/Shelly.GetStatus")
            status_resp.raise_for_status()
            st = status_resp.json()

            climate_obj: Optional[dict[str, Any]] = None
            try:
                kvs_resp = await client.get(f"{base}/rpc/KVS.Get", params={"key": "blu_ht_latest"})
                if kvs_resp.status_code == 200:
                    raw_val = kvs_resp.json().get("value")
                    parsed = json.loads(raw_val) if isinstance(raw_val, str) else raw_val
                    if isinstance(parsed, dict):
                        climate_obj = {
                            "device_id": str(parsed.get("mac") or "blu-ht"),
                            "name": "Capteur Salon (H&T)",
                            "model": "Shelly BLU H&T",
                            "temperature_c": _to_float(parsed.get("t")),
                            "humidity_pct": _to_float(parsed.get("h")),
                            "battery_pct": _to_int(parsed.get("b")),
                            "online": True,
                            "updated_at": str(parsed.get("ts") or now),
                        }
            except Exception:
                climate_obj = None

        _, is_on, relay_temp, timer_rem = _extract_switch_state(st)
        dev_id = _normalize_id(str(info.get("mac") or info.get("id") or DEFAULT_HEATING_DEVICE_ID))
        heating = {
            "device_id": dev_id,
            "name": str(info.get("name") or "Chauffage gaz"),
            "model": str(info.get("model") or "S3SW-001X16EU"),
            "channel": 0,
            "is_on": bool(is_on),
            "online": True,
            "relay_temp_c": relay_temp,
            "rssi": _extract_rssi(st),
            "timer_remaining_sec": timer_rem,
            "updated_at": now,
        }
        return {
            "configured": True,
            "source": "local",
            "server_uri": base,
            "online": True,
            "pin_required": pin_required,
            "fetched_at": now,
            "error": "",
            "heating": heating,
            "climate": climate_obj,
            "lights": [],
        }
    except Exception as exc:
        return {
            "configured": True,
            "source": "local",
            "server_uri": base,
            "online": False,
            "pin_required": pin_required,
            "fetched_at": now,
            "error": f"Shelly local injoignable ({str(exc)[:120]})",
            "heating": None,
            "climate": None,
            "lights": [],
        }


async def fetch_domotique_overview(*, force: bool = False) -> dict[str, Any]:
    global _CACHE_TS, _CACHE_DATA

    pin_required = bool(os.environ.get("DUO_PIN", "").strip())
    cfg = get_shelly_config()
    auth_key = cfg["auth_key"]
    server_uri = cfg["server_uri"]
    local_host = cfg["local_host"]

    if not auth_key and not local_host:
        return {
            "configured": False,
            "source": "unconfigured",
            "server_uri": server_uri,
            "online": False,
            "pin_required": pin_required,
            "fetched_at": _utc_now(),
            "error": "",
            "heating": None,
            "climate": None,
            "lights": [],
        }

    if not force and _CACHE_DATA is not None and (time.monotonic() - _CACHE_TS) < CACHE_TTL_SECONDS:
        cached = dict(_CACHE_DATA)
        cached["pin_required"] = pin_required
        return cached

    if not auth_key and local_host:
        result = await _fetch_local_overview(local_host, pin_required)
        _CACHE_TS = time.monotonic()
        _CACHE_DATA = result
        return result

    now = _utc_now()
    url = f"{server_uri}/device/all_status"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                url,
                data={"auth_key": auth_key, "show_info": "true"},
            )
            if resp.status_code == 401:
                raise RuntimeError("Clé Shelly Cloud (SHELLY_AUTH_KEY) refusée")
            if resp.status_code == 429:
                raise RuntimeError("Limite Shelly Cloud atteinte — réessayez dans 2 s")
            resp.raise_for_status()
            body = resp.json()

        if not isinstance(body, dict) or not body.get("isok"):
            err_detail = body.get("errors") if isinstance(body, dict) else "Réponse invalide"
            raise RuntimeError(f"Erreur Shelly Cloud : {err_detail}")

        data = body.get("data") or {}
        devices_status = data.get("devices_status") if isinstance(data, dict) else {}
        if not isinstance(devices_status, dict):
            devices_status = {}

        heating, climate, lights = parse_cloud_devices_status(
            devices_status,
            heating_id_hint=cfg["heating_id"],
            climate_id_hint=cfg["climate_id"],
        )

        any_online = bool(
            (heating and heating.get("online"))
            or (climate and climate.get("online"))
            or any(item.get("online") for item in lights)
        )
        result = {
            "configured": True,
            "source": "cloud",
            "server_uri": server_uri,
            "online": any_online,
            "pin_required": pin_required,
            "fetched_at": now,
            "error": "",
            "heating": heating,
            "climate": climate,
            "lights": lights,
        }
        _CACHE_TS = time.monotonic()
        _CACHE_DATA = result
        return result
    except Exception as exc:
        return {
            "configured": True,
            "source": "cloud",
            "server_uri": server_uri,
            "online": False,
            "pin_required": pin_required,
            "fetched_at": now,
            "error": _sanitize_error(str(exc), auth_key),
            "heating": _CACHE_DATA.get("heating") if _CACHE_DATA else None,
            "climate": _CACHE_DATA.get("climate") if _CACHE_DATA else None,
            "lights": _CACHE_DATA.get("lights", []) if _CACHE_DATA else [],
        }


async def control_shelly_device(
    *,
    device_id: str,
    kind: str,
    channel: int,
    on: bool,
    brightness: Optional[int] = None,
    timer_minutes: Optional[int] = None,
) -> dict[str, Any]:
    cfg = get_shelly_config()
    auth_key = cfg["auth_key"]
    server_uri = cfg["server_uri"]
    local_host = cfg["local_host"]
    timer_sec = int(timer_minutes * 60) if (on and timer_minutes) else None

    if not auth_key and not local_host:
        raise RuntimeError("SHELLY_AUTH_KEY non configuré sur le serveur")

    if not auth_key and local_host:
        base = local_host if local_host.startswith(("http://", "https://")) else f"http://{local_host}"
        params: dict[str, Any] = {"id": channel, "on": "true" if on else "false"}
        if timer_sec:
            params["toggle_after"] = timer_sec
        async with httpx.AsyncClient(timeout=6.0) as client:
            resp = await client.get(f"{base}/rpc/Switch.Set", params=params)
            resp.raise_for_status()
        invalidate_cache()
        return await fetch_domotique_overview(force=True)

    target_id = _normalize_id(device_id) or cfg["heating_id"]
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            if kind == "light":
                v2_payload: dict[str, Any] = {
                    "id": target_id,
                    "channel": channel,
                    "ison": bool(on),
                }
                if brightness is not None:
                    v2_payload["brightness"] = int(brightness)
                resp = await client.post(
                    f"{server_uri}/v2/devices/api/set/light",
                    params={"auth_key": auth_key},
                    json=v2_payload,
                )
                if resp.status_code in (400, 404, 405, 501):
                    v1_form: dict[str, Any] = {
                        "id": target_id,
                        "auth_key": auth_key,
                        "channel": channel,
                        "turn": "on" if on else "off",
                    }
                    if brightness is not None:
                        v1_form["brightness"] = int(brightness)
                    resp = await client.post(f"{server_uri}/device/light/control", data=v1_form)
            else:
                v2_payload = {
                    "id": target_id,
                    "channel": channel,
                    "on": bool(on),
                }
                if timer_sec:
                    v2_payload["toggle_after"] = timer_sec
                resp = await client.post(
                    f"{server_uri}/v2/devices/api/set/switch",
                    params={"auth_key": auth_key},
                    json=v2_payload,
                )
                if resp.status_code in (400, 404, 405, 501):
                    v1_form = {
                        "id": target_id,
                        "auth_key": auth_key,
                        "channel": channel,
                        "turn": "on" if on else "off",
                    }
                    if timer_sec:
                        v1_form["timer"] = timer_sec
                    resp = await client.post(f"{server_uri}/device/relay/control", data=v1_form)

            if resp.status_code == 401:
                raise RuntimeError("Clé Shelly Cloud (SHELLY_AUTH_KEY) refusée")
            if resp.status_code == 429:
                raise RuntimeError("Limite Shelly Cloud atteinte — réessayez dans 2 s")
            resp.raise_for_status()
            body = resp.json()
            if isinstance(body, dict) and body.get("isok") is False:
                raise RuntimeError(f"Commande refusée par Shelly Cloud : {body.get('errors') or body}")
    except Exception as exc:
        raise RuntimeError(_sanitize_error(str(exc), auth_key)) from exc

    invalidate_cache()
    overview = await fetch_domotique_overview(force=True)
    # Optimistically reflect commanded state if Shelly Cloud status lags by a few hundred ms
    if kind == "switch" and overview.get("heating") and _normalize_id(overview["heating"]["device_id"]) == target_id:
        overview["heating"]["is_on"] = bool(on)
        if timer_sec:
            overview["heating"]["timer_remaining_sec"] = timer_sec
        elif not on:
            overview["heating"]["timer_remaining_sec"] = None
    else:
        for item in overview.get("lights", []):
            if _normalize_id(item.get("device_id", "")) == target_id:
                item["is_on"] = bool(on)
                if brightness is not None:
                    item["brightness"] = int(brightness)
    global _CACHE_TS, _CACHE_DATA
    _CACHE_TS = time.monotonic()
    _CACHE_DATA = overview
    return overview
