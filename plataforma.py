"""Valorize Bot · Plataforma multiusuario (fase 1: beta privada en modo simulado).

Cada usuario invitado tiene su cuenta, su panel y su propio bot con dinero ficticio y precios
reales. No se usan claves de exchange de los usuarios en esta fase (ni testnet ni dinero real).

    python plataforma.py --port 8766                 # servidor (lo arranca systemd en el servidor)
    python plataforma.py --invitar-admin             # crea un enlace de registro de administrador

Datos: carpeta plataforma-datos/ (base de datos SQLite y una carpeta por usuario).
"""
import argparse
import base64
import json
import logging
import logging.handlers
import os
import secrets
import sys
import threading
import time
from dataclasses import fields, replace
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, quote, urlparse

from dotenv import load_dotenv

import auth
import bot
import config as C
import exchange as xch
import panel
import plataforma_db as pdb
import setup_api
import telegram_setup

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "plataforma-datos"
WEB = ROOT / "web"
COOKIE = "vp_session"
MAX_USERS = int(os.getenv("PLATFORM_MAX_USERS", "25"))
USER_FIELDS = ("exchange", "symbols", "timeframe", "risk_per_trade", "paper_balance", "fee", "market_filter")
log = logging.getLogger("plataforma")


# ---------- datos de mercado compartidos ----------
class SharedMarket:
    """Conexión PÚBLICA a un exchange compartida por todos los usuarios, con caché y bloqueo:
    20 usuarios con BTC no hacen 20 peticiones iguales."""
    TICKER_TTL, OHLCV_TTL = 10, 30

    def __init__(self, ex):
        self._ex, self._lock, self._cache = ex, threading.Lock(), {}
        self._markets_loaded = False

    def __getattr__(self, name):
        return getattr(self._ex, name)

    def _cached(self, key, ttl, fn):
        with self._lock:
            hit = self._cache.get(key)
            if hit and time.time() - hit[0] < ttl:
                return hit[1]
            value = fn()
            self._cache[key] = (time.time(), value)
            if len(self._cache) > 2000:
                self._cache.clear()
            return value

    def load_markets(self, *a, **k):
        with self._lock:
            if not self._markets_loaded:
                self._ex.load_markets()
                self._markets_loaded = True
            return self._ex.markets

    def fetch_ticker(self, symbol, *a, **k):
        return self._cached(("t", symbol), self.TICKER_TTL, lambda: self._ex.fetch_ticker(symbol))

    def fetch_ohlcv(self, symbol, timeframe="1m", since=None, limit=None, *a, **k):
        return self._cached(("o", symbol, timeframe, since, limit), self.OHLCV_TTL,
                            lambda: self._ex.fetch_ohlcv(symbol, timeframe, limit=limit) if since is None
                            else self._ex.fetch_ohlcv(symbol, timeframe, since=since, limit=limit))


_markets, _markets_lock = {}, threading.Lock()


def market(exchange_id: str) -> SharedMarket:
    with _markets_lock:
        if exchange_id not in _markets:
            _markets[exchange_id] = SharedMarket(xch.make_exchange(C.Config(exchange=exchange_id), private=False))
        return _markets[exchange_id]


# ---------- un bot por usuario ----------
def user_dir(uid: int) -> Path:
    d = DATA / "usuarios" / str(int(uid))
    d.mkdir(parents=True, exist_ok=True)
    return d


def read_user_settings(uid) -> dict:
    try:
        return json.loads((user_dir(uid) / "settings.json").read_text(encoding="utf-8"))
    except (FileNotFoundError, ValueError):
        return {}


def user_config(user: dict) -> C.Config:
    """Configuración del usuario: valores por defecto + lo que eligió. Siempre simulado y SIN
    ninguna clave (nunca se mezclan con las del .env del servidor)."""
    names = {f.name for f in fields(C.Config)}
    kw = {k: v for k, v in read_user_settings(user["id"]).items() if k in USER_FIELDS and k in names}
    if "symbols" in kw:
        kw["symbols"] = tuple(kw["symbols"])
    return C.Config(**kw, mode="paper", testnet=False, telegram_token=user.get("telegram_token") or "",
                    telegram_chat_id=user.get("telegram_chat") or "")


