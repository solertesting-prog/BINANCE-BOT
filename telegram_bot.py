"""Comandos por Telegram: controlar el bot desde el chat donde llegan los avisos.

    /estado      capital, resultado, posiciones y si está en marcha
    /posiciones  detalle de las posiciones abiertas
    /parar       detiene el bot (las posiciones abiertas mantienen su stop en el exchange)
    /arrancar    vuelve a ponerlo en marcha
    /ayuda       esta lista

Solo obedece al chat configurado en el panel (🔔 Avisos): cualquier otra persona que escriba
al bot es ignorada. Al arrancar se descartan los mensajes antiguos, para no ejecutar órdenes viejas.
"""
import json
import logging

import requests

import telegram_setup

log = logging.getLogger("bot")
API = "https://api.telegram.org/bot{token}/{method}"
COMMANDS = [("estado", "Capital, resultado y posiciones"), ("posiciones", "Detalle de las posiciones"),
            ("parar", "Detener el bot"), ("arrancar", "Poner el bot en marcha"), ("ayuda", "Lista de comandos")]


def _n(v, d=2):
    if v is None:
        return "—"
    return f"{v:,.{d}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _pct(v):
    return "—" if v is None else ("+" if v > 0 else "") + _n(v * 100) + " %"


def handle(app, text: str) -> str:
    """Respuesta a un mensaje del dueño del bot."""
    cmd = (text or "").strip().split()[0].lower().split("@")[0] if (text or "").strip() else ""
    e = app.engine
    if cmd in ("/start", "/ayuda", "/help"):
        return "🤖 Valorize Bot\n" + "\n".join(f"/{c} — {d}" for c, d in COMMANDS)
    if cmd == "/estado":
        s = e.snapshot()
        mode = "simulado" if s["mode"] == "paper" else ("testnet" if s["testnet"] else "REAL")
        state = "⛔ detenido por seguridad" if s["halted"] else ("🟢 en marcha" if s["running"] else "⏸ parado")
        lines = [f"{state} · {s['exchange_name']} · {mode}",
                 f"Capital: {_n(s['equity'])} {s['quote']} ({_pct(s['pnl_total_pct'])} desde el inicio)",
                 f"Posiciones: {len(s['positions'])}/{s['max_positions']} · Operaciones cerradas: {s['trades_count']}"]
        for p in s["positions"]:
            lines.append(f"• {p['symbol']} {_pct(p['pnl_pct'])} (stop {_n(p['stop'], 4 if p['price'] < 10 else 2)})")
        if s["last_error"]:
            lines.append(f"⚠️ Último error: {s['last_error'][:200]}")
        return "\n".join(lines)
    if cmd == "/posiciones":
        pos = e.snapshot()["positions"]
        if not pos:
            return "No hay posiciones abiertas."
        return "\n\n".join(
            f"{p['symbol']}\nEntrada {_n(p['entry'], 4 if p['entry'] < 10 else 2)} · ahora {_n(p['price'], 4 if p['price'] < 10 else 2)}\n"
            f"Resultado {_pct(p['pnl_pct'])} ({_n(p['pnl_usdt'])})\n"
            f"{p['stop_kind'].capitalize()} {_n(p['stop'], 4 if p['price'] < 10 else 2)}"
            f"{' · puesto en el exchange' if p['exchange_stop'] else ''}" for p in pos)
    if cmd == "/parar":
        if not e.is_running():
            return "El bot ya estaba parado."
        e.stop(notify_user=False)
        log.info("Bot parado desde Telegram.")
        return "■ Bot parado. Las posiciones abiertas conservan su stop. Para seguir: /arrancar"
    if cmd == "/arrancar":
        if e.is_running():
            return "El bot ya está en marcha."
        try:
            e.start()                          # ya envía "🤖 Valorize Bot iniciado"
        except (Exception, SystemExit) as ex:
            return f"No se pudo arrancar: {ex}"
        log.info("Bot arrancado desde Telegram.")
        return ""
    return "No conozco ese comando. Escribe /ayuda"


def _call(token, method, http_timeout=35, **params):
    r = requests.post(API.format(token=token, method=method), data=params, timeout=http_timeout)
    return r.json()


def listener(app, stop_event):
    """Hilo del panel: lee los mensajes del bot de Telegram y responde a los comandos."""
    current, offset = None, None
    while not stop_event.is_set():
        token, chat = telegram_setup.saved()
        if not (token and chat):
            current = None
            stop_event.wait(30)
            continue
        try:
            if token != current:               # bot nuevo: descarta mensajes antiguos y pon el menú
                old = _call(token, "getUpdates", http_timeout=15, timeout=0).get("result") or []
                offset = old[-1]["update_id"] + 1 if old else None
                _call(token, "setMyCommands", http_timeout=15,
                      commands=json.dumps([{"command": c, "description": d} for c, d in COMMANDS]))
                current = token
            params = {"timeout": 25, "allowed_updates": '["message"]'}
            if offset is not None:
                params["offset"] = offset
            res = _call(token, "getUpdates", **params)
            if not res.get("ok"):
                stop_event.wait(10)            # p. ej. 409 si otro proceso lee el mismo bot
                continue
            for u in res.get("result", []):
                offset = u["update_id"] + 1
                msg = u.get("message") or {}
                if str((msg.get("chat") or {}).get("id")) != str(chat) or not msg.get("text"):
                    continue
                try:
                    reply = handle(app, msg["text"])
                except Exception as ex:
                    log.exception("Error atendiendo un comando de Telegram")
                    reply = f"Error: {ex}"
                if reply:
                    _call(token, "sendMessage", http_timeout=15, chat_id=chat, text=reply)
        except (requests.RequestException, ValueError) as ex:
            log.debug(f"Telegram: {ex}")
            stop_event.wait(15)
