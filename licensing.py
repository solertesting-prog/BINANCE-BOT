"""Licencias de Valorize Bot (con Lemon Squeezy).

Cómo funciona:
  1. El cliente compra en tu tienda de Lemon Squeezy y recibe una clave de licencia por email.
  2. En el panel la pega y pulsa "Activar": se registra ESTE PC como una activación de la clave
     (Lemon Squeezy limita cuántos PCs puede activar cada licencia).
  3. El bot vuelve a validar la licencia al arrancar y cada 6 horas. Si la suscripción caduca
     o la desactivas en Lemon Squeezy, deja de poder operar con dinero real.
  4. Sin internet, sigue funcionando durante GRACE_HOURS desde la última validación correcta.

CONFIGURACIÓN DEL VENDEDOR (rellena con los datos de tu tienda, ver VENTA_LICENCIAS.md):
"""
import hashlib
import hmac
import json
import platform
import socket
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

import requests

STORE_ID = None          # id de tu tienda en Lemon Squeezy, p. ej. 123456 (None = no comprobar)
PRODUCT_IDS = []         # ids de los productos que dan licencia, p. ej. [654321] ([] = cualquiera de la tienda)
PURCHASE_URL = ""        # enlace de compra que se muestra en el panel
REQUIRE_LICENSE = False  # De momento GRATIS: no se pide licencia. Pon True para empezar a cobrar.
FREE_PAPER_MODE = True   # True = el modo simulado es gratis (prueba); la licencia hace falta para testnet/real
GRACE_HOURS = 72         # horas que funciona sin poder conectar con el servidor de licencias
REVALIDATE_HOURS = 6     # cada cuánto se vuelve a comprobar

API = "https://api.lemonsqueezy.com/v1/licenses"
ROOT = Path(__file__).resolve().parent
LICENSE_FILE = ROOT / "license.json"
_SALT = b"valorize-bot/license/v1"
_lock = threading.Lock()


class LicenseError(RuntimeError):
    """Error de licencia con un mensaje pensado para el usuario."""
    code = "license"


# ---------- utilidades ----------
def fingerprint() -> str:
    """Huella de este ordenador (no contiene datos personales: es un resumen)."""
    raw = f"{uuid.getnode()}|{platform.node()}|{platform.system()}|{platform.machine()}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def instance_name() -> str:
    host = (socket.gethostname() or "PC")[:40]
    return f"{host} · {fingerprint()[:8]}"


def _now() -> float:
    return time.time()


def _sign(data: dict) -> str:
    key = hashlib.sha256(_SALT + fingerprint().encode()).digest()
    return hmac.new(key, json.dumps(data, sort_keys=True).encode(), hashlib.sha256).hexdigest()


def _load() -> dict:
    try:
        blob = json.loads(LICENSE_FILE.read_text(encoding="utf-8"))
        data = blob["data"]
    except (FileNotFoundError, ValueError, KeyError, TypeError):
        return {}
    if not hmac.compare_digest(blob.get("sig", ""), _sign(data)) or data.get("fingerprint") != fingerprint():
        return {}                            # copiado de otro PC o modificado a mano: no vale
    return data


def _save(data: dict):
    data = {**data, "fingerprint": fingerprint()}
    tmp = LICENSE_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps({"data": data, "sig": _sign(data)}, indent=2), encoding="utf-8")
    tmp.replace(LICENSE_FILE)


def _post(endpoint: str, payload: dict) -> dict:
    """Llamada a la API de licencias de Lemon Squeezy. Devuelve el JSON (también en errores 4xx)."""
    r = requests.post(f"{API}/{endpoint}", data=payload, headers={"Accept": "application/json"}, timeout=15)
    try:
        return r.json()
    except ValueError:
        r.raise_for_status()
        raise


def mask_email(email: str) -> str:
    if not email or "@" not in email:
        return email or ""
    user, dom = email.split("@", 1)
    return (user[:2] + "•" * max(1, len(user) - 2)) + "@" + dom


def _check_owner(resp: dict):
    meta = resp.get("meta") or {}
    if STORE_ID is not None and meta.get("store_id") != STORE_ID:
        raise LicenseError("Esta clave no es de Valorize Bot.")
    if PRODUCT_IDS and meta.get("product_id") not in PRODUCT_IDS:
        raise LicenseError("Esta clave es de otro producto.")


def _record(resp: dict, key: str, instance_id: str) -> dict:
    lk, meta = resp.get("license_key") or {}, resp.get("meta") or {}
    return {"key": key, "instance_id": instance_id, "status": lk.get("status"),
            "expires_at": lk.get("expires_at"), "activation_limit": lk.get("activation_limit"),
            "activation_usage": lk.get("activation_usage"), "product": meta.get("product_name"),
            "variant": meta.get("variant_name"), "customer_email": meta.get("customer_email"),
            "customer_name": meta.get("customer_name"), "last_ok": _now(), "last_check": _now(),
            "last_error": None}


