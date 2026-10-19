"""Asistente de configuración del panel: exchanges, mercados, prueba de conexión y guardado.

Las claves se guardan SOLO en el archivo .env de este ordenador (nunca en settings.json ni en
GitHub) y el panel nunca las devuelve completas: solo muestra los 4 últimos caracteres.
"""
import json
import shutil
import threading
import time
from collections import Counter

from dotenv import dotenv_values, set_key

import config as C
import exchange as xch

PREFERRED_QUOTES = ["USDT", "USDC", "EUR", "USD", "FDUSD", "JPY", "GBP", "BTC"]
FRIENDLY_ERRORS = {
    "AuthenticationError": "Las claves no son correctas (revisa que estén completas y sin espacios).",
    "PermissionDenied": "Las claves no tienen permiso suficiente: activa 'lectura' y 'trading spot'.",
    "AccountSuspended": "La cuenta del exchange está suspendida o restringida.",
    "AccountNotEnabled": "La cuenta no tiene activado el trading spot o la API.",
    "InvalidNonce": "El reloj del ordenador no está en hora. Sincronízalo (Configuración → Hora) y repite.",
    "RateLimitExceeded": "Demasiadas peticiones seguidas. Espera un minuto y vuelve a probar.",
    "ExchangeNotAvailable": "El exchange no responde ahora mismo (mantenimiento o bloqueo por país).",
    "NetworkError": "No se pudo conectar con el exchange. Revisa tu conexión a internet.",
}
_cache = {}
_lock = threading.Lock()


def masked(value: str) -> str:
    return "•••• " + value[-4:] if value and len(value) > 6 else ("••••" if value else "")


def friendly(e: Exception) -> str:
    for cls in type(e).__mro__:
        if cls.__name__ in FRIENDLY_ERRORS:
            return FRIENDLY_ERRORS[cls.__name__]
    return f"{type(e).__name__}: {str(e)[:250]}"


# ---------- claves guardadas ----------
def stored_credentials(exchange_id: str, testnet: bool) -> dict:
    """Claves ya guardadas en .env para ese exchange y modo (nombres de ccxt)."""
    vals = dotenv_values(C.ENV_FILE) if C.ENV_FILE.exists() else {}
    out = {}
    for key, field in C.CRED_FIELDS.items():
        v = vals.get(C.env_name(exchange_id, field, testnet))
        if not v and testnet:
            v = vals.get(C.env_name(exchange_id, field))
        if v:
            out[key] = v.strip()
    return out


# ---------- información ----------
def catalog() -> dict:
    featured = []
    for ex_id, name in xch.FEATURED:
        try:
            info = xch.exchange_info(ex_id)
        except (SystemExit, Exception):
            continue
        info["name"] = name
        featured.append(info)
    ids = {f["id"] for f in featured}
    return {"featured": featured, "others": [i for i in xch.all_exchange_ids() if i not in ids]}


def current(cfg) -> dict:
    return {
        "configured": C.SETTINGS_FILE.exists(),
        "current": {"exchange": cfg.exchange, "mode": cfg.mode, "testnet": cfg.testnet,
                    "symbols": list(cfg.symbols), "timeframe": cfg.timeframe,
                    "risk_per_trade": cfg.risk_per_trade, "paper_balance": cfg.paper_balance},
        "saved_credentials": {k: masked(v) for k, v in stored_credentials(cfg.exchange, cfg.testnet).items()},
    }


def saved_for(exchange_id: str, testnet: bool) -> dict:
    return {k: masked(v) for k, v in stored_credentials(exchange_id, testnet).items()}


def markets(exchange_id: str, testnet: bool) -> dict:
    """Mercados spot activos del exchange (con caché de 10 minutos)."""
    key = (exchange_id, testnet)
    with _lock:
        hit = _cache.get(key)
        if hit and time.time() - hit[0] < 600:
            return hit[1]
    ex = xch.make_exchange(C.Config(exchange=exchange_id, testnet=testnet))
    try:
        ms = ex.load_markets()
    except Exception as e:
        raise RuntimeError(friendly(e))
    rows = [{"symbol": s, "base": m.get("base"), "quote": m.get("quote"), "taker": m.get("taker")}
            for s, m in ms.items()
            if m.get("spot") and m.get("active") is not False and "/" in s and ":" not in s]
    counts = Counter(r["quote"] for r in rows)
    quotes = sorted(counts, key=lambda q: (PREFERRED_QUOTES.index(q) if q in PREFERRED_QUOTES else 99, -counts[q]))
    data = {"markets": rows, "quotes": [{"quote": q, "count": counts[q]} for q in quotes]}
    with _lock:
        _cache[key] = (time.time(), data)
    return data


