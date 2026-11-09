"""Acceso con contraseña al panel, para poder usarlo por internet (en un servidor).

- Sin contraseña configurada, el panel solo funciona en este ordenador (como siempre).
- Con contraseña (PANEL_PASSWORD_HASH en .env), pide iniciar sesión. Se crea con:
      python panel.py --set-password
- La contraseña se guarda solo como "hash" (scrypt): ni siquiera el archivo .env la contiene.
- Tras 5 intentos fallidos desde la misma IP, se bloquea 15 minutos.
- PANEL_HOSTS en .env: dominios desde los que se permite abrir el panel (p. ej. el del servidor).
- Las sesiones sobreviven a reinicios y actualizaciones: se guardan en sessions.json (solo una
  huella de cada sesión, no la sesión en sí) y caducan todas si cambia la contraseña.
"""
import hashlib
import hmac
import json
import os
import secrets
import threading
import time

from dotenv import dotenv_values, set_key

import config as C

SESSION_HOURS = 24 * 7
MAX_FAILS = 5
LOCK_MINUTES = 15
MIN_LENGTH = 10
LOCAL_HOSTS = {"127.0.0.1", "localhost"}
_sessions = {}            # huella del token -> caducidad (epoch)
_loaded_for = None        # archivo de sesiones ya cargado
_fails = {}               # ip -> [nº de fallos, bloqueado hasta]
_lock = threading.Lock()


class AuthError(Exception):
    pass


def _setting(name: str) -> str:
    vals = dotenv_values(C.ENV_FILE) if C.ENV_FILE.exists() else {}
    return (vals.get(name) or os.getenv(name) or "").strip()


def password_hash() -> str:
    return _setting("PANEL_PASSWORD_HASH")


def enabled() -> bool:
    return bool(password_hash())


def allowed_hosts() -> set:
    extra = {h.strip().lower() for h in _setting("PANEL_HOSTS").split(",") if h.strip()}
    return LOCAL_HOSTS | extra


def unsafe_config() -> bool:
    """True si se permiten dominios externos sin contraseña (no se debe arrancar así)."""
    return bool(allowed_hosts() - LOCAL_HOSTS) and not enabled()


# ---------- sesiones persistentes ----------
def _sessions_file():
    return C.ENV_FILE.parent / "sessions.json"


def _key(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _pw_tag() -> str:
    """Huella de la contraseña actual: si cambia, las sesiones guardadas dejan de valer."""
    return hashlib.sha256(password_hash().encode()).hexdigest()[:16]


def _load():
    """Carga las sesiones guardadas (llamar con _lock)."""
    global _loaded_for
    f = _sessions_file()
    if _loaded_for == f:
        return
    _loaded_for = f
    _sessions.clear()
    try:
        data = json.loads(f.read_text(encoding="utf-8"))
        if data.get("pw") == _pw_tag():
            now = time.time()
            _sessions.update({k: v for k, v in data.get("sessions", {}).items() if v > now})
    except (OSError, ValueError, AttributeError):
        pass


def _save():
    """Guarda las sesiones de forma atómica y privada (llamar con _lock)."""
    f = _sessions_file()
    tmp = f.with_suffix(".tmp")
    try:
        fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump({"pw": _pw_tag(), "sessions": _sessions}, fh)
        os.replace(tmp, f)
    except OSError:
        pass                                   # sin disco: las sesiones siguen en memoria


def make_hash(password: str) -> str:
    salt = secrets.token_bytes(16)
    h = hashlib.scrypt(password.encode(), salt=salt, n=2 ** 14, r=8, p=1, dklen=32)
    return f"scrypt:{salt.hex()}:{h.hex()}"


def verify(password: str, stored: str) -> bool:
    try:
        algo, salt, h = stored.split(":")
        if algo != "scrypt":
            return False
        calc = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt), n=2 ** 14, r=8, p=1, dklen=32)
        return hmac.compare_digest(calc.hex(), h)
    except (ValueError, TypeError):
        return False


def set_password(password: str):
    if len(password) < MIN_LENGTH:
        raise AuthError(f"La contraseña debe tener al menos {MIN_LENGTH} caracteres.")
    if not C.ENV_FILE.exists():
        C.ENV_FILE.touch()
    set_key(str(C.ENV_FILE), "PANEL_PASSWORD_HASH", make_hash(password), quote_mode="never")
    with _lock:
        _load()
        _sessions.clear()                  # cambiar la contraseña cierra todas las sesiones
        _save()


def login(password: str, ip: str) -> str:
    now = time.time()
    with _lock:
        fails, until = _fails.get(ip, [0, 0])
        if until > now:
            raise AuthError(f"Demasiados intentos. Espera {int((until - now) // 60) + 1} min.")
    ok = verify(password or "", password_hash())
    with _lock:
        if not ok:
            fails += 1
            _fails[ip] = [fails, now + LOCK_MINUTES * 60 if fails >= MAX_FAILS else 0]
            if fails >= MAX_FAILS:
                _fails[ip] = [0, now + LOCK_MINUTES * 60]
                raise AuthError(f"Contraseña incorrecta. Acceso bloqueado {LOCK_MINUTES} min.")
            raise AuthError("Contraseña incorrecta.")
        _fails.pop(ip, None)
        _load()
        token = secrets.token_urlsafe(32)
        _sessions[_key(token)] = now + SESSION_HOURS * 3600
        for t, exp in list(_sessions.items()):     # limpia sesiones caducadas
            if exp < now:
                _sessions.pop(t, None)
        _save()
        return token


def check(token: str) -> bool:
    if not token:
        return False
    with _lock:
        _load()
        k = _key(token)
        exp = _sessions.get(k)
        if exp and exp > time.time():
            return True
        if _sessions.pop(k, None):
            _save()
        return False


def logout(token: str):
    with _lock:
        _load()
        if _sessions.pop(_key(token or ""), None):
            _save()