# ---------- acciones ----------
def activate(key: str) -> dict:
    key = (key or "").strip()
    if len(key) < 8:
        raise LicenseError("Pega la clave de licencia completa (la recibiste por email al comprar).")
    with _lock:
        try:
            resp = _post("activate", {"license_key": key, "instance_name": instance_name()})
        except requests.RequestException:
            raise LicenseError("No se pudo conectar con el servidor de licencias. Revisa tu conexión a internet.")
        if not resp.get("activated"):
            err = (resp.get("error") or "").lower()
            if "limit" in err:
                raise LicenseError("Esta licencia ya está activada en el máximo de ordenadores. "
                                   "Desactívala en el otro PC (panel → Licencia) y vuelve a intentarlo.")
            if "expired" in err or (resp.get("license_key") or {}).get("status") == "expired":
                raise LicenseError("Esta licencia ha caducado. Renueva la suscripción para seguir usándola.")
            if "disabled" in err:
                raise LicenseError("Esta licencia está desactivada. Contacta con el vendedor.")
            if "not found" in err:
                raise LicenseError("Esa clave de licencia no existe. Revisa que la hayas copiado completa.")
            raise LicenseError("Clave de licencia no válida." + (f" ({resp.get('error')})" if resp.get("error") else ""))
        instance_id = (resp.get("instance") or {}).get("id")
        try:
            _check_owner(resp)
        except LicenseError:                 # clave de otro producto: liberamos la activación
            try:
                _post("deactivate", {"license_key": key, "instance_id": instance_id})
            except requests.RequestException:
                pass
            raise
        data = _record(resp, key, instance_id)
        _save(data)
        return status()


def validate(force: bool = False) -> dict:
    """Vuelve a comprobar la licencia con el servidor (si toca, o siempre con force=True)."""
    with _lock:
        data = _load()
        if not data:
            return status()
        if not force and _now() - data.get("last_check", 0) < REVALIDATE_HOURS * 3600:
            return status()
        data["last_check"] = _now()
        try:
            resp = _post("validate", {"license_key": data["key"], "instance_id": data["instance_id"]})
        except requests.RequestException:
            data["last_error"] = "offline"
            _save(data)
            return status()
        lk = resp.get("license_key") or {}
        inst = resp.get("instance") or {}
        ok = bool(resp.get("valid")) and lk.get("status") == "active" and fingerprint()[:8] in (inst.get("name") or "")
        try:
            if ok:
                _check_owner(resp)
        except LicenseError:
            ok = False
        if ok:
            data.update(_record(resp, data["key"], data["instance_id"]))
        else:
            data.update(status_remote=lk.get("status") or "invalid", last_ok=0,
                        last_error=lk.get("status") or resp.get("error") or "invalid",
                        expires_at=lk.get("expires_at", data.get("expires_at")))
            data["status"] = lk.get("status") or "invalid"
        _save(data)
        return status()


def deactivate() -> dict:
    with _lock:
        data = _load()
        if data:
            try:
                _post("deactivate", {"license_key": data["key"], "instance_id": data["instance_id"]})
            except requests.RequestException:
                raise LicenseError("No se pudo conectar con el servidor de licencias para liberar este PC. "
                                   "Inténtalo con internet.")
        LICENSE_FILE.unlink(missing_ok=True)
        return status()


# ---------- consulta ----------
def status() -> dict:
    """Estado de la licencia SIN conectarse (lo que se sabe de la última comprobación)."""
    base = {"required": REQUIRE_LICENSE, "free_paper": FREE_PAPER_MODE, "purchase_url": PURCHASE_URL,
            "machine": instance_name()}
    if not REQUIRE_LICENSE:
        return {**base, "licensed": True, "state": "not_required", "message": "Licencia no necesaria."}
    data = _load()
    if not data:
        return {**base, "licensed": False, "state": "none", "message": "Sin licencia en este ordenador."}
    age_h = (_now() - data.get("last_ok", 0)) / 3600
    info = {**base, "product": data.get("product"), "variant": data.get("variant"),
            "customer": mask_email(data.get("customer_email")), "expires_at": data.get("expires_at"),
            "key_hint": "…" + data["key"][-6:], "activations": f"{data.get('activation_usage')}/{data.get('activation_limit')}",
            "last_check": datetime.fromtimestamp(data.get("last_check", 0), timezone.utc).strftime("%Y-%m-%d %H:%M UTC")}
    if data.get("status") != "active":
        msg = {"expired": "La licencia ha caducado: renueva la suscripción.",
               "disabled": "La licencia ha sido desactivada."}.get(data.get("status"), "La licencia no es válida.")
        return {**info, "licensed": False, "state": data.get("status") or "invalid", "message": msg}
    if age_h > GRACE_HOURS:
        return {**info, "licensed": False, "state": "offline",
                "message": f"No se ha podido comprobar la licencia en más de {GRACE_HOURS} h. Conéctate a internet."}
    if data.get("last_error") == "offline":
        return {**info, "licensed": True, "state": "grace",
                "message": f"Sin conexión con el servidor de licencias: funciona {GRACE_HOURS - age_h:.0f} h más."}
    return {**info, "licensed": True, "state": "active", "message": "Licencia activa."}


def require(mode: str, testnet: bool = False):
    """Lanza LicenseError si la licencia no permite operar en ese modo."""
    if not REQUIRE_LICENSE or (mode == "paper" and FREE_PAPER_MODE):
        return
    st = validate()                          # revalida si toca (con periodo de gracia sin internet)
    if not st["licensed"]:
        what = "el modo simulado" if mode == "paper" else "operar en testnet" if testnet else "operar con dinero real"
        raise LicenseError(f"Necesitas una licencia activa para {what}. {st['message']}")
