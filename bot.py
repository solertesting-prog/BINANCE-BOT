"""Motor del bot de trading (Binance spot, solo compras en largo).

Normalmente se usa desde el PANEL (doble clic en el icono del escritorio o en panel.bat).
También funciona en la consola:

    python bot.py             # arranca el bot en esta ventana
    python bot.py --status    # muestra el estado guardado sin conectarse

Qué hace en cada ciclo (cada `poll_seconds`):
  1. Lee los precios y comprueba el interruptor de seguridad (drawdown máximo).
  2. Para cada moneda con compra abierta: comprueba si saltó el stop en Binance, el stop
     o el take profit; si no, sube el stop dinámico (y lo actualiza en Binance).
  3. Al cerrar cada vela, calcula la señal (misma lógica que el backtest) y compra o vende.

Robustez:
  - En modo real deja una orden STOP_LOSS_LIMIT en Binance: protege aunque el PC se apague.
    El bot vigila además el precio por su cuenta (doble protección).
  - Al arrancar comprueba que su estado cuadra con la cuenta (reconciliación).
  - Reintenta las consultas si falla la red; las órdenes NUNCA se reintentan a ciegas.
  - Guarda el estado en state.json de forma atómica y lo recupera al reiniciar.
"""
import argparse
import csv
import json
import logging
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

import exchange as xch
from config import CONFIG
from strategy import add_signals, describe, exit_levels, initial_stop, position_spend, warmup_candles

STATE_FILE = Path("state.json")
TRADES_FILE = Path("trades_log.csv")
LOG_FILE = Path("bot.log")
TRADE_FIELDS = ["entrada", "salida", "par", "precio_entrada", "precio_salida", "cantidad",
                "motivo", "pnl_pct", "pnl_usdt", "modo"]
log = logging.getLogger("bot")


# ---------- utilidades ----------
def setup_logging(console: bool = True):
    handlers = [logging.FileHandler(LOG_FILE, encoding="utf-8")]
    if console and sys.stderr:
        handlers.append(logging.StreamHandler())
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s",
                        datefmt="%Y-%m-%d %H:%M:%S", handlers=handlers, force=True)
    for noisy in ("urllib3", "ccxt"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def notify(msg: str, cfg=CONFIG):
    log.info(msg)
    if cfg.telegram_token and cfg.telegram_chat_id:
        try:
            requests.post(f"https://api.telegram.org/bot{cfg.telegram_token}/sendMessage",
                          data={"chat_id": cfg.telegram_chat_id, "text": msg}, timeout=10)
        except Exception as e:
            log.warning(f"No se pudo enviar a Telegram: {e}")


def _retryable_errors() -> tuple:
    try:
        import ccxt
        err = getattr(ccxt, "NetworkError", None)
        return (err,) if isinstance(err, type) else ()
    except ImportError:
        return ()


def retry(fn, *args, tries: int = 3, **kwargs):
    """Repite una CONSULTA si falla la red. No usar con órdenes (podrían duplicarse)."""
    errors = _retryable_errors()
    for i in range(tries):
        try:
            return fn(*args, **kwargs)
        except errors as e:
            if i == tries - 1:
                raise
            log.warning(f"Fallo de red ({e}); reintentando en {2 * (i + 1)} s...")
            time.sleep(2 * (i + 1))


# ---------- estado ----------
def new_state(cfg) -> dict:
    return {"version": 2, "positions": {}, "last_candle": {}, "paper_usdt": cfg.paper_balance,
            "start_equity": None, "halted": False, "last_summary": None, "running": False,
            "equity_history": []}


def load_state(cfg=CONFIG) -> dict:
    s = new_state(cfg)
    if not STATE_FILE.exists():
        return s
    old = json.loads(STATE_FILE.read_text(encoding="utf-8"))
    if "positions" in old:
        s.update(old)
        return s
    # Estado de la versión anterior (una sola moneda): se migra
    sym = cfg.symbols[0]
    if old.get("in_position"):
        s["positions"][sym] = {"qty": old["qty"], "entry": old["entry"],
                               "peak": old.get("peak") or old["entry"], "atr": 0.0,
                               "entry_time": old.get("entry_time"), "spent": old["qty"] * old["entry"],
                               "stop_order": None}
    for k in ("paper_usdt", "start_equity", "halted", "last_summary"):
        if old.get(k) is not None:
            s[k] = old[k]
    if old.get("last_candle"):
        s["last_candle"][sym] = old["last_candle"]
    return s


def save_state(s: dict):
    tmp = STATE_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(s, indent=2), encoding="utf-8")
    tmp.replace(STATE_FILE)                      # escritura atómica: nunca queda a medias


