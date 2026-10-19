"""Panel de control del bot (se abre en el navegador).

    python panel.py               # abre el panel en http://127.0.0.1:8765
    python panel.py --no-browser  # sin abrir el navegador (para el arranque automático)

El panel y el bot funcionan en el mismo programa. Si cierras la pestaña del navegador,
el bot SIGUE funcionando; para apagarlo todo usa el botón "Apagar" del panel.
Si el bot estaba en marcha cuando se apagó el PC, al volver a abrir el panel continúa solo.

Seguridad: solo escucha en este ordenador (127.0.0.1) y las acciones exigen una cabecera
especial, así que ninguna página web puede controlar el bot.
"""
import argparse
import json
import logging
import socket
import sys
import threading
import time
import webbrowser
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import numpy as np

import bot
import exchange as xch
from config import CONFIG
from strategy import add_signals

ROOT = Path(__file__).resolve().parent
WEB_DIR = ROOT / "web"
ALLOWED_HOSTS = {"127.0.0.1", "localhost"}
log = logging.getLogger("bot")


def tail(path: Path, n: int = 200) -> list:
    if not path.exists():
        return []
    with path.open("rb") as f:
        f.seek(0, 2)
        f.seek(max(0, f.tell() - 65536))
        return f.read().decode("utf-8", "replace").splitlines()[-n:]


