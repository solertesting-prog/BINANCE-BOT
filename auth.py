"""Acceso con contraseña al panel, para poder usarlo por internet (en un servidor).

- Sin contraseña configurada, el panel solo funciona en este ordenador (como siempre).
- Con contraseña (PANEL_PASSWORD_HASH en .env), pide iniciar sesión. Se crea con:
      python panel.py --set-password
- La contraseña se guarda solo como "hash" (scrypt): ni siquiera el archivo .env la contiene.
- Tras 5 intentos fallidos desde la misma IP, se bloquea 15 minutos.
- PANEL_HOSTS en .env: dominios desde los que se permite abrir el panel (p. ej. el del servidor).
"""
import hashlib
import hmac
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
_sessions = {}            # token -> caducidad (epoch)
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
        _sessions.clear()                  # cambiar la contraseña cierra todas las sesiones


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
        token = secrets.token_urlsafe(32)
        _sessions[token] = now + SESSION_HOURS * 3600
        for t, exp in list(_sessions.items()):     # limpia sesiones caducadas
            if exp < now:
                _sessions.pop(t, None)
        return token


def check(token: str) -> bool:
    if not token:
        return False
    with _lock:
        exp = _sessions.get(token)
        if exp and exp > time.time():
            return True
        _sessions.pop(token, None)
        return False


def logout(token: str):
    with _lock:
        _sessions.pop(token, None)