def read_trades() -> list:
    if not TRADES_FILE.exists():
        return []
    with TRADES_FILE.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def append_trade(row: dict):
    new = not TRADES_FILE.exists()
    with TRADES_FILE.open("a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=TRADE_FIELDS)
        if new:
            w.writeheader()
        w.writerow(row)


# ---------- brokers ----------
class PaperBroker:
    """Simulado: precios reales, dinero ficticio."""
    live = False

    def __init__(self, ex, state, cfg):
        self.ex, self.s, self.cfg = ex, state, cfg

    def cash(self) -> float:
        return self.s["paper_usdt"]

    def equity(self, prices: dict) -> float:
        return self.s["paper_usdt"] + sum(p["qty"] * prices.get(sym, p["entry"])
                                          for sym, p in self.s["positions"].items())

    def buy(self, sym, spend, price):
        self.s["paper_usdt"] -= spend
        return spend * (1 - self.cfg.fee) / price, price

    def sell(self, sym, pos, price):
        self.s["paper_usdt"] += pos["qty"] * price * (1 - self.cfg.fee)
        return price

    def place_stop(self, sym, qty, stop):
        return None

    def update_stop(self, sym, pos, stop):
        return None

    def cancel_stop(self, sym, pos):
        pos["stop_order"] = None

    def stop_fill(self, sym, pos):
        return None

    def base_total(self, sym):
        pos = self.s["positions"].get(sym)
        return pos["qty"] if pos else 0.0


class LiveBroker(PaperBroker):
    """Real (o testnet): órdenes de verdad en Binance."""
    live = True

    def _balance(self):
        return retry(self.ex.fetch_balance)

    def _free(self, asset):
        return float(self._balance()["free"].get(asset) or 0)

    def quote(self):
        return self.cfg.symbols[0].split("/")[1]

    def cash(self):
        return self._free(self.quote())

    def equity(self, prices):
        quote_total = float(self._balance()["total"].get(self.quote()) or 0)
        # solo cuenta lo que ha comprado el bot, no el resto de tus monedas
        return quote_total + sum(p["qty"] * prices.get(sym, p["entry"])
                                 for sym, p in self.s["positions"].items())

    def base_total(self, sym):
        return float(self._balance()["total"].get(sym.split("/")[0]) or 0)

    def buy(self, sym, spend, price):
        base = sym.split("/")[0]
        before = self._free(base)
        if self.ex.has.get("createMarketBuyOrderWithCost"):
            order = self.ex.create_market_buy_order_with_cost(sym, spend)
        else:
            amount = float(self.ex.amount_to_precision(sym, spend / price))
            order = self.ex.create_market_buy_order(sym, amount)
        fill = float(order.get("average") or price)
        got = self._free(base) - before                # lo que ha llegado de verdad (sin comisión)
        qty = got if got > 0 else float(order.get("filled") or spend / fill) * (1 - self.cfg.fee)
        return qty, fill

    def sell(self, sym, pos, price):
        self.cancel_stop(sym, pos)                     # libera las monedas bloqueadas por el stop
        qty = min(pos["qty"], self._free(sym.split("/")[0]))
        amount = float(self.ex.amount_to_precision(sym, qty))
        order = self.ex.create_market_sell_order(sym, amount)
        return float(order.get("average") or price)

    def place_stop(self, sym, qty, stop):
        if not self.cfg.exchange_stops or not stop:
            return None
        try:
            amount = float(self.ex.amount_to_precision(sym, min(qty, self._free(sym.split("/")[0]))))
            stop_p = float(self.ex.price_to_precision(sym, stop))
            limit_p = float(self.ex.price_to_precision(sym, stop * (1 - self.cfg.stop_limit_gap)))
            o = self.ex.create_order(sym, "STOP_LOSS_LIMIT", "sell", amount, limit_p, {"stopPrice": stop_p})
            log.info(f"Stop colocado en Binance para {sym}: {stop_p}")
            return {"id": o["id"], "stop": stop_p}
        except Exception as e:
            notify(f"⚠️ No se pudo colocar el stop en Binance para {sym} ({e}). "
                   f"El bot sigue vigilando el precio por su cuenta.", self.cfg)
            return None

    def update_stop(self, sym, pos, stop):
        cur = pos.get("stop_order")
        if cur and stop <= cur["stop"] * 1.003:        # solo si sube algo (evita mover órdenes sin parar)
            return cur
        self.cancel_stop(sym, pos)
        return self.place_stop(sym, pos["qty"], stop)

    def cancel_stop(self, sym, pos):
        so = pos.get("stop_order")
        if so:
            try:
                self.ex.cancel_order(so["id"], sym)
            except Exception as e:                     # puede que ya se haya ejecutado
                log.warning(f"No se pudo cancelar el stop {so['id']} de {sym}: {e}")
        pos["stop_order"] = None

    def stop_fill(self, sym, pos):
        """Precio de venta si el stop de Binance se ejecutó; None si sigue pendiente."""
        so = pos.get("stop_order")
        if not so:
            return None
        o = retry(self.ex.fetch_order, so["id"], sym)
        status = o.get("status")
        if status == "closed":
            return float(o.get("average") or o.get("price") or so["stop"])
        if status in ("canceled", "expired", "rejected"):
            log.warning(f"El stop de {sym} en Binance está '{status}'; se volverá a colocar.")
            pos["stop_order"] = None
        return None


# ---------- motor ----------
class Engine:
    def __init__(self, cfg=CONFIG, ex=None):
        self.cfg = cfg
        self.ex = ex
        self.broker = None
        self.state = load_state(cfg)
        self.lock = threading.RLock()
        self.thread = None
        self._stop_event = threading.Event()
        self.prices, self.frames, self.signals = {}, {}, {}
        self.last_error, self.last_cycle, self.last_equity = None, None, None

    # --- conexión ---
    def connect(self):
        cfg = self.cfg
        if cfg.mode not in ("paper", "live"):
            raise SystemExit("MODE debe ser 'paper' o 'live' en el archivo .env")
        if len({s.split("/")[1] for s in cfg.symbols}) > 1:
            raise SystemExit("Todas las monedas deben cotizar contra lo mismo (p. ej. todas /USDT)")
        if self.ex is None:
            self.ex = xch.make_exchange(cfg, private=(cfg.mode == "live"))
        if hasattr(self.ex, "load_markets"):
            retry(self.ex.load_markets)
        missing = [s for s in cfg.symbols if s not in getattr(self.ex, "markets", {s: 1 for s in cfg.symbols})]
        if missing:
            raise SystemExit(f"Binance no tiene estos pares: {', '.join(missing)}")
        self.broker = (LiveBroker if cfg.mode == "live" else PaperBroker)(self.ex, self.state, cfg)

    def min_cost(self, sym) -> float:
        m = getattr(self.ex, "markets", {}).get(sym) or {}
        return ((m.get("limits") or {}).get("cost") or {}).get("min") or 10.0

    # --- operaciones ---
    def _close(self, sym, price, reason, already_sold=False):
        pos = self.state["positions"].pop(sym)
        fill = price if already_sold else self.broker.sell(sym, pos, price)
        pnl_pct = (fill / pos["entry"]) * (1 - self.cfg.fee) ** 2 - 1
        pnl_usdt = pos["qty"] * fill * (1 - self.cfg.fee) - pos.get("spent", pos["qty"] * pos["entry"])
        append_trade({"entrada": pos.get("entry_time"), "salida": now_iso(), "par": sym,
                      "precio_entrada": round(pos["entry"], 8), "precio_salida": round(fill, 8),
                      "cantidad": pos["qty"], "motivo": reason, "pnl_pct": round(pnl_pct, 5),
                      "pnl_usdt": round(pnl_usdt, 2), "modo": self.cfg.mode})
        notify(f"🔴 VENTA {sym} {pos['qty']:.6f} a {fill:.2f} | {reason} | {pnl_pct:+.2%} "
               f"({pnl_usdt:+.2f} USDT) [{self.cfg.mode}]", self.cfg)

    def _open(self, sym, price, atr_value):
        cfg, b, s = self.cfg, self.broker, self.state
        if len(s["positions"]) >= cfg.max_open_positions:
            log.info(f"Señal de compra en {sym} ignorada: ya hay {len(s['positions'])} posiciones abiertas")
            return
        stop0 = initial_stop(price, atr_value, cfg)
        spend = position_spend(b.equity(self.prices), b.cash(), price, stop0, cfg)
        if spend < self.min_cost(sym):
            notify(f"Saldo insuficiente para comprar {sym} ({spend:.2f} < mínimo {self.min_cost(sym):g})", cfg)
            return
        qty, fill = b.buy(sym, spend, price)
        pos = {"qty": qty, "entry": fill, "peak": fill, "atr": atr_value, "entry_time": now_iso(),
               "spent": spend, "stop_order": None}
        s["positions"][sym] = pos
        stop, _, _ = exit_levels(fill, fill, atr_value, cfg)
        pos["stop_order"] = b.place_stop(sym, qty, stop)
        notify(f"🟢 COMPRA {sym} {qty:.6f} a {fill:.2f} ({spend:.2f} USDT) | stop {stop:.2f} "
               f"[{cfg.mode}]" if stop else f"🟢 COMPRA {sym} {qty:.6f} a {fill:.2f} [{cfg.mode}]", cfg)

    def _manage(self, sym, price):
        cfg, b, s = self.cfg, self.broker, self.state
        pos, exited = s["positions"].get(sym), False

        # 1) Salidas por precio
        if pos:
            fill = b.stop_fill(sym, pos)
            if fill:
                self._close(sym, fill, "stop loss (Binance)", already_sold=True)
                pos, exited = None, True
            else:
                stop, tp, kind = exit_levels(pos["entry"], pos["peak"], pos["atr"], cfg)
                if stop and price <= stop:
                    self._close(sym, price, kind)
                    pos, exited = None, True
                elif tp and price >= tp:
                    self._close(sym, price, "take profit")
                    pos, exited = None, True
                else:
                    pos["peak"] = max(pos["peak"], price)
                    new_stop, _, _ = exit_levels(pos["entry"], pos["peak"], pos["atr"], cfg)
                    if b.live and cfg.exchange_stops and new_stop:
                        pos["stop_order"] = (b.update_stop(sym, pos, new_stop) if pos.get("stop_order")
                                             else b.place_stop(sym, pos["qty"], new_stop))

        # 2) Señal de la estrategia: una vez por vela cerrada
        df = xch.fetch_closed_candles(self.ex, sym, cfg.timeframe, warmup_candles(cfg))
        last_ts = int(df["ts"].iloc[-1])
        if s["last_candle"].get(sym) == last_ts:
            return
        s["last_candle"][sym] = last_ts
        sig_df = add_signals(df, cfg)
        self.frames[sym] = sig_df
        sig = int(sig_df["signal"].iloc[-1])
        self.signals[sym] = sig
        log.info(f"{sym} vela {df.index[-1]:%Y-%m-%d %H:%M} cerrada | precio {price:.2f} | señal {sig}")

        if sig == 1 and not pos and not exited:
            atr_v = sig_df["atr"].iloc[-1]
            self._open(sym, price, float(atr_v) if atr_v == atr_v else 0.0)
        elif sig == -1 and pos:
            self._close(sym, price, "cruce bajista")

    def step(self):
        cfg, s, b = self.cfg, self.state, self.broker
        self.prices = {sym: float(retry(self.ex.fetch_ticker, sym)["last"]) for sym in cfg.symbols}

        eq = b.equity(self.prices)
        if s["start_equity"] is None:
            s["start_equity"] = eq
        if cfg.max_drawdown and eq < s["start_equity"] * (1 - cfg.max_drawdown):
            for sym in list(s["positions"]):
                self._close(sym, self.prices[sym], "interruptor de drawdown")
            s["halted"], s["running"] = True, False
            notify(f"⛔ Capital {eq:.2f} por debajo del límite de seguridad. Bot detenido. "
                   f"Revisa qué ha pasado antes de reactivarlo.", cfg)
            return

        for sym in cfg.symbols:
            self._manage(sym, self.prices[sym])

        eq = self.last_equity = b.equity(self.prices)
        hist = s["equity_history"]
        if not hist or time.time() - hist[-1][0] >= 3600:
            hist.append([int(time.time()), round(eq, 2)])
            del hist[:-2000]
        self._daily_summary(eq)
        self.last_cycle, self.last_error = now_iso(), None

    def _daily_summary(self, eq):
        s = self.state
        today = datetime.now(timezone.utc).date().isoformat()
        if s["last_summary"] == today:
            return
        s["last_summary"] = today
        pos = ", ".join(f"{sym} {self.prices[sym] / p['entry'] - 1:+.2%}" for sym, p in s["positions"].items())
        notify(f"📊 Resumen diario | capital {eq:.2f} ({eq / s['start_equity'] - 1:+.2%} desde el inicio) | "
               f"{'posiciones: ' + pos if pos else 'sin posiciones'}", self.cfg)

    def reconcile(self):
        """Al arrancar en real: comprueba que lo que cree el bot coincide con la cuenta."""
        b, s = self.broker, self.state
        if not b.live:
            return
        for sym, pos in list(s["positions"].items()):
            fill = b.stop_fill(sym, pos)
            if fill:
                self._close(sym, fill, "stop loss (Binance, con el bot parado)", already_sold=True)
            elif b.base_total(sym) < pos["qty"] * 0.5:
                price = float(retry(self.ex.fetch_ticker, sym)["last"])
                s["positions"].pop(sym)
                append_trade({"entrada": pos.get("entry_time"), "salida": now_iso(), "par": sym,
                              "precio_entrada": pos["entry"], "precio_salida": price, "cantidad": pos["qty"],
                              "motivo": "cerrada fuera del bot", "pnl_pct": round(price / pos["entry"] - 1, 5),
                              "pnl_usdt": round(pos["qty"] * (price - pos["entry"]), 2), "modo": self.cfg.mode})
                notify(f"⚠️ La posición de {sym} ya no está en la cuenta (¿vendida a mano?). "
                       f"Se da por cerrada.", self.cfg)
            elif self.cfg.exchange_stops and not pos.get("stop_order"):
                stop, _, _ = exit_levels(pos["entry"], pos["peak"], pos["atr"], self.cfg)
                pos["stop_order"] = b.place_stop(sym, pos["qty"], stop)

    # --- control (panel / consola) ---
    def is_running(self) -> bool:
        return bool(self.thread and self.thread.is_alive())

    def start(self, background: bool = True):
        with self.lock:
            if self.is_running():
                return
            if self.state["halted"]:
                raise RuntimeError("El bot está detenido por el interruptor de seguridad. Reactívalo primero.")
            if self.broker is None:
                self.connect()
            self.reconcile()
            self.state["running"] = True
            save_state(self.state)
            self._stop_event = threading.Event()
        notify(f"🤖 Bot iniciado | {', '.join(self.cfg.symbols)} {self.cfg.timeframe} | {describe(self.cfg)} | "
               f"modo {self.cfg.mode}{' (testnet)' if self.cfg.testnet else ''}", self.cfg)
        if background:
            self.thread = threading.Thread(target=self._loop, name="bot", daemon=True)
            self.thread.start()
        else:
            self.thread = threading.current_thread()
            self._loop()

    def _loop(self):
        while not self._stop_event.is_set() and not self.state["halted"]:
            with self.lock:
                try:
                    self.step()
                except Exception as e:      # errores de red, etc.: se registra y se reintenta
                    self.last_error = f"{type(e).__name__}: {e}"
                    log.exception(f"Error en el ciclo: {e}")
                save_state(self.state)
            self._stop_event.wait(self.cfg.poll_seconds)

    def stop(self, notify_user: bool = True):
        self._stop_event.set()
        with self.lock:
            self.state["running"] = False
            save_state(self.state)
        if notify_user:
            notify("■ Bot parado.", self.cfg)

    def close_position(self, sym):
        with self.lock:
            if sym not in self.state["positions"]:
                raise ValueError(f"No hay posición abierta en {sym}")
            if self.broker is None:
                self.connect()
            price = float(retry(self.ex.fetch_ticker, sym)["last"])
            self._close(sym, price, "cierre manual")
            save_state(self.state)

    def resume_after_halt(self):
        with self.lock:
            self.state["halted"] = False
            self.state["start_equity"] = None      # el nuevo punto de partida es el capital actual
            save_state(self.state)
        notify("Interruptor de seguridad reactivado manualmente.", self.cfg)

    # --- información para el panel ---
    def refresh_prices(self):
        """Actualiza precios aunque el bot esté parado (para el panel)."""
        with self.lock:
            if self.broker is None:
                self.connect()
            self.prices = {sym: float(retry(self.ex.fetch_ticker, sym)["last"]) for sym in self.cfg.symbols}
            self.last_equity = self.broker.equity(self.prices)

    def snapshot(self) -> dict:
        cfg, s = self.cfg, self.state
        positions = []
        for sym, p in s["positions"].items():
            price = self.prices.get(sym, p["entry"])
            stop, tp, kind = exit_levels(p["entry"], max(p["peak"], price), p["atr"], cfg)
            value = p["qty"] * price * (1 - cfg.fee)
            positions.append({"symbol": sym, "qty": p["qty"], "entry": p["entry"], "price": price,
                              "pnl_pct": price / p["entry"] - 1, "pnl_usdt": value - p.get("spent", p["qty"] * p["entry"]),
                              "stop": stop, "stop_kind": kind, "tp": tp, "entry_time": p.get("entry_time"),
                              "exchange_stop": bool(p.get("stop_order"))})
        cash = s["paper_usdt"] if cfg.mode == "paper" else None
        equity = None
        if cfg.mode == "paper":
            equity = cash + sum(x["qty"] * x["price"] for x in positions)
        else:
            equity = self.last_equity or (s["equity_history"][-1][1] if s["equity_history"] else None)
        trades = read_trades()
        pnl_closed = sum(float(t["pnl_usdt"] or 0) for t in trades)
        wins = sum(1 for t in trades if float(t["pnl_pct"] or 0) > 0)
        start = s["start_equity"] or (cfg.paper_balance if cfg.mode == "paper" else None)
        return {
            "mode": cfg.mode, "testnet": cfg.testnet, "running": self.is_running(), "halted": s["halted"],
            "symbols": list(cfg.symbols), "timeframe": cfg.timeframe, "strategy": describe(cfg),
            "equity": equity, "start_equity": start,
            "pnl_total_pct": (equity / start - 1) if equity and start else None,
            "cash": cash, "positions": positions, "max_positions": cfg.max_open_positions,
            "trades_count": len(trades), "win_rate": wins / len(trades) if trades else None,
            "pnl_closed": pnl_closed, "prices": self.prices, "signals": self.signals,
            "last_cycle": self.last_cycle, "last_error": self.last_error,
            "equity_history": s["equity_history"][-500:], "now": now_iso(),
            "settings": {"risk_per_trade": cfg.risk_per_trade, "max_drawdown": cfg.max_drawdown,
                         "exchange_stops": cfg.exchange_stops, "poll_seconds": cfg.poll_seconds},
        }


# ---------- consola ----------
def show_status(cfg=CONFIG):
    s = load_state(cfg)
    print(f"Configuración: {', '.join(cfg.symbols)} {cfg.timeframe} | {describe(cfg)} | modo {cfg.mode}")
    if s["halted"]:
        print("⛔ DETENIDO por el interruptor de seguridad (reactívalo desde el panel)")
    if not s["positions"]:
        print("Sin posiciones abiertas")
    for sym, p in s["positions"].items():
        stop, tp, kind = exit_levels(p["entry"], p["peak"], p["atr"], cfg)
        print(f"Posición {sym}: {p['qty']:.6f} desde {p['entry']:.2f} (máx. {p['peak']:.2f}) "
              f"abierta {p.get('entry_time')} UTC" + (f" | {kind}: {stop:.2f}" if stop else ""))
    if cfg.mode == "paper":
        print(f"Saldo simulado disponible: {s['paper_usdt']:.2f} USDT")
    trades = read_trades()
    if trades:
        wins = sum(1 for t in trades if float(t["pnl_pct"]) > 0)
        total = sum(float(t["pnl_usdt"]) for t in trades)
        print(f"Operaciones cerradas: {len(trades)} | acierto {wins / len(trades):.0%} | resultado {total:+.2f} USDT")
        print("\nÚltimas operaciones:")
        print(f"  {'salida (UTC)':<17} {'par':<10} {'entrada':>10} {'salida':>10}  {'motivo':<20} {'resultado':>9} {'USDT':>8}")
        for t in trades[-5:]:
            print(f"  {t['salida'][:16]:<17} {t['par']:<10} {float(t['precio_entrada']):>10.2f} "
                  f"{float(t['precio_salida']):>10.2f}  {t['motivo'][:20]:<20} {float(t['pnl_pct']):>+9.2%} "
                  f"{float(t['pnl_usdt']):>+8.2f}")


def main():
    p = argparse.ArgumentParser(description="Bot de cruce de medias para Binance")
    p.add_argument("--status", action="store_true", help="muestra el estado y sale")
    if p.parse_args().status:
        return show_status()
    setup_logging()
    engine = Engine()
    try:
        engine.start(background=False)
    except KeyboardInterrupt:
        pass
    except RuntimeError as e:
        raise SystemExit(str(e))
    finally:
        if engine.broker is not None:
            engine.stop()


if __name__ == "__main__":
    main()