def user_logger(uid: int) -> logging.Logger:
    lg = logging.getLogger(f"plataforma.u{int(uid)}")
    if not lg.handlers:
        h = logging.handlers.RotatingFileHandler(user_dir(uid) / "bot.log", maxBytes=1_000_000,
                                                 backupCount=1, encoding="utf-8")
        h.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s", "%Y-%m-%d %H:%M:%S"))
        lg.addHandler(h)
        lg.setLevel(logging.INFO)
        lg.propagate = False
    return lg


class Bots:
    """Motores de los usuarios (se crean al entrar o al arrancar el servidor)."""

    def __init__(self, db):
        self.db, self.apps, self.lock = db, {}, threading.Lock()

    def app(self, user: dict) -> panel.PanelApp:
        with self.lock:
            a = self.apps.get(user["id"])
            if a is None:
                a = self.apps[user["id"]] = self._build(user)
            return a

    def _build(self, user) -> panel.PanelApp:
        cfg = user_config(user)
        files = bot.Files(user_dir(user["id"]), user_logger(user["id"]))
        ex = market(cfg.exchange)
        engine = bot.Engine(cfg, ex, files)
        try:
            engine.connect()
            engine.refresh_prices()
        except (Exception, SystemExit) as e:
            engine.last_error = f"No se pudo conectar con el exchange: {e}"
        return panel.PanelApp(engine, ex)

    def rebuild(self, user):
        """Tras cambiar la configuración o el Telegram: motor nuevo (sigue si estaba en marcha)."""
        with self.lock:
            old = self.apps.pop(user["id"], None)
        was_running = False
        if old:
            was_running = old.engine.is_running()
            if was_running:
                old.engine.stop(notify_user=False)
                old.engine.thread.join(timeout=45)
            bot.save_state(old.engine.state, old.engine.files.state)
        a = self.app(self.db.user(user["id"]))
        if was_running and a.engine.broker is not None:
            a.engine.start()
        return a, was_running

    def stop(self, uid):
        with self.lock:
            a = self.apps.pop(uid, None)
        if a and a.engine.is_running():
            a.engine.stop(notify_user=False)

    def resume_all(self):
        """Al arrancar el servidor, vuelve a poner en marcha los bots que lo estaban."""
        for u in self.db.q("SELECT * FROM users WHERE status='active'"):
            st = bot.load_state(user_config(u), user_dir(u["id"]) / "state.json")
            if st.get("running") and not st.get("halted"):
                try:
                    a = self.app(u)
                    if a.engine.broker is not None:
                        a.engine.start()
                except Exception as e:
                    log.warning(f"No se pudo reanudar el bot del usuario {u['id']}: {e}")

    def summary(self, uid):
        a = self.apps.get(uid)
        if not a:
            return {"running": False}
        e = a.engine
        return {"running": e.is_running(), "equity": e.last_equity, "positions": len(e.state["positions"]),
                "symbols": len(e.cfg.symbols), "last_cycle": e.last_cycle, "error": e.last_error}


def save_user_settings(uid, body: dict):
    """Valida lo elegido en el asistente (solo modo simulado) y lo guarda en la carpeta del usuario."""
    if body.get("mode") != "paper" or body.get("testnet"):
        raise ValueError("De momento la plataforma funciona solo en modo simulado.")
    ex_id = str(body.get("exchange", "")).strip()
    info = xch.exchange_info(ex_id)
    if not info["compatible"]:
        raise ValueError(f"{info['name']}: {info['reason']}")
    symbols = [str(s).strip().upper() for s in body.get("symbols") or [] if str(s).strip()]
    if not symbols or len(symbols) > 10:
        raise ValueError("Elige entre 1 y 10 monedas.")
    if len({s.split("/")[1] for s in symbols}) > 1:
        raise ValueError("Todas las monedas deben cotizar contra lo mismo (p. ej. todas en USDT).")
    timeframe = body.get("timeframe", "4h")
    if timeframe not in info["timeframes"]:
        raise ValueError(f"{info['name']} no ofrece velas de {timeframe}.")
    risk = float(body.get("risk_per_trade", 0.01))
    if not 0.001 <= risk <= 0.05:
        raise ValueError("El riesgo por operación debe estar entre 0,1 % y 5 %.")
    balance = float(body.get("paper_balance") or 1000)
    if not 10 <= balance <= 10_000_000:
        raise ValueError("El saldo simulado debe estar entre 10 y 10.000.000.")
    by_symbol = {m["symbol"]: m for m in setup_api.markets(ex_id, False)["markets"]}
    missing = [s for s in symbols if s not in by_symbol]
    if missing:
        raise ValueError(f"{info['name']} no tiene: {', '.join(missing)}")
    taker = by_symbol[symbols[0]].get("taker")
    data = {"exchange": ex_id, "symbols": symbols, "timeframe": timeframe, "risk_per_trade": risk,
            "paper_balance": balance, "fee": float(taker) if taker else 0.001,
            "market_filter": "BTC" if body.get("market_filter") else ""}
    path = user_dir(uid) / "settings.json"
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
    tmp.replace(path)
    return data