def _series(df, col):
    if col not in df:
        return []
    return [{"time": int(t), "value": round(float(v), 8)}
            for t, v in zip(df["ts"] // 1000, df[col]) if v == v]


def _utc_seconds(text):
    try:
        return int(datetime.strptime(text[:19], "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc).timestamp())
    except (TypeError, ValueError):
        return None


class PanelApp:
    def __init__(self, engine, data_ex=None):
        self.engine = engine
        self.data_ex = data_ex or engine.ex
        self.cache = {}
        self.lock = threading.Lock()
        self.server = None

    def candles(self, sym: str) -> dict:
        cfg = self.engine.cfg
        if sym not in cfg.symbols:
            raise ValueError(f"Moneda desconocida: {sym}")
        with self.lock:
            hit = self.cache.get(sym)
            if hit and time.time() - hit[0] < 30:
                return hit[1]
        rows = bot.retry(self.data_ex.fetch_ohlcv, sym, cfg.timeframe, limit=500)
        df = add_signals(xch.to_df(rows), cfg).tail(300).reset_index(drop=True)
        times = (df["ts"] // 1000).to_numpy()
        tf = xch.timeframe_seconds(cfg.timeframe)

        def snap(t):                           # coloca la marca en la vela correspondiente
            if t is None or t < times[0] or t > times[-1] + tf:
                return None
            return int(times[max(0, np.searchsorted(times, t, side="right") - 1)])

        markers = []
        for tr in bot.read_trades():
            if tr["par"] != sym:
                continue
            pnl = float(tr["pnl_pct"] or 0)
            for when, kind in ((tr["entrada"], "buy"), (tr["salida"], "sell")):
                t = snap(_utc_seconds(when))
                if t is None:
                    continue
                markers.append({"time": t, "position": "belowBar" if kind == "buy" else "aboveBar",
                                "shape": "arrowUp" if kind == "buy" else "arrowDown",
                                "color": "#2ebd85" if kind == "buy" else ("#2ebd85" if pnl > 0 else "#f6465d"),
                                "text": "Compra" if kind == "buy" else f"Venta {pnl:+.1%}"})
        lines = []
        pos = self.engine.state["positions"].get(sym)
        if pos:
            t = snap(_utc_seconds(pos.get("entry_time")))
            if t is not None:
                markers.append({"time": t, "position": "belowBar", "shape": "arrowUp",
                                "color": "#f5b83d", "text": "Compra (abierta)"})
            snap_pos = next(p for p in self.engine.snapshot()["positions"] if p["symbol"] == sym)
            lines.append({"price": pos["entry"], "title": "Entrada", "color": "#8b93a7"})
            if snap_pos["stop"]:
                lines.append({"price": snap_pos["stop"], "title": snap_pos["stop_kind"].capitalize(),
                              "color": "#f6465d"})
            if snap_pos["tp"]:
                lines.append({"price": snap_pos["tp"], "title": "Take profit", "color": "#2ebd85"})
        markers.sort(key=lambda m: m["time"])
        kind = cfg.ma_type.upper()
        payload = {
            "symbol": sym, "timeframe": cfg.timeframe,
            "candles": [{"time": int(r.ts // 1000), "open": r.open, "high": r.high, "low": r.low,
                         "close": r.close} for r in df.itertuples()],
            "ma_fast": _series(df, "ma_fast"), "ma_slow": _series(df, "ma_slow"),
            "ma_trend": _series(df, "ma_trend"),
            "labels": {"ma_fast": f"{kind} {cfg.fast}", "ma_slow": f"{kind} {cfg.slow}",
                       "ma_trend": f"{kind} {cfg.trend_filter}" if cfg.trend_filter else None},
            "markers": markers, "lines": lines,
        }
        with self.lock:
            self.cache[sym] = (time.time(), payload)
        return payload

    def invalidate(self):
        with self.lock:
            self.cache.clear()


class Handler(BaseHTTPRequestHandler):
    server_version = "BotPanel"

    def log_message(self, *args):
        pass

    def _send(self, code, body: bytes, ctype: str):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, obj, code=200):
        self._send(code, json.dumps(obj, default=str).encode("utf-8"), "application/json; charset=utf-8")

    def _host_ok(self) -> bool:
        host = (self.headers.get("Host") or "").rsplit(":", 1)[0]
        return host in ALLOWED_HOSTS

    def do_GET(self):
        if not self._host_ok():
            return self._json({"ok": False, "error": "host no permitido"}, 403)
        app = self.server.app
        u = urlparse(self.path)
        q = parse_qs(u.query)
        try:
            if u.path in ("/", "/index.html"):
                self._send(200, (WEB_DIR / "panel.html").read_bytes(), "text/html; charset=utf-8")
            elif u.path == "/favicon.ico" and (ROOT / "assets" / "bot.ico").exists():
                self._send(200, (ROOT / "assets" / "bot.ico").read_bytes(), "image/x-icon")
            elif u.path == "/api/status":
                self._json(app.engine.snapshot())
            elif u.path == "/api/candles":
                self._json(app.candles(q.get("symbol", [app.engine.cfg.symbols[0]])[0]))
            elif u.path == "/api/trades":
                self._json(bot.read_trades()[-200:][::-1])
            elif u.path == "/api/log":
                self._json({"lines": tail(bot.LOG_FILE, 200)})
            else:
                self._json({"ok": False, "error": "no encontrado"}, 404)
        except Exception as e:
            log.exception(f"Error del panel en {u.path}")
            self._json({"ok": False, "error": str(e)}, 500)

    def do_POST(self):
        # La cabecera X-Panel obliga al navegador a pedir permiso (CORS), que este servidor
        # nunca concede a otras webs: solo el propio panel puede ejecutar acciones.
        if not self._host_ok() or self.headers.get("X-Panel") != "1":
            return self._json({"ok": False, "error": "no autorizado"}, 403)
        app = self.server.app
        e = app.engine
        u = urlparse(self.path)
        q = parse_qs(u.query)
        try:
            if u.path == "/api/start":
                e.start()
            elif u.path == "/api/stop":
                e.stop()
            elif u.path == "/api/close":
                e.close_position(q["symbol"][0])
            elif u.path == "/api/resume":
                e.resume_after_halt()
            elif u.path == "/api/shutdown":
                if e.is_running():
                    e.stop()                   # apagado a propósito: no se reanuda solo
                self._json({"ok": True})
                log.info("Panel apagado desde el navegador.")
                threading.Thread(target=self.server.shutdown, daemon=True).start()
                return
            else:
                return self._json({"ok": False, "error": "no encontrado"}, 404)
            app.invalidate()
            self._json({"ok": True})
        except (Exception, SystemExit) as ex:
            log.warning(f"Acción {u.path} fallida: {ex}")
            self._json({"ok": False, "error": str(ex)}, 400)


def make_server(engine, port: int = None, host: str = "127.0.0.1", data_ex=None):
    server = ThreadingHTTPServer((host, CONFIG.panel_port if port is None else port), Handler)
    server.daemon_threads = True
    server.app = PanelApp(engine, data_ex)
    server.app.server = server
    return server


def port_in_use(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex(("127.0.0.1", port)) == 0


def price_watcher(engine, stop_event):
    """Con el bot parado, mantiene los precios del panel actualizados."""
    while not stop_event.wait(20):
        if engine.is_running():
            continue
        try:
            engine.refresh_prices()
        except (Exception, SystemExit) as e:
            engine.last_error = str(e)


def main():
    p = argparse.ArgumentParser(description="Panel de control del bot")
    p.add_argument("--no-browser", action="store_true", help="no abrir el navegador")
    p.add_argument("--port", type=int, default=CONFIG.panel_port)
    a = p.parse_args()
    url = f"http://127.0.0.1:{a.port}/"

    if port_in_use(a.port):                    # ya abierto: solo mostramos el navegador
        if not a.no_browser:
            webbrowser.open(url)
        return

    bot.setup_logging(console=bool(sys.stderr))
    engine = bot.Engine()
    try:
        engine.connect()
        engine.refresh_prices()
    except (Exception, SystemExit) as e:
        engine.last_error = f"No se pudo conectar con Binance: {e}"
        log.error(engine.last_error)

    server = make_server(engine, a.port, data_ex=xch.make_exchange(CONFIG, private=False))
    log.info(f"Panel disponible en {url}")

    if engine.state.get("running") and not engine.state.get("halted") and engine.broker:
        log.info("El bot estaba en marcha la última vez: continúa automáticamente.")
        try:
            engine.start()
        except Exception as e:
            engine.last_error = str(e)

    stop_event = threading.Event()
    threading.Thread(target=price_watcher, args=(engine, stop_event), daemon=True).start()
    if not a.no_browser:
        threading.Timer(1.0, webbrowser.open, [url]).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        stop_event.set()
        # No se llama a engine.stop(): así, si se apaga el PC con el bot en marcha,
        # al volver a abrir el panel el bot continúa donde estaba.
        bot.save_state(engine.state)


if __name__ == "__main__":
    try:
        main()
    except Exception:                          # con pythonw no hay ventana: guardamos el error
        import traceback
        (ROOT / "panel_error.txt").write_text(traceback.format_exc(), encoding="utf-8")
        raise
