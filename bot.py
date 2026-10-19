"""Bot de trading: cruce de medias en Binance spot.

    python bot.py             # arranca el bot (modo según MODE en .env; por defecto "paper", simulado)
    python bot.py --status    # muestra el estado actual sin operar

- Cada `poll_seconds` revisa el precio para stop loss, trailing stop y take profit.
- Al cerrar cada vela, evalúa el cruce de medias y los filtros (misma lógica que el backtest).
- Guarda su estado en state.json: puedes pararlo y relanzarlo sin perder la posición.
- Registra cada operación cerrada en trades_log.csv y todo lo demás en bot.log.
- Si configuras Telegram, avisa de cada compra/venta y manda un resumen diario.
"""
import argparse
import csv
import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

from config import CONFIG as cfg
from strategy import add_signals, describe, exit_levels, warmup_candles

STATE_FILE = Path("state.json")
TRADES_FILE = Path("trades_log.csv")
log = logging.getLogger("bot")


# ---------- utilidades ----------
def setup_logging():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s",
                        handlers=[logging.FileHandler("bot.log"), logging.StreamHandler()])


def notify(msg: str):
    log.info(msg)
    if cfg.telegram_token and cfg.telegram_chat_id:
        try:
            requests.post(f"https://api.telegram.org/bot{cfg.telegram_token}/sendMessage",
                          data={"chat_id": cfg.telegram_chat_id, "text": msg}, timeout=10)
        except Exception as e:
            log.warning(f"No se pudo enviar a Telegram: {e}")


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


DEFAULT_STATE = {"in_position": False, "qty": 0.0, "entry": 0.0, "peak": 0.0, "entry_time": None,
                 "last_candle": None, "paper_usdt": None, "start_equity": None, "halted": False,
                 "last_summary": None}


def load_state() -> dict:
    s = dict(DEFAULT_STATE, paper_usdt=cfg.paper_balance)
    if STATE_FILE.exists():
        s.update(json.loads(STATE_FILE.read_text()))   # estados antiguos reciben los campos nuevos
    return s


def save_state(s: dict):
    tmp = STATE_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(s, indent=2))
    tmp.replace(STATE_FILE)                              # escritura atómica: nunca queda a medias


def log_trade(s: dict, exit_price: float, qty: float, reason: str):
    new = not TRADES_FILE.exists()
    pnl_pct = (exit_price / s["entry"]) * (1 - cfg.fee) ** 2 - 1
    with TRADES_FILE.open("a", newline="") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["entrada", "salida", "par", "precio_entrada", "precio_salida",
                        "cantidad", "motivo", "pnl_pct", "pnl_usdt", "modo"])
        w.writerow([s["entry_time"], now_iso(), cfg.symbol, round(s["entry"], 2), round(exit_price, 2),
                    qty, reason, round(pnl_pct, 5), round(qty * s["entry"] * pnl_pct, 2), cfg.mode])
    return pnl_pct