# ---------- servidor web ----------
class Handler(panel.Handler):
    server_version = "ValorizePlataforma"

    @property
    def db(self) -> pdb.DB:
        return self.server.db

    def _host_ok(self) -> bool:
        host = (self.headers.get("Host") or "").rsplit(":", 1)[0].lower()
        allowed = {h.strip().lower() for h in auth._setting("PLATFORM_HOSTS").split(",") if h.strip()}
        return host in allowed | auth.LOCAL_HOSTS

    def _token(self) -> str:
        for part in (self.headers.get("Cookie") or "").split(";"):
            k, _, v = part.strip().partition("=")
            if k == COOKIE:
                return v
        return ""

    def _cookie(self, token: str, max_age: int) -> str:
        return (f"{COOKIE}={token}; Path=/; HttpOnly; SameSite=Strict; Max-Age={max_age}"
                + ("; Secure" if self._https() else ""))

    def _page(self, name):
        return self._send(200, (WEB / name).read_bytes(), "text/html; charset=utf-8")

    def _redirect(self, where):
        self.send_response(302)
        self.send_header("Location", where)
        self.send_header("Content-Length", "0")
        self.end_headers()

    # --- GET ---
    def do_GET(self):
        if not self._host_ok():
            return self._json({"ok": False, "error": "host no permitido"}, 403)
        u = urlparse(self.path)
        q = parse_qs(u.query)
        if u.path in ("/login", "/registro", "/restablecer"):
            return self._page("plataforma_acceso.html")
        if u.path == "/favicon.ico" and (ROOT / "assets" / "bot.ico").exists():
            return self._send(200, (ROOT / "assets" / "bot.ico").read_bytes(), "image/x-icon")
        user = self.db.session_user(self._token())
        if not user:
            if u.path.startswith("/api/"):
                return self._json({"ok": False, "error": "Inicia sesión", "code": "auth"}, 401)
            return self._redirect("/login")
        try:
            if u.path in ("/", "/index.html"):
                return self._page("panel.html")
            if u.path == "/admin":
                return self._page("plataforma_admin.html") if user["role"] == "admin" else self._redirect("/")
            if u.path.startswith("/api/admin/"):
                return self._admin_get(user, u.path)
            app = self.server.bots.app(user)
            e = app.engine
            if u.path == "/api/status":
                self._json({**e.snapshot(), "remote": True, "platform": True, "email": user["email"],
                            "admin": user["role"] == "admin",
                            "license": {"required": False, "state": "not_required"}})
            elif u.path == "/api/candles":
                self._json(app.candles(q.get("symbol", [e.cfg.symbols[0]])[0]))
            elif u.path == "/api/trades":
                self._json(bot.read_trades(e.files.trades)[-200:][::-1])
            elif u.path == "/api/trades/export":
                self._send(200, bot.export_trades_csv(e.files.trades), "text/csv; charset=utf-8",
                           {"Content-Disposition": 'attachment; filename="valorize-operaciones.csv"'})
            elif u.path == "/api/log":
                self._json({"lines": panel.tail(e.files.log_file, 200)})
            elif u.path == "/api/license":
                self._json({"required": False, "state": "not_required"})
            elif u.path == "/api/setup":
                cfg = e.cfg
                self._json({"configured": (user_dir(user["id"]) / "settings.json").exists(), "paper_only": True,
                            "current": {"exchange": cfg.exchange, "mode": "paper", "testnet": False,
                                        "symbols": list(cfg.symbols), "timeframe": cfg.timeframe,
                                        "risk_per_trade": cfg.risk_per_trade, "paper_balance": cfg.paper_balance,
                                        "market_filter": bool(cfg.market_filter)},
                            "saved_credentials": {}, **setup_api.catalog()})
            elif u.path == "/api/setup/exchange":
                self._json({**xch.exchange_info(q["id"][0]), "saved": {}})
            elif u.path == "/api/setup/markets":
                self._json(setup_api.markets(q["id"][0], False))
            elif u.path == "/api/telegram":
                tok = user["telegram_token"]
                self._json({"configured": bool(tok and user["telegram_chat"]),
                            "token_hint": ("•••• " + tok[-4:]) if tok else "", "chat_id": user["telegram_chat"]})
            elif u.path == "/api/security":
                self._json({"remote": True, "totp": bool(user["totp_secret"])})
            elif u.path == "/api/health":
                self._json({"hidden": True})
            elif u.path == "/api/update":
                self._json({"available": False})
            else:
                self._json({"ok": False, "error": "no encontrado"}, 404)
        except Exception as ex:
            log.exception(f"Error en {u.path}")
            self._json({"ok": False, "error": str(ex)}, 500)

    def _admin_get(self, user, path):
        if user["role"] != "admin":
            return self._json({"ok": False, "error": "solo administradores"}, 403)
        if path == "/api/admin/users":
            rows = self.db.users()
            for r in rows:
                r.update(self.server.bots.summary(r["id"]))
            return self._json({"users": rows, "max_users": MAX_USERS, "invites": self.db.invites()})
        return self._json({"ok": False, "error": "no encontrado"}, 404)

    # --- POST ---
    def do_POST(self):
        if not self._host_ok() or self.headers.get("X-Panel") != "1":
            return self._json({"ok": False, "error": "no autorizado"}, 403)
        u = urlparse(self.path)
        q = parse_qs(u.query)
        try:
            length = min(int(self.headers.get("Content-Length") or 0), 65536)
            body = json.loads(self.rfile.read(length) or b"{}") if length else {}
        except ValueError:
            return self._json({"ok": False, "error": "petición no válida"}, 400)
        try:
            return self._post(u, q, body)
        except (pdb.DBError, auth.AuthError, ValueError, telegram_setup.TelegramError) as ex:
            return self._json({"ok": False, "error": str(ex), "need_code": isinstance(ex, pdb.NeedCode)},
                              401 if isinstance(ex, pdb.NeedCode) else 400)
        except (Exception, SystemExit) as ex:
            log.exception(f"Acción {u.path} fallida")
            return self._json({"ok": False, "error": str(ex)}, 400)

    def _post(self, u, q, body):
        db, bots = self.db, self.server.bots
        if u.path == "/api/login":
            token = db.login(body.get("email", ""), str(body.get("password", "")), self._ip(), str(body.get("code", "")))
            return self._json({"ok": True}, headers={"Set-Cookie": self._cookie(token, pdb.SESSION_HOURS * 3600)})
        if u.path == "/api/register":
            if db.count() >= MAX_USERS:
                raise ValueError("La beta está completa. Contacta con el administrador.")
            db.register(str(body.get("invite", "")), str(body.get("email", "")), str(body.get("password", "")))
            token = db.login(body.get("email", ""), str(body.get("password", "")), self._ip())
            log.info(f"Nuevo usuario registrado: {str(body.get('email', '')).strip().lower()}")
            return self._json({"ok": True}, headers={"Set-Cookie": self._cookie(token, pdb.SESSION_HOURS * 3600)})
        if u.path == "/api/reset":
            db.reset_password(str(body.get("token", "")), str(body.get("password", "")))
            return self._json({"ok": True})
        if u.path == "/api/logout":
            db.logout(self._token())
            return self._json({"ok": True}, headers={"Set-Cookie": self._cookie("", 0)})

        user = db.session_user(self._token())
        if not user:
            return self._json({"ok": False, "error": "Inicia sesión", "code": "auth"}, 401)
        if u.path.startswith("/api/admin/"):
            return self._admin_post(user, u.path, body)
        if u.path.startswith("/api/security/totp/"):
            return self._totp(user, u.path.rsplit("/", 1)[1], body)
        if u.path.startswith("/api/telegram/"):
            return self._telegram(user, u.path.rsplit("/", 1)[1], body)
        if u.path == "/api/setup/save":
            save_user_settings(user["id"], body)
            app = bots.app(user)
            if app.engine.state["positions"]:
                kept = [s for s in app.engine.state["positions"] if s not in body.get("symbols", [])]
                if kept or body.get("exchange") != app.engine.cfg.exchange:
                    raise ValueError("Hay posiciones abiertas: ciérralas antes de quitar esas monedas o cambiar de exchange.")
            new_cfg = user_config(user)
            s = app.engine.state
            if not s["positions"] and (new_cfg.paper_balance != app.engine.cfg.paper_balance
                                       or new_cfg.exchange != app.engine.cfg.exchange):
                s.update(paper_usdt=new_cfg.paper_balance, start_equity=None, equity_history=[], last_candle={})
                bot.save_state(s, app.engine.files.state)
            _, restarted = bots.rebuild(user)
            return self._json({"ok": True, "restarted": restarted})
        app = bots.app(user)
        e = app.engine
        if u.path == "/api/start":
            e.start()
        elif u.path == "/api/stop":
            e.stop()
        elif u.path == "/api/close":
            e.close_position(q["symbol"][0])
        elif u.path == "/api/resume":
            e.resume_after_halt()
        else:
            return self._json({"ok": False, "error": "no encontrado"}, 404)
        app.invalidate()
        return self._json({"ok": True})

    def _totp(self, user, what, body):
        db = self.db
        if what == "begin":
            if user["totp_secret"]:
                raise ValueError("La verificación en dos pasos ya está activada.")
            secret = base64.b32encode(secrets.token_bytes(20)).decode().rstrip("=")
            self.server.pending_totp[user["id"]] = secret
            uri = (f"otpauth://totp/{quote('Valorize Bot:' + user['email'])}?secret={secret}"
                   f"&issuer=Valorize%20Bot&digits=6&period=30")
            return self._json({"ok": True, "secret": secret, "uri": uri})
        if what == "confirm":
            secret = self.server.pending_totp.get(user["id"])
            if not secret or not auth.totp_verify(secret, body.get("code", "")):
                raise ValueError("El código no es correcto. Revisa que la hora del móvil esté en automático.")
            db.update(user["id"], totp_secret=secret)
            self.server.pending_totp.pop(user["id"], None)
            return self._json({"ok": True, "totp": True})
        if what == "disable":
            if user["totp_secret"] and not auth.totp_verify(user["totp_secret"], body.get("code", "")):
                raise ValueError("El código no es correcto.")
            db.update(user["id"], totp_secret="")
            return self._json({"ok": True, "totp": False})
        return self._json({"ok": False, "error": "no encontrado"}, 404)

    def _telegram(self, user, what, body):
        db, bots = self.db, self.server.bots
        if what == "connect":
            token = str(body.get("token", "")).strip() or self.server.pending_tg.get(user["id"], "") \
                or user["telegram_token"]
            if not telegram_setup.TOKEN_RE.match(token):
                raise ValueError("Eso no parece un token de Telegram. Tiene esta forma: 123456789:AAH...")
            me = telegram_setup._call(token, "getMe")
            chat = telegram_setup._find_chat(token)
            if not chat:
                self.server.pending_tg[user["id"]] = token
                name = me.get("username", "")
                return self._json({"ok": True, "configured": False, "need_message": True, "bot": name,
                                   "link": f"https://t.me/{name}" if name else ""})
            telegram_setup._call(token, "sendMessage", chat_id=chat["id"],
                                 text="✅ Valorize Bot conectado. Te avisaré aquí de cada compra, venta y problema.")
            db.update(user["id"], telegram_token=token, telegram_chat=str(chat["id"]))
            self.server.pending_tg.pop(user["id"], None)
            bots.rebuild(db.user(user["id"]))
            return self._json({"ok": True, "configured": True, "token_hint": "•••• " + token[-4:],
                               "chat_id": str(chat["id"])})
        if what == "test":
            if not (user["telegram_token"] and user["telegram_chat"]):
                raise ValueError("Los avisos por Telegram no están configurados.")
            telegram_setup._call(user["telegram_token"], "sendMessage", chat_id=user["telegram_chat"],
                                 text="🔔 Mensaje de prueba de Valorize Bot.")
            return self._json({"ok": True})
        if what == "remove":
            db.update(user["id"], telegram_token="", telegram_chat="")
            bots.rebuild(db.user(user["id"]))
            return self._json({"ok": True, "configured": False, "token_hint": "", "chat_id": ""})
        return self._json({"ok": False, "error": "no encontrado"}, 404)

    def _admin_post(self, user, path, body):
        if user["role"] != "admin":
            return self._json({"ok": False, "error": "solo administradores"}, 403)
        db, base = self.db, f"https://{(self.headers.get('Host') or 'localhost')}"
        if path == "/api/admin/invite":
            role = "admin" if body.get("role") == "admin" else "user"
            token = db.create_invite(role, str(body.get("note", "")))
            log.info(f"Invitación creada por {user['email']} ({role})")
            return self._json({"ok": True, "link": f"{base}/registro?invitacion={token}", "days": pdb.INVITE_DAYS})
        uid = int(body.get("user_id", 0))
        target = db.user(uid)
        if not target:
            raise ValueError("Usuario no encontrado.")
        if path == "/api/admin/status":
            if uid == user["id"]:
                raise ValueError("No puedes desactivar tu propia cuenta.")
            status = "disabled" if body.get("status") == "disabled" else "active"
            db.set_status(uid, status)
            if status == "disabled":
                self.server.bots.stop(uid)
            log.info(f"Usuario {target['email']} {'desactivado' if status == 'disabled' else 'activado'} por {user['email']}")
            return self._json({"ok": True})
        if path == "/api/admin/reset":
            token = db.create_reset(uid)
            return self._json({"ok": True, "link": f"{base}/restablecer?codigo={token}", "hours": pdb.RESET_HOURS})
        return self._json({"ok": False, "error": "no encontrado"}, 404)


