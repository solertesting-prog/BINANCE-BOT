"""Avisos por Telegram desde el panel: conectar el bot de Telegram del usuario sin tocar archivos.

Flujo: el usuario crea su bot con @BotFather, pega el token y le escribe un mensaje.
Aquí se comprueba el token (getMe), se detecta su chat (getUpdates), se envía un mensaje
de prueba y se guardan TELEGRAM_TOKEN y TELEGRAM_CHAT_ID en .env.
"""
import re
import shutil

import requests
from dotenv import dotenv_values, set_key, unset_key

import config as C

API = "https://api.telegram.org/bot{token}/{method}"
TOKEN_RE = re.compile(r"^\d{5,15}:[A-Za-z0-9_-]{30,60}$")


class TelegramError(Exception):
    pass


def _call(token: str, method: str, **params) -> dict:
    try:
        r = requests.post(API.format(token=token, method=method), data=params, timeout=15)
        j = r.json()
    except requests.RequestException:
        raise TelegramError("No se pudo conectar con Telegram. Revisa la conexión a internet.")
    except ValueError:
        raise TelegramError("Telegram ha respondido algo inesperado. Prueba de nuevo en un minuto.")
    if not j.get("ok"):
        code = j.get("error_code")
        if code in (401, 404):
            raise TelegramError("El token no es válido. Cópialo entero desde el mensaje de @BotFather.")
        if code == 403:
            raise TelegramError("El bot no puede escribirte: abre el chat con tu bot en Telegram y pulsa «Iniciar».")
        raise TelegramError(f"Telegram: {j.get('description', 'error desconocido')}")
    return j["result"]


def _env() -> dict:
    return dotenv_values(C.ENV_FILE) if C.ENV_FILE.exists() else {}


def status() -> dict:
    v = _env()
    token, chat = (v.get("TELEGRAM_TOKEN") or "").strip(), (v.get("TELEGRAM_CHAT_ID") or "").strip()
    return {"configured": bool(token and chat),
            "token_hint": ("•••• " + token[-4:]) if token else "",
            "chat_id": chat}


def _find_chat(token: str):
    """Último chat privado que ha escrito al bot (o grupo, si no hay privados)."""
    updates = _call(token, "getUpdates", limit=100, timeout=0)
    found = None
    for u in reversed(updates):
        msg = u.get("message") or u.get("edited_message") or u.get("my_chat_member") or {}
        chat = msg.get("chat")
        if not chat:
            continue
        if chat.get("type") == "private":
            return chat
        found = found or chat
    return found


def connect(token: str, chat_id: str = "") -> dict:
    """Comprueba el token, detecta el chat, envía un mensaje de prueba y lo guarda."""
    token = (token or "").strip()
    if not token:                                     # reutiliza el guardado (p. ej. tras escribir al bot)
        token = (_env().get("TELEGRAM_PENDING_TOKEN") or _env().get("TELEGRAM_TOKEN") or "").strip()
    if not TOKEN_RE.match(token):
        raise TelegramError("Eso no parece un token de Telegram. Tiene esta forma: 123456789:AAH...")
    me = _call(token, "getMe")
    username = me.get("username", "")
    chat_id = str(chat_id or "").strip()
    name = ""
    if not chat_id:
        chat = _find_chat(token)
        if not chat:
            _ensure_env()
            set_key(str(C.ENV_FILE), "TELEGRAM_PENDING_TOKEN", token, quote_mode="never")
            return {"ok": True, "configured": False, "need_message": True, "bot": username,
                    "link": f"https://t.me/{username}" if username else ""}
        chat_id = str(chat["id"])
        name = chat.get("first_name") or chat.get("title") or ""
    _call(token, "sendMessage", chat_id=chat_id,
          text="✅ Valorize Bot conectado. A partir de ahora te avisaré aquí de cada compra, venta y problema.")
    _ensure_env()
    set_key(str(C.ENV_FILE), "TELEGRAM_TOKEN", token, quote_mode="never")
    set_key(str(C.ENV_FILE), "TELEGRAM_CHAT_ID", chat_id, quote_mode="never")
    if "TELEGRAM_PENDING_TOKEN" in _env():
        unset_key(str(C.ENV_FILE), "TELEGRAM_PENDING_TOKEN")
    return {"ok": True, **status(), "bot": username, "name": name}


def saved() -> tuple:
    v = _env()
    return (v.get("TELEGRAM_TOKEN") or "").strip(), (v.get("TELEGRAM_CHAT_ID") or "").strip()


def test() -> dict:
    v = _env()
    token, chat = (v.get("TELEGRAM_TOKEN") or "").strip(), (v.get("TELEGRAM_CHAT_ID") or "").strip()
    if not (token and chat):
        raise TelegramError("Los avisos por Telegram no están configurados.")
    _call(token, "sendMessage", chat_id=chat, text="🔔 Mensaje de prueba de Valorize Bot.")
    return {"ok": True}


def remove() -> dict:
    for k in ("TELEGRAM_TOKEN", "TELEGRAM_CHAT_ID", "TELEGRAM_PENDING_TOKEN"):
        if C.ENV_FILE.exists() and k in _env():
            set_key(str(C.ENV_FILE), k, "", quote_mode="never") if k != "TELEGRAM_PENDING_TOKEN" \
                else unset_key(str(C.ENV_FILE), k)
    return {"ok": True, **status()}


def _ensure_env():
    if not C.ENV_FILE.exists():
        example = C.ROOT / ".env.example"
        shutil.copy(example, C.ENV_FILE) if example.exists() else C.ENV_FILE.touch()