# ---------- ejecución (simulada o real) ----------
class Broker:
    def __init__(self, ex, state):
        self.ex, self.s = ex, state
        self.base, self.quote = cfg.symbol.split("/")
        self.market = ex.market(cfg.symbol)

    def free(self, asset: str) -> float:
        return float(self.ex.fetch_balance()["free"].get(asset, 0) or 0)

    def usdt_balance(self) -> float:
        return self.s["paper_usdt"] if cfg.mode == "paper" else self.free(self.quote)

    def equity(self, price: float) -> float:
        if cfg.mode == "paper":
            return self.s["paper_usdt"] + self.s["qty"] * price
        bal = self.ex.fetch_balance()["total"]
        return float(bal.get(self.quote, 0) or 0) + float(bal.get(self.base, 0) or 0) * price

    def buy(self, price: float) -> bool:
        spend = self.usdt_balance() * cfg.position_pct
        min_cost = ((self.market.get("limits") or {}).get("cost") or {}).get("min") or 10
        if spend < min_cost:
            notify(f"Saldo insuficiente para comprar ({spend:.2f} {self.quote} < mínimo {min_cost})")
            return False
        if cfg.mode == "paper":
            qty, fill = spend * (1 - cfg.fee) / price, price
            self.s["paper_usdt"] -= spend
        else:
            if self.ex.has.get("createMarketBuyOrderWithCost"):
                order = self.ex.create_market_buy_order_with_cost(cfg.symbol, spend)
            else:
                amount = float(self.ex.amount_to_precision(cfg.symbol, spend / price))
                order = self.ex.create_market_buy_order(cfg.symbol, amount)
            fill = float(order.get("average") or price)
            filled = float(order.get("filled") or 0)
            # La comisión puede descontarse en la moneda comprada: nunca contamos más de lo disponible
            qty = min(filled, self.free(self.base)) if filled else self.free(self.base)
        self.s.update(in_position=True, qty=qty, entry=fill, peak=fill, entry_time=now_iso())
        notify(f"🟢 COMPRA {qty:.6f} {self.base} a {fill:.2f} ({cfg.mode})")
        return True

    def sell(self, price: float, reason: str):
        qty = self.s["qty"]
        if cfg.mode == "paper":
            self.s["paper_usdt"] += qty * price * (1 - cfg.fee)
            fill = price
        else:
            qty = min(qty, self.free(self.base))          # solo vende lo que compró el bot
            amount = float(self.ex.amount_to_precision(cfg.symbol, qty))
            order = self.ex.create_market_sell_order(cfg.symbol, amount)
            fill = float(order.get("average") or price)
        pnl = log_trade(self.s, fill, qty, reason)
        notify(f"🔴 VENTA {qty:.6f} {self.base} a {fill:.2f} | {reason} | {pnl:+.2%} ({cfg.mode})")
        self.s.update(in_position=False, qty=0.0, entry=0.0, peak=0.0, entry_time=None)


# ---------- lógica de cada ciclo ----------
def check_exits(broker: Broker, s: dict, price: float) -> bool:
    """Stop loss / trailing / take profit. Devuelve True si ha cerrado la posición."""
    if not s["in_position"]:
        return False
    stop, tp = exit_levels(s["entry"], s["peak"], cfg)
    if stop and price <= stop:
        fixed = s["entry"] * (1 - cfg.stop_loss) if cfg.stop_loss else 0
        broker.sell(price, "trailing stop" if stop > fixed else "stop loss")
        return True
    if tp and price >= tp:
        broker.sell(price, "take profit")
        return True
    s["peak"] = max(s["peak"], price)
    return False


def daily_summary(broker: Broker, s: dict, price: float, eq: float):
    today = datetime.now(timezone.utc).date().isoformat()
    if s["last_summary"] == today:
        return
    s["last_summary"] = today
    pos = (f"en posición: {s['qty']:.6f} {broker.base} desde {s['entry']:.2f} ({price / s['entry'] - 1:+.2%})"
           if s["in_position"] else "sin posición")
    notify(f"📊 Resumen diario | capital {eq:.2f} {broker.quote} "
           f"({eq / s['start_equity'] - 1:+.2%} desde el inicio) | {pos}")