def _git_head() -> str:
    import subprocess
    try:
        return subprocess.run(["git", "-C", str(ROOT), "rev-parse", "HEAD"], capture_output=True,
                              text=True, timeout=20).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return ""


def restart_on_update(server, every: int = 60):
    """Si el panel principal instala una versión nueva (botón ⬆ Actualizar), la plataforma se
    reinicia sola para usarla: guarda los estados y sale; systemd la vuelve a arrancar."""
    start = _git_head()
    if not start or not os.getenv("INVOCATION_ID"):
        return
    while True:
        time.sleep(every)
        if _git_head() not in ("", start):
            log.info("Versión nueva instalada: reiniciando la plataforma.")
            for app in list(server.bots.apps.values()):
                bot.save_state(app.engine.state, app.engine.files.state)
            os._exit(3)


def make_server(port: int, db: pdb.DB = None, host: str = "127.0.0.1") -> ThreadingHTTPServer:
    server = ThreadingHTTPServer((host, port), Handler)
    server.daemon_threads = True
    server.db = db or pdb.DB(DATA / "valorize.db")
    server.bots = Bots(server.db)
    server.pending_totp, server.pending_tg = {}, {}
    return server


def main():
    p = argparse.ArgumentParser(description="Valorize Bot · plataforma multiusuario")
    p.add_argument("--port", type=int, default=8766)
    p.add_argument("--invitar-admin", action="store_true", help="crea un enlace de registro de administrador")
    p.add_argument("--dominio", default=os.getenv("PLATFORM_HOSTS", "localhost").split(",")[0])
    a = p.parse_args()
    load_dotenv(C.ENV_FILE, override=True)              # PLATFORM_HOSTS y similares
    if a.invitar_admin:
        db = pdb.DB(DATA / "valorize.db")
        token = db.create_invite("admin", "creada desde la consola")
        print(f"Enlace de registro de administrador (válido {pdb.INVITE_DAYS} días, un solo uso):")
        print(f"https://{a.dominio}/registro?invitacion={token}")
        return
    DATA.mkdir(exist_ok=True)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s",
                        datefmt="%Y-%m-%d %H:%M:%S",
                        handlers=[logging.FileHandler(DATA / "plataforma.log", encoding="utf-8"),
                                  logging.StreamHandler(sys.stderr)], force=True)
    for noisy in ("urllib3", "ccxt"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
    server = make_server(a.port)
    server.bots.resume_all()
    threading.Thread(target=restart_on_update, args=(server,), daemon=True).start()
    log.info(f"Plataforma disponible en http://127.0.0.1:{a.port}/ ({server.db.count()} usuarios)")
    try:
        server.serve_forever()
    finally:
        for app in list(server.bots.apps.values()):
            bot.save_state(app.engine.state, app.engine.files.state)


if __name__ == "__main__":
    main()