def test_connection(exchange_id: str, testnet: bool, creds: dict) -> dict:
    full = {**stored_credentials(exchange_id, testnet), **{k: v.strip() for k, v in creds.items() if v and v.strip()}}
    try:
        ex = xch.make_exchange(C.Config(exchange=exchange_id, testnet=testnet), private=True, credentials=full)
        ex.load_markets()
        bal = ex.fetch_balance()
    except SystemExit as e:
        return {"ok": False, "error": str(e)}
    except Exception as e:
        return {"ok": False, "error": friendly(e)}
    totals = [{"asset": a, "total": v} for a, v in (bal.get("total") or {}).items() if v]
    totals.sort(key=lambda x: (x["asset"] not in PREFERRED_QUOTES, x["asset"]))
    return {"ok": True, "name": ex.name, "balances": totals[:12]}


# ---------- guardar ----------
def validate_and_save(engine, body: dict) -> bool:
    """Valida lo elegido en el asistente y lo guarda (.env + settings.json).

    Devuelve True si cambia el "lugar" donde opera (exchange, modo o testnet)."""
    ex_id = str(body.get("exchange", "")).strip()
    mode = body.get("mode")
    testnet = bool(body.get("testnet")) and mode == "live"
    if mode not in ("paper", "live"):
        raise ValueError("Elige un modo: simulado o real.")
    info = xch.exchange_info(ex_id)
    if not info["compatible"]:
        raise ValueError(f"{info['name']}: {info['reason']}")
    if testnet and not info["testnet"]:
        raise ValueError(f"{info['name']} no tiene testnet.")

    symbols = [str(s).strip().upper() for s in body.get("symbols") or [] if str(s).strip()]
    if not symbols:
        raise ValueError("Elige al menos una moneda.")
    if len(symbols) > 10:
        raise ValueError("Como máximo 10 monedas.")
    if len({s.split("/")[1] for s in symbols}) > 1:
        raise ValueError("Todas las monedas deben cotizar contra lo mismo (p. ej. todas en USDT o todas en EUR).")
    timeframe = body.get("timeframe", "4h")
    if timeframe not in info["timeframes"]:
        raise ValueError(f"{info['name']} no ofrece velas de {timeframe}.")
    risk = float(body.get("risk_per_trade", 0.01))
    if not 0.001 <= risk <= 0.05:
        raise ValueError("El riesgo por operación debe estar entre 0,1 % y 5 %.")
    paper_balance = float(body.get("paper_balance") or 1000)
    if paper_balance <= 0:
        raise ValueError("El saldo simulado debe ser mayor que cero.")

    mk = markets(ex_id, testnet)
    by_symbol = {m["symbol"]: m for m in mk["markets"]}
    missing = [s for s in symbols if s not in by_symbol]
    if missing:
        raise ValueError(f"{info['name']} no tiene: {', '.join(missing)}")

    creds = {k: v.strip() for k, v in (body.get("credentials") or {}).items()
             if k in C.CRED_FIELDS and isinstance(v, str) and v.strip()}
    if mode == "live":
        have = {**stored_credentials(ex_id, testnet), **creds}
        need = [c["label"] for c in info["credentials"] if not have.get(c["key"])]
        if need:
            raise ValueError(f"Faltan claves: {', '.join(need)}.")

    cur, positions = engine.cfg, engine.state["positions"]
    venue_changed = (ex_id, mode, testnet) != (cur.exchange, cur.mode, cur.testnet)
    if positions and venue_changed:
        raise ValueError("Hay posiciones abiertas. Ciérralas antes de cambiar de exchange o de modo.")
    kept = [s for s in positions if s not in symbols]
    if kept:
        raise ValueError(f"No puedes quitar {', '.join(kept)}: tiene una posición abierta.")

    # .env (modo y claves)
    if not C.ENV_FILE.exists():
        example = C.ROOT / ".env.example"
        shutil.copy(example, C.ENV_FILE) if example.exists() else C.ENV_FILE.touch()
    set_key(str(C.ENV_FILE), "MODE", mode, quote_mode="never")
    set_key(str(C.ENV_FILE), "TESTNET", "true" if testnet else "false", quote_mode="never")
    for k, v in creds.items():
        set_key(str(C.ENV_FILE), C.env_name(ex_id, C.CRED_FIELDS[k], testnet), v, quote_mode="never")

    # settings.json (lo demás)
    settings = C.read_settings()
    taker = by_symbol[symbols[0]].get("taker")
    settings.update({"exchange": ex_id, "symbols": symbols, "timeframe": timeframe, "risk_per_trade": risk,
                     "paper_balance": paper_balance, "fee": float(taker) if taker else 0.001})
    tmp = C.SETTINGS_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(settings, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(C.SETTINGS_FILE)
    return venue_changed