def step(ex, broker: Broker, s: dict):
    from exchange import fetch_closed_candles
    price = float(ex.fetch_ticker(cfg.symbol)["last"])

    # 1) Interruptor de seguridad por drawdown
    eq = broker.equity(price)
    if s["start_equity"] is None:
        s["start_equity"] = eq
    if cfg.max_drawdown and eq < s["start_equity"] * (1 - cfg.max_drawdown):
        if s["in_position"]:
            broker.sell(price, "interruptor de drawdown")
        s["halted"] = True
        notify(f"⛔ Capital {eq:.2f} por debajo del límite. Bot detenido. Revisa antes de relanzar.")
        return

    # 2) Salidas por precio (en cualquier momento, no solo al cierre de vela)
    exited = check_exits(broker, s, price)
    daily_summary(broker, s, price, eq)

    # 3) Señal de la estrategia: una sola vez por vela cerrada
    df = fetch_closed_candles(ex, cfg.symbol, cfg.timeframe, warmup_candles(cfg))
    last_ts = int(df["ts"].iloc[-1])
    if last_ts == s["last_candle"]:
        return
    s["last_candle"] = last_ts
    sig = int(add_signals(df, cfg)["signal"].iloc[-1])
    log.info(f"Vela cerrada {df.index[-1]:%Y-%m-%d %H:%M} | precio {price:.2f} | señal {sig} | capital {eq:.2f}")

    if sig == 1 and not s["in_position"] and not exited:
        broker.buy(price)
    elif sig == -1 and s["in_position"]:
        broker.sell(price, "cruce bajista")


# ---------- arranque ----------
def show_status():
    s = load_state()
    print(f"Configuración: {cfg.symbol} {cfg.timeframe} | {describe(cfg)} | modo {cfg.mode}")
    if s["halted"]:
        print("⛔ DETENIDO por el interruptor de drawdown (borra state.json para reiniciar)")
    if s["in_position"]:
        print(f"Posición: {s['qty']:.6f} desde {s['entry']:.2f} (máx. {s['peak']:.2f}) abierta {s['entry_time']} UTC")
        stop, tp = exit_levels(s["entry"], s["peak"], cfg)
        print(f"Stop actual: {stop:.2f}" if stop else "Sin stop", "|", f"Take profit: {tp:.2f}" if tp else "Sin TP")
    else:
        print("Sin posición abierta")
    if cfg.mode == "paper":
        print(f"Saldo simulado: {s['paper_usdt']:.2f} USDT")
    if TRADES_FILE.exists():
        import pandas as pd
        t = pd.read_csv(TRADES_FILE)
        print(f"Operaciones cerradas: {len(t)} | acierto {(t.pnl_pct > 0).mean():.0%} | "
              f"resultado {t.pnl_usdt.sum():+.2f} USDT")
        last = t.tail(5)
        print("\nÚltimas operaciones:")
        print(f"  {'salida (UTC)':<19}  {'entrada':>10}  {'salida':>10}  {'motivo':<14} {'resultado':>9} {'USDT':>8}")
        for x in last.itertuples():
            print(f"  {str(x.salida)[:16]:<19}  {x.precio_entrada:>10.2f}  {x.precio_salida:>10.2f}  "
                  f"{x.motivo:<14} {x.pnl_pct:>+9.2%} {x.pnl_usdt:>+8.2f}")


def main():
    p = argparse.ArgumentParser(description="Bot de cruce de medias para Binance")
    p.add_argument("--status", action="store_true", help="muestra el estado y sale")
    if p.parse_args().status:
        return show_status()

    if cfg.mode not in ("paper", "live"):
        raise SystemExit("MODE debe ser 'paper' o 'live'")
    setup_logging()
    from exchange import make_exchange
    ex = make_exchange(cfg, private=(cfg.mode == "live"))
    ex.load_markets()
    s = load_state()
    if s["halted"]:
        raise SystemExit("El bot está detenido por el interruptor de drawdown. Borra state.json para reiniciar.")

    broker = Broker(ex, s)
    notify(f"🤖 Bot iniciado | {cfg.symbol} {cfg.timeframe} | {describe(cfg)} | "
           f"modo {cfg.mode}{' (testnet)' if cfg.testnet else ''}")
    try:
        while not s["halted"]:
            try:
                step(ex, broker, s)
            except Exception as e:  # errores de red, etc.: registra y reintenta en el siguiente ciclo
                log.exception(f"Error en el ciclo: {e}")
            save_state(s)
            time.sleep(cfg.poll_seconds)
    except KeyboardInterrupt:
        pass
    finally:
        save_state(s)
        notify("Bot parado.")


if __name__ == "__main__":
    main()
